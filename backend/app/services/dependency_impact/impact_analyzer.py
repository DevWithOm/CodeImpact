"""Finding-level impact analysis engine for CodeImpact.

Evaluates direct dependants (incoming import edges) and direct dependencies
(outgoing import edges) for static analysis findings mapped to a dependency graph.
Preserves graph invariants, excludes transitive dependencies, detects self-loops,
incorporates circular dependency context, and generates traceable edge evidence.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from pydantic import BaseModel

from backend.app.schemas.impact import (
    DirectDependant,
    EnrichedFinding,
    FindingImpactSummary,
    ImpactEvidence,
)
from backend.app.services.dependency_impact.finding_mapper import (
    MAPPING_STATUS_INVALID_PATH,
    MAPPING_STATUS_MAPPED,
    MAPPING_STATUS_MISSING_FILE_PATH,
    MAPPING_STATUS_UNMAPPED,
    map_findings_to_nodes,
)

logger = logging.getLogger(__name__)

# Canonical Impact Statuses
IMPACT_STATUS_SUCCESS = "success"
IMPACT_STATUS_PARTIAL = "partial"
IMPACT_STATUS_UNAVAILABLE = "unavailable"

EVIDENCE_TYPE_STATIC_IMPORT = "static_import_relationship"


def _extract_graph_info(graph_input: Any) -> tuple[dict[str, Any], str, bool, bool]:
    """Normalize and inspect input graph to extract graph data and completeness status.

    Distinguishes between:
    - Unavailable/failed graphs (None, unparseable, explicit status 'unavailable' or 'failed')
    - Valid empty graphs (successfully analyzed repositories with zero nodes/edges)
    - Truncated or partial graphs
    - Complete graphs

    Args:
        graph_input: Input graph dictionary, Pydantic model, or envelope.

    Returns:
        tuple (graph_dict, graph_status, graph_is_available, graph_is_truncated)
    """
    if graph_input is None:
        return {}, IMPACT_STATUS_UNAVAILABLE, False, False

    if isinstance(graph_input, BaseModel):
        data = graph_input.model_dump()
    elif isinstance(graph_input, dict):
        data = copy.deepcopy(graph_input)
    else:
        return {}, IMPACT_STATUS_UNAVAILABLE, False, False

    # Check for envelope wrapper, e.g. {"status": ..., "graph": {...}}
    top_status = data.get("status")
    top_error = data.get("error")

    if "graph" in data and isinstance(data["graph"], dict):
        graph_dict = data["graph"]
        top_status = top_status or graph_dict.get("status")
        top_error = top_error or graph_dict.get("error")
    else:
        graph_dict = data

    # 1. Explicit failure or unavailable state
    if top_status in (IMPACT_STATUS_UNAVAILABLE, "failed") or (
        top_error is not None and not (graph_dict.get("nodes") or graph_dict.get("edges"))
    ):
        return graph_dict, IMPACT_STATUS_UNAVAILABLE, False, False

    # 2. Missing graph dictionary or missing graph keys
    if not isinstance(graph_dict, dict) or ("nodes" not in graph_dict and "edges" not in graph_dict):
        return {}, IMPACT_STATUS_UNAVAILABLE, False, False

    # 3. Valid graph structure (can be empty graph or populated graph)
    graph_is_available = True
    graph_is_truncated = bool(graph_dict.get("truncated", False))

    if graph_is_truncated or top_status == IMPACT_STATUS_PARTIAL or graph_dict.get("status") == IMPACT_STATUS_PARTIAL:
        graph_status = IMPACT_STATUS_PARTIAL
    else:
        graph_status = IMPACT_STATUS_SUCCESS

    return graph_dict, graph_status, graph_is_available, graph_is_truncated


def build_graph_indexes(
    edges: list[dict[str, Any]] | None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    """Build O(1) indexed lookup tables for incoming and outgoing edges.

    In the canonical graph:
        A -> B means A imports B.
        A is the source (importer / dependant).
        B is the target (imported / dependency).

    Args:
        edges: List of directed edge dictionaries.

    Returns:
        tuple (incoming_edges, outgoing_edges) where:
        - incoming_edges: target -> list of edges where edge.target == target
        - outgoing_edges: source -> list of edges where edge.source == source
    """
    incoming: dict[str, list[dict[str, Any]]] = {}
    outgoing: dict[str, list[dict[str, Any]]] = {}

    if not edges or not isinstance(edges, list):
        return incoming, outgoing

    for edge in edges:
        if isinstance(edge, BaseModel):
            edge_dict = edge.model_dump()
        elif isinstance(edge, dict):
            edge_dict = edge
        else:
            continue

        src = edge_dict.get("source")
        tgt = edge_dict.get("target")

        if not src or not tgt or not isinstance(src, str) or not isinstance(tgt, str):
            continue

        # Outgoing index: source -> [edges]
        if src not in outgoing:
            outgoing[src] = []
        outgoing[src].append(edge_dict)

        # Incoming index: target -> [edges]
        if tgt not in incoming:
            incoming[tgt] = []
        incoming[tgt].append(edge_dict)

    return incoming, outgoing


def extract_direct_dependants(
    node_id: str,
    incoming_edges: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], bool]:
    """Extract direct dependants for a given node from incoming import edges.

    For node B, incoming edges A -> B mean A imports B, so A is a direct dependant.
    Self-loops (B -> B) are detected and excluded from external dependants.

    Args:
        node_id: Canonical repository-relative path of the node.
        incoming_edges: Indexed incoming edge lookup dictionary.

    Returns:
        tuple (dependants_list, self_dependency_detected)
    """
    dependants: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    self_dependency_detected = False

    edges = incoming_edges.get(node_id, [])
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")

        if not src or not tgt:
            continue

        # Detect self-loop: B -> B
        if src == node_id:
            self_dependency_detected = True
            continue

        if src not in seen_sources:
            seen_sources.add(src)
            edge_id = edge.get("id") or f"{src}->{tgt}"
            relationship = edge.get("relationship") or "imports"

            evidence = {
                "edge_id": edge_id,
                "source": src,
                "target": tgt,
                "relationship": relationship,
                "evidence_type": EVIDENCE_TYPE_STATIC_IMPORT,
            }
            dependants.append({
                "file_path": src,
                "relationship": relationship,
                "evidence": evidence,
            })

    # Sort deterministically by file_path
    dependants.sort(key=lambda d: d["file_path"])
    return dependants, self_dependency_detected


def extract_direct_dependencies(
    node_id: str,
    outgoing_edges: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], bool]:
    """Extract direct dependencies for a given node from outgoing import edges.

    For node A, outgoing edges A -> B mean A imports B, so B is a direct dependency.
    Self-loops (A -> A) are detected and excluded from external dependencies.

    Args:
        node_id: Canonical repository-relative path of the node.
        outgoing_edges: Indexed outgoing edge lookup dictionary.

    Returns:
        tuple (dependencies_list, self_dependency_detected)
    """
    dependencies: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    self_dependency_detected = False

    edges = outgoing_edges.get(node_id, [])
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")

        if not src or not tgt:
            continue

        # Detect self-loop: A -> A
        if tgt == node_id:
            self_dependency_detected = True
            continue

        if tgt not in seen_targets:
            seen_targets.add(tgt)
            edge_id = edge.get("id") or f"{src}->{tgt}"
            relationship = edge.get("relationship") or "imports"

            evidence = {
                "edge_id": edge_id,
                "source": src,
                "target": tgt,
                "relationship": relationship,
                "evidence_type": EVIDENCE_TYPE_STATIC_IMPORT,
            }
            dependencies.append({
                "file_path": tgt,
                "relationship": relationship,
                "evidence": evidence,
            })

    # Sort deterministically by file_path
    dependencies.sort(key=lambda d: d["file_path"])
    return dependencies, self_dependency_detected


def enrich_finding(
    adapted_finding: dict[str, Any],
    mapping_status: str,
    matched_node_id: str | None,
    incoming_edges: dict[str, list[dict[str, Any]]],
    outgoing_edges: dict[str, list[dict[str, Any]]],
    cycles_by_node: dict[str, list[list[str]]],
    graph_is_available: bool = True,
    graph_is_truncated: bool = False,
    graph_status: str = IMPACT_STATUS_SUCCESS,
    unmapped_reason: str | None = None,
) -> dict[str, Any]:
    """Enrich a single finding dictionary with direct impact analysis and evidence.

    Preserves all original fields from the static analysis finding without mutation.
    """
    result = copy.deepcopy(adapted_finding)

    # Set mapping status
    result["mapping_status"] = mapping_status

    # Initial impact defaults
    direct_dependants: list[dict[str, Any]] = []
    direct_dependencies: list[dict[str, Any]] = []
    self_dependency_detected = False
    cycle_member = False
    matching_cycles: list[list[str]] = []

    if not graph_is_available:
        result["impact_status"] = IMPACT_STATUS_UNAVAILABLE
        result["impact_reason"] = "Dependency graph data is unavailable"
    elif mapping_status != MAPPING_STATUS_MAPPED or not matched_node_id:
        result["impact_status"] = IMPACT_STATUS_PARTIAL
        if unmapped_reason:
            result["impact_reason"] = unmapped_reason
        elif mapping_status == MAPPING_STATUS_UNMAPPED:
            result["impact_reason"] = (
                f"File '{adapted_finding.get('file_path')}' is not present in the dependency graph"
            )
        elif mapping_status == MAPPING_STATUS_MISSING_FILE_PATH:
            result["impact_reason"] = "Finding does not specify a valid file_path"
        elif mapping_status == MAPPING_STATUS_INVALID_PATH:
            result["impact_reason"] = "Finding specifies an invalid or unsafe file path"
    else:
        # Successful mapping
        # 1. Direct dependants (incoming edges: X -> matched_node_id)
        dep_items, self_dep_inc = extract_direct_dependants(matched_node_id, incoming_edges)
        direct_dependants = dep_items

        # 2. Direct dependencies (outgoing edges: matched_node_id -> Y)
        depn_items, self_dep_out = extract_direct_dependencies(matched_node_id, outgoing_edges)
        direct_dependencies = depn_items

        self_dependency_detected = self_dep_inc or self_dep_out

        # 3. Cycle information
        node_cycles = cycles_by_node.get(matched_node_id, [])
        matching_cycles = node_cycles
        cycle_member = len(node_cycles) > 0

        # Status: partial if graph was truncated or upstream graph was partial; else success
        if graph_is_truncated:
            result["impact_status"] = IMPACT_STATUS_PARTIAL
            result["impact_note"] = "Graph was truncated for visualization; degrees reflect full graph"
        elif graph_status == IMPACT_STATUS_PARTIAL:
            result["impact_status"] = IMPACT_STATUS_PARTIAL
            result["impact_note"] = "Upstream dependency graph extraction was partial"
        else:
            result["impact_status"] = IMPACT_STATUS_SUCCESS

    result["direct_dependants"] = direct_dependants
    result["direct_dependencies"] = direct_dependencies
    result["self_dependency_detected"] = self_dependency_detected
    result["cycle_member"] = cycle_member
    result["cycles"] = matching_cycles
    result["summary"] = {
        "direct_dependant_count": len(direct_dependants),
        "direct_dependency_count": len(direct_dependencies),
    }

    return result


def analyze_impact(
    graph: dict[str, Any] | BaseModel | None = None,
    findings: list[dict[str, Any]] | None = None,
    analysis_id: str = "",
    *,
    repo_path: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Perform finding-level direct impact analysis.

    Supports two invocation patterns:
    1. analyze_impact(graph=graph, findings=findings, analysis_id=analysis_id):
       Consumes an already-built graph dict or Pydantic GraphData / DependencyGraphResponse.
       NEVER executes Madge.
    2. analyze_impact(repo_path=repo_path, findings=findings, analysis_id=analysis_id):
       Fallback for direct repository-level execution; runs Madge and builds graph.

    Args:
        graph: Already-built graph dict/model.
        findings: List of static analysis findings (e.g. from OM_2).
        analysis_id: Unique analysis identifier.
        repo_path: Optional repository path (used only if graph is omitted).

    Returns:
        Dictionary containing analysis_id, status, graph, and enriched_findings.
    """
    from backend.app.services.dependency_impact.graph_builder import (
        build_dependency_graph,
    )
    from backend.app.services.dependency_impact.madge_runner import (
        get_circular_dependencies,
        get_dependency_map,
    )

    if findings is None:
        findings = []

    # Handle backwards-compatible positional repo_path or keyword graph_or_repo
    if isinstance(graph, str):
        if repo_path is None:
            repo_path = graph
        graph = None
    elif graph is None and "graph_or_repo" in kwargs:
        arg = kwargs.pop("graph_or_repo")
        if isinstance(arg, str):
            repo_path = arg
        else:
            graph = arg

    graph_dict: dict[str, Any] = {}
    graph_is_available = True
    graph_is_truncated = False
    graph_status = IMPACT_STATUS_SUCCESS

    # If an already-constructed graph is supplied, consume it directly (NEVER run Madge)
    if graph is not None:
        graph_dict, graph_status, graph_is_available, graph_is_truncated = _extract_graph_info(graph)
    elif repo_path is not None:
        # Fallback repository-level workflow
        dep_result = get_dependency_map(repo_path)
        circ_result = get_circular_dependencies(repo_path)

        if dep_result.get("status") not in ("success", "partial"):
            graph_is_available = False
            graph_status = IMPACT_STATUS_UNAVAILABLE
            raw_dep_map = {}
        else:
            raw_dep_map = dep_result.get("dependency_map") or {}
            if dep_result.get("status") == "partial" or circ_result.get("status") != "success":
                graph_status = IMPACT_STATUS_PARTIAL

        raw_cycles = circ_result.get("cycles") or []
        built_graph = build_dependency_graph(raw_dep_map, raw_cycles, findings)
        graph_dict = built_graph
        graph_is_truncated = bool(built_graph.get("truncated", False))
        if graph_is_truncated:
            graph_status = IMPACT_STATUS_PARTIAL
    else:
        # Neither graph nor repo_path provided
        graph_is_available = False
        graph_status = IMPACT_STATUS_UNAVAILABLE

    # Extract nodes, edges, cycles
    nodes = graph_dict.get("nodes") or []
    edges = graph_dict.get("edges") or []
    cycles = graph_dict.get("cycles") or []

    # Build node_id set
    node_ids: set[str] = set()
    for n in nodes:
        if isinstance(n, dict):
            nid = n.get("id") or n.get("file_path")
            if nid and isinstance(nid, str):
                node_ids.add(nid)
        elif isinstance(n, BaseModel):
            nid = getattr(n, "id", None) or getattr(n, "file_path", None)
            if nid and isinstance(nid, str):
                node_ids.add(nid)

    # Build cycle map: node_id -> list of cycles containing that node
    cycles_by_node: dict[str, list[list[str]]] = {}
    if cycles and isinstance(cycles, list):
        for cycle in cycles:
            if isinstance(cycle, list):
                for node_path in cycle:
                    if isinstance(node_path, str):
                        if node_path not in cycles_by_node:
                            cycles_by_node[node_path] = []
                        cycles_by_node[node_path].append(cycle)

    # Build graph edge indexes
    incoming_edges, outgoing_edges = build_graph_indexes(edges)

    # Map findings to nodes
    mapped_findings = map_findings_to_nodes(findings, node_ids)

    # Enrich each finding
    enriched_findings: list[dict[str, Any]] = []
    for adapted_f, map_status, matched_id, reason in mapped_findings:
        enriched = enrich_finding(
            adapted_finding=adapted_f,
            mapping_status=map_status,
            matched_node_id=matched_id,
            incoming_edges=incoming_edges,
            outgoing_edges=outgoing_edges,
            cycles_by_node=cycles_by_node,
            graph_is_available=graph_is_available,
            graph_is_truncated=graph_is_truncated,
            graph_status=graph_status,
            unmapped_reason=reason,
        )
        enriched_findings.append(enriched)

    # Overall analysis status
    overall_status = graph_status if graph_is_available else IMPACT_STATUS_UNAVAILABLE

    return {
        "analysis_id": analysis_id,
        "status": overall_status,
        "graph": graph_dict,
        "enriched_findings": enriched_findings,
    }

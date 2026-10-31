"""Dependency graph construction engine for CodeImpact.

Converts normalized Madge dependency maps and cycle lists into a directed graph
with degree metrics, cycle member tagging, pre-truncation statistics, and
deterministic bounded visualization truncation. Supports self-loops and
enforces strict full-graph integrity validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.app.services.dependency_impact.cycle_detector import (
    get_cycle_members,
    normalize_cycles,
)
from backend.app.services.dependency_impact.madge_runner import normalize_repo_relative_path

logger = logging.getLogger(__name__)

# Default visualization payload limits
DEFAULT_MAX_NODES = 150
DEFAULT_MAX_EDGES = 200


def extract_finding_counts_by_file(findings: list[dict[str, Any]] | None) -> dict[str, int]:
    """Aggregate static analysis finding counts grouped by normalized file path.

    Args:
        findings: List of finding dictionaries (from OM_2 or mock data).

    Returns:
        Mapping of normalized file_path -> count of findings.
    """
    counts: dict[str, int] = {}
    if not findings or not isinstance(findings, list):
        return counts

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        raw_path = finding.get("file_path")
        if raw_path and isinstance(raw_path, str):
            norm_p = normalize_repo_relative_path(raw_path)
            if norm_p:
                counts[norm_p] = counts.get(norm_p, 0) + 1

    return counts


def validate_graph_integrity(graph_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate graph internal consistency, degree integrity, edge IDs, and cycle memberships.

    Checks:
    1. Node IDs are unique, non-empty, and equal to file_path.
    2. Node labels match Path(file_path).name.
    3. Node degrees and finding counts are non-negative.
    4. Edge IDs are unique and strictly formatted as 'source->target'.
    5. Edge relationship is canonical 'imports'.
    6. No dangling edges: source and target must exist in returned nodes.
    7. Full-graph degree sums equal original_edge_count when untruncated.
    8. Individual node degrees match edge incident counts when untruncated.
    9. Cycle member flag consistency with cycle metadata.
    10. Cycle paths reference valid nodes when untruncated.
    11. Statistics match actual collection sizes and truncation state.

    Args:
        graph_data: Dictionary containing 'nodes', 'edges', 'cycles', 'stats', 'truncated'.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors: list[str] = []
    if not isinstance(graph_data, dict):
        return False, ["Graph data must be a dictionary."]

    nodes = graph_data.get("nodes")
    edges = graph_data.get("edges")
    cycles = graph_data.get("cycles")
    stats = graph_data.get("stats")
    is_truncated = graph_data.get("truncated", False)

    if not isinstance(nodes, list):
        errors.append("'nodes' must be a list.")
        nodes = []
    if not isinstance(edges, list):
        errors.append("'edges' must be a list.")
        edges = []
    if not isinstance(cycles, list):
        errors.append("'cycles' must be a list.")
        cycles = []
    if not isinstance(stats, dict):
        errors.append("'stats' must be a dictionary.")
        stats = {}

    # 1. Node Validation
    node_ids: set[str] = set()
    node_map: dict[str, dict[str, Any]] = {}

    for node in nodes:
        if not isinstance(node, dict):
            errors.append(f"Invalid node entry (not a dictionary): {node}")
            continue

        nid = node.get("id")
        npath = node.get("file_path")
        nlabel = node.get("label")
        n_in = node.get("in_degree", 0)
        n_out = node.get("out_degree", 0)
        n_findings = node.get("finding_count", 0)
        n_cycle = node.get("cycle_member")

        if not nid or not isinstance(nid, str):
            errors.append(f"Encountered node without valid string 'id': {node}")
            continue

        if nid in node_ids:
            errors.append(f"Duplicate node ID detected: '{nid}'.")
        node_ids.add(nid)
        node_map[nid] = node

        if nid != npath:
            errors.append(f"Node id '{nid}' does not equal file_path '{npath}'.")

        expected_label = Path(nid).name
        if nlabel != expected_label:
            errors.append(f"Node label '{nlabel}' does not match expected filename '{expected_label}'.")

        if not isinstance(n_in, int) or n_in < 0:
            errors.append(f"Invalid in_degree on node '{nid}': {n_in}")

        if not isinstance(n_out, int) or n_out < 0:
            errors.append(f"Invalid out_degree on node '{nid}': {n_out}")

        if not isinstance(n_findings, int) or n_findings < 0:
            errors.append(f"Invalid finding_count on node '{nid}': {n_findings}")

        if not isinstance(n_cycle, bool):
            errors.append(f"Invalid cycle_member boolean on node '{nid}': {n_cycle}")

    # 2. Edge Validation
    edge_ids: set[str] = set()
    edge_in_counts: dict[str, int] = {nid: 0 for nid in node_ids}
    edge_out_counts: dict[str, int] = {nid: 0 for nid in node_ids}

    for edge in edges:
        if not isinstance(edge, dict):
            errors.append(f"Invalid edge entry (not a dictionary): {edge}")
            continue

        eid = edge.get("id")
        src = edge.get("source")
        tgt = edge.get("target")
        rel = edge.get("relationship")

        if not eid or not src or not tgt:
            errors.append(f"Malformed edge structure: {edge}")
            continue

        if eid in edge_ids:
            errors.append(f"Duplicate edge ID detected: '{eid}'.")
        edge_ids.add(eid)

        expected_eid = f"{src}->{tgt}"
        if eid != expected_eid:
            errors.append(f"Edge ID '{eid}' does not match expected canonical format '{expected_eid}'.")

        if rel != "imports":
            errors.append(f"Edge '{eid}' has non-canonical relationship '{rel}'; expected 'imports'.")

        # Dangling edge detection
        if src not in node_ids:
            errors.append(f"Dangling edge '{eid}': source '{src}' is absent from returned nodes.")
        else:
            edge_out_counts[src] += 1

        if tgt not in node_ids:
            errors.append(f"Dangling edge '{eid}': target '{tgt}' is absent from returned nodes.")
        else:
            edge_in_counts[tgt] += 1

    # 3. Cycle Validation and cycle_member Consistency
    cycle_member_files = get_cycle_members(cycles)

    for cycle in cycles:
        if not isinstance(cycle, (list, tuple)) or len(cycle) < 2:
            errors.append(f"Cycle must be a list of at least 2 files: {cycle}")
        elif len(set(cycle)) != len(cycle):
            errors.append(f"Cycle contains duplicate members: {cycle}")

        # If untruncated, all cycle members must exist in node_ids
        if not is_truncated:
            for member in cycle:
                if member not in node_ids:
                    errors.append(f"Cycle references file '{member}' absent from graph nodes.")

    # Consistency between node.cycle_member and cycle metadata
    for nid, node in node_map.items():
        is_member = node.get("cycle_member", False)
        in_metadata = nid in cycle_member_files

        if is_member and not in_metadata:
            errors.append(f"Node '{nid}' is marked cycle_member=True but does not appear in cycles metadata.")
        elif not is_member and in_metadata:
            errors.append(f"Node '{nid}' appears in cycles metadata but has cycle_member=False.")

    # 4. Statistics and Degree Sums
    orig_nodes = stats.get("original_node_count")
    orig_edges = stats.get("original_edge_count")
    ret_nodes = stats.get("returned_node_count")
    ret_edges = stats.get("returned_edge_count")
    cyc_count = stats.get("cycle_count")

    if ret_nodes != len(nodes):
        errors.append(f"Statistics mismatch: len(nodes)={len(nodes)} != returned_node_count={ret_nodes}")
    if ret_edges != len(edges):
        errors.append(f"Statistics mismatch: len(edges)={len(edges)} != returned_edge_count={ret_edges}")
    if cyc_count != len(cycles):
        errors.append(f"Statistics mismatch: len(cycles)={len(cycles)} != cycle_count={cyc_count}")

    # Full-graph degree identities when graph is NOT truncated
    if not is_truncated:
        if orig_nodes != len(nodes):
            errors.append(f"Untruncated graph must have original_node_count == len(nodes).")
        if orig_edges != len(edges):
            errors.append(f"Untruncated graph must have original_edge_count == len(edges).")

        total_in = sum(n.get("in_degree", 0) for n in nodes)
        total_out = sum(n.get("out_degree", 0) for n in nodes)

        if total_in != len(edges):
            errors.append(f"Degree sum mismatch: sum(in_degree)={total_in} != edge_count={len(edges)}")
        if total_out != len(edges):
            errors.append(f"Degree sum mismatch: sum(out_degree)={total_out} != edge_count={len(edges)}")

        # Individual degree accuracy
        for nid, node in node_map.items():
            if node.get("in_degree", 0) != edge_in_counts[nid]:
                errors.append(
                    f"Node '{nid}' in_degree={node.get('in_degree')} does not match actual incoming edge count={edge_in_counts[nid]}"
                )
            if node.get("out_degree", 0) != edge_out_counts[nid]:
                errors.append(
                    f"Node '{nid}' out_degree={node.get('out_degree')} does not match actual outgoing edge count={edge_out_counts[nid]}"
                )

    return len(errors) == 0, errors


def build_dependency_graph(
    dependency_map: dict[str, list[str]] | None,
    cycles: list[list[str]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_edges: int = DEFAULT_MAX_EDGES,
) -> dict[str, Any]:
    """Construct a directed dependency graph from normalized Madge maps and cycles.

    Calculates in-degree, out-degree, cycle memberships, full graph metrics,
    preserves self-loops (Option A), and applies deterministic truncation when bounds are exceeded.

    Args:
        dependency_map: Mapping of source file -> list of imported dependency files.
        cycles: Optional list of circular dependency chains from Madge.
        findings: Optional static analysis findings list.
        max_nodes: Maximum node count returned in visualization payload.
        max_edges: Maximum edge count returned in visualization payload.

    Returns:
        Structured dictionary conforming to the CodeImpact Graph contract.
    """
    if dependency_map is None:
        dependency_map = {}

    if not isinstance(dependency_map, dict):
        raise ValueError("dependency_map must be a dictionary or None.")

    # Step 1: Normalize cycles and extract cycle members
    normalized_cycles = normalize_cycles(cycles)
    cycle_members = get_cycle_members(normalized_cycles)

    # Step 2: Extract finding counts by file
    finding_counts = extract_finding_counts_by_file(findings)

    # Step 3: Discover complete node universe & deduplicate directed edges
    all_nodes_set: set[str] = set()
    unique_edges_set: set[tuple[str, str]] = set()

    for raw_src, raw_deps in dependency_map.items():
        norm_src = normalize_repo_relative_path(raw_src)
        if not norm_src:
            continue
        all_nodes_set.add(norm_src)

        if not isinstance(raw_deps, (list, tuple, set)):
            continue

        for raw_dep in raw_deps:
            norm_dep = normalize_repo_relative_path(raw_dep)
            if not norm_dep:
                continue
            all_nodes_set.add(norm_dep)

            # Option A: Preserve self-loops as valid directed dependency edges
            unique_edges_set.add((norm_src, norm_dep))

    # Also include any files participating in cycles into the node set
    for member in cycle_members:
        all_nodes_set.add(member)

    # Step 4: Calculate full-graph degrees across all unique edges
    # Source IMPORTS Target:
    # Source has out_degree += 1 (dependencies)
    # Target has in_degree += 1 (dependants)
    # For self-loops (src == tgt): both in_degree and out_degree increment by 1
    in_degrees: dict[str, int] = {n: 0 for n in all_nodes_set}
    out_degrees: dict[str, int] = {n: 0 for n in all_nodes_set}

    for src, tgt in unique_edges_set:
        out_degrees[src] = out_degrees.get(src, 0) + 1
        in_degrees[tgt] = in_degrees.get(tgt, 0) + 1

    # Step 5: Build full node dictionaries
    full_nodes: list[dict[str, Any]] = []
    for nid in sorted(all_nodes_set):
        full_nodes.append({
            "id": nid,
            "label": Path(nid).name,
            "file_path": nid,
            "finding_count": finding_counts.get(nid, 0),
            "cycle_member": nid in cycle_members,
            "in_degree": in_degrees.get(nid, 0),
            "out_degree": out_degrees.get(nid, 0),
        })

    # Step 6: Build full edge dictionaries
    full_edges: list[dict[str, Any]] = []
    for src, tgt in sorted(unique_edges_set):
        full_edges.append({
            "id": f"{src}->{tgt}",
            "source": src,
            "target": tgt,
            "relationship": "imports",
        })

    # Step 7: Record pre-truncation statistics (truthful architectural metrics)
    original_node_count = len(full_nodes)
    original_edge_count = len(full_edges)
    cycle_count = len(normalized_cycles)

    # Step 8: Apply deterministic truncation if limits exceeded
    needs_node_truncation = original_node_count > max_nodes
    needs_edge_truncation = original_edge_count > max_edges
    is_truncated = needs_node_truncation or needs_edge_truncation

    if not is_truncated:
        returned_nodes = full_nodes
        returned_edges = full_edges
    else:
        # Priority order for node retention:
        # 1. finding_count (descending)
        # 2. cycle_member (descending)
        # 3. in_degree (descending - architectural hubs)
        # 4. file_path (ascending - stable tie-breaker)
        def node_rank_key(n: dict[str, Any]):
            return (
                -n["finding_count"],
                0 if n["cycle_member"] else 1,
                -n["in_degree"],
                n["file_path"],
            )

        ranked_nodes = sorted(full_nodes, key=node_rank_key)
        selected_nodes = ranked_nodes[:max_nodes]
        selected_node_ids = {n["id"] for n in selected_nodes}

        # Filter edges: BOTH source and target must be in selected_nodes
        candidate_edges = [
            e for e in full_edges
            if e["source"] in selected_node_ids and e["target"] in selected_node_ids
        ]

        if len(candidate_edges) <= max_edges:
            selected_edges = candidate_edges
        else:
            # Rank edges prioritizing endpoints with findings or cycle membership
            def edge_rank_key(e: dict[str, Any]):
                src_node = next(n for n in selected_nodes if n["id"] == e["source"])
                tgt_node = next(n for n in selected_nodes if n["id"] == e["target"])
                endpoint_findings = src_node["finding_count"] + tgt_node["finding_count"]
                endpoint_cycles = (1 if src_node["cycle_member"] else 0) + (1 if tgt_node["cycle_member"] else 0)
                return (-endpoint_findings, -endpoint_cycles, e["id"])

            ranked_edges = sorted(candidate_edges, key=edge_rank_key)
            selected_edges = ranked_edges[:max_edges]

        # Re-sort returned collections deterministically by ID for stable serialization
        returned_nodes = sorted(selected_nodes, key=lambda n: n["id"])
        returned_edges = sorted(selected_edges, key=lambda e: e["id"])

    # Step 9: Assemble final statistics payload
    stats = {
        "node_count": original_node_count,
        "edge_count": original_edge_count,
        "cycle_count": cycle_count,
        "original_node_count": original_node_count,
        "original_edge_count": original_edge_count,
        "returned_node_count": len(returned_nodes),
        "returned_edge_count": len(returned_edges),
    }

    graph_payload = {
        "nodes": returned_nodes,
        "edges": returned_edges,
        "cycles": normalized_cycles,
        "stats": stats,
        "truncated": is_truncated,
    }

    # Step 10: Validate graph integrity before emitting
    is_valid, validation_errors = validate_graph_integrity(graph_payload)
    if not is_valid:
        logger.error("Graph validation failed: %s", validation_errors)
        raise ValueError(f"Generated dependency graph failed integrity checks: {validation_errors}")

    return graph_payload


def create_graph_response(
    analysis_id: str,
    graph_data: dict[str, Any],
    enriched_findings: list[dict[str, Any]] | None = None,
    status: str = "success",
) -> dict[str, Any]:
    """Wrap graph data and findings into the top-level CodeImpact API response envelope.

    Args:
        analysis_id: Unique analysis identifier.
        graph_data: Output dictionary from build_dependency_graph.
        enriched_findings: List of finding dictionaries enriched with impact context.
        status: Canonical status ('success', 'partial', 'unavailable').

    Returns:
        Dictionary conforming to DependencyGraphResponse schema.
    """
    return {
        "analysis_id": analysis_id,
        "status": status,
        "graph": graph_data,
        "enriched_findings": enriched_findings if enriched_findings is not None else [],
    }

"""Top-level service coordinator for Phase 5 Potential Test Impact Mapping.

Coordinates test file discovery, testing framework detection, entry-point analysis,
and finding-level test impact mapping without executing untrusted repository code.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from backend.app.schemas.test_impact import TestImpactAnalysisResult
from backend.app.services.dependency_impact.entry_point_detector import detect_entry_points
from backend.app.services.dependency_impact.impact_analyzer import (
    IMPACT_STATUS_PARTIAL,
    IMPACT_STATUS_SUCCESS,
    IMPACT_STATUS_UNAVAILABLE,
    _extract_graph_info,
    build_graph_indexes,
)
from backend.app.services.dependency_impact.test_discovery import discover_test_files
from backend.app.services.dependency_impact.test_framework_detector import detect_test_frameworks
from backend.app.services.dependency_impact.test_mapper import map_tests_for_finding

logger = logging.getLogger(__name__)


def analyze_test_impact(
    graph: dict[str, Any] | BaseModel | None = None,
    enriched_findings: list[dict[str, Any]] | None = None,
    repo_path: str | Path | None = None,
    analysis_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Perform potential test impact mapping for findings.

    Extends Phase 4 enriched findings with candidate test mapping, detected frameworks,
    and entry points. Reuses the pre-constructed graph; NEVER calls Madge or runs tests.

    Args:
        graph: Pre-constructed dependency graph dictionary or Pydantic model.
        enriched_findings: List of finding dictionaries from Phase 4.
        repo_path: Optional local path to repository workspace for static metadata inspection.
        analysis_id: Unique analysis identifier.

    Returns:
        Structured dictionary conforming to TestImpactAnalysisResult schema.
    """
    if enriched_findings is None:
        enriched_findings = []

    # Handle backwards-compatible positional repo_path or keyword graph_or_repo
    if isinstance(graph, (str, Path)):
        if repo_path is None:
            repo_path = graph
        graph = None
    elif graph is None and "graph_or_repo" in kwargs:
        arg = kwargs.pop("graph_or_repo")
        if isinstance(arg, (str, Path)):
            repo_path = arg
        else:
            graph = arg

    graph_dict, graph_status, graph_is_available, graph_is_truncated = _extract_graph_info(graph)

    # 1. Extract nodes and edges
    nodes = graph_dict.get("nodes") or []
    edges = graph_dict.get("edges") or []

    # Build incoming/outgoing edge indexes once for the analysis
    incoming_edges, _ = build_graph_indexes(edges)

    # 2. Discover all test files once across graph nodes and repository workspace
    all_discovered_tests = discover_test_files(repo_path=repo_path, graph_nodes=nodes)

    # 3. Statically detect testing frameworks once
    detected_frameworks = detect_test_frameworks(repo_path=repo_path)

    # 4. Statically detect entry points once
    entry_points = detect_entry_points(repo_path=repo_path, graph_nodes=nodes)

    # 5. Map test candidates for each finding
    updated_findings: list[dict[str, Any]] = []
    for raw_finding in enriched_findings:
        if not isinstance(raw_finding, dict):
            continue

        finding_copy = copy.deepcopy(raw_finding)
        source_file = finding_copy.get("file_path")

        test_impact = map_tests_for_finding(
            source_file=source_file,
            incoming_edges=incoming_edges,
            all_discovered_tests=all_discovered_tests,
            graph_is_available=graph_is_available,
            graph_is_truncated=graph_is_truncated,
        )

        finding_copy["test_impact"] = test_impact
        updated_findings.append(finding_copy)

    # Determine overall status
    if not graph_is_available and not repo_path:
        overall_status = IMPACT_STATUS_UNAVAILABLE
    elif graph_is_truncated or graph_status == IMPACT_STATUS_PARTIAL:
        overall_status = IMPACT_STATUS_PARTIAL
    else:
        overall_status = IMPACT_STATUS_SUCCESS

    result = {
        "analysis_id": analysis_id,
        "status": overall_status,
        "detected_frameworks": detected_frameworks,
        "entry_points": entry_points,
        "enriched_findings": updated_findings,
    }

    return result


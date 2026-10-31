"""Integration validation and hardening tests for finding-level impact analysis.

Covers:
Task A — Graph completeness and truncation propagation
Task B — Empty graph vs unavailable graph handling
Task C — Prevention of duplicate Madge execution
Task D — Preservation of original finding data and Pydantic serialization
"""

import copy
import json
from unittest.mock import MagicMock, patch
import pytest

from backend.app.schemas.graph import DependencyGraphResponse
from backend.app.schemas.impact import EnrichedFinding
from backend.app.services.dependency_impact.impact_analyzer import (
    IMPACT_STATUS_PARTIAL,
    IMPACT_STATUS_SUCCESS,
    IMPACT_STATUS_UNAVAILABLE,
    analyze_impact,
)


@pytest.fixture
def complete_graph():
    """A valid, untruncated dependency graph with 2 nodes and 1 directed edge."""
    return {
        "nodes": [
            {"id": "src/app.ts", "file_path": "src/app.ts", "label": "app.ts", "in_degree": 0, "out_degree": 1},
            {"id": "src/utils.ts", "file_path": "src/utils.ts", "label": "utils.ts", "in_degree": 1, "out_degree": 0},
        ],
        "edges": [
            {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts", "relationship": "imports"}
        ],
        "cycles": [],
        "stats": {
            "node_count": 2,
            "edge_count": 1,
            "cycle_count": 0,
            "original_node_count": 2,
            "original_edge_count": 1,
            "returned_node_count": 2,
            "returned_edge_count": 1,
        },
        "truncated": False,
        "status": "success",
    }


@pytest.fixture
def truncated_graph(complete_graph):
    """A graph marked as truncated."""
    tg = copy.deepcopy(complete_graph)
    tg["truncated"] = True
    tg["stats"]["original_node_count"] = 500
    tg["stats"]["original_edge_count"] = 800
    return tg


@pytest.fixture
def valid_empty_graph():
    """A successfully analyzed codebase with zero import edges."""
    return {
        "nodes": [],
        "edges": [],
        "cycles": [],
        "stats": {
            "node_count": 0,
            "edge_count": 0,
            "cycle_count": 0,
            "original_node_count": 0,
            "original_edge_count": 0,
            "returned_node_count": 0,
            "returned_edge_count": 0,
        },
        "truncated": False,
        "status": "success",
    }


# ==============================================================================
# Task A — Graph Completeness & Truncation Propagation
# ==============================================================================

def test_complete_graph_produces_success_impact_status(complete_graph):
    """A complete, untruncated graph produces impact_status='success'."""
    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts", "category": "unused_export"}]
    res = analyze_impact(graph=complete_graph, findings=findings, analysis_id="test_a1")

    assert res["status"] == IMPACT_STATUS_SUCCESS
    f = res["enriched_findings"][0]
    assert f["mapping_status"] == "mapped"
    assert f["impact_status"] == IMPACT_STATUS_SUCCESS
    assert len(f["direct_dependants"]) == 1
    assert f["direct_dependants"][0]["file_path"] == "src/app.ts"


def test_truncated_graph_produces_partial_impact_status(truncated_graph):
    """A truncated graph must communicate impact_status='partial' even for mapped findings."""
    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts", "category": "unused_export"}]
    res = analyze_impact(graph=truncated_graph, findings=findings, analysis_id="test_a2")

    assert res["status"] == IMPACT_STATUS_PARTIAL
    f = res["enriched_findings"][0]
    assert f["mapping_status"] == "mapped"
    assert f["impact_status"] == IMPACT_STATUS_PARTIAL
    assert "truncated" in f.get("impact_note", "").lower()
    # Dependants in the returned subgraph are still computed
    assert len(f["direct_dependants"]) == 1


def test_partial_upstream_graph_propagates_partial_status(complete_graph):
    """A graph flagged as partial upstream produces impact_status='partial'."""
    graph_partial = copy.deepcopy(complete_graph)
    graph_partial["status"] = "partial"

    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts", "category": "unused_export"}]
    res = analyze_impact(graph=graph_partial, findings=findings, analysis_id="test_a3")

    assert res["status"] == IMPACT_STATUS_PARTIAL
    f = res["enriched_findings"][0]
    assert f["impact_status"] == IMPACT_STATUS_PARTIAL
    assert "partial" in f.get("impact_note", "").lower()


def test_missing_graph_metadata_or_none_propagates_unavailable():
    """Missing or None graph must communicate impact_status='unavailable'."""
    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts"}]
    res = analyze_impact(graph=None, findings=findings, analysis_id="test_a4")

    assert res["status"] == IMPACT_STATUS_UNAVAILABLE
    f = res["enriched_findings"][0]
    assert f["impact_status"] == IMPACT_STATUS_UNAVAILABLE
    assert "unavailable" in f.get("impact_reason", "").lower()


# ==============================================================================
# Task B — Empty Graph vs Unavailable Graph
# ==============================================================================

def test_valid_empty_graph_succeeds(valid_empty_graph):
    """A valid empty graph represents successful analysis, not failure."""
    findings = [{"finding_id": "f_1", "file_path": "src/unreferenced.ts", "category": "unused_file"}]
    res = analyze_impact(graph=valid_empty_graph, findings=findings, analysis_id="test_b1")

    # Overall graph analysis succeeded
    assert res["status"] == IMPACT_STATUS_SUCCESS
    f = res["enriched_findings"][0]
    # Finding is unmapped because the file is not in the graph
    assert f["mapping_status"] == "unmapped"
    assert f["impact_status"] == IMPACT_STATUS_PARTIAL
    assert "not present in the dependency graph" in f["impact_reason"]


def test_valid_empty_graph_with_no_findings(valid_empty_graph):
    """Valid empty graph with no findings completes cleanly."""
    res = analyze_impact(graph=valid_empty_graph, findings=[], analysis_id="test_b2")
    assert res["status"] == IMPACT_STATUS_SUCCESS
    assert res["enriched_findings"] == []


def test_unavailable_graph_with_madge_error_status():
    """Graph with explicit 'unavailable' status marks impact as unavailable."""
    error_graph = {
        "status": "unavailable",
        "error": {"code": "MADGE_NOT_FOUND", "message": "Executable not found"},
    }
    findings = [{"finding_id": "f_1", "file_path": "src/app.ts"}]
    res = analyze_impact(graph=error_graph, findings=findings, analysis_id="test_b3")

    assert res["status"] == IMPACT_STATUS_UNAVAILABLE
    f = res["enriched_findings"][0]
    assert f["impact_status"] == IMPACT_STATUS_UNAVAILABLE


def test_failed_graph_status_propagates_unavailable():
    """Graph with 'failed' status marks impact as unavailable."""
    failed_graph = {
        "status": "failed",
        "error": {"code": "MADGE_EXECUTION_FAILED", "message": "Syntax error"},
    }
    findings = [{"finding_id": "f_1", "file_path": "src/app.ts"}]
    res = analyze_impact(graph=failed_graph, findings=findings, analysis_id="test_b4")

    assert res["status"] == IMPACT_STATUS_UNAVAILABLE
    f = res["enriched_findings"][0]
    assert f["impact_status"] == IMPACT_STATUS_UNAVAILABLE


# ==============================================================================
# Task C — Prevent Duplicate Madge Execution
# ==============================================================================

@patch("backend.app.services.dependency_impact.madge_runner.run_madge")
@patch("backend.app.services.dependency_impact.madge_runner.get_dependency_map")
@patch("backend.app.services.dependency_impact.madge_runner.get_circular_dependencies")
def test_analyze_impact_with_existing_graph_never_calls_madge(
    mock_circ, mock_dep, mock_run, complete_graph
):
    """Passing a pre-constructed graph guarantees Madge runner is NEVER called."""
    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts"}]

    res = analyze_impact(graph=complete_graph, findings=findings, analysis_id="test_c1")

    assert res["status"] == IMPACT_STATUS_SUCCESS
    mock_run.assert_not_called()
    mock_dep.assert_not_called()
    mock_circ.assert_not_called()


@patch("backend.app.services.dependency_impact.madge_runner.run_madge")
@patch("backend.app.services.dependency_impact.madge_runner.get_dependency_map")
@patch("backend.app.services.dependency_impact.madge_runner.get_circular_dependencies")
def test_analyze_impact_with_both_graph_and_repo_path_prefers_graph(
    mock_circ, mock_dep, mock_run, complete_graph
):
    """When both graph and repo_path are supplied, graph takes precedence and Madge is not invoked."""
    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts"}]

    res = analyze_impact(
        graph=complete_graph,
        findings=findings,
        analysis_id="test_c2",
        repo_path="C:\\DeadCode",
    )

    assert res["status"] == IMPACT_STATUS_SUCCESS
    mock_run.assert_not_called()
    mock_dep.assert_not_called()
    mock_circ.assert_not_called()


def test_orchestrator_call_sequence_simulated(complete_graph):
    """Simulate orchestrator sequence: build graph once, pass to analyze_impact once."""
    from backend.app.services.dependency_impact import analyze_impact, build_dependency_graph

    # Step 1: Raw dependency map
    raw_deps = {"src/app.ts": ["src/utils.ts"], "src/utils.ts": []}
    # Step 2: Build graph
    graph = build_dependency_graph(raw_deps, cycles=[])
    # Step 3: Analyze impact
    findings = [{"finding_id": "f_1", "file_path": "src/utils.ts"}]

    with patch("backend.app.services.dependency_impact.madge_runner.get_dependency_map") as mock_dep:
        impact_result = analyze_impact(graph=graph, findings=findings, analysis_id="sim_orch")
        mock_dep.assert_not_called()

    assert impact_result["status"] == IMPACT_STATUS_SUCCESS
    assert len(impact_result["enriched_findings"]) == 1


# ==============================================================================
# Task D — Preserve Original Finding Data
# ==============================================================================

def test_original_finding_fields_strictly_preserved(complete_graph):
    """Enriched finding retains all original fields without in-place mutation."""
    original_finding = {
        "finding_id": "f_orig_001",
        "category": "unused_export",
        "title": "Potentially unused export formatDate",
        "file_path": "src/utils.ts",
        "start_line": 12,
        "end_line": 18,
        "symbol": "formatDate",
        "source_tool": "knip",
        "description": "No static reference was found by the configured scan.",
        "evidence_class": "inconclusive",
        "review_risk": "unknown",
        "evidence": [
            {
                "kind": "static_reference_scan",
                "status": "not_found",
                "source": "knip",
                "details": "No direct static reference was returned by this scan.",
            }
        ],
        "risk_factors": ["Possible framework entry point"],
        "metadata": {
            "export_type": "named",
            "additional_context": {"source": "knip_v5", "heuristic": False},
        },
        "custom_plugin_field": 42,
    }

    # Keep a deep copy for pre/post mutation comparison
    finding_copy_before = copy.deepcopy(original_finding)

    res = analyze_impact(graph=complete_graph, findings=[original_finding], analysis_id="test_d1")
    enriched = res["enriched_findings"][0]

    # 1. Verify original dictionary was NOT mutated in-place
    assert original_finding == finding_copy_before

    # 2. Verify all original top-level fields exist in enriched output
    for key in (
        "finding_id",
        "category",
        "title",
        "file_path",
        "start_line",
        "end_line",
        "symbol",
        "source_tool",
        "description",
        "evidence_class",
        "review_risk",
        "custom_plugin_field",
    ):
        assert enriched[key] == original_finding[key]

    # 3. Verify nested structures are intact
    assert enriched["evidence"] == original_finding["evidence"]
    assert enriched["risk_factors"] == original_finding["risk_factors"]
    assert enriched["metadata"] == original_finding["metadata"]

    # 4. Verify original evidence was NOT replaced by graph edge evidence
    assert enriched["evidence"][0]["source"] == "knip"
    assert enriched["direct_dependants"][0]["evidence"]["source"] == "src/app.ts"


def test_enriched_finding_json_serialization_roundtrip(complete_graph):
    """Enriched finding conforms to Pydantic EnrichedFinding schema and survives JSON roundtrip."""
    finding = {
        "finding_id": "f_json_1",
        "category": "unused_file",
        "file_path": "src/utils.ts",
        "title": "Unused File",
        "evidence": [{"kind": "scan", "status": "flagged", "source": "knip"}],
        "risk_factors": ["low_churn"],
        "metadata": {"tags": ["core", "legacy"]},
        "extra_arbitrary_key": "preserved_value",
    }

    res = analyze_impact(graph=complete_graph, findings=[finding], analysis_id="test_d2")
    enriched_dict = res["enriched_findings"][0]

    # Validate against Pydantic model
    validated = EnrichedFinding(**enriched_dict)
    assert validated.finding_id == "f_json_1"
    assert getattr(validated, "extra_arbitrary_key", None) == "preserved_value"

    # JSON roundtrip
    serialized = json.dumps(enriched_dict)
    deserialized = json.loads(serialized)

    assert deserialized["finding_id"] == "f_json_1"
    assert deserialized["metadata"]["tags"] == ["core", "legacy"]
    assert deserialized["extra_arbitrary_key"] == "preserved_value"
    assert deserialized["summary"]["direct_dependant_count"] == 1

    # Validate top-level response envelope
    resp_obj = DependencyGraphResponse(**res)
    assert resp_obj.analysis_id == "test_d2"
    assert resp_obj.status == "success"
    assert len(resp_obj.enriched_findings) == 1


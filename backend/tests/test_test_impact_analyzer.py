"""Integration and end-to-end tests for test impact analysis coordinator."""

from pathlib import Path
from unittest.mock import patch
import pytest

from backend.app.schemas.test_impact import TestImpactAnalysisResult
from backend.app.services.dependency_impact.test_impact_analyzer import (
    analyze_test_impact,
)


@pytest.fixture
def sample_graph():
    return {
        "nodes": [
            {"id": "src/app.ts", "file_path": "src/app.ts"},
            {"id": "src/utils.ts", "file_path": "src/utils.ts"},
            {"id": "tests/app.test.ts", "file_path": "tests/app.test.ts"},
        ],
        "edges": [
            {"id": "tests/app.test.ts->src/app.ts", "source": "tests/app.test.ts", "target": "src/app.ts", "relationship": "imports"},
            {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts", "relationship": "imports"},
        ],
        "cycles": [],
        "stats": {
            "node_count": 3,
            "edge_count": 2,
            "cycle_count": 0,
            "original_node_count": 3,
            "original_edge_count": 2,
            "returned_node_count": 3,
            "returned_edge_count": 2,
        },
        "truncated": False,
        "status": "success",
    }


def test_analyze_test_impact_end_to_end(sample_graph):
    findings = [
        {
            "finding_id": "FIND-APP",
            "file_path": "src/app.ts",
            "category": "unused_export",
            "direct_dependants": [{"file_path": "tests/app.test.ts"}],
            "summary": {"direct_dependant_count": 1, "direct_dependency_count": 1},
        },
        {
            "finding_id": "FIND-UTILS",
            "file_path": "src/utils.ts",
            "category": "unused_file",
            "direct_dependants": [{"file_path": "src/app.ts"}],
            "summary": {"direct_dependant_count": 1, "direct_dependency_count": 0},
        },
    ]

    result = analyze_test_impact(
        graph=sample_graph,
        enriched_findings=findings,
        analysis_id="test_analysis_100",
    )

    assert result["analysis_id"] == "test_analysis_100"
    assert result["status"] == "success"
    assert len(result["enriched_findings"]) == 2

    # FIND-APP has direct test: tests/app.test.ts
    f_app = result["enriched_findings"][0]
    assert "test_impact" in f_app
    ti_app = f_app["test_impact"]
    assert ti_app["status"] == "success"
    assert ti_app["summary"]["direct_test_count"] == 1
    assert ti_app["candidate_tests"][0]["file_path"] == "tests/app.test.ts"
    assert ti_app["candidate_tests"][0]["mapping_status"] == "direct"

    # FIND-UTILS has transitive test: tests/app.test.ts
    f_utils = result["enriched_findings"][1]
    assert "test_impact" in f_utils
    ti_utils = f_utils["test_impact"]
    assert ti_utils["summary"]["heuristic_test_count"] == 1
    assert ti_utils["candidate_tests"][0]["file_path"] == "tests/app.test.ts"
    assert ti_utils["candidate_tests"][0]["mapping_status"] == "heuristic"
    assert ti_utils["candidate_tests"][0]["evidence_type"] == "transitive_dependency"

    # Validate against Pydantic schema
    validated = TestImpactAnalysisResult(**result)
    assert validated.analysis_id == "test_analysis_100"


@patch("backend.app.services.dependency_impact.madge_runner.run_madge")
def test_analyze_test_impact_never_runs_madge(mock_run, sample_graph):
    findings = [{"finding_id": "f_1", "file_path": "src/app.ts"}]
    res = analyze_test_impact(graph=sample_graph, enriched_findings=findings)
    assert res["status"] == "success"
    mock_run.assert_not_called()


def test_analyze_test_impact_with_real_fixture():
    fixture_dir = Path("backend/tests/fixtures/dependency_fixture").resolve()
    assert fixture_dir.exists()

    # Pre-constructed graph matching fixture structure
    graph = {
        "nodes": [
            {"id": "src/app.ts", "file_path": "src/app.ts"},
            {"id": "src/utils.ts", "file_path": "src/utils.ts"},
            {"id": "tests/app.test.ts", "file_path": "tests/app.test.ts"},
        ],
        "edges": [
            {"id": "tests/app.test.ts->src/app.ts", "source": "tests/app.test.ts", "target": "src/app.ts"},
            {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts"},
        ],
        "status": "success",
    }

    findings = [{"finding_id": "f_fixture", "file_path": "src/app.ts"}]

    res = analyze_test_impact(
        graph=graph,
        enriched_findings=findings,
        repo_path=str(fixture_dir),
        analysis_id="fixture_test_analysis",
    )

    assert res["status"] == "success"
    # Entry points and frameworks detected from fixture
    assert isinstance(res["entry_points"], list)
    assert isinstance(res["detected_frameworks"], list)
    assert len(res["enriched_findings"]) == 1
    ti = res["enriched_findings"][0]["test_impact"]
    assert ti["summary"]["direct_test_count"] == 1
    assert ti["candidate_tests"][0]["file_path"] == "tests/app.test.ts"


def test_analyze_test_impact_preserves_all_phase4_fields(sample_graph):
    findings = [
        {
            "finding_id": "f_orig",
            "file_path": "src/app.ts",
            "category": "unused_export",
            "title": "Unused export",
            "start_line": 20,
            "end_line": 25,
            "symbol": "myExport",
            "source_tool": "knip",
            "description": "Original description.",
            "evidence": [{"source": "knip", "status": "flagged"}],
            "risk_factors": ["direct_dependants:1"],
            "metadata": {"export_type": "named"},
            "direct_dependants": [{"file_path": "tests/app.test.ts"}],
            "direct_dependencies": [{"file_path": "src/utils.ts"}],
            "self_dependency_detected": False,
            "cycle_member": False,
            "cycles": [],
            "summary": {"direct_dependant_count": 1, "direct_dependency_count": 1},
        }
    ]

    res = analyze_test_impact(graph=sample_graph, enriched_findings=findings)
    f = res["enriched_findings"][0]

    # All Phase 4 and OM_2 fields remain intact
    assert f["finding_id"] == "f_orig"
    assert f["symbol"] == "myExport"
    assert f["start_line"] == 20
    assert f["evidence"][0]["source"] == "knip"
    assert f["direct_dependants"][0]["file_path"] == "tests/app.test.ts"
    assert f["summary"]["direct_dependant_count"] == 1

    # New test_impact field attached
    assert "test_impact" in f
    assert f["test_impact"]["status"] == "success"


"""Integration and regression tests for Phase 6 review-risk analyzer service.

Verifies end-to-end execution, input finding non-mutation (deep-copy immutability),
deterministic reproduction, summary metrics accuracy, Pydantic schema compatibility,
and robust handling of partial/unavailable upstream states.
"""

from __future__ import annotations

import copy
import pytest

from backend.app.schemas.risk import RiskAnalysisResult
from backend.app.services.dependency_impact.finding_mapper import (
    MAPPING_STATUS_INVALID_PATH,
    MAPPING_STATUS_MAPPED,
)
from backend.app.services.dependency_impact.risk_analyzer import (
    analyze_review_risk,
    compute_completeness,
    compute_confidence,
)


@pytest.fixture
def sample_graph():
    return {
        "nodes": [
            {"id": "src/services/auth.ts", "file_path": "src/services/auth.ts"},
            {"id": "src/utils.ts", "file_path": "src/utils.ts"},
            {"id": "src/index.ts", "file_path": "src/index.ts"},
        ],
        "edges": [
            {"id": "src/services/auth.ts->src/utils.ts", "source": "src/services/auth.ts", "target": "src/utils.ts"},
            {"id": "src/index.ts->src/services/auth.ts", "source": "src/index.ts", "target": "src/services/auth.ts"},
        ],
        "cycles": [],
        "truncated": False,
        "status": "success",
    }


@pytest.fixture
def sample_findings():
    return [
        {
            "finding_id": "f_001",
            "category": "unused_export",
            "file_path": "src/utils.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "impact_status": "success",
            "evidence_class": "inconclusive",
            "direct_dependants": [{"file_path": "src/services/auth.ts"}],
            "direct_dependencies": [],
            "cycle_member": False,
            "cycles": [],
            "self_dependency_detected": False,
            "test_impact": {
                "status": "success",
                "mapping_complete": True,
                "candidate_tests": [
                    {
                        "file_path": "tests/test_utils.ts",
                        "mapping_status": "direct",
                        "evidence_type": "static_import",
                    }
                ],
                "summary": {"direct_test_count": 1, "heuristic_test_count": 0},
            },
            "custom_metadata_tag": "preserve_this_value",
        },
        {
            "finding_id": "f_002",
            "category": "unused_file",
            "file_path": "src/helpers/legacy.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "impact_status": "success",
            "evidence_class": "conclusive",
            "direct_dependants": [],
            "direct_dependencies": [],
            "cycle_member": False,
            "cycles": [],
            "self_dependency_detected": False,
            "test_impact": {
                "status": "success",
                "mapping_complete": True,
                "candidate_tests": [],
                "summary": {"direct_test_count": 0, "heuristic_test_count": 0},
            },
        },
        {
            "finding_id": "f_003",
            "category": "unused_file",
            "file_path": "invalid/path/../file.ts",
            "mapping_status": MAPPING_STATUS_INVALID_PATH,
            "impact_status": "unavailable",
            "evidence_class": "inconclusive",
            "direct_dependants": [],
            "direct_dependencies": [],
        },
    ]


class TestRiskAnalyzerIntegration:
    """Verify top-level service execution and data contracts."""

    def test_analyze_review_risk_basic(self, sample_graph, sample_findings):
        result = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=sample_findings,
            analysis_id="run_123",
        )

        assert result["analysis_id"] == "run_123"
        assert result["status"] == "success"
        assert len(result["enriched_findings"]) == 3

        summary = result["summary"]
        assert summary["total_findings"] == 3
        assert summary["assessed_findings"] == 2
        assert summary["unassessed_findings"] == 1
        assert summary["unknown_risk_count"] == 1
        assert summary["average_risk_score"] is not None

        # Verify Pydantic validation of output payload
        validated = RiskAnalysisResult.model_validate(result)
        assert validated.analysis_id == "run_123"

    def test_findings_are_not_mutated(self, sample_graph, sample_findings):
        # Deep-copy before passing to analyzer
        original_copy = copy.deepcopy(sample_findings)

        result = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=sample_findings,
            analysis_id="immutability_check",
        )

        # Original input list should be identical to pre-call snapshot
        assert sample_findings == original_copy
        # Output should preserve extra metadata
        assert result["enriched_findings"][0]["custom_metadata_tag"] == "preserve_this_value"

    def test_determinism_across_multiple_runs(self, sample_graph, sample_findings):
        res1 = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=sample_findings,
            analysis_id="det_1",
        )
        res2 = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=sample_findings,
            analysis_id="det_1",
        )

        assert res1 == res2

    def test_truncated_graph_marks_confidence_low(self, sample_graph, sample_findings):
        truncated_graph = copy.deepcopy(sample_graph)
        truncated_graph["truncated"] = True
        truncated_graph["status"] = "partial"

        result = analyze_review_risk(
            graph=truncated_graph,
            enriched_findings=sample_findings,
            analysis_id="trunc_run",
        )

        assert result["status"] == "partial"
        # Mapped finding on truncated graph should have low confidence
        f1 = result["enriched_findings"][0]
        assert f1["risk_confidence"] == "low"
        assert f1["risk_assessment"]["analysis_completeness"] == "partial"

    def test_unavailable_graph_handling(self, sample_findings):
        result = analyze_review_risk(
            graph=None,
            enriched_findings=sample_findings,
            analysis_id="unavail_run",
        )

        assert result["status"] == "unavailable"
        assert result["summary"]["assessed_findings"] == 0
        assert result["summary"]["unassessed_findings"] == 3
        assert result["summary"]["average_risk_score"] is None

        for f in result["enriched_findings"]:
            assert f["review_risk"] == "unknown"
            assert f["risk_score"] is None
            assert f["risk_confidence"] == "unknown"
            assert f["risk_assessment"]["analysis_completeness"] == "unavailable"

    def test_serialized_factor_sum_equality(self, sample_graph, sample_findings):
        result = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=sample_findings,
            analysis_id="sum_check",
        )
        for f in result["enriched_findings"]:
            score = f["risk_score"]
            if score is not None:
                factors = f["risk_assessment"]["factor_breakdown"]
                factor_sum = round(sum(item["score"] for item in factors), 1)
                assert score == factor_sum, f"Finding {f['finding_id']} risk_score {score} != factor sum {factor_sum}"

    def test_valid_empty_graph_handling(self):
        empty_graph = {
            "nodes": [],
            "edges": [],
            "cycles": [],
            "truncated": False,
            "status": "success",
        }
        findings = [
            {
                "finding_id": "f_empty",
                "file_path": "src/utils.ts",
                "mapping_status": MAPPING_STATUS_MAPPED,
                "category": "unused_file",
                "evidence_class": "conclusive",
                "direct_dependants": [],
                "direct_dependencies": [],
            }
        ]
        result = analyze_review_risk(
            graph=empty_graph,
            enriched_findings=findings,
            analysis_id="empty_graph_run",
        )
        assert result["status"] == "success"
        f = result["enriched_findings"][0]
        # In a valid complete empty graph, finding has evaluated risk score
        assert f["risk_score"] is not None
        assert f["risk_confidence"] == "high"
        assert f["risk_assessment"]["analysis_completeness"] == "complete"

    def test_missing_test_impact_and_entry_points(self, sample_graph):
        findings = [
            {
                "finding_id": "f_no_extras",
                "file_path": "src/utils.ts",
                "mapping_status": MAPPING_STATUS_MAPPED,
                "category": "unused_export",
                "evidence_class": "inconclusive",
                "direct_dependants": [{"file_path": "src/services/auth.ts"}],
                # No test_impact key at all
            }
        ]
        result = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=findings,
            entry_points=None,  # No entry points provided
            analysis_id="missing_extras_run",
        )
        assert result["status"] == "success"
        f = result["enriched_findings"][0]
        assert f["risk_score"] is not None
        # Absence of test impact does not crash or mark code safe
        test_factor = next(
            item for item in f["risk_assessment"]["factor_breakdown"]
            if item["factor"] == "test_impact_evidence"
        )
        assert test_factor["score"] == 0.0

    def test_preservation_of_all_nested_and_custom_fields(self, sample_graph):
        complex_finding = {
            "finding_id": "f_complex",
            "file_path": "src/utils.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "category": "unused_export",
            "title": "Unused export 'foo'",
            "symbol": "foo",
            "start_line": 10,
            "end_line": 15,
            "source_tool": "knip",
            "description": "Static analysis detected no references",
            "evidence_class": "inconclusive",
            "evidence": [{"type": "static_scan", "rule": "unused_export"}],
            "risk_factors": ["external_api"],
            "metadata": {"tags": ["critical", "legacy"], "author": "Samar"},
            "direct_dependants": [{"file_path": "src/services/auth.ts"}],
            "direct_dependencies": [{"file_path": "src/types.ts"}],
            "cycle_member": False,
            "cycles": [],
            "self_dependency_detected": False,
            "test_impact": {
                "status": "success",
                "candidate_tests": [{"file_path": "tests/utils.test.ts"}],
            },
            "arbitrary_unmodelled_field": {"deep": [1, 2, 3]},
        }
        result = analyze_review_risk(
            graph=sample_graph,
            enriched_findings=[complex_finding],
            analysis_id="preservation_run",
        )
        f = result["enriched_findings"][0]
        # Verify ALL original fields remain completely preserved
        assert f["title"] == "Unused export 'foo'"
        assert f["symbol"] == "foo"
        assert f["start_line"] == 10
        assert f["end_line"] == 15
        assert f["source_tool"] == "knip"
        assert f["description"] == "Static analysis detected no references"
        assert f["evidence"] == [{"type": "static_scan", "rule": "unused_export"}]
        assert f["risk_factors"] == ["external_api"]
        assert f["metadata"] == {"tags": ["critical", "legacy"], "author": "Samar"}
        assert f["direct_dependants"] == [{"file_path": "src/services/auth.ts"}]
        assert f["direct_dependencies"] == [{"file_path": "src/types.ts"}]
        assert f["arbitrary_unmodelled_field"] == {"deep": [1, 2, 3]}



"""Unit and regression tests for CodeImpact review-risk scoring engine.

Verifies deterministic scoring, factor bounds, classification thresholds, cycle differentiation,
test impact handling without coverage claims, and unmapped/unavailable fallback states.
"""

from __future__ import annotations

import pytest

from backend.app.schemas.risk import RiskFactorBreakdown
from backend.app.services.dependency_impact.finding_mapper import (
    MAPPING_STATUS_INVALID_PATH,
    MAPPING_STATUS_MAPPED,
    MAPPING_STATUS_UNMAPPED,
)
from backend.app.services.dependency_impact.risk_scorer import (
    LOWER_THRESHOLD,
    MAX_F1_DEPENDENCY,
    MAX_F2_CYCLE,
    MAX_F3_ENTRY_POINT,
    MAX_F4_TEST_IMPACT,
    MAX_F5_FINDING_EVIDENCE,
    MAX_F6_STRUCTURAL,
    MEDIUM_THRESHOLD,
    RISK_LEVEL_HIGHER,
    RISK_LEVEL_LOWER,
    RISK_LEVEL_MEDIUM,
    RISK_LEVEL_UNKNOWN,
    calculate_risk_score,
    classify_risk,
    score_cycle_exposure,
    score_dependency_exposure,
    score_entry_point_exposure,
    score_finding_evidence,
    score_structural_exposure,
    score_test_impact_evidence,
)


class TestRiskScorerClassification:
    """Verify categorical classification thresholds and edge cases."""

    def test_classify_risk_threshold_boundaries(self):
        assert classify_risk(0.0) == RISK_LEVEL_LOWER
        assert classify_risk(29.9) == RISK_LEVEL_LOWER
        assert classify_risk(30.0) == RISK_LEVEL_MEDIUM
        assert classify_risk(59.9) == RISK_LEVEL_MEDIUM
        assert classify_risk(60.0) == RISK_LEVEL_HIGHER
        assert classify_risk(100.0) == RISK_LEVEL_HIGHER

    def test_classify_risk_invalid_or_none(self):
        assert classify_risk(None) == RISK_LEVEL_UNKNOWN
        assert classify_risk(75.0, is_valid_assessment=False) == RISK_LEVEL_UNKNOWN


class TestDependencyExposureScoring:
    """L1: Verify dependency exposure calculations and bounded contributions."""

    def test_zero_dependants(self):
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "direct_dependants": [],
        }
        res = score_dependency_exposure(finding, graph_is_available=True)
        assert res.score == 0.0
        assert res.observed_value == 0
        assert res.status == "evaluated"
        assert res.evidence == []

    def test_single_dependant(self):
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "direct_dependants": [{"file_path": "src/services/auth.ts"}],
        }
        res = score_dependency_exposure(finding, graph_is_available=True)
        assert res.score == 5.0
        assert res.observed_value == 1
        assert "src/services/auth.ts" in res.evidence

    def test_multiple_dependants_bounded(self):
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "direct_dependants": [
                {"file_path": f"src/module_{i}.ts"} for i in range(4)
            ],
        }
        res = score_dependency_exposure(finding, graph_is_available=True)
        assert res.score == 20.0
        assert res.observed_value == 4

    def test_high_dependant_count_with_breadth_bonus(self):
        # 6 dependants spanning across distinct directories
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "direct_dependants": [
                {"file_path": "api/routes.ts"},
                {"file_path": "services/payment.ts"},
                {"file_path": "cli/run.ts"},
                {"file_path": "workers/job.ts"},
                {"file_path": "web/index.ts"},
                {"file_path": "admin/portal.ts"},
            ],
        }
        res = score_dependency_exposure(finding, graph_is_available=True)
        # Cap is MAX_F1_DEPENDENCY (25.0)
        assert res.score == MAX_F1_DEPENDENCY
        assert res.observed_value == 6

    def test_unmapped_or_unavailable_graph(self):
        finding = {
            "mapping_status": MAPPING_STATUS_UNMAPPED,
            "direct_dependants": [{"file_path": "src/app.ts"}],
        }
        res = score_dependency_exposure(finding, graph_is_available=True)
        assert res.score == 0.0
        assert res.status == "unmapped"

        res_unavail = score_dependency_exposure(finding, graph_is_available=False)
        assert res_unavail.score == 0.0
        assert res_unavail.status == "unavailable"


class TestCycleExposureScoring:
    """L2: Verify cycle exposure and proper differentiation of self-loops."""

    def test_no_cycle(self):
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "cycle_member": False,
            "self_dependency_detected": False,
            "cycles": [],
        }
        res = score_cycle_exposure(finding, graph_is_available=True)
        assert res.score == 0.0
        assert res.observed_value == "no_cycle"

    def test_self_loop_only_is_not_multi_file_cycle(self):
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "file_path": "src/utils.ts",
            "cycle_member": True,
            "self_dependency_detected": True,
            "cycles": [["src/utils.ts", "src/utils.ts"]],
        }
        res = score_cycle_exposure(finding, graph_is_available=True)
        # Self loop gets 4 points, NOT 15 points
        assert res.score == 4.0
        assert res.observed_value == "self_loop_only"

    def test_multi_file_cycle(self):
        finding = {
            "mapping_status": MAPPING_STATUS_MAPPED,
            "file_path": "src/a.ts",
            "cycle_member": True,
            "self_dependency_detected": False,
            "cycles": [["src/a.ts", "src/b.ts", "src/a.ts"]],
        }
        res = score_cycle_exposure(finding, graph_is_available=True)
        assert res.score == MAX_F2_CYCLE
        assert res.observed_value == "multi_file_cycle"


class TestEntryPointExposureScoring:
    """L4: Verify entry-point exposure scoring."""

    def test_strong_entry_point_from_package(self):
        finding = {"file_path": "src/index.ts"}
        entry_points = [
            {
                "file_path": "src/index.ts",
                "entry_point_type": "package_main",
                "evidence": [{"source": "package.json"}],
            }
        ]
        res = score_entry_point_exposure(finding, entry_points=entry_points)
        assert res.score == 20.0
        assert "package_main" in str(res.observed_value)

    def test_canonical_filename_heuristic(self):
        finding = {"file_path": "src/index.ts"}
        res = score_entry_point_exposure(finding, entry_points=[])
        assert res.score == 12.0
        assert res.observed_value == "canonical_entry_filename"

    def test_not_an_entry_point(self):
        finding = {"file_path": "src/helpers/string.ts"}
        res = score_entry_point_exposure(finding, entry_points=[])
        assert res.score == 0.0
        assert res.observed_value == "not_entry_point"


class TestTestImpactExposureScoring:
    """L3: Verify test impact evidence scoring and safety invariants."""

    def test_direct_test_candidate(self):
        finding = {
            "test_impact": {
                "summary": {"direct_test_count": 1, "heuristic_test_count": 0},
                "candidate_tests": [
                    {
                        "file_path": "tests/test_auth.ts",
                        "mapping_status": "direct",
                        "evidence_type": "static_import",
                    }
                ],
            }
        }
        res = score_test_impact_evidence(finding)
        assert res.score == MAX_F4_TEST_IMPACT
        assert res.observed_value == "direct_test_candidate"

    def test_transitive_test_candidate(self):
        finding = {
            "test_impact": {
                "summary": {"direct_test_count": 0, "heuristic_test_count": 1},
                "candidate_tests": [
                    {
                        "file_path": "tests/test_flow.ts",
                        "mapping_status": "heuristic",
                        "evidence_type": "transitive_dependency",
                    }
                ],
            }
        }
        res = score_test_impact_evidence(finding)
        assert res.score == 10.0
        assert res.observed_value == "transitive_test_candidate"

    def test_heuristic_test_candidate_only(self):
        finding = {
            "test_impact": {
                "summary": {"direct_test_count": 0, "heuristic_test_count": 1},
                "candidate_tests": [
                    {
                        "file_path": "src/utils.test.ts",
                        "mapping_status": "heuristic",
                        "evidence_type": "filename_match",
                    }
                ],
            }
        }
        res = score_test_impact_evidence(finding)
        assert res.score == 6.0
        assert res.observed_value == "heuristic_test_candidate"

    def test_absence_of_tests_never_reduces_score(self):
        finding = {
            "test_impact": {
                "summary": {"direct_test_count": 0, "heuristic_test_count": 0},
                "candidate_tests": [],
            }
        }
        res = score_test_impact_evidence(finding)
        # Score is 0 (does not reduce below 0, never negative)
        assert res.score == 0.0
        assert res.observed_value == "no_tests_identified"


class TestCalculateRiskScoreIntegration:
    """Verify combined factor calculation and score clamping."""

    def test_higher_risk_combination(self):
        finding = {
            "file_path": "src/services/payment.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "category": "unused_export",
            "evidence_class": "inconclusive",
            "direct_dependants": [{"file_path": f"src/c_{i}.ts"} for i in range(5)],
            "direct_dependencies": [{"file_path": f"src/d_{i}.ts"} for i in range(6)],
            "cycle_member": True,
            "cycles": [["src/services/payment.ts", "src/services/order.ts", "src/services/payment.ts"]],
            "self_dependency_detected": False,
            "test_impact": {
                "summary": {"direct_test_count": 1},
                "candidate_tests": [{"file_path": "tests/payment.test.ts", "mapping_status": "direct"}],
            },
        }
        entry_points = [{"file_path": "src/services/payment.ts", "entry_point_type": "package_main"}]

        score, risk_level, factors = calculate_risk_score(
            finding=finding,
            graph_is_available=True,
            entry_points=entry_points,
        )
        assert score is not None
        assert score >= 60.0
        assert risk_level == RISK_LEVEL_HIGHER
        assert len(factors) == 6
        # Must be bounded to 100 max
        assert score <= 100.0

    def test_lower_risk_combination(self):
        finding = {
            "file_path": "src/utils/math.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "category": "unused_file",
            "evidence_class": "conclusive",
            "direct_dependants": [],
            "direct_dependencies": [],
            "cycle_member": False,
            "cycles": [],
            "self_dependency_detected": False,
            "test_impact": {
                "summary": {"direct_test_count": 0},
                "candidate_tests": [],
            },
        }
        score, risk_level, factors = calculate_risk_score(
            finding=finding,
            graph_is_available=True,
            entry_points=[],
        )
        assert score is not None
        assert score < 30.0
        assert risk_level == RISK_LEVEL_LOWER

    def test_unmapped_finding_produces_unknown(self):
        finding = {
            "file_path": "invalid/path/../file.ts",
            "mapping_status": MAPPING_STATUS_INVALID_PATH,
        }
        score, risk_level, factors = calculate_risk_score(
            finding=finding,
            graph_is_available=True,
        )
        assert score is None
        assert risk_level == RISK_LEVEL_UNKNOWN


class TestRiskScorerMathematicalInvariants:
    """Rigorous mathematical audits for factor sum, additive bonuses, and clamping."""

    def test_exact_factor_sum_consistency_across_scenarios(self):
        scenarios = [
            # Minimal / zero
            {
                "file_path": "src/utils.ts",
                "mapping_status": MAPPING_STATUS_MAPPED,
                "category": "unused_file",
                "evidence_class": "conclusive",
                "direct_dependants": [],
                "direct_dependencies": [],
            },
            # Moderate
            {
                "file_path": "src/services/user.ts",
                "mapping_status": MAPPING_STATUS_MAPPED,
                "category": "unused_export",
                "evidence_class": "conclusive",
                "direct_dependants": [{"file_path": "src/api/user.ts"}, {"file_path": "src/api/auth.ts"}],
                "direct_dependencies": [],
                "test_impact": {
                    "summary": {"direct_test_count": 0, "heuristic_test_count": 1},
                    "candidate_tests": [{"file_path": "src/services/user.test.ts", "mapping_status": "heuristic"}],
                },
            },
            # High
            {
                "file_path": "src/services/payment.ts",
                "mapping_status": MAPPING_STATUS_MAPPED,
                "category": "unused_export",
                "evidence_class": "inconclusive",
                "direct_dependants": [
                    {"file_path": "src/api/checkout.ts"},
                    {"file_path": "src/workers/billing.ts"},
                    {"file_path": "src/admin/portal.ts"},
                ],
                "direct_dependencies": [{"file_path": "src/utils/logger.ts"}],
                "cycle_member": True,
                "cycles": [["src/services/payment.ts", "src/services/order.ts", "src/services/payment.ts"]],
                "self_dependency_detected": False,
                "test_impact": {
                    "status": "success",
                    "mapping_complete": True,
                    "candidate_tests": [{"file_path": "tests/payment.test.ts", "mapping_status": "direct"}],
                    "summary": {"direct_test_count": 1, "heuristic_test_count": 0},
                },
            },
        ]

        for finding in scenarios:
            score, risk_level, factors = calculate_risk_score(finding, graph_is_available=True)
            assert score is not None
            expected_sum = round(min(100.0, max(0.0, sum(f.score for f in factors))), 1)
            # The total risk score MUST EQUAL the sum of its factor contributions
            assert score == expected_sum, f"Score {score} != expected factor sum {expected_sum}"

    def test_inconclusive_evidence_additive_rule(self):
        # 1. unused_export: 10 base
        f_export_conclusive = {"category": "unused_export", "evidence_class": "conclusive"}
        res = score_finding_evidence(f_export_conclusive)
        assert res.score == 10.0

        # unused_export + inconclusive: 10 + 5 = 15
        f_export_inconclusive = {"category": "unused_export", "evidence_class": "inconclusive"}
        res = score_finding_evidence(f_export_inconclusive)
        assert res.score == 15.0

        # 2. unused_file: 5 base
        f_file_conclusive = {"category": "unused_file", "evidence_class": "conclusive"}
        res = score_finding_evidence(f_file_conclusive)
        assert res.score == 5.0

        # unused_file + inconclusive: 5 + 5 = 10
        f_file_inconclusive = {"category": "unused_file", "evidence_class": "inconclusive"}
        res = score_finding_evidence(f_file_inconclusive)
        assert res.score == 10.0

        # 3. duplicate_code: 8 base
        f_dup_conclusive = {"category": "duplicate_code", "evidence_class": "conclusive"}
        res = score_finding_evidence(f_dup_conclusive)
        assert res.score == 8.0

        # duplicate_code + inconclusive: 8 + 5 = 13
        f_dup_inconclusive = {"category": "duplicate_code", "evidence_class": "inconclusive"}
        res = score_finding_evidence(f_dup_inconclusive)
        assert res.score == 13.0

    def test_score_upper_bound_clamping(self):
        # Construct synthetic finding where individual factors sum to > 100
        # F1: 25, F2: 15, F3: 20, F4: 15, F5: 15, F6: 10 => Sum: 100
        finding = {
            "file_path": "src/core/main.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "category": "unused_export",
            "evidence_class": "inconclusive",
            "direct_dependants": [{"file_path": f"module_{i}/file.ts"} for i in range(10)],
            "direct_dependencies": [{"file_path": f"src/dep_{i}.ts"} for i in range(8)],
            "cycle_member": True,
            "cycles": [["src/core/main.ts", "src/core/other.ts", "src/core/main.ts"]],
            "test_impact": {
                "summary": {"direct_test_count": 2},
                "candidate_tests": [{"file_path": "tests/main.test.ts", "mapping_status": "direct"}],
            },
        }
        entry_points = [{"file_path": "src/core/main.ts", "entry_point_type": "package_main"}]
        score, risk_level, factors = calculate_risk_score(
            finding=finding,
            graph_is_available=True,
            entry_points=entry_points,
        )
        assert score == 100.0
        assert risk_level == RISK_LEVEL_HIGHER
        assert all(f.score <= f.maximum_score for f in factors)

    def test_no_accidental_double_counting(self):
        finding = {
            "file_path": "src/utils.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "category": "unused_file",
            "evidence_class": "conclusive",
            "direct_dependants": [],
            "direct_dependencies": [{"file_path": "src/helper.ts"} for _ in range(10)],
        }
        f1 = score_dependency_exposure(finding, graph_is_available=True)
        # Outgoing dependencies must NEVER be counted in incoming dependency exposure
        assert f1.score == 0.0
        assert f1.observed_value == 0

        # Direct test candidate must not also trigger transitive or heuristic points in F4
        test_finding = {
            "test_impact": {
                "summary": {"direct_test_count": 1, "heuristic_test_count": 2},
                "candidate_tests": [
                    {"file_path": "tests/test.ts", "mapping_status": "direct"},
                    {"file_path": "tests/other.ts", "mapping_status": "heuristic"},
                ],
            }
        }
        f4 = score_test_impact_evidence(test_finding)
        # Directly imports -> 15.0 (not 15 + 6 = 21)
        assert f4.score == 15.0

    def test_deterministic_reproducibility(self):
        finding = {
            "file_path": "src/services/auth.ts",
            "mapping_status": MAPPING_STATUS_MAPPED,
            "category": "unused_export",
            "evidence_class": "inconclusive",
            "direct_dependants": [{"file_path": "src/api/auth.ts"}],
            "direct_dependencies": [],
        }
        scores = [calculate_risk_score(finding, graph_is_available=True)[0] for _ in range(50)]
        assert all(s == scores[0] for s in scores)



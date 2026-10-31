"""Unit tests for CodeImpact review-risk explainability engine.

Verifies positive factor justifications, strict mitigation rules (mitigations only
allowed on complete graphs, absence of tests never considered a mitigation),
explicit uncertainty disclosures, and actionable review recommendations.
"""

from __future__ import annotations

import pytest

from backend.app.schemas.risk import RiskFactorBreakdown
from backend.app.services.dependency_impact.risk_explainer import (
    generate_mitigating_observations,
    generate_positive_factors,
    generate_recommendation,
    generate_uncertainties,
)


class TestRiskExplainerPositiveFactors:
    """Verify generation of positive risk factors from evidence."""

    def test_positive_factors_for_dependants_and_cycles(self):
        finding = {"category": "unused_export"}
        factors = [
            RiskFactorBreakdown(
                factor="dependency_exposure",
                score=15.0,
                maximum_score=25.0,
                observed_value=3,
                reason="3 files import this module.",
            ),
            RiskFactorBreakdown(
                factor="cycle_exposure",
                score=15.0,
                maximum_score=15.0,
                observed_value="multi_file_cycle",
                reason="Cycle detected.",
            ),
            RiskFactorBreakdown(
                factor="entry_point_exposure",
                score=0.0,
                maximum_score=20.0,
                observed_value="not_entry_point",
            ),
        ]
        pos = generate_positive_factors(finding, factors)
        assert any("3 files directly import" in p for p in pos)
        assert any("multi-file circular dependency" in p for p in pos)
        # Entry point had score 0, should not appear in positive factors
        assert not any("entry-point" in p for p in pos)


class TestRiskExplainerMitigations:
    """Verify strict mitigation generation rules."""

    def test_mitigations_emitted_on_complete_graph(self):
        finding = {
            "direct_dependants": [],
            "cycle_member": False,
            "self_dependency_detected": False,
        }
        factors = [
            RiskFactorBreakdown(
                factor="entry_point_exposure",
                score=0.0,
                maximum_score=20.0,
                observed_value="not_entry_point",
            )
        ]
        mitigations = generate_mitigating_observations(
            finding=finding,
            graph_is_available=True,
            graph_is_truncated=False,
            factors=factors,
        )
        assert any("No incoming static import edges" in m for m in mitigations)
        assert any("No circular dependencies" in m for m in mitigations)
        assert any("No application or module entry-point" in m for m in mitigations)

    def test_no_mitigations_when_graph_is_truncated(self):
        finding = {
            "direct_dependants": [],
            "cycle_member": False,
            "self_dependency_detected": False,
        }
        # In a truncated graph, zero dependants could just be omitted by truncation!
        mitigations = generate_mitigating_observations(
            finding=finding,
            graph_is_available=True,
            graph_is_truncated=True,
        )
        assert len(mitigations) == 0

    def test_no_mitigations_when_graph_is_unavailable(self):
        finding = {
            "direct_dependants": [],
            "cycle_member": False,
        }
        mitigations = generate_mitigating_observations(
            finding=finding,
            graph_is_available=False,
            graph_is_truncated=False,
        )
        assert len(mitigations) == 0

    def test_absence_of_tests_never_emitted_as_mitigation(self):
        finding = {
            "direct_dependants": [],
            "cycle_member": False,
            "self_dependency_detected": False,
            "test_impact": {"candidate_tests": []},
        }
        mitigations = generate_mitigating_observations(
            finding=finding,
            graph_is_available=True,
            graph_is_truncated=False,
        )
        # Safety rule: "no tests found" must NEVER be in mitigations
        for m in mitigations:
            assert "test" not in m.lower(), f"Forbidden mitigation found: {m}"


class TestRiskExplainerUncertainties:
    """Verify transparent disclosure of uncertainties."""

    def test_uncertainties_include_dynamic_imports_and_truncation(self):
        finding = {"test_impact": {"candidate_tests": []}}
        unc = generate_uncertainties(
            finding=finding,
            graph_is_available=True,
            graph_is_truncated=True,
            test_impact_complete=False,
        )
        assert any("dynamic import" in u.lower() for u in unc)
        assert any("truncated" in u.lower() for u in unc)
        assert any("absence of tests does not indicate code is safe to delete" in u for u in unc)
        assert any("partial or incomplete" in u.lower() for u in unc)


class TestRiskExplainerRecommendations:
    """Verify actionable recommendation generation."""

    def test_recommendation_with_dependants_and_tests(self):
        finding = {"file_path": "src/api.ts"}
        factors = [
            RiskFactorBreakdown(
                factor="dependency_exposure",
                score=15.0,
                maximum_score=25.0,
                observed_value=3,
            ),
            RiskFactorBreakdown(
                factor="test_impact_evidence",
                score=15.0,
                maximum_score=15.0,
                observed_value="direct_test_candidate",
            ),
        ]
        rec = generate_recommendation(finding, review_risk="higher", factors=factors)
        assert "review all 3 direct dependant(s)" in rec
        assert "inspect potentially related candidate tests" in rec

    def test_recommendation_for_unknown_risk(self):
        finding = {"file_path": "src/api.ts"}
        rec = generate_recommendation(finding, review_risk="unknown", factors=[])
        assert "Obtain complete dependency graph" in rec


"""Explainability Engine for CodeImpact Review-Risk Engine.

Generates human-readable, evidence-backed justifications including positive risk factors,
strict mitigating observations from complete analyses, explicit uncertainties, and
actionable review recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.schemas.risk import RiskFactorBreakdown

logger = logging.getLogger(__name__)


def generate_positive_factors(
    finding: dict[str, Any],
    factors: list[RiskFactorBreakdown],
) -> list[str]:
    """Generate list of factors increasing review urgency based on observed evidence."""
    positive: list[str] = []

    for f in factors:
        if f.score <= 0:
            continue

        if f.factor == "dependency_exposure":
            count = f.observed_value
            if isinstance(count, int) and count > 0:
                s = "s" if count > 1 else ""
                positive.append(f"{count} file{s} directly import{'' if count > 1 else 's'} this module.")
        elif f.factor == "cycle_exposure":
            if f.observed_value == "multi_file_cycle":
                positive.append("Module participates in a multi-file circular dependency.")
            elif f.observed_value == "self_loop_only":
                positive.append("Module exhibits a self-import loop.")
        elif f.factor == "entry_point_exposure":
            positive.append(f"Application entry-point indicator detected: {f.reason}")
        elif f.factor == "test_impact_evidence":
            if f.observed_value == "direct_test_candidate":
                positive.append("Candidate test files directly import this module.")
            elif f.observed_value == "transitive_test_candidate":
                positive.append("Candidate test files are connected via transitive dependency chains.")
            elif f.observed_value == "heuristic_test_candidate":
                positive.append("Candidate test files were matched via naming or directory heuristics.")
        elif f.factor == "finding_evidence_uncertainty":
            category = finding.get("category", "")
            if category == "unused_export":
                positive.append("Flagged symbol is an export; external consumers or dynamic imports may rely on it.")
            elif category == "duplicate_code":
                positive.append("Duplicate code refactoring requires cross-module structural reconciliation.")
        elif f.factor == "special_structural_exposure":
            if f.score > 0:
                positive.append(f.reason)

    return positive


def generate_mitigating_observations(
    finding: dict[str, Any],
    graph_is_available: bool = True,
    graph_is_truncated: bool = False,
    factors: list[RiskFactorBreakdown] | None = None,
) -> list[str]:
    """Generate mitigating observations.

    SAFETY RULE: Mitigations are ONLY emitted when the graph is available and NOT truncated.
    Absence of tests is NEVER emitted as a mitigation.
    """
    mitigating: list[str] = []

    if not graph_is_available or graph_is_truncated:
        return mitigating

    # Check direct dependants
    direct_dependants = finding.get("direct_dependants") or []
    if len(direct_dependants) == 0:
        mitigating.append("No incoming static import edges identified in complete dependency graph.")

    # Check cycle membership
    is_cycle_member = bool(finding.get("cycle_member", False))
    self_loop = bool(finding.get("self_dependency_detected", False))
    if not is_cycle_member and not self_loop:
        mitigating.append("No circular dependencies detected for this module in complete graph.")

    # Check entry point
    ep_factor = next((f for f in (factors or []) if f.factor == "entry_point_exposure"), None)
    if ep_factor and ep_factor.score == 0:
        mitigating.append("No application or module entry-point characteristics identified.")

    return mitigating


def generate_uncertainties(
    finding: dict[str, Any],
    graph_is_available: bool = True,
    graph_is_truncated: bool = False,
    test_impact_complete: bool = True,
) -> list[str]:
    """Generate explicit uncertainties and analysis limitations."""
    uncertainties: list[str] = [
        "Static dependency analysis cannot detect dynamic import() expressions, reflection, or external consumers.",
    ]

    if not graph_is_available:
        uncertainties.append("Dependency graph was unavailable; dependency and cycle exposure could not be validated.")

    if graph_is_truncated:
        uncertainties.append("Dependency graph was truncated due to node/edge limits; some relationships may be omitted.")

    test_impact = finding.get("test_impact") or {}
    candidates = test_impact.get("candidate_tests") or []
    if candidates:
        uncertainties.append("Identified candidate tests do not establish runtime assertion or code coverage.")
    else:
        uncertainties.append("No candidate test files were identified; absence of tests does not indicate code is safe to delete.")

    if not test_impact_complete:
        uncertainties.append("Test impact mapping was executed against a partial or incomplete file inventory.")

    return uncertainties


def generate_recommendation(
    finding: dict[str, Any],
    review_risk: str,
    factors: list[RiskFactorBreakdown],
) -> str:
    """Generate actionable, evidence-driven human review recommendation."""
    if review_risk == "unknown":
        return "Obtain complete dependency graph and repository mapping before evaluating refactoring risk."

    actions: list[str] = []

    # Check dependency factor
    dep_factor = next((f for f in factors if f.factor == "dependency_exposure"), None)
    if dep_factor and dep_factor.observed_value and int(dep_factor.observed_value) > 0:
        count = int(dep_factor.observed_value)
        actions.append(f"review all {count} direct dependant(s)")

    # Check cycle factor
    cycle_factor = next((f for f in factors if f.factor == "cycle_exposure"), None)
    if cycle_factor and cycle_factor.observed_value == "multi_file_cycle":
        actions.append("inspect and decouple circular dependency chain")

    # Check entry point factor
    ep_factor = next((f for f in factors if f.factor == "entry_point_exposure"), None)
    if ep_factor and ep_factor.score > 0:
        actions.append("verify runtime application bootstrap and entry-point behavior")

    # Check test factor
    test_factor = next((f for f in factors if f.factor == "test_impact_evidence"), None)
    if test_factor and test_factor.score > 0:
        actions.append("inspect potentially related candidate tests")

    if not actions:
        if review_risk == "lower":
            return "Verify whether module is dynamically imported or consumed by external packages before considering removal."
        return "Perform standard code review before refactoring."

    joined_actions = ", ".join(actions)
    return f"Carefully {joined_actions} before making any refactoring or deletion decisions."


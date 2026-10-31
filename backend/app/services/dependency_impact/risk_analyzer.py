"""Top-level service coordinator for Phase 6 Explainable Review-Risk Engine.

Synthesizes evidence from dependency graphs, direct impacts, test impact candidates,
and entry-point indicators into deterministic review-risk scores, confidence ratings,
factor breakdowns, and human decision-support recommendations.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from pydantic import BaseModel

from backend.app.schemas.risk import (
    RiskAnalysisResult,
    RiskAssessment,
    RiskSummary,
)
from backend.app.services.dependency_impact.impact_analyzer import (
    IMPACT_STATUS_PARTIAL,
    IMPACT_STATUS_SUCCESS,
    IMPACT_STATUS_UNAVAILABLE,
    _extract_graph_info,
)
from backend.app.services.dependency_impact.risk_explainer import (
    generate_mitigating_observations,
    generate_positive_factors,
    generate_recommendation,
    generate_uncertainties,
)
from backend.app.services.dependency_impact.risk_scorer import (
    RISK_LEVEL_HIGHER,
    RISK_LEVEL_LOWER,
    RISK_LEVEL_MEDIUM,
    RISK_LEVEL_UNKNOWN,
    calculate_risk_score,
)

logger = logging.getLogger(__name__)


def compute_confidence(
    finding: dict[str, Any],
    graph_is_available: bool,
    graph_is_truncated: bool,
    review_risk: str,
) -> str:
    """Determine confidence level for an individual finding's review-risk assessment.

    Args:
        finding: Enriched finding dictionary.
        graph_is_available: Whether graph was successfully analyzed.
        graph_is_truncated: Whether graph was truncated due to limits.
        review_risk: Calculated risk level.

    Returns:
        One of 'high', 'medium', 'low', 'unknown'.
    """
    if not graph_is_available or review_risk == RISK_LEVEL_UNKNOWN:
        return "unknown"

    if graph_is_truncated:
        return "low"

    test_impact = finding.get("test_impact") or {}
    test_status = test_impact.get("status")
    if test_status in (IMPACT_STATUS_PARTIAL, IMPACT_STATUS_UNAVAILABLE):
        return "medium"

    return "high"


def compute_completeness(
    finding: dict[str, Any],
    graph_is_available: bool,
    graph_is_truncated: bool,
    review_risk: str,
) -> str:
    """Determine analysis completeness for an individual finding.

    Args:
        finding: Enriched finding dictionary.
        graph_is_available: Whether graph was successfully analyzed.
        graph_is_truncated: Whether graph was truncated.
        review_risk: Calculated risk level.

    Returns:
        One of 'complete', 'partial', 'unavailable'.
    """
    if not graph_is_available or review_risk == RISK_LEVEL_UNKNOWN:
        return "unavailable"

    if graph_is_truncated or finding.get("impact_status") == IMPACT_STATUS_PARTIAL:
        return "partial"

    test_impact = finding.get("test_impact") or {}
    if test_impact.get("status") == IMPACT_STATUS_PARTIAL:
        return "partial"

    return "complete"


def analyze_review_risk(
    graph: dict[str, Any] | BaseModel | None = None,
    enriched_findings: list[dict[str, Any]] | None = None,
    entry_points: list[dict[str, Any]] | None = None,
    analysis_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Calculate deterministic, explainable review-risk assessments for enriched findings.

    Reuses Phase 3 graph, Phase 4 impact findings, and Phase 5 test-impact data.
    NEVER calls Madge, never executes target code, never mutates input findings.

    Args:
        graph: Pre-constructed dependency graph dictionary or Pydantic model.
        enriched_findings: List of enriched findings from Phase 4/5.
        entry_points: Optional list of detected application/module entry points.
        analysis_id: Unique analysis identifier.

    Returns:
        Structured dictionary conforming to RiskAnalysisResult schema.
    """
    if enriched_findings is None:
        enriched_findings = []

    # Handle entry_points in kwargs if passed
    if entry_points is None and "entry_point_evidence" in kwargs:
        entry_points = kwargs.pop("entry_point_evidence")

    graph_dict, graph_status, graph_is_available, graph_is_truncated = _extract_graph_info(graph)

    updated_findings: list[dict[str, Any]] = []
    assessed_count = 0
    unassessed_count = 0
    higher_count = 0
    medium_count = 0
    lower_count = 0
    unknown_count = 0
    total_score = 0.0

    for raw_finding in enriched_findings:
        if not isinstance(raw_finding, dict):
            continue

        # Non-mutating deep-copy of input finding
        finding_copy = copy.deepcopy(raw_finding)

        # 1. Deterministic scoring
        risk_score, review_risk, factors = calculate_risk_score(
            finding=finding_copy,
            graph_is_available=graph_is_available,
            entry_points=entry_points,
        )

        # 2. Confidence and completeness
        confidence = compute_confidence(
            finding=finding_copy,
            graph_is_available=graph_is_available,
            graph_is_truncated=graph_is_truncated,
            review_risk=review_risk,
        )
        completeness = compute_completeness(
            finding=finding_copy,
            graph_is_available=graph_is_available,
            graph_is_truncated=graph_is_truncated,
            review_risk=review_risk,
        )

        # 3. Explanations
        positive_factors = generate_positive_factors(finding_copy, factors)
        mitigating = generate_mitigating_observations(
            finding=finding_copy,
            graph_is_available=graph_is_available,
            graph_is_truncated=graph_is_truncated,
            factors=factors,
        )
        uncertainties = generate_uncertainties(
            finding=finding_copy,
            graph_is_available=graph_is_available,
            graph_is_truncated=graph_is_truncated,
            test_impact_complete=(completeness == "complete"),
        )
        recommendation = generate_recommendation(finding_copy, review_risk, factors)

        risk_assessment = RiskAssessment(
            analysis_completeness=completeness,
            factor_breakdown=factors,
            positive_factors=positive_factors,
            mitigating_observations=mitigating,
            uncertainties=uncertainties,
            recommendation=recommendation,
        )

        # 4. Attach Phase 6 fields
        finding_copy["review_risk"] = review_risk
        finding_copy["risk_score"] = risk_score
        finding_copy["risk_confidence"] = confidence
        finding_copy["risk_assessment"] = risk_assessment.model_dump()

        updated_findings.append(finding_copy)

        # Aggregate summary counters
        if review_risk == RISK_LEVEL_HIGHER:
            higher_count += 1
        elif review_risk == RISK_LEVEL_MEDIUM:
            medium_count += 1
        elif review_risk == RISK_LEVEL_LOWER:
            lower_count += 1
        else:
            unknown_count += 1

        if risk_score is not None:
            assessed_count += 1
            total_score += risk_score
        else:
            unassessed_count += 1

    # Average risk score across assessed findings
    average_score: float | None = None
    if assessed_count > 0:
        average_score = round(total_score / assessed_count, 1)

    summary = RiskSummary(
        total_findings=len(updated_findings),
        assessed_findings=assessed_count,
        unassessed_findings=unassessed_count,
        higher_risk_count=higher_count,
        medium_risk_count=medium_count,
        lower_risk_count=lower_count,
        unknown_risk_count=unknown_count,
        average_risk_score=average_score,
    )

    # Determine overall execution status
    if not graph_is_available:
        overall_status = IMPACT_STATUS_UNAVAILABLE
    elif graph_is_truncated or graph_status == IMPACT_STATUS_PARTIAL:
        overall_status = IMPACT_STATUS_PARTIAL
    else:
        overall_status = IMPACT_STATUS_SUCCESS

    result = RiskAnalysisResult(
        analysis_id=analysis_id,
        status=overall_status,
        enriched_findings=updated_findings,
        summary=summary,
    )

    return result.model_dump()


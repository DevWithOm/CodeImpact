"""Pydantic schemas for CodeImpact explainable review-risk engine."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class RiskFactorBreakdown(BaseModel):
    """Detailed score and evidence breakdown for an individual review-risk factor."""
    __test__ = False
    factor: str = Field(description="Factor identifier (e.g. 'dependency_exposure', 'cycle_exposure')")
    score: float = Field(ge=0.0, le=100.0, description="Numerical points contributed by this factor")
    maximum_score: float = Field(ge=0.0, le=100.0, description="Maximum possible points for this factor")
    observed_value: Any | None = Field(default=None, description="Observed metric value (count, flag, or label)")
    status: str = Field(
        default="evaluated",
        description="Factor evaluation status: 'evaluated', 'not_applicable', 'unavailable'"
    )
    reason: str = Field(default="", description="Human-readable explanation of factor contribution")
    evidence: list[Any] = Field(
        default_factory=list,
        description="Traceable supporting evidence items (paths, cycle chains, etc.)"
    )

    model_config = ConfigDict(extra="allow")


class RiskAssessment(BaseModel):
    """Comprehensive explainable review-risk assessment payload."""
    __test__ = False
    analysis_completeness: str = Field(
        default="complete",
        description="Analysis stage completeness: 'complete', 'partial', 'unavailable'"
    )
    factor_breakdown: list[RiskFactorBreakdown] = Field(
        default_factory=list,
        description="Factor-by-factor breakdown of risk contributions"
    )
    positive_factors: list[str] = Field(
        default_factory=list,
        description="Factors increasing review urgency"
    )
    mitigating_observations: list[str] = Field(
        default_factory=list,
        description="Genuine mitigating observations from complete analyses"
    )
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Identified analysis limitations, heuristics, or unverified areas"
    )
    recommendation: str = Field(
        default="",
        description="Deterministic, evidence-based human review recommendation"
    )

    model_config = ConfigDict(extra="allow")


class FindingRiskResult(BaseModel):
    """Review-risk result for an individual static analysis finding."""
    __test__ = False
    finding_id: str = Field(description="Unique finding identifier")
    review_risk: str = Field(
        description="Categorical risk priority: 'lower', 'medium', 'higher', 'unknown'"
    )
    risk_score: float | None = Field(
        default=None,
        description="Deterministic bounded score (0-100), or None if unassessed/unknown"
    )
    risk_confidence: str = Field(
        description="Confidence in evidence backing the assessment: 'high', 'medium', 'low', 'unknown'"
    )
    risk_assessment: RiskAssessment = Field(
        description="Detailed explainability payload and factor breakdown"
    )

    model_config = ConfigDict(extra="allow")


class RiskSummary(BaseModel):
    """Repository-level summary metrics of review-risk distribution."""
    __test__ = False
    total_findings: int = Field(default=0, ge=0, description="Total number of findings provided")
    assessed_findings: int = Field(default=0, ge=0, description="Findings with evaluated numeric risk scores")
    unassessed_findings: int = Field(default=0, ge=0, description="Findings with unknown/unassessed risk")
    higher_risk_count: int = Field(default=0, ge=0, description="Count of findings classified as higher risk")
    medium_risk_count: int = Field(default=0, ge=0, description="Count of findings classified as medium risk")
    lower_risk_count: int = Field(default=0, ge=0, description="Count of findings classified as lower risk")
    unknown_risk_count: int = Field(default=0, ge=0, description="Count of findings classified as unknown risk")
    average_risk_score: float | None = Field(
        default=None,
        description="Mean score across all assessed findings, or None if none assessed"
    )

    model_config = ConfigDict(extra="allow")


class RiskAnalysisResult(BaseModel):
    """Top-level response envelope for Phase 6 Explainable Review-Risk Engine."""
    __test__ = False
    analysis_id: str = Field(description="Unique analysis run identifier")
    status: str = Field(
        default="success",
        description="Overall execution status: 'success', 'partial', 'unavailable'"
    )
    enriched_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Findings enriched with Phase 6 review-risk assessments"
    )
    summary: RiskSummary = Field(
        default_factory=RiskSummary,
        description="Repository-level review-risk summary"
    )

    model_config = ConfigDict(extra="allow")


__all__ = [
    "RiskFactorBreakdown",
    "RiskAssessment",
    "FindingRiskResult",
    "RiskSummary",
    "RiskAnalysisResult",
]


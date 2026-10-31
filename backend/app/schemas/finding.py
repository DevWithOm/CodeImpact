"""Pydantic schemas for static analysis findings and enriched finding models."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.impact import (
    DirectDependant,
    EnrichedFinding,
    FindingImpactSummary,
    ImpactEvidence,
)


class FindingEvidenceItem(BaseModel):
    """Evidence item associated with a static analysis finding."""
    kind: str
    status: str
    source: str
    details: str | None = None


class Finding(BaseModel):
    """Normalized static analysis finding from OM_2."""
    finding_id: str = Field(description="Unique stable finding ID")
    category: str = Field(description="Finding category (unused_export, unused_file, etc.)")
    title: str = Field(default="")
    file_path: str = Field(description="Repository-relative POSIX path")
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    source_tool: str = Field(default="")
    description: str = Field(default="")
    evidence_class: str = Field(default="inconclusive")
    review_risk: str = Field(default="unknown")
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


__all__ = [
    "Finding",
    "FindingEvidenceItem",
    "EnrichedFinding",
    "ImpactEvidence",
    "DirectDependant",
    "FindingImpactSummary",
]

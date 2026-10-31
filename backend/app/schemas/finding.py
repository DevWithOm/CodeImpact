"""Finding schema for CodeImpact static analysis and dependency results."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.evidence import EvidenceItem, FindingImpact
from backend.app.schemas.impact import (
    DirectDependant,
    EnrichedFinding,
    FindingImpactSummary,
    ImpactEvidence,
)

FindingCategory = Literal[
    "unused_file",
    "unused_export",
    "unused_dependency",
    "duplicate_code",
    "duplicate_block",
    "other",
]

EvidenceClass = Literal["strong", "inconclusive", "contradictory"]
ReviewRisk = Literal["lower", "medium", "higher", "unknown"]


class FindingEvidenceItem(BaseModel):
    """Evidence item associated with a static analysis finding."""
    kind: str
    status: str
    source: str
    details: str | None = None
    value: Any | None = None

    model_config = ConfigDict(extra="allow")


class Finding(BaseModel):
    """Normalized static analysis finding."""
    finding_id: str = Field(description="Unique stable finding identifier within analysis")
    category: str = Field(description="Standardized finding category")
    title: str = Field(default="", description="User-friendly title for the finding")
    file_path: str = Field(description="Relative file path from repository root")
    start_line: int | None = Field(default=None, description="Starting line number (1-based), if reported")
    end_line: int | None = Field(default=None, description="Ending line number (1-based), if reported")
    symbol: str | None = Field(default=None, description="Exported identifier or function name, if applicable")
    source_tool: str = Field(default="", description="Tool that produced this finding ('knip' | 'jscpd')")
    description: str = Field(default="", description="Carefully worded finding summary")
    evidence_class: str = Field(
        default="inconclusive",
        description="Confidence classification (strong, inconclusive, contradictory)"
    )
    review_risk: str = Field(
        default="unknown",
        description="Assigned review risk level (SAMAR_3 finalizes; OM_2 sets 'unknown')"
    )
    evidence: list[Any] = Field(
        default_factory=list,
        description="Individual evidence items supporting this finding"
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Risk factors associated with modifying or removing this code"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw or tool-specific supplementary metrics"
    )

    model_config = ConfigDict(extra="allow")


class FindingItem(BaseModel):
    """API-level finding item for frontend and reports."""
    finding_id: str
    category: str
    title: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    source_tool: str
    description: str
    evidence_class: str = "inconclusive"
    review_risk: str = "unknown"
    evidence: list[Any] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    impact: Any | None = None

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class FindingDetail(FindingItem):
    """Detailed finding view with analysis limitations."""
    limitations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class FindingsListResponse(BaseModel):
    """Paginated findings response."""
    analysis_id: str
    items: list[FindingItem] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    tool_coverage: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


__all__ = [
    "FindingCategory",
    "EvidenceClass",
    "ReviewRisk",
    "EvidenceItem",
    "Finding",
    "FindingItem",
    "FindingDetail",
    "FindingsListResponse",
    "FindingEvidenceItem",
    "EnrichedFinding",
    "ImpactEvidence",
    "DirectDependant",
    "FindingImpactSummary",
]

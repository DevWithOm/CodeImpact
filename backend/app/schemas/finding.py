"""Finding schema for CodeImpact static analysis and dependency results."""

from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.app.schemas.evidence import EvidenceItem


FindingCategory = Literal[
    "unused_file",
    "unused_export",
    "unused_dependency",
    "duplicate_code",
    "other",
]

EvidenceClass = Literal["strong", "inconclusive", "contradictory"]
ReviewRisk = Literal["lower", "medium", "higher", "unknown"]


class Finding(BaseModel):
    finding_id: str = Field(..., description="Unique stable finding identifier within analysis")
    category: FindingCategory = Field(..., description="Standardized finding category")
    title: str = Field(..., description="User-friendly title for the finding")
    file_path: str = Field(..., description="Relative file path from repository root")
    start_line: int | None = Field(default=None, description="Starting line number (1-based), if reported")
    end_line: int | None = Field(default=None, description="Ending line number (1-based), if reported")
    symbol: str | None = Field(default=None, description="Exported identifier or function name, if applicable")
    source_tool: str = Field(..., description="Tool that produced this finding ('knip' | 'jscpd')")
    description: str = Field(..., description="Carefully worded finding summary")
    evidence_class: EvidenceClass = Field(
        default="inconclusive",
        description="Confidence classification (strong, inconclusive, contradictory)"
    )
    review_risk: ReviewRisk = Field(
        default="unknown",
        description="Assigned review risk level (SAMAR_3 finalizes; OM_2 sets 'unknown')"
    )
    evidence: list[EvidenceItem] = Field(
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

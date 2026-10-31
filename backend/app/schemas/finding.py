from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

# Re-export Phase 4 types for backward compatibility across teammate modules
from .impact import DirectDependant, FindingImpactSummary, ImpactEvidence


class FindingCategory(str, Enum):
    """Normalized finding categories across Knip and jscpd."""
    UNUSED_FILE = "unused_file"
    UNUSED_EXPORT = "unused_export"
    UNUSED_DEPENDENCY = "unused_dependency"
    DUPLICATE_CODE = "duplicate_code"
    OTHER = "other"


class EvidenceClass(str, Enum):
    """Evidence strength levels."""
    STRONG = "strong"
    INCONCLUSIVE = "inconclusive"
    CONTRADICTORY = "contradictory"


class ReviewRisk(str, Enum):
    """Review risk assessment levels."""
    HIGHER = "higher"
    MEDIUM = "medium"
    LOWER = "lower"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    """Individual piece of supporting evidence."""
    rule: str | None = None
    kind: str | None = None
    status: str | None = None
    detail: str | None = None
    details: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = "knip"
    value: Any | None = None

    model_config = ConfigDict(extra="allow")


class Finding(BaseModel):
    """Raw finding emitted by static code analysis tools (Person 2 / OM_2)."""
    finding_id: str
    category: FindingCategory
    title: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    source_tool: str
    description: str
    evidence_class: EvidenceClass = EvidenceClass.INCONCLUSIVE
    review_risk: ReviewRisk = ReviewRisk.UNKNOWN
    evidence: list[Any] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class FindingEvidenceItem(BaseModel):
    """Legacy/OM evidence model."""
    rule: str
    detail: str
    source_tool: str = "knip"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    model_config = ConfigDict(extra="allow")


class EnrichedFinding(BaseModel):
    """Enriched finding model representing findings augmented with dependency impact."""
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
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


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

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class FindingsListResponse(BaseModel):
    """Paginated findings response."""
    analysis_id: str
    items: list[Any] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    tool_coverage: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


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

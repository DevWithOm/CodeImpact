from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import EvidenceItem, FindingImpact


class ReviewRisk(str, Enum):
    HIGHER = "higher"
    MEDIUM = "medium"
    LOWER = "lower"
    UNKNOWN = "unknown"


class EvidenceClass(str, Enum):
    STRONG = "strong"
    INCONCLUSIVE = "inconclusive"
    CONTRADICTORY = "contradictory"


class FindingCategory(str, Enum):
    UNUSED_EXPORT = "unused_export"
    UNUSED_FILE = "unused_file"
    UNUSED_DEPENDENCY = "unused_dependency"
    DUPLICATE_BLOCK = "duplicate_block"


class FindingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    evidence: list[EvidenceItem] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    impact: FindingImpact | None = None


class FindingDetail(FindingItem):
    limitations: list[str] = Field(default_factory=list)


class FindingsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    items: list[FindingItem] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    tool_coverage: dict[str, str] = Field(default_factory=dict)

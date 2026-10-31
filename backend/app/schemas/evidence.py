"""Evidence schema for CodeImpact findings."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

EvidenceStatus = Literal["found", "not_found", "unknown", "not_checked", "conflicting"]


class EvidenceItem(BaseModel):
    kind: str = Field(..., description="Evidence type (e.g. static_reference_scan, duplicate_block)")
    status: str = Field(..., description="Observation status (found, not_found, unknown, not_checked, conflicting)")
    source: str = Field(..., description="Tool or component providing the evidence (e.g. knip, jscpd)")
    details: str = Field(..., description="Human-readable description of the specific evidence found")
    value: Any | None = Field(default=None, description="Optional raw value or metric associated with evidence")

    model_config = ConfigDict(extra="allow")


class TestCandidate(BaseModel):
    __test__ = False
    file_path: str = Field(..., description="Path to potential test file")
    reason: str = Field(default="", description="Reason this test file was associated")
    mapping_strength: str = Field(default="direct", description="Strength: direct, naming, directory")

    model_config = ConfigDict(extra="allow")


class FindingImpact(BaseModel):
    direct_dependants: list[str] = Field(default_factory=list, description="Files directly importing this component")
    dependency_count: int = Field(default=0, ge=0, description="Total number of direct dependents")
    cycle_member: bool = Field(default=False, description="Whether this file participates in a dependency cycle")
    related_test_candidates: list[TestCandidate] = Field(default_factory=list, description="Suggested test files")
    risk_factors: list[str] = Field(default_factory=list, description="Specific risk drivers identified")
    review_risk: str = Field(default="unknown", description="Review risk priority: higher, medium, lower, unknown")

    model_config = ConfigDict(extra="allow")


__all__ = [
    "EvidenceStatus",
    "EvidenceItem",
    "TestCandidate",
    "FindingImpact",
]

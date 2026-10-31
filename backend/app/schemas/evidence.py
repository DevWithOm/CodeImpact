from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., description="Type of evidence (e.g. direct_reference, package_json_entry)")
    status: str = Field(..., description="Status: found, not_found, unknown, not_checked, conflicting")
    source: str = Field(..., description="Tool or inspection source (e.g. knip, jscpd, ast)")
    details: str = Field(..., description="Human-readable evidence detail")
    value: Any | None = Field(default=None, description="Optional raw or structured value")


class TestCandidate(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., description="Path to potential test file")
    reason: str = Field(..., description="Reason this test file was associated")
    mapping_strength: str = Field(default="direct", description="Strength: direct, naming, directory")


class FindingImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direct_dependants: list[str] = Field(default_factory=list, description="Files directly importing this component")
    dependency_count: int = Field(default=0, ge=0, description="Total number of direct dependents")
    cycle_member: bool = Field(default=False, description="Whether this file participates in a dependency cycle")
    related_test_candidates: list[TestCandidate] = Field(default_factory=list, description="Suggested test files")
    risk_factors: list[str] = Field(default_factory=list, description="Specific risk drivers identified")
    review_risk: str = Field(default="unknown", description="Review risk priority: higher, medium, lower, unknown")

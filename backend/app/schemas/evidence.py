"""Evidence schema for CodeImpact findings."""

from typing import Any, Literal
from pydantic import BaseModel, Field


EvidenceStatus = Literal["found", "not_found", "unknown", "not_checked", "conflicting"]


class EvidenceItem(BaseModel):
    kind: str = Field(..., description="Evidence type (e.g. static_reference_scan, duplicate_block)")
    status: EvidenceStatus = Field(..., description="Observation status")
    source: str = Field(..., description="Tool or component providing the evidence (e.g. knip, jscpd)")
    details: str = Field(..., description="Human-readable description of the specific evidence found")
    value: Any | None = Field(default=None, description="Optional raw value or metric associated with evidence")

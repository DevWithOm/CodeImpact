"""Pydantic schemas for CodeImpact finding-level impact analysis."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ImpactEvidence(BaseModel):
    """Traceable graph edge evidence supporting a reported dependency relationship."""
    edge_id: str = Field(description="Canonical edge ID (source->target)")
    source: str = Field(description="Repository-relative path of importing module")
    target: str = Field(description="Repository-relative path of imported module")
    relationship: str = Field(default="imports", description="Canonical edge relationship")
    evidence_type: str = Field(
        default="static_import_relationship",
        description="Evidence category classification"
    )


class DirectDependant(BaseModel):
    """Direct dependant or dependency relationship item with supporting evidence."""
    file_path: str = Field(description="Repository-relative POSIX path of related file")
    relationship: str = Field(default="imports", description="Relationship connecting the files")
    evidence: ImpactEvidence = Field(description="Supporting graph edge evidence")


class FindingImpactSummary(BaseModel):
    """Summary metrics of direct impact for a single finding."""
    direct_dependant_count: int = Field(default=0, ge=0, description="Count of unique direct dependants")
    direct_dependency_count: int = Field(default=0, ge=0, description="Count of unique direct dependencies")


class EnrichedFinding(BaseModel):
    """Finding enriched with direct dependency and dependant impact analysis."""
    finding_id: str | None = Field(default=None, description="Unique finding identifier")
    file_path: str | None = Field(default=None, description="Normalized repository-relative file path")
    category: str | None = Field(default=None, description="Normalized finding category / type")
    mapping_status: str = Field(
        default="unmapped",
        description="Node mapping status: 'mapped', 'unmapped', 'invalid_path', 'missing_file_path'"
    )
    impact_status: str = Field(
        default="success",
        description="Impact calculation status: 'success', 'partial', 'unavailable'"
    )
    direct_dependants: list[DirectDependant] = Field(
        default_factory=list,
        description="List of files that directly import this file"
    )
    direct_dependencies: list[DirectDependant] = Field(
        default_factory=list,
        description="List of files that this file directly imports"
    )
    self_dependency_detected: bool = Field(
        default=False,
        description="Whether a self-import loop (A -> A) was observed"
    )
    cycle_member: bool = Field(
        default=False,
        description="Whether the associated node is part of a circular dependency"
    )
    cycles: list[list[str]] = Field(
        default_factory=list,
        description="List of circular dependency chains containing this node"
    )
    summary: FindingImpactSummary = Field(
        default_factory=FindingImpactSummary,
        description="Summary counts of direct connections"
    )
    # Extra fields preserved from original static analysis finding
    title: str | None = Field(default=None)
    symbol: str | None = Field(default=None)
    start_line: int | None = Field(default=None)
    end_line: int | None = Field(default=None)
    source_tool: str | None = Field(default=None)
    description: str | None = Field(default=None)
    evidence_class: str | None = Field(default=None)
    review_risk: str | None = Field(default=None)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

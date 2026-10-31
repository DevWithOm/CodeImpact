"""Pydantic schemas for CodeImpact potential test impact mapping."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class TestCandidate(BaseModel):
    """A candidate test file potentially related to a flagged source file."""
    __test__ = False
    file_path: str = Field(description="Repository-relative POSIX path of candidate test file")
    test_type: str = Field(
        default="unit_test",
        description="Test classification: 'unit_test', 'integration_test', 'e2e_test', 'test_config', 'unknown_test_type'"
    )
    mapping_status: str = Field(
        default="heuristic",
        description="Confidence classification: 'direct', 'heuristic', 'unknown'"
    )
    evidence_type: str = Field(
        default="filename_match",
        description="Evidence type: 'static_import', 'transitive_dependency', 'filename_match', 'directory_match'"
    )
    dependency_path: list[str] = Field(
        default_factory=list,
        description="Dependency chain connecting test file to source file, if graph-backed"
    )
    reason: str = Field(
        default="",
        description="Human-readable explanation of why this test file was identified"
    )

    model_config = ConfigDict(extra="allow")


class TestImpactSummary(BaseModel):
    """Summary metrics of test candidates for a single finding."""
    __test__ = False
    direct_test_count: int = Field(default=0, ge=0, description="Count of directly importing test files")
    heuristic_test_count: int = Field(default=0, ge=0, description="Count of heuristically matched test files")
    unknown_test_count: int = Field(default=0, ge=0, description="Count of tests with unestablished relationships")


class FindingTestImpact(BaseModel):
    """Test impact payload associated with an individual finding."""
    status: str = Field(
        default="success",
        description="Execution status: 'success', 'partial', 'unavailable'"
    )
    mapping_complete: bool = Field(
        default=True,
        description="Whether the test mapping was executed against a complete graph and file inventory"
    )
    candidate_tests: list[TestCandidate] = Field(
        default_factory=list,
        description="List of candidate test files potentially related to the flagged code"
    )
    summary: TestImpactSummary = Field(
        default_factory=TestImpactSummary,
        description="Summary counts of candidate tests"
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Transparent notes regarding limits, heuristics, or lack of coverage claim"
    )

    model_config = ConfigDict(extra="allow")


class FrameworkEvidence(BaseModel):
    """Evidence supporting a detected test framework in the repository."""
    name: str = Field(description="Detected testing framework name (e.g. 'jest', 'vitest', 'pytest')")
    confidence: str = Field(default="high", description="Detection confidence: 'high', 'medium', 'low'")
    evidence: list[str] = Field(default_factory=list, description="Static files or package entries observed")

    model_config = ConfigDict(extra="allow")


class EntryPointEvidence(BaseModel):
    """Evidence identifying a potential application or module entry point."""
    file_path: str = Field(description="Repository-relative POSIX path of candidate entry point")
    entry_point_status: str = Field(
        default="found",
        description="Status: 'found', 'not_found', 'unknown', 'not_checked'"
    )
    entry_point_type: str = Field(
        default="application_entry",
        description="Entry type: 'application_entry', 'package_main', 'script_entry', 'cli_bin'"
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Static evidence supporting this entry point identification"
    )

    model_config = ConfigDict(extra="allow")


class TestImpactAnalysisResult(BaseModel):
    """Top-level response envelope for Phase 5 Potential Test Impact Mapping."""
    __test__ = False
    analysis_id: str
    status: str = Field(default="success")
    detected_frameworks: list[FrameworkEvidence] = Field(default_factory=list)
    entry_points: list[EntryPointEvidence] = Field(default_factory=list)
    enriched_findings: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

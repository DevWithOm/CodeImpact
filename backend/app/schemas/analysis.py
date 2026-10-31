"""Analysis and tool coverage schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.finding import Finding

ToolStatus = Literal["completed", "partial", "failed", "skipped"]


class ToolCoverageItem(BaseModel):
    status: ToolStatus = Field(..., description="Status of the tool execution")
    finding_count: int = Field(default=0, description="Total findings identified by this tool")
    message: str | None = Field(default=None, description="Optional diagnostic or error message")

    model_config = ConfigDict(extra="allow")


class ToolCoverage(BaseModel):
    knip: ToolCoverageItem
    jscpd: ToolCoverageItem

    model_config = ConfigDict(extra="allow")


class AnalysisResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    tool_coverage: dict[str, ToolCoverageItem] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class AnalysisStage(str, Enum):
    QUEUED = "queued"
    CLONING = "cloning"
    STATIC_ANALYSIS = "static_analysis"
    DEPENDENCY_GRAPH = "dependency_graph"
    RISK_SCORING = "risk_scoring"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_url: str = Field(
        ...,
        description="Public Git repository HTTP/HTTPS URL",
        examples=["https://github.com/owner/repository"],
    )
    branch: str = Field(
        default="main",
        description="Repository branch name to analyze",
        examples=["main"],
    )

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("repository_url must not be empty.")

        # Reject local filesystem patterns
        if trimmed.startswith(("file://", "/", "\\")) or re.match(r"^[a-zA-Z]:[\\/]", trimmed):
            raise ValueError("Local filesystem paths are not accepted. Provide an HTTP or HTTPS Git repository URL.")

        # If user passed "owner/repo" shorthand (e.g. facebook/react), normalize to "https://github.com/owner/repo"
        if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", trimmed):
            trimmed = f"https://github.com/{trimmed}"

        try:
            parsed = urlparse(trimmed)
        except Exception as exc:
            raise ValueError(f"Malformed repository URL: {exc}") from exc

        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("Unsupported URL scheme. Only HTTP and HTTPS repository URLs are supported.")

        if not parsed.netloc:
            raise ValueError("Invalid repository URL: host/domain is missing.")

        # Ensure path contains at least owner/repo
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) < 2:
            raise ValueError("Repository URL must specify both owner and repository name (e.g. https://github.com/owner/repo).")

        return trimmed

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            return "main"
        # Disallow control characters or whitespaces in git branch names
        if re.search(r"[\s\x00-\x1f\x7f~^:?*\[\\]", trimmed):
            raise ValueError(f"Invalid branch name '{trimmed}'. Branch names must not contain spaces or control characters.")
        return trimmed

    def get_repository_identifier(self) -> str:
        parsed = urlparse(self.repository_url)
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return path


class AnalysisCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    analysis_id: str
    status: AnalysisStatus = AnalysisStatus.QUEUED
    repository: str
    branch: str


class AnalysisMetrics(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_findings: int = Field(default=0, ge=0)
    higher_risk: int = Field(default=0, ge=0)
    medium_risk: int = Field(default=0, ge=0)
    lower_risk: int = Field(default=0, ge=0)
    unknown_risk: int = Field(default=0, ge=0)
    circular_dependencies: int = Field(default=0, ge=0)
    duplicate_groups: int = Field(default=0, ge=0)
    test_candidates: int = Field(default=0, ge=0)


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    analysis_id: str
    repository: str
    repository_url: str | None = None
    branch: str
    commit_sha: str | None = None
    status: AnalysisStatus
    current_stage: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    metrics: AnalysisMetrics = Field(default_factory=AnalysisMetrics)
    tool_coverage: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


__all__ = [
    "ToolStatus",
    "ToolCoverageItem",
    "ToolCoverage",
    "AnalysisResult",
    "AnalysisStatus",
    "AnalysisStage",
    "AnalysisRequest",
    "AnalysisCreatedResponse",
    "AnalysisMetrics",
    "AnalysisStatusResponse",
]

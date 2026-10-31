"""Analysis and tool coverage schemas."""

from typing import Literal
from pydantic import BaseModel, Field

from backend.app.schemas.finding import Finding


ToolStatus = Literal["completed", "partial", "failed", "skipped"]


class ToolCoverageItem(BaseModel):
    status: ToolStatus = Field(..., description="Status of the tool execution")
    finding_count: int = Field(default=0, description="Total findings identified by this tool")
    message: str | None = Field(default=None, description="Optional diagnostic or error message")


class ToolCoverage(BaseModel):
    knip: ToolCoverageItem
    jscpd: ToolCoverageItem


class AnalysisResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    tool_coverage: dict[str, ToolCoverageItem] = Field(default_factory=dict)

from pydantic import BaseModel, ConfigDict, Field


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(..., description="ID of the finding to generate explanation for", examples=["f_001"])
    prompt: str | None = Field(default=None, description="Optional custom prompt or user query for contextual AI explanation")


class ExplainResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str = Field(..., description="Evidence-grounded explanation of the finding")
    why_it_matters: str = Field(..., description="Impact and maintenance importance")
    false_positive_scenarios: list[str] = Field(default_factory=list, description="Scenarios where code is actually used")
    verification_steps: list[str] = Field(default_factory=list, description="Concrete validation steps")
    suggested_action: str = Field(..., description="Recommended safe action")
    limitations: list[str] = Field(default_factory=list, description="Static analysis blind spots")

from pydantic import BaseModel, ConfigDict, Field


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique node ID, typically repository-relative POSIX file path")
    label: str = Field(..., description="Display label (e.g. filename basename)")
    file_path: str = Field(..., description="Full repository-relative file path")
    finding_count: int = Field(default=0, ge=0, description="Number of findings associated with this file")
    cycle_member: bool = Field(default=False, description="Whether node is part of a circular dependency")


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Edge identifier, e.g. source->target")
    source: str = Field(..., description="Source node ID (importer)")
    target: str = Field(..., description="Target node ID (imported module)")
    relationship: str = Field(default="imports", description="Relationship type")


class GraphStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    cycle_count: int = Field(default=0, ge=0)


class GraphResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    cycles: list[list[str]] = Field(default_factory=list)
    stats: GraphStats = Field(default_factory=GraphStats)
    truncated: bool = False

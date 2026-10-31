"""Pydantic schemas for CodeImpact Dependency Graph."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Represents a source file node in the dependency graph."""
    id: str = Field(description="Unique repository-relative file path")
    label: str = Field(description="Display filename (basename)")
    file_path: str = Field(description="Repository-relative POSIX file path")
    finding_count: int = Field(default=0, ge=0, description="Count of static analysis findings on this file")
    cycle_member: bool = Field(default=False, description="Whether node participates in a circular dependency")
    in_degree: int = Field(default=0, ge=0, description="Number of direct importers (dependants)")
    out_degree: int = Field(default=0, ge=0, description="Number of direct imports (dependencies)")


class GraphEdge(BaseModel):
    """Represents a directed import edge (source imports target)."""
    id: str = Field(description="Unique edge identifier, formatted as 'source->target'")
    source: str = Field(description="Repository-relative path of importing module")
    target: str = Field(description="Repository-relative path of imported module")
    relationship: str = Field(default="imports", description="Canonical edge relationship")


class GraphStats(BaseModel):
    """Summary metrics of the complete and returned graph."""
    node_count: int = Field(ge=0, description="Total nodes in the complete graph")
    edge_count: int = Field(ge=0, description="Total directed edges in the complete graph")
    cycle_count: int = Field(ge=0, description="Total unique detected cycles")
    original_node_count: int = Field(ge=0, description="Total nodes prior to visualization truncation")
    original_edge_count: int = Field(ge=0, description="Total edges prior to visualization truncation")
    returned_node_count: int = Field(ge=0, description="Number of nodes returned in payload")
    returned_edge_count: int = Field(ge=0, description="Number of edges returned in payload")


class GraphData(BaseModel):
    """Complete graph payload consumed by frontend React Flow visualization."""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    cycles: list[list[str]] = Field(default_factory=list)
    stats: GraphStats
    truncated: bool = Field(default=False)


class DependencyGraphResponse(BaseModel):
    """Top-level response envelope for dependency graph analysis."""
    analysis_id: str
    status: str = Field(default="success", description="Overall execution status: 'success', 'partial', 'unavailable'")
    graph: GraphData
    enriched_findings: list[dict[str, Any]] = Field(default_factory=list)


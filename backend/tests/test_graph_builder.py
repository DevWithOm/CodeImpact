"""Comprehensive unit and integration tests for CodeImpact Graph Builder.

Includes:
- Directed node and edge construction
- In-degree and out-degree invariants
- Self-loop dependency handling (Option A)
- Strict graph integrity validation checks
- Deterministic bounded visualization truncation
- Real Madge fixture integration
"""

from __future__ import annotations

from pathlib import Path
import pytest

from backend.app.schemas.graph import DependencyGraphResponse, GraphData
from backend.app.services.dependency_impact.graph_builder import (
    build_dependency_graph,
    create_graph_response,
    extract_finding_counts_by_file,
    validate_graph_integrity,
)
from backend.app.services.dependency_impact.madge_runner import run_madge

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "dependency_fixture"


def test_empty_dependency_map():
    """An empty dependency map produces an empty graph with valid statistics."""
    graph = build_dependency_graph({})
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["cycles"] == []
    assert graph["truncated"] is False
    assert graph["stats"]["node_count"] == 0
    assert graph["stats"]["edge_count"] == 0
    assert graph["stats"]["cycle_count"] == 0
    assert graph["stats"]["returned_node_count"] == 0
    assert graph["stats"]["returned_edge_count"] == 0

    is_valid, errors = validate_graph_integrity(graph)
    assert is_valid is True
    assert errors == []


def test_basic_node_and_edge_construction():
    """Verify directed edge creation, labels, and degree calculation."""
    dep_map = {
        "src/main.ts": ["src/app.ts"],
        "src/app.ts": ["src/utils.ts"],
        "src/utils.ts": [],
    }
    graph = build_dependency_graph(dep_map)

    # 3 nodes: app.ts, main.ts, utils.ts (sorted alphabetically)
    nodes = graph["nodes"]
    assert len(nodes) == 3
    node_by_id = {n["id"]: n for n in nodes}

    assert "src/main.ts" in node_by_id
    assert node_by_id["src/main.ts"]["label"] == "main.ts"
    assert node_by_id["src/main.ts"]["in_degree"] == 0
    assert node_by_id["src/main.ts"]["out_degree"] == 1

    assert "src/app.ts" in node_by_id
    assert node_by_id["src/app.ts"]["label"] == "app.ts"
    assert node_by_id["src/app.ts"]["in_degree"] == 1  # imported by main.ts
    assert node_by_id["src/app.ts"]["out_degree"] == 1  # imports utils.ts

    assert "src/utils.ts" in node_by_id
    assert node_by_id["src/utils.ts"]["label"] == "utils.ts"
    assert node_by_id["src/utils.ts"]["in_degree"] == 1  # imported by app.ts
    assert node_by_id["src/utils.ts"]["out_degree"] == 0  # leaf

    # Edges: source imports target
    edges = graph["edges"]
    assert len(edges) == 2
    assert edges[0] == {
        "id": "src/app.ts->src/utils.ts",
        "source": "src/app.ts",
        "target": "src/utils.ts",
        "relationship": "imports",
    }
    assert edges[1] == {
        "id": "src/main.ts->src/app.ts",
        "source": "src/main.ts",
        "target": "src/app.ts",
        "relationship": "imports",
    }

    # Degree identity check
    sum_in = sum(n["in_degree"] for n in nodes)
    sum_out = sum(n["out_degree"] for n in nodes)
    assert sum_in == len(edges) == 2
    assert sum_out == len(edges) == 2


def test_target_missing_as_map_key_is_included():
    """A module referenced as an import must be created as a node even if not a key."""
    dep_map = {
        "src/main.ts": ["src/external_module.ts"]
    }
    graph = build_dependency_graph(dep_map)
    node_ids = [n["id"] for n in graph["nodes"]]
    assert "src/main.ts" in node_ids
    assert "src/external_module.ts" in node_ids
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1


def test_path_normalization_and_traversal_rejection():
    """Windows backslashes are normalized and directory traversal is rejected."""
    dep_map = {
        "src\\controllers\\user.ts": [".\\src\\models\\user.ts", "src/../escaped.ts"]
    }
    graph = build_dependency_graph(dep_map)
    node_ids = [n["id"] for n in graph["nodes"]]
    assert "src/controllers/user.ts" in node_ids
    assert "src/models/user.ts" in node_ids
    assert "src/../escaped.ts" not in node_ids


def test_duplicate_dependencies_deduplicated():
    """Duplicate dependencies in list create only one unique directed edge."""
    dep_map = {
        "src/main.ts": ["src/app.ts", "src/app.ts", "./src/app.ts"]
    }
    graph = build_dependency_graph(dep_map)
    assert len(graph["edges"]) == 1
    assert graph["stats"]["edge_count"] == 1
    assert graph["nodes"][1]["out_degree"] == 1  # src/main.ts
    assert graph["nodes"][0]["in_degree"] == 1   # src/app.ts


def test_finding_counts_associated_with_nodes():
    """Finding counts from input findings are attached to the matching node."""
    dep_map = {
        "src/a.ts": ["src/b.ts"]
    }
    findings = [
        {"file_path": "src/a.ts", "category": "unused_export"},
        {"file_path": "src/a.ts", "category": "duplicate_code"},
        {"file_path": ".\\src\\b.ts", "category": "unused_file"},
    ]
    graph = build_dependency_graph(dep_map, findings=findings)
    node_map = {n["id"]: n for n in graph["nodes"]}
    assert node_map["src/a.ts"]["finding_count"] == 2
    assert node_map["src/b.ts"]["finding_count"] == 1


def test_cycle_members_flagged_in_nodes():
    """Nodes participating in circular dependencies have cycle_member=True."""
    dep_map = {
        "src/a.ts": ["src/b.ts"],
        "src/b.ts": ["src/a.ts"],
        "src/clean.ts": [],
    }
    cycles = [["src/a.ts", "src/b.ts"]]
    graph = build_dependency_graph(dep_map, cycles=cycles)

    node_map = {n["id"]: n for n in graph["nodes"]}
    assert node_map["src/a.ts"]["cycle_member"] is True
    assert node_map["src/b.ts"]["cycle_member"] is True
    assert node_map["src/clean.ts"]["cycle_member"] is False
    assert len(graph["cycles"]) == 1
    assert graph["stats"]["cycle_count"] == 1


# ==============================================================================
# SELF-LOOP TESTS (OPTION A)
# ==============================================================================

def test_self_loop_single_node():
    """A self-referencing module creates a valid self-loop edge and increments both degrees."""
    dep_map = {
        "src/recursive.ts": ["src/recursive.ts"]
    }
    graph = build_dependency_graph(dep_map)
    assert len(graph["nodes"]) == 1
    node = graph["nodes"][0]
    assert node["id"] == "src/recursive.ts"
    assert node["in_degree"] == 1
    assert node["out_degree"] == 1

    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert edge["id"] == "src/recursive.ts->src/recursive.ts"
    assert edge["source"] == "src/recursive.ts"
    assert edge["target"] == "src/recursive.ts"
    assert edge["relationship"] == "imports"

    assert graph["stats"]["edge_count"] == 1
    assert graph["stats"]["node_count"] == 1

    # Degree identity check
    assert sum(n["in_degree"] for n in graph["nodes"]) == 1
    assert sum(n["out_degree"] for n in graph["nodes"]) == 1

    is_valid, errors = validate_graph_integrity(graph)
    assert is_valid is True
    assert errors == []


def test_self_loop_with_other_edges():
    """A self-loop alongside standard edges counts accurately in degrees and statistics."""
    dep_map = {
        "src/a.ts": ["src/a.ts", "src/b.ts"],
        "src/b.ts": [],
    }
    graph = build_dependency_graph(dep_map)
    node_map = {n["id"]: n for n in graph["nodes"]}

    assert node_map["src/a.ts"]["out_degree"] == 2  # imports a.ts and b.ts
    assert node_map["src/a.ts"]["in_degree"] == 1   # imported by a.ts
    assert node_map["src/b.ts"]["in_degree"] == 1   # imported by a.ts
    assert node_map["src/b.ts"]["out_degree"] == 0

    assert len(graph["edges"]) == 2
    edge_ids = [e["id"] for e in graph["edges"]]
    assert "src/a.ts->src/a.ts" in edge_ids
    assert "src/a.ts->src/b.ts" in edge_ids

    is_valid, errors = validate_graph_integrity(graph)
    assert is_valid is True
    assert errors == []


def test_self_loop_duplicate_handling():
    """Duplicate self-loops in dependency list are deduplicated without inflating degrees."""
    dep_map = {
        "src/a.ts": ["src/a.ts", "./src/a.ts", "src/a.ts"]
    }
    graph = build_dependency_graph(dep_map)
    assert len(graph["edges"]) == 1
    assert graph["nodes"][0]["in_degree"] == 1
    assert graph["nodes"][0]["out_degree"] == 1


def test_self_loop_and_multi_node_cycle():
    """Graph with both a self-loop and a multi-node cycle maintains distinct invariant checks."""
    dep_map = {
        "src/self.ts": ["src/self.ts"],
        "src/c1.ts": ["src/c2.ts"],
        "src/c2.ts": ["src/c1.ts"],
    }
    cycles = [["src/c1.ts", "src/c2.ts"]]
    graph = build_dependency_graph(dep_map, cycles=cycles)

    node_map = {n["id"]: n for n in graph["nodes"]}
    assert node_map["src/self.ts"]["cycle_member"] is False  # self-loop is not a cycle
    assert node_map["src/c1.ts"]["cycle_member"] is True
    assert node_map["src/c2.ts"]["cycle_member"] is True

    assert len(graph["edges"]) == 3
    is_valid, errors = validate_graph_integrity(graph)
    assert is_valid is True
    assert errors == []


# ==============================================================================
# GRAPH INTEGRITY VALIDATOR INVARIANT TESTS
# ==============================================================================

def test_validate_integrity_duplicate_node_ids():
    """Validator detects and rejects duplicate node IDs."""
    malformed_graph = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 0, "finding_count": 0, "cycle_member": False},
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 0, "finding_count": 0, "cycle_member": False},
        ],
        "edges": [],
        "cycles": [],
        "stats": {"returned_node_count": 2, "returned_edge_count": 0, "cycle_count": 0, "original_node_count": 2, "original_edge_count": 0},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(malformed_graph)
    assert is_valid is False
    assert any("Duplicate node ID detected" in e for e in errors)


def test_validate_integrity_duplicate_edge_ids():
    """Validator detects and rejects duplicate edge IDs."""
    malformed_graph = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 1, "finding_count": 0, "cycle_member": False},
            {"id": "src/b.ts", "file_path": "src/b.ts", "label": "b.ts", "in_degree": 1, "out_degree": 0, "finding_count": 0, "cycle_member": False},
        ],
        "edges": [
            {"id": "src/a.ts->src/b.ts", "source": "src/a.ts", "target": "src/b.ts", "relationship": "imports"},
            {"id": "src/a.ts->src/b.ts", "source": "src/a.ts", "target": "src/b.ts", "relationship": "imports"},
        ],
        "cycles": [],
        "stats": {"returned_node_count": 2, "returned_edge_count": 2, "cycle_count": 0, "original_node_count": 2, "original_edge_count": 2},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(malformed_graph)
    assert is_valid is False
    assert any("Duplicate edge ID detected" in e for e in errors)


def test_validate_integrity_incorrect_edge_id_format():
    """Validator detects and rejects edge IDs that do not match 'source->target'."""
    malformed_graph = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 1, "finding_count": 0, "cycle_member": False},
            {"id": "src/b.ts", "file_path": "src/b.ts", "label": "b.ts", "in_degree": 1, "out_degree": 0, "finding_count": 0, "cycle_member": False},
        ],
        "edges": [
            {"id": "custom_edge_123", "source": "src/a.ts", "target": "src/b.ts", "relationship": "imports"},
        ],
        "cycles": [],
        "stats": {"returned_node_count": 2, "returned_edge_count": 1, "cycle_count": 0, "original_node_count": 2, "original_edge_count": 1},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(malformed_graph)
    assert is_valid is False
    assert any("does not match expected canonical format" in e for e in errors)


def test_validate_integrity_missing_edge_endpoints():
    """Validator detects dangling edges where source or target is absent from nodes."""
    malformed_graph = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 1, "finding_count": 0, "cycle_member": False},
        ],
        "edges": [
            {"id": "src/a.ts->src/missing.ts", "source": "src/a.ts", "target": "src/missing.ts", "relationship": "imports"},
        ],
        "cycles": [],
        "stats": {"returned_node_count": 1, "returned_edge_count": 1, "cycle_count": 0, "original_node_count": 1, "original_edge_count": 1},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(malformed_graph)
    assert is_valid is False
    assert any("Dangling edge" in e for e in errors)


def test_validate_integrity_degree_sum_mismatch():
    """Validator fails if degree sums on an untruncated graph do not equal edge count."""
    malformed_graph = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 5, "out_degree": 1, "finding_count": 0, "cycle_member": False},
            {"id": "src/b.ts", "file_path": "src/b.ts", "label": "b.ts", "in_degree": 1, "out_degree": 0, "finding_count": 0, "cycle_member": False},
        ],
        "edges": [
            {"id": "src/a.ts->src/b.ts", "source": "src/a.ts", "target": "src/b.ts", "relationship": "imports"},
        ],
        "cycles": [],
        "stats": {"returned_node_count": 2, "returned_edge_count": 1, "cycle_count": 0, "original_node_count": 2, "original_edge_count": 1},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(malformed_graph)
    assert is_valid is False
    assert any("Degree sum mismatch" in e for e in errors)


def test_validate_integrity_cycle_member_consistency():
    """Validator catches discrepancies between cycle_member flags and cycles metadata."""
    # Case A: Marked True but missing from cycles metadata
    bad_graph_a = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 0, "finding_count": 0, "cycle_member": True},
        ],
        "edges": [],
        "cycles": [],
        "stats": {"returned_node_count": 1, "returned_edge_count": 0, "cycle_count": 0, "original_node_count": 1, "original_edge_count": 0},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(bad_graph_a)
    assert is_valid is False
    assert any("marked cycle_member=True but does not appear in cycles metadata" in e for e in errors)

    # Case B: In cycle metadata but marked cycle_member=False
    bad_graph_b = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 1, "out_degree": 1, "finding_count": 0, "cycle_member": False},
            {"id": "src/b.ts", "file_path": "src/b.ts", "label": "b.ts", "in_degree": 1, "out_degree": 1, "finding_count": 0, "cycle_member": True},
        ],
        "edges": [
            {"id": "src/a.ts->src/b.ts", "source": "src/a.ts", "target": "src/b.ts", "relationship": "imports"},
            {"id": "src/b.ts->src/a.ts", "source": "src/b.ts", "target": "src/a.ts", "relationship": "imports"},
        ],
        "cycles": [["src/a.ts", "src/b.ts"]],
        "stats": {"returned_node_count": 2, "returned_edge_count": 2, "cycle_count": 1, "original_node_count": 2, "original_edge_count": 2},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(bad_graph_b)
    assert is_valid is False
    assert any("appears in cycles metadata but has cycle_member=False" in e for e in errors)


def test_validate_integrity_cycle_references_missing_node():
    """In an untruncated graph, cycle metadata referencing an unknown file fails validation."""
    malformed_graph = {
        "nodes": [
            {"id": "src/a.ts", "file_path": "src/a.ts", "label": "a.ts", "in_degree": 0, "out_degree": 0, "finding_count": 0, "cycle_member": True},
        ],
        "edges": [],
        "cycles": [["src/a.ts", "src/ghost.ts"]],
        "stats": {"returned_node_count": 1, "returned_edge_count": 0, "cycle_count": 1, "original_node_count": 1, "original_edge_count": 0},
        "truncated": False,
    }
    is_valid, errors = validate_graph_integrity(malformed_graph)
    assert is_valid is False
    assert any("absent from graph nodes" in e for e in errors)


def test_validate_integrity_disconnected_components():
    """A valid graph with multiple disconnected components passes integrity checks."""
    dep_map = {
        "src/comp1_a.ts": ["src/comp1_b.ts"],
        "src/comp1_b.ts": [],
        "src/comp2_x.ts": ["src/comp2_y.ts"],
        "src/comp2_y.ts": [],
    }
    graph = build_dependency_graph(dep_map)
    is_valid, errors = validate_graph_integrity(graph)
    assert is_valid is True
    assert errors == []
    assert len(graph["nodes"]) == 4
    assert len(graph["edges"]) == 2


# ==============================================================================
# TRUNCATION & INTEGRATION TESTS
# ==============================================================================

def test_truncation_when_max_nodes_exceeded():
    """When node count exceeds max_nodes, nodes are prioritized deterministically without dangling edges."""
    dep_map = {
        "src/a.ts": ["src/b.ts"],
        "src/b.ts": ["src/c.ts"],
        "src/c.ts": ["src/d.ts"],
        "src/d.ts": [],
    }
    findings = [{"file_path": "src/d.ts"}]
    cycles = [["src/b.ts", "src/c.ts"]]

    graph = build_dependency_graph(
        dep_map,
        cycles=cycles,
        findings=findings,
        max_nodes=2,
        max_edges=10,
    )

    assert graph["truncated"] is True
    assert graph["stats"]["original_node_count"] == 4
    assert graph["stats"]["returned_node_count"] == 2
    assert len(graph["nodes"]) == 2

    returned_ids = {n["id"] for n in graph["nodes"]}
    assert "src/d.ts" in returned_ids
    assert ("src/b.ts" in returned_ids or "src/c.ts" in returned_ids)

    # Invariant: No dangling edges!
    for edge in graph["edges"]:
        assert edge["source"] in returned_ids
        assert edge["target"] in returned_ids

    # Invariant: Complete cycles preserved in metadata
    assert len(graph["cycles"]) == 1
    assert graph["cycles"][0] == ["src/b.ts", "src/c.ts"]

    # Invariant: Node degrees retain full-graph values
    node_map = {n["id"]: n for n in graph["nodes"]}
    if "src/d.ts" in node_map:
        assert node_map["src/d.ts"]["in_degree"] == 1


def test_truncation_when_max_edges_exceeded():
    """When edge count exceeds max_edges, edges are bounded without violating node presence."""
    dep_map = {
        "src/hub.ts": ["src/a.ts", "src/b.ts", "src/c.ts"]
    }
    graph = build_dependency_graph(
        dep_map,
        max_nodes=10,
        max_edges=2,
    )
    assert graph["truncated"] is True
    assert graph["stats"]["original_edge_count"] == 3
    assert graph["stats"]["returned_edge_count"] == 2
    assert len(graph["edges"]) == 2

    is_valid, errors = validate_graph_integrity(graph)
    assert is_valid is True
    assert errors == []


def test_deterministic_sorting():
    """Repeated construction on unsorted dictionaries yields identical output."""
    dep_map_1 = {
        "src/z.ts": ["src/a.ts"],
        "src/a.ts": ["src/m.ts"],
        "src/m.ts": [],
    }
    dep_map_2 = {
        "src/m.ts": [],
        "src/a.ts": ["src/m.ts"],
        "src/z.ts": ["src/a.ts"],
    }
    g1 = build_dependency_graph(dep_map_1)
    g2 = build_dependency_graph(dep_map_2)
    assert g1 == g2


def test_create_graph_response_schema_validation():
    """Verify create_graph_response adheres to Pydantic DependencyGraphResponse."""
    dep_map = {"src/main.ts": ["src/app.ts"]}
    graph = build_dependency_graph(dep_map)
    response_dict = create_graph_response("analysis_demo", graph, enriched_findings=[])

    validated = DependencyGraphResponse(**response_dict)
    assert validated.analysis_id == "analysis_demo"
    assert len(validated.graph.nodes) == 2
    assert len(validated.graph.edges) == 1
    assert validated.graph.stats.original_node_count == 2


def test_real_madge_fixture_integration():
    """End-to-end integration: Madge runner output fed directly into graph builder."""
    assert FIXTURE_PATH.exists()

    madge_result = run_madge(str(FIXTURE_PATH))
    assert madge_result["status"] == "success"

    dep_map = madge_result["dependency_map"]
    cycles = madge_result["cycles"]

    graph = build_dependency_graph(dep_map, cycles=cycles)

    # Verify nodes
    node_ids = {n["id"] for n in graph["nodes"]}
    expected_nodes = {
        "src/app.ts",
        "src/main.ts",
        "src/services/auth.ts",
        "src/services/user.ts",
        "src/utils.ts",
        "tests/app.test.ts",
    }
    assert node_ids == expected_nodes
    assert len(graph["nodes"]) == 6

    # Verify edges
    edge_ids = {e["id"] for e in graph["edges"]}
    expected_edges = {
        "src/app.ts->src/utils.ts",
        "src/main.ts->src/app.ts",
        "src/services/auth.ts->src/services/user.ts",
        "src/services/user.ts->src/services/auth.ts",
        "tests/app.test.ts->src/app.ts",
    }
    assert edge_ids == expected_edges
    assert len(graph["edges"]) == 5

    # Verify cycle detection in graph
    node_map = {n["id"]: n for n in graph["nodes"]}
    assert node_map["src/services/auth.ts"]["cycle_member"] is True
    assert node_map["src/services/user.ts"]["cycle_member"] is True
    assert node_map["src/main.ts"]["cycle_member"] is False
    assert len(graph["cycles"]) == 1

    # Verify degree integrity
    sum_in = sum(n["in_degree"] for n in graph["nodes"])
    sum_out = sum(n["out_degree"] for n in graph["nodes"])
    assert sum_in == len(graph["edges"]) == 5
    assert sum_out == len(graph["edges"]) == 5

    # Verify statistics
    stats = graph["stats"]
    assert stats["node_count"] == 6
    assert stats["edge_count"] == 5
    assert stats["cycle_count"] == 1
    assert stats["original_node_count"] == 6
    assert stats["original_edge_count"] == 5
    assert stats["returned_node_count"] == 6
    assert stats["returned_edge_count"] == 5
    assert graph["truncated"] is False

    # Verify Pydantic validation
    pydantic_obj = GraphData(**graph)
    assert pydantic_obj.stats.node_count == 6

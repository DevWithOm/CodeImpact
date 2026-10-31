"""Unit and integration tests for finding-level impact analysis."""

from pathlib import Path
import pytest

from backend.app.schemas.impact import EnrichedFinding
from backend.app.services.dependency_impact.impact_analyzer import (
    EVIDENCE_TYPE_STATIC_IMPORT,
    IMPACT_STATUS_PARTIAL,
    IMPACT_STATUS_SUCCESS,
    IMPACT_STATUS_UNAVAILABLE,
    analyze_impact,
    build_graph_indexes,
    extract_direct_dependants,
    extract_direct_dependencies,
)


@pytest.fixture
def sample_graph():
    """Returns a deterministic sample graph matching the canonical contract."""
    return {
        "nodes": [
            {"id": "src/main.ts", "file_path": "src/main.ts", "label": "main.ts"},
            {"id": "src/app.ts", "file_path": "src/app.ts", "label": "app.ts"},
            {"id": "src/utils.ts", "file_path": "src/utils.ts", "label": "utils.ts"},
            {"id": "src/admin.ts", "file_path": "src/admin.ts", "label": "admin.ts"},
            {"id": "src/auth.ts", "file_path": "src/auth.ts", "label": "auth.ts", "cycle_member": True},
            {"id": "src/user.ts", "file_path": "src/user.ts", "label": "user.ts", "cycle_member": True},
            {"id": "src/standalone.ts", "file_path": "src/standalone.ts", "label": "standalone.ts"},
        ],
        "edges": [
            {"id": "src/main.ts->src/app.ts", "source": "src/main.ts", "target": "src/app.ts", "relationship": "imports"},
            {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts", "relationship": "imports"},
            {"id": "src/admin.ts->src/utils.ts", "source": "src/admin.ts", "target": "src/utils.ts", "relationship": "imports"},
            {"id": "src/auth.ts->src/user.ts", "source": "src/auth.ts", "target": "src/user.ts", "relationship": "imports"},
            {"id": "src/user.ts->src/auth.ts", "source": "src/user.ts", "target": "src/auth.ts", "relationship": "imports"},
        ],
        "cycles": [
            ["src/auth.ts", "src/user.ts"]
        ],
        "stats": {
            "node_count": 7,
            "edge_count": 5,
            "cycle_count": 1,
            "original_node_count": 7,
            "original_edge_count": 5,
            "returned_node_count": 7,
            "returned_edge_count": 5,
        },
        "truncated": False,
    }


def test_build_graph_indexes():
    edges = [
        {"id": "A->B", "source": "A", "target": "B", "relationship": "imports"},
        {"id": "B->C", "source": "B", "target": "C", "relationship": "imports"},
    ]
    incoming, outgoing = build_graph_indexes(edges)

    assert "B" in incoming
    assert len(incoming["B"]) == 1
    assert incoming["B"][0]["source"] == "A"

    assert "A" in outgoing
    assert len(outgoing["A"]) == 1
    assert outgoing["A"][0]["target"] == "B"


def test_direct_dependants_multiple_importers():
    edges = [
        {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts", "relationship": "imports"},
        {"id": "src/admin.ts->src/utils.ts", "source": "src/admin.ts", "target": "src/utils.ts", "relationship": "imports"},
        {"id": "src/main.ts->src/app.ts", "source": "src/main.ts", "target": "src/app.ts", "relationship": "imports"},
    ]
    incoming, _ = build_graph_indexes(edges)

    dependants, self_loop = extract_direct_dependants("src/utils.ts", incoming)
    dep_paths = [d["file_path"] for d in dependants]

    # Exactly app.ts and admin.ts directly depend on utils.ts
    assert sorted(dep_paths) == ["src/admin.ts", "src/app.ts"]
    assert self_loop is False

    # CRITICAL: Transitive dependant main.ts MUST NOT be included
    assert "src/main.ts" not in dep_paths


def test_direct_dependants_root_importer_zero_dependants():
    edges = [
        {"id": "src/main.ts->src/app.ts", "source": "src/main.ts", "target": "src/app.ts", "relationship": "imports"}
    ]
    incoming, _ = build_graph_indexes(edges)

    dependants, self_loop = extract_direct_dependants("src/main.ts", incoming)
    assert len(dependants) == 0
    assert self_loop is False


def test_direct_dependencies_multiple_imports():
    edges = [
        {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts", "relationship": "imports"},
        {"id": "src/app.ts->src/auth.ts", "source": "src/app.ts", "target": "src/auth.ts", "relationship": "imports"},
    ]
    _, outgoing = build_graph_indexes(edges)

    dependencies, self_loop = extract_direct_dependencies("src/app.ts", outgoing)
    dep_paths = [d["file_path"] for d in dependencies]

    assert sorted(dep_paths) == ["src/auth.ts", "src/utils.ts"]
    assert self_loop is False


def test_self_loop_handling():
    # A imports A
    edges = [
        {"id": "src/a.ts->src/a.ts", "source": "src/a.ts", "target": "src/a.ts", "relationship": "imports"},
        {"id": "src/b.ts->src/a.ts", "source": "src/b.ts", "target": "src/a.ts", "relationship": "imports"},
    ]
    incoming, outgoing = build_graph_indexes(edges)

    dependants, self_dep_inc = extract_direct_dependants("src/a.ts", incoming)
    assert self_dep_inc is True
    # src/a.ts MUST NOT be in external dependants
    assert [d["file_path"] for d in dependants] == ["src/b.ts"]

    dependencies, self_dep_out = extract_direct_dependencies("src/a.ts", outgoing)
    assert self_dep_out is True
    assert len(dependencies) == 0


def test_evidence_traceability(sample_graph):
    findings = [
        {"finding_id": "FIND-001", "file_path": "src/utils.ts", "category": "unused_export"}
    ]
    result = analyze_impact(sample_graph, findings, analysis_id="test_01")
    enriched = result["enriched_findings"]

    assert len(enriched) == 1
    f = enriched[0]
    assert f["impact_status"] == IMPACT_STATUS_SUCCESS
    assert f["summary"]["direct_dependant_count"] == 2

    for dep in f["direct_dependants"]:
        ev = dep["evidence"]
        assert ev["evidence_type"] == EVIDENCE_TYPE_STATIC_IMPORT
        assert ev["relationship"] == "imports"
        assert ev["target"] == "src/utils.ts"
        assert ev["edge_id"] == f"{ev['source']}->src/utils.ts"


def test_cycle_context_propagation(sample_graph):
    findings = [
        {"finding_id": "FIND-AUTH", "file_path": "src/auth.ts", "category": "unused_file"}
    ]
    result = analyze_impact(sample_graph, findings, analysis_id="test_02")
    enriched = result["enriched_findings"][0]

    assert enriched["cycle_member"] is True
    assert len(enriched["cycles"]) == 1
    assert "src/auth.ts" in enriched["cycles"][0]
    assert "src/user.ts" in enriched["cycles"][0]
    # Direct dependants from cycle: src/user.ts imports src/auth.ts
    assert [d["file_path"] for d in enriched["direct_dependants"]] == ["src/user.ts"]


def test_unmapped_finding_handling(sample_graph):
    findings = [
        {"finding_id": "FIND-MISSING", "file_path": "src/missing.ts", "category": "unused_file"}
    ]
    result = analyze_impact(sample_graph, findings, analysis_id="test_03")
    enriched = result["enriched_findings"][0]

    assert enriched["mapping_status"] == "unmapped"
    assert enriched["impact_status"] == IMPACT_STATUS_PARTIAL
    assert enriched["summary"]["direct_dependant_count"] == 0
    assert "not present in the dependency graph" in enriched["impact_reason"]


def test_invalid_and_missing_paths(sample_graph):
    findings = [
        {"finding_id": "FIND-INV", "file_path": "C:\\Windows\\system32\\cmd.exe"},
        {"finding_id": "FIND-NONE", "file_path": None},
    ]
    result = analyze_impact(sample_graph, findings, analysis_id="test_04")
    enriched = result["enriched_findings"]

    assert enriched[0]["mapping_status"] == "invalid_path"
    assert enriched[0]["impact_status"] == IMPACT_STATUS_PARTIAL

    assert enriched[1]["mapping_status"] == "missing_file_path"
    assert enriched[1]["impact_status"] == IMPACT_STATUS_PARTIAL


def test_empty_graph_and_unavailable_status():
    findings = [{"finding_id": "FIND-01", "file_path": "src/app.ts"}]
    result = analyze_impact({}, findings, analysis_id="test_05")
    enriched = result["enriched_findings"][0]

    assert enriched["impact_status"] == IMPACT_STATUS_UNAVAILABLE


def test_empty_findings_list(sample_graph):
    result = analyze_impact(sample_graph, [], analysis_id="test_06")
    assert result["analysis_id"] == "test_06"
    assert result["enriched_findings"] == []


def test_synthetic_fixture_master_scenario(sample_graph):
    """Verifies the exact scenario described in Part 11.6 of the Phase 4 specification."""
    findings = [
        {
            "id": "FIND-001",
            "file_path": "src/utils.ts",
            "type": "unused_export",
            "symbol": "formatDate",
            "start_line": 12,
        },
        {
            "id": "FIND-002",
            "file_path": "src/app.ts",
            "type": "duplicate_code",
            "start_line": 50,
        },
        {
            "id": "FIND-003",
            "file_path": "src/missing.ts",
            "type": "unused_export",
        },
    ]

    result = analyze_impact(sample_graph, findings, analysis_id="master_scenario")
    enriched = result["enriched_findings"]
    assert len(enriched) == 3

    # FIND-001 (src/utils.ts)
    f1 = enriched[0]
    assert f1["finding_id"] == "FIND-001"
    assert f1["mapping_status"] == "mapped"
    assert f1["impact_status"] == IMPACT_STATUS_SUCCESS
    assert sorted([d["file_path"] for d in f1["direct_dependants"]]) == ["src/admin.ts", "src/app.ts"]
    assert "src/main.ts" not in [d["file_path"] for d in f1["direct_dependants"]]
    assert f1["symbol"] == "formatDate"
    assert f1["start_line"] == 12

    # FIND-002 (src/app.ts)
    f2 = enriched[1]
    assert f2["finding_id"] == "FIND-002"
    assert f2["mapping_status"] == "mapped"
    assert f2["impact_status"] == IMPACT_STATUS_SUCCESS
    assert [d["file_path"] for d in f2["direct_dependants"]] == ["src/main.ts"]
    assert [d["file_path"] for d in f2["direct_dependencies"]] == ["src/utils.ts"]
    assert f2["start_line"] == 50

    # FIND-003 (src/missing.ts)
    f3 = enriched[2]
    assert f3["finding_id"] == "FIND-003"
    assert f3["mapping_status"] == "unmapped"
    assert f3["impact_status"] == IMPACT_STATUS_PARTIAL
    assert f3["summary"]["direct_dependant_count"] == 0

    # Validate against Pydantic schema
    for ef in enriched:
        validated = EnrichedFinding(**ef)
        assert validated.finding_id is not None


def test_real_madge_fixture_integration():
    """Runs analyze_impact with repo_path against the real TS fixture created in Phase 2."""
    fixture_dir = Path("backend/tests/fixtures/dependency_fixture").resolve()
    assert fixture_dir.exists()

    findings = [
        {
            "finding_id": "f_utils",
            "file_path": "src/utils.ts",
            "category": "unused_export",
            "description": "Utility export not referenced.",
        },
        {
            "finding_id": "f_circular_auth",
            "file_path": "src/services/auth.ts",
            "category": "unused_file",
        },
    ]

    result = analyze_impact(str(fixture_dir), findings, analysis_id="fixture_run")
    assert result["analysis_id"] == "fixture_run"
    assert "graph" in result
    assert "nodes" in result["graph"]
    assert len(result["enriched_findings"]) == 2

    # src/utils.ts is imported by src/app.ts
    f_utils = result["enriched_findings"][0]
    assert f_utils["mapping_status"] == "mapped"
    assert f_utils["impact_status"] == IMPACT_STATUS_SUCCESS
    assert "src/app.ts" in [d["file_path"] for d in f_utils["direct_dependants"]]

    # src/services/auth.ts is in cycle with src/services/user.ts
    f_circ = result["enriched_findings"][1]
    assert f_circ["mapping_status"] == "mapped"
    assert f_circ["cycle_member"] is True
    assert len(f_circ["cycles"]) >= 1

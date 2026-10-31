import pytest
from pydantic import ValidationError

from app.schemas.ai import ExplainRequest, ExplainResponse
from app.schemas.analysis import AnalysisMetrics, AnalysisStatus
from app.schemas.evidence import EvidenceItem, FindingImpact
from app.schemas.finding import FindingDetail, FindingItem
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphStats


def test_analysis_status_enum_valid():
    assert AnalysisStatus("queued") == AnalysisStatus.QUEUED
    assert AnalysisStatus("running") == AnalysisStatus.RUNNING
    assert AnalysisStatus("completed") == AnalysisStatus.COMPLETED
    assert AnalysisStatus("partial") == AnalysisStatus.PARTIAL
    assert AnalysisStatus("failed") == AnalysisStatus.FAILED


def test_analysis_status_enum_invalid():
    with pytest.raises(ValueError):
        AnalysisStatus("unknown_status")


def test_analysis_metrics_non_negative():
    metrics = AnalysisMetrics(
        total_findings=5,
        higher_risk=1,
        medium_risk=2,
        lower_risk=1,
        unknown_risk=1,
        circular_dependencies=0,
        duplicate_groups=1,
        test_candidates=2,
    )
    assert metrics.total_findings == 5

    with pytest.raises(ValidationError):
        AnalysisMetrics(total_findings=-1)


def test_graph_response_schema():
    node = GraphNode(id="src/main.ts", label="main.ts", file_path="src/main.ts", finding_count=1)
    edge = GraphEdge(id="src/main.ts->src/app.ts", source="src/main.ts", target="src/app.ts", relationship="imports")
    stats = GraphStats(node_count=1, edge_count=1, cycle_count=0)

    graph = GraphResponse(
        analysis_id="an_test123",
        nodes=[node],
        edges=[edge],
        cycles=[],
        stats=stats,
        truncated=False,
    )
    assert graph.analysis_id == "an_test123"
    assert len(graph.nodes) == 1
    assert graph.edges[0].relationship == "imports"


def test_explain_response_schema():
    explanation = ExplainResponse(
        summary="No static reference found.",
        why_it_matters="Reduces code bloat.",
        false_positive_scenarios=["Dynamically imported"],
        verification_steps=["Check reflection usage"],
        suggested_action="Review before removing",
        limitations=["Static analysis only"],
    )
    assert explanation.summary == "No static reference found."
    assert len(explanation.false_positive_scenarios) == 1


def test_finding_item_schema_with_null_locations():
    evidence = EvidenceItem(
        kind="direct_reference",
        status="not_found",
        source="knip",
        details="No direct reference found by scanner.",
    )
    finding = FindingItem(
        finding_id="f_001",
        category="unused_file",
        title="Potentially unused file",
        file_path="src/unused.ts",
        start_line=None,
        end_line=None,
        symbol=None,
        source_tool="knip",
        description="File has no importers.",
        evidence_class="inconclusive",
        review_risk="medium",
        evidence=[evidence],
    )
    assert finding.finding_id == "f_001"
    assert finding.start_line is None
    assert finding.symbol is None

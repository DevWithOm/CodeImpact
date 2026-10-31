from datetime import datetime, timezone

from app.schemas.analysis import AnalysisMetrics, AnalysisRequest, AnalysisStatus
from app.schemas.evidence import EvidenceItem, FindingImpact, TestCandidate
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphNode, GraphResponse, GraphStats
from app.services.analysis_store import AnalysisRecord
from app.services.reports.report_generator import generate_markdown_report


def test_generate_markdown_report_full_structure():
    fixed_time = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)

    f1 = FindingItem(
        finding_id="f_rep_1",
        category="unused_export",
        title="Unused formatDate helper",
        file_path="src/utils/date.ts",
        start_line=10,
        end_line=20,
        symbol="formatDate",
        source_tool="knip",
        description="No static consumers in project",
        review_risk="higher",
        evidence=[
            EvidenceItem(
                kind="direct_reference",
                status="not_found",
                source="knip",
                details="Zero references found in workspace scan",
            )
        ],
        impact=FindingImpact(
            direct_dependants=["src/index.ts"],
            dependency_count=1,
            cycle_member=True,
            related_test_candidates=[
                TestCandidate(file_path="tests/date.test.ts", reason="Direct unit test", mapping_strength="direct")
            ],
            risk_factors=["Symbol participates in circular dependency"],
            review_risk="higher",
        ),
    )

    graph = GraphResponse(
        analysis_id="an_test_rep",
        nodes=[GraphNode(id="src/utils/date.ts", label="date.ts", file_path="src/utils/date.ts")],
        edges=[],
        cycles=[["src/utils/date.ts", "src/index.ts"]],
        stats=GraphStats(node_count=1, edge_count=0, cycle_count=1),
    )

    record = AnalysisRecord(
        analysis_id="an_test_rep",
        repository="owner/my-app",
        repository_url="https://github.com/owner/my-app",
        branch="main",
        commit_sha="commit12345",
        status=AnalysisStatus.COMPLETED,
        current_stage="completed",
        created_at=fixed_time,
        started_at=fixed_time,
        completed_at=fixed_time,
        metrics=AnalysisMetrics(
            total_findings=1,
            higher_risk=1,
            circular_dependencies=1,
            test_candidates=1,
        ),
        tool_coverage={"knip": "success", "madge": "success"},
        findings=[f1],
        graph=graph,
    )

    md = generate_markdown_report(record, generation_time=fixed_time)

    # 1. Title & Header
    assert "# CodeImpact Audit Report" in md
    assert "owner/my-app" in md
    assert "an_test_rep" in md

    # 2. Executive Summary
    assert "## 1. Executive Summary" in md
    assert "COMPLETED" in md
    assert "**Total Findings Flagged:** 1" in md
    assert "**Higher Review Risk:** 1" in md
    assert "**Circular Dependencies:** 1 cycles" in md

    # 3. Metadata
    assert "## 2. Analysis Metadata" in md
    assert "commit12345" in md
    assert "knip" in md

    # 4. Summary Metrics
    assert "## 3. Summary Metrics" in md

    # 5. Findings Breakdown
    assert "## 4. Findings Breakdown & Details" in md
    assert "Finding `f_rep_1`: Unused formatDate helper" in md
    assert "src/utils/date.ts" in md
    assert "tests/date.test.ts" in md
    assert "HIGHER" in md

    # 6. Dependency Graph & Cycles
    assert "## 5. Dependency Graph & Circular Dependencies" in md
    assert "`src/utils/date.ts` -> `src/index.ts` -> `src/utils/date.ts`" in md

    # 7. Verification Guidelines & Limitations
    assert "## 6. Pre-Cleanup Verification Guidelines & Limitations" in md
    assert "Pre-Cleanup Developer Checklist" in md
    assert "Analysis Limitations" in md


def test_generate_markdown_report_empty_findings_and_graph():
    fixed_time = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    record = AnalysisRecord(
        analysis_id="an_empty_rep",
        repository="clean/repo",
        repository_url="https://github.com/clean/repo",
        branch="main",
        status=AnalysisStatus.COMPLETED,
        created_at=fixed_time,
        metrics=AnalysisMetrics(),
        findings=[],
        graph=GraphResponse(analysis_id="an_empty_rep", stats=GraphStats()),
    )

    md = generate_markdown_report(record, generation_time=fixed_time)

    assert "*No findings recorded for this analysis.*" in md
    assert "*No circular dependency cycles detected.*" in md


def test_generate_markdown_report_determinism():
    fixed_time = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    record = AnalysisRecord(
        analysis_id="an_det_rep",
        repository="test/repo",
        repository_url="https://github.com/test/repo",
        branch="main",
        status=AnalysisStatus.COMPLETED,
        created_at=fixed_time,
        metrics=AnalysisMetrics(total_findings=0),
    )

    md1 = generate_markdown_report(record, generation_time=fixed_time)
    md2 = generate_markdown_report(record, generation_time=fixed_time)

    assert md1 == md2

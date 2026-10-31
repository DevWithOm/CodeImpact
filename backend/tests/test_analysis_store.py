from app.schemas.analysis import AnalysisRequest, AnalysisStatus
from app.schemas.evidence import EvidenceItem, FindingImpact, TestCandidate
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphStats
from app.services.analysis_store import AnalysisStore, compute_metrics


def test_store_create_and_get_analysis():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/facebook/react", branch="main")
    res = store.create_analysis("an_test1", req)

    assert res.analysis_id == "an_test1"
    assert res.status == AnalysisStatus.QUEUED
    assert res.repository == "facebook/react"
    assert res.branch == "main"
    assert res.created_at is not None

    fetched = store.get_analysis("an_test1")
    assert fetched is not None
    assert fetched.analysis_id == "an_test1"
    assert fetched.status == AnalysisStatus.QUEUED


def test_store_get_unknown_analysis_returns_none():
    store = AnalysisStore()
    assert store.get_analysis("an_nonexistent") is None


def test_store_update_status_and_timestamps():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_test2", req)

    # Transition to running
    running = store.update_status("an_test2", AnalysisStatus.RUNNING, stage="cloning")
    assert running is not None
    assert running.status == AnalysisStatus.RUNNING
    assert running.current_stage == "cloning"

    # Transition to completed
    completed = store.update_status("an_test2", AnalysisStatus.COMPLETED, stage="completed")
    assert completed is not None
    assert completed.status == AnalysisStatus.COMPLETED
    assert completed.completed_at is not None


def test_store_update_results_and_compute_metrics():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_test3", req)

    f1 = FindingItem(
        finding_id="f_001",
        category="unused_export",
        title="Unused export",
        file_path="src/a.ts",
        source_tool="knip",
        description="Not used",
        review_risk="higher",
        impact=FindingImpact(
            direct_dependants=[],
            related_test_candidates=[TestCandidate(file_path="tests/a.test.ts", reason="Direct test")],
        ),
    )
    f2 = FindingItem(
        finding_id="f_002",
        category="duplicate_block",
        title="Duplicate code",
        file_path="src/b.ts",
        source_tool="jscpd",
        description="Duplicate",
        review_risk="medium",
    )

    graph = GraphResponse(
        analysis_id="an_test3",
        nodes=[GraphNode(id="src/a.ts", label="a.ts", file_path="src/a.ts")],
        edges=[],
        cycles=[["src/a.ts", "src/b.ts"]],
        stats=GraphStats(node_count=1, edge_count=0, cycle_count=1),
    )

    updated = store.update_results(
        analysis_id="an_test3",
        findings=[f1, f2],
        graph=graph,
        tool_coverage={"knip": "success", "jscpd": "success"},
        status=AnalysisStatus.COMPLETED,
    )
    assert updated is not None
    assert updated.metrics.total_findings == 2
    assert updated.metrics.higher_risk == 1
    assert updated.metrics.medium_risk == 1
    assert updated.metrics.duplicate_groups == 1
    assert updated.metrics.circular_dependencies == 1
    assert updated.metrics.test_candidates == 1


def test_store_get_findings_filtering_and_pagination():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_test4", req)

    findings = [
        FindingItem(
            finding_id=f"f_{i}",
            category="unused_file" if i % 2 == 0 else "unused_export",
            title=f"Finding {i}",
            file_path=f"src/file_{i}.ts",
            source_tool="knip",
            description=f"Desc {i}",
            review_risk="higher" if i > 3 else "lower",
        )
        for i in range(1, 7)
    ]
    graph = GraphResponse(analysis_id="an_test4", stats=GraphStats())
    store.update_results("an_test4", findings, graph, {"knip": "success"})

    # Filter by category
    unused_files = store.get_findings("an_test4", category="unused_file")
    assert unused_files is not None
    assert len(unused_files.items) == 3

    # Filter by risk
    higher_risks = store.get_findings("an_test4", review_risk="higher")
    assert higher_risks is not None
    assert len(higher_risks.items) == 3

    # Search filter
    searched = store.get_findings("an_test4", search="file_3")
    assert searched is not None
    assert len(searched.items) == 1
    assert searched.items[0].finding_id == "f_3"

    # Pagination
    page1 = store.get_findings("an_test4", page=1, page_size=2)
    assert page1 is not None
    assert len(page1.items) == 2
    assert page1.total == 6


def test_store_get_finding_detail_and_unknown():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_test5", req)

    f = FindingItem(
        finding_id="f_100",
        category="unused_file",
        title="Unused file",
        file_path="src/old.ts",
        source_tool="knip",
        description="Dead code",
    )
    store.update_results("an_test5", [f], GraphResponse(analysis_id="an_test5", stats=GraphStats()), {})

    detail = store.get_finding("an_test5", "f_100")
    assert detail is not None
    assert detail.finding_id == "f_100"
    assert len(detail.limitations) > 0

    assert store.get_finding("an_test5", "nonexistent") is None
    assert store.get_finding("unknown_an", "f_100") is None


def test_store_isolation_between_analyses():
    store = AnalysisStore()
    req1 = AnalysisRequest(repository_url="https://github.com/owner/repo1")
    req2 = AnalysisRequest(repository_url="https://github.com/owner/repo2")
    store.create_analysis("an_1", req1)
    store.create_analysis("an_2", req2)

    f1 = FindingItem(finding_id="f_1", category="c", title="t", file_path="p", source_tool="knip", description="d")
    store.update_results("an_1", [f1], GraphResponse(analysis_id="an_1", stats=GraphStats()), {})

    res1 = store.get_findings("an_1")
    res2 = store.get_findings("an_2")
    assert res1 is not None and len(res1.items) == 1
    assert res2 is not None and len(res2.items) == 0

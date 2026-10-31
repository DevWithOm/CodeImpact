from app.schemas.analysis import AnalysisRequest, AnalysisStatus
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphResponse, GraphStats
from app.services.analysis_store import AnalysisStore


def test_lifecycle_success_path():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    status_res = store.create_analysis("an_life_1", req)
    assert status_res.status == AnalysisStatus.QUEUED
    assert status_res.created_at is not None
    assert status_res.completed_at is None

    store.update_status("an_life_1", AnalysisStatus.RUNNING, stage="cloning")
    running = store.get_analysis("an_life_1")
    assert running.status == AnalysisStatus.RUNNING
    assert running.current_stage == "cloning"

    store.update_results(
        "an_life_1",
        findings=[],
        graph=GraphResponse(analysis_id="an_life_1", stats=GraphStats()),
        tool_coverage={"git": "success", "knip": "success", "madge": "success"},
        status=AnalysisStatus.COMPLETED,
    )
    completed = store.get_analysis("an_life_1")
    assert completed.status == AnalysisStatus.COMPLETED
    assert completed.completed_at is not None
    assert completed.tool_coverage["knip"] == "success"


def test_lifecycle_partial_failure():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_life_2", req)

    f = FindingItem(
        finding_id="f_part",
        category="unused_export",
        title="Unused export",
        file_path="src/index.ts",
        source_tool="knip",
        description="Not used",
    )
    store.update_results(
        "an_life_2",
        findings=[f],
        graph=GraphResponse(analysis_id="an_life_2", stats=GraphStats()),
        tool_coverage={"knip": "success", "jscpd": "failed"},
        status=AnalysisStatus.PARTIAL,
        error_message="Tools failed: jscpd",
    )
    partial = store.get_analysis("an_life_2")
    assert partial.status == AnalysisStatus.PARTIAL
    assert partial.tool_coverage["jscpd"] == "failed"
    assert partial.metrics.total_findings == 1
    assert partial.error_message == "Tools failed: jscpd"


def test_lifecycle_complete_failure():
    store = AnalysisStore()
    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_life_3", req)

    store.update_status(
        "an_life_3",
        AnalysisStatus.FAILED,
        stage="failed",
        error_message="Repository not accessible",
    )
    failed = store.get_analysis("an_life_3")
    assert failed.status == AnalysisStatus.FAILED
    assert failed.current_stage == "failed"
    assert "Repository not accessible" in failed.error_message

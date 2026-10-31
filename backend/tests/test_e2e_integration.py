import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalysisRequest, AnalysisStatus
from app.services.analysis_store import analysis_store
from app.services.orchestrator import AnalysisOrchestrator
from app.adapters.repository_adapter import RepositoryAdapter
from app.adapters.static_analysis_adapter import StaticAnalysisAdapter
from app.adapters.dependency_impact_adapter import DependencyImpactAdapter


class LocalTestRepoAdapter:
    """Adapter that supplies the local sample-js-repository fixture."""
    def __init__(self, fixture_path: str):
        self.fixture_path = fixture_path

    def retrieve_repository(self, repository_url: str, branch: str, analysis_id: str) -> dict:
        return {
            "workspace_path": self.fixture_path,
            "repository": "DevWithOm/DeadCode-Detective",
            "branch": branch or "main",
            "commit_sha": "fixture_sha_e2e_777",
            "file_count": 6,
            "languages": ["JavaScript", "TypeScript"],
        }

    def cleanup_workspace(self, workspace_path: str) -> bool:
        return True


@pytest.fixture
def sample_fixture_path() -> str:
    p = Path("fixtures/sample-js-repository").resolve()
    if not (p / "src").exists():
        p = (Path(__file__).resolve().parents[2] / "fixtures" / "sample-js-repository").resolve()
    return str(p)


@pytest.mark.asyncio
async def test_complete_e2e_pipeline_and_api_connectivity(sample_fixture_path: str):
    """
    End-to-End Test:
    1. Orchestrator executes retrieval, Knip, jscpd, and Madge.
    2. Analysis status transitions to completed.
    3. Status endpoint returns metrics and coverage.
    4. Findings endpoint returns normalized findings.
    5. Graph endpoint returns nodes, edges, cycles.
    6. Explain endpoint returns evidence-grounded AI assessment.
    7. Report endpoint returns complete downloadable Markdown.
    """
    client = TestClient(app)

    aid = "an_e2e_full_validation"
    req = AnalysisRequest(
        repository_url="https://github.com/DevWithOm/DeadCode-Detective",
        branch="main"
    )
    analysis_store.create_analysis(aid, req)

    orchestrator = AnalysisOrchestrator(
        store=analysis_store,
        repo_adapter=LocalTestRepoAdapter(sample_fixture_path),
        static_adapter=StaticAnalysisAdapter(),
        dependency_adapter=DependencyImpactAdapter(),
    )

    # 1. Run Pipeline
    await orchestrator.run_pipeline(aid)
    rec = analysis_store.get_analysis(aid)
    assert rec.status in (AnalysisStatus.COMPLETED, AnalysisStatus.PARTIAL)

    # 2. Status Endpoint Verification
    status_get = client.get(f"/api/analyses/{aid}")
    assert status_get.status_code == 200
    status_data = status_get.json()
    assert status_data["analysis_id"] == aid
    assert status_data["status"] in ("completed", "partial")
    assert status_data["metrics"]["total_findings"] > 0

    # 3. Findings Endpoint Verification
    findings_get = client.get(f"/api/analyses/{aid}/findings")
    assert findings_get.status_code == 200
    findings_data = findings_get.json()
    assert findings_data["total"] > 0
    items = findings_data["items"]
    assert len(items) > 0

    first_finding = items[0]
    fid = first_finding["finding_id"]
    assert "file_path" in first_finding
    assert "category" in first_finding
    assert "review_risk" in first_finding

    # 4. Graph Endpoint Verification
    graph_get = client.get(f"/api/analyses/{aid}/graph")
    assert graph_get.status_code == 200
    graph_data = graph_get.json()
    assert len(graph_data["nodes"]) > 0
    assert len(graph_data["edges"]) > 0

    # 5. Explain Endpoint Verification
    explain_post = client.post(
        f"/api/analyses/{aid}/explain",
        json={"finding_id": fid}
    )
    # 200 (Gemini or deterministic fallback) or 503 (if unconfigured)
    assert explain_post.status_code in (200, 503)
    if explain_post.status_code == 200:
        explain_data = explain_post.json()
        assert "explanation" in explain_data
        assert "verification_steps" in explain_data

    # 6. Report Endpoint Verification
    report_get = client.get(f"/api/analyses/{aid}/report")
    assert report_get.status_code == 200
    assert "text/markdown" in report_get.headers.get("content-type", "")
    assert "attachment" in report_get.headers.get("content-disposition", "")
    report_text = report_get.text
    assert "# CodeImpact Audit Report" in report_text
    assert aid in report_text
    assert "Executive Summary" in report_text
    assert "Pre-Cleanup" in report_text
    assert "Checklist" in report_text

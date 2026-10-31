from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.analysis import AnalysisRequest
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphResponse, GraphStats
from app.services.analysis_store import analysis_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_report_analysis():
    analysis_store.clear()
    req = AnalysisRequest(repository_url="https://github.com/facebook/react", branch="main")
    analysis_store.create_analysis("an_report_test", req)

    f = FindingItem(
        finding_id="f_rep_api",
        category="unused_export",
        title="Unused React export",
        file_path="src/React.ts",
        source_tool="knip",
        description="Not consumed statically",
        review_risk="higher",
    )
    analysis_store.update_results(
        "an_report_test",
        findings=[f],
        graph=GraphResponse(analysis_id="an_report_test", stats=GraphStats()),
        tool_coverage={"knip": "success", "madge": "success"},
    )


def test_download_report_endpoint_unknown_analysis():
    res = client.get("/api/analyses/an_nonexistent/report")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "an_nonexistent" in body["error"]["message"]


def test_download_report_endpoint_success():
    res = client.get("/api/analyses/an_report_test/report")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert 'attachment; filename="CodeImpact_Report_facebook_react_an_report_test.md"' in res.headers["content-disposition"]

    markdown_body = res.text
    assert "# CodeImpact Audit Report" in markdown_body
    assert "facebook/react" in markdown_body
    assert "f_rep_api" in markdown_body
    assert "Unused React export" in markdown_body
    assert "Pre-Cleanup Developer Checklist" in markdown_body

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalysisRequest
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphNode, GraphResponse, GraphStats
from app.services.analysis_store import analysis_store

client = TestClient(app)


def test_api_analysis_status_and_not_found():
    # Unknown analysis returns 404 with error envelope
    res = client.get("/api/analyses/an_unknown_999")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"

    # Known analysis returns 200
    req = AnalysisRequest(repository_url="https://github.com/facebook/react")
    analysis_store.create_analysis("an_api_test_1", req)

    res_known = client.get("/api/analyses/an_api_test_1")
    assert res_known.status_code == 200
    body = res_known.json()
    assert body["analysis_id"] == "an_api_test_1"
    assert body["status"] == "queued"
    assert body["repository"] == "facebook/react"


def test_api_analysis_findings_and_detail():
    req = AnalysisRequest(repository_url="https://github.com/facebook/react")
    analysis_store.create_analysis("an_api_test_2", req)

    f = FindingItem(
        finding_id="f_detail_1",
        category="unused_export",
        title="Unused component export",
        file_path="src/Component.tsx",
        source_tool="knip",
        description="Component export has 0 static consumers",
        review_risk="higher",
    )
    analysis_store.update_results(
        "an_api_test_2",
        findings=[f],
        graph=GraphResponse(analysis_id="an_api_test_2", stats=GraphStats()),
        tool_coverage={"knip": "success"},
    )

    # List findings
    res_list = client.get("/api/analyses/an_api_test_2/findings")
    assert res_list.status_code == 200
    list_body = res_list.json()
    assert list_body["total"] == 1
    assert list_body["items"][0]["finding_id"] == "f_detail_1"

    # Get finding detail
    res_det = client.get("/api/analyses/an_api_test_2/findings/f_detail_1")
    assert res_det.status_code == 200
    det_body = res_det.json()
    assert det_body["finding_id"] == "f_detail_1"
    assert "limitations" in det_body

    # Finding not found in valid analysis
    res_det_missing = client.get("/api/analyses/an_api_test_2/findings/nonexistent")
    assert res_det_missing.status_code == 404

    # Analysis not found for findings
    res_list_missing = client.get("/api/analyses/an_missing/findings")
    assert res_list_missing.status_code == 404


def test_api_analysis_graph():
    req = AnalysisRequest(repository_url="https://github.com/facebook/react")
    analysis_store.create_analysis("an_api_test_3", req)

    graph = GraphResponse(
        analysis_id="an_api_test_3",
        nodes=[GraphNode(id="src/a.ts", label="a.ts", file_path="src/a.ts")],
        edges=[],
        cycles=[["src/a.ts", "src/b.ts"]],
        stats=GraphStats(node_count=1, edge_count=0, cycle_count=1),
    )
    analysis_store.update_results("an_api_test_3", findings=[], graph=graph, tool_coverage={})

    res = client.get("/api/analyses/an_api_test_3/graph")
    assert res.status_code == 200
    body = res.json()
    assert body["analysis_id"] == "an_api_test_3"
    assert len(body["nodes"]) == 1
    assert len(body["cycles"]) == 1

    # Unknown graph returns 404
    res_missing = client.get("/api/analyses/an_missing/graph")
    assert res_missing.status_code == 404

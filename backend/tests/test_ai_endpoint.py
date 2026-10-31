import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.analysis import AnalysisRequest
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphResponse, GraphStats
from app.services.ai.gemini_service import gemini_service
from app.services.analysis_store import analysis_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_analysis():
    analysis_store.clear()
    req = AnalysisRequest(repository_url="https://github.com/facebook/react")
    analysis_store.create_analysis("an_explain_test", req)

    f = FindingItem(
        finding_id="f_exp_1",
        category="unused_export",
        title="Unused component export",
        file_path="src/Button.tsx",
        symbol="Button",
        source_tool="knip",
        description="No static imports of Button",
        review_risk="medium",
        evidence=[],
    )
    analysis_store.update_results(
        "an_explain_test",
        findings=[f],
        graph=GraphResponse(analysis_id="an_explain_test", stats=GraphStats()),
        tool_coverage={"knip": "success"},
    )


def test_explain_endpoint_unknown_analysis():
    res = client.post("/api/analyses/an_nonexistent/explain", json={"finding_id": "f_exp_1"})
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_explain_endpoint_unknown_finding():
    res = client.post("/api/analyses/an_explain_test/explain", json={"finding_id": "f_nonexistent"})
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "f_nonexistent" in body["error"]["message"]


def test_explain_endpoint_missing_required_fields():
    res = client.post("/api/analyses/an_explain_test/explain", json={})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "finding_id" in body["error"]["message"]


def test_explain_endpoint_invalid_field_type():
    res = client.post("/api/analyses/an_explain_test/explain", json={"finding_id": None})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_explain_endpoint_extra_forbidden_fields_rejected():
    res = client.post(
        "/api/analyses/an_explain_test/explain",
        json={"finding_id": "f_exp_1", "extra_unsupported_field": "disallowed"},
    )
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "extra_unsupported_field" in body["error"]["message"]


def test_explain_endpoint_gemini_unavailable():
    # Force gemini_service._client to None
    original_client = gemini_service._client
    gemini_service._client = None
    try:
        res = client.post("/api/analyses/an_explain_test/explain", json={"finding_id": "f_exp_1"})
        assert res.status_code == 503
        body = res.json()
        assert body["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
        assert "Gemini API key is not configured" in body["error"]["message"]
    finally:
        gemini_service._client = original_client


def test_explain_endpoint_successful_generation_without_prompt():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "summary": "Button export is not directly consumed statically in src/Button.tsx.",
        "why_it_matters": "Reduces public API footprint.",
        "false_positive_scenarios": ["Export may be imported dynamically by a router or story."],
        "verification_steps": ["Verify storybook or dynamic import references before cleanup."],
        "suggested_action": "Review before making a change.",
        "limitations": ["Static analysis does not check runtime reflection."]
    })
    mock_client.models.generate_content.return_value = mock_response

    original_client = gemini_service._client
    gemini_service._client = mock_client
    try:
        res = client.post("/api/analyses/an_explain_test/explain", json={"finding_id": "f_exp_1"})
        assert res.status_code == 200
        body = res.json()
        assert "Button" in body["summary"]
        assert len(body["false_positive_scenarios"]) == 1
        assert len(body["verification_steps"]) == 1
        assert body["suggested_action"] == "Review before making a change."
        # Verify convenience aliases populated
        assert body["explanation"] == body["summary"]
        assert body["potential_risks"] == body["false_positive_scenarios"]
        assert body["uncertainty_notes"] == body["limitations"]
    finally:
        gemini_service._client = original_client


def test_explain_endpoint_successful_generation_with_custom_prompt():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "summary": "Button is safe to keep if used by external consumers.",
        "why_it_matters": "Library export boundaries must be respected.",
        "false_positive_scenarios": ["Consumed by consumer repositories."],
        "verification_steps": ["Check npm package exports map."],
        "suggested_action": "Verify public API before removal.",
        "limitations": ["Static analysis only inspects internal files."]
    })
    mock_client.models.generate_content.return_value = mock_response

    original_client = gemini_service._client
    gemini_service._client = mock_client
    try:
        res = client.post(
            "/api/analyses/an_explain_test/explain",
            json={"finding_id": "f_exp_1", "prompt": "Can I delete Button.tsx safely?"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["summary"] == "Button is safe to keep if used by external consumers."
        assert body["explanation"] == body["summary"]
    finally:
        gemini_service._client = original_client


def test_explain_endpoint_repeated_requests_idempotent():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "summary": "Idempotent analysis test summary.",
        "why_it_matters": "Test.",
        "false_positive_scenarios": [],
        "verification_steps": [],
        "suggested_action": "Test action.",
        "limitations": []
    })
    mock_client.models.generate_content.return_value = mock_response

    original_client = gemini_service._client
    gemini_service._client = mock_client
    try:
        for _ in range(3):
            res = client.post(
                "/api/analyses/an_explain_test/explain",
                json={"finding_id": "f_exp_1", "prompt": "Repeated request check"},
            )
            assert res.status_code == 200
            assert res.json()["summary"] == "Idempotent analysis test summary."
    finally:
        gemini_service._client = original_client

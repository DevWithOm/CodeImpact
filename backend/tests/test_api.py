"""API and static analysis integration tests."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ImportError:
    from app.main import app

from backend.app.services.static_analysis.analyzer import analyze_repository

client = TestClient(app)


def test_api_root_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_api_repositories_analyse_endpoint():
    res = client.post("/api/repositories/analyse", json={"repository_url": "https://github.com/owner/repo"})
    assert res.status_code == 202
    assert res.json()["status"] == "queued"


def test_analyze_repository_fixture():
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    analysis_id = "an_test_e2e"

    result = analyze_repository(fixture_path, analysis_id)

    assert "findings" in result
    assert "tool_coverage" in result

    findings = result["findings"]
    coverage = result["tool_coverage"]

    # Verify coverage contract
    assert "knip" in coverage
    assert "jscpd" in coverage
    assert coverage["knip"]["status"] in ("completed", "partial")
    assert coverage["jscpd"]["status"] == "completed"
    assert coverage["knip"]["finding_count"] > 0
    assert coverage["jscpd"]["finding_count"] > 0

    # Verify findings count matches sum
    assert len(findings) == coverage["knip"]["finding_count"] + coverage["jscpd"]["finding_count"]

    # Verify finding schema compliance
    categories = {f["category"] for f in findings}
    assert "unused_file" in categories or "unused_dependency" in categories
    assert "duplicate_code" in categories

    for f in findings:
        assert isinstance(f["finding_id"], str) and f["finding_id"].startswith("f_")
        assert f["category"] in ("unused_file", "unused_export", "unused_dependency", "duplicate_code", "other")
        assert isinstance(f["title"], str)
        assert isinstance(f["file_path"], str)
        assert f["source_tool"] in ("knip", "jscpd")
        assert isinstance(f["description"], str)
        assert f["evidence_class"] in ("strong", "inconclusive", "contradictory")
        assert f["review_risk"] == "unknown"  # OM_2 sets to unknown; SAMAR_3 calculates final risk
        assert isinstance(f["evidence"], list)
        assert isinstance(f["risk_factors"], list)
        assert isinstance(f["metadata"], dict)

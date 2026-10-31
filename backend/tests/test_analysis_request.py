from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_start_analysis_valid_request():
    payload = {
        "repository_url": "https://github.com/facebook/react",
        "branch": "main",
    }
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "analysis_id" in data
    assert data["analysis_id"].startswith("an_")
    assert data["status"] == "queued"
    assert data["repository"] == "facebook/react"
    assert data["branch"] == "main"


def test_start_analysis_default_branch():
    payload = {
        "repository_url": "https://github.com/DevWithOm/DeadCode-Detective.git"
    }
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert data["branch"] == "main"
    assert data["repository"] == "DevWithOm/DeadCode-Detective"


def test_start_analysis_custom_branch():
    payload = {
        "repository_url": "https://github.com/owner/my-project",
        "branch": "feature/refactor",
    }
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert data["branch"] == "feature/refactor"


def test_start_analysis_missing_url_rejected():
    response = client.post("/api/repositories/analyse", json={})
    assert response.status_code == 422

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "repository_url" in data["error"]["message"]
    assert "request_id" in data["error"]


def test_start_analysis_empty_url_rejected():
    payload = {"repository_url": "   "}
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "empty" in data["error"]["message"].lower()


def test_start_analysis_local_filesystem_path_rejected():
    payload = {"repository_url": "file:///c:/Users/code/repo"}
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "filesystem" in data["error"]["message"].lower()


def test_start_analysis_unsupported_scheme_rejected():
    payload = {"repository_url": "ftp://github.com/owner/repo"}
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "scheme" in data["error"]["message"].lower()


def test_start_analysis_invalid_branch_name_rejected():
    payload = {
        "repository_url": "https://github.com/owner/repo",
        "branch": "invalid branch with spaces",
    }
    response = client.post("/api/repositories/analyse", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"

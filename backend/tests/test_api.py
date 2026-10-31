from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_root_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_api_repositories_analyse_endpoint():
    res = client.post("/api/repositories/analyse", json={"repository_url": "https://github.com/owner/repo"})
    assert res.status_code == 202
    assert res.json()["status"] == "queued"

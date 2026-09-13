from fastapi.testclient import TestClient

from homeprep_server.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness() -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_system_info() -> None:
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "HomePrep Server"
    assert payload["api_version"] == "v1"

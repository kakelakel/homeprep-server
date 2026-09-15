from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from homeprep_server.core.config import settings
from homeprep_server.database import get_engine, reset_database_state
from homeprep_server.main import app
from homeprep_server.models import Base


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    original_database_url = settings.database_url
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-readiness-areas.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())
    with TestClient(app) as test_client:
        setup = test_client.post(
            "/api/v1/auth/setup",
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert setup.status_code == 201
        yield test_client
    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def _household(client: TestClient) -> str:
    response = client.post("/api/v1/households", json={"name": "Readiness home"})
    assert response.status_code == 201
    return response.json()["id"]


def test_unconfigured_areas_do_not_lower_overall_score(client: TestClient) -> None:
    household_id = _household(client)
    item = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Emergency torch",
            "category": "lighting",
            "quantity": 1,
            "unit": "piece",
        },
    )
    assert item.status_code == 201

    response = client.get(f"/api/v1/readiness/{household_id}")
    assert response.status_code == 200
    body = response.json()
    areas = {area["key"]: area for area in body["areas"]}
    assert areas["inventory"]["configured"] is True
    assert areas["inventory"]["score"] == 100
    assert areas["containers"]["configured"] is False
    assert areas["containers"]["score"] is None
    assert areas["targets"]["configured"] is False
    assert body["score"] == 100


def test_configured_area_attention_affects_overall(client: TestClient) -> None:
    household_id = _household(client)
    item = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Expired water",
            "category": "water",
            "quantity": 2,
            "unit": "liter",
            "expires_at": "2000-01-01",
        },
    )
    assert item.status_code == 201
    task = client.post(
        "/api/v1/tasks",
        json={
            "household_id": household_id,
            "name": "Future inspection",
            "next_due_at": date.max.isoformat(),
            "recurrence_type": "months",
            "recurrence_interval": 6,
        },
    )
    assert task.status_code == 201

    response = client.get(f"/api/v1/readiness/{household_id}")
    assert response.status_code == 200
    body = response.json()
    areas = {area["key"]: area for area in body["areas"]}
    assert areas["inventory"]["score"] == 0
    assert areas["tasks"]["score"] == 100
    assert body["score"] == 50
    assert body["status"] == "critical"

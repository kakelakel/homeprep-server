# ruff: noqa: I001

from fastapi.testclient import TestClient

from homeprep_server.main import app


HA_CATEGORIES = {
    "food",
    "water",
    "medicine",
    "first_aid",
    "hygiene",
    "lighting",
    "power",
    "communication",
    "fire_safety",
    "tools",
    "shelter_warmth",
    "cooking",
    "documents",
    "cash",
    "pet_supplies",
    "other",
}


def test_inventory_taxonomy_matches_ha_vocabulary() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/taxonomy/inventory")

    assert response.status_code == 200
    taxonomy = response.json()
    assert set(taxonomy["categories"]) == HA_CATEGORIES
    assert set(taxonomy["category_meta"]) == HA_CATEGORIES
    assert set(taxonomy["item_types"]) == {"consumable", "equipment"}
    assert taxonomy["category_meta"]["hygiene"]["default_unit"] == "piece"
    assert taxonomy["category_meta"]["water"]["default_unit"] == "liter"
    assert "tablet" in taxonomy["units"]
    assert "gallon_us" in taxonomy["units"]
    assert "kilowatt_hour" in taxonomy["units"]

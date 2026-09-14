from fastapi import APIRouter

from homeprep_server.taxonomy import inventory_taxonomy

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])


@router.get("/inventory")
def get_inventory_taxonomy() -> dict[str, object]:
    """Return the canonical HomePrep inventory form vocabulary."""
    return inventory_taxonomy()

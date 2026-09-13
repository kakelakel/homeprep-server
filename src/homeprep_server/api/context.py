from fastapi import APIRouter
from sqlalchemy import select

from homeprep_server import __version__
from homeprep_server.api.client_auth import PrincipalDep, SessionDep
from homeprep_server.core.identity import get_server_id
from homeprep_server.models import HouseholdModel
from homeprep_server.schemas import (
    ClientContext,
    ClientContextHousehold,
    ClientContextPrincipal,
)

router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("", response_model=ClientContext)
def get_context(principal: PrincipalDep, session: SessionDep) -> ClientContext:
    household = session.scalar(
        select(HouseholdModel).where(HouseholdModel.deleted_at.is_(None)).limit(1)
    )
    household_payload = None
    if household is not None:
        household_payload = ClientContextHousehold(id=household.id, name=household.name)

    return ClientContext(
        server_id=get_server_id(),
        server_version=__version__,
        api_version="v1",
        principal=ClientContextPrincipal(
            kind=principal.kind,
            id=principal.id,
            name=principal.name,
            role=principal.role,
        ),
        household=household_payload,
    )

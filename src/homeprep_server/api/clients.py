from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from homeprep_server.api.authz import OwnerDep
from homeprep_server.core.security import create_client_token, hash_client_token
from homeprep_server.database import get_session
from homeprep_server.models import ClientCredentialModel, utc_now
from homeprep_server.schemas import (
    ClientCredentialCreate,
    ClientCredentialCreated,
    ClientCredentialRead,
)

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[ClientCredentialRead])
def list_clients(session: SessionDep, _owner: OwnerDep) -> list[ClientCredentialRead]:
    clients = session.scalars(
        select(ClientCredentialModel).order_by(ClientCredentialModel.created_at.asc())
    ).all()
    return [ClientCredentialRead.model_validate(client) for client in clients]


@router.post("", response_model=ClientCredentialCreated, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCredentialCreate,
    session: SessionDep,
    _owner: OwnerDep,
) -> ClientCredentialCreated:
    token = create_client_token()
    client = ClientCredentialModel(
        id=str(uuid4()),
        name=payload.name.strip(),
        client_type=payload.client_type,
        access_role=payload.access_role,
        token_hash=hash_client_token(token),
    )
    session.add(client)
    session.commit()
    session.refresh(client)

    return ClientCredentialCreated(
        **ClientCredentialRead.model_validate(client).model_dump(),
        token=token,
    )


@router.post("/{client_id}/revoke", response_model=ClientCredentialRead)
def revoke_client(
    client_id: UUID,
    session: SessionDep,
    _owner: OwnerDep,
) -> ClientCredentialRead:
    client = session.get(ClientCredentialModel, str(client_id))
    if client is None:
        raise HTTPException(status_code=404, detail="Client credential not found")
    if client.revoked_at is None:
        client.revoked_at = utc_now()
        session.commit()
        session.refresh(client)
    return ClientCredentialRead.model_validate(client)

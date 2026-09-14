from datetime import timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from homeprep_server.api.authz import OwnerDep
from homeprep_server.core.security import create_client_token, hash_client_token
from homeprep_server.database import get_session
from homeprep_server.models import ClientCredentialModel, ClientPairingModel, utc_now
from homeprep_server.schemas import (
    ClientCredentialCreated,
    ClientCredentialRead,
    ClientPairingCreate,
    ClientPairingCreated,
    ClientPairingExchange,
)

router = APIRouter(prefix="/api/v1/pairing", tags=["pairing"])
SessionDep = Annotated[Session, Depends(get_session)]
PAIRING_LIFETIME_MINUTES = 10


@router.post(
    "",
    response_model=ClientPairingCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_pairing(
    payload: ClientPairingCreate,
    session: SessionDep,
    _owner: OwnerDep,
) -> ClientPairingCreated:
    pairing_token = create_client_token()
    expires_at = utc_now() + timedelta(minutes=PAIRING_LIFETIME_MINUTES)
    pairing = ClientPairingModel(
        id=str(uuid4()),
        pairing_token_hash=hash_client_token(pairing_token),
        name=payload.name.strip(),
        client_type=payload.client_type,
        access_role=payload.access_role,
        expires_at=expires_at,
    )
    session.add(pairing)
    session.commit()
    session.refresh(pairing)
    return ClientPairingCreated(
        id=pairing.id,
        name=pairing.name,
        client_type=pairing.client_type,
        access_role=pairing.access_role,
        pairing_token=pairing_token,
        expires_at=pairing.expires_at,
    )


@router.post("/exchange", response_model=ClientCredentialCreated)
def exchange_pairing(
    payload: ClientPairingExchange,
    session: SessionDep,
) -> ClientCredentialCreated:
    pairing = session.scalar(
        select(ClientPairingModel).where(
            ClientPairingModel.pairing_token_hash == hash_client_token(payload.pairing_token),
            ClientPairingModel.consumed_at.is_(None),
            ClientPairingModel.expires_at > utc_now(),
        )
    )
    if pairing is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_pairing_token",
                "message": "Pairing token is invalid, expired, or already used",
            },
        )

    client_token = create_client_token()
    client = ClientCredentialModel(
        id=str(uuid4()),
        name=pairing.name,
        client_type=pairing.client_type,
        access_role=pairing.access_role,
        token_hash=hash_client_token(client_token),
    )
    pairing.consumed_at = utc_now()
    session.add(client)
    session.commit()
    session.refresh(client)

    return ClientCredentialCreated(
        **ClientCredentialRead.model_validate(client).model_dump(),
        token=client_token,
    )

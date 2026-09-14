from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from homeprep_server.api.auth import get_optional_user
from homeprep_server.api.authz import EDITOR_ROLE, OWNER_ROLE
from homeprep_server.core.security import hash_client_token
from homeprep_server.database import get_session
from homeprep_server.models import ClientCredentialModel, UserModel, utc_now

SessionDep = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class RequestPrincipal:
    kind: Literal["user", "client"]
    id: str
    role: str
    name: str


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.casefold() != "bearer" or not token:
        return None
    return token.strip()


def get_optional_principal(
    request: Request,
    session: SessionDep,
    user: Annotated[UserModel | None, Depends(get_optional_user)],
) -> RequestPrincipal | None:
    if user is not None:
        return RequestPrincipal(kind="user", id=user.id, role=user.role, name=user.username)

    token = _bearer_token(request)
    if token is None:
        return None

    client = session.scalar(
        select(ClientCredentialModel).where(
            ClientCredentialModel.token_hash == hash_client_token(token),
            ClientCredentialModel.revoked_at.is_(None),
        )
    )
    if client is None:
        return None

    client.last_seen_at = utc_now()
    session.commit()
    return RequestPrincipal(
        kind="client",
        id=client.id,
        role=client.access_role,
        name=client.name,
    )


OptionalPrincipalDep = Annotated[RequestPrincipal | None, Depends(get_optional_principal)]


def require_principal(principal: OptionalPrincipalDep) -> RequestPrincipal:
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return principal


PrincipalDep = Annotated[RequestPrincipal, Depends(require_principal)]


def require_write_principal(principal: PrincipalDep) -> RequestPrincipal:
    can_write = (
        principal.kind == "user" and principal.role in {OWNER_ROLE, EDITOR_ROLE}
    ) or (principal.kind == "client" and principal.role == "full_access")
    if not can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "write_access_required",
                "message": "This identity does not have write access",
            },
        )
    return principal


WritePrincipalDep = Annotated[RequestPrincipal, Depends(require_write_principal)]

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.schemas import AssetCreate, AssetRead, AssetUpdate
from homeprep_server.services import AssetService, ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> AssetRead:
    del principal
    try:
        return AssetService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[AssetRead])
def list_assets(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[AssetRead]:
    del principal
    try:
        return list(AssetService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> AssetRead:
    del principal
    try:
        return AssetService(session).get(asset_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> AssetRead:
    del principal
    try:
        return AssetService(session).update(asset_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{asset_id}", response_model=AssetRead)
def delete_asset(
    asset_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> AssetRead:
    del principal
    try:
        return AssetService(session).delete(asset_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc

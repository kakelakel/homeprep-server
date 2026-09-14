from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.operations import NotificationModel, NotificationService
from homeprep_server.services import NotFoundError

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
SessionDep = Annotated[Session, Depends(get_session)]


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    event_key: str
    kind: str
    severity: str
    title: str
    message: str
    resource_type: str | None
    resource_id: UUID | None
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[NotificationRead]:
    del principal
    try:
        return list(NotificationService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: UUID,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> NotificationModel:
    del principal
    try:
        return NotificationService(session).mark_read(notification_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{notification_id}/dismiss", response_model=NotificationRead)
def dismiss_notification(
    notification_id: UUID,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> NotificationModel:
    del principal
    try:
        return NotificationService(session).dismiss(notification_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from homeprep_server.api.authz import OWNER_ROLE, OwnerDep
from homeprep_server.core.security import hash_password
from homeprep_server.database import get_session
from homeprep_server.models import AuthSessionModel, UserModel, utc_now
from homeprep_server.schemas import UserCreate, UserRead, UserUpdate
from fastapi import Depends

router = APIRouter(prefix="/api/v1/users", tags=["users"])
SessionDep = Annotated[Session, Depends(get_session)]


def _normalize_username(username: str) -> str:
    return username.strip().casefold()


def _active_owner_count(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(UserModel).where(
                UserModel.role == OWNER_ROLE,
                UserModel.disabled_at.is_(None),
            )
        )
        or 0
    )


def _get_user_or_404(session: Session, user_id: UUID) -> UserModel:
    user = session.get(UserModel, str(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )
    return user


def _protect_last_owner(session: Session, user: UserModel, payload: UserUpdate) -> None:
    removes_owner = (
        payload.role is not None and payload.role.value != OWNER_ROLE
    ) or payload.disabled is True
    if (
        user.role == OWNER_ROLE
        and user.disabled_at is None
        and removes_owner
        and _active_owner_count(session) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "last_owner_required",
                "message": "At least one active owner must remain",
            },
        )


@router.get("", response_model=list[UserRead])
def list_users(session: SessionDep, _owner: OwnerDep) -> list[UserRead]:
    users = session.scalars(select(UserModel).order_by(UserModel.created_at.asc())).all()
    return [UserRead.model_validate(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: SessionDep, _owner: OwnerDep) -> UserRead:
    username = _normalize_username(payload.username)
    if not username:
        raise HTTPException(status_code=422, detail="Username cannot be empty")

    now = utc_now()
    user = UserModel(
        id=str(uuid4()),
        username=username,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "username_exists",
                "message": "A user with that username already exists",
            },
        ) from exc
    session.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    session: SessionDep,
    _owner: OwnerDep,
) -> UserRead:
    user = _get_user_or_404(session, user_id)
    _protect_last_owner(session, user, payload)

    revoke_sessions = False
    if payload.role is not None:
        user.role = payload.role.value
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        revoke_sessions = True
    if payload.disabled is True and user.disabled_at is None:
        user.disabled_at = utc_now()
        revoke_sessions = True
    elif payload.disabled is False:
        user.disabled_at = None

    user.updated_at = utc_now()
    if revoke_sessions:
        sessions = session.scalars(
            select(AuthSessionModel).where(
                AuthSessionModel.user_id == user.id,
                AuthSessionModel.revoked_at.is_(None),
            )
        ).all()
        now = utc_now()
        for auth_session in sessions:
            auth_session.revoked_at = now

    session.commit()
    session.refresh(user)
    return UserRead.model_validate(user)

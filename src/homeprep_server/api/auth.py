from datetime import timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from homeprep_server.core.config import settings
from homeprep_server.core.security import (
    create_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from homeprep_server.database import get_session
from homeprep_server.models import AuthSessionModel, UserModel, utc_now
from homeprep_server.schemas import AuthLogin, AuthSetup, AuthStatus, UserRead

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
SessionDep = Annotated[Session, Depends(get_session)]
SESSION_COOKIE = "homeprep_session"


def _normalize_username(username: str) -> str:
    return username.strip().casefold()


def _set_session_cookie(response: Response, token: str) -> None:
    max_age = settings.session_lifetime_days * 24 * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def _create_session(session: Session, user: UserModel) -> str:
    token = create_session_token()
    now = utc_now()
    auth_session = AuthSessionModel(
        id=str(uuid4()),
        token_hash=hash_session_token(token),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(days=settings.session_lifetime_days),
    )
    session.add(auth_session)
    session.commit()
    return token


def get_optional_user(request: Request, session: SessionDep) -> UserModel | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    auth_session = session.scalar(
        select(AuthSessionModel).where(
            AuthSessionModel.token_hash == hash_session_token(token),
            AuthSessionModel.revoked_at.is_(None),
            AuthSessionModel.expires_at > utc_now(),
        )
    )
    if auth_session is None:
        return None

    return session.scalar(
        select(UserModel).where(
            UserModel.id == auth_session.user_id,
            UserModel.disabled_at.is_(None),
        )
    )


OptionalUserDep = Annotated[UserModel | None, Depends(get_optional_user)]


def require_user(user: OptionalUserDep) -> UserModel:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


CurrentUserDep = Annotated[UserModel, Depends(require_user)]


@router.get("/status", response_model=AuthStatus)
def auth_status(session: SessionDep, user: OptionalUserDep) -> AuthStatus:
    user_count = session.scalar(select(func.count()).select_from(UserModel)) or 0
    return AuthStatus(
        setup_required=user_count == 0,
        authenticated=user is not None,
        user=UserRead.model_validate(user) if user is not None else None,
    )


@router.post("/setup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def setup_owner(payload: AuthSetup, response: Response, session: SessionDep) -> UserRead:
    user_count = session.scalar(select(func.count()).select_from(UserModel)) or 0
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="HomePrep authentication has already been configured",
        )

    username = _normalize_username(payload.username)
    if not username:
        raise HTTPException(status_code=422, detail="Username cannot be empty")

    now = utc_now()
    user = UserModel(
        id=str(uuid4()),
        username=username,
        password_hash=hash_password(payload.password),
        role="owner",
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = _create_session(session, user)
    _set_session_cookie(response, token)
    return UserRead.model_validate(user)


@router.post("/login", response_model=UserRead)
def login(payload: AuthLogin, response: Response, session: SessionDep) -> UserRead:
    username = _normalize_username(payload.username)
    user = session.scalar(select(UserModel).where(UserModel.username == username))
    if user is None or user.disabled_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    try:
        valid_password = verify_password(payload.password, user.password_hash)
    except Exception:
        valid_password = False

    if not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_session(session, user)
    _set_session_cookie(response, token)
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, session: SessionDep) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth_session = session.scalar(
            select(AuthSessionModel).where(
                AuthSessionModel.token_hash == hash_session_token(token),
                AuthSessionModel.revoked_at.is_(None),
            )
        )
        if auth_session is not None:
            auth_session.revoked_at = utc_now()
            session.commit()

    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)

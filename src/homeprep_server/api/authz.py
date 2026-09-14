from typing import Annotated

from fastapi import Depends, HTTPException, status

from homeprep_server.api.auth import CurrentUserDep
from homeprep_server.models import UserModel

OWNER_ROLE = "owner"
EDITOR_ROLE = "editor"
VIEWER_ROLE = "viewer"
USER_ROLES = {OWNER_ROLE, EDITOR_ROLE, VIEWER_ROLE}


def require_owner(user: CurrentUserDep) -> UserModel:
    if user.role != OWNER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "owner_required",
                "message": "Owner access is required",
            },
        )
    return user


OwnerDep = Annotated[UserModel, Depends(require_owner)]


def require_editor(user: CurrentUserDep) -> UserModel:
    if user.role not in {OWNER_ROLE, EDITOR_ROLE}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "write_access_required",
                "message": "Editor or owner access is required",
            },
        )
    return user


EditorDep = Annotated[UserModel, Depends(require_editor)]

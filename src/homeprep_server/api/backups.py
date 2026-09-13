from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from homeprep_server.api.auth import CurrentUserDep
from homeprep_server.core.backup import create_backup, list_backups
from homeprep_server.models import UserModel
from homeprep_server.schemas import BackupRead

router = APIRouter(prefix="/api/v1/backups", tags=["backups"])


def require_owner(user: CurrentUserDep) -> UserModel:
    if user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "owner_required",
                "message": "Owner access is required for backup administration",
            },
        )
    return user


OwnerDep = Annotated[UserModel, Depends(require_owner)]


@router.get("", response_model=list[BackupRead])
def get_backups(_owner: OwnerDep) -> list[BackupRead]:
    return [BackupRead(**result.__dict__) for result in list_backups()]


@router.post("", response_model=BackupRead, status_code=status.HTTP_201_CREATED)
def create_server_backup(_owner: OwnerDep) -> BackupRead:
    result = create_backup()
    return BackupRead(**result.__dict__)

from __future__ import annotations

import base64
import binascii
import json
import secrets
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.core.config import settings

router = APIRouter(prefix="/api/v1/media", tags=["media"])
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ImageUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    data_base64: str = Field(min_length=1)


class ImageRead(BaseModel):
    image_id: UUID
    image_token: str
    image_content_type: str
    image_filename: str
    url: str


def _media_dir() -> Path:
    path = Path(settings.data_dir) / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _paths(image_id: UUID) -> tuple[Path, Path]:
    root = _media_dir()
    return root / f"{image_id}.bin", root / f"{image_id}.json"


def _read_meta(image_id: UUID) -> dict:
    data_path, meta_path = _paths(image_id)
    if not data_path.exists() or not meta_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Image metadata is invalid") from exc


@router.post("/images", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
def upload_image(payload: ImageUpload, principal: WritePrincipalDep) -> ImageRead:
    del principal
    if payload.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image format")
    try:
        raw = base64.b64decode(payload.data_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 5 MB")

    image_id = uuid4()
    token = secrets.token_urlsafe(24)
    data_path, meta_path = _paths(image_id)
    safe_name = Path(payload.filename).name[:255] or "image"
    meta = {
        "image_id": str(image_id),
        "image_token": token,
        "image_content_type": payload.content_type,
        "image_filename": safe_name,
    }
    data_path.write_bytes(raw)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return ImageRead(**meta, url=f"/api/v1/media/images/{image_id}")


@router.get("/images/{image_id}")
def get_image(image_id: UUID, principal: PrincipalDep) -> FileResponse:
    del principal
    meta = _read_meta(image_id)
    data_path, _ = _paths(image_id)
    return FileResponse(
        data_path,
        media_type=meta["image_content_type"],
        filename=meta["image_filename"],
        content_disposition_type="inline",
    )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: UUID, principal: WritePrincipalDep) -> Response:
    del principal
    data_path, meta_path = _paths(image_id)
    if not data_path.exists() and not meta_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    data_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# backend/api/routers/cards.py
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.db.deps import get_db
from backend.schemas.card import CardPublic
from backend.services import card_service, vault_service

router = APIRouter(tags=["cards"])

MEDIA_DIR = Path("backend/media")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}

# Extension fallback (when browser gives empty/odd content_type)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v"}


def _safe_ext(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    ext = os.path.splitext(name)[1]
    if ext and len(ext) <= 10:
        return ext
    return ""


def _parse_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def get_media_type(upload: UploadFile) -> str | None:
    """
    Determine media type using:
      1) content_type if it's one of our allowed types
      2) filename extension fallback
    Returns: "image" | "video" | None
    """
    ct = (upload.content_type or "").lower().strip()

    if ct in ALLOWED_IMAGE_TYPES:
        return "image"
    if ct in ALLOWED_VIDEO_TYPES:
        return "video"

    # Fallback: extension
    name = (upload.filename or "").lower()
    ext = os.path.splitext(name)[1]

    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"

    return None


@router.get("/vaults/{vault_id}/cards", response_model=list[CardPublic])
def list_cards(vault_id: str, db: Session = Depends(get_db)):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    cards = card_service.list_cards(db, vault_id)
    return [card_service.to_public_dict(c) for c in cards]


@router.post("/vaults/{vault_id}/cards", response_model=CardPublic)
async def create_card(
    vault_id: str,
    media_type: str = Form(...),  # still accepted from frontend, but we will trust detected type
    caption: str = Form(...),
    tags: str | None = Form(None),
    isActive: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    detected_type = get_media_type(file)
    if detected_type not in {"image", "video"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: content_type={file.content_type} filename={file.filename}",
        )

    # Read file data
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(file)
    media_id = f"{uuid.uuid4()}{ext}"
    dest_path = MEDIA_DIR / media_id
    dest_path.write_bytes(data)

    thumbnail_id = media_id if detected_type == "image" else None

    card = card_service.create_card(
        db=db,
        vault_id=vault_id,
        media_id=media_id,
        thumbnail_id=thumbnail_id,
        media_type=detected_type,
        caption=caption,
        tags=_parse_tags(tags),
        is_active=isActive,
    )

    return card_service.to_public_dict(card)
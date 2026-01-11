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
    media_type: str = Form(...),
    caption: str = Form(...),
    tags: str | None = Form(None),
    isActive: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    if media_type not in {"image", "video"}:
        raise HTTPException(status_code=400, detail="media_type must be 'image' or 'video'")

    if media_type == "image" and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image content-type: {file.content_type}")

    if media_type == "video" and file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported video content-type: {file.content_type}")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(file)
    media_id = f"{uuid.uuid4()}{ext}"
    dest_path = MEDIA_DIR / media_id

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    dest_path.write_bytes(data)

    thumbnail_id = media_id if media_type == "image" else None

    card = card_service.create_card(
        db=db,
        vault_id=vault_id,
        media_id=media_id,
        thumbnail_id=thumbnail_id,
        media_type=media_type,
        caption=caption,
        tags=_parse_tags(tags),
        is_active=isActive,
    )

    return card_service.to_public_dict(card)

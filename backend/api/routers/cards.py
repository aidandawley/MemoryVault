# backend/api/routers/cards.py
from __future__ import annotations

import os
import uuid
from pathlib import Path
from collections import Counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.db.deps import get_db
from backend.schemas.card import CardPublic
from backend.services import card_service, vault_service

# Tagging tools
from backend.api.tools.gemini_image_tags import get_tags_for_image_file
from backend.api.tools.twelvelabs_hashtag import get_hashtags_for_video_file

# Normalization + resolver pipeline
from backend.api.tools.tag_normalizer import normalize_and_alias
from backend.api.tools.tag_similarity import CategoryIndex
from backend.api.tools.tag_resolver import resolve_tags

router = APIRouter(tags=["cards"])

MEDIA_DIR = Path("backend/media")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v", ".avi"}

# Seed categories for your demo so matching has a good base even when the DB is empty.
SEED_CATEGORIES = [
    # wedding-ish
    "wedding",
    "ceremony",
    "reception",
    "bride",
    "groom",
    "vows",
    "bouquet",
    "cake",
    "dance",
    "speeches",
    # concert-ish
    "concert",
    "stage",
    "crowd",
    "music",
    "singer",
    "band",
    "guitar",
    "drums",
    "lights",
    "performance",
]


def _safe_ext(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    ext = os.path.splitext(name)[1]
    if ext and len(ext) <= 10:
        return ext
    return ""


def _parse_user_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def _detect_media_kind(upload: UploadFile, fallback_media_type: str | None = None) -> str:
    """
    Returns: "image" | "video" | "unknown"
    Uses content_type first, then extension, then optional form field fallback.
    """
    ct = (upload.content_type or "").lower().strip()

    if ct.startswith("image/") or ct in ALLOWED_IMAGE_TYPES:
        return "image"
    if ct.startswith("video/") or ct in ALLOWED_VIDEO_TYPES:
        return "video"

    ext = _safe_ext(upload).lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"

    if fallback_media_type in {"image", "video"}:
        return fallback_media_type

    return "unknown"


def _iter_card_tags_from_vault(db: Session, vault_id: str) -> list[str]:
    """
    Returns all tags already stored on cards in this vault (raw stored tag strings).
    """
    cards = card_service.list_cards(db, vault_id)
    out: list[str] = []

    for c in cards:
        raw = (c.tags or "").strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        out.extend(parts)

    return out


def _top_categories_for_vault(db: Session, vault_id: str, limit: int = 7) -> list[str]:
    """
    Returns top-N most common tags in this vault, normalized.
    NOTE: since we no longer store ambiguous tags, we don't need to filter them out.
    """
    all_tags = _iter_card_tags_from_vault(db, vault_id)

    normalized: list[str] = []
    for t in all_tags:
        tt = (t or "").strip()
        if not tt:
            continue
        normalized.append(normalize_and_alias(tt))

    counts = Counter([t for t in normalized if t])
    return [tag for tag, _ in counts.most_common(limit)]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in items:
        xx = (x or "").strip()
        if not xx:
            continue
        if xx in seen:
            continue
        seen.add(xx)
        out.append(xx)
    return out


@router.get("/vaults/{vault_id}/cards", response_model=list[CardPublic])
def list_cards(vault_id: str, db: Session = Depends(get_db)):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    cards = card_service.list_cards(db, vault_id)
    return [card_service.to_public_dict(c) for c in cards]


@router.get("/vaults/{vault_id}/top-tags", response_model=list[str])
def get_top_tags(vault_id: str, limit: int = 7, db: Session = Depends(get_db)):
    """Returns the top-N most frequent tags in a vault."""
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    top_tags = _top_categories_for_vault(db, vault_id, limit=limit)
    return top_tags


@router.post("/vaults/{vault_id}/cards", response_model=CardPublic)
async def create_card(
    vault_id: str,
    media_type: str = Form(...),  # frontend sends "image" | "video"
    caption: str = Form(...),
    tags: str | None = Form(None),  # user-entered comma tags (optional)
    isActive: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    detected_kind = _detect_media_kind(file, fallback_media_type=media_type)
    if detected_kind == "unknown":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: content_type={file.content_type} filename={file.filename}",
        )

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(file)
    media_id = f"{uuid.uuid4()}{ext}"
    dest_path = MEDIA_DIR / media_id
    dest_path.write_bytes(data)

    thumbnail_id = media_id if detected_kind == "image" else None

    # -------------------------------
    # 1) Generate raw tags (AI)
    # -------------------------------
    generated_tags: list[str] = []
    try:
        if detected_kind == "image":
            generated_tags = get_tags_for_image_file(str(dest_path)) or []
        else:
            result = get_hashtags_for_video_file(str(dest_path)) or {}
            hashtags = result.get("hashtags") or []
            generated_tags = [str(h).lstrip("#").strip() for h in hashtags if str(h).strip()]
            print(f"[tagging] video hashtags for {media_id}:", generated_tags)
    except Exception as e:
        # Don't crash upload for demo
        print("[tagging] failed:", repr(e))
        generated_tags = []

    user_tags = _parse_user_tags(tags)

    # Combine user + AI tags (AI first so it drives discovery)
    raw_tags = _dedupe_preserve_order([*generated_tags, *user_tags])

    # If nothing at all, still create the card
    if not raw_tags:
        card = card_service.create_card(
            db=db,
            vault_id=vault_id,
            media_id=media_id,
            thumbnail_id=thumbnail_id,
            media_type=detected_kind,
            caption=caption,
            tags=[],
            is_active=isActive,
        )
        return card_service.to_public_dict(card)

    # ---------------------------------------------
    # 2) Build comparison categories (seed + top 7)
    # ---------------------------------------------
    top7 = _top_categories_for_vault(db, vault_id, limit=7)
    categories = _dedupe_preserve_order([*SEED_CATEGORIES, *top7])

    index = CategoryIndex(categories)
    index.rebuild()

    # ---------------------------------------------
    # 3) Resolve tags (normalize + match/new/ambig)
    # ---------------------------------------------
    resolved = resolve_tags(raw_tags, index, top_k=3, learn_new=True)

    # Store ONLY match/new.
    # Ambiguous are NOT stored, but we log them so you can see what's being skipped.
    final_tags: list[str] = []
    ambiguous_skipped: list[str] = []

    for r in resolved:
        if r.action in {"match", "new"} and r.chosen:
            final_tags.append(r.chosen)
        elif r.action == "ambiguous":
            ambiguous_skipped.append(r.normalized)

    final_tags = _dedupe_preserve_order(final_tags)

    # Debug print
    print(f"[tags] raw={raw_tags}")
    print(
        "[tags] resolved=",
        [
            {"raw": r.raw, "action": r.action, "chosen": r.chosen, "norm": r.normalized}
            for r in resolved
        ],
    )
    if ambiguous_skipped:
        print(f"[tags] ambiguous_skipped={ambiguous_skipped}")
    print(f"[tags] final_saved={final_tags}")

    # ---------------------------------------------
    # 4) Create card with resolved tags
    # ---------------------------------------------
    card = card_service.create_card(
        db=db,
        vault_id=vault_id,
        media_id=media_id,
        thumbnail_id=thumbnail_id,
        media_type=detected_kind,
        caption=caption,
        tags=final_tags,
        is_active=isActive,
    )

    return card_service.to_public_dict(card)


@router.delete("/cards/{card_id}")
def delete_card(card_id: str, db: Session = Depends(get_db)):
    """Delete a card and its associated media files."""
    card = card_service.get_card(db, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Delete media files from disk
    if card.media_id:
        media_path = MEDIA_DIR / card.media_id
        if media_path.exists():
            media_path.unlink()

    if card.thumbnail_id and card.thumbnail_id != card.media_id:
        thumb_path = MEDIA_DIR / card.thumbnail_id
        if thumb_path.exists():
            thumb_path.unlink()

    # Delete from database
    card_service.delete_card(db, card_id)

    return {"success": True, "message": "Card deleted successfully"}
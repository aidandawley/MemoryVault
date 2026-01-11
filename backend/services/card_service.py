from sqlalchemy.orm import Session
from backend.models.card import Card

def _serialize_tags(tags: list[str]) -> str:
    return ",".join([t.strip() for t in tags if t.strip()])

def _parse_tags(tags: str) -> list[str]:
    if not tags:
        return []
    return [t for t in tags.split(",") if t]

def create_card(
    db: Session,
    vault_id: str,
    media_id: str,
    thumbnail_id: str | None,
    media_type: str,
    caption: str,
    tags: list[str],
    is_active: bool,
) -> Card:
    c = Card(
        vault_id=vault_id,
        media_id=media_id,
        thumbnail_id=thumbnail_id,
        media_type=media_type,
        caption=caption,
        tags=_serialize_tags(tags),
        is_active=is_active,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def list_cards(db: Session, vault_id: str) -> list[Card]:
    return db.query(Card).filter(Card.vault_id == vault_id).order_by(Card.created_at.desc()).all()

def delete_card(db: Session, card_id: str) -> None:
    card = db.query(Card).filter(Card.id == card_id).first()
    if card:
        db.delete(card)
        db.commit()

def to_public_dict(card: Card) -> dict:
    return {
        "cardId": card.id,
        "media_id": card.media_id,
        "thumbnail_id": card.thumbnail_id,
        "media_type": card.media_type,
        "caption": card.caption,
        "tags": _parse_tags(card.tags),
        "isActive": card.is_active,
    }

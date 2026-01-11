import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.deps import get_db
from backend.services import vault_service, card_service

router = APIRouter()

_SHARE_TOKENS: dict[str, str] = {}  # token -> vault_id (resets on restart)

@router.post("/vaults/{vault_id}/share-link")
def create_share_link(vault_id: str, db: Session = Depends(get_db)):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    token = secrets.token_urlsafe(24)
    _SHARE_TOKENS[token] = vault_id
    return {"token": token}

@router.get("/share/{token}")
def open_share_link(token: str, db: Session = Depends(get_db)):
    vault_id = _SHARE_TOKENS.get(token)
    if not vault_id:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    cards = card_service.list_cards(db, vault_id)
    return {
        "vaultId": vault.id,
        "ownerId": vault.owner_id,
        "title": vault.title,
        "description": vault.description,
        "cards": [card_service.to_public_dict(c) for c in cards],
    }

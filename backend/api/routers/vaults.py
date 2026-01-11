from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.deps import get_db
from backend.schemas.vault import VaultCreate, VaultPublic
from backend.services import vault_service

router = APIRouter()

@router.post("/vaults", response_model=VaultPublic)
def create_vault(payload: VaultCreate, db: Session = Depends(get_db)):
    v = vault_service.create_vault(db, payload.title, payload.description)
    return {"vaultId": v.id, "ownerId": v.owner_id, "title": v.title, "description": v.description}

@router.get("/vaults", response_model=list[VaultPublic])
def list_vaults(db: Session = Depends(get_db)):
    vaults = vault_service.list_vaults(db)
    return [
        {"vaultId": v.id, "ownerId": v.owner_id, "title": v.title, "description": v.description}
        for v in vaults
    ]

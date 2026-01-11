from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.deps import get_db
from backend.schemas.vault import VaultPublic, VaultCreate
from backend.services import vault_service

router = APIRouter(tags=["vaults"])

DEMO_OWNER_ID = "demo-user"

@router.get("/vaults", response_model=list[VaultPublic])
def list_vaults(db: Session = Depends(get_db)):
    vaults = vault_service.list_vaults(db, owner_id=DEMO_OWNER_ID)
    return [vault_service.to_public_dict(v) for v in vaults]

@router.post("/vaults", response_model=VaultPublic)
def create_vault(payload: VaultCreate, db: Session = Depends(get_db)):
    vault = vault_service.create_vault(
        db=db,
        owner_id=DEMO_OWNER_ID,
        title=payload.title,
        description=payload.description,
    )
    return vault_service.to_public_dict(vault)

@router.get("/vaults/{vault_id}", response_model=VaultPublic)
def get_vault(vault_id: str, db: Session = Depends(get_db)):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    return vault_service.to_public_dict(vault)

@router.delete("/vaults/{vault_id}")
def delete_vault(vault_id: str, db: Session = Depends(get_db)):
    vault = vault_service.get_vault(db, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")
    vault_service.delete_vault(db, vault_id)
    return {"ok": True}

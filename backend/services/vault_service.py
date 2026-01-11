from sqlalchemy.orm import Session
from backend.models.vault import Vault

FAKE_USER_ID = "u1"

def create_vault(db: Session, owner_id: str, title: str, description: str | None) -> Vault:
    v = Vault(owner_id=owner_id, title=title, description=description)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v

def list_vaults(db: Session, owner_id: str = None) -> list[Vault]:
    query = db.query(Vault)
    if owner_id:
        query = query.filter(Vault.owner_id == owner_id)
    return query.order_by(Vault.updated_at.desc()).all()

def get_vault(db: Session, vault_id: str) -> Vault | None:
    return db.query(Vault).filter(Vault.id == vault_id).first()

def delete_vault(db: Session, vault_id: str) -> None:
    vault = db.query(Vault).filter(Vault.id == vault_id).first()
    if vault:
        db.delete(vault)
        db.commit()

def to_public_dict(vault: Vault) -> dict:
    return {
        "vaultId": vault.id,
        "vault_id": vault.id,  # Include both for compatibility
        "ownerId": vault.owner_id,
        "owner_id": vault.owner_id,  # Include both for compatibility
        "title": vault.title,
        "description": vault.description,
    }

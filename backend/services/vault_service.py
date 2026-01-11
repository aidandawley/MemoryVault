from sqlalchemy.orm import Session
from backend.models.vault import Vault

FAKE_USER_ID = "u1"

def create_vault(db: Session, title: str, description: str | None) -> Vault:
    v = Vault(owner_id=FAKE_USER_ID, title=title, description=description)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v

def list_vaults(db: Session) -> list[Vault]:
    return db.query(Vault).filter(Vault.owner_id == FAKE_USER_ID).order_by(Vault.updated_at.desc()).all()

def get_vault(db: Session, vault_id: str) -> Vault | None:
    return db.query(Vault).filter(Vault.id == vault_id).first()

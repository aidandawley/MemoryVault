from backend.db.base import Base
from backend.db.session import engine

# Import models so they register with SQLAlchemy metadata
from backend.models.vault import Vault  # noqa: F401
from backend.models.card import Card    # noqa: F401
from backend.models.vault_access import VaultAccess  # noqa: F401

def init_db() -> None:
    return



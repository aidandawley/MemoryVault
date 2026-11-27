from backend.db.base import Base
from backend.db.session import engine

# Import every model so create_all knows about all tables.
from backend.models.vault import Vault  # noqa: F401
from backend.models.card import Card  # noqa: F401
from backend.models.vault_access import VaultAccess  # noqa: F401
from backend.models.card_embedding import CardEmbedding  # noqa: F401


def connect_db() -> None:
    # Create any missing tables (existing tables are left as they are)
    Base.metadata.create_all(bind=engine)

from backend.db.base import Base
from backend.db.session import engine

# Import every model so create_all knows about all tables.
from backend.models.vault import Vault  # noqa: F401
from backend.models.card import Card  # noqa: F401
from backend.models.vault_access import VaultAccess  # noqa: F401
from backend.models.card_embedding import CardEmbedding  # noqa: F401


def _add_missing_columns() -> None:
    """create_all never alters existing tables, so add columns introduced after a DB was created."""
    with engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(cards)")}
        if cols and "raw_tags" not in cols:
            conn.exec_driver_sql("ALTER TABLE cards ADD COLUMN raw_tags TEXT NOT NULL DEFAULT '[]'")


def connect_db() -> None:
    # Create any missing tables (existing tables are left as they are)
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        _add_missing_columns()

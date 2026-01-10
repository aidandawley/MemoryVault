from db.session import engine
from db.base import Base

# IMPORTANT: import models so SQLAlchemy "registers" them with Base.metadata
from models.vault import Vault  # noqa: F401
from models.card import Card    # noqa: F401

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

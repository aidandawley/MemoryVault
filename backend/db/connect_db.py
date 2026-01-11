from backend.db.base import Base
from backend.db.session import engine, SessionLocal
from backend.models.vault import Vault  # noqa: F401
def connect_db() -> None:
    # Create tables
    Base.metadata.create_all(bind=engine)
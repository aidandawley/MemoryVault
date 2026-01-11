from backend.db.session import engine, SessionLocal
from backend.db.base import Base

# IMPORTANT: import models so Base.metadata knows them
from backend.models.vault import Vault  # noqa: F401
from backend.models.card import Card    # noqa: F401

def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        # Seed only if there are no vaults yet
        if db.query(Vault).first() is not None:
            return

        DEMO_OWNER_ID = "demo-user"  # must be non-null; later replace with real user id

        vaults = [
            Vault(
                owner_id=DEMO_OWNER_ID,
                title="Personal",
                description="Personal memories and notes",
            ),
            Vault(
                owner_id=DEMO_OWNER_ID,
                title="School",
                description="Class notes, study clips, assignments",
            ),
            Vault(
                owner_id=DEMO_OWNER_ID,
                title="Work",
                description="Projects, meetings, references",
            ),
        ]

        db.add_all(vaults)
        db.commit()

    finally:
        db.close()
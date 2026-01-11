import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

def _uuid() -> str:
    return str(uuid.uuid4())

class Vault(Base):
    __tablename__ = "vaults"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    cards = relationship("Card", back_populates="vault", cascade="all, delete-orphan")
    accesses = relationship("VaultAccess", back_populates="vault", cascade="all, delete-orphan")

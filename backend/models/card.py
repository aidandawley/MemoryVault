import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base  # or wherever your Base lives


def _uuid() -> str:
    return str(uuid.uuid4())


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    vault_id: Mapped[str] = mapped_column(String(36), ForeignKey("vaults.id", ondelete="CASCADE"), index=True)

    media_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "image" or "video"

    caption: Mapped[str] = mapped_column(Text, nullable=False)

    # Simple tags storage for hackathon: comma-separated string
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    vault = relationship("Vault", back_populates="cards")

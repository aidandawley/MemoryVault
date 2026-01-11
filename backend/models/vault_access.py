from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

class VaultAccess(Base):
    __tablename__ = "vault_access"

    vault_id: Mapped[str] = mapped_column(String(36), ForeignKey("vaults.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")  # viewer | editor

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    vault = relationship("Vault", back_populates="accesses")

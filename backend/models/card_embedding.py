from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class CardEmbedding(Base):
    """One embedding per searchable field of a card (its caption, and each normalized tag).

    Search scores a card by its best-matching field, so a one-word query like "beer"
    can match the single tag "drinks" without being diluted by the rest of the card.
    """

    __tablename__ = "card_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(36), ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    vault_id: Mapped[str] = mapped_column(String(36), index=True)

    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # "caption" | "tag"
    text: Mapped[str] = mapped_column(Text, nullable=False)

    model: Mapped[str] = mapped_column(String(100), nullable=False)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # float32, L2-normalized

    # The card's updated_at when this row was built; a mismatch means the row is stale.
    card_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

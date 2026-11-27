"""Semantic search over a vault's cards.

Each card gets one embedding per field (caption + each normalized tag), stored in
card_embeddings. A query is embedded with the same local model and a card's score is
the max cosine similarity over its fields. Embeddings are built when a card is created,
and lazily for any card whose stored rows are missing or stale.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy.orm import Session

from backend.api.tools.tag_similarity import _MODEL_NAME, embed_texts
from backend.models.card import Card
from backend.models.card_embedding import CardEmbedding
from backend.services import card_service


@dataclass
class SearchHit:
    card: Card
    score: float
    matched_kind: str
    matched_text: str


@dataclass
class SearchResult:
    hits: list[SearchHit]
    timings_ms: dict[str, float] = field(default_factory=dict)
    cards_indexed: int = 0


def fields_for_card(card: Card) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    caption = (card.caption or "").strip()
    if caption:
        out.append(("caption", caption))
    for t in card_service.normalized_tags(card_service._parse_tags(card.tags)):
        out.append(("tag", t))
    return out


def index_card(db: Session, card: Card, commit: bool = True) -> int:
    """(Re)builds a card's embedding rows. Returns the number of rows written."""
    db.query(CardEmbedding).filter(CardEmbedding.card_id == card.id).delete()
    fields = fields_for_card(card)
    if fields:
        vecs = embed_texts([text for _, text in fields])
        for (kind, text), vec in zip(fields, vecs):
            db.add(CardEmbedding(
                card_id=card.id, vault_id=card.vault_id, kind=kind, text=text,
                model=_MODEL_NAME, vector=vec.astype(np.float32).tobytes(),
                card_updated_at=card.updated_at,
            ))
    if commit:
        db.commit()
    return len(fields)


def delete_card_embeddings(db: Session, card_id: str) -> None:
    # SQLite does not enforce ON DELETE CASCADE unless PRAGMA foreign_keys is on.
    db.query(CardEmbedding).filter(CardEmbedding.card_id == card_id).delete()
    db.commit()


def _ensure_indexed(db: Session, cards: list[Card], rows: list[CardEmbedding]) -> int:
    """Index cards with no rows, rows from another model, or rows older than the card."""
    ok: dict[str, bool] = {}
    by_id = {c.id: c for c in cards}
    for r in rows:
        card = by_id.get(r.card_id)
        good = card is not None and r.model == _MODEL_NAME and r.card_updated_at == card.updated_at
        ok[r.card_id] = ok.get(r.card_id, True) and good
    stale = [c for c in cards if not ok.get(c.id, False)]
    for c in stale:
        index_card(db, c, commit=False)
    if stale:
        db.commit()
    return len(stale)


def search_vault(db: Session, vault_id: str, query: str, limit: int = 5) -> SearchResult:
    t = {}
    t0 = time.perf_counter()
    cards = card_service.list_cards(db, vault_id)
    rows = db.query(CardEmbedding).filter(CardEmbedding.vault_id == vault_id).all()
    t["db_ms"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    n_indexed = _ensure_indexed(db, cards, rows)
    if n_indexed:
        rows = db.query(CardEmbedding).filter(CardEmbedding.vault_id == vault_id).all()
    t["index_ms"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    q = embed_texts([query])[0]
    t["embed_ms"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    hits: list[SearchHit] = []
    by_id = {c.id: c for c in cards}
    rows = [r for r in rows if r.card_id in by_id]
    if rows:
        mat = np.frombuffer(b"".join(r.vector for r in rows), dtype=np.float32).reshape(len(rows), -1)
        sims = mat @ q
        best: dict[str, int] = {}
        for i, r in enumerate(rows):
            if r.card_id not in best or sims[i] > sims[best[r.card_id]]:
                best[r.card_id] = i
        ranked = sorted(best.items(), key=lambda kv: -sims[kv[1]])[:limit]
        hits = [SearchHit(by_id[cid], float(sims[i]), rows[i].kind, rows[i].text) for cid, i in ranked]
    t["score_ms"] = (time.perf_counter() - t0) * 1000

    return SearchResult(hits=hits, timings_ms={k: round(v, 3) for k, v in t.items()}, cards_indexed=n_indexed)

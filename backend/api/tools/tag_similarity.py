# backend/api/tools/tag_similarity.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Literal
import threading

import numpy as np

from .tag_normalizer import normalize_and_alias

# Small + common model (downloads once, then cached locally by HF)
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Lazy-loaded singleton embedder (safe with uvicorn reload)
_embedder = None
_lock = threading.Lock()


def _get_embedder():
    global _embedder
    if _embedder is not None:
        return _embedder

    with _lock:
        if _embedder is not None:
            return _embedder

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers is not installed. Run: pip3 install sentence-transformers numpy"
            ) from e

        _embedder = SentenceTransformer(_MODEL_NAME)
        return _embedder


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Returns L2-normalized embeddings as float32, shape: (n, d)
    """
    model = _get_embedder()
    emb = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return emb.astype(np.float32)


def cosine_sim_matrix(query_vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    """
    query_vec: (d,)
    mat: (n, d)
    returns: (n,) cosine similarities
    """
    q = query_vec.astype(np.float32)
    m = mat.astype(np.float32)
    # assume both already L2-normalized => cosine = dot
    return m @ q


@dataclass
class MatchResult:
    input_tag: str
    normalized_tag: str
    best: Optional[Tuple[str, float]]          # (category, score)
    second: Optional[Tuple[str, float]]        # (category, score)
    topk: List[Tuple[str, float]]              # sorted desc


class CategoryIndex:
    """
    In-memory category embedding index.

    - categories: canonical category strings
    - embeddings: L2-normalized matrix aligned with categories
    """

    def __init__(self, categories: List[str]):
        self.categories: List[str] = categories[:]
        self._embeddings: Optional[np.ndarray] = None  # (n,d)

    def rebuild(self) -> None:
        if not self.categories:
            self._embeddings = None
            return
        self._embeddings = embed_texts(self.categories)

    @property
    def embeddings(self) -> Optional[np.ndarray]:
        return self._embeddings

    def ensure_built(self) -> None:
        if self._embeddings is None and self.categories:
            self.rebuild()

    def add_category(self, category: str) -> None:
        category = category.strip()
        if not category:
            return
        if category in self.categories:
            return

        self.categories.append(category)

        new_vec = embed_texts([category])  # (1,d)
        if self._embeddings is None:
            self._embeddings = new_vec
        else:
            self._embeddings = np.vstack([self._embeddings, new_vec])

    def match_tag(self, tag: str, top_k: int = 3) -> MatchResult:
        """
        Returns similarity scores to existing categories.
        No thresholding or decisions in here. Pure signal.
        """
        normalized = normalize_and_alias(tag)

        if not self.categories:
            return MatchResult(tag, normalized, None, None, [])

        self.ensure_built()
        assert self._embeddings is not None

        q = embed_texts([normalized])[0]              # (d,)
        sims = cosine_sim_matrix(q, self._embeddings) # (n,)

        k = min(top_k, len(self.categories))
        idxs = np.argpartition(-sims, kth=k - 1)[:k]
        idxs = idxs[np.argsort(-sims[idxs])]

        topk = [(self.categories[i], float(sims[i])) for i in idxs]
        best = topk[0] if len(topk) >= 1 else None
        second = topk[1] if len(topk) >= 2 else None

        return MatchResult(tag, normalized, best, second, topk)


# ---------------------------
# Decision layer (deterministic)
# ---------------------------

@dataclass
class ResolveResult:
    input_tag: str
    normalized_tag: str
    action: Literal["match", "new", "ambiguous"]
    chosen: Optional[str]
    confidence: float
    margin: float
    topk: List[Tuple[str, float]]


def decide_resolution(
    mr: MatchResult,
    existing_categories: List[str],
    *,
    match_threshold: float = 0.70,
    ambiguous_threshold: float = 0.55,
    new_threshold: float = 0.50,
    margin_threshold: float = 0.08,
) -> ResolveResult:
    """
    Deterministic decision policy.

    - match: clear winner (high score + enough margin), or exact category hit
    - ambiguous: mid score, or close/tied candidates
    - new: low score (not similar enough)
    """

    normalized = (mr.normalized_tag or "").strip()
    if not normalized:
        return ResolveResult(mr.input_tag, mr.normalized_tag, "ambiguous", None, 0.0, 0.0, mr.topk)

    existing_set = set(existing_categories)

    # Exact hit => match immediately (cheap + deterministic)
    if normalized in existing_set:
        return ResolveResult(mr.input_tag, mr.normalized_tag, "match", normalized, 1.0, 1.0, mr.topk)

    if mr.best is None:
        return ResolveResult(mr.input_tag, mr.normalized_tag, "new", normalized, 0.0, 0.0, [])

    best_cat, best_score = mr.best
    second_score = mr.second[1] if mr.second is not None else None
    margin = float(best_score - second_score) if second_score is not None else float(best_score)

    # Very low similarity => new category
    if best_score < new_threshold:
        return ResolveResult(mr.input_tag, mr.normalized_tag, "new", normalized, float(best_score), margin, mr.topk)

    # High confidence + clear winner => match
    if best_score >= match_threshold and margin >= margin_threshold:
        return ResolveResult(mr.input_tag, mr.normalized_tag, "match", best_cat, float(best_score), margin, mr.topk)

    # Mid confidence or "tie" => ambiguous (leave for LLM/manual)
    if best_score >= ambiguous_threshold:
        # if it's a close call, keep ambiguous
        if margin < margin_threshold:
            return ResolveResult(mr.input_tag, mr.normalized_tag, "ambiguous", None, float(best_score), margin, mr.topk)

        # clear-ish winner but below match_threshold => still ambiguous (safer)
        return ResolveResult(mr.input_tag, mr.normalized_tag, "ambiguous", None, float(best_score), margin, mr.topk)

    # In-between zone (>= new_threshold but < ambiguous_threshold)
    return ResolveResult(mr.input_tag, mr.normalized_tag, "ambiguous", None, float(best_score), margin, mr.topk)
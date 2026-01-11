# backend/api/tools/tag_resolver.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .tag_similarity import CategoryIndex, MatchResult, decide_resolution


@dataclass
class ResolvedTag:
    raw: str
    normalized: str
    action: str
    chosen: Optional[str]
    confidence: float
    margin: float
    topk: List[Tuple[str, float]]


def resolve_tags(
    tags: List[str],
    index: CategoryIndex,
    top_k: int = 3,
    learn_new: bool = True,
) -> List[ResolvedTag]:
    out: List[ResolvedTag] = []

    seen_norm: set[str] = set()

    for t in tags:
        mr: MatchResult = index.match_tag(t, top_k=top_k)

        # skip empty or duplicate normalized tags in this batch
        norm = (mr.normalized_tag or "").strip()
        if not norm:
            continue
        if norm in seen_norm:
            continue
        seen_norm.add(norm)

        decision = decide_resolution(mr, index.categories)

        if decision.action == "new" and decision.chosen and learn_new:
            index.add_category(decision.chosen)

        out.append(
            ResolvedTag(
                raw=mr.input_tag,
                normalized=mr.normalized_tag,
                action=decision.action,
                chosen=decision.chosen,
                confidence=decision.confidence,
                margin=decision.margin,
                topk=mr.topk,
            )
        )

    return out
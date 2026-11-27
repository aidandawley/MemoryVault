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
    *,
    keep_ambiguous: bool = False,
    merge_within_batch: bool = True,
    **decision_kwargs,
) -> List[ResolvedTag]:
    """
    Resolve one media item's tags against the category index.

    keep_ambiguous: store an ambiguous tag as its own (new) category instead of
        dropping it.
    merge_within_batch: if False, a tag may not merge into a category that was
        learned from an earlier tag of this same batch. Tags the model returned
        together for one image are meant to be distinct (e.g. "sunrise" and
        "sunset"), so they should not collapse into each other.
    decision_kwargs: threshold overrides passed to decide_resolution.
    """
    out: List[ResolvedTag] = []

    seen_norm: set[str] = set()
    learned_here: set[str] = set()

    for t in tags:
        exclude = None if merge_within_batch else learned_here
        mr: MatchResult = index.match_tag(t, top_k=top_k, exclude=exclude)

        # skip empty or duplicate normalized tags in this batch
        norm = (mr.normalized_tag or "").strip()
        if not norm:
            continue
        if norm in seen_norm:
            continue
        seen_norm.add(norm)

        candidates = index.categories if exclude is None else [c for c in index.categories if c not in exclude]
        decision = decide_resolution(mr, candidates, **decision_kwargs)

        action, chosen = decision.action, decision.chosen
        if action == "ambiguous" and keep_ambiguous:
            action, chosen = "new", norm

        if action == "new" and chosen and learn_new:
            if chosen not in index.categories:
                learned_here.add(chosen)
            index.add_category(chosen)

        out.append(
            ResolvedTag(
                raw=mr.input_tag,
                normalized=mr.normalized_tag,
                action=action,
                chosen=chosen,
                confidence=decision.confidence,
                margin=decision.margin,
                topk=mr.topk,
            )
        )

    return out

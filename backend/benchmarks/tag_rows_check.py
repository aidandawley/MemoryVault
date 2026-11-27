"""Simulate VaultDetail's "Browse by tag" rows against the real DB (read-only).

old: frontend groups cards by tag.trim().toLowerCase() and only shows a row if that
     key equals one of the backend's /top-tags (which are normalize_and_alias'd).
new: frontend groups by the backend-provided normalized_tags.
Run from repo root: python -m backend.benchmarks.tag_rows_check
"""
import json
import sqlite3
import sys
from collections import Counter, defaultdict

from backend.api.tools.tag_normalizer import normalize_and_alias


def rows(cards, top7, key):
    groups = defaultdict(set)
    for cid, tags in cards:
        for t in tags:
            k = key(t)
            if k:
                groups[k].add(cid)
    shown = {t: groups[t] for t in groups if t in top7}
    return shown


def main(db="app.db", vault="Personal"):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cards = [
        (cid, [p.strip() for p in (raw or "").split(",") if p.strip()])
        for cid, raw in con.execute(
            "select c.id, c.tags from cards c join vaults v on v.id=c.vault_id where v.title=?", (vault,)
        )
    ]
    counts = Counter(t for _, tags in cards for t in (normalize_and_alias(x) for x in tags) if t)
    top7 = [t for t, _ in counts.most_common(7)]
    old = rows(cards, top7, lambda t: t.strip().lower())
    new = rows(cards, top7, normalize_and_alias)
    out = {
        "top7_from_backend": top7,
        "old_rows_shown": {k: len(v) for k, v in old.items()},
        "new_rows_shown": {k: len(v) for k, v in new.items()},
        "old_row_count": len(old),
        "new_row_count": len(new),
        "old_card_slots": sum(len(v) for v in old.values()),
        "new_card_slots": sum(len(v) for v in new.values()),
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main(*sys.argv[1:])

"""Offline evaluation of the tag-resolution pipeline against tag_labels.csv.

Replays the 2026-11-27 re-tag run (7 photo cards, 50 raw Gemini tags) through the
real normalize -> CategoryIndex -> resolve_tags code under different settings.
No API calls: the Gemini tags come from benchmarks/data/photo_retag_raw.json and
embeddings come from the local all-MiniLM-L6-v2 model.

Run from repo root:  python -m backend.benchmarks.tag_pipeline_eval [out.json]
"""
from __future__ import annotations

import ast
import csv
import itertools
import json
import os
import sys
from collections import Counter

from backend.api.tools.tag_normalizer import ALIASES, normalize_and_alias
from backend.api.tools.tag_resolver import resolve_tags
from backend.api.tools.tag_similarity import CategoryIndex

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

with open(os.path.join(REPO, "backend", "api", "routers", "cards.py"), encoding="utf-8") as _f:
    for _n in ast.parse(_f.read()).body:
        if isinstance(_n, ast.Assign) and getattr(_n.targets[0], "id", "") == "SEED_CATEGORIES":
            SEED_CATEGORIES = ast.literal_eval(_n.value)


def dedupe(items):
    seen, out = set(), []
    for x in items:
        xx = (x or "").strip()
        if xx and xx not in seen:
            seen.add(xx)
            out.append(xx)
    return out


def load():
    run = json.load(open(os.path.join(HERE, "data", "photo_retag_raw.json"), encoding="utf-8"))
    init = json.load(open(os.path.join(HERE, "data", "retag_initial_state.json"), encoding="utf-8"))
    with open(os.path.join(REPO, "tag_labels.csv"), encoding="utf-8") as f:
        labels = list(csv.DictReader(f))
    return run, init["cards"], labels


def replay(run, vault_cards, **cfg):
    """Returns {(card_id, raw_tag): output or None} and {card_id: stored tags}.

    vault_cards is the vault in SQLite row order; tags are updated in place because
    the top-7 tie-break (Counter.most_common) depends on first occurrence."""
    vault = {c["card_id"]: [p.strip() for p in (c["tags"] or "").split(",") if p.strip()] for c in vault_cards}
    outputs, stored = {}, {}
    for card in run["cards"]:
        existing = vault[card["card_id"]]
        vault_tags = [t for tags in vault.values() for t in tags]
        counts = Counter(t for t in (normalize_and_alias(x) for x in vault_tags) if t)
        cats = dedupe([*SEED_CATEGORIES, *[t for t, _ in counts.most_common(7)]])
        index = CategoryIndex(cats)
        index.rebuild()
        resolved = resolve_tags(dedupe([*card["ai_tags"], *existing]), index, top_k=3, learn_new=True, **cfg)
        for r in resolved:
            outputs[(card["card_id"], r.raw)] = r.chosen if r.action in ("match", "new") else None
        final = dedupe([r.chosen for r in resolved if r.action in ("match", "new") and r.chosen])
        stored[card["card_id"]] = final
        vault[card["card_id"]] = final  # the card's old tags are replaced in place
    return outputs, stored


def score(outputs, stored, labels):
    s = Counter()
    for row in labels:
        out = outputs.get((row["card_id"], row["raw_tag"]))
        acc = set(row["acceptable_outputs"].split("|")) - {""}
        merged = out is not None and out != normalize_and_alias(row["raw_tag"])
        if out is None:
            s["useful_dropped" if acc else "correctly_dropped"] += 1
            continue
        s["tags_kept"] += 1
        if out in acc:
            s["correct"] += 1
            if merged:
                s["correct_merges"] += 1
        else:
            s["incorrect_merges"] += 1
    s["stored_tags"] = sum(len(v) for v in stored.values())
    s["unique_stored_tags"] = len({t for v in stored.values() for t in v})
    for k in ("tags_kept", "correct", "correct_merges", "incorrect_merges", "useful_dropped", "correctly_dropped"):
        s.setdefault(k, 0)
    s["accuracy"] = round(s["correct"] / len(labels), 4)
    return dict(s)


def alias_idempotence_failures():
    """Alias targets that normalize_and_alias does not map to themselves.
    e.g. "best friends" -> "friends", but "friends" -> "friend": one concept, two tags."""
    return sorted(v for v in set(ALIASES.values()) if normalize_and_alias(v) != v)


def main(out_path=None):
    run, vault_cards, labels = load()
    results = {"n_labels": len(labels), "label_counts": dict(Counter(r["label"] for r in labels))}

    # 0) sanity: replaying the baseline must reproduce the recorded run exactly
    outputs, stored = replay(run, vault_cards)
    recorded = {c["card_id"]: c["final_tags"] for c in run["cards"]}
    results["baseline_replay_matches_recorded_run"] = stored == recorded
    if stored != recorded:
        print("WARNING: baseline replay differs from the recorded run", file=sys.stderr)

    raw_unique = {t.strip().lower() for c in run["cards"] for t in c["ai_tags"]}
    # Settings are explicit so the results don't change when production defaults do.
    OLD = {"keep_ambiguous": False, "merge_within_batch": True}
    NEW = {"keep_ambiguous": True, "merge_within_batch": False}
    configs = {
        "baseline": dict(OLD),
        "keep_ambiguous": {**OLD, "keep_ambiguous": True},
        "no_merge_within_batch": {**OLD, "merge_within_batch": False},
        "keep_ambiguous+no_merge_within_batch": dict(NEW),
    }
    results["configs"] = {}
    for name, cfg in configs.items():
        o, s = replay(run, vault_cards, **cfg)
        results["configs"][name] = {"settings": cfg, **score(o, s, labels)}

    grid = list(itertools.product((0.60, 0.65, 0.70, 0.75, 0.80), (0.0, 0.04, 0.08, 0.12), (0.40, 0.50, 0.60)))
    for key, flags in (("threshold_sweep", OLD), ("threshold_sweep_on_new_flags", NEW)):
        sweep = []
        for mt, mg, nt in grid:
            if nt > mt:
                continue
            cfg = {**flags, "match_threshold": mt, "margin_threshold": mg, "new_threshold": nt,
                   "ambiguous_threshold": max(nt, min(0.55, mt))}
            o, s = replay(run, vault_cards, **cfg)
            sweep.append({"settings": cfg, **score(o, s, labels)})
        results[key] = sweep

    results["unique_raw_gemini_tags"] = len(raw_unique)
    results["alias_idempotence_failures"] = alias_idempotence_failures()

    text = json.dumps(results, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
    return results


if __name__ == "__main__":
    r = main(*sys.argv[1:])
    print("baseline replay matches recorded run:", r["baseline_replay_matches_recorded_run"])
    keys = ("tags_kept", "correct", "correct_merges", "incorrect_merges", "useful_dropped", "unique_stored_tags", "accuracy")
    print(f"{'config':45}" + "".join(f"{k[:14]:>15}" for k in keys))
    for name, s in r["configs"].items():
        print(f"{name:45}" + "".join(f"{s[k]:>15}" for k in keys))
    for key in ("threshold_sweep", "threshold_sweep_on_new_flags"):
        print(f"\n{key} (match, margin, new):")
        for s in r[key]:
            c = s["settings"]
            print(f"  {c['match_threshold']:.2f} {c['margin_threshold']:.2f} {c['new_threshold']:.2f}"
                  + "".join(f"{s[k]:>15}" for k in keys))
    print("\nunique raw Gemini tags:", r["unique_raw_gemini_tags"])
    print("alias idempotence failures:", r["alias_idempotence_failures"])

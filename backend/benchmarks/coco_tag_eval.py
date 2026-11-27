"""Tag-pipeline evaluation on the COCO eval set, scored against COCO's human annotations.

Replays the 50 recorded Gemini outputs (data/coco_eval_uploads.json) through the tag
pipeline exactly as create_card does (seed categories + the vault's top-7, cards in
upload order), under the old and new settings. No API calls.

Configs:
  raw          Gemini's tags, lowercased; no pipeline (reference)
  old          before this branch: ambiguous tags dropped, merges into same-photo tags
               allowed, alias targets singularized
  +keep_ambiguous / +no_same_photo_merge / +alias_fix   one change at a time on top of old
  new          all three (production)

Metrics (per image, averaged; "grounded" = supported by COCO's human annotations):
  category_recall           share of the image's COCO categories named by some stored tag
  prominent_category_recall same, only categories covering >= 5% of the image
  tag_precision             share of stored tags with a content word in the 5 human captions
                            or naming one of the image's COCO categories
  grounded_tags_lost        raw Gemini tags that were grounded but have no stored counterpart
                            (dropped as ambiguous, or merged into a tag and de-duplicated away)
  merges / bad_merges       tags stored under a different name than their normalized form;
                            bad = the raw tag was grounded but the stored name is not (automatic,
                            lenient: "street" -> "street sign" passes because both say "street")
  merge_audit (manual)      every merge labeled good / shift / wrong in data/coco_merge_audit.csv
                            (our judgment, written after seeing the merges; see LEARNING.md)
  unique_tags_in_vault      how many distinct tags the vault ends up with

Run from repo root:  python -m backend.benchmarks.coco_tag_eval [out.json]
"""
from __future__ import annotations

import ast
import contextlib
import json
import os
import re
import statistics
import sys
from collections import Counter

from backend.api.tools import tag_normalizer
from backend.api.tools.tag_normalizer import normalize_and_alias
from backend.api.tools.tag_resolver import resolve_tags
from backend.api.tools.tag_similarity import CategoryIndex
from backend.benchmarks import coco_eval

with open(os.path.join(coco_eval.REPO, "backend", "api", "routers", "cards.py"), encoding="utf-8") as _f:
    for _n in ast.parse(_f.read()).body:
        if isinstance(_n, ast.Assign) and getattr(_n.targets[0], "id", "") == "SEED_CATEGORIES":
            SEED_CATEGORIES = ast.literal_eval(_n.value)

# Words that name a COCO category besides the category name itself. Fixed before looking at
# results: the synonyms already used as search queries, plus common words for a person.
CATEGORY_WORDS = {
    "person": {"person", "people", "man", "men", "woman", "women", "boy", "girl", "child", "children", "kid",
               "toddler", "player", "surfer", "rider", "passenger", "crowd", "officer", "team", "individual"},
    "dog": {"pup", "puppy", "collie", "beagle"}, "cat": {"kitty", "kitten"}, "car": {"automobile"},
    "bicycle": {"bike"}, "airplane": {"plane", "aircraft", "airliner", "jet"}, "couch": {"sofa"},
    "dining table": {"table"}, "toilet": {"loo", "urinal"}, "tennis racket": {"racquet", "racket"},
    "handbag": {"purse"}, "backpack": {"rucksack"}, "laptop": {"notebook"}, "truck": {"lorry"},
    "traffic light": {"stoplight"}, "sink": {"washbasin"}, "frisbee": {"disc"}, "motorcycle": {"motorbike", "scooter"},
    "tv": {"television"}, "cell phone": {"phone", "smartphone"},
}
STOP = {"a", "an", "the", "of", "in", "on", "with", "and", "or", "to", "at", "for", "by", "from", "is", "are",
        "it", "its", "his", "her", "their", "some", "two", "three", "one", "very", "near", "next", "this", "that"}
PROMINENT = 0.05


def singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("sses", "shes", "ches", "xes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def words(text: str) -> set[str]:
    return {singular(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def names_category(tag: str, cat: str) -> bool:
    tw = words(tag)
    cat_words = {singular(w) for w in cat.split()}
    if cat_words <= tw:  # all words of the category name appear in the tag ("red car" names car)
        return True
    return bool(tw & {singular(w) for w in CATEGORY_WORDS.get(cat, set())})


def grounded(tag: str, image: dict, caption_words: set[str]) -> bool:
    return bool(words(tag) & caption_words) or any(names_category(tag, c) for c in image["categories"])


@contextlib.contextmanager
def old_normalizer():
    """Before the alias fix, alias targets were singularized ("friends" -> "friend")."""
    saved = tag_normalizer.ALIAS_TARGETS
    tag_normalizer.ALIAS_TARGETS = frozenset()
    try:
        yield
    finally:
        tag_normalizer.ALIAS_TARGETS = saved


def dedupe(items):
    seen, out = set(), []
    for x in items:
        xx = (x or "").strip()
        if xx and xx not in seen:
            seen.add(xx)
            out.append(xx)
    return out


def replay(uploads, keep_ambiguous, merge_within_batch, alias_fix):
    """Returns {card_id: [(raw_tag, stored_name_or_None)]} and {card_id: stored tags}."""
    ctx = contextlib.nullcontext() if alias_fix else old_normalizer()
    vault: list[tuple[str, list[str]]] = []  # newest first, like card_service.list_cards
    mapping, stored = {}, {}
    with ctx:
        for u in uploads:
            counts = Counter(t for _, tags in vault for t in (normalize_and_alias(x) for x in tags) if t)
            cats = dedupe([*SEED_CATEGORIES, *[t for t, _ in counts.most_common(7)]])
            index = CategoryIndex(cats)
            index.rebuild()
            resolved = resolve_tags(dedupe(u["raw_tags"]), index, top_k=3, learn_new=True,
                                    keep_ambiguous=keep_ambiguous, merge_within_batch=merge_within_batch)
            by_raw = {r.raw: (r.chosen if r.action in ("match", "new") else None) for r in resolved}
            mapping[u["card_id"]] = [(t, by_raw.get(t, "__dup__")) for t in u["raw_tags"]]
            final = dedupe([r.chosen for r in resolved if r.action in ("match", "new") and r.chosen])
            stored[u["card_id"]] = final
            vault.insert(0, (u["card_id"], final))
    return mapping, stored


def load_merge_audit():
    import csv
    path = os.path.join(coco_eval.HERE, "data", "coco_merge_audit.csv")
    with open(path, encoding="utf-8") as f:
        return {(r["raw_tag"], r["merged_into"]): r["label"] for r in csv.DictReader(f)}


AUDIT = load_merge_audit()


def score(images, uploads, mapping, stored, count_merges=True):
    audit = Counter()
    per = []
    merges = bad_merges = lost = 0
    bad_examples, lost_examples = [], []
    for u in uploads:
        im = images[u["image_id"]]
        cw = set().union(*(words(c) for c in im["captions"]))
        tags = stored[u["card_id"]]
        cats = im["categories"]
        prom = [c for c in cats if im["category_area_fraction"][c] >= PROMINENT]
        per.append({
            "category_recall": sum(any(names_category(t, c) for t in tags) for c in cats) / len(cats),
            "prominent_category_recall": (sum(any(names_category(t, c) for t in tags) for c in prom) / len(prom)) if prom else None,
            "tag_precision": (sum(grounded(t, im, cw) for t in tags) / len(tags)) if tags else 0.0,
            "tags": len(tags),
        })
        stored_set = set(tags)
        for raw, out in mapping[u["card_id"]]:
            raw_ok = grounded(raw, im, cw)
            norm = normalize_and_alias(raw)
            if count_merges and out not in (None, "__dup__") and out != norm:
                merges += 1
                audit[AUDIT.get((raw, out), "unaudited")] += 1
                if raw_ok and not grounded(out, im, cw):
                    bad_merges += 1
                    bad_examples.append(f"{u['image_id']}: {raw} -> {out}")
            if raw_ok and not any(words(raw) & words(s) for s in stored_set):
                lost += 1
                lost_examples.append(f"{u['image_id']}: {raw}")
    avg = lambda k: round(statistics.mean(p[k] for p in per if p[k] is not None), 4)
    return {
        "category_recall": avg("category_recall"),
        "prominent_category_recall": avg("prominent_category_recall"),
        "tag_precision": avg("tag_precision"),
        "tags_per_image": avg("tags"),
        "grounded_tags_lost": lost,
        "merges": merges,
        "bad_merges": bad_merges,
        "merge_audit (manual)": {k: audit.get(k, 0) for k in ("good", "shift", "wrong", "unaudited")},
        "unique_tags_in_vault": len({t for v in stored.values() for t in v}),
        "bad_merge_examples": bad_examples,
        "lost_examples": lost_examples,
    }


def main(out_path=None):
    spec = json.load(open(coco_eval.EVAL_SET, encoding="utf-8"))
    rec = json.load(open(coco_eval.UPLOADS, encoding="utf-8"))
    images = {im["image_id"]: im for im in spec["images"]}
    uploads = [u for u in rec["uploads"] if u["status"] == "ok"]

    configs = {
        "old": dict(keep_ambiguous=False, merge_within_batch=True, alias_fix=False),
        "old+keep_ambiguous": dict(keep_ambiguous=True, merge_within_batch=True, alias_fix=False),
        "old+no_same_photo_merge": dict(keep_ambiguous=False, merge_within_batch=False, alias_fix=False),
        "old+alias_fix": dict(keep_ambiguous=False, merge_within_batch=True, alias_fix=True),
        "new": dict(keep_ambiguous=True, merge_within_batch=False, alias_fix=True),
    }
    res = {"n_images": len(uploads), "configs": {}}
    raw_stored = {u["card_id"]: dedupe([t.lower() for t in u["raw_tags"]]) for u in uploads}
    raw_map = {u["card_id"]: [(t, t.lower()) for t in u["raw_tags"]] for u in uploads}
    res["configs"]["raw (no pipeline)"] = score(images, uploads, raw_map, raw_stored, count_merges=False)
    for name, cfg in configs.items():
        mapping, stored = replay(uploads, **cfg)
        res["configs"][name] = {"settings": cfg, **score(images, uploads, mapping, stored)}
        if name == "new":
            recorded = {u["card_id"]: u["stored_tags"] for u in uploads}
            diffs = [cid for cid in recorded if recorded[cid] != stored[cid]]
            res["new_replay_matches_stored_tags"] = not diffs
            res["new_replay_diff_card_ids"] = diffs
    if out_path:
        json.dump(res, open(out_path, "w", encoding="utf-8"), indent=2)
    return res


if __name__ == "__main__":
    r = main(*sys.argv[1:])
    print("new replay matches tags stored by the real upload pipeline:", r["new_replay_matches_stored_tags"])
    keys = ("category_recall", "prominent_category_recall", "tag_precision", "tags_per_image",
            "grounded_tags_lost", "merges", "bad_merges", "unique_tags_in_vault")
    print(f"{'config':26}" + "".join(f"{k[:13]:>14}" for k in keys))
    for name, s in r["configs"].items():
        print(f"{name:26}" + "".join(f"{s[k]:>14}" for k in keys))
    print("\nmanual merge audit (good / shift / wrong / unaudited):")
    for name, s in r["configs"].items():
        print(f"  {name:26}", s["merge_audit (manual)"])
    for name in ("old", "new"):
        print(f"\n{name} bad merges:", r["configs"][name]["bad_merge_examples"])
        print(f"{name} grounded tags lost:", r["configs"][name]["lost_examples"])

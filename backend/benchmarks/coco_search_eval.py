"""Search evaluation on the COCO eval vault, with COCO's human annotations as ground truth.

A result is relevant iff COCO's instance annotations label that image with the query's
category. Compares semantic vs keyword search (precision@5, recall@5, top-1 accuracy) and
measures latency of both over real HTTP. No paid API calls: the server only embeds
queries with the local MiniLM model. Runs against eval.db (rebuilt from recorded uploads
if missing); the demo database is never read, so its duplicate photos can't leak in.

Run from repo root:  python -m backend.benchmarks.coco_search_eval [out.json]
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

import httpx

from backend.benchmarks import coco_eval

K = 5
LATENCY_ROUNDS = 3  # every query, per mode


def pct(xs, p):
    xs = sorted(xs)
    i = (len(xs) - 1) * p / 100
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (i - lo), 3)


def summarize(rows, key):
    out = {}
    for m in ("precision_at_5", "precision_at_5_ceiling", "recall_at_5", "recall_at_5_ceiling", "top1_accuracy"):
        out[m] = round(statistics.mean(r[key][m] for r in rows), 4)
    return out


def main(out_path=None):
    spec = json.load(open(coco_eval.EVAL_SET, encoding="utf-8"))
    rec = json.load(open(coco_eval.UPLOADS, encoding="utf-8"))
    queries = json.load(open(os.path.join(coco_eval.HERE, "data", "coco_search_queries.json"), encoding="utf-8"))["queries"]
    if not os.path.exists(coco_eval.EVAL_DB):
        coco_eval.cmd_rebuild(None)

    cats_by_image = {im["image_id"]: set(im["categories"]) for im in spec["images"]}
    image_by_card = {u["card_id"]: u["image_id"] for u in rec["uploads"] if u["status"] == "ok"}

    per_query, lat = [], {"semantic": [], "keyword": []}
    with coco_eval.EvalServer({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_VERBOSITY": "error"}) as srv, httpx.Client(timeout=60) as c:
        vid = coco_eval.eval_vault_id(c, srv.base)
        cards = c.get(f"{srv.base}/api/vaults/{vid}/cards").json()
        assert {x["cardId"] for x in cards} == set(image_by_card), "eval vault must contain exactly the COCO cards"

        def search(q, mode):
            t = time.perf_counter()
            r = c.get(f"{srv.base}/api/vaults/{vid}/search", params={"q": q, "limit": K, "mode": mode})
            total = (time.perf_counter() - t) * 1000
            r.raise_for_status()
            return r.json(), total

        search("warm up", "semantic")  # builds embeddings if eval.db was just rebuilt
        for q in queries:
            relevant = {img for img, cats in cats_by_image.items() if q["category"] in cats}
            row = {**q, "n_relevant": len(relevant)}
            for mode in ("semantic", "keyword"):
                j, _ = search(q["query"], mode)
                ids = [image_by_card[h["cardId"]] for h in j["results"]]
                hits = sum(1 for i in ids if i in relevant)
                row[mode] = {
                    "precision_at_5": hits / K,
                    "precision_at_5_ceiling": min(len(relevant), K) / K,
                    "recall_at_5": hits / len(relevant),
                    "recall_at_5_ceiling": min(len(relevant), K) / len(relevant),
                    "top1_accuracy": 1.0 if ids and ids[0] in relevant else 0.0,
                    "n_results": len(ids),
                    "top5": [{"image_id": i, "relevant": i in relevant, "score": h["score"], "matched": h["matched"]["text"]}
                             for i, h in zip(ids, j["results"])],
                }
            per_query.append(row)

        for _ in range(LATENCY_ROUNDS):
            for q in queries:
                for mode in ("semantic", "keyword"):
                    j, total = search(q["query"], mode)
                    lat[mode].append({"total_ms": total, **{f"{k}": v for k, v in j["timings_ms"].items()}})

    def lat_summary(samples):
        keys = samples[0].keys()
        return {"n_requests": len(samples),
                **{k: {"p50": pct([s[k] for s in samples], 50), "p95": pct([s[k] for s in samples], 95)} for k in keys}}

    res = {
        "k": K,
        "n_images": len(cats_by_image),
        "n_queries": len(per_query),
        "summary": {
            mode: {
                "all": summarize(per_query, mode),
                "category_names": summarize([r for r in per_query if r["type"] == "category_name"], mode),
                "synonyms": summarize([r for r in per_query if r["type"] == "synonym"], mode),
                "queries_with_zero_results": sum(1 for r in per_query if r[mode]["n_results"] == 0),
            }
            for mode in ("semantic", "keyword")
        },
        "latency_ms": {mode: lat_summary(s) for mode, s in lat.items()},
        "per_query": per_query,
    }
    if out_path:
        json.dump(res, open(out_path, "w", encoding="utf-8"), indent=2)
    return res


if __name__ == "__main__":
    r = main(*sys.argv[1:])
    print(f"{'query':20}{'type':>14}{'rel':>5} | {'sem P@5':>8}{'R@5':>6}{'top1':>5} | {'kw P@5':>7}{'R@5':>6}{'top1':>5}")
    for row in r["per_query"]:
        s, k = row["semantic"], row["keyword"]
        print(f"{row['query']:20}{row['type']:>14}{row['n_relevant']:>5} | {s['precision_at_5']:>8.2f}{s['recall_at_5']:>6.2f}{s['top1_accuracy']:>5.0f}"
              f" | {k['precision_at_5']:>7.2f}{k['recall_at_5']:>6.2f}{k['top1_accuracy']:>5.0f}")
    print(json.dumps(r["summary"], indent=2))
    print(json.dumps(r["latency_ms"], indent=2))

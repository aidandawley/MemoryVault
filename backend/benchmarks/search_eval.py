"""Search quality and latency benchmark. No paid API calls (local MiniLM only).

Quality: precision@5, recall@5 and hit@1 for the 15 pre-registered queries in
data/search_queries.json, for three rankers:
  - semantic_maxsim  (production: max cosine over caption + each normalized tag)
  - semantic_concat  (comparison: one vector for "caption. tag, tag, ...")
  - keyword          (baseline: exact normalized-tag match or caption substring)
Latency: real HTTP requests to a uvicorn server; per-stage server timings come from
the Server-Timing header (db, index, embed, score).

Everything runs on a temporary copy of app.db; the repo's app.db is not modified.
Run from repo root:  python -m backend.benchmarks.search_eval [out.json]
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TMP = tempfile.mkdtemp(prefix="mv-search-eval-")
DB_COPY = os.path.join(TMP, "app.db")
shutil.copyfile(os.path.join(REPO, "app.db"), DB_COPY)
os.environ["DATABASE_URL"] = f"sqlite:///{DB_COPY}"  # must be set before backend imports

import httpx  # noqa: E402
import numpy as np  # noqa: E402

from backend.api.tools.tag_normalizer import normalize_and_alias  # noqa: E402
from backend.api.tools.tag_similarity import embed_texts  # noqa: E402
from backend.db.connect_db import connect_db  # noqa: E402
from backend.db.session import SessionLocal, engine  # noqa: E402
from backend.services import card_service, search_service  # noqa: E402

K = 5
LATENCY_ROUNDS = 10  # each of the 15 queries this many times


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    i = (len(xs) - 1) * p / 100
    lo, hi = int(np.floor(i)), int(np.ceil(i))
    return round(xs[lo] + (xs[hi] - xs[lo]) * (i - lo), 3)


def metrics(ranked_ids, relevant):
    top = ranked_ids[:K]
    hits = sum(1 for c in top if c in relevant)
    return {
        "precision_at_5": hits / K,
        "precision_at_5_ceiling": min(len(relevant), K) / K,
        "recall_at_5": hits / len(relevant),
        "hit_at_1": 1.0 if top and top[0] in relevant else 0.0,
    }


def rank_keyword(cards, q):
    nq = normalize_and_alias(q)
    words = q.lower().split()
    out = []
    for c in cards:
        tags = card_service.normalized_tags(card_service._parse_tags(c.tags))
        cap = (c.caption or "").lower()
        if nq in tags or all(w in cap for w in words):
            out.append(c.id)
    return out


def rank_concat(cards, q):
    texts = [f"{c.caption}. {', '.join(card_service.normalized_tags(card_service._parse_tags(c.tags)))}" for c in cards]
    m = embed_texts(texts)
    s = m @ embed_texts([q])[0]
    return [cards[i].id for i in np.argsort(-s)]


def quality(spec):
    db = SessionLocal()
    try:
        vault_id = db.execute(
            __import__("sqlalchemy").text("select id from vaults where title='Personal'")
        ).scalar_one()
        cards = card_service.list_cards(db, vault_id)
        per_query, agg = [], {}
        for item in spec["queries"]:
            q, rel = item["query"], set(item["relevant"])
            res = search_service.search_vault(db, vault_id, q, limit=K)
            rankers = {
                "semantic_maxsim": [h.card.id for h in res.hits],
                "semantic_concat": rank_concat(cards, q),
                "keyword": rank_keyword(cards, q),
            }
            row = {"query": q, "relevant_captions": item["relevant_captions"],
                   "maxsim_top5": [{"caption": h.card.caption, "score": round(h.score, 3),
                                    "matched": h.matched_text, "relevant": h.card.id in rel} for h in res.hits]}
            for name, ids in rankers.items():
                row[name] = metrics(ids, rel)
                for k, v in row[name].items():
                    agg.setdefault(name, {}).setdefault(k, []).append(v)
            per_query.append(row)
        summary = {name: {k: round(statistics.mean(v), 4) for k, v in m.items()} for name, m in agg.items()}
        return vault_id, per_query, summary
    finally:
        db.close()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def latency(vault_id, queries):
    port = free_port()
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_VERBOSITY": "error"}
    log = open(os.path.join(TMP, "uvicorn.log"), "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        t0 = time.perf_counter()
        with httpx.Client(timeout=60) as c:
            while True:
                try:
                    if c.get(f"{base}/api/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if proc.poll() is not None or time.perf_counter() - t0 > 180:
                    raise RuntimeError("uvicorn did not start; see " + log.name)
                time.sleep(0.25)
            startup_s = time.perf_counter() - t0

            # first-ever search on a vault with no stored embeddings: includes indexing all cards
            with engine.begin() as conn:
                conn.exec_driver_sql("delete from card_embeddings")
            t = time.perf_counter()
            r = c.get(f"{base}/api/vaults/{vault_id}/search", params={"q": queries[0], "limit": K})
            cold = {"total_ms": round((time.perf_counter() - t) * 1000, 3), "server": r.json()["timings_ms"],
                    "cards_indexed": r.json()["cards_indexed"]}

            for q in queries[:5]:  # warm-up, not measured
                c.get(f"{base}/api/vaults/{vault_id}/search", params={"q": q, "limit": K})

            samples = []
            for _ in range(LATENCY_ROUNDS):
                for q in queries:
                    t = time.perf_counter()
                    r = c.get(f"{base}/api/vaults/{vault_id}/search", params={"q": q, "limit": K})
                    total = (time.perf_counter() - t) * 1000
                    r.raise_for_status()
                    stages = {p.split(";")[0].strip(): float(p.split("dur=")[1]) for p in r.headers["server-timing"].split(",")}
                    samples.append({"total_ms": total, **{f"{k}_ms": v for k, v in stages.items()}})
    finally:
        proc.terminate()
        proc.wait(timeout=30)
        log.close()

    keys = list(samples[0])
    out = {"n_requests": len(samples), "server_startup_incl_model_load_s": round(startup_s, 3), "first_search_cold_index": cold}
    for k in keys:
        xs = [s[k] for s in samples]
        out[k] = {"p50": pct(xs, 50), "p95": pct(xs, 95), "mean": round(statistics.mean(xs), 3)}
    stage_sum = [s["db_ms"] + s["index_ms"] + s["embed_ms"] + s["score_ms"] for s in samples]
    other = [s["total_ms"] - st for s, st in zip(samples, stage_sum)]
    out["other_ms (http, routing, serialization)"] = {"p50": pct(other, 50), "p95": pct(other, 95), "mean": round(statistics.mean(other), 3)}
    return out


def main(out_path=None):
    spec = json.load(open(os.path.join(HERE, "data", "search_queries.json"), encoding="utf-8"))
    connect_db()  # creates card_embeddings in the copy
    vault_id, per_query, summary = quality(spec)
    lat = latency(vault_id, [q["query"] for q in spec["queries"]])
    res = {"k": K, "n_queries": len(per_query), "summary": summary, "latency": lat, "per_query": per_query}
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
    shutil.rmtree(TMP, ignore_errors=True)
    return res


if __name__ == "__main__":
    r = main(*sys.argv[1:])
    print(f"{'query':18}{'P@5':>6}{'ceil':>6}{'R@5':>6}{'hit@1':>6} | keyword P@5 | concat P@5 | top-5 (maxsim)")
    for row in r["per_query"]:
        m = row["semantic_maxsim"]
        tops = ", ".join(f"{'+' if h['relevant'] else '-'}{h['caption']}<{h['matched']}>" for h in row["maxsim_top5"])
        print(f"{row['query']:18}{m['precision_at_5']:>6.2f}{m['precision_at_5_ceiling']:>6.2f}{m['recall_at_5']:>6.2f}"
              f"{m['hit_at_1']:>6.0f} | {row['keyword']['precision_at_5']:>11.2f} | {row['semantic_concat']['precision_at_5']:>10.2f} | {tops}")
    print("\nsummary:", json.dumps(r["summary"], indent=2))
    print("latency:", json.dumps(r["latency"], indent=2))

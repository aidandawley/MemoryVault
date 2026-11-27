"""Run every benchmark and write benchmark_results.json at the repo root. No paid API calls.

Quality metrics come only from the COCO val2017 eval set (50 images, human annotations as
ground truth). The demo vault (8 photos = 2 distinct images) is excluded from every quality
metric; it's only used for the tag-row bug check.

Needs nothing beyond the repo: COCO images are re-downloaded (free) if missing, and eval.db
is rebuilt from the recorded uploads (no Gemini calls) if missing.

Run from repo root:  python -m backend.benchmarks.run_all
"""
import json
import os
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone

from backend.api.tools.tag_normalizer import normalize_and_alias
from backend.benchmarks import coco_eval, coco_search_eval, coco_tag_eval, tag_rows_check

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def pre_branch_db():
    """app.db as of commit 6edd022 (main before this branch), extracted from git."""
    path = os.path.join(tempfile.mkdtemp(prefix="mv-bench-"), "app_6edd022.db")
    with open(path, "wb") as f:
        f.write(subprocess.run(["git", "show", "6edd022:app.db"], cwd=REPO, check=True, capture_output=True).stdout)
    return path


def demo_dataset_stats(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("select media_type, tags from cards").fetchall()
    raw = [t.strip() for _, tags in rows for t in (tags or "").split(",") if t.strip()]
    return {
        "cards": len(rows),
        "by_media_type": dict(Counter(m for m, _ in rows)),
        "cards_with_tags": sum(1 for _, t in rows if (t or "").strip()),
        "unique_stored_tags_as_written": len(set(raw)),
        "unique_tags_after_normalize_and_alias": len({normalize_and_alias(t) for t in raw}),
    }


def stats(xs):
    xs = sorted(xs)
    pct = lambda p: round(xs[min(len(xs) - 1, round((len(xs) - 1) * p / 100))], 3)
    return {"n": len(xs), "median_s": round(statistics.median(xs), 3), "mean_s": round(statistics.mean(xs), 3),
            "p95_s": pct(95), "min_s": round(xs[0], 3), "max_s": round(xs[-1], 3)}


def coco_upload_timings():
    rec = json.load(open(coco_eval.UPLOADS, encoding="utf-8"))
    ok = [u for u in rec["uploads"] if u["status"] == "ok"]
    return {
        "what": "end-to-end POST /api/vaults/{id}/cards per photo (Gemini tagging + tag resolution + DB + search indexing), localhost",
        "gemini_calls": rec["gemini_calls"],
        "successful_uploads": len(ok),
        "upload_seconds": stats([u["upload_s"] for u in ok]),
        "video_tagging": "not measured: no TWELVELABS_API_KEY available",
    }


def main():
    if not all(os.path.exists(os.path.join(coco_eval.IMG_DIR, im["file_name"]))
               for im in json.load(open(coco_eval.EVAL_SET, encoding="utf-8"))["images"]):
        coco_eval.cmd_download(None)

    results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "machine": platform.platform(),
        "python": platform.python_version(),
        "paid_api_calls_made_by_this_script": 0,
        "coco_eval": {
            "dataset": "50 COCO val2017 images (data/coco_eval_set.json), human annotations as ground truth; "
                       "separate 'COCO eval' vault in eval.db",
            "photo_upload_latency": coco_upload_timings(),
            "search": coco_search_eval.main(),
            "tag_pipeline": coco_tag_eval.main(),
        },
        "demo_vault (excluded from quality metrics)": {
            "note": "8 photo cards are 2 distinct images (5 + 3 byte-identical copies); used only for the tag-row bug check",
            "dataset_before_branch (6edd022)": demo_dataset_stats(pre_branch_db()),
            "dataset_current": demo_dataset_stats(os.path.join(REPO, "app.db")),
            "tag_rows_bug_check": {
                "before_branch_db": tag_rows_check.main(pre_branch_db()),
                "current_db": tag_rows_check.main(os.path.join(REPO, "app.db")),
            },
        },
    }
    out = os.path.join(REPO, "benchmark_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())

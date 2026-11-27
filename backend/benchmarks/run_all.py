"""Run every free benchmark and write benchmark_results.json at the repo root.

No paid API calls. Photo-tagging timings are read from the recorded Gemini run
(data/photo_retag_raw.json); re-measuring them needs Gemini calls
(see the reproduce section of LEARNING.md).

Run from repo root:  python -m backend.benchmarks.run_all
"""
import json
import os
import platform
import sqlite3
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

from backend.benchmarks import search_eval, tag_pipeline_eval, tag_rows_check
from backend.api.tools.tag_normalizer import normalize_and_alias

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def pre_retag_db():
    """app.db as of commit 6edd022 (main before this branch), extracted from git."""
    import subprocess
    import tempfile
    path = os.path.join(tempfile.mkdtemp(prefix="mv-bench-"), "app_6edd022.db")
    with open(path, "wb") as f:
        f.write(subprocess.run(["git", "show", "6edd022:app.db"], cwd=REPO, check=True, capture_output=True).stdout)
    return path


def dataset_stats(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("select media_type, tags from cards").fetchall()
    raw = [t.strip() for _, tags in rows for t in (tags or "").split(",") if t.strip()]
    return {
        "cards": len(rows),
        "by_media_type": dict(Counter(m for m, _ in rows)),
        "cards_with_tags": sum(1 for _, t in rows if (t or "").strip()),
        "stored_tag_strings": len(raw),
        "unique_stored_tags_as_written": len(set(raw)),
        "unique_tags_after_normalize_and_alias": len({normalize_and_alias(t) for t in raw}),
    }


def tagging_timings():
    run = json.load(open(os.path.join(HERE, "data", "photo_retag_raw.json"), encoding="utf-8"))
    g = [c["gemini_s"] for c in run["cards"]]
    r = [c["resolve_s"] for c in run["cards"]]
    summ = lambda xs: {"n": len(xs), "median_s": round(statistics.median(xs), 3), "mean_s": round(statistics.mean(xs), 3),
                       "min_s": round(min(xs), 3), "max_s": round(max(xs), 3)}
    return {
        "source": "recorded run " + run["run_at_utc"] + " (" + run["gemini_model"] + "), single run on " + run["machine"],
        "gemini_call": summ(g),
        "gemini_call_excluding_first": summ(g[1:]),
        "local_tag_resolution": summ(r),
        "video_tagging": "not measured: no TWELVELABS_API_KEY available",
    }


def main():
    db = os.path.join(REPO, "app.db")
    results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "machine": platform.platform(),
        "python": platform.python_version(),
        "paid_api_calls_made_by_this_script": 0,
        "dataset": {"before_this_branch (6edd022)": dataset_stats(pre_retag_db()), "current": dataset_stats(db)},
        "photo_tagging_latency": tagging_timings(),
        "tag_rows": {
            "before_retag_db (git 6edd022:app.db)": tag_rows_check.main(pre_retag_db()),
            "current_db": tag_rows_check.main(db),
        },
        "tag_pipeline": tag_pipeline_eval.main(),
        "search": search_eval.main(),
    }
    out = os.path.join(REPO, "benchmark_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())

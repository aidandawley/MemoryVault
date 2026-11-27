"""Re-resolve the 7 re-tagged cards from their recorded Gemini output with the
current pipeline and write the result to app.db. No API calls.

Run from repo root:  python -m backend.benchmarks.reresolve_retagged
"""
import sqlite3
from datetime import datetime, timezone

from backend.benchmarks.tag_pipeline_eval import load, replay


def main(db="app.db"):
    run, vault_cards, _ = load()
    _, stored = replay(run, vault_cards)  # production defaults
    con = sqlite3.connect(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
    for card_id, tags in stored.items():
        old = con.execute("select tags from cards where id=?", (card_id,)).fetchone()[0]
        con.execute("update cards set tags=?, updated_at=? where id=?", (",".join(tags), now, card_id))
        print(f"{card_id[:8]}  {old}\n          -> {','.join(tags)}")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()

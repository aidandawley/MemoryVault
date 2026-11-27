"""COCO val2017 evaluation set for MemoryVault.

Subcommands (run from the repo root):
  python -m backend.benchmarks.coco_eval annotations   # download + extract COCO val2017 annotations (free, ~241 MB zip)
  python -m backend.benchmarks.coco_eval select        # pick the eval images -> data/coco_eval_set.json (deterministic)
  python -m backend.benchmarks.coco_eval download      # download exactly those images to backend/media/eval_coco/images (sha256-checked)
  python -m backend.benchmarks.coco_eval upload --max-calls 50
        # PAID: uploads each image through the real POST /api/vaults/{id}/cards pipeline (1 Gemini call per image)
        # into a separate "COCO eval" vault in eval.db. Resumable; already-uploaded images are skipped.
        # Results (raw Gemini tags, stored tags, timings) -> data/coco_eval_uploads.json
  python -m backend.benchmarks.coco_eval rebuild       # FREE: recreate eval.db from data/coco_eval_uploads.json (no Gemini calls)

The images come from Flickr under various licenses and are NOT committed (see .gitignore).
The annotations (CC BY 4.0) are only used for the derived labels stored in data/coco_eval_set.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(HERE, ".cache", "coco")
ANN_DIR = os.path.join(CACHE, "extracted")
ANN_ZIP_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
EVAL_SET = os.path.join(HERE, "data", "coco_eval_set.json")
UPLOADS = os.path.join(HERE, "data", "coco_eval_uploads.json")
IMG_DIR = os.path.join(REPO, "backend", "media", "eval_coco", "images")
UPLOAD_MEDIA_DIR = os.path.join(REPO, "backend", "media", "eval_coco", "uploads")
EVAL_DB = os.path.join(REPO, "eval.db")
EVAL_VAULT_TITLE = "COCO eval"

SEED = 2026
PER_TARGET = 3
# Spread across COCO supercategories: animal, food, vehicle, electronic/furniture (indoor),
# outdoor, sports, plus person-only images.
TARGETS = [
    "dog", "cat", "horse",                         # animal
    "pizza", "banana", "cake",                     # food
    "car", "bus", "airplane", "train",             # vehicle
    "laptop", "bed", "toilet",                     # indoor (electronic, furniture)
    "stop sign",                                   # outdoor
    "tennis racket", "surfboard",                  # sports
]
PERSON_ONLY = 2
MIN_TARGET_AREA = 0.02  # target's summed mask area as a fraction of the image


def eval_env() -> dict:
    return {**os.environ, "DATABASE_URL": f"sqlite:///{EVAL_DB}", "MEDIA_DIR": UPLOAD_MEDIA_DIR}


# ---------------------------------------------------------------- annotations
def cmd_annotations(_):
    os.makedirs(ANN_DIR, exist_ok=True)
    zpath = os.path.join(CACHE, "annotations_trainval2017.zip")
    if not os.path.exists(zpath):
        print("downloading", ANN_ZIP_URL)
        urllib.request.urlretrieve(ANN_ZIP_URL, zpath)
    with zipfile.ZipFile(zpath) as z:
        for name in ("annotations/instances_val2017.json", "annotations/captions_val2017.json"):
            with z.open(name) as src, open(os.path.join(ANN_DIR, os.path.basename(name)), "wb") as dst:
                shutil.copyfileobj(src, dst)
    print("extracted to", ANN_DIR)


def load_coco():
    inst = json.load(open(os.path.join(ANN_DIR, "instances_val2017.json"), encoding="utf-8"))
    caps = json.load(open(os.path.join(ANN_DIR, "captions_val2017.json"), encoding="utf-8"))
    return inst, caps


# ---------------------------------------------------------------- select
def cmd_select(_):
    inst, caps = load_coco()
    cat_name = {c["id"]: c["name"] for c in inst["categories"]}
    cat_super = {c["name"]: c["supercategory"] for c in inst["categories"]}
    licenses = {l["id"]: l for l in inst["licenses"]}
    images = {im["id"]: im for im in inst["images"]}

    area = defaultdict(lambda: defaultdict(float))   # image -> category -> summed area
    count = defaultdict(lambda: defaultdict(int))
    for a in inst["annotations"]:
        n = cat_name[a["category_id"]]
        area[a["image_id"]][n] += a["area"]
        count[a["image_id"]][n] += 1
    captions = defaultdict(list)
    for c in caps["annotations"]:
        captions[c["image_id"]].append(c["caption"].strip())

    def frac(img_id, n):
        im = images[img_id]
        return area[img_id][n] / (im["width"] * im["height"])

    rng = random.Random(SEED)
    chosen: list[tuple[int, str]] = []
    used: set[int] = set()
    for target in TARGETS:
        cands = []
        for img_id in sorted(area):
            non_person = {n: a for n, a in area[img_id].items() if n != "person"}
            if not non_person or img_id in used:
                continue
            if max(non_person, key=non_person.get) == target and frac(img_id, target) >= MIN_TARGET_AREA:
                cands.append(img_id)
        pick = rng.sample(cands, PER_TARGET)
        chosen += [(i, target) for i in pick]
        used.update(pick)
    person_cands = [i for i in sorted(area) if set(area[i]) == {"person"} and frac(i, "person") >= 0.2 and i not in used]
    chosen += [(i, "person") for i in rng.sample(person_cands, PERSON_ONLY)]
    rng.shuffle(chosen)  # upload order interleaves categories

    out_images = []
    for img_id, target in chosen:
        im = images[img_id]
        out_images.append({
            "image_id": img_id,
            "file_name": im["file_name"],
            "coco_url": im["coco_url"],
            "flickr_url": im.get("flickr_url"),
            "license": licenses[im["license"]]["name"],
            "license_url": licenses[im["license"]]["url"],
            "width": im["width"], "height": im["height"],
            "selected_for": target,
            "categories": sorted(area[img_id]),
            "category_instances": dict(sorted(count[img_id].items())),
            "category_area_fraction": {n: round(frac(img_id, n), 4) for n in sorted(area[img_id])},
            "captions": captions[img_id],
            "sha256": None,
        })
    spec = {
        "source": "COCO 2017 val (instances_val2017.json, captions_val2017.json); annotations CC BY 4.0",
        "selection": {"seed": SEED, "targets": TARGETS, "per_target": PER_TARGET, "person_only": PERSON_ONLY,
                      "rule": f"target = largest non-person category by summed mask area, covering >= {MIN_TARGET_AREA:.0%} of the image; "
                              "person-only images contain only 'person' covering >= 20%"},
        "supercategory": {n: cat_super[n] for im in out_images for n in im["categories"]},
        "images": out_images,
    }
    if os.path.exists(EVAL_SET):  # keep recorded hashes if the selection is unchanged
        old = {im["image_id"]: im.get("sha256") for im in json.load(open(EVAL_SET, encoding="utf-8"))["images"]}
        for im in out_images:
            im["sha256"] = old.get(im["image_id"])
    json.dump(spec, open(EVAL_SET, "w", encoding="utf-8"), indent=2)
    supers = defaultdict(int)
    for im in out_images:
        supers[cat_super.get(im["selected_for"], "person")] += 1
    print(len(out_images), "images selected ->", EVAL_SET, dict(supers))


# ---------------------------------------------------------------- download
def cmd_download(_):
    spec = json.load(open(EVAL_SET, encoding="utf-8"))
    os.makedirs(IMG_DIR, exist_ok=True)
    changed = False
    for im in spec["images"]:
        path = os.path.join(IMG_DIR, im["file_name"])
        if not os.path.exists(path):
            urllib.request.urlretrieve(im["coco_url"], path)
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if im["sha256"] is None:
            im["sha256"] = digest
            changed = True
        elif im["sha256"] != digest:
            raise SystemExit(f"sha256 mismatch for {im['file_name']}: expected {im['sha256']}, got {digest}")
    if changed:
        json.dump(spec, open(EVAL_SET, "w", encoding="utf-8"), indent=2)
    print(len(spec["images"]), "images present and verified in", IMG_DIR)


# ---------------------------------------------------------------- server helpers
def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EvalServer:
    """uvicorn on eval.db + eval media dir, so the demo database is never touched."""

    def __init__(self, extra_env: dict | None = None):
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.env = {**eval_env(), **(extra_env or {})}

    def __enter__(self):
        import httpx
        os.makedirs(UPLOAD_MEDIA_DIR, exist_ok=True)
        self.log = open(os.path.join(CACHE, "eval_server.log"), "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(self.port), "--log-level", "warning"],
            cwd=REPO, env=self.env, stdout=self.log, stderr=subprocess.STDOUT,
        )
        t0 = time.time()
        while True:
            try:
                if httpx.get(f"{self.base}/api/health", timeout=5).status_code == 200:
                    return self
            except httpx.TransportError:
                pass
            if self.proc.poll() is not None or time.time() - t0 > 180:
                raise RuntimeError("eval server did not start; see " + self.log.name)
            time.sleep(0.25)

    def __exit__(self, *exc):
        self.proc.terminate()
        self.proc.wait(timeout=30)
        self.log.close()


def eval_vault_id(client, base) -> str:
    for v in client.get(f"{base}/api/vaults").json():
        if v["title"] == EVAL_VAULT_TITLE:
            return v["vaultId"]
    return client.post(f"{base}/api/vaults", json={
        "title": EVAL_VAULT_TITLE, "description": "COCO val2017 evaluation images (not demo content)"}).json()["vaultId"]


# ---------------------------------------------------------------- upload (PAID)
def cmd_upload(args):
    import httpx
    import sqlite3

    spec = json.load(open(EVAL_SET, encoding="utf-8"))
    rec = json.load(open(UPLOADS, encoding="utf-8")) if os.path.exists(UPLOADS) else {"uploads": [], "gemini_calls": 0}
    done = {u["image_id"] for u in rec["uploads"] if u["status"] == "ok"}
    todo = [im for im in spec["images"] if im["image_id"] not in done]
    if not todo:
        print("nothing to upload")
        return
    with EvalServer() as srv, httpx.Client(timeout=300) as c:
        vid = eval_vault_id(c, srv.base)
        rec["vault_id"] = vid
        for im in todo:
            if rec["gemini_calls"] >= args.max_calls:
                print(f"stopping: reached --max-calls {args.max_calls}")
                break
            path = os.path.join(IMG_DIR, im["file_name"])
            rec["gemini_calls"] += 1  # one Gemini call per image upload
            t0 = time.perf_counter()
            with open(path, "rb") as f:
                r = c.post(f"{srv.base}/api/vaults/{vid}/cards",
                           data={"media_type": "image", "caption": f"COCO {im['image_id']}", "isActive": "true"},
                           files={"file": (im["file_name"], f, "image/jpeg")})
            elapsed = time.perf_counter() - t0
            r.raise_for_status()
            card = r.json()
            con = sqlite3.connect(EVAL_DB)
            raw, created = con.execute("select raw_tags, created_at from cards where id=?", (card["cardId"],)).fetchone()
            con.close()
            raw = json.loads(raw)
            entry = {"image_id": im["image_id"], "card_id": card["cardId"], "media_id": card["media_id"],
                     "created_at": created, "upload_s": round(elapsed, 3), "raw_tags": raw, "stored_tags": card["tags"],
                     "status": "ok" if raw else "no_ai_tags"}
            rec["uploads"].append(entry)
            json.dump(rec, open(UPLOADS, "w", encoding="utf-8"), indent=2)
            print(f"[{rec['gemini_calls']:>2}] {im['image_id']} ({im['selected_for']}): {elapsed:.2f}s raw={raw} -> {card['tags']}", flush=True)
            if not raw:
                print("stopping: Gemini returned no tags (see backend/benchmarks/.cache/coco/eval_server.log)")
                break
            time.sleep(args.delay)
    print("total Gemini calls recorded:", rec["gemini_calls"])


# ---------------------------------------------------------------- rebuild (FREE)
def cmd_rebuild(_):
    """Recreate eval.db from recorded uploads: same images, raw Gemini tags and stored tags, no API calls."""
    rec = json.load(open(UPLOADS, encoding="utf-8"))
    spec = {im["image_id"]: im for im in json.load(open(EVAL_SET, encoding="utf-8"))["images"]}
    if os.path.exists(EVAL_DB):
        os.remove(EVAL_DB)
    os.environ.update(eval_env())
    from datetime import datetime
    from backend.db.connect_db import connect_db
    from backend.db.session import SessionLocal
    from backend.models.card import Card
    from backend.services import search_service, vault_service

    connect_db()
    os.makedirs(UPLOAD_MEDIA_DIR, exist_ok=True)
    db = SessionLocal()
    try:
        v = vault_service.create_vault(db, "demo-user", EVAL_VAULT_TITLE, "COCO val2017 evaluation images (not demo content)")
        for u in rec["uploads"]:
            if u["status"] != "ok":
                continue
            src = os.path.join(IMG_DIR, spec[u["image_id"]]["file_name"])
            shutil.copyfile(src, os.path.join(UPLOAD_MEDIA_DIR, u["media_id"]))
            ts = datetime.fromisoformat(u["created_at"])
            c = Card(id=u["card_id"], vault_id=v.id, media_id=u["media_id"], thumbnail_id=u["media_id"],
                     media_type="image", caption=f"COCO {u['image_id']}", tags=",".join(u["stored_tags"]),
                     raw_tags=json.dumps(u["raw_tags"]), is_active=True, created_at=ts, updated_at=ts)
            db.add(c)
            db.commit()
            search_service.index_card(db, c)
        print("rebuilt", EVAL_DB, "with", len(rec["uploads"]), "cards")
    finally:
        db.close()


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("annotations").set_defaults(fn=cmd_annotations)
    sub.add_parser("select").set_defaults(fn=cmd_select)
    sub.add_parser("download").set_defaults(fn=cmd_download)
    up = sub.add_parser("upload")
    up.add_argument("--max-calls", type=int, required=True, help="hard cap on Gemini calls (counted across runs)")
    up.add_argument("--delay", type=float, default=4.0, help="seconds between uploads (rate limiting)")
    up.set_defaults(fn=cmd_upload)
    sub.add_parser("rebuild").set_defaults(fn=cmd_rebuild)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

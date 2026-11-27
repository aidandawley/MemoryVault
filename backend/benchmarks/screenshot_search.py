"""Screenshot the vault search box returning results (visual check).

Starts the API on eval.db (COCO eval vault) and the Vite dev server, opens the vault page
in Microsoft Edge via Playwright, searches, and saves desktop + phone-width screenshots.
Needs: pip install playwright (uses the installed Edge, no browser download), npm install.

Run from repo root:  python -m backend.benchmarks.screenshot_search OUT_DIR [query]
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import httpx
from playwright.sync_api import sync_playwright

from backend.benchmarks import coco_eval


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main(out_dir: str, query: str = "pup"):
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.exists(coco_eval.EVAL_DB):
        coco_eval.cmd_rebuild(None)
    with coco_eval.EvalServer({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_VERBOSITY": "error"}) as api:
        vault_id = coco_eval.eval_vault_id(httpx.Client(), api.base)
        web_port = 5173  # must be one of the CORS origins in backend/main.py
        vite = subprocess.Popen(
            "npx vite --port %d --strictPort --host 127.0.0.1" % web_port,
            cwd=coco_eval.REPO, shell=True, env={**os.environ, "VITE_API_URL": api.base},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            url = f"http://127.0.0.1:{web_port}/vaults/{vault_id}"
            for _ in range(120):
                try:
                    if httpx.get(f"http://127.0.0.1:{web_port}/", timeout=2).status_code == 200:
                        break
                except httpx.TransportError:
                    time.sleep(0.5)
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge")
                shots = []
                for name, viewport in (("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 390, "height": 844})):
                    page = browser.new_page(viewport=viewport)
                    errors = []
                    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                    page.goto(url, wait_until="networkidle")
                    page.fill("#vault-search-input", query)
                    page.wait_for_selector(".vault-search__item", timeout=30000)
                    page.wait_for_load_state("networkidle")
                    section = page.locator(".vault-search")
                    section.scroll_into_view_if_needed()
                    path = os.path.join(out_dir, f"vault_search_{name}.png")
                    section.screenshot(path=path)
                    full = os.path.join(out_dir, f"vault_page_{name}.png")
                    page.screenshot(path=full, full_page=False)
                    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                    n = page.locator(".vault-search__item").count()
                    shots.append((name, path, full, n, overflow, errors))
                    page.close()
                browser.close()
        finally:
            subprocess.run(f"taskkill /PID {vite.pid} /T /F", shell=True, capture_output=True) if os.name == "nt" else vite.terminate()
    for name, path, full, n, overflow, errors in shots:
        print(f"{name}: {n} results, horizontal overflow={overflow}, console errors={errors}\n  {path}\n  {full}")


if __name__ == "__main__":
    main(*sys.argv[1:])

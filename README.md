<div align="center">

# memoryvault

**Upload photos and videos into vaults; AI tags them automatically, and semantic search finds them by meaning.**

![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

</div>

## 🌟 Highlights

- **Automated media tagging.** Photos are tagged by Google Gemini (`gemini-3.5-flash-lite`) and videos by Twelve Labs (Pegasus 1.2 hashtags).
- **Tag standardization.** Raw AI tags are normalized (case, punctuation, a hand-written alias map, singularization). Each one is then matched by meaning against the vault's categories using local `all-MiniLM-L6-v2` sentence embeddings and cosine similarity, so "music festival" is stored as "concert" while distinct tags like "sky" are kept.
- **Semantic search inside a vault.** Searching "beer" finds a video tagged "drinks". Each card's caption and tags are embedded and stored; a query is ranked by its best-matching field.
- **Browse by tag.** The vault page shows a row for each of the vault's 7 most common tags.
- **Photos and videos together.** Both media types appear in the same carousel, tag rows and search results.
- **React frontend.** Drag-and-drop uploads, a carousel, tag rows and a media modal with delete.

## 📊 Evaluation

Quality is measured on **50 COCO val2017 photos with human annotations as ground truth**, uploaded through the real pipeline into a separate eval vault. The demo vault is excluded: its 8 photos are only 2 distinct images. Full method and caveats: [`LEARNING.md`](LEARNING.md) §10. Raw numbers: [`benchmark_results.json`](benchmark_results.json).

**Search** (50 queries: 30 COCO category names + 20 synonyms; relevant = COCO labels the image with that category)

| | Keyword | Semantic |
|---|---|---|
| Precision@5 (max possible 0.648) | 0.208 | **0.492** |
| Recall@5 (max possible 0.947) | 0.292 | **0.677** |
| Top-1 accuracy | 0.40 | **0.72** |
| Synonym queries ("pup", "automobile", "loo"): top-1 | 0.05 | **0.70** |
| Latency p50 / p95 (150 local HTTP requests) | **2.6 / 2.8 ms** | 9.4 / 10.1 ms |

**Tag pipeline** (stored tags vs COCO categories and captions)

| | Old pipeline | New pipeline |
|---|---|---|
| Category recall (prominent ≥5% of image) | 0.631 (0.839) | **0.739 (0.931)**, same as raw Gemini |
| Supported tags lost by the pipeline | 46 | **3** |
| Merges audited wrong | 14 of 39 | **4 of 12** |
| Tag precision | **0.740** | 0.722 |
| Unique tags in the vault (lower = more standardized) | **173** | 255 (raw Gemini: 268) |

The new pipeline stops losing and corrupting tags, but it standardizes much less, and a few wrong merges remain (e.g. "street" → "street sign"). See LEARNING.md §6.

**Upload latency per photo** (Gemini tagging, tag resolution, DB writes and search indexing; n=50): median **1.59 s**, p95 2.68 s.

**Reproduce** (no paid API calls; re-downloads the 50 images and rebuilds the eval DB from recorded Gemini output):

```bash
python -m backend.benchmarks.run_all
```

## 🚀 Usage

Run the FastAPI backend and the Vite frontend. In the web UI you can create a vault and upload photos or videos. The backend tags each upload, standardizes the tags, and stores the card with search embeddings. On a vault's page you can search by meaning, browse by tag, or delete items.

## ⬇️ Installation

```bash
git clone https://github.com/aidandawley/MemoryVault
cd MemoryVault

# frontend
npm install

# backend (Python 3.13 tested)
pip install -r backend/requirements.txt
```

Create a `.env` file in the repo root:

```bash
GEMINI_API_KEY=...          # photo tagging
TWELVELABS_API_KEY=...      # video tagging (optional: the app starts without it; only video tagging needs it)
TWELVELABS_INDEX_ID=...     # optional: reuse an existing Twelve Labs index instead of creating one
```

The first start downloads the `all-MiniLM-L6-v2` embedding model (about 90 MB) from Hugging Face. After that it runs locally.

### Run

```bash
# terminal 1, from the repo root (paths like backend/media are relative to it)
uvicorn backend.main:app --reload --port 8000

# terminal 2
npm run dev                  # set VITE_API_URL if the API is not at http://127.0.0.1:8000
```

### Benchmarks

```bash
python -m backend.benchmarks.run_all                    # everything -> benchmark_results.json (free)
python -m backend.benchmarks.coco_eval download         # the 50 COCO eval images (gitignored, sha256-checked)
python -m backend.benchmarks.coco_eval rebuild          # eval.db from recorded uploads (free)
python -m backend.benchmarks.coco_search_eval           # search: semantic vs keyword
python -m backend.benchmarks.coco_tag_eval              # tag pipeline: old vs new vs raw
python -m backend.benchmarks.coco_eval upload --max-calls 50   # PAID: re-tag the eval set with Gemini
```

To browse the eval vault in the UI, run the API with `DATABASE_URL=sqlite:///./eval.db MEDIA_DIR=backend/media/eval_coco/uploads`.

## 🔌 API

| Method | Path | What it does |
|---|---|---|
| GET / POST | `/api/vaults` | List / create vaults |
| GET / DELETE | `/api/vaults/{vault_id}` | Get / delete a vault |
| GET | `/api/vaults/{vault_id}/cards` | List cards, with `tags` and `normalized_tags` |
| POST | `/api/vaults/{vault_id}/cards` | Upload media (multipart); tags, standardizes and indexes it |
| GET | `/api/vaults/{vault_id}/top-tags?limit=7` | Most common normalized tags |
| GET | `/api/vaults/{vault_id}/search?q=&limit=5&mode=semantic` | Semantic search (`mode=keyword` for the exact-match baseline); includes per-stage timings and a `Server-Timing` header |
| DELETE | `/api/cards/{card_id}` | Delete a card (and its media file if no other card uses it) |
| POST | `/api/media/upload-photo-tags`, `/api/media/upload-video-hashtags` | Tag a file without saving it |
| POST / GET | `/api/vaults/{vault_id}/share-link`, `/api/share/{token}` | Read-only share token (kept in memory) |

## 🛠️ Tech Stack

| Category | Technologies |
| --- | --- |
| **Frontend** | React 19, TypeScript, Vite, React Router, react-dropzone |
| **Backend** | Python, FastAPI, SQLAlchemy, SQLite (`app.db`) |
| **AI services** | Google Gemini (`google-genai`), Twelve Labs |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` (local), NumPy cosine similarity |

## 🏗️ Architecture

The React frontend talks to a FastAPI backend.

When you upload a file, the backend:
1. saves it to `backend/media/`;
2. tags it, with Gemini for images or Twelve Labs for videos;
3. runs the tags through `normalize_and_alias`, then through an embedding match against 20 seed categories plus the vault's 7 most common tags;
4. stores the card in SQLite, and stores one embedding per caption and tag in `card_embeddings`.

Search embeds the query with the same local model and ranks the vault's cards by their best-matching field.

## ⚠️ Known limitations

- **No authentication.** Every vault belongs to a hardcoded demo user. The `vault_access` table exists but isn't used, and share links are lost when the server restarts. Multi-user shared vaults are not built yet.
- **Search loads all of a vault's vectors on every request.** That's fine for small vaults; large ones would need a vector index.
- **Tags don't cover small background objects.** Gemini returns 6–8 tags, so items like a backpack or a cup are rarely findable (COCO search recall is 0 for these).
- **Standardization is weak.** Near-duplicates like "banana" / "yellow banana" are both stored (LEARNING.md §6).
- **Video tagging is untested** in the evaluation (it needs a Twelve Labs key).

## 📁 Project Structure

```text
memoryvault/
├── backend/
│   ├── api/          # routers (vaults, cards, search, media, share) and tools (Gemini, Twelve Labs, tag pipeline)
│   ├── benchmarks/   # reproducible metrics + recorded data
│   ├── db/
│   ├── media/        # uploaded files
│   ├── models/       # Vault, Card, CardEmbedding, VaultAccess
│   ├── schemas/
│   └── services/     # card, vault and search logic
├── src/              # React app (components, pages, styles, types)
├── public/
├── app.db            # SQLite database (demo data)
├── tag_labels.csv    # demo-set hand labels (discovery history)
├── benchmark_results.json
├── LEARNING.md       # what changed, why, and the numbers
└── README.md
```

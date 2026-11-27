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

## 📊 Measured results

All numbers come from `python -m backend.benchmarks.run_all` (no paid API calls) and are saved in [`benchmark_results.json`](benchmark_results.json). [`LEARNING.md`](LEARNING.md) explains each one. The demo dataset is small (10 cards, of which the 8 photos are 2 distinct images), so these show the method works on this data, not how it performs at scale.

| Metric | Result |
|---|---|
| Tag standardization, on 50 hand-labeled Gemini tags | 39 → **50** correct; incorrect merges 1 → **0**; useful tags dropped 10 → **0** |
| Semantic search, 15 queries | Precision@5 **0.53** (best possible on this data: 0.60), recall@5 **0.91**, top result relevant in **15/15** queries; keyword baseline: P@5 0.16, recall@5 0.28 |
| Search latency, 150 local HTTP requests | p50 **6.7 ms**, p95 **7.4 ms** (embedding the query is about 60% of that) |
| Photo tagging, 7 Gemini calls | median **1.03 s** per photo, plus 0.05 s of local tag resolution |

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
python -m backend.benchmarks.run_all             # all free metrics -> benchmark_results.json
python -m backend.benchmarks.tag_pipeline_eval   # tag standardization vs tag_labels.csv
python -m backend.benchmarks.search_eval         # search quality + latency (runs on a temp copy of app.db)
```

## 🔌 API

| Method | Path | What it does |
|---|---|---|
| GET / POST | `/api/vaults` | List / create vaults |
| GET / DELETE | `/api/vaults/{vault_id}` | Get / delete a vault |
| GET | `/api/vaults/{vault_id}/cards` | List cards, with `tags` and `normalized_tags` |
| POST | `/api/vaults/{vault_id}/cards` | Upload media (multipart); tags, standardizes and indexes it |
| GET | `/api/vaults/{vault_id}/top-tags?limit=7` | Most common normalized tags |
| GET | `/api/vaults/{vault_id}/search?q=&limit=5` | Semantic search; includes per-stage timings and a `Server-Timing` header |
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
- **`npm run build` fails** because of TypeScript errors that predate this branch (unused imports). `npx vite build` bundles successfully.

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
├── tag_labels.csv    # hand labels for the tag-pipeline benchmark
├── benchmark_results.json
├── LEARNING.md       # what changed, why, and the numbers
└── README.md
```

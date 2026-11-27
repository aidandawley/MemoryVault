# What we changed in MemoryVault, and what we learned

This document walks through every change on the `memoryvault-improvements` branch. For each one it covers the problem, how it was found, the fix, why the fix works, the before/after numbers, and three interview questions with answers. It's written for a CS student, so jargon is explained the first time it appears.

All numbers come from scripts in `backend/benchmarks/` and are saved in `benchmark_results.json`. The commands to reproduce them are at the end.

---

## First, how big is the data? (read this before quoting any number)

| | Value |
|---|---|
| Cards (media items) | 10: 8 photos, 2 videos, all in one vault ("Personal") |
| **Distinct photos** | **2.** The 8 photo cards are 5 copies of one concert photo and 3 copies of one sunset photo (identical bytes, checked with md5). |
| Labeled tags | 50 (every tag Gemini returned in the re-tag run) |
| Search test queries | 15 |
| Photo-tagging timing samples | 7 Gemini calls, one run, one machine |

This is a small demo dataset. The numbers below are real measurements, but they show that the method works **on this data**. They don't show how it would perform on a large photo library. In an interview, say exactly that; it's a strength, not a weakness.

**How we kept ourselves honest:**
- The tag labels (`tag_labels.csv`) were written and committed *before* any pipeline setting was changed.
- The search queries and expected answers (`backend/benchmarks/data/search_queries.json`) were committed *before* search was built.
- The ranking method was chosen before measuring it.
- The tag benchmark replays the real run offline and first checks that the replay reproduces the recorded results exactly. That confirms the test harness itself isn't lying.

---

## 1. Photo tagging was silently broken

**Problem.** Every photo upload ended up with no AI tags. The code called Google's `gemini-2.0-flash-lite` model, which had been retired. The upload handler caught the error, printed one short line, and saved the photo with no tags, so nothing looked broken.

**How we found it.** The database showed 7 of 8 photos with no useful tags. A one-photo test call returned `NotFound: This model models/gemini-2.0-flash-lite is no longer available`.

**Fix.**
- Moved from the deprecated `google.generativeai` SDK to `google.genai` and switched to `gemini-3.5-flash-lite`.
- An empty model response now raises an error that includes the reason, instead of quietly returning `[]`.
- The upload handler logs failures with `logger.exception`, which includes the full stack trace, and warns when tagging returns 0 tags.
- The image's real mime type is sent; before, every image was labelled `image/jpeg`.

**Why it works.** The model name and SDK are the supported ones now. The logging change means the next failure like this shows up in the logs as an error with its cause, instead of as missing data you discover weeks later.

**Before/after.**

| | Before | After |
|---|---|---|
| Photo cards with AI tags | 1 of 8 | 8 of 8 |
| Gemini call time (n=7) | n/a (every call failed) | median **1.03 s**; mean 1.30 s, min 0.89 s, max 2.31 s |
| Local tag resolution per photo | n/a | median **0.05 s** |

Gemini accounts for about 95% of the time it takes to tag a photo.

**Interview questions**
1. *Why is "catch the exception and continue" dangerous?*
   It turns a loud failure into silent data loss. Here, uploads "succeeded" with zero tags for weeks. If you must keep going (we don't want an upload to fail just because tagging failed), log the full exception at error level and make the bad outcome visible, for example by warning on 0 tags.
2. *How would you stop this from happening again when a provider retires a model?*
   Keep the model name in one constant or config value, add a health check that makes one cheap tagging call, alert on the rate of tagging failures, and watch provider deprecation notices. A small integration test with one image would also catch it.
3. *Gemini returned different tags for byte-identical images. Is that a bug?*
   No. LLM output is not deterministic, even at a low temperature. Our 5 copies of the concert photo got 5 different tag lists, and one copy of the sunset photo was tagged "sunrise". It's one reason a normalization layer after the model is useful, and why evaluation should use more than one sample.

---

## 2. The API couldn't start without a Twelve Labs key

**Problem.** `twelvelabs_hashtag.py` raised an error *when it was imported* if `TWELVELABS_API_KEY` was missing. The cards router imports it, so the whole backend crashed at startup, even for features that don't need Twelve Labs. `requirements.txt` was also missing three packages the code needs: SQLAlchemy, python-dotenv and python-multipart.

**How we found it.** Starting the app for testing failed with exactly those errors.

**Fix.** The Twelve Labs client is now created the first time it's used (lazy initialization), and the missing packages are pinned in `requirements.txt`.

**Why it works.** Code that runs at import time runs for everyone. Moving the key check to first use means only video tagging needs the key.

**Before/after.** Starting without a Twelve Labs key: before, the app crashed. After, it starts, and photos, search, browsing and delete all work.

**Interview questions**
1. *What's the difference between failing at import time and failing at call time?*
   Import-time code runs as soon as any module imports the file, so one missing optional dependency takes down the whole app. Call-time failures only affect the feature that needs the missing piece.
2. *Why pin dependency versions?*
   So a fresh install gets the same versions you tested with. Missing or unpinned packages "work on my machine" only because they happen to be installed there already.
3. *How would you catch a missing dependency in CI?*
   Install from `requirements.txt` into a clean virtual environment or container, then start the app or run the tests. That's exactly the environment where these three were missing.

---

## 3. Cards vanished from the "Browse by tag" rows

**Problem.** The backend's `/top-tags` endpoint returns tags *after* normalization: "clouds" becomes "cloud", "SocialGathering" becomes "social gathering". The frontend grouped cards by `tag.toLowerCase()`, so "clouds" never equalled the top tag "cloud", and that card silently fell out of the row.

**How we found it.** By comparing the code paths of `/top-tags` (Python) and `VaultDetail.tsx` (TypeScript). `tag_rows_check.py` then simulates both groupings on the real database.

**Fix.** Each card response now includes `normalized_tags`, built with the same `normalize_and_alias` function, and the UI groups by that. There's one source of truth: we did not copy the roughly 200-entry alias map into TypeScript, where the two copies would drift apart.

**Before/after** (from `tag_rows_check`):

| Data | Rows shown (old → new) | Card slots in rows (old → new) |
|---|---|---|
| `app.db` before this branch | 6 → **7** | 6 → **7** |
| Right after the re-tag (measured during the fix) | 7 → 7 | 27 → **28** |

**Interview questions**
1. *Why not just reimplement the normalization in TypeScript?*
   Two copies of the same logic eventually disagree, and that disagreement is exactly the bug we were fixing. Having the server send the derived key keeps a single source of truth.
2. *How would you test for this class of bug?*
   With a test that builds rows the way the UI does and checks that every card carrying a top tag appears in that tag's row. Our `tag_rows_check.py` is a script version of that test.
3. *What's the trade-off of sending `normalized_tags` in every response?*
   A slightly bigger payload and a little more server work, in exchange for consistency. With roughly 10 tags per card, that's negligible.

---

## 4. The delete button called a route that didn't exist

**Problem.** `CategoryLine.tsx` sends `DELETE /api/cards/{id}`, but the backend never defined that route, so every delete failed (no route matched, so the server returned an error).

**How we found it.** By tracing the frontend's `fetch` calls against the backend routers.

**Fix.** Added `DELETE /api/cards/{card_id}`. It returns 404 if the card doesn't exist. It deletes the media file only if no other card still uses that file, and it also removes the card's search embeddings.

**Before/after.** Delete went from always failing to working. Tested on a database copy: deleting a card whose file is shared keeps the file; deleting the last card that uses a file removes it; deleting again returns 404.

**Interview questions**
1. *Why check whether another card still uses the file before deleting it?*
   Files can be shared (this dataset has duplicate media). Deleting a file that another card still points to would break that card. It's a reference-counting decision.
2. *SQLite has `ON DELETE CASCADE`, so why delete embeddings by hand?*
   SQLite only enforces foreign keys when `PRAGMA foreign_keys=ON` is set for the connection, and this app doesn't set it. Deleting explicitly makes the cleanup work no matter what.
3. *Should DELETE be idempotent?*
   The *state* is idempotent (after one or many calls the card is gone). Returning 404 on the second call is common and fine; returning 204 every time is the other common choice. Pick one and document it.

---

## 5. Tag standardization: keep ambiguous tags

Background: after Gemini returns tags, the pipeline:
1. normalizes them (lowercase, strip punctuation, a hand-written alias map, singularization);
2. embeds them with the `all-MiniLM-L6-v2` sentence-embedding model;
3. compares them with cosine similarity to a set of categories (20 seed words plus the vault's 7 most common tags).

A tag is **matched** to a category if its best similarity is at least 0.70 and beats the second-best by at least 0.08. It becomes a **new** category if its best similarity is below 0.50. Everything in between is **ambiguous**, and ambiguous tags were **thrown away**.

**Problem.** Throwing ambiguous tags away lost real, useful tags: "sky", "water", "horizon", "sunrays", and "stage lights" (three times). A tag is ambiguous because it's somewhat similar to an existing category, not because it's wrong.

**How we found it.** We labeled all 50 Gemini tags by hand (`tag_labels.csv`; each row has the acceptable outputs and a one-line reason), then scored the pipeline against those labels. 10 of the 50 were useful tags that had been dropped.

**Fix.** `keep_ambiguous=True`: an ambiguous tag is stored as its own normalized tag instead of being dropped.

**Why it works.** "Ambiguous" means "not similar enough to merge safely". The safe fallback is to keep the tag as-is, not delete it. You lose a little standardization (more unique tags), but no information.

**Before/after** (50 labeled tags; this change measured on its own):

| | Baseline | keep_ambiguous |
|---|---|---|
| Tags kept | 40 | 50 |
| Correct | 39 | 49 |
| Correct merges | 7 | 7 |
| Incorrect merges | 1 | 1 |
| Useful tags dropped | 10 | **0** |
| Unique stored tags (cost) | 14 | 19 |

**Interview questions**
1. *What's the trade-off of keeping ambiguous tags?*
   Fewer lost tags (recall) against more distinct tags (less standardization). We measured both: 10 → 0 useful tags dropped, and 14 → 19 unique tags. Search (section 9) reduces the cost of having more distinct tags, because "sea" still finds "ocean".
2. *Why label the data before trying new settings?*
   If you label after seeing results, you subconsciously label in favour of the setting you like. Committing the labels first (and git shows the order) prevents that.
3. *Why is 50 labels on 2 distinct photos a weak test?*
   Many labels are repeats of the same decision, so they aren't independent. A real evaluation needs hundreds of tags from varied photos, split into data you tune on and data you only test on.

---

## 6. Tag standardization: don't merge two tags from the same photo

**Problem.** One photo's tags came back from Gemini as `sunrise, ocean, sky, clouds, sunset, …`. "sunrise" came first, so it became a new category. Then "sunset" scored 0.73 against "sunrise", above the 0.70 match threshold, and was merged into it. The photo captioned "sunset" lost its `sunset` tag.

**How we found it.** It was the only `incorrect_merge` in the labels.

**Fix.** `merge_within_batch=False`: a tag can't merge into a category that was created from an earlier tag of the *same photo*.

**Why it works.** If the model lists two tags for one photo, it means them as different things. Merging them can only lose information. The rule follows from what the data means, so it doesn't depend on any particular threshold.

**Before/after** (measured on its own, then combined with section 5):

| | Baseline | no_merge_within_batch | Both changes (shipped) |
|---|---|---|---|
| Tags kept | 40 | 47 | **50** |
| Correct | 39 | 47 | **50 / 50** |
| Correct merges | 7 | 7 | 7 |
| Incorrect merges | 1 | **0** | **0** |
| Useful tags dropped | 10 | 3 | **0** |

The 7 correct merges are "music festival" → concert (×5), "outdoor stage" → stage, and "outdoor crowd" → crowd.

**Interview questions**
1. *Why not just raise the match threshold above 0.73?*
   We tried it. At 0.75, correct merges drop from 7 to 1, because "music festival" → concert is 0.723. Raising a global threshold to fix one pair breaks many good merges. The structural rule fixes the real cause.
2. *Couldn't you add an antonym list (sunrise/sunset, day/night)?*
   You could, but lists like that never cover every case. The rule we used handles every pair the model returns together without anyone maintaining a list.
3. *What does 50/50 correct mean here?*
   It means the pipeline is right on these labels, not that it's perfect. The labels cover 2 distinct photos, so the next step is more labeled data.

---

## 7. What we tried and did *not* ship: threshold sweeps

We swept the match threshold (0.60–0.80), the margin (0–0.12) and the new-tag threshold (0.40–0.60): 60 combinations, run both with and without the two flags above.

- With the old flags, no setting beat the baseline without adding incorrect merges. For example, 0.60 / 0.00 / 0.60 keeps everything but makes 2 incorrect merges.
- With the new flags, margin 0 at a match threshold of 0.60–0.65 scored "+3 correct merges". All 3 were the same decision, "stage lights" → "lights", repeated on three copies of the same photo. "lights" won with 0.667 against "stage" at 0.654, which is a coin flip.

**Decision: keep 0.70 / 0.08 / 0.50.** A "gain" that comes from one near-tie, repeated 3 times, is noise, not improvement.

**Interview questions**
1. *Your sweep found a better score. Why didn't you use it?*
   Because it was one decision counted three times, and it came from removing the safety margin, which had caused incorrect merges elsewhere in the sweep. Reading *which* examples changed matters more than the headline number.
2. *What's overfitting in this context?*
   Choosing settings that look best on the exact examples you measured, which then do worse on new data. With 50 labels from 2 photos, tuning thresholds is very likely to overfit.
3. *How would you tune thresholds properly?*
   Label a larger, varied set; split it into tuning and test sets; pick thresholds on the tuning set; report on the test set once. Look at the precision/recall curve for merges rather than a single number.

---

## 8. Alias targets weren't canonical

**Problem.** The alias map says "best friends" → "friends", but `normalize_and_alias("friends")` returned "friend", because one-word tags are singularized after the alias lookup. So one idea ended up stored under two names. Worse, "chaos" became "chao".

**How we found it.** With an invariant check: every alias *target* should map to itself (applying the function twice should change nothing; this property is called *idempotence*). 5 targets failed: chaos, flowers, friends, photos, vows.

**Fix.** If the text is already an alias target, return it unchanged before singularizing.

**Before/after.** Idempotence failures: **5 → 0.** The 50-label tag scores didn't change; "friend" and "friends" were both acceptable there. Stored tags changed from `friend` to `friends` on 2 cards.

**Interview questions**
1. *What's idempotence and why does it matter for normalization?*
   f(f(x)) = f(x). If normalizing an already-normalized tag changes it, the same concept ends up under two names depending on how many times it was processed.
2. *Why test an invariant instead of specific examples?*
   An invariant checks the whole alias table at once, all 45 targets, including cases nobody thought to write a test for (like "chaos").
3. *Isn't hand-written singularization fragile?*
   Yes: "chaos" → "chao" proves it. A lemmatizer (for example spaCy) is more robust. The alias-target guard is the minimal safe fix for now.

---

## 9. Semantic search inside a vault

**Problem.** There was no way to search a vault's media. The only search box filtered *vault names*. Browsing by tag only matched exact tags and only showed the top 7, so searching "beer" could never find a video tagged "drinks".

**How we found it.** By tracing every input and API call. No branch contained a media search.

**Fix.**
- **Storage:** a new `card_embeddings` table holds one MiniLM embedding per *field* of each card: its caption plus each normalized tag. Rows are built when a card is created, and rebuilt lazily when missing or stale (a different model, or the card's `updated_at` changed).
- **Search:** `GET /api/vaults/{vault_id}/search?q=…&limit=5` embeds the query and scores each card by the **maximum** cosine similarity across its fields. It returns the matching field, the score, and per-stage timings (also in a `Server-Timing` header).
- **UI:** a debounced search box on the vault page.

**Why it works.** Embeddings put words with similar meanings close together, so "beer" lands near "drinks" (similarity 0.72) even though they share no letters. Scoring by the *best single field* means a short query isn't diluted by a card's other tags. We chose this method before measuring it.

**Before/after** (15 pre-written queries, top 5 results, 10 cards):

| Ranker | Precision@5 | Max possible P@5 | Recall@5 | Top result relevant |
|---|---|---|---|---|
| Keyword (exact tag or caption match, roughly the old browsing) | 0.16 | 0.60 | 0.28 | 5 / 15 |
| **Semantic, best field (shipped)** | **0.53** | 0.60 | **0.91** | **15 / 15** |
| Semantic, one concatenated vector (comparison) | 0.55 | 0.60 | 0.94 | 13 / 15 |

**Why "max possible P@5" is 0.60.** Most queries have only 1–3 correct answers in a 10-card vault. If a query has 1 correct card, even a perfect search scores 1/5 = 0.2. Recall@5 and "top result relevant" are fairer here.

**Where it missed:**
- "best friends" (2 of 5): only 2 of the 5 concert cards are *tagged* "friends". Search can only find what the tags and captions say.
- "night out" (1 of 2): the concert photo's "nightlife" tag outranked the second party video.

**Latency** (150 HTTP requests on localhost, warm server):

| Stage | p50 | p95 |
|---|---|---|
| **Total (client-measured)** | **6.7 ms** | **7.4 ms** |
| Embed the query (MiniLM) | 4.0 ms | 4.4 ms |
| Load embeddings from DB | 0.9 ms | 1.1 ms |
| Staleness check (nothing to re-index) | 0.1 ms | 0.1 ms |
| Similarity and ranking | 0.1 ms | 0.1 ms |
| Other (HTTP, routing, JSON) | 1.6 ms | 1.9 ms |

- Embedding the query takes about 60% of the time.
- The first search on a vault that has never been indexed builds the embeddings for all 10 cards: 109 ms in total, 93 ms of it indexing.
- Server startup, including loading the model, takes about 7 s.

At 10 cards there's no bottleneck worth fixing. At thousands of cards, reading every vector from SQLite on each request would start to dominate. The next step would be to cache vectors in memory or use a vector index (FAISS or sqlite-vec).

**Interview questions**
1. *Why max-over-fields instead of one vector per card?*
   One vector for "Jules' Party. drinks, bar, socializing, alcohol, nightout" averages all those meanings together, so a one-word query matches it less strongly. Max-over-fields lets "beer" match the "drinks" field directly. Here, the concatenated vector had slightly higher recall but put a wrong card first in 2 of 15 queries. We kept the method we chose beforehand, and we report both.
2. *Why is precision@5 misleading on this dataset, and what would you report instead?*
   With 1–3 relevant items per query, the best possible P@5 averages 0.60. Report recall@5, the top-1 hit rate, or a rank-aware metric like nDCG, and always state the ceiling.
3. *How would this scale to a million cards?*
   Don't load every vector per request. Keep them in an approximate-nearest-neighbour index (HNSW via FAISS, pgvector or sqlite-vec), filter by vault, and cache the model in memory. Embedding the query (4 ms) would then dominate, and it can be batched or cached for repeat queries.

---

## Reproduce every number

Run these from the repo root with Python 3.13 and `pip install -r backend/requirements.txt`. None of them makes a paid API call. `HF_HUB_OFFLINE=1` is optional once the MiniLM model has been downloaded.

```bash
python -m backend.benchmarks.run_all              # everything -> benchmark_results.json
python -m backend.benchmarks.tag_pipeline_eval    # section 5-8 tables
python -m backend.benchmarks.search_eval          # section 9 tables (uses a temp DB copy)
python -m backend.benchmarks.tag_rows_check       # section 3 (current app.db)
```

Re-measuring photo-tagging latency **does** call Gemini: one paid call per photo. The recorded run is in `backend/benchmarks/data/photo_retag_raw.json`. Video tagging hasn't been measured, because no Twelve Labs key was available.

# What we changed in MemoryVault, and what we learned

This document walks through every change on the `memoryvault-improvements` branch. For each one it covers the problem, how it was found, the fix, why the fix works, the before/after numbers, and three interview questions with answers. It's written for a CS student, so jargon is explained the first time it appears.

All numbers come from scripts in `backend/benchmarks/` and are saved in `benchmark_results.json`. The commands to reproduce them are at the end.

---

## Read this before quoting any number

**The quality metrics come from 50 COCO photos labeled by humans** (section 10). They don't come from the demo vault.

The demo vault looks like 8 photos, but they're really **2 distinct images**: 5 byte-identical copies of a concert photo and 3 of a sunset photo. Metrics on that set mostly measure one or two decisions repeated many times.

We first found the bugs and designed the fixes on the demo set. Those early numbers appear below only as "how we found it", marked *(demo set)*. Every before/after table that matters uses COCO.

**How we kept ourselves honest:**
- Labels and test queries were committed to git *before* the code they evaluate. That covers the demo tag labels, the demo queries and the COCO queries.
- The COCO search ground truth is COCO's human annotations, not our opinion.
- Each benchmark first checks that its offline replay reproduces what the real pipeline stored.
- We report what got worse, not only what improved.

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
| Photo uploads that got AI tags | 0 (every call failed) | **50 / 50** COCO uploads |
| End-to-end upload time per photo (n=50, localhost) | n/a | median **1.59 s**, p95 2.68 s, max 4.60 s |
| Of which: Gemini call (demo re-tag, n=7) | n/a | median 1.03 s |
| Of which: local tag resolution (demo re-tag, n=7) | n/a | median 0.05 s |

The upload time covers Gemini tagging, tag resolution, database writes and search indexing. Gemini is most of it.

**Interview questions**
1. *Why is "catch the exception and continue" dangerous?*
   It turns a loud failure into silent data loss. Here, uploads "succeeded" with zero tags. If you must keep going, log the full exception at error level and make the bad outcome visible, for example by warning on 0 tags.
2. *How would you stop this from happening again when a provider retires a model?*
   Keep the model name in one constant or config value, add a health check that makes one cheap tagging call, alert on the rate of tagging failures, and watch provider deprecation notices.
3. *Gemini returned different tags for byte-identical images. Is that a bug?*
   No. LLM output is not deterministic, even at a low temperature. Our 5 copies of the demo concert photo got 5 different tag lists. It's one reason a normalization layer after the model is useful, and why evaluations need many distinct images.

---

## 2. The API couldn't start without a Twelve Labs key

**Problem.** `twelvelabs_hashtag.py` raised an error *when it was imported* if `TWELVELABS_API_KEY` was missing. The cards router imports it, so the whole backend crashed at startup. `requirements.txt` was also missing SQLAlchemy, python-dotenv and python-multipart.

**Fix.** The Twelve Labs client is now created the first time it's used (lazy initialization), and the missing packages are pinned.

**Why it works.** Code that runs at import time runs for everyone. Moving the key check to first use means only video tagging needs the key.

**Before/after.** Starting without a Twelve Labs key: before, the app crashed. After, it starts, and photos, search, browsing and delete all work.

**Interview questions**
1. *What's the difference between failing at import time and failing at call time?*
   Import-time code runs whenever any module imports the file, so one missing optional dependency takes down the whole app. Call-time failures only affect the feature that needs it.
2. *Why pin dependency versions?*
   So a fresh install gets the versions you tested with. Missing packages "work on my machine" only because they happen to be installed there already.
3. *How would you catch a missing dependency in CI?*
   Install from `requirements.txt` into a clean virtual environment or container, then start the app or run the tests.

---

## 3. Cards vanished from the "Browse by tag" rows

**Problem.** `/top-tags` returns *normalized* tags ("clouds" becomes "cloud"), but the frontend grouped cards by `tag.toLowerCase()`. So a card tagged "clouds" never matched the top tag "cloud", and silently fell out of the row.

**How we found it.** By comparing `/top-tags` (Python) with `VaultDetail.tsx` (TypeScript). `tag_rows_check.py` then simulates both groupings on the real database.

**Fix.** Each card response now includes `normalized_tags`, built with the same `normalize_and_alias` function, and the UI groups by that. There's one source of truth: we did not copy the alias map into TypeScript.

**Before/after** (demo database, from `tag_rows_check`): on the pre-branch data, rows shown went 6 → **7** and card slots 6 → **7**.

**Interview questions**
1. *Why not reimplement the normalization in TypeScript?*
   Two copies of the same logic eventually disagree, and that disagreement was the bug. Having the server send the derived key keeps a single source of truth.
2. *How would you test for this class of bug?*
   With a test that builds rows the way the UI does and checks that every card carrying a top tag appears in that tag's row.
3. *What's the cost of sending `normalized_tags` in every response?*
   A slightly bigger payload, in exchange for consistency. With roughly 10 tags per card, that's negligible.

---

## 4. The delete button called a route that didn't exist

**Problem.** `CategoryLine.tsx` sends `DELETE /api/cards/{id}`, but the backend never defined that route, so every delete failed.

**Fix.** Added `DELETE /api/cards/{card_id}`. It returns 404 if the card is missing. It deletes the media file only if no other card uses it, and it removes the card's search embeddings.

**Before/after.** Delete went from always failing to working. Tested on a database copy with a throwaway file: a shared file is kept, the last user's file is removed, and a second delete returns 404.

**Interview questions**
1. *Why check whether another card still uses the file?*
   Files can be shared, and this dataset has duplicates. Deleting a file another card still points to would break that card. It's a reference-counting decision.
2. *SQLite has `ON DELETE CASCADE`, so why delete embeddings by hand?*
   SQLite only enforces foreign keys when `PRAGMA foreign_keys=ON` is set for the connection, and this app doesn't set it.
3. *Should DELETE be idempotent?*
   The *state* is idempotent: after one or many calls the card is gone. Returning 404 on repeat calls is a common, documented choice.

---

## 5. Tag standardization: keep ambiguous tags

Background: after Gemini returns tags, the pipeline:
1. normalizes them (lowercase, strip punctuation, a hand-written alias map, singularization);
2. embeds them with the local `all-MiniLM-L6-v2` model;
3. compares them with cosine similarity to a set of categories (20 seed words plus the vault's 7 most common tags).

A tag is **matched** to a category if its best similarity is at least 0.70 and beats the second-best by at least 0.08. It becomes a **new** category if its best similarity is below 0.50. Everything in between is **ambiguous**, and ambiguous tags were **thrown away**.

**Problem.** Throwing ambiguous tags away loses real, useful tags. On COCO, the old pipeline dropped "cat" from cat photos. Once the vault contained "dog", "cat" scored 0.661 against it: too close to keep as new, too far to match. So it was discarded, on 4 different photos.

**How we found it.** On the demo set, hand labels showed 10 of 50 useful tags dropped. On COCO, the old pipeline lost **46** tags that human captions or categories support.

**Fix.** `keep_ambiguous=True`: an ambiguous tag is stored as its own normalized tag.

**Why it works.** "Ambiguous" means "not similar enough to merge safely". The safe fallback is to keep the tag, not delete it.

**Before/after on COCO** (this change alone; definitions in section 10):

| | Old | Old + keep_ambiguous |
|---|---|---|
| Category recall | 0.631 | 0.699 |
| Prominent-category recall | 0.839 | 0.909 |
| Grounded tags lost | 46 | 10 |
| Wrong merges (manual audit) | 14 | **19 (worse)** |

**What got worse:** on its own, this change *increases* wrong merges. Kept tags become categories, and later tags from the same photo can then merge into them wrongly, for example "surfboard" → "surfer". Section 6 fixes that.

**Interview questions**
1. *What's the trade-off of keeping ambiguous tags?*
   Fewer lost tags against more distinct tags (less standardization), and here also more chances for bad merges. We measured all three.
2. *Why label data before trying new settings?*
   If you label after seeing results, you subconsciously label in favour of the setting you like. Git history shows the labels came first.
3. *Why did the demo set say "50/50 correct" but COCO shows problems?*
   The demo set had 2 distinct photos, so a few decisions were counted many times. More varied data exposed interactions (like the one above) that the small set couldn't.

---

## 6. Tag standardization: don't merge two tags from the same photo

**Problem.** On the demo sunset photo, Gemini returned "sunrise" and then "sunset". "sunrise" became a category, and "sunset" (0.73 similarity) merged into it. On COCO the same pattern produced:
- "pet" → "dog" on a **cat** photo
- "toilet" → "bathroom"
- "tennis racket" → "tennis player"
- "surfboard" → "surfer"
- "green stars" → "blue stars"

**Fix.** `merge_within_batch=False`: a tag can't merge into a category that was created from an earlier tag of the *same photo*.

**Why it works.** If the model lists two tags for one photo, it means them as different things, so merging them loses information.

**Before/after on COCO, both changes together (shipped):**

| | Raw Gemini (no pipeline) | Old pipeline | **New pipeline** |
|---|---|---|---|
| Category recall | 0.739 | 0.631 | **0.739** |
| Prominent-category recall (≥5% of image) | 0.931 | 0.839 | **0.931** |
| Tag precision (supported by human captions/categories) | 0.722 | **0.740** | 0.722 |
| Tags per image | 6.74 | 4.46 | 6.68 |
| Grounded tags lost | 0 | 46 | **3** |
| Merges | — | 39 | 12 |
| Merge audit: good / shift / wrong | — | 16 / 9 / 14 | 5 / 3 / **4** |
| Unique tags in the vault | 268 | **173** | 255 |

**What got worse at this size (be ready to say this in an interview):**
- **Standardization mostly disappeared.** The vault ends with 255 unique tags, against 173 before and 268 for raw Gemini output. The pipeline now removes only about 5% of duplicates.
- **Good merges dropped** from 16 to 5. The same-photo rule also blocks *correct* merges ("yellow banana" → "banana", "black car" → "car", "airliner" → "airplane"), so both forms get stored.
- **Tag precision dipped**, 0.740 → 0.722, because keeping more tags keeps a few more that no human caption mentions.
- **4 wrong merges remain**, all into seed or top-7 categories:
  - "street" → "street sign" (×2)
  - "beach" → "sand"
  - "vehicle" → "car" on a bus photo, which makes that bus show up in an "automobile" search
- **The alias fix (section 8) has no effect on COCO.**
- **The same-photo rule alone** slightly lowers prominent-category recall (0.839 → 0.828). It only helps in combination with keep_ambiguous.

**What we'd do next** (not done, to avoid tuning on the test set):
- Allow a same-photo merge when one tag is the other plus modifiers ("yellow banana" → "banana"), which would recover the good merges.
- Stop matching against the vault's top-7 at 0.70 for place and object words, or raise that threshold. Then re-evaluate on a *new* COCO sample.

**Interview questions**
1. *Why not just raise the match threshold to fix sunset → sunrise?*
   We tried it on the demo set. At 0.75 most good merges disappear ("music festival" → "concert" is 0.72). A global threshold can't separate "similar" from "same". The structural rule targets the actual cause.
2. *Your change made standardization worse. Why ship it?*
   Because the old pipeline's standardization came mostly from *destroying* information: 46 supported tags lost, 14 wrong merges, and cat photos without "cat". Recall now matches the raw model output. We'd rather have duplicates, which semantic search tolerates ("sea" still finds "ocean"), than lose or corrupt tags. The cost is stated openly, with a concrete next step.
3. *How do you know your merge audit isn't biased?*
   Partly we don't: it's our judgment, written after seeing the merges. We reduced bias by labeling each merge *pair* once, regardless of which pipeline produced it, and keeping the labels in `coco_merge_audit.csv` for anyone to check. The automatic metrics don't depend on it.

---

## 7. What we tried and did *not* ship: threshold sweeps

*(Demo set.)* We swept the match threshold (0.60–0.80), the margin (0–0.12) and the new-tag threshold (0.40–0.60). The only apparent gain was one near-tie ("stage lights": "lights" 0.667 vs "stage" 0.654) counted three times, on three copies of the same photo. The thresholds stayed at 0.70 / 0.08 / 0.50.

**Interview questions**
1. *Your sweep found a better score. Why didn't you use it?*
   It was one decision counted three times, and it came from removing a safety margin that caused wrong merges elsewhere. Look at *which* examples changed, not only at the headline number.
2. *What's overfitting here?*
   Choosing settings that look best on the examples you measured but do worse on new data.
3. *How would you tune thresholds properly?*
   Use a large, varied labeled set split into tuning and test data. Pick thresholds on the tuning split and report on the test split once. The COCO tooling now makes a second, fresh sample cheap: change the seed.

---

## 8. Alias targets weren't canonical

**Problem.** The alias map says "best friends" → "friends", but `normalize_and_alias("friends")` returned "friend", because one-word tags are singularized after the alias lookup. "chaos" became "chao".

**How we found it.** With an invariant check: every alias target should map to itself (applying the function twice changes nothing; this is called *idempotence*). 5 of the 45 targets failed.

**Fix.** If the text is already an alias target, return it unchanged.

**Before/after.** Idempotence failures 5 → **0**. No measurable effect on COCO, because none of its tags hit those aliases; it's a correctness fix.

**Interview questions**
1. *What's idempotence and why does it matter for normalization?*
   f(f(x)) = f(x). If normalizing an already-normalized tag changes it, one concept gets two names.
2. *Why test an invariant instead of examples?*
   It checks all 45 targets at once, including cases nobody would think to test (like "chaos").
3. *Isn't hand-written singularization fragile?*
   Yes. A lemmatizer such as spaCy is more robust; the guard is the minimal safe fix.

---

## 9. Semantic search inside a vault

**Problem.** There was no way to search a vault's media. The only search box filtered *vault names*. Tag browsing matched exact tags only, so "beer" could never find "drinks".

**Fix.**
- **Storage:** a `card_embeddings` table holds one MiniLM embedding per *field* of a card (its caption and each normalized tag). Rows are built on upload and rebuilt lazily when missing or stale.
- **Search:** `GET /api/vaults/{id}/search?q=` scores each card by the **maximum** cosine similarity over its fields. `mode=keyword` runs the exact-match baseline through the same endpoint, for fair latency comparisons.
- **UI:** a debounced search box on the vault page, checked visually (section 13).

**Why it works.** Embeddings put words with similar meanings close together, so "pup" lands near "dog" (0.81). Scoring by the best single field keeps a short query from being diluted by a card's other tags.

**Results on COCO** (50 photos, 50 queries; relevance from human annotations, see section 10):

| | Keyword | **Semantic** |
|---|---|---|
| Precision@5, all queries (best possible: 0.648) | 0.208 | **0.492** |
| Recall@5 (best possible: 0.947) | 0.292 | **0.677** |
| Top-1 accuracy | 0.40 | **0.72** |
| Category-name queries: P@5 / R@5 / top-1 | 0.333 / 0.469 / 0.633 | **0.467 / 0.686 / 0.733** |
| Synonym queries ("pup", "automobile", "loo"…): P@5 / R@5 / top-1 | 0.020 / 0.025 / 0.050 | **0.530 / 0.664 / 0.700** |
| Queries returning nothing | 27 of 50 | 0 of 50 |
| Latency p50 / p95 (150 HTTP requests each) | **2.6 / 2.8 ms** | 9.4 / 10.1 ms |

**Where semantic search misses** (it can only find what the tags say):
- backpack, handbag, cup, truck/lorry and rucksack score 0. These are small background objects that COCO's annotators labeled but Gemini never tagged.
- "person" has 25 relevant images, so even a perfect top 5 gives recall of only 0.2.

**Latency.** Semantic search is about 3.6× slower than keyword (p50 9.4 vs 2.6 ms), but still around 10 ms. At p50, the time splits roughly as:
- embedding the query: 3.6 ms
- loading every vector from SQLite: 2.9 ms
- ranking: 0.5 ms

At thousands of cards, loading every vector on each request would dominate. An in-memory or approximate-nearest-neighbour index (FAISS, sqlite-vec, pgvector) is the fix.

*(Demo set, for history: P@5 0.53 vs 0.16 keyword. It looked similar, but 2 distinct photos can't support that claim.)*

**Interview questions**
1. *Why max-over-fields instead of one vector per card?*
   One vector for all of a card's tags averages their meanings together, so a one-word query matches it less strongly. Max-over-fields lets "pup" match the "dog" field directly.
2. *Why is recall@5 capped, and how do you report it honestly?*
   With 25 relevant "person" images, 5 results can recall at most 0.2. We report the ceilings next to every metric (P@5 ≤ 0.648, R@5 ≤ 0.947).
3. *Keyword search is 3.6× faster. When would you use it?*
   For exact filters, or as a first stage. In practice a hybrid works well: an exact tag hit ranks first, then semantic results.

---

## 10. The COCO evaluation, and why human labels matter

**Problem.** Every earlier metric came from 2 distinct photos, and *we* decided what was relevant. That has two flaws:
- **The data is tiny and repetitive.** One decision repeated 5 times looks like 5 results.
- **Grading your own homework.** When the person who built the system also decides what counts as correct, they tend to judge in the system's favour, even without meaning to.

**Method.**
- **The data.** COCO (Common Objects in Context) is a public dataset in which **human annotators** outlined every object from 80 categories in each image and wrote 5 captions per image.
- **Selecting images.** `coco_eval.py select` picks 50 val2017 images deterministically (seed 2026): 3 images for each of 16 target categories, plus 2 person-only images.
  - The targets span animals, food, vehicles, indoor, outdoor and sports.
  - The target must be the image's largest non-person object and cover at least 2% of the image.
  - The 50 images contain **41** COCO categories in total.
- **Running the real system.** Each image went through the **real upload endpoint** (50 Gemini calls) into a **separate "COCO eval" vault** in its own `eval.db`. The demo vault and its duplicate photos are never part of any metric.
  - Each card's caption is just "COCO &lt;id&gt;". Using COCO's own captions would leak the answers into search.
- **Search ground truth.** A result is relevant **only if COCO's annotators labeled that image with the query's category**, at any size.
  - Queries are the 30 categories that appear in at least 2 images, plus 20 synonyms. Both were written and committed before any image was tagged.
  - We chose only the synonyms, not what counts as relevant.
- **Tag ground truth.**
  - A stored tag is "grounded" if a content word appears in the 5 human captions or names one of the image's COCO categories.
  - *Category recall* is the share of an image's COCO categories named by at least one stored tag.
  - The word lists for this matching (`CATEGORY_WORDS`, e.g. "puppy" names "dog") were fixed in code before results were seen.
- **Reproducibility.**
  - The images are Flickr-licensed, so they're not committed. `coco_eval.py download` re-fetches exactly the same 50 and checks each SHA-256.
  - Gemini's raw output is stored per card (section 11), so `coco_eval.py rebuild` recreates `eval.db` with no API calls. A from-scratch rebuild reproduced identical search metrics.

**Limits.**
- 50 images is still small; differences of 1–2 points are noise.
- COCO labels tiny background objects, which a 6–8-tag photo tagger rarely mentions. That's why we also report *prominent* recall.
- The merge audit (good, shift or wrong) is our judgment, labeled per merge pair in `coco_merge_audit.csv`.
- Video tagging is not evaluated, because there was no Twelve Labs key.

**Interview questions**
1. *Why do human labels matter more than your own judgment?*
   They're independent of the system and of the person who built it. When I chose relevance myself, my expectations were shaped by knowing what the tags said. COCO's annotators never saw our tags.
2. *What's a weakness of COCO as ground truth for this app?*
   It covers 80 object categories, not scenes, moods or events ("sunset", "party"), which are what a memories app is searched for. It also labels tiny objects a person wouldn't search for. A next step is a small human-labeled set of scene and event queries.
3. *How do you stop the eval set from becoming a tuning set?*
   Treat these 50 images as the test set. Tune on a *different* seed's 50 images, then evaluate here once. The selection script makes a fresh, non-overlapping sample one command away.

---

## 11. Storing the model's raw tags

**Problem.** Only the final, resolved tags were saved. Evaluating a pipeline change, or re-processing old uploads, meant paying for the Gemini calls again.

**Fix.** A `cards.raw_tags` column holds the model's output as JSON. `connect_db` adds the column to existing SQLite databases, because `create_all` never alters existing tables.

**Before/after.** The COCO tag evaluation (5 pipeline variants replayed over 50 photos) cost **0** extra Gemini calls. Without the column, the raw output would have been lost after each upload. Every re-evaluation would have meant re-tagging (50 paid calls), and because Gemini isn't deterministic, old and new pipelines would no longer have seen the same input.

**Interview questions**
1. *Why keep raw model output when you already have the cleaned result?*
   Cleaning logic changes. Raw output lets you replay, A/B test and back-fill without the cost or the nondeterminism of calling the model again.
2. *Why not use a migration tool like Alembic?*
   For one additive column in a SQLite demo app, a small idempotent `ALTER TABLE` check is enough. With more schema changes or several databases, Alembic is the right tool.
3. *What could go wrong with `ALTER TABLE ADD COLUMN ... NOT NULL`?*
   It needs a default for existing rows (`DEFAULT '[]'`). Without one, SQLite rejects it.

---

## 12. `npm run build` was failing

**Problem.** `npm run build` runs `tsc -b` first, which failed with 21 errors on `main`, all TS6133 ("declared but never read"):
- 16 default `React` imports that the modern JSX runtime doesn't need
- unused imports and a mock object in `App.tsx`
- an unused import in `landing-page.tsx`
- an unused variable in `VaultDetailSidebar.tsx`

**Fix.** Removed them, plus an `eslint-disable` comment that existed only for those unused variables.

**Before/after.** TypeScript errors 21 → **0**, and `npm run build` now exits 0. ESLint went from 10 problems to 8; the remaining 8 are older `no-explicit-any` errors, which aren't part of the build.

**Interview questions**
1. *Why doesn't React 17+ need `import React`?*
   The automatic JSX runtime compiles JSX into imports from `react/jsx-runtime`, so the `React` identifier no longer has to be in scope.
2. *Why does an unused import fail the build?*
   `noUnusedLocals` is enabled in `tsconfig`, which turns dead code into a compile error. That's strict, and it's how this dead code was caught.
3. *Why not just turn the rule off?*
   It catches real mistakes (leftover mocks, half-removed features). Fixing 21 one-line issues is cheaper than losing that check.

---

## 13. Visual check of the search box

**Method.** `screenshot_search.py` starts the API on `eval.db` and the Vite dev server, then opens the COCO vault in Edge through Playwright. It searches and captures the results at 1280 px and 390 px wide.

**Found and fixed.**
- The "matched #tag · score" lines sat at different heights when cards in a row differed in height. Each result now fills its grid cell.
- The shared `Card` component draws every tag twice, as chips over the photo and again below it, and the chips hid most of the photo. The overlay is now hidden inside search results only.

**Result.** 5 results for "pup" and for "automobile", no horizontal overflow at 390 px, and no console errors.

**Interview questions**
1. *Why take screenshots when type-checking and lint pass?*
   They check that code is valid, not that the page looks right. Layout bugs like these only show up when the page is rendered.
2. *Why fix the duplicate tags in the search CSS instead of in `Card`?*
   `Card` is used elsewhere. Changing it would change other pages that weren't part of this review.
3. *How would you make this check automatic?*
   Use Playwright visual-regression tests (`toHaveScreenshot`) in CI, with seeded data and fixed viewports.

---

## Reproduce every number

Run these from the repo root with Python 3.13, `pip install -r backend/requirements.txt` and `npm install`.

```bash
# Everything, no paid calls: re-downloads the 50 COCO images if missing and rebuilds eval.db
# from recorded uploads -> benchmark_results.json
python -m backend.benchmarks.run_all

# Individual pieces (all free)
python -m backend.benchmarks.coco_eval download        # the exact 50 images, sha256-checked
python -m backend.benchmarks.coco_eval rebuild         # eval.db from recorded uploads, no API calls
python -m backend.benchmarks.coco_search_eval          # section 9 tables
python -m backend.benchmarks.coco_tag_eval             # sections 5-6 tables
python -m backend.benchmarks.screenshot_search OUT_DIR pup   # section 13 (needs Edge + pip install playwright)

# Re-selecting from COCO (free, ~241 MB download), then re-tagging (PAID: 1 Gemini call per image)
python -m backend.benchmarks.coco_eval annotations
python -m backend.benchmarks.coco_eval select
python -m backend.benchmarks.coco_eval upload --max-calls 50
```

The demo-set scripts (`tag_pipeline_eval`, `search_eval`) still run, but their numbers are only the discovery history described above.

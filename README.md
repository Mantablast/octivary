# Octivary

Config-driven MCDA search UI with a low-cost AWS serverless backend and CDK infra scaffold.

## Repo Layout

- `frontend/` React + Vite (TypeScript) SPA
- `backend/` FastAPI app (Lambda-ready) + provider registry
- `infra/` AWS CDK stack (S3/CloudFront, API, Lambda, DynamoDB, Cognito, budget hooks)
- `config/filters/` Canonical public filter configs (copy/sync to frontend + backend as needed)

## Local Dev (quick start)

Frontend:

```
cd frontend
npm install
npm run dev
```

Backend:

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend env:

```
cp backend/.env.example backend/.env
```

## OpenAI Setup

Unknown-product searches only use the AI builder after you configure OpenAI on the backend.

1. Create an API key in the OpenAI dashboard: https://platform.openai.com/api-keys
2. Copy the backend env template if you have not done it yet:

```
cp backend/.env.example backend/.env
```

3. Set these values in `backend/.env`:

```
OPENAI_API_KEY=your_real_api_key
OPENAI_MODEL=gpt-5-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=300
OPENAI_MAX_RETRIES=3
DYNAMIC_SEARCH_SEED_LISTING_COUNT=10
DYNAMIC_SEARCH_ENRICH_BATCH_SIZE=10
```

4. Restart the backend after saving the env file:

```
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Notes:

- Keep `OPENAI_API_KEY` server-side only. Do not put it in Vite or any browser-exposed env var.
- Keep all provider keys and secrets in backend environment variables only. Do not place secrets in `frontend/`, `VITE_*` vars, client-side local storage, or hard-coded source files.
- This project uses the Responses API plus the `web_search` tool for AI-built filters when no local MCDA config exists yet.
- `OPENAI_MODEL=gpt-5-mini` is the current default in this repo because it supports the Responses API, structured outputs, and web search with lower latency and cost than larger models.
- `OPENAI_TIMEOUT_SECONDS=300` is the safer starting point for web-backed filter generation. Increase it further if your searches are broad and return a lot of product research work.
- `OPENAI_MAX_RETRIES=3` lets the backend back off and retry if OpenAI returns transient rate limits. The retry path also reduces the listing target to improve the chance of a successful build.
- `DYNAMIC_SEARCH_SEED_LISTING_COUNT=10` returns the first usable generated MCDA quickly instead of waiting for the full target listing count.
- `DYNAMIC_SEARCH_ENRICH_BATCH_SIZE=10` controls how many additional products are appended per background enrichment pass.
- If you switch models, pick one that supports the Responses API and web search.
- The backend now redacts common secret formats before storing job failures or returning upstream error details to the browser, but secret safety still depends on keeping real keys out of committed files and frontend code.

Official docs:

- Quickstart and API key setup: https://developers.openai.com/api/docs/quickstart
- Responses API reference: https://developers.openai.com/api/reference/resources/responses/methods/create
- Web search tool: https://developers.openai.com/api/docs/guides/tools-web-search
- GPT-5 mini model page: https://developers.openai.com/api/docs/models/gpt-5-mini

Dynamic finder:

- Visit `/finder` in the frontend.
- The frontend creates a search job, the backend stores it in local SQLite by default, and a local in-process worker resolves the job progressively.
- Unknown-product AI builds now use a seed-and-enrich pipeline: the first generated MCDA opens after the initial batch, then additional products are appended in the background until the target count is reached.
- Completed AI-generated filters are now cached by normalized query in a database so later searches can reuse the stored config, sections, display metadata, generated filters, and listings without rebuilding from scratch.
- Current local sample datasets are `insulin-devices`, `bible-catalog`, and `vehicle-catalog`.
- Weak local config matches are filtered out with `DYNAMIC_SEARCH_MIN_MATCH_SCORE` so unrelated searches fall through to AI generation instead of opening the wrong MCDA.
- For AWS-oriented testing later, switch `RUNTIME_PROFILE`, `SEARCH_JOB_STORE_BACKEND`, `SEARCH_QUEUE_BACKEND`, and `GENERATED_FILTER_STORE_BACKEND`.

## Configs

Canonical filter configs live in `config/filters/`. For local dev and deploys, mirror them into:

- `frontend/public/config/filters/` (static hosting)
- `backend/config/filters/` (API config endpoint)

## Provider Secrets

Follow `secure-provider-config.md` for provider key resolution and secret handling.


## Vehicle Catalog Generator (NHTSA vPIC)

This repo includes a local vehicle catalog builder (not for-sale listings) using the free NHTSA vPIC API.

Build the catalog:

```
python -m scripts.catalog_tools.build_vehicle_catalog --db vehicles_catalog.db --years 20 --export-json vehicles_catalog.json
```

Python helper queries:

```
from scripts.catalog_tools.catalog_db import CatalogDB

db = CatalogDB('vehicles_catalog.db')
print(db.list_makes(prefix='TO', limit=10))
print(db.list_models('TOYOTA', year=2020, contains='Cam'))
print(db.search_catalog(2015, 2020, makes=['TOYOTA', 'HONDA'], q='civic'))
```

Notes:
- Requires Python 3 and `requests` (install with `pip install requests`).
- JSON export includes an `images` array placeholder for future listing-like media.

## Bible Catalog Builder (Open Library metadata)

This repo includes a metadata-only Bible catalog builder using Open Library. It does not store any scripture text.

Build the catalog:

```
python -m scripts.catalog_tools.build_bible_catalog --db bible_catalog.db --max-results-per-query 300 --export-json bible_catalog.json
```

Query examples:

```
python -m scripts.catalog_tools.query_bible_catalog list_translations
python -m scripts.catalog_tools.query_bible_catalog search --translation ESV,NIV --study-bible --print-size large --limit 25
python -m scripts.catalog_tools.query_bible_catalog search --publisher Zondervan --format hardcover --red-letter
```

Notes:
- Requires Python 3 and `requests` (install with `pip install requests`).
- Use `--enable-wikidata` to enrich missing publisher/language/date fields.
- Data is metadata-only (ISBNs, titles, bindings, features). No copyrighted scripture text is stored.

## Notes

- This is a scaffold: endpoints and infra are minimal and include placeholders for cost guardrails.
- Keep costs low by default (on-demand DynamoDB, low Lambda memory, minimal services).

## CDK (infra)

```
cd infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk deploy -c budgetAlertEmail=you@example.com
```

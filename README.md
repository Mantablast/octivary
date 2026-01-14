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
python build_catalog.py --db vehicles_catalog.db --years 20 --export-json vehicles_catalog.json
```

Python helper queries:

```
from catalog_db import CatalogDB

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
python build_bible_catalog.py --db bible_catalog.db --max-results-per-query 300 --export-json bible_catalog.json
```

Query examples:

```
python query_bible_catalog.py list_translations
python query_bible_catalog.py search --translation ESV,NIV --study-bible --print-size large --limit 25
python query_bible_catalog.py search --publisher Zondervan --format hardcover --red-letter
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

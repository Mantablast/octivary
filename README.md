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

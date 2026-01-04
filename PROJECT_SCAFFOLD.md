# Octivary Scaffold (Build Spec for Codex)

## Project Summary

Octivary is a consumer website that lets users run MCDA-style filters on live listing APIs, rank results by their priorities, and earn affiliate revenue. Users can create accounts, save priority searches, and return to them later. The system should be low-cost to start, scalable, and protected by strict cost guardrails.

## Core Requirements

- Low-cost, scalable AWS CDK stack with guardrails to keep monthly spend under $50 USD.
- Web UI with two navbars:
  - Top navbar for user account actions.
  - Secondary navbar with category dropdowns: Musical Instruments, Clothing, Vehicles, Wearable Accessories, Entertainment, Flights.
- Each category dropdown links to an MCDA filter page that loads quickly using its assigned config.
- MCDA filter + listings load quickly and are driven by config.json per dropdown item.
- Use the secure provider configuration guidance in `secure-provider-config.md` (and archive in `secure-provider-config.md.zip`).

## Constraints and Concerns

- Keep cost extremely low; minimize managed services and idle compute.
- Collect anonymous priority data only with clear notice and user consent.
- Affiliate codes are stored server-side; Octivary does not process payments.
- User accounts and saved searches are required (basic auth + CRUD).

## Future Goal

- Notification settings: alert users when a new listing scores above a threshold (e.g., 80%).

## Architecture (Suggested)

- Frontend: React + Vite SPA
- Backend: Python (FastAPI or Flask) on AWS Lambda
- API: API Gateway HTTP API
- Data:
  - DynamoDB for saved searches, user profile metadata, and optional analytics
  - S3 + CloudFront for static site
- Auth: Amazon Cognito (User Pool + Hosted UI or custom UI)
- Cost guardrails:
  - AWS Budgets alert to email/Slack
  - Lambda "cost guardrail" that can disable CloudFront or throttle API if budget exceeded
  - Low Lambda memory/timeouts, on-demand DynamoDB, no always-on instances

## Config-Driven Filtering

- Each dropdown item loads a config (public) that defines filters, sections, display, and provider_key.
- Backend resolves provider_key -> API base + API key via env or Secrets Manager (see secure-provider-config.md).
- Frontend must never receive API keys.

## Core Pages

- Home: category landing with descriptions
- Category list page: short intro + category link tiles
- MCDA filter page: config-driven UI, drag priorities, sort results
- Account: login/register, saved searches list
- Search detail: opens MCDA filter page with saved priorities
- Privacy/Consent: clear notice for anonymous priority collection

## Data Model (Draft)

- users
  - user_id (Cognito sub)
  - created_at
- saved_searches
  - search_id
  - user_id
  - category_key
  - config_key
  - priority_payload
  - filters_payload
  - created_at
  - updated_at
- anonymous_priority_events (optional)
  - event_id
  - category_key
  - timestamp
  - payload_summary (no PII)

## API Endpoints (Draft)

- GET /api/config/:config_key
- POST /api/items
- GET /api/saved-searches
- POST /api/saved-searches
- GET /api/saved-searches/:id
- DELETE /api/saved-searches/:id

## Cost Guardrail Behavior (Draft)

- Read monthly budget from env (e.g., MAX_MONTHLY_COST=50).
- If exceeded:
  - Block non-essential APIs or return "service paused" response.
  - Disable CloudFront distribution if necessary.
  - Leave admin access for recovery.

## Security & Compliance

- Use HTTPS everywhere.
- Do not store API keys in config files.
- Log only aggregated, non-PII priority data.
- Show consent prompt for anonymous analytics.
- Provide a simple privacy policy page.

## Implementation Phases

1) Scaffold repo and CDK stack (S3 + CloudFront + API Gateway + Lambda + DynamoDB + Cognito).
2) Build the UI shell with dual navbars and category routing.
3) Port MCDA filter + listing UI (config-driven).
4) Implement provider registry and secure config loading.
5) Add saved searches with account login.
6) Add anonymous analytics + consent banner.
7) Add cost guardrail automation and alerts.
8) Add future notifications (deferred).

## Notes for Codex

- Use `secure-provider-config.md` as the canonical guide for provider_key resolution.
- Keep the initial stack minimal to stay under $50/month and run as cheaply as possible.
- Treat all config as public and cacheable; keep secrets server-side only.

# Before Production Checklist

Use this checklist before exposing Octivary to real users or production traffic.

## Immediate Actions

- [ ] Rotate every secret that has been used in local development, screenshots, terminal output, chat transcripts, or committed files.
- [ ] Rotate the current `OPENAI_API_KEY` immediately if it was ever displayed outside a secure local terminal session.
- [ ] Confirm `.env` files are not committed and not copied into frontend bundles.
- [ ] Confirm all secrets stay server-side only. Never use `VITE_*` variables for secrets.

## Authentication And Access Control

- [ ] Set `AUTH_REQUIRED=1` in production.
- [ ] Configure `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, and `COGNITO_REGION` for the production environment.
- [ ] Verify every API route that should require identity is protected by backend auth, not only by frontend navigation.
- [ ] Remove any reliance on fallback anonymous identities such as `demo-user` in production paths.
- [ ] If `VITE_API_TOKEN` is used at all, ensure it is not a long-lived secret. Anything in `VITE_*` is browser-visible.

## Secret Storage

- [ ] Move all production secrets out of plaintext `.env` files and into a real secret manager.
- [ ] For AWS deploys, store `OPENAI_API_KEY` and provider keys in AWS Secrets Manager or SSM Parameter Store.
- [ ] Restrict secret access by environment so only the production backend runtime can read production secrets.
- [ ] Separate development, staging, and production OpenAI projects and keys.
- [ ] Use least-privilege OpenAI API key permissions.
- [ ] Rotate provider API keys on a defined schedule.

## Frontend Exposure Review

- [ ] Confirm no secret values appear in `frontend/` source files.
- [ ] Confirm no secret values are assigned to `VITE_API_BASE`, `VITE_API_TOKEN`, or any other `VITE_*` variable.
- [ ] Inspect the built frontend bundle once before launch to ensure no keys, bearer tokens, or `.env` values are embedded.
- [ ] Verify browser local storage and session storage do not hold secrets.

## Error Handling And Logging

- [ ] Keep backend-side sanitization enabled so job failures and upstream errors redact tokens and API keys before being stored or returned.
- [ ] Verify application logs do not print request headers containing `Authorization`, `X-API-Key`, or raw upstream error bodies.
- [ ] Ensure reverse proxy, CDN, load balancer, and platform logs do not capture sensitive request bodies or auth headers.
- [ ] Confirm debug logging is disabled in production.
- [ ] Establish a log retention and deletion policy.

## API Hardening

- [ ] Lock `CORS_ALLOW_ORIGINS` to real production origins only. Never use permissive wildcard CORS for production.
- [ ] Review `RATE_LIMIT_PER_MINUTE` and raise or lower it based on production traffic expectations and abuse tolerance.
- [ ] Add stricter per-user and per-IP throttling for expensive AI build routes.
- [ ] Add request size limits and timeouts at the HTTP edge.
- [ ] Add bot and abuse protections for the dynamic search endpoints.

## OpenAI And AI Builder Controls

- [ ] Set a production `OPENAI_MODEL`, `OPENAI_TIMEOUT_SECONDS`, and `OPENAI_MAX_RETRIES` appropriate for cost and latency.
- [ ] Add budget alarms and hard stop behavior for OpenAI usage.
- [ ] Confirm `MAX_MONTHLY_COST` and `OCTIVARY_PAUSED` behavior are connected to real production monitoring.
- [ ] Validate that AI-generated filters are cached and reused before making another OpenAI call for the same normalized search.
- [ ] Add operational limits for generated listing counts so heavy searches cannot exhaust quota.
- [ ] Review prompts and outputs to ensure they do not leak internal system information.

## Database And Persistence

- [ ] Move `SEARCH_JOB_STORE_BACKEND` and `GENERATED_FILTER_STORE_BACKEND` to production-grade storage before launch.
- [ ] If using DynamoDB in production, configure encryption at rest, IAM-scoped access, backups, and PITR where appropriate.
- [ ] If temporarily using SQLite anywhere, ensure the file is not on ephemeral or shared storage and is inaccessible from the public web tier.
- [ ] Protect `search_jobs` and generated filter cache data with least-privilege database access.
- [ ] Decide retention rules for completed jobs, generated filters, cached listings, and user search history.
- [ ] Add cleanup jobs for stale data and cached generated filters.

## Generated Filter Cache Safety

- [ ] Confirm cached generated filters do not store secrets, auth tokens, or raw upstream request headers.
- [ ] Review cached generated filter payloads to ensure only product/filter data needed for recall is stored.
- [ ] Add backup and restore procedures for generated filter cache data if it becomes business-critical.
- [ ] Document cache invalidation rules for stale or incorrect AI-built filters.

## Infrastructure And Network Security

- [ ] Serve the entire site and API only over HTTPS.
- [ ] Put the backend behind a managed gateway, load balancer, or API layer with TLS termination and request limits.
- [ ] Restrict backend egress and ingress with security groups, firewall rules, and network ACLs as appropriate.
- [ ] Lock down IAM roles so each service can access only the tables, queues, buckets, and secrets it needs.
- [ ] Ensure CloudFront, API Gateway, Lambda, DynamoDB, and Cognito policies follow least privilege.
- [ ] Remove unused infrastructure resources and permissions.

## Queue And Worker Security

- [ ] If using SQS in production, validate queue policies, DLQs, retry behavior, and worker IAM permissions.
- [ ] Ensure queue payloads do not contain secrets.
- [ ] Ensure failed jobs do not store raw upstream credential material in `error_message`.

## Dependency And Supply Chain

- [ ] Run dependency auditing for Python and Node packages before release.
- [ ] Pin or review production dependency versions.
- [ ] Remove unused packages from both `frontend/` and `backend/`.
- [ ] Verify build and deployment runners do not echo secrets in logs.
- [ ] Protect CI/CD secrets separately from developer-local secrets.

## Content, Privacy, And Compliance

- [ ] Publish final production `Privacy Policy` and `Terms of Use` pages.
- [ ] Define what user data, search history, and cached filter data are retained and for how long.
- [ ] If account creation is enabled, document password reset, account deletion, and data deletion flows.
- [ ] Review whether stored user queries could contain personal or sensitive information and handle them accordingly.

## Monitoring And Incident Response

- [ ] Add alerts for 5xx rates, auth failures, rate-limit spikes, queue backlogs, and OpenAI quota failures.
- [ ] Add alerts for unusual secret access, IAM changes, or cost spikes.
- [ ] Create a runbook for leaked key rotation.
- [ ] Create a runbook for disabling expensive AI generation quickly, including `OCTIVARY_PAUSED` or equivalent circuit breakers.
- [ ] Create a rollback plan for frontend, backend, and infra changes.

## Verification Before Launch

- [ ] Run a production-like deployment with `AUTH_REQUIRED=1`.
- [ ] Confirm login, account access, pending filters, previous filters, and generated filter recall all work end to end.
- [ ] Confirm a repeated unknown-product search reuses the stored generated filter immediately instead of rebuilding.
- [ ] Confirm no secret values appear in browser dev tools, API responses, logs, cached job data, or generated filter cache rows.
- [ ] Confirm CORS blocks unauthorized origins.
- [ ] Confirm rate limiting and abuse protections trigger as expected.
- [ ] Confirm the app still works when one provider or OpenAI is unavailable.

## Nice-To-Have But Strongly Recommended

- [ ] Add automated secret scanning in CI.
- [ ] Add dependency scanning in CI.
- [ ] Add SAST and basic security linting in CI.
- [ ] Add audit logging for admin and security-sensitive actions.
- [ ] Add separate staging infrastructure and keys so production is never used for development testing.

## Current Octivary-Specific Risks To Resolve Before Prod

- [ ] Replace plaintext local `.env` secret usage with managed secret storage.
- [ ] Rotate any development keys that may have been exposed.
- [ ] Treat `VITE_API_TOKEN` as public if it exists in the frontend; redesign if you intended it to be secret.
- [ ] Ensure production does not rely on local SQLite for job storage or generated filter cache storage.
- [ ] Review all provider integrations to confirm none return raw upstream secret material in errors.

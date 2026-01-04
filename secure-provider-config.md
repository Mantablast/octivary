# Secure Provider Configuration (Draft)

This note captures the approach for supporting multiple filter configs while keeping API secrets out of source control.

## Goals

- Allow multiple datasets/filters to select different external APIs.
- Keep API keys and sensitive URLs out of `config.json`.
- Make staging/prod swaps easy via environment variables or secret managers.

## Proposed Config Shape (Public)

Store only non-sensitive identifiers in `config.json`:

```json
{
  "datasets": {
    "house_listings": {
      "data_source": {
        "type": "external_api",
        "provider_key": "rentals_v1"
      }
    },
    "condos": {
      "data_source": {
        "type": "external_api",
        "provider_key": "condos_v2"
      }
    }
  }
}
```

Notes:
- `provider_key` is a logical name, not a URL or secret.
- All filters/sections stay in `config.json` as they do today.

## Backend Provider Registry (Private)

Map `provider_key` to secrets via environment variables or a secrets manager.

Example environment variables:

```
PROVIDER_RENTALS_V1_BASE_URL=https://api.example.com/rentals
PROVIDER_RENTALS_V1_API_KEY=***secret***
PROVIDER_CONDOS_V2_BASE_URL=https://api.example.com/condos
PROVIDER_CONDOS_V2_API_KEY=***secret***
```

Backend lookup (pseudo-code):

```python
def resolve_provider(provider_key: str) -> ProviderConfig:
    normalized = provider_key.strip().upper()
    base = os.getenv(f"PROVIDER_{normalized}_BASE_URL")
    api_key = os.getenv(f"PROVIDER_{normalized}_API_KEY")
    if not base or not api_key:
        raise RuntimeError(f"Missing provider config for {provider_key}")
    return ProviderConfig(base_url=base, api_key=api_key)
```

## CDK / Deployment

- Store secrets in AWS SSM Parameter Store or Secrets Manager.
- Inject them into the Lambda environment at deploy time.
  - CDK: `lambda.Function` → `environment` or `SecretValue` lookups.
  - Prefer SSM/Secrets Manager for rotation and auditing.

## Frontend Rules

- The frontend should never receive API keys.
- The frontend continues to call the backend only.
- `config.json` is safe to publish because it has no secrets.

## Suggested Next Steps

1. Add `provider_key` to `config.json` schemas for datasets that rely on external APIs.
2. Implement provider registry in the backend (env + SSM/Secrets Manager support).
3. Update deployment to set provider env vars for staging/prod.
4. Add a backend health check that validates all configured provider keys on startup.

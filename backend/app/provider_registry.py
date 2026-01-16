import os
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    base_url: str
    api_key: str


PUBLIC_PROVIDERS = {"halara_v1"}
DEFAULT_BASE_URLS = {
    "halara_v1": "https://api-proxy.ca.halara.com",
}


def resolve_provider(provider_key: str) -> ProviderConfig:
    normalized = provider_key.strip().upper()
    key = provider_key.strip().lower()
    base_url = os.getenv(f"PROVIDER_{normalized}_BASE_URL")
    api_key = os.getenv(f"PROVIDER_{normalized}_API_KEY")
    if not base_url:
        base_url = DEFAULT_BASE_URLS.get(key)
    if not base_url:
        raise RuntimeError(f"Missing provider config for {provider_key}")
    if not api_key and key not in PUBLIC_PROVIDERS:
        raise RuntimeError(f"Missing provider config for {provider_key}")
    return ProviderConfig(base_url=base_url, api_key=api_key or "")

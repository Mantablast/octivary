import os
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    base_url: str
    api_key: str


def resolve_provider(provider_key: str) -> ProviderConfig:
    normalized = provider_key.strip().upper()
    base_url = os.getenv(f"PROVIDER_{normalized}_BASE_URL")
    api_key = os.getenv(f"PROVIDER_{normalized}_API_KEY")
    if not base_url or not api_key:
        raise RuntimeError(f"Missing provider config for {provider_key}")
    return ProviderConfig(base_url=base_url, api_key=api_key)

import os
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    value: object
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() >= entry.expires_at:
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: object) -> None:
        if len(self._store) >= self.max_entries:
            self._store.pop(next(iter(self._store)), None)
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + self.ttl_seconds)


def _default_cache() -> TTLCache:
    ttl = int(os.getenv("CACHE_TTL_SECONDS", "120"))
    max_entries = int(os.getenv("CACHE_MAX_ENTRIES", "256"))
    return TTLCache(ttl_seconds=ttl, max_entries=max_entries)


response_cache = _default_cache()

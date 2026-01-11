import asyncio
import os
import re
from typing import Any, Iterable, Tuple
from urllib.parse import urljoin

import requests
from starlette.concurrency import run_in_threadpool

from .provider_registry import resolve_provider


_GAMEBRAIN_LOCK = asyncio.Lock()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in values:
        if entry in seen:
            continue
        seen.add(entry)
        ordered.append(entry)
    return ordered


def _rating_bucket(mean: float | None) -> str | None:
    if mean is None:
        return None
    try:
        score = float(mean)
    except (TypeError, ValueError):
        return None
    percent = score * 100 if score <= 1 else score
    if percent >= 95:
        return "Brilliant (95+)"
    if percent >= 90:
        return "Amazing (90+)"
    if percent >= 80:
        return "Great (80+)"
    if percent >= 70:
        return "Good (70+)"
    return None


def _extract_genre_tags(genre: str | None, options: Iterable[str]) -> list[str]:
    if not genre:
        return []
    normalized = _normalize_text(genre)
    matches = []
    for option in options:
        if not option:
            continue
        if _normalize_text(option) in normalized:
            matches.append(option)
    return _dedupe(matches)


def _map_gamebrain_item(item: dict[str, Any], genre_options: Iterable[str]) -> dict[str, Any]:
    rating = item.get("rating") if isinstance(item.get("rating"), dict) else {}
    rating_mean = rating.get("mean")
    rating_count = rating.get("count")
    genre = item.get("genre") or ""
    platforms = item.get("platforms") if isinstance(item.get("platforms"), list) else []
    platform_names: list[str] = []
    for entry in platforms:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("value")
            if name:
                platform_names.append(str(name))
        elif isinstance(entry, str):
            platform_names.append(entry)

    arcade_value = item.get("arcadia")
    if arcade_value is None:
        arcade_value = item.get("arcade_enabled")

    adult_value = item.get("adult_only")
    adult_only = None if adult_value is None else bool(adult_value)
    arcade_game = None if arcade_value is None else bool(arcade_value)

    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "year": item.get("year"),
        "genre": genre,
        "genre_tags": _extract_genre_tags(genre, genre_options),
        "rating": {"mean": rating_mean, "count": rating_count},
        "rating_mean": rating_mean,
        "rating_count": rating_count,
        "rating_bucket": _rating_bucket(rating_mean),
        "adult_only": adult_only,
        "arcade_game": arcade_game,
        "image": item.get("image"),
        "link": item.get("link"),
        "screenshots": item.get("screenshots") if isinstance(item.get("screenshots"), list) else [],
        "micro_trailer": item.get("micro_trailer"),
        "gameplay": item.get("gameplay"),
        "short_description": item.get("short_description"),
        "platforms": platforms,
        "platform_names": _dedupe(platform_names),
    }


async def fetch_gamebrain_listings(
    query: str,
    offset: int,
    limit: int,
    genre_options: Iterable[str],
) -> Tuple[list[dict[str, Any]], int]:
    provider = resolve_provider("gamebrain_v1")
    base_url = provider.base_url.rstrip("/")
    search_path = os.getenv("GAMEBRAIN_SEARCH_PATH", "/v1/games").lstrip("/")
    timeout_seconds = float(os.getenv("GAMEBRAIN_TIMEOUT_SECONDS", "8"))
    http_method = os.getenv("GAMEBRAIN_HTTP_METHOD", "GET").strip().upper() or "GET"
    url = urljoin(f"{base_url}/", search_path)

    payload = {"query": query, "limit": limit, "offset": offset}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-Key": provider.api_key,
    }

    def _request() -> dict[str, Any]:
        if http_method == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
            if response.status_code == 405:
                response = requests.get(url, params=payload, headers=headers, timeout=timeout_seconds)
        else:
            response = requests.get(url, params=payload, headers=headers, timeout=timeout_seconds)
            if response.status_code == 405:
                response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        return response.json()

    async with _GAMEBRAIN_LOCK:
        data = await run_in_threadpool(_request)

    results = data.get("results") if isinstance(data, dict) else None
    listings = []
    if isinstance(results, list):
        listings = [
            _map_gamebrain_item(item, genre_options)
            for item in results
            if isinstance(item, dict)
        ]
    total = data.get("total_results") if isinstance(data, dict) else None
    try:
        total_count = int(total)
    except (TypeError, ValueError):
        total_count = len(listings)
    return listings, total_count

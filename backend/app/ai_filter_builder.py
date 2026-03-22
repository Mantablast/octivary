import json
import os
import re
import time
from typing import Any, Callable
from urllib.parse import urljoin

import requests

from .mcda_scoring import resolve_path
from .models import (
    DynamicSearchCandidate,
    DynamicSearchFilterOption,
    DynamicSearchFilterSummary,
    DynamicSearchResult,
)
from .secret_sanitizer import redact_sensitive_text

OPENAI_RESPONSES_URL = "/responses"

PRODUCT_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "title",
        "brand",
        "model",
        "summary",
        "price_amount",
        "price_currency",
        "buy_site",
        "buy_url",
        "product_url",
        "image_url",
        "source_urls",
        "attributes",
    ],
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "brand": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "summary": {"type": "string"},
        "price_amount": {"type": ["number", "null"]},
        "price_currency": {"type": ["string", "null"]},
        "buy_site": {"type": "string"},
        "buy_url": {"type": "string"},
        "product_url": {"type": "string"},
        "image_url": {"type": ["string", "null"]},
        "source_urls": {"type": "array", "items": {"type": "string"}},
        "attributes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "key",
                    "type",
                    "text_value",
                    "list_value",
                    "number_value",
                    "boolean_value",
                ],
                "properties": {
                    "key": {"type": "string"},
                    "type": {"type": "string", "enum": ["text", "list", "number", "boolean"]},
                    "text_value": {"type": ["string", "null"]},
                    "list_value": {"type": "array", "items": {"type": "string"}},
                    "number_value": {"type": ["number", "null"]},
                    "boolean_value": {"type": ["boolean", "null"]},
                },
            },
        },
    },
}

SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "description", "filters", "sections", "products"],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "filters": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "label", "type", "helper_text", "options", "min", "max"],
                "properties": {
                    "key": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {"type": "string", "enum": ["checkboxes", "boolean", "range", "text"]},
                    "helper_text": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "min": {"type": ["number", "null"]},
                    "max": {"type": ["number", "null"]},
                },
            },
        },
        "sections": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "filters"],
                "properties": {
                    "title": {"type": "string"},
                    "filters": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "products": {
            "type": "array",
            "minItems": 4,
            "maxItems": 50,
            "items": PRODUCT_ITEM_SCHEMA,
        },
    },
}

PRODUCTS_ONLY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["products"],
    "properties": {
        "products": {
            "type": "array",
            "minItems": 0,
            "maxItems": 50,
            "items": PRODUCT_ITEM_SCHEMA,
        }
    },
}


def _openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def _openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"


def _openai_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def _openai_timeout_seconds() -> int:
    return max(10, int(os.getenv("OPENAI_TIMEOUT_SECONDS", "300")))


def _openai_max_retries() -> int:
    return max(0, int(os.getenv("OPENAI_MAX_RETRIES", "3")))


def _seed_listing_count(target_limit: int) -> int:
    configured = max(1, int(os.getenv("DYNAMIC_SEARCH_SEED_LISTING_COUNT", "10")))
    return min(max(1, int(target_limit)), configured)


def _enrichment_batch_size() -> int:
    return max(1, int(os.getenv("DYNAMIC_SEARCH_ENRICH_BATCH_SIZE", "10")))


def _extract_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = payload.get("output") or []
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text)
    return "\n".join(chunks).strip()


def _prompt(query: str, limit: int) -> str:
    return (
        "Build an evidence-backed MCDA shopping filter for the user's query. "
        "Use web search to find real products and buy pages. "
        "Return only products and URLs supported by your search results. "
        "Do not invent products, images, sellers, or specs. "
        "Choose factual filter fields only, such as brand, format, size, power, price, feature booleans, and numeric measurements. "
        f"Return up to {limit} distinct products, and prefer at least 12 when enough credible options exist. "
        "Prefer mainstream retail or manufacturer pages for buy URLs. "
        "If direct image URLs are unavailable, set image_url to null. "
        f"User query: {query}"
    )


def _enrichment_prompt(
    query: str,
    limit: int,
    generated_config: dict[str, Any],
    existing_listings: list[dict[str, Any]],
) -> str:
    filter_keys = [
        str(entry.get("key"))
        for entry in generated_config.get("filters") or []
        if isinstance(entry, dict) and entry.get("key")
    ]
    existing_refs = [
        f"{entry.get('id') or ''} | {entry.get('title') or ''} | {entry.get('buy_url') or entry.get('product_url') or ''}"
        for entry in existing_listings[:30]
    ]
    return (
        "Continue enriching an existing evidence-backed MCDA shopping filter. "
        "Return only additional products that fit the same comparison. "
        "Do not repeat or paraphrase any already known products. "
        "Use web search to find real products and buy pages. "
        "Keep the comparison structure stable. "
        f"Return up to {limit} additional distinct products. "
        "Do not invent products, images, sellers, or specs. "
        "Prefer mainstream retail or manufacturer pages for buy URLs. "
        "If direct image URLs are unavailable, set image_url to null. "
        f"Only use these attribute keys when populating product attributes: {', '.join(filter_keys) or 'brand, model, price'}. "
        f"User query: {query}. "
        f"Existing products to avoid: {'; '.join(existing_refs) or 'none'}"
    )


def _best_effort_error_message(response: requests.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    message = error.get("message")
    if isinstance(message, str) and message.strip():
        return redact_sensitive_text(message.strip())
    return None


def _retry_delay_seconds(response: requests.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(1.0, float(retry_after))
            except ValueError:
                pass
    return min(20.0, 2 ** attempt)


def _retry_limit(original_limit: int, attempt: int) -> int:
    if attempt <= 0:
        return original_limit
    if original_limit > 24 and attempt == 1:
        return 24
    if original_limit > 12:
        return 12
    return original_limit


def _generated_result_base_note() -> str:
    return "This filter was generated from live web research because no existing local MCDA filter was available."


def _append_generated_stage_note(note: str | None, loaded: int, target: int) -> str:
    base = note or _generated_result_base_note()
    base = re.sub(r"\s*Seed comparison ready with \d+ products\. Continuing enrichment toward \d+\.\s*", " ", base)
    base = re.sub(r"\s*Comparison built with \d+ products\.\s*", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    if loaded < target:
        stage = f"Seed comparison ready with {loaded} products. Continuing enrichment toward {target}."
    else:
        stage = f"Comparison built with {loaded} products."
    if stage in base:
        return base
    return f"{base} {stage}".strip()


def _ordered_distinct_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        token = cleaned.lower()
        if token in seen:
            continue
        seen.add(token)
        ordered.append(cleaned)
    return ordered


def _numeric_values(values: list[Any]) -> list[float]:
    numeric: list[float] = []
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            numeric.append(float(value))
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                continue
            try:
                numeric.append(float(cleaned))
            except ValueError:
                continue
    return numeric


def _value_list_for_path(listings: list[dict[str, Any]], path: str) -> list[Any]:
    return [resolve_path(item, path) for item in listings]


def _refresh_generated_config_from_listings(config: dict[str, Any], listings: list[dict[str, Any]]) -> dict[str, Any]:
    refreshed = dict(config)
    next_filters: list[dict[str, Any]] = []
    for entry in refreshed.get("filters") or []:
        if not isinstance(entry, dict):
            continue
        next_entry = dict(entry)
        path = str(next_entry.get("path") or next_entry.get("key") or "").strip()
        if not path:
            next_filters.append(next_entry)
            continue
        filter_type = str(next_entry.get("type") or "").strip()
        values = _value_list_for_path(listings, path)
        if filter_type == "checkboxes":
            observed: list[str] = []
            for value in values:
                if isinstance(value, list):
                    observed.extend([str(item) for item in value if str(item).strip()])
                elif value is not None and str(value).strip():
                    observed.append(str(value))
            merged = _ordered_distinct_strings((next_entry.get("options") or []) + observed)
            next_entry["options"] = merged
        elif filter_type == "range":
            numeric = _numeric_values(values)
            if numeric:
                next_entry["min"] = min(numeric)
                next_entry["max"] = max(numeric)
        next_filters.append(next_entry)
    refreshed["filters"] = next_filters
    return refreshed


def _generated_filter_summaries(config: dict[str, Any], listings: list[dict[str, Any]]) -> list[DynamicSearchFilterSummary]:
    summaries: list[DynamicSearchFilterSummary] = []
    for entry in config.get("filters") or []:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        label = str(entry.get("label") or key).strip()
        filter_type = str(entry.get("type") or "").strip()
        path = str(entry.get("path") or key).strip()
        if not key or not label or not filter_type or not path or filter_type == "text":
            continue

        values = _value_list_for_path(listings, path)
        if filter_type == "range":
            numeric = _numeric_values(values)
            if not numeric:
                continue
            summaries.append(
                DynamicSearchFilterSummary(
                    key=key,
                    label=label,
                    type=filter_type,
                    min=min(numeric),
                    max=max(numeric),
                    path=path,
                    helper_text=entry.get("helper_text"),
                )
            )
            continue

        counts: dict[str, int] = {}
        if filter_type == "boolean":
            for value in values:
                if value is None:
                    continue
                token = "Yes" if bool(value) else "No"
                counts[token] = counts.get(token, 0) + 1
        else:
            for value in values:
                if isinstance(value, list):
                    for item in value:
                        cleaned = str(item).strip()
                        if cleaned:
                            counts[cleaned] = counts.get(cleaned, 0) + 1
                elif value is not None:
                    cleaned = str(value).strip()
                    if cleaned:
                        counts[cleaned] = counts.get(cleaned, 0) + 1
        if not counts:
            continue
        option_summaries = [
            DynamicSearchFilterOption(label=label_value, value=label_value, count=count)
            for label_value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))[:12]
        ]
        summaries.append(
            DynamicSearchFilterSummary(
                key=key,
                label=label,
                type=filter_type,
                option_count=len(counts),
                options=option_summaries,
                path=path,
                helper_text=entry.get("helper_text"),
            )
        )
    return summaries


def _listing_identity(item: dict[str, Any]) -> str:
    for key in ("id", "buy_url", "product_url"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    parts = [str(item.get("title") or "").strip().lower(), str(item.get("brand") or "").strip().lower()]
    return "|".join(parts)


def _merge_generated_listings(
    existing_listings: list[dict[str, Any]],
    incoming_listings: list[dict[str, Any]],
    target_limit: int,
) -> list[dict[str, Any]]:
    merged = list(existing_listings)
    seen = {_listing_identity(item) for item in merged}
    for item in incoming_listings:
        identity = _listing_identity(item)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        merged.append(item)
        if len(merged) >= target_limit:
            break
    return merged


def _refresh_generated_result_state(
    result: DynamicSearchResult,
    target_limit: int,
) -> DynamicSearchResult:
    listings = list(result.generated_listings or [])
    config = _refresh_generated_config_from_listings(result.generated_config or {}, listings)
    result.generated_config = config
    result.generated_filters = _generated_filter_summaries(config, listings)
    result.evidence_count = len(listings)
    result.loaded_listing_count = len(listings)
    result.target_listing_count = max(target_limit, len(listings))
    result.is_partial = len(listings) < result.target_listing_count
    result.config_title = str(config.get("title") or result.config_title or result.query.title())
    result.config_description = str(config.get("description") or result.config_description or f"Generated comparison for {result.query}")
    result.note = _append_generated_stage_note(result.note, len(listings), result.target_listing_count)
    return result


def _request_openai_json(
    prompt_builder: Callable[[int], str],
    schema: dict[str, Any],
    limit: int,
) -> dict[str, Any] | None:
    api_key = _openai_api_key()
    if not api_key:
        return None
    bounded_limit = max(1, min(int(limit), 50))
    max_retries = _openai_max_retries()
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        attempt_limit = _retry_limit(bounded_limit, attempt)
        payload = {
            "model": _openai_model(),
            "input": prompt_builder(attempt_limit),
            "tool_choice": "auto",
            "tools": [{"type": "web_search"}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "generated_mcda_filter",
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{_openai_base_url()}{OPENAI_RESPONSES_URL}",
                headers=headers,
                json=payload,
                timeout=_openai_timeout_seconds(),
            )
        except requests.Timeout as exc:
            last_exception = exc
            if attempt >= max_retries:
                raise RuntimeError(
                    "OpenAI took too long while researching this product. Try again, use a narrower search term, or lower the listing count."
                ) from exc
            time.sleep(_retry_delay_seconds(None, attempt))
            continue
        except requests.RequestException as exc:
            raise RuntimeError("OpenAI research failed before a response was returned.") from exc

        if response.status_code == 429:
            last_exception = requests.HTTPError(response=response)
            if attempt >= max_retries:
                detail = _best_effort_error_message(response)
                raise RuntimeError(
                    detail
                    or "OpenAI rate limits were reached while building this filter. Wait a minute and try again, or reduce the requested listing count."
                )
            time.sleep(_retry_delay_seconds(response, attempt))
            continue

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = _best_effort_error_message(response)
            raise RuntimeError(detail or f"OpenAI request failed with status {response.status_code}.") from exc

        body = response.json()
        output_text = _extract_output_text(body)
        if not output_text:
            return None
        parsed = json.loads(output_text)
        products = parsed.get("products")
        if isinstance(products, list):
            parsed["products"] = products[:attempt_limit]
        return parsed

    if last_exception is not None:
        raise RuntimeError("OpenAI research failed after multiple retries.") from last_exception
    return None


def _extract_image_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        response = requests.get(url, timeout=6, headers={"User-Agent": "OctivaryBot/1.0"})
        response.raise_for_status()
    except requests.RequestException:
        return None

    html = response.text
    for pattern in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urljoin(url, match.group(1))
    return None


def _normalize_generated_filter(filter_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": filter_spec["key"],
        "label": filter_spec["label"],
        "type": filter_spec["type"],
        "path": filter_spec["key"],
        "options": filter_spec.get("options") or [],
        "min": filter_spec.get("min"),
        "max": filter_spec.get("max"),
        "helper_text": filter_spec.get("helper_text") or "",
        "allow_custom": filter_spec["type"] == "text",
    }


def _attribute_value(attribute: dict[str, Any]) -> Any:
    kind = attribute.get("type")
    if kind == "list":
        return attribute.get("list_value") or []
    if kind == "number":
        return attribute.get("number_value")
    if kind == "boolean":
        return attribute.get("boolean_value")
    return attribute.get("text_value")


def _normalize_generated_listing(product: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": product["id"],
        "title": product["title"],
        "brand": product.get("brand"),
        "model": product.get("model"),
        "summary": product.get("summary"),
        "buy_site": product.get("buy_site"),
        "buy_url": product.get("buy_url"),
        "product_url": product.get("product_url"),
        "source_urls": product.get("source_urls") or [],
        "price": {
            "amount": product.get("price_amount"),
            "currency": product.get("price_currency") or "USD",
        },
        "images": [],
    }
    image_url = product.get("image_url") or _extract_image_from_url(product.get("buy_url")) or _extract_image_from_url(product.get("product_url"))
    if image_url:
        item["images"] = [image_url]

    for attribute in product.get("attributes") or []:
        if not isinstance(attribute, dict):
            continue
        key = attribute.get("key")
        if not key:
            continue
        item[str(key)] = _attribute_value(attribute)
    return item


def _normalize_generated_payload(query: str, payload: dict[str, Any], target_limit: int | None = None) -> DynamicSearchResult:
    filters = [_normalize_generated_filter(entry) for entry in payload.get("filters") or []]
    listings = [_normalize_generated_listing(entry) for entry in payload.get("products") or []]
    currency = next(
        (
            entry.get("price_currency")
            for entry in payload.get("products") or []
            if isinstance(entry, dict) and entry.get("price_currency")
        ),
        "USD",
    )
    generated_config = {
        "config_key": "generated-filter",
        "category_key": "generated",
        "title": payload.get("title") or query.title(),
        "description": payload.get("description") or f"Generated comparison for {query}",
        "datasets": {
            "primary": {
                "label": "Generated web research",
                "data_source": {
                    "type": "generated_job",
                    "provider_key": "generated_job",
                },
            }
        },
        "text_search_fields": ["title", "brand", "model", "summary", "buy_site"],
        "filters": filters,
        "sections": payload.get("sections") or [{"title": "Filters", "filters": [entry["key"] for entry in filters]}],
        "display": {
            "title_template": "{title}",
            "subtitle_template": "{brand} {model}",
            "image_path": "images[0]",
            "empty_image": "/assets/octonotes.png",
            "metadata": [
                {"label": "Price", "path": "price.amount", "format": "currency", "currency": currency},
                {"label": "Buy site", "path": "buy_site"},
                {"label": "Brand", "path": "brand"},
            ],
        },
    }

    result = DynamicSearchResult(
        query=query,
        config_key=None,
        config_title=generated_config["title"],
        config_description=generated_config["description"],
        category_key="generated",
        evidence_count=len(listings),
        generated_config=generated_config,
        generated_listings=listings,
        generated_filters=[],
        listings=[],
        candidates=[
            DynamicSearchCandidate(
                config_key="generated-filter",
                title=generated_config["title"],
                category_key="generated",
                description=generated_config["description"],
                match_score=100.0,
                evidence_count=len(listings),
                source_type="ai_web_research",
                local_data_available=False,
            )
        ],
        local_only=False,
        note=_generated_result_base_note(),
    )
    return _refresh_generated_result_state(result, target_limit or len(listings))


def build_ai_generated_filter_result(query: str, limit: int = 50) -> DynamicSearchResult | None:
    parsed = _request_openai_json(lambda request_limit: _prompt(query, request_limit), SCHEMA, limit)
    if not parsed:
        return None
    return _normalize_generated_payload(query, parsed, target_limit=limit)


def build_ai_seed_filter_result(query: str, target_limit: int = 50) -> DynamicSearchResult | None:
    seed_limit = _seed_listing_count(target_limit)
    return build_ai_generated_filter_result(query, limit=seed_limit)


def enrich_ai_generated_filter_result(
    query: str,
    result: DynamicSearchResult,
    target_limit: int = 50,
    on_batch: Callable[[DynamicSearchResult], None] | None = None,
) -> DynamicSearchResult:
    if not result.generated_config or not result.generated_listings:
        return result

    refreshed = _refresh_generated_result_state(
        DynamicSearchResult(**result.model_dump()),
        max(1, min(int(target_limit), 50)),
    )

    while len(refreshed.generated_listings) < refreshed.target_listing_count:
        remaining = refreshed.target_listing_count - len(refreshed.generated_listings)
        batch_limit = min(_enrichment_batch_size(), remaining)
        parsed = _request_openai_json(
            lambda request_limit: _enrichment_prompt(
                query,
                request_limit,
                refreshed.generated_config or {},
                refreshed.generated_listings or [],
            ),
            PRODUCTS_ONLY_SCHEMA,
            batch_limit,
        )
        if not parsed:
            break
        products = parsed.get("products") or []
        if not isinstance(products, list):
            break
        additional_listings = [
            _normalize_generated_listing(entry)
            for entry in products
            if isinstance(entry, dict)
        ]
        merged_listings = _merge_generated_listings(
            refreshed.generated_listings or [],
            additional_listings,
            refreshed.target_listing_count,
        )
        if len(merged_listings) == len(refreshed.generated_listings or []):
            break
        refreshed.generated_listings = merged_listings
        refreshed = _refresh_generated_result_state(refreshed, refreshed.target_listing_count)
        if on_batch:
            on_batch(DynamicSearchResult(**refreshed.model_dump()))

    return refreshed

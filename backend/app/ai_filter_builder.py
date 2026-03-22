import json
import os
import re
from typing import Any
from urllib.parse import urljoin

import requests

from .models import DynamicSearchCandidate, DynamicSearchResult

OPENAI_RESPONSES_URL = "/responses"

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
            "maxItems": 12,
            "items": {
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
            },
        },
    },
}


def _openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def _openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"


def _openai_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def _openai_timeout_seconds() -> int:
    return max(10, int(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")))


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


def _prompt(query: str) -> str:
    return (
        "Build an evidence-backed MCDA shopping filter for the user's query. "
        "Use web search to find real products and buy pages. "
        "Return only products and URLs supported by your search results. "
        "Do not invent products, images, sellers, or specs. "
        "Choose factual filter fields only, such as brand, format, size, power, price, feature booleans, and numeric measurements. "
        "Prefer mainstream retail or manufacturer pages for buy URLs. "
        "If direct image URLs are unavailable, set image_url to null. "
        f"User query: {query}"
    )


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


def _normalize_generated_payload(query: str, payload: dict[str, Any]) -> DynamicSearchResult:
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

    return DynamicSearchResult(
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
        note="This filter was generated from live web research because no existing local MCDA filter was available.",
    )


def build_ai_generated_filter_result(query: str) -> DynamicSearchResult | None:
    api_key = _openai_api_key()
    if not api_key:
        return None

    payload = {
        "model": _openai_model(),
        "input": _prompt(query),
        "tool_choice": "auto",
        "tools": [{"type": "web_search"}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "generated_mcda_filter",
                "schema": SCHEMA,
                "strict": True,
            }
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{_openai_base_url()}{OPENAI_RESPONSES_URL}",
        headers=headers,
        json=payload,
        timeout=_openai_timeout_seconds(),
    )
    response.raise_for_status()
    body = response.json()
    output_text = _extract_output_text(body)
    if not output_text:
        return None
    parsed = json.loads(output_text)
    return _normalize_generated_payload(query, parsed)

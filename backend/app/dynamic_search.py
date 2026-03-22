import os
import re
import time
from collections import Counter
from typing import Any, Callable, Iterable
from urllib.parse import quote

from .ai_filter_builder import build_ai_generated_filter_result
from .config_loader import load_filter_config
from .listings_store import load_local_listings
from .mcda_scoring import SEARCH_TERM_ITEM_PREFIX, normalize, resolve_path
from .models import (
    DynamicSearchCandidate,
    DynamicSearchFilterOption,
    DynamicSearchFilterSummary,
    DynamicSearchListingMetadata,
    DynamicSearchListingSummary,
    DynamicSearchResult,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_DYNAMIC_CONFIG_KEYS = ("insulin-devices", "bible-catalog", "vehicle-catalog")
DEFAULT_TITLE_PATHS = ("product_name", "title", "name")
CONFIG_KEYWORDS = {
    "insulin-devices": ["cgm", "glucose", "dexcom", "libre", "insulin", "sensor", "medtronic"],
    "bible-catalog": ["bible", "kjv", "niv", "esv", "journaling", "study", "scripture"],
    "vehicle-catalog": ["car", "sedan", "suv", "truck", "vehicle", "auto", "toyota", "tesla", "camry"],
}


def _normalize_query(query: str) -> str:
    return " ".join(TOKEN_RE.findall(query.lower()))


def _tokenize_query(query: str) -> list[str]:
    return list(dict.fromkeys(TOKEN_RE.findall(query.lower())))


def _configured_config_keys() -> list[str]:
    raw = os.getenv("DYNAMIC_SEARCH_CONFIG_KEYS", "")
    if raw.strip():
        return [value.strip() for value in raw.split(",") if value.strip()]
    return list(DEFAULT_DYNAMIC_CONFIG_KEYS)


def _max_listings_per_config() -> int:
    return max(1, int(os.getenv("DYNAMIC_SEARCH_MAX_LISTINGS_PER_CONFIG", "5000")))


def _step_delay_seconds() -> float:
    delay_ms = max(0, int(os.getenv("DYNAMIC_SEARCH_STEP_DELAY_MS", "120")))
    return delay_ms / 1000


def _push_strings(bucket: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for entry in value.values():
            _push_strings(bucket, entry)
        return
    if isinstance(value, list):
        for entry in value:
            _push_strings(bucket, entry)
        return
    text = str(value).strip()
    if text:
        bucket.append(text)


def _config_haystack(config: dict[str, Any]) -> str:
    parts: list[str] = [config.get("title", ""), config.get("description", ""), config.get("category_key", "")]
    for entry in config.get("filters") or []:
        if not isinstance(entry, dict):
            continue
        parts.append(str(entry.get("label", "")))
        for option in entry.get("options") or []:
            parts.append(str(option))
    for keyword in CONFIG_KEYWORDS.get(config.get("config_key", ""), []):
        parts.append(keyword)
    return normalize(" ".join(parts))


def _listing_haystack(item: dict[str, Any], config: dict[str, Any]) -> str:
    parts: list[str] = []
    text_paths = set(config.get("text_search_fields") or [])
    for entry in config.get("filters") or []:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if path:
            text_paths.add(path)
    for path in text_paths:
        _push_strings(parts, resolve_path(item, str(path)))
    if not parts:
        _push_strings(parts, item)
    return normalize(" ".join(parts))


def _match_score(query: str, terms: list[str], haystack: str) -> float:
    if not query or not haystack:
        return 0.0
    score = 0.0
    if query in haystack:
        score += 10.0 + len(terms)
    matched = 0
    for term in terms:
        if term in haystack:
            matched += 1
            score += 2.5
    if matched and matched == len(terms):
        score += 4.0
    if matched:
        score += matched / max(len(terms), 1)
    return score


def _title_for_item(item: dict[str, Any]) -> str:
    for path in DEFAULT_TITLE_PATHS:
        value = resolve_path(item, path)
        if value:
            return str(value)
    make = item.get("make_name")
    model = item.get("model_name")
    if make or model:
        return " ".join(part for part in [str(make or "").strip(), str(model or "").strip()] if part)
    item_id = item.get("id")
    return str(item_id) if item_id is not None else "Listing"


def _render_template(template: str | None, item: dict[str, Any], fallback: str) -> str:
    if not template:
        return fallback
    rendered = template
    for match in re.findall(r"\{([^}]+)\}", template):
        replacement = resolve_path(item, match)
        rendered = rendered.replace(f"{{{match}}}", "" if replacement is None else str(replacement))
    rendered = re.sub(r"\s+", " ", rendered).strip(" .,-")
    return rendered or fallback


def _stringify_metadata(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def _metadata_for_item(item: dict[str, Any], config: dict[str, Any]) -> list[DynamicSearchListingMetadata]:
    display = config.get("display") or {}
    metadata_specs = display.get("metadata") or []
    metadata: list[DynamicSearchListingMetadata] = []
    for spec in metadata_specs[:4]:
        if not isinstance(spec, dict):
            continue
        label = str(spec.get("label") or "").strip()
        path = spec.get("path")
        if not label or not path:
            continue
        value = _stringify_metadata(resolve_path(item, str(path)))
        if not value:
            continue
        metadata.append(DynamicSearchListingMetadata(label=label, value=value))
    return metadata


def _image_for_item(item: dict[str, Any], config: dict[str, Any]) -> str | None:
    display = config.get("display") or {}
    image_path = display.get("image_path")
    if image_path:
        value = resolve_path(item, str(image_path))
        if isinstance(value, str) and value.strip():
            return value
    images = item.get("images")
    if isinstance(images, list):
        for entry in images:
            if isinstance(entry, str) and entry.strip():
                return entry
    return None


def _source_url_for_item(item: dict[str, Any]) -> str | None:
    for key in ("official_info_url", "source_url", "url"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _listing_summary(
    item: dict[str, Any],
    config: dict[str, Any],
    relevance_score: float,
    strongest_score: float,
) -> DynamicSearchListingSummary:
    display = config.get("display") or {}
    title = _render_template(display.get("title_template"), item, _title_for_item(item))
    subtitle = _render_template(display.get("subtitle_template"), item, "")
    subtitle_value = subtitle or None
    completeness = min(1.0, len(_metadata_for_item(item, config)) / 4 if config.get("display") else 0.5)
    relative = relevance_score / strongest_score if strongest_score else 0.0
    score = round(min(100.0, 55.0 + relative * 30.0 + completeness * 15.0), 1)
    return DynamicSearchListingSummary(
        listing_id=str(item.get("id") or title),
        title=title,
        subtitle=subtitle_value,
        score=score,
        image_url=_image_for_item(item, config),
        metadata=_metadata_for_item(item, config),
        source_url=_source_url_for_item(item),
    )


def _numeric_values(values: Iterable[Any]) -> list[float]:
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


def _filter_values(items: list[dict[str, Any]], path: str) -> list[Any]:
    values: list[Any] = []
    for item in items:
        values.append(resolve_path(item, path))
    return values


def _generated_filters(config: dict[str, Any], items: list[dict[str, Any]]) -> list[DynamicSearchFilterSummary]:
    generated: list[DynamicSearchFilterSummary] = []
    for entry in config.get("filters") or []:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        label = str(entry.get("label") or key).strip()
        filter_type = str(entry.get("type") or "").strip()
        path = entry.get("path")
        if not key or not label or not filter_type or not path:
            continue
        if filter_type == "text":
            continue

        values = _filter_values(items, str(path))
        if filter_type == "range":
            numeric = _numeric_values(values)
            if len(numeric) < 2:
                continue
            observed_min = min(numeric)
            observed_max = max(numeric)
            if observed_min == observed_max:
                continue
            generated.append(
                DynamicSearchFilterSummary(
                    key=key,
                    label=label,
                    type=filter_type,
                    min=observed_min,
                    max=observed_max,
                    path=str(path),
                    helper_text=entry.get("helper_text"),
                )
            )
            continue

        option_counts: Counter[str] = Counter()
        if filter_type == "boolean":
            for value in values:
                if value is None:
                    continue
                option_counts["Yes" if bool(value) else "No"] += 1
        else:
            for value in values:
                if isinstance(value, list):
                    flattened = value
                else:
                    flattened = [value]
                for candidate in flattened:
                    text = str(candidate).strip() if candidate is not None else ""
                    if text:
                        option_counts[text] += 1

        if len(option_counts) < 2:
            continue
        options = [
            DynamicSearchFilterOption(label=option, value=option, count=count)
            for option, count in option_counts.most_common(8)
        ]
        generated.append(
            DynamicSearchFilterSummary(
                key=key,
                label=label,
                type=filter_type,
                option_count=len(option_counts),
                options=options,
                path=str(path),
                helper_text=entry.get("helper_text"),
            )
        )
        if len(generated) >= 8:
            break
    return generated


def _default_section_order(config: dict[str, Any]) -> list[str]:
    filter_keys = [
        entry.get("key")
        for entry in config.get("filters") or []
        if isinstance(entry, dict) and entry.get("key")
    ]
    ordered: list[str] = []
    for section in config.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for key in section.get("filters") or []:
            if key in filter_keys and key not in ordered:
                ordered.append(key)
    for key in filter_keys:
        if key not in ordered:
            ordered.append(key)
    return ordered


def _preferred_text_filter_key(config: dict[str, Any]) -> str | None:
    text_filters = [
        entry
        for entry in config.get("filters") or []
        if isinstance(entry, dict) and entry.get("type") == "text" and entry.get("key")
    ]
    if not text_filters:
        return None
    for entry in text_filters:
        label = normalize(entry.get("label"))
        if "text" in label or "keyword" in label:
            return str(entry["key"])
    for entry in text_filters:
        label = normalize(entry.get("label"))
        key = normalize(entry.get("key"))
        if any(term in f"{label} {key}" for term in ("title", "model", "name", "description")):
            return str(entry["key"])
    for entry in text_filters:
        label = normalize(entry.get("label"))
        if "notes" in label:
            return str(entry["key"])
    return str(text_filters[-1]["key"])


def _text_term_key(base_key: str, term: str) -> str:
    return f"{SEARCH_TERM_ITEM_PREFIX}{base_key}:{quote(term, safe='')}"


def _should_infer_common_value(key: str, label: str) -> bool:
    haystack = normalize(f"{key} {label}")
    return any(term in haystack for term in ("manufacturer", "brand", "make", "translation", "publisher"))


def _option_matches_query(option_text: str, query: str, terms: list[str], key: str, label: str) -> bool:
    normalized_option = normalize(option_text)
    if not normalized_option:
        return False
    if normalized_option.isdigit() or len(normalized_option) < 2:
        label_haystack = normalize(f"{key} {label}")
        return normalized_option in terms and any(term in query for term in label_haystack.split())
    return normalized_option in query


def _prefill_payload(
    config: dict[str, Any],
    items: list[dict[str, Any]],
    query: str,
    terms: list[str],
) -> tuple[dict[str, Any], dict[str, list[str]], list[str]]:
    filters: dict[str, Any] = {}
    selected_order: dict[str, list[str]] = {}
    base_section_order = _default_section_order(config)
    selected_keys: list[str] = []
    claimed_terms: set[str] = set()
    focus_items = items[: min(len(items), 3)]

    for entry in config.get("filters") or []:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        filter_type = str(entry.get("type") or "").strip()
        path = entry.get("path")
        if not key or not filter_type or not path:
            continue

        if filter_type in {"checkboxes", "select"}:
            matched_options: list[str] = []
            for option in entry.get("options") or []:
                option_text = str(option).strip()
                if _option_matches_query(option_text, query, terms, key, str(entry.get("label") or key)) and option_text not in matched_options:
                    matched_options.append(option_text)
                    claimed_terms.update(_tokenize_query(option_text))
            if not matched_options and focus_items and _should_infer_common_value(key, str(entry.get("label") or key)):
                values = []
                for item in focus_items:
                    value = resolve_path(item, str(path))
                    if isinstance(value, list):
                        values.extend([str(entry_value).strip() for entry_value in value if str(entry_value).strip()])
                    elif value is not None and str(value).strip():
                        values.append(str(value).strip())
                distinct_values = {value for value in values if value}
                if len(distinct_values) == 1:
                    matched_options = [next(iter(distinct_values))]

            if matched_options:
                filters[key] = matched_options if filter_type == "checkboxes" else matched_options[0]
                selected_order[key] = matched_options
                selected_keys.append(key)
            continue

        if filter_type == "boolean":
            label = normalize(entry.get("label"))
            if label and label in query:
                filters[key] = True
                selected_order[key] = ["true"]
                selected_keys.append(key)
                claimed_terms.update(_tokenize_query(label))
            continue

    text_filter_key = _preferred_text_filter_key(config)
    remaining_terms = [term for term in terms if term not in claimed_terms]
    if text_filter_key and remaining_terms:
        filters[text_filter_key] = []
        selected_keys.append(text_filter_key)
        for term in remaining_terms[:2]:
            term_key = _text_term_key(text_filter_key, term)
            selected_order[term_key] = [term]

    section_order = [key for key in base_section_order if key in selected_keys]
    for key in base_section_order:
        if key not in section_order:
            section_order.append(key)
    if text_filter_key and filters.get(text_filter_key) == []:
        insert_at = section_order.index(text_filter_key) + 1 if text_filter_key in section_order else len(section_order)
        for term in remaining_terms[:2]:
            term_key = _text_term_key(text_filter_key, term)
            if term_key not in section_order:
                section_order.insert(insert_at, term_key)
                insert_at += 1

    return filters, selected_order, section_order


def _load_config_matches(query: str, terms: list[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for config_key in _configured_config_keys():
        config = load_filter_config(config_key)
        data_source = ((config.get("datasets") or {}).get("primary") or {}).get("data_source") or {}
        provider_key = data_source.get("provider_key")
        source_type = str(data_source.get("type") or "")
        listings: list[dict[str, Any]] = []
        if source_type == "local_json" and provider_key:
            try:
                listings = load_local_listings(str(provider_key))[: _max_listings_per_config()]
            except FileNotFoundError:
                listings = []

        listing_scores: list[tuple[float, dict[str, Any]]] = []
        for item in listings:
            item_score = _match_score(query, terms, _listing_haystack(item, config))
            if item_score > 0:
                listing_scores.append((item_score, item))

        listing_scores.sort(key=lambda entry: entry[0], reverse=True)
        metadata_score = _match_score(query, terms, _config_haystack(config))
        combined_score = round(metadata_score + (listing_scores[0][0] if listing_scores else 0.0) + min(len(listing_scores), 20) * 0.4, 2)
        if combined_score <= 0:
            continue
        matches.append(
            {
                "config": config,
                "config_key": config_key,
                "source_type": source_type,
                "combined_score": combined_score,
                "listing_scores": listing_scores,
                "evidence_count": len(listing_scores),
            }
        )
    matches.sort(
        key=lambda entry: (
            entry["evidence_count"] > 0,
            entry["evidence_count"],
            entry["combined_score"],
        ),
        reverse=True,
    )
    return matches


def _emit_progress(
    progress_callback: Callable[[float, str], None] | None,
    progress: float,
    message: str,
) -> None:
    if progress_callback:
        progress_callback(progress, message)
        delay = _step_delay_seconds()
        if delay > 0:
            time.sleep(delay)


def build_dynamic_search_result(
    query: str,
    limit: int = 12,
    progress_callback: Callable[[float, str], None] | None = None,
) -> DynamicSearchResult:
    normalized_query = _normalize_query(query)
    terms = _tokenize_query(query)

    _emit_progress(progress_callback, 0.2, "Loading local sample datasets")
    matches = _load_config_matches(normalized_query, terms)

    _emit_progress(progress_callback, 0.55, "Comparing factual attributes")
    candidates = [
        DynamicSearchCandidate(
            config_key=entry["config_key"],
            title=entry["config"].get("title", entry["config_key"]),
            category_key=entry["config"].get("category_key", ""),
            description=entry["config"].get("description", ""),
            match_score=float(entry["combined_score"]),
            evidence_count=int(entry["evidence_count"]),
            source_type=entry["source_type"],
            local_data_available=entry["source_type"] == "local_json",
        )
        for entry in matches[:4]
    ]

    if not matches:
        _emit_progress(progress_callback, 0.45, "No existing filter found, researching live sources")
        generated_result = build_ai_generated_filter_result(query)
        if generated_result is not None:
            return generated_result
        return DynamicSearchResult(
            query=query,
            candidates=[],
            local_only=False,
            note="No local filter matched this query, and the AI web builder is not configured yet.",
        )

    top_match = matches[0]
    config = top_match["config"]
    evidence_items = [item for _, item in top_match["listing_scores"][: max(limit * 3, 24)]]

    _emit_progress(progress_callback, 0.8, "Generating dynamic filters")
    generated_filters = _generated_filters(config, evidence_items)
    prefill_filters, prefill_selected_order, prefill_section_order = _prefill_payload(
        config,
        evidence_items,
        normalized_query,
        terms,
    )
    strongest_score = top_match["listing_scores"][0][0] if top_match["listing_scores"] else 0.0
    listings = [
        _listing_summary(item, config, score, strongest_score)
        for score, item in top_match["listing_scores"][:limit]
    ]

    note = (
        "Results are drawn from local sample datasets and initial ranking is relevance-based until you refine the comparison."
        if listings
        else "The best matching local config was found, but no evidence-backed listings matched the exact query terms."
    )

    if not listings:
        _emit_progress(progress_callback, 0.45, "No exact local results, researching live sources")
        generated_result = build_ai_generated_filter_result(query)
        if generated_result is not None:
            return generated_result

    _emit_progress(progress_callback, 0.95, "Ranking evidence-backed matches")
    return DynamicSearchResult(
        query=query,
        config_key=top_match["config_key"],
        config_title=config.get("title"),
        config_description=config.get("description"),
        category_key=config.get("category_key"),
        evidence_count=int(top_match["evidence_count"]),
        prefill_filters=prefill_filters,
        prefill_selected_order=prefill_selected_order,
        prefill_section_order=prefill_section_order,
        generated_filters=generated_filters,
        listings=listings,
        candidates=candidates,
        local_only=True,
        note=note,
        open_filter_path=f"/filters/{top_match['config_key']}",
    )

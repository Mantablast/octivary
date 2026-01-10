import re
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import unquote


SECTION_DOMINANCE_BASE = 5
VALUE_DECAY = 0.65
HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD = 0.5
SEARCH_TERM_ITEM_PREFIX = "search_term_item:"

TEXT_SEARCH_FIELDS = [
    "system_type",
    "scanner_reader",
    "components_included.scanner_reader",
    "phone_models",
    "scan_required",
    "scan_required_for_current_reading",
    "pricing_notes",
    "insurance_notes",
    "product_name",
    "notes",
]


def normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value)).strip()


def resolve_path(data: Any, path: str | None) -> Any:
    if not path:
        return None
    value = data
    for segment in path.split("."):
        if value is None:
            return None
        if isinstance(value, list):
            match = re.match(r"(.+)\\[(\\d+)\\]$", segment)
            if match:
                key, idx = match.group(1), int(match.group(2))
                collection = [entry.get(key) if isinstance(entry, dict) else None for entry in value]
                return collection[idx] if idx < len(collection) else None
            return None
        if isinstance(value, dict):
            match = re.match(r"(.+)\\[(\\d+)\\]$", segment)
            if match:
                key, idx = match.group(1), int(match.group(2))
                inner = value.get(key)
                return inner[idx] if isinstance(inner, list) and idx < len(inner) else None
            value = value.get(segment)
        else:
            return None
    return value


def parse_search_term_item_key(key: str) -> Dict[str, str] | None:
    if not key.startswith(SEARCH_TERM_ITEM_PREFIX):
        return None
    rest = key[len(SEARCH_TERM_ITEM_PREFIX) :]
    separator = rest.find(":")
    if separator < 0:
        return None
    base_key = rest[:separator]
    term = unquote(rest[separator + 1 :])
    return {"base_key": base_key, "term": term}


def canonical_section_weight(total_sections: int, index: int) -> float:
    dominance_power = max(0, total_sections - index - 1)
    return float(SECTION_DOMINANCE_BASE**dominance_power)


def canonical_value_weight(rank: int) -> float:
    return float(VALUE_DECAY**rank)


def _push_value(bucket: List[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, list):
        for entry in value:
            _push_value(bucket, entry)
        return
    if isinstance(value, dict):
        for entry in value.values():
            _push_value(bucket, entry)
        return
    bucket.append(str(value))


def build_text_search_haystack(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    for path in TEXT_SEARCH_FIELDS:
        _push_value(parts, resolve_path(item, path))
    pricing_sources = resolve_path(item, "pricing_sources")
    if isinstance(pricing_sources, list):
        for entry in pricing_sources:
            if isinstance(entry, dict):
                _push_value(parts, entry.get("label"))
    scan_required = resolve_path(item, "scan_required")
    if isinstance(scan_required, str):
        if normalize(scan_required) == "no":
            parts.append("no scanning")
        if normalize(scan_required) == "yes":
            parts.append("scan required")
    elif isinstance(scan_required, bool):
        parts.append("scan required" if scan_required else "no scanning")
    scan_required_for_reading = resolve_path(item, "scan_required_for_current_reading")
    if isinstance(scan_required_for_reading, bool):
        parts.append("scan required" if scan_required_for_reading else "no scanning")
    return normalize(strip_html(" ".join(parts)))


def _build_filter_map(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    filters = config.get("filters") or []
    return {entry.get("key"): entry for entry in filters if isinstance(entry, dict)}


def _default_section_order(config: Dict[str, Any]) -> List[str]:
    filters = config.get("filters") or []
    filter_keys = [entry.get("key") for entry in filters if isinstance(entry, dict) and entry.get("key")]
    section_keys = []
    for section in config.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_keys.extend([key for key in section.get("filters") or [] if key in filter_keys])
    return section_keys or filter_keys


def _extract_range_filters(filters: Dict[str, Any], filter_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float | None]]:
    selections: Dict[str, Dict[str, float | None]] = {}
    for key, spec in filter_map.items():
        if spec.get("type") != "range":
            continue
        raw = filters.get(key)
        if not isinstance(raw, dict):
            continue
        min_value = raw.get("min")
        max_value = raw.get("max")
        min_parsed = float(min_value) if isinstance(min_value, (int, float)) else None
        max_parsed = float(max_value) if isinstance(max_value, (int, float)) else None
        if min_parsed is None and max_parsed is None:
            continue
        selections[key] = {"min": min_parsed, "max": max_parsed}
    return selections


def _build_priority_spec(
    section_order: List[str],
    selected_order: Dict[str, List[str]],
    range_keys: Iterable[str],
) -> Dict[str, Any]:
    sections: List[str] = []
    selected_values: Dict[str, List[str]] = {}
    token_weights: Dict[str, float] = {}
    section_weights: Dict[str, float] = {}
    selected_tokens: set[str] = set()
    high_priority_tokens: set[str] = set()
    total_selected_count = 0
    total_sections = len(section_order)
    range_keys_set = set(range_keys)

    for index, section_key in enumerate(section_order):
        normalized_section = normalize(section_key)
        if not normalized_section:
            continue
        items = selected_order.get(section_key) or selected_order.get(normalized_section) or []
        normalized_items: List[str] = []
        seen: set[str] = set()
        for item in items:
            normalized_item = normalize(item)
            if not normalized_item or normalized_item in seen:
                continue
            seen.add(normalized_item)
            normalized_items.append(normalized_item)

        has_range = section_key in range_keys_set
        if not normalized_items and not has_range:
            continue

        sections.append(section_key)
        if normalized_items:
            selected_values[section_key] = normalized_items
            total_selected_count += len(normalized_items)
        else:
            total_selected_count += 1

        section_weight = canonical_section_weight(total_sections, index)
        section_weights[section_key] = section_weight
        for value_index, value in enumerate(normalized_items):
            value_weight = canonical_value_weight(value_index)
            token = f"{section_key}:{value}"
            token_weights[token] = section_weight * value_weight
            selected_tokens.add(token)
            if value_weight >= HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD:
                high_priority_tokens.add(token)

    return {
        "sections": sections,
        "selected_values": selected_values,
        "token_weights": token_weights,
        "section_weights": section_weights,
        "selected_tokens": selected_tokens,
        "high_priority_tokens": high_priority_tokens,
        "total_selected_count": total_selected_count,
    }


def _filter_is_text(section_key: str, spec: Dict[str, Any] | None) -> bool:
    if section_key.startswith(SEARCH_TERM_ITEM_PREFIX):
        return True
    if spec and spec.get("type") == "text":
        return True
    return False


def _extract_tokens(item: Dict[str, Any], section_key: str, spec: Dict[str, Any] | None) -> List[str]:
    if not spec or not spec.get("path"):
        return []
    filter_type = spec.get("type")
    value = resolve_path(item, spec.get("path"))

    if filter_type in ("checkboxes", "select", "scalar"):
        if isinstance(value, list):
            return [f"{section_key}:{normalize(entry)}" for entry in value if normalize(entry)]
        normalized_value = normalize(value)
        return [f"{section_key}:{normalized_value}"] if normalized_value else []

    if filter_type == "boolean":
        if value is None:
            return []
        return [f"{section_key}:{'true' if bool(value) else 'false'}"]

    if isinstance(value, list):
        return [f"{section_key}:{normalize(entry)}" for entry in value if normalize(entry)]

    normalized_value = normalize(value)
    return [f"{section_key}:{normalized_value}"] if normalized_value else []


def score_listings(
    listings: List[Dict[str, Any]],
    config: Dict[str, Any],
    filters: Dict[str, Any],
    selected_order: Dict[str, List[str]],
    section_order: List[str] | None,
) -> Tuple[List[Dict[str, Any]], int]:
    filter_map = _build_filter_map(config)
    effective_section_order = section_order or _default_section_order(config)
    range_selections = _extract_range_filters(filters, filter_map)

    priority_spec = _build_priority_spec(
        effective_section_order,
        selected_order,
        range_selections.keys(),
    )
    priority_section_keys = priority_spec["sections"]
    selected_values = priority_spec["selected_values"]
    token_weights = priority_spec["token_weights"]
    section_weights = priority_spec["section_weights"]
    selected_tokens = priority_spec["selected_tokens"]
    high_priority_tokens = priority_spec["high_priority_tokens"]
    total_selected_count = priority_spec["total_selected_count"]

    priority_sections = [
        (key, filter_map.get(key))
        for key in priority_section_keys
        if not _filter_is_text(key, filter_map.get(key))
    ]
    priority_search_sections = [
        key for key in priority_section_keys if _filter_is_text(key, filter_map.get(key))
    ]

    scored: List[Tuple[Dict[str, Any], float, int, int, int]] = []
    for index, item in enumerate(listings):
        item_tokens: set[str] = set()
        for section_key, spec in priority_sections:
            for token in _extract_tokens(item, section_key, spec):
                item_tokens.add(token)

        if priority_search_sections:
            haystack = build_text_search_haystack(item)
            for section_key in priority_search_sections:
                terms = selected_values.get(section_key) or []
                for term in terms:
                    if term and term in haystack:
                        item_tokens.add(f"{section_key}:{term}")

        total_matches = 0
        high_priority_matches = 0
        derived_score = 0.0
        range_matches = 0
        for token in item_tokens:
            if token in selected_tokens:
                total_matches += 1
                if token in high_priority_tokens:
                    high_priority_matches += 1
                derived_score += token_weights.get(token, 0.0)

        for section_key, range_spec in range_selections.items():
            spec = filter_map.get(section_key)
            if not spec or not spec.get("path"):
                continue
            raw_value = resolve_path(item, spec.get("path"))
            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError):
                continue
            min_value = range_spec.get("min")
            max_value = range_spec.get("max")
            if min_value is not None and numeric_value < min_value:
                continue
            if max_value is not None and numeric_value > max_value:
                continue
            total_matches += 1
            high_priority_matches += 1
            range_matches += 1
            derived_score += section_weights.get(section_key, 0.0)

        item_copy = dict(item)
        item_copy["_mcda"] = {
            "derived_score": derived_score,
            "total_matches": total_matches,
            "high_priority_matches": high_priority_matches,
            "range_matches": range_matches,
            "total_selected_count": total_selected_count,
            "index": index,
        }
        scored.append((item_copy, derived_score, total_matches, high_priority_matches, range_matches))

    if total_selected_count > 0:
        scored.sort(key=lambda entry: (-entry[1], entry[0]["_mcda"]["index"]))

    return [entry[0] for entry in scored], total_selected_count

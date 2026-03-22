import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}

TRANSLATION_ALIASES = {
    "KJV": ["kjv", "king james version", "king james"],
    "NKJV": ["nkjv", "new king james version", "new king james"],
    "ESV": ["esv", "english standard version"],
    "NIV": ["niv", "new international version"],
    "NLT": ["nlt", "new living translation"],
    "NASB": ["nasb", "new american standard", "new american standard bible"],
    "CSB": ["csb", "christian standard bible"],
    "RSV": ["rsv", "revised standard version"],
    "NRSV": ["nrsv", "new revised standard version"],
    "ASV": ["asv", "american standard version"],
    "CEB": ["ceb", "common english bible"],
    "GNT": ["gnt", "good news translation"],
    "AMP": ["amp", "amplified bible"],
}

FORMAT_KEYWORDS = {
    "bonded leather": ["bonded leather"],
    "imitation leather": ["imitation leather", "leatherette", "faux leather"],
    "leather": ["genuine leather", "leather"],
    "hardcover": ["hardcover", "hard cover", "casebound"],
    "paperback": ["paperback", "softcover", "soft cover"],
    "cloth": ["cloth", "cloth over board"],
}

COVER_COLORS = [
    "black",
    "brown",
    "burgundy",
    "navy",
    "blue",
    "red",
    "green",
    "pink",
    "gray",
    "white",
    "tan",
]

FEATURE_PATTERNS = {
    "red_letter": ["red letter", "red-letter", "redletter"],
    "study_bible": ["study bible", "study edition"],
    "commentary_notes": ["commentary", "study notes"],
    "cross_references": ["cross reference", "cross-reference", "crossreferences"],
    "concordance": ["concordance"],
    "maps": ["maps", "map section"],
    "thumb_indexed": ["thumb index", "thumb-indexed", "thumb indexed"],
    "gilded_edges": ["gilded", "gilt", "gold edges", "gilded edges"],
    "journaling": ["journaling", "wide margin", "wide-margin", "wide margins"],
    "single_column": ["single column", "single-column"],
    "two_column": ["two column", "two-column", "double column", "double-column"],
    "devotionals": ["devotional", "devotionals"],
    "reading_plan": ["reading plan", "read through", "one-year", "one year", "365 day"],
}

PRINT_SIZE_PATTERNS = [
    ("giant", ["giant print", "super giant print"]),
    ("large", ["large print"]),
    ("compact", ["compact", "ultra compact"]),
    ("personal", ["personal size"]),
]

FONT_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(pt|point)")


def _normalize_texts(texts: Iterable[Optional[str]]) -> str:
    parts = [text.strip() for text in texts if text and text.strip()]
    return " ".join(parts).lower()


def _find_phrases(text: str, phrases: Iterable[str]) -> List[str]:
    hits = []
    for phrase in phrases:
        if phrase in text:
            hits.append(phrase)
    return hits


def parse_features(texts: Iterable[Optional[str]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    combined = _normalize_texts(texts)
    features: Dict[str, Any] = {}
    evidence: Dict[str, Any] = {}

    for feature, phrases in FEATURE_PATTERNS.items():
        hits = _find_phrases(combined, phrases)
        if hits:
            features[feature] = 1
            evidence[feature] = hits

    print_size = None
    for label, phrases in PRINT_SIZE_PATTERNS:
        hits = _find_phrases(combined, phrases)
        if hits:
            print_size = label
            evidence["print_size"] = hits
            break
    if print_size:
        features["print_size"] = print_size

    font_match = FONT_SIZE_RE.search(combined)
    if font_match:
        features["font_size"] = float(font_match.group(1))
        evidence["font_size"] = font_match.group(0)

    ribbon_match = re.search(r"(\d+)\s+ribbon", combined)
    if ribbon_match:
        features["ribbon_markers_count"] = int(ribbon_match.group(1))
        evidence["ribbon_markers_count"] = ribbon_match.group(0)
    else:
        word_match = re.search(r"(one|two|three|four|five)\s+ribbon", combined)
        if word_match:
            features["ribbon_markers_count"] = WORD_NUMBERS.get(word_match.group(1))
            evidence["ribbon_markers_count"] = word_match.group(0)

    return features, evidence


def extract_translation(
    texts: Iterable[Optional[str]], seed_codes: Iterable[str]
) -> Tuple[Optional[str], Optional[str]]:
    combined = _normalize_texts(texts)
    for code, aliases in TRANSLATION_ALIASES.items():
        for alias in aliases:
            if alias in combined:
                return code, alias
    for code in seed_codes:
        code_lower = code.strip().lower()
        if not code_lower:
            continue
        if code_lower in combined:
            return code.upper(), code_lower
    return None, None


def extract_format(physical_format: Optional[str], texts: Iterable[Optional[str]]) -> Optional[str]:
    combined = _normalize_texts(texts)
    if physical_format:
        physical_lower = physical_format.lower()
        for fmt, phrases in FORMAT_KEYWORDS.items():
            if _find_phrases(physical_lower, phrases):
                return fmt
    for fmt, phrases in FORMAT_KEYWORDS.items():
        if _find_phrases(combined, phrases):
            return fmt
    return None


def extract_cover_color(texts: Iterable[Optional[str]]) -> Optional[str]:
    combined = _normalize_texts(texts)
    for color in COVER_COLORS:
        pattern = rf"\\b{color}\\b\\s+(leather|cover|hardcover|paperback|cloth|binding)"
        reverse = rf"(leather|cover|hardcover|paperback|cloth|binding)\\s+\\b{color}\\b"
        if re.search(pattern, combined) or re.search(reverse, combined):
            return color
    return None


def to_feature_evidence(evidence: Dict[str, Any]) -> str:
    return json.dumps(evidence, ensure_ascii=True)

import argparse
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from catalog_db import BibleCatalogDB
from feature_parser import (
    extract_cover_color,
    extract_format,
    extract_translation,
    parse_features,
    to_feature_evidence,
)
from openlibrary_client import OpenLibraryClient

try:
    from wikidata_client import WikidataClient
except ImportError:
    WikidataClient = None

LANGUAGE_MAP = {
    "eng": "English",
    "spa": "Spanish",
    "fre": "French",
    "ger": "German",
    "heb": "Hebrew",
    "grc": "Greek",
    "lat": "Latin",
}

BASE_QUERIES = [
    "study bible",
    "journaling bible",
    "red letter bible",
    "large print bible",
    "giant print bible",
    "wide margin bible",
    "thinline bible",
    "reference bible",
]

ISBN10_RE = re.compile(r"^\d{9}[0-9Xx]$")
ISBN13_RE = re.compile(r"^\d{13}$")
YEAR_RE = re.compile(r"\b(\d{4})\b")

BIBLE_EXCLUDE_PHRASES = [
    "study guide",
    "study guides",
    "bible study",
    "workbook",
    "teacher guide",
    "leader guide",
    "curriculum",
    "lesson",
    "survey",
    "handbook",
    "dictionary",
    "atlas",
    "encyclopedia",
    "companion",
    "introduction",
    "overview",
    "guidebook",
    "commentary",
    "commentaries",
    "storybook",
    "story book",
    "coloring book",
    "activity book",
]


def normalize_isbn(value: str) -> Optional[str]:
    digits = re.sub(r"[^0-9Xx]", "", value or "")
    if ISBN13_RE.match(digits):
        return digits
    if ISBN10_RE.match(digits):
        return digits.upper()
    return None


def isbn10_to_isbn13(isbn10: str) -> Optional[str]:
    if not ISBN10_RE.match(isbn10):
        return None
    core = "978" + isbn10[:-1]
    total = 0
    for idx, char in enumerate(core):
        factor = 1 if idx % 2 == 0 else 3
        total += int(char) * factor
    check = (10 - (total % 10)) % 10
    return core + str(check)


def parse_page_count(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return None


def extract_publish_year(value: Any) -> Optional[int]:
    if isinstance(value, int):
        if 0 < value < 10000:
            return value
        return None
    if isinstance(value, str):
        years = [int(match.group(1)) for match in YEAR_RE.finditer(value)]
        if years:
            return max(years)
    return None


def extract_languages(languages: Any) -> Optional[str]:
    if not isinstance(languages, list) or not languages:
        return None
    for lang in languages:
        if isinstance(lang, dict):
            key = lang.get("key")
            if key:
                code = key.split("/")[-1]
                return LANGUAGE_MAP.get(code, code)
        if isinstance(lang, str):
            return LANGUAGE_MAP.get(lang, lang)
    return None


def extract_publishers(publishers: Any) -> Optional[str]:
    if not isinstance(publishers, list) or not publishers:
        return None
    names = []
    for pub in publishers:
        if isinstance(pub, dict):
            name = pub.get("name")
        else:
            name = pub
        if name:
            names.append(str(name))
    return names[0] if names else None


def extract_subjects(subjects: Any) -> List[str]:
    items: List[str] = []
    if not isinstance(subjects, list):
        return items
    for subject in subjects:
        if isinstance(subject, dict):
            name = subject.get("name") or subject.get("title") or subject.get("key")
            if name:
                items.append(str(name))
        elif isinstance(subject, str):
            items.append(subject)
    return items


def extract_notes(notes: Any) -> Optional[str]:
    if isinstance(notes, dict):
        value = notes.get("value")
        return str(value) if value else None
    if isinstance(notes, list):
        return " ".join([str(note) for note in notes if note])
    if isinstance(notes, str):
        return notes
    return None


def is_probable_bible(title: Optional[str], subtitle: Optional[str], notes: Optional[str]) -> bool:
    parts = [text.strip() for text in (title, subtitle, notes) if text and text.strip()]
    combined = " ".join(parts).lower()
    if not combined:
        return False
    has_bible = "bible" in combined
    has_testament = "old testament" in combined or "new testament" in combined
    if not (has_bible or has_testament):
        return False
    for phrase in BIBLE_EXCLUDE_PHRASES:
        if phrase in combined:
            return False
    return True


def extract_identifiers(identifiers: Any) -> Tuple[Optional[str], Optional[str]]:
    isbn10 = None
    isbn13 = None
    if isinstance(identifiers, dict):
        isbn10_list = identifiers.get("isbn_10") or []
        isbn13_list = identifiers.get("isbn_13") or []
        if isbn10_list:
            isbn10 = normalize_isbn(isbn10_list[0])
        if isbn13_list:
            isbn13 = normalize_isbn(isbn13_list[0])
    return isbn10, isbn13


def normalize_openlibrary_entry(entry: Dict[str, Any], isbn_hint: Optional[str]) -> Dict[str, Any]:
    data = entry.get("data", {})
    source = entry.get("source")
    identifiers = data.get("identifiers") if source == "books" else None
    isbn10, isbn13 = extract_identifiers(identifiers)
    if source == "isbn":
        isbn10_list = data.get("isbn_10") or []
        isbn13_list = data.get("isbn_13") or []
        if not isbn10 and isbn10_list:
            isbn10 = normalize_isbn(isbn10_list[0])
        if not isbn13 and isbn13_list:
            isbn13 = normalize_isbn(isbn13_list[0])

    title = data.get("title")
    subtitle = data.get("subtitle")
    publish_date = data.get("publish_date")
    publishers = data.get("publishers")
    page_count = parse_page_count(data.get("number_of_pages") or data.get("pagination"))
    physical_format = data.get("physical_format")
    dimensions = data.get("physical_dimensions")
    subjects = extract_subjects(data.get("subjects"))
    notes = extract_notes(data.get("notes"))
    languages = extract_languages(data.get("languages"))
    source_key = data.get("key") or isbn_hint
    source_url = data.get("url")
    if not source_url and data.get("key"):
        source_url = f"https://openlibrary.org{data.get('key')}"

    if not source_url and isbn_hint:
        source_url = f"https://openlibrary.org/isbn/{isbn_hint}"

    return {
        "title": title,
        "subtitle": subtitle,
        "publish_date": publish_date,
        "publisher": extract_publishers(publishers),
        "page_count": page_count,
        "physical_format": physical_format,
        "dimensions": dimensions,
        "subjects": subjects,
        "notes": notes,
        "language": languages,
        "source_key": source_key,
        "source_url": source_url,
        "isbn10": isbn10,
        "isbn13": isbn13,
    }


def build_queries(seed_codes: Iterable[str]) -> List[str]:
    seen = set()
    queries: List[str] = []
    for query in BASE_QUERIES:
        if query not in seen:
            queries.append(query)
            seen.add(query)
    for code in seed_codes:
        code = code.strip()
        if not code:
            continue
        query = f"{code} bible"
        if query not in seen:
            queries.append(query)
            seen.add(query)
    return queries


def load_seed_translations(seed: str) -> Dict[str, str]:
    translations = {}
    for item in seed.split(","):
        code = item.strip()
        if not code:
            continue
        translations[code.upper()] = code.upper()
    return translations


def merge_wikidata(listing: Dict[str, Any], wikidata: Dict[str, Any]) -> None:
    for key in ("publisher", "publish_date", "language"):
        if not listing.get(key) and wikidata.get(key):
            listing[key] = wikidata.get(key)
    if not listing.get("source_url") and wikidata.get("source_url"):
        listing["source_url"] = wikidata.get("source_url")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Bible catalog database from Open Library.")
    parser.add_argument("--db", default="bible_catalog.db", help="SQLite database path")
    parser.add_argument("--max-results-per-query", type=int, default=200)
    parser.add_argument("--max-queries", type=int, default=50)
    parser.add_argument(
        "--seed-translations",
        default="KJV,NKJV,ESV,NIV,NLT,NASB,CSB",
        help="Comma separated translation codes",
    )
    parser.add_argument("--enable-wikidata", action="store_true")
    parser.add_argument("--export-json", default=None)
    parser.add_argument("--refresh-existing", action="store_true")
    parser.add_argument(
        "--recent-years",
        type=int,
        default=10,
        help="Only keep listings from the last N years (0 disables filtering)",
    )
    parser.add_argument("--no-resume", action="store_true", help="Ignore saved progress checkpoints")
    args = parser.parse_args()

    seed_translations = load_seed_translations(args.seed_translations)
    seed_codes = list(seed_translations.keys())

    db = BibleCatalogDB(args.db)
    db.ensure_translations(seed_translations)

    client = OpenLibraryClient()
    wikidata = WikidataClient() if args.enable_wikidata and WikidataClient else None

    queries = build_queries(seed_codes)
    max_queries = min(args.max_queries, len(queries))
    page_size = 100
    seen_isbns = set()
    log_every = 25
    recent_years = max(args.recent_years, 0)
    min_publish_year = None
    if recent_years:
        current_year = datetime.now(timezone.utc).year
        min_publish_year = current_year - (recent_years - 1)

    resume_query = None
    resume_page = None
    if not args.no_resume:
        resume_query = db.get_progress("bible_resume_query") or None
        resume_page_raw = db.get_progress("bible_resume_page")
        if resume_page_raw:
            try:
                resume_page = int(resume_page_raw)
            except ValueError:
                resume_page = None

    resume_query_idx = None
    if resume_query and resume_query in queries:
        resume_query_idx = queries.index(resume_query)
        if resume_query_idx >= max_queries:
            resume_query_idx = None
        elif resume_page is not None:
            print(f"Resuming after query '{resume_query}' page {resume_page}.")
        else:
            print(f"Resuming at query '{resume_query}'.")

    for query_idx, query in enumerate(queries[:max_queries]):
        total_processed = 0
        pages = max(1, math.ceil(args.max_results_per_query / page_size))
        page_start = 1
        if resume_query_idx is not None:
            if query_idx < resume_query_idx:
                continue
            if query_idx == resume_query_idx and resume_page is not None:
                page_start = resume_page + 1
                if page_start > pages:
                    continue
        for page in range(page_start, pages + 1):
            try:
                data = client.search(query, page=page, limit=page_size)
            except Exception as exc:
                print(f"Query '{query}' page {page} failed: {exc}")
                continue
            docs = data.get("docs", [])
            print(f"Query '{query}' page {page}: {len(docs)} docs")
            page_processed = 0
            page_attempted = 0
            page_filtered = 0
            page_recent_filtered = 0
            for doc in docs:
                for raw_isbn in doc.get("isbn", []) or []:
                    normalized = normalize_isbn(raw_isbn)
                    if not normalized:
                        continue
                    isbn10 = normalized if len(normalized) == 10 else None
                    isbn13 = normalized if len(normalized) == 13 else None
                    if isbn10 and not isbn13:
                        isbn13 = isbn10_to_isbn13(isbn10)
                    if normalized in seen_isbns or (isbn13 and isbn13 in seen_isbns):
                        continue
                    seen_isbns.add(normalized)
                    if isbn13:
                        seen_isbns.add(isbn13)
                    page_attempted += 1
                    if not args.refresh_existing and db.listing_exists(isbn13, isbn10):
                        continue

                    try:
                        edition = client.get_edition_by_isbn(isbn13 or isbn10)
                    except Exception as exc:
                        print(f"ISBN {isbn13 or isbn10} failed: {exc}")
                        continue
                    if not edition:
                        continue

                    normalized_entry = normalize_openlibrary_entry(edition, isbn13 or isbn10)
                    title = normalized_entry.get("title")
                    if not title:
                        continue
                    if not is_probable_bible(
                        title, normalized_entry.get("subtitle"), normalized_entry.get("notes")
                    ):
                        page_filtered += 1
                        continue
                    publish_year = extract_publish_year(normalized_entry.get("publish_date"))
                    if min_publish_year is not None:
                        if publish_year is None or publish_year < min_publish_year:
                            page_recent_filtered += 1
                            continue

                    texts = [
                        title,
                        normalized_entry.get("subtitle"),
                        normalized_entry.get("physical_format"),
                        normalized_entry.get("notes"),
                    ] + normalized_entry.get("subjects", [])

                    translation_code, translation_raw = extract_translation(texts, seed_codes)
                    format_value = extract_format(normalized_entry.get("physical_format"), texts)
                    cover_color = extract_cover_color(texts)

                    features, evidence = parse_features(texts)

                    listing = {
                        "isbn13": normalized_entry.get("isbn13") or isbn13,
                        "isbn10": normalized_entry.get("isbn10") or isbn10,
                        "title": title,
                        "subtitle": normalized_entry.get("subtitle"),
                        "translation": translation_code,
                        "translation_raw": translation_raw,
                        "language": normalized_entry.get("language"),
                        "publisher": normalized_entry.get("publisher"),
                        "publish_date": normalized_entry.get("publish_date"),
                        "page_count": normalized_entry.get("page_count"),
                        "format": format_value,
                        "dimensions": normalized_entry.get("dimensions"),
                        "cover_color": cover_color,
                        "source": "openlibrary",
                        "source_key": normalized_entry.get("source_key") or (isbn13 or isbn10),
                        "source_url": normalized_entry.get("source_url"),
                    }

                    if wikidata:
                        wikidata_info = wikidata.lookup_isbn(listing.get("isbn13"), listing.get("isbn10"))
                        merge_wikidata(listing, wikidata_info)

                    listing_id = db.upsert_listing(listing)
                    if listing_id:
                        features["feature_evidence"] = to_feature_evidence(evidence)
                        db.upsert_features(listing_id, features)
                        total_processed += 1
                        page_processed += 1

                    if page_attempted % log_every == 0:
                        print(
                            f"  Page {page}: attempted {page_attempted} ISBNs, "
                            f"stored {page_processed} listings, filtered {page_filtered}, "
                            f"recent-filtered {page_recent_filtered}"
                        )

            print(f"Processed {total_processed} listings so far for query '{query}'.")

            db.set_progress("bible_resume_query", query)
            db.set_progress("bible_resume_page", str(page))
            db.conn.commit()
            print(
                f"Committed page {page} for query '{query}'. "
                f"Stored {page_processed} listings, filtered {page_filtered}, "
                f"recent-filtered {page_recent_filtered} on this page."
            )

        db.conn.commit()

    db.conn.commit()

    if args.export_json:
        exported = db.export_catalog_json(args.export_json)
        print(f"Exported {exported} listings to {args.export_json}")

    db.close()


if __name__ == "__main__":
    main()

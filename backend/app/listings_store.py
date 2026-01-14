import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


LOCAL_DATA_DIR = Path(os.getenv("LOCAL_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
LOCAL_DATA_MAP = {
    "insulin_devices_v1": "insulin_devices.json",
    "vehicles_catalog_v1": "vehicles_catalog.json",
    "bible_catalog_v1": "bible_catalog.json",
}

VEHICLE_CATALOG_DB = Path(
    os.getenv(
        "VEHICLE_CATALOG_DB_PATH",
        Path(__file__).resolve().parents[2] / "vehicles_catalog.db",
    )
)

BIBLE_CATALOG_DB = Path(
    os.getenv(
        "BIBLE_CATALOG_DB_PATH",
        Path(__file__).resolve().parents[2] / "bible_catalog.db",
    )
)

YEAR_RE = re.compile(r"\b(\d{4})\b")


def _normalize_vehicle_type(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Local data not found: {path}")
    return json.loads(path.read_text())


def _extract_year(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value if 0 < value < 10000 else None
    if isinstance(value, str):
        years = [int(match.group(1)) for match in YEAR_RE.finditer(value)]
        return max(years) if years else None
    return None


def _normalize_listing(item: Dict[str, Any]) -> Dict[str, Any]:
    if "id" not in item and "product_id" in item:
        item = {**item, "id": item.get("product_id")}
    return item


def _vehicle_catalog_id(year: Any, make: Any, model: Any) -> str:
    return f"{year}-{make}-{model}"


def _load_vehicle_catalog_from_sqlite() -> List[Dict[str, Any]]:
    if not VEHICLE_CATALOG_DB.exists():
        raise FileNotFoundError(f"Vehicle catalog DB not found: {VEHICLE_CATALOG_DB}")
    max_rows = int(os.getenv("VEHICLE_CATALOG_MAX_ROWS", "0"))
    passenger_only = os.getenv("VEHICLE_CATALOG_PASSENGER_ONLY", "1") == "1"
    conn = sqlite3.connect(str(VEHICLE_CATALOG_DB))
    conn.row_factory = sqlite3.Row
    try:
        supports_body_style = True
        params: list[Any] = []
        query = (
            "SELECT year, make_name, model_name, vehicle_type, body_style, source "
            "FROM v_catalog"
        )
        if passenger_only:
            query += " WHERE lower(vehicle_type) LIKE ?"
            params.append("%passenger%")
        query += " ORDER BY year DESC, make_name ASC, model_name ASC"
        if max_rows > 0:
            query += " LIMIT ?"
            params.append(max_rows)
        try:
            rows = conn.execute(query, params).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such column: body_style" not in str(exc):
                raise
            supports_body_style = False
            params = []
            query = "SELECT year, make_name, model_name, vehicle_type, source FROM v_catalog"
            if passenger_only:
                query += " WHERE lower(vehicle_type) LIKE ?"
                params.append("%passenger%")
            query += " ORDER BY year DESC, make_name ASC, model_name ASC"
            if max_rows > 0:
                query += " LIMIT ?"
                params.append(max_rows)
            rows = conn.execute(query, params).fetchall()

        if passenger_only and not rows:
            params = []
            if supports_body_style:
                query = (
                    "SELECT year, make_name, model_name, vehicle_type, body_style, source "
                    "FROM v_catalog"
                )
            else:
                query = "SELECT year, make_name, model_name, vehicle_type, source FROM v_catalog"
            query += " ORDER BY year DESC, make_name ASC, model_name ASC"
            if max_rows > 0:
                query += " LIMIT ?"
                params.append(max_rows)
            rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    listings: List[Dict[str, Any]] = []
    for row in rows:
        listing = {
            "id": _vehicle_catalog_id(row["year"], row["make_name"], row["model_name"]),
            "year": row["year"],
            "make_name": row["make_name"],
            "model_name": row["model_name"],
            "vehicle_type": row["vehicle_type"],
            "body_style": row["body_style"] if "body_style" in row.keys() else None,
            "source": row["source"],
            "images": [],
        }
        listings.append(listing)
    return listings


def _load_bible_catalog_from_sqlite() -> List[Dict[str, Any]]:
    if not BIBLE_CATALOG_DB.exists():
        raise FileNotFoundError(f"Bible catalog DB not found: {BIBLE_CATALOG_DB}")
    max_rows = int(os.getenv("BIBLE_CATALOG_MAX_ROWS", "0"))
    conn = sqlite3.connect(str(BIBLE_CATALOG_DB))
    conn.row_factory = sqlite3.Row
    try:
        query = """
            SELECT
                listings.listing_id,
                listings.isbn13,
                listings.isbn10,
                listings.title,
                listings.subtitle,
                listings.translation,
                listings.translation_raw,
                listings.language,
                listings.publisher,
                listings.publish_date,
                listings.page_count,
                listings.format,
                listings.dimensions,
                listings.cover_color,
                listings.source,
                listings.source_url,
                features.red_letter,
                features.study_bible,
                features.commentary_notes,
                features.cross_references,
                features.concordance,
                features.maps,
                features.ribbon_markers_count,
                features.thumb_indexed,
                features.gilded_edges,
                features.journaling,
                features.single_column,
                features.two_column,
                features.devotionals,
                features.reading_plan,
                features.print_size,
                features.font_size
            FROM listings
            LEFT JOIN features ON features.listing_id = listings.listing_id
            ORDER BY listings.title ASC
        """
        params: list[Any] = []
        if max_rows > 0:
            query += " LIMIT ?"
            params.append(max_rows)
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    listings: List[Dict[str, Any]] = []
    for row in rows:
        publish_year = _extract_year(row["publish_date"])
        listing_id = row["isbn13"] or row["isbn10"] or f"listing-{row['listing_id']}"
        listing = {
            "id": listing_id,
            "isbn13": row["isbn13"],
            "isbn10": row["isbn10"],
            "title": row["title"],
            "subtitle": row["subtitle"],
            "translation": row["translation"],
            "translation_raw": row["translation_raw"],
            "language": row["language"],
            "publisher": row["publisher"],
            "publish_date": row["publish_date"],
            "publish_year": publish_year,
            "page_count": row["page_count"],
            "format": row["format"],
            "dimensions": row["dimensions"],
            "cover_color": row["cover_color"],
            "source": row["source"],
            "source_url": row["source_url"],
            "red_letter": bool(row["red_letter"]) if row["red_letter"] is not None else None,
            "study_bible": bool(row["study_bible"]) if row["study_bible"] is not None else None,
            "commentary_notes": bool(row["commentary_notes"]) if row["commentary_notes"] is not None else None,
            "cross_references": bool(row["cross_references"]) if row["cross_references"] is not None else None,
            "concordance": bool(row["concordance"]) if row["concordance"] is not None else None,
            "maps": bool(row["maps"]) if row["maps"] is not None else None,
            "ribbon_markers_count": row["ribbon_markers_count"],
            "thumb_indexed": bool(row["thumb_indexed"]) if row["thumb_indexed"] is not None else None,
            "gilded_edges": bool(row["gilded_edges"]) if row["gilded_edges"] is not None else None,
            "journaling": bool(row["journaling"]) if row["journaling"] is not None else None,
            "single_column": bool(row["single_column"]) if row["single_column"] is not None else None,
            "two_column": bool(row["two_column"]) if row["two_column"] is not None else None,
            "devotionals": bool(row["devotionals"]) if row["devotionals"] is not None else None,
            "reading_plan": bool(row["reading_plan"]) if row["reading_plan"] is not None else None,
            "print_size": row["print_size"],
            "font_size": row["font_size"],
            "images": [],
        }
        listings.append(listing)
    return listings


def load_local_listings(provider_key: str) -> List[Dict[str, Any]]:
    if provider_key == "vehicles_catalog_v1":
        json_path = LOCAL_DATA_DIR / LOCAL_DATA_MAP[provider_key]
        if json_path.exists():
            data = _load_json(json_path)
            if isinstance(data, list):
                listings = data
            else:
                listings = data.get("listings") or data.get("products") or []
            passenger_only = os.getenv("VEHICLE_CATALOG_PASSENGER_ONLY", "1") == "1"
            if passenger_only:
                listings = [
                    item
                    for item in listings
                    if _normalize_vehicle_type(item.get("vehicleType") or item.get("vehicle_type")).find("passenger") >= 0
                ]
            normalized = []
            for item in listings:
                if not isinstance(item, dict):
                    continue
                listing = dict(item)
                listing.setdefault(
                    "id",
                    _vehicle_catalog_id(
                        listing.get("year"),
                        listing.get("make") or listing.get("make_name"),
                        listing.get("model") or listing.get("model_name"),
                    ),
                )
                listing.setdefault("make_name", listing.get("make"))
                listing.setdefault("model_name", listing.get("model"))
                listing.setdefault("vehicle_type", listing.get("vehicleType"))
                listing.setdefault("body_style", listing.get("bodyStyle"))
                listing.setdefault("images", [])
                normalized.append(listing)
            return normalized
        return _load_vehicle_catalog_from_sqlite()

    if provider_key == "bible_catalog_v1":
        json_path = LOCAL_DATA_DIR / LOCAL_DATA_MAP[provider_key]
        if json_path.exists():
            data = _load_json(json_path)
            if isinstance(data, list):
                listings = data
            else:
                listings = data.get("listings") or data.get("products") or []
            normalized = []
            for item in listings:
                if not isinstance(item, dict):
                    continue
                listing = dict(item)
                listing.setdefault(
                    "id",
                    listing.get("isbn13")
                    or listing.get("isbn10")
                    or listing.get("id")
                    or f"listing-{listing.get('listing_id')}",
                )
                listing.setdefault("publish_year", _extract_year(listing.get("publish_date")))
                listing.setdefault("images", [])
                normalized.append(listing)
            return normalized
        return _load_bible_catalog_from_sqlite()

    filename = LOCAL_DATA_MAP.get(provider_key, f"{provider_key}.json")
    data = _load_json(LOCAL_DATA_DIR / filename)
    if isinstance(data, list):
        listings = data
    else:
        listings = data.get("listings") or data.get("products") or []
    return [_normalize_listing(item) for item in listings if isinstance(item, dict)]

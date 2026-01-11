import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


LOCAL_DATA_DIR = Path(os.getenv("LOCAL_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
LOCAL_DATA_MAP = {
    "insulin_devices_v1": "insulin_devices.json",
    "vehicles_catalog_v1": "vehicles_catalog.json",
}

VEHICLE_CATALOG_DB = Path(
    os.getenv(
        "VEHICLE_CATALOG_DB_PATH",
        Path(__file__).resolve().parents[2] / "vehicles_catalog.db",
    )
)


def _normalize_vehicle_type(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Local data not found: {path}")
    return json.loads(path.read_text())


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
        query = (
            "SELECT year, make_name, model_name, vehicle_type, source "
            "FROM v_catalog"
        )
        params: list[Any] = []
        if passenger_only:
            query += " WHERE lower(vehicle_type) LIKE ?"
            params.append("%passenger%")
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
            "source": row["source"],
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
                listing.setdefault("images", [])
                normalized.append(listing)
            return normalized
        return _load_vehicle_catalog_from_sqlite()

    filename = LOCAL_DATA_MAP.get(provider_key, f"{provider_key}.json")
    data = _load_json(LOCAL_DATA_DIR / filename)
    if isinstance(data, list):
        listings = data
    else:
        listings = data.get("listings") or data.get("products") or []
    return [_normalize_listing(item) for item in listings if isinstance(item, dict)]

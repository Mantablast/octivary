import json
import os
from pathlib import Path
from typing import Any, Dict, List


LOCAL_DATA_DIR = Path(os.getenv("LOCAL_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
LOCAL_DATA_MAP = {
    "insulin_devices_v1": "insulin_devices.json",
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Local data not found: {path}")
    return json.loads(path.read_text())


def _normalize_listing(item: Dict[str, Any]) -> Dict[str, Any]:
    if "id" not in item and "product_id" in item:
        item = {**item, "id": item.get("product_id")}
    return item


def load_local_listings(provider_key: str) -> List[Dict[str, Any]]:
    filename = LOCAL_DATA_MAP.get(provider_key, f"{provider_key}.json")
    data = _load_json(LOCAL_DATA_DIR / filename)
    listings = data.get("listings") or data.get("products") or []
    return [_normalize_listing(item) for item in listings if isinstance(item, dict)]

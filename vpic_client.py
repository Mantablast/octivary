import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests


class VpicClient:
    def __init__(
        self,
        base_url: str = "https://vpic.nhtsa.dot.gov/api/vehicles",
        timeout: float = 10.0,
        max_retries: int = 5,
        backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 16.0,
        throttle_seconds: float = 0.2,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.throttle_seconds = throttle_seconds
        self.session = session or requests.Session()

    def close(self) -> None:
        self.session.close()

    def _request_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        params = dict(params or {})
        params["format"] = "json"

        attempt = 0
        backoff = self.backoff_seconds
        while True:
            attempt += 1
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt > self.max_retries:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_seconds)
                continue

            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt > self.max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                wait = backoff
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        wait = backoff
                time.sleep(wait)
                backoff = min(backoff * 2, self.max_backoff_seconds)
                continue

            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                if attempt > self.max_retries:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_seconds)
                continue
            if self.throttle_seconds:
                time.sleep(self.throttle_seconds)
            return data

    def get_makes(self) -> List[str]:
        data = self._request_json("GetAllMakes")
        results = data.get("Results") or []
        seen = set()
        makes: List[str] = []
        for entry in results:
            name = str(entry.get("Make_Name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            makes.append(name)
        return sorted(makes)

    def get_models_for_make_year(self, make_name: str, year: int) -> List[Dict[str, Any]]:
        safe_make = quote(make_name, safe="")
        path = f"GetModelsForMakeYear/make/{safe_make}/modelyear/{year}"
        try:
            data = self._request_json(path)
        except requests.HTTPError as exc:
            response = exc.response
            if response is not None and response.status_code == 404:
                return []
            raise
        except (requests.exceptions.JSONDecodeError, ValueError):
            return []
        results = data.get("Results") or []
        models: List[Dict[str, Any]] = []
        seen = set()
        for entry in results:
            model_name = str(entry.get("Model_Name") or "").strip()
            if not model_name or model_name in seen:
                continue
            seen.add(model_name)
            vehicle_type = entry.get("VehicleTypeName")
            models.append({"model_name": model_name, "vehicle_type": vehicle_type})
        return models

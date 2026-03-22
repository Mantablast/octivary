import random
import time
from typing import Any, Dict, Optional

import requests


class OpenLibraryClient:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        base_url: str = "https://openlibrary.org",
        timeout: int = 20,
        max_retries: int = 3,
        rate_limit_sleep: float = 0.2,
    ) -> None:
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_sleep = rate_limit_sleep

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"retryable {response.status_code}")
                response.raise_for_status()
                if self.rate_limit_sleep:
                    time.sleep(self.rate_limit_sleep + random.uniform(0, 0.1))
                return response
            except requests.RequestException:
                if attempt >= self.max_retries:
                    raise
                backoff = min(2 ** (attempt - 1), 8)
                time.sleep(backoff + random.uniform(0, 0.25))
        raise RuntimeError("OpenLibrary request failed")

    def search(self, query: str, page: int = 1, limit: int = 100) -> Dict[str, Any]:
        params = {
            "q": query,
            "page": page,
            "limit": limit,
            "fields": "title,subtitle,isbn,edition_key,language,publisher,first_publish_year,subject",
        }
        response = self._get("/search.json", params=params)
        return response.json()

    def get_edition_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        params = {"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"}
        response = self._get("/api/books", params=params)
        data = response.json().get(f"ISBN:{isbn}")
        if data:
            return {"source": "books", "data": data}
        try:
            response = self._get(f"/isbn/{isbn}.json")
        except requests.RequestException:
            return None
        return {"source": "isbn", "data": response.json()}

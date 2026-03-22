import json
import random
import time
from typing import Any, Dict, Optional

import requests


class WikidataClient:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        endpoint: str = "https://query.wikidata.org/sparql",
        timeout: int = 20,
        max_retries: int = 3,
        rate_limit_sleep: float = 0.5,
    ) -> None:
        self.session = session or requests.Session()
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_sleep = rate_limit_sleep

    def _get(self, query: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "OctivaryBibleCatalog/1.0 (metadata-only)",
        }
        params = {"query": query, "format": "json"}
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    self.endpoint, params=params, headers=headers, timeout=self.timeout
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"retryable {response.status_code}")
                response.raise_for_status()
                if self.rate_limit_sleep:
                    time.sleep(self.rate_limit_sleep + random.uniform(0, 0.2))
                return response.json()
            except requests.RequestException:
                if attempt >= self.max_retries:
                    raise
                backoff = min(2 ** (attempt - 1), 8)
                time.sleep(backoff + random.uniform(0, 0.5))
        raise RuntimeError("Wikidata request failed")

    def lookup_isbn(self, isbn13: Optional[str], isbn10: Optional[str]) -> Dict[str, Any]:
        conditions = []
        if isbn13:
            conditions.append(f'{{ ?item wdt:P957 "{isbn13}". }}')
        if isbn10:
            conditions.append(f'{{ ?item wdt:P212 "{isbn10}". }}')
        if not conditions:
            return {}

        query = (
            "SELECT ?item ?itemLabel ?publisherLabel ?publicationDate ?languageLabel WHERE {"
            + " UNION ".join(conditions)
            + " OPTIONAL { ?item wdt:P123 ?publisher. }"
            + " OPTIONAL { ?item wdt:P577 ?publicationDate. }"
            + " OPTIONAL { ?item wdt:P407 ?language. }"
            + " SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". }"
            + " } LIMIT 1"
        )
        data = self._get(query)
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return {}
        row = bindings[0]
        return {
            "source_url": row.get("item", {}).get("value"),
            "publisher": row.get("publisherLabel", {}).get("value"),
            "publish_date": row.get("publicationDate", {}).get("value"),
            "language": row.get("languageLabel", {}).get("value"),
        }

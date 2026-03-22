import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .models import DynamicSearchResult, GeneratedFilterCacheEntry
from .runtime import generated_filter_store_backend

_BOTO3_AVAILABLE = False

try:
    import boto3  # type: ignore

    _BOTO3_AVAILABLE = True
except Exception:
    _BOTO3_AVAILABLE = False


def _utcnow() -> datetime:
    return datetime.utcnow()


def _local_db_path() -> Path:
    env_path = os.getenv("GENERATED_FILTERS_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "data" / "generated_filters.db"


class GeneratedFilterStore(Protocol):
    def get_record(self, normalized_query: str) -> GeneratedFilterCacheEntry | None: ...

    def upsert_result(
        self,
        normalized_query: str,
        source_query: str,
        result: DynamicSearchResult,
    ) -> GeneratedFilterCacheEntry: ...

    def record_reuse(self, normalized_query: str) -> None: ...


class LocalGeneratedFilterStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_filter_cache (
                    normalized_query TEXT PRIMARY KEY,
                    source_query TEXT NOT NULL,
                    listing_count INTEGER NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_record(self, row: sqlite3.Row | None) -> GeneratedFilterCacheEntry | None:
        if row is None:
            return None
        return GeneratedFilterCacheEntry(
            normalized_query=row["normalized_query"],
            source_query=row["source_query"],
            listing_count=int(row["listing_count"]),
            hit_count=int(row["hit_count"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            result=DynamicSearchResult(**json.loads(row["result_json"])),
        )

    def get_record(self, normalized_query: str) -> GeneratedFilterCacheEntry | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM generated_filter_cache WHERE normalized_query = ?",
                (normalized_query,),
            ).fetchone()
        finally:
            conn.close()
        return self._row_to_record(row)

    def upsert_result(
        self,
        normalized_query: str,
        source_query: str,
        result: DynamicSearchResult,
    ) -> GeneratedFilterCacheEntry:
        current = self.get_record(normalized_query)
        now = _utcnow()
        created_at = current.created_at if current else now
        hit_count = current.hit_count if current else 0
        listing_count = len(result.generated_listings or [])
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO generated_filter_cache (
                    normalized_query,
                    source_query,
                    listing_count,
                    hit_count,
                    created_at,
                    updated_at,
                    result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(normalized_query) DO UPDATE SET
                    source_query = excluded.source_query,
                    listing_count = excluded.listing_count,
                    hit_count = excluded.hit_count,
                    updated_at = excluded.updated_at,
                    result_json = excluded.result_json
                """,
                (
                    normalized_query,
                    source_query,
                    listing_count,
                    hit_count,
                    created_at.isoformat(),
                    now.isoformat(),
                    json.dumps(result.model_dump()),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        record = self.get_record(normalized_query)
        if record is None:
            raise RuntimeError("Failed to persist generated filter cache entry.")
        return record

    def record_reuse(self, normalized_query: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE generated_filter_cache
                SET hit_count = hit_count + 1,
                    updated_at = ?
                WHERE normalized_query = ?
                """,
                (_utcnow().isoformat(), normalized_query),
            )
            conn.commit()
        finally:
            conn.close()


class DynamoGeneratedFilterStore:
    def __init__(self, table_name: str) -> None:
        resource = boto3.resource("dynamodb")
        self.table = resource.Table(table_name)

    def _item_to_record(self, item: dict[str, Any] | None) -> GeneratedFilterCacheEntry | None:
        if not item:
            return None
        return GeneratedFilterCacheEntry(
            normalized_query=item["normalized_query"],
            source_query=item["source_query"],
            listing_count=int(item.get("listing_count", 0)),
            hit_count=int(item.get("hit_count", 0)),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            result=DynamicSearchResult(**item["result"]),
        )

    def get_record(self, normalized_query: str) -> GeneratedFilterCacheEntry | None:
        response = self.table.get_item(Key={"normalized_query": normalized_query})
        return self._item_to_record(response.get("Item"))

    def upsert_result(
        self,
        normalized_query: str,
        source_query: str,
        result: DynamicSearchResult,
    ) -> GeneratedFilterCacheEntry:
        current = self.get_record(normalized_query)
        now = _utcnow()
        item = {
            "normalized_query": normalized_query,
            "source_query": source_query,
            "listing_count": len(result.generated_listings or []),
            "hit_count": current.hit_count if current else 0,
            "created_at": (current.created_at if current else now).isoformat(),
            "updated_at": now.isoformat(),
            "result": result.model_dump(),
        }
        self.table.put_item(Item=item)
        record = self.get_record(normalized_query)
        if record is None:
            raise RuntimeError("Failed to persist generated filter cache entry.")
        return record

    def record_reuse(self, normalized_query: str) -> None:
        current = self.get_record(normalized_query)
        if current is None:
            return
        item = current.model_dump()
        item["hit_count"] = current.hit_count + 1
        item["updated_at"] = _utcnow().isoformat()
        item["created_at"] = current.created_at.isoformat()
        item["result"] = current.result.model_dump()
        self.table.put_item(Item=item)


_GENERATED_FILTER_STORE: GeneratedFilterStore | None = None


def get_generated_filter_store() -> GeneratedFilterStore:
    global _GENERATED_FILTER_STORE
    if _GENERATED_FILTER_STORE is not None:
        return _GENERATED_FILTER_STORE

    backend = generated_filter_store_backend()
    if backend == "dynamodb" and _BOTO3_AVAILABLE:
        table_name = os.getenv("GENERATED_FILTERS_TABLE")
        if table_name:
            _GENERATED_FILTER_STORE = DynamoGeneratedFilterStore(table_name)
            return _GENERATED_FILTER_STORE

    _GENERATED_FILTER_STORE = LocalGeneratedFilterStore(_local_db_path())
    return _GENERATED_FILTER_STORE

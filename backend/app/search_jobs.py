import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from .models import DynamicSearchJob, DynamicSearchResult
from .runtime import search_job_store_backend

_BOTO3_AVAILABLE = False

try:
    import boto3  # type: ignore

    _BOTO3_AVAILABLE = True
except Exception:
    _BOTO3_AVAILABLE = False


def _utcnow() -> datetime:
    return datetime.utcnow()


def _local_db_path() -> Path:
    env_path = os.getenv("SEARCH_JOBS_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "data" / "search_jobs.db"


class SearchJobStore(Protocol):
    def create_job(self, user_id: str, query: str, limit: int, profile: str) -> DynamicSearchJob: ...

    def get_job(self, job_id: str) -> DynamicSearchJob | None: ...

    def list_jobs(self, user_id: str, limit: int = 20) -> list[DynamicSearchJob]: ...

    def update_job(self, job_id: str, **updates: Any) -> DynamicSearchJob | None: ...

    def delete_job(self, job_id: str) -> bool: ...


class LocalSearchJobStore:
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
                CREATE TABLE IF NOT EXISTS dynamic_search_jobs (
                    job_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    limit_value INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    current_step TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_message TEXT,
                    result_json TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_job(self, row: sqlite3.Row | None) -> DynamicSearchJob | None:
        if row is None:
            return None
        result_payload = row["result_json"]
        result = DynamicSearchResult(**json.loads(result_payload)) if result_payload else None
        return DynamicSearchJob(
            job_id=row["job_id"],
            user_id=row["user_id"],
            query=row["query"],
            limit=int(row["limit_value"]),
            status=row["status"],
            progress=float(row["progress"]),
            current_step=row["current_step"],
            profile=row["profile"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            error_message=row["error_message"],
            result=result,
        )

    def create_job(self, user_id: str, query: str, limit: int, profile: str) -> DynamicSearchJob:
        now = _utcnow()
        job = DynamicSearchJob(
            job_id=str(uuid4()),
            user_id=user_id,
            query=query,
            limit=limit,
            status="queued",
            progress=0.05,
            current_step="Search job created",
            profile=profile,
            created_at=now,
            updated_at=now,
        )
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO dynamic_search_jobs (
                    job_id,
                    user_id,
                    query,
                    limit_value,
                    status,
                    progress,
                    current_step,
                    profile,
                    created_at,
                    updated_at,
                    error_message,
                    result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.user_id,
                    job.query,
                    job.limit,
                    job.status,
                    job.progress,
                    job.current_step,
                    job.profile,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.error_message,
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return job

    def get_job(self, job_id: str) -> DynamicSearchJob | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM dynamic_search_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        finally:
            conn.close()
        return self._row_to_job(row)

    def list_jobs(self, user_id: str, limit: int = 20) -> list[DynamicSearchJob]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM dynamic_search_jobs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, max(1, min(limit, 50))),
            ).fetchall()
        finally:
            conn.close()
        return [job for job in (self._row_to_job(row) for row in rows) if job is not None]

    def update_job(self, job_id: str, **updates: Any) -> DynamicSearchJob | None:
        current = self.get_job(job_id)
        if not current:
            return None

        data = current.model_dump()
        data.update(updates)
        data["updated_at"] = _utcnow()
        result = data.get("result")
        result_json = None
        if isinstance(result, DynamicSearchResult):
            result_json = json.dumps(result.model_dump())
        elif isinstance(result, dict):
            result_json = json.dumps(result)

        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE dynamic_search_jobs
                SET limit_value = ?,
                    status = ?,
                    progress = ?,
                    current_step = ?,
                    profile = ?,
                    updated_at = ?,
                    error_message = ?,
                    result_json = ?
                WHERE job_id = ?
                """,
                (
                    int(data["limit"]),
                    data["status"],
                    float(data["progress"]),
                    data["current_step"],
                    data["profile"],
                    data["updated_at"].isoformat(),
                    data.get("error_message"),
                    result_json,
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return self.get_job(job_id)

    def delete_job(self, job_id: str) -> bool:
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM dynamic_search_jobs WHERE job_id = ?",
                (job_id,),
            )
            conn.commit()
        finally:
            conn.close()
        return cursor.rowcount > 0


class DynamoSearchJobStore:
    def __init__(self, table_name: str) -> None:
        resource = boto3.resource("dynamodb")
        self.table = resource.Table(table_name)

    def _item_to_job(self, item: dict[str, Any] | None) -> DynamicSearchJob | None:
        if not item:
            return None
        return DynamicSearchJob(
            job_id=item["job_id"],
            user_id=item["user_id"],
            query=item["query"],
            limit=int(item["limit"]),
            status=item["status"],
            progress=float(item["progress"]),
            current_step=item["current_step"],
            profile=item["profile"],
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            error_message=item.get("error_message"),
            result=DynamicSearchResult(**item["result"]) if item.get("result") else None,
        )

    def create_job(self, user_id: str, query: str, limit: int, profile: str) -> DynamicSearchJob:
        now = _utcnow()
        job = DynamicSearchJob(
            job_id=str(uuid4()),
            user_id=user_id,
            query=query,
            limit=limit,
            status="queued",
            progress=0.05,
            current_step="Search job created",
            profile=profile,
            created_at=now,
            updated_at=now,
        )
        item = job.model_dump()
        item["created_at"] = job.created_at.isoformat()
        item["updated_at"] = job.updated_at.isoformat()
        item["result"] = None
        self.table.put_item(Item=item)
        return job

    def get_job(self, job_id: str) -> DynamicSearchJob | None:
        response = self.table.get_item(Key={"job_id": job_id})
        return self._item_to_job(response.get("Item"))

    def list_jobs(self, user_id: str, limit: int = 20) -> list[DynamicSearchJob]:
        from boto3.dynamodb.conditions import Key  # type: ignore

        response = self.table.query(
            IndexName="UserIdIndex",
            KeyConditionExpression=Key("user_id").eq(user_id),
            Limit=max(1, min(limit, 50)),
            ScanIndexForward=False,
        )
        items = response.get("Items", [])
        return [job for job in (self._item_to_job(item) for item in items) if job is not None]

    def update_job(self, job_id: str, **updates: Any) -> DynamicSearchJob | None:
        current = self.get_job(job_id)
        if not current:
            return None
        data = current.model_dump()
        data.update(updates)
        data["updated_at"] = _utcnow()
        item = dict(data)
        item["created_at"] = data["created_at"].isoformat()
        item["updated_at"] = data["updated_at"].isoformat()
        result = item.get("result")
        if isinstance(result, DynamicSearchResult):
            item["result"] = result.model_dump()
        self.table.put_item(Item=item)
        return self.get_job(job_id)

    def delete_job(self, job_id: str) -> bool:
        self.table.delete_item(Key={"job_id": job_id})
        return True


_SEARCH_JOB_STORE: SearchJobStore | None = None


def get_search_job_store() -> SearchJobStore:
    global _SEARCH_JOB_STORE
    if _SEARCH_JOB_STORE is not None:
        return _SEARCH_JOB_STORE

    backend = search_job_store_backend()
    if backend == "dynamodb" and _BOTO3_AVAILABLE:
        table_name = os.getenv("SEARCH_JOBS_TABLE")
        if table_name:
            _SEARCH_JOB_STORE = DynamoSearchJobStore(table_name)
            return _SEARCH_JOB_STORE

    _SEARCH_JOB_STORE = LocalSearchJobStore(_local_db_path())
    return _SEARCH_JOB_STORE

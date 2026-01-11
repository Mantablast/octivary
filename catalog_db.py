import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


class CatalogDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS makes (
                make_id INTEGER PRIMARY KEY AUTOINCREMENT,
                make_name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS models (
                model_id INTEGER PRIMARY KEY AUTOINCREMENT,
                make_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                UNIQUE(make_id, model_name),
                FOREIGN KEY(make_id) REFERENCES makes(make_id)
            );

            CREATE TABLE IF NOT EXISTS model_years (
                model_year_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                vehicle_type TEXT NULL,
                source TEXT NOT NULL DEFAULT 'NHTSA_vPIC',
                created_at TEXT NOT NULL,
                UNIQUE(model_id, year),
                FOREIGN KEY(model_id) REFERENCES models(model_id)
            );

            CREATE TABLE IF NOT EXISTS progress (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_models_make_id ON models(make_id);
            CREATE INDEX IF NOT EXISTS idx_model_years_year ON model_years(year);

            CREATE VIEW IF NOT EXISTS v_catalog AS
            SELECT
                model_years.year AS year,
                makes.make_name AS make_name,
                models.model_name AS model_name,
                model_years.vehicle_type AS vehicle_type,
                model_years.source AS source
            FROM model_years
            JOIN models ON models.model_id = model_years.model_id
            JOIN makes ON makes.make_id = models.make_id;
            """
        )
        self.conn.commit()

    def set_progress(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO progress (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_progress(self, key: str) -> Optional[str]:
        row = self.conn.execute("SELECT value FROM progress WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def is_year_completed(self, year: int) -> bool:
        return self.get_progress(f"completed_year_{year}") is not None

    def ensure_make(self, make_name: str) -> int:
        self.conn.execute("INSERT OR IGNORE INTO makes (make_name) VALUES (?)", (make_name,))
        row = self.conn.execute("SELECT make_id FROM makes WHERE make_name = ?", (make_name,)).fetchone()
        return int(row["make_id"]) if row else 0

    def ensure_model(self, make_id: int, model_name: str) -> int:
        self.conn.execute(
            "INSERT OR IGNORE INTO models (make_id, model_name) VALUES (?, ?)",
            (make_id, model_name),
        )
        row = self.conn.execute(
            "SELECT model_id FROM models WHERE make_id = ? AND model_name = ?",
            (make_id, model_name),
        ).fetchone()
        return int(row["model_id"]) if row else 0

    def insert_model_year(
        self,
        model_id: int,
        year: int,
        vehicle_type: Optional[str],
        source: str = "NHTSA_vPIC",
        created_at: Optional[str] = None,
    ) -> None:
        created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT OR IGNORE INTO model_years
                (model_id, year, vehicle_type, source, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (model_id, year, vehicle_type, source, created_at),
        )
        if vehicle_type:
            self.conn.execute(
                """
                UPDATE model_years
                SET vehicle_type = ?
                WHERE model_id = ? AND year = ?
                  AND (vehicle_type IS NULL OR vehicle_type = '')
                """,
                (vehicle_type, model_id, year),
            )

    def list_makes(self, prefix: Optional[str] = None, limit: int = 50) -> List[str]:
        params: List[Any] = []
        sql = "SELECT make_name FROM makes"
        if prefix:
            sql += " WHERE make_name LIKE ?"
            params.append(f"{prefix}%")
        sql += " ORDER BY make_name ASC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [row["make_name"] for row in rows]

    def list_models(
        self,
        make: str,
        year: Optional[int] = None,
        contains: Optional[str] = None,
        limit: int = 100,
    ) -> List[str]:
        params: List[Any] = [make]
        sql = (
            "SELECT DISTINCT models.model_name "
            "FROM models "
            "JOIN makes ON makes.make_id = models.make_id "
            "LEFT JOIN model_years ON model_years.model_id = models.model_id "
            "WHERE makes.make_name = ?"
        )
        if year is not None:
            sql += " AND model_years.year = ?"
            params.append(year)
        if contains:
            sql += " AND models.model_name LIKE ? COLLATE NOCASE"
            params.append(f"%{contains}%")
        sql += " ORDER BY models.model_name ASC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [row["model_name"] for row in rows]

    def search_catalog(
        self,
        year_min: int,
        year_max: int,
        makes: Optional[Iterable[str]] = None,
        q: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = [year_min, year_max]
        sql = (
            "SELECT year, make_name, model_name, vehicle_type, source "
            "FROM v_catalog WHERE year BETWEEN ? AND ?"
        )
        make_list = list(makes or [])
        if make_list:
            placeholders = ",".join(["?"] * len(make_list))
            sql += f" AND make_name IN ({placeholders})"
            params.extend(make_list)
        if q:
            sql += " AND (make_name LIKE ? COLLATE NOCASE OR model_name LIKE ? COLLATE NOCASE)"
            params.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY year DESC, make_name ASC, model_name ASC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            entry_id = f"{row['year']}-{row['make_name']}-{row['model_name']}"
            results.append(
                {
                    "id": entry_id,
                    "year": row["year"],
                    "make": row["make_name"],
                    "model": row["model_name"],
                    "vehicleType": row["vehicle_type"],
                    "source": row["source"],
                    "images": [],
                }
            )
        return results

    def export_catalog_json(self, output_path: str) -> int:
        rows = self.conn.execute(
            """
            SELECT year, make_name, model_name, vehicle_type, source
            FROM v_catalog
            ORDER BY year DESC, make_name ASC, model_name ASC
            """
        ).fetchall()
        records: List[Dict[str, Any]] = []
        for row in rows:
            entry_id = f"{row['year']}-{row['make_name']}-{row['model_name']}"
            records.append(
                {
                    "id": entry_id,
                    "year": row["year"],
                    "make": row["make_name"],
                    "model": row["model_name"],
                    "vehicleType": row["vehicle_type"],
                    "source": row["source"],
                    "images": [],
                }
            )
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2)
        return len(records)

    def counts(self) -> Dict[str, int]:
        make_count = self.conn.execute("SELECT COUNT(*) FROM makes").fetchone()[0]
        model_count = self.conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        year_count = self.conn.execute("SELECT COUNT(*) FROM model_years").fetchone()[0]
        return {
            "makes": int(make_count),
            "models": int(model_count),
            "model_years": int(year_count),
        }

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
                body_style TEXT NULL,
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
            """
        )
        self._ensure_body_style_column()
        self._refresh_catalog_view()
        self.conn.commit()

    def _ensure_body_style_column(self) -> None:
        columns = self.conn.execute("PRAGMA table_info(model_years)").fetchall()
        column_names = {row["name"] for row in columns}
        if "body_style" not in column_names:
            self.conn.execute("ALTER TABLE model_years ADD COLUMN body_style TEXT NULL")

    def _refresh_catalog_view(self) -> None:
        self.conn.execute("DROP VIEW IF EXISTS v_catalog")
        self.conn.execute(
            """
            CREATE VIEW v_catalog AS
            SELECT
                model_years.year AS year,
                makes.make_name AS make_name,
                models.model_name AS model_name,
                model_years.vehicle_type AS vehicle_type,
                model_years.body_style AS body_style,
                model_years.source AS source
            FROM model_years
            JOIN models ON models.model_id = model_years.model_id
            JOIN makes ON makes.make_id = models.make_id;
            """
        )

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
        body_style: Optional[str],
        source: str = "NHTSA_vPIC",
        created_at: Optional[str] = None,
    ) -> None:
        created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT OR IGNORE INTO model_years
                (model_id, year, vehicle_type, body_style, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (model_id, year, vehicle_type, body_style, source, created_at),
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
        if body_style:
            self.conn.execute(
                """
                UPDATE model_years
                SET body_style = ?
                WHERE model_id = ? AND year = ?
                  AND (body_style IS NULL OR body_style = '')
                """,
                (body_style, model_id, year),
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
            "SELECT year, make_name, model_name, vehicle_type, body_style, source "
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
                    "bodyStyle": row["body_style"],
                    "source": row["source"],
                    "images": [],
                }
            )
        return results

    def export_catalog_json(self, output_path: str) -> int:
        rows = self.conn.execute(
            """
            SELECT year, make_name, model_name, vehicle_type, body_style, source
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
                    "bodyStyle": row["body_style"],
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


class BibleCatalogDB:
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
            CREATE TABLE IF NOT EXISTS listings (
                listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn13 TEXT UNIQUE,
                isbn10 TEXT,
                title TEXT NOT NULL,
                subtitle TEXT,
                translation TEXT,
                translation_raw TEXT,
                language TEXT,
                publisher TEXT,
                publish_date TEXT,
                page_count INTEGER,
                format TEXT,
                dimensions TEXT,
                cover_color TEXT,
                source TEXT NOT NULL,
                source_key TEXT NOT NULL,
                source_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS features (
                listing_id INTEGER PRIMARY KEY,
                red_letter INTEGER,
                study_bible INTEGER,
                commentary_notes INTEGER,
                cross_references INTEGER,
                concordance INTEGER,
                maps INTEGER,
                ribbon_markers_count INTEGER,
                thumb_indexed INTEGER,
                gilded_edges INTEGER,
                journaling INTEGER,
                single_column INTEGER,
                two_column INTEGER,
                devotionals INTEGER,
                reading_plan INTEGER,
                print_size TEXT,
                font_size REAL,
                feature_evidence TEXT,
                FOREIGN KEY(listing_id) REFERENCES listings(listing_id)
            );

            CREATE TABLE IF NOT EXISTS translations (
                translation_code TEXT PRIMARY KEY,
                display_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS progress (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_listings_title ON listings(title);
            CREATE INDEX IF NOT EXISTS idx_listings_translation ON listings(translation);
            CREATE INDEX IF NOT EXISTS idx_listings_publisher ON listings(publisher);
            CREATE INDEX IF NOT EXISTS idx_listings_publish_date ON listings(publish_date);
            """
        )
        self._ensure_column("listings", "translation_raw", "TEXT")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, column_type: str) -> None:
        columns = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        column_names = {row["name"] for row in columns}
        if column not in column_names:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def set_progress(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO progress (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_progress(self, key: str) -> Optional[str]:
        row = self.conn.execute("SELECT value FROM progress WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def ensure_translations(self, translations: Dict[str, str]) -> None:
        for code, display_name in translations.items():
            self.conn.execute(
                "INSERT OR REPLACE INTO translations (translation_code, display_name) VALUES (?, ?)",
                (code, display_name),
            )

    def list_translations(self) -> List[Dict[str, str]]:
        rows = self.conn.execute(
            "SELECT translation_code, display_name FROM translations ORDER BY translation_code"
        ).fetchall()
        return [
            {"translation_code": row["translation_code"], "display_name": row["display_name"]}
            for row in rows
        ]

    def get_listing_id(self, isbn13: Optional[str], isbn10: Optional[str]) -> Optional[int]:
        if isbn13:
            row = self.conn.execute(
                "SELECT listing_id FROM listings WHERE isbn13 = ?", (isbn13,)
            ).fetchone()
            if row:
                return int(row["listing_id"])
        if isbn10:
            row = self.conn.execute(
                "SELECT listing_id FROM listings WHERE isbn10 = ?", (isbn10,)
            ).fetchone()
            if row:
                return int(row["listing_id"])
        return None

    def listing_exists(self, isbn13: Optional[str], isbn10: Optional[str]) -> bool:
        return self.get_listing_id(isbn13, isbn10) is not None

    def upsert_listing(self, listing: Dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        isbn13 = listing.get("isbn13")
        isbn10 = listing.get("isbn10")
        existing_id = self.get_listing_id(isbn13, isbn10)

        if existing_id is None:
            fields = [
                "isbn13",
                "isbn10",
                "title",
                "subtitle",
                "translation",
                "translation_raw",
                "language",
                "publisher",
                "publish_date",
                "page_count",
                "format",
                "dimensions",
                "cover_color",
                "source",
                "source_key",
                "source_url",
                "created_at",
                "updated_at",
            ]
            values = [listing.get(field) for field in fields[:-2]] + [now, now]
            placeholders = ", ".join(["?"] * len(fields))
            cursor = self.conn.execute(
                f"INSERT INTO listings ({', '.join(fields)}) VALUES ({placeholders})",
                values,
            )
            return int(cursor.lastrowid or 0)

        updates = []
        params: List[Any] = []
        for field, value in listing.items():
            if field in ("listing_id", "created_at"):
                continue
            if value is not None and value != "":
                updates.append(f"{field} = ?")
                params.append(value)
        updates.append("updated_at = ?")
        params.append(now)
        params.append(existing_id)
        self.conn.execute(
            f"UPDATE listings SET {', '.join(updates)} WHERE listing_id = ?",
            params,
        )
        return existing_id

    def upsert_features(self, listing_id: int, features: Dict[str, Any]) -> None:
        fields = [
            "listing_id",
            "red_letter",
            "study_bible",
            "commentary_notes",
            "cross_references",
            "concordance",
            "maps",
            "ribbon_markers_count",
            "thumb_indexed",
            "gilded_edges",
            "journaling",
            "single_column",
            "two_column",
            "devotionals",
            "reading_plan",
            "print_size",
            "font_size",
            "feature_evidence",
        ]
        values = [listing_id] + [features.get(field) for field in fields[1:]]
        placeholders = ", ".join(["?"] * len(fields))
        updates = ", ".join([f"{field} = excluded.{field}" for field in fields[1:]])
        self.conn.execute(
            f"""
            INSERT INTO features ({', '.join(fields)}) VALUES ({placeholders})
            ON CONFLICT(listing_id) DO UPDATE SET {updates}
            """,
            values,
        )

    def export_catalog_json(self, output_path: str) -> int:
        rows = self.conn.execute(
            """
            SELECT
                listings.isbn13,
                listings.title,
                listings.translation,
                listings.publisher,
                listings.format,
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
        ).fetchall()
        records: List[Dict[str, Any]] = []
        for row in rows:
            records.append(
                {
                    "isbn13": row["isbn13"],
                    "title": row["title"],
                    "translation": row["translation"],
                    "publisher": row["publisher"],
                    "format": row["format"],
                    "features": {
                        "red_letter": row["red_letter"],
                        "study_bible": row["study_bible"],
                        "commentary_notes": row["commentary_notes"],
                        "cross_references": row["cross_references"],
                        "concordance": row["concordance"],
                        "maps": row["maps"],
                        "ribbon_markers_count": row["ribbon_markers_count"],
                        "thumb_indexed": row["thumb_indexed"],
                        "gilded_edges": row["gilded_edges"],
                        "journaling": row["journaling"],
                        "single_column": row["single_column"],
                        "two_column": row["two_column"],
                        "devotionals": row["devotionals"],
                        "reading_plan": row["reading_plan"],
                        "print_size": row["print_size"],
                        "font_size": row["font_size"],
                    },
                    "source_url": row["source_url"],
                }
            )
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2)
        return len(records)

    def search_listings(
        self,
        translation: Optional[List[str]] = None,
        publisher: Optional[str] = None,
        fmt: Optional[str] = None,
        print_size: Optional[str] = None,
        study_bible: Optional[int] = None,
        journaling: Optional[int] = None,
        red_letter: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        params: List[Any] = []
        sql = (
            "SELECT listings.*, features.* FROM listings "
            "LEFT JOIN features ON features.listing_id = listings.listing_id"
        )
        clauses = []
        if translation:
            placeholders = ", ".join(["?"] * len(translation))
            clauses.append(f"listings.translation IN ({placeholders})")
            params.extend(translation)
        if publisher:
            clauses.append("listings.publisher LIKE ?")
            params.append(f"%{publisher}%")
        if fmt:
            clauses.append("listings.format = ?")
            params.append(fmt)
        if print_size:
            clauses.append("features.print_size = ?")
            params.append(print_size)
        if study_bible is not None:
            clauses.append("features.study_bible = ?")
            params.append(study_bible)
        if journaling is not None:
            clauses.append("features.journaling = ?")
            params.append(journaling)
        if red_letter is not None:
            clauses.append("features.red_letter = ?")
            params.append(red_letter)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY listings.title ASC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "isbn13": row["isbn13"],
                    "isbn10": row["isbn10"],
                    "title": row["title"],
                    "subtitle": row["subtitle"],
                    "translation": row["translation"],
                    "language": row["language"],
                    "publisher": row["publisher"],
                    "publish_date": row["publish_date"],
                    "page_count": row["page_count"],
                    "format": row["format"],
                    "dimensions": row["dimensions"],
                    "cover_color": row["cover_color"],
                    "source_url": row["source_url"],
                    "features": {
                        "red_letter": row["red_letter"],
                        "study_bible": row["study_bible"],
                        "commentary_notes": row["commentary_notes"],
                        "cross_references": row["cross_references"],
                        "concordance": row["concordance"],
                        "maps": row["maps"],
                        "ribbon_markers_count": row["ribbon_markers_count"],
                        "thumb_indexed": row["thumb_indexed"],
                        "gilded_edges": row["gilded_edges"],
                        "journaling": row["journaling"],
                        "single_column": row["single_column"],
                        "two_column": row["two_column"],
                        "devotionals": row["devotionals"],
                        "reading_plan": row["reading_plan"],
                        "print_size": row["print_size"],
                        "font_size": row["font_size"],
                    },
                }
            )
        return results

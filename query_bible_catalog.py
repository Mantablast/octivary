import argparse
import json
from typing import List, Optional

from catalog_db import BibleCatalogDB


def parse_bool_flag(args: argparse.Namespace, flag: str) -> Optional[int]:
    return 1 if getattr(args, flag) else None


def list_translations(db: BibleCatalogDB) -> None:
    translations = db.list_translations()
    print(json.dumps(translations, indent=2))


def search(db: BibleCatalogDB, args: argparse.Namespace) -> None:
    translations: Optional[List[str]] = None
    if args.translation:
        translations = [code.strip().upper() for code in args.translation.split(",") if code.strip()]

    results = db.search_listings(
        translation=translations,
        publisher=args.publisher,
        fmt=args.format,
        print_size=args.print_size,
        study_bible=parse_bool_flag(args, "study_bible"),
        journaling=parse_bool_flag(args, "journaling"),
        red_letter=parse_bool_flag(args, "red_letter"),
        limit=args.limit,
    )
    print(json.dumps(results, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the Bible catalog database.")
    parser.add_argument("--db", default="bible_catalog.db", help="SQLite database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list_translations", help="List translation codes")
    list_parser.set_defaults(func=list_translations)

    search_parser = subparsers.add_parser("search", help="Search listings with filters")
    search_parser.add_argument("--translation", help="Comma-separated translation codes")
    search_parser.add_argument("--publisher", help="Publisher name contains")
    search_parser.add_argument("--format", help="Format (hardcover, leather, etc)")
    search_parser.add_argument("--print-size", dest="print_size", help="Print size (large, giant)")
    search_parser.add_argument("--study-bible", action="store_true")
    search_parser.add_argument("--journaling", action="store_true")
    search_parser.add_argument("--red-letter", dest="red_letter", action="store_true")
    search_parser.add_argument("--limit", type=int, default=50)
    search_parser.set_defaults(func=search)

    args = parser.parse_args()
    db = BibleCatalogDB(args.db)
    try:
        args.func(db, args) if args.command == "search" else args.func(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

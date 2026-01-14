import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from catalog_db import CatalogDB
from vpic_client import VpicClient


def compute_years(current_year: int, span_years: int) -> List[int]:
    start_year = current_year - (span_years - 1)
    return list(range(current_year, start_year - 1, -1))


def infer_body_style(model_name: str, vehicle_type: str | None) -> str | None:
    if not model_name:
        return None
    name = model_name.lower()
    if vehicle_type and "motorcycle" in vehicle_type.lower():
        return None
    checks = [
        ("Pickup truck", ["pickup", "pick-up"]),
        ("SUV", ["suv", "sport utility"]),
        ("Crossover", ["crossover", "cuv"]),
        ("Station wagon", ["wagon", "estate"]),
        ("Hatchback", ["hatchback"]),
        ("Convertible", ["convertible", "cabriolet", "roadster", "spyder", "spider"]),
        ("Coupe", ["coupe"]),
        ("Sedan", ["sedan", "saloon"]),
    ]
    for label, keywords in checks:
        if any(keyword in name for keyword in keywords):
            return label
    return None


def append_run_log(message: str) -> None:
    log_path = Path("run_log.txt")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a vehicle catalog using NHTSA vPIC.")
    parser.add_argument("--db", default="vehicles_catalog.db", help="SQLite DB path")
    parser.add_argument("--years", type=int, default=20, help="Number of years to include (inclusive)")
    parser.add_argument("--export-json", default=None, help="Optional JSON export path")
    parser.add_argument("--max-zero-streak", type=int, default=10, help="Zero-model streak before skipping")
    parser.add_argument("--throttle", type=float, default=0.2, help="Seconds to sleep between calls")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout seconds")
    parser.add_argument("--max-retries", type=int, default=5, help="Max retries for 429/5xx")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    append_run_log(f"START {started_at.isoformat()} db={args.db} years={args.years}")

    client = VpicClient(
        timeout=args.timeout,
        max_retries=args.max_retries,
        throttle_seconds=args.throttle,
    )
    db = CatalogDB(args.db)

    try:
        makes = client.get_makes()
        for make_name in makes:
            db.ensure_make(make_name)
        db.conn.commit()

        make_cache: Dict[str, int] = {}
        rows = db.conn.execute("SELECT make_id, make_name FROM makes").fetchall()
        for row in rows:
            make_cache[row["make_name"]] = int(row["make_id"])

        model_cache: Dict[str, Dict[str, int]] = {}
        zero_streak: Dict[str, int] = {}
        skipped_makes = set()

        now_year = datetime.now(timezone.utc).year
        years = compute_years(now_year, args.years)
        total_years = len(years)
        total_makes = len(makes)

        for year_idx, year in enumerate(years, start=1):
            if db.is_year_completed(year):
                continue

            for make_idx, make_name in enumerate(makes, start=1):
                if make_name in skipped_makes:
                    continue

                make_id = make_cache.get(make_name)
                if not make_id:
                    make_id = db.ensure_make(make_name)
                    make_cache[make_name] = make_id

                models = client.get_models_for_make_year(make_name, year)
                model_count = len(models)
                print(
                    f"Year {year} ({year_idx}/{total_years}): "
                    f"Make {make_name} ({make_idx}/{total_makes}): {model_count} models"
                )

                if model_count == 0:
                    zero_streak[make_name] = zero_streak.get(make_name, 0) + 1
                    if zero_streak[make_name] >= args.max_zero_streak:
                        skipped_makes.add(make_name)
                        print(f"Skipping {make_name}: zero streak {zero_streak[make_name]}")
                    continue

                zero_streak[make_name] = 0
                if make_id not in model_cache:
                    model_cache[make_id] = {}

                for model in models:
                    model_name = model.get("model_name")
                    if not model_name:
                        continue
                    vehicle_type = model.get("vehicle_type")
                    body_style = infer_body_style(model_name, vehicle_type)
                    cached = model_cache[make_id].get(model_name)
                    if cached:
                        model_id = cached
                    else:
                        model_id = db.ensure_model(make_id, model_name)
                        model_cache[make_id][model_name] = model_id
                    db.insert_model_year(
                        model_id=model_id,
                        year=year,
                        vehicle_type=vehicle_type,
                        body_style=body_style,
                    )

            db.set_progress(f"completed_year_{year}", "true")
            db.conn.commit()

        db.set_progress("last_run_iso", datetime.now(timezone.utc).isoformat())
        db.conn.commit()

        counts = db.counts()
        print(
            f"Counts: makes={counts['makes']}, models={counts['models']}, "
            f"model_years={counts['model_years']}"
        )

        if args.export_json:
            output_path = Path(args.export_json)
            exported = db.export_catalog_json(str(output_path))
            print(f"Exported {exported} records to {output_path}")

    finally:
        client.close()
        db.close()
        finished_at = datetime.now(timezone.utc)
        append_run_log(f"END {finished_at.isoformat()} db={args.db}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from app.data.catalog_loader import load_catalog_from_path
from app.data.catalog_sync import CatalogSyncResult, sync_catalog_snapshot
from app.data.database import bootstrap_database


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the Postgres schema and sync curated seed data."
    )
    parser.add_argument(
        "--database-url",
        help="Explicit Postgres database URL. Defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--catalog-path",
        type=Path,
        help="Validate and sync an explicit normalized catalog JSON file.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _format_sync_result(result: CatalogSyncResult) -> str:
    return (
        "catalog sync complete: "
        f"ski_regions={result.ski_regions} "
        f"stay_destinations={result.stay_destinations} "
        f"stay_bases={result.stay_bases} "
        f"ski_areas={result.ski_areas} "
        f"ski_area_access={result.ski_area_access} "
        f"terrain_domains={result.terrain_domains} "
        f"lift_pass_products={result.lift_pass_products} "
        f"rental_display_facts={result.rental_display_facts} "
        f"relationships={result.relationships}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.catalog_path is None:
        bootstrap_database(args.database_url)
        return 0

    try:
        snapshot = load_catalog_from_path(args.catalog_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
        print(f"catalog validation failed: {error}", file=sys.stderr)
        return 2

    result = sync_catalog_snapshot(snapshot, args.database_url)
    print(_format_sync_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

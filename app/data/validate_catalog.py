from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the normalized Snowcast catalog JSON file."
    )
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=CATALOG_PATH,
        help=f"Catalog JSON path (default: {CATALOG_PATH}).",
    )
    return parser.parse_args(argv)


def _validation_error_summary(error: ValidationError) -> str:
    issues = error.errors(include_url=False)
    first_issue = issues[0]
    location = ".".join(str(part) for part in first_issue.get("loc", ()))
    message = str(first_issue.get("msg", "catalog validation failed"))
    first_summary = f"{location}: {message}" if location else message
    remaining_count = len(issues) - 1
    if remaining_count:
        return f"{first_summary} (+{remaining_count} more errors)"
    return first_summary


def _print_invalid(message: str) -> None:
    print(f"[catalog-invalid] {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        catalog = load_catalog_from_path(args.catalog_path)
    except json.JSONDecodeError as error:
        _print_invalid(
            f"invalid JSON in {args.catalog_path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        )
        return 1
    except OSError as error:
        _print_invalid(f"cannot read {args.catalog_path}: {error}")
        return 1
    except ValidationError as error:
        _print_invalid(
            f"catalog validation failed for {args.catalog_path}: "
            f"{_validation_error_summary(error)}"
        )
        return 1

    print(
        "[catalog-valid] "
        f"schema_version={catalog.schema_version} "
        f"ski_regions={len(catalog.ski_regions)} "
        f"stay_destinations={len(catalog.stay_destinations)} "
        f"stay_bases={len(catalog.stay_bases)} "
        f"ski_areas={len(catalog.ski_areas)} "
        f"access_links={len(catalog.ski_area_access)} "
        f"terrain_domains={len(catalog.terrain_domains)} "
        f"lift_pass_products={len(catalog.lift_pass_products)} "
        f"rental_display_facts={len(catalog.rental_display_facts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

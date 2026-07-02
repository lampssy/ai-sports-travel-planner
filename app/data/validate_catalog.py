from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.data.catalog_policy import catalog_policy_issues
from app.domain.catalog_trust import CatalogTrustManifest


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
    parser.add_argument(
        "--trust-manifest-path",
        type=Path,
        help="Optional normalized trust-manifest JSON path.",
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


def _load_trust_manifest_from_path(path: Path) -> CatalogTrustManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CatalogTrustManifest.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        catalog = load_catalog_from_path(args.catalog_path)
    except UnicodeDecodeError as error:
        _print_invalid(
            f"invalid UTF-8 in {args.catalog_path}: byte {error.start}: {error.reason}"
        )
        return 1
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

    trust_manifest = None
    policy_errors = [
        issue.message
        for issue in catalog_policy_issues(catalog)
        if issue.severity == "error"
    ]
    if policy_errors:
        _print_invalid("catalog policy failed: " + "; ".join(policy_errors))
        return 1

    if args.trust_manifest_path is not None:
        try:
            trust_manifest = _load_trust_manifest_from_path(args.trust_manifest_path)
        except UnicodeDecodeError as error:
            _print_invalid(
                f"invalid UTF-8 in {args.trust_manifest_path}: "
                f"byte {error.start}: {error.reason}"
            )
            return 1
        except json.JSONDecodeError as error:
            _print_invalid(
                f"invalid JSON in {args.trust_manifest_path}: "
                f"line {error.lineno}, column {error.colno}: {error.msg}"
            )
            return 1
        except OSError as error:
            _print_invalid(f"cannot read {args.trust_manifest_path}: {error}")
            return 1
        except ValidationError as error:
            _print_invalid(
                f"trust manifest validation failed for "
                f"{args.trust_manifest_path}: {_validation_error_summary(error)}"
            )
            return 1

        try:
            trust_manifest.validate_against_catalog(catalog)
        except ValueError as error:
            _print_invalid(
                f"trust manifest graph validation failed for "
                f"{args.trust_manifest_path}: {error}"
            )
            return 1

    summary = (
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
    if trust_manifest is not None:
        trust_entry_count = sum(
            len(entries) for entries in trust_manifest.entities.values()
        )
        summary += (
            f" trust_manifest_version={trust_manifest.version} "
            f"trust_entries={trust_entry_count}"
        )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

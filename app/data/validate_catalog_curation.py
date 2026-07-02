from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from app.data.catalog_curation import (
    CatalogValidationError,
    load_catalog_curation_report,
    render_catalog_curation_report_markdown,
    validate_catalog_curation_report,
)
from app.data.catalog_curation_reconciliation import (
    reconcile_catalog_curation_report,
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a normalized Snowcast catalog curation report."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    typed_parser = subparsers.add_parser("typed", help="Validate the report only.")
    typed_parser.add_argument("report_path", type=Path)
    typed_parser.add_argument("--markdown-output", type=Path)

    reconcile_parser = subparsers.add_parser(
        "reconcile",
        help="Validate and reconcile the report against normalized snapshots.",
    )
    reconcile_parser.add_argument("report_path", type=Path)
    reconcile_parser.add_argument("--base-catalog-path", type=Path, required=True)
    reconcile_parser.add_argument("--current-catalog-path", type=Path, required=True)
    reconcile_parser.add_argument(
        "--base-trust-manifest-path",
        type=Path,
        required=True,
    )
    reconcile_parser.add_argument(
        "--current-trust-manifest-path",
        type=Path,
        required=True,
    )
    reconcile_parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def _pydantic_issue_messages(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for issue in error.errors(include_url=False):
        location = ".".join(str(part) for part in issue.get("loc", ()))
        message = str(issue.get("msg", issue))
        messages.append(f"{location}: {message}" if location else message)
    return messages


def _print_invalid(issues: Sequence[str]) -> None:
    for issue in issues:
        print(f"[catalog-curation-invalid] {issue}")


def _write_markdown_report(report_path: Path, output_path: Path) -> None:
    report = load_catalog_curation_report(report_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_catalog_curation_report_markdown(report),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = load_catalog_curation_report(args.report_path)
        validate_catalog_curation_report(report)
        reconciliation_result = None
        if args.command == "reconcile":
            reconciliation_result = reconcile_catalog_curation_report(
                report,
                base_catalog_path=args.base_catalog_path,
                current_catalog_path=args.current_catalog_path,
                base_trust_manifest_path=args.base_trust_manifest_path,
                current_trust_manifest_path=args.current_trust_manifest_path,
            )
        if args.markdown_output is not None:
            _write_markdown_report(args.report_path, args.markdown_output)
    except ValidationError as error:
        _print_invalid(_pydantic_issue_messages(error))
        return 1
    except CatalogValidationError as error:
        _print_invalid(error.issues)
        return 1

    summary = (
        f"[catalog-curation-valid] mode={args.command} "
        f"changes={len(report.changes)} coverage={len(report.field_coverage)} "
        f"evidence={len(report.evidence)}"
    )
    if reconciliation_result is not None:
        summary += f" reconciled_deltas={reconciliation_result.delta_count}"
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

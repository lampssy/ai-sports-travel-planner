from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from app.data.catalog_curation import (
    CURRENT_CATALOG_CURATION_REPORT_SCHEMA_VERSION,
    CatalogCurationReport,
    CatalogValidationError,
    load_catalog_curation_report,
    render_catalog_curation_report_markdown,
    validate_catalog_curation_report,
    validate_catalog_resulting_graph,
)
from app.data.catalog_curation_backlog import (
    validate_catalog_curation_backlog_refs,
)
from app.data.catalog_curation_reconciliation import (
    reconcile_catalog_curation_report,
)
from app.data.catalog_loader import load_catalog_from_path
from app.domain.catalog import CatalogSnapshot


def _add_report_schema_version_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--require-report-schema-version",
        type=int,
        choices=tuple(range(1, CURRENT_CATALOG_CURATION_REPORT_SCHEMA_VERSION + 1)),
        help="Reject reports older than this curation-report schema version.",
    )


def _add_product_backlog_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--product-backlog-path",
        type=Path,
        help=(
            "Validate deferred entity-scope references against the catalog "
            "curation backlog."
        ),
    )


def _add_markdown_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--require-markdown-path",
        type=Path,
        help=(
            "Require an existing Markdown companion to exactly match the "
            "canonical rendered report."
        ),
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a normalized Snowcast catalog curation report."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    typed_parser = subparsers.add_parser("typed", help="Validate the report only.")
    typed_parser.add_argument("report_path", type=Path)
    _add_markdown_arguments(typed_parser)
    typed_parser.add_argument(
        "--current-catalog-path",
        type=Path,
        help="Current normalized catalog used to derive the resulting graph.",
    )
    _add_report_schema_version_argument(typed_parser)
    _add_product_backlog_argument(typed_parser)

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
    _add_markdown_arguments(reconcile_parser)
    _add_report_schema_version_argument(reconcile_parser)
    _add_product_backlog_argument(reconcile_parser)
    reconcile_parser.add_argument(
        "--skip-product-backlog-validation",
        action="store_true",
        help=(
            "Skip backlog anchor validation for the maintainer's separately "
            "reviewed free-form backlog prose."
        ),
    )
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


def _write_markdown_report(
    report: CatalogCurationReport,
    output_path: Path,
    catalog: CatalogSnapshot | None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_catalog_curation_report_markdown(report, catalog),
        encoding="utf-8",
    )


def _validate_markdown_report(
    report: CatalogCurationReport,
    markdown_path: Path,
    catalog: CatalogSnapshot | None,
) -> None:
    expected = render_catalog_curation_report_markdown(report, catalog)
    try:
        actual = markdown_path.read_text(encoding="utf-8")
    except OSError as error:
        raise CatalogValidationError(
            ["rendered Markdown companion could not be read"]
        ) from error
    if actual != expected:
        raise CatalogValidationError(
            ["rendered Markdown does not match canonical report"]
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = load_catalog_curation_report(args.report_path)
        if (
            args.require_report_schema_version is not None
            and report.report_schema_version < args.require_report_schema_version
        ):
            raise CatalogValidationError(
                [
                    f"report schema version {report.report_schema_version} is below "
                    f"required version {args.require_report_schema_version}"
                ]
            )
        require_resulting_graph = (
            args.require_report_schema_version is not None
            and args.require_report_schema_version >= 3
        )
        validate_catalog_curation_report(
            report,
            require_resulting_graph=require_resulting_graph,
            require_current_destination_policy=require_resulting_graph,
        )
        if not getattr(args, "skip_product_backlog_validation", False):
            validate_catalog_curation_backlog_refs(report, args.product_backlog_path)
        reconciliation_result = None
        current_catalog = None
        if args.command == "reconcile":
            current_catalog = load_catalog_from_path(args.current_catalog_path)
            validate_catalog_resulting_graph(
                report,
                current_catalog,
                require=require_resulting_graph,
            )
            reconciliation_result = reconcile_catalog_curation_report(
                report,
                base_catalog_path=args.base_catalog_path,
                current_catalog_path=args.current_catalog_path,
                base_trust_manifest_path=args.base_trust_manifest_path,
                current_trust_manifest_path=args.current_trust_manifest_path,
            )
        elif args.current_catalog_path is not None:
            current_catalog = load_catalog_from_path(args.current_catalog_path)
            validate_catalog_resulting_graph(
                report,
                current_catalog,
                require=require_resulting_graph,
            )
        if args.require_markdown_path is not None:
            _validate_markdown_report(
                report,
                args.require_markdown_path,
                current_catalog,
            )
        if args.markdown_output is not None:
            _write_markdown_report(report, args.markdown_output, current_catalog)
    except ValidationError as error:
        _print_invalid(_pydantic_issue_messages(error))
        return 1
    except CatalogValidationError as error:
        _print_invalid(error.issues)
        return 1

    summary = (
        f"[catalog-curation-valid] mode={args.command} "
        f"report_schema_version={report.report_schema_version} "
        f"changes={len(report.changes)} coverage={len(report.field_coverage)} "
        f"evidence={len(report.evidence)}"
    )
    backlog_ref_count = sum(
        assessment.backlog_ref is not None
        for assessment in report.entity_scope_assessments
    )
    summary += f" backlog_refs={backlog_ref_count}"
    if reconciliation_result is not None:
        summary += f" reconciled_deltas={reconciliation_result.delta_count}"
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from app.data.catalog_curation import (
    CatalogCurationReport,
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
        description="Validate a Snowcast catalog curation report JSON file."
    )
    parser.add_argument(
        "--report-path",
        required=True,
        type=Path,
        help="Path to the catalog curation report JSON file.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for the rendered Markdown curation report.",
    )
    parser.add_argument(
        "--validation-mode",
        choices=("typed-only", "reconcile"),
        default="typed-only",
        help="Validate only the typed report or reconcile it against snapshots.",
    )
    parser.add_argument("--base-resorts-path", type=Path)
    parser.add_argument("--current-resorts-path", type=Path)
    parser.add_argument("--base-terrain-domains-path", type=Path)
    parser.add_argument("--current-terrain-domains-path", type=Path)
    parser.add_argument("--base-trust-manifest-path", type=Path)
    parser.add_argument("--current-trust-manifest-path", type=Path)
    parser.add_argument(
        "--required-boundary-target",
        action="append",
        default=[],
        help="Destination id requiring a complete passing boundary assessment.",
    )
    parser.add_argument(
        "--required-weather-geometry-target",
        action="append",
        default=[],
        help="Ski-area id requiring exact before/after weather geometry.",
    )
    return parser.parse_args(argv)


def _pydantic_issue_messages(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue.get("loc", ()))
        message = str(issue.get("msg", issue))
        if location:
            messages.append(f"{location}: {message}")
        else:
            messages.append(message)
    return messages


def _print_invalid(issues: Sequence[str]) -> None:
    for issue in issues:
        print(f"[catalog-curation-invalid] {issue}")


def _write_markdown_report(report: CatalogCurationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _render_with_preserved_appendix(report, output_path),
        encoding="utf-8",
    )


def _render_with_preserved_appendix(
    report: CatalogCurationReport,
    output_path: Path,
) -> str:
    rendered = render_catalog_curation_report_markdown(report).rstrip()
    appendix = _existing_field_coverage_appendix(output_path)
    if appendix:
        return f"{rendered}\n{appendix}"
    return f"{rendered}\n"


def _existing_field_coverage_appendix(output_path: Path) -> str:
    marker = "\n## Field Coverage Matrix\n"
    try:
        existing = output_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if marker not in existing:
        return ""
    return marker.lstrip("\n") + existing.split(marker, maxsplit=1)[1]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        report = load_catalog_curation_report(args.report_path)
        validate_catalog_curation_report(report)
        reconciliation_result = None
        if args.validation_mode == "reconcile":
            snapshot_options = {
                "--base-resorts-path": args.base_resorts_path,
                "--current-resorts-path": args.current_resorts_path,
                "--base-terrain-domains-path": args.base_terrain_domains_path,
                "--current-terrain-domains-path": args.current_terrain_domains_path,
                "--base-trust-manifest-path": args.base_trust_manifest_path,
                "--current-trust-manifest-path": args.current_trust_manifest_path,
            }
            missing_options = [
                option for option, value in snapshot_options.items() if value is None
            ]
            if missing_options:
                raise CatalogValidationError(
                    ["reconcile validation requires: " + " ".join(missing_options)]
                )
            reconciliation_result = reconcile_catalog_curation_report(
                report,
                base_resorts_path=args.base_resorts_path,
                current_resorts_path=args.current_resorts_path,
                base_terrain_domains_path=args.base_terrain_domains_path,
                current_terrain_domains_path=args.current_terrain_domains_path,
                base_trust_manifest_path=args.base_trust_manifest_path,
                current_trust_manifest_path=args.current_trust_manifest_path,
                required_boundary_targets=args.required_boundary_target,
                required_weather_geometry_targets=(
                    args.required_weather_geometry_target
                ),
            )
    except CatalogValidationError as error:
        _print_invalid(error.issues)
        return 1
    except ValidationError as error:
        _print_invalid(_pydantic_issue_messages(error))
        return 1

    if args.markdown_output:
        try:
            _write_markdown_report(report, args.markdown_output)
        except OSError as error:
            _print_invalid(
                [f"failed to write markdown report to {args.markdown_output}: {error}"]
            )
            return 1

    print(
        "[catalog-curation-valid] "
        f"mode={args.validation_mode} "
        f"changes={len(report.changes)} "
        f"field_coverage={len(report.field_coverage)} "
        f"evidence={len(report.evidence)}"
        + (
            ""
            if reconciliation_result is None
            else f" snapshot_deltas={reconciliation_result.delta_count}"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

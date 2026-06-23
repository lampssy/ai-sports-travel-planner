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
        render_catalog_curation_report_markdown(report), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        report = load_catalog_curation_report(args.report_path)
        validate_catalog_curation_report(report)
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
        f"changes={len(report.changes)} evidence={len(report.evidence)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.data.catalog_curation import (
    CATALOG_BACKLOG_REF_PREFIX,
    CatalogCurationReport,
    CatalogValidationError,
)

CATALOG_CURATION_SECTION = "Catalog Curation Refinements"


def markdown_heading_anchor(heading: str) -> str:
    decomposed = unicodedata.normalize("NFKD", heading)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "-", without_marks.lower()).strip("-")


def _catalog_curation_items(markdown: str) -> tuple[dict[str, str], set[str]]:
    items: dict[str, list[str]] = {}
    duplicate_anchors: set[str] = set()
    in_section = False
    current_anchor: str | None = None

    for line in markdown.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            in_section = line.removeprefix("## ").strip() == CATALOG_CURATION_SECTION
            current_anchor = None
            continue
        if not in_section:
            continue
        if line.startswith("### "):
            current_anchor = markdown_heading_anchor(line.removeprefix("### ").strip())
            if current_anchor in items:
                duplicate_anchors.add(current_anchor)
            else:
                items[current_anchor] = []
            continue
        if current_anchor is not None:
            items[current_anchor].append(line)

    return (
        {anchor: "\n".join(lines) for anchor, lines in items.items()},
        duplicate_anchors,
    )


def validate_catalog_curation_backlog_refs(
    report: CatalogCurationReport,
    backlog_path: Path | None,
) -> None:
    assessments = [
        assessment
        for assessment in report.entity_scope_assessments
        if assessment.backlog_ref is not None
    ]
    if not assessments:
        return
    if backlog_path is None:
        raise CatalogValidationError(
            ["product backlog path is required when backlog_ref is present"]
        )
    try:
        markdown = backlog_path.read_text(encoding="utf-8")
    except OSError as error:
        raise CatalogValidationError(
            [f"Unable to read product backlog at {backlog_path}: {error}"]
        ) from error

    items, duplicate_anchors = _catalog_curation_items(markdown)
    issues = [
        f"duplicate backlog anchor in Catalog Curation Refinements: {anchor}"
        for anchor in sorted(duplicate_anchors)
    ]
    for assessment in assessments:
        backlog_ref = assessment.backlog_ref
        if backlog_ref is None:
            continue
        anchor = backlog_ref.removeprefix(CATALOG_BACKLOG_REF_PREFIX)
        item_body = items.get(anchor)
        if item_body is None:
            issues.append(
                f"{assessment.candidate_id}: unknown backlog reference {backlog_ref}"
            )
            continue
        candidate_marker = f"`{assessment.candidate_kind}:{assessment.candidate_id}`"
        if candidate_marker not in item_body:
            issues.append(
                f"{assessment.candidate_id}: backlog item {anchor} is missing "
                f"candidate marker {candidate_marker}"
            )
    if issues:
        raise CatalogValidationError(sorted(set(issues)))

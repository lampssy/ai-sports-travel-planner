from pathlib import Path

import pytest

from app.data.catalog_curation import (
    CatalogCurationReport,
    CatalogValidationError,
)
from app.data.catalog_curation_backlog import (
    markdown_heading_anchor,
    validate_catalog_curation_backlog_refs,
)

BACKLOG_REF = "docs/product-backlog.md#kitzski-catalog-extension"


def _deferred_report_with_candidates(
    *candidates: tuple[str, str],
) -> CatalogCurationReport:
    return CatalogCurationReport.model_validate(
        {
            "report_schema_version": 2,
            "title": "Deferred catalog candidates",
            "summary": "Tracks justified regional catalog extensions.",
            "reviewed_targets": [],
            "entity_scope_assessments": [
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_id.replace("-", " ").title(),
                    "candidate_kind": candidate_kind,
                    "disposition": "deferred",
                    "signals": ["official_independent_identity"],
                    "evidence_refs": [f"scope-{candidate_id}"],
                    "target_refs": [],
                    "rationale": "A wider regional recuration is required.",
                    "backlog_ref": BACKLOG_REF,
                }
                for candidate_kind, candidate_id in candidates
            ],
        }
    )


def _deferred_report() -> CatalogCurationReport:
    return _deferred_report_with_candidates(("ski_area", "horn"))


def _write_backlog(tmp_path: Path, item_markdown: str) -> Path:
    path = tmp_path / "product-backlog.md"
    path.write_text(
        f"# Product Backlog\n\n## Catalog Curation Refinements\n\n{item_markdown}",
        encoding="utf-8",
    )
    return path


def test_backlog_validation_requires_path_for_references() -> None:
    with pytest.raises(CatalogValidationError, match="product backlog path"):
        validate_catalog_curation_backlog_refs(_deferred_report(), None)


def test_backlog_validation_ignores_path_when_report_has_no_references() -> None:
    report = _deferred_report()
    report.entity_scope_assessments[0].backlog_ref = None

    validate_catalog_curation_backlog_refs(report, None)


def test_backlog_validation_rejects_unreadable_path(tmp_path: Path) -> None:
    with pytest.raises(CatalogValidationError, match="Unable to read product backlog"):
        validate_catalog_curation_backlog_refs(
            _deferred_report(),
            tmp_path / "missing.md",
        )


def test_backlog_validation_rejects_heading_outside_curation_section(
    tmp_path: Path,
) -> None:
    path = tmp_path / "product-backlog.md"
    path.write_text(
        "# Backlog\n\n## Current Backlog\n\n### KitzSki Catalog Extension\n"
        "- `ski_area:horn`\n",
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError, match="unknown backlog reference"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_rejects_nonexistent_anchor(tmp_path: Path) -> None:
    path = _write_backlog(
        tmp_path,
        "### Another Region Catalog Extension\n\n- `ski_area:horn`\n",
    )

    with pytest.raises(CatalogValidationError, match="unknown backlog reference"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_rejects_missing_candidate_marker(tmp_path: Path) -> None:
    path = _write_backlog(
        tmp_path,
        "### KitzSki Catalog Extension\n\n- `ski_area:another-area`\n",
    )

    with pytest.raises(CatalogValidationError, match="missing candidate marker"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_rejects_duplicate_normalized_anchor(
    tmp_path: Path,
) -> None:
    path = _write_backlog(
        tmp_path,
        "### KitzSki Catalog Extension\n\n- `ski_area:horn`\n\n"
        "### KitzSki: Catalog Extension\n\n- `ski_area:horn`\n",
    )

    with pytest.raises(CatalogValidationError, match="duplicate backlog anchor"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_accepts_shared_regional_item(tmp_path: Path) -> None:
    report = _deferred_report_with_candidates(
        ("ski_area", "horn"),
        ("stay_destination", "kirchberg"),
    )
    path = _write_backlog(
        tmp_path,
        "### KitzSki Catalog Extension\n\n"
        "- `ski_area:horn`\n"
        "- `stay_destination:kirchberg`\n",
    )

    validate_catalog_curation_backlog_refs(report, path)


def test_markdown_heading_anchor_normalizes_unicode() -> None:
    assert (
        markdown_heading_anchor("Kitzbühel Catalog Extension")
        == "kitzbuhel-catalog-extension"
    )

import json

import pytest
from pydantic import ValidationError

from app.data.catalog_curation import (
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogEvidenceItem,
    CatalogValidationError,
    render_catalog_curation_report_markdown,
    validate_catalog_curation_report,
)


def _valid_report() -> CatalogCurationReport:
    return CatalogCurationReport(
        title="Zell am See-Kaprun catalog curation",
        summary="Adds reviewed Kitzsteinhorn terrain facts.",
        changed_entities=["zell-am-see-kaprun", "ski_area:kitzsteinhorn"],
        changes=[
            CatalogChangeSummary(
                target_type="ski_area",
                target_id="kitzsteinhorn",
                field_path="total_piste_km",
                before=None,
                after=61,
                trust_status="verified",
                ranking_relevant=True,
            )
        ],
        evidence=[
            CatalogEvidenceItem(
                target_type="ski_area",
                target_id="kitzsteinhorn",
                field_path="total_piste_km",
                source_type="official",
                source_url=(
                    "https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board"
                ),
                source_title="Kitzsteinhorn ski and board",
                source_value=61,
                evidence_summary="Official page lists 61 piste kilometres.",
            )
        ],
        validation_commands=[
            "UV_CACHE_DIR=.uv-cache uv run --no-config python -m "
            "app.data.validate_resort_catalog"
        ],
        ranking_comparison_summary="Ranking comparison showed no top-result changes.",
    )


def test_catalog_curation_report_accepts_source_backed_change() -> None:
    report = _valid_report()

    validate_catalog_curation_report(report)

    assert report.changes[0].target_key == (
        "ski_area",
        "kitzsteinhorn",
        "total_piste_km",
    )


def test_catalog_curation_report_rejects_invalid_source_url() -> None:
    with pytest.raises(ValidationError):
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            source_type="official",
            source_url="notaurl",
            source_title="Broken source",
            source_value=61,
            evidence_summary="Official page lists 61 piste kilometres.",
        )


def test_catalog_curation_report_rejects_whitespace_only_text_fields() -> None:
    payload = _valid_report().model_dump(mode="python")
    payload["title"] = "   "

    with pytest.raises(ValidationError):
        CatalogCurationReport.model_validate(payload)

    with pytest.raises(ValidationError):
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            source_type="official",
            source_url=(
                "https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board"
            ),
            source_title="Kitzsteinhorn ski and board",
            source_value=61,
            evidence_summary="   ",
        )

    with pytest.raises(ValidationError):
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="   ",
            field_path="total_piste_km",
            source_type="official",
            source_url=(
                "https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board"
            ),
            source_title="Kitzsteinhorn ski and board",
            source_value=61,
            evidence_summary="Official page lists 61 piste kilometres.",
        )


def test_catalog_curation_report_requires_evidence_for_verified_change() -> None:
    report = _valid_report().model_copy(update={"evidence": []})

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("missing evidence" in issue for issue in error.value.issues)


def test_catalog_curation_report_rejects_third_party_only_verified_change() -> None:
    report = _valid_report()
    report.evidence[0].source_type = "third_party"

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "third_party source cannot verify" in issue for issue in error.value.issues
    )


def test_catalog_curation_report_requires_normalization_note() -> None:
    report = _valid_report()
    report.evidence[0].source_value = 61.4

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("normalization_note" in issue for issue in error.value.issues)


def test_render_catalog_curation_report_markdown_contains_clickable_evidence() -> None:
    markdown = render_catalog_curation_report_markdown(_valid_report())

    assert "# Zell am See-Kaprun catalog curation" in markdown
    assert (
        "| `ski_area:kitzsteinhorn` | `total_piste_km` | `null` | `61` | `verified` |"
    ) in markdown
    assert (
        "[Kitzsteinhorn ski and board]"
        "(https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board)"
    ) in markdown
    assert "Ranking comparison showed no top-result changes." in markdown


def test_render_catalog_curation_report_markdown_escapes_table_cells() -> None:
    report = _valid_report()
    report.evidence[0].source_title = "Kitzsteinhorn | Ski\nBoard"
    report.evidence[0].evidence_summary = "Lists 61 km | terrain\nfor winter."
    report.evidence[0].normalization_note = "Rounded | from\nsource."

    markdown = render_catalog_curation_report_markdown(report)

    assert "[Kitzsteinhorn \\| Ski Board]" in markdown
    assert "Lists 61 km \\| terrain for winter." in markdown
    assert "Rounded \\| from source." in markdown
    assert "Kitzsteinhorn | Ski\nBoard" not in markdown
    assert "Lists 61 km | terrain\nfor winter." not in markdown


def test_catalog_curation_report_round_trips_json() -> None:
    payload = _valid_report().model_dump(mode="json")

    report = CatalogCurationReport.model_validate(json.loads(json.dumps(payload)))

    assert report.evidence[0].source_url.startswith("https://www.kitzsteinhorn.at/")

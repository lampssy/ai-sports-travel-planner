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
from app.data.validate_catalog_curation import main as validate_curation_main


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


def test_catalog_curation_report_rejects_unknown_change_fields() -> None:
    payload = _valid_report().model_dump(mode="python")
    payload["changes"][0]["ranking_relevnt"] = True

    with pytest.raises(ValidationError):
        CatalogCurationReport.model_validate(payload)


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


@pytest.mark.parametrize(
    "source_url",
    [
        "https://example.com/kitzsteinhorn terrain",
        "https://example.com/kitzsteinhorn\nterrain",
        "https://example.com/kitzsteinhorn)",
        "https://example.com/kitzsteinhorn|terrain",
    ],
)
def test_catalog_evidence_item_rejects_unsafe_source_url(source_url: str) -> None:
    with pytest.raises(ValidationError):
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            source_type="official",
            source_url=source_url,
            source_title="Kitzsteinhorn ski and board",
            source_value=61,
            evidence_summary="Official page lists 61 piste kilometres.",
        )


def test_catalog_evidence_item_requires_source_value_field() -> None:
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
            evidence_summary="Official page lists 61 piste kilometres.",
        )


def test_catalog_evidence_item_accepts_explicit_null_source_value() -> None:
    evidence = CatalogEvidenceItem(
        target_type="ski_area",
        target_id="kitzsteinhorn",
        field_path="opening_status",
        source_type="official",
        source_url="https://www.kitzsteinhorn.at/en/service/current-information",
        source_title="Kitzsteinhorn current information",
        source_value=None,
        evidence_summary="Official page does not publish a current opening status.",
    )

    assert evidence.source_value is None


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


def test_catalog_curation_report_rejects_duplicate_changes() -> None:
    report = _valid_report()
    report.changes.append(
        CatalogChangeSummary(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            before=61,
            after=62,
            trust_status="verified",
            ranking_relevant=True,
        )
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("duplicate change" in issue for issue in error.value.issues)


def test_catalog_curation_report_rejects_evidence_without_matching_change() -> None:
    report = _valid_report()
    report.evidence.append(
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="vertical_drop_m",
            source_type="official",
            source_url="https://example.com/kitzsteinhorn-vertical-drop",
            source_title="Kitzsteinhorn vertical drop",
            source_value=2261,
            evidence_summary="Official page lists the vertical drop.",
        )
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "evidence has no matching change" in issue for issue in error.value.issues
    )


def test_catalog_curation_report_rejects_third_party_only_verified_change() -> None:
    report = _valid_report()
    report.evidence[0].source_type = "third_party"

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "third_party source cannot verify" in issue for issue in error.value.issues
    )


def test_catalog_curation_report_rejects_third_party_only_adjusted() -> None:
    report = _valid_report()
    report.changes[0].trust_status = "verified_with_adjustment"
    report.evidence[0].source_type = "third_party"

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "third_party source cannot verify verified_with_adjustment" in issue
        for issue in error.value.issues
    )


def test_catalog_curation_report_accepts_third_party_corroboration() -> None:
    report = _valid_report()
    report.evidence.append(
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            source_type="third_party",
            source_url="https://example.com/kitzsteinhorn-terrain-summary",
            source_title="Kitzsteinhorn terrain summary",
            source_value=61,
            evidence_summary="Third-party page corroborates 61 piste kilometres.",
        )
    )

    validate_catalog_curation_report(report)


def test_catalog_curation_report_accepts_adjusted_corroboration() -> None:
    report = _valid_report()
    report.changes[0].trust_status = "verified_with_adjustment"
    report.evidence.append(
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            source_type="third_party",
            source_url="https://example.com/kitzsteinhorn-terrain-summary",
            source_title="Kitzsteinhorn terrain summary",
            source_value=61,
            evidence_summary="Third-party page corroborates 61 piste kilometres.",
        )
    )

    validate_catalog_curation_report(report)


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


def test_render_catalog_curation_report_markdown_escapes_source_link_label() -> None:
    report = _valid_report()
    report.evidence[0].source_title = "Trusted](https://evil.example)"

    markdown = render_catalog_curation_report_markdown(report)

    assert (
        "[Trusted\\]\\(https://evil.example\\)]"
        "(https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board)"
    ) in markdown
    assert "[Trusted](https://evil.example)" not in markdown


def test_render_catalog_curation_report_markdown_encodes_source_link_url() -> None:
    report = _valid_report()
    report.evidence[0].source_url = "https://example.com/a|b"

    markdown = render_catalog_curation_report_markdown(report)

    evidence_row = next(
        line
        for line in markdown.splitlines()
        if line.startswith(
            "| `ski_area:kitzsteinhorn` | `total_piste_km` | [Kitzsteinhorn"
        )
    )
    assert "https://example.com/a%7Cb" in evidence_row
    assert "https://example.com/a|b" not in evidence_row
    assert evidence_row.count("|") == 7


def test_catalog_curation_report_round_trips_json() -> None:
    payload = _valid_report().model_dump(mode="json")

    report = CatalogCurationReport.model_validate(json.loads(json.dumps(payload)))

    assert report.evidence[0].source_url.startswith("https://www.kitzsteinhorn.at/")


def test_validate_catalog_curation_cli_accepts_valid_report(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "curation-report.json"
    markdown_path = tmp_path / "reports" / "curation-report.md"
    report_path.write_text(
        json.dumps(_valid_report().model_dump(mode="json")), encoding="utf-8"
    )

    exit_code = validate_curation_main(
        [
            "--report-path",
            str(report_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[catalog-curation-valid]" in output
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Zell am See-Kaprun catalog curation"
    )


def test_validate_catalog_curation_cli_rejects_markdown_output_write_error(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "curation-report.json"
    markdown_parent = tmp_path / "markdown-parent"
    markdown_path = markdown_parent / "curation-report.md"
    report_path.write_text(
        json.dumps(_valid_report().model_dump(mode="json")), encoding="utf-8"
    )
    markdown_parent.write_text("not a directory", encoding="utf-8")

    exit_code = validate_curation_main(
        [
            "--report-path",
            str(report_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "[catalog-curation-invalid]" in output
    assert str(markdown_path) in output
    assert "Traceback" not in output


def test_validate_catalog_curation_cli_rejects_invalid_report(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _valid_report().model_copy(update={"evidence": []})
    report_path = tmp_path / "curation-report.json"
    report_path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")

    exit_code = validate_curation_main(["--report-path", str(report_path)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "[catalog-curation-invalid]" in output

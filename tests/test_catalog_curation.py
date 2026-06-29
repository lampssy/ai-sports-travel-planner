import json

import pytest
from pydantic import ValidationError

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    CatalogBoundaryGateAssessment,
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogDestinationBoundaryAssessment,
    CatalogEvidenceItem,
    CatalogFieldCoverage,
    CatalogIdentitySignalAssessment,
    CatalogReviewedTarget,
    CatalogValidationError,
    CatalogWeatherRequestGeometry,
    CatalogWeatherRequestGeometryAssessment,
    catalog_weather_request_geometry,
    render_catalog_curation_report_markdown,
    rental_reconciliation_target_id,
    validate_catalog_curation_report,
)
from app.data.validate_catalog_curation import main as validate_curation_main
from app.domain.models import SkiArea


def _valid_report() -> CatalogCurationReport:
    return CatalogCurationReport(
        title="Zell am See-Kaprun catalog curation",
        summary="Adds reviewed Kitzsteinhorn terrain facts.",
        changed_entities=["zell-am-see-kaprun", "ski_area:kitzsteinhorn"],
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="ski_area",
                target_id="kitzsteinhorn",
                scope="narrow",
                required_field_paths=["total_piste_km"],
            )
        ],
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
        field_coverage=[
            CatalogFieldCoverage(
                target_type="ski_area",
                target_id="kitzsteinhorn",
                field_path="total_piste_km",
                status="changed",
                notes="Reviewed official piste-kilometre source and updated value.",
            )
        ],
        evidence=[
            CatalogEvidenceItem(
                evidence_id="kitzsteinhorn-total-piste-km",
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


def _boundary_assessment(
    *,
    candidate_id: str = "zell-am-see-kaprun",
    gate_status: str = "pass",
    signal_status: str = "pass",
    failure_route: str | None = None,
) -> CatalogDestinationBoundaryAssessment:
    return CatalogDestinationBoundaryAssessment(
        candidate_id=candidate_id,
        gates=[
            CatalogBoundaryGateAssessment(
                gate_name=gate_name,
                status=gate_status,
                notes=f"Reviewed {gate_name}.",
                evidence_refs=["boundary-official"],
            )
            for gate_name in (
                "independent_stay_context",
                "independent_ski_access",
                "independent_recommendation_value",
            )
        ],
        identity_signals=[
            CatalogIdentitySignalAssessment(
                signal_type="official_destination_treatment",
                status=signal_status,
                notes="Official destination page treats it independently.",
                evidence_refs=["boundary-official"],
            )
        ],
        failure_route=failure_route,
    )


def _report_with_boundary_assessment() -> CatalogCurationReport:
    report = _valid_report()
    report.reviewed_targets.append(
        CatalogReviewedTarget(
            target_type="destination",
            target_id="zell-am-see-kaprun",
            scope="narrow",
            required_field_paths=["resort_id"],
        )
    )
    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="destination",
            target_id="zell-am-see-kaprun",
            field_path="resort_id",
            status="reviewed-no-change",
        )
    )
    report.evidence.append(
        CatalogEvidenceItem(
            evidence_id="boundary-official",
            target_type="destination",
            target_id="zell-am-see-kaprun",
            field_path="resort_id",
            source_type="official",
            source_url="https://example.com/zell-am-see-kaprun",
            source_title="Official destination page",
            source_value="zell-am-see-kaprun",
            evidence_summary="Official page presents the destination independently.",
        )
    )
    report.boundary_decision_targets = ["zell-am-see-kaprun"]
    report.destination_boundary_assessments = [_boundary_assessment()]
    return report


def test_catalog_curation_report_accepts_source_backed_change() -> None:
    report = _valid_report()

    validate_catalog_curation_report(report)

    assert report.changes[0].target_key == (
        "ski_area",
        "kitzsteinhorn",
        "total_piste_km",
    )


def test_catalog_curation_report_accepts_scoped_catalog_targets() -> None:
    report = CatalogCurationReport(
        title="Scoped catalog facts",
        summary="Adds scoped pass product and aggregate terrain evidence.",
        changed_entities=[
            "zell-am-see-kaprun",
            "lift_pass_product:ski-alpin-card",
            "terrain_group:kitzsteinhorn-maiskogel",
            "terrain_domain:tignes-val-disere",
        ],
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                scope="narrow",
                required_field_paths=["validity_scope"],
            ),
            CatalogReviewedTarget(
                target_type="terrain_group",
                target_id="kitzsteinhorn-maiskogel",
                scope="narrow",
                required_field_paths=["piste_km_by_difficulty.beginner"],
            ),
            CatalogReviewedTarget(
                target_type="terrain_domain",
                target_id="tignes-val-disere",
                scope="narrow",
                required_field_paths=["total_lift_count"],
            ),
        ],
        changes=[
            CatalogChangeSummary(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                field_path="validity_scope",
                before=None,
                after="regional_network",
                trust_status="verified_with_adjustment",
                ranking_relevant=False,
            ),
            CatalogChangeSummary(
                target_type="terrain_group",
                target_id="kitzsteinhorn-maiskogel",
                field_path="piste_km_by_difficulty.beginner",
                before=None,
                after=30.5,
                trust_status="verified_with_adjustment",
                ranking_relevant=True,
            ),
            CatalogChangeSummary(
                target_type="terrain_domain",
                target_id="tignes-val-disere",
                field_path="total_lift_count",
                before=None,
                after=72,
                trust_status="verified_with_adjustment",
                ranking_relevant=True,
            ),
        ],
        field_coverage=[
            CatalogFieldCoverage(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                field_path="validity_scope",
                status="changed",
                notes="Normalized official ticket validity wording.",
            ),
            CatalogFieldCoverage(
                target_type="terrain_group",
                target_id="kitzsteinhorn-maiskogel",
                field_path="piste_km_by_difficulty.beginner",
                status="changed",
                notes="Stored aggregate terrain-group difficulty split.",
            ),
            CatalogFieldCoverage(
                target_type="terrain_domain",
                target_id="tignes-val-disere",
                field_path="total_lift_count",
                status="changed",
                notes="Stored linked-domain fallback lift count.",
            ),
        ],
        evidence=[
            CatalogEvidenceItem(
                evidence_id="ski-alpin-card-validity-scope",
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                field_path="validity_scope",
                source_type="official",
                source_url="https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes",
                source_title="Zell am See-Kaprun ski passes",
                source_value="Ski ALPIN CARD valid across regional network",
                evidence_summary=(
                    "Official tariff page describes the Ski ALPIN CARD network."
                ),
                normalization_note=(
                    "Normalized official validity wording to regional_network."
                ),
            ),
            CatalogEvidenceItem(
                evidence_id="kitzsteinhorn-maiskogel-difficulty",
                target_type="terrain_group",
                target_id="kitzsteinhorn-maiskogel",
                field_path="piste_km_by_difficulty.beginner",
                source_type="reviewed_editorial",
                source_url="https://www.skiresort.info/ski-resorts/alpin-card/sorted/day-ticket-price/",
                source_title="Skiresort.info ALPIN CARD terrain overview",
                source_value=30.5,
                evidence_summary=(
                    "Reviewed editorial source publishes the aggregate "
                    "Kitzsteinhorn/Maiskogel difficulty split."
                ),
            ),
            CatalogEvidenceItem(
                evidence_id="tignes-official-lift-count",
                target_type="terrain_domain",
                target_id="tignes-val-disere",
                field_path="total_lift_count",
                source_type="official",
                source_url="https://en.tignes.net/skiing/ski-area",
                source_title="Tignes - Val d'Isere ski area",
                source_value=74,
                evidence_summary=(
                    "Official Tignes page publishes a linked-domain lift count."
                ),
                normalization_note=(
                    "Official sources conflict, so this value is retained as "
                    "conflict evidence rather than used as the canonical count."
                ),
            ),
            CatalogEvidenceItem(
                evidence_id="tignes-reviewed-lift-count",
                target_type="terrain_domain",
                target_id="tignes-val-disere",
                field_path="total_lift_count",
                source_type="third_party",
                source_url="https://www.bergfex.com/skiregionen/valdiseres-tignes/",
                source_title="Bergfex Val d'Isere - Tignes skiregion",
                source_value=[15, 38, 6, 3, 2, 1, 7],
                evidence_summary=(
                    "Bergfex publishes linked skiregion lift category counts "
                    "for the same 300 km Val d'Isere - Tignes scope."
                ),
                normalization_note=(
                    "Summed Bergfex lift categories to total_lift_count=72 as "
                    "the fallback value after official-source disagreement."
                ),
            ),
        ],
        validation_commands=[
            "UV_CACHE_DIR=.uv-cache uv run --no-config python -m "
            "app.data.validate_resort_catalog"
        ],
        ranking_comparison_summary=(
            "Ranking comparison was reviewed because aggregate terrain facts are "
            "fit-relevant."
        ),
    )

    validate_catalog_curation_report(report)


def test_canonical_field_paths_are_immutable_and_include_trust_contract() -> None:
    assert CANONICAL_FIELD_PATHS["trust_manifest"] == frozenset(
        {"display_name", "field_statuses", "source_refs", "notes"}
    )

    with pytest.raises(TypeError):
        CANONICAL_FIELD_PATHS["trust_manifest"] = frozenset()  # type: ignore[index]


def test_catalog_evidence_requires_unique_evidence_id() -> None:
    payload = _valid_report().model_dump(mode="python")
    payload["evidence"][0].pop("evidence_id")

    with pytest.raises(ValidationError):
        CatalogCurationReport.model_validate(payload)

    report = _valid_report()
    report.evidence.append(report.evidence[0].model_copy())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("duplicate evidence_id" in issue for issue in error.value.issues)


def test_full_reviewed_target_requires_every_canonical_field_path() -> None:
    report = _valid_report()
    report.reviewed_targets[0] = CatalogReviewedTarget(
        target_type="ski_area",
        target_id="kitzsteinhorn",
        scope="full",
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("missing field coverage" in issue for issue in error.value.issues)
    assert any("ski_area_id" in issue for issue in error.value.issues)


def test_changed_only_full_review_is_rejected() -> None:
    report = _valid_report()
    report.reviewed_targets[0] = CatalogReviewedTarget(
        target_type="ski_area",
        target_id="kitzsteinhorn",
        scope="full",
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert (
        len(
            [issue for issue in error.value.issues if "missing field coverage" in issue]
        )
        == len(CANONICAL_FIELD_PATHS["ski_area"]) - 1
    )


def test_narrow_reviewed_target_requires_exact_declared_paths() -> None:
    report = _valid_report()
    report.reviewed_targets[0] = CatalogReviewedTarget(
        target_type="ski_area",
        target_id="kitzsteinhorn",
        scope="narrow",
        required_field_paths=["total_piste_km", "name"],
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("name: missing field coverage" in issue for issue in error.value.issues)


def test_changed_trust_target_must_be_declared_as_reviewed() -> None:
    report = _valid_report()
    report.changes.append(
        CatalogChangeSummary(
            target_type="trust_manifest",
            target_id="destination:zell-am-see-kaprun",
            field_path="display_name",
            before="Zell am See",
            after="Zell am See-Kaprun",
            trust_status="verified",
        )
    )
    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="trust_manifest",
            target_id="destination:zell-am-see-kaprun",
            field_path="display_name",
            status="changed",
        )
    )
    report.evidence.append(
        CatalogEvidenceItem(
            evidence_id="zell-trust-display-name",
            target_type="trust_manifest",
            target_id="destination:zell-am-see-kaprun",
            field_path="display_name",
            source_type="official",
            source_url="https://example.com/zell-am-see-kaprun-name",
            source_title="Official destination name",
            source_value="Zell am See-Kaprun",
            evidence_summary="Official page uses the current display name.",
        )
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("target is not declared" in issue for issue in error.value.issues)


def test_catalog_curation_report_accepts_mixed_full_and_narrow_reviews() -> None:
    report = _valid_report()
    report.reviewed_targets[0] = CatalogReviewedTarget(
        target_type="ski_area",
        target_id="kitzsteinhorn",
        scope="full",
    )
    report.field_coverage = [
        CatalogFieldCoverage(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path=field_path,
            status=(
                "changed" if field_path == "total_piste_km" else "reviewed-no-change"
            ),
        )
        for field_path in sorted(CANONICAL_FIELD_PATHS["ski_area"])
    ]
    report.reviewed_targets.append(
        CatalogReviewedTarget(
            target_type="destination",
            target_id="zell-am-see-kaprun",
            scope="narrow",
            required_field_paths=["resort_id"],
        )
    )
    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="destination",
            target_id="zell-am-see-kaprun",
            field_path="resort_id",
            status="reviewed-no-change",
        )
    )

    validate_catalog_curation_report(report)


def test_nested_collection_change_keeps_collection_and_exact_coverage() -> None:
    report = CatalogCurationReport(
        title="Lift-pass price correction",
        summary="Corrects one indexed adult price.",
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                scope="narrow",
                required_field_paths=["name"],
            )
        ],
        changes=[
            CatalogChangeSummary(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                field_path="prices[0].amount",
                before=75,
                after=79,
                trust_status="estimated",
            )
        ],
        field_coverage=[
            CatalogFieldCoverage(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                field_path="name",
                status="reviewed-no-change",
            ),
            CatalogFieldCoverage(
                target_type="lift_pass_product",
                target_id="ski-alpin-card",
                field_path="prices[0].amount",
                status="changed",
            ),
        ],
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "prices: missing field coverage" in issue for issue in error.value.issues
    )

    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="lift_pass_product",
            target_id="ski-alpin-card",
            field_path="prices",
            status="reviewed-no-change",
        )
    )

    validate_catalog_curation_report(report)


def test_reviewed_target_scope_rejects_invalid_required_field_paths() -> None:
    with pytest.raises(ValidationError):
        CatalogReviewedTarget(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            scope="full",
            required_field_paths=["name"],
        )

    with pytest.raises(ValidationError):
        CatalogReviewedTarget(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            scope="narrow",
            required_field_paths=[],
        )

    with pytest.raises(ValidationError):
        CatalogReviewedTarget(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            scope="narrow",
            required_field_paths=["not_a_catalog_field"],
        )

    with pytest.raises(ValidationError):
        CatalogChangeSummary(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="name.value",
            before="Old",
            after="New",
            trust_status="estimated",
        )


def test_catalog_boundary_assessment_requires_exact_gate_set() -> None:
    payload = _boundary_assessment().model_dump(mode="python")
    payload["gates"].pop()

    with pytest.raises(ValidationError):
        CatalogDestinationBoundaryAssessment.model_validate(payload)


@pytest.mark.parametrize("gate_status", ["fail", "unresolved"])
def test_non_passing_boundary_assessment_requires_route(gate_status: str) -> None:
    with pytest.raises(ValidationError):
        _boundary_assessment(gate_status=gate_status)


def test_boundary_assessment_without_passing_signal_requires_route() -> None:
    with pytest.raises(ValidationError):
        _boundary_assessment(signal_status="fail")


def test_boundary_assessment_rejects_unknown_evidence_reference() -> None:
    report = _report_with_boundary_assessment()
    report.destination_boundary_assessments[0].gates[0].evidence_refs = [
        "missing-evidence"
    ]

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("unknown evidence ref" in issue for issue in error.value.issues)


def test_boundary_assessment_requires_source_backed_passing_evidence() -> None:
    report = _report_with_boundary_assessment()
    report.evidence[-1].source_type = "third_party"

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("passing gate" in issue for issue in error.value.issues)
    assert any(
        "official_destination_treatment" in issue for issue in error.value.issues
    )


def test_boundary_only_evidence_is_valid_only_when_referenced() -> None:
    report = _report_with_boundary_assessment()

    validate_catalog_curation_report(report)

    report.destination_boundary_assessments[0].gates[0].evidence_refs = [
        report.evidence[0].evidence_id
    ]
    report.destination_boundary_assessments[0].gates[1].evidence_refs = [
        report.evidence[0].evidence_id
    ]
    report.destination_boundary_assessments[0].gates[2].evidence_refs = [
        report.evidence[0].evidence_id
    ]
    report.destination_boundary_assessments[0].identity_signals[0].evidence_refs = [
        report.evidence[0].evidence_id
    ]

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "evidence has no matching change" in issue for issue in error.value.issues
    )


def test_typed_only_boundary_failure_can_exist_without_catalog_changes() -> None:
    report = _report_with_boundary_assessment()
    report.changes.clear()
    report.field_coverage[0].status = "reviewed-no-change"
    report.evidence.pop(0)
    report.ranking_comparison_summary = None
    report.destination_boundary_assessments[0].gates[0].status = "fail"
    report.destination_boundary_assessments[0].failure_route = "blocked"

    parsed = CatalogCurationReport.model_validate(report.model_dump(mode="python"))

    validate_catalog_curation_report(parsed)


@pytest.mark.parametrize(
    ("rental_name", "expected"),
    [
        ("École Ski & Rent", "madonna-di-campiglio:ecole-ski-rent"),
        ("Straße SPORT", "madonna-di-campiglio:strasse-sport"),
        ("Ski---Rent / Campiglio", "madonna-di-campiglio:ski-rent-campiglio"),
    ],
)
def test_rental_reconciliation_target_id_is_destination_qualified(
    rental_name: str, expected: str
) -> None:
    assert (
        rental_reconciliation_target_id("madonna-di-campiglio", rental_name) == expected
    )


def test_rental_reconciliation_target_id_rejects_empty_slug() -> None:
    with pytest.raises(ValueError):
        rental_reconciliation_target_id("madonna-di-campiglio", "---")


def _ski_area_geometry(
    *,
    latitude: float = 46.2267,
    longitude: float = 10.8268,
    base_elevation_m: int = 1550,
    summit_elevation_m: int = 2504,
) -> CatalogWeatherRequestGeometry:
    ski_area = SkiArea(
        ski_area_id="madonna-di-campiglio-ski-area",
        name="Madonna di Campiglio",
        latitude=latitude,
        longitude=longitude,
        base_elevation_m=base_elevation_m,
        summit_elevation_m=summit_elevation_m,
        season_start_month=12,
        season_end_month=4,
    )
    return catalog_weather_request_geometry(ski_area)


def test_weather_geometry_assessment_requires_declared_assessment() -> None:
    report = _valid_report()
    report.weather_request_geometry_targets = ["kitzsteinhorn"]

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "missing weather request geometry assessment" in issue
        for issue in error.value.issues
    )


def test_weather_geometry_material_change_detects_coordinate_only_change() -> None:
    before = _ski_area_geometry()
    after = before.model_copy(update={"longitude": 10.9})

    assessment = CatalogWeatherRequestGeometryAssessment(
        ski_area_id="madonna-di-campiglio-ski-area",
        before=before,
        after=after,
    )

    assert assessment.material_change is True


def test_weather_geometry_material_change_detects_band_only_change() -> None:
    before = _ski_area_geometry()
    after = before.model_copy(update={"upper_elevation_m": 2410})

    assessment = CatalogWeatherRequestGeometryAssessment(
        ski_area_id="madonna-di-campiglio-ski-area",
        before=before,
        after=after,
    )

    assert assessment.material_change is True


def test_weather_geometry_material_change_is_false_for_identical_geometry() -> None:
    geometry = _ski_area_geometry()

    assessment = CatalogWeatherRequestGeometryAssessment(
        ski_area_id="madonna-di-campiglio-ski-area",
        before=geometry,
        after=geometry.model_copy(),
    )

    assert assessment.material_change is False


def test_weather_geometry_material_change_cannot_be_supplied() -> None:
    geometry = _ski_area_geometry().model_dump(mode="python")

    with pytest.raises(ValidationError):
        CatalogWeatherRequestGeometryAssessment.model_validate(
            {
                "ski_area_id": "madonna-di-campiglio-ski-area",
                "before": geometry,
                "after": geometry,
                "material_change": True,
            }
        )


def test_e8f4e11_madonna_weather_geometry_uses_open_meteo_bands() -> None:
    before = _ski_area_geometry()
    after = _ski_area_geometry(longitude=10.8269, summit_elevation_m=2505)

    assessment = CatalogWeatherRequestGeometryAssessment(
        ski_area_id="madonna-di-campiglio-ski-area",
        before=before,
        after=after,
    )

    assert before == CatalogWeatherRequestGeometry(
        latitude=46.2267,
        longitude=10.8268,
        base_elevation_m=1550,
        mid_elevation_m=2027,
        upper_elevation_m=2409,
    )
    assert assessment.material_change is True


def test_catalog_curation_report_rejects_unknown_change_fields() -> None:
    payload = _valid_report().model_dump(mode="python")
    payload["changes"][0]["ranking_relevnt"] = True

    with pytest.raises(ValidationError):
        CatalogCurationReport.model_validate(payload)


def test_catalog_field_coverage_rejects_blank_notes() -> None:
    with pytest.raises(ValidationError):
        CatalogFieldCoverage(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            status="reviewed-no-change",
            notes="   ",
        )


def test_catalog_curation_report_rejects_invalid_source_url() -> None:
    with pytest.raises(ValidationError):
        CatalogEvidenceItem(
            evidence_id="explicit-null-source-value",
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
            evidence_id="kitzsteinhorn-vertical-drop",
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
            evidence_id="kitzsteinhorn-third-party-corroboration",
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
        evidence_id="explicit-null-source-value",
        target_type="ski_area",
        target_id="kitzsteinhorn",
        field_path="total_lift_count",
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
            evidence_id="kitzsteinhorn-adjusted-corroboration",
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
            evidence_id="blank-target-id",
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


def test_report_requires_ranking_summary_for_ranking_relevant_change() -> None:
    report = _valid_report().model_copy(update={"ranking_comparison_summary": None})

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("ranking_comparison_summary" in issue for issue in error.value.issues)


def test_catalog_curation_report_requires_evidence_for_ranking_relevant_change() -> (
    None
):
    report = _valid_report()
    report.changes[0].trust_status = "estimated"
    report.evidence.clear()

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "missing evidence" in issue and "ranking-relevant" in issue
        for issue in error.value.issues
    )


def test_report_accepts_estimated_non_ranking_change_without_evidence() -> None:
    report = _valid_report()
    report.changes[0].trust_status = "estimated"
    report.changes[0].ranking_relevant = False
    report.evidence.clear()
    report.ranking_comparison_summary = None

    validate_catalog_curation_report(report)


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


def test_catalog_curation_report_requires_changed_field_coverage() -> None:
    report = _valid_report().model_copy(update={"field_coverage": []})

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "missing changed field coverage" in issue for issue in error.value.issues
    )


def test_catalog_curation_report_requires_changed_coverage_status() -> None:
    report = _valid_report()
    report.field_coverage[0].status = "reviewed-no-change"

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "must be covered with status=changed" in issue for issue in error.value.issues
    )


def test_catalog_curation_report_rejects_changed_coverage_without_change() -> None:
    report = _valid_report()
    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_lift_count",
            status="changed",
            notes="Marked changed without a corresponding catalog change.",
        )
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "changed field coverage has no matching change" in issue
        for issue in error.value.issues
    )


def test_catalog_curation_report_rejects_duplicate_field_coverage() -> None:
    report = _valid_report()
    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            status="changed",
            notes="Duplicate field coverage row.",
        )
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("duplicate field coverage" in issue for issue in error.value.issues)


def test_catalog_curation_report_requires_notes_for_unresolved_coverage() -> None:
    report = _valid_report()
    report.field_coverage.append(
        CatalogFieldCoverage(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_lift_count",
            status="unresolved",
        )
    )

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any(
        "unresolved field coverage requires notes" in issue
        for issue in error.value.issues
    )


def test_catalog_curation_report_rejects_evidence_without_matching_change() -> None:
    report = _valid_report()
    report.evidence.append(
        CatalogEvidenceItem(
            evidence_id="kitzsteinhorn-unmatched-lift-count",
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_lift_count",
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
            evidence_id="kitzsteinhorn-third-party-corroboration",
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
            evidence_id="kitzsteinhorn-adjusted-corroboration",
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
    assert "## Field Coverage" in markdown
    assert (
        "| `ski_area:kitzsteinhorn` | `total_piste_km` | `changed` | "
        "Reviewed official piste-kilometre source and updated value. |"
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
    assert "field_coverage=1" in output
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Zell am See-Kaprun catalog curation"
    )


def test_validate_catalog_curation_cli_preserves_field_coverage_appendix(
    tmp_path,
) -> None:
    report_path = tmp_path / "curation-report.json"
    markdown_path = tmp_path / "curation-report.md"
    report_path.write_text(
        json.dumps(_valid_report().model_dump(mode="json")), encoding="utf-8"
    )
    markdown_path.write_text(
        "# Old report\n\n## Field Coverage Matrix\n\nManual field coverage.\n",
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "--report-path",
            str(report_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    markdown = markdown_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert markdown.startswith("# Zell am See-Kaprun catalog curation")
    assert "## Field Coverage Matrix\n\nManual field coverage." in markdown


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

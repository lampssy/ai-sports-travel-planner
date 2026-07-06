import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogEvidenceItem,
    CatalogFieldCoverage,
    CatalogReviewedTarget,
    CatalogValidationError,
    catalog_weather_request_geometry,
    load_catalog_curation_report,
    render_catalog_curation_report_markdown,
    validate_catalog_curation_report,
)
from app.data.catalog_policy import catalog_policy_issues
from app.domain.catalog import CatalogSnapshot
from tests.test_catalog_models import minimal_catalog_payload

NORMALIZED_TARGET_TYPES = {
    "ski_region",
    "stay_destination",
    "stay_base",
    "ski_area",
    "ski_area_access",
    "terrain_domain",
    "lift_pass_product",
    "rental_display_fact",
    "trust_manifest",
}


def _access_distance_report(*, status: str = "estimated") -> CatalogCurationReport:
    return CatalogCurationReport(
        title="Example access review",
        summary="Reviews one normalized ski-area access distance.",
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="ski_area_access",
                target_id="example-village--example-area",
                scope="narrow",
                required_field_paths=["distance_m"],
            )
        ],
        changes=[
            CatalogChangeSummary(
                target_type="ski_area_access",
                target_id="example-village--example-area",
                field_path="distance_m",
                before=300,
                after=350,
                trust_status=status,
            )
        ],
        field_coverage=[
            CatalogFieldCoverage(
                target_type="ski_area_access",
                target_id="example-village--example-area",
                field_path="distance_m",
                status="changed",
            )
        ],
    )


def _scope_report_payload(
    *,
    candidate_kind: str = "ski_area_access",
    disposition: str = "represented",
    signals: list[str] | None = None,
    source_type: str = "official",
    target_type: str = "ski_area_access",
    target_id: str = "example-village--example-area",
) -> dict:
    payload = _access_distance_report().model_dump(mode="json")
    payload.update(
        {
            "report_schema_version": 2,
            "entity_scope_assessments": [
                {
                    "candidate_id": "example-access",
                    "candidate_name": "Example access",
                    "candidate_kind": candidate_kind,
                    "disposition": disposition,
                    "signals": signals or ["direct_access_relationship"],
                    "evidence_refs": ["example-scope"],
                    "target_refs": [
                        {
                            "target_type": target_type,
                            "target_id": target_id,
                        }
                    ],
                    "rationale": "The official source identifies the catalog scope.",
                }
            ],
            "evidence": [
                {
                    "evidence_id": "example-scope",
                    "target_type": "ski_area_access",
                    "target_id": "example-village--example-area",
                    "field_path": "source_urls",
                    "source_type": source_type,
                    "source_url": "https://example.com/ski-map",
                    "source_title": "Official ski map",
                    "source_value": ["https://example.com/ski-map"],
                    "evidence_summary": "Shows the named access and terrain scope.",
                }
            ],
        }
    )
    return payload


def test_canonical_paths_cover_only_normalized_catalog_entities() -> None:
    assert set(CANONICAL_FIELD_PATHS) == NORMALIZED_TARGET_TYPES
    assert "stay_destination_id" in CANONICAL_FIELD_PATHS["stay_destination"]
    assert "stay_destination_id" in CANONICAL_FIELD_PATHS["stay_base"]
    assert {"stay_base_id", "ski_area_id", "source_urls"} <= (
        CANONICAL_FIELD_PATHS["ski_area_access"]
    )
    assert (
        "available_from_stay_destination_ids"
        in CANONICAL_FIELD_PATHS["lift_pass_product"]
    )
    assert {
        "elevation_m",
        "base_type",
        "base_character.development_style",
        "base_character.local_pace",
        "local_apres_profile.availability",
        "local_apres_profile.intensity",
        "local_apres_profile.season_label",
    } <= CANONICAL_FIELD_PATHS["stay_base"]
    assert {
        "snowmaking.availability",
        "snowmaking.coverage_pct",
        "snowmaking.coverage_basis",
        "snowmaking.season_label",
        "glacier_terrain.availability",
        "snow_park.availability",
        "snow_park.park_count",
        "snow_park.season_label",
        "night_skiing.availability",
        "night_skiing.season_label",
        "marked_freeride_routes.availability",
        "marked_freeride_routes.route_count",
        "marked_freeride_routes.season_label",
        "official_trail_map.url",
        "official_trail_map.season_label",
        "ski_day_apres_profile.availability",
        "ski_day_apres_profile.intensity",
        "ski_day_apres_profile.season_label",
    } <= CANONICAL_FIELD_PATHS["ski_area"]
    assert {
        "official_trail_map.url",
        "official_trail_map.season_label",
    } <= CANONICAL_FIELD_PATHS["terrain_domain"]
    assert "atmosphere_tags" not in CANONICAL_FIELD_PATHS["stay_destination"]
    assert "atmosphere_tags" not in CANONICAL_FIELD_PATHS["stay_base"]
    assert "field_source_refs" in CANONICAL_FIELD_PATHS["trust_manifest"]
    assert "source_refs" not in CANONICAL_FIELD_PATHS["trust_manifest"]


def test_report_requires_coverage_for_every_declared_field() -> None:
    report = _access_distance_report()
    report.field_coverage.clear()

    with pytest.raises(CatalogValidationError, match="missing changed field coverage"):
        validate_catalog_curation_report(report)


def test_existing_report_defaults_to_schema_version_one() -> None:
    payload = _access_distance_report().model_dump(mode="json")
    payload.pop("report_schema_version")
    payload.pop("entity_scope_assessments")
    report = CatalogCurationReport.model_validate(payload)

    assert report.report_schema_version == 1
    validate_catalog_curation_report(report)


def test_schema_version_two_requires_entity_scope_assessments() -> None:
    payload = _access_distance_report().model_dump(mode="json")
    payload["report_schema_version"] = 2
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="schema version 2 requires entity_scope_assessments",
    ):
        validate_catalog_curation_report(report)


def test_scope_assessment_accepts_evidence_without_a_field_change() -> None:
    report = CatalogCurationReport.model_validate(_scope_report_payload())

    validate_catalog_curation_report(report)


def test_scope_assessment_rejects_unknown_evidence() -> None:
    payload = _scope_report_payload()
    payload["entity_scope_assessments"][0]["evidence_refs"] = ["missing-evidence"]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match="unknown scope evidence"):
        validate_catalog_curation_report(report)


def test_scope_assessment_candidate_ids_must_be_unique() -> None:
    payload = _scope_report_payload()
    payload["entity_scope_assessments"].append(
        payload["entity_scope_assessments"][0].copy()
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match="duplicate scope candidate"):
        validate_catalog_curation_report(report)


def test_scope_assessment_target_must_be_reviewed() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        target_type="ski_area",
        target_id="missing-ski-area",
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match="scope target is not reviewed"):
        validate_catalog_curation_report(report)


def test_scope_assessment_target_kind_must_match_candidate_kind() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="deferred",
    )

    with pytest.raises(ValidationError, match="target_refs must match candidate_kind"):
        CatalogCurationReport.model_validate(payload)


def test_full_graph_target_must_appear_in_scope_inventory() -> None:
    payload = _scope_report_payload()
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "scope": "full",
            "required_field_paths": [],
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="full graph target is missing from entity scope assessments",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize("disposition", ["represented", "add_entity", "not_separate"])
def test_source_backed_scope_dispositions_require_verification_evidence(
    disposition: str,
) -> None:
    report = CatalogCurationReport.model_validate(
        _scope_report_payload(disposition=disposition, source_type="third_party")
    )

    with pytest.raises(
        CatalogValidationError,
        match="requires verification-capable evidence",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "signal",
    [
        "official_map_sector",
        "webcam",
        "limited_area_ticket",
        "secondary_provider_listing",
    ],
)
def test_supporting_signal_alone_cannot_create_a_ski_area(signal: str) -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[signal],
        target_type="ski_area",
        target_id="example-area",
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="new ski area requires an independent-owner signal",
    ):
        validate_catalog_curation_report(report)


def test_connected_named_sector_can_be_assessed_as_not_separate() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="kitzski",
    )
    payload["entity_scope_assessments"][0]["candidate_id"] = "pengelstein-sector"
    payload["entity_scope_assessments"][0]["candidate_name"] = "Pengelstein"
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "kitzski",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "kitzski",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


def test_independent_owner_signal_can_support_a_new_ski_area() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=["child_scoped_terrain_metrics", "full_local_pass"],
        target_type="ski_area",
        target_id="independent-area",
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "independent-area",
            "scope": "narrow",
            "required_field_paths": ["ski_area_id", "name"],
        }
    )
    payload["changes"].append(
        {
            "target_type": "ski_area",
            "target_id": "independent-area",
            "field_path": "ski_area_id",
            "before": None,
            "after": "independent-area",
            "trust_status": "estimated",
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "independent-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "independent-area",
            "field_path": "ski_area_id",
            "status": "changed",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


def test_add_entity_requires_a_matching_identity_change() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=["official_independent_identity"],
        target_type="ski_area",
        target_id="independent-area",
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "independent-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "independent-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="add_entity requires a matching identity-field creation change",
    ):
        validate_catalog_curation_report(report)


def test_scope_assessment_markdown_is_rendered() -> None:
    report = CatalogCurationReport.model_validate(_scope_report_payload())

    rendered = render_catalog_curation_report_markdown(report)

    assert "## Entity Scope Assessments" in rendered
    assert "`example-access`" in rendered
    assert "`represented`" in rendered


def test_verified_change_requires_direct_evidence() -> None:
    report = _access_distance_report(status="verified")

    with pytest.raises(CatalogValidationError, match="missing evidence for verified"):
        validate_catalog_curation_report(report)

    report.evidence.append(
        CatalogEvidenceItem(
            evidence_id="example-access-distance",
            target_type="ski_area_access",
            target_id="example-village--example-area",
            field_path="distance_m",
            source_type="open_data",
            source_url="https://www.openstreetmap.org/way/1",
            source_title="OSM lift access",
            source_value=350,
            evidence_summary="Measured the representative access geometry.",
        )
    )
    validate_catalog_curation_report(report)


def test_report_markdown_renders_clickable_evidence_and_coverage() -> None:
    report = _access_distance_report(status="verified")
    report.evidence.append(
        CatalogEvidenceItem(
            evidence_id="example-access-distance",
            target_type="ski_area_access",
            target_id="example-village--example-area",
            field_path="distance_m",
            source_type="open_data",
            source_url="https://www.openstreetmap.org/way/1",
            source_title="OSM lift access",
            source_value=350,
            evidence_summary="Measured the representative access geometry.",
        )
    )

    rendered = render_catalog_curation_report_markdown(report)

    assert "## Field Coverage" in rendered
    assert "[OSM lift access](https://www.openstreetmap.org/way/1)" in rendered
    assert "`ski_area_access:example-village--example-area`" in rendered


def test_weather_geometry_uses_normalized_ski_area() -> None:
    ski_area = CatalogSnapshot.model_validate(minimal_catalog_payload()).ski_areas[0]

    geometry = catalog_weather_request_geometry(ski_area)

    assert geometry.base_elevation_m == 1200
    assert geometry.mid_elevation_m == 1800
    assert geometry.upper_elevation_m == 2280


def test_catalog_policy_checks_normalized_access_and_terrain_metrics() -> None:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["distance_m"] = 1800
    payload["ski_areas"][0].update(
        {
            "total_piste_km": 100,
            "piste_km_by_difficulty": {
                "beginner": 10,
                "intermediate": 20,
                "advanced": 30,
            },
        }
    )
    snapshot = CatalogSnapshot.model_validate(payload)

    issues = catalog_policy_issues(snapshot)

    assert any("difficulty piste total" in issue.message for issue in issues)
    assert any("walk access conflicts" in issue.message for issue in issues)


def test_load_report_rejects_unknown_legacy_target_type(tmp_path: Path) -> None:
    payload = _access_distance_report().model_dump(mode="json")
    payload["reviewed_targets"][0]["target_type"] = "destination"
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_catalog_curation_report(path)

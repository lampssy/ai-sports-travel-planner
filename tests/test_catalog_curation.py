import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    NESTED_FIELD_PATH_ROOTS,
    CatalogBoundaryGateAssessment,
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogDestinationBoundaryAssessment,
    CatalogEvidenceItem,
    CatalogFieldCoverage,
    CatalogIdentitySignalAssessment,
    CatalogResultingGraph,
    CatalogReviewedTarget,
    CatalogValidationError,
    catalog_weather_request_geometry,
    load_catalog_curation_report,
    render_catalog_curation_report_markdown,
    render_catalog_resulting_graph_markdown,
    validate_catalog_curation_report,
    validate_catalog_resulting_graph,
)
from app.data.catalog_policy import catalog_policy_issues
from app.domain.catalog import CatalogSnapshot
from tests.test_catalog_models import (
    add_second_destination_base_with_access,
    add_terrain_domain,
    minimal_catalog_payload,
)

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


def _destination_boundary_report(
    *,
    gate_names: tuple[str, str, str],
    identity_signal: str,
    failure_route: str | None = None,
    source_type: str = "official",
) -> CatalogCurationReport:
    evidence = CatalogEvidenceItem(
        evidence_id="example-stay-market",
        boundary_target_ids=["example"],
        target_type="stay_destination",
        target_id="example",
        field_path="name",
        source_type=source_type,
        source_url="https://example.com/stays",
        source_title="Official accommodation market",
        source_value="Example",
        evidence_summary="Defines the complete independently managed stay market.",
    )
    assessment = CatalogDestinationBoundaryAssessment(
        candidate_id="example",
        gates=[
            CatalogBoundaryGateAssessment(
                gate_name=gate_name,
                status="pass",
                notes="The official source supports this gate.",
                evidence_refs=[evidence.evidence_id],
            )
            for gate_name in gate_names
        ],
        identity_signals=[
            CatalogIdentitySignalAssessment(
                signal_type=identity_signal,
                status="pass",
                notes="The official source owns the accommodation market.",
                evidence_refs=[evidence.evidence_id],
            )
        ],
        failure_route=failure_route,
    )
    return CatalogCurationReport(
        title="Example destination boundary",
        summary="Reviews one stay-market boundary.",
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="stay_destination",
                target_id="example",
                scope="narrow",
                required_field_paths=["name"],
            )
        ],
        field_coverage=[
            CatalogFieldCoverage(
                target_type="stay_destination",
                target_id="example",
                field_path="name",
                status="reviewed-no-change",
            )
        ],
        evidence=[evidence],
        destination_boundary_assessments=[assessment],
        boundary_decision_targets=["example"],
    )


def _current_destination_scope_report() -> CatalogCurationReport:
    payload = _destination_boundary_report(
        gate_names=(
            "complete_stay_market_scope",
            "independent_stay_market_ownership",
            "material_destination_level_separation_value",
        ),
        identity_signal="official_stay_market_treatment",
    ).model_dump(mode="json")
    payload.update(
        {
            "report_schema_version": 3,
            "resulting_graph": {"focus_stay_destination_ids": ["example"]},
            "entity_scope_assessments": [
                {
                    "candidate_id": "example",
                    "candidate_name": "Example",
                    "candidate_kind": "stay_destination",
                    "disposition": "represented",
                    "signals": ["independent_stay_market"],
                    "evidence_refs": ["example-stay-market"],
                    "target_refs": [
                        {
                            "target_type": "stay_destination",
                            "target_id": "example",
                        }
                    ],
                    "rationale": "The official source defines this stay market.",
                }
            ],
        }
    )
    return CatalogCurationReport.model_validate(payload)


def _legacy_schema_v3_payload() -> dict:
    return _current_destination_scope_report().model_dump(mode="json")


def _bounded_review_report(*, missing: str | None = None) -> CatalogCurationReport:
    payload = _legacy_schema_v3_payload()
    if missing != "envelope":
        payload["review_evidence_envelope"] = [
            {
                "family_id": "official-booking-directory",
                "source_kind": "destination_booking",
                "source_urls": [payload["evidence"][0]["source_url"]],
                "candidate_kinds": ["stay_destination", "stay_base"],
            }
        ]
    if missing != "graph_impact":
        payload["entity_scope_assessments"][0]["graph_impact"] = "graph_blocking"
    return CatalogCurationReport.model_validate(payload)


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
    backlog_ref: str | None = None,
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
    if backlog_ref is not None:
        payload["entity_scope_assessments"][0]["backlog_ref"] = backlog_ref
    return payload


def _ski_area_boundary_payload(
    *,
    parent_ski_area_id: str | None = None,
    terrain_scope: str = "complete",
    connectivity_to_parent: str = "not_applicable",
    operational_scope: str = "unknown",
    weather_scope: str = "unknown",
    pass_scope: str = "none",
    provider_consensus: str = "separate",
    separation_value: str = "material",
    evidence_refs: list[str] | None = None,
) -> dict:
    return {
        "parent_ski_area_id": parent_ski_area_id,
        "terrain_scope": terrain_scope,
        "connectivity_to_parent": connectivity_to_parent,
        "operational_scope": operational_scope,
        "weather_scope": weather_scope,
        "pass_scope": pass_scope,
        "provider_consensus": provider_consensus,
        "separation_value": separation_value,
        "evidence_refs": evidence_refs or ["example-scope"],
    }


def _complete_new_ski_area_report_target(payload: dict, target_id: str) -> None:
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": target_id,
            "scope": "narrow",
            "required_field_paths": ["ski_area_id", "name"],
        }
    )
    payload["changes"].append(
        {
            "target_type": "ski_area",
            "target_id": target_id,
            "field_path": "ski_area_id",
            "before": None,
            "after": target_id,
            "trust_status": "estimated",
        }
    )
    payload["field_coverage"].extend(
        [
            {
                "target_type": "ski_area",
                "target_id": target_id,
                "field_path": "ski_area_id",
                "status": "changed",
            },
            {
                "target_type": "ski_area",
                "target_id": target_id,
                "field_path": "name",
                "status": "reviewed-no-change",
            },
        ]
    )


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
    assert "validity_windows" in CANONICAL_FIELD_PATHS["lift_pass_product"]
    assert "validity_windows" in NESTED_FIELD_PATH_ROOTS["lift_pass_product"]
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


def _pass_validity_report_payload() -> dict:
    windows = [
        {
            "season_label": "2026-2027",
            "start_date": "2026-12-05",
            "end_date": "2027-04-11",
            "status": "planned",
        }
    ]
    return {
        "report_schema_version": 3,
        "title": "Example pass validity review",
        "summary": "Adds the operator-published pass validity window.",
        "resulting_graph": {"focus_stay_destination_ids": ["example"]},
        "reviewed_targets": [
            {
                "target_type": "lift_pass_product",
                "target_id": "example-local-pass",
                "scope": "narrow",
                "required_field_paths": ["name", "validity_windows"],
            }
        ],
        "changes": [
            {
                "target_type": "lift_pass_product",
                "target_id": "example-local-pass",
                "field_path": "validity_windows",
                "before": [],
                "after": windows,
                "trust_status": "verified",
            }
        ],
        "field_coverage": [
            {
                "target_type": "lift_pass_product",
                "target_id": "example-local-pass",
                "field_path": "name",
                "status": "reviewed-no-change",
            },
            {
                "target_type": "lift_pass_product",
                "target_id": "example-local-pass",
                "field_path": "validity_windows",
                "status": "changed",
                "notes": (
                    "An empty list means no separate pass window was modeled; "
                    "it did not assert year-round validity."
                ),
            },
        ],
        "evidence": [
            {
                "evidence_id": "example-pass-scope",
                "target_type": "lift_pass_product",
                "target_id": "example-local-pass",
                "field_path": "name",
                "source_type": "official",
                "source_url": "https://operator.example.com/winter/tariff",
                "source_title": "Official operator winter tariff",
                "source_value": "Example Local Pass",
                "evidence_summary": "The tariff identifies the pass product.",
            },
            {
                "evidence_id": "example-pass-tariff",
                "target_type": "lift_pass_product",
                "target_id": "example-local-pass",
                "field_path": "validity_windows",
                "source_type": "official",
                "source_url": "https://operator.example.com/winter/tariff",
                "source_title": "Official operator winter tariff",
                "source_value": windows,
                "evidence_summary": (
                    "The operator tariff publishes the complete modeled window."
                ),
            },
        ],
        "entity_scope_assessments": [
            {
                "candidate_id": "example-local-pass",
                "candidate_name": "Example Local Pass",
                "candidate_kind": "lift_pass_product",
                "disposition": "represented",
                "signals": ["official_product_identity"],
                "evidence_refs": ["example-pass-scope"],
                "target_refs": [
                    {
                        "target_type": "lift_pass_product",
                        "target_id": "example-local-pass",
                    }
                ],
                "rationale": "The operator tariff identifies the pass product.",
            }
        ],
    }


def test_report_accepts_operator_evidence_for_complete_pass_validity_windows() -> None:
    report = CatalogCurationReport.model_validate(_pass_validity_report_payload())

    validate_catalog_curation_report(report, require_resulting_graph=True)


def test_report_requires_pass_validity_window_evidence() -> None:
    payload = _pass_validity_report_payload()
    payload["evidence"] = [payload["evidence"][0]]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="validity_windows: non-empty change requires official root-path evidence",
    ):
        validate_catalog_curation_report(report, require_resulting_graph=True)


def test_report_rejects_unrelated_nested_pass_validity_window_evidence() -> None:
    payload = _pass_validity_report_payload()
    payload["evidence"][1]["field_path"] = "validity_windows[0].start_date"
    payload["field_coverage"].append(
        {
            "target_type": "lift_pass_product",
            "target_id": "example-local-pass",
            "field_path": "validity_windows[0].start_date",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="validity_windows: non-empty change requires official root-path evidence",
    ):
        validate_catalog_curation_report(report, require_resulting_graph=True)


def test_report_rejects_non_official_pass_validity_window_evidence() -> None:
    payload = _pass_validity_report_payload()
    payload["evidence"][1]["source_type"] = "reviewed_editorial"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="validity_windows: non-empty change requires official root-path evidence",
    ):
        validate_catalog_curation_report(report, require_resulting_graph=True)


def test_report_allows_empty_pass_validity_windows_without_direct_evidence() -> None:
    payload = _pass_validity_report_payload()
    payload["changes"][0]["before"] = payload["changes"][0]["after"]
    payload["changes"][0]["after"] = []
    payload["changes"][0]["trust_status"] = "estimated"
    payload["evidence"] = [payload["evidence"][0]]
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report, require_resulting_graph=True)


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


def test_current_destination_boundary_policy_is_required_for_current_workflow() -> None:
    report = _destination_boundary_report(
        gate_names=(
            "complete_stay_market_scope",
            "independent_stay_market_ownership",
            "material_destination_level_separation_value",
        ),
        identity_signal="official_stay_market_treatment",
    )

    validate_catalog_curation_report(
        report,
        require_current_destination_policy=True,
    )


def test_legacy_destination_boundary_policy_remains_historically_loadable() -> None:
    report = _destination_boundary_report(
        gate_names=(
            "independent_stay_context",
            "independent_ski_access",
            "independent_recommendation_value",
        ),
        identity_signal="official_destination_treatment",
    )

    validate_catalog_curation_report(report)
    with pytest.raises(
        CatalogValidationError,
        match="current stay-market policy gates",
    ):
        validate_catalog_curation_report(
            report,
            require_current_destination_policy=True,
        )


def test_current_destination_policy_requires_stay_market_ownership_signal() -> None:
    report = _destination_boundary_report(
        gate_names=(
            "complete_stay_market_scope",
            "independent_stay_market_ownership",
            "material_destination_level_separation_value",
        ),
        identity_signal="local_pass",
        failure_route="stay_base",
    )

    with pytest.raises(
        CatalogValidationError,
        match="direct stay-market ownership signal assessment",
    ):
        validate_catalog_curation_report(
            report,
            require_current_destination_policy=True,
        )


def test_passing_stay_market_ownership_requires_official_evidence() -> None:
    report = _destination_boundary_report(
        gate_names=(
            "complete_stay_market_scope",
            "independent_stay_market_ownership",
            "material_destination_level_separation_value",
        ),
        identity_signal="official_stay_market_treatment",
        source_type="reviewed_editorial",
    )

    with pytest.raises(
        CatalogValidationError,
        match="passing stay-market ownership requires official evidence",
    ):
        validate_catalog_curation_report(
            report,
            require_current_destination_policy=True,
        )


def test_current_workflow_requires_retained_destination_boundary_assessment() -> None:
    report = _current_destination_scope_report()
    validate_catalog_curation_report(
        report,
        require_resulting_graph=True,
        require_current_destination_policy=True,
    )

    report.destination_boundary_assessments.clear()
    report.boundary_decision_targets.clear()

    with pytest.raises(
        CatalogValidationError,
        match="current stay destination requires a passing boundary assessment",
    ):
        validate_catalog_curation_report(
            report,
            require_resulting_graph=True,
            require_current_destination_policy=True,
        )


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


@pytest.mark.parametrize("disposition", ["deferred", "unresolved"])
def test_schema_two_deferred_scope_requires_a_backlog_ref(disposition: str) -> None:
    payload = _scope_report_payload(disposition=disposition)
    payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=f"{disposition} requires backlog_ref",
    ):
        validate_catalog_curation_report(report)


def test_schema_one_deferred_scope_remains_compatible_without_a_backlog_ref() -> None:
    payload = _scope_report_payload(disposition="deferred")
    payload["report_schema_version"] = 1
    payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "disposition",
    ["represented", "add_entity", "not_separate", "external_pass_context"],
)
def test_non_deferred_scope_forbids_a_backlog_ref(disposition: str) -> None:
    payload = _scope_report_payload(
        disposition=disposition,
        backlog_ref="docs/product-backlog.md#example-region-extension",
    )
    if disposition == "external_pass_context":
        payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=f"{disposition} forbids backlog_ref",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "backlog_ref",
    [
        "product-backlog.md#example-region-extension",
        "docs/product-backlog.md#Example-Region",
        "docs/product-backlog.md#example_region",
        "docs/product-backlog.md#",
    ],
)
def test_scope_assessment_rejects_noncanonical_backlog_ref(backlog_ref: str) -> None:
    payload = _scope_report_payload(
        disposition="deferred",
        backlog_ref=backlog_ref,
    )
    payload["entity_scope_assessments"][0]["target_refs"] = []

    with pytest.raises(ValidationError, match="canonical product backlog reference"):
        CatalogCurationReport.model_validate(payload)


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


def test_schema_three_ski_area_assessment_requires_boundary_contract() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 3
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "parent-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "parent-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="schema version 3 ski-area assessment requires boundary contract",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_ski_area_identity_without_owner_evidence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=["official_independent_identity", "child_scoped_terrain_metrics"],
        target_type="ski_area",
        target_id="identity-only-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload()
    )
    _complete_new_ski_area_report_target(payload, "identity-only-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="requires independent operations, weather, or full local pass evidence",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_connected_ski_area_requires_two_owner_categories() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "full_local_pass",
            "ski_connected_terrain",
        ],
        target_type="ski_area",
        target_id="connected-pass-only-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="connected",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="full_local",
            provider_consensus="aggregated",
        )
    )
    _complete_new_ski_area_report_target(payload, "connected-pass-only-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="connected ski area requires two independent owner categories",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_accepts_connected_area_with_pass_and_operations() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_status_or_schedule",
            "full_local_pass",
            "ski_connected_terrain",
        ],
        target_type="ski_area",
        target_id="connected-independent-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="connected",
            operational_scope="independent",
            pass_scope="full_local",
        )
    )
    _complete_new_ski_area_report_target(payload, "connected-independent-area")
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


def test_schema_three_accepts_transfer_area_with_independent_weather() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="transfer-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="transfer_required",
            weather_scope="independent",
        )
    )
    _complete_new_ski_area_report_target(payload, "transfer-area")
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


def test_schema_three_not_separate_requires_redundant_separation_value() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="sector",
            connectivity_to_parent="connected",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            separation_value="material",
        )
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "parent-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "parent-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="not_separate ski area requires redundant separation value",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_not_separate_requires_parent_target() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            terrain_scope="sector",
            connectivity_to_parent="not_applicable",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            separation_value="redundant",
        )
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "parent-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "parent-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="not_separate ski area requires its parent as the catalog target",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_separate_area_requires_resolved_parent_connectivity() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="unknown-connectivity-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="unknown",
            weather_scope="independent",
        )
    )
    _complete_new_ski_area_report_target(payload, "unknown-connectivity-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="separate ski area requires resolved parent connectivity",
    ):
        validate_catalog_curation_report(report)


def test_schema_two_independent_owner_signal_can_support_new_ski_area() -> None:
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


def test_ski_area_boundary_markdown_is_rendered() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="sector",
            connectivity_to_parent="connected",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            separation_value="redundant",
        )
    )
    report = CatalogCurationReport.model_validate(payload)

    rendered = render_catalog_curation_report_markdown(report)

    assert "## Ski-Area Boundary Assessments" in rendered
    assert "`parent-area`" in rendered
    assert "`parent_owned`" in rendered
    assert "`redundant`" in rendered


def test_schema_three_graph_is_required_only_when_requested() -> None:
    payload = _scope_report_payload()
    payload["report_schema_version"] = 3
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)
    with pytest.raises(
        CatalogValidationError,
        match="schema version 3 requires resulting_graph",
    ):
        validate_catalog_curation_report(report, require_resulting_graph=True)


def test_schema_v3_accepts_bounded_review_envelope_and_graph_impact() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    payload["review_evidence_envelope"] = [
        {
            "family_id": "official-booking-directory",
            "source_kind": "destination_booking",
            "source_urls": [payload["evidence"][0]["source_url"]],
            "candidate_kinds": ["stay_destination", "stay_base"],
        }
    ]
    payload["entity_scope_assessments"][0]["graph_impact"] = "graph_blocking"

    report = CatalogCurationReport.model_validate(payload)
    validate_catalog_curation_report(report, require_resulting_graph=True)

    assert report.review_evidence_envelope[0].family_id == (
        "official-booking-directory"
    )
    assert report.entity_scope_assessments[0].graph_impact == "graph_blocking"


def test_regional_followup_requires_deferred_or_unresolved_backlog_item() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    assessment = payload["entity_scope_assessments"][0]
    assessment["graph_impact"] = "regional_followup"

    with pytest.raises(
        CatalogValidationError,
        match="regional_followup requires deferred or unresolved backlog scope",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_review_envelope_rejects_unsafe_url() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    payload["review_evidence_envelope"] = [
        {
            "family_id": "official-booking-directory",
            "source_kind": "destination_booking",
            "source_urls": ["file:///tmp/source"],
            "candidate_kinds": ["stay_base"],
        }
    ]

    with pytest.raises(ValidationError):
        CatalogCurationReport.model_validate(payload)


def test_review_envelope_rejects_duplicate_family() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    family = {
        "family_id": "official-booking-directory",
        "source_kind": "destination_booking",
        "source_urls": [payload["evidence"][0]["source_url"]],
        "candidate_kinds": ["stay_base"],
    }
    payload["review_evidence_envelope"] = [family, family]

    with pytest.raises(
        CatalogValidationError,
        match="review_evidence_envelope contains a duplicate family",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_review_envelope_source_url_must_be_referenced_by_evidence() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    payload["review_evidence_envelope"] = [
        {
            "family_id": "official-booking-directory",
            "source_kind": "destination_booking",
            "source_urls": ["https://example.com/other-directory"],
            "candidate_kinds": ["stay_base"],
        }
    ]

    with pytest.raises(
        CatalogValidationError,
        match="review source URL is not referenced by evidence",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_legacy_schema_v3_remains_readable_without_review_inventory() -> None:
    report = CatalogCurationReport.model_validate(_legacy_schema_v3_payload())

    validate_catalog_curation_report(report)
    rendered = render_catalog_curation_report_markdown(
        report.model_copy(update={"resulting_graph": None})
    )

    assert "## Review Evidence Envelope" not in rendered
    assert "| Graph Impact |" not in rendered
    assert (
        "| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | "
        "Backlog | Rationale |"
    ) in rendered


@pytest.mark.parametrize("missing", ["envelope", "graph_impact"])
def test_finalized_maintainer_profile_requires_complete_review_inventory(
    missing: str,
) -> None:
    report = _bounded_review_report(missing=missing)

    with pytest.raises(CatalogValidationError, match="bounded review inventory"):
        validate_catalog_curation_report(
            report,
            require_bounded_review_inventory=True,
        )


def test_bounded_review_inventory_markdown_is_rendered() -> None:
    report = _bounded_review_report().model_copy(update={"resulting_graph": None})

    rendered = render_catalog_curation_report_markdown(report)

    assert "## Review Evidence Envelope" in rendered
    assert "| Graph Impact |" in rendered
    assert "`official-booking-directory`" in rendered
    assert "`graph_blocking`" in rendered


def test_resulting_graph_is_derived_from_the_current_catalog() -> None:
    catalog_payload = minimal_catalog_payload()
    add_terrain_domain(catalog_payload)
    catalog = CatalogSnapshot.model_validate(catalog_payload)
    payload = _scope_report_payload()
    payload.update(
        {
            "report_schema_version": 3,
            "resulting_graph": {
                "focus_stay_destination_ids": ["example"],
            },
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_resulting_graph(report, catalog, require=True)
    graph = render_catalog_resulting_graph_markdown(report, catalog)
    rendered_report = render_catalog_curation_report_markdown(report, catalog)

    assert graph.startswith("## Resulting Graph\n\n```mermaid\nflowchart LR\n")
    assert "Trip market<br/>Example Valley" in graph
    assert "Stay destination<br/>Example" in graph
    assert "Stay base<br/>Example Village" in graph
    assert "Ski area<br/>Example Area" in graph
    assert "Ski area<br/>Other Area" in graph
    assert "Terrain domain<br/>Example Domain" in graph
    assert "Lift pass<br/>Example Local Pass" in graph
    assert "valid " not in graph
    assert '|"access: walk via Example Gondola, 300 m"|' in graph
    assert '|"default pass"|' in graph
    assert graph in rendered_report


def test_resulting_graph_renders_explicit_pass_validity_windows() -> None:
    catalog_payload = minimal_catalog_payload()
    catalog_payload["lift_pass_products"][0]["validity_windows"] = [
        {
            "season_label": "2027 autumn",
            "start_date": "2027-10-02",
            "end_date": "2027-12-03",
            "status": "estimated",
        },
        {
            "season_label": "2026-2027",
            "start_date": "2026-12-05",
            "end_date": "2027-04-11",
            "status": "planned",
        },
    ]
    catalog = CatalogSnapshot.model_validate(catalog_payload)
    payload = _scope_report_payload()
    payload.update(
        {
            "report_schema_version": 3,
            "resulting_graph": {"focus_stay_destination_ids": ["example"]},
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    graph = render_catalog_resulting_graph_markdown(report, catalog)

    assert (
        "Lift pass<br/>Example Local Pass"
        "<br/>valid 2026-12-05 to 2027-04-11 (planned)"
        "<br/>valid 2027-10-02 to 2027-12-03 (estimated)"
    ) in graph


def test_resulting_graph_marks_changed_to_empty_pass_validity_windows() -> None:
    catalog = CatalogSnapshot.model_validate(minimal_catalog_payload())
    payload = _pass_validity_report_payload()
    payload["summary"] = "Removes the separately modeled pass window."
    payload["changes"][0]["before"] = payload["changes"][0]["after"]
    payload["changes"][0]["after"] = []
    payload["evidence"][1]["normalization_note"] = (
        "The reviewed report records removal of the prior modeled window."
    )
    report = CatalogCurationReport.model_validate(payload)

    graph = render_catalog_resulting_graph_markdown(report, catalog)

    assert (
        "Lift pass<br/>Example Local Pass<br/>no separate pass window modeled"
    ) in graph


def test_resulting_graph_rejects_unknown_focus_destination() -> None:
    catalog = CatalogSnapshot.model_validate(minimal_catalog_payload())
    payload = _scope_report_payload()
    payload.update(
        {
            "report_schema_version": 3,
            "resulting_graph": CatalogResultingGraph(
                focus_stay_destination_ids=["missing-destination"]
            ).model_dump(mode="json"),
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="unknown focus stay destination missing-destination",
    ):
        validate_catalog_resulting_graph(report, catalog, require=True)


def test_resulting_graph_requires_destinations_owning_reviewed_graph_targets() -> None:
    catalog_payload = minimal_catalog_payload()
    add_second_destination_base_with_access(catalog_payload)
    catalog = CatalogSnapshot.model_validate(catalog_payload)
    payload = _scope_report_payload()
    for collection in (
        "reviewed_targets",
        "changes",
        "field_coverage",
        "evidence",
    ):
        for item in payload[collection]:
            if item["target_type"] == "ski_area_access":
                item["target_id"] = "other-village--example-area"
    for assessment in payload["entity_scope_assessments"]:
        for target in assessment["target_refs"]:
            target["target_id"] = "other-village--example-area"
    payload.update(
        {
            "report_schema_version": 3,
            "resulting_graph": {
                "focus_stay_destination_ids": ["example"],
            },
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="missing required focus stay destination other-destination",
    ):
        validate_catalog_resulting_graph(report, catalog, require=True)

    report = report.model_copy(
        update={
            "resulting_graph": CatalogResultingGraph(
                focus_stay_destination_ids=["example", "other-destination"]
            )
        }
    )
    validate_catalog_resulting_graph(report, catalog, require=True)


def test_resulting_graph_excludes_linked_dependency_review_targets() -> None:
    catalog_payload = minimal_catalog_payload()
    add_second_destination_base_with_access(catalog_payload)
    catalog = CatalogSnapshot.model_validate(catalog_payload)
    payload = _scope_report_payload()
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area_access",
            "target_id": "other-village--example-area",
            "scope": "narrow",
            "required_field_paths": ["source_urls"],
            "resulting_graph_role": "linked_dependency",
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area_access",
            "target_id": "other-village--example-area",
            "field_path": "source_urls",
            "status": "reviewed-no-change",
        }
    )
    payload["evidence"].append(
        {
            "evidence_id": "other-access-scope",
            "target_type": "ski_area_access",
            "target_id": "other-village--example-area",
            "field_path": "source_urls",
            "source_type": "official",
            "source_url": "https://example.com/other-ski-map",
            "source_title": "Official linked ski map",
            "source_value": ["https://example.com/other-ski-map"],
            "evidence_summary": "Reviews a dependency owned outside this graph.",
        }
    )
    payload["entity_scope_assessments"].append(
        {
            "candidate_id": "other-village--example-area",
            "candidate_name": "Other access",
            "candidate_kind": "ski_area_access",
            "disposition": "deferred",
            "signals": ["direct_access_relationship"],
            "evidence_refs": ["other-access-scope"],
            "target_refs": [],
            "backlog_ref": "docs/product-backlog.md#other-access",
            "rationale": "The linked access belongs to a separately owned graph.",
        }
    )
    payload.update(
        {
            "report_schema_version": 3,
            "resulting_graph": {
                "focus_stay_destination_ids": ["example"],
            },
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_resulting_graph(report, catalog, require=True)
    rendered = render_catalog_curation_report_markdown(report, catalog)

    assert "Stay destination<br/>Other Destination" not in rendered
    assert "`linked_dependency`" in rendered


def test_linked_dependency_review_target_cannot_own_changes() -> None:
    payload = _scope_report_payload()
    payload["reviewed_targets"][0]["resulting_graph_role"] = "linked_dependency"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="linked_dependency reviewed target cannot own changes",
    ):
        validate_catalog_curation_report(report)


def test_linked_dependency_review_target_requires_narrow_scope() -> None:
    with pytest.raises(
        ValidationError,
        match="linked_dependency reviewed targets require narrow scope",
    ):
        CatalogReviewedTarget(
            target_type="ski_area",
            target_id="example-area",
            scope="full",
            resulting_graph_role="linked_dependency",
        )


def test_scope_assessment_markdown_renders_backlog_reference() -> None:
    payload = _scope_report_payload(
        disposition="deferred",
        backlog_ref="docs/product-backlog.md#example-region-extension",
    )
    payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    rendered = render_catalog_curation_report_markdown(report)

    assert "| Backlog |" in rendered
    assert "`docs/product-backlog.md#example-region-extension`" in rendered


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

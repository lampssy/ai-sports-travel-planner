import json
from copy import deepcopy
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
    CatalogSkiAreaTripConsequence,
    CatalogValidationError,
    CatalogWeatherRequestGeometry,
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

pytestmark = pytest.mark.db_free

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
                    "boundary_target_ids": ["example-access"],
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
    component_candidate_ids: list[str] | None = None,
    coordination_evidence_refs: list[str] | None = None,
    coordination_evidence_families: list[dict] | None = None,
    material_trip_consequences: list[dict] | None = None,
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
        "component_candidate_ids": component_candidate_ids or [],
        "coordination_evidence_refs": coordination_evidence_refs or [],
        "coordination_evidence_families": coordination_evidence_families or [],
        "material_trip_consequences": material_trip_consequences or [],
        "evidence_refs": evidence_refs or ["example-scope"],
    }


def _material_trip_consequence_payload(
    *,
    consequence_type: str = "stay_access_or_transfer",
    decision_effect: str = "selected_ski_area",
    comparison_basis: str = "parent_ski_area",
    comparison_target_id: str = "parent-area",
    durability_basis: str = "durable_access_geometry",
    evidence_refs: list[str] | None = None,
) -> dict:
    return {
        "consequence_type": consequence_type,
        "decision_effect": decision_effect,
        "comparison_basis": comparison_basis,
        "comparison_target_id": comparison_target_id,
        "durability_basis": durability_basis,
        "evidence_refs": evidence_refs or ["example-scope"],
        "rationale": (
            "Compared with the parent, this substantial primary ski-day option "
            "changes the selected ski area for a normal trip."
        ),
    }


def _add_stay_market_scope_assessment(
    payload: dict,
    *,
    destination_id: str,
    evidence_ref: str = "example-scope",
) -> None:
    payload["reviewed_targets"].append(
        {
            "target_type": "stay_destination",
            "target_id": destination_id,
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "stay_destination",
            "target_id": destination_id,
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    payload["entity_scope_assessments"].append(
        {
            "candidate_id": destination_id,
            "candidate_name": destination_id.replace("-", " ").title(),
            "candidate_kind": "stay_destination",
            "disposition": "represented",
            "signals": ["independent_stay_market"],
            "evidence_refs": [evidence_ref],
            "target_refs": [
                {"target_type": "stay_destination", "target_id": destination_id}
            ],
            "rationale": "The official source identifies the stay market.",
        }
    )


def _add_parent_ski_area_scope_assessment(
    payload: dict,
    *,
    parent_id: str = "parent-area",
    destination_id: str = "example-destination",
    evidence_ref: str = "example-scope",
) -> None:
    _add_stay_market_scope_assessment(
        payload,
        destination_id=destination_id,
        evidence_ref=evidence_ref,
    )
    parent_candidate_id = f"{parent_id}-boundary"
    payload["entity_scope_assessments"].append(
        {
            "candidate_id": parent_candidate_id,
            "candidate_name": parent_id.replace("-", " ").title(),
            "candidate_kind": "ski_area",
            "disposition": "represented",
            "signals": [
                "official_independent_identity",
                "independent_weather_presentation",
            ],
            "evidence_refs": [evidence_ref],
            "target_refs": [{"target_type": "ski_area", "target_id": parent_id}],
            "rationale": "The official source identifies the parent ski area.",
            "ski_area_boundary": _ski_area_boundary_payload(
                weather_scope="independent",
                material_trip_consequences=[
                    _material_trip_consequence_payload(
                        consequence_type="weather_or_season",
                        decision_effect="conditions_evidence_profile",
                        comparison_basis="stay_market_baseline",
                        comparison_target_id=destination_id,
                        durability_basis="recurring_season_pattern",
                        evidence_refs=[evidence_ref],
                    )
                ],
                evidence_refs=[evidence_ref],
            ),
        }
    )
    for evidence in payload["evidence"]:
        if evidence["evidence_id"] == evidence_ref:
            evidence.setdefault("boundary_target_ids", []).append(parent_candidate_id)
    _complete_existing_ski_area_report_target(payload, parent_id)


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


def _complete_existing_ski_area_report_target(payload: dict, target_id: str) -> None:
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": target_id,
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": target_id,
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )


_COORDINATED_EVIDENCE_FAMILY_REFS = {
    "complete_terrain_lift_inventory": "coordination-inventory",
    "exhaustive_component_operator_roster": "coordination-roster",
    "component_addressable_operations_status": "coordination-operations",
    "every_component_pass_coverage": "coordination-pass",
    "direct_component_parent_assignment": "coordination-assignment",
}


def _coordinated_ski_area_report_payload() -> dict:
    parent_id = "coordinated-area"
    component_ids = ["operator-a-sector", "operator-b-sector"]
    coordination_evidence_refs = list(_COORDINATED_EVIDENCE_FAMILY_REFS.values())
    coordination_evidence_families = [
        {
            "family": family,
            "evidence_refs": [evidence_id],
            "covered_component_candidate_ids": component_ids.copy(),
        }
        for family, evidence_id in _COORDINATED_EVIDENCE_FAMILY_REFS.items()
    ]
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_complete_lift_inventory",
            "coordinated_status_or_schedule",
            "common_full_coverage_pass",
        ],
        target_type="ski_area",
        target_id=parent_id,
    )
    payload["report_schema_version"] = 3
    payload["evidence"] = [
        {
            "evidence_id": evidence_id,
            "target_type": "ski_area_access",
            "target_id": "example-village--example-area",
            "field_path": "source_urls",
            "source_type": "official",
            "source_url": f"https://example.com/{evidence_id}",
            "source_title": family.replace("_", " ").title(),
            "source_value": [f"https://example.com/{evidence_id}"],
            "evidence_summary": f"Official evidence for {family}.",
        }
        for family, evidence_id in _COORDINATED_EVIDENCE_FAMILY_REFS.items()
    ]
    parent = payload["entity_scope_assessments"][0]
    parent["evidence_refs"] = coordination_evidence_refs.copy()
    parent["ski_area_boundary"] = _ski_area_boundary_payload(
        operational_scope="coordinated",
        weather_scope="unknown",
        pass_scope="shared_only",
        provider_consensus="aggregated",
        component_candidate_ids=component_ids.copy(),
        coordination_evidence_refs=coordination_evidence_refs.copy(),
        coordination_evidence_families=coordination_evidence_families,
        evidence_refs=coordination_evidence_refs.copy(),
    )
    _complete_new_ski_area_report_target(payload, parent_id)
    for component_id in component_ids:
        payload["entity_scope_assessments"].append(
            {
                "candidate_id": component_id,
                "candidate_name": component_id.replace("-", " ").title(),
                "candidate_kind": "ski_area",
                "disposition": "not_separate",
                "signals": ["official_map_sector", "ski_connected_terrain"],
                "evidence_refs": ["coordination-assignment"],
                "target_refs": [{"target_type": "ski_area", "target_id": parent_id}],
                "rationale": "The complete coordinated sources assign this sector.",
                "ski_area_boundary": _ski_area_boundary_payload(
                    parent_ski_area_id=parent_id,
                    terrain_scope="sector",
                    connectivity_to_parent="connected",
                    operational_scope="coordinated",
                    weather_scope="parent_owned",
                    pass_scope="shared_only",
                    provider_consensus="aggregated",
                    separation_value="redundant",
                    evidence_refs=["coordination-assignment"],
                ),
            }
        )
    return payload


def _coordinated_parent(payload: dict) -> dict:
    return payload["entity_scope_assessments"][0]


def _upgrade_coordinated_payload_to_schema_four(payload: dict) -> None:
    payload["report_schema_version"] = 4
    parent = _coordinated_parent(payload)
    for family in parent["ski_area_boundary"]["coordination_evidence_families"]:
        if family["family"] == "direct_component_parent_assignment":
            family["family"] = "component_parent_assignment"
    parent["ski_area_boundary"]["material_trip_consequences"] = [
        _material_trip_consequence_payload(
            consequence_type="pass_price_or_coverage",
            decision_effect="lift_pass_choice",
            comparison_basis="stay_market_baseline",
            comparison_target_id="example-destination",
            durability_basis="published_product_contract",
            evidence_refs=["coordination-pass"],
        )
    ]
    _add_stay_market_scope_assessment(
        payload,
        destination_id="example-destination",
        evidence_ref="coordination-inventory",
    )
    candidate_ids = [
        assessment["candidate_id"] for assessment in payload["entity_scope_assessments"]
    ]
    for evidence in payload["evidence"]:
        evidence["boundary_target_ids"] = candidate_ids.copy()


def _sync_coordination_evidence_refs(parent: dict) -> None:
    parent["ski_area_boundary"]["coordination_evidence_refs"] = [
        evidence_ref
        for family in parent["ski_area_boundary"]["coordination_evidence_families"]
        for evidence_ref in family["evidence_refs"]
    ]


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
        "weather_sampling_status",
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


def test_boundary_evidence_names_the_missing_candidate_metadata_field() -> None:
    report = _destination_boundary_report(
        gate_names=(
            "complete_stay_market_scope",
            "independent_stay_market_ownership",
            "material_destination_level_separation_value",
        ),
        identity_signal="official_stay_market_treatment",
    )
    report.evidence[0].boundary_target_ids.clear()

    with pytest.raises(
        CatalogValidationError,
        match=(
            "example: evidence example-stay-market must include example in "
            "boundary_target_ids"
        ),
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


def test_schema_three_rejects_coordinated_weather_scope() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(weather_scope="coordinated")
    )

    with pytest.raises(ValidationError, match="weather_scope"):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_defaults_coordination_metadata_for_legacy_boundary() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 3
    boundary_payload = _ski_area_boundary_payload(
        parent_ski_area_id="parent-area",
        terrain_scope="sector",
        connectivity_to_parent="connected",
        operational_scope="parent_owned",
        weather_scope="parent_owned",
        pass_scope="shared_only",
        provider_consensus="aggregated",
        separation_value="redundant",
    )
    del boundary_payload["component_candidate_ids"]
    del boundary_payload["coordination_evidence_refs"]
    del boundary_payload["coordination_evidence_families"]
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = boundary_payload
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
    boundary = report.entity_scope_assessments[0].ski_area_boundary

    validate_catalog_curation_report(report)
    assert boundary is not None
    assert boundary.component_candidate_ids == []
    assert boundary.coordination_evidence_refs == []
    assert boundary.coordination_evidence_families == []

    explicit_payload = json.loads(json.dumps(payload))
    explicit_boundary = explicit_payload["entity_scope_assessments"][0][
        "ski_area_boundary"
    ]
    explicit_boundary["component_candidate_ids"] = []
    explicit_boundary["coordination_evidence_refs"] = []
    explicit_boundary["coordination_evidence_families"] = []
    explicit_report = CatalogCurationReport.model_validate(explicit_payload)

    assert render_catalog_curation_report_markdown(
        report
    ) == render_catalog_curation_report_markdown(explicit_report)


def test_schema_three_rejects_coordination_metadata_on_independent_boundary() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            operational_scope="independent",
            component_candidate_ids=["operator-a", "operator-b"],
            coordination_evidence_refs=["example-scope"],
        )
    )

    with pytest.raises(
        ValidationError,
        match="coordination metadata requires operational_scope=coordinated",
    ):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_rejects_unowned_coordination_evidence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            operational_scope="coordinated",
            component_candidate_ids=["operator-a", "operator-b"],
            coordination_evidence_refs=["missing-coordination-evidence"],
            coordination_evidence_families=[
                {
                    "family": "direct_component_parent_assignment",
                    "evidence_refs": ["missing-coordination-evidence"],
                    "covered_component_candidate_ids": [
                        "operator-a",
                        "operator-b",
                    ],
                }
            ],
        )
    )

    with pytest.raises(
        ValidationError,
        match="coordination_evidence_refs must be included in evidence_refs",
    ):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_accepts_complete_coordinated_parent() -> None:
    report = CatalogCurationReport.model_validate(
        _coordinated_ski_area_report_payload()
    )

    validate_catalog_curation_report(report)


def test_schema_three_rejects_coordination_aggregate_outside_family_union() -> None:
    payload = _coordinated_ski_area_report_payload()
    boundary = _coordinated_parent(payload)["ski_area_boundary"]
    boundary["coordination_evidence_refs"].remove("coordination-roster")

    with pytest.raises(
        ValidationError,
        match=(
            "coordination_evidence_refs must equal the union of coordination "
            "evidence family refs"
        ),
    ):
        CatalogCurationReport.model_validate(payload)


@pytest.mark.parametrize("missing_family", _COORDINATED_EVIDENCE_FAMILY_REFS)
def test_schema_three_coordinated_parent_requires_every_evidence_family(
    missing_family: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    parent = _coordinated_parent(payload)
    families = parent["ski_area_boundary"]["coordination_evidence_families"]
    parent["ski_area_boundary"]["coordination_evidence_families"] = [
        family for family in families if family["family"] != missing_family
    ]
    _sync_coordination_evidence_refs(parent)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=f"coordinated ski area requires evidence family {missing_family}",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_pass_only_coordination_evidence() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent = _coordinated_parent(payload)
    pass_family = next(
        family
        for family in parent["ski_area_boundary"]["coordination_evidence_families"]
        if family["family"] == "every_component_pass_coverage"
    )
    parent["ski_area_boundary"]["coordination_evidence_families"] = [pass_family]
    parent["ski_area_boundary"]["coordination_evidence_refs"] = ["coordination-pass"]
    parent["ski_area_boundary"]["evidence_refs"] = ["coordination-pass"]
    parent["evidence_refs"] = ["coordination-pass"]
    for child in payload["entity_scope_assessments"][1:]:
        child["evidence_refs"] = ["coordination-pass"]
        child["ski_area_boundary"]["evidence_refs"] = ["coordination-pass"]
    payload["evidence"] = [
        evidence
        for evidence in payload["evidence"]
        if evidence["evidence_id"] == "coordination-pass"
    ]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "coordinated ski area requires evidence family "
            "complete_terrain_lift_inventory"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_non_official_coordination_family_evidence() -> None:
    payload = _coordinated_ski_area_report_payload()
    roster_evidence = next(
        evidence
        for evidence in payload["evidence"]
        if evidence["evidence_id"] == "coordination-roster"
    )
    roster_evidence["source_type"] = "reviewed_editorial"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "evidence family exhaustive_component_operator_roster requires "
            "official evidence coordination-roster"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_requires_family_evidence_in_scope_refs() -> None:
    payload = _coordinated_ski_area_report_payload()
    _coordinated_parent(payload)["evidence_refs"].remove("coordination-roster")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="ski-area boundary evidence must also appear in scope evidence_refs",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "family_name",
    [
        "component_addressable_operations_status",
        "every_component_pass_coverage",
    ],
)
def test_schema_three_rejects_incomplete_component_family_coverage(
    family_name: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    family = next(
        family
        for family in _coordinated_parent(payload)["ski_area_boundary"][
            "coordination_evidence_families"
        ]
        if family["family"] == family_name
    )
    family["covered_component_candidate_ids"] = ["operator-a-sector"]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            f"evidence family {family_name} must cover exactly coordinated "
            "components; missing=operator-b-sector"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_extra_component_family_coverage() -> None:
    payload = _coordinated_ski_area_report_payload()
    inventory_family = _coordinated_parent(payload)["ski_area_boundary"][
        "coordination_evidence_families"
    ][0]
    inventory_family["covered_component_candidate_ids"].append("operator-c-sector")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "evidence family complete_terrain_lift_inventory must cover exactly "
            "coordinated components; missing=none; extra=operator-c-sector"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_unresolved_component_assignment_coverage() -> None:
    payload = _coordinated_ski_area_report_payload()
    assignment_family = next(
        family
        for family in _coordinated_parent(payload)["ski_area_boundary"][
            "coordination_evidence_families"
        ]
        if family["family"] == "direct_component_parent_assignment"
    )
    assignment_family["covered_component_candidate_ids"] = ["operator-a-sector"]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "evidence family direct_component_parent_assignment must cover "
            "exactly coordinated components; missing=operator-b-sector"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_schema_four_component_assignment_family() -> None:
    payload = _coordinated_ski_area_report_payload()
    assignment_family = next(
        family
        for family in _coordinated_parent(payload)["ski_area_boundary"][
            "coordination_evidence_families"
        ]
        if family["family"] == "direct_component_parent_assignment"
    )
    assignment_family["family"] = "component_parent_assignment"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "coordinated ski area requires evidence family "
            "direct_component_parent_assignment"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_one_rejects_coordinated_scope_and_metadata() -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["report_schema_version"] = 1
    _coordinated_parent(payload)["disposition"] = "represented"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires report schema version 3",
    ):
        validate_catalog_curation_report(report)


def test_schema_two_rejects_coordinated_scope_and_metadata() -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["report_schema_version"] = 2
    _coordinated_parent(payload)["disposition"] = "represented"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires report schema version 3",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_child_rejects_parent_metadata() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent = _coordinated_parent(payload)
    child = payload["entity_scope_assessments"][1]
    child_boundary = child["ski_area_boundary"]
    child_boundary["component_candidate_ids"] = parent["ski_area_boundary"][
        "component_candidate_ids"
    ]
    child_boundary["coordination_evidence_refs"] = parent["ski_area_boundary"][
        "coordination_evidence_refs"
    ]
    child_boundary["coordination_evidence_families"] = parent["ski_area_boundary"][
        "coordination_evidence_families"
    ]
    child_boundary["evidence_refs"] = parent["ski_area_boundary"]["evidence_refs"]
    child["evidence_refs"] = parent["evidence_refs"]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "operator-a-sector: coordination metadata is only valid on a "
            "represented or added parent"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_requires_coordination_evidence_refs() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent_boundary = _coordinated_parent(payload)["ski_area_boundary"]
    parent_boundary["coordination_evidence_refs"] = []
    parent_boundary["coordination_evidence_families"] = []
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires coordination evidence refs",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "missing_signal",
    [
        "official_complete_lift_inventory",
        "coordinated_status_or_schedule",
        "common_full_coverage_pass",
    ],
)
def test_schema_three_coordinated_parent_requires_every_signal(
    missing_signal: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    parent = payload["entity_scope_assessments"][0]
    parent["signals"].remove(missing_signal)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=f"coordinated ski area requires signal {missing_signal}",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize("pass_scope", ["limited", "none", "unknown"])
def test_schema_three_coordinated_parent_requires_full_component_pass(
    pass_scope: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["entity_scope_assessments"][0]["ski_area_boundary"]["pass_scope"] = (
        pass_scope
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires pass_scope=full_local or shared_only",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_requires_two_components() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent_boundary = payload["entity_scope_assessments"][0]["ski_area_boundary"]
    parent_boundary["component_candidate_ids"] = ["operator-a-sector"]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires at least two component candidates",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_rejects_missing_component_assessment() -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["entity_scope_assessments"] = [
        assessment
        for assessment in payload["entity_scope_assessments"]
        if assessment["candidate_id"] != "operator-b-sector"
    ]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated component operator-b-sector has no scope assessment",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_rejects_self_membership() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent = _coordinated_parent(payload)
    parent_boundary = parent["ski_area_boundary"]
    component_ids = [parent["candidate_id"], "operator-a-sector"]
    parent_boundary["component_candidate_ids"] = component_ids
    for family in parent_boundary["coordination_evidence_families"]:
        family["covered_component_candidate_ids"] = component_ids
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated parent cannot list itself as a component",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_rejects_duplicate_component_ids() -> None:
    payload = _coordinated_ski_area_report_payload()
    _coordinated_parent(payload)["ski_area_boundary"]["component_candidate_ids"] = [
        "operator-a-sector",
        "operator-a-sector",
    ]

    with pytest.raises(
        ValidationError,
        match="ski-area boundary component_candidate_ids must be unique",
    ):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_rejects_multiple_coordinated_candidates_for_one_parent() -> None:
    payload = _coordinated_ski_area_report_payload()
    duplicate_parent = json.loads(json.dumps(_coordinated_parent(payload)))
    duplicate_parent["candidate_id"] = "duplicate-parent-assessment"
    duplicate_parent["candidate_name"] = "Duplicate Parent Assessment"
    payload["entity_scope_assessments"].append(duplicate_parent)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "ski_area:coordinated-area: coordinated parent is represented by "
            "multiple candidates"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_targets_exactly_one_catalog_area() -> None:
    payload = _coordinated_ski_area_report_payload()
    _coordinated_parent(payload)["target_refs"].append(
        {"target_type": "ski_area", "target_id": "other-area"}
    )
    _complete_new_ski_area_report_target(payload, "other-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area must target exactly one catalog ski area",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    ("field_path", "value", "message"),
    [
        ("disposition", "represented", "must use disposition=not_separate"),
        (
            "ski_area_boundary.operational_scope",
            "parent_owned",
            "must use operational_scope=coordinated",
        ),
        (
            "ski_area_boundary.parent_ski_area_id",
            "other-area",
            "must name coordinated parent coordinated-area",
        ),
        (
            "ski_area_boundary.weather_scope",
            "independent",
            "cannot retain independent weather scope",
        ),
    ],
)
def test_schema_three_coordinated_component_must_close_to_parent(
    field_path: str,
    value: str,
    message: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    component = payload["entity_scope_assessments"][1]
    target = component
    segments = field_path.split(".")
    for segment in segments[:-1]:
        target = target[segment]
    target[segments[-1]] = value
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match=message):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_component_targets_only_parent_catalog_area() -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["entity_scope_assessments"][1]["target_refs"] = [
        {"target_type": "ski_area", "target_id": "other-area"}
    ]
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "other-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "other-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="must target coordinated parent ski_area:coordinated-area",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_independently_viable_coordinated_component() -> None:
    payload = _coordinated_ski_area_report_payload()
    component = payload["entity_scope_assessments"][1]
    component["signals"] = [
        "official_independent_identity",
        "separate_operator",
        "independent_status_or_schedule",
        "full_local_pass",
        "ski_connected_terrain",
    ]
    component_boundary = component["ski_area_boundary"]
    component_boundary["terrain_scope"] = "complete"
    component_boundary["pass_scope"] = "full_local"
    component_boundary["provider_consensus"] = "separate"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "operator-a-sector: coordinated component independently satisfies "
            "ordinary separate-ski-area evidence gates"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_accepts_connected_coordinated_component_with_only_pass() -> None:
    payload = _coordinated_ski_area_report_payload()
    component = payload["entity_scope_assessments"][1]
    component["signals"] = [
        "official_independent_identity",
        "full_local_pass",
        "ski_connected_terrain",
    ]
    component_boundary = component["ski_area_boundary"]
    component_boundary["terrain_scope"] = "complete"
    component_boundary["pass_scope"] = "full_local"
    component_boundary["provider_consensus"] = "separate"
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


def test_schema_three_rejects_transfer_component_with_independent_operations() -> None:
    payload = _coordinated_ski_area_report_payload()
    component = payload["entity_scope_assessments"][1]
    component["signals"] = [
        "official_independent_identity",
        "separate_operator",
        "disconnected_terrain",
    ]
    component_boundary = component["ski_area_boundary"]
    component_boundary["terrain_scope"] = "complete"
    component_boundary["connectivity_to_parent"] = "transfer_required"
    component_boundary["provider_consensus"] = "separate"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "operator-a-sector: coordinated component independently satisfies "
            "ordinary separate-ski-area evidence gates"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_four_allows_coordinated_component_without_trip_consequence() -> None:
    payload = _coordinated_ski_area_report_payload()
    _upgrade_coordinated_payload_to_schema_four(payload)
    component = payload["entity_scope_assessments"][1]
    component["signals"] = [
        "official_independent_identity",
        "separate_operator",
        "independent_status_or_schedule",
        "full_local_pass",
        "ski_connected_terrain",
    ]
    component_boundary = component["ski_area_boundary"]
    component_boundary["terrain_scope"] = "complete"
    component_boundary["pass_scope"] = "full_local"
    component_boundary["provider_consensus"] = "separate"

    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_legacy_direct_parent_assignment_family() -> None:
    payload = _coordinated_ski_area_report_payload()
    _upgrade_coordinated_payload_to_schema_four(payload)
    parent = _coordinated_parent(payload)
    assignment_family = next(
        family
        for family in parent["ski_area_boundary"]["coordination_evidence_families"]
        if family["family"] == "component_parent_assignment"
    )
    assignment_family["family"] = "direct_component_parent_assignment"
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "coordinated ski area requires evidence family component_parent_assignment"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_four_rejects_coordinated_component_when_all_three_gates_pass() -> None:
    payload = _coordinated_ski_area_report_payload()
    _upgrade_coordinated_payload_to_schema_four(payload)
    component = payload["entity_scope_assessments"][1]
    component["signals"] = [
        "official_independent_identity",
        "separate_operator",
        "independent_status_or_schedule",
        "full_local_pass",
        "ski_connected_terrain",
    ]
    component["evidence_refs"].append("coordination-pass")
    component_boundary = component["ski_area_boundary"]
    component_boundary["terrain_scope"] = "complete"
    component_boundary["pass_scope"] = "full_local"
    component_boundary["provider_consensus"] = "separate"
    component_boundary["separation_value"] = "material"
    component_boundary["evidence_refs"].append("coordination-pass")
    component_boundary["material_trip_consequences"] = [
        _material_trip_consequence_payload(
            consequence_type="pass_price_or_coverage",
            decision_effect="lift_pass_choice",
            durability_basis="published_product_contract",
            evidence_refs=["coordination-pass"],
        )
    ]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "operator-a-sector: coordinated component independently satisfies "
            "ordinary separate-ski-area evidence gates"
        ),
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_component_cannot_belong_to_two_parents() -> None:
    payload = _coordinated_ski_area_report_payload()
    first_parent = payload["entity_scope_assessments"][0]
    second_parent = json.loads(json.dumps(first_parent))
    second_parent["candidate_id"] = "second-coordinated-area"
    second_parent["candidate_name"] = "Second Coordinated Area"
    second_parent["target_refs"] = [
        {"target_type": "ski_area", "target_id": "second-coordinated-area"}
    ]
    second_parent["ski_area_boundary"]["component_candidate_ids"] = [
        "operator-a-sector",
        "operator-c-sector",
    ]
    payload["entity_scope_assessments"].append(second_parent)
    _complete_new_ski_area_report_target(payload, "second-coordinated-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated component operator-a-sector belongs to multiple parents",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_unlisted_coordinated_child() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent_boundary = payload["entity_scope_assessments"][0]["ski_area_boundary"]
    parent_boundary["component_candidate_ids"] = [
        "operator-a-sector",
        "replacement-sector",
    ]
    replacement = json.loads(json.dumps(payload["entity_scope_assessments"][2]))
    replacement["candidate_id"] = "replacement-sector"
    replacement["candidate_name"] = "Replacement Sector"
    payload["entity_scope_assessments"].append(replacement)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "coordinated child operator-b-sector is not listed by parent "
            "coordinated-area"
        ),
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


def test_schema_four_requires_material_trip_consequence_for_separate_area() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    _add_parent_ski_area_scope_assessment(payload)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="separate ski area requires a material trip consequence",
    ):
        validate_catalog_curation_report(report)


def test_schema_four_accepts_separate_area_with_material_trip_consequence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    _add_parent_ski_area_scope_assessment(payload)

    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_accepts_root_area_with_stay_market_comparison() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="root-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    consequence_type="weather_or_season",
                    decision_effect="conditions_evidence_profile",
                    comparison_basis="stay_market_baseline",
                    comparison_target_id="example-destination",
                    durability_basis="recurring_season_pattern",
                )
            ],
        )
    )
    _add_stay_market_scope_assessment(
        payload,
        destination_id="example-destination",
    )
    _complete_existing_ski_area_report_target(payload, "root-area")

    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_parent_comparison_for_root_area() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="root-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            weather_scope="independent",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_existing_ski_area_report_target(payload, "root-area")

    with pytest.raises(
        CatalogValidationError,
        match="parent_ski_area comparison requires parent_ski_area_id",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_parent_comparison_target_mismatch() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="child-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    comparison_target_id="different-parent"
                )
            ],
        )
    )
    _complete_existing_ski_area_report_target(payload, "child-area")

    with pytest.raises(
        CatalogValidationError,
        match="parent_ski_area comparison target must equal parent_ski_area_id",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_unassessed_parent_comparison_target() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="child-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="ghost-parent",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(comparison_target_id="ghost-parent")
            ],
        )
    )
    _complete_existing_ski_area_report_target(payload, "child-area")

    with pytest.raises(
        CatalogValidationError,
        match=(
            "parent comparison target ghost-parent must resolve to one "
            "represented or added ski area"
        ),
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_self_parent_comparison_target() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="self-parent-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="self-parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    comparison_target_id="self-parent-area"
                )
            ],
        )
    )
    _complete_existing_ski_area_report_target(payload, "self-parent-area")

    with pytest.raises(
        CatalogValidationError,
        match="parent comparison must name a different ski-area target",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_stay_market_comparison_for_child_area() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="child-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    comparison_basis="stay_market_baseline",
                    comparison_target_id="example-destination",
                )
            ],
        )
    )
    _add_stay_market_scope_assessment(
        payload,
        destination_id="example-destination",
    )
    _complete_existing_ski_area_report_target(payload, "child-area")

    with pytest.raises(
        CatalogValidationError,
        match="stay_market_baseline comparison forbids parent_ski_area_id",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_unrepresented_stay_market_comparison_target() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="root-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    consequence_type="weather_or_season",
                    decision_effect="conditions_evidence_profile",
                    comparison_basis="stay_market_baseline",
                    comparison_target_id="missing-destination",
                    durability_basis="recurring_season_pattern",
                )
            ],
        )
    )
    _complete_existing_ski_area_report_target(payload, "root-area")

    with pytest.raises(
        CatalogValidationError,
        match=(
            "stay-market comparison target missing-destination must resolve "
            "to one represented or added stay destination"
        ),
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_resolves_stay_market_comparison_by_catalog_target_id() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="root-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    consequence_type="weather_or_season",
                    decision_effect="conditions_evidence_profile",
                    comparison_basis="stay_market_baseline",
                    comparison_target_id="destination-candidate-alias",
                    durability_basis="recurring_season_pattern",
                )
            ],
        )
    )
    _complete_existing_ski_area_report_target(payload, "root-area")
    _add_stay_market_scope_assessment(
        payload,
        destination_id="actual-destination-id",
    )
    payload["entity_scope_assessments"][-1]["candidate_id"] = (
        "destination-candidate-alias"
    )

    with pytest.raises(
        CatalogValidationError,
        match=(
            "stay-market comparison target destination-candidate-alias must "
            "resolve to one represented or added stay destination"
        ),
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_two_stay_market_roots_for_one_destination() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="root-one",
    )
    payload["report_schema_version"] = 4
    consequence = _material_trip_consequence_payload(
        consequence_type="weather_or_season",
        decision_effect="conditions_evidence_profile",
        comparison_basis="stay_market_baseline",
        comparison_target_id="example-destination",
        durability_basis="recurring_season_pattern",
    )
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            weather_scope="independent",
            material_trip_consequences=[consequence],
        )
    )
    second = deepcopy(payload["entity_scope_assessments"][0])
    second["candidate_id"] = "root-two"
    second["candidate_name"] = "Root Two"
    second["target_refs"] = [{"target_type": "ski_area", "target_id": "root-two"}]
    payload["entity_scope_assessments"].append(second)
    _complete_existing_ski_area_report_target(payload, "root-one")
    _complete_existing_ski_area_report_target(payload, "root-two")
    _add_stay_market_scope_assessment(
        payload,
        destination_id="example-destination",
    )

    with pytest.raises(
        CatalogValidationError,
        match="stay-market comparison must identify the sole root ski area",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_unknown_sibling_comparison_target() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="child-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(
                    comparison_basis="sibling_ski_area",
                    comparison_target_id="missing-sibling",
                )
            ],
        )
    )
    _complete_existing_ski_area_report_target(payload, "child-area")

    with pytest.raises(
        CatalogValidationError,
        match="unknown sibling comparison target missing-sibling",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_sibling_with_different_parent() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="child-one",
    )
    payload["report_schema_version"] = 4
    first = payload["entity_scope_assessments"][0]
    first["ski_area_boundary"] = _ski_area_boundary_payload(
        parent_ski_area_id="parent-one",
        connectivity_to_parent="disconnected",
        weather_scope="independent",
        material_trip_consequences=[
            _material_trip_consequence_payload(
                comparison_basis="sibling_ski_area",
                comparison_target_id="child-two",
            )
        ],
    )
    second = deepcopy(first)
    second["candidate_id"] = "child-two"
    second["candidate_name"] = "Child Two"
    second["target_refs"] = [{"target_type": "ski_area", "target_id": "child-two"}]
    second["ski_area_boundary"]["parent_ski_area_id"] = "parent-two"
    second["ski_area_boundary"]["material_trip_consequences"][0][
        "comparison_target_id"
    ] = "child-one"
    payload["entity_scope_assessments"].append(second)
    _complete_existing_ski_area_report_target(payload, "child-one")
    _complete_existing_ski_area_report_target(payload, "child-two")

    with pytest.raises(
        CatalogValidationError,
        match="sibling comparison target child-two must share parent_ski_area_id",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_external_pass_context_for_ski_area() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="external_pass_context",
        signals=["official_independent_identity"],
        target_type="ski_area",
        target_id="external-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["target_refs"] = []
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(separation_value="unresolved")
    )

    with pytest.raises(
        CatalogValidationError,
        match="ski-area candidate forbids external_pass_context",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_not_separate_can_retain_materiality_when_terrain_gate_fails() -> (
    None
):
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=[
            "official_map_sector",
            "independent_status_or_schedule",
            "distinct_access",
        ],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="sector",
            connectivity_to_parent="connected",
            operational_scope="independent",
            weather_scope="parent_owned",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            separation_value="material",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _add_parent_ski_area_scope_assessment(payload)

    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_not_separate_candidate_that_passes_all_three_gates() -> (
    None
):
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=[
            "official_independent_identity",
            "independent_status_or_schedule",
            "independent_weather_presentation",
            "disconnected_terrain",
            "distinct_access",
        ],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            operational_scope="independent",
            weather_scope="independent",
            pass_scope="shared_only",
            separation_value="material",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _add_parent_ski_area_scope_assessment(payload)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "not_separate candidate independently satisfies ordinary "
            "separate-ski-area gates"
        ),
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize("schema_version", [3, 4])
def test_schema_four_inherits_schema_three_connected_owner_gate(
    schema_version: int,
) -> None:
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
    payload["report_schema_version"] = schema_version
    consequences = (
        [
            _material_trip_consequence_payload(
                consequence_type="pass_price_or_coverage",
                decision_effect="lift_pass_choice",
                durability_basis="published_product_contract",
            )
        ]
        if schema_version == 4
        else []
    )
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="connected",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="full_local",
            provider_consensus="aggregated",
            material_trip_consequences=consequences,
        )
    )
    _complete_new_ski_area_report_target(payload, "connected-pass-only-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="connected ski area requires two independent owner categories",
    ):
        validate_catalog_curation_report(report)


def test_schema_four_rejects_unknown_material_trip_consequence_evidence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["evidence_refs"].append("missing-proof")
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[
                _material_trip_consequence_payload(evidence_refs=["missing-proof"])
            ],
            evidence_refs=["example-scope", "missing-proof"],
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="unknown material trip consequence evidence missing-proof",
    ):
        validate_catalog_curation_report(report)


def test_schema_four_requires_consequence_evidence_to_name_candidate() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 4
    payload["evidence"][0]["boundary_target_ids"] = []
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "material trip consequence evidence example-scope must include "
            "example-access in boundary_target_ids"
        ),
    ):
        validate_catalog_curation_report(report)


def test_material_trip_consequence_requires_matching_durability_basis() -> None:
    payload = _material_trip_consequence_payload(
        consequence_type="pass_price_or_coverage",
        durability_basis="durable_access_geometry",
    )

    with pytest.raises(
        ValueError,
        match=(
            "pass_price_or_coverage consequence requires durability_basis="
            "published_product_contract"
        ),
    ):
        CatalogSkiAreaTripConsequence.model_validate(payload)


def test_schema_four_accepts_multiple_consequences_of_the_same_type() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 4
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
            material_trip_consequences=[
                _material_trip_consequence_payload(),
                _material_trip_consequence_payload(),
            ],
        )
    )

    consequences = payload["entity_scope_assessments"][0]["ski_area_boundary"][
        "material_trip_consequences"
    ]
    consequences[1]["decision_effect"] = "stay_to_ski_configuration"
    _add_parent_ski_area_scope_assessment(payload)

    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_exact_duplicate_trip_consequences() -> None:
    consequence = _material_trip_consequence_payload()
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 4
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
            material_trip_consequences=[consequence, consequence.copy()],
        )
    )

    with pytest.raises(
        ValueError,
        match="exact duplicate material trip consequences are forbidden",
    ):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_rejects_material_trip_consequence_fields() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="material trip consequences require report schema version 4",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    ("separation_value", "consequences", "message"),
    [
        (
            "redundant",
            [_material_trip_consequence_payload()],
            "redundant separation value forbids material trip consequences",
        ),
        (
            "material",
            [],
            "material separation value requires a material trip consequence",
        ),
        (
            "unresolved",
            [],
            "not_separate ski area requires redundant or material separation value",
        ),
    ],
)
def test_schema_four_enforces_separation_value_consequence_consistency(
    separation_value: str,
    consequences: list[dict],
    message: str,
) -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector", "ski_connected_terrain"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="sector",
            connectivity_to_parent="connected",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            separation_value=separation_value,
            material_trip_consequences=consequences,
        )
    )
    _complete_existing_ski_area_report_target(payload, "parent-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match=message):
        validate_catalog_curation_report(report)


def test_schema_four_not_separate_requires_resolved_parent_connectivity() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=[
            "official_independent_identity",
            "independent_status_or_schedule",
            "independent_weather_presentation",
        ],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="unknown",
            operational_scope="independent",
            weather_scope="independent",
            separation_value="material",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_existing_ski_area_report_target(payload, "parent-area")

    with pytest.raises(
        CatalogValidationError,
        match="not_separate ski area requires resolved parent connectivity",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_deferred_boundary_requires_unresolved_separation_value() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="deferred",
        signals=["official_map_sector"],
        target_type="ski_area",
        target_id="parent-area",
        backlog_ref="docs/product-backlog.md#example-ski-area-boundary",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="unresolved",
            connectivity_to_parent="unknown",
            operational_scope="unknown",
            weather_scope="unknown",
            pass_scope="unknown",
            provider_consensus="unknown",
            separation_value="material",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_existing_ski_area_report_target(payload, "parent-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="deferred ski area requires unresolved separation value",
    ):
        validate_catalog_curation_report(report)


def test_schema_four_unresolved_boundary_can_retain_verified_consequence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="unresolved",
        signals=["official_map_sector", "distinct_access"],
        target_type="ski_area",
        target_id="parent-area",
        backlog_ref="docs/product-backlog.md#example-ski-area-boundary",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="unresolved",
            connectivity_to_parent="unknown",
            operational_scope="unknown",
            weather_scope="unknown",
            pass_scope="unknown",
            provider_consensus="mixed",
            separation_value="unresolved",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _add_parent_ski_area_scope_assessment(payload)

    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_schema_four_rejects_third_party_trip_consequence_evidence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 4
    payload["evidence"][0]["source_type"] = "third_party"
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=(
            "material trip consequence requires verification-capable evidence "
            "example-scope"
        ),
    ):
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
        signals=[
            "official_independent_identity",
            "separate_operator",
            "independent_weather_presentation",
            "full_local_pass",
        ],
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
    assert "| Components |" not in rendered
    assert "| Coordination Evidence |" not in rendered


def test_schema_four_ski_area_boundary_markdown_renders_trip_consequences() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_independent_identity",
            "independent_weather_presentation",
            "disconnected_terrain",
        ],
        target_type="ski_area",
        target_id="separate-area",
    )
    payload["report_schema_version"] = 4
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            connectivity_to_parent="disconnected",
            weather_scope="independent",
            material_trip_consequences=[_material_trip_consequence_payload()],
        )
    )
    _complete_new_ski_area_report_target(payload, "separate-area")
    report = CatalogCurationReport.model_validate(payload)

    rendered = render_catalog_curation_report_markdown(report)

    assert "| Material Trip Consequences |" in rendered
    assert "`stay_access_or_transfer`" in rendered
    assert "`selected_ski_area`" in rendered
    assert "target `parent-area`" in rendered
    assert "`durable_access_geometry`" in rendered
    assert "evidence `example-scope`" in rendered


def test_coordinated_ski_area_markdown_renders_components_and_evidence() -> None:
    payload = _coordinated_ski_area_report_payload()
    _coordinated_parent(payload)["ski_area_boundary"][
        "coordination_evidence_families"
    ].reverse()
    report = CatalogCurationReport.model_validate(payload)

    rendered = render_catalog_curation_report_markdown(report)

    evidence_refs = (
        "`coordination-inventory`, `coordination-roster`, "
        "`coordination-operations`, `coordination-pass`, "
        "`coordination-assignment`"
    )
    family_ownership = "<br>".join(
        [
            "`complete_terrain_lift_inventory`: components "
            "`operator-a-sector`, `operator-b-sector`; evidence "
            "`coordination-inventory`",
            "`exhaustive_component_operator_roster`: components "
            "`operator-a-sector`, `operator-b-sector`; evidence "
            "`coordination-roster`",
            "`component_addressable_operations_status`: components "
            "`operator-a-sector`, `operator-b-sector`; evidence "
            "`coordination-operations`",
            "`every_component_pass_coverage`: components "
            "`operator-a-sector`, `operator-b-sector`; evidence "
            "`coordination-pass`",
            "`direct_component_parent_assignment`: components "
            "`operator-a-sector`, `operator-b-sector`; evidence "
            "`coordination-assignment`",
        ]
    )
    parent_row = (
        "| `example-access` |  | `complete` | `not_applicable` | "
        "`coordinated` | `unknown` | `shared_only` | `aggregated` | "
        "`material` | `operator-a-sector`, `operator-b-sector` | "
        f"{evidence_refs} | {family_ownership} | {evidence_refs} |"
    )

    assert "| Components | Coordination Evidence | Evidence Families |" in rendered
    assert rendered.splitlines().count(parent_row) == 1


def test_schema_four_markdown_renders_component_parent_assignment() -> None:
    payload = _coordinated_ski_area_report_payload()
    _upgrade_coordinated_payload_to_schema_four(payload)
    report = CatalogCurationReport.model_validate(payload)

    rendered = render_catalog_curation_report_markdown(report)

    assert "`component_parent_assignment`: components" in rendered
    assert "`direct_component_parent_assignment`: components" not in rendered


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

    expected = (
        "# Example destination boundary\n"
        "\n"
        "Reviews one stay-market boundary.\n"
        "\n"
        "## Reviewed Targets\n"
        "\n"
        "| Target | Scope | Graph Role | Required Fields |\n"
        "| --- | --- | --- | --- |\n"
        "| `stay_destination:example` | `narrow` | `focus` | `name` |\n"
        "\n"
        "## Entity Scope Assessments\n"
        "\n"
        "| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | "
        "Backlog | Rationale |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| `example` (Example) | `stay_destination` | `represented` | "
        "`independent_stay_market` | `stay_destination:example` | "
        "`example-stay-market` |  | The official source defines this stay market. |\n"
        "\n"
        "## Changed Fields\n"
        "\n"
        "| Target | Field | Before | After | Trust | Ranking Relevant |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "\n"
        "## Field Coverage\n"
        "\n"
        "| Target | Field | Status | Notes |\n"
        "| --- | --- | --- | --- |\n"
        "| `stay_destination:example` | `name` | `reviewed-no-change` |  |\n"
        "\n"
        "## Evidence\n"
        "\n"
        "| Target | Field | Source | Source Value | Evidence | Normalization |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| `stay_destination:example` | `name` | "
        '[Official accommodation market](https://example.com/stays) | `"Example"` | '
        "Defines the complete independently managed stay market. |  |\n"
        "\n"
        "## Boundary Decisions\n"
        "\n"
        "- `example`: `pass`\n"
    )

    assert rendered == expected


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
    assert geometry.weather_sampling_status == "active"


def test_weather_geometry_rejects_out_of_order_elevation_bands() -> None:
    with pytest.raises(ValidationError):
        CatalogWeatherRequestGeometry(
            weather_sampling_status="active",
            latitude=45.0,
            longitude=6.0,
            base_elevation_m=1800,
            mid_elevation_m=1600,
            upper_elevation_m=2200,
        )


def test_active_weather_geometry_requires_reproducible_derivation_metadata() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "separate_operator",
            "independent_weather_presentation",
            "full_local_pass",
        ],
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0].update(
        {
            "candidate_id": "example-area",
            "evidence_refs": ["example-scope", "example-weather-geometry"],
            "ski_area_boundary": _ski_area_boundary_payload(
                operational_scope="independent",
                weather_scope="independent",
                pass_scope="full_local",
                evidence_refs=["example-scope", "example-weather-geometry"],
            ),
        }
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "scope": "narrow",
            "required_field_paths": ["latitude"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "latitude",
            "status": "reviewed-no-change",
        }
    )
    payload["evidence"].append(
        {
            "evidence_id": "example-weather-geometry",
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "latitude",
            "source_type": "official",
            "source_url": "https://example.com/trail-map",
            "source_title": "Official trail map",
            "source_value": "complete terrain footprint",
            "evidence_summary": "Supports the reviewed terrain geometry.",
        }
    )
    payload["weather_request_geometry_targets"] = ["example-area"]
    payload["weather_request_geometry_assessments"] = [
        {
            "ski_area_id": "example-area",
            "before": None,
            "after": {
                "weather_sampling_status": "active",
                "latitude": 45.01,
                "longitude": 6.01,
                "base_elevation_m": 1200,
                "mid_elevation_m": 1800,
                "upper_elevation_m": 2280,
            },
            "coordinate_derivation_method": "official_terrain_medoid",
            "elevation_derivation_method": "official_lift_served_range",
            "geometry_completeness": "complete",
            "derivation_status": "verified",
            "evidence_refs": ["example-weather-geometry"],
            "post_merge_handoff": "scheduled_completion",
        }
    ]
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)

    assessment = report.weather_request_geometry_assessments[0]
    assert assessment.coordinate_derivation_method == "official_terrain_medoid"
    assert assessment.elevation_derivation_method == "official_lift_served_range"

    payload["weather_request_geometry_assessments"][0].update(
        {
            "coordinate_derivation_method": "preserved_existing",
            "elevation_derivation_method": "preserved_existing",
            "derivation_status": "verified_with_adjustment",
        }
    )
    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_deferred_weather_geometry_requires_exhaustive_coordinate_attempts() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "separate_operator",
            "independent_weather_presentation",
            "full_local_pass",
        ],
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0].update(
        {
            "candidate_id": "example-area",
            "ski_area_boundary": _ski_area_boundary_payload(
                operational_scope="independent",
                weather_scope="independent",
                pass_scope="full_local",
            ),
        }
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "scope": "narrow",
            "required_field_paths": ["weather_sampling_status"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "weather_sampling_status",
            "status": "reviewed-no-change",
        }
    )
    payload["weather_request_geometry_targets"] = ["example-area"]
    payload["weather_request_geometry_assessments"] = [
        {
            "ski_area_id": "example-area",
            "before": None,
            "after": {
                "weather_sampling_status": "deferred",
                "latitude": 45.01,
                "longitude": 6.01,
                "base_elevation_m": 1200,
                "mid_elevation_m": 1800,
                "upper_elevation_m": 2280,
            },
            "geometry_completeness": "unavailable",
            "derivation_status": "deferred",
            "evidence_refs": [],
        }
    ]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="deferred weather sampling requires activation_prerequisite",
    ):
        validate_catalog_curation_report(report)

    payload["weather_request_geometry_assessments"][0]["activation_prerequisite"] = (
        "Source a reproducible in-terrain sampling point and elevation range."
    )
    with pytest.raises(
        CatalogValidationError,
        match="deferred weather sampling requires documented coordinate attempts",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))

    attempt_specs = [
        ("official_terrain_medoid", "official", "Official map has no geometry"),
        ("osm_terrain_medoid", "open_data", "OSM terrain coverage is partial"),
        (
            "official_central_on_mountain_point",
            "official",
            "No exact central weather or hub point is published",
        ),
        (
            "structured_lift_inventory_medoid",
            "open_data",
            "No complete structured lift inventory is available",
        ),
    ]
    evidence_refs = []
    coordinate_attempts = []
    for index, (method, source_type, rationale) in enumerate(attempt_specs, start=1):
        evidence_id = f"coordinate-attempt-{index}"
        evidence_refs.append(evidence_id)
        payload["evidence"].append(
            {
                "evidence_id": evidence_id,
                "target_type": "ski_area",
                "target_id": "example-area",
                "field_path": "latitude",
                "source_type": source_type,
                "source_url": f"https://example.com/coordinate-attempt-{index}",
                "source_title": f"Coordinate attempt {index}",
                "source_value": rationale,
                "evidence_summary": rationale,
            }
        )
        coordinate_attempts.append(
            {
                "method": method,
                "outcome": "unavailable",
                "evidence_refs": [evidence_id],
                "rationale": rationale,
            }
        )
    assessment = payload["weather_request_geometry_assessments"][0]
    assessment["evidence_refs"] = evidence_refs
    assessment["coordinate_derivation_attempts"] = coordinate_attempts

    report = CatalogCurationReport.model_validate(payload)
    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))

    rendered = render_catalog_curation_report_markdown(report)
    assert "Coordinate derivation attempts" in rendered
    assert "`official_terrain_medoid`: `unavailable`" in rendered

    assessment["coordinate_derivation_attempts"].pop()
    with pytest.raises(
        CatalogValidationError,
        match="missing coordinate derivation attempts: "
        "structured_lift_inventory_medoid",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))

    assessment["coordinate_derivation_method"] = "osm_terrain_medoid"
    assessment["coordinate_derivation_attempts"] = coordinate_attempts[:2]
    with pytest.raises(
        CatalogValidationError,
        match="selected coordinate attempt must match osm_terrain_medoid",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))

    assessment["coordinate_derivation_attempts"][1]["outcome"] = "selected"
    validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_retained_weather_geometry_change_requires_post_merge_refetch_handoff() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        signals=[
            "official_independent_identity",
            "separate_operator",
            "independent_weather_presentation",
            "full_local_pass",
        ],
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0].update(
        {
            "candidate_id": "example-area",
            "evidence_refs": ["example-scope", "example-weather-geometry"],
            "ski_area_boundary": _ski_area_boundary_payload(
                operational_scope="independent",
                weather_scope="independent",
                pass_scope="full_local",
                evidence_refs=["example-scope", "example-weather-geometry"],
            ),
        }
    )
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "scope": "narrow",
            "required_field_paths": ["latitude"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "latitude",
            "status": "changed",
        }
    )
    payload["changes"].append(
        {
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "latitude",
            "before": 45.0,
            "after": 45.01,
            "trust_status": "verified",
            "ranking_relevant": False,
        }
    )
    payload["evidence"].append(
        {
            "evidence_id": "example-weather-geometry",
            "target_type": "ski_area",
            "target_id": "example-area",
            "field_path": "latitude",
            "source_type": "official",
            "source_url": "https://example.com/trail-map",
            "source_title": "Official trail map",
            "source_value": 45.01,
            "evidence_summary": "Supports the reviewed terrain geometry.",
        }
    )
    payload["weather_request_geometry_targets"] = ["example-area"]
    payload["weather_request_geometry_assessments"] = [
        {
            "ski_area_id": "example-area",
            "before": {
                "weather_sampling_status": "active",
                "latitude": 45.0,
                "longitude": 6.0,
                "base_elevation_m": 1200,
                "mid_elevation_m": 1800,
                "upper_elevation_m": 2280,
            },
            "after": {
                "weather_sampling_status": "active",
                "latitude": 45.01,
                "longitude": 6.01,
                "base_elevation_m": 1200,
                "mid_elevation_m": 1800,
                "upper_elevation_m": 2280,
            },
            "coordinate_derivation_method": "official_terrain_medoid",
            "elevation_derivation_method": "preserved_existing",
            "geometry_completeness": "complete",
            "derivation_status": "verified_with_adjustment",
            "evidence_refs": ["example-weather-geometry"],
        }
    ]

    with pytest.raises(
        CatalogValidationError,
        match="retained weather geometry changes require "
        "post_merge_handoff=force_refetch_and_rebuild_climatology",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))

    payload["weather_request_geometry_assessments"][0]["post_merge_handoff"] = (
        "force_refetch_and_rebuild_climatology"
    )
    report = CatalogCurationReport.model_validate(payload)
    validate_catalog_curation_report(report)

    rendered = render_catalog_curation_report_markdown(report)
    assert "Post-merge weather handoff" in rendered
    assert "targeted forced historical refetch and climatology rebuild" in rendered


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

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogFieldCoverage,
    CatalogReviewedTarget,
    CatalogValidationError,
    render_catalog_resulting_graph_markdown,
)
from app.data.catalog_curation_reconciliation import (
    _derived_weather_geometry,
    reconcile_catalog_curation_report,
)
from app.data.validate_catalog_curation import main as validate_curation_main
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import FIELD_GROUPS
from tests.test_catalog_models import minimal_catalog_payload

pytestmark = pytest.mark.db_free


def test_weather_geometry_derivation_includes_new_ski_areas() -> None:
    base_catalog = CatalogSnapshot.model_validate(minimal_catalog_payload())
    current_payload = minimal_catalog_payload()
    new_area = dict(current_payload["ski_areas"][0])
    new_area.update(
        {
            "ski_area_id": "new-area",
            "name": "New Area",
            "weather_sampling_status": "deferred",
        }
    )
    current_payload["ski_areas"].append(new_area)
    new_access = dict(current_payload["ski_area_access"][0])
    new_access.update(
        {
            "ski_area_access_id": "example-village--new-area",
            "ski_area_id": "new-area",
        }
    )
    current_payload["ski_area_access"].append(new_access)
    current_payload["lift_pass_products"][0]["valid_ski_area_ids"].append("new-area")
    current_payload["lift_pass_products"][0]["validity_scope"] = "local_multi_area"
    current_catalog = CatalogSnapshot.model_validate(current_payload)

    derived = _derived_weather_geometry(
        SimpleNamespace(
            ski_areas={area.ski_area_id: area for area in base_catalog.ski_areas}
        ),
        SimpleNamespace(
            ski_areas={area.ski_area_id: area for area in current_catalog.ski_areas}
        ),
    )

    before, after = derived["new-area"]
    assert before is None
    assert after.weather_sampling_status == "deferred"


def _trust_payload(catalog_payload: dict) -> dict:
    snapshot = CatalogSnapshot.model_validate(catalog_payload)
    base_names = {item.stay_base_id: item.name for item in snapshot.stay_bases}
    area_names = {item.ski_area_id: item.name for item in snapshot.ski_areas}
    descriptors = {
        "ski_regions": (snapshot.ski_regions, "ski_region_id"),
        "stay_destinations": (
            snapshot.stay_destinations,
            "stay_destination_id",
        ),
        "stay_bases": (snapshot.stay_bases, "stay_base_id"),
        "ski_areas": (snapshot.ski_areas, "ski_area_id"),
        "ski_area_access": (snapshot.ski_area_access, "ski_area_access_id"),
        "terrain_domains": (snapshot.terrain_domains, "terrain_domain_id"),
        "lift_pass_products": (
            snapshot.lift_pass_products,
            "lift_pass_product_id",
        ),
        "rental_display_facts": (
            snapshot.rental_display_facts,
            "rental_display_fact_id",
        ),
    }
    entities: dict[str, dict[str, dict]] = {}
    for entity_type, (items, id_field) in descriptors.items():
        entries = {}
        for item in items:
            entity_id = getattr(item, id_field)
            if entity_type == "ski_area_access":
                display_name = (
                    f"{base_names[item.stay_base_id]} -> {area_names[item.ski_area_id]}"
                )
            else:
                display_name = item.name
            entries[entity_id] = {
                "display_name": display_name,
                "field_statuses": {
                    field_group: "estimated"
                    for field_group in FIELD_GROUPS[entity_type]
                },
                "field_source_refs": {
                    field_group: [] for field_group in FIELD_GROUPS[entity_type]
                },
                "notes": [],
            }
            if entity_type == "ski_area_access":
                entries[entity_id]["field_source_refs"]["relationship"] = list(
                    item.source_urls
                )
        entities[entity_type] = entries
    return {
        "version": "test-v2",
        "catalog_schema_version": 2,
        "status_values": [
            "verified",
            "verified_with_adjustment",
            "estimated",
            "needs_source",
        ],
        "field_groups": {
            entity_type: list(field_groups)
            for entity_type, field_groups in FIELD_GROUPS.items()
        },
        "entities": entities,
    }


def _write_snapshot(
    root: Path,
    label: str,
    catalog_payload: dict,
) -> tuple[Path, Path]:
    catalog_path = root / f"{label}-catalog.json"
    trust_path = root / f"{label}-trust.json"
    catalog_path.write_text(json.dumps(catalog_payload), encoding="utf-8")
    trust_path.write_text(
        json.dumps(_trust_payload(catalog_payload)),
        encoding="utf-8",
    )
    return catalog_path, trust_path


def _relationship_change_report(*, include_endpoints: bool) -> CatalogCurationReport:
    reviewed_targets = [
        CatalogReviewedTarget(
            target_type="ski_area_access",
            target_id="example-village--example-area",
            scope="narrow",
            required_field_paths=["distance_m"],
        ),
    ]
    field_coverage = [
        CatalogFieldCoverage(
            target_type="ski_area_access",
            target_id="example-village--example-area",
            field_path="distance_m",
            status="changed",
        ),
    ]
    if include_endpoints:
        reviewed_targets.extend(
            [
                CatalogReviewedTarget(
                    target_type="stay_base",
                    target_id="example-village",
                    scope="narrow",
                    required_field_paths=["stay_base_id"],
                ),
                CatalogReviewedTarget(
                    target_type="ski_area",
                    target_id="example-area",
                    scope="narrow",
                    required_field_paths=["ski_area_id"],
                ),
            ]
        )
        field_coverage.append(
            CatalogFieldCoverage(
                target_type="stay_base",
                target_id="example-village",
                field_path="stay_base_id",
                status="reviewed-no-change",
            )
        )
        field_coverage.append(
            CatalogFieldCoverage(
                target_type="ski_area",
                target_id="example-area",
                field_path="ski_area_id",
                status="reviewed-no-change",
            )
        )
    return CatalogCurationReport(
        title="Access relationship reconciliation",
        summary="Moves one access edge between normalized ski areas.",
        reviewed_targets=reviewed_targets,
        changes=[
            CatalogChangeSummary(
                target_type="ski_area_access",
                target_id="example-village--example-area",
                field_path="distance_m",
                before=300,
                after=450,
                trust_status="estimated",
            ),
        ],
        field_coverage=field_coverage,
    )


def _schema_two_relationship_report() -> CatalogCurationReport:
    payload = _relationship_change_report(include_endpoints=True).model_dump(
        mode="json"
    )
    payload.update(
        {
            "report_schema_version": 2,
            "entity_scope_assessments": [
                {
                    "candidate_id": "example-access",
                    "candidate_name": "Example village access",
                    "candidate_kind": "ski_area_access",
                    "disposition": "represented",
                    "signals": ["direct_access_relationship"],
                    "evidence_refs": ["example-access-scope"],
                    "target_refs": [
                        {
                            "target_type": "ski_area_access",
                            "target_id": "example-village--example-area",
                        }
                    ],
                    "rationale": "The official map confirms the direct access edge.",
                }
            ],
            "evidence": [
                {
                    "evidence_id": "example-access-scope",
                    "target_type": "ski_area_access",
                    "target_id": "example-village--example-area",
                    "field_path": "source_urls",
                    "source_type": "official",
                    "source_url": "https://example.com/map",
                    "source_title": "Official map",
                    "source_value": ["https://example.com/map"],
                    "evidence_summary": "Shows the village access to the ski area.",
                }
            ],
        }
    )
    return CatalogCurationReport.model_validate(payload)


def _schema_three_relationship_report() -> CatalogCurationReport:
    payload = _schema_two_relationship_report().model_dump(mode="json")
    payload["report_schema_version"] = 3
    payload["resulting_graph"] = {
        "focus_stay_destination_ids": ["example"],
    }
    return CatalogCurationReport.model_validate(payload)


def _schema_two_deferred_report() -> CatalogCurationReport:
    payload = _schema_two_relationship_report().model_dump(mode="json")
    assessment = payload["entity_scope_assessments"][0]
    assessment["disposition"] = "deferred"
    assessment["target_refs"] = []
    assessment["backlog_ref"] = (
        "docs/product-backlog.md#example-region-catalog-extension"
    )
    return CatalogCurationReport.model_validate(payload)


def _write_valid_backlog(tmp_path: Path) -> Path:
    backlog_path = tmp_path / "product-backlog.md"
    backlog_path.write_text(
        "# Product Backlog\n\n"
        "## Catalog Curation Refinements\n\n"
        "### Example Region Catalog Extension\n\n"
        "- `ski_area_access:example-access`\n",
        encoding="utf-8",
    )
    return backlog_path


def _unknown_access_report(
    *,
    access_mode_status: Literal["reviewed-no-change", "unresolved"],
) -> CatalogCurationReport:
    access_id = "example-village--example-area"
    return CatalogCurationReport(
        title="Unknown access mode review",
        summary="Reviews a normalized access edge with unresolved mode.",
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="ski_area_access",
                target_id=access_id,
                scope="full",
            )
        ],
        field_coverage=[
            CatalogFieldCoverage(
                target_type="ski_area_access",
                target_id=access_id,
                field_path=field_path,
                status=(
                    access_mode_status
                    if field_path == "access_mode"
                    else "reviewed-no-change"
                ),
                notes=(
                    "No authoritative access mode has been established."
                    if field_path == "access_mode"
                    and access_mode_status == "unresolved"
                    else None
                ),
            )
            for field_path in sorted(CANONICAL_FIELD_PATHS["ski_area_access"])
        ],
    )


def _unknown_access_snapshots(
    tmp_path: Path,
) -> tuple[tuple[Path, Path], tuple[Path, Path]]:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["access_mode"] = "unknown"
    return (
        _write_snapshot(tmp_path, "unknown-base", payload),
        _write_snapshot(tmp_path, "unknown-current", payload),
    )


def test_full_access_review_requires_unknown_mode_to_be_unresolved(
    tmp_path: Path,
) -> None:
    base_paths, current_paths = _unknown_access_snapshots(tmp_path)

    with pytest.raises(
        CatalogValidationError,
        match="access_mode=unknown must be unresolved",
    ):
        reconcile_catalog_curation_report(
            _unknown_access_report(access_mode_status="reviewed-no-change"),
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_full_access_review_accepts_unresolved_unknown_mode(tmp_path: Path) -> None:
    base_paths, current_paths = _unknown_access_snapshots(tmp_path)

    result = reconcile_catalog_curation_report(
        _unknown_access_report(access_mode_status="unresolved"),
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert result is not None


def _relationship_snapshots(
    tmp_path: Path,
) -> tuple[tuple[Path, Path], tuple[Path, Path]]:
    base = minimal_catalog_payload()
    current = json.loads(json.dumps(base))
    current["ski_area_access"][0]["distance_m"] = 450
    return (
        _write_snapshot(tmp_path, "base", base),
        _write_snapshot(tmp_path, "current", current),
    )


def _pass_validity_snapshots(
    tmp_path: Path,
    *,
    trust_status: str = "verified",
    trust_source_refs: list[str] | None = None,
    update_trust: bool = True,
) -> tuple[tuple[Path, Path], tuple[Path, Path], list[dict], dict, dict]:
    windows = [
        {
            "season_label": "2026-2027",
            "start_date": "2026-12-05",
            "end_date": "2027-04-11",
            "status": "planned",
        }
    ]
    base = minimal_catalog_payload()
    current = json.loads(json.dumps(base))
    current["lift_pass_products"][0]["validity_windows"] = windows
    base_paths = _write_snapshot(tmp_path, "pass-validity-base", base)
    current_paths = _write_snapshot(tmp_path, "pass-validity-current", current)

    current_trust = json.loads(current_paths[1].read_text(encoding="utf-8"))
    pass_trust = current_trust["entities"]["lift_pass_products"]["example-local-pass"]
    if update_trust:
        pass_trust["field_statuses"]["identity_scope_availability"] = trust_status
        pass_trust["field_source_refs"]["identity_scope_availability"] = sorted(
            trust_source_refs
            if trust_source_refs is not None
            else ["https://operator.example.com/winter/tariff"]
        )
    current_paths[1].write_text(json.dumps(current_trust), encoding="utf-8")

    return (
        base_paths,
        current_paths,
        windows,
        pass_trust["field_statuses"],
        pass_trust["field_source_refs"],
    )


def _pass_validity_report(
    *,
    windows: list[dict],
    field_statuses_after: dict,
    field_source_refs_after: dict,
    validity_trust_status: str = "verified",
    include_trust_changes: bool = True,
    evidence_url: str = "https://operator.example.com/winter/tariff",
) -> CatalogCurationReport:
    base_trust = _trust_payload(minimal_catalog_payload())["entities"][
        "lift_pass_products"
    ]["example-local-pass"]
    changes = [
        {
            "target_type": "lift_pass_product",
            "target_id": "example-local-pass",
            "field_path": "validity_windows",
            "before": [],
            "after": windows,
            "trust_status": validity_trust_status,
        }
    ]
    if include_trust_changes:
        changes.extend(
            [
                {
                    "target_type": "trust_manifest",
                    "target_id": "lift_pass_products:example-local-pass",
                    "field_path": "field_statuses",
                    "before": base_trust["field_statuses"],
                    "after": field_statuses_after,
                    "trust_status": "verified",
                },
                {
                    "target_type": "trust_manifest",
                    "target_id": "lift_pass_products:example-local-pass",
                    "field_path": "field_source_refs",
                    "before": base_trust["field_source_refs"],
                    "after": field_source_refs_after,
                    "trust_status": "verified",
                },
            ]
        )
    reviewed_targets = [
        {
            "target_type": "lift_pass_product",
            "target_id": "example-local-pass",
            "scope": "narrow",
            "required_field_paths": ["validity_windows"],
        }
    ]
    if include_trust_changes:
        reviewed_targets.append(
            {
                "target_type": "trust_manifest",
                "target_id": "lift_pass_products:example-local-pass",
                "scope": "narrow",
                "required_field_paths": [
                    "field_statuses",
                    "field_source_refs",
                ],
            }
        )
    return CatalogCurationReport.model_validate(
        {
            "report_schema_version": 3,
            "title": "Example pass validity reconciliation",
            "summary": "Adds one operator-published pass validity window.",
            "resulting_graph": {"focus_stay_destination_ids": ["example"]},
            "reviewed_targets": reviewed_targets,
            "changes": changes,
            "field_coverage": [
                {
                    "target_type": change["target_type"],
                    "target_id": change["target_id"],
                    "field_path": change["field_path"],
                    "status": "changed",
                    "notes": (
                        "The prior empty validity_windows list meant no separate "
                        "pass window was modeled, not verified year-round validity."
                        if change["field_path"] == "validity_windows"
                        else None
                    ),
                }
                for change in changes
            ],
            "evidence": [
                {
                    "evidence_id": f"pass-validity-{change['field_path']}",
                    "target_type": change["target_type"],
                    "target_id": change["target_id"],
                    "field_path": change["field_path"],
                    "source_type": "official",
                    "source_url": evidence_url,
                    "source_title": "Official operator winter tariff",
                    "source_value": change["after"],
                    "evidence_summary": (
                        "The operator tariff supports the complete resulting value."
                    ),
                }
                for change in changes
            ],
            "entity_scope_assessments": [
                {
                    "candidate_id": "example-local-pass",
                    "candidate_name": "Example Local Pass",
                    "candidate_kind": "lift_pass_product",
                    "disposition": "represented",
                    "signals": ["official_product_identity"],
                    "evidence_refs": ["pass-validity-validity_windows"],
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
    )


def _with_supplemental_pass_validity_evidence(
    report: CatalogCurationReport,
) -> CatalogCurationReport:
    payload = report.model_dump(mode="json")
    payload["evidence"].append(
        {
            "evidence_id": "pass-validity-supplemental",
            "target_type": "lift_pass_product",
            "target_id": "example-local-pass",
            "field_path": "validity_windows",
            "source_type": "reviewed_editorial",
            "source_url": "https://guide.example.com/pass-validity",
            "source_title": "Reviewed pass validity guide",
            "source_value": payload["changes"][0]["after"],
            "evidence_summary": "Corroborates the complete official pass window.",
        }
    )
    return CatalogCurationReport.model_validate(payload)


def _pass_validity_removal_case(
    tmp_path: Path,
    *,
    include_evidence: bool,
    trust_source_refs: list[str],
) -> tuple[CatalogCurationReport, tuple[Path, Path], tuple[Path, Path]]:
    (
        empty_paths,
        window_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(
        tmp_path,
        trust_status="estimated",
        trust_source_refs=trust_source_refs,
    )
    payload = _pass_validity_report(
        windows=windows,
        field_statuses_after=field_statuses_after,
        field_source_refs_after=field_source_refs_after,
        validity_trust_status="estimated",
        include_trust_changes=False,
    ).model_dump(mode="json")
    payload["changes"][0]["before"] = windows
    payload["changes"][0]["after"] = []
    validity_evidence = payload["evidence"][0]
    if include_evidence:
        validity_evidence["source_value"] = []
    identity_evidence = {
        **validity_evidence,
        "evidence_id": "pass-identity",
        "field_path": "lift_pass_product_id",
        "source_value": "example-local-pass",
        "evidence_summary": "The operator identifies the pass product.",
    }
    payload["evidence"] = [identity_evidence]
    if include_evidence:
        payload["evidence"].append(validity_evidence)
    payload["entity_scope_assessments"][0]["evidence_refs"] = ["pass-identity"]
    report = CatalogCurationReport.model_validate(payload)
    return report, window_paths, (empty_paths[0], window_paths[1])


def test_reconcile_requires_both_access_link_endpoints(tmp_path: Path) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)

    with pytest.raises(CatalogValidationError, match="missing reviewed endpoint"):
        reconcile_catalog_curation_report(
            _relationship_change_report(include_endpoints=False),
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_reconcile_accepts_exact_entity_and_relationship_deltas(tmp_path: Path) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)

    result = reconcile_catalog_curation_report(
        _relationship_change_report(include_endpoints=True),
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert {
        (delta.target_type, delta.target_id, delta.field_path)
        for delta in result.deltas
    } == {
        (
            "ski_area_access",
            "example-village--example-area",
            "distance_m",
        )
    }


def test_reconcile_accepts_exact_pass_validity_windows_and_owning_trust_deltas(
    tmp_path: Path,
) -> None:
    (
        base_paths,
        current_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(tmp_path)
    report = _pass_validity_report(
        windows=windows,
        field_statuses_after=field_statuses_after,
        field_source_refs_after=field_source_refs_after,
    )

    result = reconcile_catalog_curation_report(
        report,
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert {
        (delta.target_type, delta.target_id, delta.field_path)
        for delta in result.deltas
    } == {
        ("lift_pass_product", "example-local-pass", "validity_windows"),
        (
            "trust_manifest",
            "lift_pass_products:example-local-pass",
            "field_statuses",
        ),
        (
            "trust_manifest",
            "lift_pass_products:example-local-pass",
            "field_source_refs",
        ),
    }
    graph = render_catalog_resulting_graph_markdown(
        report,
        CatalogSnapshot.model_validate_json(
            current_paths[0].read_text(encoding="utf-8")
        ),
    )
    assert "valid 2026-12-05 to 2027-04-11" in graph


def test_reconcile_rejects_pass_validity_trust_status_mismatch(
    tmp_path: Path,
) -> None:
    (
        base_paths,
        current_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(tmp_path)
    report = _pass_validity_report(
        windows=windows,
        field_statuses_after=field_statuses_after,
        field_source_refs_after=field_source_refs_after,
        validity_trust_status="verified_with_adjustment",
    )

    with pytest.raises(
        CatalogValidationError,
        match="validity_windows trust_status=verified_with_adjustment does not match",
    ):
        reconcile_catalog_curation_report(
            report,
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_reconcile_rejects_stale_pass_validity_source_refs(tmp_path: Path) -> None:
    (
        base_paths,
        current_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(
        tmp_path,
        trust_source_refs=["https://operator.example.com/old-tariff"],
    )
    report = _pass_validity_report(
        windows=windows,
        field_statuses_after=field_statuses_after,
        field_source_refs_after=field_source_refs_after,
    )

    with pytest.raises(
        CatalogValidationError,
        match="identity_scope_availability source refs omit validity evidence",
    ):
        reconcile_catalog_curation_report(
            report,
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_reconcile_requires_supplemental_direct_validity_evidence_in_trust_refs(
    tmp_path: Path,
) -> None:
    (
        base_paths,
        current_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(tmp_path)
    report = _with_supplemental_pass_validity_evidence(
        _pass_validity_report(
            windows=windows,
            field_statuses_after=field_statuses_after,
            field_source_refs_after=field_source_refs_after,
        )
    )

    with pytest.raises(
        CatalogValidationError,
        match="identity_scope_availability source refs omit validity evidence",
    ):
        reconcile_catalog_curation_report(
            report,
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_reconcile_accepts_all_direct_validity_evidence_in_trust_refs(
    tmp_path: Path,
) -> None:
    (
        base_paths,
        current_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(
        tmp_path,
        trust_source_refs=[
            "https://operator.example.com/winter/tariff",
            "https://guide.example.com/pass-validity",
        ],
    )
    report = _with_supplemental_pass_validity_evidence(
        _pass_validity_report(
            windows=windows,
            field_statuses_after=field_statuses_after,
            field_source_refs_after=field_source_refs_after,
        )
    )

    result = reconcile_catalog_curation_report(
        report,
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert (
        "lift_pass_product",
        "example-local-pass",
        "validity_windows",
    ) in {
        (delta.target_type, delta.target_id, delta.field_path)
        for delta in result.deltas
    }


def test_reconcile_accepts_empty_pass_validity_without_direct_evidence(
    tmp_path: Path,
) -> None:
    report, base_paths, current_paths = _pass_validity_removal_case(
        tmp_path,
        include_evidence=False,
        trust_source_refs=[],
    )

    result = reconcile_catalog_curation_report(
        report,
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert result.delta_count == 1


def test_reconcile_rejects_empty_pass_validity_with_unowned_evidence(
    tmp_path: Path,
) -> None:
    report, base_paths, current_paths = _pass_validity_removal_case(
        tmp_path,
        include_evidence=True,
        trust_source_refs=[],
    )

    with pytest.raises(
        CatalogValidationError,
        match="identity_scope_availability source refs omit validity evidence",
    ):
        reconcile_catalog_curation_report(
            report,
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_reconcile_accepts_empty_pass_validity_with_owned_evidence(
    tmp_path: Path,
) -> None:
    report, base_paths, current_paths = _pass_validity_removal_case(
        tmp_path,
        include_evidence=True,
        trust_source_refs=["https://operator.example.com/winter/tariff"],
    )

    result = reconcile_catalog_curation_report(
        report,
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert result.delta_count == 1


def test_reconcile_rejects_unchanged_unowned_pass_validity_trust(
    tmp_path: Path,
) -> None:
    (
        base_paths,
        current_paths,
        windows,
        field_statuses_after,
        field_source_refs_after,
    ) = _pass_validity_snapshots(tmp_path, update_trust=False)
    report = _pass_validity_report(
        windows=windows,
        field_statuses_after=field_statuses_after,
        field_source_refs_after=field_source_refs_after,
        validity_trust_status="estimated",
        include_trust_changes=False,
    )

    with pytest.raises(
        CatalogValidationError,
        match="identity_scope_availability source refs omit validity evidence",
    ):
        reconcile_catalog_curation_report(
            report,
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_reconcile_cli_uses_normalized_catalog_paths(tmp_path: Path, capsys) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    report_path.write_text(
        _relationship_change_report(include_endpoints=True).model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    assert "reconciled_deltas=1" in capsys.readouterr().out
    assert markdown_path.exists()


def test_typed_cli_rejects_report_below_required_schema_version(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report-v1.json"
    report_path.write_text(
        _relationship_change_report(include_endpoints=True).model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "typed",
            str(report_path),
            "--require-report-schema-version",
            "2",
        ]
    )

    assert exit_code == 1
    assert (
        "report schema version 1 is below required version 2" in capsys.readouterr().out
    )


def test_typed_cli_accepts_required_schema_version_and_reports_it(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report-v2.json"
    report_path.write_text(
        _schema_two_relationship_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "typed",
            str(report_path),
            "--require-report-schema-version",
            "2",
        ]
    )

    assert exit_code == 0
    assert "report_schema_version=2" in capsys.readouterr().out


def test_typed_cli_accepts_required_schema_version_three(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report-v3.json"
    report_path.write_text(
        _schema_three_relationship_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "typed",
            str(report_path),
            "--require-report-schema-version",
            "3",
        ]
    )

    assert exit_code == 0
    assert "report_schema_version=3" in capsys.readouterr().out


def test_typed_cli_requires_resulting_graph_for_current_schema_three(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report-v3-without-graph.json"
    payload = _schema_three_relationship_report().model_dump(mode="json")
    payload.pop("resulting_graph")
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = validate_curation_main(
        [
            "typed",
            str(report_path),
            "--require-report-schema-version",
            "3",
        ]
    )

    assert exit_code == 1
    assert "schema version 3 requires resulting_graph" in capsys.readouterr().out


def test_reconcile_cli_renders_the_canonical_resulting_graph(
    tmp_path: Path,
) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report-v3.json"
    markdown_path = tmp_path / "report-v3.md"
    report_path.write_text(
        _schema_three_relationship_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--require-report-schema-version",
            "3",
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    rendered = markdown_path.read_text(encoding="utf-8")
    assert "## Resulting Graph" in rendered
    assert "Stay destination<br/>Example" in rendered
    assert '|"access: walk via Example Gondola, 450 m"|' in rendered


def test_reconcile_cli_accepts_matching_markdown_companion(
    tmp_path: Path,
) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report-v3.json"
    markdown_path = tmp_path / "report-v3.md"
    report_path.write_text(
        _schema_three_relationship_report().model_dump_json(indent=2),
        encoding="utf-8",
    )
    assert (
        validate_curation_main(
            [
                "reconcile",
                str(report_path),
                "--base-catalog-path",
                str(base_paths[0]),
                "--current-catalog-path",
                str(current_paths[0]),
                "--base-trust-manifest-path",
                str(base_paths[1]),
                "--current-trust-manifest-path",
                str(current_paths[1]),
                "--require-report-schema-version",
                "3",
                "--markdown-output",
                str(markdown_path),
            ]
        )
        == 0
    )

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--require-report-schema-version",
            "3",
            "--require-markdown-path",
            str(markdown_path),
        ]
    )

    assert exit_code == 0


def test_reconcile_cli_rejects_stale_markdown_companion(
    tmp_path: Path,
    capsys,
) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report-v3.json"
    markdown_path = tmp_path / "report-v3.md"
    report_path.write_text(
        _schema_three_relationship_report().model_dump_json(indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text("# Stale report\n", encoding="utf-8")

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--require-report-schema-version",
            "3",
            "--require-markdown-path",
            str(markdown_path),
        ]
    )

    assert exit_code == 1
    assert "rendered Markdown does not match canonical report" in (
        capsys.readouterr().out
    )


def test_typed_cli_requires_backlog_path_for_deferred_report(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        _schema_two_deferred_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(["typed", str(report_path)])

    assert exit_code == 1
    assert "product backlog path is required" in capsys.readouterr().out


def test_typed_cli_accepts_valid_deferred_backlog_reference(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report.json"
    backlog_path = _write_valid_backlog(tmp_path)
    report_path.write_text(
        _schema_two_deferred_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "typed",
            str(report_path),
            "--product-backlog-path",
            str(backlog_path),
        ]
    )

    assert exit_code == 0
    assert "backlog_refs=1" in capsys.readouterr().out


def test_reconcile_cli_applies_required_schema_version(
    tmp_path: Path,
    capsys,
) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report-v2.json"
    report_path.write_text(
        _schema_two_relationship_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--require-report-schema-version",
            "2",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "report_schema_version=2" in output
    assert "reconciled_deltas=1" in output


def test_reconcile_cli_accepts_valid_deferred_backlog_reference(
    tmp_path: Path,
    capsys,
) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report-v2.json"
    backlog_path = _write_valid_backlog(tmp_path)
    report_path.write_text(
        _schema_two_deferred_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--product-backlog-path",
            str(backlog_path),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "backlog_refs=1" in output
    assert "reconciled_deltas=1" in output


def test_reconcile_cli_can_explicitly_skip_backlog_prose_validation(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report_path = tmp_path / "report-v2.json"
    report_path.write_text(
        _schema_two_deferred_report().model_dump_json(indent=2),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.data.validate_catalog_curation.validate_catalog_curation_backlog_refs",
        lambda *args: pytest.fail("backlog parser must not run"),
    )

    exit_code = validate_curation_main(
        [
            "reconcile",
            str(report_path),
            "--base-catalog-path",
            str(base_paths[0]),
            "--current-catalog-path",
            str(current_paths[0]),
            "--base-trust-manifest-path",
            str(base_paths[1]),
            "--current-trust-manifest-path",
            str(current_paths[1]),
            "--skip-product-backlog-validation",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "backlog_refs=1" in output
    assert "reconciled_deltas=1" in output

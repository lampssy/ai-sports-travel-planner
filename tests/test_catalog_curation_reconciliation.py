import json
from pathlib import Path

import pytest

from app.data.catalog_curation import (
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogFieldCoverage,
    CatalogReviewedTarget,
    CatalogValidationError,
)
from app.data.catalog_curation_reconciliation import (
    reconcile_catalog_curation_report,
)
from app.data.validate_catalog_curation import main as validate_curation_main
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import FIELD_GROUPS
from tests.test_catalog_models import minimal_catalog_payload


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
                "source_refs": [],
                "notes": [],
            }
        entities[entity_type] = entries
    return {
        "version": "test-v1",
        "catalog_schema_version": 1,
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

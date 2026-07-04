from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.data import migrate_catalog_v2 as migration_cli
from app.data.catalog_v2_migration import (
    VERSION_1_GROUPS,
    CatalogV2MigrationReport,
    build_migration_report,
    migrate_catalog_payload,
    migrate_trust_payload,
    reconcile_migration_report,
)
from tests.test_catalog_models import minimal_catalog_payload


def minimal_v1_catalog_payload() -> dict[str, Any]:
    payload = minimal_catalog_payload()
    payload["schema_version"] = 1
    return payload


def _version_1_entry(display_name: str, entity_type: str) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "field_statuses": {
            group: "estimated" for group in VERSION_1_GROUPS[entity_type]
        },
        "source_refs": [],
        "notes": [],
    }


def minimal_manifest_payload() -> dict[str, Any]:
    return {
        "version": "test-v1",
        "catalog_schema_version": 1,
        "status_values": [
            "verified",
            "verified_with_adjustment",
            "estimated",
            "needs_source",
        ],
        "field_groups": {key: list(value) for key, value in VERSION_1_GROUPS.items()},
        "entities": {
            "ski_regions": {
                "example": _version_1_entry("Example Valley", "ski_regions")
            },
            "stay_destinations": {
                "example": _version_1_entry("Example", "stay_destinations")
            },
            "stay_bases": {
                "example-village": _version_1_entry("Example Village", "stay_bases")
            },
            "ski_areas": {
                "example-area": _version_1_entry("Example Area", "ski_areas")
            },
            "ski_area_access": {
                "example-village--example-area": _version_1_entry(
                    "Example Village -> Example Area", "ski_area_access"
                )
            },
            "terrain_domains": {},
            "lift_pass_products": {
                "example-local-pass": _version_1_entry(
                    "Example Local Pass", "lift_pass_products"
                )
            },
            "rental_display_facts": {},
        },
    }


def test_migrate_catalog_v1_to_v2_normalizes_structure_and_retires_tags() -> None:
    catalog = minimal_v1_catalog_payload()
    catalog["stay_destinations"][0]["atmosphere_tags"] = ["premium"]
    catalog["stay_bases"][0].update(
        {
            "base_type": "traditional_village",
            "atmosphere_tags": ["quiet", "family-friendly"],
        }
    )

    migrated, audit = migrate_catalog_payload(catalog)

    assert migrated["schema_version"] == 2
    assert "atmosphere_tags" not in migrated["stay_destinations"][0]
    assert "atmosphere_tags" not in migrated["stay_bases"][0]
    assert migrated["stay_bases"][0]["base_type"] == "village"
    assert migrated["stay_bases"][0]["elevation_m"] is None
    assert migrated["stay_bases"][0]["base_character"] == {
        "development_style": "unknown",
        "local_pace": "unknown",
    }
    assert migrated["stay_bases"][0]["local_apres_profile"] == {
        "availability": "unknown",
        "intensity": None,
        "season_label": None,
    }
    assert migrated["ski_areas"][0]["snowmaking"] == {
        "availability": "unknown",
        "coverage_pct": None,
        "coverage_basis": "unknown",
        "season_label": None,
    }
    assert migrated["ski_areas"][0]["official_trail_map"] is None
    assert audit.retired_atmosphere_tags[0].field_path == "atmosphere_tags"
    assert audit.base_type_normalizations[0].before == "traditional_village"
    assert catalog["schema_version"] == 1
    assert catalog["stay_bases"][0]["base_type"] == "traditional_village"


def test_migrate_trust_v1_to_v2_uses_independent_needs_source_groups() -> None:
    trust = minimal_manifest_payload()
    area = trust["entities"]["ski_areas"]["example-area"]
    area["field_statuses"]["identity_coordinates"] = "verified"
    area["source_refs"] = ["https://www.example.com/area"]

    migrated = migrate_trust_payload(trust)

    assert migrated["catalog_schema_version"] == 2
    destination = migrated["entities"]["stay_destinations"]["example"]
    stay_base = migrated["entities"]["stay_bases"]["example-village"]
    ski_area = migrated["entities"]["ski_areas"]["example-area"]
    assert destination["field_statuses"]["price_level"] == "estimated"
    assert stay_base["field_statuses"]["base_character"] == "needs_source"
    assert ski_area["field_statuses"]["night_skiing"] == "needs_source"
    assert ski_area["field_source_refs"]["identity_coordinates"] == [
        "https://www.example.com/area"
    ]
    assert ski_area["field_source_refs"]["night_skiing"] == []
    assert "source_refs" not in ski_area
    assert trust["catalog_schema_version"] == 1


def test_migration_report_reconciliation_rejects_tampered_output() -> None:
    catalog = minimal_v1_catalog_payload()
    trust = minimal_manifest_payload()
    migrated_catalog, audit = migrate_catalog_payload(catalog)
    migrated_trust = migrate_trust_payload(trust)
    report = build_migration_report(
        before_catalog=catalog,
        after_catalog=migrated_catalog,
        before_trust=trust,
        after_trust=migrated_trust,
        audit=audit,
    )
    migrated_catalog["stay_bases"][0]["base_type"] = "town"

    with pytest.raises(ValueError, match="catalog after hash"):
        reconcile_migration_report(
            report,
            before_catalog=catalog,
            after_catalog=migrated_catalog,
            before_trust=trust,
            after_trust=migrated_trust,
        )


@pytest.mark.parametrize("version", [0, 2, 3])
def test_migration_rejects_non_v1_input(version: int) -> None:
    catalog = minimal_v1_catalog_payload()
    catalog["schema_version"] = version
    with pytest.raises(ValueError, match="expected catalog schema version 1"):
        migrate_catalog_payload(catalog)


def test_migration_rejects_unknown_legacy_base_type() -> None:
    catalog = minimal_v1_catalog_payload()
    catalog["stay_bases"][0]["base_type"] = "marketing_concept"

    with pytest.raises(ValueError, match="unknown legacy base_type"):
        migrate_catalog_payload(catalog)


def test_write_and_reconcile_cli_use_audited_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base_catalog = tmp_path / "base-catalog.json"
    base_trust = tmp_path / "base-trust.json"
    current_catalog = tmp_path / "catalog.json"
    current_trust = tmp_path / "trust.json"
    report_path = tmp_path / "report.json"
    catalog_payload = minimal_v1_catalog_payload()
    trust_payload = minimal_manifest_payload()
    for path, payload in (
        (base_catalog, catalog_payload),
        (current_catalog, catalog_payload),
        (base_trust, trust_payload),
        (current_trust, trust_payload),
    ):
        path.write_text(json.dumps(payload), encoding="utf-8")

    assert (
        migration_cli.main(
            [
                "write",
                "--catalog-path",
                str(current_catalog),
                "--trust-manifest-path",
                str(current_trust),
                "--report-path",
                str(report_path),
            ]
        )
        == 0
    )
    assert json.loads(current_catalog.read_text())["schema_version"] == 2
    assert json.loads(current_trust.read_text())["catalog_schema_version"] == 2
    CatalogV2MigrationReport.model_validate_json(report_path.read_text())

    assert (
        migration_cli.main(
            [
                "reconcile",
                "--base-catalog-path",
                str(base_catalog),
                "--current-catalog-path",
                str(current_catalog),
                "--base-trust-manifest-path",
                str(base_trust),
                "--current-trust-manifest-path",
                str(current_trust),
                "--report-path",
                str(report_path),
            ]
        )
        == 0
    )
    assert "[catalog-v2-migration-reconciled]" in capsys.readouterr().out


def test_cli_reports_one_clean_error_line(tmp_path: Path, capsys: Any) -> None:
    catalog_path = tmp_path / "catalog.json"
    trust_path = tmp_path / "trust.json"
    catalog = minimal_catalog_payload()
    catalog["schema_version"] = 2
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    trust_path.write_text(json.dumps(minimal_manifest_payload()), encoding="utf-8")

    assert (
        migration_cli.main(
            [
                "dry-run",
                "--catalog-path",
                str(catalog_path),
                "--trust-manifest-path",
                str(trust_path),
            ]
        )
        == 1
    )
    stderr_lines = capsys.readouterr().err.splitlines()
    assert len(stderr_lines) == 1
    assert stderr_lines[0].startswith("[catalog-v2-migration-invalid]")
    assert "Traceback" not in stderr_lines[0]

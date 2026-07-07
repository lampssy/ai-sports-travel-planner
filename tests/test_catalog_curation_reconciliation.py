import json
from pathlib import Path
from typing import Literal

import pytest

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
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
                "field_source_refs": {
                    field_group: [] for field_group in FIELD_GROUPS[entity_type]
                },
                "notes": [],
            }
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

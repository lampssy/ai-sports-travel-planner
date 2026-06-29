import json
from pathlib import Path

import pytest

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
    CatalogWeatherRequestGeometryAssessment,
    catalog_weather_request_geometry,
    rental_reconciliation_target_id,
)
from app.data.catalog_curation_reconciliation import (
    reconcile_catalog_curation_report,
)
from app.data.loader import load_resorts_from_path
from app.data.validate_catalog_curation import main as validate_curation_main

TRUST_FIELD_GROUPS = [
    "destination_identity",
    "country_region",
    "destination_coordinates",
    "destination_elevation",
    "season_window",
    "ski_areas",
    "terrain_groups",
    "stay_bases",
    "stay_base_quality_tier",
    "stay_base_lift_distance",
    "supported_skill_levels",
    "lift_pass_products",
    "rental_examples",
    "rental_quality_tier",
    "price_ranges",
]


def _destination(
    resort_id: str = "madonna-di-campiglio",
    *,
    name: str = "Madonna di Campiglio",
    region: str = "Trentino",
    rental_name: str = "Ski Rent Campiglio",
) -> dict:
    return {
        "resort_id": resort_id,
        "name": name,
        "country": "Italy",
        "region": region,
        "price_level": "medium",
        "latitude": 46.2267,
        "longitude": 10.8268,
        "base_elevation_m": 1550,
        "summit_elevation_m": 2504,
        "season_start_month": 12,
        "season_end_month": 4,
        "rentals": [
            {
                "name": rental_name,
                "price_range": "EUR 35-50",
                "quality": "standard",
                "lift_distance": "near",
            }
        ],
        "stay_bases": [
            {
                "stay_base_id": f"{resort_id}-village",
                "name": name,
                "price_range": "EUR 180-260",
                "quality": "standard",
                "lift_distance": "near",
                "supported_skill_levels": ["beginner", "intermediate"],
            }
        ],
        "ski_areas": [
            {
                "ski_area_id": f"{resort_id}-ski-area",
                "name": name,
                "latitude": 46.2267,
                "longitude": 10.8268,
                "base_elevation_m": 1550,
                "summit_elevation_m": 2504,
                "season_start_month": 12,
                "season_end_month": 4,
            }
        ],
    }


def _trust_manifest(destinations: list[dict], domains: list[dict]) -> dict:
    return {
        "version": "test",
        "field_groups": TRUST_FIELD_GROUPS,
        "destinations": {
            destination["resort_id"]: {
                "display_name": destination["name"],
                "field_statuses": {
                    field_group: "estimated" for field_group in TRUST_FIELD_GROUPS
                },
                "source_refs": [],
                "notes": ["Test destination trust record."],
            }
            for destination in destinations
        },
        "terrain_domains": {
            domain["terrain_domain_id"]: {
                "display_name": domain["name"],
                "field_statuses": {
                    "membership": "estimated",
                    "terrain_metrics": "estimated",
                    "season_window": "estimated",
                },
                "source_refs": ["https://example.com/domain"],
                "notes": ["Test terrain-domain trust record."],
            }
            for domain in domains
        },
    }


def _domain(domain_id: str, name: str, destinations: list[dict]) -> dict:
    return {
        "terrain_domain_id": domain_id,
        "name": name,
        "ski_area_refs": [
            {
                "resort_id": destination["resort_id"],
                "ski_area_id": destination["ski_areas"][0]["ski_area_id"],
            }
            for destination in destinations
        ],
        "metric_scope": "aggregate",
        "total_piste_km": 300,
        "total_lift_count": 70,
        "source_urls": ["https://example.com/domain"],
    }


def _write_snapshot(
    root: Path,
    label: str,
    *,
    destinations: list[dict],
    domains: list[dict] | None = None,
    trust: dict | None = None,
) -> tuple[Path, Path, Path]:
    resolved_domains = domains or []
    paths = (
        root / f"{label}-resorts.json",
        root / f"{label}-domains.json",
        root / f"{label}-trust.json",
    )
    payloads = (
        destinations,
        resolved_domains,
        trust or _trust_manifest(destinations, resolved_domains),
    )
    for path, payload in zip(paths, payloads, strict=True):
        path.write_text(json.dumps(payload), encoding="utf-8")
    return paths


def _report(changes: list[CatalogChangeSummary]) -> CatalogCurationReport:
    fields_by_target: dict[tuple[str, str], set[str]] = {}
    for change in changes:
        canonical_field_path = next(
            (
                field_path
                for field_path in CANONICAL_FIELD_PATHS[change.target_type]
                if change.field_path == field_path
                or change.field_path.startswith(f"{field_path}[")
                or change.field_path.startswith(f"{field_path}.")
            ),
            change.field_path,
        )
        fields_by_target.setdefault((change.target_type, change.target_id), set()).add(
            canonical_field_path
        )
    return CatalogCurationReport(
        title="Catalog reconciliation fixture",
        summary="Reconciles a temporary catalog snapshot.",
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type=target_type,
                target_id=target_id,
                scope="narrow",
                required_field_paths=sorted(field_paths),
            )
            for (target_type, target_id), field_paths in sorted(
                fields_by_target.items()
            )
        ],
        changes=changes,
        field_coverage=(
            [
                CatalogFieldCoverage(
                    target_type=change.target_type,
                    target_id=change.target_id,
                    field_path=change.field_path,
                    status="changed",
                )
                for change in changes
            ]
            + [
                CatalogFieldCoverage(
                    target_type=target_type,
                    target_id=target_id,
                    field_path=field_path,
                    status="reviewed-no-change",
                )
                for (target_type, target_id), field_paths in fields_by_target.items()
                for field_path in field_paths
                if not any(
                    change.target_type == target_type
                    and change.target_id == target_id
                    and change.field_path == field_path
                    for change in changes
                )
            ]
        ),
    )


def _estimated_change(
    target_type: str,
    target_id: str,
    field_path: str,
    before: object,
    after: object,
) -> CatalogChangeSummary:
    return CatalogChangeSummary(
        target_type=target_type,
        target_id=target_id,
        field_path=field_path,
        before=before,
        after=after,
        trust_status="estimated",
    )


def _reconcile(
    report: CatalogCurationReport,
    base_paths: tuple[Path, Path, Path],
    current_paths: tuple[Path, Path, Path],
    *,
    required_boundary_targets: tuple[str, ...] = (),
    required_weather_geometry_targets: tuple[str, ...] = (),
):
    return reconcile_catalog_curation_report(
        report,
        base_resorts_path=base_paths[0],
        current_resorts_path=current_paths[0],
        base_terrain_domains_path=base_paths[1],
        current_terrain_domains_path=current_paths[1],
        base_trust_manifest_path=base_paths[2],
        current_trust_manifest_path=current_paths[2],
        required_boundary_targets=required_boundary_targets,
        required_weather_geometry_targets=required_weather_geometry_targets,
    )


@pytest.mark.parametrize("omitted_target", ["destination", "trust_manifest", "domain"])
def test_reconciliation_rejects_undeclared_snapshot_delta(
    tmp_path: Path, omitted_target: str
) -> None:
    base_destinations = [_destination(), _destination("pinzolo", name="Pinzolo")]
    current_destinations = json.loads(json.dumps(base_destinations))
    current_destinations[0]["region"] = "Trentino-Alto Adige"
    base_domains = [_domain("campiglio-domain", "Campiglio Domain", base_destinations)]
    current_domains = json.loads(json.dumps(base_domains))
    current_domains[0]["name"] = "Campiglio Dolomiti Domain"
    base_trust = _trust_manifest(base_destinations, base_domains)
    current_trust = _trust_manifest(current_destinations, current_domains)
    current_trust["destinations"]["madonna-di-campiglio"]["display_name"] = (
        "Madonna di Campiglio Pinzolo"
    )
    base_paths = _write_snapshot(
        tmp_path,
        "base",
        destinations=base_destinations,
        domains=base_domains,
        trust=base_trust,
    )
    current_paths = _write_snapshot(
        tmp_path,
        "current",
        destinations=current_destinations,
        domains=current_domains,
        trust=current_trust,
    )
    changes = {
        "destination": _estimated_change(
            "destination",
            "madonna-di-campiglio",
            "region",
            "Trentino",
            "Trentino-Alto Adige",
        ),
        "trust_manifest": _estimated_change(
            "trust_manifest",
            "destination:madonna-di-campiglio",
            "display_name",
            "Madonna di Campiglio",
            "Madonna di Campiglio Pinzolo",
        ),
        "domain": _estimated_change(
            "terrain_domain",
            "campiglio-domain",
            "name",
            "Campiglio Domain",
            "Campiglio Dolomiti Domain",
        ),
        "domain_trust": _estimated_change(
            "trust_manifest",
            "terrain_domain:campiglio-domain",
            "display_name",
            "Campiglio Domain",
            "Campiglio Dolomiti Domain",
        ),
    }
    included = [
        change
        for key, change in changes.items()
        if key != omitted_target
        and not (omitted_target == "domain" and key == "domain_trust")
    ]

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(_report(included), base_paths, current_paths)

    assert any(
        "missing report change for snapshot delta" in issue
        for issue in error.value.issues
    )


@pytest.mark.parametrize(
    ("omitted_domain", "retained_domain"),
    [
        ("tignes-val-disere", "matterhorn-ski-paradise"),
        ("matterhorn-ski-paradise", "tignes-val-disere"),
    ],
)
def test_reconciliation_tracks_each_domain_trust_record_independently(
    tmp_path: Path, omitted_domain: str, retained_domain: str
) -> None:
    destinations = [_destination(), _destination("pinzolo", name="Pinzolo")]
    base_domains = [
        _domain("tignes-val-disere", "Tignes - Val d'Isere", destinations),
        _domain("matterhorn-ski-paradise", "Matterhorn Ski Paradise", destinations),
    ]
    current_domains = json.loads(json.dumps(base_domains))
    for domain in current_domains:
        domain["name"] += " Updated"
    base_trust = _trust_manifest(destinations, base_domains)
    current_trust = _trust_manifest(destinations, current_domains)
    base_paths = _write_snapshot(
        tmp_path,
        "base",
        destinations=destinations,
        domains=base_domains,
        trust=base_trust,
    )
    current_paths = _write_snapshot(
        tmp_path,
        "current",
        destinations=destinations,
        domains=current_domains,
        trust=current_trust,
    )
    changes: list[CatalogChangeSummary] = []
    for domain in base_domains:
        domain_id = domain["terrain_domain_id"]
        changes.append(
            _estimated_change(
                "terrain_domain",
                domain_id,
                "name",
                domain["name"],
                f"{domain['name']} Updated",
            )
        )
        if domain_id == retained_domain:
            changes.append(
                _estimated_change(
                    "trust_manifest",
                    f"terrain_domain:{domain_id}",
                    "display_name",
                    domain["name"],
                    f"{domain['name']} Updated",
                )
            )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(_report(changes), base_paths, current_paths)

    assert any(
        f"trust_manifest:terrain_domain:{omitted_domain} display_name" in issue
        for issue in error.value.issues
    )


def test_reconciliation_accepts_destination_trust_display_name_delta(
    tmp_path: Path,
) -> None:
    destinations = [_destination()]
    base_trust = _trust_manifest(destinations, [])
    current_trust = json.loads(json.dumps(base_trust))
    current_trust["destinations"]["madonna-di-campiglio"]["display_name"] = (
        "Madonna di Campiglio Dolomiti"
    )
    base_paths = _write_snapshot(
        tmp_path, "base", destinations=destinations, trust=base_trust
    )
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=destinations, trust=current_trust
    )
    report = _report(
        [
            _estimated_change(
                "trust_manifest",
                "destination:madonna-di-campiglio",
                "display_name",
                "Madonna di Campiglio",
                "Madonna di Campiglio Dolomiti",
            )
        ]
    )

    result = _reconcile(report, base_paths, current_paths)

    assert result.delta_count == 1


def test_reconciliation_emits_exact_nested_trust_status_delta(
    tmp_path: Path,
) -> None:
    destinations = [_destination()]
    base_trust = _trust_manifest(destinations, [])
    current_trust = json.loads(json.dumps(base_trust))
    current_trust["destinations"]["madonna-di-campiglio"]["field_statuses"][
        "destination_identity"
    ] = "needs_source"
    base_paths = _write_snapshot(
        tmp_path, "base", destinations=destinations, trust=base_trust
    )
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=destinations, trust=current_trust
    )
    report = _report(
        [
            _estimated_change(
                "trust_manifest",
                "destination:madonna-di-campiglio",
                "field_statuses.destination_identity",
                "estimated",
                "needs_source",
            )
        ]
    )

    result = _reconcile(report, base_paths, current_paths)

    assert result.deltas[0].field_path == "field_statuses.destination_identity"


def test_reconciliation_validates_empty_trust_manifest(tmp_path: Path) -> None:
    base_destinations = [_destination()]
    current_destinations = [_destination(region="Trentino-Alto Adige")]
    base_paths = _write_snapshot(
        tmp_path,
        "base",
        destinations=base_destinations,
        trust={},
    )
    base_paths[2].write_text("{}", encoding="utf-8")
    current_paths = _write_snapshot(
        tmp_path,
        "current",
        destinations=current_destinations,
    )
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(report, base_paths, current_paths)

    assert any(
        "trust manifest must contain destinations object" in issue
        for issue in error.value.issues
    )


def _rental_rename_changes(
    before_name: str,
    after_name: str,
) -> list[CatalogChangeSummary]:
    resort_id = "madonna-di-campiglio"
    before_id = rental_reconciliation_target_id(resort_id, before_name)
    after_id = rental_reconciliation_target_id(resort_id, after_name)
    before = {
        "name": before_name,
        "price_range": "EUR 35-50",
        "price_min": 35.0,
        "price_max": 50.0,
        "quality": "standard",
        "lift_distance": "near",
    }
    after = {**before, "name": after_name}
    changes = [
        _estimated_change("destination", resort_id, "rentals[0]", before_id, after_id)
    ]
    changes.extend(
        _estimated_change("rental", before_id, field_path, value, None)
        for field_path, value in before.items()
    )
    changes.extend(
        _estimated_change("rental", after_id, field_path, None, value)
        for field_path, value in after.items()
    )
    return changes


def test_reconciliation_treats_rental_rename_as_removal_and_addition(
    tmp_path: Path,
) -> None:
    before_name = "École Ski Rent"
    after_name = "Scuola Ski Rent"
    base_destinations = [_destination(rental_name=before_name)]
    current_destinations = [_destination(rental_name=after_name)]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )

    result = _reconcile(
        _report(_rental_rename_changes(before_name, after_name)),
        base_paths,
        current_paths,
    )

    rental_target_ids = {
        delta.target_id for delta in result.deltas if delta.target_type == "rental"
    }
    assert rental_target_ids == {
        "madonna-di-campiglio:ecole-ski-rent",
        "madonna-di-campiglio:scuola-ski-rent",
    }


def test_reconciliation_rejects_rental_identity_collision(tmp_path: Path) -> None:
    destinations = [_destination()]
    destinations[0]["rentals"].append(
        {
            "name": "Ski-Rent Campiglio",
            "price_range": "EUR 35-50",
            "quality": "standard",
            "lift_distance": "near",
        }
    )
    base_paths = _write_snapshot(tmp_path, "base", destinations=destinations)
    current = json.loads(json.dumps(destinations))
    current[0]["region"] = "Trentino-Alto Adige"
    current_paths = _write_snapshot(tmp_path, "current", destinations=current)
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(report, base_paths, current_paths)

    assert any(
        "rental reconciliation identity collision" in issue
        for issue in error.value.issues
    )


def _add_passing_boundary_and_geometry(
    report: CatalogCurationReport,
    resorts_path: Path,
) -> None:
    destination_id = "madonna-di-campiglio"
    ski_area = load_resorts_from_path(resorts_path)[0].ski_areas[0]
    destination_target = next(
        target
        for target in report.reviewed_targets
        if target.target_type == "destination" and target.target_id == destination_id
    )
    destination_target.required_field_paths.append("resort_id")
    report.reviewed_targets.append(
        CatalogReviewedTarget(
            target_type="ski_area",
            target_id=ski_area.ski_area_id,
            scope="narrow",
            required_field_paths=["ski_area_id"],
        )
    )
    report.field_coverage.extend(
        [
            CatalogFieldCoverage(
                target_type="destination",
                target_id=destination_id,
                field_path="resort_id",
                status="reviewed-no-change",
            ),
            CatalogFieldCoverage(
                target_type="ski_area",
                target_id=ski_area.ski_area_id,
                field_path="ski_area_id",
                status="reviewed-no-change",
            ),
        ]
    )
    report.evidence.append(
        CatalogEvidenceItem(
            evidence_id="madonna-boundary-official",
            target_type="destination",
            target_id=destination_id,
            field_path="resort_id",
            source_type="official",
            source_url="https://example.com/madonna-di-campiglio",
            source_title="Official Madonna di Campiglio destination page",
            source_value=destination_id,
            evidence_summary="Official destination treatment and local ski access.",
        )
    )
    gates = [
        CatalogBoundaryGateAssessment(
            gate_name=gate_name,
            status="pass",
            notes=f"Reviewed {gate_name}.",
            evidence_refs=["madonna-boundary-official"],
        )
        for gate_name in (
            "independent_stay_context",
            "independent_ski_access",
            "independent_recommendation_value",
        )
    ]
    report.boundary_decision_targets = [destination_id]
    report.destination_boundary_assessments = [
        CatalogDestinationBoundaryAssessment(
            candidate_id=destination_id,
            gates=gates,
            identity_signals=[
                CatalogIdentitySignalAssessment(
                    signal_type="official_destination_treatment",
                    status="pass",
                    notes="Official site presents the destination independently.",
                    evidence_refs=["madonna-boundary-official"],
                )
            ],
        )
    ]
    geometry = catalog_weather_request_geometry(ski_area)
    report.weather_request_geometry_targets = [ski_area.ski_area_id]
    report.weather_request_geometry_assessments = [
        CatalogWeatherRequestGeometryAssessment(
            ski_area_id=ski_area.ski_area_id,
            before=geometry,
            after=geometry,
        )
    ]


def test_reconciliation_rejects_omitted_required_retained_destination(
    tmp_path: Path,
) -> None:
    base_destinations = [_destination()]
    current_destinations = [_destination(region="Trentino-Alto Adige")]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(
            report,
            base_paths,
            current_paths,
            required_boundary_targets=("madonna-di-campiglio",),
        )

    assert any("required boundary target" in issue for issue in error.value.issues)


@pytest.mark.parametrize(
    ("gate_status", "signal_status"),
    [("fail", "pass"), ("unresolved", "pass"), ("pass", "fail")],
)
def test_reconciliation_requires_complete_passing_boundary_assessment(
    tmp_path: Path, gate_status: str, signal_status: str
) -> None:
    base_destinations = [_destination()]
    current_destinations = [_destination(region="Trentino-Alto Adige")]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )
    _add_passing_boundary_and_geometry(report, base_paths[0])
    assessment = report.destination_boundary_assessments[0]
    assessment.gates[0].status = gate_status
    assessment.identity_signals[0].status = signal_status
    assessment.failure_route = "blocked"

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(
            report,
            base_paths,
            current_paths,
            required_boundary_targets=("madonna-di-campiglio",),
        )

    assert any("complete passing assessment" in issue for issue in error.value.issues)


def test_reconciliation_rejects_routed_failure_without_required_flag(
    tmp_path: Path,
) -> None:
    base_destinations = [_destination()]
    current_destinations = [_destination(region="Trentino-Alto Adige")]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )
    _add_passing_boundary_and_geometry(report, base_paths[0])
    assessment = report.destination_boundary_assessments[0]
    assessment.gates[0].status = "fail"
    assessment.failure_route = "blocked"

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(report, base_paths, current_paths)

    assert any(
        "reconcile mode requires a complete passing assessment" in issue
        for issue in error.value.issues
    )


def test_reconciliation_rejects_invented_report_change(tmp_path: Path) -> None:
    base_destinations = [_destination()]
    current_destinations = [_destination(region="Trentino-Alto Adige")]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "name",
                "Madonna di Campiglio",
                "Campiglio",
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(report, base_paths, current_paths)

    assert any(
        "report change has no snapshot delta" in issue for issue in error.value.issues
    )


def test_reconciliation_accepts_complete_delta_and_retained_decisions(
    tmp_path: Path,
) -> None:
    base_destinations = [_destination()]
    current_destinations = [_destination(region="Trentino-Alto Adige")]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )
    _add_passing_boundary_and_geometry(report, base_paths[0])

    result = _reconcile(
        report,
        base_paths,
        current_paths,
        required_boundary_targets=("madonna-di-campiglio",),
        required_weather_geometry_targets=("madonna-di-campiglio-ski-area",),
    )

    assert result.delta_count == 1
    assert result.required_boundary_target_count == 1
    assert result.required_weather_geometry_target_count == 1


def test_reconcile_cli_requires_all_snapshot_paths_before_rendering(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _report(
        [
            _estimated_change(
                "destination",
                "madonna-di-campiglio",
                "region",
                "Trentino",
                "Trentino-Alto Adige",
            )
        ]
    )
    report_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    report_path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")

    exit_code = validate_curation_main(
        [
            "--report-path",
            str(report_path),
            "--markdown-output",
            str(markdown_path),
            "--validation-mode",
            "reconcile",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "--base-resorts-path" in output
    assert not markdown_path.exists()

import json
from pathlib import Path

import pytest

from app.data import catalog_curation_reconciliation as reconciliation
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


def _destination_with_prices(prices: list[dict]) -> dict:
    destination = _destination()
    destination["lift_pass_products"] = [
        {
            "lift_pass_product_id": "campiglio-skipass",
            "name": "Campiglio Skipass",
            "validity_scope": "single_ski_area",
            "is_default": False,
            "valid_ski_area_ids": ["madonna-di-campiglio-ski-area"],
            "prices": prices,
        }
    ]
    return destination


def _price(duration_days: int, amount: float) -> dict:
    return {
        "duration_days": duration_days,
        "audience": "adult",
        "amount": amount,
        "currency": "EUR",
        "price_kind": "fixed",
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


def _report(
    changes: list[CatalogChangeSummary],
    *,
    include_boundary: bool = True,
) -> CatalogCurationReport:
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
    report = CatalogCurationReport(
        title="Catalog reconciliation fixture",
        summary="Reconciles a temporary catalog snapshot.",
        boundary_decision_targets=(
            ["madonna-di-campiglio"] if include_boundary else []
        ),
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
    if include_boundary:
        _add_passing_boundary(report)
    return report


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
    required_boundary_targets: tuple[str, ...] = ("madonna-di-campiglio",),
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


def _add_passing_boundary(
    report: CatalogCurationReport,
    destination_id: str = "madonna-di-campiglio",
) -> None:
    destination_target = next(
        (
            target
            for target in report.reviewed_targets
            if target.target_type == "destination"
            and target.target_id == destination_id
        ),
        None,
    )
    if destination_target is None:
        report.reviewed_targets.append(
            CatalogReviewedTarget(
                target_type="destination",
                target_id=destination_id,
                scope="narrow",
                required_field_paths=["resort_id"],
            )
        )
    elif "resort_id" not in destination_target.required_field_paths:
        destination_target.required_field_paths.append("resort_id")
    if not any(
        coverage.target_type == "destination"
        and coverage.target_id == destination_id
        and coverage.field_path == "resort_id"
        for coverage in report.field_coverage
    ):
        report.field_coverage.append(
            CatalogFieldCoverage(
                target_type="destination",
                target_id=destination_id,
                field_path="resort_id",
                status="reviewed-no-change",
            )
        )
    if not any(
        evidence.evidence_id == f"{destination_id}-boundary-official"
        for evidence in report.evidence
    ):
        identity_change = next(
            (
                change
                for change in report.changes
                if change.target_type == "destination"
                and change.target_id == destination_id
                and change.field_path == "resort_id"
            ),
            None,
        )
        report.evidence.append(
            CatalogEvidenceItem(
                evidence_id=f"{destination_id}-boundary-official",
                boundary_target_ids=[destination_id],
                target_type="destination",
                target_id=destination_id,
                field_path="resort_id",
                source_type="official",
                source_url=f"https://example.com/{destination_id}",
                source_title=f"Official {destination_id} destination page",
                source_value=destination_id,
                evidence_summary=(
                    "Official destination treatment and local ski access."
                ),
                normalization_note=(
                    "Boundary evidence retains the removed destination identity."
                    if identity_change is not None
                    and identity_change.after != destination_id
                    else None
                ),
            )
        )
    gates = [
        CatalogBoundaryGateAssessment(
            gate_name=gate_name,
            status="pass",
            notes=f"Reviewed {gate_name}.",
            evidence_refs=[f"{destination_id}-boundary-official"],
        )
        for gate_name in (
            "independent_stay_context",
            "independent_ski_access",
            "independent_recommendation_value",
        )
    ]
    if destination_id not in report.boundary_decision_targets:
        report.boundary_decision_targets.append(destination_id)
    report.destination_boundary_assessments = [
        assessment
        for assessment in report.destination_boundary_assessments
        if assessment.candidate_id != destination_id
    ]
    report.destination_boundary_assessments.append(
        CatalogDestinationBoundaryAssessment(
            candidate_id=destination_id,
            gates=gates,
            identity_signals=[
                CatalogIdentitySignalAssessment(
                    signal_type="official_destination_treatment",
                    status="pass",
                    notes="Official site presents the destination independently.",
                    evidence_refs=[f"{destination_id}-boundary-official"],
                )
            ],
        )
    )


def _report_for_snapshot_deltas(
    base_paths: tuple[Path, Path, Path],
    current_paths: tuple[Path, Path, Path],
) -> CatalogCurationReport:
    base = reconciliation._load_snapshot(
        resorts_path=base_paths[0],
        terrain_domains_path=base_paths[1],
        trust_manifest_path=base_paths[2],
        label="test base",
    )
    current = reconciliation._load_snapshot(
        resorts_path=current_paths[0],
        terrain_domains_path=current_paths[1],
        trust_manifest_path=current_paths[2],
        label="test current",
    )
    return _report(
        [
            _estimated_change(
                delta.target_type,
                delta.target_id,
                delta.field_path,
                delta.before,
                delta.after,
            )
            for delta in reconciliation._derive_deltas(base, current)
        ]
    )


def test_reconciliation_accepts_new_boundary_target_outside_base_snapshot(
    tmp_path: Path,
) -> None:
    base_destinations = [_destination()]
    current_destinations = [
        _destination(),
        _destination("pinzolo", name="Pinzolo"),
    ]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report_for_snapshot_deltas(base_paths, current_paths)
    _add_passing_boundary(report, "pinzolo")

    result = _reconcile(
        report,
        base_paths,
        current_paths,
        required_boundary_targets=("madonna-di-campiglio", "pinzolo"),
    )

    assert result.required_boundary_targets == (
        "madonna-di-campiglio",
        "pinzolo",
    )

    for omitted_target in ("madonna-di-campiglio", "pinzolo"):
        with pytest.raises(CatalogValidationError) as error:
            _reconcile(
                report,
                base_paths,
                current_paths,
                required_boundary_targets=tuple(
                    target
                    for target in ("madonna-di-campiglio", "pinzolo")
                    if target != omitted_target
                ),
            )

        assert any(
            "required_boundary_targets must exactly match" in issue
            for issue in error.value.issues
        )


def test_reconciliation_accepts_removed_boundary_target_outside_current_snapshot(
    tmp_path: Path,
) -> None:
    base_destinations = [
        _destination(),
        _destination("pinzolo", name="Pinzolo"),
    ]
    current_destinations = [_destination()]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report_for_snapshot_deltas(base_paths, current_paths)
    _add_passing_boundary(report, "pinzolo")

    result = _reconcile(
        report,
        base_paths,
        current_paths,
        required_boundary_targets=("madonna-di-campiglio", "pinzolo"),
    )

    assert result.required_boundary_targets == (
        "madonna-di-campiglio",
        "pinzolo",
    )
    assert result.required_weather_geometry_targets == ()


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


@pytest.mark.parametrize("operation", ["addition", "removal"])
def test_reconciliation_requires_exact_trust_source_ref_leaf_delta(
    tmp_path: Path,
    operation: str,
) -> None:
    destinations = [_destination()]
    source_url = "https://example.com/madonna-source"
    base_trust = _trust_manifest(destinations, [])
    current_trust = json.loads(json.dumps(base_trust))
    base_refs: list[str] = []
    current_refs = [source_url]
    if operation == "removal":
        base_refs, current_refs = current_refs, base_refs
    base_trust["destinations"]["madonna-di-campiglio"]["source_refs"] = base_refs
    current_trust["destinations"]["madonna-di-campiglio"]["source_refs"] = current_refs
    base_paths = _write_snapshot(
        tmp_path, "base", destinations=destinations, trust=base_trust
    )
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=destinations, trust=current_trust
    )
    parent_only_report = _report(
        [
            _estimated_change(
                "trust_manifest",
                "destination:madonna-di-campiglio",
                "source_refs",
                base_refs,
                current_refs,
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(parent_only_report, base_paths, current_paths)

    assert any(
        "source_refs: report change has no snapshot delta" in issue
        for issue in error.value.issues
    )

    exact_report = _report(
        [
            _estimated_change(
                "trust_manifest",
                "destination:madonna-di-campiglio",
                "source_refs[0]",
                None if operation == "addition" else source_url,
                source_url if operation == "addition" else None,
            )
        ]
    )

    result = _reconcile(exact_report, base_paths, current_paths)

    assert [delta.field_path for delta in result.deltas] == ["source_refs[0]"]


def test_reconciliation_ignores_scalar_set_reordering(tmp_path: Path) -> None:
    destinations = [_destination()]
    base_trust = _trust_manifest(destinations, [])
    current_trust = json.loads(json.dumps(base_trust))
    source_refs = ["https://example.com/source-b", "https://example.com/source-a"]
    base_trust["destinations"]["madonna-di-campiglio"]["source_refs"] = source_refs
    current_trust["destinations"]["madonna-di-campiglio"]["source_refs"] = list(
        reversed(source_refs)
    )
    base_paths = _write_snapshot(
        tmp_path, "base", destinations=destinations, trust=base_trust
    )
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=destinations, trust=current_trust
    )

    result = _reconcile(_report([]), base_paths, current_paths)

    assert result.deltas == ()


def test_reconciliation_requires_exact_price_object_addition_leaves(
    tmp_path: Path,
) -> None:
    base_destinations = [_destination()]
    base_destinations[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "campiglio-skipass",
            "name": "Campiglio Skipass",
            "validity_scope": "single_ski_area",
            "is_default": True,
            "valid_ski_area_ids": ["madonna-di-campiglio-ski-area"],
            "prices": [],
        }
    ]
    current_destinations = json.loads(json.dumps(base_destinations))
    current_destinations[0]["lift_pass_products"][0]["prices"] = [
        {
            "duration_days": 1,
            "audience": "adult",
            "amount": 79.0,
            "currency": "EUR",
            "price_kind": "fixed",
        }
    ]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    parent_only_report = _report(
        [
            _estimated_change(
                "lift_pass_product",
                "campiglio-skipass",
                "prices",
                [],
                [
                    {
                        "amount": 79.0,
                        "amount_max": None,
                        "amount_min": None,
                        "audience": "adult",
                        "currency": "EUR",
                        "duration_days": 1,
                        "price_kind": "fixed",
                        "season_label": None,
                        "source_url": None,
                    }
                ],
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(parent_only_report, base_paths, current_paths)

    assert any(
        "prices: report change has no snapshot delta" in issue
        for issue in error.value.issues
    )

    expected_leaf_values = {
        "amount": 79.0,
        "audience": "adult",
        "currency": "EUR",
        "duration_days": 1,
        "price_kind": "fixed",
    }
    exact_report = _report(
        [
            _estimated_change(
                "lift_pass_product",
                "campiglio-skipass",
                f"prices[0].{field_name}",
                None,
                value,
            )
            for field_name, value in expected_leaf_values.items()
        ]
    )

    result = _reconcile(exact_report, base_paths, current_paths)

    assert {delta.field_path for delta in result.deltas} == {
        f"prices[0].{field_name}" for field_name in expected_leaf_values
    }


def test_reconciliation_matches_prices_by_stable_identity(tmp_path: Path) -> None:
    base_destinations = [_destination_with_prices([_price(1, 100.0), _price(2, 500.0)])]
    current_destinations = [
        _destination_with_prices([_price(1, 600.0), _price(2, 500.0)])
    ]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "lift_pass_product",
                "campiglio-skipass",
                "prices[0].amount",
                100.0,
                600.0,
            )
        ]
    )

    result = _reconcile(report, base_paths, current_paths)

    assert [
        (delta.field_path, delta.before, delta.after) for delta in result.deltas
    ] == [("prices[0].amount", 100.0, 600.0)]


def test_reconciliation_ignores_price_reordering(tmp_path: Path) -> None:
    base_destinations = [_destination_with_prices([_price(1, 100.0), _price(2, 500.0)])]
    current_destinations = [
        _destination_with_prices([_price(2, 500.0), _price(1, 100.0)])
    ]
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )

    result = _reconcile(_report([]), base_paths, current_paths)

    assert result.deltas == ()


def test_reconciliation_rejects_duplicate_price_identity(tmp_path: Path) -> None:
    destinations = [_destination_with_prices([_price(1, 100.0), _price(1, 600.0)])]
    base_paths = _write_snapshot(tmp_path, "base", destinations=destinations)
    current_paths = _write_snapshot(tmp_path, "current", destinations=destinations)

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(_report([]), base_paths, current_paths)

    assert any("duplicate stable identity" in issue for issue in error.value.issues)


def test_reconciliation_json_equality_distinguishes_bool_from_number(
    tmp_path: Path,
) -> None:
    base_destination = _destination_with_prices([])
    current_destination = json.loads(json.dumps(base_destination))
    current_destination["lift_pass_products"][0]["is_default"] = True
    base_paths = _write_snapshot(tmp_path, "base", destinations=[base_destination])
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=[current_destination]
    )
    report = _report(
        [
            _estimated_change(
                "lift_pass_product",
                "campiglio-skipass",
                "is_default",
                False,
                1,
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(report, base_paths, current_paths)

    assert any(
        "report before/after does not match snapshot delta" in issue
        for issue in error.value.issues
    )


def test_reconciliation_json_equality_accepts_equivalent_numbers(
    tmp_path: Path,
) -> None:
    base_destinations = [_destination()]
    current_destinations = json.loads(json.dumps(base_destinations))
    current_destinations[0]["ski_areas"][0]["total_lift_count"] = 1
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "ski_area",
                "madonna-di-campiglio-ski-area",
                "total_lift_count",
                None,
                1.0,
            )
        ]
    )

    result = _reconcile(report, base_paths, current_paths)

    assert result.delta_count == 1


@pytest.mark.parametrize("operation", ["addition", "removal"])
def test_reconciliation_flattens_new_and_removed_lift_pass_nested_leaves(
    tmp_path: Path,
    operation: str,
) -> None:
    destination_without_pass = _destination()
    destination_with_pass = _destination()
    destination_with_pass["lift_pass_products"] = [
        {
            "lift_pass_product_id": "campiglio-skipass",
            "name": "Campiglio Skipass",
            "validity_scope": "single_ski_area",
            "is_default": True,
            "valid_ski_area_ids": ["madonna-di-campiglio-ski-area"],
            "prices": [
                {
                    "duration_days": 1,
                    "audience": "adult",
                    "amount": 79.0,
                    "currency": "EUR",
                    "price_kind": "fixed",
                }
            ],
        }
    ]
    base_destination = (
        destination_without_pass if operation == "addition" else destination_with_pass
    )
    current_destination = (
        destination_with_pass if operation == "addition" else destination_without_pass
    )
    base_paths = _write_snapshot(tmp_path, "base", destinations=[base_destination])
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=[current_destination]
    )
    price_record = {
        "amount": 79.0,
        "amount_max": None,
        "amount_min": None,
        "audience": "adult",
        "currency": "EUR",
        "duration_days": 1,
        "price_kind": "fixed",
        "season_label": None,
        "source_url": None,
    }

    def values(value: object) -> tuple[object, object]:
        return (None, value) if operation == "addition" else (value, None)

    parent_only_changes = [
        _estimated_change(
            "destination",
            "madonna-di-campiglio",
            "lift_pass_products[0]",
            *values("campiglio-skipass"),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "lift_pass_product_id",
            *values("campiglio-skipass"),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "name",
            *values("Campiglio Skipass"),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "validity_scope",
            *values("single_ski_area"),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "is_default",
            *values(True),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "valid_ski_area_ids",
            *values(["madonna-di-campiglio-ski-area"]),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "terrain_domain_ids",
            *values([]),
        ),
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "prices",
            *values([price_record]),
        ),
    ]

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(
            _report(parent_only_changes),
            base_paths,
            current_paths,
        )

    assert any(
        "prices: report change has no snapshot delta" in issue
        for issue in error.value.issues
    )

    price_leaf_values = {
        "amount": 79.0,
        "audience": "adult",
        "currency": "EUR",
        "duration_days": 1,
        "price_kind": "fixed",
    }
    exact_changes = [
        change
        for change in parent_only_changes
        if change.field_path not in {"valid_ski_area_ids", "prices"}
    ]
    exact_changes.append(
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            "valid_ski_area_ids[0]",
            *values("madonna-di-campiglio-ski-area"),
        )
    )
    exact_changes.extend(
        _estimated_change(
            "lift_pass_product",
            "campiglio-skipass",
            f"prices[0].{field_name}",
            *values(value),
        )
        for field_name, value in price_leaf_values.items()
    )

    result = _reconcile(
        _report(exact_changes),
        base_paths,
        current_paths,
    )

    assert {
        delta.field_path
        for delta in result.deltas
        if delta.target_type == "lift_pass_product"
        and delta.field_path.startswith("prices")
    } == {f"prices[0].{field_name}" for field_name in price_leaf_values}


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
        _estimated_change("destination", resort_id, "rentals[0]", before_id, None),
        _estimated_change("destination", resort_id, "rentals[1]", None, after_id),
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


def _add_weather_geometry(
    report: CatalogCurationReport,
    base_resorts_path: Path,
    current_resorts_path: Path,
    ski_area_id: str = "madonna-di-campiglio-ski-area",
) -> None:
    base_ski_area = next(
        ski_area
        for destination in load_resorts_from_path(base_resorts_path)
        for ski_area in destination.ski_areas
        if ski_area.ski_area_id == ski_area_id
    )
    current_ski_area = next(
        ski_area
        for destination in load_resorts_from_path(current_resorts_path)
        for ski_area in destination.ski_areas
        if ski_area.ski_area_id == ski_area_id
    )
    if not any(
        target.target_type == "ski_area" and target.target_id == ski_area_id
        for target in report.reviewed_targets
    ):
        report.reviewed_targets.append(
            CatalogReviewedTarget(
                target_type="ski_area",
                target_id=ski_area_id,
                scope="narrow",
                required_field_paths=["ski_area_id"],
            )
        )
        report.field_coverage.append(
            CatalogFieldCoverage(
                target_type="ski_area",
                target_id=ski_area_id,
                field_path="ski_area_id",
                status="reviewed-no-change",
            )
        )
    report.weather_request_geometry_targets = [ski_area_id]
    report.weather_request_geometry_assessments = [
        CatalogWeatherRequestGeometryAssessment(
            ski_area_id=ski_area_id,
            before=catalog_weather_request_geometry(base_ski_area),
            after=catalog_weather_request_geometry(current_ski_area),
        )
    ]


@pytest.mark.parametrize(
    ("field_path", "after"),
    [("longitude", 10.9), ("summit_elevation_m", 2600)],
)
def test_reconciliation_derives_retained_weather_geometry_targets(
    tmp_path: Path,
    field_path: str,
    after: float | int,
) -> None:
    base_destinations = [_destination()]
    current_destinations = json.loads(json.dumps(base_destinations))
    ski_area = current_destinations[0]["ski_areas"][0]
    before = ski_area[field_path]
    ski_area[field_path] = after
    base_paths = _write_snapshot(tmp_path, "base", destinations=base_destinations)
    current_paths = _write_snapshot(
        tmp_path, "current", destinations=current_destinations
    )
    report = _report(
        [
            _estimated_change(
                "ski_area",
                "madonna-di-campiglio-ski-area",
                field_path,
                before,
                after,
            )
        ]
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(report, base_paths, current_paths)

    assert any(
        "derived retained weather geometry targets" in issue
        for issue in error.value.issues
    )

    _add_weather_geometry(report, base_paths[0], current_paths[0])

    result = _reconcile(
        report,
        base_paths,
        current_paths,
        required_weather_geometry_targets=("madonna-di-campiglio-ski-area",),
    )

    assert result.required_weather_geometry_targets == (
        "madonna-di-campiglio-ski-area",
    )
    assert report.weather_request_geometry_assessments[0].material_change is True


def test_reconciliation_accepts_explicit_unchanged_retained_geometry(
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
    _add_weather_geometry(report, base_paths[0], current_paths[0])

    result = _reconcile(
        report,
        base_paths,
        current_paths,
        required_weather_geometry_targets=("madonna-di-campiglio-ski-area",),
    )

    assert result.required_weather_geometry_targets == (
        "madonna-di-campiglio-ski-area",
    )
    assert report.weather_request_geometry_assessments[0].material_change is False


def test_reconciliation_rejects_incorrect_unchanged_geometry_assessment(
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
    _add_weather_geometry(report, base_paths[0], current_paths[0])
    assessment = report.weather_request_geometry_assessments[0]
    assessment.after = assessment.after.model_copy(update={"longitude": 10.9})

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(
            report,
            base_paths,
            current_paths,
            required_weather_geometry_targets=("madonna-di-campiglio-ski-area",),
        )

    assert any(
        "weather geometry assessment does not match snapshots" in issue
        for issue in error.value.issues
    )


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
        ],
        include_boundary=False,
    )

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(
            report,
            base_paths,
            current_paths,
            required_boundary_targets=("madonna-di-campiglio",),
        )

    assert any(
        "required_boundary_targets must exactly match" in issue
        for issue in error.value.issues
    )


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


def test_reconciliation_rejects_routed_boundary_failure(
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
    assessment = report.destination_boundary_assessments[0]
    assessment.gates[0].status = "fail"
    assessment.failure_route = "blocked"

    with pytest.raises(CatalogValidationError) as error:
        _reconcile(
            report,
            base_paths,
            current_paths,
        )

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
    result = _reconcile(
        report,
        base_paths,
        current_paths,
        required_boundary_targets=("madonna-di-campiglio",),
    )

    assert result.delta_count == 1
    assert result.required_boundary_target_count == 1
    assert result.required_weather_geometry_target_count == 0


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


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ("[null]", "base resort snapshot"),
        ("{}", "must be a JSON list"),
        ("[", "Invalid JSON"),
    ],
)
def test_reconcile_cli_normalizes_malformed_snapshot_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    payload: str,
    expected_message: str,
) -> None:
    destinations = [_destination()]
    base_paths = _write_snapshot(tmp_path, "base", destinations=destinations)
    current_paths = _write_snapshot(tmp_path, "current", destinations=destinations)
    base_paths[0].write_text(payload, encoding="utf-8")
    report = _report([])
    report_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    report_path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")

    exit_code = validate_curation_main(
        _snapshot_cli_args(report_path, base_paths, current_paths)
        + [
            "--required-boundary-target",
            "madonna-di-campiglio",
            "--markdown-output",
            str(markdown_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "[catalog-curation-invalid]" in output
    assert expected_message in output
    assert "Traceback" not in output
    assert not markdown_path.exists()


def _snapshot_cli_args(
    report_path: Path,
    base_paths: tuple[Path, Path, Path],
    current_paths: tuple[Path, Path, Path],
) -> list[str]:
    return [
        "--report-path",
        str(report_path),
        "--validation-mode",
        "reconcile",
        "--base-resorts-path",
        str(base_paths[0]),
        "--current-resorts-path",
        str(current_paths[0]),
        "--base-terrain-domains-path",
        str(base_paths[1]),
        "--current-terrain-domains-path",
        str(current_paths[1]),
        "--base-trust-manifest-path",
        str(base_paths[2]),
        "--current-trust-manifest-path",
        str(current_paths[2]),
    ]


def test_reconcile_cli_requires_at_least_one_boundary_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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
    report_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    report_path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")
    argv = _snapshot_cli_args(report_path, base_paths, current_paths)
    argv.extend(["--markdown-output", str(markdown_path)])

    exit_code = validate_curation_main(argv)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "requires at least one required_boundary_target" in output
    assert not markdown_path.exists()


def test_reconcile_cli_rejects_omitted_declared_weather_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base_destinations = [_destination()]
    current_destinations = json.loads(json.dumps(base_destinations))
    current_destinations[0]["region"] = "Trentino-Alto Adige"
    current_destinations[0]["ski_areas"][0]["longitude"] = 10.9
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
            ),
            _estimated_change(
                "ski_area",
                "madonna-di-campiglio-ski-area",
                "longitude",
                10.8268,
                10.9,
            ),
        ]
    )
    _add_weather_geometry(report, base_paths[0], current_paths[0])
    report_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    report_path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")
    argv = _snapshot_cli_args(report_path, base_paths, current_paths)
    argv.extend(
        [
            "--required-boundary-target",
            "madonna-di-campiglio",
            "--markdown-output",
            str(markdown_path),
        ]
    )

    exit_code = validate_curation_main(argv)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "required_weather_geometry_targets must exactly match" in output
    assert not markdown_path.exists()


def test_reconcile_cli_accepts_empty_matching_weather_targets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")
    argv = _snapshot_cli_args(report_path, base_paths, current_paths)
    argv.extend(["--required-boundary-target", "madonna-di-campiglio"])

    exit_code = validate_curation_main(argv)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "mode=reconcile" in output

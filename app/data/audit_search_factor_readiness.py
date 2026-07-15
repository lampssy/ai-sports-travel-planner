from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.search_factors import build_factor_registry
from app.domain.search_factors.registry import FactorRegistry
from app.domain.search_policy import (
    DEFAULT_SEARCH_POLICY_PATH,
    FactorPolicy,
    SearchPolicy,
    load_search_policy,
)

DEFAULT_TRUST_MANIFEST_PATH = Path(__file__).with_name("resort_trust_manifest.json")
_SOURCE_STRENGTH = {
    "verified": 1.0,
    "verified_with_adjustment": 1.0,
    "estimated": 0.25,
    "needs_source": 0.0,
}
_SOURCE_BACKED = frozenset({"verified", "verified_with_adjustment"})


class ReadinessFactorReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    factor_id: str
    lifecycle: str
    evidence_mode: str
    evaluator_status: str
    readiness_status: str
    population_count: int = Field(ge=0)
    resolved_count: int = Field(ge=0)
    resolved_coverage: float = Field(ge=0, le=1)
    average_evidence_strength: float = Field(ge=0, le=1)
    verified_positive_count: int = Field(ge=0)
    distinct_trusted_utilities: int = Field(ge=0)
    comparable_slice_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()


class SearchFactorReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    search_model_version: str
    ranking_policy_version: str
    catalog_schema_version: int
    trust_manifest_version: str
    pass_duration_days: int
    pass_audience: str
    pass_season_label: str | None
    factors: tuple[ReadinessFactorReport, ...]


def build_readiness_report(
    *,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
    policy: SearchPolicy,
    registry: FactorRegistry,
    pass_duration_days: int,
    pass_audience: str,
    pass_season_label: str | None,
) -> SearchFactorReadinessReport:
    manifest.validate_against_catalog(snapshot)
    registered_ids = set(registry.factor_ids)
    rows = tuple(
        _factor_report(
            factor=factor,
            snapshot=snapshot,
            manifest=manifest,
            registered_ids=registered_ids,
            pass_duration_days=pass_duration_days,
            pass_audience=pass_audience,
            pass_season_label=pass_season_label,
        )
        for factor in policy.factors
    )
    return SearchFactorReadinessReport(
        search_model_version=policy.search_model_version,
        ranking_policy_version=policy.ranking_policy_version,
        catalog_schema_version=snapshot.schema_version,
        trust_manifest_version=manifest.version,
        pass_duration_days=pass_duration_days,
        pass_audience=pass_audience,
        pass_season_label=pass_season_label,
        factors=rows,
    )


def _factor_report(
    *,
    factor: FactorPolicy,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
    registered_ids: set[str],
    pass_duration_days: int,
    pass_audience: str,
    pass_season_label: str | None,
) -> ReadinessFactorReport:
    evaluator_status = (
        "registered"
        if factor.factor_id in registered_ids
        else "not_required"
        if factor.lifecycle in {"planned", "retired"}
        else "not_registered"
    )
    if factor.lifecycle in {"planned", "retired"}:
        return _empty_report(
            factor,
            evaluator_status=evaluator_status,
            readiness_status="not_applicable",
        )
    metrics = _collect_metrics(
        factor=factor,
        snapshot=snapshot,
        manifest=manifest,
        pass_duration_days=pass_duration_days,
        pass_audience=pass_audience,
        pass_season_label=pass_season_label,
    )
    readiness_status = _readiness_status(
        factor=factor,
        evaluator_status=evaluator_status,
        **metrics,
    )
    return ReadinessFactorReport(
        factor_id=factor.factor_id,
        lifecycle=factor.lifecycle,
        evidence_mode=factor.evidence_mode,
        evaluator_status=evaluator_status,
        readiness_status=readiness_status,
        **metrics,
    )


def _empty_report(
    factor: FactorPolicy,
    *,
    evaluator_status: str,
    readiness_status: str,
    notes: tuple[str, ...] = (),
) -> ReadinessFactorReport:
    return ReadinessFactorReport(
        factor_id=factor.factor_id,
        lifecycle=factor.lifecycle,
        evidence_mode=factor.evidence_mode,
        evaluator_status=evaluator_status,
        readiness_status=readiness_status,
        population_count=0,
        resolved_count=0,
        resolved_coverage=0,
        average_evidence_strength=0,
        verified_positive_count=0,
        distinct_trusted_utilities=0,
        comparable_slice_count=0,
        notes=notes,
    )


def _collect_metrics(
    *,
    factor: FactorPolicy,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
    pass_duration_days: int,
    pass_audience: str,
    pass_season_label: str | None,
) -> dict[str, object]:
    factor_id = factor.factor_id
    if factor_id in {
        "trip_window_snow_fit",
        "climatological_snow_reliability",
        "trip_window_snowpack_outlook",
    }:
        return _metrics(notes=("runtime weather evidence required",))
    if factor_id == "travel_effort":
        return _metrics(notes=("origin-specific route evidence required",))
    if factor_id == "party_skill_coverage":
        values = []
        for area in snapshot.ski_areas:
            status = _status(manifest, "ski_areas", area.ski_area_id, "skill_fit")
            if area.piste_km_by_difficulty is not None:
                values.append(_SOURCE_STRENGTH[status])
            elif area.supported_skill_levels:
                values.append(min(_SOURCE_STRENGTH[status], 0.25))
            else:
                values.append(None)
        return _comparative_metrics(values)
    if factor_id == "accessible_terrain_scale":
        values = [
            _pass_terrain_strength(product, snapshot, manifest)
            for product in snapshot.lift_pass_products
        ]
        return _comparative_metrics(values)
    if factor_id in {"terrain_potential_scale", "lift_network_scale"}:
        metric = (
            "total_piste_km"
            if factor_id == "terrain_potential_scale"
            else "total_lift_count"
        )
        values = [
            _area_or_domain_strength(area.ski_area_id, metric, snapshot, manifest)
            for area in snapshot.ski_areas
        ]
        return _comparative_metrics(values)
    if factor_id == "stay_base_access":
        values = [
            _SOURCE_STRENGTH[
                _status(
                    manifest,
                    "ski_area_access",
                    access.ski_area_access_id,
                    "access_mode_distance",
                )
            ]
            if access.access_mode != "unknown"
            else None
            for access in snapshot.ski_area_access
        ]
        return _comparative_metrics(values)
    if factor_id == "lodging_budget_fit":
        values = [
            _SOURCE_STRENGTH[
                _status(
                    manifest,
                    "stay_bases",
                    base.stay_base_id,
                    "lodging_price_quality",
                )
            ]
            for base in snapshot.stay_bases
        ]
        return _comparative_metrics(values)
    if factor_id in {"pass_price_per_day", "pass_terrain_value"}:
        return _pass_slice_metrics(
            factor_id=factor_id,
            snapshot=snapshot,
            manifest=manifest,
            duration_days=pass_duration_days,
            audience=pass_audience,
            season_label=pass_season_label,
        )
    if factor_id in {
        "marked_freeride_routes",
        "snow_park",
        "night_skiing",
        "glacier_terrain",
        "snowmaking_availability",
        "ski_day_apres",
    }:
        return _ski_area_presence_metrics(factor_id, snapshot, manifest)
    if factor_id == "local_apres":
        return _stay_base_presence_metrics(snapshot, manifest)
    if factor_id in {"local_pace", "development_style", "base_type"}:
        return _categorical_metrics(factor_id, snapshot, manifest)
    return _metrics(notes=("metric collector not implemented",))


def _metrics(
    *,
    population_count: int = 0,
    resolved_count: int = 0,
    average_evidence_strength: float = 0,
    verified_positive_count: int = 0,
    distinct_trusted_utilities: int = 0,
    comparable_slice_count: int = 0,
    notes: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "population_count": population_count,
        "resolved_count": resolved_count,
        "resolved_coverage": (
            resolved_count / population_count if population_count else 0
        ),
        "average_evidence_strength": average_evidence_strength,
        "verified_positive_count": verified_positive_count,
        "distinct_trusted_utilities": distinct_trusted_utilities,
        "comparable_slice_count": comparable_slice_count,
        "notes": notes,
    }


def _comparative_metrics(values: list[float | None]) -> dict[str, object]:
    resolved = [value for value in values if value is not None]
    return _metrics(
        population_count=len(values),
        resolved_count=len(resolved),
        average_evidence_strength=(sum(resolved) / len(resolved) if resolved else 0),
    )


def _pass_terrain_strength(
    product: object,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
) -> float | None:
    aggregate = getattr(product, "pass_accessible_terrain")
    product_id = getattr(product, "lift_pass_product_id")
    if aggregate is not None and aggregate.total_piste_km is not None:
        return _SOURCE_STRENGTH[
            _status(
                manifest,
                "lift_pass_products",
                product_id,
                "pass_accessible_terrain",
            )
        ]
    domain_ids = set(getattr(product, "terrain_domain_ids"))
    matching_domains = [
        domain
        for domain in snapshot.terrain_domains
        if domain.terrain_domain_id in domain_ids and domain.total_piste_km is not None
    ]
    if len(matching_domains) == 1:
        domain = matching_domains[0]
        return _SOURCE_STRENGTH[
            _status(
                manifest,
                "terrain_domains",
                domain.terrain_domain_id,
                "aggregate_terrain",
            )
        ]
    area_ids = set(getattr(product, "valid_ski_area_ids"))
    strengths = [
        _SOURCE_STRENGTH[
            _status(
                manifest,
                "ski_areas",
                area.ski_area_id,
                "terrain_metrics",
            )
        ]
        for area in snapshot.ski_areas
        if area.ski_area_id in area_ids and area.total_piste_km is not None
    ]
    return max(strengths) if strengths else None


def _area_or_domain_strength(
    area_id: str,
    metric: str,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
) -> float | None:
    area = next(item for item in snapshot.ski_areas if item.ski_area_id == area_id)
    sources: list[float] = []
    if getattr(area, metric) is not None:
        sources.append(
            _SOURCE_STRENGTH[_status(manifest, "ski_areas", area_id, "terrain_metrics")]
        )
    for domain in snapshot.terrain_domains:
        if area_id in domain.ski_area_ids and getattr(domain, metric) is not None:
            sources.append(
                _SOURCE_STRENGTH[
                    _status(
                        manifest,
                        "terrain_domains",
                        domain.terrain_domain_id,
                        "aggregate_terrain",
                    )
                ]
            )
    return max(sources) if sources else None


def _pass_slice_metrics(
    *,
    factor_id: str,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
    duration_days: int,
    audience: str,
    season_label: str | None,
) -> dict[str, object]:
    strengths: list[float | None] = []
    comparable = 0
    for product in snapshot.lift_pass_products:
        prices = [
            price
            for price in product.prices
            if price.duration_days == duration_days
            and _same_text(price.audience, audience)
            and price.price_kind != "unknown"
            and (
                season_label is None
                or (
                    price.season_label is not None
                    and _same_text(price.season_label, season_label)
                )
            )
        ]
        if not prices:
            strengths.append(None)
            continue
        strength = _SOURCE_STRENGTH[
            _status(
                manifest,
                "lift_pass_products",
                product.lift_pass_product_id,
                "prices",
            )
        ]
        if factor_id == "pass_terrain_value":
            terrain_strength = _pass_terrain_strength(product, snapshot, manifest)
            if terrain_strength is None:
                strengths.append(None)
                continue
            strength = min(strength, terrain_strength)
        strengths.append(strength)
        comparable += 1
    metrics = _comparative_metrics(strengths)
    metrics["comparable_slice_count"] = comparable
    return metrics


def _ski_area_presence_metrics(
    factor_id: str,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
) -> dict[str, object]:
    field_group = factor_id
    attribute = factor_id
    if factor_id == "snowmaking_availability":
        field_group = "snowmaking"
        attribute = "snowmaking"
    elif factor_id == "ski_day_apres":
        field_group = "ski_day_apres"
        attribute = "ski_day_apres_profile"
    strengths: list[float | None] = []
    positives = 0
    for area in snapshot.ski_areas:
        fact = getattr(area, attribute)
        status = _status(manifest, "ski_areas", area.ski_area_id, field_group)
        strengths.append(
            _SOURCE_STRENGTH[status] if fact.availability != "unknown" else None
        )
        if fact.availability == "available" and status in _SOURCE_BACKED:
            positives += 1
    metrics = _comparative_metrics(strengths)
    metrics["verified_positive_count"] = positives
    return metrics


def _stay_base_presence_metrics(
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
) -> dict[str, object]:
    strengths: list[float | None] = []
    positives = 0
    for base in snapshot.stay_bases:
        fact = base.local_apres_profile
        status = _status(manifest, "stay_bases", base.stay_base_id, "local_apres")
        strengths.append(
            _SOURCE_STRENGTH[status] if fact.availability != "unknown" else None
        )
        if fact.availability == "available" and status in _SOURCE_BACKED:
            positives += 1
    metrics = _comparative_metrics(strengths)
    metrics["verified_positive_count"] = positives
    return metrics


def _categorical_metrics(
    factor_id: str,
    snapshot: CatalogSnapshot,
    manifest: CatalogTrustManifest,
) -> dict[str, object]:
    values: list[float | None] = []
    trusted_values: set[str] = set()
    for base in snapshot.stay_bases:
        if factor_id == "base_type":
            value = base.base_type
            field_group = "base_type"
        elif factor_id == "local_pace":
            value = base.base_character.local_pace
            field_group = "base_character"
        else:
            value = base.base_character.development_style
            field_group = "base_character"
        status = _status(manifest, "stay_bases", base.stay_base_id, field_group)
        if value in {None, "unknown"}:
            values.append(None)
            continue
        strength = _SOURCE_STRENGTH[status]
        values.append(strength)
        if status in _SOURCE_BACKED:
            trusted_values.add(value)
    metrics = _comparative_metrics(values)
    metrics["distinct_trusted_utilities"] = len(trusted_values)
    return metrics


def _readiness_status(
    *,
    factor: FactorPolicy,
    evaluator_status: str,
    population_count: int,
    resolved_count: int,
    resolved_coverage: float,
    average_evidence_strength: float,
    verified_positive_count: int,
    distinct_trusted_utilities: int,
    comparable_slice_count: int,
    notes: tuple[str, ...],
) -> str:
    del population_count, resolved_count, comparable_slice_count, notes
    if evaluator_status != "registered":
        return "not_ready"
    readiness = factor.readiness
    if factor.evidence_mode in {"comparative", "objective_comparison"}:
        return (
            "ready"
            if resolved_coverage >= (readiness.minimum_resolved_coverage or 0)
            and average_evidence_strength
            >= (readiness.minimum_average_evidence_strength or 0)
            else "not_ready"
        )
    if factor.evidence_mode == "positive_presence":
        return (
            "ready"
            if verified_positive_count
            >= (readiness.minimum_verified_positive_count or 0)
            else "not_ready"
        )
    if factor.evidence_mode == "categorical_match":
        return (
            "ready"
            if distinct_trusted_utilities
            >= (readiness.minimum_distinct_trusted_utilities or 0)
            else "not_ready"
        )
    if factor.evidence_mode == "measured_only":
        return "measured"
    return "ready"


def _status(
    manifest: CatalogTrustManifest,
    entity_type: str,
    entity_id: str,
    field_group: str,
) -> str:
    return manifest.entities[entity_type][entity_id].field_statuses[field_group]  # type: ignore[index]


def _same_text(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Search V4 factor readiness against catalog evidence."
    )
    parser.add_argument("--catalog-path", type=Path, default=CATALOG_PATH)
    parser.add_argument(
        "--trust-manifest-path", type=Path, default=DEFAULT_TRUST_MANIFEST_PATH
    )
    parser.add_argument("--policy-path", type=Path, default=DEFAULT_SEARCH_POLICY_PATH)
    parser.add_argument("--duration-days", type=int, default=6)
    parser.add_argument("--audience", default="adult")
    parser.add_argument("--season")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    snapshot = load_catalog_from_path(args.catalog_path)
    manifest = CatalogTrustManifest.model_validate_json(
        args.trust_manifest_path.read_text(encoding="utf-8")
    )
    report = build_readiness_report(
        snapshot=snapshot,
        manifest=manifest,
        policy=load_search_policy(args.policy_path),
        registry=build_factor_registry(),
        pass_duration_days=args.duration_days,
        pass_audience=args.audience,
        pass_season_label=args.season,
    )
    if args.json:
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        for row in report.factors:
            print(
                f"{row.factor_id}: {row.readiness_status}; "
                f"coverage={row.resolved_coverage:.3f}; "
                f"strength={row.average_evidence_strength:.3f}; "
                f"positives={row.verified_positive_count}; "
                f"distinct={row.distinct_trusted_utilities}; "
                f"slices={row.comparable_slice_count}; "
                f"evaluator={row.evaluator_status}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

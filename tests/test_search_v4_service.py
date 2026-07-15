from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.data.audit_search_factor_readiness import DEFAULT_TRUST_MANIFEST_PATH
from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.domain.catalog_graph import CatalogGraph
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    LocationScope,
    LodgingBudgetConstraint,
    PartyContext,
    SearchConstraints,
    SearchIntent,
    TravelContext,
    TravelLimitConstraint,
    TravelWindow,
)
from app.domain.search_v4_service import (
    SearchV4Response,
    forecast_run_is_fresh,
    generate_v4_candidate_records,
    search_trip_configurations,
)
from app.domain.weather_forecast import WeatherForecastRun

pytestmark = pytest.mark.db_free


class _ClimatologyRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_daily_rows_for_ski_areas_window(self, ski_area_ids, **kwargs):
        self.calls.append({"ski_area_ids": ski_area_ids, **kwargs})
        return {
            (ski_area_id, "mid", baseline): ()
            for ski_area_id in ski_area_ids
            for baseline in ("normal_30y", "recent_15y")
        }


class _ForecastRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_latest_daily_rows(self, **kwargs):
        self.calls.append(kwargs)
        return ()


def _catalog_and_trust():
    snapshot = load_catalog_from_path(CATALOG_PATH)
    manifest = CatalogTrustManifest.model_validate_json(
        DEFAULT_TRUST_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    return snapshot, manifest


def _intent(**constraint_updates: object) -> SearchIntent:
    return SearchIntent(
        constraints=SearchConstraints(
            location=LocationScope(country="France"),
            travel_window=TravelWindow(
                start_date=date(2027, 1, 10),
                end_date=date(2027, 1, 12),
            ),
            **constraint_updates,
        ),
        party=PartyContext(skill_levels=("intermediate",)),
    )


def test_service_constrains_then_bulk_loads_weather_once_and_ranks() -> None:
    snapshot, manifest = _catalog_and_trust()
    climatology = _ClimatologyRepository()
    forecast = _ForecastRepository()

    result = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        include_refinements=False,
    )

    assert isinstance(result, SearchV4Response)
    assert result.search_model_version == "search-v4"
    assert result.ranking_policy_version == "search-v4-policy-1"
    assert result.ranking_status == "ranked"
    assert result.eligible_candidate_count > 0
    assert result.excluded_candidate_count > 0
    assert result.results
    assert result.results[0].top_configuration.fit_score is not None
    assert len(climatology.calls) == 1
    assert len(forecast.calls) == 1
    assert forecast.calls[0]["source_keys"] == (
        "ecmwf_ifs025_ensemble_mean",
        "ncep_gefs05_ensemble_mean",
    )
    assert len(forecast.calls[0]["ski_area_ids"]) == len(
        set(forecast.calls[0]["ski_area_ids"])
    )


def test_candidate_generation_expands_each_applicable_pass_without_default_bias() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()
    records = generate_v4_candidate_records(
        graph=CatalogGraph.from_snapshot(snapshot),
        intent=SearchIntent(),
        trust_manifest=manifest,
    )

    pass_ids_by_access: dict[str, set[str]] = {}
    for record in records:
        pass_ids_by_access.setdefault(record.access.ski_area_access_id, set()).add(
            record.selected_pass.lift_pass_product_id
        )

    assert any(len(pass_ids) > 1 for pass_ids in pass_ids_by_access.values())
    assert len({record.candidate_id for record in records}) == len(records)
    graph = CatalogGraph.from_snapshot(snapshot)
    for record in records:
        expected = set(record.selected_pass.valid_ski_area_ids)
        for domain_id in record.selected_pass.terrain_domain_ids:
            expected.update(graph.domains_by_id[domain_id].ski_area_ids)
        assert record.pass_covered_ski_area_ids == tuple(sorted(expected))
        expected_domain_ids = set(record.selected_pass.terrain_domain_ids)
        expected_domain_ids.update(
            domain.terrain_domain_id
            for domain in snapshot.terrain_domains
            if record.ski_area.ski_area_id in domain.ski_area_ids
        )
        assert {domain.terrain_domain_id for domain in record.terrain_domains} == (
            expected_domain_ids
        )


def test_estimate_aware_lodging_and_hard_travel_limits_filter_before_scoring() -> None:
    snapshot, manifest = _catalog_and_trust()
    climatology = _ClimatologyRepository()
    forecast = _ForecastRepository()
    budget_result = search_trip_configurations(
        intent=_intent(
            lodging_budget=LodgingBudgetConstraint(
                mode="lodging_nightly",
                maximum=1,
                currency="EUR",
            )
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        include_refinements=False,
    )
    travel_result = search_trip_configurations(
        intent=SearchIntent(
            constraints=SearchConstraints(
                location=LocationScope(country="France"),
                travel_limit=TravelLimitConstraint(
                    maximum_duration_hours=1,
                    mode="car",
                ),
            ),
            travel_context=TravelContext(origin_text="Berlin", mode="car"),
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        include_refinements=False,
    )

    assert budget_result.eligible_candidate_count == 0
    assert budget_result.results == ()
    assert travel_result.eligible_candidate_count == 0
    assert travel_result.results == ()


def test_forecast_freshness_uses_provider_update_interval_and_consistency_delay() -> (
    None
):
    available = datetime(2027, 1, 1, 7, tzinfo=UTC)
    run = WeatherForecastRun(
        forecast_run_id="run",
        forecast_source_key="ecmwf_ifs025_ensemble_mean",
        provider_gateway="open-meteo",
        producer="ecmwf",
        provider_model_id="ifs025",
        forecast_kind="ensemble_mean",
        model_initialization_time=datetime(2027, 1, 1, tzinfo=UTC),
        provider_availability_time=available,
        ingested_at=available + timedelta(minutes=10),
        completed_at=available + timedelta(minutes=15),
        first_valid_date=date(2027, 1, 1),
        last_valid_date=date(2027, 1, 16),
        status="complete",
        schema_version="forecast-v1",
        parser_version="open-meteo-v1",
        aggregation_policy_version="local-day-v1",
        provider_metadata={"update_interval_seconds": 21_600},
    )

    assert forecast_run_is_fresh(
        run,
        available + timedelta(hours=6, minutes=9),
    )
    assert not forecast_run_is_fresh(
        run,
        available + timedelta(hours=6, minutes=11),
    )


def test_service_validates_intent_even_when_constraints_exclude_every_candidate() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()

    with pytest.raises(ValueError, match="unknown factor ID"):
        search_trip_configurations(
            intent=SearchIntent(
                constraints=SearchConstraints(
                    location=LocationScope(country="Nowhere")
                ),
                factor_preferences=(
                    FactorPreferencePatch(
                        factor_id="invented",
                        mode="prefer",
                    ),
                ),
            ),
            catalog_snapshot=snapshot,
            trust_manifest=manifest,
            climatology_repository=_ClimatologyRepository(),
            forecast_repository=_ForecastRepository(),
            include_refinements=False,
        )

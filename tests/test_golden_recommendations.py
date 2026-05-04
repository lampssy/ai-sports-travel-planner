from datetime import UTC, date, datetime

from app.domain.models import (
    Destination,
    RawWeatherObservation,
    Rental,
    ResortConditions,
    SearchFilters,
    SkiArea,
    StayBase,
)
from app.domain.planning import derive_planning_assessment
from app.domain.search_service import search_resorts


class EmptyHistoryRepository:
    def list_snapshots_for_resort(self, resort_id: str):
        return ()


class EmptyRawHistoryRepository:
    def list_observations_for_resort(self, resort_id: str, **kwargs):
        return ()


class StaticConditionsProvider:
    def __init__(self, conditions: dict[str, ResortConditions | None]) -> None:
        self._conditions = conditions

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        return self._conditions.get(resort_name)


def _ski_area(
    resort_id: str,
    *,
    name: str | None = None,
    base: int = 1400,
    summit: int = 2800,
    season_end_month: int = 5,
) -> SkiArea:
    return SkiArea(
        ski_area_id=f"{resort_id}-ski-area",
        name=name or f"{resort_id.title()} Ski Area",
        latitude=46.5,
        longitude=7.4,
        base_elevation_m=base,
        summit_elevation_m=summit,
        season_start_month=12,
        season_end_month=season_end_month,
    )


def _stay_base(
    *,
    name: str = "Village Base",
    price_min: float = 160,
    price_max: float = 220,
    quality: str = "standard",
    lift_distance: str = "near",
    skill_levels: list[str] | None = None,
) -> StayBase:
    return StayBase(
        name=name,
        price_range=f"EUR {price_min:.0f}-{price_max:.0f}",
        price_min=price_min,
        price_max=price_max,
        quality=quality,
        lift_distance=lift_distance,
        supported_skill_levels=skill_levels or ["intermediate"],
    )


def _rental(
    *,
    name: str = "Rental Desk",
    price_min: float = 35,
    price_max: float = 55,
) -> Rental:
    return Rental(
        name=name,
        price_range=f"EUR {price_min:.0f}-{price_max:.0f}",
        price_min=price_min,
        price_max=price_max,
        quality="standard",
        lift_distance="near",
    )


def _destination(
    resort_id: str,
    *,
    country: str = "Goldenland",
    ski_area: SkiArea | None = None,
    stay_base: StayBase | None = None,
    rental: Rental | None = None,
) -> Destination:
    active_ski_area = ski_area or _ski_area(resort_id)
    return Destination(
        resort_id=resort_id,
        name=resort_id.replace("-", " ").title(),
        country=country,
        region="Golden Alps",
        price_level="medium",
        latitude=active_ski_area.latitude,
        longitude=active_ski_area.longitude,
        base_elevation_m=active_ski_area.base_elevation_m,
        summit_elevation_m=active_ski_area.summit_elevation_m,
        season_start_month=active_ski_area.season_start_month,
        season_end_month=active_ski_area.season_end_month,
        ski_areas=[active_ski_area],
        stay_bases=[stay_base or _stay_base()],
        rentals=[rental or _rental()],
    )


def _conditions(
    resort_name: str,
    *,
    snow_score: float = 0.82,
    conditions_score: float = 0.78,
    status: str = "open",
) -> ResortConditions:
    return ResortConditions(
        resort_name=resort_name,
        snow_confidence_score=snow_score,
        availability_status=status,
        weather_summary="Stable snow signal with manageable weather disruption risk.",
        conditions_score=conditions_score,
        source="open-meteo",
        updated_at="2026-04-20T12:00:00+00:00",
    )


def _raw_observation(
    ski_area: SkiArea,
    *,
    observed_on: str,
    snow_depth_m: float = 1.6,
    max_temp_c: float = -2.0,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        resort_id=ski_area.ski_area_id,
        resort_name=ski_area.name,
        elevation_band="mid",
        elevation_m=round(
            (ski_area.base_elevation_m + ski_area.summit_elevation_m) / 2
        ),
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=6,
        snow_depth_m=snow_depth_m,
        temperature_2m_max_c=max_temp_c,
        temperature_2m_min_c=max_temp_c - 6,
        wind_speed_10m_max_kmh=16,
        wind_gusts_10m_max_kmh=24,
        weather_code=3,
        record_type="archive",
        source="open-meteo",
        source_model="best_match",
    )


def test_budget_filter_uses_stay_base_price_not_rental_price() -> None:
    in_budget_area = _ski_area("stay-budget-expensive-rental")
    out_of_budget_area = _ski_area("stay-expensive-cheap-rental")
    in_budget = _destination(
        "stay-budget-expensive-rental",
        ski_area=in_budget_area,
        stay_base=_stay_base(price_min=180, price_max=200),
        rental=_rental(price_min=900, price_max=1000),
    )
    out_of_budget = _destination(
        "stay-expensive-cheap-rental",
        ski_area=out_of_budget_area,
        stay_base=_stay_base(price_min=420, price_max=480),
        rental=_rental(price_min=5, price_max=10),
    )

    results = search_resorts(
        SearchFilters(
            location="Goldenland",
            min_price=150,
            max_price=220,
            stars=1,
            skill_level="intermediate",
        ),
        resorts=(in_budget, out_of_budget),
        conditions_provider=StaticConditionsProvider(
            {
                in_budget_area.name: _conditions(in_budget_area.name),
                out_of_budget_area.name: _conditions(out_of_budget_area.name),
            }
        ),
        condition_history_repository=EmptyHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert [result.resort_id for result in results] == ["stay-budget-expensive-rental"]


def test_beginner_skill_fit_excludes_advanced_only_destinations() -> None:
    beginner_area = _ski_area("beginner-basin")
    advanced_area = _ski_area("expert-ridge")
    beginner = _destination(
        "beginner-basin",
        ski_area=beginner_area,
        stay_base=_stay_base(skill_levels=["beginner", "intermediate"]),
    )
    advanced = _destination(
        "expert-ridge",
        ski_area=advanced_area,
        stay_base=_stay_base(skill_levels=["advanced"]),
    )

    results = search_resorts(
        SearchFilters(
            location="Goldenland",
            min_price=140,
            max_price=260,
            stars=1,
            skill_level="beginner",
        ),
        resorts=(beginner, advanced),
        conditions_provider=StaticConditionsProvider(
            {
                beginner_area.name: _conditions(beginner_area.name, snow_score=0.65),
                advanced_area.name: _conditions(advanced_area.name, snow_score=0.95),
            }
        ),
        condition_history_repository=EmptyHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert [result.resort_id for result in results] == ["beginner-basin"]


def test_sparse_evidence_is_labeled_as_fallback_heavy() -> None:
    ski_area = _ski_area("sparse-evidence")
    resort = _destination("sparse-evidence", ski_area=ski_area)

    results = search_resorts(
        SearchFilters(
            location="Goldenland",
            min_price=140,
            max_price=260,
            stars=1,
            skill_level="intermediate",
            travel_month=4,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider({ski_area.name: None}),
        condition_history_repository=EmptyHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert results
    assert results[0].planning_provenance is not None
    assert results[0].planning_provenance.evidence_profile == "fallback_heavy"
    assert results[0].planning_provenance.source_type == "estimated"


def test_search_does_not_emit_reported_provenance_without_reported_provider() -> None:
    ski_area = _ski_area("forecast-only")
    resort = _destination("forecast-only", ski_area=ski_area)

    results = search_resorts(
        SearchFilters(
            location="Goldenland",
            min_price=140,
            max_price=260,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(
            {ski_area.name: _conditions(ski_area.name)}
        ),
        condition_history_repository=EmptyHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert results
    assert results[0].conditions_provenance.source_type != "reported"
    assert results[0].planning_provenance is not None
    assert results[0].planning_provenance.source_type != "reported"


def test_late_spring_high_elevation_destination_beats_low_elevation_peer() -> None:
    high_area = _ski_area("high-spring", base=2300, summit=3600, season_end_month=5)
    low_area = _ski_area("low-spring", base=900, summit=1800, season_end_month=5)

    high = _destination("high-spring", ski_area=high_area)
    low = _destination("low-spring", ski_area=low_area)

    results = search_resorts(
        SearchFilters(
            location="Goldenland",
            min_price=140,
            max_price=260,
            stars=1,
            skill_level="intermediate",
            travel_month=5,
        ),
        resorts=(low, high),
        conditions_provider=StaticConditionsProvider(
            {
                high_area.name: _conditions(high_area.name, snow_score=0.55),
                low_area.name: _conditions(low_area.name, snow_score=0.55),
            }
        ),
        condition_history_repository=EmptyHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert results[0].resort_id == "high-spring"
    assert results[0].score > results[-1].score


def test_exact_date_planning_distinguishes_forecast_assisted_from_archive_backed() -> (
    None
):
    ski_area = _ski_area("date-window")
    observations = (
        _raw_observation(ski_area, observed_on="2024-04-09"),
        _raw_observation(ski_area, observed_on="2025-04-10"),
    )

    archive_only = derive_planning_assessment(
        resort=ski_area,
        snapshots=(),
        raw_weather_observations=observations,
        trip_start_date=date(2026, 4, 9),
        trip_end_date=date(2026, 4, 16),
        reference_date=datetime(2026, 1, 1, tzinfo=UTC),
    )
    near_trip = derive_planning_assessment(
        resort=ski_area,
        snapshots=(),
        raw_weather_observations=observations,
        current_conditions=_conditions(ski_area.name),
        trip_start_date=date(2026, 4, 9),
        trip_end_date=date(2026, 4, 16),
        reference_date=datetime(2026, 4, 1, tzinfo=UTC),
    )

    assert archive_only.evidence_profile == "archive_backed"
    assert near_trip.evidence_profile == "forecast_assisted"

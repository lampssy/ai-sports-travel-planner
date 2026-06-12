from datetime import UTC, date, datetime

from app.ai.narrative import RecommendationNarrativeGenerator
from app.data.repositories import get_resort_repository
from app.domain.models import (
    Destination,
    RawWeatherObservation,
    Rental,
    ResortConditions,
    ResortConditionSnapshot,
    SearchFilters,
    SkiArea,
    StayBase,
    WeatherElevationBand,
)
from app.domain.planning import (
    _current_signal_weight,
    derive_planning_assessment,
    derive_weather_evidence_metrics,
)
from app.domain.planning_policy import (
    DEFAULT_PLANNING_HEURISTIC_POLICY,
    PLANNING_HEURISTIC_VERSION,
)
from app.domain.search_service import _build_planning_provenance, search_resorts


def _raw_weather_observation(
    *,
    observed_on: str,
    snowfall_cm: float,
    snow_depth_m: float | None,
    max_temp_c: float,
    gust_kmh: float,
    record_type: str = "archive",
    resort_id: str = "tignes",
    resort_name: str = "Tignes",
    elevation_band: WeatherElevationBand = "mid",
    elevation_m: int | None = 2500,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        resort_id=resort_id,
        resort_name=resort_name,
        elevation_band=elevation_band,
        elevation_m=elevation_m,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=snowfall_cm,
        snow_depth_m=snow_depth_m,
        temperature_2m_max_c=max_temp_c,
        temperature_2m_min_c=max_temp_c - 6,
        wind_speed_10m_max_kmh=max(gust_kmh - 8, 0),
        wind_gusts_10m_max_kmh=gust_kmh,
        weather_code=3,
        record_type=record_type,
        source="open-meteo",
        source_model="best_match",
    )


def _multi_stay_base_tignes() -> Destination:
    ski_area = SkiArea(
        ski_area_id="tignes-ski-area",
        name="Tignes",
        latitude=45.4696,
        longitude=6.9055,
        base_elevation_m=1550,
        summit_elevation_m=3456,
        season_start_month=11,
        season_end_month=5,
    )
    return Destination(
        resort_id="tignes",
        name="Tignes",
        country="France",
        region="Savoie",
        price_level="high",
        latitude=ski_area.latitude,
        longitude=ski_area.longitude,
        base_elevation_m=ski_area.base_elevation_m,
        summit_elevation_m=ski_area.summit_elevation_m,
        season_start_month=ski_area.season_start_month,
        season_end_month=ski_area.season_end_month,
        rentals=[
            Rental(
                name="Tignes Spirit",
                price_range="EUR 50-75",
                price_min=50,
                price_max=75,
                quality="standard",
                lift_distance="near",
            )
        ],
        stay_bases=[
            StayBase(
                stay_base_id="tignes-le-lac",
                name="Le Lac",
                price_range="EUR 210-310",
                price_min=210,
                price_max=310,
                quality="premium",
                lift_distance="near",
                supported_skill_levels=["intermediate", "advanced"],
            ),
            StayBase(
                stay_base_id="tignes-val-claret",
                name="Val Claret",
                price_range="EUR 180-260",
                price_min=180,
                price_max=260,
                quality="premium",
                lift_distance="medium",
                supported_skill_levels=["intermediate", "advanced"],
            ),
            StayBase(
                stay_base_id="tignes-1800",
                name="Tignes 1800",
                price_range="EUR 160-240",
                price_min=160,
                price_max=240,
                quality="standard",
                lift_distance="near",
                supported_skill_levels=["intermediate", "advanced"],
            ),
            StayBase(
                stay_base_id="tignes-les-brevieres",
                name="Les Brevieres",
                price_range="EUR 130-190",
                price_min=130,
                price_max=190,
                quality="budget",
                lift_distance="far",
                supported_skill_levels=["intermediate", "advanced"],
            ),
        ],
        ski_areas=[ski_area],
    )


def _multi_ski_area_tignes() -> Destination:
    destination = _multi_stay_base_tignes()
    grande_motte = SkiArea(
        ski_area_id="grande-motte-ski-area",
        name="Grande Motte",
        latitude=45.456,
        longitude=6.903,
        base_elevation_m=2100,
        summit_elevation_m=3456,
        season_start_month=11,
        season_end_month=5,
    )
    return destination.model_copy(
        update={"ski_areas": [destination.ski_areas[0], grande_motte]}
    )


class StaticConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
        return ResortConditions(
            resort_name=resort_name,
            snow_confidence_score=0.7,
            snow_confidence_label="good",
            availability_status="open",
            weather_summary="Good current signal.",
            conditions_score=0.7,
            updated_at="2026-05-06T21:43:00+00:00",
            source="test",
        )


class EmptyConditionHistoryRepository:
    def list_snapshots_for_resort(self, resort_id: str) -> tuple:
        return ()


class CountingRawHistoryRepository:
    def __init__(self, observations: tuple[RawWeatherObservation, ...]) -> None:
        self.observations = observations
        self.single_calls: list[tuple[str, str | None]] = []
        self.batch_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def list_observations_for_resort(
        self,
        resort_id: str,
        *,
        elevation_band: str | None = None,
    ) -> tuple[RawWeatherObservation, ...]:
        self.single_calls.append((resort_id, elevation_band))
        if elevation_band != "mid":
            return ()
        return tuple(
            observation
            for observation in self.observations
            if observation.resort_id == resort_id
            and observation.elevation_band == elevation_band
        )

    def list_observations_for_resorts(
        self,
        resort_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[str, ...],
    ) -> dict[tuple[str, str], tuple[RawWeatherObservation, ...]]:
        self.batch_calls.append((resort_ids, elevation_bands))
        grouped: dict[tuple[str, str], list[RawWeatherObservation]] = {
            (resort_id, elevation_band): []
            for resort_id in resort_ids
            for elevation_band in elevation_bands
        }
        for observation in self.observations:
            key = (observation.resort_id, observation.elevation_band)
            if key in grouped:
                grouped[key].append(observation)
        return {key: tuple(value) for key, value in grouped.items()}


class StableConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
        return ResortConditions(
            resort_name=resort_name,
            snow_confidence_score=0.78,
            availability_status="open",
            weather_summary="Stable snow signal with manageable weather risk.",
            conditions_score=0.76,
            updated_at="2026-01-15T12:00:00+00:00",
            source="open-meteo",
        )


def test_search_resorts_matches_location_case_insensitively() -> None:
    results = search_resorts(
        SearchFilters(
            location="france",
            min_price=150,
            max_price=260,
            stars=2,
            skill_level="intermediate",
        )
    )

    assert results
    assert all("france" in result.link.lower() for result in results)
    assert all(result.conditions_summary for result in results)
    assert all(result.explanation.highlights for result in results)
    assert all(
        result.snow_confidence_label in {"poor", "fair", "good"} for result in results
    )
    assert all(result.travel_effort is None for result in results)


def test_search_resorts_does_not_resolve_travel_cache_without_origin(
    monkeypatch,
) -> None:
    def fail_if_called(**kwargs):
        raise AssertionError("travel effort should not be assessed without origin_text")

    monkeypatch.setattr(
        "app.domain.search_service.assess_deterministic_travel_effort",
        fail_if_called,
    )

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=260,
            stars=2,
            skill_level="intermediate",
        )
    )

    assert results
    assert all(result.travel_effort is None for result in results)


def test_search_resorts_with_origin_uses_deterministic_travel_without_cache(
    monkeypatch,
) -> None:
    resort = _multi_stay_base_tignes()

    def fail_if_persistent_cache_path_is_used(**kwargs):
        raise AssertionError("persistent travel cache path should not be used")

    monkeypatch.setattr(
        "app.domain.search_service.assess_travel_effort",
        fail_if_persistent_cache_path_is_used,
    )

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
            origin_text="Berlin",
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=CountingRawHistoryRepository(()),
    )

    assert results
    assert results[0].travel_effort is not None
    assert results[0].travel_effort.origin_label == "Berlin"
    assert results[0].travel_effort.provider == "approximate_haversine_v2"


def test_search_resorts_with_origin_returns_travel_effort() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            origin_text="Munich",
        )
    )

    assert results
    assert all(result.travel_effort is not None for result in results)
    assert all(
        result.travel_effort.origin_label == "Munich"
        for result in results
        if result.travel_effort is not None
    )
    assert any(
        "drive from Munich" in item.label
        for result in results
        for item in result.explanation.highlights + result.explanation.risks
    )


def test_search_resorts_excludes_destinations_beyond_max_drive() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            origin_text="Munich",
            max_drive_minutes=1,
        )
    )

    assert results == []


def test_search_resorts_excludes_unsuitable_skill_levels() -> None:
    results = search_resorts(
        SearchFilters(
            location="Switzerland",
            min_price=200,
            max_price=320,
            stars=2,
            skill_level="beginner",
        )
    )

    assert results == []


def test_search_resorts_uses_lift_distance_filter_and_ranking() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=260,
            stars=1,
            skill_level="intermediate",
            lift_distance="near",
        )
    )

    assert results
    assert all(result.selected_stay_base_lift_distance == "near" for result in results)
    assert results[0].selected_stay_base_name


def test_search_resorts_allows_budget_flex_with_penalty() -> None:
    strict_results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=145,
            max_price=145,
            stars=2,
            skill_level="intermediate",
        )
    )
    flex_results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=145,
            max_price=145,
            stars=2,
            skill_level="intermediate",
            budget_flex=0.2,
        )
    )

    assert strict_results == []
    assert flex_results
    assert all(result.budget_penalty > 0 for result in flex_results)


def test_search_resorts_returns_stable_descending_order() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            lift_distance="medium",
        )
    )

    assert results
    assert [result.score for result in results] == sorted(
        [result.score for result in results],
        reverse=True,
    )
    assert all("france" in result.link.lower() for result in results)


def test_search_resorts_includes_structured_explanation_and_confidence() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert results
    top_result = results[0]
    assert 0 <= top_result.recommendation_confidence <= 1
    assert top_result.explanation.highlights
    assert top_result.explanation.confidence_contributors
    assert 0 <= top_result.snow_confidence_score <= 1
    assert any(
        "snow" in item.label.lower() or "conditions" in item.label.lower()
        for item in top_result.explanation.highlights + top_result.explanation.risks
    )


def test_search_result_exposes_top_option_and_empty_alternatives() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert results
    top_result = results[0]
    assert top_result.top_option is not None
    assert top_result.top_option.stay_base_name == top_result.selected_stay_base_name
    assert top_result.top_option.ski_area_id == top_result.selected_ski_area_id
    assert top_result.top_option.ski_area_name == top_result.selected_ski_area_name
    assert top_result.top_option.score == top_result.score
    assert isinstance(top_result.alternative_options, list)
    assert top_result.alternative_options == []


def test_search_groups_stay_base_alternatives_under_one_result() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        ),
        resorts=(_multi_stay_base_tignes(),),
        conditions_provider=StableConditionsProvider(),
    )

    tignes = next(result for result in results if result.resort_id == "tignes")

    assert len(results) == 1
    assert tignes.resort_id == "tignes"
    assert tignes.top_option is not None
    assert tignes.top_option.stay_base_name == "Le Lac"
    assert len(tignes.alternative_options) == 3
    assert [option.stay_base_name for option in tignes.alternative_options] == [
        "Val Claret",
        "Tignes 1800",
        "Les Brevieres",
    ]
    assert all(
        alternative.stay_base_name != tignes.top_option.stay_base_name
        for alternative in tignes.alternative_options
    )
    assert len({option.stay_base_name for option in tignes.alternative_options}) == len(
        tignes.alternative_options
    )
    assert all(
        alternative.score <= tignes.top_option.score
        for alternative in tignes.alternative_options
    )
    assert [option.score for option in tignes.alternative_options] == sorted(
        [option.score for option in tignes.alternative_options],
        reverse=True,
    )


def test_search_groups_stay_base_alternatives_by_ski_area_context() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        ),
        resorts=(_multi_ski_area_tignes(),),
        conditions_provider=StableConditionsProvider(),
    )

    group_keys = [(result.resort_id, result.selected_ski_area_id) for result in results]

    assert len(results) == 2
    assert len(group_keys) == len(set(group_keys))
    assert {result.selected_ski_area_id for result in results} == {
        "tignes-ski-area",
        "grande-motte-ski-area",
    }
    for result in results:
        assert result.top_option is not None
        assert result.top_option.ski_area_id == result.selected_ski_area_id
        assert len(result.alternative_options) == 3
        assert len(
            {option.stay_base_name for option in result.alternative_options}
        ) == len(result.alternative_options)
        assert all(
            option.ski_area_id == result.selected_ski_area_id
            for option in result.alternative_options
        )
        assert [option.score for option in result.alternative_options] == sorted(
            [option.score for option in result.alternative_options],
            reverse=True,
        )


def test_search_does_not_return_duplicate_resort_cards_by_default() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        ),
        resorts=(_multi_stay_base_tignes(),),
        conditions_provider=StableConditionsProvider(),
    )

    resort_ids = [result.resort_id for result in results]

    assert resort_ids == ["tignes"]
    assert len(resort_ids) == len(set(resort_ids))


def test_search_resorts_frames_poor_snow_as_risk_and_negative_contributor() -> None:
    class StubConditionsProvider:
        def get_conditions_for_resort(
            self, resort_name: str
        ) -> ResortConditions | None:
            if resort_name == "Tignes":
                return ResortConditions(
                    resort_name="Tignes",
                    snow_confidence_score=0.22,
                    availability_status="limited",
                    weather_summary="Poor snow outlook with warm temperatures.",
                    conditions_score=0.11,
                    updated_at="2026-04-07T10:00:00+00:00",
                    source="open-meteo",
                )
            return None

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=140,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        conditions_provider=StubConditionsProvider(),
    )

    tignes = next(result for result in results if result.resort_name == "Tignes")

    assert not any(
        contributor.label.lower().startswith("snow outlook")
        and contributor.direction == "positive"
        for contributor in tignes.explanation.confidence_contributors
    )
    assert any("poor" in risk.label.lower() for risk in tignes.explanation.risks)
    assert any(
        contributor.direction == "negative" and "snow" in contributor.label.lower()
        for contributor in tignes.explanation.confidence_contributors
    )


def test_search_resorts_keeps_fair_snow_outlook_out_of_positive_contributors() -> None:
    class StubConditionsProvider:
        def get_conditions_for_resort(
            self, resort_name: str
        ) -> ResortConditions | None:
            if resort_name == "Tignes":
                return ResortConditions(
                    resort_name="Tignes",
                    snow_confidence_score=0.48,
                    availability_status="open",
                    weather_summary="Fair snow outlook with calm weather.",
                    conditions_score=0.53,
                    updated_at="2026-04-07T10:00:00+00:00",
                    source="open-meteo",
                )
            return None

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=140,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        conditions_provider=StubConditionsProvider(),
    )

    tignes = next(result for result in results if result.resort_name == "Tignes")

    assert any("fair" in item.label.lower() for item in tignes.explanation.highlights)
    assert not any(
        contributor.label.lower().startswith("snow outlook")
        for contributor in tignes.explanation.confidence_contributors
    )


def test_search_resorts_uses_conditions_signal_in_ranking() -> None:
    class StubConditionsProvider:
        def __init__(self) -> None:
            self._conditions = {
                "Tignes": ResortConditions(
                    resort_name="Tignes",
                    snow_confidence_score=0.91,
                    availability_status="open",
                    weather_summary="Strong snow signal.",
                    conditions_score=0.88,
                    updated_at="2026-04-07T10:00:00+00:00",
                    source="open-meteo",
                ),
                "Chamonix Mont-Blanc": ResortConditions(
                    resort_name="Chamonix Mont-Blanc",
                    snow_confidence_score=0.42,
                    availability_status="limited",
                    weather_summary="Mixed snow signal.",
                    conditions_score=0.36,
                    updated_at="2026-04-07T10:00:00+00:00",
                    source="open-meteo",
                ),
            }

        def get_conditions_for_resort(
            self, resort_name: str
        ) -> ResortConditions | None:
            return self._conditions.get(resort_name)

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        conditions_provider=StubConditionsProvider(),
    )

    ranked = {result.resort_name: result for result in results}
    assert (
        ranked["Tignes"].conditions_score
        > ranked["Chamonix Mont-Blanc"].conditions_score
    )
    assert (
        ranked["Tignes"].snow_confidence_score
        > ranked["Chamonix Mont-Blanc"].snow_confidence_score
    )
    assert ranked["Tignes"].conditions_provenance.source_type == "forecast"
    assert results.index(ranked["Tignes"]) < results.index(
        ranked["Chamonix Mont-Blanc"]
    )


def test_search_resorts_excludes_out_of_season_resorts() -> None:
    class StubConditionsProvider:
        def get_conditions_for_resort(
            self, resort_name: str
        ) -> ResortConditions | None:
            if resort_name == "La Plagne":
                return ResortConditions(
                    resort_name="La Plagne",
                    snow_confidence_score=0.18,
                    availability_status="out_of_season",
                    weather_summary="Out of season.",
                    conditions_score=0.08,
                    updated_at="2026-04-07T10:00:00+00:00",
                    source="open-meteo",
                )
            return None

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=110,
            max_price=220,
            stars=1,
            skill_level="beginner",
        ),
        conditions_provider=StubConditionsProvider(),
    )

    assert all(result.resort_name != "La Plagne" for result in results)


def test_search_resorts_uses_travel_month_history_in_ranking() -> None:
    class StubHistoryRepository:
        def __init__(self) -> None:
            self._snapshots = {
                "tignes": (
                    ResortConditionSnapshot(
                        resort_id="tignes",
                        resort_name="Tignes",
                        observed_month=2,
                        observed_at="2026-02-10T00:00:00+00:00",
                        snow_confidence_score=0.9,
                        snow_confidence_label="good",
                        availability_status="open",
                        weather_summary="Strong February signal.",
                        conditions_score=0.88,
                        source="open-meteo",
                    ),
                ),
                "chamonix-mont-blanc": (
                    ResortConditionSnapshot(
                        resort_id="chamonix-mont-blanc",
                        resort_name="Chamonix Mont-Blanc",
                        observed_month=2,
                        observed_at="2026-02-10T00:00:00+00:00",
                        snow_confidence_score=0.45,
                        snow_confidence_label="fair",
                        availability_status="limited",
                        weather_summary="Mixed February signal.",
                        conditions_score=0.42,
                        source="open-meteo",
                    ),
                ),
            }

        def list_snapshots_for_resort(self, resort_id: str):
            return self._snapshots.get(resort_id, ())

    class EmptyRawHistoryRepository:
        def list_observations_for_resort(self, resort_id: str, **kwargs):
            return ()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=2,
        ),
        resorts=tuple(
            resort
            for resort in get_resort_repository().list_resorts()
            if resort.resort_id in {"tignes", "chamonix-mont-blanc"}
        ),
        condition_history_repository=StubHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert results
    assert results[0].resort_name == "Tignes"
    assert results[0].planning_summary is not None
    assert results[0].planning_provenance is not None
    assert results[0].planning_provenance.freshness_status == "historical"
    assert results[0].planning_evidence_count == 1
    assert results[0].best_travel_months


def test_search_resorts_degrades_gracefully_with_sparse_month_history() -> None:
    class EmptyHistoryRepository:
        def list_snapshots_for_resort(self, resort_id: str):
            return ()

    class EmptyRawHistoryRepository:
        def list_observations_for_resort(self, resort_id: str, **kwargs):
            return ()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=4,
        ),
        condition_history_repository=EmptyHistoryRepository(),
        raw_weather_history_repository=EmptyRawHistoryRepository(),
    )

    assert results
    assert results[0].planning_summary is not None
    assert results[0].planning_provenance is not None
    assert results[0].planning_provenance.freshness_status == "unknown"
    assert "historical weather data is limited" in results[0].planning_summary.lower()
    assert results[0].planning_evidence_count == 0


def test_search_resorts_reuses_raw_weather_across_matching_stay_bases() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]
    raw_repository = CountingRawHistoryRepository(
        (
            _raw_weather_observation(
                resort_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                elevation_band="mid",
                observed_on="2024-03-05",
                snowfall_cm=8,
                snow_depth_m=1.2,
                max_temp_c=-3,
                gust_kmh=22,
            ),
            _raw_weather_observation(
                resort_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                elevation_band="mid",
                observed_on="2025-03-07",
                snowfall_cm=7,
                snow_depth_m=1.1,
                max_temp_c=-2,
                gust_kmh=25,
            ),
        )
    )

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=raw_repository,
    )

    assert results
    assert raw_repository.single_calls == []
    assert raw_repository.batch_calls == [
        ((ski_area.ski_area_id,), ("mid", "upper", "base"))
    ]


def test_search_resorts_single_repository_fallback_still_caches_per_request() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]

    class SingleOnlyRawHistoryRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        def list_observations_for_resort(
            self,
            resort_id: str,
            *,
            elevation_band: str | None = None,
        ) -> tuple[RawWeatherObservation, ...]:
            self.calls.append((resort_id, elevation_band))
            if resort_id != ski_area.ski_area_id or elevation_band != "mid":
                return ()
            return (
                _raw_weather_observation(
                    resort_id=ski_area.ski_area_id,
                    resort_name=ski_area.name,
                    elevation_band="mid",
                    observed_on="2024-03-05",
                    snowfall_cm=8,
                    snow_depth_m=1.2,
                    max_temp_c=-3,
                    gust_kmh=22,
                ),
            )

    raw_repository = SingleOnlyRawHistoryRepository()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=raw_repository,
    )

    assert results
    assert raw_repository.calls == [(ski_area.ski_area_id, "mid")]


def test_search_resorts_reuses_planning_snapshots_across_matching_stay_bases() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]

    class CountingEmptyHistoryRepository:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def list_snapshots_for_resort(self, resort_id: str) -> tuple:
            self.calls.append(resort_id)
            return ()

    history_repository = CountingEmptyHistoryRepository()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=history_repository,
        raw_weather_history_repository=CountingRawHistoryRepository(()),
    )

    assert results
    assert history_repository.calls == [ski_area.ski_area_id, resort.resort_id]


def test_search_resorts_skips_planning_snapshots_when_raw_weather_exists() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]
    raw_repository = CountingRawHistoryRepository(
        (
            _raw_weather_observation(
                resort_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                elevation_band="mid",
                observed_on="2024-03-05",
                snowfall_cm=8,
                snow_depth_m=1.2,
                max_temp_c=-3,
                gust_kmh=22,
            ),
        )
    )

    class FailingHistoryRepository:
        def list_snapshots_for_resort(self, resort_id: str) -> tuple:
            raise AssertionError("snapshot history should not be loaded")

        def list_snapshots_for_resorts(
            self,
            resort_ids: tuple[str, ...],
        ) -> dict[str, tuple]:
            raise AssertionError("snapshot history should not be preloaded")

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=FailingHistoryRepository(),
        raw_weather_history_repository=raw_repository,
    )

    assert results


def test_search_resorts_preloads_planning_snapshots_when_batch_loader_exists() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]

    class BatchCountingHistoryRepository:
        def __init__(self) -> None:
            self.single_calls: list[str] = []
            self.batch_calls: list[tuple[str, ...]] = []

        def list_snapshots_for_resort(self, resort_id: str) -> tuple:
            self.single_calls.append(resort_id)
            return ()

        def list_snapshots_for_resorts(
            self,
            resort_ids: tuple[str, ...],
        ) -> dict[str, tuple]:
            self.batch_calls.append(resort_ids)
            return {resort_id: () for resort_id in resort_ids}

    history_repository = BatchCountingHistoryRepository()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=history_repository,
        raw_weather_history_repository=CountingRawHistoryRepository(()),
    )

    assert results
    assert history_repository.single_calls == []
    assert history_repository.batch_calls == [(ski_area.ski_area_id, resort.resort_id)]


def test_search_resorts_reuses_ski_area_planning_context_per_request() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]

    class CountingConditionsProvider(StaticConditionsProvider):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
            self.calls.append(resort_name)
            return super().get_conditions_for_resort(resort_name)

    conditions_provider = CountingConditionsProvider()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=conditions_provider,
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=CountingRawHistoryRepository(()),
    )

    assert results
    assert conditions_provider.calls == [ski_area.name]


def test_search_resorts_keeps_temporarily_closed_resorts_with_penalty() -> None:
    class StubConditionsProvider:
        def get_conditions_for_resort(
            self, resort_name: str
        ) -> ResortConditions | None:
            if resort_name == "Tignes":
                return ResortConditions(
                    resort_name="Tignes",
                    snow_confidence_score=0.7,
                    availability_status="temporarily_closed",
                    weather_summary="Strong wind disruption.",
                    conditions_score=0.3,
                    updated_at="2026-04-07T10:00:00+00:00",
                    source="open-meteo",
                )
            return None

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=140,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        conditions_provider=StubConditionsProvider(),
    )

    tignes = next(result for result in results if result.resort_name == "Tignes")

    assert tignes.availability_status == "temporarily_closed"
    assert any(
        "high disruption risk" in risk.label.lower()
        for risk in tignes.explanation.risks
    )
    assert any(
        contributor.direction == "negative"
        for contributor in tignes.explanation.confidence_contributors
    )


def test_planning_policy_surface_is_centralized_and_versioned() -> None:
    assert PLANNING_HEURISTIC_VERSION == "v2"
    assert DEFAULT_PLANNING_HEURISTIC_POLICY.out_of_season_snow_score == 0.18
    assert (
        DEFAULT_PLANNING_HEURISTIC_POLICY.seasonality_core_month_score
        > DEFAULT_PLANNING_HEURISTIC_POLICY.seasonality_edge_month_score
    )


def test_planning_assessment_returns_out_of_season_fallback_with_no_evidence() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )

    assessment = derive_planning_assessment(
        resort=resort,
        travel_month=8,
        snapshots=(),
    )

    assert assessment.conditions.availability_status == "out_of_season"
    assert (
        assessment.conditions.snow_confidence_score
        == DEFAULT_PLANNING_HEURISTIC_POLICY.out_of_season_snow_score
    )
    assert (
        assessment.conditions.conditions_score
        == DEFAULT_PLANNING_HEURISTIC_POLICY.out_of_season_conditions_score
    )
    assert assessment.evidence_count == 0


def test_planning_core_season_month_scores_higher_than_edge_month() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )

    march = derive_planning_assessment(
        resort=resort,
        travel_month=3,
        snapshots=(),
    )
    november = derive_planning_assessment(
        resort=resort,
        travel_month=11,
        snapshots=(),
    )

    assert (
        march.conditions.snow_confidence_score
        > november.conditions.snow_confidence_score
    )
    assert march.conditions.conditions_score > november.conditions.conditions_score


def test_planning_single_snapshot_penalty_keeps_scores_below_raw_snapshot_average() -> (
    None
):
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )
    snapshot = ResortConditionSnapshot(
        resort_id="tignes",
        resort_name="Tignes",
        observed_month=2,
        observed_at="2026-02-10T00:00:00+00:00",
        snow_confidence_score=0.9,
        snow_confidence_label="good",
        availability_status="open",
        weather_summary="Strong February signal.",
        conditions_score=0.88,
        source="open-meteo",
    )

    assessment = derive_planning_assessment(
        resort=resort,
        travel_month=2,
        snapshots=(snapshot,),
    )

    assert assessment.evidence_count == 1
    assert assessment.conditions.snow_confidence_score < snapshot.snow_confidence_score
    assert assessment.conditions.conditions_score < snapshot.conditions_score


def test_planning_uses_raw_weather_history_windows_when_available() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )
    observations = (
        RawWeatherObservation(
            resort_id="tignes",
            resort_name="Tignes",
            observed_on="2024-03-05",
            observed_at="2024-03-05T12:00:00+00:00",
            snowfall_cm=9,
            snow_depth_m=1.4,
            temperature_2m_max_c=-4,
            temperature_2m_min_c=-10,
            wind_speed_10m_max_kmh=18,
            wind_gusts_10m_max_kmh=24,
            weather_code=3,
            record_type="archive",
            source="open-meteo",
            source_model="best_match",
        ),
        RawWeatherObservation(
            resort_id="tignes",
            resort_name="Tignes",
            observed_on="2025-03-08",
            observed_at="2025-03-08T12:00:00+00:00",
            snowfall_cm=7,
            snow_depth_m=1.2,
            temperature_2m_max_c=-2,
            temperature_2m_min_c=-8,
            wind_speed_10m_max_kmh=20,
            wind_gusts_10m_max_kmh=28,
            weather_code=3,
            record_type="archive",
            source="open-meteo",
            source_model="best_match",
        ),
    )

    assessment = derive_planning_assessment(
        resort=resort,
        travel_month=3,
        snapshots=(),
        raw_weather_observations=observations,
    )

    assert assessment.evidence_source == "raw_history"
    assert assessment.evidence_count == 2
    assert assessment.conditions.snow_confidence_label in {"fair", "good"}
    assert assessment.latest_snapshot_at == "2025-03-08T12:00:00+00:00"


def test_weather_evidence_metrics_use_archive_rows_for_month() -> None:
    observations = (
        _raw_weather_observation(
            observed_on="2024-03-05",
            snowfall_cm=9,
            snow_depth_m=1.4,
            max_temp_c=-4,
            gust_kmh=24,
        ),
        _raw_weather_observation(
            observed_on="2025-03-08",
            snowfall_cm=7,
            snow_depth_m=1.2,
            max_temp_c=-2,
            gust_kmh=28,
        ),
        _raw_weather_observation(
            observed_on="2026-03-08",
            snowfall_cm=40,
            snow_depth_m=4.0,
            max_temp_c=4,
            gust_kmh=80,
            record_type="forecast",
        ),
        _raw_weather_observation(
            observed_on="2025-04-08",
            snowfall_cm=20,
            snow_depth_m=2.0,
            max_temp_c=1,
            gust_kmh=40,
        ),
    )

    metrics = derive_weather_evidence_metrics(
        raw_weather_observations=observations,
        travel_month=3,
    )

    assert metrics is not None
    assert metrics.average_snow_depth_cm == 130.0
    assert metrics.average_daily_snowfall_cm == 8.0
    assert metrics.average_max_temperature_c == -3.0
    assert metrics.average_wind_gust_kmh == 26.0
    assert metrics.evidence_years == 2
    assert metrics.latest_observed_on == "2025-03-08"
    assert metrics.elevation_band == "mid"
    assert metrics.elevation_m == 2500


def test_weather_evidence_metrics_match_exact_dates_across_archive_years() -> None:
    observations = (
        _raw_weather_observation(
            observed_on="2024-03-10",
            snowfall_cm=8,
            snow_depth_m=1.1,
            max_temp_c=-3,
            gust_kmh=24,
        ),
        _raw_weather_observation(
            observed_on="2025-03-11",
            snowfall_cm=6,
            snow_depth_m=1.0,
            max_temp_c=-2,
            gust_kmh=28,
        ),
        _raw_weather_observation(
            observed_on="2025-03-20",
            snowfall_cm=30,
            snow_depth_m=3.0,
            max_temp_c=3,
            gust_kmh=60,
        ),
    )

    metrics = derive_weather_evidence_metrics(
        raw_weather_observations=observations,
        trip_start_date=date(2026, 3, 8),
        trip_end_date=date(2026, 3, 12),
    )

    assert metrics is not None
    assert metrics.average_snow_depth_cm == 105.0
    assert metrics.average_daily_snowfall_cm == 7.0
    assert metrics.average_max_temperature_c == -2.5
    assert metrics.average_wind_gust_kmh == 26.0
    assert metrics.evidence_years == 2
    assert metrics.latest_observed_on == "2025-03-11"
    assert metrics.elevation_band == "mid"


def test_weather_evidence_metrics_fall_back_to_upper_rows_when_mid_missing() -> None:
    observations = (
        _raw_weather_observation(
            observed_on="2025-03-08",
            snowfall_cm=7,
            snow_depth_m=2.0,
            max_temp_c=-2,
            gust_kmh=28,
            elevation_band="upper",
            elevation_m=3200,
        ),
    )

    metrics = derive_weather_evidence_metrics(
        raw_weather_observations=observations,
        travel_month=3,
    )

    assert metrics is not None
    assert metrics.average_snow_depth_cm == 200.0
    assert metrics.evidence_years == 1
    assert metrics.elevation_band == "upper"
    assert metrics.elevation_m == 3200


def test_weather_evidence_metrics_exclude_implausible_snow_depth_outliers() -> None:
    observations = (
        _raw_weather_observation(
            observed_on="2024-04-05",
            snowfall_cm=4,
            snow_depth_m=2.0,
            max_temp_c=-1,
            gust_kmh=24,
        ),
        _raw_weather_observation(
            observed_on="2025-04-05",
            snowfall_cm=5,
            snow_depth_m=27.0,
            max_temp_c=-2,
            gust_kmh=28,
        ),
    )

    metrics = derive_weather_evidence_metrics(
        raw_weather_observations=observations,
        travel_month=4,
    )

    assert metrics is not None
    assert metrics.average_snow_depth_cm == 200.0
    assert metrics.evidence_years == 2


def test_weather_evidence_metrics_are_absent_without_archive_rows() -> None:
    observations = (
        _raw_weather_observation(
            observed_on="2026-03-08",
            snowfall_cm=40,
            snow_depth_m=4.0,
            max_temp_c=4,
            gust_kmh=80,
            record_type="forecast",
        ),
    )

    assert (
        derive_weather_evidence_metrics(
            raw_weather_observations=observations,
            travel_month=3,
        )
        is None
    )


def test_search_resorts_includes_planning_weather_metrics_when_archive_rows_exist() -> (
    None
):
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )
    ski_area = resort.ski_areas[0]

    class StubRawHistoryRepository:
        def list_observations_for_resort(self, resort_id: str, **kwargs):
            if resort_id != ski_area.ski_area_id:
                return ()
            return (
                _raw_weather_observation(
                    resort_id=ski_area.ski_area_id,
                    resort_name=ski_area.name,
                    observed_on="2024-03-05",
                    snowfall_cm=9,
                    snow_depth_m=1.4,
                    max_temp_c=-4,
                    gust_kmh=24,
                ),
                _raw_weather_observation(
                    resort_id=ski_area.ski_area_id,
                    resort_name=ski_area.name,
                    observed_on="2025-03-08",
                    snowfall_cm=7,
                    snow_depth_m=1.2,
                    max_temp_c=-2,
                    gust_kmh=28,
                ),
            )

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        raw_weather_history_repository=StubRawHistoryRepository(),
    )

    assert results
    assert results[0].planning_weather_metrics is not None
    assert results[0].planning_weather_metrics.average_snow_depth_cm == 130.0


def test_search_resorts_falls_back_to_upper_band_archive_weather() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "cervinia"
    )
    ski_area = resort.ski_areas[0]

    class UpperOnlyRawHistoryRepository:
        def list_observations_for_resort(self, resort_id: str, **kwargs):
            if resort_id != ski_area.ski_area_id:
                return ()
            if kwargs.get("elevation_band") != "upper":
                return ()
            return (
                _raw_weather_observation(
                    resort_id=ski_area.ski_area_id,
                    resort_name=ski_area.name,
                    elevation_band="upper",
                    elevation_m=ski_area.summit_elevation_m,
                    observed_on="2024-03-21",
                    snowfall_cm=9,
                    snow_depth_m=1.8,
                    max_temp_c=-5,
                    gust_kmh=24,
                ),
                _raw_weather_observation(
                    resort_id=ski_area.ski_area_id,
                    resort_name=ski_area.name,
                    elevation_band="upper",
                    elevation_m=ski_area.summit_elevation_m,
                    observed_on="2025-03-23",
                    snowfall_cm=7,
                    snow_depth_m=1.6,
                    max_temp_c=-4,
                    gust_kmh=28,
                ),
            )

    results = search_resorts(
        SearchFilters(
            location="Italy",
            min_price=150,
            max_price=320,
            stars=2,
            skill_level="intermediate",
            trip_start_date=date(2027, 3, 21),
            trip_end_date=date(2027, 3, 27),
        ),
        resorts=(resort,),
        raw_weather_history_repository=UpperOnlyRawHistoryRepository(),
    )

    assert results
    assert results[0].planning_evidence_count == 2
    assert results[0].planning_weather_metrics is not None
    assert results[0].planning_weather_metrics.elevation_band == "upper"
    assert results[0].planning_weather_metrics.average_snow_depth_cm == 170.0


def test_planning_date_range_uses_forecast_assistance_for_near_trip_window() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )
    observations = (
        RawWeatherObservation(
            resort_id="tignes",
            resort_name="Tignes",
            observed_on="2024-03-10",
            observed_at="2024-03-10T12:00:00+00:00",
            snowfall_cm=8,
            snow_depth_m=1.1,
            temperature_2m_max_c=-3,
            temperature_2m_min_c=-9,
            wind_speed_10m_max_kmh=18,
            wind_gusts_10m_max_kmh=24,
            weather_code=3,
            record_type="archive",
            source="open-meteo",
            source_model="best_match",
        ),
        RawWeatherObservation(
            resort_id="tignes",
            resort_name="Tignes",
            observed_on="2025-03-11",
            observed_at="2025-03-11T12:00:00+00:00",
            snowfall_cm=6,
            snow_depth_m=1.0,
            temperature_2m_max_c=-2,
            temperature_2m_min_c=-8,
            wind_speed_10m_max_kmh=20,
            wind_gusts_10m_max_kmh=28,
            weather_code=3,
            record_type="archive",
            source="open-meteo",
            source_model="best_match",
        ),
    )
    current_conditions = ResortConditions(
        resort_name="Tignes",
        snow_confidence_score=0.92,
        snow_confidence_label="good",
        availability_status="open",
        weather_summary="Strong current signal.",
        conditions_score=0.9,
        updated_at="2026-03-01T00:00:00+00:00",
        source="open-meteo",
    )

    assessment = derive_planning_assessment(
        resort=resort,
        snapshots=(),
        raw_weather_observations=observations,
        current_conditions=current_conditions,
        trip_start_date=date(2026, 3, 8),
        trip_end_date=date(2026, 3, 12),
        reference_date=datetime(2026, 3, 1, tzinfo=UTC),
    )

    forecast_assisted_text = DEFAULT_PLANNING_HEURISTIC_POLICY.text.forecast_assisted
    expected_template = forecast_assisted_text.planning_summary_template
    expected_summary = expected_template.format(
        snow_label=assessment.conditions.snow_confidence_label.capitalize(),
        planning_label="8 Mar–12 Mar",
        evidence_count=assessment.evidence_count,
    )

    assert assessment.evidence_profile == "forecast_assisted"
    assert assessment.evidence_source == "raw_history"
    assert assessment.planning_summary == expected_summary


def test_planning_date_range_stays_archive_backed_for_far_trip_window() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "tignes"
    )
    observations = (
        RawWeatherObservation(
            resort_id="tignes",
            resort_name="Tignes",
            observed_on="2024-03-10",
            observed_at="2024-03-10T12:00:00+00:00",
            snowfall_cm=8,
            snow_depth_m=1.1,
            temperature_2m_max_c=-3,
            temperature_2m_min_c=-9,
            wind_speed_10m_max_kmh=18,
            wind_gusts_10m_max_kmh=24,
            weather_code=3,
            record_type="archive",
            source="open-meteo",
            source_model="best_match",
        ),
        RawWeatherObservation(
            resort_id="tignes",
            resort_name="Tignes",
            observed_on="2025-03-11",
            observed_at="2025-03-11T12:00:00+00:00",
            snowfall_cm=6,
            snow_depth_m=1.0,
            temperature_2m_max_c=-2,
            temperature_2m_min_c=-8,
            wind_speed_10m_max_kmh=20,
            wind_gusts_10m_max_kmh=28,
            weather_code=3,
            record_type="archive",
            source="open-meteo",
            source_model="best_match",
        ),
    )
    current_conditions = ResortConditions(
        resort_name="Tignes",
        snow_confidence_score=0.92,
        snow_confidence_label="good",
        availability_status="open",
        weather_summary="Strong current signal.",
        conditions_score=0.9,
        updated_at="2026-01-01T00:00:00+00:00",
        source="open-meteo",
    )

    assessment = derive_planning_assessment(
        resort=resort,
        snapshots=(),
        raw_weather_observations=observations,
        current_conditions=current_conditions,
        trip_start_date=date(2026, 3, 8),
        trip_end_date=date(2026, 3, 12),
        reference_date=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert assessment.evidence_profile == "archive_backed"
    assert assessment.evidence_source == "raw_history"


def test_current_signal_weight_uses_policy_thresholds_and_weights() -> None:
    policy = DEFAULT_PLANNING_HEURISTIC_POLICY.forecast_window
    reference_date = datetime(2026, 3, 1, tzinfo=UTC)

    near_weight = _current_signal_weight(
        travel_month=3,
        reference_date=reference_date,
        trip_start_date=date(2026, 3, 8),
    )
    medium_weight = _current_signal_weight(
        travel_month=3,
        reference_date=reference_date,
        trip_start_date=date(2026, 3, 20),
    )
    month_weight = _current_signal_weight(
        travel_month=3,
        reference_date=reference_date,
    )

    assert near_weight == policy.near_trip_weight
    assert medium_weight == policy.medium_trip_weight
    assert month_weight == policy.same_month_weight


def test_planning_provenance_uses_centralized_policy_wording() -> None:
    policy = DEFAULT_PLANNING_HEURISTIC_POLICY.text

    provenance = _build_planning_provenance(
        evidence_count=2,
        latest_snapshot_at="2025-03-08T12:00:00+00:00",
        evidence_source="raw_history",
        evidence_profile="forecast_assisted",
    )

    assert provenance.source_name == policy.forecast_assisted.source_name
    assert provenance.basis_summary == policy.forecast_assisted.provenance_summary
    assert provenance.evidence_profile == "forecast_assisted"


def test_planning_late_spring_sparse_history_penalizes_ischgl() -> None:
    resort = next(
        resort
        for resort in get_resort_repository().list_resorts()
        if resort.resort_id == "ischgl"
    )

    assessment = derive_planning_assessment(
        resort=resort,
        travel_month=5,
        snapshots=(),
    )

    assert assessment.conditions.snow_confidence_label == "poor"
    assert assessment.conditions.availability_status == "limited"


def test_planning_high_alpine_resorts_remain_viable_in_may() -> None:
    resorts = {
        resort.resort_id: resort for resort in get_resort_repository().list_resorts()
    }

    zermatt = derive_planning_assessment(
        resort=resorts["zermatt"],
        travel_month=5,
        snapshots=(),
    )
    ischgl = derive_planning_assessment(
        resort=resorts["ischgl"],
        travel_month=5,
        snapshots=(),
    )

    assert (
        zermatt.conditions.snow_confidence_score
        > ischgl.conditions.snow_confidence_score
    )
    assert zermatt.conditions.snow_confidence_label in {"fair", "good"}


def test_search_resorts_surfaces_ischgl_conservatively_for_austrian_may() -> None:
    results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=150,
            max_price=350,
            stars=2,
            skill_level="intermediate",
            travel_month=5,
        )
    )

    assert results
    ischgl = next(result for result in results if result.resort_name == "Ischgl")
    assert ischgl.snow_confidence_label == "poor"
    assert ischgl.availability_status == "limited"
    assert ischgl.recommendation_confidence < 0.8


def test_search_resorts_falls_back_when_conditions_are_missing(monkeypatch) -> None:
    class EmptyConditionsProvider:
        def get_conditions_for_resort(self, resort_name: str) -> None:
            return None

    monkeypatch.setattr(
        "app.domain.search_service.get_conditions_provider",
        lambda: EmptyConditionsProvider(),
    )

    results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=90,
            max_price=220,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert results
    assert (
        results[0].conditions_summary
        == "No live conditions signal available for this ski area."
    )
    assert results[0].snow_confidence_label == "fair"
    assert results[0].availability_status == "limited"


def test_search_resorts_returns_empty_list_when_no_resorts_match() -> None:
    results = search_resorts(
        SearchFilters(
            location="Italy",
            min_price=100,
            max_price=90,
            stars=3,
            skill_level="advanced",
        )
    )

    assert results == []


def test_domain_search_adds_narrative_only_to_top_result() -> None:
    from app.domain.services import search_resorts as search_resorts_with_narrative

    class StubNarrativeGenerator(RecommendationNarrativeGenerator):
        def generate(self, result) -> str | None:
            return f"{result.resort_name} is the strongest overall match."

    results = search_resorts_with_narrative(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        narrative_generator=StubNarrativeGenerator(),
    )

    assert results[0].recommendation_narrative is not None
    assert all(result.recommendation_narrative is None for result in results[1:])


def test_domain_search_degrades_to_null_narrative_on_generator_failure() -> None:
    from app.domain.services import search_resorts as search_resorts_with_narrative

    class BrokenNarrativeGenerator(RecommendationNarrativeGenerator):
        def generate(self, result) -> str | None:
            raise RuntimeError("llm failure")

    results = search_resorts_with_narrative(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        narrative_generator=BrokenNarrativeGenerator(),
    )

    assert results
    assert results[0].recommendation_narrative is None


def test_domain_search_with_debug_returns_narrative_debug() -> None:
    from app.domain.services import search_resorts_with_debug

    class StubNarrativeGenerator(RecommendationNarrativeGenerator):
        def generate(self, result) -> str | None:
            return "unused"

        def generate_with_debug(self, result):
            return (
                "Tignes is the strongest overall match.",
                {
                    "narrative_source": "llm",
                    "narrative_cache_hit": False,
                    "narrative_error": None,
                    "narrative_model": "stub-model",
                    "top_result_resort_id": result.resort_id,
                },
            )

    results, debug = search_resorts_with_debug(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        narrative_generator=StubNarrativeGenerator(),
    )

    assert results[0].recommendation_narrative is not None
    assert debug.narrative_source == "llm"

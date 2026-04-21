from datetime import UTC, date, datetime

from app.ai.narrative import RecommendationNarrativeGenerator
from app.data.repositories import get_resort_repository
from app.domain.models import (
    RawWeatherObservation,
    ResortConditions,
    ResortConditionSnapshot,
    SearchFilters,
)
from app.domain.planning import _current_signal_weight, derive_planning_assessment
from app.domain.planning_policy import (
    DEFAULT_PLANNING_HEURISTIC_POLICY,
    PLANNING_HEURISTIC_VERSION,
)
from app.domain.search_service import _build_planning_provenance, search_resorts


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
            min_price=90,
            max_price=90,
            stars=2,
            skill_level="intermediate",
        )
    )
    flex_results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=90,
            max_price=90,
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
        def list_observations_for_resort(self, resort_id: str):
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
        def list_observations_for_resort(self, resort_id: str):
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
        "temporarily closed" in risk.label.lower() for risk in tignes.explanation.risks
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
        planning_label="8 Mar-12 Mar",
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

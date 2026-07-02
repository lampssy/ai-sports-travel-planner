from app.domain.models import (
    Destination,
    Rental,
    ResortConditions,
    SearchFilters,
    SkiArea,
    StayBase,
)
from app.domain.search_service import search_resorts
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)
from app.observability.search import record_search_v3_completed


class StaticConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
        return ResortConditions(
            resort_name=resort_name,
            snow_confidence_score=0.82,
            snow_confidence_label="good",
            availability_status="open",
            weather_summary="Good current snow outlook.",
            conditions_score=0.78,
            updated_at="2026-01-15T00:00:00+00:00",
            source="open-meteo",
        )


class EmptyHistoryRepository:
    def list_snapshots_for_ski_area(self, ski_area_id: str) -> tuple:
        return ()


class EmptyRawWeatherRepository:
    def list_observations_for_ski_areas(self, ski_area_ids, *, elevation_bands):
        return {
            (ski_area_id, elevation_band): ()
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
        }

    def list_observations_for_ski_area(self, ski_area_id: str, *, elevation_band: str):
        return ()


def test_search_records_phase_and_completion_metrics():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        results = search_resorts(
            SearchFilters(
                location="Italy",
                min_price=100,
                max_price=250,
                stars=1,
                skill_level="intermediate",
                travel_month=3,
            ),
            resorts=(_destination(),),
            conditions_provider=StaticConditionsProvider(),
            condition_history_repository=EmptyHistoryRepository(),
            raw_weather_history_repository=EmptyRawWeatherRepository(),
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert results
    metric_names = [name for name, _, _ in recorder.histograms]
    assert "snowcast_search_duration_seconds" in metric_names
    assert "snowcast_search_phase_duration_seconds" in metric_names
    phase_attributes = [
        attrs
        for name, attrs, _ in recorder.histograms
        if name == "snowcast_search_phase_duration_seconds"
    ]
    assert {
        "phase": "load_planning_evidence",
        "window_type": "month",
        "has_origin": False,
    } in phase_attributes
    assert recorder.counters[-1] == (
        "snowcast_search_requests_total",
        {"parser_mode": "unknown", "has_origin": False, "window_type": "month"},
        1,
    )


def test_search_v3_metrics_use_only_bounded_labels() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        record_search_v3_completed(
            filters=SearchFilters(
                location="France",
                min_price=100,
                max_price=250,
                stars=1,
                skill_level="intermediate",
            ),
            candidate_seed_count=8,
            configuration_count=6,
            result_count=3,
            evidence_profile_counts={"archive_backed": 4, "current_only": 2},
            duration_seconds=0.2,
        )
    finally:
        reset_metrics_recorder_for_tests()

    all_attributes = [
        attributes for _, attributes, _ in (*recorder.counters, *recorder.histograms)
    ]
    assert all(
        attributes.get("search_model") == "search_v3" for attributes in all_attributes
    )
    assert all(
        not any(
            "region" in key or "area_id" in key or "base_id" in key
            for key in attributes
        )
        for attributes in all_attributes
    )


def _destination() -> Destination:
    return Destination(
        resort_id="test-resort",
        name="Test Resort",
        country="Italy",
        region="Test Region",
        price_level="medium",
        latitude=46.0,
        longitude=11.0,
        base_elevation_m=1200,
        summit_elevation_m=2400,
        season_start_month=12,
        season_end_month=4,
        ski_areas=[
            SkiArea(
                ski_area_id="test-ski-area",
                name="Test Ski Area",
                latitude=46.0,
                longitude=11.0,
                base_elevation_m=1200,
                summit_elevation_m=2400,
                season_start_month=12,
                season_end_month=4,
            )
        ],
        stay_bases=[
            StayBase(
                stay_base_id="test-base",
                name="Test Base",
                price_range="EUR 100-180",
                price_min=100,
                price_max=180,
                quality="standard",
                lift_distance="near",
                supported_skill_levels=["intermediate"],
            )
        ],
        rentals=[
            Rental(
                name="Test Rental",
                price_range="EUR 30-45",
                price_min=30,
                price_max=45,
                quality="standard",
                lift_distance="near",
            )
        ],
    )

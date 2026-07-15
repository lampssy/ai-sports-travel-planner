from app.domain.search_v4_models import SearchIntent, TravelContext, TravelWindow
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)
from app.observability.search import (
    record_search_phase_duration,
    record_search_v4_completed,
)


def test_search_v4_metrics_use_only_bounded_labels() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        intent = SearchIntent(
            constraints={"travel_window": TravelWindow(month=3)},
            travel_context=TravelContext(origin_text="private origin", mode="car"),
        )
        record_search_phase_duration(
            phase="weather_preload",
            intent=intent,
            duration_seconds=0.01,
        )
        record_search_v4_completed(
            intent=intent,
            ranking_policy_version="search-v4-policy-1",
            ranking_status="ranked",
            candidate_count=8,
            eligible_candidate_count=6,
            result_group_count=3,
            question_count=2,
            duration_seconds=0.2,
        )
    finally:
        reset_metrics_recorder_for_tests()

    all_attributes = [
        attributes for _, attributes, _ in (*recorder.counters, *recorder.histograms)
    ]
    assert all(
        attributes.get("search_model") == "search-v4" for attributes in all_attributes
    )
    assert all(
        "private origin" not in str(attributes)
        and not any(
            "area_id" in key or "base_id" in key or "brief" in key or "run_id" in key
            for key in attributes
        )
        for attributes in all_attributes
    )

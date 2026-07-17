from app.domain.search_v4_models import SearchIntent, TravelContext, TravelWindow
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)
from app.observability.search import (
    record_search_phase_duration,
    record_search_refinement_completed,
    record_search_refinement_route_outcome,
    record_search_refinement_snapshot_outcome,
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


def test_refinement_metrics_keep_public_status_reason_and_count_bounded() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        intent = SearchIntent()
        record_search_refinement_completed(
            intent=intent,
            ranking_policy_version="search-v4-policy-1",
            status="temporarily_unavailable",
            reason="stale_baseline",
            fallback_used=False,
            question_count=0,
            duration_seconds=0.2,
        )
        record_search_refinement_route_outcome("admission_rejected")
        record_search_refinement_snapshot_outcome("hit")
        record_search_refinement_snapshot_outcome("expired", count=2)
    finally:
        reset_metrics_recorder_for_tests()

    assert (
        "snowcast_search_refinement_requests_total",
        {
            "search_model": "search-v4",
            "ranking_policy_version": "search-v4-policy-1",
            "status": "temporarily_unavailable",
            "reason": "stale_baseline",
            "fallback_used": False,
            "window_type": "none",
            "has_origin": False,
        },
        1,
    ) in recorder.counters
    assert (
        "snowcast_search_refinement_questions",
        {
            "search_model": "search-v4",
            "status": "temporarily_unavailable",
        },
        0.0,
    ) in recorder.histograms
    assert (
        "snowcast_search_refinement_route_outcomes_total",
        {"search_model": "search-v4", "outcome": "admission_rejected"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_search_refinement_snapshot_outcomes_total",
        {"search_model": "search-v4", "outcome": "hit"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_search_refinement_snapshot_outcomes_total",
        {"search_model": "search-v4", "outcome": "expired"},
        2,
    ) in recorder.counters

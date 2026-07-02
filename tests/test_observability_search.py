from app.domain.models import SearchFilters
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)
from app.observability.search import record_search_v3_completed


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

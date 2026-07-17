from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.domain.search_v4_models import SearchIntent
from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import set_span_attributes, start_span


def search_window_type(intent: SearchIntent) -> str:
    window = intent.constraints.travel_window
    return window.mode if window is not None else "none"


def search_common_attributes(
    intent: SearchIntent,
    *,
    ranking_policy_version: str,
    ranking_status: str,
) -> dict[str, str | bool]:
    return {
        "search_model": "search-v4",
        "ranking_policy_version": ranking_policy_version,
        "ranking_status": ranking_status,
        "has_origin": bool(intent.travel_context.origin_text),
        "window_type": search_window_type(intent),
    }


def record_search_phase_duration(
    *,
    phase: str,
    intent: SearchIntent,
    duration_seconds: float,
) -> None:
    get_metrics_recorder().observe(
        "snowcast_search_phase_duration_seconds",
        duration_seconds,
        {
            "phase": phase,
            "window_type": search_window_type(intent),
            "has_origin": bool(intent.travel_context.origin_text),
            "search_model": "search-v4",
        },
    )


@contextmanager
def search_phase(*, phase: str, intent: SearchIntent) -> Iterator[None]:
    """Time and trace one bounded Search V4 phase without sensitive labels."""

    attributes = {
        "snowcast.search.phase": phase,
        "snowcast.search.window_type": search_window_type(intent),
        "snowcast.search.has_origin": bool(intent.travel_context.origin_text),
        "snowcast.search.model": "search-v4",
    }
    started = time.perf_counter()
    with start_span(f"search.{phase}", attributes):
        try:
            yield
        finally:
            record_search_phase_duration(
                phase=phase,
                intent=intent,
                duration_seconds=time.perf_counter() - started,
            )


def record_search_v4_completed(
    *,
    intent: SearchIntent,
    ranking_policy_version: str,
    ranking_status: str,
    candidate_count: int,
    eligible_candidate_count: int,
    result_group_count: int,
    duration_seconds: float,
    span: object | None = None,
) -> None:
    attributes = search_common_attributes(
        intent,
        ranking_policy_version=ranking_policy_version,
        ranking_status=ranking_status,
    )
    recorder = get_metrics_recorder()
    recorder.increment("snowcast_search_requests_total", attributes)
    recorder.observe(
        "snowcast_search_duration_seconds",
        duration_seconds,
        attributes,
    )
    bounded_counts = {
        "window_type": attributes["window_type"],
        "has_origin": attributes["has_origin"],
        "search_model": "search-v4",
        "ranking_status": ranking_status,
    }
    for metric_name, value in (
        ("snowcast_search_candidates", candidate_count),
        ("snowcast_search_eligible_candidates", eligible_candidate_count),
        ("snowcast_search_result_groups", result_group_count),
    ):
        recorder.observe(metric_name, float(value), bounded_counts)
    if eligible_candidate_count == 0:
        recorder.increment("snowcast_search_empty_results_total", bounded_counts)
    if span is not None:
        set_span_attributes(
            span,
            {
                "snowcast.search.model": "search-v4",
                "snowcast.search.ranking_policy_version": ranking_policy_version,
                "snowcast.search.ranking_status": ranking_status,
                "snowcast.search.candidate_count": candidate_count,
                "snowcast.search.eligible_candidate_count": (eligible_candidate_count),
                "snowcast.search.result_group_count": result_group_count,
            },
        )


def record_search_refinement_completed(
    *,
    intent: SearchIntent,
    ranking_policy_version: str,
    status: str,
    reason: str,
    fallback_used: bool,
    question_count: int,
    duration_seconds: float,
) -> None:
    attributes = {
        "search_model": "search-v4",
        "ranking_policy_version": ranking_policy_version,
        "status": status,
        "reason": reason,
        "fallback_used": fallback_used,
        "window_type": search_window_type(intent),
        "has_origin": bool(intent.travel_context.origin_text),
    }
    recorder = get_metrics_recorder()
    recorder.increment("snowcast_search_refinement_requests_total", attributes)
    recorder.observe(
        "snowcast_search_refinement_duration_seconds",
        duration_seconds,
        attributes,
    )
    recorder.observe(
        "snowcast_search_refinement_questions",
        float(question_count),
        {"search_model": "search-v4", "status": status},
    )
    if fallback_used:
        recorder.increment(
            "snowcast_search_refinement_fallbacks_total",
            {"search_model": "search-v4"},
        )


def record_search_refinement_route_outcome(outcome: str) -> None:
    get_metrics_recorder().increment(
        "snowcast_search_refinement_route_outcomes_total",
        {"search_model": "search-v4", "outcome": outcome},
    )


def record_search_refinement_snapshot_outcome(
    outcome: str,
    *,
    count: int = 1,
) -> None:
    """Record one of the bounded evaluated-baseline snapshot outcomes."""

    get_metrics_recorder().increment(
        "snowcast_search_refinement_snapshot_outcomes_total",
        {"search_model": "search-v4", "outcome": outcome},
        amount=count,
    )

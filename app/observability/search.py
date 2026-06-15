from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.domain.models import SearchFilters
from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import set_span_attributes, start_span


def search_window_type(filters: SearchFilters) -> str:
    if filters.trip_start_date is not None and filters.trip_end_date is not None:
        return "exact_dates"
    if filters.travel_month is not None:
        return "month"
    return "none"


def search_common_attributes(
    filters: SearchFilters,
    *,
    parser_mode: str = "unknown",
) -> dict[str, str | bool]:
    return {
        "parser_mode": parser_mode,
        "has_origin": bool(filters.origin_text),
        "window_type": search_window_type(filters),
    }


@contextmanager
def search_span(
    filters: SearchFilters,
    *,
    candidate_resort_count: int | None = None,
) -> Iterator[object]:
    with start_span(
        "api.search",
        {
            "snowcast.search.window_type": search_window_type(filters),
            "snowcast.search.has_origin": bool(filters.origin_text),
            "snowcast.search.candidate_resort_count": candidate_resort_count,
        },
    ) as span:
        yield span


@contextmanager
def search_phase(
    name: str,
    filters: SearchFilters,
) -> Iterator[None]:
    attributes = {
        "phase": name,
        "window_type": search_window_type(filters),
        "has_origin": bool(filters.origin_text),
    }
    started_at = time.perf_counter()
    with start_span(
        f"search.{name}",
        {
            "snowcast.search.phase": name,
            "snowcast.search.window_type": attributes["window_type"],
            "snowcast.search.has_origin": attributes["has_origin"],
        },
    ):
        try:
            yield
        finally:
            get_metrics_recorder().observe(
                "snowcast_search_phase_duration_seconds",
                time.perf_counter() - started_at,
                attributes,
            )


def record_search_completed(
    *,
    filters: SearchFilters,
    result_count: int,
    duration_seconds: float,
    parser_mode: str = "unknown",
    span: object | None = None,
) -> None:
    attributes = search_common_attributes(filters, parser_mode=parser_mode)
    recorder = get_metrics_recorder()
    recorder.increment("snowcast_search_requests_total", attributes)
    recorder.observe("snowcast_search_duration_seconds", duration_seconds, attributes)
    recorder.observe(
        "snowcast_search_results_total",
        float(result_count),
        {
            "window_type": attributes["window_type"],
            "has_origin": attributes["has_origin"],
        },
    )
    if result_count == 0:
        recorder.increment(
            "snowcast_search_empty_results_total",
            {
                "window_type": attributes["window_type"],
                "has_origin": attributes["has_origin"],
            },
        )
    if span is not None:
        set_span_attributes(
            span,
            {
                "snowcast.search.result_count": result_count,
                "snowcast.search.empty_results": result_count == 0,
            },
        )

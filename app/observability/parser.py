from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import set_span_attributes, start_span

_BOUNDED_LLM_FAILURE_REASONS = frozenset(
    {"auth_error", "network_error", "provider_error", "quota_error"}
)


@contextmanager
def parser_operation(operation: str, *, model: str | None = None) -> Iterator[float]:
    start = time.perf_counter()
    with start_span(
        f"llm.{operation}",
        {
            "snowcast.llm.operation": operation,
            "snowcast.llm.model": model,
        },
    ):
        yield start


def record_parse_result(
    *,
    mode: str,
    status: str,
    duration_seconds: float,
    confidence: float | None = None,
    fallback_reason: str | None = None,
    model: str | None = None,
) -> None:
    recorder = get_metrics_recorder()
    attributes = {"mode": mode, "status": status}
    recorder.increment("snowcast_parse_requests_total", attributes)
    recorder.observe(
        "snowcast_parse_duration_seconds",
        duration_seconds,
        attributes,
    )
    if confidence is not None:
        recorder.observe("snowcast_parse_confidence", confidence, {"mode": mode})
    if fallback_reason is not None:
        recorder.increment(
            "snowcast_llm_fallbacks_total",
            {"operation": "query_parser", "reason": fallback_reason},
        )


def record_llm_result(
    *,
    operation: str,
    model: str | None,
    status: str,
    duration_seconds: float,
) -> None:
    recorder = get_metrics_recorder()
    attributes = {
        "operation": operation,
        "model": model or "unknown",
        "status": status,
    }
    recorder.increment("snowcast_llm_requests_total", attributes)
    recorder.observe("snowcast_llm_duration_seconds", duration_seconds, attributes)


def record_llm_failure(
    *,
    operation: str,
    model: str | None,
    reason: str,
) -> None:
    safe_reason = reason if reason in _BOUNDED_LLM_FAILURE_REASONS else "provider_error"
    get_metrics_recorder().increment(
        "snowcast_llm_failures_total",
        {
            "operation": operation,
            "model": model or "unknown",
            "reason": safe_reason,
        },
    )


def record_llm_retry(
    *,
    operation: str,
    model: str | None,
    reason: str,
) -> None:
    get_metrics_recorder().increment(
        "snowcast_llm_retries_total",
        {
            "operation": operation,
            "model": model or "unknown",
            "reason": reason,
        },
    )


def set_parser_span_attributes(
    span: object,
    *,
    mode: str,
    fallback_used: bool,
    confidence: float | None,
    fallback_reason: str | None,
    model: str | None,
    status: str,
) -> None:
    set_span_attributes(
        span,
        {
            "snowcast.parser.mode": mode,
            "snowcast.parser.fallback_used": fallback_used,
            "snowcast.parser.fallback_reason": fallback_reason or "none",
            "snowcast.parser.confidence": confidence,
            "snowcast.llm.model": model,
            "snowcast.llm.status": status,
        },
    )

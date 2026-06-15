from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import start_span


@contextmanager
def job_span(
    name: str,
    *,
    attributes: dict[str, str | int | float | bool] | None = None,
) -> Iterator[None]:
    started = time.perf_counter()
    status = "success"
    with start_span(f"job.{name}", attributes):
        try:
            yield
        except Exception:
            status = "failure"
            raise
        finally:
            get_metrics_recorder().observe(
                f"snowcast_{name}_duration_seconds",
                time.perf_counter() - started,
                {"status": status},
            )


def record_conditions_refresh_result(
    *,
    source: str,
    status: str,
    updated_at: str | None = None,
    reason: str | None = None,
    now: datetime | None = None,
) -> None:
    recorder = get_metrics_recorder()
    if status == "success":
        recorder.increment(
            "snowcast_conditions_refresh_success_total",
            {"source": source},
        )
        age_seconds = seconds_since(updated_at, now=now)
        if age_seconds is not None:
            recorder.gauge(
                "snowcast_conditions_refresh_age_seconds",
                age_seconds,
                {"source": source},
            )
        return
    recorder.increment(
        "snowcast_conditions_refresh_failure_total",
        {"source": source, "reason": reason or "unknown"},
    )


def seconds_since(value: str | None, *, now: datetime | None = None) -> float | None:
    if value is None:
        return None
    reference = now or datetime.now(UTC)
    observed = datetime.fromisoformat(value)
    return (reference - observed).total_seconds()

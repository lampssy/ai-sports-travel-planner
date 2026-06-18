from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Protocol

from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import start_span


class DataQualityEntityCountSnapshot(Protocol):
    domain: str
    status: str
    count: int


class DataQualityGaugeSnapshot(Protocol):
    name: str
    value: float | int
    labels: dict[str, str]


class DataQualityMetricSnapshot(Protocol):
    completeness_ratios: dict[str, float]
    entity_counts: tuple[DataQualityEntityCountSnapshot, ...]
    gauges: tuple[DataQualityGaugeSnapshot, ...]


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


def record_snow_climatology_rebuild_result(
    source_model: str,
    status: str,
    targeted_ski_areas: int,
    raw_rows_read: int,
    climatology_rows_written: int,
    weak_coverage_groups: int,
) -> None:
    attributes = {"source_model": source_model, "status": status}
    recorder = get_metrics_recorder()
    recorder.increment("snowcast_snow_climatology_rebuild_total", attributes)
    recorder.gauge(
        "snowcast_snow_climatology_rebuild_ski_areas",
        targeted_ski_areas,
        attributes,
    )
    recorder.gauge(
        "snowcast_snow_climatology_raw_rows_read",
        raw_rows_read,
        attributes,
    )
    recorder.gauge(
        "snowcast_snow_climatology_rows_written",
        climatology_rows_written,
        attributes,
    )
    recorder.gauge(
        "snowcast_snow_climatology_weak_coverage_groups",
        weak_coverage_groups,
        attributes,
    )


def record_data_quality_audit_result(result: DataQualityMetricSnapshot) -> None:
    recorder = get_metrics_recorder()
    for domain, ratio in sorted(result.completeness_ratios.items()):
        recorder.gauge(
            "snowcast_data_completeness_ratio",
            ratio,
            {"domain": domain},
        )
    for item in result.entity_counts:
        recorder.gauge(
            "snowcast_data_completeness_entities",
            item.count,
            {"domain": item.domain, "status": item.status},
        )
    for gauge in result.gauges:
        recorder.gauge(gauge.name, gauge.value, gauge.labels)


def seconds_since(value: str | None, *, now: datetime | None = None) -> float | None:
    if value is None:
        return None
    reference = now or datetime.now(UTC)
    observed = datetime.fromisoformat(value)
    return (reference - observed).total_seconds()

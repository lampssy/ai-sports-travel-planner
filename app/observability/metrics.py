from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from opentelemetry.metrics import Observation

MetricAttributes = Mapping[str, str | int | float | bool]


class MetricsRecorder(Protocol):
    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        raise NotImplementedError

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        raise NotImplementedError

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        raise NotImplementedError


class NoopMetricsRecorder:
    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        return None

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        return None

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        return None


@dataclass
class InMemoryMetricsRecorder:
    counters: list[tuple[str, dict[str, str | int | float | bool], int]] = field(
        default_factory=list
    )
    histograms: list[tuple[str, dict[str, str | int | float | bool], float]] = field(
        default_factory=list
    )
    gauges: list[tuple[str, dict[str, str | int | float | bool], float]] = field(
        default_factory=list
    )

    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        self.counters.append((name, dict(attributes or {}), amount))

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        self.histograms.append((name, dict(attributes or {}), value))

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        self.gauges.append((name, dict(attributes or {}), value))


class OpenTelemetryMetricsRecorder:
    def __init__(self, meter: Any) -> None:
        self._meter = meter
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}
        self._gauges: dict[str, Any] = {}
        self._gauge_values: dict[
            str,
            dict[
                tuple[tuple[str, str | int | float | bool], ...],
                tuple[float, dict[str, str | int | float | bool]],
            ],
        ] = {}

    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        instrument = self._counters.get(name)
        if instrument is None:
            instrument = self._meter.create_counter(name)
            self._counters[name] = instrument
        instrument.add(amount, attributes=dict(attributes or {}))

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        instrument = self._histograms.get(name)
        if instrument is None:
            instrument = self._meter.create_histogram(name)
            self._histograms[name] = instrument
        instrument.record(value, attributes=dict(attributes or {}))

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        if name not in self._gauges:
            self._gauge_values.setdefault(name, {})
            self._gauges[name] = self._meter.create_observable_gauge(
                name,
                callbacks=[self._gauge_callback(name)],
            )
        attributes_dict = dict(attributes or {})
        self._gauge_values[name][_attributes_key(attributes_dict)] = (
            value,
            attributes_dict,
        )

    def _gauge_callback(self, name: str):
        def callback(_options) -> list[Observation]:
            return [
                Observation(value, attributes=attributes)
                for value, attributes in self._gauge_values.get(name, {}).values()
            ]

        return callback


_metrics_recorder: MetricsRecorder = NoopMetricsRecorder()


def get_metrics_recorder() -> MetricsRecorder:
    return _metrics_recorder


def configure_metrics_recorder(recorder: MetricsRecorder) -> None:
    global _metrics_recorder
    _metrics_recorder = recorder


def set_metrics_recorder_for_tests(recorder: MetricsRecorder) -> None:
    configure_metrics_recorder(recorder)


def reset_metrics_recorder_for_tests() -> None:
    configure_metrics_recorder(NoopMetricsRecorder())


def _attributes_key(
    attributes: dict[str, str | int | float | bool],
) -> tuple[tuple[str, str | int | float | bool], ...]:
    return tuple(sorted(attributes.items()))

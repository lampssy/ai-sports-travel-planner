from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

_tracer = None


def configure_tracer(tracer: object | None) -> None:
    global _tracer
    _tracer = tracer


@contextmanager
def start_span(
    name: str,
    attributes: Mapping[str, str | int | float | bool | None] | None = None,
) -> Iterator[object]:
    if _tracer is None:
        span = _NoopSpan()
        set_span_attributes(span, attributes or {})
        yield span
        return

    with _tracer.start_as_current_span(name) as span:
        set_span_attributes(span, attributes or {})
        yield span


def set_span_attributes(
    span: object,
    attributes: Mapping[str, str | int | float | bool | None],
) -> None:
    setter = getattr(span, "set_attribute", None)
    if setter is None:
        return
    for key, value in attributes.items():
        if value is not None:
            setter(key, value)


class _NoopSpan:
    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        return None

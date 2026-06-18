from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.observability.config import ObservabilitySettings
from app.observability.otel import (
    configure_observability_runtime,
    shutdown_observability_runtime,
)
from app.observability.tracing import start_span


@contextmanager
def configure_cli_observability(job_name: str) -> Iterator[ObservabilitySettings]:
    settings = configure_observability_runtime()
    if not settings.enabled:
        yield settings
        return

    try:
        with start_span("job.cli", {"snowcast.job.name": job_name}):
            yield settings
    finally:
        shutdown_observability_runtime()

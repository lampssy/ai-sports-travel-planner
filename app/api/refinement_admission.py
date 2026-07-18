from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

MAX_CONCURRENT_REFINEMENTS = 2
REQUESTS_PER_MINUTE = 6
BURST_CAPACITY = 2
CLIENT_RETENTION_SECONDS = 60.0
MAX_TRACKED_CLIENTS = 2_048


@dataclass
class _ClientBucket:
    tokens: float
    last_updated: float


@dataclass
class RefinementAdmission:
    accepted: bool
    retry_after_seconds: int | None
    _release: Callable[[], None] | None = None

    def release(self) -> None:
        if self._release is not None:
            release = self._release
            self._release = None
            release()


class RefinementAdmissionGuard:
    """Bound local refinement work before candidate evaluation starts."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_concurrent: int = MAX_CONCURRENT_REFINEMENTS,
        requests_per_minute: int = REQUESTS_PER_MINUTE,
        burst_capacity: int = BURST_CAPACITY,
        retention_seconds: float = CLIENT_RETENTION_SECONDS,
        max_clients: int = MAX_TRACKED_CLIENTS,
    ) -> None:
        self._clock = clock
        self._max_concurrent = max_concurrent
        self._rate_per_second = requests_per_minute / 60
        self._burst_capacity = burst_capacity
        self._retention_seconds = retention_seconds
        self._max_clients = max_clients
        self._lock = threading.Lock()
        self._active = 0
        self._clients: dict[str, _ClientBucket] = {}

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def acquire(self, client_key: str) -> RefinementAdmission:
        now = self._clock()
        with self._lock:
            self._cleanup(now)
            if self._active >= self._max_concurrent:
                return RefinementAdmission(accepted=False, retry_after_seconds=1)

            bucket = self._clients.get(client_key)
            if bucket is None:
                self._evict_if_full()
                bucket = _ClientBucket(
                    tokens=float(self._burst_capacity),
                    last_updated=now,
                )
                self._clients[client_key] = bucket
            else:
                elapsed = max(0.0, now - bucket.last_updated)
                bucket.tokens = min(
                    float(self._burst_capacity),
                    bucket.tokens + elapsed * self._rate_per_second,
                )
                bucket.last_updated = now

            if bucket.tokens < 1:
                retry_after_seconds = math.ceil(
                    (1 - bucket.tokens) / self._rate_per_second
                )
                return RefinementAdmission(
                    accepted=False,
                    retry_after_seconds=max(1, retry_after_seconds),
                )

            bucket.tokens -= 1
            self._active += 1
            return RefinementAdmission(
                accepted=True,
                retry_after_seconds=None,
                _release=self._release,
            )

    def _release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    def _cleanup(self, now: float) -> None:
        expired = [
            key
            for key, bucket in self._clients.items()
            if now - bucket.last_updated >= self._retention_seconds
        ]
        for key in expired:
            del self._clients[key]

    def _evict_if_full(self) -> None:
        if len(self._clients) < self._max_clients:
            return
        oldest_key = min(
            self._clients,
            key=lambda key: self._clients[key].last_updated,
        )
        del self._clients[oldest_key]

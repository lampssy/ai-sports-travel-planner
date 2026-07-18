from __future__ import annotations

from concurrent.futures import Executor, Future
from threading import RLock
from typing import Any, Callable


class RefinementWorkerUnavailableError(RuntimeError):
    """Raised while a timed-out worker still occupies the bounded pool."""


class RefinementWorkerPool:
    """Bound refinement work and fail fast after an unresolved worker timeout."""

    def __init__(self, *, executor: Executor) -> None:
        self._executor = executor
        self._lock = RLock()
        self._timed_out_futures: set[Future[Any]] = set()

    def submit(
        self,
        function: Callable[..., Any],
        /,
        *args: object,
        **kwargs: object,
    ) -> Future[Any]:
        with self._lock:
            self._timed_out_futures = {
                future for future in self._timed_out_futures if not future.done()
            }
            if self._timed_out_futures:
                raise RefinementWorkerUnavailableError(
                    "a timed-out refinement worker is still running"
                )
            future = self._executor.submit(function, *args, **kwargs)
            future.add_done_callback(self._worker_finished)
            return future

    def mark_timed_out(self, future: Future[Any]) -> None:
        if future.cancel():
            return
        with self._lock:
            if not future.done():
                self._timed_out_futures.add(future)

    def _worker_finished(self, future: Future[Any]) -> None:
        with self._lock:
            self._timed_out_futures.discard(future)

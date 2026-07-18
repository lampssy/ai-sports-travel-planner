from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event

import pytest

from app.api.refinement_workers import (
    RefinementWorkerPool,
    RefinementWorkerUnavailableError,
)

pytestmark = pytest.mark.db_free


def test_non_returning_workers_open_a_bounded_circuit_instead_of_queueing() -> None:
    executor = ThreadPoolExecutor(max_workers=2)
    pool = RefinementWorkerPool(executor=executor)
    release_workers = Event()
    started = (Event(), Event())

    def block(index: int) -> None:
        started[index].set()
        release_workers.wait()

    try:
        futures = tuple(pool.submit(block, index) for index in range(2))
        assert all(event.wait(timeout=1) for event in started)
        for future in futures:
            with pytest.raises(TimeoutError):
                future.result(timeout=0.01)
            pool.mark_timed_out(future)

        with pytest.raises(RefinementWorkerUnavailableError):
            pool.submit(lambda: None)

        release_workers.set()
        for future in futures:
            future.result(timeout=1)

        recovered = pool.submit(lambda: "recovered")
        assert recovered.result(timeout=1) == "recovered"
    finally:
        release_workers.set()
        executor.shutdown(wait=True)

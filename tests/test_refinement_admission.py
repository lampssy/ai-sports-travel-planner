from __future__ import annotations

import pytest

from app.api.refinement_admission import RefinementAdmissionGuard

pytestmark = pytest.mark.db_free


def test_admission_allows_burst_two_then_refills_at_six_per_minute() -> None:
    now = [0.0]
    guard = RefinementAdmissionGuard(clock=lambda: now[0])

    first = guard.acquire("client-a")
    second = guard.acquire("client-a")
    first.release()
    second.release()
    rejected = guard.acquire("client-a")

    assert first.accepted is True
    assert second.accepted is True
    assert rejected.accepted is False
    assert rejected.retry_after_seconds == 10

    now[0] = 10.0

    refilled = guard.acquire("client-a")

    assert refilled.accepted is True
    refilled.release()


def test_admission_sustains_six_requests_per_minute_after_initial_burst() -> None:
    now = [0.0]
    guard = RefinementAdmissionGuard(clock=lambda: now[0])

    for second in (0.0, 0.0, 10.0, 20.0, 30.0, 40.0):
        now[0] = second
        admission = guard.acquire("client-a")
        assert admission.accepted is True
        admission.release()

    rejected = guard.acquire("client-a")

    assert rejected.accepted is False
    assert rejected.retry_after_seconds == 10


def test_admission_enforces_app_wide_concurrency_without_consuming_rate_tokens() -> (
    None
):
    guard = RefinementAdmissionGuard(clock=lambda: 0.0)
    first = guard.acquire("client-a")
    second = guard.acquire("client-b")
    rejected = guard.acquire("client-c")

    assert first.accepted is True
    assert second.accepted is True
    assert rejected.accepted is False
    assert rejected.retry_after_seconds == 1

    first.release()
    accepted_after_release = guard.acquire("client-c")

    assert accepted_after_release.accepted is True
    second.release()
    accepted_after_release.release()


def test_admission_bounds_idle_client_retention() -> None:
    now = [0.0]
    guard = RefinementAdmissionGuard(clock=lambda: now[0], max_clients=2)
    guard.acquire("client-a").release()
    guard.acquire("client-b").release()
    guard.acquire("client-c").release()

    assert guard.client_count == 2

    now[0] = 61.0
    guard.acquire("client-d").release()

    assert guard.client_count == 1

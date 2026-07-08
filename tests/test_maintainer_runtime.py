from __future__ import annotations

import json
import os
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.maintainer.runtime import (
    LeaseOwnershipError,
    LockBusyError,
    RunLease,
)

NOW = datetime(2026, 7, 8, 10, tzinfo=UTC)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_first_run_lease_blocks_a_second_worker(tmp_path: Path) -> None:
    first = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    with pytest.raises(LockBusyError, match="catalog-curation"):
        RunLease.acquire(
            tmp_path,
            "catalog-discovery",
            now=NOW + timedelta(minutes=1),
        )

    assert RunLease.load(tmp_path) == first


def test_run_lease_is_immutable_and_wrong_token_cannot_assert_or_release(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    forged = RunLease(
        state_dir=tmp_path,
        worker=lease.worker,
        token="wrong-token",
    )

    with pytest.raises(FrozenInstanceError):
        lease.token = "replacement"
    with pytest.raises(LeaseOwnershipError, match="does not own"):
        lease.assert_owner("wrong-token")
    with pytest.raises(LeaseOwnershipError, match="does not own"):
        forged.release()

    assert lease.lock_dir.is_dir()
    assert _read_json(lease.metadata_path)["token"] == lease.token


def test_release_allows_another_worker_to_acquire(tmp_path: Path) -> None:
    first = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    first.release()
    second = RunLease.acquire(
        tmp_path,
        "catalog-discovery",
        now=NOW + timedelta(minutes=1),
    )

    assert second.worker == "catalog-discovery"
    assert second.token != first.token
    assert second.lock_dir.is_dir()


def test_stale_valid_lock_is_recovered_and_preserved(tmp_path: Path) -> None:
    first = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    second = RunLease.acquire(
        tmp_path,
        "catalog-discovery",
        now=NOW + timedelta(hours=7),
    )

    stale_dirs = list(tmp_path.glob("run.lock.stale-*"))
    assert second.token != first.token
    assert len(stale_dirs) == 1
    assert _read_json(stale_dirs[0] / "owner.json")["token"] == first.token


@pytest.mark.parametrize("metadata", [None, "not-json"])
def test_stale_lock_with_missing_or_malformed_metadata_is_recovered(
    tmp_path: Path,
    metadata: str | None,
) -> None:
    lock_dir = tmp_path / "run.lock"
    lock_dir.mkdir()
    if metadata is not None:
        (lock_dir / "owner.json").write_text(metadata, encoding="utf-8")
    stale_time = (NOW - timedelta(hours=7)).timestamp()
    os.utime(lock_dir, (stale_time, stale_time))

    lease = RunLease.acquire(tmp_path, "catalog-discovery", now=NOW)

    assert lease.worker == "catalog-discovery"
    assert len(list(tmp_path.glob("run.lock.stale-*"))) == 1


def test_fresh_malformed_lock_is_treated_as_busy(tmp_path: Path) -> None:
    lock_dir = tmp_path / "run.lock"
    lock_dir.mkdir()
    (lock_dir / "owner.json").write_text("not-json", encoding="utf-8")
    fresh_time = (NOW - timedelta(minutes=1)).timestamp()
    os.utime(lock_dir, (fresh_time, fresh_time))

    with pytest.raises(LockBusyError, match="unknown"):
        RunLease.acquire(tmp_path, "catalog-discovery", now=NOW)

    assert lock_dir.is_dir()


def test_heartbeat_does_not_implicitly_serialize_environment_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GH_TOKEN", "secret-from-environment")
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    heartbeat_path = lease.write_heartbeat(
        "review",
        {"pull_request": 42, "status": "running"},
    )

    heartbeat = _read_json(heartbeat_path)
    assert heartbeat == {
        "worker": "catalog-curation",
        "phase": "review",
        "details": {"pull_request": 42, "status": "running"},
        "updated_at": heartbeat["updated_at"],
    }
    assert "secret-from-environment" not in heartbeat_path.read_text(encoding="utf-8")


def test_heartbeat_refreshes_owner_timestamp(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    later = NOW + timedelta(minutes=20)

    lease.heartbeat(now=later)

    assert _read_json(lease.metadata_path) == {
        "worker": lease.worker,
        "token": lease.token,
        "updated_at": later.isoformat(),
    }

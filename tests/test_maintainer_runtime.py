from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.maintainer.runtime import (
    LeaseOwnershipError,
    LockBusyError,
    RunLease,
    RunLeaseError,
)

pytestmark = pytest.mark.db_free

NOW = datetime(2026, 7, 8, 10, tzinfo=UTC)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_lease_has_minimal_private_owner_payload(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    previous_umask = os.umask(0)
    try:
        lease = RunLease.acquire(state_dir, "curation", now=NOW)
    finally:
        os.umask(previous_umask)

    assert lease.worker == "curation"
    assert re.fullmatch(r"[0-9a-f]{32}", lease.run_id)
    assert state_dir.stat().st_mode & 0o777 == 0o700
    assert lease.lock_dir.stat().st_mode & 0o777 == 0o700
    assert lease.owner_path.stat().st_mode & 0o777 == 0o600
    assert _read_json(lease.owner_path) == {
        "worker": "curation",
        "run_id": lease.run_id,
        "acquired_at": NOW.isoformat(),
        "heartbeat_at": NOW.isoformat(),
    }
    assert not list(state_dir.glob("*credential*"))


def test_run_lease_blocks_fresh_competitor(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)

    with pytest.raises(LockBusyError, match="curation"):
        RunLease.acquire(tmp_path, "discovery", now=NOW + timedelta(minutes=1))

    assert RunLease.load_owner(tmp_path, "curation", lease.run_id) == lease


def test_run_lease_preserves_stale_lock_on_takeover(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)

    new = RunLease.acquire(tmp_path, "discovery", now=NOW + timedelta(hours=7))

    stale_locks = list(tmp_path.glob("run.lock.stale-*"))
    assert len(stale_locks) == 1
    assert _read_json(stale_locks[0] / "owner.json")["run_id"] == old.run_id
    assert RunLease.load_owner(tmp_path, "discovery", new.run_id) == new


def test_old_run_id_cannot_adopt_stale_successor(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    new = RunLease.acquire(tmp_path, "curation", now=NOW + timedelta(hours=7))

    with pytest.raises(LeaseOwnershipError):
        RunLease.load_owner(tmp_path, "curation", old.run_id)
    with pytest.raises(LeaseOwnershipError):
        old.heartbeat(now=NOW + timedelta(hours=8))
    with pytest.raises(LeaseOwnershipError):
        old.release()

    assert RunLease.load_owner(tmp_path, "curation", new.run_id) == new


def test_other_worker_cannot_use_active_run_id(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "discovery", now=NOW)

    with pytest.raises(LeaseOwnershipError):
        RunLease.load_owner(tmp_path, "curation", lease.run_id)


def test_heartbeat_and_release_require_exact_owner(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    later = NOW + timedelta(minutes=5)

    loaded = RunLease.load_owner(tmp_path, "curation", lease.run_id)
    loaded.heartbeat(now=later)

    assert _read_json(lease.owner_path)["heartbeat_at"] == later.isoformat()
    forged = RunLease(state_dir=tmp_path, worker="curation", run_id="f" * 32)
    with pytest.raises(LeaseOwnershipError):
        forged.heartbeat(now=later)
    with pytest.raises(LeaseOwnershipError):
        forged.release()

    loaded.release()
    assert not lease.lock_dir.exists()


@pytest.mark.parametrize(
    "unsafe_kind",
    ["symlink", "directory", "malformed", "oversized"],
)
def test_owner_rejects_unsafe_or_invalid_metadata(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    if unsafe_kind == "symlink":
        replacement = tmp_path / "replacement-owner.json"
        replacement.write_text(lease.owner_path.read_text(encoding="utf-8"))
        replacement.chmod(0o600)
        lease.owner_path.unlink()
        lease.owner_path.symlink_to(replacement)
    elif unsafe_kind == "directory":
        lease.owner_path.unlink()
        lease.owner_path.mkdir()
    elif unsafe_kind == "malformed":
        lease.owner_path.write_text("not-json", encoding="utf-8")
        lease.owner_path.chmod(0o600)
    else:
        lease.owner_path.write_text("x" * 4097, encoding="utf-8")
        lease.owner_path.chmod(0o600)

    with pytest.raises(RunLeaseError):
        RunLease.load_owner(tmp_path, "curation", lease.run_id)


def test_run_lease_rejects_state_directory_symlink(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    lease = RunLease.acquire(state_dir, "curation", now=NOW)
    alias = tmp_path / "state-alias"
    alias.symlink_to(state_dir, target_is_directory=True)

    with pytest.raises(RunLeaseError):
        RunLease.load_owner(alias, "curation", lease.run_id)

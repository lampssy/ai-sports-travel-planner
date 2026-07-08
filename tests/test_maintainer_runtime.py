from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from queue import Queue
from threading import Event, Thread, current_thread

import pytest
from pydantic import ValidationError

from ops.maintainer import runtime as maintainer_runtime
from ops.maintainer.models import MaintainerState
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


def _wait(event: Event) -> None:
    assert event.wait(timeout=5), "concurrency barrier was not reached"


def _join(thread: Thread) -> None:
    thread.join(timeout=5)
    assert not thread.is_alive(), f"{thread.name} did not finish"


def _start_operation(
    name: str,
    operation: Callable[[], object],
    outcomes: Queue[tuple[str, object | None, BaseException | None]],
) -> Thread:
    def run() -> None:
        try:
            outcomes.put((name, operation(), None))
        except BaseException as exc:
            outcomes.put((name, None, exc))

    thread = Thread(target=run, name=name)
    thread.start()
    return thread


def test_first_run_lease_blocks_a_second_worker(tmp_path: Path) -> None:
    first = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    with pytest.raises(LockBusyError, match="catalog-curation"):
        RunLease.acquire(
            tmp_path,
            "catalog-discovery",
            now=NOW + timedelta(minutes=1),
        )

    assert RunLease.load(tmp_path) == first


def test_lease_files_are_private_independent_of_umask(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    previous_umask = os.umask(0)
    try:
        lease = RunLease.acquire(state_dir, "catalog-curation", now=NOW)
    finally:
        os.umask(previous_umask)

    assert state_dir.stat().st_mode & 0o777 == 0o700
    assert lease.lock_dir.stat().st_mode & 0o777 == 0o700
    assert lease.metadata_path.stat().st_mode & 0o777 == 0o600
    assert (state_dir / "run.transition.lock").stat().st_mode & 0o777 == 0o600


def test_owned_legacy_state_directory_is_tightened_to_private_mode(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o755)
    state_dir.chmod(0o755)

    RunLease.acquire(state_dir, "catalog-curation", now=NOW)

    assert state_dir.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("unsafe_kind", ["symlink", "regular-file", "foreign-owner"])
def test_unsafe_state_directory_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_kind: str,
) -> None:
    state_dir = tmp_path / "state"
    if unsafe_kind == "symlink":
        target = tmp_path / "target"
        target.mkdir()
        state_dir.symlink_to(target, target_is_directory=True)
    elif unsafe_kind == "regular-file":
        state_dir.write_text("not a directory", encoding="utf-8")
    else:
        state_dir.mkdir()
        monkeypatch.setattr(os, "getuid", lambda: state_dir.stat().st_uid + 1)

    with pytest.raises(RunLeaseError):
        RunLease.acquire(state_dir, "catalog-curation", now=NOW)


def test_loading_lease_through_state_directory_symlink_is_rejected(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "real-state"
    RunLease.acquire(state_dir, "catalog-curation", now=NOW)
    alias = tmp_path / "state-alias"
    alias.symlink_to(state_dir, target_is_directory=True)

    with pytest.raises(RunLeaseError):
        RunLease.load(alias)


@pytest.mark.parametrize("unsafe_kind", ["symlink", "permissive", "foreign-owner"])
def test_owner_metadata_requires_safe_regular_current_uid_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_kind: str,
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    if unsafe_kind == "symlink":
        payload = lease.metadata_path.read_text(encoding="utf-8")
        replacement = tmp_path / "replacement-owner.json"
        replacement.write_text(payload, encoding="utf-8")
        lease.metadata_path.unlink()
        lease.metadata_path.symlink_to(replacement)
    elif unsafe_kind == "permissive":
        lease.metadata_path.chmod(0o640)
    else:
        monkeypatch.setattr(os, "getuid", lambda: lease.metadata_path.stat().st_uid + 1)

    with pytest.raises(RunLeaseError):
        RunLease.load(tmp_path)


def test_json_temporary_file_is_private_independent_of_umask(tmp_path: Path) -> None:
    target = tmp_path / "owner.json"
    previous_umask = os.umask(0)
    try:
        temporary = maintainer_runtime._write_json_temp(target, {"token": "secret"})
    finally:
        os.umask(previous_umask)
    try:
        assert temporary.stat().st_mode & 0o777 == 0o600
    finally:
        temporary.unlink(missing_ok=True)


def test_atomic_owner_update_and_release_fsync_containing_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    synced_modes: list[int] = []
    real_fsync = maintainer_runtime.os.fsync

    def record_fsync(descriptor: int) -> None:
        synced_modes.append(maintainer_runtime.os.fstat(descriptor).st_mode)
        real_fsync(descriptor)

    monkeypatch.setattr(maintainer_runtime.os, "fsync", record_fsync)

    lease.heartbeat(now=NOW + timedelta(minutes=1))
    lease.release()

    assert any(stat.S_ISREG(mode) for mode in synced_modes)
    assert sum(stat.S_ISDIR(mode) for mode in synced_modes) >= 3


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
    with pytest.raises(LeaseOwnershipError) as assert_error:
        lease.assert_owner("wrong-token")
    with pytest.raises(LeaseOwnershipError) as release_error:
        forged.release()

    for error in (assert_error.value, release_error.value):
        message = str(error)
        assert "wrong-token" not in message
        assert lease.token not in message
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


def test_stale_takeover_and_owner_heartbeat_are_linearized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    original_load_owner = maintainer_runtime._load_owner
    original_transition_mutex = maintainer_runtime._transition_mutex
    stale_read = Event()
    allow_takeover = Event()
    heartbeat_attempted_mutex = Event()
    outcomes: Queue[tuple[str, object | None, BaseException | None]] = Queue()

    def gated_load_owner(path: Path) -> object:
        metadata = original_load_owner(path)
        if (
            current_thread().name == "takeover"
            and metadata is not None
            and metadata.token == lease.token
        ):
            stale_read.set()
            _wait(allow_takeover)
        return metadata

    @contextmanager
    def observed_transition_mutex(state_dir: Path):
        if current_thread().name == "heartbeat":
            heartbeat_attempted_mutex.set()
        with original_transition_mutex(state_dir):
            yield

    monkeypatch.setattr(maintainer_runtime, "_load_owner", gated_load_owner)
    monkeypatch.setattr(
        maintainer_runtime,
        "_transition_mutex",
        observed_transition_mutex,
    )

    takeover = _start_operation(
        "takeover",
        lambda: RunLease.acquire(
            tmp_path,
            "catalog-discovery",
            now=NOW + timedelta(hours=7),
        ),
        outcomes,
    )
    _wait(stale_read)
    heartbeat = _start_operation(
        "heartbeat",
        lambda: lease.heartbeat(now=NOW + timedelta(hours=7)),
        outcomes,
    )
    _wait(heartbeat_attempted_mutex)
    allow_takeover.set()
    _join(takeover)
    _join(heartbeat)

    results = {}
    for _ in range(2):
        name, value, error = outcomes.get_nowait()
        results[name] = (value, error)
    successor, takeover_error = results["takeover"]
    _, heartbeat_error = results["heartbeat"]
    assert takeover_error is None
    assert isinstance(successor, RunLease)
    assert isinstance(heartbeat_error, LeaseOwnershipError)
    assert RunLease.load(tmp_path) == successor


def test_release_finishes_before_successor_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    original_load_owner = maintainer_runtime._load_owner
    original_transition_mutex = maintainer_runtime._transition_mutex
    release_owner_read = Event()
    allow_release = Event()
    successor_attempted_mutex = Event()
    outcomes: Queue[tuple[str, object | None, BaseException | None]] = Queue()

    def gated_load_owner(path: Path) -> object:
        metadata = original_load_owner(path)
        if (
            current_thread().name == "release"
            and metadata is not None
            and metadata.token == lease.token
        ):
            release_owner_read.set()
            _wait(allow_release)
        return metadata

    @contextmanager
    def observed_transition_mutex(state_dir: Path):
        if current_thread().name == "successor":
            successor_attempted_mutex.set()
        with original_transition_mutex(state_dir):
            yield

    monkeypatch.setattr(maintainer_runtime, "_load_owner", gated_load_owner)
    monkeypatch.setattr(
        maintainer_runtime,
        "_transition_mutex",
        observed_transition_mutex,
    )

    release = _start_operation("release", lease.release, outcomes)
    _wait(release_owner_read)
    successor = _start_operation(
        "successor",
        lambda: RunLease.acquire(
            tmp_path,
            "catalog-discovery",
            now=NOW + timedelta(hours=7),
        ),
        outcomes,
    )
    _wait(successor_attempted_mutex)
    allow_release.set()
    _join(release)
    _join(successor)

    results = {}
    for _ in range(2):
        name, value, error = outcomes.get_nowait()
        results[name] = (value, error)
    _, release_error = results["release"]
    successor_lease, successor_error = results["successor"]
    assert release_error is None
    assert successor_error is None
    assert isinstance(successor_lease, RunLease)
    assert RunLease.load(tmp_path) == successor_lease
    assert not list(tmp_path.glob("run.lock.stale-*"))


def test_heartbeat_does_not_implicitly_serialize_environment_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GH_TOKEN", "secret-from-environment")
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    details = maintainer_runtime.HeartbeatDetails(
        pr=42,
        state=MaintainerState.WORKING,
        candidate_key="catalog-curation-42",
        reason_code="review_started",
    )

    heartbeat_path = lease.write_heartbeat(
        "review",
        details,
    )

    heartbeat = _read_json(heartbeat_path)
    assert heartbeat == {
        "worker": "catalog-curation",
        "phase": "review",
        "details": {
            "pr": 42,
            "state": "maintainer:working",
            "candidate_key": "catalog-curation-42",
            "reason_code": "review_started",
        },
        "updated_at": heartbeat["updated_at"],
    }
    assert "secret-from-environment" not in heartbeat_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "unsafe_details",
    [
        {"gh_token": "credential"},
        {"environment": {"GH_TOKEN": "credential"}},
        {"command_output": "full command output"},
        {"source_content": "full source content"},
    ],
)
def test_heartbeat_rejects_unapproved_detail_fields(
    tmp_path: Path,
    unsafe_details: dict[str, object],
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    with pytest.raises(ValidationError, match="extra_forbidden"):
        maintainer_runtime.HeartbeatDetails.model_validate(unsafe_details)
    with pytest.raises(TypeError, match="HeartbeatDetails"):
        lease.write_heartbeat("review", unsafe_details)  # type: ignore[arg-type]

    assert not (tmp_path / "catalog-curation-heartbeat.json").exists()


@pytest.mark.parametrize(
    "unsafe_details",
    [
        {"candidate_key": "x" * 129},
        {"reason_code": "x" * 65},
        {"reason_code": "command output with whitespace"},
    ],
)
def test_heartbeat_rejects_oversized_or_free_form_values(
    unsafe_details: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        maintainer_runtime.HeartbeatDetails.model_validate(unsafe_details)


@pytest.mark.parametrize(
    "phase",
    [
        "x" * 65,
        "git status\nfull command output",
        "../../source-content",
    ],
)
def test_write_heartbeat_rejects_unsafe_phase_codes(
    tmp_path: Path,
    phase: str,
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)

    with pytest.raises(ValueError, match="concise operational code"):
        lease.write_heartbeat(phase, maintainer_runtime.HeartbeatDetails(pr=42))

    assert not (tmp_path / "catalog-curation-heartbeat.json").exists()


@pytest.mark.parametrize(
    "unsafe_details",
    [
        {"reason_code": "x" * 65},
        {"candidate_key": object()},
    ],
)
def test_write_heartbeat_revalidates_constructed_details(
    tmp_path: Path,
    unsafe_details: dict[str, object],
) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    details = maintainer_runtime.HeartbeatDetails.model_construct(**unsafe_details)

    with pytest.raises(ValidationError):
        lease.write_heartbeat("review", details)

    assert not (tmp_path / "catalog-curation-heartbeat.json").exists()


def test_heartbeat_refreshes_owner_timestamp(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    later = NOW + timedelta(minutes=20)

    lease.heartbeat(now=later)

    assert _read_json(lease.metadata_path) == {
        "worker": lease.worker,
        "token": lease.token,
        "updated_at": later.isoformat(),
    }


def test_lost_lease_error_does_not_expose_either_token(tmp_path: Path) -> None:
    original = RunLease.acquire(tmp_path, "catalog-curation", now=NOW)
    successor = RunLease.acquire(
        tmp_path,
        "catalog-discovery",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(LeaseOwnershipError) as error:
        original.heartbeat(now=NOW + timedelta(hours=8))

    message = str(error.value)
    assert original.token not in message
    assert successor.token not in message

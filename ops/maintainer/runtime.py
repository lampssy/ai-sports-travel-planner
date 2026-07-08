from __future__ import annotations

import fcntl
import json
import os
import re
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ops.maintainer.models import MaintainerState

DEFAULT_STALE_AFTER = timedelta(hours=6)
_HEARTBEAT_PHASE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class RunLeaseError(RuntimeError):
    """Base error for local maintainer lease operations."""


class LockBusyError(RunLeaseError):
    """Raised when another worker owns a fresh maintainer lease."""

    def __init__(self, worker: str) -> None:
        self.worker = worker
        super().__init__(f"maintainer run lock is held by worker {worker!r}")


class LeaseOwnershipError(RunLeaseError):
    """Raised when a process tries to mutate a lease it does not own."""


class LeaseMetadataError(RunLeaseError):
    """Raised when active lease metadata cannot be loaded safely."""


class HeartbeatDetails(BaseModel):
    """Allowlisted, bounded operational details safe for local persistence."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    pr: int | None = Field(default=None, ge=1)
    state: MaintainerState | None = None
    candidate_key: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    reason_code: str | None = Field(
        default=None,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )


@dataclass(frozen=True, slots=True)
class _OwnerMetadata:
    worker: str
    token: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RunLease:
    token: str
    worker: str
    state_dir: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_dir", Path(self.state_dir))
        _validate_worker(self.worker)
        if not self.token:
            raise ValueError("lease token must not be blank")

    @property
    def lock_dir(self) -> Path:
        return self.state_dir / "run.lock"

    @property
    def metadata_path(self) -> Path:
        return self.lock_dir / "owner.json"

    @classmethod
    def acquire(
        cls,
        state_dir: str | Path,
        worker: str,
        now: datetime | None = None,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> RunLease:
        state_path = Path(state_dir)
        _validate_worker(worker)
        observed_at = _normalize_time(now)
        if stale_after <= timedelta(0):
            raise ValueError("stale_after must be positive")

        state_path.mkdir(parents=True, exist_ok=True)
        with _transition_mutex(state_path):
            return cls._acquire_locked(
                state_path,
                worker,
                observed_at,
                stale_after,
            )

    @classmethod
    def _acquire_locked(
        cls,
        state_path: Path,
        worker: str,
        observed_at: datetime,
        stale_after: timedelta,
    ) -> RunLease:
        lock_dir = state_path / "run.lock"
        for _attempt in range(8):
            try:
                lock_dir.mkdir()
            except FileExistsError:
                metadata = _load_owner(lock_dir / "owner.json")
                try:
                    updated_at = (
                        metadata.updated_at
                        if metadata is not None
                        else datetime.fromtimestamp(lock_dir.stat().st_mtime, UTC)
                    )
                except FileNotFoundError:
                    continue

                if observed_at - updated_at < stale_after:
                    owner = metadata.worker if metadata is not None else "unknown"
                    raise LockBusyError(owner)

                stale_dir = _next_stale_path(state_path, observed_at)
                try:
                    lock_dir.rename(stale_dir)
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    raise RunLeaseError(
                        f"unable to preserve stale maintainer lock at {stale_dir}"
                    ) from exc
                continue
            except OSError as exc:
                raise RunLeaseError(
                    f"unable to create maintainer lock directory {lock_dir}"
                ) from exc

            lease = cls(token=uuid4().hex, worker=worker, state_dir=state_path)
            try:
                _write_json_atomic(
                    lease.metadata_path,
                    _owner_payload(lease.worker, lease.token, observed_at),
                )
            except Exception:
                _remove_failed_acquisition(lease.lock_dir)
                raise
            return lease

        raise RunLeaseError("maintainer lock changed repeatedly during acquisition")

    @classmethod
    def load(cls, state_dir: str | Path) -> RunLease:
        state_path = Path(state_dir)
        metadata = _load_owner(state_path / "run.lock" / "owner.json")
        if metadata is None:
            raise LeaseMetadataError(
                f"maintainer lock metadata is missing or malformed in {state_path}"
            )
        return cls(
            token=metadata.token,
            worker=metadata.worker,
            state_dir=state_path,
        )

    def assert_owner(self, token: str) -> None:
        metadata = _load_owner(self.metadata_path)
        if metadata is None or metadata.token != token:
            raise LeaseOwnershipError(
                f"maintainer lock ownership check failed for {self.lock_dir}"
            )
        if metadata.worker != self.worker:
            raise LeaseOwnershipError(
                f"maintainer lock ownership check failed for {self.lock_dir}"
            )

    def heartbeat(self, now: datetime | None = None) -> None:
        with _transition_mutex(self.state_dir):
            self._heartbeat_at(_normalize_time(now))

    def write_heartbeat(
        self,
        phase: str,
        details: HeartbeatDetails,
    ) -> Path:
        if type(details) is not HeartbeatDetails:
            raise TypeError("details must be a HeartbeatDetails instance")
        raw_details = {
            field_name: getattr(details, field_name)
            for field_name in HeartbeatDetails.model_fields
        }
        validated_details = HeartbeatDetails.model_validate(raw_details)
        if _HEARTBEAT_PHASE_PATTERN.fullmatch(phase) is None:
            raise ValueError("heartbeat phase must be a concise operational code")
        updated_at = _normalize_time(None)
        with _transition_mutex(self.state_dir):
            self._heartbeat_at(updated_at)
            heartbeat_path = self.state_dir / f"{self.worker}-heartbeat.json"
            _write_json_atomic(
                heartbeat_path,
                {
                    "worker": self.worker,
                    "phase": phase,
                    "details": validated_details.model_dump(
                        mode="json",
                        exclude_none=True,
                    ),
                    "updated_at": updated_at.isoformat(),
                },
            )
        return heartbeat_path

    def release(self) -> None:
        with _transition_mutex(self.state_dir):
            self._release_locked()

    def _release_locked(self) -> None:
        self.assert_owner(self.token)
        releasing_dir = self.state_dir / f"run.lock.releasing-{uuid4().hex}"
        try:
            self.lock_dir.rename(releasing_dir)
        except FileNotFoundError as exc:
            raise LeaseOwnershipError(
                f"maintainer lock ownership changed during release of {self.lock_dir}"
            ) from exc
        except OSError as exc:
            raise RunLeaseError(
                f"unable to begin release of maintainer lock {self.lock_dir}"
            ) from exc

        metadata = _load_owner(releasing_dir / "owner.json")
        if (
            metadata is None
            or metadata.token != self.token
            or metadata.worker != self.worker
        ):
            _restore_misplaced_lock(releasing_dir, self.lock_dir)
            raise LeaseOwnershipError(
                "maintainer lock ownership changed during release"
            )

        try:
            (releasing_dir / "owner.json").unlink()
            releasing_dir.rmdir()
        except OSError as exc:
            raise RunLeaseError(
                f"unable to finish release of maintainer lock {releasing_dir}"
            ) from exc

    def _heartbeat_at(self, updated_at: datetime) -> None:
        self.assert_owner(self.token)
        _write_owned_json(
            self,
            self.metadata_path,
            _owner_payload(self.worker, self.token, updated_at),
        )


def _validate_worker(worker: str) -> None:
    if not worker.strip():
        raise ValueError("worker must not be blank")
    if worker in {".", ".."} or "/" in worker or "\\" in worker:
        raise ValueError("worker must be a safe filename component")


@contextmanager
def _transition_mutex(state_dir: Path) -> Iterator[None]:
    state_dir.mkdir(parents=True, exist_ok=True)
    mutex_path = state_dir / "run.transition.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(mutex_path, flags, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _normalize_time(value: datetime | None) -> datetime:
    observed_at = value if value is not None else datetime.now(UTC)
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("lease timestamps must include a timezone")
    return observed_at.astimezone(UTC)


def _owner_payload(worker: str, token: str, updated_at: datetime) -> dict[str, str]:
    return {
        "worker": worker,
        "token": token,
        "updated_at": updated_at.isoformat(),
    }


def _load_owner(path: Path) -> _OwnerMetadata | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        worker = raw["worker"]
        token = raw["token"]
        updated_at_raw = raw["updated_at"]
        if not isinstance(worker, str) or not worker.strip():
            return None
        if not isinstance(token, str) or not token:
            return None
        if not isinstance(updated_at_raw, str):
            return None
        updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
        if updated_at.tzinfo is None or updated_at.utcoffset() is None:
            return None
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return _OwnerMetadata(
        worker=worker,
        token=token,
        updated_at=updated_at.astimezone(UTC),
    )


def _next_stale_path(state_dir: Path, observed_at: datetime) -> Path:
    timestamp = observed_at.strftime("%Y%m%dT%H%M%S.%fZ")
    candidate = state_dir / f"run.lock.stale-{timestamp}"
    suffix = 1
    while candidate.exists():
        candidate = state_dir / f"run.lock.stale-{timestamp}-{suffix}"
        suffix += 1
    return candidate


def _write_json_temp(path: Path, payload: Mapping[str, Any]) -> Path:
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary_path.open("x", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary_path = _write_json_temp(path, payload)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_owned_json(
    lease: RunLease,
    path: Path,
    payload: Mapping[str, Any],
) -> None:
    temporary_path = _write_json_temp(path, payload)
    try:
        lease.assert_owner(lease.token)
        temporary_path.replace(path)
        lease.assert_owner(lease.token)
    except FileNotFoundError as exc:
        raise LeaseOwnershipError(
            "maintainer lock ownership changed during update"
        ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def _remove_failed_acquisition(lock_dir: Path) -> None:
    try:
        for path in lock_dir.iterdir():
            if path.name.startswith(".owner.json.") and path.name.endswith(".tmp"):
                path.unlink(missing_ok=True)
        lock_dir.rmdir()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RunLeaseError(
            f"unable to clean up failed maintainer lock acquisition {lock_dir}"
        ) from exc


def _restore_misplaced_lock(releasing_dir: Path, lock_dir: Path) -> None:
    try:
        releasing_dir.rename(lock_dir)
    except OSError as exc:
        raise RunLeaseError(
            "lease ownership changed during release; the other lock was preserved at "
            f"{releasing_dir}"
        ) from exc

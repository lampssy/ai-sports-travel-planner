from __future__ import annotations

import fcntl
import json
import os
import re
import stat
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
_WORKER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_LEASE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_MAX_LEASE_METADATA_BYTES = 4096


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
    lease_id: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class _SimpleOwnerMetadata:
    worker: str
    run_id: str
    acquired_at: datetime
    heartbeat_at: datetime


@dataclass(frozen=True, slots=True)
class SimpleRunLease:
    """Interim token-free lease used by the simplified maintainer workflow."""

    worker: str
    run_id: str
    state_dir: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_dir", Path(self.state_dir))
        _validate_worker(self.worker)
        _validate_lease_id(self.run_id)

    @property
    def lock_dir(self) -> Path:
        return self.state_dir / "run.lock"

    @property
    def owner_path(self) -> Path:
        return self.lock_dir / "owner.json"

    @classmethod
    def acquire(
        cls,
        state_dir: str | Path,
        worker: str,
        now: datetime | None = None,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> SimpleRunLease:
        state_path = Path(state_dir)
        _validate_worker(worker)
        observed_at = _normalize_time(now)
        if stale_after <= timedelta(0):
            raise ValueError("stale_after must be positive")

        _ensure_private_directory(state_path, parents=True)
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
    ) -> SimpleRunLease:
        lock_dir = state_path / "run.lock"
        for _attempt in range(8):
            try:
                lock_dir.mkdir(mode=0o700)
                _ensure_private_directory(lock_dir, parents=False)
            except FileExistsError:
                _ensure_private_directory(lock_dir, parents=False, create=False)
                try:
                    owner = _load_simple_owner(lock_dir / "owner.json")
                except LeaseMetadataError:
                    owner = None
                try:
                    heartbeat_at = (
                        owner.heartbeat_at
                        if owner is not None
                        else datetime.fromtimestamp(lock_dir.stat().st_mtime, UTC)
                    )
                except FileNotFoundError:
                    continue

                if observed_at - heartbeat_at < stale_after:
                    held_by = owner.worker if owner is not None else "unknown"
                    raise LockBusyError(held_by)

                stale_dir = _next_stale_path(state_path, observed_at)
                try:
                    lock_dir.rename(stale_dir)
                    _fsync_directory(state_path)
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

            lease = cls(worker=worker, run_id=uuid4().hex, state_dir=state_path)
            try:
                _write_json_atomic(
                    lease.owner_path,
                    _simple_owner_payload(
                        lease.worker,
                        lease.run_id,
                        observed_at,
                        observed_at,
                    ),
                )
                _fsync_directory(state_path)
            except Exception:
                _remove_failed_simple_acquisition(lease)
                raise
            return lease

        raise RunLeaseError("maintainer lock changed repeatedly during acquisition")

    @classmethod
    def load_owner(
        cls,
        state_dir: str | Path,
        worker: str,
        run_id: str,
    ) -> SimpleRunLease:
        state_path = Path(state_dir)
        _validate_worker(worker)
        _validate_lease_id(run_id)
        _ensure_private_directory(state_path, parents=False, create=False)
        _ensure_private_directory(
            state_path / "run.lock",
            parents=False,
            create=False,
        )
        owner = _load_simple_owner(state_path / "run.lock" / "owner.json")
        if owner.worker != worker or owner.run_id != run_id:
            raise LeaseOwnershipError("maintainer run does not own the active lock")
        return cls(worker=worker, run_id=run_id, state_dir=state_path)

    def assert_owner(self) -> None:
        owner = _load_simple_owner(self.owner_path)
        if owner.worker != self.worker or owner.run_id != self.run_id:
            raise LeaseOwnershipError("maintainer run does not own the active lock")

    def heartbeat(self, now: datetime | None = None) -> None:
        heartbeat_at = _normalize_time(now)
        with _transition_mutex(self.state_dir):
            owner = _load_simple_owner(self.owner_path)
            if owner.worker != self.worker or owner.run_id != self.run_id:
                raise LeaseOwnershipError("maintainer run does not own the active lock")
            if heartbeat_at < owner.heartbeat_at:
                raise ValueError("heartbeat timestamp must not move backwards")
            _write_simple_owned_json(
                self,
                self.owner_path,
                _simple_owner_payload(
                    self.worker,
                    self.run_id,
                    owner.acquired_at,
                    heartbeat_at,
                ),
            )

    def release(self) -> None:
        with _transition_mutex(self.state_dir):
            self.assert_owner()
            releasing_dir = self.state_dir / f"run.lock.releasing-{uuid4().hex}"
            try:
                self.lock_dir.rename(releasing_dir)
                _fsync_directory(self.state_dir)
            except FileNotFoundError as exc:
                raise LeaseOwnershipError(
                    "maintainer lock ownership changed during release"
                ) from exc
            except OSError as exc:
                raise RunLeaseError(
                    f"unable to begin release of maintainer lock {self.lock_dir}"
                ) from exc

            try:
                owner = _load_simple_owner(releasing_dir / "owner.json")
            except RunLeaseError:
                _restore_misplaced_lock(releasing_dir, self.lock_dir)
                raise
            if owner.worker != self.worker or owner.run_id != self.run_id:
                _restore_misplaced_lock(releasing_dir, self.lock_dir)
                raise LeaseOwnershipError(
                    "maintainer lock ownership changed during release"
                )

            try:
                (releasing_dir / "owner.json").unlink()
                releasing_dir.rmdir()
                _fsync_directory(self.state_dir)
            except OSError as exc:
                raise RunLeaseError(
                    f"unable to finish release of maintainer lock {releasing_dir}"
                ) from exc


@dataclass(frozen=True, slots=True)
class RunLease:
    token: str
    worker: str
    state_dir: Path
    lease_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_dir", Path(self.state_dir))
        _validate_worker(self.worker)
        if not self.token:
            raise ValueError("lease token must not be blank")
        _validate_lease_id(self.lease_id)

    @property
    def lock_dir(self) -> Path:
        return self.state_dir / "run.lock"

    @property
    def metadata_path(self) -> Path:
        return self.lock_dir / "owner.json"

    @property
    def credential_path(self) -> Path:
        return self.state_dir / f"run.credential-{self.worker}.json"

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

        _ensure_private_directory(state_path, parents=True)
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
                lock_dir.mkdir(mode=0o700)
                _ensure_private_directory(lock_dir, parents=False)
            except FileExistsError:
                _ensure_private_directory(lock_dir, parents=False)
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
                    _fsync_directory(state_path)
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

            lease = cls(
                token=uuid4().hex,
                worker=worker,
                state_dir=state_path,
                lease_id=uuid4().hex,
            )
            try:
                _write_json_atomic(
                    lease.metadata_path,
                    _owner_payload(
                        lease.worker,
                        lease.token,
                        lease.lease_id,
                        observed_at,
                    ),
                )
                _write_worker_credential(lease, observed_at)
                _fsync_directory(state_path)
            except Exception:
                try:
                    _remove_matching_credential(lease)
                finally:
                    _remove_failed_acquisition(lease)
                raise
            return lease

        raise RunLeaseError("maintainer lock changed repeatedly during acquisition")

    @classmethod
    def load(cls, state_dir: str | Path) -> RunLease:
        state_path = Path(state_dir)
        _ensure_private_directory(state_path, parents=False, create=False)
        _ensure_private_directory(
            state_path / "run.lock",
            parents=False,
            create=False,
        )
        metadata = _load_owner(state_path / "run.lock" / "owner.json")
        if metadata is None:
            raise LeaseMetadataError(
                f"maintainer lock metadata is missing or malformed in {state_path}"
            )
        return cls(
            token=metadata.token,
            worker=metadata.worker,
            state_dir=state_path,
            lease_id=metadata.lease_id,
        )

    @classmethod
    def load_for_worker(
        cls,
        state_dir: str | Path,
        worker: str,
        lease_id: str,
    ) -> RunLease:
        state_path = Path(state_dir)
        _validate_worker(worker)
        _validate_lease_id(lease_id)
        _ensure_private_directory(state_path, parents=False, create=False)
        _ensure_private_directory(
            state_path / "run.lock",
            parents=False,
            create=False,
        )
        owner = _load_owner(state_path / "run.lock" / "owner.json")
        credential = _load_owner(state_path / f"run.credential-{worker}.json")
        if owner is None:
            raise LeaseMetadataError("active maintainer lock metadata is invalid")
        if (
            credential is None
            or owner.worker != worker
            or credential.worker != worker
            or credential.token != owner.token
            or owner.lease_id != lease_id
            or credential.lease_id != lease_id
        ):
            raise LeaseOwnershipError(
                "maintainer worker credential does not own the active lock"
            )
        lease = cls(
            token=credential.token,
            worker=worker,
            state_dir=state_path,
            lease_id=lease_id,
        )
        lease.assert_owner(credential.token)
        return lease

    def assert_owner(self, token: str) -> None:
        _ensure_private_directory(self.state_dir, parents=False, create=False)
        _ensure_private_directory(self.lock_dir, parents=False, create=False)
        metadata = _load_owner(self.metadata_path)
        if (
            metadata is None
            or metadata.token != token
            or metadata.lease_id != self.lease_id
        ):
            raise LeaseOwnershipError(
                f"maintainer lock ownership check failed for {self.lock_dir}"
            )
        if metadata.worker != self.worker:
            raise LeaseOwnershipError(
                f"maintainer lock ownership check failed for {self.lock_dir}"
            )

    def assert_credential(self) -> None:
        credential = _load_owner(self.credential_path)
        if (
            credential is None
            or credential.worker != self.worker
            or credential.token != self.token
            or credential.lease_id != self.lease_id
        ):
            raise LeaseOwnershipError(
                "maintainer worker credential does not own the active lock"
            )
        self.assert_owner(credential.token)

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
        self.assert_credential()
        self.assert_owner(self.token)
        releasing_dir = self.state_dir / f"run.lock.releasing-{uuid4().hex}"
        try:
            self.lock_dir.rename(releasing_dir)
            _fsync_directory(self.state_dir)
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
            or metadata.lease_id != self.lease_id
        ):
            _restore_misplaced_lock(releasing_dir, self.lock_dir)
            raise LeaseOwnershipError(
                "maintainer lock ownership changed during release"
            )

        credential = _load_owner(self.credential_path)
        if (
            credential is None
            or credential.token != self.token
            or credential.worker != self.worker
            or credential.lease_id != self.lease_id
        ):
            _restore_misplaced_lock(releasing_dir, self.lock_dir)
            raise LeaseOwnershipError(
                "maintainer worker credential changed during release"
            )

        try:
            (releasing_dir / "owner.json").unlink()
            releasing_dir.rmdir()
            _fsync_directory(self.state_dir)
        except OSError as exc:
            raise RunLeaseError(
                f"unable to finish release of maintainer lock {releasing_dir}"
            ) from exc
        _remove_matching_credential(self, required=True)

    def _heartbeat_at(self, updated_at: datetime) -> None:
        self.assert_credential()
        self.assert_owner(self.token)
        _write_owned_json(
            self,
            self.metadata_path,
            _owner_payload(
                self.worker,
                self.token,
                self.lease_id,
                updated_at,
            ),
        )


def _validate_worker(worker: str) -> None:
    if _WORKER_PATTERN.fullmatch(worker) is None or worker in {".", ".."}:
        raise ValueError("worker must be a safe filename component")


def _validate_lease_id(lease_id: str) -> None:
    if _LEASE_ID_PATTERN.fullmatch(lease_id) is None:
        raise ValueError("lease_id must be a 32-character lowercase hex identifier")


@contextmanager
def _transition_mutex(state_dir: Path) -> Iterator[None]:
    _ensure_private_directory(state_dir, parents=True)
    mutex_path = state_dir / "run.transition.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(mutex_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise RunLeaseError("maintainer transition lock is unsafe")
        os.fchmod(descriptor, 0o600)
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


def _owner_payload(
    worker: str,
    token: str,
    lease_id: str,
    updated_at: datetime,
) -> dict[str, str]:
    return {
        "worker": worker,
        "token": token,
        "lease_id": lease_id,
        "updated_at": updated_at.isoformat(),
    }


def _simple_owner_payload(
    worker: str,
    run_id: str,
    acquired_at: datetime,
    heartbeat_at: datetime,
) -> dict[str, str]:
    return {
        "worker": worker,
        "run_id": run_id,
        "acquired_at": acquired_at.isoformat(),
        "heartbeat_at": heartbeat_at.isoformat(),
    }


def _read_private_json(
    path: Path,
    *,
    max_bytes: int = _MAX_LEASE_METADATA_BYTES,
) -> Any:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
            or metadata.st_size > max_bytes
        ):
            raise LeaseMetadataError("maintainer JSON state is unsafe")
        with os.fdopen(descriptor, encoding="utf-8") as file:
            descriptor = None
            return json.load(file)
    except FileNotFoundError:
        raise
    except LeaseMetadataError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LeaseMetadataError("maintainer JSON state is invalid") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _load_simple_owner(path: Path) -> _SimpleOwnerMetadata:
    try:
        raw = _read_private_json(path)
        if not isinstance(raw, dict) or set(raw) != {
            "worker",
            "run_id",
            "acquired_at",
            "heartbeat_at",
        }:
            raise ValueError
        worker = raw["worker"]
        run_id = raw["run_id"]
        acquired_raw = raw["acquired_at"]
        heartbeat_raw = raw["heartbeat_at"]
        if not all(
            isinstance(value, str)
            for value in (worker, run_id, acquired_raw, heartbeat_raw)
        ):
            raise ValueError
        _validate_worker(worker)
        _validate_lease_id(run_id)
        acquired_at = datetime.fromisoformat(acquired_raw.replace("Z", "+00:00"))
        heartbeat_at = datetime.fromisoformat(heartbeat_raw.replace("Z", "+00:00"))
        if (
            acquired_at.tzinfo is None
            or acquired_at.utcoffset() is None
            or heartbeat_at.tzinfo is None
            or heartbeat_at.utcoffset() is None
        ):
            raise ValueError
        acquired_at = acquired_at.astimezone(UTC)
        heartbeat_at = heartbeat_at.astimezone(UTC)
        if heartbeat_at < acquired_at:
            raise ValueError
    except FileNotFoundError as exc:
        raise LeaseMetadataError("active maintainer owner state is missing") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise LeaseMetadataError("active maintainer owner state is invalid") from exc
    return _SimpleOwnerMetadata(
        worker=worker,
        run_id=run_id,
        acquired_at=acquired_at,
        heartbeat_at=heartbeat_at,
    )


def _load_owner(path: Path) -> _OwnerMetadata | None:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
            or metadata.st_size > _MAX_LEASE_METADATA_BYTES
        ):
            return None
        with os.fdopen(descriptor, encoding="utf-8") as file:
            descriptor = None
            raw = json.load(file)
        if not isinstance(raw, dict) or set(raw) != {
            "worker",
            "token",
            "lease_id",
            "updated_at",
        }:
            return None
        worker = raw["worker"]
        token = raw["token"]
        lease_id = raw["lease_id"]
        updated_at_raw = raw["updated_at"]
        if not isinstance(worker, str) or not worker.strip():
            return None
        if not isinstance(token, str) or not token:
            return None
        if (
            not isinstance(lease_id, str)
            or _LEASE_ID_PATTERN.fullmatch(lease_id) is None
        ):
            return None
        if not isinstance(updated_at_raw, str):
            return None
        updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
        if updated_at.tzinfo is None or updated_at.utcoffset() is None:
            return None
    except (
        FileNotFoundError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return _OwnerMetadata(
        worker=worker,
        token=token,
        lease_id=lease_id,
        updated_at=updated_at.astimezone(UTC),
    )


def _write_worker_credential(lease: RunLease, observed_at: datetime) -> None:
    try:
        lease.credential_path.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise LeaseMetadataError("worker credential path is unsafe") from exc
    else:
        existing = _load_owner(lease.credential_path)
        if existing is None or existing.worker != lease.worker:
            raise LeaseMetadataError("worker credential path is unsafe")
    _write_json_atomic(
        lease.credential_path,
        _owner_payload(
            lease.worker,
            lease.token,
            lease.lease_id,
            observed_at,
        ),
    )


def _remove_matching_credential(
    lease: RunLease,
    *,
    required: bool = False,
) -> None:
    credential = _load_owner(lease.credential_path)
    if credential is None:
        if required:
            raise LeaseOwnershipError("maintainer worker credential is invalid")
        return
    if (
        credential.worker != lease.worker
        or credential.token != lease.token
        or credential.lease_id != lease.lease_id
    ):
        if required:
            raise LeaseOwnershipError("maintainer worker credential changed")
        return
    try:
        lease.credential_path.unlink()
        _fsync_directory(lease.state_dir)
    except OSError as exc:
        raise RunLeaseError("unable to remove maintainer worker credential") from exc


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
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary_path, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            descriptor = None
            json.dump(payload, file, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return temporary_path


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary_path = _write_json_temp(path, payload)
    try:
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
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
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
        lease.assert_owner(lease.token)
    except FileNotFoundError as exc:
        raise LeaseOwnershipError(
            "maintainer lock ownership changed during update"
        ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_simple_owned_json(
    lease: SimpleRunLease,
    path: Path,
    payload: Mapping[str, Any],
) -> None:
    temporary_path = _write_json_temp(path, payload)
    try:
        lease.assert_owner()
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
        lease.assert_owner()
    except FileNotFoundError as exc:
        raise LeaseOwnershipError(
            "maintainer lock ownership changed during update"
        ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def _remove_failed_simple_acquisition(lease: SimpleRunLease) -> None:
    try:
        for path in lease.lock_dir.iterdir():
            if path.name.startswith(".owner.json.") and path.name.endswith(".tmp"):
                path.unlink(missing_ok=True)
        try:
            owner = _load_simple_owner(lease.owner_path)
        except RunLeaseError:
            owner = None
        if (
            owner is not None
            and owner.worker == lease.worker
            and owner.run_id == lease.run_id
        ):
            lease.owner_path.unlink()
        lease.lock_dir.rmdir()
        _fsync_directory(lease.state_dir)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RunLeaseError(
            f"unable to clean up failed maintainer lock acquisition {lease.lock_dir}"
        ) from exc


def _remove_failed_acquisition(lease: RunLease) -> None:
    lock_dir = lease.lock_dir
    try:
        for path in lock_dir.iterdir():
            if path.name.startswith(".owner.json.") and path.name.endswith(".tmp"):
                path.unlink(missing_ok=True)
        owner = _load_owner(lease.metadata_path)
        if (
            owner is not None
            and owner.worker == lease.worker
            and owner.token == lease.token
            and owner.lease_id == lease.lease_id
        ):
            lease.metadata_path.unlink()
        lock_dir.rmdir()
        _fsync_directory(lock_dir.parent)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RunLeaseError(
            f"unable to clean up failed maintainer lock acquisition {lock_dir}"
        ) from exc


def _restore_misplaced_lock(releasing_dir: Path, lock_dir: Path) -> None:
    try:
        releasing_dir.rename(lock_dir)
        _fsync_directory(lock_dir.parent)
    except OSError as exc:
        raise RunLeaseError(
            "lease ownership changed during release; the other lock was preserved at "
            f"{releasing_dir}"
        ) from exc


def _ensure_private_directory(
    path: Path,
    *,
    parents: bool,
    create: bool = True,
) -> None:
    try:
        if create:
            path.mkdir(mode=0o700, parents=parents, exist_ok=True)
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise RunLeaseError("maintainer state directory is unsafe")
            os.fchmod(descriptor, 0o700)
        finally:
            os.close(descriptor)
    except RunLeaseError:
        raise
    except OSError:
        raise RunLeaseError("maintainer state directory is unsafe") from None


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

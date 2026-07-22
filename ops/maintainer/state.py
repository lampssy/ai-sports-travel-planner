from __future__ import annotations

import json
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Iterator, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ops.maintainer.git_ops import GuardedSyncResult
from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.intent import is_allowed_curation_path
from ops.maintainer.runtime import (
    LeaseMetadataError,
    LeaseOwnershipError,
    RunLease,
    RunLeaseError,
    _ensure_private_directory,
    _read_private_json,
    _transition_mutex,
    _write_json_atomic,
)

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_REF_PATTERN = r"^refs/[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$"
_REASON_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"
_MAX_STATE_BYTES = 65536


class StateStoreError(RuntimeError):
    """Raised when persisted maintainer state cannot be trusted or advanced."""


class WorkPhase(StrEnum):
    SELECTED = "selected"
    PREPARED = "prepared"
    REVIEWED = "reviewed"
    VALIDATED = "validated"
    PUSHED = "pushed"
    PUBLISHED = "published"


class PushPhase(StrEnum):
    AUTHORIZED = "authorized"
    PUSHED = "pushed"
    PR_CREATED = "pr-created"
    PUBLISHED = "published"


class ContinuationStatus(StrEnum):
    AVAILABLE = "available"
    RESOLVING = "resolving"
    VALIDATED = "validated"
    CONSUMED = "consumed"
    INVALIDATED = "invalidated"


class ContinuationValidationStatus(StrEnum):
    NOT_RUN = "not-run"
    FAILED = "failed"
    PASSED = "passed"


class RemediationContinuationStatus(StrEnum):
    AVAILABLE = "available"
    RESOLVING = "resolving"
    CONSUMED = "consumed"
    INVALIDATED = "invalidated"


_WORK_PHASES = tuple(WorkPhase)


class WorkState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN.pattern)
    worker: Literal["curation", "discovery"]
    run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    phase: WorkPhase
    updated_at: datetime
    pr_number: int | None = Field(default=None, ge=1)
    candidate_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_ID_PATTERN.pattern,
    )
    candidate_origin: Literal["backlog", "external"] | None = None
    report_path: str | None = Field(
        default=None,
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$",
    )
    resulting_graph_markdown: str | None = Field(
        default=None,
        min_length=1,
        max_length=32768,
    )
    selected_head: str = Field(pattern=_SHA_PATTERN)
    prepared_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    reviewed_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    validated_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    backup_ref: str | None = Field(default=None, pattern=_REF_PATTERN)
    sync: GuardedSyncResult | None = None

    @model_validator(mode="after")
    def validate_work_state(self) -> WorkState:
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        object.__setattr__(self, "updated_at", self.updated_at.astimezone(UTC))

        if self.worker == "curation":
            if self.pr_number is None:
                raise ValueError("curation work requires a PR number")
            if any(
                value is not None
                for value in (
                    self.candidate_key,
                    self.candidate_origin,
                )
            ):
                raise ValueError("curation work cannot include candidate metadata")
        else:
            if self.candidate_key is None or self.candidate_origin is None:
                raise ValueError("discovery work requires candidate identity")
            if self.sync is not None or self.backup_ref is not None:
                raise ValueError("discovery work cannot include curation sync state")
            if self.phase is WorkPhase.PUBLISHED:
                if self.pr_number is None:
                    raise ValueError("published discovery work requires a PR number")
            elif self.pr_number is not None:
                raise ValueError("discovery receives a PR only when published")

        phase_index = _WORK_PHASES.index(self.phase)
        required_fields = (
            (1, "prepared_head", self.prepared_head),
            (2, "reviewed_head", self.reviewed_head),
            (3, "validated_head", self.validated_head),
        )
        for minimum_phase, field_name, value in required_fields:
            if phase_index >= minimum_phase and value is None:
                raise ValueError(f"{field_name} is required for {self.phase.value}")
            if phase_index < minimum_phase and value is not None:
                raise ValueError(f"{field_name} belongs to a later phase")
        if phase_index < 3 and self.resulting_graph_markdown is not None:
            raise ValueError("resulting graph belongs to validated work")
        if self.worker == "curation":
            if phase_index < 3 and self.report_path is not None:
                raise ValueError("curation report path belongs to validated work")
            if phase_index >= 1 and self.sync is None:
                raise ValueError("curation prepared phase requires sync state")
            if phase_index == 0 and self.sync is not None:
                raise ValueError("curation sync state belongs to prepared phase")
            if self.sync is not None and (
                self.sync.original_head != self.selected_head
                or self.sync.rebased_head != self.prepared_head
                or self.sync.backup_ref != self.backup_ref
            ):
                raise ValueError("curation sync facts do not match work state")
        elif phase_index >= 3 and self.report_path is None:
            raise ValueError("validated discovery work requires report path")
        return self


class ReviewedContinuation(BaseModel):
    """Durable authority for one exact reviewed-but-unpushed curation tree."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN.pattern)
    origin_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    recovery_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    updated_at: datetime
    pr_number: int = Field(ge=1)
    selected_head: str = Field(pattern=_SHA_PATTERN)
    reviewed_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$",
    )
    sync: GuardedSyncResult
    reviewed_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)
    status: ContinuationStatus
    validation_status: ContinuationValidationStatus

    @model_validator(mode="after")
    def validate_reviewed_continuation(self) -> ReviewedContinuation:
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        object.__setattr__(self, "updated_at", self.updated_at.astimezone(UTC))
        if self.work_id != f"curation-pr-{self.pr_number}":
            raise ValueError("continuation identity does not match its PR")
        if self.sync.original_head != self.selected_head:
            raise ValueError("continuation sync does not match selected head")
        reviewed_prefix = f"refs/snowcast-maintainer/reviewed/pr-{self.pr_number}/"
        squash_prefix = f"refs/snowcast-maintainer/continuations/pr-{self.pr_number}/"
        if not self.reviewed_ref.startswith(reviewed_prefix):
            raise ValueError("reviewed ref does not match continuation identity")
        if not self.squash_ref.startswith(squash_prefix):
            raise ValueError("squash ref does not match continuation identity")
        if (
            self.status is ContinuationStatus.VALIDATED
            and self.validation_status is not ContinuationValidationStatus.PASSED
        ):
            raise ValueError("validated continuation requires passed validation")
        if (
            self.validation_status is ContinuationValidationStatus.PASSED
            and self.status
            not in {
                ContinuationStatus.VALIDATED,
                ContinuationStatus.CONSUMED,
                ContinuationStatus.INVALIDATED,
            }
        ):
            raise ValueError("passed validation requires a terminal-ready status")
        return self


class RemediationContinuation(BaseModel):
    """Durable authority for one exact remediation checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN.pattern)
    origin_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    recovery_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    updated_at: datetime
    pr_number: int = Field(ge=1)
    selected_head: str = Field(pattern=_SHA_PATTERN)
    remediation_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$",
    )
    sync: GuardedSyncResult
    allowed_paths: frozenset[str] = Field(min_length=1)
    remediation_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)
    completed_stage: Literal["delta-validated"]
    status: RemediationContinuationStatus

    @model_validator(mode="after")
    def validate_remediation_continuation(self) -> RemediationContinuation:
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        object.__setattr__(self, "updated_at", self.updated_at.astimezone(UTC))
        if self.work_id != f"curation-pr-{self.pr_number}":
            raise ValueError("remediation identity does not match its PR")
        if self.sync.original_head != self.selected_head:
            raise ValueError("remediation sync does not match selected head")
        if not all(is_allowed_curation_path(path) for path in self.allowed_paths):
            raise ValueError("remediation paths are outside curation scope")
        remediation_prefix = (
            f"refs/snowcast-maintainer/remediation/pr-{self.pr_number}/"
        )
        squash_prefix = (
            f"refs/snowcast-maintainer/remediation-continuations/pr-{self.pr_number}/"
        )
        if not self.remediation_ref.startswith(remediation_prefix):
            raise ValueError("remediation ref does not match continuation identity")
        if not self.squash_ref.startswith(squash_prefix):
            raise ValueError("squash ref does not match continuation identity")
        return self


class PushJournal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN.pattern)
    worker: Literal["curation", "discovery"]
    origin_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    recovery_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    pr_number: int | None = Field(default=None, ge=1)
    branch: str = Field(min_length=1, max_length=200)
    expected_remote_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    new_head: str = Field(pattern=_SHA_PATTERN)
    candidate_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_ID_PATTERN.pattern,
    )
    candidate_origin: Literal["backlog", "external"] | None = None
    report_path: str | None = Field(
        default=None,
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$",
    )
    resulting_graph_markdown: str | None = Field(
        default=None,
        min_length=1,
        max_length=32768,
    )
    phase: PushPhase

    @model_validator(mode="after")
    def validate_push_journal(self) -> PushJournal:
        if not is_safe_codex_branch(self.branch):
            raise ValueError("branch must be a safe codex ref")
        if self.worker == "curation":
            if self.pr_number is None:
                raise ValueError("curation push requires a PR number")
            if self.expected_remote_head is None:
                raise ValueError("curation push requires an expected remote head")
            if self.candidate_key is not None or self.candidate_origin is not None:
                raise ValueError("curation push cannot include candidate identity")
            if self.phase is PushPhase.PR_CREATED:
                raise ValueError("curation does not create a PR")
        else:
            if self.candidate_key is None or self.candidate_origin is None:
                raise ValueError("discovery push requires candidate identity")
            if self.expected_remote_head is not None:
                raise ValueError("discovery publication must be create-only")
            if self.phase in {PushPhase.AUTHORIZED, PushPhase.PUSHED}:
                if self.pr_number is not None:
                    raise ValueError("discovery PR is unknown before creation")
            elif self.pr_number is None:
                raise ValueError("created discovery proposal requires a PR number")
        return self


class RunOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    worker: Literal["curation", "discovery"]
    lease_run_id: str | None = Field(default=None, pattern=_RUN_ID_PATTERN.pattern)
    work_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_ID_PATTERN.pattern,
    )
    pr_number: int | None = Field(default=None, ge=1)
    candidate_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_ID_PATTERN.pattern,
    )
    last_phase: WorkPhase | None = None
    mutation_occurred: bool
    terminal_reason: str = Field(
        min_length=1,
        max_length=64,
        pattern=_REASON_PATTERN,
    )

    @model_validator(mode="after")
    def validate_outcome(self) -> RunOutcome:
        if self.lease_run_id is None:
            if self.mutation_occurred:
                raise ValueError("mutation requires a lease run ID")
            if any(
                value is not None
                for value in (
                    self.work_id,
                    self.pr_number,
                    self.candidate_key,
                    self.last_phase,
                )
            ):
                raise ValueError("pre-lease outcome cannot claim work identity")
        return self


_StateModel = TypeVar(
    "_StateModel",
    WorkState,
    PushJournal,
    ReviewedContinuation,
    RemediationContinuation,
)


@dataclass(frozen=True, slots=True)
class StateStore:
    state_dir: Path
    _read_only: bool = False

    def __post_init__(self) -> None:
        state_dir = Path(self.state_dir)
        object.__setattr__(self, "state_dir", state_dir)
        if self._read_only:
            _validate_private_directory_read_only(state_dir)
        else:
            _ensure_private_directory(state_dir, parents=True)

    @classmethod
    def list_unresolved_for_inspection(
        cls,
        state_dir: str | Path,
    ) -> tuple[PushJournal, ...]:
        state_path = Path(state_dir)
        try:
            state_path.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("maintainer state directory is unsafe") from exc
        return cls(state_path, _read_only=True).list_unresolved_pushes()

    @classmethod
    def list_continuations_for_inspection_path(
        cls,
        state_dir: str | Path,
    ) -> tuple[ReviewedContinuation, ...]:
        state_path = Path(state_dir)
        try:
            state_path.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("maintainer state directory is unsafe") from exc
        return cls(state_path, _read_only=True).list_continuations_for_inspection()

    @classmethod
    def list_remediation_continuations_for_inspection_path(
        cls,
        state_dir: str | Path,
    ) -> tuple[RemediationContinuation, ...]:
        state_path = Path(state_dir)
        try:
            state_path.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("maintainer state directory is unsafe") from exc
        return cls(
            state_path,
            _read_only=True,
        ).list_remediation_continuations_for_inspection()

    @property
    def work_dir(self) -> Path:
        return self.state_dir / "work"

    @property
    def push_dir(self) -> Path:
        return self.state_dir / "push"

    @property
    def continuation_dir(self) -> Path:
        return self.state_dir / "continuations"

    @property
    def remediation_continuation_dir(self) -> Path:
        return self.state_dir / "remediation-continuations"

    def load_work(self, work_id: str) -> WorkState | None:
        _validate_identifier(work_id, "work_id")
        loaded = self._load_model(self.work_dir, work_id, WorkState)
        if loaded is not None and loaded.work_id != work_id:
            raise StateStoreError("work state identity does not match its path")
        return loaded

    def begin_work(self, state: WorkState, lease: RunLease) -> None:
        state = _revalidate_model(state, WorkState)
        if state.phase is not WorkPhase.SELECTED:
            raise StateStoreError("new work must begin in the selected phase")
        with _transition_mutex(self.state_dir):
            self._assert_work_lease(state, lease)
            unresolved = self._list_unresolved_pushes()
            if unresolved:
                raise StateStoreError("unresolved push journal blocks fresh work")
            existing = self.load_work(state.work_id)
            if existing is not None:
                if existing.worker != state.worker:
                    raise StateStoreError("work ID is bound to another worker")
                if existing.run_id == state.run_id:
                    raise StateStoreError("work is already active for this run")
                if existing.phase is WorkPhase.PUSHED:
                    self._require_terminal_restart_journal(existing)
                if state.updated_at <= existing.updated_at:
                    raise StateStoreError("updated_at must increase across restart")
            self._save_model(self.work_dir, state.work_id, state)

    def save_work(self, state: WorkState, lease: RunLease) -> None:
        state = _revalidate_model(state, WorkState)
        with _transition_mutex(self.state_dir):
            self._assert_work_lease(state, lease)
            existing = self.load_work(state.work_id)
            if existing is None:
                raise StateStoreError("work must be begun before it can advance")
            if existing.worker != state.worker or existing.run_id != state.run_id:
                raise LeaseOwnershipError("work state is owned by another run")
            self._validate_work_identity(existing, state)
            expected_index = _WORK_PHASES.index(existing.phase) + 1
            if expected_index >= len(_WORK_PHASES):
                raise StateStoreError("published work is already terminal")
            if state.phase is not _WORK_PHASES[expected_index]:
                raise StateStoreError("work phase must advance exactly once")
            if state.updated_at <= existing.updated_at:
                raise StateStoreError("updated_at must increase on phase transition")
            if state.phase in {WorkPhase.PUSHED, WorkPhase.PUBLISHED}:
                self._require_push_journal(state)
            self._save_model(self.work_dir, state.work_id, state)

    def load_push(self, work_id: str) -> PushJournal | None:
        _validate_identifier(work_id, "work_id")
        loaded = self._load_model(self.push_dir, work_id, PushJournal)
        if loaded is not None and loaded.work_id != work_id:
            raise StateStoreError("push journal identity does not match its path")
        return loaded

    def load_continuation(self, work_id: str) -> ReviewedContinuation | None:
        _validate_identifier(work_id, "work_id")
        loaded = self._load_model(
            self.continuation_dir,
            work_id,
            ReviewedContinuation,
        )
        if loaded is not None and loaded.work_id != work_id:
            raise StateStoreError("continuation identity does not match its path")
        return loaded

    def load_remediation_continuation(
        self,
        work_id: str,
    ) -> RemediationContinuation | None:
        _validate_identifier(work_id, "work_id")
        loaded = self._load_model(
            self.remediation_continuation_dir,
            work_id,
            RemediationContinuation,
        )
        if loaded is not None and loaded.work_id != work_id:
            raise StateStoreError("remediation identity does not match its path")
        return loaded

    def save_remediation_continuation(
        self,
        remediation: RemediationContinuation,
        lease: RunLease,
    ) -> None:
        remediation = _revalidate_model(remediation, RemediationContinuation)
        with _transition_mutex(self.state_dir):
            self._assert_remediation_lease(remediation, lease)
            existing = self.load_remediation_continuation(remediation.work_id)
            if existing is None:
                if remediation.status is not RemediationContinuationStatus.AVAILABLE:
                    raise StateStoreError("new remediation must start available")
                if remediation.origin_run_id != remediation.recovery_run_id:
                    raise StateStoreError("new remediation must originate in this run")
            elif (
                existing.status
                in {
                    RemediationContinuationStatus.CONSUMED,
                    RemediationContinuationStatus.INVALIDATED,
                }
                and remediation.status is RemediationContinuationStatus.AVAILABLE
                and remediation.origin_run_id == remediation.recovery_run_id
                and remediation.origin_run_id == lease.run_id
                and existing.recovery_run_id != lease.run_id
                and remediation.selected_head != existing.selected_head
                and remediation.updated_at > existing.updated_at
            ):
                pass
            elif existing.selected_head == remediation.selected_head:
                raise StateStoreError("same-head remediation cannot reopen")
            else:
                raise StateStoreError("remediation continuation already exists")
            self._save_model(
                self.remediation_continuation_dir,
                remediation.work_id,
                remediation,
            )

    def list_remediation_continuations_for_inspection(
        self,
    ) -> tuple[RemediationContinuation, ...]:
        try:
            self.remediation_continuation_dir.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("remediation directory is unsafe") from exc
        try:
            self._validate_existing_directory(self.state_dir)
            self._validate_existing_directory(self.remediation_continuation_dir)
        except RunLeaseError as exc:
            raise StateStoreError("remediation directory is unsafe") from exc
        active = []
        for path in sorted(
            self.remediation_continuation_dir.glob("*.json"),
            key=lambda item: item.name,
        ):
            remediation = self.load_remediation_continuation(
                path.name.removesuffix(".json")
            )
            if remediation is None:
                raise StateStoreError("remediation disappeared during inventory")
            if remediation.status not in {
                RemediationContinuationStatus.CONSUMED,
                RemediationContinuationStatus.INVALIDATED,
            }:
                active.append(remediation)
        return tuple(sorted(active, key=lambda item: item.work_id))

    def adopt_remediation_continuation(
        self,
        work_id: str,
        lease: RunLease,
    ) -> RemediationContinuation:
        _validate_identifier(work_id, "work_id")
        self._assert_lease_location(lease)
        with _transition_mutex(self.state_dir):
            RunLease.load_owner(self.state_dir, lease.worker, lease.run_id)
            if lease.worker != "curation":
                raise StateStoreError("only curation can adopt remediation")
            if self._list_unresolved_pushes():
                raise StateStoreError("unresolved push journal blocks remediation")
            remediation = self.load_remediation_continuation(work_id)
            if remediation is None:
                raise StateStoreError("remediation continuation is missing")
            if remediation.status not in {
                RemediationContinuationStatus.AVAILABLE,
                RemediationContinuationStatus.RESOLVING,
            }:
                raise StateStoreError("remediation continuation is not available")
            if remediation.recovery_run_id == lease.run_id:
                raise StateStoreError("remediation adoption requires a successor run")
            updated_at = _later_than(remediation.updated_at)
            adopted = remediation.model_copy(
                update={
                    "recovery_run_id": lease.run_id,
                    "updated_at": updated_at,
                    "status": RemediationContinuationStatus.AVAILABLE,
                }
            )
            self._save_model(self.remediation_continuation_dir, work_id, adopted)
            return adopted

    def replace_remediation_continuation(
        self,
        remediation: RemediationContinuation,
        lease: RunLease,
    ) -> None:
        remediation = _revalidate_model(remediation, RemediationContinuation)
        with _transition_mutex(self.state_dir):
            self._assert_remediation_lease(remediation, lease)
            existing = self.load_remediation_continuation(remediation.work_id)
            if existing is None:
                raise StateStoreError("remediation continuation is missing")
            if (
                existing.status
                not in {
                    RemediationContinuationStatus.AVAILABLE,
                    RemediationContinuationStatus.RESOLVING,
                }
                or existing.recovery_run_id != lease.run_id
            ):
                raise StateStoreError("only the active owner can replace remediation")
            if (
                remediation.work_id != existing.work_id
                or remediation.pr_number != existing.pr_number
                or remediation.selected_head != existing.selected_head
                or remediation.origin_run_id != existing.origin_run_id
                or remediation.recovery_run_id != existing.recovery_run_id
                or remediation.updated_at <= existing.updated_at
            ):
                raise StateStoreError("replacement remediation facts are invalid")
            if existing.status is RemediationContinuationStatus.AVAILABLE:
                if remediation.status not in {
                    RemediationContinuationStatus.AVAILABLE,
                    RemediationContinuationStatus.RESOLVING,
                }:
                    raise StateStoreError(
                        "available remediation has invalid replacement"
                    )
            elif remediation.status is not RemediationContinuationStatus.AVAILABLE:
                raise StateStoreError("resolving remediation must return available")
            self._save_model(
                self.remediation_continuation_dir,
                remediation.work_id,
                remediation,
            )

    def invalidate_remediation_continuation(
        self,
        work_id: str,
        lease: RunLease,
    ) -> RemediationContinuation:
        _validate_identifier(work_id, "work_id")
        self._assert_lease_location(lease)
        with _transition_mutex(self.state_dir):
            RunLease.load_owner(self.state_dir, lease.worker, lease.run_id)
            remediation = self.load_remediation_continuation(work_id)
            if remediation is None:
                raise StateStoreError("remediation continuation is missing")
            self._assert_remediation_lease(remediation, lease)
            if remediation.status in {
                RemediationContinuationStatus.CONSUMED,
                RemediationContinuationStatus.INVALIDATED,
            }:
                raise StateStoreError("remediation continuation is terminal")
            invalidated = remediation.model_copy(
                update={
                    "updated_at": _later_than(remediation.updated_at),
                    "status": RemediationContinuationStatus.INVALIDATED,
                }
            )
            self._save_model(self.remediation_continuation_dir, work_id, invalidated)
            return invalidated

    def promote_remediation_to_reviewed(
        self,
        remediation: RemediationContinuation,
        reviewed: ReviewedContinuation,
        lease: RunLease,
    ) -> None:
        remediation = _revalidate_model(remediation, RemediationContinuation)
        reviewed = _revalidate_model(reviewed, ReviewedContinuation)
        with _transition_mutex(self.state_dir):
            self._assert_remediation_lease(remediation, lease)
            self._assert_continuation_lease(reviewed, lease)
            current = self.load_remediation_continuation(remediation.work_id)
            if current is None:
                raise StateStoreError("remediation continuation is missing")
            if current != remediation:
                raise LeaseOwnershipError("remediation continuation ownership changed")
            if current.status in {
                RemediationContinuationStatus.CONSUMED,
                RemediationContinuationStatus.INVALIDATED,
            }:
                raise StateStoreError("remediation continuation is terminal")
            if not _reviewed_matches_remediation_authority(reviewed, remediation):
                raise StateStoreError("reviewed continuation authority does not match")
            existing_reviewed = self.load_continuation(reviewed.work_id)
            if existing_reviewed is None:
                self._save_model(self.continuation_dir, reviewed.work_id, reviewed)
            elif not _reviewed_continuations_are_equivalent(
                existing_reviewed,
                reviewed,
            ):
                raise StateStoreError(
                    "reviewed continuation conflicts with remediation"
                )
            consumed = remediation.model_copy(
                update={
                    "updated_at": _later_than(remediation.updated_at),
                    "status": RemediationContinuationStatus.CONSUMED,
                }
            )
            self._save_model(
                self.remediation_continuation_dir,
                remediation.work_id,
                consumed,
            )

    def save_continuation(
        self,
        continuation: ReviewedContinuation,
        lease: RunLease,
    ) -> None:
        continuation = _revalidate_model(continuation, ReviewedContinuation)
        with _transition_mutex(self.state_dir):
            self._assert_continuation_lease(continuation, lease)
            existing = self.load_continuation(continuation.work_id)
            if existing is None:
                if continuation.status is not ContinuationStatus.AVAILABLE:
                    raise StateStoreError(
                        "new continuation must start in the available state"
                    )
                if continuation.origin_run_id != continuation.recovery_run_id:
                    raise StateStoreError("new continuation must originate in this run")
            elif (
                existing.status
                in {ContinuationStatus.CONSUMED, ContinuationStatus.INVALIDATED}
                and continuation.status is ContinuationStatus.AVAILABLE
                and continuation.origin_run_id == continuation.recovery_run_id
                and continuation.selected_head != existing.selected_head
                and continuation.updated_at > existing.updated_at
            ):
                pass
            else:
                self._validate_continuation_transition(existing, continuation)
            self._save_model(
                self.continuation_dir,
                continuation.work_id,
                continuation,
            )

    def save_adopted_continuation(
        self,
        continuation: ReviewedContinuation,
        lease: RunLease,
    ) -> None:
        """Create a continuation from exact legacy reviewed work."""
        continuation = _revalidate_model(continuation, ReviewedContinuation)
        with _transition_mutex(self.state_dir):
            self._assert_continuation_lease(continuation, lease)
            if continuation.origin_run_id == continuation.recovery_run_id:
                raise StateStoreError("legacy adoption requires a successor run")
            if self.load_continuation(continuation.work_id) is not None:
                raise StateStoreError("reviewed continuation already exists")
            if self._list_unresolved_pushes():
                raise StateStoreError("unresolved push journal blocks continuation")
            self._save_model(
                self.continuation_dir,
                continuation.work_id,
                continuation,
            )

    def replace_resolved_continuation(
        self,
        continuation: ReviewedContinuation,
        lease: RunLease,
    ) -> None:
        """Replace one replaying checkpoint after its mandatory fresh review."""
        continuation = _revalidate_model(continuation, ReviewedContinuation)
        with _transition_mutex(self.state_dir):
            self._assert_continuation_lease(continuation, lease)
            existing = self.load_continuation(continuation.work_id)
            if existing is None:
                raise StateStoreError("reviewed continuation is missing")
            if (
                existing.recovery_run_id != lease.run_id
                or existing.status is not ContinuationStatus.RESOLVING
            ):
                raise StateStoreError("only the resolving owner can replace checkpoint")
            if (
                continuation.work_id != existing.work_id
                or continuation.pr_number != existing.pr_number
                or continuation.selected_head != existing.selected_head
                or continuation.origin_run_id != existing.origin_run_id
                or continuation.recovery_run_id != existing.recovery_run_id
                or continuation.status is not ContinuationStatus.AVAILABLE
                or continuation.validation_status
                is not ContinuationValidationStatus.NOT_RUN
                or continuation.updated_at <= existing.updated_at
            ):
                raise StateStoreError("replacement continuation facts are invalid")
            self._save_model(
                self.continuation_dir,
                continuation.work_id,
                continuation,
            )

    def list_continuations_for_inspection(
        self,
    ) -> tuple[ReviewedContinuation, ...]:
        try:
            self.continuation_dir.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("continuation directory is unsafe") from exc
        try:
            self._validate_existing_directory(self.state_dir)
            self._validate_existing_directory(self.continuation_dir)
        except RunLeaseError as exc:
            raise StateStoreError("continuation directory is unsafe") from exc
        active = []
        for path in sorted(
            self.continuation_dir.glob("*.json"),
            key=lambda item: item.name,
        ):
            work_id = path.name.removesuffix(".json")
            continuation = self.load_continuation(work_id)
            if continuation is None:
                raise StateStoreError("continuation disappeared during inventory")
            if continuation.status not in {
                ContinuationStatus.CONSUMED,
                ContinuationStatus.INVALIDATED,
            }:
                active.append(continuation)
        return tuple(sorted(active, key=lambda item: item.work_id))

    def adopt_continuation(
        self,
        work_id: str,
        lease: RunLease,
    ) -> ReviewedContinuation:
        _validate_identifier(work_id, "work_id")
        self._assert_lease_location(lease)
        with _transition_mutex(self.state_dir):
            RunLease.load_owner(self.state_dir, lease.worker, lease.run_id)
            if lease.worker != "curation":
                raise StateStoreError("only curation can adopt continuations")
            if self._list_unresolved_pushes():
                raise StateStoreError("unresolved push journal blocks continuation")
            continuation = self.load_continuation(work_id)
            if continuation is None:
                raise StateStoreError("reviewed continuation is missing")
            if continuation.status in {
                ContinuationStatus.CONSUMED,
                ContinuationStatus.INVALIDATED,
            }:
                raise StateStoreError("reviewed continuation is terminal")
            if continuation.recovery_run_id == lease.run_id:
                raise StateStoreError("continuation adoption requires a successor run")
            updated_at = datetime.now(UTC)
            if updated_at <= continuation.updated_at:
                updated_at = continuation.updated_at + timedelta(microseconds=1)
            adopted = continuation.model_copy(
                update={
                    "recovery_run_id": lease.run_id,
                    "updated_at": updated_at,
                }
            )
            self._save_model(self.continuation_dir, work_id, adopted)
            return adopted

    @contextmanager
    def guard_push_mutation(
        self,
        journal: PushJournal,
        lease: RunLease,
    ) -> Iterator[None]:
        """Hold ownership stable across one irreversible external mutation."""
        journal = _revalidate_model(journal, PushJournal)
        with _transition_mutex(self.state_dir):
            current = self.load_push(journal.work_id)
            if current is None:
                raise StateStoreError("push journal is missing")
            self._assert_push_lease(current, lease)
            if current != journal:
                raise LeaseOwnershipError("push journal ownership changed")
            yield

    def save_push(self, journal: PushJournal, lease: RunLease) -> None:
        journal = _revalidate_model(journal, PushJournal)
        with _transition_mutex(self.state_dir):
            self._assert_push_lease(journal, lease)
            existing = self.load_push(journal.work_id)
            if existing is None:
                if journal.phase is not PushPhase.AUTHORIZED:
                    raise StateStoreError("new push journal must start authorized")
                if journal.origin_run_id != journal.recovery_run_id:
                    raise StateStoreError("new push journal must originate in this run")
            elif (
                existing.phase is PushPhase.PUBLISHED
                and journal.phase is PushPhase.AUTHORIZED
                and journal.origin_run_id == journal.recovery_run_id
            ):
                pass
            else:
                self._validate_push_transition(existing, journal)
            self._save_model(self.push_dir, journal.work_id, journal)

    def list_unresolved_pushes(self) -> tuple[PushJournal, ...]:
        return self._list_unresolved_pushes()

    def adopt_push(
        self,
        work_id: str,
        lease: RunLease,
        observed_remote_head: str | None,
    ) -> PushJournal:
        _validate_identifier(work_id, "work_id")
        if (
            observed_remote_head is not None
            and re.fullmatch(
                _SHA_PATTERN,
                observed_remote_head,
            )
            is None
        ):
            raise StateStoreError("observed remote head is invalid")
        self._assert_lease_location(lease)
        with _transition_mutex(self.state_dir):
            RunLease.load_owner(
                self.state_dir,
                lease.worker,
                lease.run_id,
            )
            unresolved = self._list_unresolved_pushes()
            if len(unresolved) != 1:
                raise StateStoreError(
                    "push adoption requires exactly one unresolved journal"
                )
            journal = unresolved[0]
            if journal.work_id != work_id:
                raise StateStoreError("unresolved push belongs to another work item")
            if journal.worker != lease.worker:
                raise StateStoreError("unresolved push belongs to another worker")
            if journal.recovery_run_id == lease.run_id:
                raise StateStoreError("push adoption requires a successor run")
            if observed_remote_head not in {
                journal.expected_remote_head,
                journal.new_head,
            }:
                raise StateStoreError("observed remote head is not recoverable")
            adopted = journal.model_copy(
                update={"recovery_run_id": lease.run_id},
            )
            self._save_model(self.push_dir, adopted.work_id, adopted)
            return adopted

    def _assert_work_lease(
        self,
        state: WorkState,
        lease: RunLease,
    ) -> None:
        self._assert_lease_location(lease)
        if state.worker != lease.worker or state.run_id != lease.run_id:
            raise LeaseOwnershipError("work state is not owned by this lease")
        RunLease.load_owner(
            self.state_dir,
            state.worker,
            state.run_id,
        )

    def _assert_push_lease(
        self,
        journal: PushJournal,
        lease: RunLease,
    ) -> None:
        self._assert_lease_location(lease)
        if journal.worker != lease.worker or journal.recovery_run_id != lease.run_id:
            raise LeaseOwnershipError("push journal is not owned by this lease")
        RunLease.load_owner(
            self.state_dir,
            journal.worker,
            journal.recovery_run_id,
        )

    def _assert_continuation_lease(
        self,
        continuation: ReviewedContinuation,
        lease: RunLease,
    ) -> None:
        self._assert_lease_location(lease)
        if lease.worker != "curation" or continuation.recovery_run_id != lease.run_id:
            raise LeaseOwnershipError("continuation is not owned by this lease")
        RunLease.load_owner(self.state_dir, lease.worker, lease.run_id)

    def _assert_remediation_lease(
        self,
        remediation: RemediationContinuation,
        lease: RunLease,
    ) -> None:
        self._assert_lease_location(lease)
        if lease.worker != "curation" or remediation.recovery_run_id != lease.run_id:
            raise LeaseOwnershipError("remediation is not owned by this lease")
        RunLease.load_owner(self.state_dir, lease.worker, lease.run_id)

    def _assert_lease_location(self, lease: RunLease) -> None:
        if lease.state_dir.absolute() != self.state_dir.absolute():
            raise LeaseOwnershipError("lease belongs to another state directory")

    def _validate_push_transition(
        self,
        existing: PushJournal,
        journal: PushJournal,
    ) -> None:
        immutable_fields = (
            "work_id",
            "worker",
            "origin_run_id",
            "recovery_run_id",
            "branch",
            "expected_remote_head",
            "new_head",
            "candidate_key",
            "candidate_origin",
            "report_path",
            "resulting_graph_markdown",
        )
        if any(
            getattr(existing, field_name) != getattr(journal, field_name)
            for field_name in immutable_fields
        ):
            raise StateStoreError("push journal immutable facts changed")
        if existing.pr_number is not None and journal.pr_number != existing.pr_number:
            raise StateStoreError("push journal PR number changed")
        if existing.worker == "discovery":
            allowed = {
                PushPhase.AUTHORIZED: PushPhase.PUSHED,
                PushPhase.PUSHED: PushPhase.PR_CREATED,
                PushPhase.PR_CREATED: PushPhase.PUBLISHED,
            }
        else:
            allowed = {
                PushPhase.AUTHORIZED: PushPhase.PUSHED,
                PushPhase.PUSHED: PushPhase.PUBLISHED,
            }
        if allowed.get(existing.phase) is not journal.phase:
            raise StateStoreError("push journal phase transition is invalid")

    def _validate_work_identity(
        self,
        existing: WorkState,
        state: WorkState,
    ) -> None:
        if (
            existing.work_id != state.work_id
            or existing.selected_head != state.selected_head
            or existing.candidate_key != state.candidate_key
        ):
            raise StateStoreError("work identity changed across phase transition")
        if existing.pr_number is not None and state.pr_number != existing.pr_number:
            raise StateStoreError("work identity changed across phase transition")
        for field_name in (
            "prepared_head",
            "reviewed_head",
            "validated_head",
            "backup_ref",
            "candidate_origin",
            "report_path",
            "resulting_graph_markdown",
            "sync",
        ):
            existing_value = getattr(existing, field_name)
            if (
                existing_value is not None
                and getattr(state, field_name) != existing_value
            ):
                raise StateStoreError("work identity changed across phase transition")

    def _validate_continuation_transition(
        self,
        existing: ReviewedContinuation,
        continuation: ReviewedContinuation,
    ) -> None:
        immutable_fields = (
            "work_id",
            "origin_run_id",
            "recovery_run_id",
            "pr_number",
            "selected_head",
            "reviewed_head",
            "report_path",
            "sync",
            "reviewed_ref",
            "squash_ref",
        )
        if any(
            getattr(existing, field_name) != getattr(continuation, field_name)
            for field_name in immutable_fields
        ):
            raise StateStoreError("continuation immutable facts changed")
        if continuation.updated_at <= existing.updated_at:
            raise StateStoreError("updated_at must increase on continuation transition")
        allowed_statuses = {
            ContinuationStatus.AVAILABLE: {
                ContinuationStatus.AVAILABLE,
                ContinuationStatus.RESOLVING,
                ContinuationStatus.VALIDATED,
                ContinuationStatus.CONSUMED,
                ContinuationStatus.INVALIDATED,
            },
            ContinuationStatus.RESOLVING: {
                ContinuationStatus.RESOLVING,
                ContinuationStatus.AVAILABLE,
                ContinuationStatus.CONSUMED,
                ContinuationStatus.INVALIDATED,
            },
            ContinuationStatus.VALIDATED: {
                ContinuationStatus.VALIDATED,
                ContinuationStatus.CONSUMED,
                ContinuationStatus.INVALIDATED,
            },
            ContinuationStatus.CONSUMED: set(),
            ContinuationStatus.INVALIDATED: set(),
        }
        if continuation.status not in allowed_statuses[existing.status]:
            raise StateStoreError("continuation status transition is invalid")
        allowed_validation = {
            ContinuationValidationStatus.NOT_RUN: {
                ContinuationValidationStatus.NOT_RUN,
                ContinuationValidationStatus.FAILED,
                ContinuationValidationStatus.PASSED,
            },
            ContinuationValidationStatus.FAILED: {
                ContinuationValidationStatus.FAILED,
                ContinuationValidationStatus.PASSED,
            },
            ContinuationValidationStatus.PASSED: {
                ContinuationValidationStatus.PASSED,
            },
        }
        replay_reset = (
            existing.validation_status is ContinuationValidationStatus.PASSED
            and continuation.status is ContinuationStatus.RESOLVING
            and continuation.validation_status is ContinuationValidationStatus.NOT_RUN
        )
        if not replay_reset and (
            continuation.validation_status
            not in allowed_validation[existing.validation_status]
        ):
            raise StateStoreError("continuation validation transition is invalid")
        if (
            continuation.status is ContinuationStatus.VALIDATED
            and continuation.validation_status
            is not ContinuationValidationStatus.PASSED
        ):
            raise StateStoreError("continuation transition requires passed validation")

    def _require_push_journal(self, state: WorkState) -> None:
        journal = self.load_push(state.work_id)
        if journal is None:
            raise StateStoreError("matching push journal is required")
        if (
            journal.work_id != state.work_id
            or journal.worker != state.worker
            or journal.recovery_run_id != state.run_id
            or journal.new_head != state.validated_head
        ):
            raise StateStoreError("push journal does not match current work")
        if state.phase is WorkPhase.PUBLISHED:
            if journal.phase is not PushPhase.PUBLISHED:
                raise StateStoreError("published push journal is required")
        elif journal.phase is PushPhase.AUTHORIZED:
            raise StateStoreError("push journal has not reached pushed phase")

    def _require_terminal_restart_journal(self, state: WorkState) -> None:
        journal = self.load_push(state.work_id)
        if journal is None:
            raise StateStoreError("pushed work without its journal is inconsistent")
        if (
            journal.phase is not PushPhase.PUBLISHED
            or journal.work_id != state.work_id
            or journal.worker != state.worker
            or journal.new_head != state.validated_head
        ):
            raise StateStoreError(
                "pushed work requires a matching published journal to restart"
            )

    def _list_unresolved_pushes(self) -> tuple[PushJournal, ...]:
        try:
            self.push_dir.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("push journal directory is unsafe") from exc
        try:
            self._validate_existing_directory(self.state_dir)
            self._validate_existing_directory(self.push_dir)
        except RunLeaseError as exc:
            raise StateStoreError("push journal directory is unsafe") from exc
        journals = []
        for path in sorted(self.push_dir.glob("*.json"), key=lambda item: item.name):
            work_id = path.name.removesuffix(".json")
            journal = self.load_push(work_id)
            if journal is None:
                raise StateStoreError("push journal disappeared during inventory")
            if journal.phase is not PushPhase.PUBLISHED:
                journals.append(journal)
        return tuple(sorted(journals, key=lambda item: item.work_id))

    def _load_model(
        self,
        directory: Path,
        work_id: str,
        model_type: type[_StateModel],
    ) -> _StateModel | None:
        path = directory / f"{work_id}.json"
        try:
            directory.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StateStoreError("maintainer state directory is unsafe") from exc
        try:
            self._validate_existing_directory(self.state_dir)
            self._validate_existing_directory(directory)
            raw = _read_private_json(path, max_bytes=_MAX_STATE_BYTES)
        except FileNotFoundError:
            return None
        except (LeaseMetadataError, RunLeaseError) as exc:
            raise StateStoreError("maintainer state file is unsafe or invalid") from exc
        try:
            return model_type.model_validate_json(json.dumps(raw))
        except (TypeError, ValidationError) as exc:
            raise StateStoreError("maintainer state schema is invalid") from exc

    def _save_model(
        self,
        directory: Path,
        work_id: str,
        model: WorkState | PushJournal | ReviewedContinuation | RemediationContinuation,
    ) -> None:
        _ensure_private_directory(directory, parents=False)
        _write_json_atomic(
            directory / f"{work_id}.json",
            model.model_dump(mode="json"),
        )

    def _validate_existing_directory(self, path: Path) -> None:
        if self._read_only:
            _validate_private_directory_read_only(path)
        else:
            _ensure_private_directory(path, parents=False, create=False)


def _validate_private_directory_read_only(path: Path) -> None:
    flags = os.O_RDONLY
    for flag_name in ("O_DIRECTORY", "O_CLOEXEC", "O_NOFOLLOW"):
        if not hasattr(os, flag_name):
            raise StateStoreError("maintainer state directory is unsafe")
        flags |= getattr(os, flag_name)
    try:
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o700
            ):
                raise StateStoreError("maintainer state directory is unsafe")
        finally:
            os.close(descriptor)
    except StateStoreError:
        raise
    except OSError:
        raise StateStoreError("maintainer state directory is unsafe") from None


def _validate_identifier(value: str, field_name: str) -> None:
    if _ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a bounded safe identifier")


def _revalidate_model(
    model: _StateModel,
    model_type: type[_StateModel],
) -> _StateModel:
    if type(model) is not model_type:
        raise TypeError(f"state must be a {model_type.__name__} instance")
    return model_type.model_validate(model.model_dump())


def _later_than(timestamp: datetime) -> datetime:
    observed_at = datetime.now(UTC)
    if observed_at <= timestamp:
        return timestamp + timedelta(microseconds=1)
    return observed_at


def _reviewed_matches_remediation_authority(
    reviewed: ReviewedContinuation,
    remediation: RemediationContinuation,
) -> bool:
    return (
        reviewed.work_id == remediation.work_id
        and reviewed.pr_number == remediation.pr_number
        and reviewed.origin_run_id == remediation.origin_run_id
        and reviewed.selected_head == remediation.selected_head
        and reviewed.sync == remediation.sync
        and reviewed.report_path == remediation.report_path
        and reviewed.reviewed_head == remediation.remediation_head
    )


def _reviewed_continuations_are_equivalent(
    existing: ReviewedContinuation,
    requested: ReviewedContinuation,
) -> bool:
    return all(
        getattr(existing, field_name) == getattr(requested, field_name)
        for field_name in (
            "work_id",
            "pr_number",
            "origin_run_id",
            "selected_head",
            "reviewed_head",
            "report_path",
            "sync",
            "reviewed_ref",
            "squash_ref",
            "status",
            "validation_status",
        )
    )

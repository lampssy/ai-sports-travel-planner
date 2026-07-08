from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.runtime import (
    LeaseMetadataError,
    LeaseOwnershipError,
    RunLeaseError,
    SimpleRunLease,
    _ensure_private_directory,
    _read_private_json,
    _transition_mutex,
    _write_json_atomic,
)

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_REF_PATTERN = r"^refs/[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$"
_ORIGIN_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"
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
    selected_head: str = Field(pattern=_SHA_PATTERN)
    prepared_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    reviewed_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    validated_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    backup_ref: str | None = Field(default=None, pattern=_REF_PATTERN)

    @model_validator(mode="after")
    def validate_work_state(self) -> WorkState:
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        object.__setattr__(self, "updated_at", self.updated_at.astimezone(UTC))

        if self.worker == "curation":
            if self.pr_number is None:
                raise ValueError("curation work requires a PR number")
            if self.candidate_key is not None:
                raise ValueError("curation work cannot include a candidate key")
        else:
            if self.candidate_key is None:
                raise ValueError("discovery work requires a candidate key")
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
    candidate_origin: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_ORIGIN_PATTERN,
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


_StateModel = TypeVar("_StateModel", WorkState, PushJournal)


@dataclass(frozen=True, slots=True)
class StateStore:
    state_dir: Path

    def __post_init__(self) -> None:
        state_dir = Path(self.state_dir)
        object.__setattr__(self, "state_dir", state_dir)
        _ensure_private_directory(state_dir, parents=True)

    @property
    def work_dir(self) -> Path:
        return self.state_dir / "work"

    @property
    def push_dir(self) -> Path:
        return self.state_dir / "push"

    def load_work(self, work_id: str) -> WorkState | None:
        _validate_identifier(work_id, "work_id")
        loaded = self._load_model(self.work_dir, work_id, WorkState)
        if loaded is not None and loaded.work_id != work_id:
            raise StateStoreError("work state identity does not match its path")
        return loaded

    def begin_work(self, state: WorkState, lease: SimpleRunLease) -> None:
        state = _revalidate_model(state, WorkState)
        if state.phase is not WorkPhase.SELECTED:
            raise StateStoreError("new work must begin in the selected phase")
        self._assert_work_lease(state, lease)
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
                    if self.load_push(state.work_id) is None:
                        raise StateStoreError(
                            "pushed work without its journal is inconsistent"
                        )
                    raise StateStoreError("pushed work cannot be restarted")
                if state.updated_at <= existing.updated_at:
                    raise StateStoreError("updated_at must increase across restart")
            self._save_model(self.work_dir, state.work_id, state)

    def save_work(self, state: WorkState, lease: SimpleRunLease) -> None:
        state = _revalidate_model(state, WorkState)
        self._assert_work_lease(state, lease)
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

    def save_push(self, journal: PushJournal, lease: SimpleRunLease) -> None:
        journal = _revalidate_model(journal, PushJournal)
        self._assert_push_lease(journal, lease)
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
        lease: SimpleRunLease,
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
            SimpleRunLease.load_owner(
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
        lease: SimpleRunLease,
    ) -> None:
        self._assert_lease_location(lease)
        if state.worker != lease.worker or state.run_id != lease.run_id:
            raise LeaseOwnershipError("work state is not owned by this lease")
        SimpleRunLease.load_owner(
            self.state_dir,
            state.worker,
            state.run_id,
        )

    def _assert_push_lease(
        self,
        journal: PushJournal,
        lease: SimpleRunLease,
    ) -> None:
        self._assert_lease_location(lease)
        if journal.worker != lease.worker or journal.recovery_run_id != lease.run_id:
            raise LeaseOwnershipError("push journal is not owned by this lease")
        SimpleRunLease.load_owner(
            self.state_dir,
            journal.worker,
            journal.recovery_run_id,
        )

    def _assert_lease_location(self, lease: SimpleRunLease) -> None:
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
        ):
            existing_value = getattr(existing, field_name)
            if (
                existing_value is not None
                and getattr(state, field_name) != existing_value
            ):
                raise StateStoreError("work identity changed across phase transition")

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

    def _list_unresolved_pushes(self) -> tuple[PushJournal, ...]:
        try:
            self.push_dir.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise StateStoreError("push journal directory is unsafe") from exc
        try:
            _ensure_private_directory(self.state_dir, parents=False, create=False)
            _ensure_private_directory(self.push_dir, parents=False, create=False)
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
            _ensure_private_directory(self.state_dir, parents=False, create=False)
            _ensure_private_directory(directory, parents=False, create=False)
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
        model: WorkState | PushJournal,
    ) -> None:
        _ensure_private_directory(directory, parents=False)
        _write_json_atomic(
            directory / f"{work_id}.json",
            model.model_dump(mode="json"),
        )


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

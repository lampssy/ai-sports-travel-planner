from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ops.maintainer.git_ops import GuardedSyncResult
from ops.maintainer.runtime import (
    LeaseMetadataError,
    RunLease,
    RunLeaseError,
    _ensure_private_directory,
    _read_private_json,
    _transition_mutex,
    _write_json_atomic,
)

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_GENERATION_ID_PATTERN = r"^[0-9a-f]{32}$"
_TRANSACTION_ID_PATTERN = r"^[0-9a-f]{64}$"
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_REF_PATTERN = r"^refs/[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"
_REPORT_PATTERN = r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
_GENERATION_FILE_PATTERN = re.compile(
    r"^(?P<number>[1-9][0-9]*)-(?P<generation_id>[0-9a-f]{32})\.json$"
)
_MAX_GENERATION_BYTES = 65_536


class CurationStateError(RuntimeError):
    """Raised when generation authority cannot be loaded or advanced safely."""


class CurationCheckpointStage(StrEnum):
    DELTA_VALIDATED = "delta-validated"
    REVIEWED = "reviewed"


class CurationRecipeId(StrEnum):
    CHECKPOINT_DELTA = "checkpoint_curation_delta"
    CHECKPOINT_REVIEWED = "checkpoint_curation_reviewed"
    VALIDATE = "validate_curation"
    PUBLISH_PUSH = "publish_push"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CurationActionSubstitutions(_StrictModel):
    pr: int = Field(ge=1)
    generation_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    head: str = Field(pattern=_SHA_PATTERN)
    report: str | None = Field(default=None, pattern=_REPORT_PATTERN)
    validation_base: str | None = Field(default=None, pattern=_SHA_PATTERN)


class CurationNextAction(_StrictModel):
    recipe_id: CurationRecipeId
    substitutions: CurationActionSubstitutions


class _GenerationEvent(_StrictModel):
    sequence: int = Field(ge=1)
    recorded_at: datetime

    @model_validator(mode="after")
    def normalize_recorded_at(self) -> Self:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("generation event time must include a timezone")
        object.__setattr__(self, "recorded_at", self.recorded_at.astimezone(UTC))
        return self


class GenerationPreparedEvent(_GenerationEvent):
    kind: Literal["generation-prepared"] = "generation-prepared"
    prepared_head: str = Field(pattern=_SHA_PATTERN)


class CheckpointStartedEvent(_GenerationEvent):
    kind: Literal["checkpoint-started"] = "checkpoint-started"
    transaction_id: str = Field(pattern=_TRANSACTION_ID_PATTERN)
    stage: CurationCheckpointStage
    head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)
    validation_base: str = Field(pattern=_SHA_PATTERN)
    expected_checkpoint_ref: str = Field(pattern=_REF_PATTERN)
    expected_squash_ref: str = Field(pattern=_REF_PATTERN)


class CheckpointCompletedEvent(_GenerationEvent):
    kind: Literal["checkpoint-completed"] = "checkpoint-completed"
    transaction_id: str = Field(pattern=_TRANSACTION_ID_PATTERN)
    checkpoint_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)


class ValidationFailedEvent(_GenerationEvent):
    kind: Literal["validation-failed"] = "validation-failed"
    head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)


class ValidationPassedEvent(_GenerationEvent):
    kind: Literal["validation-passed"] = "validation-passed"
    head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)
    resulting_graph_markdown: str = Field(min_length=1, max_length=32_768)


class GenerationClosedEvent(_GenerationEvent):
    kind: Literal[
        "generation-superseded",
        "generation-invalidated",
        "generation-consumed",
    ]
    reason: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")


CurationGenerationEvent = Annotated[
    GenerationPreparedEvent
    | CheckpointStartedEvent
    | CheckpointCompletedEvent
    | ValidationFailedEvent
    | ValidationPassedEvent
    | GenerationClosedEvent,
    Field(discriminator="kind"),
]


class ReviewedCurationAuthority(_StrictModel):
    work_id: str = Field(pattern=_ID_PATTERN.pattern)
    pr_number: int = Field(ge=1)
    generation_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    branch: str = Field(min_length=1, max_length=200)
    selected_head: str = Field(pattern=_SHA_PATTERN)
    base_head: str = Field(pattern=_SHA_PATTERN)
    reviewed_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)
    sync: GuardedSyncResult
    reviewed_at: datetime
    checkpoint_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)


class ValidatedCurationAuthority(ReviewedCurationAuthority):
    validated_head: str = Field(pattern=_SHA_PATTERN)
    resulting_graph_markdown: str = Field(min_length=1, max_length=32_768)
    validated_at: datetime

    @model_validator(mode="after")
    def validate_exact_head(self) -> Self:
        if self.validated_head != self.reviewed_head:
            raise ValueError("validated authority must preserve the reviewed head")
        return self


class CurationGeneration(_StrictModel):
    schema_version: Literal[2]
    work_id: str = Field(pattern=_ID_PATTERN.pattern)
    pr_number: int = Field(ge=1)
    generation_number: int = Field(ge=1)
    generation_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    created_at: datetime
    selected_head: str = Field(pattern=_SHA_PATTERN)
    target_branch: str = Field(min_length=1, max_length=200)
    sync: GuardedSyncResult
    events: tuple[CurationGenerationEvent, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_generation(self) -> Self:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("generation creation time must include a timezone")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
        if self.work_id != f"curation-pr-{self.pr_number}":
            raise ValueError("generation identity does not match its PR")
        if self.sync.original_head != self.selected_head:
            raise ValueError("generation sync does not match selected head")
        if self.sync.target_branch != self.target_branch:
            raise ValueError("generation sync does not match target branch")
        prepared = self.events[0]
        if (
            not isinstance(prepared, GenerationPreparedEvent)
            or prepared.sequence != 1
            or prepared.prepared_head != self.sync.rebased_head
        ):
            raise ValueError("generation must begin with its prepared head")

        expected_sequence = 1
        previous_time = self.created_at
        active_started: CheckpointStartedEvent | None = None
        latest_checkpoint: CheckpointStartedEvent | None = None
        latest_checkpoint_completed = False
        latest_reviewed: CheckpointStartedEvent | None = None
        closed = False
        for event in self.events:
            if event.sequence != expected_sequence:
                raise ValueError("generation event sequence is not contiguous")
            if event.recorded_at < previous_time:
                raise ValueError("generation event time moved backwards")
            if closed:
                raise ValueError("generation contains an event after closure")
            expected_sequence += 1
            previous_time = event.recorded_at

            if isinstance(event, GenerationPreparedEvent):
                if event is not prepared:
                    raise ValueError("generation contains multiple prepared events")
                continue
            if isinstance(event, CheckpointStartedEvent):
                if active_started is not None:
                    raise ValueError(
                        "generation has overlapping checkpoint transactions"
                    )
                expected_id = checkpoint_transaction_id(
                    self.generation_id,
                    event.stage,
                    event.head,
                    event.report_path,
                    event.validation_base,
                )
                if event.transaction_id != expected_id:
                    raise ValueError("checkpoint transaction identity is invalid")
                if event.validation_base != self.sync.base_head:
                    raise ValueError("checkpoint uses the wrong validation base")
                active_started = event
                latest_checkpoint_completed = False
                continue
            if isinstance(event, CheckpointCompletedEvent):
                if active_started is None:
                    raise ValueError("checkpoint completion has no started transaction")
                if (
                    event.transaction_id != active_started.transaction_id
                    or event.checkpoint_ref != active_started.expected_checkpoint_ref
                    or event.squash_ref != active_started.expected_squash_ref
                ):
                    raise ValueError("checkpoint completion does not match its start")
                latest_checkpoint = active_started
                latest_checkpoint_completed = True
                if active_started.stage is CurationCheckpointStage.REVIEWED:
                    latest_reviewed = active_started
                else:
                    latest_reviewed = None
                active_started = None
                continue
            if isinstance(event, (ValidationFailedEvent, ValidationPassedEvent)):
                if (
                    active_started is not None
                    or not latest_checkpoint_completed
                    or latest_checkpoint is None
                    or latest_reviewed is None
                    or latest_reviewed.head != event.head
                    or latest_reviewed.report_path != event.report_path
                ):
                    raise ValueError("validation does not match reviewed authority")
                continue
            if isinstance(event, GenerationClosedEvent):
                if active_started is not None:
                    raise ValueError("generation cannot close during a checkpoint")
                closed = True
        return self


class CurationGenerationProjection(_StrictModel):
    generation_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    generation_number: int = Field(ge=1)
    latest_head: str = Field(pattern=_SHA_PATTERN)
    latest_stage: (
        CurationCheckpointStage
        | Literal[
            "prepared",
            "fully-validated",
            "superseded",
            "invalidated",
            "consumed",
        ]
    )
    incomplete_transaction: str | None = Field(
        default=None,
        pattern=_TRANSACTION_ID_PATTERN,
    )
    reviewed_authority: ReviewedCurationAuthority | None = None
    validated_authority: ValidatedCurationAuthority | None = None
    next_action: CurationNextAction | None = None


def checkpoint_transaction_id(
    generation_id: str,
    stage: CurationCheckpointStage,
    head: str,
    report_path: str,
    validation_base: str,
) -> str:
    payload = "\0".join(
        (generation_id, stage.value, head, report_path, validation_base)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def project_generation(
    generation: CurationGeneration,
) -> CurationGenerationProjection:
    latest_head = generation.sync.rebased_head
    latest_stage: (
        CurationCheckpointStage
        | Literal[
            "prepared",
            "fully-validated",
            "superseded",
            "invalidated",
            "consumed",
        ]
    ) = "prepared"
    incomplete: CheckpointStartedEvent | None = None
    starts: dict[str, CheckpointStartedEvent] = {}
    reviewed: ReviewedCurationAuthority | None = None
    validated: ValidatedCurationAuthority | None = None
    latest_report: str | None = None
    latest_refs: tuple[str, str] | None = None

    for event in generation.events[1:]:
        if isinstance(event, CheckpointStartedEvent):
            starts[event.transaction_id] = event
            incomplete = event
        elif isinstance(event, CheckpointCompletedEvent):
            started = starts[event.transaction_id]
            incomplete = None
            latest_head = started.head
            latest_stage = started.stage
            latest_report = started.report_path
            latest_refs = (event.checkpoint_ref, event.squash_ref)
            validated = None
            if started.stage is CurationCheckpointStage.REVIEWED:
                reviewed = _reviewed_authority(
                    generation,
                    started,
                    event,
                )
            else:
                reviewed = None
        elif isinstance(event, ValidationFailedEvent):
            validated = None
        elif isinstance(event, ValidationPassedEvent):
            if reviewed is None:
                raise CurationStateError("validated generation lost reviewed authority")
            latest_stage = "fully-validated"
            validated = ValidatedCurationAuthority(
                **reviewed.model_dump(),
                validated_head=event.head,
                resulting_graph_markdown=event.resulting_graph_markdown,
                validated_at=event.recorded_at,
            )
        elif isinstance(event, GenerationClosedEvent):
            latest_stage = event.kind.removeprefix("generation-")
            reviewed = None
            validated = None

    next_action: CurationNextAction | None = None
    if incomplete is not None:
        next_action = _checkpoint_action(generation, incomplete)
    elif latest_stage is CurationCheckpointStage.DELTA_VALIDATED:
        assert latest_report is not None
        next_action = CurationNextAction(
            recipe_id=CurationRecipeId.CHECKPOINT_REVIEWED,
            substitutions=CurationActionSubstitutions(
                pr=generation.pr_number,
                generation_id=generation.generation_id,
                head=latest_head,
                report=latest_report,
                validation_base=generation.sync.base_head,
            ),
        )
    elif latest_stage in {"prepared", CurationCheckpointStage.REVIEWED}:
        report = reviewed.report_path if reviewed is not None else None
        recipe = (
            CurationRecipeId.VALIDATE
            if reviewed is not None
            else CurationRecipeId.CHECKPOINT_REVIEWED
        )
        next_action = CurationNextAction(
            recipe_id=recipe,
            substitutions=CurationActionSubstitutions(
                pr=generation.pr_number,
                generation_id=generation.generation_id,
                head=latest_head,
                report=report,
                validation_base=generation.sync.base_head,
            ),
        )
    elif latest_stage == "fully-validated":
        next_action = CurationNextAction(
            recipe_id=CurationRecipeId.PUBLISH_PUSH,
            substitutions=CurationActionSubstitutions(
                pr=generation.pr_number,
                generation_id=generation.generation_id,
                head=latest_head,
                report=(
                    validated.report_path if validated is not None else latest_report
                ),
                validation_base=generation.sync.base_head,
            ),
        )

    if latest_refs is None and latest_stage != "prepared":
        raise CurationStateError("generation projection lost checkpoint refs")
    return CurationGenerationProjection(
        generation_id=generation.generation_id,
        generation_number=generation.generation_number,
        latest_head=latest_head,
        latest_stage=latest_stage,
        incomplete_transaction=(
            incomplete.transaction_id if incomplete is not None else None
        ),
        reviewed_authority=reviewed,
        validated_authority=validated,
        next_action=next_action,
    )


def _reviewed_authority(
    generation: CurationGeneration,
    started: CheckpointStartedEvent,
    completed: CheckpointCompletedEvent,
) -> ReviewedCurationAuthority:
    return ReviewedCurationAuthority(
        work_id=generation.work_id,
        pr_number=generation.pr_number,
        generation_id=generation.generation_id,
        branch=generation.target_branch,
        selected_head=generation.selected_head,
        base_head=generation.sync.base_head,
        reviewed_head=started.head,
        report_path=started.report_path,
        sync=generation.sync,
        reviewed_at=completed.recorded_at,
        checkpoint_ref=completed.checkpoint_ref,
        squash_ref=completed.squash_ref,
    )


def _checkpoint_action(
    generation: CurationGeneration,
    started: CheckpointStartedEvent,
) -> CurationNextAction:
    recipe = (
        CurationRecipeId.CHECKPOINT_REVIEWED
        if started.stage is CurationCheckpointStage.REVIEWED
        else CurationRecipeId.CHECKPOINT_DELTA
    )
    return CurationNextAction(
        recipe_id=recipe,
        substitutions=CurationActionSubstitutions(
            pr=generation.pr_number,
            generation_id=generation.generation_id,
            head=started.head,
            report=started.report_path,
            validation_base=started.validation_base,
        ),
    )


class CurationGenerationStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        _ensure_private_directory(self.state_dir, parents=True)

    @classmethod
    def list_current_for_inspection_path(
        cls,
        state_dir: str | Path,
    ) -> tuple[CurationGeneration, ...]:
        path = Path(state_dir)
        if not path.exists():
            return ()
        store = cls.__new__(cls)
        store.state_dir = path
        return store.list_current_generations()

    @property
    def generation_dir(self) -> Path:
        return self.state_dir / "curation-generations"

    def list_generations(self, work_id: str) -> tuple[CurationGeneration, ...]:
        _validate_id(work_id, "work_id")
        work_dir = self.generation_dir / work_id
        try:
            work_dir.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise CurationStateError("generation directory is unsafe") from exc
        try:
            _ensure_private_directory(self.state_dir, parents=False, create=False)
            _ensure_private_directory(
                self.generation_dir,
                parents=False,
                create=False,
            )
            _ensure_private_directory(work_dir, parents=False, create=False)
        except RunLeaseError as exc:
            raise CurationStateError("generation directory is unsafe") from exc

        generations: list[CurationGeneration] = []
        for path in sorted(work_dir.iterdir(), key=lambda item: item.name):
            match = _GENERATION_FILE_PATTERN.fullmatch(path.name)
            if match is None:
                raise CurationStateError(
                    "generation directory contains an unknown file"
                )
            generation = _load_generation(path)
            if (
                generation.work_id != work_id
                or generation.generation_number != int(match.group("number"))
                or generation.generation_id != match.group("generation_id")
            ):
                raise CurationStateError("generation identity does not match its path")
            generations.append(generation)
        expected_numbers = list(range(1, len(generations) + 1))
        if [item.generation_number for item in generations] != expected_numbers:
            raise CurationStateError("generation numbers are not contiguous")
        return tuple(generations)

    def load_current(self, work_id: str) -> CurationGeneration | None:
        generations = self.list_generations(work_id)
        return generations[-1] if generations else None

    def list_current_generations(self) -> tuple[CurationGeneration, ...]:
        try:
            self.generation_dir.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise CurationStateError("generation root is unsafe") from exc
        try:
            _ensure_private_directory(self.state_dir, parents=False, create=False)
            _ensure_private_directory(
                self.generation_dir,
                parents=False,
                create=False,
            )
        except RunLeaseError as exc:
            raise CurationStateError("generation root is unsafe") from exc

        current: list[CurationGeneration] = []
        work_directories = sorted(
            self.generation_dir.iterdir(),
            key=lambda item: item.name,
        )
        for work_dir in work_directories:
            _validate_id(work_dir.name, "work_id")
            generation = self.load_current(work_dir.name)
            if generation is not None:
                current.append(generation)
        return tuple(current)

    def start_generation(
        self,
        generation: CurationGeneration,
        lease: RunLease,
    ) -> None:
        generation = CurationGeneration.model_validate(generation.model_dump())
        self._assert_lease(lease)
        with _transition_mutex(self.state_dir):
            self._assert_lease(lease)
            existing = self.list_generations(generation.work_id)
            if generation.generation_number != len(existing) + 1:
                raise CurationStateError("new generation number is not next")
            if any(item.generation_id == generation.generation_id for item in existing):
                raise CurationStateError("generation identity already exists")
            self._save_generation(generation)

    def append_event(
        self,
        work_id: str,
        generation_id: str,
        event: CurationGenerationEvent,
        lease: RunLease,
    ) -> CurationGeneration:
        _validate_id(work_id, "work_id")
        self._assert_lease(lease)
        with _transition_mutex(self.state_dir):
            self._assert_lease(lease)
            current = self.load_current(work_id)
            if current is None or current.generation_id != generation_id:
                raise CurationStateError("current generation does not match request")
            if event.sequence != len(current.events) + 1:
                raise CurationStateError("appended event sequence is invalid")
            updated = CurationGeneration.model_validate(
                {**current.model_dump(), "events": (*current.events, event)}
            )
            self._save_generation(updated)
            return updated

    def _save_generation(self, generation: CurationGeneration) -> None:
        payload = generation.model_dump(mode="json")
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        if len(encoded) + 1 > _MAX_GENERATION_BYTES:
            raise ValueError("generation document exceeds size limit")
        _ensure_private_directory(self.generation_dir, parents=False)
        work_dir = self.generation_dir / generation.work_id
        _ensure_private_directory(work_dir, parents=False)
        path = work_dir / (
            f"{generation.generation_number}-{generation.generation_id}.json"
        )
        _write_json_atomic(path, payload)

    def _assert_lease(self, lease: RunLease) -> None:
        if lease.worker != "curation" or lease.state_dir != self.state_dir:
            raise CurationStateError("generation mutation requires curation lease")
        lease.assert_owner()


def _load_generation(path: Path) -> CurationGeneration:
    try:
        raw = _read_private_json(path, max_bytes=_MAX_GENERATION_BYTES)
        return CurationGeneration.model_validate_json(json.dumps(raw))
    except (LeaseMetadataError, RunLeaseError, ValidationError, TypeError) as exc:
        raise CurationStateError("generation state is unsafe or invalid") from exc


def _validate_id(value: str, field_name: str) -> None:
    if _ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a bounded safe identifier")

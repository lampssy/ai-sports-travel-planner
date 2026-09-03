from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import unicodedata
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Protocol, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ops.maintainer.git_ops import GuardedSyncResult, LegacyCurationRef
from ops.maintainer.runtime import (
    LeaseMetadataError,
    RunLease,
    RunLeaseError,
    _ensure_private_directory,
    _read_private_json,
    _transition_mutex,
    _write_json_atomic,
)
from ops.maintainer.state import StateStore, StateStoreError, WorkState

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
_MAX_LEGACY_FILE_BYTES = 65_536
_FORMAT_MARKER_NAME = "curation-state-format.json"
_MIGRATION_POINTER_NAME = "curation-state-migration.json"
_LEGACY_ARCHIVE_ROOT = "legacy-curation-v1"


class CurationStateError(RuntimeError):
    """Raised when generation authority cannot be loaded or advanced safely."""


class CurationMigrationError(CurationStateError):
    """Raised when legacy curation state cannot be archived safely."""

    def __init__(
        self,
        reason: Literal[
            "active-lease",
            "external-recovery",
            "format-conflict",
            "unsafe-state",
        ],
    ) -> None:
        self.reason = reason
        super().__init__(reason)


class CurationCheckpointStage(StrEnum):
    DELTA_VALIDATED = "delta-validated"
    REVIEWED = "reviewed"


class CurationRecipeId(StrEnum):
    PREPARE = "prepare_curation"
    CHECKPOINT_DELTA = "checkpoint_curation_delta"
    CHECKPOINT_INVENTORY_COMPLETION = "checkpoint_curation_inventory_completion"
    CHECKPOINT_REVIEWED = "checkpoint_curation_reviewed"
    VALIDATE = "validate_curation"
    PUBLISH_PUSH = "publish_push"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CurationStateFormat(_StrictModel):
    schema_version: Literal[1]
    format: Literal["generation-v2"]
    archive_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    migrated_at: datetime

    @model_validator(mode="after")
    def normalize_migrated_at(self) -> Self:
        if self.migrated_at.tzinfo is None or self.migrated_at.utcoffset() is None:
            raise ValueError("curation format time must include a timezone")
        object.__setattr__(self, "migrated_at", self.migrated_at.astimezone(UTC))
        return self


class LegacyCurationFileEntry(_StrictModel):
    source_path: str = Field(
        pattern=(
            r"^(?:work|continuations|remediation-continuations)/"
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\.json$"
        )
    )
    archive_path: str = Field(
        pattern=(
            r"^legacy-curation-v1/[0-9a-f]{32}/"
            r"(?:work|continuations|remediation-continuations)/"
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\.json$"
        )
    )
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1, le=_MAX_LEGACY_FILE_BYTES)


class LegacyCurationArchiveManifest(_StrictModel):
    schema_version: Literal[1]
    archive_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    created_at: datetime
    files: tuple[LegacyCurationFileEntry, ...]
    refs: tuple[LegacyCurationRef, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("curation archive time must include a timezone")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
        if len({item.source_path for item in self.files}) != len(self.files):
            raise ValueError("curation archive contains duplicate file paths")
        if len({item.source_ref for item in self.refs}) != len(self.refs):
            raise ValueError("curation archive contains duplicate refs")
        for item in self.files:
            expected = f"{_LEGACY_ARCHIVE_ROOT}/{self.archive_id}/{item.source_path}"
            if item.archive_path != expected:
                raise ValueError("curation archive file target is inconsistent")
        archive_ref_prefix = (
            f"refs/snowcast-maintainer/archive/legacy-curation-v1/{self.archive_id}/"
        )
        if any(
            not item.archive_ref.startswith(archive_ref_prefix) for item in self.refs
        ):
            raise ValueError("curation archive ref uses the wrong archive ID")
        return self


class LegacyCurationMigrationPointer(_StrictModel):
    schema_version: Literal[1]
    archive_id: str = Field(pattern=_GENERATION_ID_PATTERN)


class LegacyCurationMigrationResult(_StrictModel):
    archive_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    files_archived: int = Field(ge=0, le=10_000)
    refs_archived: int = Field(ge=0, le=10_000)
    already_migrated: bool


class LegacyCurationRefRepository(Protocol):
    def legacy_curation_refs(
        self,
        archive_id: str,
    ) -> tuple[LegacyCurationRef, ...]: ...

    def archive_legacy_curation_refs(
        self,
        refs: Sequence[LegacyCurationRef],
    ) -> int: ...


class CurationActionSubstitutions(_StrictModel):
    pr: int = Field(ge=1)
    generation_id: str = Field(pattern=_GENERATION_ID_PATTERN)
    head: str = Field(pattern=_SHA_PATTERN)
    report: str | None = Field(default=None, pattern=_REPORT_PATTERN)
    validation_base: str | None = Field(default=None, pattern=_SHA_PATTERN)
    continue_conflict: bool = False


class CurationNextAction(_StrictModel):
    recipe_id: CurationRecipeId
    substitutions: CurationActionSubstitutions
    caller_created_descendant_head: Literal[True] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_caller_created_head(self) -> Self:
        if (
            self.caller_created_descendant_head
            and self.recipe_id is not CurationRecipeId.CHECKPOINT_DELTA
        ):
            raise ValueError(
                "caller-created descendant is limited to delta checkpoints"
            )
        return self


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
    report_path: str | None = Field(default=None, pattern=_REPORT_PATTERN)


class CheckpointStartedEvent(_GenerationEvent):
    kind: Literal["checkpoint-started"] = "checkpoint-started"
    transaction_id: str = Field(pattern=_TRANSACTION_ID_PATTERN)
    stage: CurationCheckpointStage
    head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)
    validation_base: str = Field(pattern=_SHA_PATTERN)
    inventory_completion: Literal[True] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    expected_checkpoint_ref: str = Field(pattern=_REF_PATTERN)
    expected_squash_ref: str = Field(pattern=_REF_PATTERN)

    @model_validator(mode="after")
    def validate_inventory_completion_stage(self) -> Self:
        if (
            self.inventory_completion
            and self.stage is not CurationCheckpointStage.DELTA_VALIDATED
        ):
            raise ValueError(
                "inventory completion is limited to delta-validated checkpoints"
            )
        return self


class CheckpointCompletedEvent(_GenerationEvent):
    kind: Literal["checkpoint-completed"] = "checkpoint-completed"
    transaction_id: str = Field(pattern=_TRANSACTION_ID_PATTERN)
    checkpoint_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)


class CurationValidationDiagnostic(_StrictModel):
    format: Literal["pytest-short"]
    text: str = Field(min_length=1, max_length=8_192)
    truncated: bool

    @field_validator("text")
    @classmethod
    def reject_unsafe_control_characters(cls, value: str) -> str:
        if any(
            unicodedata.category(character) == "Cc" and character not in {"\n", "\t"}
            for character in value
        ):
            raise ValueError("validation diagnostic contains a control character")
        return value


class CurationValidationFailure(_StrictModel):
    check: Literal[
        "preflight",
        "catalog-validation",
        "curation-reconciliation",
        "catalog-tests",
        "post-validation",
        "remote-head",
        "publication-input",
    ]
    kind: Literal[
        "mismatch",
        "command-failed",
        "timeout",
        "transport",
        "invalid-file",
        "not-basename",
    ]
    diagnostic: CurationValidationDiagnostic | None = None

    @model_validator(mode="after")
    def validate_diagnostic_scope(self) -> Self:
        if self.diagnostic is not None and (
            self.check != "catalog-tests" or self.kind != "command-failed"
        ):
            raise ValueError(
                "validation diagnostic requires a catalog test command failure"
            )
        return self


class ValidationFailedEvent(_GenerationEvent):
    kind: Literal["validation-failed"] = "validation-failed"
    head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)
    failure: CurationValidationFailure | None = None


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
    transaction_id: str = Field(pattern=_TRANSACTION_ID_PATTERN)
    branch: str = Field(min_length=1, max_length=200)
    selected_head: str = Field(pattern=_SHA_PATTERN)
    base_head: str = Field(pattern=_SHA_PATTERN)
    reviewed_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(pattern=_REPORT_PATTERN)
    sync: GuardedSyncResult
    reviewed_at: datetime
    checkpoint_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)


class CurationCheckpointAuthority(ReviewedCurationAuthority):
    stage: CurationCheckpointStage


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
                    inventory_completion=event.inventory_completion,
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
            "validation-failed",
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
    checkpoint_authority: CurationCheckpointAuthority | None = None
    reviewed_authority: ReviewedCurationAuthority | None = None
    validated_authority: ValidatedCurationAuthority | None = None
    validation_failure: CurationValidationFailure | None = None
    inventory_completion_checkpointed: bool = False
    inventory_completion_checkpoint_head: str | None = Field(
        default=None,
        pattern=_SHA_PATTERN,
    )
    next_action: CurationNextAction | None = None


def checkpoint_transaction_id(
    generation_id: str,
    stage: CurationCheckpointStage,
    head: str,
    report_path: str,
    validation_base: str,
    *,
    inventory_completion: Literal[True] | None = None,
) -> str:
    fields = [generation_id, stage.value, head, report_path, validation_base]
    # Keep pre-marker transaction identities valid when reading existing state.
    if inventory_completion:
        fields.append("inventory-completion")
    payload = "\0".join(fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def project_generation(
    generation: CurationGeneration,
) -> CurationGenerationProjection:
    latest_head = generation.sync.rebased_head
    latest_stage: (
        CurationCheckpointStage
        | Literal[
            "prepared",
            "validation-failed",
            "fully-validated",
            "superseded",
            "invalidated",
            "consumed",
        ]
    ) = "prepared"
    incomplete: CheckpointStartedEvent | None = None
    starts: dict[str, CheckpointStartedEvent] = {}
    reviewed: ReviewedCurationAuthority | None = None
    checkpoint: CurationCheckpointAuthority | None = None
    validated: ValidatedCurationAuthority | None = None
    validation_failure: CurationValidationFailure | None = None
    inventory_completion_checkpointed = False
    inventory_completion_checkpoint_head: str | None = None
    latest_report: str | None = generation.events[0].report_path
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
            checkpoint = _checkpoint_authority(generation, started, event)
            if (
                started.stage is CurationCheckpointStage.DELTA_VALIDATED
                and started.inventory_completion
            ):
                inventory_completion_checkpointed = True
                inventory_completion_checkpoint_head = started.head
            validated = None
            validation_failure = None
            if started.stage is CurationCheckpointStage.REVIEWED:
                reviewed = _reviewed_authority(
                    generation,
                    started,
                    event,
                )
            else:
                reviewed = None
        elif isinstance(event, ValidationFailedEvent):
            latest_stage = "validation-failed"
            validated = None
            validation_failure = event.failure
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
            validation_failure = None
        elif isinstance(event, GenerationClosedEvent):
            latest_stage = event.kind.removeprefix("generation-")
            checkpoint = None
            reviewed = None
            validated = None
            validation_failure = None

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
    elif latest_stage == "validation-failed" and validation_failure is not None:
        assert reviewed is not None
        next_action = CurationNextAction(
            recipe_id=CurationRecipeId.PREPARE,
            substitutions=CurationActionSubstitutions(
                pr=generation.pr_number,
                generation_id=generation.generation_id,
                head=reviewed.reviewed_head,
                report=reviewed.report_path,
                validation_base=generation.sync.base_head,
            ),
        )
    elif latest_stage in {"prepared", CurationCheckpointStage.REVIEWED}:
        report = reviewed.report_path if reviewed is not None else latest_report
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

    if latest_refs is None and latest_stage in {
        CurationCheckpointStage.DELTA_VALIDATED,
        CurationCheckpointStage.REVIEWED,
        "validation-failed",
        "fully-validated",
    }:
        raise CurationStateError("generation projection lost checkpoint refs")
    return CurationGenerationProjection(
        generation_id=generation.generation_id,
        generation_number=generation.generation_number,
        latest_head=latest_head,
        latest_stage=latest_stage,
        incomplete_transaction=(
            incomplete.transaction_id if incomplete is not None else None
        ),
        checkpoint_authority=checkpoint,
        reviewed_authority=reviewed,
        validated_authority=validated,
        validation_failure=validation_failure,
        inventory_completion_checkpointed=inventory_completion_checkpointed,
        inventory_completion_checkpoint_head=inventory_completion_checkpoint_head,
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
        transaction_id=started.transaction_id,
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


def _checkpoint_authority(
    generation: CurationGeneration,
    started: CheckpointStartedEvent,
    completed: CheckpointCompletedEvent,
) -> CurationCheckpointAuthority:
    return CurationCheckpointAuthority(
        **_reviewed_authority(generation, started, completed).model_dump(),
        stage=started.stage,
    )


def _checkpoint_action(
    generation: CurationGeneration,
    started: CheckpointStartedEvent,
) -> CurationNextAction:
    if started.stage is CurationCheckpointStage.REVIEWED:
        recipe = CurationRecipeId.CHECKPOINT_REVIEWED
    elif started.inventory_completion:
        recipe = CurationRecipeId.CHECKPOINT_INVENTORY_COMPLETION
    else:
        recipe = CurationRecipeId.CHECKPOINT_DELTA
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

        paths = tuple(work_dir.iterdir())

        def generation_number(path: Path) -> int:
            match = _GENERATION_FILE_PATTERN.fullmatch(path.name)
            if match is None:
                raise CurationStateError(
                    "generation directory contains an unknown file"
                )
            return int(match.group("number"))

        generations: list[CurationGeneration] = []
        for path in sorted(paths, key=generation_number):
            match = _GENERATION_FILE_PATTERN.fullmatch(path.name)
            assert match is not None
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


def curation_state_migration_required(state_dir: str | Path) -> bool:
    state_path = Path(state_dir)
    try:
        state_path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise CurationMigrationError("unsafe-state") from exc
    marker = _load_format_marker(state_path)
    if marker is not None:
        return False
    if (state_path / _MIGRATION_POINTER_NAME).exists():
        return True
    for directory_name in (
        "continuations",
        "remediation-continuations",
    ):
        directory = state_path / directory_name
        if directory.exists() and any(directory.iterdir()):
            return True
    try:
        store = StateStore(state_path)
        for path in _validated_json_directory(state_path / "work"):
            work = store.load_work(path.name.removesuffix(".json"))
            if not isinstance(work, WorkState):
                raise CurationMigrationError("unsafe-state")
            if work.worker == "curation":
                return True
    except StateStoreError as exc:
        raise CurationMigrationError("unsafe-state") from exc
    return False


def migrate_legacy_curation_state(
    state_dir: str | Path,
    repository: LegacyCurationRefRepository,
    *,
    now: datetime,
    archive_id_factory: Callable[[], str] = lambda: secrets.token_hex(16),
) -> LegacyCurationMigrationResult:
    state_path = Path(state_dir)
    observed_at = _normalize_migration_time(now)
    _ensure_private_directory(state_path, parents=True)
    with _transition_mutex(state_path):
        _require_no_active_lease(state_path)
        marker = _load_format_marker(state_path)
        if marker is not None:
            manifest = _load_archive_manifest(state_path, marker.archive_id)
            for entry in manifest.files:
                source = state_path / entry.source_path
                archive = state_path / entry.archive_path
                if (
                    source.exists()
                    or not archive.exists()
                    or not _matches_archive_entry(archive, entry)
                ):
                    raise CurationMigrationError("format-conflict")
            repository.archive_legacy_curation_refs(manifest.refs)
            pointer_path = state_path / _MIGRATION_POINTER_NAME
            if pointer_path.exists():
                pointer = _load_migration_pointer(pointer_path)
                if pointer.archive_id != marker.archive_id:
                    raise CurationMigrationError("format-conflict")
                pointer_path.unlink()
            return LegacyCurationMigrationResult(
                archive_id=marker.archive_id,
                files_archived=len(manifest.files),
                refs_archived=len(manifest.refs),
                already_migrated=True,
            )

        if CurationGenerationStore.list_current_for_inspection_path(state_path):
            raise CurationMigrationError("format-conflict")
        _require_no_external_recovery(state_path)
        pointer_path = state_path / _MIGRATION_POINTER_NAME
        if pointer_path.exists():
            pointer = _load_migration_pointer(pointer_path)
            manifest = _load_archive_manifest(state_path, pointer.archive_id)
        else:
            archive_id = archive_id_factory()
            if re.fullmatch(_GENERATION_ID_PATTERN, archive_id) is None:
                raise CurationMigrationError("unsafe-state")
            files = _inventory_legacy_curation_files(state_path, archive_id)
            refs = repository.legacy_curation_refs(archive_id)
            manifest = LegacyCurationArchiveManifest(
                schema_version=1,
                archive_id=archive_id,
                created_at=observed_at,
                files=files,
                refs=refs,
            )
            archive_dir = _archive_dir(state_path, archive_id)
            _ensure_private_directory(
                state_path / _LEGACY_ARCHIVE_ROOT,
                parents=False,
            )
            _ensure_private_directory(archive_dir, parents=False)
            _write_json_atomic(
                archive_dir / "manifest.json",
                manifest.model_dump(mode="json"),
            )
            _write_json_atomic(
                pointer_path,
                LegacyCurationMigrationPointer(
                    schema_version=1,
                    archive_id=archive_id,
                ).model_dump(mode="json"),
            )

        repository.archive_legacy_curation_refs(manifest.refs)
        for entry in manifest.files:
            _archive_legacy_file(state_path, entry)
        marker = CurationStateFormat(
            schema_version=1,
            format="generation-v2",
            archive_id=manifest.archive_id,
            migrated_at=observed_at,
        )
        _write_json_atomic(
            state_path / _FORMAT_MARKER_NAME,
            marker.model_dump(mode="json"),
        )
        pointer_path.unlink(missing_ok=True)
        return LegacyCurationMigrationResult(
            archive_id=manifest.archive_id,
            files_archived=len(manifest.files),
            refs_archived=len(manifest.refs),
            already_migrated=False,
        )


def _inventory_legacy_curation_files(
    state_path: Path,
    archive_id: str,
) -> tuple[LegacyCurationFileEntry, ...]:
    store = StateStore(state_path)
    candidates: list[Path] = []
    for directory_name, loader in (
        ("continuations", store.load_continuation),
        (
            "remediation-continuations",
            store.load_remediation_continuation,
        ),
    ):
        directory = state_path / directory_name
        for path in _validated_json_directory(directory):
            work_id = path.name.removesuffix(".json")
            if loader(work_id) is None:
                raise CurationMigrationError("unsafe-state")
            candidates.append(path)
    work_dir = state_path / "work"
    for path in _validated_json_directory(work_dir):
        work_id = path.name.removesuffix(".json")
        work = store.load_work(work_id)
        if not isinstance(work, WorkState):
            raise CurationMigrationError("unsafe-state")
        if work.worker == "curation":
            candidates.append(path)

    entries = []
    for path in sorted(candidates):
        raw = _read_private_bytes(path)
        relative = path.relative_to(state_path).as_posix()
        entries.append(
            LegacyCurationFileEntry(
                source_path=relative,
                archive_path=(f"{_LEGACY_ARCHIVE_ROOT}/{archive_id}/{relative}"),
                sha256=hashlib.sha256(raw).hexdigest(),
                size_bytes=len(raw),
            )
        )
    return tuple(entries)


def _validated_json_directory(directory: Path) -> tuple[Path, ...]:
    try:
        directory.lstat()
    except FileNotFoundError:
        return ()
    except OSError as exc:
        raise CurationMigrationError("unsafe-state") from exc
    try:
        _ensure_private_directory(directory, parents=False, create=False)
        entries = tuple(sorted(directory.iterdir(), key=lambda item: item.name))
    except (OSError, RunLeaseError) as exc:
        raise CurationMigrationError("unsafe-state") from exc
    if any(
        not path.name.endswith(".json") or path.name in {".json", "..json"}
        for path in entries
    ):
        raise CurationMigrationError("unsafe-state")
    return entries


def _read_private_bytes(path: Path) -> bytes:
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
            or not 0 < metadata.st_size <= _MAX_LEGACY_FILE_BYTES
        ):
            raise CurationMigrationError("unsafe-state")
        raw = os.read(descriptor, metadata.st_size + 1)
        if len(raw) != metadata.st_size:
            raise CurationMigrationError("unsafe-state")
        return raw
    except CurationMigrationError:
        raise
    except OSError as exc:
        raise CurationMigrationError("unsafe-state") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _archive_legacy_file(
    state_path: Path,
    entry: LegacyCurationFileEntry,
) -> None:
    source = state_path / entry.source_path
    archive = state_path / entry.archive_path
    if archive.exists():
        if source.exists() or not _matches_archive_entry(archive, entry):
            raise CurationMigrationError("format-conflict")
        return
    if not source.exists() or not _matches_archive_entry(source, entry):
        raise CurationMigrationError("format-conflict")
    _ensure_private_directory(archive.parent, parents=True)
    try:
        source.replace(archive)
    except OSError as exc:
        raise CurationMigrationError("unsafe-state") from exc
    if not _matches_archive_entry(archive, entry):
        raise CurationMigrationError("unsafe-state")


def _matches_archive_entry(path: Path, entry: LegacyCurationFileEntry) -> bool:
    raw = _read_private_bytes(path)
    return (
        len(raw) == entry.size_bytes and hashlib.sha256(raw).hexdigest() == entry.sha256
    )


def _load_format_marker(state_path: Path) -> CurationStateFormat | None:
    path = state_path / _FORMAT_MARKER_NAME
    try:
        raw = _read_private_json(path, max_bytes=4096)
    except FileNotFoundError:
        return None
    except (LeaseMetadataError, RunLeaseError) as exc:
        raise CurationMigrationError("unsafe-state") from exc
    try:
        return CurationStateFormat.model_validate_json(json.dumps(raw))
    except ValidationError as exc:
        raise CurationMigrationError("unsafe-state") from exc


def _load_migration_pointer(path: Path) -> LegacyCurationMigrationPointer:
    try:
        raw = _read_private_json(path, max_bytes=4096)
        return LegacyCurationMigrationPointer.model_validate_json(json.dumps(raw))
    except (LeaseMetadataError, RunLeaseError, ValidationError) as exc:
        raise CurationMigrationError("unsafe-state") from exc


def _load_archive_manifest(
    state_path: Path,
    archive_id: str,
) -> LegacyCurationArchiveManifest:
    try:
        raw = _read_private_json(
            _archive_dir(state_path, archive_id) / "manifest.json",
            max_bytes=1_048_576,
        )
        manifest = LegacyCurationArchiveManifest.model_validate_json(json.dumps(raw))
    except (
        FileNotFoundError,
        LeaseMetadataError,
        RunLeaseError,
        ValidationError,
    ) as exc:
        raise CurationMigrationError("unsafe-state") from exc
    if manifest.archive_id != archive_id:
        raise CurationMigrationError("format-conflict")
    return manifest


def _archive_dir(state_path: Path, archive_id: str) -> Path:
    return state_path / _LEGACY_ARCHIVE_ROOT / archive_id


def _require_no_active_lease(state_path: Path) -> None:
    try:
        (state_path / "run.lock").lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise CurationMigrationError("unsafe-state") from exc
    raise CurationMigrationError("active-lease")


def _require_no_external_recovery(state_path: Path) -> None:
    try:
        if (
            StateStore.list_unresolved_for_inspection(state_path)
            or StateStore.list_ci_continuations_for_inspection_path(state_path)
            or StateStore.list_terminal_publications_for_inspection_path(state_path)
        ):
            raise CurationMigrationError("external-recovery")
    except StateStoreError as exc:
        raise CurationMigrationError("unsafe-state") from exc


def _normalize_migration_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("migration time must include a timezone")
    return value.astimezone(UTC)


def _load_generation(path: Path) -> CurationGeneration:
    try:
        raw = _read_private_json(path, max_bytes=_MAX_GENERATION_BYTES)
        return CurationGeneration.model_validate_json(json.dumps(raw))
    except (LeaseMetadataError, RunLeaseError, ValidationError, TypeError) as exc:
        raise CurationStateError("generation state is unsafe or invalid") from exc


def _validate_id(value: str, field_name: str) -> None:
    if _ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a bounded safe identifier")

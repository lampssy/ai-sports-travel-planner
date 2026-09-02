from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Literal

from pydantic import ValidationError

from ops.maintainer import LABEL_DEFINITIONS
from ops.maintainer.boundary_adjudication import validate_boundary_adjudication
from ops.maintainer.curation_state import (
    CheckpointCompletedEvent,
    CheckpointStartedEvent,
    CurationActionSubstitutions,
    CurationCheckpointAuthority,
    CurationCheckpointStage,
    CurationGeneration,
    CurationGenerationStore,
    CurationMigrationError,
    CurationNextAction,
    CurationRecipeId,
    CurationStateError,
    GenerationClosedEvent,
    GenerationPreparedEvent,
    ValidationFailedEvent,
    ValidationPassedEvent,
    checkpoint_transaction_id,
    curation_state_migration_required,
    migrate_legacy_curation_state,
    project_generation,
)
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    ErrorStage,
    MaintainerError,
)
from ops.maintainer.git_ops import (
    CiRepairCheckpoint,
    CurationCheckpointIntegrityError,
    CurationCheckpointRefs,
    CurationRecoveryCheckpoint,
    GitAuthenticationError,
    GitOperationTimeoutError,
    GitPushRejectedError,
    GitRemotePolicyError,
    GitRepository,
    GitTransportError,
    GuardedSyncResult,
    IntentDriftError,
    RebaseConflictError,
    RepositorySafetyError,
    StaleRemoteHeadError,
)
from ops.maintainer.github import (
    GitHubComment,
    GitHubError,
)
from ops.maintainer.inspection import (
    DiscoveryInventory,
    ci_continuation_invalidation_reason,
    inspect_curation,
    inspect_discovery,
)
from ops.maintainer.models import (
    CheckSummary,
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
    is_confirmed_ci_failure,
)
from ops.maintainer.publication import (
    PublicationInputError,
    ci_publication_machine_state,
    create_publication_text,
    extract_managed_body,
    outcome_plan,
    publication_plan,
    publish_discovery_proposal,
    publish_outcome,
    publish_state,
    read_publication_text,
    trusted_hold_head,
    trusted_machine_state,
    validate_outcome_publication_input,
    validate_publication_state_directory,
)
from ops.maintainer.runtime import (
    LeaseOwnershipError,
    LockBusyError,
    RunLease,
    RunLeaseError,
)
from ops.maintainer.state import (
    CiContinuation,
    CiContinuationPhase,
    PushJournal,
    PushPhase,
    RunOutcome,
    StateStore,
    StateStoreError,
    TerminalPublicationIntent,
    TerminalPublicationPhase,
    WorkPhase,
    WorkState,
)
from ops.maintainer.validation import (
    DeltaValidationResult,
    ProposalValidationResult,
    ValidationResult,
    immutable_resulting_graph_markdown,
    require_single_curation_report_path,
    revalidate_curation_request,
    single_curation_report_path,
)

Worker = Literal["curation", "discovery"]
Handler = Callable[[argparse.Namespace, "Dependencies"], dict[str, object]]

_PR_HEAD_CONVERGENCE_ATTEMPTS = 5
_PR_HEAD_CONVERGENCE_DELAY_SECONDS = 3.0
_CI_REPAIR_WAITING_SUMMARY = (
    "One focused test-only CI repair was pushed. "
    "GitHub CI is running on the exact repaired head."
)


class CLIInputError(ValueError):
    """Raised instead of allowing argparse to write unstructured errors."""


@dataclass
class OutcomeTracker:
    worker: Worker
    lease_run_id: str | None = None
    work_id: str | None = None
    pr_number: int | None = None
    candidate_key: str | None = None
    last_phase: WorkPhase | None = None
    mutation_occurred: bool = False
    terminal_reason: str = "completed"
    stage: ErrorStage = ErrorStage.DISPATCH

    def payload(self) -> dict[str, object]:
        outcome = RunOutcome(
            worker=self.worker,
            lease_run_id=self.lease_run_id,
            work_id=self.work_id,
            pr_number=self.pr_number,
            candidate_key=self.candidate_key,
            last_phase=self.last_phase,
            mutation_occurred=self.mutation_occurred,
            terminal_reason=self.terminal_reason,
        )
        return outcome.model_dump(mode="json", exclude_none=True)


@dataclass(frozen=True)
class Dependencies:
    github: object
    repository: object
    base_repository: object | None
    curation_validator: Callable[..., ValidationResult]
    curation_delta_validator: Callable[..., DeltaValidationResult]
    proposal_validator: Callable[..., ProposalValidationResult]
    catalog_keys_provider: Callable[[], frozenset[str]]
    repository_root: Path
    now: Callable[[], datetime]
    tracker: OutcomeTracker


def _work_id_for_pr(pr_number: int) -> str:
    return f"curation-pr-{pr_number}"


def _work_id_for_candidate(candidate_key: str) -> str:
    return "proposal-" + candidate_key.replace(":", "-").replace("_", "-")


def _current_time(
    dependencies: Dependencies,
    existing: WorkState | CiContinuation | None = None,
) -> datetime:
    observed = dependencies.now()
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("current time must include a timezone")
    observed = observed.astimezone(UTC)
    if existing is not None and observed <= existing.updated_at:
        return existing.updated_at + timedelta(microseconds=1)
    return observed


def _state_store(args: argparse.Namespace) -> StateStore:
    return StateStore(args.state_dir)


def _owned_lease(
    args: argparse.Namespace,
    worker: Worker,
    dependencies: Dependencies,
) -> RunLease:
    dependencies.tracker.worker = worker
    dependencies.tracker.lease_run_id = args.run_id
    dependencies.tracker.stage = ErrorStage.LOCK
    return RunLease.load_owner(args.state_dir, worker, args.run_id)


def _comments_by_pr(
    github: object,
    pull_requests: Sequence[PullRequest],
) -> dict[int, Sequence[GitHubComment]]:
    return {
        pull_request.number: tuple(github.list_issue_comments(pull_request.number))
        for pull_request in pull_requests
    }


def _discovery_inventory(
    dependencies: Dependencies,
    *,
    unresolved_pushes: Sequence[PushJournal] = (),
) -> DiscoveryInventory:
    open_pull_requests = tuple(dependencies.github.list_all_open_pull_requests())
    closed_pull_requests = tuple(
        dependencies.github.list_closed_discovery_pull_requests()
    )
    all_pull_requests = (*open_pull_requests, *closed_pull_requests)
    return inspect_discovery(
        dependencies.catalog_keys_provider(),
        open_pull_requests,
        closed_pull_requests,
        _comments_by_pr(dependencies.github, all_pull_requests),
        unresolved_pushes,
    )


def _serialize_model(model: object) -> dict[str, object]:
    return model.model_dump(mode="json")


def handle_inspect_curation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    dependencies.tracker.worker = "curation"
    dependencies.tracker.stage = ErrorStage.INSPECT
    terminal_publications = StateStore.list_terminal_publications_for_inspection_path(
        args.state_dir
    )
    if terminal_publications:
        inventory = inspect_curation(
            (),
            {},
            terminal_publications=terminal_publications,
            now=_current_time(dependencies),
        )
        dependencies.tracker.terminal_reason = "recovery-required"
        return _serialize_model(inventory)
    unresolved_pushes = StateStore.list_unresolved_for_inspection(args.state_dir)
    ci_continuations = (
        ()
        if unresolved_pushes
        else StateStore.list_ci_continuations_for_inspection_path(args.state_dir)
    )
    active_ci_continuations = tuple(
        continuation
        for continuation in ci_continuations
        if continuation.phase
        not in {
            CiContinuationPhase.CONSUMED,
            CiContinuationPhase.BLOCKED,
            CiContinuationPhase.INVALIDATED,
        }
    )
    if not unresolved_pushes and not active_ci_continuations:
        if curation_state_migration_required(args.state_dir):
            raise MaintainerError(
                ErrorReason.STATE_MIGRATION_REQUIRED,
                ErrorStage.INSPECT,
            )
        generations = CurationGenerationStore.list_current_for_inspection_path(
            args.state_dir
        )
    else:
        generations = ()
    open_pull_requests = tuple(dependencies.github.list_all_open_pull_requests())
    open_pr_numbers = {item.number for item in open_pull_requests}
    continuation_pr_numbers = {
        continuation.pr_number for continuation in ci_continuations
    } | {generation.pr_number for generation in generations}
    continuation_pull_requests = tuple(
        dependencies.github.get_pull_request(pr_number)
        for pr_number in sorted(continuation_pr_numbers)
        if pr_number not in open_pr_numbers
    )
    pull_requests = (*open_pull_requests, *continuation_pull_requests)
    inventory = inspect_curation(
        pull_requests,
        _comments_by_pr(dependencies.github, pull_requests),
        unresolved_pushes,
        ci_continuations=ci_continuations,
        now=_current_time(dependencies),
        generations=generations,
    )
    dependencies.tracker.terminal_reason = (
        "recovery-required" if inventory.unresolved_pushes else "inspected"
    )
    return _serialize_model(inventory)


def handle_inspect_discovery(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    dependencies.tracker.worker = "discovery"
    dependencies.tracker.stage = ErrorStage.INSPECT
    inventory = _discovery_inventory(
        dependencies,
        unresolved_pushes=StateStore.list_unresolved_for_inspection(args.state_dir),
    )
    dependencies.tracker.terminal_reason = (
        "recovery-required"
        if inventory.unresolved_pushes
        else "proposal-cap"
        if not inventory.can_create_proposal
        else "inspected"
    )
    return _serialize_model(inventory)


def _require_exact_curation_candidate(
    pull_request: PullRequest,
    dependencies: Dependencies,
    store: StateStore,
) -> None:
    inventory = inspect_curation(
        (pull_request,),
        {
            pull_request.number: tuple(
                dependencies.github.list_issue_comments(pull_request.number)
            )
        },
        store.list_unresolved_pushes(),
    )
    if len(inventory.eligible) != 1:
        raise MaintainerError(
            ErrorReason.INVALID_GITHUB_STATE,
            ErrorStage.INSPECT,
            detail="Requested pull request is not safe curation work",
        )


def handle_prepare_curation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    generation_store = CurationGenerationStore(args.state_dir)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PREPARE
    if store.list_unresolved_terminal_publications():
        raise StateStoreError(
            "unresolved terminal publication requires exact recovery before preparation"
        )
    if store.list_ci_continuations_for_inspection():
        raise StateStoreError(
            "active CI continuation requires exact recovery before preparation"
        )
    pull_request = dependencies.github.get_pull_request(args.pr)
    _require_exact_curation_candidate(pull_request, dependencies, store)
    try:
        single_curation_report_path(pull_request.changed_paths)
    except ValueError:
        raise MaintainerError(
            ErrorReason.INVALID_GITHUB_STATE,
            ErrorStage.PREPARE,
            detail="Curation work must contain exactly one canonical report",
        ) from None
    if (
        store.load_continuation(work_id) is not None
        or store.load_remediation_continuation(work_id) is not None
    ):
        raise MaintainerError(
            ErrorReason.STATE_MIGRATION_REQUIRED,
            ErrorStage.PREPARE,
        )
    current = generation_store.load_current(work_id)
    if current is None:
        if args.continue_conflict:
            raise MaintainerError(
                ErrorReason.CHECKPOINT_CONFLICT,
                ErrorStage.PREPARE,
            )
        return _prepare_new_curation_generation(
            pull_request=pull_request,
            lease=lease,
            store=store,
            generation_store=generation_store,
            dependencies=dependencies,
            generation_number=1,
        )

    projection = project_generation(current)
    if (
        projection.latest_stage == "validation-failed"
        and projection.validation_failure is None
    ):
        raise CurationStateError(
            "unclassified validation failure cannot authorize remediation"
        )
    if projection.latest_stage in {"superseded", "invalidated", "consumed"}:
        if args.continue_conflict:
            raise MaintainerError(
                ErrorReason.CHECKPOINT_CONFLICT,
                ErrorStage.PREPARE,
            )
        return _prepare_new_curation_generation(
            pull_request=pull_request,
            lease=lease,
            store=store,
            generation_store=generation_store,
            dependencies=dependencies,
            generation_number=current.generation_number + 1,
        )
    if current.selected_head != pull_request.head_sha:
        _close_generation(
            generation_store,
            current,
            lease,
            dependencies,
            kind="generation-invalidated",
            reason="remote_head_changed",
        )
        if args.continue_conflict:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PREPARE)
        return _prepare_new_curation_generation(
            pull_request=pull_request,
            lease=lease,
            store=store,
            generation_store=generation_store,
            dependencies=dependencies,
            generation_number=current.generation_number + 1,
        )

    checkpoint = projection.checkpoint_authority
    if checkpoint is None:
        _close_generation(
            generation_store,
            current,
            lease,
            dependencies,
            kind="generation-superseded",
            reason="prepared_restart",
        )
        if args.continue_conflict:
            raise MaintainerError(
                ErrorReason.CHECKPOINT_CONFLICT,
                ErrorStage.PREPARE,
            )
        return _prepare_new_curation_generation(
            pull_request=pull_request,
            lease=lease,
            store=store,
            generation_store=generation_store,
            dependencies=dependencies,
            generation_number=current.generation_number + 1,
        )

    recovery = _generation_recovery(current, checkpoint)
    existing_work = store.load_work(work_id)
    if args.continue_conflict:
        if (
            existing_work is None
            or existing_work.run_id != lease.run_id
            or existing_work.phase is not WorkPhase.SELECTED
        ):
            raise MaintainerError(
                ErrorReason.CHECKPOINT_CONFLICT,
                ErrorStage.PREPARE,
            )
        replay = dependencies.repository.continue_curation_conflict(
            pull_request,
            recovery,
        )
        selected = existing_work
    else:
        if existing_work is not None and existing_work.run_id == lease.run_id:
            raise MaintainerError(
                ErrorReason.LOCAL_RECOVERY_REQUIRED,
                ErrorStage.PREPARE,
                retryable=True,
                next_action=_continue_conflict_action(current),
            )
        selected = _begin_selected_curation_work(
            pull_request,
            lease,
            store,
            dependencies,
        )
        try:
            replay = dependencies.repository.prepare_curation_recovery(
                pull_request,
                recovery,
                restart_interrupted=(
                    existing_work is not None and existing_work.run_id != lease.run_id
                ),
            )
        except CurationCheckpointIntegrityError:
            _close_generation(
                generation_store,
                current,
                lease,
                dependencies,
                kind="generation-invalidated",
                reason="checkpoint_missing",
            )
            return _prepare_new_curation_generation(
                pull_request=pull_request,
                lease=lease,
                store=store,
                generation_store=generation_store,
                dependencies=dependencies,
                generation_number=current.generation_number + 1,
                selected=selected,
            )

    if replay.result == "conflict":
        dependencies.tracker.mutation_occurred = True
        dependencies.tracker.last_phase = WorkPhase.SELECTED
        dependencies.tracker.terminal_reason = "curation-conflict"
        return {
            "work_id": work_id,
            "generation": _generation_result(
                current,
                result="conflict-resolution-required",
                conflict_paths=replay.conflict_paths,
                next_action=_continue_conflict_action(current),
            ),
        }
    if replay.sync is None or replay.head is None:
        raise CurationStateError("curation replay omitted prepared facts")
    prepared_work = _advance_work(
        store,
        lease,
        selected,
        dependencies,
        WorkPhase.PREPARED,
        prepared_head=replay.sync.rebased_head,
        backup_ref=replay.sync.backup_ref,
        sync=replay.sync,
    )
    if replay.result == "unchanged":
        result = "review-required"
        if checkpoint.stage is CurationCheckpointStage.REVIEWED:
            if projection.latest_stage == "validation-failed":
                result = "validation-remediation"
            else:
                prepared_work = _advance_work(
                    store,
                    lease,
                    prepared_work,
                    dependencies,
                    WorkPhase.REVIEWED,
                    reviewed_head=checkpoint.reviewed_head,
                )
                result = "validation-only"
        dependencies.tracker.last_phase = prepared_work.phase
        dependencies.tracker.terminal_reason = f"generation-{result}"
        return {
            "work_id": work_id,
            "generation": _generation_result(
                current,
                result=result,
                next_action=(
                    _validation_remediation_action(current)
                    if result == "validation-remediation"
                    else projection.next_action
                ),
            ),
        }

    _close_generation(
        generation_store,
        current,
        lease,
        dependencies,
        kind="generation-superseded",
        reason="main_advanced",
    )
    generation = _new_generation(
        pull_request,
        replay.sync,
        current.generation_number + 1,
        dependencies,
    )
    generation_store.start_generation(generation, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.PREPARED
    dependencies.tracker.terminal_reason = "generation-review-required"
    return {
        "work_id": work_id,
        "generation": _generation_result(generation, result="review-required"),
        "prepared": replay.sync.model_dump(mode="json"),
    }


def _prepare_new_curation_generation(
    *,
    pull_request: PullRequest,
    lease: RunLease,
    store: StateStore,
    generation_store: CurationGenerationStore,
    dependencies: Dependencies,
    generation_number: int,
    selected: WorkState | None = None,
) -> dict[str, object]:
    selected = selected or _begin_selected_curation_work(
        pull_request,
        lease,
        store,
        dependencies,
    )
    sync = dependencies.repository.prepare_guarded_sync(pull_request)
    _advance_work(
        store,
        lease,
        selected,
        dependencies,
        WorkPhase.PREPARED,
        prepared_head=sync.rebased_head,
        backup_ref=sync.backup_ref,
        sync=sync,
    )
    generation = _new_generation(
        pull_request,
        sync,
        generation_number,
        dependencies,
    )
    generation_store.start_generation(generation, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.PREPARED
    dependencies.tracker.terminal_reason = "prepared"
    return {
        "work_id": selected.work_id,
        "generation": _generation_result(generation, result="prepared"),
        "prepared": sync.model_dump(mode="json"),
    }


def _begin_selected_curation_work(
    pull_request: PullRequest,
    lease: RunLease,
    store: StateStore,
    dependencies: Dependencies,
) -> WorkState:
    work_id = _work_id_for_pr(pull_request.number)
    selected = WorkState(
        work_id=work_id,
        worker="curation",
        run_id=lease.run_id,
        phase=WorkPhase.SELECTED,
        updated_at=_current_time(dependencies, store.load_work(work_id)),
        pr_number=pull_request.number,
        selected_head=pull_request.head_sha,
    )
    store.begin_work(selected, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.SELECTED
    return selected


def _new_generation(
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    generation_number: int,
    dependencies: Dependencies,
) -> CurationGeneration:
    created_at = _current_time(dependencies)
    return CurationGeneration(
        schema_version=2,
        work_id=_work_id_for_pr(pull_request.number),
        pr_number=pull_request.number,
        generation_number=generation_number,
        generation_id=secrets.token_hex(16),
        created_at=created_at,
        selected_head=pull_request.head_sha,
        target_branch=pull_request.head_ref_name,
        sync=sync,
        events=(
            GenerationPreparedEvent(
                sequence=1,
                recorded_at=created_at,
                prepared_head=sync.rebased_head,
                report_path=single_curation_report_path(pull_request.changed_paths),
            ),
        ),
    )


def _close_generation(
    store: CurationGenerationStore,
    generation: CurationGeneration,
    lease: RunLease,
    dependencies: Dependencies,
    *,
    kind: Literal[
        "generation-superseded",
        "generation-invalidated",
        "generation-consumed",
    ],
    reason: str,
) -> None:
    recorded_at = max(
        _current_time(dependencies),
        generation.events[-1].recorded_at + timedelta(microseconds=1),
    )
    store.append_event(
        generation.work_id,
        generation.generation_id,
        GenerationClosedEvent(
            sequence=len(generation.events) + 1,
            recorded_at=recorded_at,
            kind=kind,
            reason=reason,
        ),
        lease,
    )
    dependencies.tracker.mutation_occurred = True


def _generation_recovery(
    generation: CurationGeneration,
    checkpoint: CurationCheckpointAuthority,
) -> CurationRecoveryCheckpoint:
    return CurationRecoveryCheckpoint(
        pr_number=generation.pr_number,
        generation_id=generation.generation_id,
        transaction_id=checkpoint.transaction_id,
        selected_head=generation.selected_head,
        checkpoint_head=checkpoint.reviewed_head,
        report_path=checkpoint.report_path,
        sync=generation.sync,
        checkpoint_ref=checkpoint.checkpoint_ref,
        squash_ref=checkpoint.squash_ref,
    )


def _continue_conflict_action(
    generation: CurationGeneration,
) -> CurationNextAction:
    return CurationNextAction(
        recipe_id=CurationRecipeId.PREPARE,
        substitutions=CurationActionSubstitutions(
            pr=generation.pr_number,
            generation_id=generation.generation_id,
            head=project_generation(generation).latest_head,
            validation_base=generation.sync.base_head,
            continue_conflict=True,
        ),
    )


def _validation_remediation_action(
    generation: CurationGeneration,
) -> CurationNextAction:
    projection = project_generation(generation)
    reviewed = projection.reviewed_authority
    if (
        projection.latest_stage != "validation-failed"
        or projection.validation_failure is None
        or reviewed is None
    ):
        raise CurationStateError("validation remediation lost reviewed authority")
    return CurationNextAction(
        recipe_id=CurationRecipeId.CHECKPOINT_DELTA,
        substitutions=CurationActionSubstitutions(
            pr=generation.pr_number,
            generation_id=generation.generation_id,
            head=reviewed.reviewed_head,
            report=reviewed.report_path,
            validation_base=generation.sync.base_head,
        ),
        caller_created_descendant_head=True,
    )


def _generation_result(
    generation: CurationGeneration,
    *,
    result: str,
    conflict_paths: Sequence[str] = (),
    next_action: CurationNextAction | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "generation_id": generation.generation_id,
        "generation_number": generation.generation_number,
        "selected_head": generation.selected_head,
        "base_head": generation.sync.base_head,
        "prepared_head": generation.sync.rebased_head,
        "result": result,
    }
    if conflict_paths:
        payload["conflict_paths"] = list(conflict_paths)
    if next_action is None:
        next_action = project_generation(generation).next_action
    if next_action is not None:
        payload["next_action"] = next_action.model_dump(
            mode="json",
            exclude_none=True,
        )
    validation_failure = project_generation(generation).validation_failure
    if validation_failure is not None:
        payload["validation_failure"] = validation_failure.model_dump(
            mode="json",
            exclude_none=True,
        )
    return payload


def _generation_event_time(
    generation: CurationGeneration,
    dependencies: Dependencies,
) -> datetime:
    return max(
        _current_time(dependencies),
        generation.events[-1].recorded_at + timedelta(microseconds=1),
    )


def _curation_checkpoint_refs(
    pr_number: int,
    generation_id: str,
    transaction_id: str,
) -> CurationCheckpointRefs:
    prefix = (
        f"refs/snowcast-maintainer/curation/pr-{pr_number}/"
        f"{generation_id}/{transaction_id}/"
    )
    return CurationCheckpointRefs(
        checkpoint_ref=f"{prefix}checkpoint",
        squash_ref=f"{prefix}replay",
    )


def handle_checkpoint_curation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    state_store = _state_store(args)
    generation_store = CurationGenerationStore(args.state_dir)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.VALIDATE
    if state_store.list_unresolved_pushes():
        raise StateStoreError("unresolved push journal blocks curation checkpoint")

    generation = generation_store.load_current(work_id)
    if generation is None or generation.generation_id != args.generation_id:
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)
    projection = project_generation(generation)
    if projection.latest_stage in {
        "fully-validated",
        "superseded",
        "invalidated",
        "consumed",
    }:
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)
    pull_request = dependencies.github.get_pull_request(args.pr)
    if (
        pull_request.head_sha != generation.selected_head
        or pull_request.head_sha != generation.sync.original_head
    ):
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    _require_exact_curation_candidate(pull_request, dependencies, state_store)
    work = _load_work_for_run(state_store, work_id, lease)
    if work.phase not in {WorkPhase.PREPARED, WorkPhase.REVIEWED}:
        raise StateStoreError("curation work is not prepared for checkpointing")
    if work.sync is None or work.sync != generation.sync:
        raise MaintainerError(ErrorReason.STALE_BASE, ErrorStage.VALIDATE)

    stage = CurationCheckpointStage(args.stage)
    if projection.latest_stage == "validation-failed":
        if projection.validation_failure is None:
            raise CurationStateError(
                "unclassified validation failure cannot authorize remediation"
            )
        if (
            stage is not CurationCheckpointStage.DELTA_VALIDATED
            or args.head == projection.latest_head
        ):
            raise MaintainerError(
                ErrorReason.CHECKPOINT_CONFLICT,
                ErrorStage.VALIDATE,
            )
        dependencies.repository.revalidate_validation_remediation_descendant(
            projection.latest_head,
            args.head,
        )
    transaction_id = checkpoint_transaction_id(
        generation.generation_id,
        stage,
        args.head,
        args.report,
        generation.sync.base_head,
    )
    expected_refs = _curation_checkpoint_refs(
        args.pr,
        generation.generation_id,
        transaction_id,
    )
    incomplete = projection.incomplete_transaction
    if incomplete is not None and incomplete != transaction_id:
        raise MaintainerError(
            ErrorReason.LOCAL_RECOVERY_REQUIRED,
            ErrorStage.VALIDATE,
            retryable=True,
            next_action=projection.next_action,
        )
    authority = projection.checkpoint_authority
    if authority is not None and authority.transaction_id == transaction_id:
        recovery = _generation_recovery(generation, authority)
        dependencies.repository.revalidate_curation_checkpoint(
            pull_request,
            recovery,
        )
        dependencies.tracker.last_phase = work.phase
        dependencies.tracker.terminal_reason = "already-completed"
        return {
            "work_id": work_id,
            "generation": _generation_result(
                generation,
                result="already-completed",
                next_action=projection.next_action,
            ),
        }
    if (
        stage is CurationCheckpointStage.REVIEWED
        and args.head != projection.latest_head
    ):
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)
    if dependencies.repository.current_head() != args.head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)

    snapshot = dependencies.repository.revalidate_prepared_result(
        pull_request,
        generation.sync,
        args.head,
    )
    try:
        require_single_curation_report_path(snapshot, args.report)
    except ValueError:
        raise MaintainerError(
            ErrorReason.CHECKPOINT_CONFLICT,
            ErrorStage.VALIDATE,
        ) from None
    base_repository = dependencies.base_repository or GitRepository(
        args.base_dir.resolve()
    )
    delta = dependencies.curation_delta_validator(
        pull_request=pull_request,
        sync=generation.sync,
        remediation_head=args.head,
        report_path=args.report,
        repository=dependencies.repository,
        base_repository=base_repository,
    )
    if delta.remediation_head != args.head:
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)

    if incomplete is None:
        generation = generation_store.append_event(
            work_id,
            generation.generation_id,
            CheckpointStartedEvent(
                sequence=len(generation.events) + 1,
                recorded_at=_generation_event_time(generation, dependencies),
                transaction_id=transaction_id,
                stage=stage,
                head=args.head,
                report_path=args.report,
                validation_base=generation.sync.base_head,
                expected_checkpoint_ref=expected_refs.checkpoint_ref,
                expected_squash_ref=expected_refs.squash_ref,
            ),
            lease,
        )
        dependencies.tracker.mutation_occurred = True

    refs = dependencies.repository.checkpoint_curation_generation(
        pull_request,
        generation.sync,
        args.head,
        generation.generation_id,
        transaction_id,
    )
    if refs != expected_refs:
        raise CurationStateError("curation checkpoint returned unexpected refs")
    generation = generation_store.append_event(
        work_id,
        generation.generation_id,
        CheckpointCompletedEvent(
            sequence=len(generation.events) + 1,
            recorded_at=_generation_event_time(generation, dependencies),
            transaction_id=transaction_id,
            checkpoint_ref=refs.checkpoint_ref,
            squash_ref=refs.squash_ref,
        ),
        lease,
    )
    dependencies.tracker.mutation_occurred = True
    if stage is CurationCheckpointStage.REVIEWED and work.phase is WorkPhase.PREPARED:
        work = _advance_work(
            state_store,
            lease,
            work,
            dependencies,
            WorkPhase.REVIEWED,
            reviewed_head=args.head,
        )
    dependencies.tracker.last_phase = work.phase
    dependencies.tracker.terminal_reason = "curation-checkpointed"
    return {
        "work_id": work_id,
        "generation": _generation_result(
            generation,
            result="completed",
            next_action=project_generation(generation).next_action,
        ),
    }


def _load_work_for_run(
    store: StateStore,
    work_id: str,
    lease: RunLease,
) -> WorkState:
    work = store.load_work(work_id)
    if work is None:
        raise StateStoreError("work state is missing")
    if work.worker != lease.worker or work.run_id != lease.run_id:
        raise LeaseOwnershipError("work state belongs to another run")
    return work


def _advance_work(
    store: StateStore,
    lease: RunLease,
    work: WorkState,
    dependencies: Dependencies,
    phase: WorkPhase,
    **updates: object,
) -> WorkState:
    advanced = work.model_copy(
        update={
            **updates,
            "phase": phase,
            "updated_at": _current_time(dependencies, work),
        }
    )
    store.save_work(advanced, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = phase
    return advanced


def _require_canonical_resulting_graph(
    work: WorkState | None,
    body: str | None,
    *,
    expected: str | None = None,
) -> None:
    if expected is None:
        expected = work.resulting_graph_markdown if work is not None else None
    if expected is None:
        return
    if body is None or expected.strip() not in body:
        raise PublicationInputError(
            "publication body must contain the canonical resulting graph"
        )


def handle_validate_curation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    generation_store = CurationGenerationStore(args.state_dir)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.VALIDATE
    work = _load_work_for_run(store, work_id, lease)
    pull_request = dependencies.github.get_pull_request(args.pr)
    generation = generation_store.load_current(work_id)
    if generation is None or generation.generation_id != args.generation_id:
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)
    projection = project_generation(generation)
    reviewed = projection.reviewed_authority
    checkpoint = projection.checkpoint_authority
    if (
        reviewed is None
        or checkpoint is None
        or reviewed.reviewed_head != args.head
        or reviewed.report_path != args.report
    ):
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)
    if projection.latest_stage == "validation-failed":
        failure = projection.validation_failure
        if failure is None:
            raise CurationStateError(
                "unclassified validation failure cannot authorize remediation"
            )
        raise MaintainerError(
            ErrorReason.VALIDATION_FAILED,
            ErrorStage.VALIDATE,
            ErrorCheck(failure.check),
            ErrorKind(failure.kind),
        )
    if pull_request.head_sha != work.selected_head or (
        pull_request.head_sha != generation.selected_head
    ):
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    if work.sync is None or work.sync != generation.sync:
        raise MaintainerError(ErrorReason.STALE_BASE, ErrorStage.VALIDATE)
    dependencies.repository.revalidate_curation_checkpoint(
        pull_request,
        _generation_recovery(generation, checkpoint),
    )
    base_repository = dependencies.base_repository or GitRepository(
        args.base_dir.resolve()
    )
    if projection.validated_authority is not None:
        if (
            work.phase is not WorkPhase.VALIDATED
            or work.reviewed_head != args.head
            or work.validated_head != args.head
            or work.report_path != args.report
        ):
            raise StateStoreError("validated curation request does not match")
        revalidate_curation_request(
            pull_request=pull_request,
            sync=generation.sync,
            reviewed_head=args.head,
            report_path=args.report,
            repository=dependencies.repository,
            base_repository=base_repository,
        )
        dependencies.tracker.last_phase = WorkPhase.VALIDATED
        dependencies.tracker.terminal_reason = "already_validated"
        return {
            "work_id": work_id,
            "validation": {
                "result": "already-validated",
                "validated_head": work.validated_head,
            },
        }
    if work.phase is not WorkPhase.REVIEWED:
        raise StateStoreError("curation work is not checkpointed for validation")
    if work.reviewed_head != args.head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    try:
        result = dependencies.curation_validator(
            pull_request=pull_request,
            sync=generation.sync,
            reviewed_head=args.head,
            report_path=args.report,
            repository=dependencies.repository,
            base_repository=base_repository,
        )
    except MaintainerError as error:
        if (
            error.reason is ErrorReason.VALIDATION_FAILED
            and error.check is not None
            and error.kind is not None
        ):
            failure = {
                "check": error.check.value,
                "kind": error.kind.value,
            }
            if error.diagnostic is not None:
                failure["diagnostic"] = error.diagnostic.model_dump(mode="json")
            generation_store.append_event(
                work_id,
                generation.generation_id,
                ValidationFailedEvent(
                    sequence=len(generation.events) + 1,
                    recorded_at=_generation_event_time(generation, dependencies),
                    head=args.head,
                    report_path=args.report,
                    failure=failure,
                ),
                lease,
            )
            dependencies.tracker.mutation_occurred = True
        raise
    if result.validated_head != args.head:
        raise MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, ErrorStage.VALIDATE)
    generation = generation_store.append_event(
        work_id,
        generation.generation_id,
        ValidationPassedEvent(
            sequence=len(generation.events) + 1,
            recorded_at=_generation_event_time(generation, dependencies),
            head=args.head,
            report_path=args.report,
            resulting_graph_markdown=result.resulting_graph_markdown,
        ),
        lease,
    )
    dependencies.tracker.mutation_occurred = True
    work = _advance_work(
        store,
        lease,
        work,
        dependencies,
        WorkPhase.VALIDATED,
        validated_head=result.validated_head,
        report_path=args.report,
        resulting_graph_markdown=result.resulting_graph_markdown,
    )
    dependencies.tracker.terminal_reason = "validated"
    return {
        "work_id": work_id,
        "validation": result.model_dump(mode="json"),
    }


def _require_candidate_available(
    candidate_key: str,
    inventory: DiscoveryInventory,
) -> None:
    if (
        candidate_key in inventory.catalog_keys
        or candidate_key in inventory.open_candidate_keys
    ):
        raise MaintainerError(
            ErrorReason.DUPLICATE_PROPOSAL,
            ErrorStage.VALIDATE,
            detail="Candidate already exists or is already proposed",
        )
    if (
        not inventory.can_create_proposal
        or inventory.open_proposal_count >= 3
        or inventory.has_unknown_proposal_identity
        or inventory.unresolved_pushes
    ):
        raise MaintainerError(
            ErrorReason.PROPOSAL_CAP,
            ErrorStage.VALIDATE,
            detail="Current proposal inventory blocks validation",
        )


def handle_validate_proposal(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "discovery", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_candidate(args.candidate_key)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.candidate_key = args.candidate_key
    dependencies.tracker.stage = ErrorStage.VALIDATE
    inventory = _discovery_inventory(
        dependencies,
        unresolved_pushes=store.list_unresolved_pushes(),
    )
    _require_candidate_available(args.candidate_key, inventory)
    selected = WorkState(
        work_id=work_id,
        worker="discovery",
        run_id=lease.run_id,
        phase=WorkPhase.SELECTED,
        updated_at=_current_time(dependencies, store.load_work(work_id)),
        candidate_key=args.candidate_key,
        candidate_origin=args.candidate_origin,
        selected_head=args.head,
    )
    store.begin_work(selected, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.SELECTED
    snapshot = dependencies.repository.verify_immutable_diff(args.base, args.head)
    result = dependencies.proposal_validator(
        candidate_key=args.candidate_key,
        candidate_origin=args.candidate_origin,
        base=args.base,
        head=args.head,
        snapshot=snapshot,
        discovery_inventory=inventory,
        repository=dependencies.repository,
    )
    prepared = _advance_work(
        store,
        lease,
        selected,
        dependencies,
        WorkPhase.PREPARED,
        prepared_head=args.head,
    )
    reviewed = _advance_work(
        store,
        lease,
        prepared,
        dependencies,
        WorkPhase.REVIEWED,
        reviewed_head=args.head,
    )
    _advance_work(
        store,
        lease,
        reviewed,
        dependencies,
        WorkPhase.VALIDATED,
        validated_head=result.validated_head,
        report_path=result.report_path,
        resulting_graph_markdown=result.resulting_graph_markdown,
    )
    dependencies.tracker.terminal_reason = "validated"
    return {"work_id": work_id, "validation": result.model_dump(mode="json")}


def _matching_curation_journal(
    work: WorkState,
    lease: RunLease,
    new_head: str,
    *,
    report_path: str | None = None,
    resulting_graph_markdown: str | None = None,
) -> PushJournal:
    if work.sync is None or work.pr_number is None:
        raise StateStoreError("prepared curation facts are incomplete")
    return PushJournal(
        work_id=work.work_id,
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=work.pr_number,
        branch=work.sync.target_branch,
        expected_remote_head=work.selected_head,
        new_head=new_head,
        report_path=report_path if report_path is not None else work.report_path,
        resulting_graph_markdown=(
            resulting_graph_markdown
            if resulting_graph_markdown is not None
            else work.resulting_graph_markdown
        ),
        phase=PushPhase.AUTHORIZED,
    )


def _ci_repair_checkpoint(continuation: CiContinuation) -> CiRepairCheckpoint:
    if (
        continuation.repair_head is None
        or continuation.repair_ref is None
        or not continuation.repair_paths
    ):
        raise StateStoreError("reviewed CI repair checkpoint is incomplete")
    return CiRepairCheckpoint(
        repair_head=continuation.repair_head,
        repair_ref=continuation.repair_ref,
        repair_paths=continuation.repair_paths,
        non_test_tree_digest=continuation.non_test_tree_digest,
    )


def _matching_ci_repair_journal(
    continuation: CiContinuation,
    lease: RunLease,
) -> PushJournal:
    checkpoint = _ci_repair_checkpoint(continuation)
    return PushJournal(
        work_id=continuation.work_id,
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=continuation.pr_number,
        branch=continuation.branch,
        expected_remote_head=continuation.current_head,
        new_head=checkpoint.repair_head,
        report_path=continuation.report_path,
        resulting_graph_markdown=continuation.resulting_graph_markdown,
        phase=PushPhase.AUTHORIZED,
    )


def _ci_repair_journal_matches(
    continuation: CiContinuation,
    journal: PushJournal,
) -> bool:
    if continuation.phase not in {
        CiContinuationPhase.REPAIR_REVIEWED,
        CiContinuationPhase.SECOND_WAIT,
    }:
        return False
    if not _ci_repair_journal_has_identity(continuation, journal):
        return False
    if continuation.phase is CiContinuationPhase.REPAIR_REVIEWED:
        return journal.phase in {PushPhase.AUTHORIZED, PushPhase.PUSHED}
    return journal.phase is PushPhase.PUSHED


def _ci_repair_journal_has_identity(
    continuation: CiContinuation,
    journal: PushJournal,
) -> bool:
    checkpoint = _ci_repair_checkpoint(continuation)
    if (
        journal.work_id != continuation.work_id
        or journal.worker != "curation"
        or journal.pr_number != continuation.pr_number
        or journal.branch != continuation.branch
        or journal.new_head != checkpoint.repair_head
        or journal.report_path != continuation.report_path
        or journal.resulting_graph_markdown != continuation.resulting_graph_markdown
    ):
        return False
    if continuation.phase is CiContinuationPhase.REPAIR_REVIEWED:
        return journal.expected_remote_head == continuation.current_head
    if continuation.phase is CiContinuationPhase.SECOND_WAIT:
        return (
            journal.expected_remote_head == continuation.semantic_head
            and journal.new_head == continuation.current_head
        )
    return False


def _require_no_nonconverged_ci_repair_publication(
    continuation: CiContinuation | None,
    journal: PushJournal | None,
) -> None:
    if (
        continuation is None
        or journal is None
        or continuation.phase
        not in {
            CiContinuationPhase.REPAIR_REVIEWED,
            CiContinuationPhase.SECOND_WAIT,
        }
        or not _ci_repair_journal_has_identity(continuation, journal)
    ):
        return
    if (
        continuation.phase is not CiContinuationPhase.SECOND_WAIT
        or journal.phase is not PushPhase.PUBLISHED
    ):
        raise StateStoreError("non-converged CI repair journal requires exact recovery")


def _revalidate_ci_repair_for_journal(
    continuation: CiContinuation,
    journal: PushJournal,
    dependencies: Dependencies,
) -> None:
    checkpoint = _ci_repair_checkpoint(continuation)
    if not _ci_repair_journal_matches(continuation, journal):
        raise StateStoreError("repair push journal does not match the CI continuation")
    pull_request = dependencies.github.get_pull_request(continuation.pr_number)
    if pull_request.head_ref_name != continuation.branch or (
        continuation.phase is CiContinuationPhase.SECOND_WAIT
        and pull_request.head_sha != continuation.current_head
    ):
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUSH)
    revalidated = dependencies.repository.revalidate_ci_repair_checkpoint(
        pull_request=pull_request,
        semantic_head=continuation.semantic_head,
        current_head=journal.expected_remote_head,
        checkpoint=checkpoint,
    )
    if revalidated != checkpoint:
        raise RepositorySafetyError(
            "revalidated CI repair checkpoint changed immutable evidence"
        )


def _preflight_new_ci_repair_push(
    continuation: CiContinuation,
    journal: PushJournal,
    dependencies: Dependencies,
) -> None:
    checkpoint = _ci_repair_checkpoint(continuation)
    if (
        continuation.phase is not CiContinuationPhase.REPAIR_REVIEWED
        or not _ci_repair_journal_matches(continuation, journal)
    ):
        raise StateStoreError("repair push journal does not match the CI continuation")
    pull_request = dependencies.github.get_pull_request(continuation.pr_number)
    _live_ci_repair_pull_request(
        continuation=continuation,
        pull_request=pull_request,
        stage=ErrorStage.PUSH,
        require_failed_checks=False,
    )
    remote_head = dependencies.repository.optional_remote_head(continuation.branch)
    if remote_head != continuation.current_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUSH)
    revalidated = dependencies.repository.revalidate_ci_repair_checkpoint(
        pull_request=pull_request,
        semantic_head=continuation.semantic_head,
        current_head=continuation.current_head,
        checkpoint=checkpoint,
    )
    if revalidated != checkpoint:
        raise RepositorySafetyError(
            "revalidated CI repair checkpoint changed immutable evidence"
        )


def _advance_curation_push(
    store: StateStore,
    lease: RunLease,
    journal: PushJournal,
    work: WorkState | None,
    dependencies: Dependencies,
    *,
    ci_continuation: CiContinuation | None = None,
    strict_new_ci_repair_push: bool = False,
) -> PushJournal:
    if ci_continuation is not None:
        if strict_new_ci_repair_push:
            _preflight_new_ci_repair_push(
                ci_continuation,
                journal,
                dependencies,
            )
        else:
            _revalidate_ci_repair_for_journal(
                ci_continuation,
                journal,
                dependencies,
            )
    remote_head = dependencies.repository.optional_remote_head(journal.branch)
    if journal.phase is PushPhase.AUTHORIZED:
        if remote_head == journal.expected_remote_head:
            if ci_continuation is not None:
                with store.guard_push_mutation(journal, lease):
                    dependencies.repository.push_exact_with_lease(
                        journal.branch,
                        journal.expected_remote_head,
                        journal.new_head,
                    )
            else:
                if work is None or work.sync is None:
                    raise StateStoreError(
                        "curation recovery requires prepared work state"
                    )
                authorized_heads = {work.reviewed_head, work.validated_head}
                if journal.new_head not in authorized_heads:
                    raise StateStoreError(
                        "push journal head lacks reviewed work evidence"
                    )
                if journal.new_head != journal.expected_remote_head:
                    with store.guard_push_mutation(journal, lease):
                        dependencies.repository.push_with_lease(
                            work.sync,
                            journal.new_head,
                        )
        elif remote_head != journal.new_head:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUSH)
        journal = journal.model_copy(update={"phase": PushPhase.PUSHED})
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
    return journal


def _consume_generation_for_journal(
    *,
    generation_store: CurationGenerationStore,
    lease: RunLease,
    work: WorkState,
    expected_head: str,
    dependencies: Dependencies,
    require_validated: bool,
) -> None:
    generation = generation_store.load_current(work.work_id)
    if generation is None:
        raise StateStoreError("matching curation generation is required")
    projection = project_generation(generation)
    authority = (
        projection.validated_authority
        if require_validated
        else projection.reviewed_authority
    )
    if (
        authority is None
        or authority.selected_head != work.selected_head
        or authority.reviewed_head != expected_head
        or authority.sync != work.sync
        or (not require_validated and projection.validated_authority is not None)
    ):
        raise StateStoreError("matching curation generation authority is required")
    _close_generation(
        generation_store,
        generation,
        lease,
        dependencies,
        kind="generation-consumed",
        reason="external_journal_authorized",
    )


def handle_publish_push(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    generation_store = CurationGenerationStore(args.state_dir)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PUSH
    work = _load_work_for_run(store, work_id, lease)
    if work.phase is not WorkPhase.VALIDATED:
        raise StateStoreError("curation work is not validated")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != work.selected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PRE_PUSH)
    assert work.validated_head is not None
    store.require_ci_generation_eligible(
        work_id,
        work.validated_head,
        lease,
    )
    journal = store.load_push(work_id)
    if journal is None or journal.phase is PushPhase.PUBLISHED:
        journal = _matching_curation_journal(work, lease, work.validated_head)
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
        _consume_generation_for_journal(
            generation_store=generation_store,
            lease=lease,
            work=work,
            expected_head=work.validated_head,
            dependencies=dependencies,
            require_validated=True,
        )
    elif journal.recovery_run_id != lease.run_id:
        raise LeaseOwnershipError("push journal belongs to another run")
    journal = _advance_curation_push(store, lease, journal, work, dependencies)
    work = _advance_work(
        store,
        lease,
        work,
        dependencies,
        WorkPhase.PUSHED,
    )
    dependencies.tracker.terminal_reason = "pushed"
    return {"work_id": work_id, "push": journal.model_dump(mode="json")}


def handle_publish_manual_check(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    generation_store = CurationGenerationStore(args.state_dir)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PRE_PUSH

    # Validate all caller-controlled publication input before any external mutation.
    summary = read_publication_text(
        args.state_dir,
        args.summary_file,
        kind="summary",
    )
    body = (
        read_publication_text(args.state_dir, args.body_file, kind="body")
        if args.body_file is not None
        else None
    )
    try:
        resulting_graph_markdown = immutable_resulting_graph_markdown(
            dependencies.repository,
            args.reviewed_head,
            args.report,
        )
    except MaintainerError:
        raise
    except Exception:
        raise PublicationInputError(
            "manual-check report must contain a reproducible resulting graph"
        ) from None
    _require_canonical_resulting_graph(
        None,
        body,
        expected=resulting_graph_markdown,
    )

    work = store.load_work(work_id)
    journal = store.load_push(work_id)
    journal_matches_request = (
        journal is not None
        and journal.worker == "curation"
        and journal.recovery_run_id == lease.run_id
        and journal.pr_number == args.pr
        and journal.new_head == args.reviewed_head
        and journal.report_path == args.report
        and journal.resulting_graph_markdown == resulting_graph_markdown
        and journal.phase
        in {PushPhase.AUTHORIZED, PushPhase.PUSHED, PushPhase.PUBLISHED}
    )

    if not journal_matches_request:
        work = _load_work_for_run(store, work_id, lease)
        if (
            work.phase is not WorkPhase.REVIEWED
            or work.sync is None
            or work.validated_head is not None
            or work.reviewed_head != args.reviewed_head
        ):
            raise StateStoreError("manual-check publication requires reviewed work")
        generation = generation_store.load_current(work_id)
        projection = project_generation(generation) if generation is not None else None
        reviewed = projection.reviewed_authority if projection is not None else None
        checkpoint = projection.checkpoint_authority if projection is not None else None
        if (
            generation is None
            or reviewed is None
            or checkpoint is None
            or projection is None
            or projection.validated_authority is not None
            or reviewed.selected_head != work.selected_head
            or reviewed.reviewed_head != args.reviewed_head
            or reviewed.sync != work.sync
        ):
            raise StateStoreError(
                "manual-check publication requires exact reviewed generation"
            )
        if reviewed.report_path != args.report:
            raise PublicationInputError(
                "manual-check report must match the reviewed checkpoint"
            )
        pull_request = dependencies.github.get_pull_request(args.pr)
        if pull_request.head_sha != work.selected_head:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PRE_PUSH)
        dependencies.repository.revalidate_curation_checkpoint(
            pull_request,
            _generation_recovery(generation, checkpoint),
        )
        snapshot = dependencies.repository.revalidate_prepared_result(
            pull_request,
            work.sync,
            args.reviewed_head,
        )
        try:
            require_single_curation_report_path(snapshot, args.report)
        except ValueError:
            raise PublicationInputError(
                "manual-check report must be the single changed curation report"
            ) from None
        journal = _matching_curation_journal(
            work,
            lease,
            args.reviewed_head,
            report_path=args.report,
            resulting_graph_markdown=resulting_graph_markdown,
        )
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
        _consume_generation_for_journal(
            generation_store=generation_store,
            lease=lease,
            work=work,
            expected_head=args.reviewed_head,
            dependencies=dependencies,
            require_validated=False,
        )
    elif journal is None:
        raise StateStoreError("matching push journal is missing")

    journal = _advance_curation_push(store, lease, journal, work, dependencies)
    dependencies.tracker.stage = ErrorStage.PUBLISH
    state_args = argparse.Namespace(
        **vars(args),
        state=MaintainerState.MANUAL_CHECK.value,
        _trusted_summary=summary,
        _trusted_body=body,
    )
    result = handle_publish_state(state_args, dependencies)
    dependencies.tracker.terminal_reason = "manual-check"
    return {"work_id": work_id, **result}


def _terminal_publication_payload(
    intent: TerminalPublicationIntent,
) -> dict[str, object]:
    return {
        "work_id": intent.work_id,
        "pr_number": intent.continuation.pr_number,
        "state": intent.target_state.value,
        "reason": intent.reason,
        "phase": intent.phase.value,
    }


def _require_matching_terminal_publication_request(
    intent: TerminalPublicationIntent,
    *,
    work_id: str,
    pr_number: int,
    expected_head: str,
    requested_state: MaintainerState,
    reason: str,
    summary: str,
) -> None:
    if (
        intent.work_id != work_id
        or intent.continuation.pr_number != pr_number
        or intent.continuation.current_head != expected_head
        or intent.target_state is not requested_state
        or intent.reason != reason
        or intent.summary != summary
    ):
        raise StateStoreError(
            "terminal publication retry does not match exact authority"
        )


def _replay_terminal_publication(
    *,
    store: StateStore,
    lease: RunLease,
    intent: TerminalPublicationIntent,
    dependencies: Dependencies,
) -> TerminalPublicationIntent:
    if (
        intent.phase is not TerminalPublicationPhase.AUTHORIZED
        or intent.recovery_run_id != lease.run_id
    ):
        raise StateStoreError("terminal publication is not owned recovery authority")
    continuation = intent.continuation
    pull_request = dependencies.github.get_pull_request(continuation.pr_number)
    if (
        pull_request.head_ref_name != continuation.branch
        or pull_request.head_sha != continuation.current_head
    ):
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUBLISH)
    plan = outcome_plan(
        requested_state=intent.target_state,
        reason=intent.reason,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=pull_request,
        existing_machine_state=intent.machine_state,
    )
    if plan.machine_state != intent.machine_state:
        raise StateStoreError("terminal publication machine evidence changed")

    def mutation_guard() -> AbstractContextManager[None]:
        return store.guard_terminal_publication_mutation(intent, lease)

    mutated = publish_outcome(
        dependencies.github,
        pull_request,
        plan,
        intent.summary,
        allow_comment_repair=True,
        mutation_guard=mutation_guard,
        validate_mutation=lambda _step, _current: lease.assert_owner(),
    )
    completed, _blocked = store.complete_terminal_publication(
        intent,
        lease,
        now=_current_time(dependencies, intent.continuation),
    )
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.terminal_reason = (
        "outcome-blocked" if mutated else "outcome-blocked-recovered"
    )
    return completed


def handle_publish_recover(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    store = _state_store(args)
    terminal_publications = store.list_unresolved_terminal_publications()
    if terminal_publications:
        if (
            len(terminal_publications) != 1
            or terminal_publications[0].work_id != args.work_id
        ):
            raise MaintainerError(
                ErrorReason.INVALID_COMMAND,
                ErrorStage.PUBLISH,
                detail=("Recovery requires exactly one matching terminal publication"),
            )
        intent = terminal_publications[0]
        lease = _owned_lease(args, "curation", dependencies)
        dependencies.tracker.work_id = intent.work_id
        dependencies.tracker.pr_number = intent.continuation.pr_number
        dependencies.tracker.stage = ErrorStage.PUBLISH
        if intent.recovery_run_id != lease.run_id:
            intent = store.adopt_terminal_publication(
                intent.work_id,
                lease,
                now=dependencies.now(),
            )
            dependencies.tracker.mutation_occurred = True
        completed = _replay_terminal_publication(
            store=store,
            lease=lease,
            intent=intent,
            dependencies=dependencies,
        )
        return {
            "work_id": completed.work_id,
            "terminal_publication": _terminal_publication_payload(completed),
        }

    unresolved = store.list_unresolved_pushes()
    if len(unresolved) != 1 or unresolved[0].work_id != args.work_id:
        raise MaintainerError(
            ErrorReason.INVALID_COMMAND,
            ErrorStage.PRE_PUSH,
            detail="Recovery requires exactly one matching push journal",
        )
    journal = unresolved[0]
    worker: Worker = journal.worker
    lease = _owned_lease(args, worker, dependencies)
    dependencies.tracker.work_id = journal.work_id
    dependencies.tracker.pr_number = journal.pr_number
    dependencies.tracker.candidate_key = journal.candidate_key
    dependencies.tracker.stage = ErrorStage.PUSH
    remote_head = dependencies.repository.optional_remote_head(journal.branch)
    if remote_head not in {journal.expected_remote_head, journal.new_head}:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUSH)
    if journal.recovery_run_id != lease.run_id:
        journal = store.adopt_push(journal.work_id, lease, remote_head)
        dependencies.tracker.mutation_occurred = True

    work = store.load_work(journal.work_id)
    recovered_ci_continuation: CiContinuation | None = None
    if journal.worker == "curation":
        ci_continuation = store.load_ci_continuation(journal.work_id)
        repair_recovery = ci_continuation is not None and _ci_repair_journal_matches(
            ci_continuation, journal
        )
        journal = _advance_curation_push(
            store,
            lease,
            journal,
            None if repair_recovery else work,
            dependencies,
            ci_continuation=ci_continuation if repair_recovery else None,
        )
        if repair_recovery and ci_continuation is not None:
            journal, recovered_ci_continuation = _complete_ci_repair_push(
                store=store,
                lease=lease,
                journal=journal,
                continuation=ci_continuation,
                dependencies=dependencies,
            )
        if (
            work is not None
            and work.run_id == lease.run_id
            and work.phase is WorkPhase.VALIDATED
        ):
            _advance_work(
                store,
                lease,
                work,
                dependencies,
                WorkPhase.PUSHED,
            )
    else:
        if journal.phase is PushPhase.AUTHORIZED:
            if remote_head is None:
                with store.guard_push_mutation(journal, lease):
                    dependencies.repository.push_create_only(
                        journal.branch,
                        journal.new_head,
                    )
                dependencies.tracker.mutation_occurred = True
            elif remote_head != journal.new_head:
                raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUSH)
            journal = journal.model_copy(update={"phase": PushPhase.PUSHED})
            store.save_push(journal, lease)
        if journal.phase is PushPhase.PUSHED:
            matches = dependencies.github.find_pull_requests_by_head(
                journal.branch,
                journal.new_head,
            )
            if len(matches) > 1:
                raise MaintainerError(
                    ErrorReason.INVALID_GITHUB_STATE,
                    ErrorStage.PROPOSAL_CREATE,
                )
            if matches:
                journal = journal.model_copy(
                    update={
                        "phase": PushPhase.PR_CREATED,
                        "pr_number": matches[0].number,
                    }
                )
                store.save_push(journal, lease)
                dependencies.tracker.mutation_occurred = True
    dependencies.tracker.terminal_reason = (
        "publication-input-required"
        if journal.worker == "discovery"
        and journal.phase in {PushPhase.PUSHED, PushPhase.PR_CREATED}
        else "recovered"
    )
    result: dict[str, object] = {
        "work_id": journal.work_id,
        "push": journal.model_dump(mode="json"),
    }
    if journal.worker == "curation":
        if recovered_ci_continuation is not None:
            result["continuation"] = recovered_ci_continuation.model_dump(mode="json")
        else:
            validation_status: Literal[
                "absent",
                "unknown",
                "validated",
            ] = "unknown"
            if work is not None and work.reviewed_head == journal.new_head:
                validation_status = (
                    "validated"
                    if work.validated_head == journal.new_head
                    else "absent"
                    if work.validated_head is None
                    else "unknown"
                )
            result["continuation"] = {
                "reviewed_head": journal.new_head,
                "validation_status": validation_status,
            }
    return result


def handle_publish_proposal(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "discovery", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_candidate(args.candidate_key)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.candidate_key = args.candidate_key
    dependencies.tracker.stage = ErrorStage.PRE_PUSH
    title = read_publication_text(args.state_dir, args.title_file, kind="title")
    body = read_publication_text(args.state_dir, args.body_file, kind="body")
    summary = read_publication_text(args.state_dir, args.summary_file, kind="summary")
    work = store.load_work(work_id)
    journal = store.load_push(work_id)
    journal_matches_run = (
        journal is not None
        and journal.recovery_run_id == lease.run_id
        and journal.candidate_key == args.candidate_key
        and journal.candidate_origin == args.candidate_origin
        and journal.new_head == args.head
    )
    work_matches_request = (
        work is not None
        and work.worker == "discovery"
        and work.phase is WorkPhase.VALIDATED
        and work.candidate_key == args.candidate_key
        and work.candidate_origin == args.candidate_origin
        and work.validated_head == args.head
        and work.report_path is not None
    )
    if work_matches_request and (work.run_id == lease.run_id or journal_matches_run):
        assert work is not None and work.report_path is not None
        report_path = work.report_path
        resulting_graph_markdown = work.resulting_graph_markdown
    elif journal_matches_run:
        report_path = journal.report_path
        resulting_graph_markdown = journal.resulting_graph_markdown
    else:
        raise StateStoreError("validated proposal evidence is missing")
    if report_path is None or resulting_graph_markdown is None:
        raise StateStoreError("validated proposal graph evidence is missing")
    _require_canonical_resulting_graph(
        None,
        body,
        expected=resulting_graph_markdown,
    )
    validation = ProposalValidationResult(
        candidate_key=args.candidate_key,
        candidate_origin=args.candidate_origin,
        validated_head=args.head,
        report_path=report_path,
        resulting_graph_markdown=resulting_graph_markdown,
    )
    journal_before = journal
    journal = publish_discovery_proposal(
        store=store,
        lease=lease,
        repository=dependencies.repository,
        github=dependencies.github,
        work_id=work_id,
        branch=args.branch,
        proposal_validation=validation,
        inventory_provider=lambda: _discovery_inventory(
            dependencies,
        ),
        title=title,
        initial_body=body,
        managed_body=body,
        summary=summary,
    )
    dependencies.tracker.mutation_occurred = journal != journal_before
    dependencies.tracker.pr_number = journal.pr_number
    if (
        work is not None
        and work.run_id == lease.run_id
        and work.phase is WorkPhase.VALIDATED
    ):
        pushed = _advance_work(
            store,
            lease,
            work,
            dependencies,
            WorkPhase.PUSHED,
        )
        _advance_work(
            store,
            lease,
            pushed,
            dependencies,
            WorkPhase.PUBLISHED,
            pr_number=journal.pr_number,
        )
    dependencies.tracker.terminal_reason = (
        "proposal-published"
        if dependencies.tracker.mutation_occurred
        else "proposal-unchanged"
    )
    return {"work_id": work_id, "pr_number": journal.pr_number}


def _requested_state(value: str) -> MaintainerState:
    normalized = value.removeprefix("maintainer:").replace("_", "-")
    try:
        return MaintainerState(f"maintainer:{normalized}")
    except ValueError:
        raise CLIInputError("requested state is not allowlisted") from None


@contextmanager
def _lease_mutation_guard(lease: RunLease) -> Iterator[None]:
    lease.assert_owner()
    yield
    lease.assert_owner()


def _pull_request_after_exact_push(
    *,
    pr_number: int,
    reviewed_head: str,
    journal: PushJournal | None,
    dependencies: Dependencies,
) -> PullRequest:
    pull_request = dependencies.github.get_pull_request(pr_number)
    matching_journal = (
        journal is not None
        and journal.worker == "curation"
        and journal.phase in {PushPhase.PUSHED, PushPhase.PUBLISHED}
        and journal.pr_number == pr_number
        and journal.new_head == reviewed_head
    )
    if matching_journal and journal is not None:
        if pull_request.head_ref_name != journal.branch:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
        if (
            dependencies.repository.optional_remote_head(journal.branch)
            != reviewed_head
        ):
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
    if pull_request.head_sha == reviewed_head:
        return pull_request
    if (
        not matching_journal
        or journal is None
        or journal.phase is not PushPhase.PUSHED
        or pull_request.head_sha != journal.expected_remote_head
    ):
        return pull_request
    for _attempt in range(_PR_HEAD_CONVERGENCE_ATTEMPTS):
        sleep(_PR_HEAD_CONVERGENCE_DELAY_SECONDS)
        pull_request = dependencies.github.get_pull_request(pr_number)
        if pull_request.head_ref_name != journal.branch:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
        if (
            dependencies.repository.optional_remote_head(journal.branch)
            != reviewed_head
        ):
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
        if pull_request.head_sha == reviewed_head:
            return pull_request
        if pull_request.head_sha != journal.expected_remote_head:
            return pull_request
    return pull_request


def _ensure_initial_ci_continuation(
    *,
    store: StateStore,
    lease: RunLease,
    work: WorkState | None,
    journal: PushJournal,
    reviewed_head: str,
    dependencies: Dependencies,
) -> CiContinuation:
    if (
        work is None
        or work.worker != "curation"
        or work.work_id != journal.work_id
        or work.run_id != journal.origin_run_id
        or work.phase is not WorkPhase.PUSHED
        or work.pr_number != journal.pr_number
        or work.validated_head != reviewed_head
        or work.report_path is None
        or work.resulting_graph_markdown is None
        or journal.recovery_run_id != lease.run_id
        or journal.phase is not PushPhase.PUSHED
        or journal.new_head != reviewed_head
        or journal.report_path != work.report_path
        or journal.resulting_graph_markdown != work.resulting_graph_markdown
    ):
        raise StateStoreError(
            "waiting-CI handoff requires matching validated work and push evidence"
        )
    non_test_tree_digest = dependencies.repository.non_test_tree_digest(reviewed_head)
    existing = store.load_ci_continuation(work.work_id)
    if existing is not None and existing.phase not in {
        CiContinuationPhase.CONSUMED,
        CiContinuationPhase.BLOCKED,
        CiContinuationPhase.INVALIDATED,
    }:
        expected_facts = {
            "work_id": work.work_id,
            "pr_number": journal.pr_number,
            "branch": journal.branch,
            "semantic_head": reviewed_head,
            "current_head": reviewed_head,
            "report_path": work.report_path,
            "resulting_graph_markdown": work.resulting_graph_markdown,
            "non_test_tree_digest": non_test_tree_digest,
            "phase": CiContinuationPhase.INITIAL_WAIT,
            "repair_attempted": False,
            "first_wait_seconds": 0,
            "repair_active_seconds": 0,
            "repair_activity_observed_at": None,
            "repair_head": None,
            "repair_ref": None,
            "repair_paths": frozenset(),
            "second_wait_started_at": None,
            "second_wait_seconds": 0,
        }
        if (
            any(
                getattr(existing, field_name) != expected
                for field_name, expected in expected_facts.items()
            )
            or existing.origin_run_id != existing.recovery_run_id
        ):
            raise StateStoreError(
                "existing CI continuation conflicts with push handoff"
            )
        return existing

    observed_at = _current_time(dependencies, existing)
    continuation = CiContinuation(
        work_id=work.work_id,
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=observed_at,
        pr_number=journal.pr_number,
        branch=journal.branch,
        semantic_head=reviewed_head,
        current_head=reviewed_head,
        report_path=work.report_path,
        resulting_graph_markdown=work.resulting_graph_markdown,
        non_test_tree_digest=non_test_tree_digest,
        phase=CiContinuationPhase.INITIAL_WAIT,
        repair_attempted=False,
        first_wait_started_at=observed_at,
        first_wait_seconds=0,
        repair_active_seconds=0,
        second_wait_seconds=0,
    )
    store.save_ci_continuation(continuation, lease)
    return continuation


def _require_clear_ci_repair_journal(store: StateStore) -> None:
    if store.list_unresolved_terminal_publications():
        raise StateStoreError(
            "unresolved terminal publication requires exact recovery before CI repair"
        )
    if store.list_unresolved_pushes():
        raise StateStoreError(
            "unresolved push journal requires exact recovery before CI repair"
        )


def _live_ci_repair_pull_request(
    *,
    continuation: CiContinuation,
    pull_request: PullRequest,
    stage: ErrorStage,
    require_failed_checks: bool,
) -> tuple[CheckSummary, ...]:
    if (
        pull_request.lifecycle_state != "OPEN"
        or pull_request.is_cross_repository
        or pull_request.base_ref_name != "main"
        or pull_request.head_repository_owner != "lampssy"
        or pull_request.head_ref_name != continuation.branch
        or pull_request.mergeable != "MERGEABLE"
    ):
        raise MaintainerError(
            ErrorReason.INVALID_GITHUB_STATE,
            stage,
        )
    if pull_request.head_sha != continuation.current_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, stage)
    failed_checks = tuple(
        check for check in pull_request.checks if is_confirmed_ci_failure(check)
    )
    if require_failed_checks and (
        pull_request.check_state != "failure" or not failed_checks
    ):
        raise MaintainerError(
            ErrorReason.INVALID_GITHUB_STATE,
            stage,
        )
    return failed_checks


def handle_invalidate_ci_continuation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.INSPECT
    _require_clear_ci_repair_journal(store)
    continuation = store.load_ci_continuation(work_id)
    if continuation is None or continuation.phase in {
        CiContinuationPhase.CONSUMED,
        CiContinuationPhase.BLOCKED,
        CiContinuationPhase.INVALIDATED,
    }:
        raise StateStoreError("active CI continuation is required")
    pull_request = dependencies.github.get_pull_request(args.pr)
    availability_reason = ci_continuation_invalidation_reason(
        continuation,
        pull_request,
    )
    if availability_reason is None:
        raise StateStoreError(
            "live CI facts do not authorize continuation invalidation"
        )
    if continuation.recovery_run_id != lease.run_id:
        continuation = store.adopt_ci_continuation(
            work_id,
            lease,
            now=dependencies.now(),
        )
        dependencies.tracker.mutation_occurred = True
    if continuation.phase is CiContinuationPhase.REPAIR_ACTIVE:
        continuation = store.record_ci_heartbeat(
            work_id,
            lease,
            now=dependencies.now(),
        )
    invalidated = continuation.model_copy(
        update={"phase": CiContinuationPhase.INVALIDATED}
    )
    invalidated = store.advance_ci_continuation(
        invalidated,
        lease,
        now=_current_time(dependencies, continuation),
    )
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.terminal_reason = f"ci-continuation-{availability_reason}"
    return {
        "work_id": work_id,
        "pr_number": args.pr,
        "phase": invalidated.phase.value,
        "availability_reason": availability_reason,
        "continuation_head": invalidated.current_head,
        "observed_head": pull_request.head_sha,
    }


def handle_prepare_ci_repair(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PREPARE
    _require_clear_ci_repair_journal(store)
    continuation = store.load_ci_continuation(work_id)
    if continuation is None:
        raise StateStoreError("matching CI continuation is missing")
    if continuation.phase not in {
        CiContinuationPhase.INITIAL_WAIT,
        CiContinuationPhase.REPAIR_ACTIVE,
        CiContinuationPhase.REPAIR_REVIEWED,
    }:
        raise StateStoreError("CI repair attempt is unavailable")
    needs_adoption = continuation.recovery_run_id != lease.run_id
    successor_recovery = continuation.origin_run_id != lease.run_id
    if (
        continuation.phase
        in {
            CiContinuationPhase.REPAIR_ACTIVE,
            CiContinuationPhase.REPAIR_REVIEWED,
        }
        and not successor_recovery
    ):
        raise StateStoreError("CI repair attempt is already owned by this run")

    pull_request = dependencies.github.get_pull_request(args.pr)
    failed_checks = _live_ci_repair_pull_request(
        continuation=continuation,
        pull_request=pull_request,
        stage=ErrorStage.PREPARE,
        require_failed_checks=(
            continuation.phase is not CiContinuationPhase.REPAIR_REVIEWED
        ),
    )
    if continuation.phase is CiContinuationPhase.REPAIR_REVIEWED:
        checkpoint = _ci_repair_checkpoint(continuation)
        revalidated = dependencies.repository.revalidate_ci_repair_checkpoint(
            pull_request=pull_request,
            semantic_head=continuation.semantic_head,
            current_head=continuation.current_head,
            checkpoint=checkpoint,
        )
        if revalidated != checkpoint:
            raise RepositorySafetyError(
                "revalidated CI repair checkpoint changed immutable evidence"
            )
    else:
        if (
            continuation.phase is CiContinuationPhase.REPAIR_ACTIVE
            and continuation.repair_active_seconds >= 3600
        ):
            raise StateStoreError("CI repair active budget is exhausted")
        prepared_head = dependencies.repository.prepare_ci_repair(pull_request)
        if prepared_head != continuation.current_head:
            raise RepositorySafetyError(
                "prepared CI repair head does not match the continuation"
            )

    if needs_adoption:
        continuation = store.adopt_ci_continuation(
            work_id,
            lease,
            now=dependencies.now(),
        )
        dependencies.tracker.mutation_occurred = True

    if continuation.phase is CiContinuationPhase.REPAIR_REVIEWED:
        dependencies.tracker.terminal_reason = "ci-repair-reviewed-resumed"
        return {
            "work_id": work_id,
            "phase": continuation.phase.value,
            "resumed": successor_recovery,
            "repair_head": continuation.repair_head,
            "repair_ref": continuation.repair_ref,
            "repair_paths": sorted(continuation.repair_paths),
            "remaining_repair_seconds": 3600 - continuation.repair_active_seconds,
        }

    if continuation.phase is CiContinuationPhase.REPAIR_ACTIVE:
        continuation = store.record_ci_heartbeat(
            work_id,
            lease,
            now=dependencies.now(),
        )
        dependencies.tracker.mutation_occurred = True
        if continuation.repair_active_seconds >= 3600:
            raise StateStoreError("CI repair active budget is exhausted")

    if continuation.phase is CiContinuationPhase.INITIAL_WAIT:
        observed_at = _current_time(dependencies, continuation)
        active = continuation.model_copy(
            update={
                "phase": CiContinuationPhase.REPAIR_ACTIVE,
                "repair_attempted": True,
                "repair_activity_observed_at": observed_at,
            }
        )
        active = store.advance_ci_continuation(active, lease, now=observed_at)
        dependencies.tracker.mutation_occurred = True
        dependencies.tracker.terminal_reason = "ci-repair-prepared"
    else:
        active = continuation
        dependencies.tracker.terminal_reason = "ci-repair-active-resumed"
    return {
        "work_id": work_id,
        "phase": active.phase.value,
        "resumed": (
            successor_recovery
            and continuation.phase is CiContinuationPhase.REPAIR_ACTIVE
        ),
        "current_head": active.current_head,
        "failed_checks": [check.model_dump(mode="json") for check in failed_checks],
        "remaining_repair_seconds": 3600 - active.repair_active_seconds,
        "permitted_path_pattern": "tests/test_*.py",
    }


def handle_checkpoint_ci_repair(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.VALIDATE
    _require_clear_ci_repair_journal(store)
    continuation = store.load_ci_continuation(work_id)
    if (
        continuation is None
        or continuation.recovery_run_id != lease.run_id
        or continuation.phase is not CiContinuationPhase.REPAIR_ACTIVE
        or not continuation.repair_attempted
    ):
        raise StateStoreError("active owned CI repair is required")
    continuation = store.record_ci_heartbeat(
        work_id,
        lease,
        now=dependencies.now(),
    )
    if continuation.repair_active_seconds >= 3600:
        raise StateStoreError("CI repair active budget is exhausted")

    pull_request = dependencies.github.get_pull_request(args.pr)
    if (
        pull_request.lifecycle_state != "OPEN"
        or pull_request.head_ref_name != continuation.branch
    ):
        raise MaintainerError(
            ErrorReason.INVALID_GITHUB_STATE,
            ErrorStage.VALIDATE,
        )
    if pull_request.head_sha != continuation.current_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    checkpoint: CiRepairCheckpoint = dependencies.repository.checkpoint_ci_repair(
        pull_request=pull_request,
        semantic_head=continuation.semantic_head,
        current_head=continuation.current_head,
        repair_head=args.head,
        expected_non_test_tree_digest=continuation.non_test_tree_digest,
    )
    if (
        checkpoint.repair_head != args.head
        or checkpoint.non_test_tree_digest != continuation.non_test_tree_digest
    ):
        raise RepositorySafetyError(
            "CI repair checkpoint does not match continuation evidence"
        )
    observed_at = _current_time(dependencies, continuation)
    reviewed = continuation.model_copy(
        update={
            "phase": CiContinuationPhase.REPAIR_REVIEWED,
            "repair_head": checkpoint.repair_head,
            "repair_ref": checkpoint.repair_ref,
            "repair_paths": checkpoint.repair_paths,
        }
    )
    reviewed = store.advance_ci_continuation(
        reviewed,
        lease,
        now=observed_at,
    )
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.terminal_reason = "ci-repair-reviewed"
    return {
        "work_id": work_id,
        "repair_head": reviewed.repair_head,
        "repair_ref": reviewed.repair_ref,
        "repair_paths": sorted(reviewed.repair_paths),
    }


def _complete_ci_repair_push(
    *,
    store: StateStore,
    lease: RunLease,
    journal: PushJournal,
    continuation: CiContinuation,
    dependencies: Dependencies,
) -> tuple[PushJournal, CiContinuation]:
    if journal.phase is not PushPhase.PUSHED:
        raise StateStoreError("CI repair journal has not reached pushed phase")
    if continuation.recovery_run_id != lease.run_id:
        continuation = store.adopt_ci_continuation_for_push_recovery(
            continuation.work_id,
            lease,
            journal,
            now=dependencies.now(),
        )
        dependencies.tracker.mutation_occurred = True
    pull_request = _pull_request_after_exact_push(
        pr_number=continuation.pr_number,
        reviewed_head=journal.new_head,
        journal=journal,
        dependencies=dependencies,
    )
    if (
        pull_request.head_ref_name != continuation.branch
        or pull_request.head_sha != journal.new_head
    ):
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
    if continuation.phase not in {
        CiContinuationPhase.REPAIR_REVIEWED,
        CiContinuationPhase.SECOND_WAIT,
    }:
        raise StateStoreError("CI continuation is not ready for repair push completion")
    if continuation.phase is CiContinuationPhase.REPAIR_REVIEWED:
        observed_at = _current_time(dependencies, continuation)
        waiting = continuation.model_copy(
            update={
                "phase": CiContinuationPhase.SECOND_WAIT,
                "current_head": journal.new_head,
                "second_wait_started_at": observed_at,
            }
        )
        waiting = store.advance_ci_continuation(
            waiting,
            lease,
            now=observed_at,
        )
        dependencies.tracker.mutation_occurred = True
    else:
        waiting = continuation

    try:
        managed_body = extract_managed_body(pull_request.body)
    except ValueError:
        raise MaintainerError(
            ErrorReason.INVALID_GITHUB_STATE,
            ErrorStage.READINESS,
            detail="Managed body markers are not trusted",
        ) from None
    if managed_body is None:
        managed_body = waiting.resulting_graph_markdown
    _require_canonical_resulting_graph(
        None,
        managed_body,
        expected=waiting.resulting_graph_markdown,
    )
    comments = tuple(dependencies.github.list_issue_comments(waiting.pr_number))
    machine = ci_publication_machine_state(
        continuation=waiting,
        pull_request=pull_request,
        repair_checkpoint_revalidated=True,
    )
    plan = publication_plan(
        requested_state=MaintainerState.WAITING_CI,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=pull_request,
        machine_state=machine,
        superseded_hold_head=trusted_hold_head(pull_request, comments),
        exact_repair_push_handoff=True,
    )

    def mutation_guard() -> AbstractContextManager[None]:
        return store.guard_push_mutation(journal, lease)

    publication_mutated = publish_state(
        dependencies.github,
        pull_request,
        plan,
        managed_body,
        _CI_REPAIR_WAITING_SUMMARY,
        allow_comment_repair=True,
        mutation_guard=mutation_guard,
        validate_mutation=lambda _step, _current: lease.assert_owner(),
        report_path=waiting.report_path,
    )
    dependencies.tracker.mutation_occurred = (
        dependencies.tracker.mutation_occurred or publication_mutated
    )
    journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
    store.save_push(journal, lease)
    dependencies.tracker.mutation_occurred = True
    return journal, waiting


def handle_publish_ci_repair(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PUSH
    _require_clear_ci_repair_journal(store)
    continuation = store.load_ci_continuation(work_id)
    if (
        continuation is None
        or continuation.recovery_run_id != lease.run_id
        or continuation.phase is not CiContinuationPhase.REPAIR_REVIEWED
        or not continuation.repair_attempted
    ):
        raise StateStoreError("reviewed owned CI repair is required")
    prior_journal = store.load_push(work_id)
    if (
        prior_journal is None
        or prior_journal.worker != "curation"
        or prior_journal.phase is not PushPhase.PUBLISHED
        or prior_journal.pr_number != args.pr
        or prior_journal.branch != continuation.branch
        or prior_journal.new_head != continuation.current_head
        or prior_journal.report_path != continuation.report_path
        or prior_journal.resulting_graph_markdown
        != continuation.resulting_graph_markdown
    ):
        raise StateStoreError(
            "published initial push journal is required for CI repair"
        )
    journal = _matching_ci_repair_journal(continuation, lease)
    _preflight_new_ci_repair_push(
        continuation,
        journal,
        dependencies,
    )
    store.save_push(journal, lease)
    dependencies.tracker.mutation_occurred = True
    journal = _advance_curation_push(
        store,
        lease,
        journal,
        None,
        dependencies,
        ci_continuation=continuation,
        strict_new_ci_repair_push=True,
    )
    journal, waiting = _complete_ci_repair_push(
        store=store,
        lease=lease,
        journal=journal,
        continuation=continuation,
        dependencies=dependencies,
    )
    dependencies.tracker.terminal_reason = "ci-repair-pushed"
    return {
        "work_id": work_id,
        "push": journal.model_dump(mode="json"),
        "continuation": waiting.model_dump(mode="json"),
    }


def handle_publish_state(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    requested_state = _requested_state(args.state)
    if requested_state is MaintainerState.PROPOSAL:
        raise CLIInputError("proposal state requires publish proposal")
    readiness_state = requested_state in {
        MaintainerState.WAITING_CI,
        MaintainerState.READY,
    }
    if readiness_state and args.body_file is None:
        raise PublicationInputError("readiness publication requires a body")
    adopt_body = getattr(args, "adopt_body", False)
    if adopt_body and not readiness_state:
        raise PublicationInputError("body adoption is limited to readiness publication")
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PUBLISH
    if store.list_unresolved_terminal_publications():
        raise StateStoreError("unresolved terminal publication requires exact recovery")
    if hasattr(args, "_trusted_summary"):
        summary = args._trusted_summary
        body = args._trusted_body
    else:
        summary = read_publication_text(
            args.state_dir,
            args.summary_file,
            kind="summary",
        )
        body = (
            read_publication_text(args.state_dir, args.body_file, kind="body")
            if args.body_file is not None
            else None
        )
    work = store.load_work(work_id)
    journal = store.load_push(work_id)
    ci_continuation = store.load_ci_continuation(work_id)
    _require_no_nonconverged_ci_repair_publication(
        ci_continuation,
        journal,
    )
    ci_needs_adoption = False
    if (
        ci_continuation is not None
        and ci_continuation.phase
        in {
            CiContinuationPhase.INITIAL_WAIT,
            CiContinuationPhase.SECOND_WAIT,
        }
        and ci_continuation.recovery_run_id != lease.run_id
    ):
        deferred_journal_adoption = (
            journal is not None
            and journal.worker == "curation"
            and journal.recovery_run_id == lease.run_id
            and journal.phase is PushPhase.PUSHED
            and journal.pr_number == args.pr
            and journal.branch == ci_continuation.branch
            and journal.new_head == ci_continuation.current_head
        )
        if deferred_journal_adoption:
            ci_needs_adoption = True
        else:
            ci_continuation = store.adopt_ci_continuation(
                work_id,
                lease,
                now=dependencies.now(),
            )
            dependencies.tracker.mutation_occurred = True
    _require_canonical_resulting_graph(
        work,
        body,
        expected=(
            ci_continuation.resulting_graph_markdown
            if ci_continuation is not None
            and ci_continuation.phase
            in {
                CiContinuationPhase.INITIAL_WAIT,
                CiContinuationPhase.SECOND_WAIT,
            }
            else None
        ),
    )
    matching_pushed_journal = (
        journal is not None
        and journal.worker == "curation"
        and journal.recovery_run_id == lease.run_id
        and journal.pr_number == args.pr
        and journal.new_head == args.reviewed_head
        and journal.phase in {PushPhase.PUSHED, PushPhase.PUBLISHED}
    )
    pull_request = _pull_request_after_exact_push(
        pr_number=args.pr,
        reviewed_head=args.reviewed_head,
        journal=journal if matching_pushed_journal else None,
        dependencies=dependencies,
    )
    if pull_request.head_sha != args.reviewed_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
    if (
        requested_state is MaintainerState.WAITING_CI
        and matching_pushed_journal
        and journal is not None
        and journal.phase is PushPhase.PUSHED
        and (
            ci_continuation is None
            or ci_continuation.phase
            in {
                CiContinuationPhase.INITIAL_WAIT,
                CiContinuationPhase.CONSUMED,
                CiContinuationPhase.BLOCKED,
                CiContinuationPhase.INVALIDATED,
            }
        )
    ):
        ci_continuation = _ensure_initial_ci_continuation(
            store=store,
            lease=lease,
            work=work,
            journal=journal,
            reviewed_head=args.reviewed_head,
            dependencies=dependencies,
        )
    comments = tuple(dependencies.github.list_issue_comments(args.pr))
    existing_machine = trusted_machine_state(comments)
    active_ci_wait = ci_continuation is not None and ci_continuation.phase in {
        CiContinuationPhase.INITIAL_WAIT,
        CiContinuationPhase.SECOND_WAIT,
    }
    if active_ci_wait and ci_continuation is not None:
        if args.reviewed_head != ci_continuation.current_head:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
        repair_checkpoint_revalidated = False
        if ci_continuation.phase is CiContinuationPhase.SECOND_WAIT:
            checkpoint = _ci_repair_checkpoint(ci_continuation)
            revalidated = dependencies.repository.revalidate_ci_repair_checkpoint(
                pull_request=pull_request,
                semantic_head=ci_continuation.semantic_head,
                current_head=ci_continuation.semantic_head,
                checkpoint=checkpoint,
            )
            if revalidated != checkpoint:
                raise RepositorySafetyError(
                    "revalidated CI repair checkpoint changed immutable evidence"
                )
            repair_checkpoint_revalidated = True
        machine = ci_publication_machine_state(
            continuation=ci_continuation,
            pull_request=pull_request,
            repair_checkpoint_revalidated=repair_checkpoint_revalidated,
        )
    else:
        validated_head = None
        last_operation: Literal[
            "reviewed",
            "validated",
            "pushed",
            "published",
        ] = "reviewed"
        if (
            work is not None
            and work.validated_head == args.reviewed_head
            and (work.run_id == lease.run_id or matching_pushed_journal)
        ):
            validated_head = work.validated_head
            last_operation = (
                "published"
                if (
                    work.phase is WorkPhase.PUBLISHED
                    or (
                        matching_pushed_journal
                        and journal is not None
                        and journal.phase is PushPhase.PUBLISHED
                    )
                )
                else "pushed"
                if work.phase is WorkPhase.PUSHED or matching_pushed_journal
                else "validated"
            )
        elif (
            existing_machine is not None
            and existing_machine.validated_head == args.reviewed_head
        ):
            validated_head = existing_machine.validated_head
            last_operation = existing_machine.last_operation
        machine = MachineState(
            schema_version=2,
            reviewed_head=args.reviewed_head,
            validated_head=validated_head,
            last_operation=last_operation,
        )
    plan = publication_plan(
        requested_state=requested_state,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=pull_request,
        machine_state=machine,
        superseded_hold_head=trusted_hold_head(pull_request, comments),
    )
    if plan.machine_state.validated_head is not None:
        plan = plan.model_copy(
            update={
                "machine_state": plan.machine_state.model_copy(
                    update={"last_operation": "published"}
                )
            }
        )
    wait_recorded = ci_needs_adoption
    if (
        requested_state is MaintainerState.WAITING_CI
        and active_ci_wait
        and ci_continuation is not None
        and not ci_needs_adoption
    ):
        ci_continuation = store.record_ci_wait_observation(
            work_id,
            lease,
            now=_current_time(dependencies, ci_continuation),
        )
        dependencies.tracker.mutation_occurred = True
        wait_recorded = True
    mutation_guard: Callable[[], AbstractContextManager[None]]
    if journal is not None and journal.recovery_run_id == lease.run_id:

        def mutation_guard() -> AbstractContextManager[None]:
            return store.guard_push_mutation(journal, lease)

    else:

        def mutation_guard() -> AbstractContextManager[None]:
            return _lease_mutation_guard(lease)

    publication_mutated = publish_state(
        dependencies.github,
        pull_request,
        plan,
        body,
        summary,
        adopt_unmanaged_body=adopt_body,
        allow_comment_repair=True,
        mutation_guard=mutation_guard,
        validate_mutation=lambda _step, _current: lease.assert_owner(),
        report_path=(
            ci_continuation.report_path
            if active_ci_wait and ci_continuation is not None
            else journal.report_path
            if matching_pushed_journal and journal is not None
            else work.report_path
            if work is not None
            and work.report_path is not None
            and (
                work.reviewed_head == args.reviewed_head
                or work.validated_head == args.reviewed_head
            )
            else None
        ),
    )
    dependencies.tracker.mutation_occurred = (
        dependencies.tracker.mutation_occurred or publication_mutated
    )
    if (
        journal is not None
        and journal.recovery_run_id == lease.run_id
        and journal.phase is PushPhase.PUSHED
    ):
        journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
    if ci_needs_adoption and ci_continuation is not None:
        ci_continuation = store.adopt_ci_continuation(
            ci_continuation.work_id,
            lease,
            now=dependencies.now(),
        )
        dependencies.tracker.mutation_occurred = True
    if (
        requested_state is MaintainerState.WAITING_CI
        and active_ci_wait
        and ci_continuation is not None
        and not wait_recorded
    ):
        ci_continuation = store.record_ci_wait_observation(
            work_id,
            lease,
            now=_current_time(dependencies, ci_continuation),
        )
        dependencies.tracker.mutation_occurred = True
    if (
        requested_state is MaintainerState.READY
        and active_ci_wait
        and ci_continuation is not None
    ):
        consumed = ci_continuation.model_copy(
            update={"phase": CiContinuationPhase.CONSUMED}
        )
        store.advance_ci_continuation(
            consumed,
            lease,
            now=_current_time(dependencies, ci_continuation),
        )
        dependencies.tracker.mutation_occurred = True
    if (
        work is not None
        and work.run_id == lease.run_id
        and work.phase is WorkPhase.PUSHED
    ):
        _advance_work(
            store,
            lease,
            work,
            dependencies,
            WorkPhase.PUBLISHED,
        )
    state_reason = requested_state.name.lower().replace("_", "-")
    dependencies.tracker.terminal_reason = (
        state_reason
        if dependencies.tracker.mutation_occurred
        else f"{state_reason}-unchanged"
    )
    return {"pr_number": args.pr, "state": requested_state.value}


def handle_publish_outcome(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    requested_state = _requested_state(args.state)
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PUBLISH
    summary = read_publication_text(
        args.state_dir,
        args.summary_file,
        kind="summary",
    )
    terminal_publications = store.list_unresolved_terminal_publications()
    if terminal_publications:
        if (
            len(terminal_publications) != 1
            or terminal_publications[0].work_id != work_id
        ):
            raise StateStoreError("terminal publication retry requires exact authority")
        intent = terminal_publications[0]
        _require_matching_terminal_publication_request(
            intent,
            work_id=work_id,
            pr_number=args.pr,
            expected_head=args.expected_head,
            requested_state=requested_state,
            reason=args.reason,
            summary=summary,
        )
        if intent.recovery_run_id != lease.run_id:
            raise StateStoreError(
                "successor terminal publication requires publish recover"
            )
        completed = _replay_terminal_publication(
            store=store,
            lease=lease,
            intent=intent,
            dependencies=dependencies,
        )
        return {
            "pr_number": completed.continuation.pr_number,
            "state": completed.target_state.value,
            "reason": completed.reason,
        }
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != args.expected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUBLISH)
    journal = store.load_push(work_id)
    ci_continuation = store.load_ci_continuation(work_id)
    _require_no_nonconverged_ci_repair_publication(
        ci_continuation,
        journal,
    )
    active_ci_continuation = ci_continuation is not None and ci_continuation.phase in {
        CiContinuationPhase.INITIAL_WAIT,
        CiContinuationPhase.REPAIR_ACTIVE,
        CiContinuationPhase.REPAIR_REVIEWED,
        CiContinuationPhase.SECOND_WAIT,
    }
    repair_in_progress = ci_continuation is not None and ci_continuation.phase in {
        CiContinuationPhase.REPAIR_ACTIVE,
        CiContinuationPhase.REPAIR_REVIEWED,
    }
    ci_wait_phase = ci_continuation is not None and ci_continuation.phase in {
        CiContinuationPhase.INITIAL_WAIT,
        CiContinuationPhase.SECOND_WAIT,
    }
    ci_needs_adoption = False
    if active_ci_continuation and ci_continuation is not None:
        if (
            pull_request.head_ref_name != ci_continuation.branch
            or pull_request.head_sha != ci_continuation.current_head
        ):
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUBLISH)
        if repair_in_progress:
            if requested_state is not MaintainerState.BLOCKED:
                raise StateStoreError(
                    "active CI repair requires a terminal blocked outcome"
                )
        elif (
            ci_wait_phase
            and requested_state is MaintainerState.BLOCKED
            and args.reason == "ci-failure"
        ):
            if pull_request.check_state != "failure" or not any(
                is_confirmed_ci_failure(check) for check in pull_request.checks
            ):
                raise MaintainerError(
                    ErrorReason.INVALID_GITHUB_STATE,
                    ErrorStage.PUBLISH,
                )
            if ci_continuation.phase is CiContinuationPhase.SECOND_WAIT:
                checkpoint = _ci_repair_checkpoint(ci_continuation)
                revalidated = dependencies.repository.revalidate_ci_repair_checkpoint(
                    pull_request=pull_request,
                    semantic_head=ci_continuation.semantic_head,
                    current_head=ci_continuation.semantic_head,
                    checkpoint=checkpoint,
                )
                if revalidated != checkpoint:
                    raise RepositorySafetyError(
                        "revalidated CI repair checkpoint changed immutable evidence"
                    )
        else:
            raise StateStoreError(
                "active CI continuation requires a terminal CI-failure outcome"
            )
        if ci_continuation.recovery_run_id != lease.run_id:
            deferred_journal_adoption = (
                journal is not None
                and journal.worker == "curation"
                and journal.recovery_run_id == lease.run_id
                and journal.phase is PushPhase.PUSHED
                and journal.pr_number == args.pr
                and journal.branch == ci_continuation.branch
                and journal.new_head == ci_continuation.current_head
            )
            if deferred_journal_adoption:
                ci_needs_adoption = True
            else:
                ci_continuation = store.adopt_ci_continuation(
                    work_id,
                    lease,
                    now=dependencies.now(),
                )
                dependencies.tracker.mutation_occurred = True
    machine_state = trusted_machine_state(
        dependencies.github.list_issue_comments(args.pr)
    )
    plan = outcome_plan(
        requested_state=requested_state,
        reason=args.reason,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=pull_request,
        existing_machine_state=machine_state,
    )
    if repair_in_progress and ci_continuation is not None:
        validate_outcome_publication_input(plan, summary)
        intent = TerminalPublicationIntent(
            work_id=work_id,
            worker="curation",
            origin_run_id=lease.run_id,
            recovery_run_id=lease.run_id,
            updated_at=_current_time(dependencies, ci_continuation),
            continuation=ci_continuation,
            target_state=requested_state,
            reason=args.reason,
            summary=summary,
            machine_state=plan.machine_state,
            phase=TerminalPublicationPhase.AUTHORIZED,
        )
        intent = store.save_terminal_publication(intent, lease)
        dependencies.tracker.mutation_occurred = True
        completed = _replay_terminal_publication(
            store=store,
            lease=lease,
            intent=intent,
            dependencies=dependencies,
        )
        return {
            "pr_number": completed.continuation.pr_number,
            "state": completed.target_state.value,
            "reason": completed.reason,
        }
    if journal is not None and journal.recovery_run_id == lease.run_id:

        def mutation_guard() -> AbstractContextManager[None]:
            return store.guard_push_mutation(journal, lease)

    else:

        def mutation_guard() -> AbstractContextManager[None]:
            return _lease_mutation_guard(lease)

    mutated = publish_outcome(
        dependencies.github,
        pull_request,
        plan,
        summary,
        allow_comment_repair=True,
        mutation_guard=mutation_guard,
        validate_mutation=lambda _step, _current: lease.assert_owner(),
    )
    dependencies.tracker.mutation_occurred = (
        dependencies.tracker.mutation_occurred or mutated
    )
    if (
        journal is not None
        and journal.recovery_run_id == lease.run_id
        and journal.phase is PushPhase.PUSHED
    ):
        journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
    if ci_needs_adoption and ci_continuation is not None:
        ci_continuation = store.adopt_ci_continuation(
            work_id,
            lease,
            now=dependencies.now(),
        )
        dependencies.tracker.mutation_occurred = True
    if active_ci_continuation and ci_continuation is not None:
        blocked = ci_continuation.model_copy(
            update={"phase": CiContinuationPhase.BLOCKED}
        )
        store.advance_ci_continuation(
            blocked,
            lease,
            now=_current_time(dependencies, ci_continuation),
        )
        dependencies.tracker.mutation_occurred = True
    reason = requested_state.name.lower().replace("_", "-")
    dependencies.tracker.terminal_reason = (
        f"outcome-{reason}" if mutated else f"outcome-{reason}-unchanged"
    )
    return {
        "pr_number": args.pr,
        "state": requested_state.value,
        "reason": args.reason,
    }


def handle_ensure_labels(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, args.worker, dependencies)
    dependencies.tracker.stage = ErrorStage.PUBLISH
    lease.assert_owner()
    mutated = dependencies.github.ensure_labels(LABEL_DEFINITIONS)
    lease.assert_owner()
    dependencies.tracker.mutation_occurred = bool(mutated)
    dependencies.tracker.terminal_reason = (
        "labels-synchronized" if mutated else "labels-unchanged"
    )
    return {"worker": args.worker}


def _read_publication_stdin() -> bytes:
    try:
        payload = sys.stdin.buffer.read(65_537)
    except (AttributeError, OSError):
        raise PublicationInputError("publication input is unsafe") from None
    if type(payload) is not bytes:
        raise PublicationInputError("publication input is unsafe")
    return payload


def handle_publication_input_create(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    validate_publication_state_directory(args.state_dir)
    try:
        lease = _owned_lease(args, args.worker, dependencies)
    except RunLeaseError as exc:
        raise LeaseOwnershipError(
            "maintainer run does not own the active lock"
        ) from exc
    dependencies.tracker.stage = ErrorStage.PUBLISH
    basename = create_publication_text(
        lease,
        kind=args.kind,
        payload=_read_publication_stdin(),
    )
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.terminal_reason = "publication-input-created"
    return {"basename": basename}


def handle_migrate_curation_state(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    dependencies.tracker.worker = "curation"
    dependencies.tracker.stage = ErrorStage.PREPARE
    if not args.archive_legacy:
        raise CLIInputError("curation state migration mode is required")
    try:
        result = migrate_legacy_curation_state(
            args.state_dir,
            dependencies.repository,
            now=_current_time(dependencies),
        )
    except CurationMigrationError as exc:
        if exc.reason == "active-lease":
            raise MaintainerError(
                ErrorReason.LEASE_CONFLICT,
                ErrorStage.LOCK,
            ) from exc
        if exc.reason == "external-recovery":
            raise MaintainerError(
                ErrorReason.LOCAL_RECOVERY_REQUIRED,
                ErrorStage.INSPECT,
            ) from exc
        if exc.reason == "format-conflict":
            raise MaintainerError(
                ErrorReason.STATE_MIGRATION_REQUIRED,
                ErrorStage.PREPARE,
            ) from exc
        raise MaintainerError(
            ErrorReason.UNSAFE_REPOSITORY,
            ErrorStage.PREPARE,
        ) from exc
    dependencies.tracker.mutation_occurred = not result.already_migrated
    dependencies.tracker.terminal_reason = (
        "curation_state_already_migrated"
        if result.already_migrated
        else "curation_state_migrated"
    )
    return {
        "migration": result.model_dump(mode="json"),
        "next_action": {
            "recipe_id": "inspect_curation",
            "substitutions": {},
        },
    }


def handle_validate_boundary_adjudication(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    dependencies.tracker.worker = "curation"
    dependencies.tracker.lease_run_id = args.run_id
    dependencies.tracker.stage = ErrorStage.VALIDATE
    result = validate_boundary_adjudication(args.input)
    dependencies.tracker.terminal_reason = "boundary_adjudication_validated"
    return {"adjudication": result.model_dump(mode="json")}


HANDLERS: dict[tuple[str, str], Handler] = {
    ("migrate", "curation-state"): handle_migrate_curation_state,
    ("inspect", "curation"): handle_inspect_curation,
    ("inspect", "discovery"): handle_inspect_discovery,
    ("prepare", "curation"): handle_prepare_curation,
    ("prepare", "ci-repair"): handle_prepare_ci_repair,
    ("checkpoint", "curation"): handle_checkpoint_curation,
    ("checkpoint", "ci-repair"): handle_checkpoint_ci_repair,
    ("invalidate", "ci-continuation"): handle_invalidate_ci_continuation,
    ("validate", "curation"): handle_validate_curation,
    ("validate", "boundary-adjudication"): handle_validate_boundary_adjudication,
    ("validate", "proposal"): handle_validate_proposal,
    ("publish", "push"): handle_publish_push,
    ("publish", "ci-repair"): handle_publish_ci_repair,
    ("publish", "manual-check"): handle_publish_manual_check,
    ("publish", "recover"): handle_publish_recover,
    ("publish", "proposal"): handle_publish_proposal,
    ("publish", "outcome"): handle_publish_outcome,
    ("publish", "state"): handle_publish_state,
    ("publish", "ensure-labels"): handle_ensure_labels,
    ("publication-input", "create"): handle_publication_input_create,
}


def dispatch(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    handler = HANDLERS.get((args.family, args.command))
    if handler is None:
        raise MaintainerError(
            ErrorReason.INVALID_COMMAND,
            ErrorStage.DISPATCH,
            detail="Command is outside the maintainer capability surface",
        )
    return handler(args, dependencies)


def handle_lock(
    args: argparse.Namespace,
    tracker: OutcomeTracker,
    now: Callable[[], datetime],
) -> dict[str, object]:
    tracker.worker = args.worker
    tracker.stage = ErrorStage.LOCK
    if args.command == "acquire":

        def require_recoverable_worker() -> None:
            terminal_publications = (
                StateStore.list_terminal_publications_for_inspection_path(
                    args.state_dir
                )
            )
            if len(terminal_publications) > 1:
                raise RunLeaseError(
                    "multiple terminal publications require owner attention"
                )
            if terminal_publications and args.worker != "curation":
                raise LeaseOwnershipError("terminal publication belongs to curation")
            unresolved = StateStore.list_unresolved_for_inspection(args.state_dir)
            if len(unresolved) > 1:
                raise RunLeaseError(
                    "multiple recovery journals require owner attention"
                )
            if unresolved and unresolved[0].worker != args.worker:
                raise LeaseOwnershipError("recovery journal belongs to another worker")

        lease = RunLease.acquire(
            args.state_dir,
            args.worker,
            now=now(),
            precondition=require_recoverable_worker,
        )
        tracker.lease_run_id = lease.run_id
        tracker.mutation_occurred = True
        tracker.terminal_reason = "acquired"
        return {"worker": lease.worker, "run_id": lease.run_id}
    tracker.lease_run_id = args.run_id
    lease = RunLease.load_owner(args.state_dir, args.worker, args.run_id)
    if args.command == "heartbeat":
        observed_at = now()
        lease.heartbeat(now=observed_at)
        continuation = StateStore(args.state_dir).record_owned_ci_heartbeat(
            lease,
            now=observed_at,
        )
        tracker.mutation_occurred = True
        tracker.terminal_reason = "heartbeat"
        result: dict[str, object] = {"worker": lease.worker}
        if continuation is not None:
            result["ci_budget"] = {
                "first_wait_seconds": continuation.first_wait_seconds,
                "repair_active_seconds": continuation.repair_active_seconds,
                "second_wait_seconds": continuation.second_wait_seconds,
            }
        return result
    if args.command == "release":
        lease.release()
        tracker.mutation_occurred = True
        tracker.terminal_reason = "released"
        return {"worker": lease.worker}
    raise CLIInputError("lock command is invalid")


def safe_error(error: Exception, stage: ErrorStage) -> MaintainerError:
    if isinstance(error, MaintainerError):
        return error
    if isinstance(error, LockBusyError):
        return MaintainerError(ErrorReason.LOCK_BUSY, ErrorStage.LOCK)
    if isinstance(error, LeaseOwnershipError):
        return MaintainerError(ErrorReason.LEASE_OWNERSHIP, ErrorStage.LOCK)
    if isinstance(error, RebaseConflictError):
        return MaintainerError(ErrorReason.REBASE_CONFLICT, ErrorStage.PREPARE)
    if isinstance(error, StaleRemoteHeadError):
        return MaintainerError(ErrorReason.STALE_HEAD, stage)
    if isinstance(error, IntentDriftError):
        return MaintainerError(ErrorReason.INTENT_DRIFT, ErrorStage.PREPARE)
    if isinstance(error, GitAuthenticationError):
        return MaintainerError(ErrorReason.AUTHENTICATION_FAILED, stage)
    if isinstance(error, (GitTransportError, GitOperationTimeoutError, GitHubError)):
        return MaintainerError(ErrorReason.TRANSPORT_FAILED, stage)
    if isinstance(error, GitPushRejectedError):
        return MaintainerError(ErrorReason.PUSH_REJECTED, ErrorStage.PUSH)
    if isinstance(error, GitRemotePolicyError):
        return MaintainerError(ErrorReason.AUTHENTICATION_FAILED, stage)
    if isinstance(error, PublicationInputError):
        return MaintainerError(
            ErrorReason.PUBLICATION_INPUT,
            ErrorStage.PUBLISH,
            ErrorCheck.PUBLICATION_INPUT,
            error.kind,
        )
    if isinstance(error, CurationStateError):
        return MaintainerError(ErrorReason.LOCAL_RECOVERY_REQUIRED, stage)
    if isinstance(error, RepositorySafetyError):
        return MaintainerError(ErrorReason.UNSAFE_REPOSITORY, stage)
    if isinstance(error, ValidationError):
        return MaintainerError(ErrorReason.CHECKPOINT_CONFLICT, stage)
    if isinstance(
        error,
        (
            CLIInputError,
            StateStoreError,
            RunLeaseError,
            ValueError,
            TypeError,
        ),
    ):
        return MaintainerError(ErrorReason.INVALID_COMMAND, stage)
    return MaintainerError(ErrorReason.INTERNAL_ERROR, stage)
    (CurationCheckpointIntegrityError,)
    (CurationRecoveryCheckpoint,)

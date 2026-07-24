from __future__ import annotations

import argparse
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
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorReason,
    ErrorStage,
    MaintainerError,
)
from ops.maintainer.git_ops import (
    ContinuationReplayResult,
    GitAuthenticationError,
    GitOperationTimeoutError,
    GitPushRejectedError,
    GitRemotePolicyError,
    GitRepository,
    GitTransportError,
    IntentDriftError,
    RebaseConflictError,
    RemediationCheckpointIntegrityError,
    RemediationCheckpointRefs,
    RepositorySafetyError,
    ReviewedCheckpointRefs,
    StaleRemoteHeadError,
)
from ops.maintainer.github import (
    GitHubComment,
    GitHubError,
)
from ops.maintainer.inspection import (
    DiscoveryInventory,
    inspect_curation,
    inspect_discovery,
)
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)
from ops.maintainer.publication import (
    PublicationInputError,
    create_publication_text,
    outcome_plan,
    publication_plan,
    publish_discovery_proposal,
    publish_outcome,
    publish_state,
    read_publication_text,
    trusted_hold_head,
    trusted_machine_state,
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
    ContinuationStatus,
    ContinuationValidationStatus,
    PushJournal,
    PushPhase,
    RemediationContinuation,
    RemediationContinuationStatus,
    ReviewedContinuation,
    RunOutcome,
    StateStore,
    StateStoreError,
    WorkPhase,
    WorkState,
    remediation_supersedes_reviewed,
)
from ops.maintainer.validation import (
    DeltaValidationResult,
    ProposalValidationResult,
    ValidationResult,
    immutable_resulting_graph_markdown,
    require_single_curation_report_path,
    revalidate_curation_request,
)

Worker = Literal["curation", "discovery"]
Handler = Callable[[argparse.Namespace, "Dependencies"], dict[str, object]]

_PR_HEAD_CONVERGENCE_ATTEMPTS = 5
_PR_HEAD_CONVERGENCE_DELAY_SECONDS = 3.0


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
    existing: WorkState | ReviewedContinuation | RemediationContinuation | None = None,
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
    unresolved_pushes = StateStore.list_unresolved_for_inspection(args.state_dir)
    ci_continuations = (
        ()
        if unresolved_pushes
        else StateStore.list_ci_continuations_for_inspection_path(args.state_dir)
    )
    open_pull_requests = tuple(dependencies.github.list_all_open_pull_requests())
    open_pr_numbers = {item.number for item in open_pull_requests}
    continuation_pull_requests = tuple(
        dependencies.github.get_pull_request(continuation.pr_number)
        for continuation in ci_continuations
        if continuation.pr_number not in open_pr_numbers
    )
    pull_requests = (*open_pull_requests, *continuation_pull_requests)
    inventory = inspect_curation(
        pull_requests,
        _comments_by_pr(dependencies.github, pull_requests),
        unresolved_pushes,
        (
            ()
            if unresolved_pushes
            else StateStore.list_continuations_for_inspection_path(args.state_dir)
        ),
        (
            ()
            if unresolved_pushes
            else StateStore.list_remediation_continuations_for_inspection_path(
                args.state_dir
            )
        ),
        ci_continuations,
        now=_current_time(dependencies),
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
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PREPARE
    pull_request = dependencies.github.get_pull_request(args.pr)
    _require_exact_curation_candidate(pull_request, dependencies, store)
    continuation = store.load_continuation(work_id)
    if continuation is not None and continuation.status not in {
        ContinuationStatus.CONSUMED,
        ContinuationStatus.INVALIDATED,
    }:
        if continuation.selected_head == pull_request.head_sha:
            raise MaintainerError(
                ErrorReason.CONTINUATION_REQUIRED,
                ErrorStage.PREPARE,
            )
        if continuation.recovery_run_id != lease.run_id:
            continuation = store.adopt_continuation(work_id, lease)
        invalidated = continuation.model_copy(
            update={
                "status": ContinuationStatus.INVALIDATED,
                "updated_at": _current_time(dependencies, continuation),
            }
        )
        store.save_continuation(invalidated, lease)
    remediation = store.load_remediation_continuation(work_id)
    if remediation is not None:
        remediation_is_terminal = remediation.status in {
            RemediationContinuationStatus.CONSUMED,
            RemediationContinuationStatus.INVALIDATED,
        }
        if not remediation_is_terminal and (
            remediation.selected_head == pull_request.head_sha
        ):
            raise MaintainerError(
                ErrorReason.CONTINUATION_REQUIRED,
                ErrorStage.PREPARE,
            )
        if not remediation_is_terminal:
            _invalidate_remediation_continuation(
                store=store,
                lease=lease,
                continuation=remediation,
            )
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PREPARE)
        if (
            remediation.status is RemediationContinuationStatus.INVALIDATED
            and remediation.recovery_run_id == lease.run_id
        ):
            reason = (
                ErrorReason.STALE_HEAD
                if remediation.selected_head != pull_request.head_sha
                else ErrorReason.CONTINUATION_REQUIRED
            )
            raise MaintainerError(reason, ErrorStage.PREPARE)
    selected = WorkState(
        work_id=work_id,
        worker="curation",
        run_id=lease.run_id,
        phase=WorkPhase.SELECTED,
        updated_at=_current_time(dependencies, store.load_work(work_id)),
        pr_number=args.pr,
        selected_head=pull_request.head_sha,
    )
    store.begin_work(selected, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.SELECTED
    sync = dependencies.repository.prepare_guarded_sync(pull_request)
    prepared = selected.model_copy(
        update={
            "phase": WorkPhase.PREPARED,
            "updated_at": _current_time(dependencies, selected),
            "prepared_head": sync.rebased_head,
            "backup_ref": sync.backup_ref,
            "sync": sync,
        }
    )
    store.save_work(prepared, lease)
    dependencies.tracker.last_phase = WorkPhase.PREPARED
    dependencies.tracker.terminal_reason = "prepared"
    return {"work_id": work_id, "prepared": sync.model_dump(mode="json")}


def _checkpoint_refs(continuation: ReviewedContinuation) -> ReviewedCheckpointRefs:
    return ReviewedCheckpointRefs(
        reviewed_ref=continuation.reviewed_ref,
        squash_ref=continuation.squash_ref,
    )


def _remediation_checkpoint_refs(
    continuation: RemediationContinuation,
) -> RemediationCheckpointRefs:
    return RemediationCheckpointRefs(
        remediation_ref=continuation.remediation_ref,
        squash_ref=continuation.squash_ref,
    )


def _new_remediation_continuation(
    *,
    work: WorkState,
    lease: RunLease,
    report_path: str,
    remediation_head: str,
    allowed_paths: frozenset[str],
    refs: RemediationCheckpointRefs,
    dependencies: Dependencies,
    previous: RemediationContinuation | None = None,
    reviewed: ReviewedContinuation | None = None,
) -> RemediationContinuation:
    if work.pr_number is None or work.sync is None:
        raise StateStoreError("prepared curation facts are incomplete")
    return RemediationContinuation(
        work_id=work.work_id,
        origin_run_id=(
            previous.origin_run_id
            if previous is not None
            and previous.status
            not in {
                RemediationContinuationStatus.CONSUMED,
                RemediationContinuationStatus.INVALIDATED,
            }
            else reviewed.origin_run_id
            if reviewed is not None
            and reviewed.status is ContinuationStatus.RESOLVING
            and reviewed.recovery_run_id == lease.run_id
            and reviewed.work_id == work.work_id
            and reviewed.pr_number == work.pr_number
            and reviewed.selected_head == work.selected_head
            and reviewed.report_path == report_path
            and reviewed.sync.target_branch == work.sync.target_branch
            and reviewed.sync.original_head == work.sync.original_head
            else lease.run_id
        ),
        recovery_run_id=lease.run_id,
        updated_at=_current_time(dependencies, previous or reviewed),
        pr_number=work.pr_number,
        selected_head=work.selected_head,
        remediation_head=remediation_head,
        report_path=report_path,
        sync=work.sync,
        allowed_paths=allowed_paths,
        remediation_ref=refs.remediation_ref,
        squash_ref=refs.squash_ref,
        completed_stage="delta-validated",
        status=RemediationContinuationStatus.AVAILABLE,
    )


def handle_checkpoint_remediation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.VALIDATE
    if store.list_unresolved_pushes():
        raise StateStoreError("unresolved push journal blocks remediation checkpoint")
    work = _load_work_for_run(store, work_id, lease)
    if work.phase is not WorkPhase.PREPARED or work.sync is None:
        raise StateStoreError("remediation checkpoint requires prepared curation work")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != work.selected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    _require_exact_curation_candidate(pull_request, dependencies, store)
    if dependencies.repository.current_head() != args.head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)

    existing = store.load_remediation_continuation(work_id)
    reviewed = store.load_continuation(work_id)
    existing_is_terminal = existing is not None and existing.status in {
        RemediationContinuationStatus.CONSUMED,
        RemediationContinuationStatus.INVALIDATED,
    }
    if (
        existing is not None
        and existing.recovery_run_id == lease.run_id
        and existing.status is RemediationContinuationStatus.AVAILABLE
        and existing.selected_head == work.selected_head
        and existing.remediation_head == args.head
        and existing.report_path == args.report
        and existing.sync == work.sync
    ):
        dependencies.repository.checkpoint_remediation_continuation(
            pull_request,
            work.sync,
            args.head,
        )
        dependencies.tracker.last_phase = WorkPhase.PREPARED
        dependencies.tracker.terminal_reason = "already-checkpointed"
        return {
            "continuation": {
                "kind": "remediation",
                "result": "already-checkpointed",
                "head": args.head,
                "report_path": args.report,
            }
        }
    if (
        existing is not None
        and not existing_is_terminal
        and existing.recovery_run_id != lease.run_id
    ):
        raise LeaseOwnershipError("remediation continuation belongs to another run")
    if (
        existing is not None
        and not existing_is_terminal
        and existing.selected_head != work.selected_head
    ):
        raise StateStoreError("active remediation continuation has different authority")

    snapshot = dependencies.repository.revalidate_prepared_result(
        pull_request,
        work.sync,
        args.head,
    )
    try:
        require_single_curation_report_path(snapshot, args.report)
    except ValueError:
        raise MaintainerError(
            ErrorReason.INVALID_COMMAND,
            ErrorStage.VALIDATE,
            detail="Remediation checkpoint requires the single changed report",
        ) from None
    base_repository = dependencies.base_repository or GitRepository(
        args.base_dir.resolve()
    )
    result = dependencies.curation_delta_validator(
        pull_request=pull_request,
        sync=work.sync,
        remediation_head=args.head,
        report_path=args.report,
        repository=dependencies.repository,
        base_repository=base_repository,
    )
    if result.remediation_head != args.head:
        raise StateStoreError("delta validation returned a different remediation head")
    refs = dependencies.repository.checkpoint_remediation_continuation(
        pull_request,
        work.sync,
        args.head,
    )
    remediation = _new_remediation_continuation(
        work=work,
        lease=lease,
        report_path=args.report,
        remediation_head=args.head,
        allowed_paths=snapshot.changed_paths,
        refs=refs,
        dependencies=dependencies,
        previous=existing,
        reviewed=reviewed,
    )
    if existing is None or existing.status in {
        RemediationContinuationStatus.CONSUMED,
        RemediationContinuationStatus.INVALIDATED,
    }:
        store.save_remediation_continuation(remediation, lease)
    else:
        store.replace_remediation_continuation(remediation, lease)
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.PREPARED
    dependencies.tracker.terminal_reason = "remediation-checkpointed"
    return {
        "continuation": {
            "kind": "remediation",
            "result": "checkpointed",
            "head": args.head,
            "report_path": args.report,
        }
    }


def _new_reviewed_continuation(
    *,
    work: WorkState,
    lease: RunLease,
    report_path: str,
    refs: ReviewedCheckpointRefs,
    dependencies: Dependencies,
    origin_run_id: str | None = None,
    previous: ReviewedContinuation | None = None,
) -> ReviewedContinuation:
    if work.pr_number is None or work.sync is None or work.reviewed_head is None:
        raise StateStoreError("reviewed curation facts are incomplete")
    return ReviewedContinuation(
        work_id=work.work_id,
        origin_run_id=origin_run_id or lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=_current_time(dependencies, previous),
        pr_number=work.pr_number,
        selected_head=work.selected_head,
        reviewed_head=work.reviewed_head,
        report_path=report_path,
        sync=work.sync,
        reviewed_ref=refs.reviewed_ref,
        squash_ref=refs.squash_ref,
        status=ContinuationStatus.AVAILABLE,
        validation_status=ContinuationValidationStatus.NOT_RUN,
    )


def handle_validate_reviewed(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.VALIDATE
    pull_request = dependencies.github.get_pull_request(args.pr)
    existing_continuation = store.load_continuation(work_id)
    work = store.load_work(work_id)
    if work is None or work.worker != "curation" or work.pr_number != args.pr:
        raise StateStoreError("reviewed curation work is missing")
    if args.adopt_existing:
        if existing_continuation is not None:
            raise StateStoreError("reviewed continuation already exists")
        if (
            work.phase is not WorkPhase.REVIEWED
            or work.reviewed_head != args.reviewed_head
        ):
            raise StateStoreError("legacy reviewed work does not match request")
    else:
        if work.run_id != lease.run_id:
            raise LeaseOwnershipError("work state belongs to another run")
        if work.phase not in {WorkPhase.PREPARED, WorkPhase.REVIEWED}:
            raise StateStoreError("curation work is not ready for review checkpoint")
        if (
            work.phase is WorkPhase.REVIEWED
            and work.reviewed_head != args.reviewed_head
        ):
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    if work.sync is None:
        raise StateStoreError("reviewed curation sync facts are missing")
    if (
        not args.adopt_existing
        and work.phase is WorkPhase.REVIEWED
        and existing_continuation is not None
        and existing_continuation.recovery_run_id == lease.run_id
        and existing_continuation.selected_head == work.selected_head
        and existing_continuation.reviewed_head == args.reviewed_head
        and existing_continuation.report_path == args.report
        and existing_continuation.sync == work.sync
        and existing_continuation.status
        not in {ContinuationStatus.CONSUMED, ContinuationStatus.INVALIDATED}
    ):
        remediation = store.load_remediation_continuation(work_id)
        dependencies.repository.revalidate_reviewed_checkpoint(
            pull_request,
            work.sync,
            args.reviewed_head,
            _checkpoint_refs(existing_continuation),
        )
        if remediation is not None and remediation.status not in {
            RemediationContinuationStatus.CONSUMED,
            RemediationContinuationStatus.INVALIDATED,
        }:
            store.promote_remediation_to_reviewed(
                remediation,
                existing_continuation,
                lease,
            )
            dependencies.tracker.mutation_occurred = True
        dependencies.tracker.last_phase = WorkPhase.REVIEWED
        dependencies.tracker.terminal_reason = "already-checkpointed"
        return {
            "work_id": work_id,
            "continuation": {
                "result": "already-checkpointed",
                "reviewed_head": args.reviewed_head,
                "report_path": args.report,
            },
        }
    snapshot = dependencies.repository.revalidate_prepared_result(
        pull_request,
        work.sync,
        args.reviewed_head,
    )
    try:
        require_single_curation_report_path(snapshot, args.report)
    except ValueError:
        raise MaintainerError(
            ErrorReason.INVALID_COMMAND,
            ErrorStage.VALIDATE,
            detail="Review checkpoint requires the single changed report",
        ) from None
    refs = dependencies.repository.checkpoint_reviewed_continuation(
        pull_request,
        work.sync,
        args.reviewed_head,
    )
    if work.phase is WorkPhase.PREPARED:
        work = _advance_work(
            store,
            lease,
            work,
            dependencies,
            WorkPhase.REVIEWED,
            reviewed_head=args.reviewed_head,
        )
    remediation = store.load_remediation_continuation(work_id)
    active_remediation = remediation is not None and remediation.status not in {
        RemediationContinuationStatus.CONSUMED,
        RemediationContinuationStatus.INVALIDATED,
    }
    continuation = _new_reviewed_continuation(
        work=work,
        lease=lease,
        report_path=args.report,
        refs=refs,
        dependencies=dependencies,
        origin_run_id=(
            work.run_id
            if args.adopt_existing
            else remediation.origin_run_id
            if active_remediation and remediation is not None
            else existing_continuation.origin_run_id
            if existing_continuation is not None
            and existing_continuation.status is ContinuationStatus.RESOLVING
            else None
        ),
        previous=existing_continuation,
    )
    if active_remediation:
        assert remediation is not None
        store.promote_remediation_to_reviewed(remediation, continuation, lease)
    elif args.adopt_existing:
        store.save_adopted_continuation(continuation, lease)
    elif (
        existing_continuation is not None
        and existing_continuation.status is ContinuationStatus.RESOLVING
    ):
        store.replace_resolved_continuation(continuation, lease)
    elif existing_continuation is None:
        store.save_continuation(continuation, lease)
    elif existing_continuation.status in {
        ContinuationStatus.CONSUMED,
        ContinuationStatus.INVALIDATED,
    }:
        store.save_continuation(continuation, lease)
    elif existing_continuation != continuation:
        raise StateStoreError("active continuation does not match reviewed checkpoint")
    dependencies.tracker.mutation_occurred = True
    dependencies.tracker.last_phase = WorkPhase.REVIEWED
    dependencies.tracker.terminal_reason = "reviewed-checkpointed"
    return {
        "work_id": work_id,
        "continuation": {
            "result": "checkpointed",
            "reviewed_head": args.reviewed_head,
            "report_path": args.report,
        },
    }


def _begin_continuation_work(
    *,
    store: StateStore,
    lease: RunLease,
    continuation: ReviewedContinuation | RemediationContinuation,
    pull_request: PullRequest,
    replay: ContinuationReplayResult,
    dependencies: Dependencies,
    reviewed: bool,
) -> WorkState:
    existing_work = store.load_work(continuation.work_id)
    selected = WorkState(
        work_id=continuation.work_id,
        worker="curation",
        run_id=lease.run_id,
        phase=WorkPhase.SELECTED,
        updated_at=_current_time(dependencies, existing_work),
        pr_number=continuation.pr_number,
        selected_head=pull_request.head_sha,
    )
    store.begin_work(selected, lease)
    if replay.sync is None or replay.head is None:
        raise StateStoreError("continuation replay omitted prepared facts")
    prepared = _advance_work(
        store,
        lease,
        selected,
        dependencies,
        WorkPhase.PREPARED,
        prepared_head=replay.sync.rebased_head,
        backup_ref=replay.sync.backup_ref,
        sync=replay.sync,
    )
    if not reviewed:
        return prepared
    return _advance_work(
        store,
        lease,
        prepared,
        dependencies,
        WorkPhase.REVIEWED,
        reviewed_head=replay.head,
    )


def _prepare_reviewed_continuation(
    args: argparse.Namespace,
    dependencies: Dependencies,
    *,
    lease: RunLease,
    store: StateStore,
    continuation: ReviewedContinuation,
) -> dict[str, object]:
    work_id = continuation.work_id
    pull_request = dependencies.github.get_pull_request(args.pr)
    _require_exact_curation_candidate(pull_request, dependencies, store)
    if pull_request.head_sha != continuation.selected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PREPARE)
    if continuation.recovery_run_id != lease.run_id:
        if args.continue_conflict:
            raise LeaseOwnershipError("interrupted conflict must be recreated")
        continuation = store.adopt_continuation(work_id, lease)
    remediation = store.load_remediation_continuation(work_id)
    if (
        remediation is not None
        and remediation.status
        not in {
            RemediationContinuationStatus.CONSUMED,
            RemediationContinuationStatus.INVALIDATED,
        }
        and remediation.origin_run_id == continuation.origin_run_id
        and remediation.selected_head == continuation.selected_head
        and remediation.sync == continuation.sync
        and remediation.remediation_head == continuation.reviewed_head
        and remediation.report_path == continuation.report_path
    ):
        if remediation.recovery_run_id != lease.run_id:
            remediation = store.adopt_remediation_continuation(work_id, lease)
        store.promote_remediation_to_reviewed(remediation, continuation, lease)
        dependencies.tracker.mutation_occurred = True
    refs = _checkpoint_refs(continuation)
    if args.continue_conflict:
        if continuation.status is not ContinuationStatus.RESOLVING:
            raise StateStoreError("continuation conflict is not active")
        replay = dependencies.repository.continue_reviewed_conflict(
            pull_request,
            continuation.sync,
            continuation.reviewed_head,
            refs,
        )
    else:
        replay = dependencies.repository.prepare_reviewed_continuation(
            pull_request,
            continuation.sync,
            continuation.reviewed_head,
            refs,
        )
    if replay.result == "unchanged":
        work = _begin_continuation_work(
            store=store,
            lease=lease,
            continuation=continuation,
            pull_request=pull_request,
            replay=replay,
            dependencies=dependencies,
            reviewed=True,
        )
        dependencies.tracker.last_phase = work.phase
        dependencies.tracker.terminal_reason = "continuation-validation-only"
        return {
            "work_id": work_id,
            "continuation": {
                "kind": "reviewed",
                "result": "validation-only",
                "base_head": replay.base_head,
                "reviewed_head": continuation.reviewed_head,
                "report_path": continuation.report_path,
            },
        }
    resolving = continuation.model_copy(
        update={
            "status": ContinuationStatus.RESOLVING,
            "validation_status": ContinuationValidationStatus.NOT_RUN,
            "updated_at": _current_time(dependencies, continuation),
        }
    )
    store.save_continuation(resolving, lease)
    dependencies.tracker.mutation_occurred = True
    if replay.result == "conflict":
        dependencies.tracker.terminal_reason = "continuation-conflict"
        return {
            "work_id": work_id,
            "continuation": {
                "kind": "reviewed",
                "result": "conflict-resolution-required",
                "base_head": replay.base_head,
                "conflict_paths": list(replay.conflict_paths),
            },
        }
    work = _begin_continuation_work(
        store=store,
        lease=lease,
        continuation=resolving,
        pull_request=pull_request,
        replay=replay,
        dependencies=dependencies,
        reviewed=False,
    )
    dependencies.tracker.last_phase = work.phase
    dependencies.tracker.terminal_reason = "continuation-review-required"
    return {
        "work_id": work_id,
        "continuation": {
            "kind": "reviewed",
            "result": "review-required",
            "base_head": replay.base_head,
            "prepared_head": replay.head,
            "report_path": continuation.report_path,
        },
    }


def _begin_remediation_resolution(
    *,
    store: StateStore,
    lease: RunLease,
    continuation: RemediationContinuation,
    dependencies: Dependencies,
    superseded_reviewed: ReviewedContinuation | None = None,
) -> RemediationContinuation:
    if continuation.recovery_run_id != lease.run_id:
        continuation = store.adopt_remediation_continuation(
            continuation.work_id,
            lease,
            superseded_reviewed=superseded_reviewed,
        )
    if continuation.status is RemediationContinuationStatus.AVAILABLE:
        resolving = continuation.model_copy(
            update={
                "status": RemediationContinuationStatus.RESOLVING,
                "updated_at": _current_time(dependencies, continuation),
            }
        )
        store.replace_remediation_continuation(resolving, lease)
        return resolving
    if continuation.status is not RemediationContinuationStatus.RESOLVING:
        raise StateStoreError("remediation continuation is not resumable")
    return continuation


def _invalidate_remediation_continuation(
    *,
    store: StateStore,
    lease: RunLease,
    continuation: RemediationContinuation,
) -> None:
    if continuation.recovery_run_id != lease.run_id:
        continuation = store.adopt_remediation_continuation(continuation.work_id, lease)
    store.invalidate_remediation_continuation(continuation.work_id, lease)


def _checkpoint_replayed_remediation(
    *,
    store: StateStore,
    lease: RunLease,
    continuation: RemediationContinuation,
    pull_request: PullRequest,
    replay: ContinuationReplayResult,
    dependencies: Dependencies,
) -> RemediationContinuation:
    if replay.head is None or replay.sync is None:
        raise StateStoreError("remediation replay omitted prepared facts")
    refs = dependencies.repository.checkpoint_remediation_continuation(
        pull_request,
        replay.sync,
        replay.head,
    )
    replayed = continuation.model_copy(
        update={
            "updated_at": _current_time(dependencies, continuation),
            "remediation_head": replay.head,
            "sync": replay.sync,
            "remediation_ref": refs.remediation_ref,
            "squash_ref": refs.squash_ref,
            "status": RemediationContinuationStatus.AVAILABLE,
        }
    )
    store.replace_remediation_continuation(replayed, lease)
    return replayed


def _prepare_remediation_continuation(
    args: argparse.Namespace,
    dependencies: Dependencies,
    *,
    lease: RunLease,
    store: StateStore,
    continuation: RemediationContinuation,
    superseded_reviewed: ReviewedContinuation | None = None,
) -> dict[str, object]:
    work_id = continuation.work_id
    pull_request = dependencies.github.get_pull_request(args.pr)
    if (
        pull_request.lifecycle_state != "OPEN"
        or pull_request.head_sha != continuation.selected_head
    ):
        _invalidate_remediation_continuation(
            store=store,
            lease=lease,
            continuation=continuation,
        )
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PREPARE)
    _require_exact_curation_candidate(pull_request, dependencies, store)
    if args.continue_conflict and continuation.recovery_run_id != lease.run_id:
        raise LeaseOwnershipError("interrupted conflict must be recreated")
    restart_interrupted = (
        not args.continue_conflict
        and continuation.recovery_run_id != lease.run_id
        and continuation.status is RemediationContinuationStatus.RESOLVING
    )
    continuation = _begin_remediation_resolution(
        store=store,
        lease=lease,
        continuation=continuation,
        dependencies=dependencies,
        superseded_reviewed=superseded_reviewed,
    )
    refs = _remediation_checkpoint_refs(continuation)
    try:
        if args.continue_conflict:
            replay = dependencies.repository.continue_remediation_conflict(
                pull_request,
                continuation.sync,
                continuation.remediation_head,
                refs,
            )
        else:
            replay = dependencies.repository.prepare_remediation_continuation(
                pull_request,
                continuation.sync,
                continuation.remediation_head,
                refs,
                restart_interrupted=restart_interrupted,
            )
    except (RemediationCheckpointIntegrityError, StaleRemoteHeadError):
        _invalidate_remediation_continuation(
            store=store,
            lease=lease,
            continuation=continuation,
        )
        raise
    dependencies.tracker.mutation_occurred = True
    if replay.result == "conflict":
        dependencies.tracker.terminal_reason = "remediation-conflict"
        return {
            "work_id": work_id,
            "continuation": {
                "kind": "remediation",
                "result": "conflict-resolution-required",
                "base_head": replay.base_head,
                "conflict_paths": list(replay.conflict_paths),
            },
        }
    continuation = _checkpoint_replayed_remediation(
        store=store,
        lease=lease,
        continuation=continuation,
        pull_request=pull_request,
        replay=replay,
        dependencies=dependencies,
    )
    work = _begin_continuation_work(
        store=store,
        lease=lease,
        continuation=continuation,
        pull_request=pull_request,
        replay=replay,
        dependencies=dependencies,
        reviewed=False,
    )
    dependencies.tracker.last_phase = work.phase
    dependencies.tracker.terminal_reason = "remediation-review-required"
    return {
        "work_id": work_id,
        "continuation": {
            "kind": "remediation",
            "result": "review-required",
            "base_head": replay.base_head,
            "prepared_head": replay.head,
            "report_path": continuation.report_path,
        },
    }


def handle_prepare_continuation(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PREPARE
    continuation = store.load_continuation(work_id)
    remediation = store.load_remediation_continuation(work_id)
    if (
        continuation is not None
        and remediation is not None
        and remediation_supersedes_reviewed(continuation, remediation)
    ):
        return _prepare_remediation_continuation(
            args,
            dependencies,
            lease=lease,
            store=store,
            continuation=remediation,
            superseded_reviewed=continuation,
        )
    if continuation is not None and continuation.status not in {
        ContinuationStatus.CONSUMED,
        ContinuationStatus.INVALIDATED,
    }:
        return _prepare_reviewed_continuation(
            args,
            dependencies,
            lease=lease,
            store=store,
            continuation=continuation,
        )
    if remediation is None or remediation.status in {
        RemediationContinuationStatus.CONSUMED,
        RemediationContinuationStatus.INVALIDATED,
    }:
        raise StateStoreError("resumable curation continuation is missing")
    return _prepare_remediation_continuation(
        args,
        dependencies,
        lease=lease,
        store=store,
        continuation=remediation,
    )


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
    work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.work_id = work_id
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.VALIDATE
    work = _load_work_for_run(store, work_id, lease)
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != work.selected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    continuation = store.load_continuation(work_id)
    if (
        continuation is None
        or continuation.recovery_run_id != lease.run_id
        or continuation.pr_number != args.pr
        or continuation.selected_head != work.selected_head
        or continuation.reviewed_head != args.reviewed_head
        or continuation.report_path != args.report
        or continuation.sync != work.sync
        or continuation.status
        in {ContinuationStatus.CONSUMED, ContinuationStatus.INVALIDATED}
    ):
        raise StateStoreError("exact reviewed continuation is required")
    assert work.sync is not None
    dependencies.repository.revalidate_reviewed_checkpoint(
        pull_request,
        work.sync,
        args.reviewed_head,
        _checkpoint_refs(continuation),
    )
    base_repository = dependencies.base_repository or GitRepository(
        args.base_dir.resolve()
    )
    if work.phase is WorkPhase.VALIDATED:
        if (
            work.sync is None
            or work.reviewed_head != args.reviewed_head
            or work.validated_head != args.reviewed_head
            or work.report_path != args.report
        ):
            raise StateStoreError("validated curation request does not match")
        revalidate_curation_request(
            pull_request=pull_request,
            sync=work.sync,
            reviewed_head=args.reviewed_head,
            report_path=args.report,
            repository=dependencies.repository,
            base_repository=base_repository,
        )
        if continuation.status is not ContinuationStatus.VALIDATED:
            continuation = continuation.model_copy(
                update={
                    "status": ContinuationStatus.VALIDATED,
                    "validation_status": ContinuationValidationStatus.PASSED,
                    "updated_at": _current_time(dependencies, continuation),
                }
            )
            store.save_continuation(continuation, lease)
            dependencies.tracker.mutation_occurred = True
        dependencies.tracker.last_phase = WorkPhase.VALIDATED
        dependencies.tracker.terminal_reason = "already_validated"
        return {
            "work_id": work_id,
            "validation": {
                "result": "already-validated",
                "validated_head": work.validated_head,
            },
        }
    if work.phase is not WorkPhase.REVIEWED or work.sync is None:
        raise StateStoreError("curation work is not checkpointed for validation")
    if work.reviewed_head != args.reviewed_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    try:
        result = dependencies.curation_validator(
            pull_request=pull_request,
            sync=work.sync,
            reviewed_head=args.reviewed_head,
            report_path=args.report,
            repository=dependencies.repository,
            base_repository=base_repository,
        )
    except Exception:
        failed = continuation.model_copy(
            update={
                "status": ContinuationStatus.AVAILABLE,
                "validation_status": ContinuationValidationStatus.FAILED,
                "updated_at": _current_time(dependencies, continuation),
            }
        )
        store.save_continuation(failed, lease)
        dependencies.tracker.mutation_occurred = True
        raise
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
    validated = continuation.model_copy(
        update={
            "status": ContinuationStatus.VALIDATED,
            "validation_status": ContinuationValidationStatus.PASSED,
            "updated_at": _current_time(dependencies, continuation),
        }
    )
    store.save_continuation(validated, lease)
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


def _advance_curation_push(
    store: StateStore,
    lease: RunLease,
    journal: PushJournal,
    work: WorkState | None,
    dependencies: Dependencies,
) -> PushJournal:
    remote_head = dependencies.repository.optional_remote_head(journal.branch)
    if journal.phase is PushPhase.AUTHORIZED:
        if remote_head == journal.expected_remote_head:
            if work is None or work.sync is None:
                raise StateStoreError("curation recovery requires prepared work state")
            authorized_heads = {work.reviewed_head, work.validated_head}
            if journal.new_head not in authorized_heads:
                raise StateStoreError("push journal head lacks reviewed work evidence")
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


def _consume_continuation_for_journal(
    *,
    store: StateStore,
    lease: RunLease,
    work: WorkState,
    expected_head: str,
    dependencies: Dependencies,
    require_validated: bool,
) -> None:
    continuation = store.load_continuation(work.work_id)
    allowed_statuses = (
        {ContinuationStatus.VALIDATED}
        if require_validated
        else {ContinuationStatus.AVAILABLE}
    )
    if (
        continuation is None
        or continuation.recovery_run_id != lease.run_id
        or continuation.status not in allowed_statuses
        or continuation.selected_head != work.selected_head
        or continuation.reviewed_head != expected_head
        or continuation.sync != work.sync
    ):
        raise StateStoreError("matching reviewed continuation is required")
    consumed = continuation.model_copy(
        update={
            "status": ContinuationStatus.CONSUMED,
            "updated_at": _current_time(dependencies, continuation),
        }
    )
    store.save_continuation(consumed, lease)
    dependencies.tracker.mutation_occurred = True


def handle_publish_push(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    lease = _owned_lease(args, "curation", dependencies)
    store = _state_store(args)
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
    journal = store.load_push(work_id)
    if journal is None or journal.phase is PushPhase.PUBLISHED:
        assert work.validated_head is not None
        journal = _matching_curation_journal(work, lease, work.validated_head)
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
        _consume_continuation_for_journal(
            store=store,
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
        continuation = store.load_continuation(work_id)
        if (
            continuation is None
            or continuation.recovery_run_id != lease.run_id
            or continuation.status is not ContinuationStatus.AVAILABLE
            or continuation.selected_head != work.selected_head
            or continuation.reviewed_head != args.reviewed_head
            or continuation.sync != work.sync
        ):
            raise StateStoreError(
                "manual-check publication requires exact reviewed continuation"
            )
        if continuation.report_path != args.report:
            raise PublicationInputError(
                "manual-check report must match the reviewed checkpoint"
            )
        pull_request = dependencies.github.get_pull_request(args.pr)
        if pull_request.head_sha != work.selected_head:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PRE_PUSH)
        dependencies.repository.revalidate_reviewed_checkpoint(
            pull_request,
            work.sync,
            args.reviewed_head,
            _checkpoint_refs(continuation),
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
        _consume_continuation_for_journal(
            store=store,
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


def handle_publish_recover(
    args: argparse.Namespace,
    dependencies: Dependencies,
) -> dict[str, object]:
    store = _state_store(args)
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
    if journal.worker == "curation":
        journal = _advance_curation_push(store, lease, journal, work, dependencies)
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
        validation_status: Literal["absent", "unknown", "validated"] = "unknown"
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
        or work.pr_number != journal.pr_number
        or work.validated_head != reviewed_head
        or work.report_path is None
        or work.resulting_graph_markdown is None
        or journal.report_path != work.report_path
        or journal.resulting_graph_markdown != work.resulting_graph_markdown
    ):
        raise StateStoreError(
            "waiting-CI handoff requires matching validated work and push evidence"
        )
    non_test_tree_digest = dependencies.repository.non_test_tree_digest(reviewed_head)
    existing = store.load_ci_continuation(work.work_id)
    if existing is not None:
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

    observed_at = dependencies.now()
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
    _require_canonical_resulting_graph(work, body)
    journal = store.load_push(work_id)
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
    ci_continuation = None
    if (
        requested_state is MaintainerState.WAITING_CI
        and matching_pushed_journal
        and journal is not None
        and journal.phase is PushPhase.PUSHED
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
    validated_head = None
    last_operation: Literal["reviewed", "validated", "pushed", "published"] = "reviewed"
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
    )
    dependencies.tracker.mutation_occurred = publication_mutated
    if (
        journal is not None
        and journal.recovery_run_id == lease.run_id
        and journal.phase is PushPhase.PUSHED
    ):
        journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
        if (
            ci_continuation is not None
            and ci_continuation.recovery_run_id != lease.run_id
        ):
            store.adopt_ci_continuation(
                ci_continuation.work_id,
                lease,
                now=dependencies.now(),
            )
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
    dependencies.tracker.work_id = _work_id_for_pr(args.pr)
    dependencies.tracker.pr_number = args.pr
    dependencies.tracker.stage = ErrorStage.PUBLISH
    summary = read_publication_text(
        args.state_dir,
        args.summary_file,
        kind="summary",
    )
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != args.expected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PUBLISH)
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
    mutated = publish_outcome(
        dependencies.github,
        pull_request,
        plan,
        summary,
        allow_comment_repair=True,
        mutation_guard=lambda: _lease_mutation_guard(lease),
        validate_mutation=lambda _step, _current: lease.assert_owner(),
    )
    dependencies.tracker.mutation_occurred = mutated
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


HANDLERS: dict[tuple[str, str], Handler] = {
    ("inspect", "curation"): handle_inspect_curation,
    ("inspect", "discovery"): handle_inspect_discovery,
    ("prepare", "curation"): handle_prepare_curation,
    ("prepare", "continuation"): handle_prepare_continuation,
    ("checkpoint", "remediation"): handle_checkpoint_remediation,
    ("validate", "curation"): handle_validate_curation,
    ("validate", "reviewed"): handle_validate_reviewed,
    ("validate", "proposal"): handle_validate_proposal,
    ("publish", "push"): handle_publish_push,
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
    if isinstance(
        error,
        (
            CLIInputError,
            StateStoreError,
            RunLeaseError,
            RepositorySafetyError,
            ValidationError,
            ValueError,
            TypeError,
        ),
    ):
        return MaintainerError(ErrorReason.INVALID_COMMAND, stage)
    return MaintainerError(ErrorReason.INTERNAL_ERROR, stage)

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from ops.maintainer import LABEL_DEFINITIONS
from ops.maintainer.errors import (
    ErrorReason,
    ErrorStage,
    MaintainerError,
)
from ops.maintainer.git_ops import (
    GitAuthenticationError,
    GitOperationTimeoutError,
    GitPushRejectedError,
    GitRemotePolicyError,
    GitRepository,
    GitTransportError,
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
    publication_plan,
    publish_discovery_proposal,
    publish_state,
    read_publication_text,
    trusted_machine_state,
)
from ops.maintainer.runtime import (
    LeaseOwnershipError,
    LockBusyError,
    RunLease,
    RunLeaseError,
)
from ops.maintainer.state import (
    PushJournal,
    PushPhase,
    RunOutcome,
    StateStore,
    StateStoreError,
    WorkPhase,
    WorkState,
)
from ops.maintainer.validation import (
    ProposalValidationResult,
    ValidationResult,
)

Worker = Literal["curation", "discovery"]
Handler = Callable[[argparse.Namespace, "Dependencies"], dict[str, object]]


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
    existing: WorkState | None = None,
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
    pull_requests = tuple(dependencies.github.list_all_open_pull_requests())
    inventory = inspect_curation(
        pull_requests,
        _comments_by_pr(dependencies.github, pull_requests),
        StateStore.list_unresolved_for_inspection(args.state_dir),
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
    if work.phase not in {WorkPhase.PREPARED, WorkPhase.REVIEWED} or work.sync is None:
        raise StateStoreError("curation work is not prepared for validation")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != work.selected_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    if work.phase is WorkPhase.PREPARED:
        work = _advance_work(
            store,
            lease,
            work,
            dependencies,
            WorkPhase.REVIEWED,
            reviewed_head=args.reviewed_head,
        )
    elif work.reviewed_head != args.reviewed_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.VALIDATE)
    base_repository = dependencies.base_repository or GitRepository(
        args.base_dir.resolve()
    )
    result = dependencies.curation_validator(
        pull_request=pull_request,
        sync=work.sync,
        reviewed_head=args.reviewed_head,
        report_path=args.report,
        repository=dependencies.repository,
        base_repository=base_repository,
    )
    work = _advance_work(
        store,
        lease,
        work,
        dependencies,
        WorkPhase.VALIDATED,
        validated_head=result.validated_head,
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
    )
    dependencies.tracker.terminal_reason = "validated"
    return {"work_id": work_id, "validation": result.model_dump(mode="json")}


def _matching_curation_journal(
    work: WorkState,
    lease: RunLease,
    new_head: str,
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

    work = store.load_work(work_id)
    journal = store.load_push(work_id)
    journal_matches_request = (
        journal is not None
        and journal.worker == "curation"
        and journal.recovery_run_id == lease.run_id
        and journal.pr_number == args.pr
        and journal.new_head == args.reviewed_head
        and journal.phase
        in {PushPhase.AUTHORIZED, PushPhase.PUSHED, PushPhase.PUBLISHED}
    )

    if not journal_matches_request:
        work = _load_work_for_run(store, work_id, lease)
        if (
            work.phase not in {WorkPhase.PREPARED, WorkPhase.REVIEWED}
            or work.sync is None
            or work.validated_head is not None
        ):
            raise StateStoreError("manual-check publication requires reviewed work")
        pull_request = dependencies.github.get_pull_request(args.pr)
        if pull_request.head_sha != work.selected_head:
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PRE_PUSH)
        if (
            work.phase is WorkPhase.REVIEWED
            and args.reviewed_head != work.reviewed_head
        ):
            raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.PRE_PUSH)
        dependencies.repository.revalidate_prepared_result(
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
        journal = _matching_curation_journal(work, lease, args.reviewed_head)
        store.save_push(journal, lease)
        dependencies.tracker.mutation_occurred = True
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
    return {"work_id": journal.work_id, "push": journal.model_dump(mode="json")}


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
    elif journal_matches_run:
        report_path = "docs/catalog-curation/recovered-proposal.json"
    else:
        raise StateStoreError("validated proposal evidence is missing")
    validation = ProposalValidationResult(
        candidate_key=args.candidate_key,
        candidate_origin=args.candidate_origin,
        validated_head=args.head,
        report_path=report_path,
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
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request.head_sha != args.reviewed_head:
        raise MaintainerError(ErrorReason.STALE_HEAD, ErrorStage.READINESS)
    work = store.load_work(work_id)
    journal = store.load_push(work_id)
    matching_pushed_journal = (
        journal is not None
        and journal.worker == "curation"
        and journal.recovery_run_id == lease.run_id
        and journal.pr_number == args.pr
        and journal.new_head == args.reviewed_head
        and journal.phase in {PushPhase.PUSHED, PushPhase.PUBLISHED}
    )
    existing_machine = trusted_machine_state(
        dependencies.github.list_issue_comments(args.pr)
    )
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


HANDLERS: dict[tuple[str, str], Handler] = {
    ("inspect", "curation"): handle_inspect_curation,
    ("inspect", "discovery"): handle_inspect_discovery,
    ("prepare", "curation"): handle_prepare_curation,
    ("validate", "curation"): handle_validate_curation,
    ("validate", "proposal"): handle_validate_proposal,
    ("publish", "push"): handle_publish_push,
    ("publish", "manual-check"): handle_publish_manual_check,
    ("publish", "recover"): handle_publish_recover,
    ("publish", "proposal"): handle_publish_proposal,
    ("publish", "state"): handle_publish_state,
    ("publish", "ensure-labels"): handle_ensure_labels,
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
        lease.heartbeat(now=now())
        tracker.mutation_occurred = True
        tracker.terminal_reason = "heartbeat"
        return {"worker": lease.worker}
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
        return MaintainerError(ErrorReason.PUBLICATION_INPUT, ErrorStage.PUBLISH)
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

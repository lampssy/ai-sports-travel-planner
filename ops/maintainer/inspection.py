from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import AbstractSet, Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.data.catalog_loader import load_catalog_from_path
from app.domain.catalog import CatalogSnapshot
from ops.maintainer.curation_state import (
    CurationGeneration,
    CurationGenerationProjection,
    CurationNextAction,
    project_generation,
)
from ops.maintainer.errors import ErrorReason, ErrorStage, MaintainerError
from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.github import TRUSTED_MAINTAINER_LOGIN, GitHubComment
from ops.maintainer.intent import CATALOG_SECTIONS, is_allowed_curation_path
from ops.maintainer.models import (
    CheckSummary,
    MaintainerState,
    PullRequest,
    is_confirmed_ci_failure,
)
from ops.maintainer.publication import trusted_hold_head, trusted_machine_state
from ops.maintainer.state import (
    CiContinuation,
    CiContinuationPhase,
    PushJournal,
    PushPhase,
    TerminalPublicationIntent,
    TerminalPublicationPhase,
)

_SELECTION_HOLD_LABELS = frozenset(
    {
        "maintainer:manual-check",
        "maintainer:owner-decision",
        "maintainer:blocked",
        "maintainer:ready",
    }
)
_CANDIDATE_KEY_PATTERN = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*:[a-z0-9]+(?:-+[a-z0-9]+)*$"

CandidateKey = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=_CANDIDATE_KEY_PATTERN,
    ),
]


class _InspectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CurationCandidate(_InspectionModel):
    number: int = Field(gt=0)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    head_ref_name: str = Field(min_length=1, max_length=200)
    base_ref_name: Literal["main"]
    labels: frozenset[str]
    changed_paths: frozenset[str] = Field(min_length=1)
    check_state: Literal["pending", "success", "failure"]
    mergeable: Literal["MERGEABLE", "CONFLICTING", "UNKNOWN"]

    @field_validator("head_ref_name")
    @classmethod
    def validate_head_ref_name(cls, value: str) -> str:
        if not is_safe_codex_branch(value):
            raise ValueError("head branch must be a safe codex ref")
        return value

    @field_validator("changed_paths")
    @classmethod
    def validate_changed_paths(cls, paths: frozenset[str]) -> frozenset[str]:
        if not all(is_allowed_curation_path(path) for path in paths):
            raise ValueError("candidate contains a path outside curation scope")
        return paths


class CiContinuationSummary(_InspectionModel):
    pr_number: int = Field(gt=0)
    semantic_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    current_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    phase: CiContinuationPhase
    check_state: Literal["pending", "success", "failure"]
    mergeable: Literal["MERGEABLE", "CONFLICTING", "UNKNOWN"]
    repair_attempted: bool
    first_wait_seconds: int = Field(ge=0, le=1800)
    repair_active_seconds: int = Field(ge=0, le=3600)
    second_wait_seconds: int = Field(ge=0, le=1800)
    failed_checks: tuple[CheckSummary, ...] = ()
    resumable: bool
    availability_reason: Literal[
        "available",
        "head-drift",
        "closed-or-merged",
        "branch-drift",
        "invalid-state",
    ]


class TerminalPublicationSummary(_InspectionModel):
    worker: Literal["curation"]
    work_id: str = Field(min_length=1, max_length=128)
    pr_number: int = Field(gt=0)
    branch: str = Field(min_length=1, max_length=200)
    continuation_phase: Literal[
        CiContinuationPhase.REPAIR_ACTIVE,
        CiContinuationPhase.REPAIR_REVIEWED,
    ]
    semantic_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    current_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repair_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    target_state: Literal[MaintainerState.BLOCKED]
    reason: str = Field(min_length=1, max_length=64)


class CurationInventory(_InspectionModel):
    terminal_publications: tuple[TerminalPublicationSummary, ...] = ()
    unresolved_pushes: tuple[PushJournalSummary, ...] = ()
    ci_continuations: tuple[CiContinuationSummary, ...] = ()
    generations: tuple[CurationGenerationSummary, ...] = ()
    eligible: tuple[CurationCandidate, ...] = ()


class PushJournalSummary(_InspectionModel):
    worker: Literal["curation", "discovery"]
    work_id: str = Field(min_length=1, max_length=128)
    pr_number: int | None = Field(default=None, gt=0)
    candidate_key: str | None = None
    candidate_origin: Literal["backlog", "external"] | None = None
    phase: PushPhase
    expected_remote_head: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
    )
    new_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def validate_recovery_identity(self) -> Self:
        if self.worker == "curation":
            if (
                self.pr_number is None
                or self.candidate_key is not None
                or self.candidate_origin is not None
                or self.expected_remote_head is None
            ):
                raise ValueError("curation journal summary requires its PR identity")
        elif (
            self.candidate_key is None
            or self.candidate_origin is None
            or self.expected_remote_head is not None
        ):
            raise ValueError("discovery journal summary requires candidate identity")
        return self


class CurationGenerationSummary(_InspectionModel):
    pr_number: int = Field(gt=0)
    generation_number: int = Field(gt=0)
    generation_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    latest_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    stage: str = Field(min_length=1, max_length=32)
    retryable: bool
    availability_reason: Literal[
        "available",
        "hold-label",
        "head-drift",
        "closed-or-merged",
        "invalid-state",
        "complete",
    ]
    next_action: CurationNextAction | None = None


class ProposalSummary(_InspectionModel):
    pr_number: int = Field(gt=0)
    lifecycle_state: Literal["OPEN", "CLOSED", "MERGED"]
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    candidate_key: CandidateKey | None = None
    candidate_origin: Literal["backlog", "external"] | None = None

    @model_validator(mode="after")
    def validate_candidate_identity(self) -> Self:
        if (self.candidate_key is None) != (self.candidate_origin is None):
            raise ValueError("candidate key and origin must appear together")
        return self

    @property
    def identity_known(self) -> bool:
        return self.candidate_key is not None


class DiscoveryInventory(_InspectionModel):
    catalog_keys: frozenset[CandidateKey]
    open_proposal_count: int = Field(ge=0)
    open_candidate_keys: frozenset[CandidateKey]
    has_unknown_proposal_identity: bool
    can_create_proposal: bool
    open_proposals: tuple[ProposalSummary, ...] = ()
    closed_proposals: tuple[ProposalSummary, ...] = ()
    unresolved_pushes: tuple[PushJournalSummary, ...] = ()

    @model_validator(mode="after")
    def validate_creation_gate(self) -> Self:
        expected = (
            self.open_proposal_count < 3
            and not self.has_unknown_proposal_identity
            and not self.unresolved_pushes
        )
        if self.can_create_proposal is not expected:
            raise ValueError("proposal creation gate does not match inventory facts")
        return self


def inspect_curation(
    pull_requests: Iterable[PullRequest],
    comments_by_pr: Mapping[int, Sequence[GitHubComment]],
    unresolved_pushes: Sequence[PushJournal] = (),
    *,
    ci_continuations: Sequence[CiContinuation] = (),
    terminal_publications: Sequence[TerminalPublicationIntent] = (),
    now: datetime | None = None,
    generations: Sequence[CurationGeneration] = (),
) -> CurationInventory:
    publications = _normalize_terminal_publications(terminal_publications)
    if publications:
        return CurationInventory(
            terminal_publications=tuple(
                _terminal_publication_summary(item) for item in publications
            )
        )
    journals = _normalize_journals(unresolved_pushes)
    if journals:
        return CurationInventory(
            unresolved_pushes=tuple(_push_journal_summary(item) for item in journals)
        )
    pull_requests = _deduplicate_pull_requests(pull_requests)
    pull_requests_by_number = {item.number: item for item in pull_requests}
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
    if active_ci_continuations and now is None:
        raise ValueError("current time is required for CI continuation inspection")
    observed_at = _inspection_time(now) if now is not None else None
    ci_summaries = tuple(
        _ci_continuation_summary(
            continuation,
            pull_requests_by_number.get(continuation.pr_number),
            observed_at,
        )
        for continuation in sorted(
            active_ci_continuations,
            key=lambda item: item.pr_number,
        )
    )
    ci_pr_numbers = {item.pr_number for item in active_ci_continuations}

    active_generations = (
        () if active_ci_continuations else _current_generations(generations)
    )
    generation_summaries = tuple(
        _generation_summary(
            generation,
            pull_requests_by_number.get(generation.pr_number),
            comments_by_pr.get(generation.pr_number, ()),
        )
        for generation in active_generations
    )
    generation_pr_numbers = {item.pr_number for item in active_generations}

    eligible = tuple(
        sorted(
            (
                _curation_candidate(pull_request)
                for pull_request in pull_requests
                if _is_safe_curation_candidate(
                    pull_request,
                    comments_by_pr.get(pull_request.number, ()),
                )
                and pull_request.number not in ci_pr_numbers
                and pull_request.number not in generation_pr_numbers
            ),
            key=lambda pull_request: pull_request.number,
        )
    )
    return CurationInventory(
        ci_continuations=ci_summaries,
        generations=generation_summaries,
        eligible=eligible,
    )


def _current_generations(
    generations: Sequence[CurationGeneration],
) -> tuple[CurationGeneration, ...]:
    by_pr: dict[int, CurationGeneration] = {}
    for generation in generations:
        current = by_pr.get(generation.pr_number)
        if current is not None and (
            generation.generation_number == current.generation_number
            or generation.work_id != current.work_id
        ):
            raise ValueError("curation generations contain ambiguous authority")
        if current is None or generation.generation_number > current.generation_number:
            by_pr[generation.pr_number] = generation
    return tuple(by_pr[number] for number in sorted(by_pr))


def _generation_summary(
    generation: CurationGeneration,
    pull_request: PullRequest | None,
    comments: Sequence[GitHubComment],
) -> CurationGenerationSummary:
    projection = project_generation(generation)
    availability = _generation_availability(
        generation,
        projection,
        pull_request,
        comments,
    )
    retryable = availability == "available" and projection.next_action is not None
    return CurationGenerationSummary(
        pr_number=generation.pr_number,
        generation_number=generation.generation_number,
        generation_id=generation.generation_id,
        selected_head=generation.selected_head,
        base_head=generation.sync.base_head,
        latest_head=projection.latest_head,
        stage=projection.latest_stage,
        retryable=retryable,
        availability_reason=availability,
        next_action=projection.next_action if retryable else None,
    )


def _generation_availability(
    generation: CurationGeneration,
    projection: CurationGenerationProjection,
    pull_request: PullRequest | None,
    comments: Sequence[GitHubComment],
) -> Literal[
    "available",
    "hold-label",
    "head-drift",
    "closed-or-merged",
    "invalid-state",
    "complete",
]:
    if projection.latest_stage in {"superseded", "invalidated", "consumed"}:
        return "complete"
    if pull_request is None or pull_request.lifecycle_state in {"CLOSED", "MERGED"}:
        return "closed-or-merged"
    if pull_request.head_sha != generation.selected_head:
        return "head-drift"
    if not pull_request.labels.isdisjoint(_SELECTION_HOLD_LABELS):
        return "hold-label"
    if not _is_safe_curation_candidate(pull_request, comments):
        return "invalid-state"
    if projection.next_action is None:
        return "complete"
    return "available"


def inspect_discovery(
    catalog_keys: AbstractSet[str],
    open_pull_requests: Iterable[PullRequest],
    closed_pull_requests: Iterable[PullRequest],
    comments_by_pr: Mapping[int, Sequence[GitHubComment]],
    unresolved_pushes: Sequence[PushJournal] = (),
) -> DiscoveryInventory:
    journals = _normalize_journals(unresolved_pushes)
    if journals:
        return DiscoveryInventory(
            catalog_keys=frozenset(catalog_keys),
            open_proposal_count=0,
            open_candidate_keys=frozenset(),
            has_unknown_proposal_identity=False,
            can_create_proposal=False,
            unresolved_pushes=tuple(_push_journal_summary(item) for item in journals),
        )
    open_pull_requests = _deduplicate_pull_requests(open_pull_requests)
    closed_pull_requests = _deduplicate_pull_requests(closed_pull_requests)
    _require_lifecycle(open_pull_requests, open_input=True)
    _require_lifecycle(closed_pull_requests, open_input=False)
    if {item.number for item in open_pull_requests} & {
        item.number for item in closed_pull_requests
    }:
        raise _invalid_github_state("GitHub returned overlapping pull request history")

    open_proposals = tuple(
        _proposal_summary(
            pull_request,
            comments_by_pr.get(pull_request.number, ()),
        )
        for pull_request in sorted(
            open_pull_requests,
            key=lambda pull_request: pull_request.number,
        )
        if "maintainer:proposal" in pull_request.labels
    )
    closed_proposals = tuple(
        _proposal_summary(
            pull_request,
            comments_by_pr.get(pull_request.number, ()),
        )
        for pull_request in sorted(
            closed_pull_requests,
            key=lambda pull_request: pull_request.number,
        )
        if "lane:catalog-discovery" in pull_request.labels
    )
    unknown_identity = any(not summary.identity_known for summary in open_proposals)
    open_count = len(open_proposals)
    return DiscoveryInventory(
        catalog_keys=frozenset(catalog_keys),
        open_proposal_count=open_count,
        open_candidate_keys=frozenset(
            summary.candidate_key
            for summary in open_proposals
            if summary.candidate_key is not None
        ),
        has_unknown_proposal_identity=unknown_identity,
        can_create_proposal=(open_count < 3 and not unknown_identity and not journals),
        open_proposals=open_proposals,
        closed_proposals=closed_proposals,
        unresolved_pushes=tuple(_push_journal_summary(item) for item in journals),
    )


def catalog_entity_keys(catalog_path: Path) -> frozenset[str]:
    snapshot = load_catalog_from_path(catalog_path)
    return _catalog_entity_keys(snapshot)


def catalog_entity_keys_from_json(catalog_json: str) -> frozenset[str]:
    snapshot = CatalogSnapshot.model_validate_json(catalog_json)
    return _catalog_entity_keys(snapshot)


def _catalog_entity_keys(snapshot: CatalogSnapshot) -> frozenset[str]:
    return frozenset(
        f"{kind}:{getattr(entity, id_field)}"
        for section, id_field, kind in CATALOG_SECTIONS
        for entity in getattr(snapshot, section)
    )


def _normalize_journals(
    unresolved_pushes: Sequence[PushJournal],
) -> tuple[PushJournal, ...]:
    by_work_id: dict[str, PushJournal] = {}
    for journal in unresolved_pushes:
        if journal.phase is PushPhase.PUBLISHED:
            raise _invalid_journal_inventory(
                "Unresolved push journals contain a terminal record"
            )
        if journal.work_id in by_work_id:
            raise _invalid_journal_inventory(
                "Unresolved push journals contain duplicate work identifiers"
            )
        by_work_id[journal.work_id] = journal
    return tuple(by_work_id[work_id] for work_id in sorted(by_work_id))


def _normalize_terminal_publications(
    terminal_publications: Sequence[TerminalPublicationIntent],
) -> tuple[TerminalPublicationIntent, ...]:
    by_work_id: dict[str, TerminalPublicationIntent] = {}
    for intent in terminal_publications:
        if intent.phase is not TerminalPublicationPhase.AUTHORIZED:
            raise _invalid_journal_inventory(
                "Terminal publication inventory contains a completed record"
            )
        if intent.work_id in by_work_id:
            raise _invalid_journal_inventory(
                "Terminal publication inventory contains duplicate work identifiers"
            )
        by_work_id[intent.work_id] = intent
    return tuple(by_work_id[work_id] for work_id in sorted(by_work_id))


def _terminal_publication_summary(
    intent: TerminalPublicationIntent,
) -> TerminalPublicationSummary:
    continuation = intent.continuation
    return TerminalPublicationSummary(
        worker=intent.worker,
        work_id=intent.work_id,
        pr_number=continuation.pr_number,
        branch=continuation.branch,
        continuation_phase=continuation.phase,
        semantic_head=continuation.semantic_head,
        current_head=continuation.current_head,
        repair_head=continuation.repair_head,
        target_state=intent.target_state,
        reason=intent.reason,
    )


def _push_journal_summary(journal: PushJournal) -> PushJournalSummary:
    return PushJournalSummary(
        worker=journal.worker,
        work_id=journal.work_id,
        pr_number=journal.pr_number,
        candidate_key=journal.candidate_key,
        candidate_origin=journal.candidate_origin,
        phase=journal.phase,
        expected_remote_head=journal.expected_remote_head,
        new_head=journal.new_head,
    )


def _inspection_time(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("current time must include a timezone")
    return now.astimezone(UTC)


def _elapsed_wait_seconds(
    *,
    saved_seconds: int,
    started_at: datetime,
    observed_at: datetime,
) -> int:
    return min(
        1800,
        max(saved_seconds, int((observed_at - started_at).total_seconds())),
    )


def ci_continuation_availability(
    continuation: CiContinuation,
    pull_request: PullRequest | None,
) -> Literal[
    "available",
    "head-drift",
    "closed-or-merged",
    "branch-drift",
    "invalid-state",
]:
    if pull_request is None or pull_request.lifecycle_state in {"CLOSED", "MERGED"}:
        return "closed-or-merged"
    if pull_request.head_sha != continuation.current_head:
        return "head-drift"
    if pull_request.head_ref_name != continuation.branch:
        return "branch-drift"
    if (
        not pull_request.routing_labels_valid
        or pull_request.mergeable != "MERGEABLE"
        or pull_request.is_cross_repository
        or pull_request.head_repository_owner != TRUSTED_MAINTAINER_LOGIN
        or pull_request.base_ref_name != "main"
        or not pull_request.changed_paths
        or not all(
            is_allowed_curation_path(path) for path in pull_request.changed_paths
        )
    ):
        return "invalid-state"
    if continuation.phase is CiContinuationPhase.REPAIR_ACTIVE and (
        pull_request.check_state != "failure"
        or not any(is_confirmed_ci_failure(check) for check in pull_request.checks)
    ):
        return "invalid-state"
    return "available"


def ci_continuation_invalidation_reason(
    continuation: CiContinuation,
    pull_request: PullRequest | None,
) -> (
    Literal[
        "head-drift",
        "closed-or-merged",
        "branch-drift",
        "invalid-state",
    ]
    | None
):
    """Return only live helper facts that authorize terminal invalidation."""
    if pull_request is None or pull_request.lifecycle_state in {"CLOSED", "MERGED"}:
        return "closed-or-merged"
    if pull_request.head_sha != continuation.current_head:
        return "head-drift"
    if pull_request.head_ref_name != continuation.branch:
        return "branch-drift"
    if (
        pull_request.is_cross_repository
        or pull_request.head_repository_owner != TRUSTED_MAINTAINER_LOGIN
        or pull_request.base_ref_name != "main"
        or not pull_request.changed_paths
        or not all(
            is_allowed_curation_path(path) for path in pull_request.changed_paths
        )
    ):
        return "invalid-state"
    if pull_request.mergeable == "CONFLICTING":
        return "invalid-state"
    if (
        continuation.phase is CiContinuationPhase.REPAIR_ACTIVE
        and pull_request.check_state == "success"
    ):
        return "invalid-state"
    return None


def _ci_continuation_summary(
    continuation: CiContinuation,
    pull_request: PullRequest | None,
    observed_at: datetime | None,
) -> CiContinuationSummary:
    if observed_at is None:
        raise ValueError("current time is required for CI continuation inspection")
    first_wait_seconds = continuation.first_wait_seconds
    second_wait_seconds = continuation.second_wait_seconds
    if continuation.phase is CiContinuationPhase.INITIAL_WAIT:
        first_wait_seconds = _elapsed_wait_seconds(
            saved_seconds=first_wait_seconds,
            started_at=continuation.first_wait_started_at,
            observed_at=observed_at,
        )
    elif continuation.phase is CiContinuationPhase.SECOND_WAIT:
        assert continuation.second_wait_started_at is not None
        second_wait_seconds = _elapsed_wait_seconds(
            saved_seconds=second_wait_seconds,
            started_at=continuation.second_wait_started_at,
            observed_at=observed_at,
        )
    availability = ci_continuation_availability(continuation, pull_request)
    return CiContinuationSummary(
        pr_number=continuation.pr_number,
        semantic_head=continuation.semantic_head,
        current_head=(
            pull_request.head_sha
            if pull_request is not None
            else continuation.current_head
        ),
        phase=continuation.phase,
        check_state=(
            pull_request.check_state if pull_request is not None else "pending"
        ),
        mergeable=pull_request.mergeable if pull_request is not None else "UNKNOWN",
        repair_attempted=continuation.repair_attempted,
        first_wait_seconds=first_wait_seconds,
        repair_active_seconds=continuation.repair_active_seconds,
        second_wait_seconds=second_wait_seconds,
        failed_checks=(
            tuple(check for check in pull_request.checks if check.status == "failure")
            if pull_request is not None
            else ()
        ),
        resumable=availability == "available",
        availability_reason=availability,
    )


def _curation_candidate(pull_request: PullRequest) -> CurationCandidate:
    return CurationCandidate(
        number=pull_request.number,
        head_sha=pull_request.head_sha,
        head_ref_name=pull_request.head_ref_name,
        base_ref_name=pull_request.base_ref_name,
        labels=pull_request.labels,
        changed_paths=pull_request.changed_paths,
        check_state=pull_request.check_state,
        mergeable=pull_request.mergeable,
    )


def _deduplicate_pull_requests(
    pull_requests: Iterable[PullRequest],
) -> tuple[PullRequest, ...]:
    by_number: dict[int, PullRequest] = {}
    for pull_request in pull_requests:
        if pull_request.number in by_number:
            raise _invalid_github_state(
                "GitHub returned a duplicate pull request number"
            )
        by_number[pull_request.number] = pull_request
    return tuple(by_number.values())


def _require_lifecycle(
    pull_requests: Sequence[PullRequest],
    *,
    open_input: bool,
) -> None:
    expected = {"OPEN"} if open_input else {"CLOSED", "MERGED"}
    if any(item.lifecycle_state not in expected for item in pull_requests):
        raise _invalid_github_state("GitHub returned an invalid pull request lifecycle")


def _is_safe_curation_candidate(
    pull_request: PullRequest,
    comments: Sequence[GitHubComment],
) -> bool:
    if (
        not pull_request.routing_labels_valid
        or pull_request.lifecycle_state != "OPEN"
        or pull_request.is_cross_repository
        or pull_request.head_repository_owner != TRUSTED_MAINTAINER_LOGIN
        or pull_request.base_ref_name != "main"
        or not is_safe_codex_branch(pull_request.head_ref_name)
        or not pull_request.changed_paths
        or not all(
            is_allowed_curation_path(path) for path in pull_request.changed_paths
        )
        or "maintainer:proposal" in pull_request.labels
    ):
        return False

    if pull_request.labels.isdisjoint(_SELECTION_HOLD_LABELS):
        return True
    hold_head = trusted_hold_head(pull_request, comments)
    return hold_head is not None and hold_head != pull_request.head_sha


def _proposal_summary(
    pull_request: PullRequest,
    comments: Sequence[GitHubComment],
) -> ProposalSummary:
    state = (
        trusted_machine_state(comments) if pull_request.routing_labels_valid else None
    )
    if state is None or state.candidate_key is None:
        candidate_key = None
        candidate_origin = None
    else:
        candidate_key = state.candidate_key
        candidate_origin = state.candidate_origin
    return ProposalSummary(
        pr_number=pull_request.number,
        lifecycle_state=pull_request.lifecycle_state,
        head_sha=pull_request.head_sha,
        candidate_key=candidate_key,
        candidate_origin=candidate_origin,
    )


def _invalid_github_state(detail: str) -> MaintainerError:
    return MaintainerError(
        reason=ErrorReason.INVALID_GITHUB_STATE,
        stage=ErrorStage.INSPECT,
        detail=detail,
    )


def _invalid_journal_inventory(detail: str) -> MaintainerError:
    return MaintainerError(
        reason=ErrorReason.INVALID_COMMAND,
        stage=ErrorStage.INSPECT,
        detail=detail,
    )

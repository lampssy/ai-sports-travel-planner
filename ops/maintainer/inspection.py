from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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
from ops.maintainer.errors import ErrorReason, ErrorStage, MaintainerError
from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.github import TRUSTED_MAINTAINER_LOGIN, GitHubComment
from ops.maintainer.intent import CATALOG_SECTIONS, is_allowed_curation_path
from ops.maintainer.models import PullRequest
from ops.maintainer.publication import trusted_hold_head, trusted_machine_state
from ops.maintainer.state import (
    ContinuationValidationStatus,
    PushJournal,
    PushPhase,
    ReviewedContinuation,
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


class CurationInventory(_InspectionModel):
    eligible: tuple[CurationCandidate, ...] = ()
    unresolved_pushes: tuple[PushJournal, ...] = ()
    reviewed_continuations: tuple[ReviewedContinuationSummary, ...] = ()


class ReviewedContinuationSummary(_InspectionModel):
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    )
    validation_status: ContinuationValidationStatus
    resumable: bool


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
    unresolved_pushes: tuple[PushJournal, ...] = ()

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
    reviewed_continuations: Sequence[ReviewedContinuation] = (),
) -> CurationInventory:
    journals = _normalize_journals(unresolved_pushes)
    if journals:
        return CurationInventory(unresolved_pushes=journals)
    pull_requests = _deduplicate_pull_requests(pull_requests)
    pull_requests_by_number = {item.number: item for item in pull_requests}

    eligible = tuple(
        sorted(
            (
                _curation_candidate(pull_request)
                for pull_request in pull_requests
                if _is_safe_curation_candidate(
                    pull_request,
                    comments_by_pr.get(pull_request.number, ()),
                )
            ),
            key=lambda pull_request: pull_request.number,
        )
    )
    summaries = tuple(
        ReviewedContinuationSummary(
            pr_number=continuation.pr_number,
            selected_head=continuation.selected_head,
            reviewed_head=continuation.reviewed_head,
            base_head=continuation.sync.base_head,
            report_path=continuation.report_path,
            validation_status=continuation.validation_status,
            resumable=_is_resumable_continuation(
                continuation,
                pull_requests_by_number.get(continuation.pr_number),
                comments_by_pr.get(continuation.pr_number, ()),
            ),
        )
        for continuation in sorted(
            reviewed_continuations,
            key=lambda item: item.pr_number,
        )
        if continuation.pr_number in pull_requests_by_number
    )
    return CurationInventory(
        eligible=eligible,
        reviewed_continuations=summaries,
    )


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
            unresolved_pushes=journals,
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
        unresolved_pushes=journals,
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
        pull_request.lifecycle_state != "OPEN"
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


def _is_resumable_continuation(
    continuation: ReviewedContinuation,
    pull_request: PullRequest | None,
    comments: Sequence[GitHubComment],
) -> bool:
    return (
        pull_request is not None
        and continuation.selected_head == pull_request.head_sha
        and pull_request.labels.isdisjoint(_SELECTION_HOLD_LABELS)
        and _is_safe_curation_candidate(pull_request, comments)
    )


def _proposal_summary(
    pull_request: PullRequest,
    comments: Sequence[GitHubComment],
) -> ProposalSummary:
    state = trusted_machine_state(comments)
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

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from ops.maintainer.git_ops import GuardedSyncResult, RepositorySafetyError
from ops.maintainer.intent import IntentSnapshot, is_allowed_curation_path
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)

_EXPECTED_PR_PATH_PREFIX = "/lampssy/ai-sports-travel-planner/pull/"
_INFERRED_CURATION_BRANCH = re.compile(r"^codex/catalog-curation-[a-z0-9][a-z0-9-]*$")
_BRANCH_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_REPORT_PATH = re.compile(r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_CATALOG_PYTHON_PATH = re.compile(r"^tests/test_catalog_[A-Za-z0-9][A-Za-z0-9_]*\.py$")
_VALIDATION_CONTEXT_TOKEN = object()


class CheckFailureClass(StrEnum):
    """Trusted, caller-supplied classification of an aggregate CI failure."""

    IN_SCOPE_DETERMINISTIC = "in-scope-deterministic"
    INFRASTRUCTURE = "infrastructure"
    STALE_CONTRACT = "stale-contract"
    OUT_OF_LANE = "out-of-lane"
    AMBIGUOUS = "ambiguous"


class DecisionReason(StrEnum):
    """Static reason codes safe to publish without untrusted command output."""

    INELIGIBLE_CURATION_SCOPE = "ineligible-curation-scope"
    NOT_WAITING_CI = "not-waiting-ci"
    REVIEW_STATE_MISSING = "review-state-missing"
    REVIEW_STATE_STALE = "review-state-stale"
    MERGE_CONFLICT = "merge-conflict"
    CI_PENDING = "ci-pending"
    REVIEWED_HEAD_READY = "reviewed-head-ready"
    CI_FAILURE_IN_SCOPE = "ci-failure-in-scope"
    CI_FAILURE_INFRASTRUCTURE = "ci-failure-infrastructure"
    CI_FAILURE_STALE_CONTRACT = "ci-failure-stale-contract"
    CI_FAILURE_OUT_OF_LANE = "ci-failure-out-of-lane"
    CI_FAILURE_AMBIGUOUS = "ci-failure-ambiguous"
    PUBLICATION_INCOMPLETE = "publication-incomplete"
    LINEAGE_CYCLE_LIMIT = "lineage-cycle-limit"
    RUN_CYCLE_LIMIT = "run-cycle-limit"
    CYCLE_ALLOWED = "cycle-allowed"


class CurationPolicyError(RuntimeError):
    """Conflicting trusted inputs prevent a deterministic policy decision."""


class ValidationBindingError(RuntimeError):
    """Validation argv cannot be bound to trusted reviewed state."""


@dataclass(frozen=True)
class CurationWork:
    waiting_ci: tuple[PullRequest, ...]
    deep_pr: PullRequest | None


@dataclass(frozen=True)
class StateDecision:
    state: MaintainerState
    reason: DecisionReason
    repeat_push: bool = False


@dataclass(frozen=True, init=False)
class ValidatedCurationContext:
    """Paths proven against one reviewed intent and immutable base checkout."""

    report_path: str
    changed_python_paths: tuple[str, ...]
    base_dir: Path
    base_sha: str
    reviewed_head: str

    def __init__(
        self,
        *,
        report_path: str,
        changed_python_paths: tuple[str, ...],
        base_dir: Path,
        base_sha: str,
        reviewed_head: str,
        _binding_token: object | None = None,
    ) -> None:
        if _binding_token is not _VALIDATION_CONTEXT_TOKEN:
            raise TypeError(
                "ValidatedCurationContext must come from bind_validation_context"
            )
        object.__setattr__(self, "report_path", report_path)
        object.__setattr__(self, "changed_python_paths", changed_python_paths)
        object.__setattr__(self, "base_dir", base_dir)
        object.__setattr__(self, "base_sha", base_sha)
        object.__setattr__(self, "reviewed_head", reviewed_head)


class ReviewedIntentRepository(Protocol):
    def reviewed_intent(
        self,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot: ...


class ValidationBaseRepository(Protocol):
    root: Path

    def verify_validation_base(self, expected_sha: str) -> None: ...


def classify_catalog_pr(pr: PullRequest) -> MaintainerLane | None:
    """Classify explicit catalog PRs or strict catalog-curation branches."""
    if not _has_only_owned_paths(pr.changed_paths):
        return None
    if pr.lane is MaintainerLane.CATALOG_CURATION:
        return MaintainerLane.CATALOG_CURATION
    if pr.lane is not None:
        return None
    if _INFERRED_CURATION_BRANCH.fullmatch(pr.head_ref_name) is None:
        return None
    return MaintainerLane.CATALOG_CURATION


def is_eligible_for_deep_curation(pr: PullRequest) -> bool:
    """Apply every non-negotiable mutation gate to a catalog PR."""
    return (
        _passes_global_safety_gates(pr)
        and classify_catalog_pr(pr) is MaintainerLane.CATALOG_CURATION
    )


def route_approved_proposal(
    pr: PullRequest,
) -> tuple[MaintainerLane, MaintainerState] | None:
    """Route only a safe discovery PR whose proposal state was removed."""
    if (
        pr.lane is MaintainerLane.CATALOG_DISCOVERY
        and pr.maintainer_state in {None, MaintainerState.WORKING}
        and _passes_global_safety_gates(pr)
    ):
        return MaintainerLane.CATALOG_CURATION, MaintainerState.WORKING
    return None


def select_curation_work(prs: Iterable[PullRequest]) -> CurationWork:
    """Reconcile every safe waiting PR and choose at most one deep PR."""
    items = _deduplicated_prs(prs)
    waiting = tuple(
        sorted(
            (
                pr
                for pr in items
                if pr.maintainer_state is MaintainerState.WAITING_CI
                and is_eligible_for_deep_curation(pr)
            ),
            key=_work_order,
        )
    )
    candidates = [
        pr
        for pr in items
        if (
            is_eligible_for_deep_curation(pr)
            and pr.maintainer_state in {None, MaintainerState.WORKING}
        )
        or route_approved_proposal(pr) is not None
    ]
    candidates.sort(key=_work_order)
    return CurationWork(
        waiting_ci=waiting,
        deep_pr=candidates[0] if candidates else None,
    )


def reconcile_waiting_ci(
    pr: PullRequest,
    machine: MachineState | None,
    *,
    failure_class: CheckFailureClass | None = None,
) -> StateDecision:
    """Reconcile aggregate CI state without inferring failure provenance."""
    if not is_eligible_for_deep_curation(pr):
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.INELIGIBLE_CURATION_SCOPE,
        )
    if pr.maintainer_state is not MaintainerState.WAITING_CI:
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.NOT_WAITING_CI,
        )
    if pr.mergeable == "CONFLICTING":
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.MERGE_CONFLICT,
        )
    if machine is None:
        return StateDecision(
            MaintainerState.WORKING,
            DecisionReason.REVIEW_STATE_MISSING,
        )
    if machine.head_sha != pr.head_sha:
        return StateDecision(
            MaintainerState.WORKING,
            DecisionReason.REVIEW_STATE_STALE,
        )
    if machine.last_publication != "complete":
        return StateDecision(
            MaintainerState.WAITING_CI,
            DecisionReason.PUBLICATION_INCOMPLETE,
        )
    if pr.check_state == "failure":
        return _failed_check_decision(failure_class)
    if pr.check_state == "pending" or pr.mergeable == "UNKNOWN":
        return StateDecision(
            MaintainerState.WAITING_CI,
            DecisionReason.CI_PENDING,
        )
    return StateDecision(
        MaintainerState.READY,
        DecisionReason.REVIEWED_HEAD_READY,
    )


def next_cycle_decision(
    machine: MachineState,
    cycles_this_run: int = 0,
) -> StateDecision:
    """Enforce both per-run and durable lineage remediation limits."""
    if type(cycles_this_run) is not int or cycles_this_run < 0:
        raise ValueError("cycles_this_run must be a non-negative integer")
    if machine.completed_cycles >= 3:
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.LINEAGE_CYCLE_LIMIT,
        )
    if cycles_this_run >= 2:
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.RUN_CYCLE_LIMIT,
        )
    return StateDecision(
        MaintainerState.WORKING,
        DecisionReason.CYCLE_ALLOWED,
    )


def bind_validation_context(
    pr: PullRequest,
    prepared: GuardedSyncResult,
    reviewed_head: str,
    reviewed_repository: ReviewedIntentRepository,
    base_repository: ValidationBaseRepository,
) -> ValidatedCurationContext:
    """Bind validation inputs to one safe PR, reviewed head, and exact base."""
    if (
        not (
            is_eligible_for_deep_curation(pr) or route_approved_proposal(pr) is not None
        )
        or prepared.target_branch != pr.head_ref_name
        or prepared.original_head != pr.head_sha
    ):
        raise ValidationBindingError("prepared state does not match the eligible PR")
    try:
        snapshot = reviewed_repository.reviewed_intent(prepared, reviewed_head)
    except RepositorySafetyError:
        raise ValidationBindingError("reviewed intent is not trusted") from None
    paths = snapshot.changed_paths
    if not paths or any(not is_allowed_curation_path(path) for path in paths):
        raise ValidationBindingError("reviewed intent paths are outside curation scope")
    report_paths = sorted(
        path for path in paths if _REPORT_PATH.fullmatch(path) is not None
    )
    if len(report_paths) != 1:
        raise ValidationBindingError(
            "reviewed intent must contain exactly one curation JSON report"
        )
    python_paths = tuple(
        sorted(path for path in paths if _CATALOG_PYTHON_PATH.fullmatch(path))
    )
    base_dir = base_repository.root
    try:
        resolved_base = base_dir.resolve(strict=True)
    except OSError:
        raise ValidationBindingError("base checkout is not trusted") from None
    if (
        not base_dir.is_absolute()
        or resolved_base != base_dir
        or any(
            ord(character) < 32 or ord(character) == 127 for character in str(base_dir)
        )
    ):
        raise ValidationBindingError("base checkout is not trusted")
    try:
        base_repository.verify_validation_base(prepared.base_head)
    except RepositorySafetyError:
        raise ValidationBindingError("base checkout is not trusted") from None
    return ValidatedCurationContext(
        report_path=report_paths[0],
        changed_python_paths=python_paths,
        base_dir=base_dir,
        base_sha=prepared.base_head,
        reviewed_head=reviewed_head,
        _binding_token=_VALIDATION_CONTEXT_TOKEN,
    )


def validation_commands(
    context: ValidatedCurationContext,
) -> tuple[tuple[str, ...], ...]:
    """Return only the fixed deterministic catalog validation argv set."""
    commands: list[tuple[str, ...]] = [
        (
            "uv",
            "run",
            "--no-config",
            "--no-sync",
            "python",
            "-m",
            "app.data.validate_catalog",
            "--catalog-path",
            "app/data/catalog.json",
            "--trust-manifest-path",
            "app/data/resort_trust_manifest.json",
        ),
        (
            "uv",
            "run",
            "--no-config",
            "--no-sync",
            "python",
            "-m",
            "app.data.validate_catalog_curation",
            "reconcile",
            context.report_path,
            "--base-catalog-path",
            str(context.base_dir / "app/data/catalog.json"),
            "--current-catalog-path",
            "app/data/catalog.json",
            "--base-trust-manifest-path",
            str(context.base_dir / "app/data/resort_trust_manifest.json"),
            "--current-trust-manifest-path",
            "app/data/resort_trust_manifest.json",
            "--require-report-schema-version",
            "2",
            "--product-backlog-path",
            "docs/product-backlog.md",
        ),
        (
            "uv",
            "run",
            "--no-config",
            "--no-sync",
            "pytest",
            "tests/test_catalog_curation.py",
            "tests/test_catalog_curation_backlog.py",
            "tests/test_catalog_curation_reconciliation.py",
            "tests/test_catalog_models.py",
            "tests/test_catalog_trust.py",
            "-q",
        ),
    ]
    if context.changed_python_paths:
        commands.append(
            (
                "uv",
                "run",
                "--no-config",
                "--no-sync",
                "ruff",
                "check",
                *context.changed_python_paths,
            )
        )
    return tuple(commands)


def _passes_global_safety_gates(pr: PullRequest) -> bool:
    return (
        pr.lifecycle_state == "OPEN"
        and not pr.is_cross_repository
        and pr.head_repository_owner == "lampssy"
        and pr.base_ref_name == "main"
        and _is_valid_codex_branch(pr.head_ref_name)
        and pr.maintainer_state is not MaintainerState.PROPOSAL
        and _has_only_owned_paths(pr.changed_paths)
        and _is_expected_repository_pr(pr)
    )


def _is_valid_codex_branch(branch: str) -> bool:
    if not branch.startswith("codex/"):
        return False
    segments = branch.split("/")
    return len(segments) > 1 and all(
        _BRANCH_SEGMENT.fullmatch(segment) is not None
        and not segment.endswith((".", ".lock"))
        for segment in segments
    )


def _has_only_owned_paths(paths: frozenset[str]) -> bool:
    # Task 4 rejects symlinks and unsafe Git modes before exposing these paths.
    return bool(paths) and all(is_allowed_curation_path(path) for path in paths)


def _is_expected_repository_pr(pr: PullRequest) -> bool:
    return (
        pr.url.host == "github.com"
        and pr.url.path == f"{_EXPECTED_PR_PATH_PREFIX}{pr.number}"
    )


def _work_order(pr: PullRequest) -> tuple[datetime, int]:
    return pr.created_at, pr.number


def _deduplicated_prs(prs: Iterable[PullRequest]) -> tuple[PullRequest, ...]:
    unique: dict[int, PullRequest] = {}
    for pr in prs:
        existing = unique.get(pr.number)
        if existing is None:
            unique[pr.number] = pr
        elif existing != pr:
            raise CurationPolicyError(f"conflicting records for PR {pr.number}")
    return tuple(unique[number] for number in sorted(unique))


def _failed_check_decision(
    failure_class: CheckFailureClass | None,
) -> StateDecision:
    if failure_class is CheckFailureClass.IN_SCOPE_DETERMINISTIC:
        return StateDecision(
            MaintainerState.WORKING,
            DecisionReason.CI_FAILURE_IN_SCOPE,
        )
    if failure_class is CheckFailureClass.INFRASTRUCTURE:
        return StateDecision(
            MaintainerState.BLOCKED,
            DecisionReason.CI_FAILURE_INFRASTRUCTURE,
        )
    if failure_class is CheckFailureClass.STALE_CONTRACT:
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.CI_FAILURE_STALE_CONTRACT,
        )
    if failure_class is CheckFailureClass.OUT_OF_LANE:
        return StateDecision(
            MaintainerState.MANUAL_CHECK,
            DecisionReason.CI_FAILURE_OUT_OF_LANE,
        )
    return StateDecision(
        MaintainerState.MANUAL_CHECK,
        DecisionReason.CI_FAILURE_AMBIGUOUS,
    )

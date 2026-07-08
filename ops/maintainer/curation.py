from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from ops.maintainer.git_ops import (
    GitRepository,
    GuardedSyncResult,
    RepositorySafetyError,
)
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
VALIDATION_COMMAND_TIMEOUT_SECONDS = 600.0
_OUTPUT_OBSERVATION_LIMIT = 4096
_PROCESS_GROUP_GRACE_SECONDS = 0.25


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


class ValidationExecutionError(RuntimeError):
    """Live state or a fixed validation command prevented safe completion."""


@dataclass(frozen=True)
class CurationWork:
    waiting_ci: tuple[PullRequest, ...]
    deep_pr: PullRequest | None


@dataclass(frozen=True)
class StateDecision:
    state: MaintainerState
    reason: DecisionReason
    repeat_push: bool = False


@dataclass(frozen=True)
class _ValidationPlan:
    """Internal fixed-argv values, not an authorization capability."""

    report_path: str
    changed_python_paths: tuple[str, ...]
    base_dir: Path
    base_sha: str
    reviewed_head: str


@dataclass(frozen=True)
class ValidationCommandObservation:
    command_index: int
    stdout_characters: int
    stderr_characters: int
    output_truncated: bool


@dataclass(frozen=True)
class ValidationExecutionResult:
    commands_completed: int
    observations: tuple[ValidationCommandObservation, ...]


class ValidationCommandRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]: ...


class _SubprocessValidationRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        if os.name != "posix":
            raise OSError("validation subprocess isolation requires POSIX")
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=False,
            shell=False,
            start_new_session=True,
        )
        process_group = process.pid
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, process_group)
            raise subprocess.TimeoutExpired(list(argv), timeout) from None
        _terminate_process_group(process, process_group)
        return subprocess.CompletedProcess(
            list(argv),
            returncode,
            stdout="",
            stderr="",
        )


def _terminate_process_group(
    process: subprocess.Popen[bytes],
    process_group: int,
) -> None:
    if process_group <= 1 or process_group == os.getpgrp():
        raise OSError("refusing to signal the parent process group")
    _signal_process_group(process_group, signal.SIGTERM)
    try:
        process.wait(timeout=_PROCESS_GROUP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    if _wait_for_process_group_exit(process_group, _PROCESS_GROUP_GRACE_SECONDS):
        process.wait()
        return
    _signal_process_group(process_group, signal.SIGKILL)
    try:
        process.wait(timeout=_PROCESS_GROUP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        _signal_process_group(process_group, signal.SIGKILL)
        process.wait()
    _wait_for_process_group_exit(process_group, _PROCESS_GROUP_GRACE_SECONDS)


def _signal_process_group(process_group: int, requested_signal: int) -> None:
    try:
        os.killpg(process_group, requested_signal)
    except (PermissionError, ProcessLookupError):
        return


def _wait_for_process_group_exit(process_group: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            pass
        time.sleep(0.01)
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


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


def execute_curation_validation(
    pr: PullRequest,
    prepared: GuardedSyncResult,
    reviewed_head: str,
    reviewed_repository: GitRepository,
    base_repository: GitRepository,
    *,
    runner: ValidationCommandRunner | None = None,
) -> ValidationExecutionResult:
    """Execute fixed validation while rechecking live state at every boundary."""
    if not isinstance(reviewed_repository, GitRepository) or not isinstance(
        base_repository, GitRepository
    ):
        raise ValidationExecutionError(
            "validation requires concrete GitRepository instances"
        )
    initial_plan = _revalidate_validation_plan(
        pr,
        prepared,
        reviewed_head,
        reviewed_repository,
        base_repository,
    )
    commands = _validation_argv(initial_plan)
    command_runner = runner or _SubprocessValidationRunner()
    observations: list[ValidationCommandObservation] = []
    for index, command in enumerate(commands, start=1):
        current_plan = _revalidate_validation_plan(
            pr,
            prepared,
            reviewed_head,
            reviewed_repository,
            base_repository,
        )
        if current_plan != initial_plan or _validation_argv(current_plan) != commands:
            raise ValidationExecutionError("reviewed validation plan drifted")
        try:
            result = command_runner.run(
                command,
                cwd=reviewed_repository.root,
                timeout=VALIDATION_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise ValidationExecutionError(
                f"validation command {index} timed out"
            ) from None
        except OSError:
            raise ValidationExecutionError(
                f"validation command {index} could not start"
            ) from None
        if result.returncode != 0:
            raise ValidationExecutionError(
                f"validation command {index} failed"
            ) from None
        observations.append(_observe_command(index, result))
    final_plan = _revalidate_validation_plan(
        pr,
        prepared,
        reviewed_head,
        reviewed_repository,
        base_repository,
    )
    if final_plan != initial_plan:
        raise ValidationExecutionError("reviewed validation plan drifted")
    return ValidationExecutionResult(
        commands_completed=len(commands),
        observations=tuple(observations),
    )


def _derive_validation_plan(
    snapshot: IntentSnapshot,
    base_dir: Path,
    base_sha: str,
    reviewed_head: str,
) -> _ValidationPlan:
    paths = snapshot.changed_paths
    if not paths or any(not is_allowed_curation_path(path) for path in paths):
        raise ValidationExecutionError(
            "reviewed intent paths are outside curation scope"
        )
    report_paths = sorted(
        path for path in paths if _REPORT_PATH.fullmatch(path) is not None
    )
    if len(report_paths) != 1:
        raise ValidationExecutionError(
            "reviewed intent must contain exactly one curation JSON report"
        )
    return _ValidationPlan(
        report_path=report_paths[0],
        changed_python_paths=tuple(
            sorted(path for path in paths if _CATALOG_PYTHON_PATH.fullmatch(path))
        ),
        base_dir=base_dir,
        base_sha=base_sha,
        reviewed_head=reviewed_head,
    )


def _validation_argv(
    plan: _ValidationPlan,
) -> tuple[tuple[str, ...], ...]:
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
            plan.report_path,
            "--base-catalog-path",
            str(plan.base_dir / "app/data/catalog.json"),
            "--current-catalog-path",
            "app/data/catalog.json",
            "--base-trust-manifest-path",
            str(plan.base_dir / "app/data/resort_trust_manifest.json"),
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
    if plan.changed_python_paths:
        commands.append(
            (
                "uv",
                "run",
                "--no-config",
                "--no-sync",
                "ruff",
                "check",
                *plan.changed_python_paths,
            )
        )
    return tuple(commands)


def _revalidate_validation_plan(
    pr: PullRequest,
    prepared: GuardedSyncResult,
    reviewed_head: str,
    reviewed_repository: GitRepository,
    base_repository: GitRepository,
) -> _ValidationPlan:
    if not (
        is_eligible_for_deep_curation(pr) or route_approved_proposal(pr) is not None
    ):
        raise ValidationExecutionError("selected PR is outside curation policy")
    if _has_control_character(str(reviewed_repository.root)):
        raise ValidationExecutionError("reviewed state drifted")
    if _has_control_character(str(base_repository.root)):
        raise ValidationExecutionError("base state drifted")
    try:
        snapshot = reviewed_repository.revalidate_prepared_result(
            pr,
            prepared,
            reviewed_head,
        )
    except RepositorySafetyError:
        raise ValidationExecutionError("reviewed state drifted") from None
    try:
        base_repository.verify_validation_base(prepared.base_head)
    except RepositorySafetyError:
        raise ValidationExecutionError("base state drifted") from None
    return _derive_validation_plan(
        snapshot,
        base_repository.root,
        prepared.base_head,
        reviewed_head,
    )


def _observe_command(
    index: int,
    result: subprocess.CompletedProcess[str],
) -> ValidationCommandObservation:
    stdout = result.stdout if isinstance(result.stdout, str) else ""
    stderr = result.stderr if isinstance(result.stderr, str) else ""
    return ValidationCommandObservation(
        command_index=index,
        stdout_characters=min(len(stdout), _OUTPUT_OBSERVATION_LIMIT),
        stderr_characters=min(len(stderr), _OUTPUT_OBSERVATION_LIMIT),
        output_truncated=(
            len(stdout) > _OUTPUT_OBSERVATION_LIMIT
            or len(stderr) > _OUTPUT_OBSERVATION_LIMIT
        ),
    )


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


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

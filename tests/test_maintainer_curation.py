from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from ops.maintainer.curation import (
    CheckFailureClass,
    CurationPolicyError,
    DecisionReason,
    ValidationExecutionError,
    _derive_validation_plan,
    _SubprocessValidationRunner,
    _validation_argv,
    classify_catalog_pr,
    execute_curation_validation,
    is_eligible_for_deep_curation,
    next_cycle_decision,
    reconcile_waiting_ci,
    route_approved_proposal,
    select_curation_work,
)
from ops.maintainer.git_ops import (
    GitRepository,
    GuardedSyncResult,
    RemotePolicy,
    RepositorySafetyError,
)
from ops.maintainer.intent import IntentSnapshot
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)

pytestmark = pytest.mark.db_free


def make_pr(**changes: Any) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Tignes",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": "codex/catalog-curation-tignes",
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "lifecycle_state": "OPEN",
        "created_at": datetime(2026, 7, 5, tzinfo=UTC),
        "labels": frozenset(),
        "head_sha": "a" * 40,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/2026-07-05-tignes.json",
            }
        ),
        "body": "",
    }
    values.update(changes)
    if "number" in changes and "url" not in changes:
        values["url"] = (
            "https://github.com/lampssy/ai-sports-travel-planner/pull/"
            f"{changes['number']}"
        )
    return PullRequest.model_validate(values)


def machine_state(**changes: object) -> MachineState:
    values: dict[str, object] = {
        "head_sha": "a" * 40,
        "lineage_id": "pr-42-lineage",
        "completed_cycles": 0,
        "last_publication": "complete",
    }
    values.update(changes)
    return MachineState.model_validate(values)


def reviewed_intent(**changes: object) -> IntentSnapshot:
    values: dict[str, object] = {
        "changed_paths": frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/2026-07-05-tignes.json",
                "tests/test_catalog_tignes.py",
            }
        ),
        "catalog_targets": frozenset({"ski_area:tignes"}),
        "report_targets": frozenset({"ski_area:tignes"}),
        "removed_backlog_markers": frozenset(),
    }
    values.update(changes)
    return IntentSnapshot.model_validate(values)


def test_catalog_branch_is_eligible_without_managed_label() -> None:
    pr = make_pr(labels=frozenset())

    assert classify_catalog_pr(pr) is MaintainerLane.CATALOG_CURATION
    assert is_eligible_for_deep_curation(pr)


def test_explicit_catalog_lane_is_eligible_on_a_different_codex_branch() -> None:
    pr = make_pr(
        head_ref_name="codex/tignes-evidence-refresh",
        labels=frozenset({MaintainerLane.CATALOG_CURATION.value}),
    )

    assert classify_catalog_pr(pr) is MaintainerLane.CATALOG_CURATION
    assert is_eligible_for_deep_curation(pr)


def test_explicit_catalog_lane_does_not_override_unowned_paths() -> None:
    pr = make_pr(
        labels=frozenset({MaintainerLane.CATALOG_CURATION.value}),
        changed_paths=frozenset({"README.md"}),
    )

    assert classify_catalog_pr(pr) is None
    assert not is_eligible_for_deep_curation(pr)


@pytest.mark.parametrize(
    "changes",
    [
        {"is_cross_repository": True},
        {"head_repository_owner": "someone-else"},
        {"base_ref_name": "release"},
        {"head_ref_name": "feature/manual"},
        {"head_ref_name": "codex/.hidden"},
        {"labels": frozenset({MaintainerState.PROPOSAL.value})},
        {"changed_paths": frozenset()},
        {"changed_paths": frozenset({"README.md"})},
        {
            "changed_paths": frozenset(
                {"app/data/catalog.json", "app/services/planner.py"}
            )
        },
        {
            "url": "https://github.com/another/repository/pull/42",
        },
    ],
)
def test_ineligible_prs_never_reach_mutation(changes: dict[str, object]) -> None:
    assert not is_eligible_for_deep_curation(make_pr(**changes))


def test_explicit_different_lane_is_not_catalog_curation() -> None:
    pr = make_pr(labels=frozenset({MaintainerLane.CATALOG_DISCOVERY.value}))

    assert classify_catalog_pr(pr) is None
    assert not is_eligible_for_deep_curation(pr)


@pytest.mark.parametrize(
    "path",
    [
        "../app/data/catalog.json",
        "/app/data/catalog.json",
        "docs/catalog-curation/../../app/data/catalog.json",
        "docs/catalog-curation/report.txt",
        "docs/catalog-curation/subdir/report.json",
        "tests/test_catalog_bad-name.py",
        "tests/test_catalog_bad.py\n--help",
        "app/data/catalog.json/extra",
    ],
)
def test_branch_inference_rejects_malformed_or_unowned_paths(path: str) -> None:
    pr = make_pr(changed_paths=frozenset({path}))

    assert classify_catalog_pr(pr) is None
    assert not is_eligible_for_deep_curation(pr)


def test_approved_discovery_proposal_routes_to_curation() -> None:
    pr = make_pr(labels=frozenset({MaintainerLane.CATALOG_DISCOVERY.value}))

    assert route_approved_proposal(pr) == (
        MaintainerLane.CATALOG_CURATION,
        MaintainerState.WORKING,
    )


def test_discovery_route_replaces_a_nonproposal_automation_state() -> None:
    pr = make_pr(
        labels=frozenset(
            {
                MaintainerLane.CATALOG_DISCOVERY.value,
                MaintainerState.WORKING.value,
            }
        )
    )

    assert route_approved_proposal(pr) == (
        MaintainerLane.CATALOG_CURATION,
        MaintainerState.WORKING,
    )


@pytest.mark.parametrize(
    "state",
    [
        MaintainerState.PROPOSAL,
        MaintainerState.WAITING_CI,
        MaintainerState.READY,
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
    ],
)
def test_discovery_human_or_waiting_states_never_route_or_take_deep_slot(
    state: MaintainerState,
) -> None:
    pr = make_pr(
        labels=frozenset(
            {
                MaintainerLane.CATALOG_DISCOVERY.value,
                state.value,
            }
        )
    )

    assert route_approved_proposal(pr) is None
    assert select_curation_work([pr]).deep_pr is None


@pytest.mark.parametrize(
    "changes",
    [
        {
            "labels": frozenset(
                {
                    MaintainerLane.CATALOG_DISCOVERY.value,
                    MaintainerState.PROPOSAL.value,
                }
            )
        },
        {"labels": frozenset()},
        {
            "labels": frozenset({MaintainerLane.CATALOG_DISCOVERY.value}),
            "is_cross_repository": True,
        },
        {
            "labels": frozenset({MaintainerLane.CATALOG_DISCOVERY.value}),
            "changed_paths": frozenset({"README.md"}),
        },
    ],
)
def test_unapproved_or_unsafe_discovery_pr_does_not_route(
    changes: dict[str, object],
) -> None:
    assert route_approved_proposal(make_pr(**changes)) is None


def test_work_selection_reconciles_all_eligible_waiting_and_one_oldest_deep() -> None:
    waiting_new = make_pr(
        number=5,
        created_at=datetime(2026, 7, 3, tzinfo=UTC),
        labels=frozenset(
            {
                MaintainerLane.CATALOG_CURATION.value,
                MaintainerState.WAITING_CI.value,
            }
        ),
    )
    waiting_old = make_pr(
        number=4,
        created_at=datetime(2026, 7, 2, tzinfo=UTC),
        labels=frozenset({MaintainerState.WAITING_CI.value}),
    )
    oldest = make_pr(
        number=2,
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    tie_higher_number = make_pr(
        number=3,
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
    )

    work = select_curation_work([tie_higher_number, waiting_new, oldest, waiting_old])

    assert [item.number for item in work.waiting_ci] == [4, 5]
    assert work.deep_pr is not None
    assert work.deep_pr.number == 2


def test_ineligible_waiting_state_is_not_reconciled() -> None:
    ineligible = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        changed_paths=frozenset({"README.md"}),
    )

    work = select_curation_work([ineligible])

    assert work.waiting_ci == ()
    assert work.deep_pr is None


@pytest.mark.parametrize("lifecycle_state", ["CLOSED", "MERGED"])
def test_nonopen_pr_is_never_selected_or_reconciled(lifecycle_state: str) -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        lifecycle_state=lifecycle_state,
    )

    work = select_curation_work([pr])
    decision = reconcile_waiting_ci(pr, machine_state())

    assert work.waiting_ci == ()
    assert work.deep_pr is None
    assert decision.state is MaintainerState.MANUAL_CHECK
    assert decision.reason is DecisionReason.INELIGIBLE_CURATION_SCOPE


def test_work_selection_normalizes_mixed_offsets_before_ordering() -> None:
    first = make_pr(
        number=8,
        created_at=datetime(
            2026,
            7,
            5,
            12,
            tzinfo=timezone(timedelta(hours=2)),
        ),
    )
    second = make_pr(
        number=7,
        created_at=datetime(2026, 7, 5, 10, 30, tzinfo=UTC),
    )

    work = select_curation_work([second, first])

    assert work.deep_pr == first


def test_work_selection_deduplicates_identical_pr_records() -> None:
    pr = make_pr(number=7)

    work = select_curation_work([pr, pr.model_copy(deep=True)])

    assert work.deep_pr == pr


def test_work_selection_rejects_conflicting_duplicate_pr_records() -> None:
    first = make_pr(number=7)
    conflicting = make_pr(number=7, head_sha="b" * 40)

    with pytest.raises(CurationPolicyError, match="conflicting records for PR 7"):
        select_curation_work([first, conflicting])


def test_approved_discovery_routes_into_the_deep_slot() -> None:
    approved = make_pr(
        number=7,
        labels=frozenset({MaintainerLane.CATALOG_DISCOVERY.value}),
    )

    work = select_curation_work([approved])

    assert work.waiting_ci == ()
    assert work.deep_pr == approved


@pytest.mark.parametrize(
    "state",
    [
        MaintainerState.READY,
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
    ],
)
def test_terminal_or_human_gated_pr_is_not_selected_for_deep_work(
    state: MaintainerState,
) -> None:
    pr = make_pr(labels=frozenset({state.value}))

    assert select_curation_work([pr]).deep_pr is None


def test_missing_or_stale_machine_state_requires_fresh_review_without_push() -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
    )

    missing = reconcile_waiting_ci(pr, None)
    stale = reconcile_waiting_ci(pr, machine_state(head_sha="b" * 40))

    assert missing.state is MaintainerState.WORKING
    assert missing.reason is DecisionReason.REVIEW_STATE_MISSING
    assert stale.state is MaintainerState.WORKING
    assert stale.reason is DecisionReason.REVIEW_STATE_STALE
    assert not missing.repeat_push
    assert not stale.repeat_push


def test_conflicting_waiting_pr_requires_manual_check() -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        mergeable="CONFLICTING",
    )

    decision = reconcile_waiting_ci(pr, machine_state())

    assert decision.state is MaintainerState.MANUAL_CHECK
    assert decision.reason is DecisionReason.MERGE_CONFLICT


@pytest.mark.parametrize(
    "changes",
    [
        {"check_state": "pending", "mergeable": "MERGEABLE"},
        {"check_state": "success", "mergeable": "UNKNOWN"},
    ],
)
def test_pending_checks_or_mergeability_stays_waiting(
    changes: dict[str, object],
) -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        **changes,
    )

    decision = reconcile_waiting_ci(pr, machine_state())

    assert decision.state is MaintainerState.WAITING_CI
    assert decision.reason is DecisionReason.CI_PENDING


def test_exact_reviewed_green_mergeable_head_becomes_ready() -> None:
    pr = make_pr(labels=frozenset({MaintainerState.WAITING_CI.value}))

    decision = reconcile_waiting_ci(pr, machine_state())

    assert decision.state is MaintainerState.READY
    assert decision.reason is DecisionReason.REVIEWED_HEAD_READY


@pytest.mark.parametrize("last_publication", ["none", "body", "comment", "labels"])
def test_partial_publication_never_becomes_ready(
    last_publication: str,
) -> None:
    pr = make_pr(labels=frozenset({MaintainerState.WAITING_CI.value}))

    decision = reconcile_waiting_ci(
        pr,
        machine_state(last_publication=last_publication),
    )

    assert decision.state is MaintainerState.WAITING_CI
    assert decision.reason is DecisionReason.PUBLICATION_INCOMPLETE
    assert not decision.repeat_push


def test_failed_check_reenters_work_only_for_explicit_in_scope_failure() -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        check_state="failure",
    )

    decision = reconcile_waiting_ci(
        pr,
        machine_state(),
        failure_class=CheckFailureClass.IN_SCOPE_DETERMINISTIC,
    )

    assert decision.state is MaintainerState.WORKING
    assert decision.reason is DecisionReason.CI_FAILURE_IN_SCOPE


@pytest.mark.parametrize(
    ("failure_class", "state", "reason"),
    [
        (
            None,
            MaintainerState.MANUAL_CHECK,
            DecisionReason.CI_FAILURE_AMBIGUOUS,
        ),
        (
            CheckFailureClass.AMBIGUOUS,
            MaintainerState.MANUAL_CHECK,
            DecisionReason.CI_FAILURE_AMBIGUOUS,
        ),
        (
            CheckFailureClass.INFRASTRUCTURE,
            MaintainerState.BLOCKED,
            DecisionReason.CI_FAILURE_INFRASTRUCTURE,
        ),
        (
            CheckFailureClass.STALE_CONTRACT,
            MaintainerState.MANUAL_CHECK,
            DecisionReason.CI_FAILURE_STALE_CONTRACT,
        ),
        (
            CheckFailureClass.OUT_OF_LANE,
            MaintainerState.MANUAL_CHECK,
            DecisionReason.CI_FAILURE_OUT_OF_LANE,
        ),
    ],
)
def test_failed_check_fail_closed_without_trusted_in_scope_classification(
    failure_class: CheckFailureClass | None,
    state: MaintainerState,
    reason: DecisionReason,
) -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        check_state="failure",
    )

    decision = reconcile_waiting_ci(
        pr,
        machine_state(),
        failure_class=failure_class,
    )

    assert decision.state is state
    assert decision.reason is reason


def test_ineligible_waiting_pr_never_reenters_work_on_failed_ci() -> None:
    pr = make_pr(
        labels=frozenset({MaintainerState.WAITING_CI.value}),
        changed_paths=frozenset({"README.md"}),
        check_state="failure",
    )

    decision = reconcile_waiting_ci(
        pr,
        machine_state(),
        failure_class=CheckFailureClass.IN_SCOPE_DETERMINISTIC,
    )

    assert decision.state is MaintainerState.MANUAL_CHECK
    assert decision.reason is DecisionReason.INELIGIBLE_CURATION_SCOPE


@pytest.mark.parametrize(
    ("completed_cycles", "cycles_this_run", "state", "reason"),
    [
        (0, 0, MaintainerState.WORKING, DecisionReason.CYCLE_ALLOWED),
        (2, 0, MaintainerState.WORKING, DecisionReason.CYCLE_ALLOWED),
        (2, 1, MaintainerState.WORKING, DecisionReason.CYCLE_ALLOWED),
        (3, 0, MaintainerState.MANUAL_CHECK, DecisionReason.LINEAGE_CYCLE_LIMIT),
        (0, 2, MaintainerState.MANUAL_CHECK, DecisionReason.RUN_CYCLE_LIMIT),
        (2, 2, MaintainerState.MANUAL_CHECK, DecisionReason.RUN_CYCLE_LIMIT),
    ],
)
def test_cycle_boundaries(
    completed_cycles: int,
    cycles_this_run: int,
    state: MaintainerState,
    reason: DecisionReason,
) -> None:
    decision = next_cycle_decision(
        machine_state(completed_cycles=completed_cycles),
        cycles_this_run=cycles_this_run,
    )

    assert decision.state is state
    assert decision.reason is reason


@pytest.mark.parametrize("value", [-1, True, 1.0, float("nan"), "1"])
def test_cycle_count_rejects_invalid_run_values(value: object) -> None:
    with pytest.raises(ValueError, match="cycles_this_run"):
        next_cycle_decision(machine_state(), cycles_this_run=value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class LocalRemotePolicy(RemotePolicy):
    expected_url: str

    def validate(
        self,
        fetch_urls: tuple[str, ...],
        push_urls: tuple[str, ...],
        *,
        resolve_ssh: object,
    ) -> None:
        del resolve_ssh
        if fetch_urls != (self.expected_url,) or push_urls != (self.expected_url,):
            raise RepositorySafetyError("test remote mismatch")


@dataclass(frozen=True)
class ValidationRepositories:
    pr: PullRequest
    prepared: GuardedSyncResult
    reviewed_head: str
    reviewed: GitRepository
    base: GitRepository


@dataclass
class RecordingValidationRunner:
    returncodes: tuple[int, ...] = ()
    mutation: Callable[[int], None] | None = None
    calls: list[tuple[tuple[str, ...], Path, float]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        command = tuple(argv)
        self.calls.append((command, cwd, timeout))
        call_number = len(self.calls)
        if self.mutation is not None:
            self.mutation(call_number)
        returncode = (
            self.returncodes[call_number - 1]
            if call_number <= len(self.returncodes)
            else 0
        )
        return subprocess.CompletedProcess(
            command,
            returncode,
            stdout="secret-output" * 500,
            stderr="private-error" * 500,
        )


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return result.stdout.strip()


def _valid_report() -> dict[str, object]:
    return {
        "report_schema_version": 2,
        "title": "Alpha full curation",
        "summary": "Reviews Alpha against its official source.",
        "reviewed_targets": [
            {
                "target_type": "ski_area",
                "target_id": "alpha",
                "scope": "narrow",
                "required_field_paths": ["name"],
            },
            {
                "target_type": "trust_manifest",
                "target_id": "ski_areas:alpha",
                "scope": "narrow",
                "required_field_paths": ["display_name"],
            },
        ],
        "entity_scope_assessments": [
            {
                "candidate_id": "alpha",
                "candidate_name": "Alpha",
                "candidate_kind": "ski_area",
                "disposition": "represented",
                "signals": ["official_independent_identity"],
                "evidence_refs": ["alpha-scope"],
                "target_refs": [
                    {"target_type": "ski_area", "target_id": "alpha"},
                ],
                "rationale": "The official source confirms the represented entity.",
            }
        ],
        "evidence": [
            {
                "evidence_id": "alpha-scope",
                "target_type": "ski_area",
                "target_id": "alpha",
                "field_path": "name",
                "source_type": "official",
                "source_url": "https://example.com/alpha",
                "source_title": "Official Alpha",
                "source_value": "Alpha",
                "evidence_summary": "Confirms Alpha's independent identity.",
            }
        ],
        "field_coverage": [
            {
                "target_type": "ski_area",
                "target_id": "alpha",
                "field_path": "name",
                "status": "reviewed-no-change",
            },
            {
                "target_type": "trust_manifest",
                "target_id": "ski_areas:alpha",
                "field_path": "display_name",
                "status": "reviewed-no-change",
            },
        ],
    }


def _validation_repositories(tmp_path: Path) -> ValidationRepositories:
    reviewed_root = (tmp_path / "reviewed").resolve()
    reviewed_root.mkdir()
    _git(reviewed_root, "init", "-b", "main")
    _git(reviewed_root, "config", "user.name", "Snowcast Test")
    _git(reviewed_root, "config", "user.email", "snowcast@example.test")
    _git(reviewed_root, "config", "commit.gpgSign", "false")
    remote_url = str((tmp_path / "origin.git").resolve())
    _git(reviewed_root, "remote", "add", "origin", remote_url)

    data_dir = reviewed_root / "app/data"
    data_dir.mkdir(parents=True)
    (data_dir / "catalog.json").write_text("{}\n", encoding="utf-8")
    (data_dir / "resort_trust_manifest.json").write_text("{}\n", encoding="utf-8")
    _git(reviewed_root, "add", ".")
    _git(reviewed_root, "commit", "-m", "base")
    base_head = _git(reviewed_root, "rev-parse", "HEAD")

    branch = "codex/catalog-curation-alpha"
    _git(reviewed_root, "switch", "-c", branch)
    report_path = "docs/catalog-curation/alpha.json"
    report = reviewed_root / report_path
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps(_valid_report()), encoding="utf-8")
    test_path = reviewed_root / "tests/test_catalog_alpha.py"
    test_path.parent.mkdir()
    test_path.write_text("def test_alpha():\n    assert True\n", encoding="utf-8")
    _git(reviewed_root, "add", ".")
    _git(reviewed_root, "commit", "-m", "curate alpha")
    original_head = _git(reviewed_root, "rev-parse", "HEAD")
    backup_ref = (
        f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{original_head[:12]}"
    )
    prepared_ref = (
        f"refs/snowcast-maintainer/prepared/pr-42/{base_head[:12]}-{original_head[:12]}"
    )
    _git(reviewed_root, "update-ref", backup_ref, original_head)
    _git(reviewed_root, "update-ref", prepared_ref, original_head)

    base_root = (tmp_path / "base").resolve()
    _git(reviewed_root, "worktree", "add", "--detach", str(base_root), base_head)
    policy = LocalRemotePolicy(remote_url)
    reviewed = GitRepository(reviewed_root, remote_policy=policy)
    base = GitRepository(base_root, remote_policy=policy)
    pr = make_pr(
        title="Curate Alpha",
        head_ref_name=branch,
        head_sha=original_head,
        changed_paths=frozenset({report_path, "tests/test_catalog_alpha.py"}),
    )
    prepared = GuardedSyncResult(
        target_branch=branch,
        original_head=original_head,
        rebased_head=original_head,
        backup_ref=backup_ref,
        prepared_ref=prepared_ref,
        base_head=base_head,
        merge_base=base_head,
    )
    return ValidationRepositories(
        pr=pr,
        prepared=prepared,
        reviewed_head=original_head,
        reviewed=reviewed,
        base=base,
    )


def _execute(
    repositories: ValidationRepositories,
    runner: RecordingValidationRunner,
) -> object:
    return execute_curation_validation(
        repositories.pr,
        repositories.prepared,
        repositories.reviewed_head,
        repositories.reviewed,
        repositories.base,
        runner=runner,
    )


def test_validation_executor_runs_only_exact_fixed_argv(tmp_path: Path) -> None:
    repositories = _validation_repositories(tmp_path)
    runner = RecordingValidationRunner()

    result = _execute(repositories, runner)

    commands = tuple(call[0] for call in runner.calls)
    assert result.commands_completed == 4
    assert commands == _validation_argv(
        _derive_validation_plan(
            repositories.reviewed.revalidate_prepared_result(
                repositories.pr,
                repositories.prepared,
                repositories.reviewed_head,
            ),
            repositories.base.root,
            repositories.prepared.base_head,
            repositories.reviewed_head,
        )
    )
    assert all(
        command[:4] == ("uv", "run", "--no-config", "--no-sync") for command in commands
    )
    assert all(call[1] == repositories.reviewed.root for call in runner.calls)
    assert all(call[2] > 0 for call in runner.calls)
    flattened = " ".join(part for command in commands for part in command).lower()
    for forbidden in ("bootstrap_database", "deploy", "pip", "install", "pr body"):
        assert forbidden not in flattened
    assert "secret-output" not in repr(result)
    assert "private-error" not in repr(result)
    assert all(item.stdout_characters == 4096 for item in result.observations)
    assert all(item.stderr_characters == 4096 for item in result.observations)
    assert all(item.output_truncated for item in result.observations)


def test_validation_executor_accepts_safely_routed_discovery_pr(
    tmp_path: Path,
) -> None:
    repositories = _validation_repositories(tmp_path)
    approved = repositories.pr.model_copy(
        update={"labels": frozenset({MaintainerLane.CATALOG_DISCOVERY.value})}
    )
    runner = RecordingValidationRunner()

    result = execute_curation_validation(
        approved,
        repositories.prepared,
        repositories.reviewed_head,
        repositories.reviewed,
        repositories.base,
        runner=runner,
    )

    assert result.commands_completed == 4


@pytest.mark.parametrize(
    "changed_paths",
    [
        frozenset({"app/data/catalog.json"}),
        frozenset(
            {
                "docs/catalog-curation/one.json",
                "docs/catalog-curation/two.json",
            }
        ),
        frozenset(
            {
                "docs/catalog-curation/report.json",
                "tests/test_catalog_bad.py\n--help",
            }
        ),
    ],
)
def test_private_plan_derivation_fails_closed_on_unsafe_or_ambiguous_paths(
    changed_paths: frozenset[str],
    tmp_path: Path,
) -> None:
    snapshot = reviewed_intent(changed_paths=changed_paths)

    with pytest.raises(ValidationExecutionError):
        _derive_validation_plan(snapshot, tmp_path, "a" * 40, "b" * 40)


def test_private_plan_omits_ruff_without_reviewed_python_paths(
    tmp_path: Path,
) -> None:
    snapshot = reviewed_intent(
        changed_paths=frozenset({"docs/catalog-curation/report.json"})
    )

    commands = _validation_argv(
        _derive_validation_plan(snapshot, tmp_path, "a" * 40, "b" * 40)
    )

    assert len(commands) == 3
    assert all("ruff" not in command for command in commands)


def test_executor_rejects_non_repository_arguments_before_commands(
    tmp_path: Path,
) -> None:
    repositories = _validation_repositories(tmp_path)
    runner = RecordingValidationRunner()

    with pytest.raises(ValidationExecutionError, match="concrete GitRepository"):
        execute_curation_validation(
            repositories.pr,
            repositories.prepared,
            repositories.reviewed_head,
            object(),  # type: ignore[arg-type]
            repositories.base,
            runner=runner,
        )

    assert runner.calls == []


def test_mutation_after_initial_validation_runs_zero_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = _validation_repositories(tmp_path)
    runner = RecordingValidationRunner()
    original = GitRepository.revalidate_prepared_result
    calls = 0

    def mutate_after_first(
        repository: GitRepository,
        pr: PullRequest,
        prepared: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot:
        nonlocal calls
        snapshot = original(repository, pr, prepared, reviewed_head)
        if repository is repositories.reviewed:
            calls += 1
            if calls == 1:
                path = repository.root / "tests/test_catalog_alpha.py"
                path.write_text("# drift\n", encoding="utf-8")
        return snapshot

    monkeypatch.setattr(
        GitRepository,
        "revalidate_prepared_result",
        mutate_after_first,
    )

    with pytest.raises(ValidationExecutionError, match="reviewed state drifted"):
        _execute(repositories, runner)

    assert runner.calls == []


def test_mutation_between_commands_stops_subsequent_commands(
    tmp_path: Path,
) -> None:
    repositories = _validation_repositories(tmp_path)

    def mutate(call_number: int) -> None:
        if call_number == 1:
            path = repositories.base.root / "app/data/catalog.json"
            path.write_text('{"drift": true}\n', encoding="utf-8")

    runner = RecordingValidationRunner(mutation=mutate)

    with pytest.raises(ValidationExecutionError, match="base state drifted"):
        _execute(repositories, runner)

    assert len(runner.calls) == 1


def test_mutation_after_final_command_never_reports_success(tmp_path: Path) -> None:
    repositories = _validation_repositories(tmp_path)

    def mutate(call_number: int) -> None:
        if call_number == 4:
            path = repositories.reviewed.root / "tests/test_catalog_alpha.py"
            path.write_text("# final drift\n", encoding="utf-8")

    runner = RecordingValidationRunner(mutation=mutate)

    with pytest.raises(ValidationExecutionError, match="reviewed state drifted"):
        _execute(repositories, runner)

    assert len(runner.calls) == 4


def test_command_failure_is_sanitized_and_stops_execution(tmp_path: Path) -> None:
    repositories = _validation_repositories(tmp_path)
    runner = RecordingValidationRunner(returncodes=(1,))

    with pytest.raises(
        ValidationExecutionError, match="validation command 1 failed"
    ) as error:
        _execute(repositories, runner)

    assert len(runner.calls) == 1
    assert "secret-output" not in str(error.value)
    assert "private-error" not in str(error.value)


def test_timeout_is_sanitized_and_stops_execution(tmp_path: Path) -> None:
    repositories = _validation_repositories(tmp_path)

    class TimeoutRunner(RecordingValidationRunner):
        def run(
            self,
            argv: Sequence[str],
            *,
            cwd: Path,
            timeout: float,
        ) -> subprocess.CompletedProcess[str]:
            self.calls.append((tuple(argv), cwd, timeout))
            raise subprocess.TimeoutExpired(["secret", "command"], timeout)

    runner = TimeoutRunner()

    with pytest.raises(ValidationExecutionError, match="timed out") as error:
        _execute(repositories, runner)

    assert len(runner.calls) == 1
    assert "secret" not in str(error.value)


def test_default_validation_runner_is_shell_free_timed_and_output_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        stdout = kwargs["stdout"]
        stderr = kwargs["stderr"]
        stdout.write("x" * 5000)  # type: ignore[union-attr]
        stderr.write("y" * 5000)  # type: ignore[union-attr]
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = _SubprocessValidationRunner().run(
        ("uv", "run", "--no-sync", "true"),
        cwd=tmp_path,
        timeout=17.0,
    )

    assert captured["shell"] is False
    assert captured["timeout"] == 17.0
    assert len(result.stdout) == 4097
    assert len(result.stderr) == 4097


def test_model_copy_of_prepared_fields_fails_live_provenance_validation(
    tmp_path: Path,
) -> None:
    repositories = _validation_repositories(tmp_path)
    mutations = [
        ("target_branch", "codex/catalog-curation-other"),
        ("original_head", "f" * 40),
        ("rebased_head", "f" * 40),
        (
            "backup_ref",
            "refs/snowcast-maintainer/backups/pr-42/20260709T100000Z-ffffffffffff",
        ),
        (
            "prepared_ref",
            "refs/snowcast-maintainer/prepared/pr-42/ffffffffffff-ffffffffffff",
        ),
        ("base_head", "f" * 40),
        ("merge_base", "f" * 40),
    ]

    for field_name, value in mutations:
        forged = repositories.prepared.model_copy(update={field_name: value})
        with pytest.raises(RepositorySafetyError):
            repositories.reviewed.revalidate_prepared_result(
                repositories.pr,
                forged,
                repositories.reviewed_head,
            )


def test_public_module_has_no_raw_validation_plan_execution_api() -> None:
    from ops.maintainer import curation

    assert not hasattr(curation, "validation_commands")
    assert not hasattr(curation, "bind_validation_context")
    assert not hasattr(curation, "ValidatedCurationContext")

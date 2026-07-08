from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from ops.maintainer.curation import (
    CheckFailureClass,
    CurationPolicyError,
    DecisionReason,
    ValidatedCurationContext,
    ValidationBindingError,
    bind_validation_context,
    classify_catalog_pr,
    is_eligible_for_deep_curation,
    next_cycle_decision,
    reconcile_waiting_ci,
    route_approved_proposal,
    select_curation_work,
    validation_commands,
)
from ops.maintainer.git_ops import GuardedSyncResult, RepositorySafetyError
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


def sync_result(**changes: object) -> GuardedSyncResult:
    values: dict[str, object] = {
        "target_branch": "codex/catalog-curation-tignes",
        "original_head": "a" * 40,
        "rebased_head": "b" * 40,
        "backup_ref": (
            "refs/snowcast-maintainer/backups/pr-42/20260705T000000Z-aaaaaaaaaaaa"
        ),
        "base_head": "c" * 40,
        "merge_base": "d" * 40,
    }
    values.update(changes)
    return GuardedSyncResult.model_validate(values)


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


@dataclass
class FakeReviewedRepository:
    snapshot: IntentSnapshot = field(default_factory=reviewed_intent)
    failure: Exception | None = None
    calls: list[tuple[GuardedSyncResult, str]] = field(default_factory=list)

    def reviewed_intent(
        self,
        prepared: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot:
        self.calls.append((prepared, reviewed_head))
        if self.failure is not None:
            raise self.failure
        return self.snapshot


@dataclass
class FakeBaseRepository:
    root: Path
    failure: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def verify_validation_base(self, expected_sha: str) -> None:
        self.calls.append(expected_sha)
        if self.failure is not None:
            raise self.failure


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


def bind_context(
    tmp_path: Path,
    *,
    snapshot: IntentSnapshot | None = None,
    reviewed_repository: FakeReviewedRepository | None = None,
    base_repository: FakeBaseRepository | None = None,
    pr: PullRequest | None = None,
    prepared: GuardedSyncResult | None = None,
) -> ValidatedCurationContext:
    return bind_validation_context(
        pr or make_pr(),
        prepared or sync_result(),
        "e" * 40,
        reviewed_repository
        or FakeReviewedRepository(snapshot=snapshot or reviewed_intent()),
        base_repository or FakeBaseRepository(tmp_path),
    )


def test_validation_context_binds_immutable_intent_and_base(
    tmp_path: Path,
) -> None:
    reviewed_repository = FakeReviewedRepository()
    base_repository = FakeBaseRepository(tmp_path)
    prepared = sync_result()

    context = bind_context(
        tmp_path,
        reviewed_repository=reviewed_repository,
        base_repository=base_repository,
        prepared=prepared,
    )

    assert context.report_path == "docs/catalog-curation/2026-07-05-tignes.json"
    assert context.changed_python_paths == ("tests/test_catalog_tignes.py",)
    assert context.base_dir == tmp_path
    assert context.base_sha == prepared.base_head
    assert context.reviewed_head == "e" * 40
    assert reviewed_repository.calls == [(prepared, "e" * 40)]
    assert base_repository.calls == [prepared.base_head]


def test_validation_context_cannot_be_constructed_without_binding() -> None:
    with pytest.raises(TypeError, match="bind_validation_context"):
        ValidatedCurationContext(  # type: ignore[call-arg]
            report_path="docs/catalog-curation/forged.json",
            changed_python_paths=("tests/test_catalog_forged.py",),
            base_dir=Path("/tmp/forged"),
            base_sha="a" * 40,
            reviewed_head="b" * 40,
        )


def test_validation_context_accepts_safely_routed_discovery_pr(
    tmp_path: Path,
) -> None:
    approved_discovery = make_pr(
        labels=frozenset({MaintainerLane.CATALOG_DISCOVERY.value})
    )

    context = bind_context(tmp_path, pr=approved_discovery)

    assert context.reviewed_head == "e" * 40


def test_validation_commands_are_exact_fixed_argv(tmp_path: Path) -> None:
    report = "docs/catalog-curation/2026-07-05-tignes.json"
    snapshot = reviewed_intent(
        changed_paths=frozenset(
            {
                "app/data/catalog.json",
                report,
                "tests/test_catalog_zeta.py",
                "tests/test_catalog_alpha.py",
            }
        )
    )

    commands = validation_commands(bind_context(tmp_path, snapshot=snapshot))

    assert commands == (
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
            str(report),
            "--base-catalog-path",
            str(tmp_path / "app/data/catalog.json"),
            "--current-catalog-path",
            "app/data/catalog.json",
            "--base-trust-manifest-path",
            str(tmp_path / "app/data/resort_trust_manifest.json"),
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
        (
            "uv",
            "run",
            "--no-config",
            "--no-sync",
            "ruff",
            "check",
            "tests/test_catalog_alpha.py",
            "tests/test_catalog_zeta.py",
        ),
    )

    assert all(
        command[:4] == ("uv", "run", "--no-config", "--no-sync") for command in commands
    )


def test_validation_commands_omit_ruff_when_no_python_paths(tmp_path: Path) -> None:
    snapshot = reviewed_intent(
        changed_paths=frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/report.json",
            }
        )
    )
    commands = validation_commands(bind_context(tmp_path, snapshot=snapshot))

    assert len(commands) == 3


@pytest.mark.parametrize(
    "report",
    [
        Path("../report.json"),
        Path("/tmp/report.json"),
        Path("docs/catalog-curation/subdir/report.json"),
        Path("docs/catalog-curation/report.md"),
        Path("docs/catalog-curation/--help.json"),
        Path("docs/catalog-curation/report\n.json"),
    ],
)
def test_validation_commands_reject_report_path_attacks(
    report: Path,
    tmp_path: Path,
) -> None:
    snapshot = reviewed_intent(
        changed_paths=frozenset({"app/data/catalog.json", str(report)})
    )

    with pytest.raises(
        ValidationBindingError,
        match="reviewed intent paths|exactly one",
    ):
        bind_context(tmp_path, snapshot=snapshot)


def test_validation_context_requires_exactly_one_reviewed_json_report(
    tmp_path: Path,
) -> None:
    no_report = reviewed_intent(changed_paths=frozenset({"app/data/catalog.json"}))
    two_reports = reviewed_intent(
        changed_paths=frozenset(
            {
                "docs/catalog-curation/one.json",
                "docs/catalog-curation/two.json",
            }
        )
    )

    with pytest.raises(ValidationBindingError, match="exactly one"):
        bind_context(tmp_path, snapshot=no_report)
    with pytest.raises(ValidationBindingError, match="exactly one"):
        bind_context(tmp_path, snapshot=two_reports)


def test_validation_context_rejects_stale_or_invalid_base_checkout(
    tmp_path: Path,
) -> None:
    base = FakeBaseRepository(
        tmp_path,
        failure=RepositorySafetyError("untrusted detailed error"),
    )

    with pytest.raises(ValidationBindingError, match="base checkout is not trusted"):
        bind_context(tmp_path, base_repository=base)


def test_validation_context_rejects_symlink_or_control_base_root(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "linked"
    symlink.symlink_to(target, target_is_directory=True)
    control = tmp_path / "base\ncontrol"
    control.mkdir()

    for root in (symlink, control):
        base = FakeBaseRepository(root)
        with pytest.raises(
            ValidationBindingError,
            match="base checkout is not trusted",
        ):
            bind_context(tmp_path, base_repository=base)
        assert base.calls == []


def test_validation_context_rejects_unbound_reviewed_state(tmp_path: Path) -> None:
    reviewed = FakeReviewedRepository(
        failure=RepositorySafetyError("untrusted detailed error")
    )

    with pytest.raises(ValidationBindingError, match="reviewed intent is not trusted"):
        bind_context(tmp_path, reviewed_repository=reviewed)


def test_validation_context_rejects_preparation_for_another_pr(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationBindingError, match="prepared state does not match"):
        bind_context(
            tmp_path,
            prepared=sync_result(target_branch="codex/catalog-curation-other"),
        )


@pytest.mark.parametrize(
    "python_path",
    [
        "../tests/test_catalog_escape.py",
        "/tmp/test_catalog_escape.py",
        "tests/test_catalog_bad-name.py",
        "tests/test_catalog_subdir/test_catalog_bad.py",
        "tests/test_catalog_bad.py\n--help",
        "app/data/validate_catalog.py",
        "tests/test_catalog_good.py\x00bad",
    ],
)
def test_validation_commands_reject_python_path_attacks(
    python_path: str,
    tmp_path: Path,
) -> None:
    snapshot = reviewed_intent(
        changed_paths=frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/report.json",
                python_path,
            }
        )
    )

    with pytest.raises(ValidationBindingError, match="reviewed intent paths"):
        bind_context(tmp_path, snapshot=snapshot)


def test_validation_commands_never_include_forbidden_operations(
    tmp_path: Path,
) -> None:
    commands = validation_commands(bind_context(tmp_path))
    flattened = " ".join(part for command in commands for part in command).lower()

    for forbidden in (
        "bootstrap_database",
        "deploy",
        "pip",
        "install",
        "pr body",
        "markdown-output",
    ):
        assert forbidden not in flattened

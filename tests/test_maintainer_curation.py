from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ops.maintainer.curation import (
    CheckFailureClass,
    CommandValidationError,
    DecisionReason,
    classify_catalog_pr,
    is_eligible_for_deep_curation,
    next_cycle_decision,
    reconcile_waiting_ci,
    route_approved_proposal,
    select_curation_work,
    validation_commands,
)
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


@pytest.mark.parametrize("value", [-1, True])
def test_cycle_count_rejects_invalid_run_values(value: int) -> None:
    with pytest.raises(ValueError, match="cycles_this_run"):
        next_cycle_decision(machine_state(), cycles_this_run=value)


def test_validation_commands_are_exact_fixed_argv(tmp_path: Path) -> None:
    report = Path("docs/catalog-curation/2026-07-05-tignes.json")

    commands = validation_commands(
        report,
        tmp_path,
        changed_python_paths=(
            "tests/test_catalog_zeta.py",
            "tests/test_catalog_alpha.py",
            "tests/test_catalog_alpha.py",
        ),
    )

    assert commands == (
        (
            "uv",
            "run",
            "--no-config",
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
            "ruff",
            "check",
            "tests/test_catalog_alpha.py",
            "tests/test_catalog_zeta.py",
        ),
    )


def test_validation_commands_omit_ruff_when_no_python_paths(tmp_path: Path) -> None:
    commands = validation_commands(
        Path("docs/catalog-curation/report.json"),
        tmp_path,
    )

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
    with pytest.raises(CommandValidationError, match="report_path"):
        validation_commands(report, tmp_path)


@pytest.mark.parametrize(
    "base_dir",
    [
        Path("relative-base"),
        Path("/"),
        Path("/tmp/base/../escape"),
        Path("/tmp/base\n--help"),
    ],
)
def test_validation_commands_reject_base_directory_attacks(
    base_dir: Path,
) -> None:
    with pytest.raises(CommandValidationError, match="base_dir"):
        validation_commands(
            Path("docs/catalog-curation/report.json"),
            base_dir,
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
    with pytest.raises(CommandValidationError, match="changed_python_paths"):
        validation_commands(
            Path("docs/catalog-curation/report.json"),
            tmp_path,
            changed_python_paths=(python_path,),
        )


def test_validation_commands_never_include_forbidden_operations(
    tmp_path: Path,
) -> None:
    commands = validation_commands(
        Path("docs/catalog-curation/report.json"),
        tmp_path,
        changed_python_paths=("tests/test_catalog_safe.py",),
    )
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

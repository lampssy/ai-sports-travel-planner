from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.errors import MaintainerError
from ops.maintainer.git_ops import GuardedSyncResult
from ops.maintainer.github import GitHubComment
from ops.maintainer.inspection import (
    catalog_entity_keys,
    inspect_curation,
    inspect_discovery,
)
from ops.maintainer.models import CheckSummary, MachineState, OutcomeState, PullRequest
from ops.maintainer.publication import render_machine_state, render_outcome_state
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
    remediation_supersedes_reviewed,
)

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
NOW = datetime(2026, 7, 8, 10, tzinfo=UTC)


def _pull_request(number: int = 42, **overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": number,
        "title": f"Catalog PR {number}",
        "url": (f"https://github.com/lampssy/ai-sports-travel-planner/pull/{number}"),
        "base_ref_name": "main",
        "head_ref_name": f"codex/catalog-{number}",
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "lifecycle_state": "OPEN",
        "created_at": datetime(2026, 7, 8, 10, tzinfo=UTC),
        "labels": frozenset({"lane:catalog-curation"}),
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset({"app/data/catalog.json"}),
        "body": "",
    }
    values.update(overrides)
    return PullRequest.model_validate(values)


def _machine_state(**overrides: object) -> MachineState:
    values: dict[str, object] = {
        "schema_version": 2,
        "last_operation": "none",
    }
    values.update(overrides)
    return MachineState.model_validate(values)


def _canonical_comment(
    state: MachineState,
    *,
    outcome: OutcomeState | None = None,
    comment_id: int = 101,
    author: str = "lampssy",
) -> GitHubComment:
    outcome_marker = f"\n{render_outcome_state(outcome)}" if outcome else ""
    return GitHubComment(
        comment_id=comment_id,
        author_login=author,
        body=(
            f"{SUMMARY_MARKER}\n"
            "## Snowcast maintainer summary\n\n"
            f"{render_machine_state(state)}{outcome_marker}"
        ),
    )


def _malformed_comment(*, comment_id: int = 101) -> GitHubComment:
    return GitHubComment(
        comment_id=comment_id,
        author_login="lampssy",
        body=(
            f"{SUMMARY_MARKER}\n"
            '<!-- snowcast-maintainer-state:{"schema_version":2} -->'
        ),
    )


def _journal(
    work_id: str = "curation-pr-42",
    *,
    new_head: str = SHA_B,
    phase: PushPhase = PushPhase.AUTHORIZED,
) -> PushJournal:
    return PushJournal(
        work_id=work_id,
        worker="curation",
        origin_run_id="1" * 32,
        recovery_run_id="2" * 32,
        pr_number=42,
        branch="codex/catalog-42",
        expected_remote_head=SHA_A,
        new_head=new_head,
        phase=phase,
    )


def _continuation(
    *,
    pr_number: int = 42,
    selected_head: str = SHA_A,
    reviewed_head: str = SHA_B,
    validation_status: ContinuationValidationStatus = (
        ContinuationValidationStatus.FAILED
    ),
) -> ReviewedContinuation:
    sync = GuardedSyncResult(
        target_branch=f"codex/catalog-{pr_number}",
        original_head=selected_head,
        rebased_head=SHA_C,
        backup_ref=f"refs/maintainer-backups/pr-{pr_number}",
        prepared_ref=f"refs/maintainer-prepared/pr-{pr_number}",
        base_head=SHA_C,
        merge_base=SHA_C,
    )
    return ReviewedContinuation(
        work_id=f"curation-pr-{pr_number}",
        origin_run_id="1" * 32,
        recovery_run_id="2" * 32,
        updated_at=datetime(2026, 7, 8, 10, tzinfo=UTC),
        pr_number=pr_number,
        selected_head=selected_head,
        reviewed_head=reviewed_head,
        report_path=f"docs/catalog-curation/pr-{pr_number}.json",
        sync=sync,
        reviewed_ref=(
            f"refs/snowcast-maintainer/reviewed/pr-{pr_number}/"
            f"{selected_head[:12]}-{reviewed_head[:12]}"
        ),
        squash_ref=(
            f"refs/snowcast-maintainer/continuations/pr-{pr_number}/"
            f"{SHA_C[:12]}-{reviewed_head[:12]}"
        ),
        status=ContinuationStatus.AVAILABLE,
        validation_status=validation_status,
    )


def _remediation(
    *,
    pr_number: int = 42,
    selected_head: str = SHA_A,
    remediation_head: str = SHA_B,
) -> RemediationContinuation:
    return RemediationContinuation(
        work_id=f"curation-pr-{pr_number}",
        origin_run_id="1" * 32,
        recovery_run_id="2" * 32,
        updated_at=datetime(2026, 7, 8, 10, tzinfo=UTC),
        pr_number=pr_number,
        selected_head=selected_head,
        remediation_head=remediation_head,
        report_path=f"docs/catalog-curation/pr-{pr_number}.json",
        sync=GuardedSyncResult(
            target_branch=f"codex/catalog-{pr_number}",
            original_head=selected_head,
            rebased_head=SHA_C,
            backup_ref=f"refs/maintainer-backups/pr-{pr_number}",
            prepared_ref=f"refs/maintainer-prepared/pr-{pr_number}",
            base_head=SHA_C,
            merge_base=SHA_C,
        ),
        allowed_paths=frozenset({"app/data/catalog.json"}),
        remediation_ref=(
            f"refs/snowcast-maintainer/remediation/pr-{pr_number}/"
            f"{selected_head[:12]}-{remediation_head[:12]}"
        ),
        squash_ref=(
            f"refs/snowcast-maintainer/remediation-continuations/pr-{pr_number}/"
            f"{SHA_C[:12]}-{remediation_head[:12]}"
        ),
        completed_stage="delta-validated",
        status=RemediationContinuationStatus.AVAILABLE,
    )


def _ci_continuation(
    *,
    pr_number: int = 42,
    semantic_head: str = SHA_B,
    current_head: str = SHA_B,
) -> CiContinuation:
    return CiContinuation(
        work_id=f"curation-pr-{pr_number}",
        origin_run_id="1" * 32,
        recovery_run_id="2" * 32,
        updated_at=NOW - timedelta(minutes=2),
        pr_number=pr_number,
        branch=f"codex/catalog-{pr_number}",
        semantic_head=semantic_head,
        current_head=current_head,
        report_path=f"docs/catalog-curation/pr-{pr_number}.json",
        resulting_graph_markdown="```mermaid\ngraph LR\n  a --> b\n```",
        non_test_tree_digest="d" * 64,
        phase=CiContinuationPhase.INITIAL_WAIT,
        repair_attempted=False,
        first_wait_started_at=NOW - timedelta(minutes=2),
        first_wait_seconds=0,
        repair_active_seconds=0,
        second_wait_seconds=0,
    )


def test_ci_continuation_summary_is_safe_live_and_first_recovery_authority() -> None:
    ci_continuation = _ci_continuation()
    failed_check = CheckSummary(
        name="backend",
        status="failure",
        conclusion="FAILURE",
        details_url=(
            "https://github.com/lampssy/ai-sports-travel-planner/actions/runs/1"
        ),
    )
    matching = _pull_request(
        head_sha=SHA_B,
        check_state="failure",
        checks=(failed_check,),
    )

    inventory = inspect_curation(
        (matching, _pull_request(43)),
        {},
        (),
        (_continuation(selected_head=SHA_B),),
        (_remediation(selected_head=SHA_B),),
        (ci_continuation,),
        now=NOW,
    )

    assert inventory.ci_continuations[0].model_dump(mode="json") == {
        "pr_number": 42,
        "semantic_head": SHA_B,
        "current_head": SHA_B,
        "phase": "initial-wait",
        "check_state": "failure",
        "mergeable": "MERGEABLE",
        "repair_attempted": False,
        "first_wait_seconds": 120,
        "repair_active_seconds": 0,
        "second_wait_seconds": 0,
        "failed_checks": [
            {
                "name": "backend",
                "status": "failure",
                "conclusion": "FAILURE",
                "details_url": (
                    "https://github.com/lampssy/ai-sports-travel-planner/actions/runs/1"
                ),
            }
        ],
        "resumable": True,
        "availability_reason": "available",
    }
    assert inventory.reviewed_continuations == ()
    assert inventory.remediation_continuations == ()
    assert [candidate.number for candidate in inventory.eligible] == [43]
    serialized = json.dumps(inventory.model_dump(mode="json"))
    for private_value in (
        ci_continuation.origin_run_id,
        ci_continuation.recovery_run_id,
        ci_continuation.report_path,
        ci_continuation.resulting_graph_markdown,
        ci_continuation.non_test_tree_digest,
    ):
        assert private_value not in serialized


def test_ci_continuation_recovery_priority_yields_only_to_unresolved_journal() -> None:
    inventory = inspect_curation(
        (_pull_request(head_sha=SHA_B),),
        {},
        (_journal(),),
        (_continuation(selected_head=SHA_B),),
        (_remediation(selected_head=SHA_B),),
        (_ci_continuation(),),
        now=NOW,
    )

    assert len(inventory.unresolved_pushes) == 1
    assert inventory.ci_continuations == ()
    assert inventory.reviewed_continuations == ()
    assert inventory.remediation_continuations == ()
    assert inventory.eligible == ()


@pytest.mark.parametrize(
    ("pull_request", "reason"),
    [
        (_pull_request(head_sha=SHA_C), "head-drift"),
        (_pull_request(head_sha=SHA_B, lifecycle_state="CLOSED"), "closed-or-merged"),
        (
            _pull_request(
                head_sha=SHA_B,
                head_ref_name="codex/catalog-other",
            ),
            "branch-drift",
        ),
        (
            _pull_request(head_sha=SHA_B, is_cross_repository=True),
            "invalid-state",
        ),
    ],
)
def test_ci_continuation_exposes_non_resumable_live_invalidated_reason(
    pull_request: PullRequest,
    reason: str,
) -> None:
    inventory = inspect_curation(
        (pull_request,),
        {},
        (),
        (),
        (),
        (_ci_continuation(),),
        now=NOW,
    )

    assert inventory.ci_continuations[0].resumable is False
    assert inventory.ci_continuations[0].availability_reason == reason
    assert inventory.reviewed_continuations == ()
    assert inventory.remediation_continuations == ()
    assert inventory.eligible == ()


@pytest.mark.parametrize(
    "labels",
    [
        frozenset({"lane:catalog-curation", "maintainer:waiting-ci"}),
        frozenset({"lane:catalog-curation"}),
        frozenset({"lane:catalog-curation", "maintainer:blocked"}),
    ],
)
def test_ci_continuation_authority_is_independent_of_labels(
    labels: frozenset[str],
) -> None:
    inventory = inspect_curation(
        (_pull_request(head_sha=SHA_B, labels=labels),),
        {},
        (),
        (),
        (),
        (_ci_continuation(),),
        now=NOW,
    )

    assert inventory.ci_continuations[0].resumable is True
    assert inventory.ci_continuations[0].availability_reason == "available"
    assert inventory.eligible == ()


def test_curation_inventory_exposes_only_safe_continuation_summary() -> None:
    continuation = _continuation()
    pull_request = _pull_request()

    inventory = inspect_curation(
        (pull_request, _pull_request(43)),
        {},
        (),
        (continuation,),
    )

    assert inventory.reviewed_continuations[0].model_dump(mode="json") == {
        "pr_number": 42,
        "selected_head": SHA_A,
        "reviewed_head": SHA_B,
        "base_head": SHA_C,
        "report_path": "docs/catalog-curation/pr-42.json",
        "validation_status": "failed",
        "resumable": True,
    }
    assert [candidate.number for candidate in inventory.eligible] == [42, 43]
    serialized = json.dumps(inventory.model_dump(mode="json"))
    assert continuation.origin_run_id not in serialized
    assert continuation.reviewed_ref not in serialized


def test_curation_continuation_stays_visible_but_paused_and_yields_to_journal() -> None:
    continuation = _continuation()
    pull_request = _pull_request(
        labels=frozenset({"lane:catalog-curation", "maintainer:blocked"})
    )

    paused = inspect_curation((pull_request,), {}, (), (continuation,))
    recovery = inspect_curation(
        (pull_request,),
        {},
        (_journal(),),
        (continuation,),
    )

    assert paused.eligible == ()
    assert paused.reviewed_continuations[0].resumable is False
    assert recovery.reviewed_continuations == ()
    assert len(recovery.unresolved_pushes) == 1


def test_curation_inventory_summarizes_remediation_after_reviewed() -> None:
    remediation = _remediation()
    pull_request = _pull_request()

    inventory = inspect_curation(
        (pull_request,),
        {},
        (),
        (),
        (remediation,),
    )
    paused = inspect_curation(
        (
            _pull_request(
                labels=frozenset({"lane:catalog-curation", "maintainer:blocked"})
            ),
        ),
        {},
        (),
        (),
        (remediation,),
    )
    preferred = inspect_curation(
        (pull_request,),
        {},
        (),
        (_continuation(),),
        (remediation,),
    )

    assert inventory.remediation_continuations[0].model_dump(mode="json") == {
        "pr_number": 42,
        "selected_head": SHA_A,
        "remediation_head": SHA_B,
        "base_head": SHA_C,
        "report_path": "docs/catalog-curation/pr-42.json",
        "resumable": True,
        "availability_reason": "available",
    }
    assert inventory.eligible == ()
    assert paused.remediation_continuations[0].resumable is False
    assert paused.remediation_continuations[0].availability_reason == "hold-label"
    assert preferred.remediation_continuations == ()


def test_newer_matching_remediation_supersedes_older_reviewed_summary() -> None:
    reviewed = _continuation(reviewed_head=SHA_B).model_copy(
        update={
            "recovery_run_id": "3" * 32,
            "status": ContinuationStatus.RESOLVING,
        }
    )
    remediation = _remediation(remediation_head=SHA_C).model_copy(
        update={
            "origin_run_id": "3" * 32,
            "recovery_run_id": "3" * 32,
            "updated_at": reviewed.updated_at + timedelta(minutes=1),
            "sync": reviewed.sync.model_copy(
                update={"base_head": SHA_B, "merge_base": SHA_B}
            ),
            "squash_ref": (
                "refs/snowcast-maintainer/remediation-continuations/pr-42/"
                f"{SHA_B[:12]}-{SHA_C[:12]}"
            ),
        }
    )

    inventory = inspect_curation(
        (_pull_request(),),
        {},
        (),
        (reviewed,),
        (remediation,),
    )

    assert inventory.reviewed_continuations == ()
    assert [item.remediation_head for item in inventory.remediation_continuations] == [
        SHA_C
    ]
    assert inventory.remediation_continuations[0].resumable is True


def test_remediation_does_not_supersede_without_exact_replay_lineage() -> None:
    reviewed = _continuation(reviewed_head=SHA_B).model_copy(
        update={
            "recovery_run_id": "3" * 32,
            "status": ContinuationStatus.RESOLVING,
        }
    )
    remediation = _remediation(remediation_head=SHA_C).model_copy(
        update={
            "origin_run_id": "3" * 32,
            "recovery_run_id": "3" * 32,
            "updated_at": reviewed.updated_at + timedelta(minutes=1),
        }
    )
    mismatches = (
        (
            reviewed.model_copy(update={"status": ContinuationStatus.AVAILABLE}),
            remediation,
        ),
        (
            reviewed,
            remediation.model_copy(update={"updated_at": reviewed.updated_at}),
        ),
        (
            reviewed,
            remediation.model_copy(
                update={"report_path": "docs/catalog-curation/other.json"}
            ),
        ),
        (
            reviewed,
            remediation.model_copy(
                update={
                    "sync": remediation.sync.model_copy(
                        update={"target_branch": "codex/catalog-other"}
                    )
                }
            ),
        ),
        (
            reviewed,
            remediation.model_copy(update={"remediation_head": reviewed.reviewed_head}),
        ),
        (
            reviewed,
            remediation.model_copy(
                update={
                    "origin_run_id": "4" * 32,
                    "recovery_run_id": "4" * 32,
                }
            ),
        ),
    )

    assert all(
        not remediation_supersedes_reviewed(old_reviewed, newer_remediation)
        for old_reviewed, newer_remediation in mismatches
    )


def test_unresolved_curation_journal_exposes_only_safe_summary() -> None:
    remediation = _remediation()
    continuation = _continuation()
    journal = PushJournal.model_validate(
        {
            **_journal().model_dump(),
            "report_path": "docs/catalog-curation/private-report.json",
            "resulting_graph_markdown": "private canonical graph",
        }
    )

    inventory = inspect_curation(
        (_pull_request(),),
        {},
        (journal,),
        (continuation,),
        (remediation,),
    )

    assert inventory.reviewed_continuations == ()
    assert inventory.remediation_continuations == ()
    serialized = json.dumps(inventory.model_dump(mode="json"))
    assert inventory.unresolved_pushes[0].model_dump(mode="json") == {
        "worker": "curation",
        "work_id": "curation-pr-42",
        "pr_number": 42,
        "candidate_key": None,
        "candidate_origin": None,
        "phase": "authorized",
        "expected_remote_head": SHA_A,
        "new_head": SHA_B,
    }
    for private_value in (
        journal.origin_run_id,
        journal.recovery_run_id,
        journal.branch,
        journal.report_path,
        journal.resulting_graph_markdown,
        continuation.reviewed_ref,
        remediation.remediation_ref,
    ):
        assert private_value not in serialized


def test_remediation_availability_reports_head_drift_closed_and_recovery_state() -> (
    None
):
    remediation = _remediation()

    drifted = inspect_curation(
        (_pull_request(head_sha=SHA_C),), {}, (), (), (remediation,)
    )
    closed = inspect_curation(
        (_pull_request(lifecycle_state="CLOSED"),), {}, (), (), (remediation,)
    )
    resolving = inspect_curation(
        (_pull_request(),),
        {},
        (),
        (),
        (
            remediation.model_copy(
                update={"status": RemediationContinuationStatus.RESOLVING}
            ),
        ),
    )

    assert drifted.remediation_continuations[0].availability_reason == "head-drift"
    assert [candidate.number for candidate in drifted.eligible] == [42]
    assert closed.remediation_continuations[0].availability_reason == "closed-or-merged"
    assert (
        resolving.remediation_continuations[0].availability_reason
        == "recovery-authority"
    )
    assert resolving.remediation_continuations[0].resumable is True
    assert resolving.eligible == ()


def test_resolving_remediation_still_respects_hold_and_candidate_safety() -> None:
    resolving = _remediation().model_copy(
        update={"status": RemediationContinuationStatus.RESOLVING}
    )

    held = inspect_curation(
        (
            _pull_request(
                labels=frozenset({"lane:catalog-curation", "maintainer:blocked"})
            ),
        ),
        {},
        (),
        (),
        (resolving,),
    )
    unsafe = inspect_curation(
        (_pull_request(is_cross_repository=True),),
        {},
        (),
        (),
        (resolving,),
    )

    assert held.remediation_continuations[0].availability_reason == "hold-label"
    assert held.remediation_continuations[0].resumable is False
    assert unsafe.remediation_continuations[0].availability_reason == "invalid-state"
    assert unsafe.remediation_continuations[0].resumable is False


def test_curation_inventory_filters_objective_scope_and_orders_by_number() -> None:
    valid_later = _pull_request(9)
    valid_earlier = _pull_request(2)
    valid_docs_and_tests = _pull_request(
        3,
        changed_paths=frozenset(
            {
                "app/data/catalog.json",
                "docs/superpowers/specs/catalog-review.md",
                "tests/test_catalog_trust.py",
            }
        ),
    )
    invalid = (
        _pull_request(10, lifecycle_state="CLOSED"),
        _pull_request(11, is_cross_repository=True),
        _pull_request(12, head_repository_owner="other"),
        _pull_request(13, base_ref_name="release"),
        _pull_request(14, head_ref_name="feature/catalog"),
        _pull_request(15, changed_paths=frozenset()),
        _pull_request(16, changed_paths=frozenset({"app/main.py"})),
        _pull_request(
            17,
            labels=frozenset({"lane:catalog-discovery", "maintainer:proposal"}),
        ),
    )

    inventory = inspect_curation(
        (valid_later, *invalid, valid_docs_and_tests, valid_earlier),
        {},
        (),
    )

    assert [pull_request.number for pull_request in inventory.eligible] == [2, 3, 9]
    assert inventory.unresolved_pushes == ()
    assert not hasattr(inventory, "selected")


def test_curation_inventory_serializes_only_approved_operational_fields() -> None:
    pull_request = _pull_request(
        title="Untrusted PR prose $(private)",
        url=(
            "https://github.com/lampssy/ai-sports-travel-planner/pull/42?private=source"
        ),
        body="Untrusted body with private source text",
        created_at=datetime(2024, 1, 2, 3, 4, tzinfo=UTC),
    )

    inventory = inspect_curation((pull_request,), {}, ())
    payload = inventory.model_dump(mode="json")
    candidate = payload["eligible"][0]
    serialized = json.dumps(payload)

    assert set(candidate) == {
        "number",
        "head_sha",
        "head_ref_name",
        "base_ref_name",
        "labels",
        "changed_paths",
        "check_state",
        "mergeable",
    }
    assert "Untrusted PR prose" not in serialized
    assert "Untrusted body" not in serialized
    assert "private=source" not in serialized
    assert "2024-01-02" not in serialized


@pytest.mark.parametrize(
    "hold_label",
    ["maintainer:manual-check", "maintainer:ready"],
)
def test_curation_selection_hold_applies_only_to_the_exact_reviewed_head(
    hold_label: str,
) -> None:
    labels = frozenset({"lane:catalog-curation", hold_label})
    same_head = _pull_request(20, labels=labels, head_sha=SHA_A)
    new_head = _pull_request(21, labels=labels, head_sha=SHA_B)
    reviewed = _canonical_comment(
        _machine_state(reviewed_head=SHA_A, last_operation="reviewed")
    )

    inventory = inspect_curation(
        (new_head, same_head),
        {20: (reviewed,), 21: (reviewed,)},
        (),
    )

    assert [pull_request.number for pull_request in inventory.eligible] == [21]


@pytest.mark.parametrize(
    "hold_label",
    ["maintainer:blocked", "maintainer:owner-decision"],
)
def test_status_only_outcome_hold_applies_only_to_the_exact_observed_head(
    hold_label: str,
) -> None:
    labels = frozenset({"lane:catalog-curation", hold_label})
    same_head = _pull_request(30, labels=labels, head_sha=SHA_A)
    new_head = _pull_request(31, labels=labels, head_sha=SHA_B)
    outcome = OutcomeState(
        schema_version=1,
        observed_head=SHA_A,
        state=hold_label,
        reason=(
            "owner-decision"
            if hold_label == "maintainer:owner-decision"
            else "conflict"
        ),
    )
    comment = _canonical_comment(
        _machine_state(),
        outcome=outcome,
    )

    inventory = inspect_curation(
        (same_head, new_head),
        {30: (comment,), 31: (comment,)},
        (),
    )

    assert [pull_request.number for pull_request in inventory.eligible] == [31]


def test_waiting_ci_remains_eligible_for_lightweight_readiness() -> None:
    pull_request = _pull_request(
        labels=frozenset({"lane:catalog-curation", "maintainer:waiting-ci"}),
        head_sha=SHA_A,
    )
    reviewed = _canonical_comment(
        _machine_state(
            reviewed_head=SHA_A,
            validated_head=SHA_A,
            last_operation="published",
        )
    )

    inventory = inspect_curation((pull_request,), {42: (reviewed,)}, ())

    assert [candidate.number for candidate in inventory.eligible] == [42]


@pytest.mark.parametrize(
    "comments",
    [
        (),
        (_malformed_comment(),),
        (_canonical_comment(_machine_state()),),
        (
            _canonical_comment(
                _machine_state(reviewed_head=SHA_A, last_operation="reviewed")
            ),
            _canonical_comment(
                _machine_state(reviewed_head=SHA_B, last_operation="reviewed"),
                comment_id=102,
            ),
        ),
        (
            _canonical_comment(
                _machine_state(reviewed_head=SHA_B, last_operation="reviewed"),
                author="untrusted",
            ),
        ),
    ],
)
def test_curation_pause_stays_closed_without_one_trusted_reviewed_state(
    comments: tuple[GitHubComment, ...],
) -> None:
    pull_request = _pull_request(
        labels=frozenset({"lane:catalog-curation", "maintainer:blocked"}),
    )

    inventory = inspect_curation((pull_request,), {42: comments}, ())

    assert inventory.eligible == ()


def test_curation_inventory_rejects_duplicate_numbers() -> None:
    with pytest.raises(MaintainerError) as exc_info:
        inspect_curation((_pull_request(), _pull_request()), {}, ())

    assert exc_info.value.payload() == {
        "status": "error",
        "reason": "invalid-github-state",
        "stage": "inspect",
        "detail": "GitHub returned a duplicate pull request number",
    }


def test_unresolved_push_journals_block_fresh_curation_inventory() -> None:
    journals = (_journal("curation-pr-43"), _journal())

    inventory = inspect_curation(
        (_pull_request(), _pull_request()),
        {},
        journals,
    )

    assert inventory.eligible == ()
    assert tuple(item.work_id for item in inventory.unresolved_pushes) == (
        "curation-pr-42",
        "curation-pr-43",
    )
    assert not hasattr(inventory, "selected_push")


def _proposal(
    number: int,
    *,
    lifecycle_state: str = "OPEN",
    labels: frozenset[str] | None = None,
) -> PullRequest:
    return _pull_request(
        number,
        lifecycle_state=lifecycle_state,
        labels=labels or frozenset({"lane:catalog-discovery", "maintainer:proposal"}),
    )


def _proposal_comment(
    key: str,
    *,
    origin: str = "backlog",
    comment_id: int = 101,
    author: str = "lampssy",
) -> GitHubComment:
    return _canonical_comment(
        _machine_state(candidate_key=key, candidate_origin=origin),
        comment_id=comment_id,
        author=author,
    )


def test_live_catalog_keys_construct_discovery_inventory() -> None:
    catalog_keys = catalog_entity_keys(Path("app/data/catalog.json"))

    inventory = inspect_discovery(catalog_keys, (), (), {}, ())

    assert inventory.catalog_keys == catalog_keys


def test_discovery_inventory_exposes_known_open_proposals_below_cap() -> None:
    open_pull_requests = (_proposal(9), _proposal(3))
    comments = {
        3: (_proposal_comment("stay_destination:nendaz"),),
        9: (_proposal_comment("ski_area:thyon-ski-area"),),
    }

    inventory = inspect_discovery(
        {"ski_area:tignes"},
        open_pull_requests,
        (),
        comments,
        (),
    )

    assert inventory.catalog_keys == frozenset({"ski_area:tignes"})
    assert inventory.open_proposal_count == 2
    assert inventory.open_candidate_keys == frozenset(
        {"stay_destination:nendaz", "ski_area:thyon-ski-area"}
    )
    assert inventory.has_unknown_proposal_identity is False
    assert inventory.can_create_proposal is True
    assert [summary.pr_number for summary in inventory.open_proposals] == [3, 9]
    assert inventory.closed_proposals == ()
    assert inventory.unresolved_pushes == ()
    assert not hasattr(inventory, "selected_candidate")


def test_discovery_inventory_closes_creation_at_three_open_proposals() -> None:
    open_pull_requests = tuple(_proposal(number) for number in (1, 2, 3))
    comments = {
        number: (_proposal_comment(f"ski_area:candidate-{number}"),)
        for number in (1, 2, 3)
    }

    inventory = inspect_discovery(
        set(),
        open_pull_requests,
        (),
        comments,
        (),
    )

    assert inventory.open_proposal_count == 3
    assert inventory.has_unknown_proposal_identity is False
    assert inventory.can_create_proposal is False


@pytest.mark.parametrize(
    "comments",
    [
        (),
        (_malformed_comment(),),
        (_canonical_comment(_machine_state()),),
        (_proposal_comment("ski_area:tignes", author="untrusted"),),
        (
            _proposal_comment("ski_area:tignes"),
            _proposal_comment("ski_area:val-disere", comment_id=102),
        ),
    ],
)
def test_unknown_open_proposal_identity_blocks_creation(
    comments: tuple[GitHubComment, ...],
) -> None:
    inventory = inspect_discovery(
        set(),
        (_proposal(42),),
        (),
        {42: comments},
        (),
    )

    assert inventory.open_proposal_count == 1
    assert inventory.open_candidate_keys == frozenset()
    assert inventory.has_unknown_proposal_identity is True
    assert inventory.can_create_proposal is False


def test_closed_discovery_history_does_not_consume_cap_or_block_when_unknown() -> None:
    closed = _proposal(7, lifecycle_state="CLOSED")
    merged = _proposal(8, lifecycle_state="MERGED")

    inventory = inspect_discovery(
        set(),
        (),
        (merged, closed),
        {7: (), 8: (_proposal_comment("ski_area:known"),)},
        (),
    )

    assert inventory.open_proposal_count == 0
    assert inventory.open_candidate_keys == frozenset()
    assert inventory.has_unknown_proposal_identity is False
    assert inventory.can_create_proposal is True
    assert [summary.pr_number for summary in inventory.closed_proposals] == [7, 8]
    assert [summary.lifecycle_state for summary in inventory.closed_proposals] == [
        "CLOSED",
        "MERGED",
    ]
    assert inventory.closed_proposals[0].candidate_key is None
    assert inventory.closed_proposals[1].candidate_key == "ski_area:known"


@pytest.mark.parametrize(
    ("open_pull_requests", "closed_pull_requests"),
    [
        ((_proposal(1, lifecycle_state="CLOSED"),), ()),
        ((), (_proposal(1, lifecycle_state="OPEN"),)),
        ((_proposal(1), _proposal(1)), ()),
        ((_proposal(1),), (_proposal(1, lifecycle_state="CLOSED"),)),
    ],
)
def test_discovery_inventory_rejects_lifecycle_or_number_conflicts(
    open_pull_requests: tuple[PullRequest, ...],
    closed_pull_requests: tuple[PullRequest, ...],
) -> None:
    with pytest.raises(MaintainerError) as exc_info:
        inspect_discovery(
            set(),
            open_pull_requests,
            closed_pull_requests,
            {},
            (),
        )

    assert exc_info.value.reason.value == "invalid-github-state"
    assert exc_info.value.stage.value == "inspect"


def test_unresolved_push_journal_blocks_discovery_creation_without_selection() -> None:
    journal = _journal()
    invalid_open = _proposal(1, lifecycle_state="CLOSED")
    invalid_closed = _proposal(1, lifecycle_state="OPEN")

    inventory = inspect_discovery(
        {"ski_area:tignes"},
        (invalid_open, invalid_open),
        (invalid_closed,),
        {},
        (journal,),
    )

    assert inventory.catalog_keys == frozenset({"ski_area:tignes"})
    assert inventory.open_proposal_count == 0
    assert inventory.open_candidate_keys == frozenset()
    assert inventory.has_unknown_proposal_identity is False
    assert inventory.closed_proposals == ()
    assert inventory.can_create_proposal is False
    assert inventory.unresolved_pushes[0].model_dump(mode="json") == {
        "worker": "curation",
        "work_id": "curation-pr-42",
        "pr_number": 42,
        "candidate_key": None,
        "candidate_origin": None,
        "phase": "authorized",
        "expected_remote_head": SHA_A,
        "new_head": SHA_B,
    }
    assert not hasattr(inventory, "selected_push")


def test_discovery_journal_summary_redacts_private_recovery_state() -> None:
    journal = PushJournal.model_validate(
        {
            **_journal().model_dump(),
            "work_id": "discovery-tignes",
            "worker": "discovery",
            "pr_number": None,
            "branch": "codex/discovery-tignes",
            "expected_remote_head": None,
            "candidate_key": "ski_area:tignes",
            "candidate_origin": "external",
        }
    )

    inventory = inspect_discovery(set(), (), (), {}, (journal,))
    serialized = json.dumps(inventory.model_dump(mode="json"))

    assert inventory.unresolved_pushes[0].model_dump(mode="json") == {
        "worker": "discovery",
        "work_id": "discovery-tignes",
        "pr_number": None,
        "candidate_key": "ski_area:tignes",
        "candidate_origin": "external",
        "phase": "authorized",
        "expected_remote_head": None,
        "new_head": SHA_B,
    }
    for private_value in (
        journal.origin_run_id,
        journal.recovery_run_id,
        journal.branch,
    ):
        assert private_value not in serialized


@pytest.mark.parametrize("workflow", ["curation", "discovery"])
@pytest.mark.parametrize("invalid_kind", ["identical", "conflicting", "terminal"])
def test_inspection_rejects_ambiguous_or_terminal_unresolved_journals(
    workflow: str,
    invalid_kind: str,
) -> None:
    first = _journal()
    if invalid_kind == "identical":
        journals = (first, first)
    elif invalid_kind == "conflicting":
        journals = (first, _journal(new_head="c" * 40))
    else:
        journals = (_journal(phase=PushPhase.PUBLISHED),)

    with pytest.raises(MaintainerError) as exc_info:
        if workflow == "curation":
            inspect_curation((), {}, journals)
        else:
            inspect_discovery(set(), (), (), {}, journals)

    assert exc_info.value.stage.value == "inspect"
    assert exc_info.value.detail in {
        "Unresolved push journals contain duplicate work identifiers",
        "Unresolved push journals contain a terminal record",
    }

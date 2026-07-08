from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.errors import MaintainerError
from ops.maintainer.github import GitHubComment
from ops.maintainer.inspection import inspect_curation, inspect_discovery
from ops.maintainer.models import MachineState, MachineStateV2, PullRequest
from ops.maintainer.state import PushJournal, PushPhase

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40


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


def _v2_state(**overrides: object) -> MachineStateV2:
    values: dict[str, object] = {
        "schema_version": 2,
        "last_operation": "none",
    }
    values.update(overrides)
    return MachineStateV2.model_validate(values)


def _canonical_comment(
    state: MachineStateV2,
    *,
    comment_id: int = 101,
    author: str = "lampssy",
) -> GitHubComment:
    payload = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return GitHubComment(
        comment_id=comment_id,
        author_login=author,
        body=(
            f"{SUMMARY_MARKER}\n"
            "## Snowcast maintainer summary\n\n"
            f"<!-- snowcast-maintainer-state:{payload} -->"
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


def _legacy_comment(*, comment_id: int = 101) -> GitHubComment:
    legacy = MachineState(
        head_sha=SHA_A,
        lineage_id="catalog-curation-42",
        last_publication="none",
    )
    payload = json.dumps(
        legacy.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return GitHubComment(
        comment_id=comment_id,
        author_login="lampssy",
        body=(f"{SUMMARY_MARKER}\n<!-- snowcast-maintainer-state:{payload} -->"),
    )


def _journal(work_id: str = "curation-pr-42") -> PushJournal:
    return PushJournal(
        work_id=work_id,
        worker="curation",
        origin_run_id="1" * 32,
        recovery_run_id="2" * 32,
        pr_number=42,
        branch="codex/catalog-42",
        expected_remote_head=SHA_A,
        new_head=SHA_B,
        phase=PushPhase.AUTHORIZED,
    )


def test_curation_inventory_filters_objective_scope_and_orders_by_number() -> None:
    valid_later = _pull_request(9)
    valid_earlier = _pull_request(2)
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
        (valid_later, *invalid, valid_earlier),
        {},
        (),
    )

    assert [pull_request.number for pull_request in inventory.eligible] == [2, 9]
    assert inventory.unresolved_pushes == ()
    assert not hasattr(inventory, "selected")


def test_curation_pause_applies_only_to_the_exact_reviewed_head() -> None:
    pause = frozenset({"lane:catalog-curation", "maintainer:manual-check"})
    same_head = _pull_request(20, labels=pause, head_sha=SHA_A)
    new_head = _pull_request(21, labels=pause, head_sha=SHA_B)
    reviewed = _canonical_comment(
        _v2_state(reviewed_head=SHA_A, last_operation="reviewed")
    )

    inventory = inspect_curation(
        (new_head, same_head),
        {20: (reviewed,), 21: (reviewed,)},
        (),
    )

    assert [pull_request.number for pull_request in inventory.eligible] == [21]


@pytest.mark.parametrize(
    "comments",
    [
        (),
        (_malformed_comment(),),
        (_legacy_comment(),),
        (_canonical_comment(_v2_state()),),
        (
            _canonical_comment(
                _v2_state(reviewed_head=SHA_A, last_operation="reviewed")
            ),
            _canonical_comment(
                _v2_state(reviewed_head=SHA_B, last_operation="reviewed"),
                comment_id=102,
            ),
        ),
        (
            _canonical_comment(
                _v2_state(reviewed_head=SHA_B, last_operation="reviewed"),
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
    journals = (_journal(), _journal("curation-pr-43"))

    inventory = inspect_curation((_pull_request(),), {}, journals)

    assert inventory.eligible == ()
    assert inventory.unresolved_pushes == journals
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
        _v2_state(candidate_key=key, candidate_origin=origin),
        comment_id=comment_id,
        author=author,
    )


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
        (_legacy_comment(),),
        (_canonical_comment(_v2_state()),),
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

    inventory = inspect_discovery(
        set(),
        (),
        (),
        {},
        (journal,),
    )

    assert inventory.can_create_proposal is False
    assert inventory.unresolved_pushes == (journal,)
    assert not hasattr(inventory, "selected_push")

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.errors import ErrorReason, MaintainerError
from ops.maintainer.github import GitHubComment
from ops.maintainer.inspection import DiscoveryInventory
from ops.maintainer.models import (
    MachineStateV2,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)
from ops.maintainer.publication import (
    PublicationInputError,
    PublicationPlan,
    parse_machine_state_v2,
    publication_plan,
    read_publication_text,
    render_machine_state_v2,
    require_ready,
    trusted_machine_state_v2,
)
from ops.maintainer.validation import ProposalValidationResult

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40


def _machine(**overrides: object) -> MachineStateV2:
    values: dict[str, object] = {
        "schema_version": 2,
        "reviewed_head": SHA_A,
        "validated_head": SHA_A,
        "last_operation": "validated",
    }
    values.update(overrides)
    return MachineStateV2.model_validate(values)


def _pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Nendaz",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": "codex/catalog-curation-nendaz",
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "lifecycle_state": "OPEN",
        "created_at": datetime(2026, 7, 8, 10, tzinfo=UTC),
        "labels": frozenset({"lane:catalog-curation"}),
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset({"app/data/catalog.json"}),
        "body": "Human text",
    }
    values.update(overrides)
    return PullRequest.model_validate(values)


def _comment(
    body: str,
    *,
    comment_id: int = 11,
    author: str = "lampssy",
) -> GitHubComment:
    return GitHubComment(comment_id=comment_id, body=body, author_login=author)


def _summary_comment(state: MachineStateV2) -> str:
    return f"{SUMMARY_MARKER}\nSummary\n\n{render_machine_state_v2(state)}"


def test_machine_state_v2_marker_is_canonical_and_round_trips() -> None:
    state = _machine(
        candidate_key="stay_destination:nendaz",
        candidate_origin="backlog",
    )

    marker = render_machine_state_v2(state)

    payload = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert marker == f"<!-- snowcast-maintainer-state:{payload} -->"
    assert parse_machine_state_v2(marker) == state
    assert parse_machine_state_v2(_summary_comment(state)) == state


@pytest.mark.parametrize(
    "body",
    [
        "plain text without a marker",
        (
            '<!-- snowcast-maintainer-state:{"head_sha":"'
            + SHA_A
            + '","schema_version":1} -->'
        ),
        '<!-- snowcast-maintainer-state:{"schema_version":3} -->',
        '<!-- snowcast-maintainer-state:{"schema_version":2} -->',
        (
            '<!-- snowcast-maintainer-state:{"last_operation":"none",'
            '"schema_version":2} -->\n'
            '<!-- snowcast-maintainer-state:{"last_operation":"none",'
            '"schema_version":2} -->'
        ),
        (
            '<!-- snowcast-maintainer-state:{ "last_operation":"none",'
            '"schema_version":2} -->'
        ),
        (
            "<!-- extra -->\n<!-- snowcast-maintainer-state:"
            '{"last_operation":"none","schema_version":2} -->'
        ),
        (
            "<!-- snowcast-maintainer-state:"
            '{"last_operation":"none","schema_version":2} -->\x00'
        ),
    ],
)
def test_machine_state_v2_parser_rejects_untrusted_encodings(body: str) -> None:
    assert parse_machine_state_v2(body) is None


def test_trusted_machine_state_requires_exactly_one_trusted_summary_comment() -> None:
    state = _machine()
    canonical = _comment(_summary_comment(state))

    assert trusted_machine_state_v2((canonical,)) == state
    assert (
        trusted_machine_state_v2((_comment(_summary_comment(state), author="other"),))
        is None
    )
    assert (
        trusted_machine_state_v2(
            (canonical, _comment(_summary_comment(state), comment_id=12))
        )
        is None
    )
    assert (
        trusted_machine_state_v2(
            (
                _comment(
                    f"{SUMMARY_MARKER}\n{SUMMARY_MARKER}\n{render_machine_state_v2(state)}"
                ),
            )
        )
        is None
    )


@pytest.mark.parametrize(
    "requested_state",
    [
        MaintainerState.WORKING,
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
    ],
)
def test_semantic_publication_plan_binds_one_lane_state_and_exact_head(
    requested_state: MaintainerState,
) -> None:
    machine = _machine(validated_head=None, last_operation="reviewed")

    plan = publication_plan(
        requested_state=requested_state,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=_pull_request(),
        machine_state=machine,
    )

    assert plan == PublicationPlan(
        lane=MaintainerLane.CATALOG_CURATION,
        state=requested_state,
        machine_state=machine,
    )


def test_new_head_invalidates_semantic_publication_authority() -> None:
    with pytest.raises(MaintainerError) as exc_info:
        publication_plan(
            requested_state=MaintainerState.MANUAL_CHECK,
            lane=MaintainerLane.CATALOG_CURATION,
            pull_request=_pull_request(head_sha=SHA_B),
            machine_state=_machine(validated_head=None, last_operation="reviewed"),
        )

    assert exc_info.value.reason is ErrorReason.STALE_HEAD


@pytest.mark.parametrize(
    "requested_state",
    [
        MaintainerState.WORKING,
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
        MaintainerState.WAITING_CI,
        MaintainerState.READY,
    ],
)
def test_proposal_label_requires_owner_approval_before_every_other_state(
    requested_state: MaintainerState,
) -> None:
    objective_state = requested_state in {
        MaintainerState.WAITING_CI,
        MaintainerState.READY,
    }
    pull_request = _pull_request(
        labels=frozenset({"lane:catalog-curation", "maintainer:proposal"}),
        check_state="pending"
        if requested_state is MaintainerState.WAITING_CI
        else "success",
    )
    machine = (
        _machine(last_operation="pushed")
        if objective_state
        else _machine(validated_head=None, last_operation="reviewed")
    )

    with pytest.raises(MaintainerError) as exc_info:
        publication_plan(
            requested_state=requested_state,
            lane=MaintainerLane.CATALOG_CURATION,
            pull_request=pull_request,
            machine_state=machine,
        )

    assert exc_info.value.reason is ErrorReason.PROPOSAL_APPROVAL_REQUIRED
    assert exc_info.value.stage.value == ("readiness" if objective_state else "publish")


@pytest.mark.parametrize(
    "overrides",
    [
        {"lifecycle_state": "CLOSED"},
        {"is_cross_repository": True},
        {"head_repository_owner": "other"},
        {"base_ref_name": "release"},
        {"head_ref_name": "feature/nendaz"},
        {"url": "https://github.com/lampssy/ai-sports-travel-planner/pull/99"},
        {"labels": frozenset({"lane:catalog-discovery"})},
    ],
)
def test_publication_plan_rejects_pr_outside_exact_authority(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(MaintainerError) as exc_info:
        publication_plan(
            requested_state=MaintainerState.WORKING,
            lane=MaintainerLane.CATALOG_CURATION,
            pull_request=_pull_request(**overrides),
            machine_state=_machine(validated_head=None, last_operation="reviewed"),
        )

    assert exc_info.value.reason is ErrorReason.INVALID_GITHUB_STATE


def test_waiting_ci_requires_exact_validated_head_and_pending_checks() -> None:
    plan = publication_plan(
        requested_state=MaintainerState.WAITING_CI,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=_pull_request(check_state="pending"),
        machine_state=_machine(last_operation="pushed"),
    )

    assert plan.state is MaintainerState.WAITING_CI

    with pytest.raises(MaintainerError):
        publication_plan(
            requested_state=MaintainerState.WAITING_CI,
            lane=MaintainerLane.CATALOG_CURATION,
            pull_request=_pull_request(check_state="success"),
            machine_state=_machine(last_operation="pushed"),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"check_state": "pending"},
        {"mergeable": "UNKNOWN"},
        {"labels": frozenset({"lane:catalog-curation", "maintainer:proposal"})},
        {"labels": frozenset({"lane:catalog-curation", "maintainer:owner-decision"})},
        {"labels": frozenset({"lane:catalog-curation", "maintainer:manual-check"})},
        {"labels": frozenset({"lane:catalog-curation", "maintainer:blocked"})},
        {"head_sha": SHA_B},
    ],
)
def test_ready_rejects_nonobjective_or_stale_state(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(MaintainerError):
        require_ready(_pull_request(**overrides), _machine(last_operation="published"))


def test_ready_plan_accepts_only_green_mergeable_exact_head() -> None:
    pull_request = _pull_request()
    machine = _machine(last_operation="published")

    require_ready(pull_request, machine)
    plan = publication_plan(
        requested_state=MaintainerState.READY,
        lane=MaintainerLane.CATALOG_CURATION,
        pull_request=pull_request,
        machine_state=machine,
    )

    assert plan.state is MaintainerState.READY


def _proposal_validation() -> ProposalValidationResult:
    return ProposalValidationResult(
        candidate_key="stay_destination:nendaz",
        candidate_origin="backlog",
        validated_head=SHA_A,
        report_path="docs/catalog-curation/nendaz.json",
    )


def _discovery_inventory(**overrides: object) -> DiscoveryInventory:
    values: dict[str, object] = {
        "catalog_keys": frozenset(),
        "open_proposal_count": 0,
        "open_candidate_keys": frozenset(),
        "has_unknown_proposal_identity": False,
        "can_create_proposal": True,
    }
    values.update(overrides)
    return DiscoveryInventory.model_validate(values)


def test_proposal_plan_requires_validated_candidate_and_current_inventory() -> None:
    validation = _proposal_validation()
    machine = _machine(
        candidate_key=validation.candidate_key,
        candidate_origin=validation.candidate_origin,
    )
    pull_request = _pull_request(labels=frozenset())

    plan = publication_plan(
        requested_state=MaintainerState.PROPOSAL,
        lane=MaintainerLane.CATALOG_DISCOVERY,
        pull_request=pull_request,
        machine_state=machine,
        proposal_validation=validation,
        discovery_inventory=_discovery_inventory(),
    )

    assert plan.state is MaintainerState.PROPOSAL


@pytest.mark.parametrize(
    "inventory",
    [
        _discovery_inventory(catalog_keys=frozenset({"stay_destination:nendaz"})),
        _discovery_inventory(
            open_candidate_keys=frozenset({"stay_destination:nendaz"})
        ),
        _discovery_inventory(
            open_proposal_count=3,
            can_create_proposal=False,
        ),
        _discovery_inventory(
            has_unknown_proposal_identity=True,
            can_create_proposal=False,
        ),
    ],
)
def test_proposal_plan_rejects_stale_or_blocked_candidate_facts(
    inventory: DiscoveryInventory,
) -> None:
    validation = _proposal_validation()

    with pytest.raises(MaintainerError):
        publication_plan(
            requested_state=MaintainerState.PROPOSAL,
            lane=MaintainerLane.CATALOG_DISCOVERY,
            pull_request=_pull_request(labels=frozenset()),
            machine_state=_machine(
                candidate_key=validation.candidate_key,
                candidate_origin=validation.candidate_origin,
            ),
            proposal_validation=validation,
            discovery_inventory=inventory,
        )


def _private_state_dir(tmp_path: Path) -> Path:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    os.chmod(state_dir, 0o700)
    return state_dir


def _write_private(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    os.chmod(path, 0o600)


@pytest.mark.parametrize(
    ("kind", "basename", "payload"),
    [
        ("title", "title.txt", b"Nendaz proposal"),
        ("body", "body.md", b"Proposal body\n"),
        ("summary", "summary.md", b"Reviewed and validated."),
    ],
)
def test_read_publication_text_accepts_private_direct_child(
    tmp_path: Path,
    kind: str,
    basename: str,
    payload: bytes,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    _write_private(state_dir / basename, payload)

    assert read_publication_text(state_dir, basename, kind=kind) == payload.decode()


@pytest.mark.parametrize(
    "supplied_path",
    [
        "/tmp/title.txt",
        "../title.txt",
        "nested/title.txt",
        "nested\\title.txt",
        ".",
        "..",
        "",
    ],
)
def test_read_publication_text_rejects_non_direct_paths_without_echo(
    tmp_path: Path,
    supplied_path: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)

    with pytest.raises(PublicationInputError) as exc_info:
        read_publication_text(state_dir, supplied_path, kind="title")

    if supplied_path:
        assert supplied_path not in str(exc_info.value)


def test_read_publication_text_rejects_leaf_and_ancestor_symlinks(
    tmp_path: Path,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    outside = tmp_path / "outside.txt"
    _write_private(outside, b"secret-source")
    (state_dir / "title.txt").symlink_to(outside)

    with pytest.raises(PublicationInputError):
        read_publication_text(state_dir, "title.txt", kind="title")

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir(mode=0o700)
    real_state = real_parent / "state"
    real_state.mkdir(mode=0o700)
    _write_private(real_state / "title.txt", b"Safe title")
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(PublicationInputError):
        read_publication_text(
            linked_parent / "state",
            "title.txt",
            kind="title",
        )


@pytest.mark.parametrize(
    ("setup", "kind"),
    [
        ("nonregular", "body"),
        ("public-mode", "body"),
        ("oversize-title", "title"),
        ("oversize-body", "body"),
        ("oversize-summary", "summary"),
        ("non-utf8", "summary"),
        ("blank-title", "title"),
        ("multiline-title", "title"),
    ],
)
def test_read_publication_text_rejects_unsafe_files(
    tmp_path: Path,
    setup: str,
    kind: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    path = state_dir / "input.txt"
    if setup == "nonregular":
        path.mkdir(mode=0o700)
    else:
        payload = {
            "public-mode": b"body",
            "oversize-title": b"x" * 257,
            "oversize-body": b"x" * 65_537,
            "oversize-summary": b"x" * 16_385,
            "non-utf8": b"\xff\xfe",
            "blank-title": b"   ",
            "multiline-title": b"line one\nline two",
        }[setup]
        _write_private(path, payload)
        if setup == "public-mode":
            os.chmod(path, 0o640)

    with pytest.raises(PublicationInputError):
        read_publication_text(state_dir, "input.txt", kind=kind)


def test_read_publication_text_rejects_secret_source_without_echo(
    tmp_path: Path,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    secret = tmp_path / "private-token.txt"
    token = "private-token-value"
    _write_private(secret, token.encode())

    with pytest.raises(PublicationInputError) as exc_info:
        read_publication_text(state_dir, str(secret), kind="body")

    rendered = str(exc_info.value)
    assert str(secret) not in rendered
    assert token not in rendered


def test_read_publication_text_rejects_nonprivate_state_directory(
    tmp_path: Path,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    _write_private(state_dir / "title.txt", b"Title")
    os.chmod(state_dir, 0o755)

    with pytest.raises(PublicationInputError):
        read_publication_text(state_dir, "title.txt", kind="title")


def test_read_publication_text_fails_closed_without_nofollow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    _write_private(state_dir / "title.txt", b"Title")
    monkeypatch.delattr(os, "O_NOFOLLOW")

    with pytest.raises(PublicationInputError):
        read_publication_text(state_dir, "title.txt", kind="title")

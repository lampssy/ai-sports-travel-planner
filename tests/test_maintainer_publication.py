from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.errors import ErrorReason, MaintainerError
from ops.maintainer.github import GitHubComment
from ops.maintainer.inspection import DiscoveryInventory, inspect_discovery
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
    publish_discovery_proposal,
    publish_state_v2,
    read_publication_text,
    render_machine_state_v2,
    require_ready,
    trusted_machine_state_v2,
)
from ops.maintainer.runtime import LeaseOwnershipError, SimpleRunLease
from ops.maintainer.state import PushJournal, PushPhase, StateStore
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


class _InjectedCrash(RuntimeError):
    pass


class _ProposalRepository:
    def __init__(self, head: str = SHA_A) -> None:
        self.head = head
        self.remote: str | None = None
        self.pushes = 0

    def current_head(self) -> str:
        return self.head

    def optional_remote_head(self, branch: str) -> str | None:
        assert branch == "codex/catalog-curation-nendaz"
        return self.remote

    def push_create_only(self, branch: str, reviewed_head: str) -> None:
        assert branch == "codex/catalog-curation-nendaz"
        assert reviewed_head == self.head
        if self.remote is not None:
            raise RuntimeError("remote exists")
        self.pushes += 1
        self.remote = reviewed_head


class _ProposalGitHub:
    def __init__(self) -> None:
        self.pull_requests: dict[int, PullRequest] = {}
        self.comments: dict[int, list[GitHubComment]] = {}
        self.created_prs = 0
        self.created_comments = 0
        self.body_writes = 0
        self.label_writes = 0

    def create_draft_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
    ) -> int:
        assert branch == "codex/catalog-curation-nendaz"
        self.created_prs += 1
        number = 70 + self.created_prs
        self.pull_requests[number] = _pull_request(
            number=number,
            title=title,
            url=(f"https://github.com/lampssy/ai-sports-travel-planner/pull/{number}"),
            labels=frozenset(),
            is_draft=True,
            body=body,
            head_ref_name=branch,
            changed_paths=frozenset(
                {
                    "app/data/catalog.json",
                    "docs/catalog-curation/nendaz.json",
                }
            ),
        )
        return number

    def find_open_pull_requests_by_head(
        self,
        branch: str,
        head_sha: str,
    ) -> list[PullRequest]:
        return [
            pull_request
            for pull_request in self.pull_requests.values()
            if pull_request.lifecycle_state == "OPEN"
            and pull_request.head_ref_name == branch
            and pull_request.head_sha == head_sha
        ]

    def get_pull_request(self, number: int) -> PullRequest:
        return self.pull_requests[number]

    def list_issue_comments(self, number: int) -> Sequence[GitHubComment]:
        return tuple(self.comments.get(number, ()))

    def update_pull_request_body(self, number: int, body: str) -> None:
        self.body_writes += 1
        self.pull_requests[number] = self.pull_requests[number].model_copy(
            update={"body": body}
        )

    def create_comment(self, number: int, body: str) -> int:
        self.created_comments += 1
        comment_id = 100 + self.created_comments
        self.comments.setdefault(number, []).append(
            _comment(body, comment_id=comment_id)
        )
        return comment_id

    def update_comment(self, comment_id: int, body: str) -> None:
        for number, comments in self.comments.items():
            for index, comment in enumerate(comments):
                if comment.comment_id == comment_id:
                    comments[index] = _comment(body, comment_id=comment_id)
                    self.comments[number] = comments
                    return
        raise AssertionError("comment was not found")

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None:
        self.label_writes += 1
        labels = (set(self.pull_requests[number].labels) - set(remove)) | set(add)
        self.pull_requests[number] = self.pull_requests[number].model_copy(
            update={"labels": frozenset(labels)}
        )


def _live_inventory(github: _ProposalGitHub) -> DiscoveryInventory:
    return inspect_discovery(
        set(),
        github.pull_requests.values(),
        (),
        github.comments,
        (),
    )


def _publish_proposal(
    *,
    store: StateStore,
    lease: SimpleRunLease,
    repository: _ProposalRepository,
    github: _ProposalGitHub,
    inventory_provider: Callable[[], DiscoveryInventory] | None = None,
    title: str = "Curate Nendaz",
    step_hook: Callable[[str], None] | None = None,
) -> PushJournal:
    return publish_discovery_proposal(
        store=store,
        lease=lease,
        repository=repository,
        github=github,
        work_id="discovery-nendaz",
        branch="codex/catalog-curation-nendaz",
        proposal_validation=_proposal_validation(),
        inventory_provider=inventory_provider or (lambda: _live_inventory(github)),
        title=title,
        initial_body="Owner proposal context",
        managed_body="Validated Snowcast catalog proposal.",
        summary="Validated candidate. Owner approval is required.",
        step_hook=step_hook,
    )


@pytest.mark.parametrize(
    ("inventory", "reason"),
    [
        (
            _discovery_inventory(catalog_keys=frozenset({"stay_destination:nendaz"})),
            ErrorReason.DUPLICATE_PROPOSAL,
        ),
        (
            _discovery_inventory(
                open_candidate_keys=frozenset({"stay_destination:nendaz"})
            ),
            ErrorReason.DUPLICATE_PROPOSAL,
        ),
        (
            _discovery_inventory(open_proposal_count=3, can_create_proposal=False),
            ErrorReason.PROPOSAL_CAP,
        ),
        (
            _discovery_inventory(
                has_unknown_proposal_identity=True,
                can_create_proposal=False,
            ),
            ErrorReason.PROPOSAL_CAP,
        ),
    ],
)
def test_discovery_proposal_rechecks_raw_inventory_before_authorization(
    tmp_path: Path,
    inventory: DiscoveryInventory,
    reason: ErrorReason,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            inventory_provider=lambda: inventory,
        )

    assert exc_info.value.reason is reason
    assert store.load_push("discovery-nendaz") is None
    assert repository.pushes == 0


@pytest.mark.parametrize("unsafe_title", ["", "line one\nline two", "x" * 257])
def test_discovery_proposal_rejects_unsafe_title_before_push_authorization(
    tmp_path: Path,
    unsafe_title: str,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            title=unsafe_title,
        )

    assert exc_info.value.reason is ErrorReason.PUBLICATION_INPUT
    assert store.load_push("discovery-nendaz") is None
    assert repository.pushes == 0


@pytest.mark.parametrize(
    "crash_step",
    [
        "authorized",
        "push",
        "pr",
        "body",
        "comment",
        "labels",
    ],
)
def test_discovery_proposal_recovers_every_crash_boundary_without_duplicates(
    tmp_path: Path,
    crash_step: str,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    def crash_after(step: str) -> None:
        if step == crash_step:
            raise _InjectedCrash(step)

    with pytest.raises(_InjectedCrash):
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            step_hook=crash_after,
        )

    assert store.load_work("discovery-nendaz") is None
    recovered = _publish_proposal(
        store=store,
        lease=lease,
        repository=repository,
        github=github,
    )

    assert recovered.phase is PushPhase.PUBLISHED
    assert recovered.pr_number == 71
    assert repository.pushes == 1
    assert github.created_prs == 1
    assert github.created_comments == 1
    assert github.body_writes == 1
    assert github.label_writes == 1
    pull_request = github.get_pull_request(71)
    assert pull_request.is_draft is True
    assert pull_request.labels == frozenset(
        {"lane:catalog-discovery", "maintainer:proposal"}
    )
    state = trusted_machine_state_v2(github.list_issue_comments(71))
    assert state is not None
    assert state.candidate_key == "stay_destination:nendaz"
    assert state.last_operation == "published"


def test_proposal_recovery_rejects_unexpected_remote_head(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(_InjectedCrash):
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            step_hook=lambda step: (
                (_ for _ in ()).throw(_InjectedCrash(step))
                if step == "authorized"
                else None
            ),
        )
    repository.remote = SHA_B

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
        )

    assert exc_info.value.reason is ErrorReason.STALE_HEAD
    assert repository.pushes == 0


@pytest.mark.parametrize("crash_step", ["authorized", "push"])
def test_stale_successor_adopts_sole_proposal_journal_and_fences_old_run(
    tmp_path: Path,
    crash_step: str,
) -> None:
    state_dir = tmp_path / "state"
    started = datetime(2026, 7, 8, 8, tzinfo=UTC)
    old = SimpleRunLease.acquire(state_dir, "discovery", now=started)
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(_InjectedCrash):
        _publish_proposal(
            store=store,
            lease=old,
            repository=repository,
            github=github,
            step_hook=lambda step: (
                (_ for _ in ()).throw(_InjectedCrash(step))
                if step == crash_step
                else None
            ),
        )

    successor = SimpleRunLease.acquire(
        state_dir,
        "discovery",
        now=started + timedelta(hours=7),
    )
    recovered = _publish_proposal(
        store=store,
        lease=successor,
        repository=repository,
        github=github,
    )

    assert recovered.origin_run_id == old.run_id
    assert recovered.recovery_run_id == successor.run_id
    assert recovered.phase is PushPhase.PUBLISHED
    with pytest.raises(LeaseOwnershipError):
        _publish_proposal(
            store=store,
            lease=old,
            repository=repository,
            github=github,
        )


def test_journal_recovery_repairs_its_own_missing_comment_after_labels(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(_InjectedCrash):
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            step_hook=lambda step: (
                (_ for _ in ()).throw(_InjectedCrash(step))
                if step == "labels"
                else None
            ),
        )
    github.comments.clear()

    recovered = _publish_proposal(
        store=store,
        lease=lease,
        repository=repository,
        github=github,
    )

    assert recovered.phase is PushPhase.PUBLISHED
    assert github.created_prs == 1
    assert github.created_comments == 2
    assert len(github.list_issue_comments(71)) == 1


def test_proposal_recovery_rejects_multiple_exact_head_pull_requests(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(_InjectedCrash):
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            step_hook=lambda step: (
                (_ for _ in ()).throw(_InjectedCrash(step)) if step == "push" else None
            ),
        )
    github.create_draft_pull_request(
        "codex/catalog-curation-nendaz",
        "First",
        "Body",
    )
    github.create_draft_pull_request(
        "codex/catalog-curation-nendaz",
        "Second",
        "Body",
    )

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
        )

    assert exc_info.value.reason is ErrorReason.INVALID_GITHUB_STATE
    assert github.created_prs == 2


def test_proposal_recovery_rejects_missing_remote_after_pr_was_bound(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    with pytest.raises(_InjectedCrash):
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            step_hook=lambda step: (
                (_ for _ in ()).throw(_InjectedCrash(step)) if step == "body" else None
            ),
        )
    repository.remote = None

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
        )

    assert exc_info.value.reason is ErrorReason.STALE_HEAD
    assert github.created_comments == 0
    assert github.label_writes == 0


def test_proposal_recovery_requires_one_unresolved_journal(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()
    first = PushJournal(
        work_id="discovery-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch="codex/catalog-curation-nendaz",
        new_head=SHA_A,
        candidate_key="stay_destination:nendaz",
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    second = first.model_copy(
        update={
            "work_id": "discovery-verbier",
            "branch": "codex/catalog-curation-verbier",
            "candidate_key": "stay_destination:verbier",
        }
    )
    store.save_push(first, lease)
    store.save_push(second, lease)

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
        )

    assert exc_info.value.reason is ErrorReason.INVALID_COMMAND
    assert repository.pushes == 0
    assert github.created_prs == 0


def test_v2_state_publisher_requires_fresh_review_to_repair_missing_comment() -> None:
    github = _ProposalGitHub()
    number = github.create_draft_pull_request(
        "codex/catalog-curation-nendaz",
        "Curate Nendaz",
        "Owner context",
    )
    pull_request = github.get_pull_request(number)
    machine = _machine(
        candidate_key="stay_destination:nendaz",
        candidate_origin="backlog",
        last_operation="published",
    )
    plan = publication_plan(
        requested_state=MaintainerState.PROPOSAL,
        lane=MaintainerLane.CATALOG_DISCOVERY,
        pull_request=pull_request,
        machine_state=machine,
        proposal_validation=_proposal_validation(),
        discovery_inventory=_discovery_inventory(),
    )

    with pytest.raises(MaintainerError) as exc_info:
        publish_state_v2(
            github,
            pull_request,
            plan,
            "Managed context",
            "Validated candidate.",
        )

    assert exc_info.value.reason is ErrorReason.VALIDATION_REQUIRED
    assert github.created_comments == 0


def test_v2_state_publisher_refetches_and_rejects_head_drift_between_writes(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    lease = SimpleRunLease.acquire(state_dir, "discovery", now=datetime.now(UTC))
    store = StateStore(state_dir)
    repository = _ProposalRepository()
    github = _ProposalGitHub()

    def drift_after_body(step: str) -> None:
        if step == "body":
            github.pull_requests[71] = github.pull_requests[71].model_copy(
                update={"head_sha": SHA_B}
            )

    with pytest.raises(MaintainerError) as exc_info:
        _publish_proposal(
            store=store,
            lease=lease,
            repository=repository,
            github=github,
            step_hook=drift_after_body,
        )

    assert exc_info.value.reason is ErrorReason.STALE_HEAD
    assert github.body_writes == 1
    assert github.created_comments == 0
    assert github.label_writes == 0

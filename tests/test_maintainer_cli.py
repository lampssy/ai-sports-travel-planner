from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.cli import HANDLERS, main
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    ErrorStage,
    MaintainerError,
)
from ops.maintainer.git_ops import (
    ContinuationReplayResult,
    GitTransportError,
    GuardedSyncResult,
    RebaseConflictError,
    RepositorySafetyError,
    ReviewedCheckpointRefs,
    StaleRemoteHeadError,
)
from ops.maintainer.github import GitHubComment, GitHubError
from ops.maintainer.intent import IntentDiffEntry, IntentSnapshot
from ops.maintainer.models import MachineState, MaintainerState, PullRequest
from ops.maintainer.publication import (
    create_publication_text,
    render_machine_state,
    trusted_machine_state,
    trusted_outcome_state,
)
from ops.maintainer.runtime import RunLease
from ops.maintainer.state import (
    ContinuationStatus,
    ContinuationValidationStatus,
    PushJournal,
    PushPhase,
    ReviewedContinuation,
    StateStore,
    WorkPhase,
    WorkState,
)
from ops.maintainer.validation import (
    ProposalValidationResult,
    ValidationCommandObservation,
    ValidationResult,
)

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
NOW = datetime(2026, 7, 8, 10, tzinfo=UTC)
CANDIDATE = "stay_destination:nendaz"
CANONICAL_GRAPH = (
    "## Resulting Graph\n\n"
    "```mermaid\n"
    "flowchart LR\n"
    '  destination_1["Stay destination<br/>Nendaz"]\n'
    "```\n"
)
BRANCH = "codex/catalog-curation-nendaz"


@pytest.fixture(autouse=True)
def _stub_manual_check_resulting_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ops.maintainer.capabilities.immutable_resulting_graph_markdown",
        lambda _repository, _revision, _report_path: CANONICAL_GRAPH,
    )


def _catalog_json(*, include_candidate: bool = False) -> str:
    ski_regions: list[dict[str, object]] = []
    stay_destinations: list[dict[str, object]] = []
    if include_candidate:
        ski_regions.append(
            {
                "ski_region_id": "nendaz",
                "name": "Nendaz",
                "grouping_policy": "trip_market",
            }
        )
        stay_destinations.append(
            {
                "stay_destination_id": "nendaz",
                "name": "Nendaz",
                "country": "Switzerland",
                "region": "Valais",
                "price_level": "medium",
                "latitude": 46.18,
                "longitude": 7.29,
                "trip_market_region_id": "nendaz",
            }
        )
    return json.dumps(
        {
            "schema_version": 2,
            "ski_regions": ski_regions,
            "stay_destinations": stay_destinations,
            "stay_bases": [],
            "ski_areas": [],
            "ski_area_access": [],
            "terrain_domains": [],
            "lift_pass_products": [],
            "rental_display_facts": [],
        }
    )


def _pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Nendaz",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": BRANCH,
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "is_draft": False,
        "lifecycle_state": "OPEN",
        "created_at": NOW,
        "labels": frozenset({"lane:catalog-curation"}),
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/nendaz.json",
            }
        ),
        "body": "Owner text",
    }
    values.update(overrides)
    number = int(values["number"])
    if "url" not in overrides:
        values["url"] = (
            f"https://github.com/lampssy/ai-sports-travel-planner/pull/{number}"
        )
    return PullRequest.model_validate(values)


def _sync() -> GuardedSyncResult:
    return GuardedSyncResult(
        target_branch=BRANCH,
        original_head=SHA_A,
        rebased_head=SHA_B,
        backup_ref=(
            f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{SHA_A[:12]}"
        ),
        prepared_ref=(
            f"refs/snowcast-maintainer/prepared/pr-42/{SHA_D[:12]}-{SHA_B[:12]}"
        ),
        base_head=SHA_D,
        merge_base=SHA_C,
    )


def _snapshot() -> IntentSnapshot:
    changed_paths = frozenset(
        {
            "app/data/catalog.json",
            "app/data/resort_trust_manifest.json",
            "docs/catalog-curation/nendaz.json",
        }
    )
    entries = tuple(
        IntentDiffEntry(
            path=path,
            old_mode="100644",
            new_mode="100644",
            old_oid=SHA_A,
            new_oid=SHA_B,
            status="M",
        )
        for path in sorted(changed_paths)
    )
    return IntentSnapshot(
        changed_paths=changed_paths,
        diff_entries=entries,
        catalog_targets=frozenset({CANDIDATE}),
        report_targets=frozenset({CANDIDATE}),
    )


def _validation_result() -> ValidationResult:
    return ValidationResult(
        validated_head=SHA_B,
        commands_completed=3,
        observations=tuple(
            ValidationCommandObservation(
                command_index=index,
                stdout_characters=0,
                stderr_characters=0,
                output_truncated=False,
            )
            for index in range(1, 4)
        ),
    )


@dataclass
class FakeGitHub:
    pull_requests: dict[int, PullRequest] = field(
        default_factory=lambda: {42: _pull_request()}
    )
    comments: dict[int, list[GitHubComment]] = field(default_factory=dict)
    closed: list[PullRequest] = field(default_factory=list)
    labels_changed: bool = True
    ensured_labels: int = 0
    body_writes: int = 0
    comment_creates: int = 0
    label_writes: int = 0
    pr_creates: int = 0
    get_pull_request_calls: int = 0
    pull_request_head_reads: list[str] = field(default_factory=list)
    failure: Exception | None = None

    def _fail(self) -> None:
        if self.failure is not None:
            raise self.failure

    def list_all_open_pull_requests(self) -> list[PullRequest]:
        self._fail()
        return [
            item
            for item in self.pull_requests.values()
            if item.lifecycle_state == "OPEN"
        ]

    def list_closed_discovery_pull_requests(self) -> list[PullRequest]:
        self._fail()
        return list(self.closed)

    def get_pull_request(self, number: int) -> PullRequest:
        self._fail()
        self.get_pull_request_calls += 1
        pull_request = self.pull_requests[number]
        if self.pull_request_head_reads:
            return pull_request.model_copy(
                update={"head_sha": self.pull_request_head_reads.pop(0)}
            )
        return pull_request

    def list_issue_comments(self, number: int) -> Sequence[GitHubComment]:
        self._fail()
        return tuple(self.comments.get(number, ()))

    def ensure_labels(self, definitions: object) -> bool:
        self._fail()
        self.ensured_labels += 1
        return self.labels_changed

    def update_pull_request_body(self, number: int, body: str) -> None:
        self._fail()
        self.body_writes += 1
        self.pull_requests[number] = self.pull_requests[number].model_copy(
            update={"body": body}
        )

    def create_comment(self, number: int, body: str) -> int:
        self._fail()
        self.comment_creates += 1
        comment_id = 100 + self.comment_creates
        self.comments.setdefault(number, []).append(
            GitHubComment(comment_id, body, "lampssy")
        )
        return comment_id

    def update_comment(self, comment_id: int, body: str) -> None:
        self._fail()
        for number, comments in self.comments.items():
            for index, comment in enumerate(comments):
                if comment.comment_id == comment_id:
                    comments[index] = GitHubComment(comment_id, body, "lampssy")
                    self.comments[number] = comments
                    return
        raise AssertionError("comment not found")

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None:
        self._fail()
        self.label_writes += 1
        labels = (set(self.pull_requests[number].labels) - set(remove)) | set(add)
        self.pull_requests[number] = self.pull_requests[number].model_copy(
            update={"labels": frozenset(labels)}
        )

    def create_draft_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
    ) -> int:
        self._fail()
        self.pr_creates += 1
        number = 70 + self.pr_creates
        self.pull_requests[number] = _pull_request(
            number=number,
            title=title,
            body=body,
            head_ref_name=branch,
            head_sha=SHA_B,
            labels=frozenset(),
            is_draft=True,
        )
        return number

    def find_pull_requests_by_head(
        self,
        branch: str,
        head_sha: str,
    ) -> list[PullRequest]:
        self._fail()
        return [
            item
            for item in self.pull_requests.values()
            if item.head_ref_name == branch and item.head_sha == head_sha
        ]


@dataclass
class FakeRepository:
    head: str = SHA_A
    remote: str | None = SHA_A
    prepared: GuardedSyncResult = field(default_factory=_sync)
    snapshot: IntentSnapshot = field(default_factory=_snapshot)
    prepare_error: Exception | None = None
    revalidate_error: Exception | None = None
    push_error: Exception | None = None
    after_push: Callable[[], None] | None = None
    after_push_error: Exception | None = None
    prepare_calls: int = 0
    revalidate_calls: int = 0
    push_calls: int = 0
    create_only_calls: int = 0
    github: FakeGitHub | None = None
    root: Path = Path("/tmp/snowcast-test-repository")
    main_head: str = SHA_A
    main_catalog_json: str = field(default_factory=_catalog_json)
    fetch_main_calls: int = 0
    continuation_result: str = "unchanged"

    def current_head(self) -> str:
        return self.head

    def verify_validation_base(self, expected_head: str) -> None:
        assert self.head == expected_head

    def fetch_main(self) -> str:
        self.fetch_main_calls += 1
        return self.main_head

    def show_text(self, revision: str, path: str) -> str:
        assert revision == self.main_head
        assert path == "app/data/catalog.json"
        return self.main_catalog_json

    def prepare_guarded_sync(self, pull_request: PullRequest) -> GuardedSyncResult:
        self.prepare_calls += 1
        if self.prepare_error is not None:
            raise self.prepare_error
        self.head = self.prepared.rebased_head
        return self.prepared

    def verify_immutable_diff(self, base: str, head: str) -> IntentSnapshot:
        assert base == SHA_A
        assert head == SHA_B
        return self.snapshot

    def revalidate_prepared_result(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot:
        self.revalidate_calls += 1
        if self.revalidate_error is not None:
            raise self.revalidate_error
        assert pull_request.number == 42
        assert result == self.prepared
        assert reviewed_head == self.head
        return self.snapshot

    def checkpoint_reviewed_continuation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> ReviewedCheckpointRefs:
        assert pull_request.number == 42
        assert result == self.prepared
        assert reviewed_head == self.head
        return ReviewedCheckpointRefs(
            reviewed_ref=(
                f"refs/snowcast-maintainer/reviewed/pr-42/"
                f"{result.original_head[:12]}-{reviewed_head[:12]}"
            ),
            squash_ref=(
                f"refs/snowcast-maintainer/continuations/pr-42/"
                f"{result.base_head[:12]}-{reviewed_head[:12]}"
            ),
        )

    def revalidate_reviewed_checkpoint(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        refs: ReviewedCheckpointRefs,
    ) -> None:
        assert pull_request.number == 42
        assert result == self.prepared
        assert reviewed_head == self.head
        assert refs.reviewed_ref.startswith("refs/snowcast-maintainer/reviewed/pr-42/")

    def prepare_reviewed_continuation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        refs: ReviewedCheckpointRefs,
    ) -> ContinuationReplayResult:
        self.revalidate_reviewed_checkpoint(pull_request, result, reviewed_head, refs)
        if self.continuation_result == "conflict":
            return ContinuationReplayResult(
                result="conflict",
                base_head=SHA_D,
                conflict_paths=("app/data/catalog.json",),
            )
        if self.continuation_result == "prepared":
            replay_sync = result.model_copy(
                update={"base_head": SHA_C, "rebased_head": SHA_D}
            )
            self.prepared = replay_sync
            self.head = SHA_D
            return ContinuationReplayResult(
                result="prepared",
                base_head=SHA_C,
                head=SHA_D,
                sync=replay_sync,
            )
        self.head = reviewed_head
        return ContinuationReplayResult(
            result="unchanged",
            base_head=result.base_head,
            head=reviewed_head,
            sync=result,
        )

    def continue_reviewed_conflict(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        refs: ReviewedCheckpointRefs,
    ) -> ContinuationReplayResult:
        self.continuation_result = "prepared"
        return self.prepare_reviewed_continuation(
            pull_request, result, reviewed_head, refs
        )

    def push_with_lease(self, sync: GuardedSyncResult, reviewed_head: str) -> None:
        self.push_calls += 1
        if self.push_error is not None:
            raise self.push_error
        assert sync == self.prepared
        assert reviewed_head == self.head
        self.remote = reviewed_head
        if self.github is not None:
            current = self.github.pull_requests[42]
            self.github.pull_requests[42] = current.model_copy(
                update={"head_sha": reviewed_head}
            )
            if self.after_push is not None:
                self.after_push()
            self.github.failure = self.after_push_error

    def remote_head(self, branch: str) -> str:
        assert branch == BRANCH
        if self.remote is None:
            raise AssertionError("remote is absent")
        return self.remote

    def optional_remote_head(self, branch: str) -> str | None:
        assert branch == BRANCH
        return self.remote

    def push_create_only(self, branch: str, reviewed_head: str) -> None:
        assert branch == BRANCH
        assert self.remote is None
        assert reviewed_head == SHA_B
        self.create_only_calls += 1
        self.remote = reviewed_head


def _private_state_dir(tmp_path: Path) -> Path:
    path = tmp_path / "state"
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


def _private_text(state_dir: Path, name: str, text: str) -> str:
    path = state_dir / name
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return name


def _invoke(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    *,
    github: FakeGitHub | None = None,
    repository: FakeRepository | None = None,
    base_repository: FakeRepository | None = None,
    curation_validator: Callable[..., ValidationResult] | None = None,
    proposal_validator: Callable[..., ProposalValidationResult] | None = None,
    catalog_keys_provider: Callable[[], frozenset[str]] | None = None,
    repository_root: Path | None = None,
) -> tuple[int, dict[str, object]]:
    result = main(
        argv,
        github=github,
        repository=repository,
        base_repository=base_repository,
        curation_validator=curation_validator,
        proposal_validator=proposal_validator,
        catalog_keys_provider=catalog_keys_provider,
        repository_root=repository_root,
        now=lambda: NOW,
    )
    output = capsys.readouterr().out
    assert output.count("\n") == 1
    return result, json.loads(output)


def _acquire(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    worker: str,
) -> str:
    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", worker],
    )
    assert code == 0
    outcome = payload["outcome"]
    assert isinstance(outcome, dict)
    run_id = outcome["lease_run_id"]
    assert isinstance(run_id, str)
    return run_id


def _assert_outcome(
    payload: dict[str, object],
    *,
    worker: str,
    mutation: bool,
    run_id: str | None,
) -> dict[str, object]:
    outcome = payload["outcome"]
    assert isinstance(outcome, dict)
    assert outcome["worker"] == worker
    assert outcome["mutation_occurred"] is mutation
    assert outcome.get("lease_run_id") == run_id
    assert isinstance(outcome["terminal_reason"], str)
    return outcome


EXPECTED_HANDLERS = {
    ("inspect", "curation"),
    ("inspect", "discovery"),
    ("prepare", "curation"),
    ("prepare", "continuation"),
    ("validate", "curation"),
    ("validate", "reviewed"),
    ("validate", "proposal"),
    ("publish", "push"),
    ("publish", "manual-check"),
    ("publish", "recover"),
    ("publish", "proposal"),
    ("publish", "outcome"),
    ("publish", "state"),
    ("publish", "ensure-labels"),
    ("publication-input", "create"),
}


def test_cli_exposes_only_the_bounded_capabilities_and_explicit_dispatch_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert set(HANDLERS) == EXPECTED_HANDLERS

    code, payload = _invoke(capsys, ["curation", "inventory"])

    assert code == 2
    assert payload["reason"] == "invalid-command"


def test_final_machine_state_contract_is_reduced() -> None:
    assert set(MachineState.model_fields) == {
        "schema_version",
        "reviewed_head",
        "validated_head",
        "candidate_key",
        "candidate_origin",
        "last_operation",
    }


def test_publish_outcome_reports_prepare_conflict_without_push_or_body_change(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        prepare_error=RebaseConflictError("untrusted conflict detail"),
    )
    run_id = _acquire(capsys, state_dir, "curation")
    prepare_code, prepare = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    summary = _private_text(
        state_dir,
        "outcome-summary.md",
        (
            "Automation stopped because current main conflicts with this PR.\n\n"
            "- No branch update was attempted.\n"
            "- Resolve the conflict before the next review.\n"
        ),
    )

    outcome_code, outcome_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_A,
            "--state",
            "maintainer:blocked",
            "--reason",
            "conflict",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert prepare_code == 2
    assert prepare["reason"] == "rebase-conflict"
    assert outcome_code == 0
    assert github.body_writes == 0
    assert github.pull_requests[42].body == "Owner text"
    assert github.pull_requests[42].labels == frozenset(
        {"lane:catalog-curation", "maintainer:blocked"}
    )
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine == MachineState(schema_version=2, last_operation="none")
    outcome = trusted_outcome_state(github.list_issue_comments(42))
    assert outcome is not None
    assert outcome.observed_head == SHA_A
    assert outcome.state == "maintainer:blocked"
    assert outcome.reason == "conflict"
    assert "- Resolve the conflict before the next review." in (
        github.list_issue_comments(42)[0].body
    )
    _assert_outcome(
        outcome_payload,
        worker="curation",
        mutation=True,
        run_id=run_id,
    )


def test_publish_outcome_rejects_stale_expected_head_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    run_id = _acquire(capsys, state_dir, "curation")
    summary = _private_text(state_dir, "outcome-summary.md", "CI failed.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            "maintainer:blocked",
            "--reason",
            "ci-failure",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert github.body_writes == 0
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_lock_lifecycle_uses_worker_and_run_id_without_credentials(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")

    heartbeat_code, heartbeat = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "heartbeat",
            "curation",
            "--run-id",
            run_id,
        ],
    )
    release_code, release = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            run_id,
        ],
    )

    assert heartbeat_code == release_code == 0
    _assert_outcome(heartbeat, worker="curation", mutation=True, run_id=run_id)
    _assert_outcome(release, worker="curation", mutation=True, run_id=run_id)
    assert {path.name for path in state_dir.rglob("*") if path.is_file()} <= {
        "run.transition.lock"
    }


def test_lock_acquire_allows_only_worker_named_by_unresolved_journal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "discovery", now=NOW)
    journal = PushJournal(
        work_id="proposal-stay-destination-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch=BRANCH,
        new_head=SHA_B,
        candidate_key=CANDIDATE,
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    StateStore(state_dir).save_push(journal, lease)
    lease.release()

    rejected_code, rejected = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", "curation"],
    )

    assert rejected_code == 2
    assert rejected["reason"] == "lease-ownership-error"
    assert not (state_dir / "run.lock").exists()
    accepted_code, accepted = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", "discovery"],
    )
    assert accepted_code == 0
    outcome = accepted["outcome"]
    assert isinstance(outcome, dict)
    _assert_outcome(
        accepted,
        worker="discovery",
        mutation=True,
        run_id=outcome["lease_run_id"],
    )


def test_lock_acquire_fails_closed_for_multiple_unresolved_journals(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "discovery", now=NOW)
    first = PushJournal(
        work_id="proposal-stay-destination-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch=BRANCH,
        new_head=SHA_B,
        candidate_key=CANDIDATE,
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    second = first.model_copy(
        update={
            "work_id": "proposal-stay-destination-verbier",
            "branch": "codex/catalog-curation-verbier",
            "candidate_key": "stay_destination:verbier",
        }
    )
    store = StateStore(state_dir)
    store.save_push(first, lease)
    store.save_push(second, lease)
    lease.release()

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", "discovery"],
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert not (state_dir / "run.lock").exists()


def test_mutation_rejects_wrong_worker_or_run_before_dependency_access(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    github = FakeGitHub(failure=AssertionError("must not access GitHub"))

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ensure-labels",
            "--worker",
            "discovery",
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "lease-ownership-error"
    _assert_outcome(payload, worker="discovery", mutation=False, run_id=run_id)
    assert "must not access" not in json.dumps(payload)


def test_inspect_curation_is_read_only_and_returns_all_safe_candidates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(),
            43: _pull_request(number=43, head_sha=SHA_C),
        }
    )

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    assert code == 0
    assert [item["number"] for item in payload["eligible"]] == [42, 43]
    assert payload["unresolved_pushes"] == []
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)
    assert not (state_dir / "run.lock").exists()


def test_inspect_does_not_create_missing_state_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = tmp_path / "missing-state"

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=FakeGitHub(),
    )

    assert code == 0
    assert not state_dir.exists()
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)


def test_inspect_surfaces_unresolved_journal_before_any_fresh_selection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "curation", now=NOW)
    journal = PushJournal(
        work_id="curation-pr-42",
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=42,
        branch=BRANCH,
        expected_remote_head=SHA_A,
        new_head=SHA_B,
        phase=PushPhase.AUTHORIZED,
    )
    StateStore(state_dir).save_push(journal, lease)
    lease.release()

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=FakeGitHub(),
    )

    assert code == 0
    assert payload["eligible"] == []
    assert payload["unresolved_pushes"][0]["work_id"] == "curation-pr-42"
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)


def test_inspect_discovery_reports_live_cap_keys_and_unknown_identity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    proposal = _pull_request(
        labels=frozenset({"lane:catalog-discovery", MaintainerState.PROPOSAL.value})
    )
    github = FakeGitHub(pull_requests={42: proposal})

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "discovery"],
        github=github,
        catalog_keys_provider=lambda: frozenset({"ski_area:tignes"}),
    )

    assert code == 0
    assert payload["catalog_keys"] == ["ski_area:tignes"]
    assert payload["open_proposal_count"] == 1
    assert payload["has_unknown_proposal_identity"] is True
    assert payload["can_create_proposal"] is False
    _assert_outcome(payload, worker="discovery", mutation=False, run_id=None)


def test_prepare_curation_persists_one_phase_record_for_requested_safe_pr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    github = FakeGitHub()
    repository = FakeRepository(github=github)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None
    assert work.phase is WorkPhase.PREPARED
    assert work.selected_head == SHA_A
    assert work.prepared_head == SHA_B
    assert work.sync == _sync()
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_reviewed_checkpoint_blocks_ordinary_prepare_and_resumes_validation_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    origin_run = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, origin_run, github, repository)

    blocked, blocked_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            origin_run,
        ],
        github=github,
        repository=repository,
    )
    assert blocked == 2
    assert blocked_payload["reason"] == "continuation-required"
    RunLease.load_owner(state_dir, "curation", origin_run).release()
    successor = _acquire(capsys, state_dir, "curation")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "continuation",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert payload["continuation"]["result"] == "validation-only"
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.REVIEWED
    assert work.run_id == successor


def test_advanced_continuation_requires_one_fresh_review(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    origin_run = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, origin_run, github, repository)
    RunLease.load_owner(state_dir, "curation", origin_run).release()
    successor = _acquire(capsys, state_dir, "curation")
    repository.continuation_result = "prepared"

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "continuation",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert payload["continuation"]["result"] == "review-required"
    store = StateStore(state_dir)
    work = store.load_work("curation-pr-42")
    continuation = store.load_continuation("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.PREPARED
    assert continuation is not None
    assert continuation.status is ContinuationStatus.RESOLVING
    _checkpoint_reviewed(
        capsys,
        state_dir,
        successor,
        github,
        repository,
        reviewed_head=SHA_D,
    )
    replaced = store.load_continuation("curation-pr-42")
    assert replaced is not None
    assert replaced.reviewed_head == SHA_D
    assert replaced.status is ContinuationStatus.AVAILABLE


def test_continuation_conflict_is_bounded_then_returns_to_fresh_review(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    origin_run = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, origin_run, github, repository)
    RunLease.load_owner(state_dir, "curation", origin_run).release()
    successor = _acquire(capsys, state_dir, "curation")
    repository.continuation_result = "conflict"

    first, first_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "continuation",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    second, second_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "continuation",
            "--pr",
            "42",
            "--continue-conflict",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert first == 0
    assert first_payload["continuation"] == {
        "result": "conflict-resolution-required",
        "base_head": SHA_D,
        "conflict_paths": ["app/data/catalog.json"],
    }
    assert second == 0
    assert second_payload["continuation"]["result"] == "review-required"


def test_validation_failure_preserves_exact_retryable_continuation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **_kwargs: (_ for _ in ()).throw(
            MaintainerError(ErrorReason.VALIDATION_FAILED, ErrorStage.VALIDATE)
        ),
    )

    assert code == 2
    assert payload["reason"] == "validation-failed"
    continuation = StateStore(state_dir).load_continuation("curation-pr-42")
    assert continuation is not None
    assert continuation.status is ContinuationStatus.AVAILABLE
    assert continuation.validation_status is ContinuationValidationStatus.FAILED


def test_legacy_reviewed_work_can_be_adopted_only_by_successor_lease(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    origin_run = _prepare_curation(capsys, state_dir, github, repository)
    store = StateStore(state_dir)
    lease = RunLease.load_owner(state_dir, "curation", origin_run)
    prepared = store.load_work("curation-pr-42")
    assert prepared is not None
    store.save_work(
        prepared.model_copy(
            update={
                "phase": WorkPhase.REVIEWED,
                "reviewed_head": SHA_B,
                "updated_at": NOW + timedelta(seconds=1),
            }
        ),
        lease,
    )
    lease.release()
    successor = _acquire(capsys, state_dir, "curation")

    _checkpoint_reviewed(
        capsys,
        state_dir,
        successor,
        github,
        repository,
        adopt_existing=True,
    )

    continuation = store.load_continuation("curation-pr-42")
    assert continuation is not None
    assert continuation.origin_run_id == origin_run
    assert continuation.recovery_run_id == successor


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (RebaseConflictError("untrusted conflict prose"), "rebase-conflict"),
        (StaleRemoteHeadError("untrusted stale prose"), "stale-head"),
        (GitTransportError("untrusted transport prose"), "transport-failed"),
    ],
)
def test_prepare_safe_stops_are_structured_without_exception_prose(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    reason: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(),
        repository=FakeRepository(prepare_error=error),
    )

    assert code == 2
    assert payload["reason"] == reason
    assert "untrusted" not in json.dumps(payload)
    outcome = _assert_outcome(
        payload,
        worker="curation",
        mutation=True,
        run_id=run_id,
    )
    assert outcome["last_phase"] == "selected"


def _prepare_curation(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    github: FakeGitHub,
    repository: FakeRepository,
) -> str:
    run_id = _acquire(capsys, state_dir, "curation")
    code, _payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert code == 0
    return run_id


def test_validate_curation_binds_reviewed_head_and_objective_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    observed: dict[str, object] = {}

    def validator(**kwargs: object) -> ValidationResult:
        observed.update(kwargs)
        return _validation_result()

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=validator,
    )

    assert code == 0
    assert observed["sync"] == _sync()
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.VALIDATED
    assert work.reviewed_head == work.validated_head == SHA_B
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_validate_curation_exact_retry_returns_existing_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    validator_calls = 0

    def validator(**kwargs: object) -> ValidationResult:
        nonlocal validator_calls
        validator_calls += 1
        return _validation_result()

    command = [
        "--state-dir",
        str(state_dir),
        "validate",
        "curation",
        "--pr",
        "42",
        "--reviewed-head",
        SHA_B,
        "--report",
        "docs/catalog-curation/nendaz.json",
        "--base-dir",
        str(tmp_path / "base"),
        "--run-id",
        run_id,
    ]
    first_code, _first_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=validator,
    )
    retry_code, retry_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=validator,
    )

    assert first_code == retry_code == 0, retry_payload
    assert validator_calls == 1
    assert retry_payload["validation"] == {
        "result": "already-validated",
        "validated_head": SHA_B,
    }
    outcome = _assert_outcome(
        retry_payload,
        worker="curation",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "already_validated"


def test_validate_curation_retry_rejects_a_different_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    first_code, _first_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **kwargs: _validation_result(),
    )
    retry_code, retry_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/other.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **kwargs: _validation_result(),
    )

    assert first_code == 0
    assert retry_code == 2
    assert retry_payload["reason"] == "invalid-command"
    assert retry_payload["stage"] == "validate"


def test_validate_curation_retry_rejects_a_changed_validation_base(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    command = [
        "--state-dir",
        str(state_dir),
        "validate",
        "curation",
        "--pr",
        "42",
        "--reviewed-head",
        SHA_B,
        "--report",
        "docs/catalog-curation/nendaz.json",
        "--base-dir",
        str(tmp_path / "base"),
        "--run-id",
        run_id,
    ]
    first_code, _first_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=lambda **kwargs: _validation_result(),
    )
    retry_code, retry_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_A),
        curation_validator=lambda **kwargs: _validation_result(),
    )

    assert first_code == 0
    assert retry_code == 2
    assert retry_payload["reason"] == "validation-failed"
    assert retry_payload["check"] == "post-validation"
    assert retry_payload["kind"] == "mismatch"


def test_validate_failure_exposes_only_allowlisted_check_and_kind(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    def fail(**kwargs: object) -> ValidationResult:
        raise MaintainerError(
            ErrorReason.VALIDATION_FAILED,
            ErrorStage.VALIDATE,
            ErrorCheck.CATALOG_TESTS,
            ErrorKind.COMMAND_FAILED,
            "Validation command failed",
        )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=fail,
    )

    assert code == 2
    assert payload["reason"] == "validation-failed"
    assert payload["check"] == "catalog-tests"
    assert payload["kind"] == "command-failed"
    assert "kwargs" not in json.dumps(payload)


def test_validate_proposal_rechecks_inventory_and_persists_candidate_facts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None)

    def validator(**kwargs: object) -> ProposalValidationResult:
        return ProposalValidationResult(
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            validated_head=SHA_B,
            report_path="docs/catalog-curation/nendaz.json",
        )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        proposal_validator=validator,
        catalog_keys_provider=frozenset,
    )

    assert code == 0
    work_id = str(payload["work_id"])
    work = StateStore(state_dir).load_work(work_id)
    assert work is not None and work.phase is WorkPhase.VALIDATED
    assert work.candidate_key == CANDIDATE
    assert work.candidate_origin == "backlog"
    assert work.report_path == "docs/catalog-curation/nendaz.json"
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_validate_proposal_checks_fetched_main_not_the_modified_worktree(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = tmp_path / "proposal-worktree"
    catalog_path = repository_root / "app/data/catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(_catalog_json(include_candidate=True), encoding="utf-8")
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(
        head=SHA_B,
        remote=None,
        root=repository_root,
        main_catalog_json=_catalog_json(),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "external",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        proposal_validator=lambda **kwargs: ProposalValidationResult(
            candidate_key=CANDIDATE,
            candidate_origin="external",
            validated_head=SHA_B,
            report_path="docs/catalog-curation/nendaz.json",
        ),
        repository_root=repository_root,
    )

    assert code == 0
    assert payload["status"] == "ok"
    assert repository.fetch_main_calls == 1


def test_validate_proposal_rejects_candidate_in_fetched_main(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = tmp_path / "proposal-worktree"
    catalog_path = repository_root / "app/data/catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(_catalog_json(include_candidate=True), encoding="utf-8")
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    repository = FakeRepository(
        head=SHA_B,
        remote=None,
        root=repository_root,
        main_catalog_json=_catalog_json(include_candidate=True),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "external",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={}),
        repository=repository,
        proposal_validator=lambda **kwargs: pytest.fail(
            "main duplicate must stop before proposal validation"
        ),
        repository_root=repository_root,
    )

    assert code == 2
    assert payload["reason"] == "duplicate-proposal"
    assert repository.fetch_main_calls == 1


@pytest.mark.parametrize(
    ("catalog_keys", "open_key", "reason"),
    [
        (frozenset({CANDIDATE}), False, "duplicate-proposal"),
        (frozenset(), True, "duplicate-proposal"),
    ],
)
def test_validate_proposal_stops_for_catalog_or_open_key_duplicate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    catalog_keys: frozenset[str],
    open_key: bool,
    reason: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(pull_requests={})
    if open_key:
        proposal = _pull_request(
            labels=frozenset(
                {"lane:catalog-discovery", MaintainerState.PROPOSAL.value}
            ),
            head_sha=SHA_B,
        )
        machine = MachineState(
            schema_version=2,
            reviewed_head=SHA_B,
            validated_head=SHA_B,
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            last_operation="published",
        )
        github.pull_requests[42] = proposal
        github.comments[42] = [
            GitHubComment(
                1,
                f"{SUMMARY_MARKER}\nReviewed.\n{render_machine_state(machine)}",
                "lampssy",
            )
        ]

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=FakeRepository(head=SHA_B, remote=None),
        proposal_validator=lambda **kwargs: pytest.fail("must stop before validation"),
        catalog_keys_provider=lambda: catalog_keys,
    )

    assert code == 2
    assert payload["reason"] == reason
    _assert_outcome(payload, worker="discovery", mutation=False, run_id=run_id)


def _validated_curation(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    resulting_graph_markdown: str | None = None,
) -> str:
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
        reviewed_head=repository.head,
    )
    code, _payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(state_dir.parent / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **kwargs: _validation_result().model_copy(
            update={"resulting_graph_markdown": resulting_graph_markdown}
        ),
    )
    assert code == 0
    return run_id


def _checkpoint_reviewed(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    run_id: str,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    reviewed_head: str = SHA_B,
    adopt_existing: bool = False,
    expect_success: bool = True,
) -> tuple[int, dict[str, object]]:
    arguments = [
        "--state-dir",
        str(state_dir),
        "validate",
        "reviewed",
        "--pr",
        "42",
        "--reviewed-head",
        reviewed_head,
        "--report",
        "docs/catalog-curation/nendaz.json",
        "--run-id",
        run_id,
    ]
    if adopt_existing:
        arguments.insert(-2, "--adopt-existing")
    code, payload = _invoke(
        capsys,
        arguments,
        github=github,
        repository=repository,
    )
    if expect_success:
        assert code == 0, payload
    return code, payload


def _manual_check_publication_files(state_dir: Path) -> tuple[str, str]:
    return (
        _private_text(state_dir, "manual-check-summary.md", "Owner review required."),
        _private_text(
            state_dir,
            "manual-check-body.md",
            f"Reviewed unresolved work.\n\n{CANONICAL_GRAPH}",
        ),
    )


def _publish_manual_check(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    run_id: str,
    github: FakeGitHub,
    repository: FakeRepository,
    reviewed_head: str = SHA_B,
) -> tuple[int, dict[str, object]]:
    work = StateStore(state_dir).load_work("curation-pr-42")
    if work is not None and work.phase is WorkPhase.PREPARED:
        checkpoint_code, checkpoint_payload = _checkpoint_reviewed(
            capsys,
            state_dir,
            run_id,
            github,
            repository,
            reviewed_head=reviewed_head,
            expect_success=False,
        )
        if checkpoint_code != 0:
            return checkpoint_code, checkpoint_payload
    summary, body = _manual_check_publication_files(state_dir)
    return _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            reviewed_head,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )


def test_publish_manual_check_pushes_reviewed_unvalidated_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 0
    assert repository.push_calls == 1
    assert repository.revalidate_calls == 2
    assert github.pull_requests[42].head_sha == SHA_B
    assert MaintainerState.MANUAL_CHECK.value in github.pull_requests[42].labels
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None
    assert machine.reviewed_head == SHA_B
    assert machine.validated_head is None
    assert machine.last_operation == "reviewed"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    assert work is not None and work.phase is WorkPhase.REVIEWED
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_publish_manual_check_accepts_writer_created_graph_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    summary = create_publication_text(
        lease,
        kind="summary",
        payload=b"Owner review required.",
    )
    body = create_publication_text(
        lease,
        kind="body",
        payload=f"Reviewed unresolved work.\n\n{CANONICAL_GRAPH}".encode(),
    )

    code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert CANONICAL_GRAPH in github.pull_requests[42].body


def test_publish_manual_check_reuses_head_recorded_before_validation_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    def fail_validation(**_kwargs: object) -> ValidationResult:
        raise MaintainerError(
            ErrorReason.VALIDATION_FAILED,
            ErrorStage.VALIDATE,
        )

    validation_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=fail_validation,
    )
    assert validation_code == 2
    reviewed = StateStore(state_dir).load_work("curation-pr-42")
    assert reviewed is not None and reviewed.phase is WorkPhase.REVIEWED

    code, _ = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 0
    assert repository.revalidate_calls == 2
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.last_operation == "reviewed"


def test_publish_manual_check_accepts_reviewed_descendant_from_prepared_work(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    store = StateStore(state_dir)
    prepared = store.load_work("curation-pr-42")
    assert prepared is not None and prepared.phase is WorkPhase.PREPARED
    repository.head = SHA_C

    code, _ = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
        reviewed_head=SHA_C,
    )

    assert code == 0
    assert github.pull_requests[42].head_sha == SHA_C
    work = store.load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.REVIEWED
    assert work.reviewed_head == SHA_C
    journal = store.load_push("curation-pr-42")
    assert journal is not None and journal.new_head == SHA_C
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.reviewed_head == SHA_C


def test_publish_manual_check_rejects_stale_remote_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github, remote=SHA_C)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert repository.push_calls == 0
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.AUTHORIZED
    assert github.pull_requests[42].head_sha == SHA_A


def test_publish_manual_check_revalidation_failure_prevents_push_authorization(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        revalidate_error=RepositorySafetyError("untrusted local detail"),
    )
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    repository.head = SHA_C

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
        reviewed_head=SHA_C,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert repository.push_calls == 0
    assert StateStore(state_dir).load_push("curation-pr-42") is None
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.PREPARED
    assert "untrusted" not in json.dumps(payload)


def test_publish_manual_check_binds_publication_text_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    summary_name = _private_text(
        state_dir,
        "manual-check-summary.md",
        "Original reviewed summary.",
    )
    body_name = _private_text(
        state_dir,
        "manual-check-body.md",
        f"Original reviewed body.\n\n{CANONICAL_GRAPH}",
    )

    def replace_publication_text() -> None:
        _private_text(
            state_dir,
            "manual-check-summary.md",
            "Replacement after push.",
        )
        _private_text(
            state_dir,
            "manual-check-body.md",
            "Replacement body after push.",
        )

    repository = FakeRepository(github=github, after_push=replace_publication_text)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary_name,
            "--body-file",
            body_name,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert "Original reviewed body." in github.pull_requests[42].body
    assert "Replacement body after push." not in github.pull_requests[42].body
    comments = github.list_issue_comments(42)
    assert len(comments) == 1
    assert "Original reviewed summary." in comments[0].body
    assert "Replacement after push." not in comments[0].body


def test_publish_manual_check_requires_canonical_graph_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    summary = _private_text(state_dir, "summary.md", "Owner review required.")
    body = _private_text(state_dir, "body.md", "Reviewed unresolved work.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert repository.push_calls == 0
    assert github.body_writes == 0


def test_publish_manual_check_rejects_report_outside_the_prepared_diff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    summary, body = _manual_check_publication_files(state_dir)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/unrelated.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert repository.push_calls == 0
    assert github.body_writes == 0


def test_publish_manual_check_waits_for_github_to_observe_exact_pushed_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def delay_pr_head() -> None:
        github.pull_request_head_reads.extend((SHA_A, SHA_B))

    repository = FakeRepository(github=github, after_push=delay_pr_head)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "ops.maintainer.capabilities.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    code, _ = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 0
    assert sleeps == [3.0]
    assert MaintainerState.MANUAL_CHECK.value in github.pull_requests[42].labels


def test_publish_manual_check_rejects_unexpected_pr_head_without_waiting(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def expose_unexpected_pr_head() -> None:
        github.pull_request_head_reads.append(SHA_C)

    repository = FakeRepository(
        github=github,
        after_push=expose_unexpected_pr_head,
    )
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "ops.maintainer.capabilities.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert sleeps == []
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.label_writes == 0


def test_publish_manual_check_stops_after_bounded_pr_head_wait(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def keep_old_pr_head() -> None:
        github.pull_request_head_reads.extend([SHA_A] * 6)

    repository = FakeRepository(github=github, after_push=keep_old_pr_head)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "ops.maintainer.capabilities.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert sleeps == [3.0] * 5
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED


def test_publish_manual_check_rejects_remote_drift_during_pr_head_wait(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def delay_pr_head() -> None:
        github.pull_request_head_reads.extend((SHA_A, SHA_B))

    repository = FakeRepository(github=github, after_push=delay_pr_head)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    def move_remote(_seconds: float) -> None:
        repository.remote = SHA_C

    monkeypatch.setattr("ops.maintainer.capabilities.sleep", move_remote)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.label_writes == 0


def test_publish_manual_check_rejects_remote_drift_when_pr_api_is_current(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)

    def move_remote() -> None:
        repository.remote = SHA_C

    repository.after_push = move_remote
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.label_writes == 0


def test_publish_manual_check_recovers_publication_after_successful_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        after_push_error=GitHubError("untrusted publication detail"),
    )
    old_run = _prepare_curation(capsys, state_dir, github, repository)

    failed_code, failed_payload = _publish_manual_check(
        capsys,
        state_dir,
        old_run,
        github,
        repository,
    )

    assert failed_code == 2
    assert failed_payload["reason"] == "transport-failed"
    assert repository.push_calls == 1
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.REVIEWED
    assert "untrusted" not in json.dumps(failed_payload)

    github.failure = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    assert recover_payload["continuation"] == {
        "reviewed_head": SHA_B,
        "validation_status": "absent",
    }

    publish_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        successor,
        github,
        repository,
    )
    retry_code, retry_payload = _publish_manual_check(
        capsys,
        state_dir,
        successor,
        github,
        repository,
    )

    assert publish_code == 0
    assert retry_code == 0
    assert repository.push_calls == 1
    recovered = StateStore(state_dir).load_push("curation-pr-42")
    assert recovered is not None and recovered.phase is PushPhase.PUBLISHED
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.last_operation == "reviewed"
    outcome = _assert_outcome(
        retry_payload,
        worker="curation",
        mutation=False,
        run_id=successor,
    )
    assert outcome["terminal_reason"] == "manual-check"


def test_recovered_reviewed_only_journal_can_publish_owner_decision(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        after_push_error=GitHubError("untrusted publication detail"),
    )
    old_run = _prepare_curation(capsys, state_dir, github, repository)
    failed_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        old_run,
        github,
        repository,
    )
    assert failed_code == 2
    github.failure = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    assert recover_payload["continuation"]["validation_status"] == "absent"
    summary = _private_text(
        state_dir,
        "owner-decision-summary.md",
        "Owner must choose the weather identity boundary.",
    )
    monkeypatch.setattr(
        "ops.maintainer.cli.GitRepository",
        lambda _root: repository,
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:owner-decision",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--run-id",
            successor,
        ],
        github=github,
    )

    assert code == 0
    assert payload["status"] == "ok"
    assert MaintainerState.OWNER_DECISION.value in github.pull_requests[42].labels
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None
    assert machine.reviewed_head == SHA_B
    assert machine.validated_head is None


def test_publish_manual_check_recovers_authorized_journal_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        push_error=GitTransportError("untrusted transport detail"),
    )
    old_run = _prepare_curation(capsys, state_dir, github, repository)
    failed_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        old_run,
        github,
        repository,
    )
    assert failed_code == 2
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.AUTHORIZED

    repository.push_error = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    recovered = StateStore(state_dir).load_push("curation-pr-42")
    assert recovered is not None and recovered.phase is PushPhase.PUSHED
    assert github.pull_requests[42].head_sha == SHA_B

    publish_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        successor,
        github,
        repository,
    )
    assert publish_code == 0
    published = StateStore(state_dir).load_push("curation-pr-42")
    assert published is not None and published.phase is PushPhase.PUBLISHED


def test_publish_recover_rejects_unrelated_remote_head_as_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    old = RunLease.acquire(state_dir, "curation", now=NOW)
    store = StateStore(state_dir)
    authorized = PushJournal(
        work_id="curation-pr-42",
        worker="curation",
        origin_run_id=old.run_id,
        recovery_run_id=old.run_id,
        pr_number=42,
        branch=BRANCH,
        expected_remote_head=SHA_A,
        new_head=SHA_B,
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(authorized, old)
    store.save_push(authorized.model_copy(update={"phase": PushPhase.PUSHED}), old)
    successor = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor.run_id,
        ],
        github=FakeGitHub(),
        repository=FakeRepository(remote=SHA_C),
    )

    assert code == 2
    assert payload["reason"] == "stale-head"


def test_publish_push_journals_before_exact_force_with_lease_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert repository.push_calls == 1
    journal = StateStore(state_dir).load_push("curation-pr-42")
    work = StateStore(state_dir).load_work("curation-pr-42")
    continuation = StateStore(state_dir).load_continuation("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert work is not None and work.phase is WorkPhase.PUSHED
    assert continuation is not None
    assert continuation.status is ContinuationStatus.CONSUMED
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_completed_curation_journal_can_start_a_second_fix_cycle(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    first_run = _validated_curation(capsys, state_dir, github, repository)
    first_push, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            first_run,
        ],
        github=github,
        repository=repository,
    )
    assert first_push == 0
    summary = _private_text(state_dir, "summary.md", "First cycle ready.")
    body = _private_text(state_dir, "body.md", "First cycle synopsis.")
    first_publish, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            first_run,
        ],
        github=github,
        repository=repository,
    )
    assert first_publish == 0
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            first_run,
        ],
    )
    assert release_code == 0

    second_run = _acquire(capsys, state_dir, "curation")
    cycle_time = NOW + timedelta(hours=1)
    sync = GuardedSyncResult(
        target_branch=BRANCH,
        original_head=SHA_B,
        rebased_head=SHA_C,
        backup_ref=(
            f"refs/snowcast-maintainer/backups/pr-42/20260708T110000Z-{SHA_B[:12]}"
        ),
        prepared_ref=(
            f"refs/snowcast-maintainer/prepared/pr-42/{SHA_D[:12]}-{SHA_C[:12]}"
        ),
        base_head=SHA_D,
        merge_base=SHA_A,
    )
    store = StateStore(state_dir)
    selected = WorkState(
        work_id="curation-pr-42",
        worker="curation",
        run_id=second_run,
        phase=WorkPhase.SELECTED,
        updated_at=cycle_time,
        pr_number=42,
        selected_head=SHA_B,
    )
    store.begin_work(selected, RunLease.load_owner(state_dir, "curation", second_run))
    prepared = selected.model_copy(
        update={
            "phase": WorkPhase.PREPARED,
            "updated_at": cycle_time + timedelta(seconds=1),
            "prepared_head": SHA_C,
            "backup_ref": sync.backup_ref,
            "sync": sync,
        }
    )
    lease = RunLease.load_owner(state_dir, "curation", second_run)
    store.save_work(prepared, lease)
    reviewed = prepared.model_copy(
        update={
            "phase": WorkPhase.REVIEWED,
            "updated_at": cycle_time + timedelta(seconds=2),
            "reviewed_head": SHA_C,
        }
    )
    store.save_work(reviewed, lease)
    validated = reviewed.model_copy(
        update={
            "phase": WorkPhase.VALIDATED,
            "updated_at": cycle_time + timedelta(seconds=3),
            "validated_head": SHA_C,
        }
    )
    store.save_work(validated, lease)
    continuation = ReviewedContinuation(
        work_id="curation-pr-42",
        origin_run_id=second_run,
        recovery_run_id=second_run,
        updated_at=cycle_time + timedelta(seconds=4),
        pr_number=42,
        selected_head=SHA_B,
        reviewed_head=SHA_C,
        report_path="docs/catalog-curation/nendaz.json",
        sync=sync,
        reviewed_ref=(
            f"refs/snowcast-maintainer/reviewed/pr-42/{SHA_B[:12]}-{SHA_C[:12]}"
        ),
        squash_ref=(
            f"refs/snowcast-maintainer/continuations/pr-42/{SHA_D[:12]}-{SHA_C[:12]}"
        ),
        status=ContinuationStatus.AVAILABLE,
        validation_status=ContinuationValidationStatus.NOT_RUN,
    )
    store.save_continuation(continuation, lease)
    store.save_continuation(
        continuation.model_copy(
            update={
                "updated_at": cycle_time + timedelta(seconds=5),
                "status": ContinuationStatus.VALIDATED,
                "validation_status": ContinuationValidationStatus.PASSED,
            }
        ),
        lease,
    )
    repository.prepared = sync
    repository.head = SHA_C
    repository.remote = SHA_B

    second_push, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            second_run,
        ],
        github=github,
        repository=repository,
    )

    assert second_push == 0
    journal = store.load_push("curation-pr-42")
    assert journal is not None
    assert journal.origin_run_id == second_run
    assert journal.new_head == SHA_C
    assert journal.phase is PushPhase.PUSHED
    assert repository.push_calls == 2
    _assert_outcome(payload, worker="curation", mutation=True, run_id=second_run)


def test_publish_push_stale_remote_is_safe_and_journal_remains_authorized(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        push_error=StaleRemoteHeadError("untrusted remote value"),
    )
    run_id = _validated_curation(capsys, state_dir, github, repository)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.AUTHORIZED
    assert "untrusted" not in json.dumps(payload)


def test_publish_recover_adopts_one_journal_and_reconciles_observed_new_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    old = RunLease.acquire(state_dir, "curation", now=NOW)
    store = StateStore(state_dir)
    store.save_push(
        PushJournal(
            work_id="curation-pr-42",
            worker="curation",
            origin_run_id=old.run_id,
            recovery_run_id=old.run_id,
            pr_number=42,
            branch=BRANCH,
            expected_remote_head=SHA_A,
            new_head=SHA_B,
            phase=PushPhase.AUTHORIZED,
        ),
        old,
    )
    successor = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW + timedelta(hours=7),
    )
    repository = FakeRepository(head=SHA_B, remote=SHA_B)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor.run_id,
        ],
        github=FakeGitHub(),
        repository=repository,
    )

    assert code == 0
    recovered = store.load_push("curation-pr-42")
    assert recovered is not None
    assert recovered.origin_run_id == old.run_id
    assert recovered.recovery_run_id == successor.run_id
    assert recovered.phase is PushPhase.PUSHED
    assert payload["continuation"] == {
        "reviewed_head": SHA_B,
        "validation_status": "unknown",
    }
    _assert_outcome(
        payload,
        worker="curation",
        mutation=True,
        run_id=successor.run_id,
    )


def test_recovered_discovery_journal_can_finish_publication_with_successor(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=SHA_B, github=github)
    old_run_id, work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    old = RunLease.load_owner(state_dir, "discovery", old_run_id)
    store = StateStore(state_dir)
    store.save_push(
        PushJournal(
            work_id=work_id,
            worker="discovery",
            origin_run_id=old.run_id,
            recovery_run_id=old.run_id,
            branch=BRANCH,
            new_head=SHA_B,
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            report_path="docs/catalog-curation/nendaz.json",
            resulting_graph_markdown=CANONICAL_GRAPH,
            phase=PushPhase.AUTHORIZED,
        ),
        old,
    )
    successor = RunLease.acquire(
        state_dir,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    recover_code, _recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            work_id,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )
    assert recover_code == 0

    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")
    publish_code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert publish_code == 0
    assert github.pr_creates == 1
    journal = store.load_push(work_id)
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    _assert_outcome(
        payload,
        worker="discovery",
        mutation=True,
        run_id=successor.run_id,
    )


def test_recovered_discovery_journal_without_graph_evidence_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    old_run_id, work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    old = RunLease.load_owner(state_dir, "discovery", old_run_id)
    store = StateStore(state_dir)
    store.save_push(
        PushJournal(
            work_id=work_id,
            worker="discovery",
            origin_run_id=old.run_id,
            recovery_run_id=old.run_id,
            branch=BRANCH,
            new_head=SHA_B,
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            phase=PushPhase.AUTHORIZED,
        ),
        old,
    )
    (state_dir / "work" / f"{work_id}.json").unlink()
    successor = RunLease.acquire(
        state_dir,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    recover_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            work_id,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )
    assert recover_code == 0
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    publish_code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert publish_code == 2
    assert payload["reason"] == "invalid-command"
    assert github.pr_creates == 0


def test_publish_recover_fails_closed_for_multiple_journals(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "discovery", now=NOW)
    store = StateStore(state_dir)
    first = PushJournal(
        work_id="proposal-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch=BRANCH,
        new_head=SHA_B,
        candidate_key=CANDIDATE,
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(first, lease)
    store.save_push(
        first.model_copy(
            update={
                "work_id": "proposal-verbier",
                "branch": "codex/catalog-curation-verbier",
                "candidate_key": "stay_destination:verbier",
            }
        ),
        lease,
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "proposal-nendaz",
            "--run-id",
            lease.run_id,
        ],
        github=FakeGitHub(pull_requests={}),
        repository=FakeRepository(head=SHA_B, remote=None),
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"


def _validated_proposal(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    catalog_keys_provider: Callable[[], frozenset[str]] | None = frozenset,
    repository_root: Path | None = None,
    resulting_graph_markdown: str | None = CANONICAL_GRAPH,
) -> tuple[str, str]:
    run_id = _acquire(capsys, state_dir, "discovery")
    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        proposal_validator=lambda **kwargs: ProposalValidationResult(
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            validated_head=SHA_B,
            report_path="docs/catalog-curation/nendaz.json",
            resulting_graph_markdown=resulting_graph_markdown,
        ),
        catalog_keys_provider=catalog_keys_provider,
        repository_root=repository_root,
    )
    assert code == 0
    return run_id, str(payload["work_id"])


def test_publish_proposal_rechecks_fetched_main_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = tmp_path / "proposal-worktree"
    catalog_path = repository_root / "app/data/catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(_catalog_json(include_candidate=True), encoding="utf-8")
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(
        head=SHA_B,
        remote=None,
        github=github,
        root=repository_root,
        main_catalog_json=_catalog_json(),
    )
    run_id, _work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        catalog_keys_provider=None,
        repository_root=repository_root,
    )
    repository.main_catalog_json = _catalog_json(include_candidate=True)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        repository_root=repository_root,
    )

    assert code == 2
    assert payload["reason"] == "duplicate-proposal"
    assert repository.create_only_calls == 0
    assert repository.fetch_main_calls == 2


def test_publish_proposal_uses_only_private_state_files_and_finishes_work(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, work_id = _validated_proposal(capsys, state_dir, github, repository)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 0
    assert github.pr_creates == 1
    assert github.comment_creates == 1
    work = StateStore(state_dir).load_work(work_id)
    assert work is not None and work.phase is WorkPhase.PUBLISHED
    assert work.pr_number == 71
    journal = StateStore(state_dir).load_push(work_id)
    assert journal is not None
    assert journal.report_path == "docs/catalog-curation/nendaz.json"
    assert journal.resulting_graph_markdown == CANONICAL_GRAPH
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_publish_proposal_requires_the_validated_canonical_graph_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, _work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(state_dir, "body.md", "Owner proposal context")
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert repository.create_only_calls == 0
    assert github.pr_creates == 0


def test_publish_proposal_idempotent_retry_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, _work_id = _validated_proposal(capsys, state_dir, github, repository)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "proposal",
        "--branch",
        BRANCH,
        "--candidate-key",
        CANDIDATE,
        "--candidate-origin",
        "backlog",
        "--head",
        SHA_B,
        "--title-file",
        title,
        "--body-file",
        body,
        "--summary-file",
        summary,
        "--run-id",
        run_id,
    ]
    first_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )
    assert first_code == 0

    code, payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 0
    assert github.pr_creates == 1
    assert github.comment_creates == 1
    outcome = _assert_outcome(
        payload,
        worker="discovery",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "proposal-unchanged"


def test_publish_proposal_rejects_absolute_publication_file_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None)
    run_id, _work_id = _validated_proposal(capsys, state_dir, github, repository)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret source", encoding="utf-8")
    os.chmod(outside, 0o600)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            str(outside),
            "--body-file",
            "body.md",
            "--summary-file",
            "summary.md",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert payload["check"] == "publication-input"
    assert payload["kind"] == "not-basename"
    assert "secret source" not in json.dumps(payload)
    assert repository.create_only_calls == 0


def test_publish_state_ready_adopts_legacy_body_with_explicit_permission(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.\n")
    body = _private_text(
        state_dir,
        "body.md",
        "## Snowcast catalog review\n\nCurrent concise synopsis.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert "Owner text" not in github.pull_requests[42].body
    assert "Current concise synopsis." in github.pull_requests[42].body
    assert github.pull_requests[42].body.count("snowcast-maintainer-body:start") == 1
    assert github.pull_requests[42].body.count("snowcast-maintainer-body:end") == 1
    assert MaintainerState.READY.value in github.pull_requests[42].labels
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.reviewed_head == SHA_B
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_publish_state_requires_the_validated_canonical_graph_before_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.\n")
    body = _private_text(
        state_dir,
        "body.md",
        "## Snowcast catalog review\n\nCurrent concise synopsis.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert github.pull_requests[42].body == "Owner text"
    assert MaintainerState.READY.value not in github.pull_requests[42].labels


def test_publish_state_accepts_the_exact_validated_canonical_graph(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.\n")
    body = _private_text(
        state_dir,
        "body.md",
        f"## Snowcast catalog review\n\nCurrent concise synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, _payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert CANONICAL_GRAPH.strip() in github.pull_requests[42].body
    assert MaintainerState.READY.value in github.pull_requests[42].labels


@pytest.mark.parametrize(
    ("state", "check_state"),
    [("ready", "success"), ("waiting-ci", "pending")],
)
def test_publish_state_readiness_requires_synopsis_before_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    state: str,
    check_state: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": check_state}
    )
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            f"maintainer:{state}",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert github.pull_requests[42].body == "Owner text"
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_publish_state_ready_stops_for_pending_ci_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    summary = _private_text(state_dir, "summary.md", "Checks pending.")
    body = _private_text(state_dir, "body.md", "Current review synopsis.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "not-ready"
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_waiting_ci_requires_pushed_evidence_not_only_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending", "head_sha": SHA_B}
    )
    summary = _private_text(state_dir, "summary.md", "Checks pending.")
    body = _private_text(state_dir, "body.md", "Current review synopsis.")
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:waiting-ci",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        run_id,
    ]

    rejected_code, rejected = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert rejected_code == 2
    assert rejected["reason"] == "validation-required"
    assert github.comment_creates == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"head_sha": SHA_A}
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0

    accepted_code, accepted = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert accepted_code == 0
    assert MaintainerState.WAITING_CI.value in github.pull_requests[42].labels
    _assert_outcome(accepted, worker="curation", mutation=True, run_id=run_id)


def test_publish_state_rejects_stale_work_from_prior_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    old_run = _validated_curation(capsys, state_dir, github, repository)
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"head_sha": SHA_B}
    )
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    summary = _private_text(state_dir, "summary.md", "Ready.")
    body = _private_text(state_dir, "body.md", "Current review synopsis.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "validation-required"
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_adopted_pushed_journal_authorizes_successor_state_publication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    old_run = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            old_run,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    assert recover_payload["continuation"] == {
        "reviewed_head": SHA_B,
        "validation_status": "validated",
    }
    summary = _private_text(state_dir, "summary.md", "Ready.")
    body = _private_text(state_dir, "body.md", "Recovered review synopsis.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert MaintainerState.READY.value in github.pull_requests[42].labels
    _assert_outcome(payload, worker="curation", mutation=True, run_id=successor)


def test_publish_state_idempotent_retry_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.")
    body = _private_text(state_dir, "body.md", "Current review synopsis.")
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:ready",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        run_id,
    ]
    first_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )
    assert first_code == 0
    bodies_before = github.body_writes
    comments_before = github.comment_creates
    labels_before = github.label_writes

    code, payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert code == 0
    assert github.body_writes == bodies_before
    assert github.comment_creates == comments_before
    assert github.label_writes == labels_before
    outcome = _assert_outcome(
        payload,
        worker="curation",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "ready-unchanged"


def test_ensure_labels_is_a_leased_publish_capability(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub()

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ensure-labels",
            "--worker",
            "discovery",
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 0
    assert github.ensured_labels == 1
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_ensure_labels_noop_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(labels_changed=False)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ensure-labels",
            "--worker",
            "discovery",
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 0
    outcome = _assert_outcome(
        payload,
        worker="discovery",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "labels-unchanged"


def test_internal_error_and_sensitive_values_never_leak(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    secret = "token=super-secret-value"
    monkeypatch.setenv("SNOWCAST_SECRET_TEST", secret)
    github = FakeGitHub(failure=RuntimeError(f"{secret} raw subprocess prose"))

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    rendered = json.dumps(payload)
    assert code == 2
    assert payload["reason"] == "internal-error"
    assert secret not in rendered
    assert "subprocess" not in rendered
    assert "Owner text" not in rendered
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)

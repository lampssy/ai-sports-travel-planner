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
    GitTransportError,
    GuardedSyncResult,
    RebaseConflictError,
    RepositorySafetyError,
    StaleRemoteHeadError,
)
from ops.maintainer.github import GitHubComment, GitHubError
from ops.maintainer.intent import IntentDiffEntry, IntentSnapshot
from ops.maintainer.models import MachineState, MaintainerState, PullRequest
from ops.maintainer.publication import render_machine_state, trusted_machine_state
from ops.maintainer.runtime import RunLease
from ops.maintainer.state import (
    PushJournal,
    PushPhase,
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
BRANCH = "codex/catalog-curation-nendaz"


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
        return self.pull_requests[number]

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

    def current_head(self) -> str:
        return self.head

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
) -> tuple[int, dict[str, object]]:
    result = main(
        argv,
        github=github,
        repository=repository,
        base_repository=base_repository,
        curation_validator=curation_validator,
        proposal_validator=proposal_validator,
        catalog_keys_provider=catalog_keys_provider,
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
    ("validate", "curation"),
    ("validate", "proposal"),
    ("publish", "push"),
    ("publish", "manual-check"),
    ("publish", "recover"),
    ("publish", "proposal"),
    ("publish", "state"),
    ("publish", "ensure-labels"),
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


def test_validate_failure_exposes_only_allowlisted_check_and_kind(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

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
) -> str:
    run_id = _prepare_curation(capsys, state_dir, github, repository)
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
        curation_validator=lambda **kwargs: _validation_result(),
    )
    assert code == 0
    return run_id


def _manual_check_publication_files(state_dir: Path) -> tuple[str, str]:
    return (
        _private_text(state_dir, "manual-check-summary.md", "Owner review required."),
        _private_text(state_dir, "manual-check-body.md", "Reviewed unresolved work."),
    )


def _publish_manual_check(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    run_id: str,
    github: FakeGitHub,
    repository: FakeRepository,
    reviewed_head: str = SHA_B,
) -> tuple[int, dict[str, object]]:
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
    assert repository.revalidate_calls == 1
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


def test_publish_manual_check_reuses_head_recorded_before_validation_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

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
    assert repository.revalidate_calls == 1
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.last_operation == "reviewed"


def test_publish_manual_check_pushes_reviewed_descendant_of_prepared_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    prepared = store.load_work("curation-pr-42")
    assert prepared is not None and prepared.phase is WorkPhase.PREPARED
    reviewed = prepared.model_copy(
        update={
            "phase": WorkPhase.REVIEWED,
            "reviewed_head": SHA_C,
            "updated_at": prepared.updated_at + timedelta(seconds=1),
        }
    )
    store.save_work(reviewed, lease)
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

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
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
        "Original reviewed body.",
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
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert work is not None and work.phase is WorkPhase.PUSHED
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
    body = _private_text(state_dir, "body.md", "Owner proposal context")
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
        ),
        catalog_keys_provider=frozenset,
    )
    assert code == 0
    return run_id, str(payload["work_id"])


def test_publish_proposal_uses_only_private_state_files_and_finishes_work(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, work_id = _validated_proposal(capsys, state_dir, github, repository)
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

    assert code == 0
    assert github.pr_creates == 1
    assert github.comment_creates == 1
    work = StateStore(state_dir).load_work(work_id)
    assert work is not None and work.phase is WorkPhase.PUBLISHED
    assert work.pr_number == 71
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_publish_proposal_idempotent_retry_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, _work_id = _validated_proposal(capsys, state_dir, github, repository)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(state_dir, "body.md", "Owner proposal context")
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
    assert "secret source" not in json.dumps(payload)
    assert repository.create_only_calls == 0


def test_publish_state_ready_refetches_objective_facts_and_preserves_owner_body(
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
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert github.pull_requests[42].body == "Owner text"
    assert MaintainerState.READY.value in github.pull_requests[42].labels
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.reviewed_head == SHA_B
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


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
    summary = _private_text(state_dir, "summary.md", "Ready.")

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
    comments_before = github.comment_creates
    labels_before = github.label_writes

    code, payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert code == 0
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

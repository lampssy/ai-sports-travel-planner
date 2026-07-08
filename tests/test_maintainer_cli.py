from __future__ import annotations

import hashlib
import json
import stat
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from app.data.catalog_curation import CatalogCurationReport
from app.data.catalog_curation_reconciliation import (
    _derive_deltas,
    _load_snapshot,
)
from ops.maintainer.cli import main
from ops.maintainer.curation import ValidationExecutionError
from ops.maintainer.discovery import (
    CoverageCandidate,
    CoverageRegistry,
    DiscoveryCandidate,
    discovery_subregion,
    render_candidate_discovery_origin,
)
from ops.maintainer.git_ops import (
    GitAuthenticationError,
    GitOperationTimeoutError,
    GitPushRejectedError,
    GitRemotePolicyError,
    GitTransportError,
    GuardedSyncResult,
    RebaseConflictError,
    RepositorySafetyError,
    StaleRemoteHeadError,
)
from ops.maintainer.github import GitHubComment
from ops.maintainer.intent import (
    IntentDriftError,
    IntentSnapshot,
    IntentValidationError,
)
from ops.maintainer.models import MachineState, MaintainerState, PullRequest
from ops.maintainer.publication import (
    MaintainerSummary,
    parse_machine_state,
    render_summary,
)
from ops.maintainer.runtime import RunLease

pytestmark = pytest.mark.db_free


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def _pull_request(**changes: object) -> PullRequest:
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
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/2026-07-05-tignes.json",
            }
        ),
        "body": "Owner text",
    }
    values.update(changes)
    if "number" in changes and "url" not in changes:
        values["url"] = (
            "https://github.com/lampssy/ai-sports-travel-planner/pull/"
            f"{changes['number']}"
        )
    return PullRequest.model_validate(values)


def _prepared() -> GuardedSyncResult:
    return GuardedSyncResult(
        target_branch="codex/catalog-curation-tignes",
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


def _no_op_prepared() -> GuardedSyncResult:
    return GuardedSyncResult(
        target_branch="codex/catalog-curation-tignes",
        original_head=SHA_A,
        rebased_head=SHA_A,
        backup_ref=(
            f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{SHA_A[:12]}"
        ),
        prepared_ref=(
            f"refs/snowcast-maintainer/prepared/pr-42/{SHA_C[:12]}-{SHA_A[:12]}"
        ),
        base_head=SHA_C,
        merge_base=SHA_C,
    )


def _proposal_pr(
    number: int,
    candidate: DiscoveryCandidate,
) -> tuple[PullRequest, GitHubComment]:
    head_sha = f"{number:x}" * 40
    head_sha = head_sha[:40]
    pull_request = _pull_request(
        number=number,
        head_sha=head_sha,
        head_ref_name=f"codex/catalog-curation-proposal-{number}",
        labels=frozenset({"lane:catalog-discovery", "maintainer:proposal"}),
        body=render_candidate_discovery_origin(candidate),
    )
    machine = MachineState(
        head_sha=head_sha,
        lineage_id=f"catalog-discovery-{number}",
        candidate_key=candidate.key,
        candidate_origin_fingerprint=candidate.origin_fingerprint,
        candidate_fingerprint=candidate.fingerprint,
        regional_graph_key=candidate.regional_graph_key,
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.PROPOSAL,
        head_sha=head_sha,
        result="Proposal prepared.",
        ci_status="Owner decision pending.",
        owner_action="Review proposal.",
        machine_state=machine,
    )
    return pull_request, GitHubComment(
        comment_id=number,
        body=render_summary(summary),
        author_login="lampssy",
    )


def _write_validated_artifact(
    tmp_path: Path,
    *,
    prepared: GuardedSyncResult | None = None,
    selected_head: str = SHA_A,
    reviewed_head: str = SHA_B,
) -> None:
    guarded = prepared or _prepared()
    payload = {
        "schema_version": 1,
        "pr_number": 42,
        "selected_head": selected_head,
        "reviewed_head": reviewed_head,
        "report_path": "docs/catalog-curation/2026-07-05-tignes.json",
        "prepared": guarded.model_dump(mode="json"),
    }
    (tmp_path / "curation-pr-42-validated.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _lineage_state(
    *,
    head_sha: str = SHA_A,
    completed_cycles: int = 1,
    **changes: object,
) -> MachineState:
    values: dict[str, object] = {
        "head_sha": head_sha,
        "lineage_id": "catalog-curation-pr-42",
        "completed_cycles": completed_cycles,
        "last_publication": "none",
    }
    values.update(changes)
    return MachineState.model_validate(values)


def _test_fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _test_attempt_id(
    lineage_state: MachineState,
    *,
    pr_number: int = 42,
    selected_head: str = SHA_A,
) -> str:
    return _test_fingerprint(
        {
            "pr_number": pr_number,
            "selected_head": selected_head,
            "lineage_state": lineage_state.model_dump(mode="json"),
        }
    )


def _test_push_authorization_id(
    prepared: GuardedSyncResult,
    reviewed_head: str,
    *,
    pr_number: int = 42,
    selected_head: str = SHA_A,
) -> str:
    return _test_fingerprint(
        {
            "pr_number": pr_number,
            "selected_head": selected_head,
            "reviewed_head": reviewed_head,
            "prepared": prepared.model_dump(mode="json"),
        }
    )


def _write_prepared_artifact(
    tmp_path: Path,
    *,
    lineage_state: MachineState | None = None,
    prepared: GuardedSyncResult | None = None,
    selected_head: str = SHA_A,
) -> None:
    lineage = lineage_state or _lineage_state(head_sha=selected_head)
    guarded = prepared or _prepared()
    attempt_id = _test_attempt_id(lineage, selected_head=selected_head)
    attempt = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "pr_number": 42,
        "selected_head": selected_head,
        "lineage_state": lineage.model_dump(mode="json"),
    }
    (tmp_path / "curation-pr-42-attempt.json").write_text(
        json.dumps(attempt),
        encoding="utf-8",
    )
    payload = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "pr_number": 42,
        "selected_head": selected_head,
        "prepared": guarded.model_dump(mode="json"),
        "lineage_state": lineage.model_dump(mode="json"),
    }
    (tmp_path / "curation-pr-42-prepared.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _write_pushed_artifact(tmp_path: Path) -> None:
    authorization_id = _test_push_authorization_id(_prepared(), SHA_B)
    payload = {
        "schema_version": 1,
        "phase": "pushed",
        "authorization_id": authorization_id,
        "pr_number": 42,
        "selected_head": SHA_A,
        "reviewed_head": SHA_B,
        "prepared": _prepared().model_dump(mode="json"),
    }
    (tmp_path / f"curation-pr-42-push-{authorization_id}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _publication_payload(
    summary: MaintainerSummary,
    managed_body: str,
) -> dict[str, object]:
    return {
        "summary": {
            "state": summary.state.value,
            "result": summary.result,
            "ci_status": summary.ci_status,
            "owner_action": summary.owner_action,
            "caveats": list(summary.caveats),
        },
        "managed_body": managed_body,
    }


def _proposal_report(
    tmp_path: Path,
    base_catalog: dict[str, object],
    current_catalog: dict[str, object],
    base_trust: dict[str, object],
    current_trust: dict[str, object],
    candidate: DiscoveryCandidate,
) -> CatalogCurationReport:
    paths: dict[str, Path] = {}
    for name, payload in {
        "base-catalog": base_catalog,
        "current-catalog": current_catalog,
        "base-trust": base_trust,
        "current-trust": current_trust,
    }.items():
        path = tmp_path / f"fixture-{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path
    base = _load_snapshot(
        catalog_path=paths["base-catalog"],
        trust_manifest_path=paths["base-trust"],
        label="base",
    )
    current = _load_snapshot(
        catalog_path=paths["current-catalog"],
        trust_manifest_path=paths["current-trust"],
        label="current",
    )
    deltas = _derive_deltas(base, current)
    fields_by_target: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for delta in deltas:
        fields_by_target[(delta.target_type, delta.target_id)].append(delta.field_path)
    candidate_id = candidate.key.split(":", 1)[1]
    identity_field = f"{candidate.candidate_kind}_id"
    return CatalogCurationReport.model_validate(
        {
            "report_schema_version": 2,
            "title": "Test proposal",
            "summary": "Adds one fully reconciled discovery candidate.",
            "reviewed_targets": [
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "scope": "narrow",
                    "required_field_paths": fields,
                }
                for (target_type, target_id), fields in fields_by_target.items()
            ],
            "changes": [
                {
                    "target_type": delta.target_type,
                    "target_id": delta.target_id,
                    "field_path": delta.field_path,
                    "before": delta.before,
                    "after": delta.after,
                    "trust_status": "estimated",
                    "ranking_relevant": False,
                }
                for delta in deltas
            ],
            "field_coverage": [
                {
                    "target_type": delta.target_type,
                    "target_id": delta.target_id,
                    "field_path": delta.field_path,
                    "status": "changed",
                }
                for delta in deltas
            ],
            "evidence": [
                {
                    "evidence_id": "candidate-scope",
                    "target_type": candidate.candidate_kind,
                    "target_id": candidate_id,
                    "field_path": identity_field,
                    "source_type": "official",
                    "source_url": candidate.official_urls[0],
                    "source_title": "Official identity",
                    "source_value": candidate_id,
                    "evidence_summary": "Identifies the proposed catalog entity.",
                }
            ],
            "entity_scope_assessments": [
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate.display_name,
                    "candidate_kind": candidate.candidate_kind,
                    "disposition": "add_entity",
                    "signals": ["official_product_identity"],
                    "evidence_refs": ["candidate-scope"],
                    "target_refs": [
                        {
                            "target_type": candidate.candidate_kind,
                            "target_id": candidate_id,
                        }
                    ],
                    "rationale": "The official source identifies the product.",
                }
            ],
        }
    )


@dataclass
class FakeGitHub:
    pull_requests: list[PullRequest] = field(default_factory=list)
    closed_pull_requests: list[PullRequest] = field(default_factory=list)
    comments: dict[int, list[GitHubComment]] = field(default_factory=dict)
    labels_ensured: bool = False
    published: list[str] = field(default_factory=list)

    def list_open_pull_requests(self) -> list[PullRequest]:
        return list(self.pull_requests)

    def get_pull_request(self, number: int) -> PullRequest:
        return next(item for item in self.pull_requests if item.number == number)

    def list_issue_comments(self, number: int) -> list[GitHubComment]:
        return list(self.comments.get(number, ()))

    def list_closed_proposal_pull_requests(self) -> list[PullRequest]:
        return list(self.closed_pull_requests)

    def ensure_labels(self, definitions: object) -> None:
        assert definitions
        self.labels_ensured = True

    def update_pull_request_body(self, number: int, body: str) -> None:
        self.published.append(f"body:{number}:{body}")

    def create_comment(self, number: int, body: str) -> int:
        self.published.append(f"comment:{number}:{body}")
        return 101

    def update_comment(self, comment_id: int, body: str) -> None:
        self.published.append(f"update:{comment_id}:{body}")

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None:
        self.published.append(
            f"labels:{number}:{','.join(sorted(add))}:{','.join(sorted(remove))}"
        )


@dataclass
class FakeRepository:
    root: Path
    head: str = SHA_B
    prepared: GuardedSyncResult = field(default_factory=_prepared)
    prepare_calls: list[int] = field(default_factory=list)
    push_calls: list[tuple[GuardedSyncResult, str]] = field(default_factory=list)
    objects: dict[tuple[str, str], str] = field(default_factory=dict)
    intent: IntentSnapshot | None = None
    remote_head_value: str = SHA_A
    remote_calls: list[str] = field(default_factory=list)

    def prepare_guarded_sync(self, pull_request: PullRequest) -> GuardedSyncResult:
        self.prepare_calls.append(pull_request.number)
        return self.prepared

    def current_head(self) -> str:
        return self.head

    def push_with_lease(
        self,
        prepared: GuardedSyncResult,
        reviewed_head: str,
    ) -> None:
        self.push_calls.append((prepared, reviewed_head))
        self.remote_head_value = reviewed_head

    def remote_head(self, branch: str) -> str:
        self.remote_calls.append(branch)
        return self.remote_head_value

    def show_text(self, revision: str, path: str) -> str:
        return self.objects[(revision, path)]

    def verify_immutable_diff(self, base: str, head: str) -> IntentSnapshot:
        assert base == SHA_A
        assert head == SHA_B
        if self.intent is None:
            raise AssertionError("test repository has no immutable intent")
        return self.intent


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    output = capsys.readouterr()
    assert output.err == ""
    lines = output.out.splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert isinstance(payload, dict)
    return payload


def test_artifact_write_fsyncs_file_and_containing_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import ops.maintainer.cli as maintainer_cli

    lease = RunLease.acquire(tmp_path, "curation")
    synced_modes: list[int] = []
    real_fsync = maintainer_cli.os.fsync

    def record_fsync(descriptor: int) -> None:
        synced_modes.append(maintainer_cli.os.fstat(descriptor).st_mode)
        real_fsync(descriptor)

    monkeypatch.setattr(maintainer_cli.os, "fsync", record_fsync)

    maintainer_cli._write_json(
        tmp_path / "artifact.json",
        _lineage_state(),
        lease,
    )

    assert any(stat.S_ISREG(mode) for mode in synced_modes)
    assert any(stat.S_ISDIR(mode) for mode in synced_modes)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RebaseConflictError("secret conflict"), "rebase-conflict"),
        (StaleRemoteHeadError("secret stale head"), "stale-head"),
        (IntentDriftError("secret drift"), "intent-drift"),
        (IntentValidationError("secret invalid intent"), "intent-validation"),
        (ValidationExecutionError("secret validation"), "validation-failed"),
        (GitAuthenticationError("secret auth"), "git-auth"),
        (GitTransportError("secret transport"), "git-transport"),
        (GitOperationTimeoutError("secret timeout"), "git-timeout"),
        (GitPushRejectedError("secret rejection"), "push-rejected"),
        (GitRemotePolicyError("secret remote policy"), "remote-policy"),
        (RepositorySafetyError("secret repository issue"), "repository-safety"),
    ],
)
def test_expected_typed_stops_have_stable_sanitized_reason_codes(
    error: Exception,
    expected: str,
) -> None:
    import ops.maintainer.cli as maintainer_cli

    reason = maintainer_cli._reason(error)

    assert reason == expected
    assert "secret" not in reason


def test_lock_acquire_returns_machine_readable_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--state-dir", str(tmp_path), "lock", "acquire", "curation"]) == 0

    payload = _json_output(capsys)
    assert payload["status"] == "acquired"
    assert isinstance(payload["token"], str)
    assert payload["token"]


@pytest.mark.parametrize(
    ("command", "arguments"),
    [
        ("next", ["--output", "candidate.json"]),
        (
            "add-source",
            [
                "--candidate-file",
                "candidate.json",
                "--official-url",
                "https://example.com/official",
            ],
        ),
        (
            "nominate",
            [
                "--output",
                "candidate.json",
                "--candidate-key",
                "ski_area:alpha",
                "--display-name",
                "Alpha",
                "--country",
                "Austria",
                "--alpine-subregion",
                "Austrian Alps",
                "--regional-graph-key",
                "alpha",
                "--official-url",
                "https://example.com/official",
            ],
        ),
    ],
)
def test_mutable_discovery_artifact_commands_require_lock_token(
    command: str,
    arguments: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "discovery",
            command,
            *arguments,
        ]
    )

    assert result != 0
    assert _json_output(capsys) == {
        "status": "error",
        "reason": "invalid-command-input",
    }


def test_wrong_lock_token_is_a_safe_json_stop(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            "wrong",
        ]
    )

    assert result != 0
    assert _json_output(capsys) == {
        "status": "error",
        "reason": "lease-ownership-error",
    }


def test_cli_never_emits_secret_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "do-not-print-this-token"
    monkeypatch.setenv("GH_TOKEN", secret)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            secret,
        ]
    )

    assert result != 0
    assert secret not in json.dumps(_json_output(capsys))


def test_label_provisioning_requires_and_preserves_active_lease(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    github = FakeGitHub()

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "github",
                "ensure-labels",
                "--lock-token",
                lease.token,
            ],
            github=github,
        )
        == 0
    )

    assert _json_output(capsys) == {"status": "labels-synchronized"}
    assert github.labels_ensured
    lease.assert_owner(lease.token)


def test_curation_inventory_selects_one_deep_pr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    oldest = _pull_request(number=2, created_at=datetime(2026, 7, 1, tzinfo=UTC))
    newest = _pull_request(number=3, created_at=datetime(2026, 7, 2, tzinfo=UTC))
    github = FakeGitHub(pull_requests=[newest, oldest])

    assert (
        main(
            ["--state-dir", str(tmp_path), "curation", "inventory"],
            github=github,
        )
        == 0
    )

    payload = _json_output(capsys)
    assert payload["status"] == "inventory"
    assert payload["waiting_ci"] == []
    assert payload["deep_pr"] == {
        "number": 2,
        "head_sha": SHA_A,
        "lane": "lane:catalog-curation",
    }


def test_prepare_persists_typed_guarded_sync_under_the_lease(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    github = FakeGitHub(pull_requests=[_pull_request()])
    repository = FakeRepository(tmp_path)

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "prepare",
                "--pr",
                "42",
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
        )
        == 0
    )

    payload = _json_output(capsys)
    assert payload["status"] == "prepared"
    assert payload["original_head"] == SHA_A
    assert payload["rebased_head"] == SHA_B
    artifact = tmp_path / "curation-pr-42-prepared.json"
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    attempt = json.loads(
        (tmp_path / "curation-pr-42-attempt.json").read_text(encoding="utf-8")
    )
    assert persisted["prepared"] == _prepared().model_dump(mode="json")
    assert persisted["pr_number"] == 42
    assert persisted["lineage_state"] == _lineage_state().model_dump(mode="json")
    assert persisted["attempt_id"] == attempt["attempt_id"]
    assert attempt["selected_head"] == SHA_A
    assert attempt["lineage_state"] == _lineage_state().model_dump(mode="json")
    assert repository.prepare_calls == [42]


def test_prepare_requires_requested_pr_to_be_current_oldest_deep_selection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    requested = _pull_request(number=42)
    oldest = _pull_request(
        number=2,
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    repository = FakeRepository(tmp_path)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=[requested, oldest]),
        repository=repository,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.prepare_calls == []


def test_prepare_rejects_selection_to_refetch_race(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    selected = _pull_request()
    moved = selected.model_copy(update={"head_sha": SHA_B})
    repository = FakeRepository(tmp_path)

    class RacingGitHub(FakeGitHub):
        def get_pull_request(self, number: int) -> PullRequest:
            assert number == 42
            return moved

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=RacingGitHub(pull_requests=[selected]),
        repository=repository,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.prepare_calls == []


def test_prepare_stops_when_persisted_lineage_reached_three_cycles(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    pull_request = _pull_request(labels=frozenset({"maintainer:working"}))
    machine = MachineState(
        head_sha=SHA_A,
        lineage_id="curation-42",
        completed_cycles=3,
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.WORKING,
        head_sha=SHA_A,
        result="Prior remediation cycles completed.",
        ci_status="Not running.",
        owner_action="Manual review required.",
        machine_state=machine,
    )
    github = FakeGitHub(
        pull_requests=[pull_request],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=render_summary(summary),
                    author_login="lampssy",
                )
            ]
        },
    )
    repository = FakeRepository(tmp_path)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=repository,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.prepare_calls == []


def test_prepare_preserves_discovery_lineage_and_advances_to_third_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    pull_request = _pull_request(
        labels=frozenset({"lane:catalog-discovery"}),
    )
    machine = MachineState(
        head_sha=SHA_A,
        lineage_id="catalog-discovery-42",
        completed_cycles=2,
        candidate_key="ski_area:alpha",
        candidate_origin_fingerprint="e" * 64,
        candidate_fingerprint="f" * 64,
        regional_graph_key="alpha-region",
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.PROPOSAL,
        head_sha=SHA_A,
        result="Discovery proposal approved.",
        ci_status="Owner gate removed.",
        owner_action="Run curation review.",
        machine_state=machine,
    )
    github = FakeGitHub(
        pull_requests=[pull_request],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=render_summary(summary),
                    author_login="lampssy",
                )
            ]
        },
    )

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "prepare",
                "--pr",
                "42",
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=FakeRepository(tmp_path),
        )
        == 0
    )
    _json_output(capsys)
    persisted = json.loads(
        (tmp_path / "curation-pr-42-prepared.json").read_text(encoding="utf-8")
    )
    lineage = persisted["lineage_state"]
    assert lineage["lineage_id"] == "catalog-discovery-42"
    assert lineage["completed_cycles"] == 3
    assert lineage["candidate_key"] == "ski_area:alpha"
    assert lineage["candidate_origin_fingerprint"] == "e" * 64
    assert lineage["candidate_fingerprint"] == "f" * 64
    assert lineage["regional_graph_key"] == "alpha-region"


def test_prepare_rejects_incomplete_candidate_lineage_before_git_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    pull_request = _pull_request(labels=frozenset({"lane:catalog-discovery"}))
    machine = MachineState(
        head_sha=SHA_A,
        lineage_id="catalog-discovery-42",
        completed_cycles=1,
        candidate_key="ski_area:alpha",
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.PROPOSAL,
        head_sha=SHA_A,
        result="Discovery proposal has incomplete provenance.",
        ci_status="Owner gate removed.",
        owner_action="Stop before mutation.",
        machine_state=machine,
    )
    github = FakeGitHub(
        pull_requests=[pull_request],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=render_summary(summary),
                    author_login="lampssy",
                )
            ]
        },
    )
    repository = FakeRepository(tmp_path)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=repository,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.prepare_calls == []


def test_prepare_rejects_approved_proposal_without_trusted_discovery_lineage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    pull_request = _pull_request(labels=frozenset({"lane:catalog-discovery"}))
    repository = FakeRepository(tmp_path)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=[pull_request]),
        repository=repository,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.prepare_calls == []


def test_prepare_attempt_write_failure_stops_before_git_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import ops.maintainer.cli as maintainer_cli

    lease = RunLease.acquire(tmp_path, "curation")
    repository = FakeRepository(tmp_path)

    def fail_attempt_write(path: Path, payload: object, owned: RunLease) -> None:
        raise OSError("simulated attempt write failure")

    monkeypatch.setattr(maintainer_cli, "_write_json", fail_attempt_write)
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=[_pull_request()]),
        repository=repository,
    )

    assert result != 0
    _json_output(capsys)
    assert repository.prepare_calls == []
    assert not (tmp_path / "curation-pr-42-attempt.json").exists()


@pytest.mark.parametrize(
    "failure",
    [
        RepositorySafetyError("sensitive rebase conflict"),
        IntentDriftError("sensitive prepared intent drift"),
    ],
    ids=("repository-conflict", "intent-drift"),
)
def test_prepare_failure_preserves_discovery_seed_for_safe_stop_publication(
    failure: Exception,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingPrepareRepository(FakeRepository):
        def prepare_guarded_sync(
            self,
            pull_request: PullRequest,
        ) -> GuardedSyncResult:
            self.prepare_calls.append(pull_request.number)
            raise failure

    lease = RunLease.acquire(tmp_path, "curation")
    pull_request = _pull_request(labels=frozenset({"lane:catalog-discovery"}))
    prior_machine = MachineState(
        head_sha=SHA_A,
        lineage_id="catalog-discovery-42",
        completed_cycles=1,
        candidate_key="ski_area:alpha",
        candidate_origin_fingerprint="e" * 64,
        candidate_fingerprint="f" * 64,
        regional_graph_key="alpha-region",
        last_publication="complete",
    )
    prior_summary = MaintainerSummary(
        state=MaintainerState.PROPOSAL,
        head_sha=SHA_A,
        result="Discovery proposal approved.",
        ci_status="Owner gate removed.",
        owner_action="Run curation review.",
        machine_state=prior_machine,
    )
    github = FakeGitHub(
        pull_requests=[pull_request],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=render_summary(prior_summary),
                    author_login="lampssy",
                )
            ]
        },
    )
    repository = FailingPrepareRepository(tmp_path)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "prepare",
            "--pr",
            "42",
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=repository,
    )
    assert result != 0
    rendered_error = json.dumps(_json_output(capsys))
    assert "sensitive" not in rendered_error
    assert repository.prepare_calls == [42]
    attempt_path = tmp_path / "curation-pr-42-attempt.json"
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert attempt["pr_number"] == 42
    assert attempt["selected_head"] == SHA_A
    assert len(attempt["attempt_id"]) == 64
    assert attempt["lineage_state"]["lineage_id"] == "catalog-discovery-42"
    assert attempt["lineage_state"]["completed_cycles"] == 2
    assert attempt["lineage_state"]["candidate_key"] == "ski_area:alpha"
    assert not (tmp_path / "curation-pr-42-prepared.json").exists()

    safe_stop = MaintainerSummary(
        state=MaintainerState.OWNER_DECISION,
        head_sha=SHA_A,
        result="Guarded preparation stopped safely.",
        ci_status="Validation was not started.",
        owner_action="Resolve the preparation conflict.",
        machine_state=prior_machine,
    )
    summary_path = tmp_path / "prepare-failure-summary.json"
    summary_path.write_text(
        json.dumps(_publication_payload(safe_stop, "Preparation stopped.")),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                "maintainer:owner-decision",
                "--summary-file",
                str(summary_path),
                "--lock-token",
                lease.token,
            ],
            github=github,
        )
        == 0
    )
    assert _json_output(capsys)["state"] == "maintainer:owner-decision"
    published_comment = next(
        item.split(":", 2)[2] for item in github.published if item.startswith("update:")
    )
    published_machine = parse_machine_state(published_comment)
    assert published_machine is not None
    assert published_machine.lineage_id == "catalog-discovery-42"
    assert published_machine.completed_cycles == 2
    assert published_machine.candidate_key == "ski_area:alpha"
    assert published_machine.candidate_origin_fingerprint == "e" * 64
    assert published_machine.candidate_fingerprint == "f" * 64
    assert published_machine.regional_graph_key == "alpha-region"


def test_failed_prepare_seed_cannot_authorize_non_safe_or_stale_publication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingPrepareRepository(FakeRepository):
        def prepare_guarded_sync(
            self,
            pull_request: PullRequest,
        ) -> GuardedSyncResult:
            self.prepare_calls.append(pull_request.number)
            raise RepositorySafetyError("conflict")

    lease = RunLease.acquire(tmp_path, "curation")
    github = FakeGitHub(pull_requests=[_pull_request()])
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "prepare",
                "--pr",
                "42",
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=FailingPrepareRepository(tmp_path),
        )
        != 0
    )
    _json_output(capsys)

    for state in (
        MaintainerState.WORKING,
        MaintainerState.WAITING_CI,
        MaintainerState.READY,
    ):
        summary = MaintainerSummary(
            state=state,
            head_sha=SHA_A,
            result="Caller requests an invalid transition.",
            ci_status="Not validated.",
            owner_action="Stop.",
            machine_state=MachineState(
                head_sha=SHA_A,
                lineage_id="caller-state",
                last_publication="complete",
            ),
        )
        summary_path = tmp_path / f"invalid-{state.value.split(':', 1)[1]}.json"
        summary_path.write_text(
            json.dumps(_publication_payload(summary, "Managed body.")),
            encoding="utf-8",
        )
        result = main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                state.value,
                "--summary-file",
                str(summary_path),
                "--lock-token",
                lease.token,
            ],
            github=github,
        )
        assert result != 0
        assert _json_output(capsys)["reason"] == "invalid-command-input"

    safe_summary = MaintainerSummary(
        state=MaintainerState.BLOCKED,
        head_sha=SHA_A,
        result="Preparation is blocked.",
        ci_status="Not validated.",
        owner_action="Inspect the conflict.",
        machine_state=MachineState(
            head_sha=SHA_A,
            lineage_id="caller-state",
            last_publication="complete",
        ),
    )
    safe_path = tmp_path / "blocked.json"
    safe_path.write_text(
        json.dumps(_publication_payload(safe_summary, "Managed body.")),
        encoding="utf-8",
    )
    github.pull_requests = [_pull_request(head_sha=SHA_B)]
    stale_head = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "publish",
            "--pr",
            "42",
            "--state",
            MaintainerState.BLOCKED.value,
            "--summary-file",
            str(safe_path),
            "--lock-token",
            lease.token,
        ],
        github=github,
    )
    assert stale_head != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"

    copied_attempt = tmp_path / "curation-pr-43-attempt.json"
    copied_attempt.write_text(
        (tmp_path / "curation-pr-42-attempt.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    github.pull_requests = [_pull_request(number=43)]
    wrong_pr = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "publish",
            "--pr",
            "43",
            "--state",
            MaintainerState.BLOCKED.value,
            "--summary-file",
            str(safe_path),
            "--lock-token",
            lease.token,
        ],
        github=github,
    )
    assert wrong_pr != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert github.published == []


def test_failed_retry_invalidates_prior_promoted_evidence_for_same_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingPrepareRepository(FakeRepository):
        def prepare_guarded_sync(
            self,
            pull_request: PullRequest,
        ) -> GuardedSyncResult:
            self.prepare_calls.append(pull_request.number)
            raise RepositorySafetyError("retry conflict")

    lease = RunLease.acquire(tmp_path, "curation")
    _write_prepared_artifact(tmp_path)
    old_attempt = json.loads(
        (tmp_path / "curation-pr-42-attempt.json").read_text(encoding="utf-8")
    )
    _write_validated_artifact(tmp_path)
    _write_pushed_artifact(tmp_path)
    github = FakeGitHub(pull_requests=[_pull_request()])

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "prepare",
                "--pr",
                "42",
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=FailingPrepareRepository(tmp_path),
        )
        != 0
    )
    _json_output(capsys)
    new_attempt = json.loads(
        (tmp_path / "curation-pr-42-attempt.json").read_text(encoding="utf-8")
    )
    assert new_attempt["attempt_id"] != old_attempt["attempt_id"]

    for state, head_sha in (
        (MaintainerState.WORKING, SHA_A),
        (MaintainerState.WAITING_CI, SHA_B),
    ):
        github.pull_requests = [_pull_request(head_sha=head_sha)]
        summary = MaintainerSummary(
            state=state,
            head_sha=head_sha,
            result="Stale evidence must not authorize publication.",
            ci_status="Not validated in this attempt.",
            owner_action="Stop.",
            machine_state=MachineState(
                head_sha=head_sha,
                lineage_id="caller-state",
                last_publication="complete",
            ),
        )
        summary_path = tmp_path / f"stale-{state.value.split(':', 1)[1]}.json"
        summary_path.write_text(
            json.dumps(_publication_payload(summary, "Managed body.")),
            encoding="utf-8",
        )
        result = main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                state.value,
                "--summary-file",
                str(summary_path),
                "--lock-token",
                lease.token,
            ],
            github=github,
        )
        assert result != 0
        assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert github.published == []


def test_validate_then_push_reuses_the_exact_reviewed_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    github = FakeGitHub(pull_requests=[_pull_request()])
    repository = FakeRepository(tmp_path, head=SHA_B)
    calls: list[tuple[int, str, Path]] = []

    def validation_executor(
        pr: PullRequest,
        prepared: GuardedSyncResult,
        reviewed_head: str,
        reviewed_repository: Any,
        base_repository: Any,
    ) -> object:
        assert prepared == _prepared()
        assert reviewed_head == SHA_B
        assert reviewed_repository is repository
        calls.append((pr.number, reviewed_head, base_repository.root))
        return type("Result", (), {"commands_completed": 4})()

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "prepare",
                "--pr",
                "42",
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
        )
        == 0
    )
    _json_output(capsys)

    base_dir = tmp_path / "base"
    base_dir.mkdir()
    base_repository = FakeRepository(base_dir, head=SHA_D)
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "validate",
                "--pr",
                "42",
                "--report",
                "docs/catalog-curation/2026-07-05-tignes.json",
                "--base-dir",
                str(base_dir),
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
            base_repository=base_repository,
            validation_executor=validation_executor,
        )
        == 0
    )
    assert _json_output(capsys) == {
        "commands_completed": 4,
        "reviewed_head": SHA_B,
        "status": "validated",
    }
    assert calls == [(42, SHA_B, base_dir)]

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "push",
                "--pr",
                "42",
                "--original-head",
                SHA_A,
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
        )
        == 0
    )
    assert _json_output(capsys) == {
        "head_sha": SHA_B,
        "status": "pushed",
    }
    assert repository.push_calls == [(_prepared(), SHA_B)]
    authorization_id = _test_push_authorization_id(_prepared(), SHA_B)
    pushed_path = tmp_path / f"curation-pr-42-push-{authorization_id}.json"
    pushed = json.loads(pushed_path.read_text(encoding="utf-8"))
    assert pushed["reviewed_head"] == SHA_B
    assert pushed["phase"] == "pushed"
    assert repository.remote_calls == ["codex/catalog-curation-tignes"]

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "push",
                "--pr",
                "42",
                "--original-head",
                SHA_A,
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
        )
        != 0
    )
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.push_calls == [(_prepared(), SHA_B)]
    assert repository.remote_calls == ["codex/catalog-curation-tignes"]


def test_push_crash_after_remote_update_cannot_repeat_network_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import ops.maintainer.cli as maintainer_cli

    lease = RunLease.acquire(tmp_path, "curation")
    _write_prepared_artifact(tmp_path)
    _write_validated_artifact(tmp_path)
    pull_request = _pull_request()
    github = FakeGitHub(pull_requests=[pull_request])
    repository = FakeRepository(tmp_path)
    real_write = maintainer_cli._write_json
    writes = 0

    def fail_after_push(path: Path, payload: object, owned: RunLease) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("simulated crash")
        real_write(path, payload, owned)

    monkeypatch.setattr(maintainer_cli, "_write_json", fail_after_push)
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "push",
            "--pr",
            "42",
            "--original-head",
            SHA_A,
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=repository,
    )
    assert result != 0
    _json_output(capsys)
    assert repository.push_calls == [(_prepared(), SHA_B)]
    authorization_id = _test_push_authorization_id(_prepared(), SHA_B)
    journal = tmp_path / f"curation-pr-42-push-{authorization_id}.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "authorized"

    monkeypatch.setattr(maintainer_cli, "_write_json", real_write)
    github.pull_requests = [pull_request.model_copy(update={"head_sha": SHA_B})]
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "push",
            "--pr",
            "42",
            "--original-head",
            SHA_A,
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=repository,
    )
    assert result == 0
    assert _json_output(capsys)["status"] == "pushed"
    assert repository.push_calls == [(_prepared(), SHA_B)]
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "pushed"

    machine = MachineState(
        head_sha=SHA_B,
        lineage_id="caller-cannot-control",
        completed_cycles=0,
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.WAITING_CI,
        head_sha=SHA_B,
        result="Recovered pushed evidence.",
        ci_status="Checks pending.",
        owner_action="Wait.",
        machine_state=machine,
    )
    summary_path = tmp_path / "recovered-summary.json"
    summary_path.write_text(
        json.dumps(_publication_payload(summary, "Managed body.")),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                "maintainer:waiting-ci",
                "--summary-file",
                str(summary_path),
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
        )
        == 0
    )
    assert _json_output(capsys)["state"] == "maintainer:waiting-ci"


def test_push_authorization_write_failure_stops_before_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import ops.maintainer.cli as maintainer_cli

    lease = RunLease.acquire(tmp_path, "curation")
    _write_prepared_artifact(tmp_path)
    _write_validated_artifact(tmp_path)
    repository = FakeRepository(tmp_path)

    def fail_write(path: Path, payload: object, owned: RunLease) -> None:
        raise OSError("simulated journal failure")

    monkeypatch.setattr(maintainer_cli, "_write_json", fail_write)
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "push",
            "--pr",
            "42",
            "--original-head",
            SHA_A,
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=[_pull_request()]),
        repository=repository,
    )

    assert result != 0
    _json_output(capsys)
    assert repository.remote_calls == []
    assert repository.push_calls == []
    assert list(tmp_path.glob("curation-pr-42-push-*.json")) == []


def test_no_op_push_records_exact_authorization_without_network_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    guarded = _no_op_prepared()
    _write_prepared_artifact(tmp_path, prepared=guarded)
    _write_validated_artifact(
        tmp_path,
        prepared=guarded,
        reviewed_head=SHA_A,
    )
    repository = FakeRepository(
        tmp_path,
        head=SHA_A,
        prepared=guarded,
        remote_head_value=SHA_A,
    )
    github = FakeGitHub(pull_requests=[_pull_request()])
    command = [
        "--state-dir",
        str(tmp_path),
        "curation",
        "push",
        "--pr",
        "42",
        "--original-head",
        SHA_A,
        "--lock-token",
        lease.token,
    ]

    assert main(command, github=github, repository=repository) == 0
    assert _json_output(capsys) == {"head_sha": SHA_A, "status": "pushed"}
    assert repository.push_calls == []
    assert repository.remote_calls == ["codex/catalog-curation-tignes"]
    journals = list(tmp_path.glob("curation-pr-42-push-*.json"))
    assert len(journals) == 1
    assert json.loads(journals[0].read_text(encoding="utf-8"))["phase"] == "pushed"

    assert main(command, github=github, repository=repository) != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.push_calls == []
    assert repository.remote_calls == ["codex/catalog-curation-tignes"]


def test_no_op_push_recovers_promotion_crash_without_network_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import ops.maintainer.cli as maintainer_cli

    lease = RunLease.acquire(tmp_path, "curation")
    guarded = _no_op_prepared()
    _write_prepared_artifact(tmp_path, prepared=guarded)
    _write_validated_artifact(
        tmp_path,
        prepared=guarded,
        reviewed_head=SHA_A,
    )
    repository = FakeRepository(
        tmp_path,
        head=SHA_A,
        prepared=guarded,
        remote_head_value=SHA_A,
    )
    github = FakeGitHub(pull_requests=[_pull_request()])
    real_write = maintainer_cli._write_json
    writes = 0

    def fail_promotion(path: Path, payload: object, owned: RunLease) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("simulated no-op promotion crash")
        real_write(path, payload, owned)

    monkeypatch.setattr(maintainer_cli, "_write_json", fail_promotion)
    command = [
        "--state-dir",
        str(tmp_path),
        "curation",
        "push",
        "--pr",
        "42",
        "--original-head",
        SHA_A,
        "--lock-token",
        lease.token,
    ]
    assert main(command, github=github, repository=repository) != 0
    _json_output(capsys)
    journal = next(tmp_path.glob("curation-pr-42-push-*.json"))
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "authorized"
    assert repository.push_calls == []

    monkeypatch.setattr(maintainer_cli, "_write_json", real_write)
    assert main(command, github=github, repository=repository) == 0
    assert _json_output(capsys)["status"] == "pushed"
    assert repository.push_calls == []
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "pushed"


def test_no_op_push_evidence_supports_waiting_and_ready_publication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    guarded = _no_op_prepared()
    _write_prepared_artifact(tmp_path, prepared=guarded)
    _write_validated_artifact(
        tmp_path,
        prepared=guarded,
        reviewed_head=SHA_A,
    )
    repository = FakeRepository(
        tmp_path,
        head=SHA_A,
        prepared=guarded,
        remote_head_value=SHA_A,
    )
    pull_request = _pull_request()
    github = FakeGitHub(pull_requests=[pull_request])
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "push",
                "--pr",
                "42",
                "--original-head",
                SHA_A,
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=repository,
        )
        == 0
    )
    _json_output(capsys)
    waiting_summary = MaintainerSummary(
        state=MaintainerState.WAITING_CI,
        head_sha=SHA_A,
        result="No branch rewrite was necessary.",
        ci_status="Checks are reconciling.",
        owner_action="Wait for checks.",
        machine_state=MachineState(
            head_sha=SHA_A,
            lineage_id="caller-cannot-control",
            last_publication="complete",
        ),
    )
    waiting_path = tmp_path / "no-op-waiting.json"
    waiting_path.write_text(
        json.dumps(_publication_payload(waiting_summary, "No rewrite required.")),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                MaintainerState.WAITING_CI.value,
                "--summary-file",
                str(waiting_path),
                "--lock-token",
                lease.token,
            ],
            github=github,
        )
        == 0
    )
    _json_output(capsys)
    rendered_waiting = next(
        item.split(":", 2)[2]
        for item in github.published
        if item.startswith("comment:")
    )
    waiting_machine = parse_machine_state(rendered_waiting)
    assert waiting_machine is not None
    assert waiting_machine.head_sha == SHA_A
    assert waiting_machine.completed_cycles == 1

    waiting_pr = pull_request.model_copy(
        update={"labels": frozenset({"lane:catalog-curation", "maintainer:waiting-ci"})}
    )
    ready_github = FakeGitHub(
        pull_requests=[waiting_pr],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=rendered_waiting,
                    author_login="lampssy",
                )
            ]
        },
    )
    ready_summary = waiting_summary.model_copy(
        update={
            "state": MaintainerState.READY,
            "ci_status": "Checks passed.",
            "owner_action": "Review and merge.",
        }
    )
    ready_path = tmp_path / "no-op-ready.json"
    ready_path.write_text(
        json.dumps(_publication_payload(ready_summary, "No rewrite required.")),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                MaintainerState.READY.value,
                "--summary-file",
                str(ready_path),
                "--lock-token",
                lease.token,
            ],
            github=ready_github,
        )
        == 0
    )
    assert _json_output(capsys)["state"] == MaintainerState.READY.value


def test_distinct_reviewed_authorization_with_same_selected_head_is_allowed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    no_op = _no_op_prepared()
    _write_prepared_artifact(tmp_path, prepared=no_op)
    _write_validated_artifact(
        tmp_path,
        prepared=no_op,
        reviewed_head=SHA_A,
    )
    repository = FakeRepository(
        tmp_path,
        head=SHA_A,
        prepared=no_op,
        remote_head_value=SHA_A,
    )
    github = FakeGitHub(pull_requests=[_pull_request()])
    command = [
        "--state-dir",
        str(tmp_path),
        "curation",
        "push",
        "--pr",
        "42",
        "--original-head",
        SHA_A,
        "--lock-token",
        lease.token,
    ]
    assert main(command, github=github, repository=repository) == 0
    _json_output(capsys)

    _write_prepared_artifact(tmp_path)
    _write_validated_artifact(tmp_path)
    repository.head = SHA_B
    repository.prepared = _prepared()
    assert main(command, github=github, repository=repository) == 0
    assert _json_output(capsys)["head_sha"] == SHA_B
    assert repository.push_calls == [(_prepared(), SHA_B)]
    assert len(list(tmp_path.glob("curation-pr-42-push-*.json"))) == 2


def test_distinct_prepared_authorization_with_same_selected_head_is_allowed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    _write_prepared_artifact(tmp_path)
    _write_validated_artifact(tmp_path)
    repository = FakeRepository(tmp_path)
    github = FakeGitHub(pull_requests=[_pull_request()])
    command = [
        "--state-dir",
        str(tmp_path),
        "curation",
        "push",
        "--pr",
        "42",
        "--original-head",
        SHA_A,
        "--lock-token",
        lease.token,
    ]
    assert main(command, github=github, repository=repository) == 0
    _json_output(capsys)

    distinct = _prepared().model_copy(
        update={
            "prepared_ref": (
                f"refs/snowcast-maintainer/prepared/pr-42/{SHA_C[:12]}-{SHA_B[:12]}"
            )
        }
    )
    _write_prepared_artifact(tmp_path, prepared=distinct)
    _write_validated_artifact(tmp_path, prepared=distinct)
    github.pull_requests = [_pull_request(head_sha=SHA_B)]
    assert main(command, github=github, repository=repository) == 0
    assert _json_output(capsys)["status"] == "pushed"
    assert repository.push_calls == [(_prepared(), SHA_B)]
    journals = list(tmp_path.glob("curation-pr-42-push-*.json"))
    assert len(journals) == 2
    assert all(
        json.loads(path.read_text(encoding="utf-8"))["phase"] == "pushed"
        for path in journals
    )


def test_failed_push_keeps_authorization_for_one_safe_retry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FlakyRepository(FakeRepository):
        attempts = 0

        def push_with_lease(
            self,
            prepared: GuardedSyncResult,
            reviewed_head: str,
        ) -> None:
            self.attempts += 1
            if self.attempts == 1:
                raise OSError("simulated network failure")
            super().push_with_lease(prepared, reviewed_head)

    lease = RunLease.acquire(tmp_path, "curation")
    _write_prepared_artifact(tmp_path)
    _write_validated_artifact(tmp_path)
    repository = FlakyRepository(tmp_path)
    github = FakeGitHub(pull_requests=[_pull_request()])
    command = [
        "--state-dir",
        str(tmp_path),
        "curation",
        "push",
        "--pr",
        "42",
        "--original-head",
        SHA_A,
        "--lock-token",
        lease.token,
    ]

    assert main(command, github=github, repository=repository) != 0
    _json_output(capsys)
    authorization_id = _test_push_authorization_id(_prepared(), SHA_B)
    journal = tmp_path / f"curation-pr-42-push-{authorization_id}.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "authorized"
    assert repository.remote_head_value == SHA_A

    assert main(command, github=github, repository=repository) == 0
    assert _json_output(capsys)["status"] == "pushed"
    assert repository.attempts == 2
    assert repository.push_calls == [(_prepared(), SHA_B)]
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "pushed"


def test_completed_push_journal_does_not_block_a_later_head_lineage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    _write_pushed_artifact(tmp_path)
    later_prepared = GuardedSyncResult(
        target_branch="codex/catalog-curation-tignes",
        original_head=SHA_B,
        rebased_head=SHA_C,
        backup_ref=f"refs/snowcast-maintainer/backups/pr-42/later-{SHA_B[:12]}",
        prepared_ref=f"refs/snowcast-maintainer/prepared/pr-42/later-{SHA_C[:12]}",
        base_head=SHA_D,
        merge_base=SHA_A,
    )
    _write_prepared_artifact(
        tmp_path,
        prepared=later_prepared,
        selected_head=SHA_B,
    )
    later_validation = {
        "schema_version": 1,
        "pr_number": 42,
        "selected_head": SHA_B,
        "reviewed_head": SHA_C,
        "report_path": "docs/catalog-curation/2026-07-05-tignes.json",
        "prepared": later_prepared.model_dump(mode="json"),
    }
    (tmp_path / "curation-pr-42-validated.json").write_text(
        json.dumps(later_validation),
        encoding="utf-8",
    )
    repository = FakeRepository(
        tmp_path,
        prepared=later_prepared,
        remote_head_value=SHA_D,
    )
    command = [
        "--state-dir",
        str(tmp_path),
        "curation",
        "push",
        "--pr",
        "42",
        "--original-head",
        SHA_B,
        "--lock-token",
        lease.token,
    ]
    github = FakeGitHub(pull_requests=[_pull_request(head_sha=SHA_B)])

    assert main(command, github=github, repository=repository) != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    later_authorization_id = _test_push_authorization_id(
        later_prepared,
        SHA_C,
        selected_head=SHA_B,
    )
    later_journal = tmp_path / (f"curation-pr-42-push-{later_authorization_id}.json")
    assert json.loads(later_journal.read_text(encoding="utf-8"))["phase"] == (
        "authorized"
    )
    assert repository.push_calls == []

    repository.remote_head_value = SHA_B
    assert (
        main(
            command,
            github=github,
            repository=repository,
        )
        == 0
    )
    assert _json_output(capsys)["head_sha"] == SHA_C
    assert repository.push_calls == [(later_prepared, SHA_C)]
    assert json.loads(later_journal.read_text(encoding="utf-8"))["phase"] == "pushed"


def test_discovery_next_holds_lease_and_writes_candidate_inside_state_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "discovery")
    output = tmp_path / "candidate.json"
    github = FakeGitHub()
    repository_root = Path(__file__).resolve().parents[1]

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "next",
                "--output",
                str(output),
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository_root=repository_root,
            today=lambda: date(2026, 7, 8),
        )
        == 0
    )

    payload = _json_output(capsys)
    assert payload["status"] in {"candidate-selected", "no-candidate"}
    if payload["status"] == "candidate-selected":
        candidate = DiscoveryCandidate.model_validate_json(
            output.read_text(encoding="utf-8"),
            strict=True,
        )
        assert payload["candidate_key"] == candidate.key
    lease.assert_owner(lease.token)


def test_discovery_add_source_updates_fingerprint_under_same_lease(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "discovery")
    candidate_path = tmp_path / "candidate.json"
    candidate = DiscoveryCandidate(
        key="ski_area:alpha",
        display_name="Alpha",
        candidate_kind="ski_area",
        country=None,
        alpine_subregion=None,
        regional_graph_key="alpha-region",
        official_urls=(),
        origin="backlog",
        backlog_ref="docs/product-backlog.md#alpha-region",
        backlog_marker="`ski_area:alpha`",
        origin_fingerprint="f" * 64,
        fingerprint="f" * 64,
    )
    candidate_path.write_text(candidate.model_dump_json(), encoding="utf-8")

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "add-source",
                "--candidate-file",
                str(candidate_path),
                "--official-url",
                "https://example.com/official",
                "--lock-token",
                lease.token,
            ]
        )
        == 0
    )

    payload = _json_output(capsys)
    updated = DiscoveryCandidate.model_validate_json(
        candidate_path.read_text(encoding="utf-8"),
        strict=True,
    )
    assert payload == {
        "candidate_key": "ski_area:alpha",
        "fingerprint": updated.fingerprint,
        "status": "source-added",
    }
    assert updated.official_urls == ("https://example.com/official",)
    assert updated.fingerprint != candidate.fingerprint


def test_nomination_is_bounded_to_current_subregion_and_checked_before_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scan_date = date(2026, 7, 8)
    subregion = discovery_subregion(scan_date)
    lease = RunLease.acquire(tmp_path, "discovery")
    output = tmp_path / "nomination.json"

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "nominate",
                "--output",
                str(output),
                "--candidate-key",
                "ski_area:new-alpha",
                "--display-name",
                "New Alpha",
                "--country",
                "Austria",
                "--alpine-subregion",
                subregion,
                "--regional-graph-key",
                "new-alpha-region",
                "--official-url",
                "https://example.com/new-alpha",
                "--lock-token",
                lease.token,
            ],
            github=FakeGitHub(),
            repository_root=Path(__file__).resolve().parents[1],
            today=lambda: scan_date,
        )
        == 0
    )

    candidate = DiscoveryCandidate.model_validate_json(
        output.read_text(encoding="utf-8"),
        strict=True,
    )
    assert _json_output(capsys) == {
        "candidate_key": candidate.key,
        "fingerprint": candidate.fingerprint,
        "status": "candidate-nominated",
    }
    assert candidate.alpine_subregion == subregion
    assert candidate.origin == "registry"


def test_candidate_artifact_must_be_a_direct_child_of_state_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    lease = RunLease.acquire(state_dir, "discovery")

    result = main(
        [
            "--state-dir",
            str(state_dir),
            "discovery",
            "add-source",
            "--candidate-file",
            str(tmp_path / "outside.json"),
            "--official-url",
            "https://example.test/source",
            "--lock-token",
            lease.token,
        ]
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"


def test_curation_publish_reads_typed_summary_as_data_after_lock_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    discovery_lineage = _lineage_state(
        completed_cycles=3,
        lineage_id="catalog-discovery-42",
        candidate_key="ski_area:alpha",
        candidate_origin_fingerprint="e" * 64,
        candidate_fingerprint="f" * 64,
        regional_graph_key="alpha-region",
    )
    _write_prepared_artifact(tmp_path, lineage_state=discovery_lineage)
    _write_validated_artifact(tmp_path)
    _write_pushed_artifact(tmp_path)
    pull_request = _pull_request(head_sha=SHA_B, labels=frozenset())
    github = FakeGitHub(pull_requests=[pull_request])
    machine = MachineState(
        head_sha=SHA_B,
        lineage_id="curation-42",
        completed_cycles=1,
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.WAITING_CI,
        head_sha=SHA_B,
        result="Review and deterministic validation completed.",
        ci_status="Required checks are pending.",
        owner_action="Wait for CI reconciliation.",
        machine_state=machine,
    )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            _publication_payload(
                summary,
                "Catalog curation report synchronized.",
            )
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "curation",
                "publish",
                "--pr",
                "42",
                "--state",
                "maintainer:waiting-ci",
                "--summary-file",
                str(summary_path),
                "--lock-token",
                lease.token,
            ],
            github=github,
            repository=FakeRepository(tmp_path),
        )
        == 0
    )

    assert _json_output(capsys) == {
        "head_sha": SHA_B,
        "state": "maintainer:waiting-ci",
        "status": "published",
    }
    assert [item.split(":", 1)[0] for item in github.published] == [
        "body",
        "comment",
        "labels",
    ]
    published_comment = next(
        item.split(":", 2)[2]
        for item in github.published
        if item.startswith("comment:")
    )
    published_machine = parse_machine_state(published_comment)
    assert published_machine is not None
    assert published_machine.lineage_id == "catalog-discovery-42"
    assert published_machine.completed_cycles == 3
    assert published_machine.head_sha == SHA_B
    assert published_machine.candidate_key == "ski_area:alpha"
    assert published_machine.candidate_origin_fingerprint == "e" * 64
    assert published_machine.candidate_fingerprint == "f" * 64
    assert published_machine.regional_graph_key == "alpha-region"


def test_waiting_ci_publication_rejects_missing_push_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    pull_request = _pull_request(head_sha=SHA_B)
    machine = MachineState(
        head_sha=SHA_B,
        lineage_id="curation-42",
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.WAITING_CI,
        head_sha=SHA_B,
        result="Caller claims validation passed.",
        ci_status="Pending.",
        owner_action="Wait.",
        machine_state=machine,
    )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(_publication_payload(summary, "Managed body.")),
        encoding="utf-8",
    )

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "publish",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--summary-file",
            str(summary_path),
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=[pull_request]),
        repository=FakeRepository(tmp_path),
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"


def test_safe_stop_publication_requires_cli_prepared_lineage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    summary = MaintainerSummary(
        state=MaintainerState.OWNER_DECISION,
        head_sha=SHA_A,
        result="A source conflict needs owner input.",
        ci_status="Not started.",
        owner_action="Choose the authoritative source.",
        machine_state=MachineState(
            head_sha=SHA_A,
            lineage_id="caller-lineage",
            last_publication="complete",
        ),
    )
    summary_path = tmp_path / "owner-decision.json"
    summary_path.write_text(
        json.dumps(_publication_payload(summary, "Managed body.")),
        encoding="utf-8",
    )
    github = FakeGitHub(pull_requests=[_pull_request()])

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "publish",
            "--pr",
            "42",
            "--state",
            "maintainer:owner-decision",
            "--summary-file",
            str(summary_path),
            "--lock-token",
            lease.token,
        ],
        github=github,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert github.published == []


def test_publication_rejects_caller_supplied_machine_state_reset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    summary = MaintainerSummary(
        state=MaintainerState.OWNER_DECISION,
        head_sha=SHA_A,
        result="Owner input required.",
        ci_status="Not started.",
        owner_action="Review the caveat.",
        machine_state=MachineState(
            head_sha=SHA_A,
            lineage_id="caller-reset",
            completed_cycles=0,
            last_publication="complete",
        ),
    )
    payload = _publication_payload(summary, "Managed body.")
    visible = payload["summary"]
    assert isinstance(visible, dict)
    visible["head_sha"] = SHA_A
    visible["machine_state"] = summary.machine_state.model_dump(mode="json")
    summary_path = tmp_path / "reset-attempt.json"
    summary_path.write_text(json.dumps(payload), encoding="utf-8")
    github = FakeGitHub(pull_requests=[_pull_request()])

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "publish",
            "--pr",
            "42",
            "--state",
            "maintainer:owner-decision",
            "--summary-file",
            str(summary_path),
            "--lock-token",
            lease.token,
        ],
        github=github,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert github.published == []


@pytest.mark.parametrize(
    ("check_state", "mergeable", "expected_success"),
    [
        ("success", "MERGEABLE", True),
        ("pending", "MERGEABLE", False),
        ("failure", "MERGEABLE", False),
        ("success", "CONFLICTING", False),
        ("success", "UNKNOWN", False),
    ],
)
def test_ready_publication_is_computed_from_current_pr_and_trusted_state(
    check_state: str,
    mergeable: str,
    expected_success: bool,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    _write_prepared_artifact(tmp_path)
    _write_validated_artifact(tmp_path)
    _write_pushed_artifact(tmp_path)
    pull_request = _pull_request(
        head_sha=SHA_B,
        labels=frozenset({"lane:catalog-curation", "maintainer:waiting-ci"}),
        check_state=check_state,
        mergeable=mergeable,
    )
    machine = MachineState(
        head_sha=SHA_B,
        lineage_id="curation-42",
        completed_cycles=1,
        last_publication="complete",
    )
    prior_summary = MaintainerSummary(
        state=MaintainerState.WAITING_CI,
        head_sha=SHA_B,
        result="Validated and pushed.",
        ci_status="Checks are reconciling.",
        owner_action="Wait.",
        machine_state=machine,
    )
    requested_summary = prior_summary.model_copy(
        update={
            "state": MaintainerState.READY,
            "ci_status": "Checks passed.",
            "owner_action": "Review and merge.",
        }
    )
    summary_path = tmp_path / "ready-summary.json"
    summary_path.write_text(
        json.dumps(_publication_payload(requested_summary, "Managed body.")),
        encoding="utf-8",
    )
    github = FakeGitHub(
        pull_requests=[pull_request],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=render_summary(prior_summary),
                    author_login="lampssy",
                )
            ]
        },
    )

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "publish",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--summary-file",
            str(summary_path),
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=FakeRepository(tmp_path),
    )

    assert (result == 0) is expected_success
    payload = _json_output(capsys)
    if expected_success:
        assert payload["state"] == "maintainer:ready"
        published_comment = next(
            item.split(":", 2)[2]
            for item in github.published
            if item.startswith("update:")
        )
        assert parse_machine_state(published_comment) == machine
    else:
        assert payload["reason"] == "invalid-command-input"
        assert github.published == []


@pytest.mark.parametrize(
    "second_fetch_update",
    [
        pytest.param(None, id="unchanged"),
        pytest.param({"head_sha": SHA_C}, id="head-drift"),
        pytest.param({"body": "Owner body changed."}, id="body-drift"),
        pytest.param(
            {"labels": frozenset({"lane:catalog-discovery", "maintainer:blocked"})},
            id="label-drift",
        ),
        pytest.param({"lifecycle_state": "CLOSED"}, id="lifecycle-drift"),
        pytest.param(
            {"changed_paths": frozenset({"app/data/catalog.json"})},
            id="changed-paths-drift",
        ),
    ],
)
def test_verify_then_publish_proposal_is_bound_to_candidate_and_head(
    second_fetch_update: dict[str, object] | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parents[1]
    lease = RunLease.acquire(tmp_path, "discovery")
    backlog = (root / "docs/product-backlog.md").read_text(encoding="utf-8")
    entry = CoverageCandidate(
        candidate_key="lift_pass_product:test-pass",
        display_name="Test Pass",
        country="Austria",
        alpine_subregion="Austrian Alps",
        regional_graph_key="test-pass-region",
        candidate_kind="lift_pass_product",
        official_urls=("https://example.com/official",),
    )
    candidate = DiscoveryCandidate(
        key=entry.candidate_key,
        display_name=entry.display_name,
        candidate_kind=entry.candidate_kind,
        country=entry.country,
        alpine_subregion=entry.alpine_subregion,
        regional_graph_key=entry.regional_graph_key,
        official_urls=entry.official_urls,
        origin="registry",
        backlog_ref=None,
        backlog_marker=None,
        origin_fingerprint=entry.fingerprint,
        fingerprint=entry.fingerprint,
    )
    candidate_path = tmp_path / "proposal-candidate.json"
    candidate_path.write_text(candidate.model_dump_json(), encoding="utf-8")

    base_catalog = json.loads(
        (root / "app/data/catalog.json").read_text(encoding="utf-8")
    )
    proposed_catalog = json.loads(json.dumps(base_catalog))
    new_row = dict(proposed_catalog["lift_pass_products"][0])
    new_row.update(
        {
            "lift_pass_product_id": "test-pass",
            "name": "Test Pass",
            "default_for_stay_destination_ids": [],
        }
    )
    proposed_catalog["lift_pass_products"].append(new_row)
    base_trust = json.loads(
        (root / "app/data/resort_trust_manifest.json").read_text(encoding="utf-8")
    )
    proposed_trust = json.loads(json.dumps(base_trust))
    trust_entry = json.loads(
        json.dumps(
            next(iter(proposed_trust["entities"]["lift_pass_products"].values()))
        )
    )
    trust_entry["display_name"] = "Test Pass"
    proposed_trust["entities"]["lift_pass_products"]["test-pass"] = trust_entry
    report = _proposal_report(
        tmp_path,
        base_catalog,
        proposed_catalog,
        base_trust,
        proposed_trust,
        candidate,
    )
    report_path = "docs/catalog-curation/test-pass.json"
    registry_path = root / "docs/catalog-discovery/alpine-coverage-registry.json"
    base_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    proposed_registry = json.loads(json.dumps(base_registry))
    proposed_registry["entries"].append(entry.model_dump(mode="json"))
    changed_paths = frozenset(
        {
            "app/data/catalog.json",
            "app/data/resort_trust_manifest.json",
            report_path,
            "docs/catalog-discovery/alpine-coverage-registry.json",
        }
    )
    intent = IntentSnapshot(
        changed_paths=changed_paths,
        catalog_targets=frozenset({candidate.key}),
        report_targets=frozenset(
            {
                candidate.key,
                "trust_manifest:lift_pass_products:test-pass",
            }
        ),
        removed_backlog_markers=frozenset(),
    )
    repository = FakeRepository(
        tmp_path,
        objects={
            (SHA_A, "app/data/catalog.json"): json.dumps(base_catalog),
            (SHA_B, "app/data/catalog.json"): json.dumps(proposed_catalog),
            (SHA_A, "app/data/resort_trust_manifest.json"): json.dumps(base_trust),
            (SHA_B, "app/data/resort_trust_manifest.json"): json.dumps(proposed_trust),
            (SHA_B, "docs/product-backlog.md"): backlog,
            (SHA_B, report_path): report.model_dump_json(),
            (SHA_A, "docs/catalog-discovery/alpine-coverage-registry.json"): json.dumps(
                base_registry
            ),
            (SHA_B, "docs/catalog-discovery/alpine-coverage-registry.json"): json.dumps(
                proposed_registry
            ),
        },
        intent=intent,
    )

    unreconciled = report.model_dump(mode="json")
    removed_change = unreconciled["changes"].pop()
    unreconciled["field_coverage"] = [
        item
        for item in unreconciled["field_coverage"]
        if not (
            item["target_type"] == removed_change["target_type"]
            and item["target_id"] == removed_change["target_id"]
            and item["field_path"] == removed_change["field_path"]
        )
    ]
    for target in unreconciled["reviewed_targets"]:
        if (
            target["target_type"] == removed_change["target_type"]
            and target["target_id"] == removed_change["target_id"]
        ):
            target["required_field_paths"].remove(removed_change["field_path"])
    repository.objects[(SHA_B, report_path)] = json.dumps(unreconciled)
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "verify-proposal",
                "--candidate-file",
                str(candidate_path),
                "--base",
                SHA_A,
                "--head",
                SHA_B,
                "--lock-token",
                lease.token,
            ],
            github=FakeGitHub(),
            repository=repository,
            repository_root=root,
        )
        != 0
    )
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    repository.objects[(SHA_B, report_path)] = report.model_dump_json()

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "verify-proposal",
                "--candidate-file",
                str(candidate_path),
                "--base",
                SHA_A,
                "--head",
                SHA_B,
                "--lock-token",
                lease.token,
            ],
            github=FakeGitHub(),
            repository=repository,
            repository_root=root,
        )
        == 0
    )
    assert _json_output(capsys) == {
        "candidate_key": candidate.key,
        "head_sha": SHA_B,
        "status": "proposal-verified",
    }

    stale_intent = intent.model_copy(
        update={"report_targets": frozenset({"lift_pass_product:other"})}
    )
    repository.intent = stale_intent
    stale_pr = _pull_request(
        head_sha=SHA_B,
        head_ref_name="codex/catalog-curation-discovery",
        changed_paths=changed_paths,
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "publish-proposal",
                "--pr",
                "42",
                "--candidate-file",
                str(candidate_path),
                "--lock-token",
                lease.token,
            ],
            github=FakeGitHub(pull_requests=[stale_pr]),
            repository=repository,
            repository_root=root,
        )
        != 0
    )
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    repository.intent = intent

    mismatched_pr = stale_pr.model_copy(
        update={"changed_paths": frozenset({"app/data/catalog.json"})}
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "publish-proposal",
                "--pr",
                "42",
                "--candidate-file",
                str(candidate_path),
                "--lock-token",
                lease.token,
            ],
            github=FakeGitHub(pull_requests=[mismatched_pr]),
            repository=repository,
            repository_root=root,
        )
        != 0
    )
    assert _json_output(capsys)["reason"] == "invalid-command-input"

    pull_request = _pull_request(
        head_sha=SHA_B,
        head_ref_name="codex/catalog-curation-discovery",
        changed_paths=changed_paths,
    )
    unrelated_entry = CoverageCandidate(
        candidate_key="lift_pass_product:unrelated-pass",
        display_name="Unrelated Pass",
        country="Austria",
        alpine_subregion="Austrian Alps",
        regional_graph_key="unrelated-pass-region",
        candidate_kind="lift_pass_product",
        official_urls=("https://example.com/unrelated",),
    )
    policy_stale_registry = json.loads(json.dumps(proposed_registry))
    policy_stale_registry["entries"].append(unrelated_entry.model_dump(mode="json"))
    repository.objects[
        (SHA_B, "docs/catalog-discovery/alpine-coverage-registry.json")
    ] = json.dumps(policy_stale_registry)
    policy_stale_github = FakeGitHub(pull_requests=[pull_request])
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "publish-proposal",
                "--pr",
                "42",
                "--candidate-file",
                str(candidate_path),
                "--lock-token",
                lease.token,
            ],
            github=policy_stale_github,
            repository=repository,
            repository_root=root,
        )
        != 0
    )
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert policy_stale_github.published == []
    repository.objects[
        (SHA_B, "docs/catalog-discovery/alpine-coverage-registry.json")
    ] = json.dumps(proposed_registry)

    class RefetchGitHub(FakeGitHub):
        fetch_count = 0

        def get_pull_request(self, number: int) -> PullRequest:
            self.fetch_count += 1
            original = super().get_pull_request(number)
            if self.fetch_count == 1 or second_fetch_update is None:
                return original
            return original.model_copy(update=second_fetch_update)

    github = RefetchGitHub(pull_requests=[pull_request])
    publication_result = main(
        [
            "--state-dir",
            str(tmp_path),
            "discovery",
            "publish-proposal",
            "--pr",
            "42",
            "--candidate-file",
            str(candidate_path),
            "--lock-token",
            lease.token,
        ],
        github=github,
        repository=repository,
        repository_root=root,
    )
    assert github.fetch_count == 2
    if second_fetch_update is not None:
        assert publication_result != 0
        assert _json_output(capsys)["reason"] == "invalid-command-input"
        assert github.published == []
        return
    assert publication_result == 0
    assert _json_output(capsys) == {
        "candidate_key": candidate.key,
        "head_sha": SHA_B,
        "state": "maintainer:proposal",
        "status": "proposal-published",
    }
    assert any("lane:catalog-discovery" in item for item in github.published)
    assert any("maintainer:proposal" in item for item in github.published)

    published_body = next(
        item.split(":", 2)[2] for item in github.published if item.startswith("body:")
    )
    published_comment = next(
        item.split(":", 2)[2]
        for item in github.published
        if item.startswith("comment:")
    )
    retry_pr = pull_request.model_copy(
        update={
            "labels": frozenset({"lane:catalog-discovery", "maintainer:proposal"}),
            "body": published_body,
        }
    )
    retry_github = FakeGitHub(
        pull_requests=[retry_pr],
        comments={
            42: [
                GitHubComment(
                    comment_id=101,
                    body=published_comment,
                    author_login="lampssy",
                )
            ]
        },
    )
    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "publish-proposal",
                "--pr",
                "42",
                "--candidate-file",
                str(candidate_path),
                "--lock-token",
                lease.token,
            ],
            github=retry_github,
            repository=repository,
            repository_root=root,
        )
        == 0
    )
    assert _json_output(capsys)["status"] == "proposal-published"


def test_discovery_help_documents_lock_token_for_all_mutable_artifact_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for command in ("next", "add-source", "nominate"):
        with pytest.raises(SystemExit) as exit_info:
            main(["discovery", command, "--help"])
        assert exit_info.value.code == 0
        assert "--lock-token" in capsys.readouterr().out


def test_wrong_lock_stops_before_github_or_repository_access(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Bomb:
        def __getattr__(self, name: str) -> object:
            raise AssertionError(f"dependency accessed before lease: {name}")

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "github",
            "ensure-labels",
            "--lock-token",
            "wrong",
        ],
        github=Bomb(),
        repository=Bomb(),
    )

    assert result != 0
    assert _json_output(capsys) == {
        "reason": "lease-ownership-error",
        "status": "error",
    }


def test_heartbeat_and_release_keep_output_token_free(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "discovery")

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "lock",
                "heartbeat",
                "--token",
                lease.token,
                "--phase",
                "source-research",
            ]
        )
        == 0
    )
    heartbeat = _json_output(capsys)
    assert heartbeat == {"status": "heartbeat", "worker": "discovery"}
    assert lease.token not in json.dumps(heartbeat)

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "lock",
                "release",
                "--token",
                lease.token,
            ]
        )
        == 0
    )
    assert _json_output(capsys) == {
        "status": "released",
        "worker": "discovery",
    }
    assert not lease.lock_dir.exists()


def test_validate_registry_is_read_only_and_machine_readable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = (
        Path(__file__).resolve().parents[1]
        / "docs/catalog-discovery/alpine-coverage-registry.json"
    )

    assert (
        main(
            [
                "--state-dir",
                str(tmp_path),
                "discovery",
                "validate-registry",
                "--registry",
                str(registry),
            ]
        )
        == 0
    )
    payload = _json_output(capsys)
    assert payload["status"] == "valid"
    assert isinstance(payload["entries"], int)
    assert payload["entries"] > 0


def test_add_source_rejects_symlink_candidate_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "discovery")
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    candidate = tmp_path / "candidate.json"
    candidate.symlink_to(target)

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "discovery",
            "add-source",
            "--candidate-file",
            str(candidate),
            "--official-url",
            "https://example.com/official",
            "--lock-token",
            lease.token,
        ]
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"


def test_nomination_rejects_a_different_rotation_subregion_without_writing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scan_date = date(2026, 7, 8)
    expected = discovery_subregion(scan_date)
    wrong = "French Alps" if expected != "French Alps" else "Swiss Alps"
    lease = RunLease.acquire(tmp_path, "discovery")
    output = tmp_path / "nomination.json"

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "discovery",
            "nominate",
            "--output",
            str(output),
            "--candidate-key",
            "ski_area:new-alpha",
            "--display-name",
            "New Alpha",
            "--country",
            "Austria",
            "--alpine-subregion",
            wrong,
            "--regional-graph-key",
            "new-alpha-region",
            "--official-url",
            "https://example.com/new-alpha",
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(),
        repository_root=Path(__file__).resolve().parents[1],
        today=lambda: scan_date,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert not output.exists()


def test_underlying_exception_text_and_secret_are_never_emitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "ghp_do_not_emit"
    monkeypatch.setenv("GH_TOKEN", secret)

    class FailingGitHub:
        def list_open_pull_requests(self) -> list[PullRequest]:
            raise RuntimeError(f"transport included {secret}")

    result = main(
        ["--state-dir", str(tmp_path), "curation", "inventory"],
        github=FailingGitHub(),
    )

    assert result != 0
    rendered = json.dumps(_json_output(capsys))
    assert secret not in rendered
    assert "transport included" not in rendered


def test_discovery_next_distinguishes_proposal_cap_from_queue_exhaustion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parents[1]
    registry_payload = json.loads(
        (root / "docs/catalog-discovery/alpine-coverage-registry.json").read_text(
            encoding="utf-8"
        )
    )
    source = registry_payload["entries"][0]
    pull_requests: list[PullRequest] = []
    comments: dict[int, list[GitHubComment]] = {}
    for number in (2, 3, 4):
        payload = dict(source)
        payload["candidate_key"] = f"ski_area:proposal-{number}"
        payload["regional_graph_key"] = f"proposal-region-{number}"
        payload["candidate_kind"] = "ski_area"
        entry = CoverageCandidate.model_validate(payload)
        candidate = DiscoveryCandidate(
            key=entry.candidate_key,
            display_name=entry.display_name,
            candidate_kind=entry.candidate_kind,
            country=entry.country,
            alpine_subregion=entry.alpine_subregion,
            regional_graph_key=entry.regional_graph_key,
            official_urls=entry.official_urls,
            origin="registry",
            backlog_ref=None,
            backlog_marker=None,
            origin_fingerprint=entry.fingerprint,
            fingerprint=entry.fingerprint,
        )
        pull_request, comment = _proposal_pr(number, candidate)
        pull_requests.append(pull_request)
        comments[number] = [comment]

    lease = RunLease.acquire(tmp_path, "discovery")
    output = tmp_path / "candidate.json"
    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "discovery",
            "next",
            "--output",
            str(output),
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=pull_requests, comments=comments),
        repository_root=root,
    )

    assert result == 0
    assert _json_output(capsys) == {
        "reason": "proposal-cap",
        "status": "no-candidate",
    }
    assert not output.exists()


def test_push_rechecks_current_pr_policy_after_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lease = RunLease.acquire(tmp_path, "curation")
    artifact = {
        "schema_version": 1,
        "pr_number": 42,
        "selected_head": SHA_A,
        "reviewed_head": SHA_B,
        "report_path": "docs/catalog-curation/2026-07-05-tignes.json",
        "prepared": _prepared().model_dump(mode="json"),
    }
    (tmp_path / "curation-pr-42-validated.json").write_text(
        json.dumps(artifact),
        encoding="utf-8",
    )
    repository = FakeRepository(tmp_path)
    ineligible = _pull_request(base_ref_name="release")

    result = main(
        [
            "--state-dir",
            str(tmp_path),
            "curation",
            "push",
            "--pr",
            "42",
            "--original-head",
            SHA_A,
            "--lock-token",
            lease.token,
        ],
        github=FakeGitHub(pull_requests=[ineligible]),
        repository=repository,
    )

    assert result != 0
    assert _json_output(capsys)["reason"] == "invalid-command-input"
    assert repository.push_calls == []


def test_registry_verification_rejects_unrelated_additions() -> None:
    from ops.maintainer.cli import _validate_nomination_registry_change

    candidate_entry = CoverageCandidate(
        candidate_key="ski_area:alpha",
        display_name="Alpha",
        country="Austria",
        alpine_subregion="Austrian Alps",
        regional_graph_key="alpha-region",
        candidate_kind="ski_area",
        official_urls=("https://example.com/alpha",),
    )
    candidate = DiscoveryCandidate(
        key=candidate_entry.candidate_key,
        display_name=candidate_entry.display_name,
        candidate_kind=candidate_entry.candidate_kind,
        country=candidate_entry.country,
        alpine_subregion=candidate_entry.alpine_subregion,
        regional_graph_key=candidate_entry.regional_graph_key,
        official_urls=candidate_entry.official_urls,
        origin="registry",
        backlog_ref=None,
        backlog_marker=None,
        origin_fingerprint=candidate_entry.fingerprint,
        fingerprint=candidate_entry.fingerprint,
    )
    unrelated = candidate_entry.model_copy(
        update={
            "candidate_key": "ski_area:beta",
            "regional_graph_key": "beta-region",
        }
    )

    with pytest.raises(ValueError, match="unrelated registry"):
        _validate_nomination_registry_change(
            candidate,
            CoverageRegistry(schema_version=1, entries=()),
            CoverageRegistry(
                schema_version=1,
                entries=(candidate_entry, unrelated),
            ),
        )


def test_proposal_intent_requires_one_coherent_report_and_candidate_targets(
    tmp_path: Path,
) -> None:
    from ops.maintainer.cli import (
        _proposal_report_path,
        _validate_materialized_proposal,
    )

    base_paths = {
        "app/data/catalog.json",
        "app/data/resort_trust_manifest.json",
    }
    with pytest.raises(ValueError, match="exactly one"):
        _proposal_report_path(
            IntentSnapshot(
                changed_paths=frozenset(base_paths),
                catalog_targets=frozenset(),
                report_targets=frozenset(),
                removed_backlog_markers=frozenset(),
            )
        )
    with pytest.raises(ValueError, match="unrelated curation"):
        _proposal_report_path(
            IntentSnapshot(
                changed_paths=frozenset(
                    {
                        *base_paths,
                        "docs/catalog-curation/alpha.json",
                        "docs/catalog-curation/unrelated.md",
                    }
                ),
                catalog_targets=frozenset(),
                report_targets=frozenset(),
                removed_backlog_markers=frozenset(),
            )
        )

    entry = CoverageCandidate(
        candidate_key="lift_pass_product:missing-target",
        display_name="Missing Target",
        country="Austria",
        alpine_subregion="Austrian Alps",
        regional_graph_key="missing-target-region",
        candidate_kind="lift_pass_product",
        official_urls=("https://example.com/missing-target",),
    )
    candidate = DiscoveryCandidate(
        key=entry.candidate_key,
        display_name=entry.display_name,
        candidate_kind=entry.candidate_kind,
        country=entry.country,
        alpine_subregion=entry.alpine_subregion,
        regional_graph_key=entry.regional_graph_key,
        official_urls=entry.official_urls,
        origin="registry",
        backlog_ref=None,
        backlog_marker=None,
        origin_fingerprint=entry.fingerprint,
        fingerprint=entry.fingerprint,
    )
    snapshot = IntentSnapshot(
        changed_paths=frozenset({*base_paths, "docs/catalog-curation/alpha.json"}),
        catalog_targets=frozenset({candidate.key}),
        report_targets=frozenset({"lift_pass_product:other"}),
        removed_backlog_markers=frozenset(),
    )
    with pytest.raises(ValueError, match="report targets"):
        _validate_materialized_proposal(
            object(),
            snapshot,
            candidate,
            SHA_A,
            SHA_B,
            tmp_path,
        )


@pytest.mark.parametrize(
    "branch",
    [
        "codex/discovery-alpha",
        "codex/catalog-curation-Alpha",
        "codex/catalog-curation-alpha_beta",
        "codex/catalog-curation-alpha/extra",
        "codex/catalog-curation-",
    ],
)
def test_proposal_publication_requires_exact_catalog_curation_branch(
    branch: str,
) -> None:
    from ops.maintainer.cli import _is_safe_proposal_publication_pr

    assert not _is_safe_proposal_publication_pr(_pull_request(head_ref_name=branch))


def test_declined_fingerprint_is_derived_from_one_strict_closed_pr_lineage() -> None:
    from ops.maintainer.cli import _declined_fingerprints

    entry = CoverageCandidate(
        candidate_key="ski_area:declined-alpha",
        display_name="Declined Alpha",
        country="Austria",
        alpine_subregion="Austrian Alps",
        regional_graph_key="declined-alpha-region",
        candidate_kind="ski_area",
        official_urls=("https://example.com/declined-alpha",),
    )
    candidate = DiscoveryCandidate(
        key=entry.candidate_key,
        display_name=entry.display_name,
        candidate_kind=entry.candidate_kind,
        country=entry.country,
        alpine_subregion=entry.alpine_subregion,
        regional_graph_key=entry.regional_graph_key,
        official_urls=entry.official_urls,
        origin="registry",
        backlog_ref=None,
        backlog_marker=None,
        origin_fingerprint=entry.fingerprint,
        fingerprint=entry.fingerprint,
    )
    pull_request, comment = _proposal_pr(7, candidate)
    closed = pull_request.model_copy(update={"lifecycle_state": "CLOSED"})
    github = FakeGitHub(
        closed_pull_requests=[closed],
        comments={7: [comment]},
    )

    assert _declined_fingerprints(github, catalog_keys=set()) == {
        (candidate.key, candidate.origin_fingerprint)
    }

    github.closed_pull_requests = [
        closed.model_copy(update={"lifecycle_state": "MERGED"})
    ]
    assert _declined_fingerprints(github, catalog_keys=set()) == set()

    github.closed_pull_requests = [
        closed.model_copy(update={"head_repository_owner": "attacker"})
    ]
    with pytest.raises(ValueError, match="provenance"):
        _declined_fingerprints(github, catalog_keys=set())


def test_decline_history_with_only_untrusted_summary_fails_closed() -> None:
    from ops.maintainer.cli import _declined_fingerprints

    entry = CoverageCandidate(
        candidate_key="ski_area:declined-beta",
        display_name="Declined Beta",
        country="Austria",
        alpine_subregion="Austrian Alps",
        regional_graph_key="declined-beta-region",
        candidate_kind="ski_area",
        official_urls=("https://example.com/declined-beta",),
    )
    candidate = DiscoveryCandidate(
        key=entry.candidate_key,
        display_name=entry.display_name,
        candidate_kind=entry.candidate_kind,
        country=entry.country,
        alpine_subregion=entry.alpine_subregion,
        regional_graph_key=entry.regional_graph_key,
        official_urls=entry.official_urls,
        origin="registry",
        backlog_ref=None,
        backlog_marker=None,
        origin_fingerprint=entry.fingerprint,
        fingerprint=entry.fingerprint,
    )
    pull_request, comment = _proposal_pr(8, candidate)
    closed = pull_request.model_copy(update={"lifecycle_state": "CLOSED"})
    forged = GitHubComment(
        comment_id=comment.comment_id,
        body=comment.body,
        author_login="attacker",
    )

    with pytest.raises(ValueError, match="exactly one trusted"):
        _declined_fingerprints(
            FakeGitHub(
                closed_pull_requests=[closed],
                comments={8: [forged]},
            ),
            catalog_keys=set(),
        )

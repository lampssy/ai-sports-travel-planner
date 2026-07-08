from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from ops.maintainer.cli import main
from ops.maintainer.discovery import (
    CoverageCandidate,
    CoverageRegistry,
    DiscoveryCandidate,
    discovery_subregion,
    parse_catalog_backlog,
    render_candidate_discovery_origin,
    with_official_urls,
)
from ops.maintainer.git_ops import GuardedSyncResult
from ops.maintainer.github import GitHubComment
from ops.maintainer.models import MachineState, MaintainerState, PullRequest
from ops.maintainer.publication import MaintainerSummary, render_summary
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


@dataclass
class FakeGitHub:
    pull_requests: list[PullRequest] = field(default_factory=list)
    comments: dict[int, list[GitHubComment]] = field(default_factory=dict)
    labels_ensured: bool = False
    published: list[str] = field(default_factory=list)

    def list_open_pull_requests(self) -> list[PullRequest]:
        return list(self.pull_requests)

    def get_pull_request(self, number: int) -> PullRequest:
        return next(item for item in self.pull_requests if item.number == number)

    def list_issue_comments(self, number: int) -> list[GitHubComment]:
        return list(self.comments.get(number, ()))

    def list_closed_proposal_comments(self) -> list[GitHubComment]:
        return []

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

    def show_text(self, revision: str, path: str) -> str:
        return self.objects[(revision, path)]


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    output = capsys.readouterr()
    assert output.err == ""
    lines = output.out.splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert isinstance(payload, dict)
    return payload


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
    assert persisted["prepared"] == _prepared().model_dump(mode="json")
    assert persisted["pr_number"] == 42
    assert repository.prepare_calls == [42]


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
    pull_request = _pull_request(labels=frozenset())
    github = FakeGitHub(pull_requests=[pull_request])
    machine = MachineState(
        head_sha=SHA_A,
        lineage_id="curation-42",
        completed_cycles=1,
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.WAITING_CI,
        head_sha=SHA_A,
        result="Review and deterministic validation completed.",
        ci_status="Required checks are pending.",
        owner_action="Wait for CI reconciliation.",
        machine_state=machine,
    )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "summary": summary.model_dump(mode="json"),
                "managed_body": "Catalog curation report synchronized.",
            }
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
        "head_sha": SHA_A,
        "state": "maintainer:waiting-ci",
        "status": "published",
    }
    assert [item.split(":", 1)[0] for item in github.published] == [
        "body",
        "comment",
        "labels",
    ]


def test_verify_then_publish_proposal_is_bound_to_candidate_and_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parents[1]
    lease = RunLease.acquire(tmp_path, "discovery")
    backlog = (root / "docs/product-backlog.md").read_text(encoding="utf-8")
    candidate = with_official_urls(
        next(
            item
            for item in parse_catalog_backlog(backlog)
            if item.candidate_kind == "stay_destination"
        ),
        ("https://example.com/official",),
    )
    candidate_path = tmp_path / "proposal-candidate.json"
    candidate_path.write_text(candidate.model_dump_json(), encoding="utf-8")

    base_catalog = json.loads(
        (root / "app/data/catalog.json").read_text(encoding="utf-8")
    )
    proposed_catalog = json.loads(json.dumps(base_catalog))
    section = f"{candidate.candidate_kind}s"
    id_field = {
        "stay_destination": "stay_destination_id",
        "stay_base": "stay_base_id",
        "ski_area": "ski_area_id",
        "ski_area_access": "ski_area_access_id",
        "terrain_domain": "terrain_domain_id",
        "lift_pass_product": "lift_pass_product_id",
    }[candidate.candidate_kind]
    new_row = dict(proposed_catalog[section][0])
    new_row[id_field] = candidate.key.split(":", 1)[1]
    proposed_catalog[section].append(new_row)
    proposed_backlog = backlog.replace(candidate.backlog_marker or "", "")
    registry_path = root / "docs/catalog-discovery/alpine-coverage-registry.json"
    registry = registry_path.read_text(encoding="utf-8")
    repository = FakeRepository(
        tmp_path,
        objects={
            (SHA_A, "app/data/catalog.json"): json.dumps(base_catalog),
            (SHA_B, "app/data/catalog.json"): json.dumps(proposed_catalog),
            (SHA_B, "docs/product-backlog.md"): proposed_backlog,
            (SHA_A, "docs/catalog-discovery/alpine-coverage-registry.json"): registry,
            (SHA_B, "docs/catalog-discovery/alpine-coverage-registry.json"): registry,
        },
    )

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

    pull_request = _pull_request(
        head_sha=SHA_B,
        head_ref_name="codex/catalog-curation-discovery",
    )
    github = FakeGitHub(pull_requests=[pull_request])
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
            github=github,
            repository=repository,
            repository_root=root,
        )
        == 0
    )
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

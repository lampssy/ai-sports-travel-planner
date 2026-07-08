from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops.maintainer.git_ops import (
    GitRepository,
    GuardedSyncResult,
    RebaseConflictError,
    RepositorySafetyError,
    StaleRemoteHeadError,
)
from ops.maintainer.intent import IntentDriftError
from ops.maintainer.models import PullRequest

pytestmark = pytest.mark.db_free


SHA_A = "a" * 40
SHA_B = "b" * 40
ZERO_SHA = "0" * 40
CANONICAL_REMOTE = "git@github.com:lampssy/ai-sports-travel-planner.git"


@dataclass
class FakeRunner:
    root: Path
    remote: str = CANONICAL_REMOTE
    responses: list[subprocess.CompletedProcess[str]] = field(default_factory=list)
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        call = tuple(argv)
        self.calls.append(call)
        if call == ("git", "rev-parse", "--show-toplevel"):
            return subprocess.CompletedProcess(call, 0, f"{self.root}\n", "")
        if call == ("git", "config", "--get", "remote.origin.url"):
            return subprocess.CompletedProcess(call, 0, f"{self.remote}\n", "")
        if not self.responses:
            return subprocess.CompletedProcess(call, 0, "", "")
        return self.responses.pop(0)


def _pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Alpha",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": "codex/catalog-curation-alpha",
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "created_at": datetime(2026, 7, 8, 10, tzinfo=UTC),
        "labels": frozenset(),
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset({"app/data/catalog.json"}),
        "body": "",
    }
    values.update(overrides)
    return PullRequest.model_validate(values)


def _result(**overrides: str) -> GuardedSyncResult:
    values = {
        "target_branch": "codex/catalog-curation-alpha",
        "original_head": SHA_A,
        "rebased_head": SHA_B,
        "backup_ref": (
            f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{SHA_A[:12]}"
        ),
        "merge_base": "c" * 40,
    }
    values.update(overrides)
    return GuardedSyncResult.model_validate(values)


def _repository(tmp_path: Path, runner: FakeRunner | None = None) -> GitRepository:
    resolved = tmp_path.resolve()
    return GitRepository(resolved, runner=runner or FakeRunner(resolved))


def test_repository_rejects_unresolved_root_before_running_git(tmp_path: Path) -> None:
    unresolved = tmp_path / "missing" / ".."
    runner = FakeRunner(tmp_path.resolve())

    with pytest.raises(RepositorySafetyError, match="resolved worktree root"):
        GitRepository(unresolved, runner=runner)

    assert runner.calls == []


def test_repository_rejects_wrong_git_root(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner((tmp_path / "other").resolve())

    with pytest.raises(RepositorySafetyError, match="worktree root mismatch"):
        GitRepository(root, runner=runner)


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com-lampss:lampssy/ai-sports-travel-planner.git",
        "git@github.com:lampssy/ai-sports-travel-planner.git",
        "ssh://git@github.com/lampssy/ai-sports-travel-planner.git",
        "https://github.com/lampssy/ai-sports-travel-planner.git",
        "https://github.com/lampssy/ai-sports-travel-planner",
    ],
)
def test_repository_accepts_only_supported_current_and_canonical_remotes(
    tmp_path: Path,
    remote: str,
) -> None:
    root = tmp_path.resolve()

    GitRepository(root, runner=FakeRunner(root, remote=remote))


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:other/ai-sports-travel-planner.git",
        "git@github.com:lampssy/other.git",
        "git@evil.example:lampssy/ai-sports-travel-planner.git",
        "https://github.com/evil/../lampssy/ai-sports-travel-planner.git",
        "https://github.com/lampssy/ai-sports-travel-planner.evil",
        "https://lampssy@github.com/lampssy/ai-sports-travel-planner.git",
        " https://github.com/lampssy/ai-sports-travel-planner.git",
        "https://github.com/lampssy/ai-sports-travel-planner.git ",
    ],
)
def test_repository_rejects_wrong_remote_owner_or_substring_tricks(
    tmp_path: Path,
    remote: str,
) -> None:
    root = tmp_path.resolve()

    with pytest.raises(RepositorySafetyError, match="origin must be"):
        GitRepository(root, runner=FakeRunner(root, remote=remote))


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "codex/",
        "codex/../main",
        "codex/bad..branch",
        "codex/bad branch",
        "codex/bad.lock",
        "codex/bad@{1}",
    ],
)
def test_malformed_target_branch_is_rejected_before_runner_mutation(
    tmp_path: Path,
    branch: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    initial_calls = list(runner.calls)

    with pytest.raises(RepositorySafetyError, match="target branch"):
        repository.fetch_for_pr(branch)

    assert runner.calls == initial_calls


@pytest.mark.parametrize("sha", ["A" * 40, "a" * 39, "z" * 40, ""])
def test_malformed_sha_is_rejected_before_backup_mutation(
    tmp_path: Path,
    sha: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    initial_calls = list(runner.calls)

    with pytest.raises(RepositorySafetyError, match="lowercase 40-hex"):
        repository.create_backup_ref(42, sha)

    assert runner.calls == initial_calls


@pytest.mark.parametrize("number", [0, -1, True])
def test_invalid_pr_number_is_rejected_before_backup_mutation(
    tmp_path: Path,
    number: object,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    initial_calls = list(runner.calls)

    with pytest.raises(RepositorySafetyError, match="positive integer"):
        repository.create_backup_ref(number, SHA_A)  # type: ignore[arg-type]

    assert runner.calls == initial_calls


def test_remote_head_uses_exact_heads_lookup_and_requires_one_sha(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            subprocess.CompletedProcess((), 0, f"{SHA_A}\trefs/heads/codex/alpha\n", "")
        ],
    )
    repository = GitRepository(root, runner=runner)

    assert repository.remote_head("codex/alpha") == SHA_A
    assert runner.calls[-1] == (
        "git",
        "ls-remote",
        "--heads",
        "origin",
        "refs/heads/codex/alpha",
    )


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        f"{SHA_A}\trefs/heads/codex/alpha\n{SHA_B}\trefs/heads/codex/alpha\n",
        f"{'A' * 40}\trefs/heads/codex/alpha\n",
        f"{SHA_A}\trefs/heads/codex/other\n",
    ],
)
def test_remote_head_rejects_missing_ambiguous_or_malformed_output(
    tmp_path: Path,
    stdout: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[subprocess.CompletedProcess((), 0, stdout, "")],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(RepositorySafetyError, match="exactly one remote head"):
        repository.remote_head("codex/alpha")


def test_fetch_for_pr_uses_only_exact_main_and_target_refspecs(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)

    repository.fetch_for_pr("codex/alpha")

    assert runner.calls[-1] == (
        "git",
        "fetch",
        "--no-tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        "+refs/heads/codex/alpha:refs/remotes/origin/codex/alpha",
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"head_repository_owner": "other"},
        {"is_cross_repository": True},
        {"base_ref_name": "release"},
    ],
)
def test_prepare_rejects_unsafe_pr_metadata_before_any_git_mutation(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    initial_calls = list(runner.calls)

    with pytest.raises(RepositorySafetyError):
        repository.prepare_guarded_sync(_pull_request(**overrides))

    assert runner.calls == initial_calls


def test_backup_ref_is_persistent_create_only_and_collision_safe(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            subprocess.CompletedProcess((), 0, "", ""),
            subprocess.CompletedProcess((), 128, "", "reference already exists"),
        ],
    )
    repository = GitRepository(
        root,
        runner=runner,
        now=lambda: datetime(2026, 7, 8, 10, tzinfo=UTC),
    )

    backup_ref = repository.create_backup_ref(42, SHA_A)

    assert backup_ref == (
        f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{SHA_A[:12]}"
    )
    assert runner.calls[-1] == (
        "git",
        "update-ref",
        backup_ref,
        SHA_A,
        ZERO_SHA,
    )

    with pytest.raises(RepositorySafetyError, match="backup ref collision"):
        repository.create_backup_ref(42, SHA_A)
    assert all("delete" not in call for call in runner.calls)


def test_push_with_lease_uses_exact_lease_and_never_plain_force(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            subprocess.CompletedProcess(
                (),
                0,
                f"{SHA_A}\trefs/heads/codex/catalog-curation-alpha\n",
                "",
            ),
            subprocess.CompletedProcess((), 0, "", ""),
        ],
    )
    repository = GitRepository(root, runner=runner)

    repository.push_with_lease(_result())

    push_calls = [call for call in runner.calls if call[1:2] == ("push",)]
    assert push_calls == [
        (
            "git",
            "push",
            f"--force-with-lease=refs/heads/codex/catalog-curation-alpha:{SHA_A}",
            "origin",
            "HEAD:refs/heads/codex/catalog-curation-alpha",
        )
    ]
    assert "--force" not in push_calls[0]


def test_stale_remote_head_blocks_push_before_any_push_invocation(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            subprocess.CompletedProcess(
                (),
                0,
                f"{SHA_B}\trefs/heads/codex/catalog-curation-alpha\n",
                "",
            )
        ],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(StaleRemoteHeadError, match=f"expected {SHA_A}.*{SHA_B}"):
        repository.push_with_lease(_result())

    assert not any(call[1:2] == ("push",) for call in runner.calls)


def test_push_reverifies_origin_before_remote_head_or_push(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    runner.remote = "git@github.com:other/ai-sports-travel-planner.git"
    initial_calls = len(runner.calls)

    with pytest.raises(RepositorySafetyError, match="origin must be"):
        repository.push_with_lease(_result())

    push_calls = runner.calls[initial_calls:]
    assert not any(call[1:2] in {("ls-remote",), ("push",)} for call in push_calls)


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return result.stdout.strip()


def _catalog(*, alpha_name: str | None = None) -> str:
    payload: dict[str, object] = {
        "schema_version": 2,
        "ski_regions": [],
        "stay_destinations": [],
        "stay_bases": [],
        "ski_areas": [],
        "ski_area_access": [],
        "terrain_domains": [],
        "lift_pass_products": [],
        "rental_display_facts": [],
    }
    if alpha_name is not None:
        payload["ski_areas"] = [{"ski_area_id": "alpha", "name": alpha_name}]
    return json.dumps(payload, indent=2) + "\n"


@dataclass(frozen=True)
class LocalRepository:
    remote: Path
    checkout: Path
    target_sha: str
    main_sha: str
    pull_request: PullRequest


def _local_repository(
    tmp_path: Path,
    *,
    target_catalog: str = _catalog(alpha_name="Target Alpha"),
    main_catalog: str | None = None,
) -> LocalRepository:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    checkout = tmp_path / "checkout"
    remote.mkdir()
    _git(remote, "init", "--bare", "--initial-branch=main")
    seed.mkdir()
    _git(seed, "init", "--initial-branch=main")
    _git(seed, "config", "user.name", "Snowcast Test")
    _git(seed, "config", "user.email", "snowcast@example.test")
    _git(seed, "config", "commit.gpgsign", "false")
    (seed / "app" / "data").mkdir(parents=True)
    (seed / "app" / "data" / "catalog.json").write_text(_catalog(), encoding="utf-8")
    (seed / "README.md").write_text("base\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", "base")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "origin", "main")

    _git(seed, "switch", "-c", "codex/catalog-curation-alpha")
    (seed / "app" / "data" / "catalog.json").write_text(
        target_catalog, encoding="utf-8"
    )
    _git(seed, "add", "app/data/catalog.json")
    _git(seed, "commit", "-m", "curate alpha")
    target_sha = _git(seed, "rev-parse", "HEAD")
    _git(seed, "push", "origin", "codex/catalog-curation-alpha")

    _git(seed, "switch", "main")
    if main_catalog is None:
        (seed / "README.md").write_text("base\nmain update\n", encoding="utf-8")
        main_path = "README.md"
    else:
        (seed / "app" / "data" / "catalog.json").write_text(
            main_catalog, encoding="utf-8"
        )
        main_path = "app/data/catalog.json"
    _git(seed, "add", main_path)
    _git(seed, "commit", "-m", "advance main")
    main_sha = _git(seed, "rev-parse", "HEAD")
    _git(seed, "push", "origin", "main")

    _git(tmp_path, "clone", str(remote), str(checkout))
    _git(checkout, "config", "user.name", "Snowcast Test")
    _git(checkout, "config", "user.email", "snowcast@example.test")
    _git(checkout, "config", "commit.gpgsign", "false")
    _git(checkout, "remote", "set-url", "origin", CANONICAL_REMOTE)
    _git(
        checkout,
        "config",
        f"url.file://{remote}.insteadOf",
        CANONICAL_REMOTE,
    )
    pull_request = _pull_request(head_sha=target_sha)
    return LocalRepository(remote, checkout, target_sha, main_sha, pull_request)


def _integration_repository(local: LocalRepository) -> GitRepository:
    return GitRepository(
        local.checkout.resolve(),
        now=lambda: datetime(2026, 7, 8, 10, tzinfo=UTC),
    )


def test_guarded_prepare_rebases_detached_creates_backup_and_does_not_push(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)

    result = repository.prepare_guarded_sync(local.pull_request)

    assert result.target_branch == local.pull_request.head_ref_name
    assert result.original_head == local.target_sha
    assert result.rebased_head == _git(local.checkout, "rev-parse", "HEAD")
    assert result.rebased_head != result.original_head
    assert _git(local.checkout, "branch", "--show-current") == ""
    assert _git(local.checkout, "rev-parse", result.backup_ref) == local.target_sha
    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )


def test_detached_prepare_is_not_blocked_when_target_is_checked_out_elsewhere(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    other = tmp_path / "other-worktree"
    _git(
        local.checkout,
        "branch",
        "--track",
        "codex/catalog-curation-alpha",
        "origin/codex/catalog-curation-alpha",
    )
    _git(
        local.checkout,
        "worktree",
        "add",
        str(other),
        "codex/catalog-curation-alpha",
    )

    result = _integration_repository(local).prepare_guarded_sync(local.pull_request)

    assert result.rebased_head == _git(local.checkout, "rev-parse", "HEAD")
    assert _git(other, "branch", "--show-current") == "codex/catalog-curation-alpha"


def test_conflict_aborts_and_preserves_remote_and_backup(tmp_path: Path) -> None:
    local = _local_repository(
        tmp_path,
        target_catalog=_catalog(alpha_name="Target Alpha"),
        main_catalog=_catalog(alpha_name="Main Alpha"),
    )
    repository = _integration_repository(local)

    with pytest.raises(RebaseConflictError, match="rebase conflict"):
        repository.prepare_guarded_sync(local.pull_request)

    backup_refs = _git(
        local.checkout,
        "for-each-ref",
        "--format=%(refname)",
        "refs/snowcast-maintainer/backups/pr-42/",
    ).splitlines()
    assert len(backup_refs) == 1
    assert _git(local.checkout, "rev-parse", backup_refs[0]) == local.target_sha
    assert not (local.checkout / ".git" / "rebase-merge").exists()
    assert not (local.checkout / ".git" / "rebase-apply").exists()
    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )


def test_remote_movement_after_prepare_blocks_push_and_preserves_remote(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    result = repository.prepare_guarded_sync(local.pull_request)
    moved_sha = local.main_sha
    _git(
        local.remote,
        "update-ref",
        "refs/heads/codex/catalog-curation-alpha",
        moved_sha,
        local.target_sha,
    )

    with pytest.raises(StaleRemoteHeadError):
        repository.push_with_lease(result)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == moved_sha
    )


def test_successful_exact_lease_push_updates_only_selected_codex_branch(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    _git(local.remote, "update-ref", "refs/heads/codex/other", local.main_sha)
    repository = _integration_repository(local)
    result = repository.prepare_guarded_sync(local.pull_request)

    repository.push_with_lease(result)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == result.rebased_head
    )
    assert _git(local.remote, "rev-parse", "refs/heads/codex/other") == local.main_sha
    assert _git(local.remote, "rev-parse", "refs/heads/main") == local.main_sha


def test_semantic_intent_drift_after_clean_rebase_prevents_push(
    tmp_path: Path,
) -> None:
    identical = _catalog(alpha_name="Same Alpha")
    local = _local_repository(
        tmp_path,
        target_catalog=identical,
        main_catalog=identical,
    )
    repository = _integration_repository(local)

    with pytest.raises(IntentDriftError, match="catalog_targets removed"):
        repository.prepare_guarded_sync(local.pull_request)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )

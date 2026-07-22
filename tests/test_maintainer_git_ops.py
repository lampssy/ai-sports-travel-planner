from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.data.catalog_curation import (
    CatalogCurationReport,
    validate_catalog_curation_report,
    validate_catalog_resulting_graph,
)
from app.data.catalog_curation_reconciliation import reconcile_catalog_curation_report
from app.data.catalog_loader import load_catalog_from_path
from ops.maintainer.git_ops import (
    ContinuationReplayResult,
    GitAuthenticationError,
    GitOperationTimeoutError,
    GitPushRejectedError,
    GitRemotePolicyError,
    GitRepository,
    GitTransportError,
    GuardedSyncResult,
    RebaseConflictError,
    RemotePolicy,
    RepositorySafetyError,
    ReviewedCheckpointRefs,
    StaleRemoteHeadError,
    _SubprocessRunner,
)
from ops.maintainer.intent import (
    IntentDriftError,
    IntentSnapshot,
    build_intent_snapshot,
)
from ops.maintainer.models import PullRequest

pytestmark = pytest.mark.db_free


SHA_A = "a" * 40
SHA_B = "b" * 40
ZERO_SHA = "0" * 40
CANONICAL_REMOTE = "git@github.com:lampssy/ai-sports-travel-planner.git"
REPORT_PATH = "docs/catalog-curation/alpha.json"
CATALOG_PATH = "app/data/catalog.json"
TRUST_MANIFEST_PATH = "app/data/resort_trust_manifest.json"


@dataclass
class FakeRunner:
    root: Path
    remote: str = CANONICAL_REMOTE
    effective_fetch_urls: tuple[str, ...] | None = None
    effective_push_urls: tuple[str, ...] | None = None
    ssh_hostname: str = "github.com"
    ssh_user: str = "git"
    responses: list[subprocess.CompletedProcess[str]] = field(default_factory=list)
    calls: list[tuple[str, ...]] = field(default_factory=list)
    call_metadata: list[tuple[tuple[str, ...], float]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float = 10.0,
    ) -> subprocess.CompletedProcess[str]:
        call = tuple(argv)
        self.calls.append(call)
        self.call_metadata.append((call, timeout))
        if call == ("git", "rev-parse", "--show-toplevel"):
            return subprocess.CompletedProcess(call, 0, f"{self.root}\n", "")
        if call == ("git", "config", "--get", "remote.origin.url"):
            return subprocess.CompletedProcess(call, 0, f"{self.remote}\n", "")
        if call == ("git", "remote", "get-url", "--all", "origin"):
            urls = self.effective_fetch_urls or (self.remote,)
            return subprocess.CompletedProcess(call, 0, "\n".join(urls) + "\n", "")
        if call == (
            "git",
            "remote",
            "get-url",
            "--push",
            "--all",
            "origin",
        ):
            urls = (
                self.effective_push_urls or self.effective_fetch_urls or (self.remote,)
            )
            return subprocess.CompletedProcess(call, 0, "\n".join(urls) + "\n", "")
        if call[:2] == ("ssh", "-G"):
            return subprocess.CompletedProcess(
                call,
                0,
                f"hostname {self.ssh_hostname}\nuser {self.ssh_user}\n"
                "identityfile /secret/must-not-leak\n",
                "",
            )
        if call[:3] == ("git", "check-ref-format", "--branch"):
            return subprocess.run(
                list(call),
                check=False,
                capture_output=True,
                text=True,
                shell=False,
            )
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
        "lifecycle_state": "OPEN",
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
        "prepared_ref": (
            f"refs/snowcast-maintainer/prepared/pr-42/{'d' * 12}-{SHA_B[:12]}"
        ),
        "base_head": "d" * 40,
        "merge_base": "c" * 40,
    }
    values.update(overrides)
    return GuardedSyncResult.model_validate(values)


def _push_responses(
    *,
    remote_sha: str = SHA_A,
    push_returncode: int = 0,
    push_stderr: str = "",
) -> list[subprocess.CompletedProcess[str]]:
    return [
        subprocess.CompletedProcess((), 0, f"{SHA_B}\n", ""),
        subprocess.CompletedProcess((), 0, f"{SHA_A}\n", ""),
        subprocess.CompletedProcess((), 0, "", ""),
        subprocess.CompletedProcess(
            (),
            0,
            f"{remote_sha}\trefs/heads/codex/catalog-curation-alpha\n",
            "",
        ),
        subprocess.CompletedProcess((), push_returncode, "", push_stderr),
    ]


def _repository(tmp_path: Path, runner: FakeRunner | None = None) -> GitRepository:
    resolved = tmp_path.resolve()
    return GitRepository(resolved, runner=runner or FakeRunner(resolved))


def _completed(
    returncode: int = 0,
    stdout: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess((), returncode, stdout, "")


def _validation_runner(
    root: Path,
    *,
    head: str = "d" * 40,
    status: str = "",
) -> FakeRunner:
    return FakeRunner(
        root,
        responses=[
            _completed(stdout=str(root / ".git/rebase-merge")),
            _completed(stdout=str(root / ".git/rebase-apply")),
            _completed(stdout=status),
            _completed(stdout=f"{head}\n"),
        ],
    )


def _write_validation_base_files(root: Path) -> None:
    data = root / "app/data"
    data.mkdir(parents=True)
    (data / "catalog.json").write_text("{}", encoding="utf-8")
    (data / "resort_trust_manifest.json").write_text("{}", encoding="utf-8")


def test_read_bounded_immutable_text_sizes_before_reading(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[_completed(stdout="5\n"), _completed(stdout="hello")],
    )
    repository = GitRepository(root, runner=runner)
    runner.calls.clear()

    content = repository.read_bounded_immutable_text(
        SHA_A,
        "docs/catalog-curation/report.json",
        max_bytes=5,
    )

    assert content == "hello"
    assert runner.calls == [
        (
            "git",
            "cat-file",
            "-s",
            f"{SHA_A}:docs/catalog-curation/report.json",
        ),
        (
            "git",
            "show",
            "--no-ext-diff",
            "--format=",
            f"{SHA_A}:docs/catalog-curation/report.json",
        ),
    ]


@pytest.mark.parametrize("reported_size", ["0\n", "6\n"])
def test_read_bounded_immutable_text_rejects_zero_or_oversized_before_read(
    tmp_path: Path,
    reported_size: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root, responses=[_completed(stdout=reported_size)])
    repository = GitRepository(root, runner=runner)
    runner.calls.clear()

    with pytest.raises(RepositorySafetyError):
        repository.read_bounded_immutable_text(
            SHA_A,
            "app/data/catalog.json",
            max_bytes=5,
        )

    assert runner.calls == [("git", "cat-file", "-s", f"{SHA_A}:app/data/catalog.json")]


@pytest.mark.parametrize("size_output", ["", "01\n", "5 bytes\n", "5\n6\n"])
def test_read_bounded_immutable_text_rejects_malformed_size(
    tmp_path: Path,
    size_output: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root, responses=[_completed(stdout=size_output)])
    repository = GitRepository(root, runner=runner)
    runner.calls.clear()

    with pytest.raises(RepositorySafetyError):
        repository.read_bounded_immutable_text(
            SHA_A,
            "app/data/catalog.json",
            max_bytes=5,
        )

    assert not any(call[1:2] == ("show",) for call in runner.calls)


def test_read_bounded_immutable_text_sanitizes_size_command_failure(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            subprocess.CompletedProcess(
                (),
                1,
                "",
                "raw secret object failure",
            )
        ],
    )
    repository = GitRepository(root, runner=runner)
    runner.calls.clear()

    with pytest.raises(RepositorySafetyError) as exc_info:
        repository.read_bounded_immutable_text(
            SHA_A,
            "app/data/catalog.json",
            max_bytes=5,
        )

    assert "raw secret" not in str(exc_info.value)
    assert not any(call[1:2] == ("show",) for call in runner.calls)


def test_read_bounded_immutable_text_rechecks_encoded_length(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[_completed(stdout="5\n"), _completed(stdout="too long")],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(RepositorySafetyError):
        repository.read_bounded_immutable_text(
            SHA_A,
            "app/data/catalog.json",
            max_bytes=5,
        )


@pytest.mark.parametrize(
    ("revision", "path"),
    [("HEAD", "app/data/catalog.json"), (SHA_A, "../catalog.json")],
)
def test_read_bounded_immutable_text_requires_full_sha_and_safe_path(
    tmp_path: Path,
    revision: str,
    path: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    runner.calls.clear()

    with pytest.raises(RepositorySafetyError):
        repository.read_bounded_immutable_text(
            revision,
            path,
            max_bytes=5,
        )

    assert runner.calls == []


def test_current_head_returns_one_verified_commit_sha(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[_completed(stdout=f"{SHA_B}\n")],
    )
    repository = GitRepository(root, runner=runner)

    assert repository.current_head() == SHA_B
    assert runner.calls[-1] == ("git", "rev-parse", "--verify", "HEAD")


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


def test_verify_validation_base_requires_clean_exact_head_and_regular_files(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    _write_validation_base_files(root)
    repository = GitRepository(root, runner=_validation_runner(root))

    repository.verify_validation_base("d" * 40)


@pytest.mark.parametrize(
    ("head", "status", "match"),
    [
        ("e" * 40, "", "exact prepared base head"),
        ("d" * 40, "?? untracked\0", "fully clean"),
    ],
)
def test_verify_validation_base_rejects_stale_or_dirty_checkout(
    tmp_path: Path,
    head: str,
    status: str,
    match: str,
) -> None:
    root = tmp_path.resolve()
    _write_validation_base_files(root)
    repository = GitRepository(
        root,
        runner=_validation_runner(root, head=head, status=status),
    )

    with pytest.raises(RepositorySafetyError, match=match):
        repository.verify_validation_base("d" * 40)


@pytest.mark.parametrize("unsafe_kind", ["missing", "symlink", "directory"])
def test_verify_validation_base_rejects_unsafe_required_file(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    root = tmp_path.resolve()
    _write_validation_base_files(root)
    catalog = root / "app/data/catalog.json"
    if unsafe_kind == "missing":
        catalog.unlink()
    elif unsafe_kind == "symlink":
        target = root / "catalog-target.json"
        target.write_text("{}", encoding="utf-8")
        catalog.unlink()
        catalog.symlink_to(target)
    else:
        catalog.unlink()
        catalog.mkdir()
    repository = GitRepository(root, runner=_validation_runner(root))

    with pytest.raises(RepositorySafetyError, match="regular non-symlink file"):
        repository.verify_validation_base("d" * 40)


@pytest.mark.parametrize("lifecycle_state", ["CLOSED", "MERGED"])
def test_guarded_sync_rejects_nonopen_pr_before_mutation(
    tmp_path: Path,
    lifecycle_state: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    calls_before = list(runner.calls)

    with pytest.raises(RepositorySafetyError, match="PR must be open"):
        repository.prepare_guarded_sync(_pull_request(lifecycle_state=lifecycle_state))

    assert runner.calls == calls_before


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


def test_repository_rejects_effective_fetch_rewrite_to_local_remote(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        remote=CANONICAL_REMOTE,
        effective_fetch_urls=(f"file://{tmp_path}/remote.git",),
    )

    with pytest.raises(RepositorySafetyError, match="effective origin"):
        GitRepository(root, runner=runner)


def test_repository_rejects_effective_pushurl_to_wrong_repository(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        effective_push_urls=("git@github.com:other/other.git",),
    )

    with pytest.raises(RepositorySafetyError, match="effective origin"):
        GitRepository(root, runner=runner)


def test_fetch_reverifies_effective_remote_before_network(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)
    runner.effective_fetch_urls = (f"file://{tmp_path}/attacker.git",)
    initial_calls = len(runner.calls)

    with pytest.raises(RepositorySafetyError, match="effective origin"):
        repository.fetch_for_pr("codex/alpha")

    assert not any(call[1:2] == ("fetch",) for call in runner.calls[initial_calls:])


def test_repository_rejects_multiple_effective_push_urls(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        effective_push_urls=(CANONICAL_REMOTE, CANONICAL_REMOTE),
    )

    with pytest.raises(RepositorySafetyError, match="exactly one effective"):
        GitRepository(root, runner=runner)


def test_ssh_alias_must_resolve_to_github_as_git_without_leaking_config(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        remote="git@github.com-lampss:lampssy/ai-sports-travel-planner.git",
        ssh_hostname="mirror.example.test",
    )

    with pytest.raises(RepositorySafetyError, match="SSH endpoint") as exc:
        GitRepository(root, runner=runner)

    assert "/secret/must-not-leak" not in str(exc.value)


def test_canonical_ssh_remote_preserves_explicit_git_user_for_resolution(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root, remote=CANONICAL_REMOTE)

    GitRepository(root, runner=runner)

    assert ("ssh", "-G", "-l", "git", "github.com") in runner.calls


def test_default_runner_sets_noninteractive_environment_and_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    _SubprocessRunner().run(
        ("git", "fetch", "origin"),
        cwd=tmp_path,
        timeout=37.0,
    )

    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_ASKPASS"] == "/usr/bin/false"
    assert environment["SSH_ASKPASS"] == "/usr/bin/false"
    assert environment["GCM_INTERACTIVE"] == "Never"
    assert "BatchMode=yes" in environment["GIT_SSH_COMMAND"]
    assert "StrictHostKeyChecking=yes" in environment["GIT_SSH_COMMAND"]
    assert captured["timeout"] == 37.0
    assert captured["shell"] is False


class TimeoutRunner(FakeRunner):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float = 10.0,
    ) -> subprocess.CompletedProcess[str]:
        call = tuple(argv)
        if call[1:2] == ("fetch",):
            raise subprocess.TimeoutExpired(
                cmd=["git", "fetch", "https://token@example.test/private"],
                timeout=timeout,
            )
        return super().run(argv, cwd=cwd, timeout=timeout)


def test_network_timeout_is_bounded_typed_and_sanitized(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    repository = GitRepository(root, runner=TimeoutRunner(root))

    with pytest.raises(GitOperationTimeoutError, match="network Git operation") as exc:
        repository.fetch_for_pr("codex/alpha")

    assert "token" not in str(exc.value)
    assert "example.test" not in str(exc.value)
    assert exc.value.__cause__ is None


@dataclass(frozen=True)
class ExactTestRemotePolicy(RemotePolicy):
    expected_url: str

    def validate(
        self,
        fetch_urls: tuple[str, ...],
        push_urls: tuple[str, ...],
        *,
        resolve_ssh: object,
    ) -> None:
        del resolve_ssh
        if fetch_urls != (self.expected_url,) or push_urls != (self.expected_url,):
            raise RepositorySafetyError("test remote does not match injected policy")


@dataclass
class RecordingRunner:
    fail_rebase_without_state: bool = False
    timeout_after_rebase_state: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)
    delegate: _SubprocessRunner = field(default_factory=_SubprocessRunner)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        call = tuple(argv)
        self.calls.append(call)
        if (
            self.fail_rebase_without_state
            and "rebase" in call
            and "--abort" not in call
        ):
            return subprocess.CompletedProcess(call, 128, "", "sanitized failure")
        result = self.delegate.run(argv, cwd=cwd, timeout=timeout)
        if (
            self.timeout_after_rebase_state
            and "rebase" in call
            and "--abort" not in call
            and result.returncode != 0
        ):
            raise subprocess.TimeoutExpired(cmd=list(call), timeout=timeout)
        return result


@dataclass
class RaceCreatingRunner(RecordingRunner):
    remote: Path | None = None
    branch: str = "codex/discovery-race"
    raced_head: str = SHA_A

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        call = tuple(argv)
        if call[1:2] == ("push",) and self.remote is not None:
            _git(
                self.remote,
                "update-ref",
                f"refs/heads/{self.branch}",
                self.raced_head,
            )
        return super().run(argv, cwd=cwd, timeout=timeout)


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


@pytest.mark.parametrize(
    "branch",
    [
        "codex/.hidden",
        "codex/.",
        "codex/..",
        "codex/topic.lock",
        "codex/topic.",
        "codex/topic/",
        "codex/topic..next",
        "codex/topic@{1}",
        "codex/topic with space",
        "codex/topic\x01control",
        "codex/-leading-dash",
    ],
)
def test_git_invalid_target_refs_are_rejected_before_fetch(
    tmp_path: Path,
    branch: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)

    with pytest.raises(RepositorySafetyError, match="target branch"):
        repository.fetch_for_pr(branch)

    assert not any(call[1:2] == ("fetch",) for call in runner.calls)


@pytest.mark.parametrize(
    "branch",
    [
        "codex/catalog/alpha",
        "codex/catalog-curation/alpha-v2",
        "codex/topic_1/sub.topic",
    ],
)
def test_valid_nested_codex_refs_pass_git_ref_format_before_fetch(
    tmp_path: Path,
    branch: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root)
    repository = GitRepository(root, runner=runner)

    repository.fetch_for_pr(branch)

    check_call = ("git", "check-ref-format", "--branch", branch)
    fetch_call = (
        "git",
        "fetch",
        "--no-tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
    )
    assert check_call in runner.calls
    assert runner.calls.index(check_call) < runner.calls.index(fetch_call)


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


def test_optional_remote_head_returns_none_only_for_absent_ref(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[subprocess.CompletedProcess((), 0, "", "")],
    )
    repository = GitRepository(root, runner=runner)

    assert repository.optional_remote_head("codex/discovery-alpha") is None


def test_optional_remote_head_returns_one_exact_present_ref(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    repository = GitRepository(
        root,
        runner=FakeRunner(
            root,
            responses=[
                _completed(stdout=(f"{SHA_A}\trefs/heads/codex/discovery-alpha\n"))
            ],
        ),
    )

    assert repository.optional_remote_head("codex/discovery-alpha") == SHA_A


@pytest.mark.parametrize(
    "stdout",
    [
        f"{SHA_A}\trefs/heads/codex/discovery-alpha\n"
        f"{SHA_B}\trefs/heads/codex/discovery-alpha\n",
        f"{'A' * 40}\trefs/heads/codex/discovery-alpha\n",
        f"{SHA_A}\trefs/heads/codex/other\n",
    ],
)
def test_optional_remote_head_rejects_nonempty_malformed_results(
    tmp_path: Path,
    stdout: str,
) -> None:
    root = tmp_path.resolve()
    repository = GitRepository(
        root,
        runner=FakeRunner(
            root,
            responses=[subprocess.CompletedProcess((), 0, stdout, "")],
        ),
    )

    with pytest.raises(RepositorySafetyError, match="remote head"):
        repository.optional_remote_head("codex/discovery-alpha")


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


@pytest.mark.parametrize("operation", ["fetch", "fetch-main", "ls-remote"])
@pytest.mark.parametrize(
    ("stderr", "error_type", "message"),
    [
        (
            "git@github.com: Permission denied (publickey).",
            GitAuthenticationError,
            "authentication",
        ),
        (
            "remote: Repository not found for https://secret@example.test",
            GitRemotePolicyError,
            "remote policy",
        ),
        (
            "fatal: unable to access https://secret@example.test: "
            "Could not resolve host",
            GitTransportError,
            "transport",
        ),
    ],
)
def test_fetch_and_remote_head_failures_are_typed_and_sanitized(
    tmp_path: Path,
    operation: str,
    stderr: str,
    error_type: type[Exception],
    message: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[subprocess.CompletedProcess((), 128, "", stderr)],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(error_type, match=message) as exc:
        if operation == "fetch":
            repository.fetch_for_pr("codex/alpha")
        elif operation == "fetch-main":
            repository.fetch_main()
        else:
            repository.remote_head("codex/alpha")

    assert "secret" not in str(exc.value)
    assert "example.test" not in str(exc.value)


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


def test_fetch_main_uses_only_the_exact_main_refspec_and_returns_its_head(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            _completed(),
            _completed(stdout=f"{SHA_A}\n"),
        ],
    )
    repository = GitRepository(root, runner=runner)
    runner.calls.clear()

    head = repository.fetch_main()

    assert head == SHA_A
    assert runner.calls[-2:] == [
        (
            "git",
            "fetch",
            "--no-tags",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
        ),
        ("git", "rev-parse", "--verify", "refs/remotes/origin/main"),
    ]


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
            subprocess.CompletedProcess((), 0, f"{SHA_A}\n", ""),
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

    assert repository.create_backup_ref(42, SHA_A) == backup_ref
    assert all("delete" not in call for call in runner.calls)


def test_backup_ref_collision_with_different_sha_fails_closed(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            subprocess.CompletedProcess((), 128, "", "reference already exists"),
            subprocess.CompletedProcess((), 0, f"{SHA_B}\n", ""),
        ],
    )
    repository = GitRepository(
        root,
        runner=runner,
        now=lambda: datetime(2026, 7, 8, 10, tzinfo=UTC),
    )

    with pytest.raises(RepositorySafetyError, match="backup ref collision"):
        repository.create_backup_ref(42, SHA_A)

    assert all("delete" not in call for call in runner.calls)


def test_push_with_lease_uses_exact_lease_and_never_plain_force(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=_push_responses(),
    )
    repository = GitRepository(root, runner=runner)

    repository.push_with_lease(_result(), SHA_B)

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


def test_create_only_push_uses_empty_expected_lease_and_normal_refspec(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            _completed(stdout=f"{SHA_B}\n"),
            _completed(stdout=""),
            _completed(),
        ],
    )
    repository = GitRepository(root, runner=runner)

    repository.push_create_only("codex/discovery-alpha", SHA_B)

    push_calls = [call for call in runner.calls if call[1:2] == ("push",)]
    assert push_calls == [
        (
            "git",
            "push",
            "--force-with-lease=refs/heads/codex/discovery-alpha:",
            "origin",
            "HEAD:refs/heads/codex/discovery-alpha",
        )
    ]
    assert "--force" not in push_calls[0]


def test_create_only_push_rejects_occupied_ref_before_push(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            _completed(stdout=f"{SHA_B}\n"),
            _completed(stdout=(f"{SHA_A}\trefs/heads/codex/discovery-alpha\n")),
        ],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(StaleRemoteHeadError, match="already exists"):
        repository.push_create_only("codex/discovery-alpha", SHA_B)

    assert not any(call[1:2] == ("push",) for call in runner.calls)


@pytest.mark.parametrize(
    ("branch", "reviewed_head", "current_head", "message"),
    [
        ("main", SHA_B, SHA_B, "target branch"),
        ("codex/discovery-alpha", SHA_B, SHA_A, "current HEAD"),
    ],
)
def test_create_only_push_rejects_unsafe_branch_or_noncurrent_reviewed_head(
    tmp_path: Path,
    branch: str,
    reviewed_head: str,
    current_head: str,
    message: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[_completed(stdout=f"{current_head}\n")],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(RepositorySafetyError, match=message):
        repository.push_create_only(branch, reviewed_head)

    assert not any(call[1:2] in {("ls-remote",), ("push",)} for call in runner.calls)


@pytest.mark.parametrize(
    ("stderr", "error_type", "message"),
    [
        (
            "! [rejected] HEAD -> codex/discovery-alpha (stale info)",
            StaleRemoteHeadError,
            "lease",
        ),
        (
            "fatal: unable to access 'https://secret-token@example.test': failure",
            GitTransportError,
            "transport",
        ),
    ],
)
def test_create_only_push_race_or_transport_failure_is_sanitized(
    tmp_path: Path,
    stderr: str,
    error_type: type[Exception],
    message: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=[
            _completed(stdout=f"{SHA_B}\n"),
            _completed(stdout=""),
            subprocess.CompletedProcess((), 1, "", stderr),
        ],
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(error_type, match=message) as exc_info:
        repository.push_create_only("codex/discovery-alpha", SHA_B)

    assert "secret-token" not in str(exc_info.value)
    assert len([call for call in runner.calls if call[1:2] == ("push",)]) == 1


def test_stale_remote_head_blocks_push_before_any_push_invocation(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=_push_responses(remote_sha=SHA_B),
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(StaleRemoteHeadError, match=f"expected {SHA_A}.*{SHA_B}"):
        repository.push_with_lease(_result(), SHA_B)

    assert not any(call[1:2] == ("push",) for call in runner.calls)


@pytest.mark.parametrize(
    ("stderr", "error_type", "message"),
    [
        (
            "git@github.com: Permission denied (publickey).",
            GitAuthenticationError,
            "authentication",
        ),
        (
            "! [rejected] HEAD -> codex/alpha (stale info)",
            StaleRemoteHeadError,
            "lease",
        ),
        (
            "fatal: unable to access 'https://secret-token@example.test': "
            "Could not resolve host",
            GitTransportError,
            "transport",
        ),
        (
            "! [remote rejected] HEAD -> codex/alpha (policy)",
            GitPushRejectedError,
            "rejected",
        ),
    ],
)
def test_push_failure_preserves_sanitized_failure_classification(
    tmp_path: Path,
    stderr: str,
    error_type: type[Exception],
    message: str,
) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(
        root,
        responses=_push_responses(push_returncode=1, push_stderr=stderr),
    )
    repository = GitRepository(root, runner=runner)

    with pytest.raises(error_type, match=message) as exc:
        repository.push_with_lease(_result(), SHA_B)

    assert "secret-token" not in str(exc.value)
    assert "identityfile" not in str(exc.value)


def test_push_reverifies_origin_before_remote_head_or_push(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    runner = FakeRunner(root, responses=_push_responses()[:3])
    repository = GitRepository(root, runner=runner)
    runner.remote = "git@github.com:other/ai-sports-travel-planner.git"
    initial_calls = len(runner.calls)

    with pytest.raises(RepositorySafetyError, match="origin must be"):
        repository.push_with_lease(_result(), SHA_B)

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


def _catalog(
    *,
    alpha_name: str | None = None,
    beta_name: str | None = None,
) -> str:
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
    ski_areas = []
    if alpha_name is not None:
        ski_areas.append({"ski_area_id": "alpha", "name": alpha_name})
    if beta_name is not None:
        ski_areas.append({"ski_area_id": "beta", "name": beta_name})
    payload["ski_areas"] = ski_areas
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
    base_catalog: str = _catalog(),
    target_catalog: str = _catalog(alpha_name="Target Alpha"),
    base_trust_manifest: str | None = None,
    target_trust_manifest: str | None = None,
    main_catalog: str | None = None,
    target_report: str | None = None,
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
    (seed / CATALOG_PATH).write_text(
        base_catalog,
        encoding="utf-8",
    )
    if base_trust_manifest is not None:
        (seed / TRUST_MANIFEST_PATH).write_text(
            base_trust_manifest,
            encoding="utf-8",
        )
    (seed / "README.md").write_text("base\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", "base")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "origin", "main")

    _git(seed, "switch", "-c", "codex/catalog-curation-alpha")
    target_paths: list[str] = []
    if target_catalog != base_catalog:
        (seed / CATALOG_PATH).write_text(target_catalog, encoding="utf-8")
        target_paths.append(CATALOG_PATH)
    if target_trust_manifest is not None:
        (seed / TRUST_MANIFEST_PATH).write_text(
            target_trust_manifest,
            encoding="utf-8",
        )
        if target_trust_manifest != base_trust_manifest:
            target_paths.append(TRUST_MANIFEST_PATH)
    if target_report is not None:
        (seed / "docs" / "catalog-curation").mkdir(parents=True)
        (seed / REPORT_PATH).write_text(target_report, encoding="utf-8")
        target_paths.append(REPORT_PATH)
    _git(seed, "add", *target_paths)
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
    pull_request = _pull_request(
        head_sha=target_sha,
        changed_paths=frozenset(target_paths),
    )
    return LocalRepository(remote, checkout, target_sha, main_sha, pull_request)


def _integration_repository(
    local: LocalRepository,
    *,
    root: Path | None = None,
    runner: RecordingRunner | None = None,
) -> GitRepository:
    effective_url = f"file://{local.remote}"
    return GitRepository(
        (root or local.checkout).resolve(),
        runner=runner,
        now=lambda: datetime(2026, 7, 8, 10, tzinfo=UTC),
        remote_policy=ExactTestRemotePolicy(effective_url),
    )


def test_default_remote_policy_rejects_local_integration_transport(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)

    with pytest.raises(RepositorySafetyError, match="effective origin"):
        GitRepository(local.checkout.resolve())


def test_verify_immutable_diff_requires_commit_ancestry_and_builds_intent(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    base = _git(local.checkout, "merge-base", local.target_sha, local.main_sha)

    snapshot = repository.verify_immutable_diff(base, local.target_sha)

    assert snapshot.catalog_targets == frozenset({"ski_area:alpha"})
    with pytest.raises(RepositorySafetyError, match="ancestor"):
        repository.verify_immutable_diff(local.main_sha, local.target_sha)


def test_v2_git_entry_points_build_prepare_and_revalidate_objective_intent(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    base = _git(local.checkout, "merge-base", local.target_sha, local.main_sha)

    immutable = repository.verify_immutable_diff(base, local.target_sha)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    reviewed = repository.revalidate_prepared_result(
        local.pull_request,
        prepared,
        prepared.rebased_head,
    )

    assert isinstance(immutable, IntentSnapshot)
    assert isinstance(reviewed, IntentSnapshot)
    assert immutable.catalog_targets == frozenset({"ski_area:alpha"})
    assert reviewed.catalog_targets == immutable.catalog_targets
    assert reviewed.changed_paths == immutable.changed_paths


def test_reviewed_checkpoint_creates_exact_reviewed_and_squash_refs(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)

    refs = repository.checkpoint_reviewed_continuation(
        local.pull_request,
        prepared,
        prepared.rebased_head,
    )

    assert isinstance(refs, ReviewedCheckpointRefs)
    assert _git(local.checkout, "rev-parse", refs.reviewed_ref) == prepared.rebased_head
    assert (
        _git(local.checkout, "rev-parse", f"{refs.squash_ref}^") == prepared.base_head
    )
    assert _git(local.checkout, "show", "-s", "--format=%T", refs.squash_ref) == _git(
        local.checkout, "show", "-s", "--format=%T", prepared.rebased_head
    )


def test_reviewed_checkpoint_rejects_dirty_or_non_descendant_head(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    (local.checkout / "untracked.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(RepositorySafetyError, match="clean"):
        repository.checkpoint_reviewed_continuation(
            local.pull_request,
            prepared,
            prepared.rebased_head,
        )

    (local.checkout / "untracked.txt").unlink()
    _git(local.checkout, "switch", "--detach", prepared.base_head)
    with pytest.raises(RepositorySafetyError, match="descend"):
        repository.checkpoint_reviewed_continuation(
            local.pull_request,
            prepared,
            prepared.base_head,
        )


def test_continuation_replay_restores_unchanged_reviewed_head(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    refs = repository.checkpoint_reviewed_continuation(
        local.pull_request, prepared, prepared.rebased_head
    )
    _git(local.checkout, "switch", "--detach", local.target_sha)

    replay = repository.prepare_reviewed_continuation(
        local.pull_request,
        prepared,
        prepared.rebased_head,
        refs,
    )

    assert replay == ContinuationReplayResult(
        result="unchanged",
        base_head=prepared.base_head,
        head=prepared.rebased_head,
        sync=prepared,
    )
    assert _git(local.checkout, "rev-parse", "HEAD") == prepared.rebased_head


def test_continuation_replay_squashes_onto_advanced_main(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    refs = repository.checkpoint_reviewed_continuation(
        local.pull_request, prepared, prepared.rebased_head
    )
    seed = tmp_path / "seed"
    _git(seed, "switch", "main")
    (seed / "README.md").write_text("base\nmain update\nagain\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "advance main again")
    _git(seed, "push", "origin", "main")
    advanced_main = _git(seed, "rev-parse", "HEAD")

    replay = repository.prepare_reviewed_continuation(
        local.pull_request,
        prepared,
        prepared.rebased_head,
        refs,
    )

    assert replay.result == "prepared"
    assert replay.base_head == advanced_main
    assert replay.head is not None
    assert replay.sync is not None
    assert _git(local.checkout, "rev-parse", f"{replay.head}^") == advanced_main
    assert _git(local.checkout, "show", f"{replay.head}:app/data/catalog.json") == (
        _catalog(alpha_name="Target Alpha").strip()
    )


def test_continuation_replay_rejects_rewritten_main_history(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    refs = repository.checkpoint_reviewed_continuation(
        local.pull_request, prepared, prepared.rebased_head
    )
    _git(
        local.remote,
        "update-ref",
        "refs/heads/main",
        local.target_sha,
        local.main_sha,
    )

    with pytest.raises(RepositorySafetyError, match="main must descend"):
        repository.prepare_reviewed_continuation(
            local.pull_request,
            prepared,
            prepared.rebased_head,
            refs,
        )


def test_continuation_replay_returns_one_allowed_conflict_and_completes_it(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    refs = repository.checkpoint_reviewed_continuation(
        local.pull_request, prepared, prepared.rebased_head
    )
    seed = tmp_path / "seed"
    _git(seed, "switch", "main")
    (seed / "app/data/catalog.json").write_text(
        _catalog(alpha_name="Main Alpha"), encoding="utf-8"
    )
    _git(seed, "add", "app/data/catalog.json")
    _git(seed, "commit", "-m", "change alpha on main")
    _git(seed, "push", "origin", "main")
    advanced_main = _git(seed, "rev-parse", "HEAD")

    replay = repository.prepare_reviewed_continuation(
        local.pull_request,
        prepared,
        prepared.rebased_head,
        refs,
    )

    assert replay.result == "conflict"
    assert replay.base_head == advanced_main
    assert replay.conflict_paths == ("app/data/catalog.json",)
    (local.checkout / "app/data/catalog.json").write_text(
        _catalog(alpha_name="Target Alpha"), encoding="utf-8"
    )
    _git(local.checkout, "add", "app/data/catalog.json")
    completed = repository.continue_reviewed_conflict(
        local.pull_request,
        prepared,
        prepared.rebased_head,
        refs,
    )

    assert completed.result == "prepared"
    assert completed.sync is not None
    assert completed.sync.base_head == advanced_main
    assert _git(local.checkout, "status", "--porcelain") == ""


def test_continuation_conflict_rejects_unrelated_staged_path_and_cleans_up(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    refs = repository.checkpoint_reviewed_continuation(
        local.pull_request, prepared, prepared.rebased_head
    )
    seed = tmp_path / "seed"
    _git(seed, "switch", "main")
    (seed / "app/data/catalog.json").write_text(
        _catalog(alpha_name="Main Alpha"), encoding="utf-8"
    )
    _git(seed, "add", "app/data/catalog.json")
    _git(seed, "commit", "-m", "change alpha on main")
    _git(seed, "push", "origin", "main")
    replay = repository.prepare_reviewed_continuation(
        local.pull_request, prepared, prepared.rebased_head, refs
    )
    assert replay.result == "conflict"
    (local.checkout / "app/data/catalog.json").write_text(
        _catalog(alpha_name="Target Alpha"), encoding="utf-8"
    )
    (local.checkout / "README.md").write_text("unauthorized\n", encoding="utf-8")
    _git(local.checkout, "add", "app/data/catalog.json", "README.md")

    with pytest.raises(RepositorySafetyError, match="outside reviewed scope"):
        repository.continue_reviewed_conflict(
            local.pull_request, prepared, prepared.rebased_head, refs
        )

    assert _git(local.checkout, "status", "--porcelain") == ""


def test_prepare_accepts_unrelated_catalog_changes_on_main(tmp_path: Path) -> None:
    base_catalog = _catalog(alpha_name="Base Alpha", beta_name="Base Beta")
    local = _local_repository(
        tmp_path,
        base_catalog=base_catalog,
        target_catalog=_catalog(alpha_name="Target Alpha", beta_name="Base Beta"),
        main_catalog=_catalog(alpha_name="Base Alpha", beta_name="Main Beta"),
    )
    repository = _integration_repository(local)

    prepared = repository.prepare_guarded_sync(local.pull_request)
    reviewed = repository.revalidate_prepared_result(
        local.pull_request,
        prepared,
        prepared.rebased_head,
    )

    assert reviewed.catalog_targets == frozenset({"ski_area:alpha"})


def test_revalidate_allows_safe_non_production_scope_expansion(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    prepared = repository.prepare_guarded_sync(local.pull_request)
    test_path = "tests/test_catalog_alpha.py"
    (local.checkout / "tests").mkdir()
    (local.checkout / test_path).write_text(
        "def test_alpha_catalog_entry():\n    assert True\n",
        encoding="utf-8",
    )
    _git(local.checkout, "add", test_path)
    _git(local.checkout, "commit", "-m", "add catalog regression test")
    reviewed_head = _git(local.checkout, "rev-parse", "HEAD")

    reviewed = repository.revalidate_prepared_result(
        local.pull_request,
        prepared,
        reviewed_head,
    )

    assert test_path in reviewed.changed_paths


def test_prepare_and_revalidate_accept_legacy_report_as_input(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    prepared_catalog = (project_root / CATALOG_PATH).read_text(encoding="utf-8")
    prepared_trust = (project_root / TRUST_MANIFEST_PATH).read_text(encoding="utf-8")
    destination = json.loads(prepared_catalog)["stay_destinations"][0]
    destination_id = destination["stay_destination_id"]
    destination_name = destination["name"]
    legacy_report = json.dumps(
        {
            "report_schema_version": 1,
            "title": "Legacy Alpha report",
            "summary": "Predates the canonical report contract.",
            "reviewed_targets": [],
        },
        indent=2,
    )
    local = _local_repository(
        tmp_path,
        base_catalog=prepared_catalog,
        target_catalog=prepared_catalog,
        base_trust_manifest=prepared_trust,
        target_trust_manifest=prepared_trust,
        target_report=legacy_report,
    )
    repository = _integration_repository(local)

    prepared = repository.prepare_guarded_sync(local.pull_request)
    normalized_report = {
        "report_schema_version": 3,
        "title": "Normalized destination report",
        "summary": "Rebuilds the legacy input before independent review.",
        "resulting_graph": {"focus_stay_destination_ids": [destination_id]},
        "reviewed_targets": [
            {
                "target_type": "stay_destination",
                "target_id": destination_id,
                "scope": "narrow",
                "required_field_paths": ["name"],
            }
        ],
        "entity_scope_assessments": [
            {
                "candidate_id": destination_id,
                "candidate_name": destination_name,
                "candidate_kind": "stay_destination",
                "disposition": "represented",
                "signals": ["independent_stay_market"],
                "evidence_refs": ["destination-scope"],
                "target_refs": [
                    {
                        "target_type": "stay_destination",
                        "target_id": destination_id,
                    }
                ],
                "rationale": "Official evidence confirms the represented stay market.",
            }
        ],
        "evidence": [
            {
                "evidence_id": "destination-scope",
                "boundary_target_ids": [destination_id],
                "target_type": "stay_destination",
                "target_id": destination_id,
                "field_path": "name",
                "source_type": "official",
                "source_url": "https://example.com/destination",
                "source_title": "Official destination market",
                "source_value": destination_name,
                "evidence_summary": "Confirms the independent stay market.",
            }
        ],
        "field_coverage": [
            {
                "target_type": "stay_destination",
                "target_id": destination_id,
                "field_path": "name",
                "status": "reviewed-no-change",
            }
        ],
        "destination_boundary_assessments": [
            {
                "candidate_id": destination_id,
                "gates": [
                    {
                        "gate_name": gate_name,
                        "status": "pass",
                        "notes": "The official source supports this stay-market gate.",
                        "evidence_refs": ["destination-scope"],
                    }
                    for gate_name in (
                        "complete_stay_market_scope",
                        "independent_stay_market_ownership",
                        "material_destination_level_separation_value",
                    )
                ],
                "identity_signals": [
                    {
                        "signal_type": "official_stay_market_treatment",
                        "status": "pass",
                        "notes": "The official source owns the stay market.",
                        "evidence_refs": ["destination-scope"],
                    }
                ],
            }
        ],
        "boundary_decision_targets": [destination_id],
    }
    (local.checkout / REPORT_PATH).write_text(
        json.dumps(normalized_report, indent=2),
        encoding="utf-8",
    )
    _git(local.checkout, "add", REPORT_PATH)
    _git(local.checkout, "commit", "-m", "normalize curation report")
    reviewed_head = _git(local.checkout, "rev-parse", "HEAD")
    assert _git(
        local.checkout,
        "diff",
        "--name-only",
        prepared.rebased_head,
        reviewed_head,
    ).splitlines() == [REPORT_PATH]
    for snapshot_path in (CATALOG_PATH, TRUST_MANIFEST_PATH):
        assert _git(
            local.checkout,
            "rev-parse",
            f"{prepared.rebased_head}:{snapshot_path}",
        ) == _git(
            local.checkout,
            "rev-parse",
            f"{reviewed_head}:{snapshot_path}",
        )
    reviewed = repository.revalidate_prepared_result(
        local.pull_request,
        prepared,
        reviewed_head,
    )
    canonical = build_intent_snapshot(
        repository,
        prepared.base_head,
        reviewed_head,
    )
    report = CatalogCurationReport.model_validate(normalized_report)
    validate_catalog_curation_report(
        report,
        require_resulting_graph=True,
        require_current_destination_policy=True,
    )
    base_catalog_path = tmp_path / "prepared-base-catalog.json"
    current_catalog_path = tmp_path / "prepared-current-catalog.json"
    base_trust_path = tmp_path / "prepared-base-trust.json"
    current_trust_path = tmp_path / "prepared-current-trust.json"
    for snapshot_path, revision, source_path in (
        (base_catalog_path, prepared.base_head, CATALOG_PATH),
        (current_catalog_path, prepared.rebased_head, CATALOG_PATH),
        (base_trust_path, prepared.base_head, TRUST_MANIFEST_PATH),
        (current_trust_path, prepared.rebased_head, TRUST_MANIFEST_PATH),
    ):
        snapshot_path.write_text(
            _git(local.checkout, "show", f"{revision}:{source_path}") + "\n",
            encoding="utf-8",
        )
    validate_catalog_resulting_graph(
        report,
        load_catalog_from_path(current_catalog_path),
        require=True,
    )
    reconciliation = reconcile_catalog_curation_report(
        report,
        base_catalog_path=base_catalog_path,
        current_catalog_path=current_catalog_path,
        base_trust_manifest_path=base_trust_path,
        current_trust_manifest_path=current_trust_path,
    )

    assert REPORT_PATH in reviewed.changed_paths
    assert reviewed.catalog_targets == frozenset()
    assert reviewed.report_targets == frozenset()
    assert canonical.report_targets == frozenset({f"stay_destination:{destination_id}"})
    assert reconciliation.delta_count == 0


def test_create_only_push_creates_absent_discovery_branch(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    branch = "codex/discovery-alpha"
    repository = _integration_repository(local)

    repository.push_create_only(branch, local.main_sha)

    assert _git(local.remote, "rev-parse", f"refs/heads/{branch}") == local.main_sha


def test_create_only_push_rejects_toctou_ref_without_overwriting_it(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    runner = RaceCreatingRunner(
        remote=local.remote,
        raced_head=local.target_sha,
    )
    repository = _integration_repository(local, runner=runner)

    with pytest.raises(StaleRemoteHeadError, match="lease"):
        repository.push_create_only(runner.branch, local.main_sha)

    assert (
        _git(local.remote, "rev-parse", f"refs/heads/{runner.branch}")
        == local.target_sha
    )
    assert len([call for call in runner.calls if call[1:2] == ("push",)]) == 1


def test_prepare_rejects_tracked_worktree_dirt_before_fetch(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    (local.checkout / "README.md").write_text("dirty tracked\n", encoding="utf-8")
    runner = RecordingRunner()
    repository = _integration_repository(local, runner=runner)

    with pytest.raises(RepositorySafetyError, match="fully clean"):
        repository.prepare_guarded_sync(local.pull_request)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )
    assert not any(call[1:2] == ("fetch",) for call in runner.calls)


def test_prepare_rejects_untracked_worktree_dirt_before_fetch(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    (local.checkout / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    runner = RecordingRunner()
    repository = _integration_repository(local, runner=runner)

    with pytest.raises(RepositorySafetyError, match="fully clean"):
        repository.prepare_guarded_sync(local.pull_request)

    assert not any(call[1:2] == ("fetch",) for call in runner.calls)


def test_prepare_allows_ignored_cache_and_pins_rebase_safety_config(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    exclude_path = Path(_git(local.checkout, "rev-parse", "--git-path", "info/exclude"))
    if not exclude_path.is_absolute():
        exclude_path = local.checkout / exclude_path
    exclude_path.write_text(".uv-cache/\n", encoding="utf-8")
    cache = local.checkout / ".uv-cache" / "state"
    cache.parent.mkdir()
    cache.write_text("ignored\n", encoding="utf-8")
    runner = RecordingRunner()
    repository = _integration_repository(local, runner=runner)

    repository.prepare_guarded_sync(local.pull_request)

    rebase_calls = [call for call in runner.calls if "rebase" in call]
    assert rebase_calls == [
        (
            "git",
            "-c",
            "rebase.autoStash=false",
            "-c",
            "rebase.updateRefs=false",
            "rebase",
            "refs/remotes/origin/main",
        )
    ]


def test_prepare_rejects_preexisting_rebase_state(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    rebase_path = Path(_git(local.checkout, "rev-parse", "--git-path", "rebase-merge"))
    if not rebase_path.is_absolute():
        rebase_path = local.checkout / rebase_path
    rebase_path.mkdir(parents=True)
    repository = _integration_repository(local)

    with pytest.raises(RepositorySafetyError, match="pre-existing rebase"):
        repository.prepare_guarded_sync(local.pull_request)


def test_non_conflict_rebase_failure_is_not_aborted_or_mislabeled(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    runner = RecordingRunner(fail_rebase_without_state=True)
    repository = _integration_repository(local, runner=runner)

    with pytest.raises(RepositorySafetyError, match="failed without active conflict"):
        repository.prepare_guarded_sync(local.pull_request)

    assert not any("--abort" in call for call in runner.calls)


def test_rebase_timeout_aborts_active_state_before_raising(tmp_path: Path) -> None:
    local = _local_repository(
        tmp_path,
        target_catalog=_catalog(alpha_name="Target Alpha"),
        main_catalog=_catalog(alpha_name="Main Alpha"),
    )
    runner = RecordingRunner(timeout_after_rebase_state=True)
    repository = _integration_repository(local, runner=runner)

    with pytest.raises(GitOperationTimeoutError, match="local Git"):
        repository.prepare_guarded_sync(local.pull_request)

    assert any("--abort" in call for call in runner.calls)
    for state_name in ("rebase-merge", "rebase-apply"):
        state_path = Path(_git(local.checkout, "rev-parse", "--git-path", state_name))
        if not state_path.is_absolute():
            state_path = local.checkout / state_path
        assert not state_path.exists()


def test_conflict_cleanup_uses_linked_worktree_git_state(tmp_path: Path) -> None:
    local = _local_repository(
        tmp_path,
        target_catalog=_catalog(alpha_name="Target Alpha"),
        main_catalog=_catalog(alpha_name="Main Alpha"),
    )
    linked = tmp_path / "maintainer-worktree"
    _git(local.checkout, "worktree", "add", "--detach", str(linked), "HEAD")
    repository = _integration_repository(local, root=linked)

    with pytest.raises(RebaseConflictError):
        repository.prepare_guarded_sync(local.pull_request)

    for state_name in ("rebase-merge", "rebase-apply"):
        state_path = Path(_git(linked, "rev-parse", "--git-path", state_name))
        if not state_path.is_absolute():
            state_path = linked / state_path
        assert not state_path.exists()


def test_guarded_prepare_rebases_detached_creates_backup_and_does_not_push(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)

    result = repository.prepare_guarded_sync(local.pull_request)

    assert result.target_branch == local.pull_request.head_ref_name
    assert result.original_head == local.target_sha
    assert result.base_head == local.main_sha
    assert result.rebased_head == _git(local.checkout, "rev-parse", "HEAD")
    assert result.rebased_head != result.original_head
    assert _git(local.checkout, "branch", "--show-current") == ""
    assert _git(local.checkout, "rev-parse", result.backup_ref) == local.target_sha
    assert _git(local.checkout, "rev-parse", result.prepared_ref) == result.rebased_head
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
        repository.push_with_lease(result, result.rebased_head)

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

    repository.push_with_lease(result, result.rebased_head)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == result.rebased_head
    )
    assert _git(local.remote, "rev-parse", "refs/heads/codex/other") == local.main_sha
    assert _git(local.remote, "rev-parse", "refs/heads/main") == local.main_sha


def test_push_blocks_when_head_changes_after_prepare(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    result = repository.prepare_guarded_sync(local.pull_request)
    _git(local.checkout, "switch", "--detach", local.main_sha)

    with pytest.raises(RepositorySafetyError, match="current HEAD.*reviewed"):
        repository.push_with_lease(result, result.rebased_head)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )


def test_push_blocks_when_backup_ref_is_tampered(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    result = repository.prepare_guarded_sync(local.pull_request)
    _git(local.checkout, "update-ref", result.backup_ref, local.main_sha)

    with pytest.raises(RepositorySafetyError, match="backup ref"):
        repository.push_with_lease(result, result.rebased_head)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )


def test_push_blocks_non_descendant_reviewed_head(tmp_path: Path) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    result = repository.prepare_guarded_sync(local.pull_request)
    _git(local.checkout, "switch", "--detach", local.main_sha)
    (local.checkout / "README.md").write_text(
        "base\nmain update\nsibling\n", encoding="utf-8"
    )
    _git(local.checkout, "add", "README.md")
    _git(local.checkout, "commit", "-m", "unrelated reviewed head")
    unrelated_head = _git(local.checkout, "rev-parse", "HEAD")

    with pytest.raises(RepositorySafetyError, match="descend from rebased head"):
        repository.push_with_lease(result, unrelated_head)


def test_push_allows_reviewed_remediation_descending_from_rebase(
    tmp_path: Path,
) -> None:
    local = _local_repository(tmp_path)
    repository = _integration_repository(local)
    result = repository.prepare_guarded_sync(local.pull_request)
    _git(local.checkout, "commit", "--allow-empty", "-m", "reviewed remediation")
    reviewed_head = _git(local.checkout, "rev-parse", "HEAD")

    repository.push_with_lease(result, reviewed_head)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == reviewed_head
    )


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

    with pytest.raises(IntentDriftError, match="rebased curation diff is empty"):
        repository.prepare_guarded_sync(local.pull_request)

    assert (
        _git(local.remote, "rev-parse", "refs/heads/codex/catalog-curation-alpha")
        == local.target_sha
    )

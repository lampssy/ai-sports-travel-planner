from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from ops.maintainer.intent import (
    IntentDriftError,
    build_intent_snapshot,
    compare_intent,
)
from ops.maintainer.models import PullRequest

__all__ = [
    "GitRepository",
    "GuardedSyncResult",
    "IntentDriftError",
    "RebaseConflictError",
    "RepositorySafetyError",
    "StaleRemoteHeadError",
]

REPOSITORY_OWNER = "lampssy"
REPOSITORY_NAME = "ai-sports-travel-planner"
BASE_BRANCH = "main"
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SAFE_BRANCH_CHARACTERS = re.compile(r"^[A-Za-z0-9._/-]+$")
_SCP_REMOTE = re.compile(
    r"^git@(?P<host>github\.com|github\.com-lampss):"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)


class RepositorySafetyError(RuntimeError):
    """The repository or requested Git operation violates the safety contract."""


class RebaseConflictError(RuntimeError):
    """A guarded rebase failed and was aborted without conflict resolution."""


class StaleRemoteHeadError(RuntimeError):
    """The target remote branch no longer matches the selected PR head."""


class GuardedSyncResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    target_branch: str
    original_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    rebased_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    backup_ref: str
    merge_base: str = Field(pattern=r"^[0-9a-f]{40}$")


class CommandRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]: ...


class _SubprocessRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_EDITOR": "true",
                "GIT_SEQUENCE_EDITOR": "true",
                "GIT_MERGE_AUTOEDIT": "no",
                "GIT_CONFIG_COUNT": "2",
                "GIT_CONFIG_KEY_0": "commit.gpgSign",
                "GIT_CONFIG_VALUE_0": "false",
                "GIT_CONFIG_KEY_1": "core.hooksPath",
                "GIT_CONFIG_VALUE_1": os.devnull,
            }
        )
        return subprocess.run(
            list(argv),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            env=environment,
        )


class GitRepository:
    """Narrow Git API for guarded maintainer synchronization."""

    def __init__(
        self,
        worktree_root: Path,
        *,
        runner: CommandRunner | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not worktree_root.is_absolute() or worktree_root != worktree_root.resolve():
            raise RepositorySafetyError(
                "resolved worktree root must be supplied as an absolute path"
            )
        self.root = worktree_root
        self._runner = runner or _SubprocessRunner()
        self._now = now or (lambda: datetime.now(UTC))
        self.verify_repository()

    def verify_repository(self) -> None:
        top_level = self._git("rev-parse", "--show-toplevel")
        if top_level.returncode != 0:
            raise RepositorySafetyError("configured worktree is not a Git repository")
        try:
            actual_root = Path(top_level.stdout.strip()).resolve()
        except (OSError, RuntimeError) as error:
            raise RepositorySafetyError("cannot resolve Git worktree root") from error
        if actual_root != self.root:
            raise RepositorySafetyError(
                "worktree root mismatch: "
                f"configured {self.root}, Git reported {actual_root}"
            )

        remote = self._git("config", "--get", "remote.origin.url")
        origin_url = remote.stdout.rstrip("\n")
        if remote.returncode != 0 or not _is_expected_remote(origin_url):
            raise RepositorySafetyError(
                "origin must be exactly lampssy/ai-sports-travel-planner on GitHub"
            )

    def remote_head(self, branch: str) -> str:
        self._validate_target_branch(branch)
        expected_ref = f"refs/heads/{branch}"
        result = self._git(
            "ls-remote",
            "--heads",
            "origin",
            expected_ref,
        )
        if result.returncode != 0:
            raise RepositorySafetyError("cannot read exact remote target head")
        parsed: list[str] = []
        for line in result.stdout.splitlines():
            fields = line.split("\t")
            if (
                len(fields) == 2
                and fields[1] == expected_ref
                and _SHA_PATTERN.fullmatch(fields[0]) is not None
            ):
                parsed.append(fields[0])
        if len(parsed) != 1 or len(result.stdout.splitlines()) != 1:
            raise RepositorySafetyError(
                f"expected exactly one remote head for {branch}"
            )
        return parsed[0]

    def fetch_for_pr(self, branch: str) -> None:
        self._validate_target_branch(branch)
        result = self._git(
            "fetch",
            "--no-tags",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
            f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
        )
        if result.returncode != 0:
            raise RepositorySafetyError("exact maintainer fetch failed")

    def create_backup_ref(self, pr_number: int, head_sha: str) -> str:
        _validate_pr_number(pr_number)
        _validate_sha(head_sha)
        timestamp = self._now()
        if timestamp.tzinfo is None:
            raise RepositorySafetyError("backup timestamp must be timezone-aware")
        utc_timestamp = timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_ref = (
            f"refs/snowcast-maintainer/backups/pr-{pr_number}/"
            f"{utc_timestamp}-{head_sha[:12]}"
        )
        result = self._git("update-ref", backup_ref, head_sha, "0" * 40)
        if result.returncode != 0:
            raise RepositorySafetyError(
                f"backup ref collision or creation failure at {backup_ref}"
            )
        return backup_ref

    def prepare_guarded_sync(self, pull_request: PullRequest) -> GuardedSyncResult:
        _validate_pull_request(pull_request)
        branch = pull_request.head_ref_name
        original_head = pull_request.head_sha

        self._validate_target_branch(branch)
        self.verify_repository()
        self.fetch_for_pr(branch)
        fetched_head = self._rev_parse(f"refs/remotes/origin/{branch}")
        if fetched_head != original_head:
            raise StaleRemoteHeadError(
                f"fetched head {fetched_head} does not match selected PR head "
                f"{original_head}"
            )

        merge_base_result = self._git(
            "merge-base",
            "refs/remotes/origin/main",
            original_head,
        )
        if merge_base_result.returncode != 0:
            raise RepositorySafetyError("cannot compute PR merge base")
        merge_base = merge_base_result.stdout.strip()
        _validate_sha(merge_base)

        before = build_intent_snapshot(self, merge_base, original_head)
        backup_ref = self.create_backup_ref(pull_request.number, original_head)

        switch = self._git("switch", "--detach", f"refs/remotes/origin/{branch}")
        if switch.returncode != 0:
            raise RepositorySafetyError("cannot detach at fetched target head")

        rebase = self._git("rebase", "refs/remotes/origin/main")
        if rebase.returncode != 0:
            abort = self._git("rebase", "--abort")
            if abort.returncode != 0:
                raise RebaseConflictError(
                    "rebase conflict occurred and automatic abort failed"
                )
            raise RebaseConflictError(
                "rebase conflict occurred; rebase was aborted without resolution"
            )

        rebased_head = self._rev_parse("HEAD")
        after = build_intent_snapshot(
            self,
            "refs/remotes/origin/main",
            rebased_head,
        )
        compare_intent(before, after)
        return GuardedSyncResult(
            target_branch=branch,
            original_head=original_head,
            rebased_head=rebased_head,
            backup_ref=backup_ref,
            merge_base=merge_base,
        )

    def push_with_lease(self, result: GuardedSyncResult) -> None:
        branch = result.target_branch
        original_head = result.original_head
        self._validate_target_branch(branch)
        _validate_sha(original_head)
        self.verify_repository()
        current_head = self.remote_head(branch)
        if current_head != original_head:
            raise StaleRemoteHeadError(
                f"remote head moved: expected {original_head}, found {current_head}"
            )
        push = self._git(
            "push",
            f"--force-with-lease=refs/heads/{branch}:{original_head}",
            "origin",
            f"HEAD:refs/heads/{branch}",
        )
        if push.returncode != 0:
            raise StaleRemoteHeadError("exact lease-protected push failed")

    def diff_names(self, base: str, head: str) -> tuple[str, ...]:
        _validate_revision(base)
        _validate_revision(head)
        result = self._git(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            base,
            head,
            "--",
        )
        if result.returncode != 0:
            raise RepositorySafetyError("cannot inspect changed paths")
        if not result.stdout:
            return ()
        paths = result.stdout.split("\0")
        if paths[-1] != "":
            raise RepositorySafetyError("Git returned malformed changed-path output")
        return tuple(paths[:-1])

    def show_text(self, revision: str, path: str) -> str:
        _validate_revision(revision)
        _validate_git_path(path)
        result = self._git(
            "show",
            "--no-ext-diff",
            "--format=",
            f"{revision}:{path}",
        )
        if result.returncode != 0:
            raise RepositorySafetyError(f"cannot read required Git object {path}")
        return result.stdout

    def _rev_parse(self, revision: str) -> str:
        _validate_revision(revision)
        result = self._git("rev-parse", "--verify", revision)
        if result.returncode != 0:
            raise RepositorySafetyError(f"cannot resolve required revision {revision}")
        sha = result.stdout.strip()
        _validate_sha(sha)
        return sha

    def _validate_target_branch(self, branch: str) -> None:
        _validate_target_branch(branch)
        check = self._git("check-ref-format", "--branch", branch)
        if check.returncode != 0:
            raise RepositorySafetyError(
                "target branch must be a ref-safe codex/* branch"
            )

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        argv = ("git", *arguments)
        try:
            return self._runner.run(argv, cwd=self.root)
        except OSError as error:
            raise RepositorySafetyError("Git command could not be started") from error


def _validate_pull_request(pull_request: PullRequest) -> None:
    if not isinstance(pull_request, PullRequest):
        raise RepositorySafetyError("guarded sync requires a strict PullRequest")
    _validate_pr_number(pull_request.number)
    _validate_target_branch(pull_request.head_ref_name)
    _validate_sha(pull_request.head_sha)
    if pull_request.head_repository_owner != REPOSITORY_OWNER:
        raise RepositorySafetyError("PR head owner must be lampssy")
    if pull_request.is_cross_repository:
        raise RepositorySafetyError("cross-repository PRs cannot be synchronized")
    if pull_request.base_ref_name != BASE_BRANCH:
        raise RepositorySafetyError("PR base branch must be main")


def _validate_pr_number(pr_number: int) -> None:
    if type(pr_number) is not int or pr_number <= 0:
        raise RepositorySafetyError("PR number must be a positive integer")


def _validate_sha(sha: str) -> None:
    if not isinstance(sha, str) or _SHA_PATTERN.fullmatch(sha) is None:
        raise RepositorySafetyError("SHA must be lowercase 40-hex")


def _validate_target_branch(branch: str) -> None:
    invalid = (
        not isinstance(branch, str)
        or not branch.startswith("codex/")
        or len(branch) == len("codex/")
        or _SAFE_BRANCH_CHARACTERS.fullmatch(branch) is None
        or branch.endswith(("/", "."))
        or branch.startswith("/")
        or "//" in branch
        or ".." in branch
        or "@{" in branch
        or any(
            segment in {"", ".", ".."}
            or segment.startswith("-")
            or segment.endswith(".lock")
            for segment in branch.split("/")
        )
    )
    if invalid:
        raise RepositorySafetyError("target branch must be a ref-safe codex/* branch")


def _validate_revision(revision: str) -> None:
    if _SHA_PATTERN.fullmatch(revision) is not None or revision == "HEAD":
        return
    if revision.startswith("refs/remotes/origin/"):
        branch = revision.removeprefix("refs/remotes/origin/")
        if branch == BASE_BRANCH:
            return
        _validate_target_branch(branch)
        return
    raise RepositorySafetyError("revision is not an allowed immutable Git reference")


def _validate_git_path(path: str) -> None:
    if not isinstance(path, str) or not path:
        raise RepositorySafetyError("Git object path must not be empty")
    pure = PurePosixPath(path)
    segments = path.split("/")
    if (
        pure.is_absolute()
        or any(part in {"", ".", ".."} for part in segments)
        or "\\" in path
        or ":" in path
        or any(ord(character) < 32 for character in path)
    ):
        raise RepositorySafetyError("Git object path is unsafe")


def _is_expected_remote(remote: str) -> bool:
    if remote != remote.strip() or any(character.isspace() for character in remote):
        return False
    scp_match = _SCP_REMOTE.fullmatch(remote)
    if scp_match is not None:
        return (
            scp_match.group("owner") == REPOSITORY_OWNER
            and scp_match.group("repo") == REPOSITORY_NAME
        )

    try:
        parsed = urlsplit(remote)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme == "https":
        valid_transport = (
            parsed.hostname == "github.com"
            and parsed.username is None
            and parsed.password is None
            and port is None
        )
    elif parsed.scheme == "ssh":
        valid_transport = (
            parsed.hostname == "github.com"
            and parsed.username == "git"
            and parsed.password is None
            and port is None
        )
    else:
        return False
    return (
        valid_transport
        and not parsed.query
        and not parsed.fragment
        and parsed.path
        in {
            f"/{REPOSITORY_OWNER}/{REPOSITORY_NAME}",
            f"/{REPOSITORY_OWNER}/{REPOSITORY_NAME}.git",
        }
    )

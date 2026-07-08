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
    IntentDiffEntry,
    IntentDriftError,
    build_intent_snapshot,
    compare_intent,
)
from ops.maintainer.models import PullRequest

__all__ = [
    "GitRepository",
    "GitAuthenticationError",
    "GitOperationTimeoutError",
    "GitPushRejectedError",
    "GitRemotePolicyError",
    "GitTransportError",
    "GuardedSyncResult",
    "IntentDriftError",
    "RebaseConflictError",
    "RepositorySafetyError",
    "RemotePolicy",
    "StaleRemoteHeadError",
]

REPOSITORY_OWNER = "lampssy"
REPOSITORY_NAME = "ai-sports-travel-planner"
BASE_BRANCH = "main"
LOCAL_GIT_TIMEOUT_SECONDS = 10.0
NETWORK_GIT_TIMEOUT_SECONDS = 60.0
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SAFE_BRANCH_CHARACTERS = re.compile(r"^[A-Za-z0-9._/-]+$")
_SCP_REMOTE = re.compile(
    r"^git@(?P<host>github\.com|github\.com-lampss):"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)
_BACKUP_REF = re.compile(
    r"^refs/snowcast-maintainer/backups/pr-[1-9][0-9]*/"
    r"[0-9]{8}T[0-9]{6}Z-(?P<prefix>[0-9a-f]{12})$"
)
_RAW_DIFF_HEADER = re.compile(
    r"^:(?P<old_mode>[0-7]{6}) (?P<new_mode>[0-7]{6}) "
    r"(?P<old_oid>[0-9a-f]{40}) (?P<new_oid>[0-9a-f]{40}) "
    r"(?P<status>[A-Z])$"
)


class RepositorySafetyError(RuntimeError):
    """The repository or requested Git operation violates the safety contract."""


class GitOperationTimeoutError(RepositorySafetyError):
    """A bounded Git or SSH operation exceeded its allowed runtime."""


class GitAuthenticationError(RepositorySafetyError):
    """Git authentication failed without exposing credential-bearing output."""


class GitTransportError(RepositorySafetyError):
    """A Git network transport failed without a stale-lease indication."""


class GitPushRejectedError(RepositorySafetyError):
    """The remote rejected a lease-protected push for a non-stale reason."""


class GitRemotePolicyError(RepositorySafetyError):
    """A remote denied or could not locate the configured repository."""


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
        timeout: float,
    ) -> subprocess.CompletedProcess[str]: ...


class _SubprocessRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_ASKPASS": "/usr/bin/false",
                "SSH_ASKPASS": "/usr/bin/false",
                "GCM_INTERACTIVE": "Never",
                "GIT_SSH_COMMAND": (
                    "ssh -o BatchMode=yes -o StrictHostKeyChecking=yes"
                ),
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
            timeout=timeout,
        )


class RemotePolicy(Protocol):
    def validate(
        self,
        fetch_urls: tuple[str, ...],
        push_urls: tuple[str, ...],
        *,
        resolve_ssh: Callable[[str, str], tuple[str, str]],
    ) -> None: ...


class _GitHubRemotePolicy:
    def validate(
        self,
        fetch_urls: tuple[str, ...],
        push_urls: tuple[str, ...],
        *,
        resolve_ssh: Callable[[str, str], tuple[str, str]],
    ) -> None:
        if len(fetch_urls) != 1 or len(push_urls) != 1:
            raise RepositorySafetyError(
                "origin must have exactly one effective fetch and push URL"
            )
        for url in (*fetch_urls, *push_urls):
            ssh_identity = _validated_remote_ssh_identity(url)
            if ssh_identity is None:
                continue
            ssh_host, explicit_user = ssh_identity
            hostname, user = resolve_ssh(ssh_host, explicit_user)
            if hostname != "github.com" or user != "git":
                raise RepositorySafetyError(
                    "effective origin SSH endpoint must resolve to GitHub as git"
                )


class GitRepository:
    """Narrow Git API for guarded maintainer synchronization."""

    def __init__(
        self,
        worktree_root: Path,
        *,
        runner: CommandRunner | None = None,
        now: Callable[[], datetime] | None = None,
        remote_policy: RemotePolicy | None = None,
    ) -> None:
        if not worktree_root.is_absolute() or worktree_root != worktree_root.resolve():
            raise RepositorySafetyError(
                "resolved worktree root must be supplied as an absolute path"
            )
        self.root = worktree_root
        self._runner = runner or _SubprocessRunner()
        self._now = now or (lambda: datetime.now(UTC))
        self._remote_policy = remote_policy or _GitHubRemotePolicy()
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

        fetch_urls = self._effective_remote_urls(push=False)
        push_urls = self._effective_remote_urls(push=True)
        try:
            self._remote_policy.validate(
                fetch_urls,
                push_urls,
                resolve_ssh=self._resolve_ssh,
            )
        except RepositorySafetyError:
            raise
        except Exception as error:
            raise RepositorySafetyError(
                "effective origin policy validation failed"
            ) from error

    def remote_head(self, branch: str) -> str:
        self._validate_target_branch(branch)
        self.verify_repository()
        expected_ref = f"refs/heads/{branch}"
        result = self._git(
            "ls-remote",
            "--heads",
            "origin",
            expected_ref,
            network=True,
        )
        if result.returncode != 0:
            _raise_sanitized_network_error("remote-head lookup", result.stderr)
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
        self.verify_repository()
        result = self._git(
            "fetch",
            "--no-tags",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
            f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
            network=True,
        )
        if result.returncode != 0:
            _raise_sanitized_network_error("fetch", result.stderr)

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
            try:
                existing_head = self._resolve_backup_ref(backup_ref)
            except RepositorySafetyError:
                existing_head = None
            if existing_head == head_sha:
                return backup_ref
            raise RepositorySafetyError(
                f"backup ref collision or creation failure at {backup_ref}"
            )
        return backup_ref

    def prepare_guarded_sync(self, pull_request: PullRequest) -> GuardedSyncResult:
        _validate_pull_request(pull_request)
        branch = pull_request.head_ref_name
        original_head = pull_request.head_sha

        self._validate_target_branch(branch)
        self._ensure_clean_preflight()
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

        try:
            rebase = self._git(
                "-c",
                "rebase.autoStash=false",
                "-c",
                "rebase.updateRefs=false",
                "rebase",
                "refs/remotes/origin/main",
            )
        except RepositorySafetyError:
            self._abort_rebase_if_active()
            raise
        if rebase.returncode != 0:
            if not self._rebase_in_progress():
                raise RepositorySafetyError(
                    "rebase failed without active conflict state"
                )
            self._abort_rebase_if_active()
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

    def push_with_lease(
        self,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> None:
        branch = result.target_branch
        original_head = result.original_head
        self._validate_target_branch(branch)
        _validate_sha(original_head)
        _validate_sha(result.rebased_head)
        _validate_sha(reviewed_head)
        _validate_backup_ref(result.backup_ref, original_head)

        current_head = self._rev_parse("HEAD")
        if current_head != reviewed_head:
            raise RepositorySafetyError(
                f"current HEAD {current_head} does not match "
                f"reviewed head {reviewed_head}"
            )
        backup_head = self._resolve_backup_ref(result.backup_ref)
        if backup_head != original_head:
            raise RepositorySafetyError(
                "backup ref no longer resolves to the prepared original head"
            )
        ancestor = self._git(
            "merge-base",
            "--is-ancestor",
            result.rebased_head,
            reviewed_head,
        )
        if ancestor.returncode == 1:
            raise RepositorySafetyError("reviewed head must descend from rebased head")
        if ancestor.returncode != 0:
            raise RepositorySafetyError("cannot verify reviewed head lineage")

        self.verify_repository()
        remote_head = self.remote_head(branch)
        if remote_head != original_head:
            raise StaleRemoteHeadError(
                f"remote head moved: expected {original_head}, found {remote_head}"
            )
        push = self._git(
            "push",
            f"--force-with-lease=refs/heads/{branch}:{original_head}",
            "origin",
            f"HEAD:refs/heads/{branch}",
            network=True,
        )
        if push.returncode != 0:
            _raise_sanitized_push_error(push.stderr)

    def diff_entries(self, base: str, head: str) -> tuple[IntentDiffEntry, ...]:
        _validate_revision(base)
        _validate_revision(head)
        result = self._git(
            "diff",
            "--raw",
            "--no-renames",
            "--abbrev=40",
            "-z",
            base,
            head,
            "--",
        )
        if result.returncode != 0:
            raise RepositorySafetyError("cannot inspect changed path metadata")
        if not result.stdout:
            return ()
        tokens = result.stdout.split("\0")
        if tokens[-1] != "" or len(tokens[:-1]) % 2 != 0:
            raise RepositorySafetyError("Git returned malformed raw diff output")
        entries: list[IntentDiffEntry] = []
        for index in range(0, len(tokens) - 1, 2):
            header = _RAW_DIFF_HEADER.fullmatch(tokens[index])
            if header is None:
                raise RepositorySafetyError("Git returned malformed raw diff metadata")
            entries.append(
                IntentDiffEntry(
                    path=tokens[index + 1],
                    old_mode=header.group("old_mode"),
                    new_mode=header.group("new_mode"),
                    old_oid=header.group("old_oid"),
                    new_oid=header.group("new_oid"),
                    status=header.group("status"),
                )
            )
        return tuple(entries)

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

    def _resolve_backup_ref(self, backup_ref: str) -> str:
        result = self._git("rev-parse", "--verify", backup_ref)
        if result.returncode != 0:
            raise RepositorySafetyError("prepared backup ref cannot be resolved")
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

    def _ensure_clean_preflight(self) -> None:
        if self._rebase_in_progress():
            raise RepositorySafetyError("pre-existing rebase state blocks prepare")
        status = self._git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=normal",
            "--ignored=no",
        )
        if status.returncode != 0:
            raise RepositorySafetyError("cannot verify clean maintainer worktree")
        if status.stdout:
            raise RepositorySafetyError(
                "maintainer worktree must be fully clean before prepare"
            )

    def _rebase_in_progress(self) -> bool:
        for state_name in ("rebase-merge", "rebase-apply"):
            result = self._git("rev-parse", "--git-path", state_name)
            if result.returncode != 0:
                raise RepositorySafetyError("cannot inspect Git rebase state")
            state_path = Path(result.stdout.strip())
            if not state_path.is_absolute():
                state_path = self.root / state_path
            if state_path.exists():
                return True
        return False

    def _abort_rebase_if_active(self) -> None:
        if not self._rebase_in_progress():
            return
        abort = self._git("rebase", "--abort")
        if abort.returncode != 0 or self._rebase_in_progress():
            raise RebaseConflictError("active rebase could not be aborted safely")

    def _effective_remote_urls(self, *, push: bool) -> tuple[str, ...]:
        arguments = ["remote", "get-url"]
        if push:
            arguments.append("--push")
        arguments.extend(("--all", "origin"))
        result = self._git(*arguments)
        if result.returncode != 0:
            raise RepositorySafetyError("cannot resolve effective origin URLs")
        urls = tuple(result.stdout.splitlines())
        malformed = not urls or any(
            not url or any(ord(char) < 32 for char in url) for url in urls
        )
        if malformed:
            raise RepositorySafetyError("effective origin URLs are malformed")
        return urls

    def _resolve_ssh(self, host: str, explicit_user: str) -> tuple[str, str]:
        result = self._command(("ssh", "-G", "-l", explicit_user, host))
        if result.returncode != 0:
            raise RepositorySafetyError("cannot resolve effective origin SSH endpoint")
        values: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition(" ")
            if separator and key in {"hostname", "user"}:
                values[key] = value.strip()
        hostname = values.get("hostname")
        user = values.get("user")
        if not hostname or not user:
            raise RepositorySafetyError("effective origin SSH endpoint is incomplete")
        return hostname, user

    def _git(
        self,
        *arguments: str,
        network: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        argv = ("git", *arguments)
        return self._command(argv, network=network)

    def _command(
        self,
        argv: tuple[str, ...],
        *,
        network: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        timeout = NETWORK_GIT_TIMEOUT_SECONDS if network else LOCAL_GIT_TIMEOUT_SECONDS
        try:
            return self._runner.run(argv, cwd=self.root, timeout=timeout)
        except subprocess.TimeoutExpired:
            operation = "network Git" if network else "local Git/SSH"
            raise GitOperationTimeoutError(
                f"{operation} operation timed out after {timeout:g} seconds"
            ) from None
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


def _validate_backup_ref(backup_ref: str, original_head: str) -> None:
    if not isinstance(backup_ref, str):
        raise RepositorySafetyError("backup ref is malformed")
    match = _BACKUP_REF.fullmatch(backup_ref)
    if match is None or match.group("prefix") != original_head[:12]:
        raise RepositorySafetyError("backup ref is not bound to original head")


def _raise_sanitized_push_error(stderr: str) -> None:
    diagnostic = stderr.lower()
    if any(
        marker in diagnostic
        for marker in (
            "authentication failed",
            "permission denied",
            "could not read username",
            "terminal prompts disabled",
        )
    ):
        raise GitAuthenticationError("Git push authentication failed")
    if "stale info" in diagnostic or "force-with-lease" in diagnostic:
        raise StaleRemoteHeadError("lease-protected push was rejected as stale")
    if "remote rejected" in diagnostic:
        raise GitPushRejectedError("lease-protected push was rejected by the remote")
    raise GitTransportError("lease-protected push failed due to a transport error")


def _raise_sanitized_network_error(operation: str, stderr: str) -> None:
    diagnostic = stderr.lower()
    if any(
        marker in diagnostic
        for marker in (
            "authentication failed",
            "permission denied",
            "could not read username",
            "terminal prompts disabled",
        )
    ):
        raise GitAuthenticationError(f"Git {operation} authentication failed")
    if any(
        marker in diagnostic
        for marker in ("repository not found", "remote rejected", "not permitted")
    ):
        raise GitRemotePolicyError(f"Git {operation} failed due to remote policy")
    raise GitTransportError(f"Git {operation} failed due to a transport error")


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


def _validated_remote_ssh_identity(remote: str) -> tuple[str, str] | None:
    if remote != remote.strip() or any(character.isspace() for character in remote):
        raise RepositorySafetyError(
            "effective origin must be exactly lampssy/ai-sports-travel-planner"
        )
    scp_match = _SCP_REMOTE.fullmatch(remote)
    if scp_match is not None:
        if (
            scp_match.group("owner") != REPOSITORY_OWNER
            or scp_match.group("repo") != REPOSITORY_NAME
        ):
            raise RepositorySafetyError(
                "effective origin must be exactly lampssy/ai-sports-travel-planner"
            )
        return scp_match.group("host"), "git"

    try:
        parsed = urlsplit(remote)
        port = parsed.port
    except ValueError:
        raise RepositorySafetyError("effective origin URL is malformed") from None
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
        raise RepositorySafetyError(
            "effective origin must be approved GitHub SSH or HTTPS"
        )
    valid_repository = (
        valid_transport
        and not parsed.query
        and not parsed.fragment
        and parsed.path
        in {
            f"/{REPOSITORY_OWNER}/{REPOSITORY_NAME}",
            f"/{REPOSITORY_OWNER}/{REPOSITORY_NAME}.git",
        }
    )
    if not valid_repository:
        raise RepositorySafetyError(
            "effective origin must be exactly lampssy/ai-sports-travel-planner"
        )
    if parsed.scheme == "ssh":
        assert parsed.hostname is not None
        assert parsed.username is not None
        return parsed.hostname, parsed.username
    return None

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.intent import (
    IntentDiffEntry,
    IntentDriftError,
    IntentSnapshot,
    IntentValidationError,
    build_intent_snapshot,
    build_preparation_intent_snapshot,
    is_allowed_ci_repair_path,
    is_allowed_curation_path,
)
from ops.maintainer.models import PullRequest

__all__ = [
    "CiRepairCheckpoint",
    "CurationCheckpointRefs",
    "CurationCheckpointIntegrityError",
    "CurationRecoveryCheckpoint",
    "GitRepository",
    "ContinuationReplayResult",
    "GitAuthenticationError",
    "GitOperationTimeoutError",
    "GitPushRejectedError",
    "GitRemotePolicyError",
    "GitTransportError",
    "GuardedSyncResult",
    "IntentDriftError",
    "LegacyCurationRef",
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
_LEGACY_CURATION_SOURCE_REF = re.compile(
    r"^refs/snowcast-maintainer/"
    r"(?P<suffix>(?:prepared|reviewed|continuations|remediation|"
    r"remediation-continuations)/[A-Za-z0-9][A-Za-z0-9._/-]{0,255})$"
)
_LEGACY_CURATION_ARCHIVE_REF = re.compile(
    r"^refs/snowcast-maintainer/archive/legacy-curation-v1/"
    r"(?P<archive_id>[0-9a-f]{32})/"
    r"(?P<suffix>(?:prepared|reviewed|continuations|remediation|"
    r"remediation-continuations)/[A-Za-z0-9][A-Za-z0-9._/-]{0,255})$"
)
_OBJECT_SIZE_PATTERN = re.compile(r"^(?:0|[1-9][0-9]*)\n?$")
_SCP_REMOTE = re.compile(
    r"^git@(?P<host>github\.com|github\.com-lampss):"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)
_BACKUP_REF = re.compile(
    r"^refs/snowcast-maintainer/backups/pr-[1-9][0-9]*/"
    r"[0-9]{8}T[0-9]{6}Z-(?P<prefix>[0-9a-f]{12})$"
)
_PREPARED_REF = re.compile(
    r"^refs/snowcast-maintainer/prepared/pr-[1-9][0-9]*/"
    r"(?P<base>[0-9a-f]{12})-(?P<rebased>[0-9a-f]{12})$"
)
_CI_REPAIR_REF = re.compile(
    r"^refs/snowcast-maintainer/ci-repairs/pr-[1-9][0-9]*/"
    r"(?P<current>[0-9a-f]{12})-(?P<repair>[0-9a-f]{12})$"
)
_RAW_DIFF_HEADER = re.compile(
    r"^:(?P<old_mode>[0-7]{6}) (?P<new_mode>[0-7]{6}) "
    r"(?P<old_oid>[0-9a-f]{40}) (?P<new_oid>[0-9a-f]{40}) "
    r"(?P<status>[A-Z])$"
)
_VALIDATION_BASE_FILES = (
    "app/data/catalog.json",
    "app/data/resort_trust_manifest.json",
    "pyproject.toml",
    "tests/conftest.py",
    "tests/test_catalog_curation.py",
    "tests/test_catalog_curation_reconciliation.py",
    "tests/test_catalog_models.py",
    "tests/test_catalog_trust.py",
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


class CurationCheckpointIntegrityError(RepositorySafetyError):
    """Immutable generation checkpoint refs are missing or no longer exact."""


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
    prepared_ref: str
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_base: str = Field(pattern=r"^[0-9a-f]{40}$")


class CurationCheckpointRefs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    checkpoint_ref: str
    squash_ref: str


class LegacyCurationRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_ref: str = Field(pattern=r"^refs/snowcast-maintainer/")
    archive_ref: str = Field(
        pattern=r"^refs/snowcast-maintainer/archive/legacy-curation-v1/"
    )
    head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def validate_archive_target(self) -> LegacyCurationRef:
        source = _LEGACY_CURATION_SOURCE_REF.fullmatch(self.source_ref)
        archive = _LEGACY_CURATION_ARCHIVE_REF.fullmatch(self.archive_ref)
        if source is None or archive is None:
            raise ValueError("legacy curation ref uses an unrecognized namespace")
        if source.group("suffix") != archive.group("suffix"):
            raise ValueError("legacy curation archive ref does not match its source")
        return self


class ContinuationReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    result: Literal["unchanged", "prepared", "conflict"]
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    conflict_paths: tuple[str, ...] = ()
    sync: GuardedSyncResult | None = None


class CurationRecoveryCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    pr_number: int = Field(ge=1)
    generation_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    checkpoint_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    )
    sync: GuardedSyncResult
    checkpoint_ref: str
    squash_ref: str

    @model_validator(mode="after")
    def validate_recovery_identity(self) -> CurationRecoveryCheckpoint:
        if self.sync.original_head != self.selected_head:
            raise ValueError("curation recovery sync does not match selected head")
        expected_prefix = (
            f"refs/snowcast-maintainer/curation/pr-{self.pr_number}/"
            f"{self.generation_id}/{self.transaction_id}/"
        )
        if self.checkpoint_ref != f"{expected_prefix}checkpoint":
            raise ValueError("curation checkpoint ref does not match recovery identity")
        if self.squash_ref != f"{expected_prefix}replay":
            raise ValueError("curation replay ref does not match recovery identity")
        return self


class CiRepairCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    repair_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repair_ref: str = Field(pattern=r"^refs/snowcast-maintainer/ci-repairs/")
    repair_paths: frozenset[str] = Field(min_length=1)
    non_test_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class CommandRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]: ...


class _SubprocessRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
        stdin: str | None = None,
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
            input=stdin,
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

    def current_head(self) -> str:
        """Return the exact commit currently checked out in this worktree."""
        return self._rev_parse("HEAD")

    def legacy_curation_refs(
        self,
        archive_id: str,
    ) -> tuple[LegacyCurationRef, ...]:
        if re.fullmatch(r"[0-9a-f]{32}", archive_id) is None:
            raise RepositorySafetyError("legacy archive ID is malformed")
        prefixes = (
            "refs/snowcast-maintainer/prepared/",
            "refs/snowcast-maintainer/reviewed/",
            "refs/snowcast-maintainer/continuations/",
            "refs/snowcast-maintainer/remediation/",
            "refs/snowcast-maintainer/remediation-continuations/",
        )
        result = self._git(
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            *prefixes,
        )
        if result.returncode != 0:
            raise RepositorySafetyError("cannot inventory legacy curation refs")
        refs: list[LegacyCurationRef] = []
        for line in result.stdout.splitlines():
            source_ref, separator, head = line.partition(" ")
            if not separator or not any(
                source_ref.startswith(item) for item in prefixes
            ):
                raise RepositorySafetyError(
                    "legacy curation ref inventory is malformed"
                )
            _validate_sha(head)
            suffix = source_ref.removeprefix("refs/snowcast-maintainer/")
            refs.append(
                LegacyCurationRef(
                    source_ref=source_ref,
                    archive_ref=(
                        "refs/snowcast-maintainer/archive/legacy-curation-v1/"
                        f"{archive_id}/{suffix}"
                    ),
                    head=head,
                )
            )
        return tuple(sorted(refs, key=lambda item: item.source_ref))

    def archive_legacy_curation_refs(
        self,
        refs: Sequence[LegacyCurationRef],
    ) -> int:
        pending: list[LegacyCurationRef] = []
        for supplied in refs:
            item = LegacyCurationRef.model_validate(supplied.model_dump())
            source_head = self._optional_ref_head(item.source_ref)
            archive_head = self._optional_ref_head(item.archive_ref)
            if source_head == item.head and archive_head is None:
                pending.append(item)
                continue
            if source_head is None and archive_head == item.head:
                continue
            raise RepositorySafetyError("legacy curation ref archive state conflicts")
        if not pending:
            return 0
        commands = ["start"]
        for item in pending:
            commands.extend(
                (
                    f"create {item.archive_ref} {item.head}",
                    f"delete {item.source_ref} {item.head}",
                )
            )
        commands.extend(("prepare", "commit"))
        result = self._git("update-ref", "--stdin", stdin="\n".join(commands) + "\n")
        if result.returncode != 0:
            raise RepositorySafetyError(
                "cannot archive legacy curation refs atomically"
            )
        for item in pending:
            if (
                self._optional_ref_head(item.source_ref) is not None
                or self._optional_ref_head(item.archive_ref) != item.head
            ):
                raise RepositorySafetyError(
                    "legacy curation ref archive did not commit"
                )
        return len(pending)

    def verify_immutable_diff(self, base: str, head: str) -> IntentSnapshot:
        """Validate one immutable ancestor/head pair and return its typed intent."""
        return self._verify_immutable_diff(base, head, build_intent_snapshot)

    def _verify_immutable_diff(
        self,
        base: str,
        head: str,
        builder: Callable[[GitRepository, str, str], IntentSnapshot],
    ) -> IntentSnapshot:
        _validate_sha(base)
        _validate_sha(head)
        if base == head:
            raise RepositorySafetyError("immutable diff must contain two commits")
        self.verify_repository()
        self._verify_commit(base)
        self._verify_commit(head)
        self._assert_ancestor(
            base,
            head,
            "immutable diff base must be an ancestor of head",
        )
        snapshot = builder(self, base, head)
        if not snapshot.changed_paths:
            raise RepositorySafetyError("immutable diff must contain changed paths")
        return snapshot

    def remote_head(self, branch: str) -> str:
        head = self._lookup_remote_head(branch, allow_absent=False)
        if head is None:
            raise RepositorySafetyError(
                f"expected exactly one remote head for {branch}"
            )
        return head

    def optional_remote_head(self, branch: str) -> str | None:
        return self._lookup_remote_head(branch, allow_absent=True)

    def _lookup_remote_head(
        self,
        branch: str,
        *,
        allow_absent: bool,
    ) -> str | None:
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
        if allow_absent and result.stdout == "":
            return None
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
            if allow_absent:
                raise RepositorySafetyError(
                    f"expected one exact remote head or an absent ref for {branch}"
                )
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

    def fetch_main(self) -> str:
        """Fetch and return the exact current canonical main head."""
        self.verify_repository()
        result = self._git(
            "fetch",
            "--no-tags",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
            network=True,
        )
        if result.returncode != 0:
            _raise_sanitized_network_error("fetch", result.stderr)
        return self._rev_parse("refs/remotes/origin/main")

    def prepare_ci_repair(self, pull_request: PullRequest) -> str:
        """Detach the clean worktree at the exact live PR head without rebasing."""
        _validate_pull_request(pull_request)
        branch = pull_request.head_ref_name
        self._ensure_clean_preflight()
        self.verify_repository()
        self.fetch_for_pr(branch)
        fetched_head = self._rev_parse(f"refs/remotes/origin/{branch}")
        if fetched_head != pull_request.head_sha:
            raise StaleRemoteHeadError(
                f"fetched head {fetched_head} does not match current PR head "
                f"{pull_request.head_sha}"
            )
        switch = self._git("switch", "--detach", fetched_head)
        if switch.returncode != 0:
            raise RepositorySafetyError("cannot detach at exact current PR head")
        if self.current_head() != fetched_head:
            raise RepositorySafetyError(
                "detached CI repair head drifted during prepare"
            )
        return fetched_head

    def checkpoint_ci_repair(
        self,
        *,
        pull_request: PullRequest,
        semantic_head: str,
        current_head: str,
        repair_head: str,
        expected_non_test_tree_digest: str,
    ) -> CiRepairCheckpoint:
        """Create one immutable checkpoint for a structurally test-only repair."""
        self._ensure_clean_preflight()
        if self.current_head() != repair_head:
            raise RepositorySafetyError(
                "current HEAD does not match the requested CI repair head"
            )
        checkpoint = self._build_ci_repair_checkpoint(
            pull_request=pull_request,
            semantic_head=semantic_head,
            current_head=current_head,
            repair_head=repair_head,
            expected_non_test_tree_digest=expected_non_test_tree_digest,
            allowed_live_heads=frozenset({current_head}),
        )
        self._create_exact_ref(
            checkpoint.repair_ref,
            checkpoint.repair_head,
        )
        return checkpoint

    def revalidate_ci_repair_checkpoint(
        self,
        *,
        pull_request: PullRequest,
        semantic_head: str,
        current_head: str,
        checkpoint: CiRepairCheckpoint,
    ) -> CiRepairCheckpoint:
        """Revalidate one exact repair solely from its immutable checkpoint ref."""
        if not isinstance(checkpoint, CiRepairCheckpoint):
            raise RepositorySafetyError("CI repair checkpoint is malformed")
        _validate_pull_request(pull_request)
        if pull_request.head_sha not in {
            current_head,
            checkpoint.repair_head,
        }:
            raise StaleRemoteHeadError(
                "live PR head does not match the checkpointed CI repair heads"
            )
        self._ensure_clean_preflight()
        _validate_ci_repair_ref(
            checkpoint.repair_ref,
            pull_request.number,
            current_head,
            checkpoint.repair_head,
        )
        if self._optional_ref_head(checkpoint.repair_ref) != checkpoint.repair_head:
            raise RepositorySafetyError(
                "CI repair ref no longer matches the checkpointed head"
            )
        switch = self._git("switch", "--detach", checkpoint.repair_ref)
        if switch.returncode != 0:
            raise RepositorySafetyError(
                "cannot restore the immutable CI repair checkpoint"
            )
        if self.current_head() != checkpoint.repair_head:
            raise RepositorySafetyError(
                "restored CI repair checkout does not match the checkpointed head"
            )
        revalidated = self._build_ci_repair_checkpoint(
            pull_request=pull_request,
            semantic_head=semantic_head,
            current_head=current_head,
            repair_head=checkpoint.repair_head,
            expected_non_test_tree_digest=checkpoint.non_test_tree_digest,
            allowed_live_heads=frozenset({current_head, checkpoint.repair_head}),
        )
        if revalidated != checkpoint:
            raise RepositorySafetyError(
                "CI repair checkpoint no longer matches immutable structure"
            )
        return revalidated

    def _build_ci_repair_checkpoint(
        self,
        *,
        pull_request: PullRequest,
        semantic_head: str,
        current_head: str,
        repair_head: str,
        expected_non_test_tree_digest: str,
        allowed_live_heads: frozenset[str],
    ) -> CiRepairCheckpoint:
        _validate_pull_request(pull_request)
        _validate_sha(semantic_head)
        _validate_sha(current_head)
        _validate_sha(repair_head)
        _validate_tree_digest(expected_non_test_tree_digest)
        if pull_request.head_sha not in allowed_live_heads:
            raise StaleRemoteHeadError(
                "live PR head does not match the checkpointed CI repair heads"
            )
        self.verify_repository()
        self._verify_commit(semantic_head)
        self._verify_commit(current_head)
        self._verify_commit(repair_head)
        self._assert_ancestor(
            current_head,
            repair_head,
            "CI repair head must descend from the current pushed head",
        )
        semantic_digest = self.non_test_tree_digest(semantic_head)
        repair_digest = self.non_test_tree_digest(repair_head)
        if (
            semantic_digest != expected_non_test_tree_digest
            or repair_digest != expected_non_test_tree_digest
        ):
            raise RepositorySafetyError(
                "CI repair changed the checkpointed non-test tree"
            )
        entries = self.diff_entries(current_head, repair_head)
        if not entries:
            raise RepositorySafetyError("CI repair diff must not be empty")
        for entry in entries:
            valid_modes = entry.new_mode == "100644" and (
                (entry.status == "A" and entry.old_mode == "000000")
                or (entry.status == "M" and entry.old_mode == "100644")
            )
            if (
                entry.status not in {"A", "M"}
                or not valid_modes
                or not is_allowed_ci_repair_path(entry.path)
            ):
                raise RepositorySafetyError(
                    "CI repair diff contains a disallowed path or file shape"
                )
        repair_ref = (
            f"refs/snowcast-maintainer/ci-repairs/pr-{pull_request.number}/"
            f"{current_head[:12]}-{repair_head[:12]}"
        )
        return CiRepairCheckpoint(
            repair_head=repair_head,
            repair_ref=repair_ref,
            repair_paths=frozenset(entry.path for entry in entries),
            non_test_tree_digest=repair_digest,
        )

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
        return self._prepare_guarded_sync(
            pull_request,
            builder=build_preparation_intent_snapshot,
        )

    def _prepare_guarded_sync(
        self,
        pull_request: PullRequest,
        *,
        builder: Callable[[GitRepository, str, str], IntentSnapshot],
    ) -> GuardedSyncResult:
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
        base_head = self._rev_parse("refs/remotes/origin/main")

        merge_base_result = self._git(
            "merge-base",
            "refs/remotes/origin/main",
            original_head,
        )
        if merge_base_result.returncode != 0:
            raise RepositorySafetyError("cannot compute PR merge base")
        merge_base = merge_base_result.stdout.strip()
        _validate_sha(merge_base)

        before = builder(self, merge_base, original_head)
        if not before.changed_paths:
            raise IntentDriftError("selected curation diff is empty")
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
        after = builder(
            self,
            base_head,
            rebased_head,
        )
        if not after.changed_paths:
            raise IntentDriftError("rebased curation diff is empty")
        prepared_ref = self._create_prepared_ref(
            pull_request.number,
            base_head,
            rebased_head,
        )
        return GuardedSyncResult(
            target_branch=branch,
            original_head=original_head,
            rebased_head=rebased_head,
            backup_ref=backup_ref,
            prepared_ref=prepared_ref,
            base_head=base_head,
            merge_base=merge_base,
        )

    def revalidate_prepared_result(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot:
        """Revalidate a complete prepared result against current immutable state."""
        return self._revalidate_prepared_result(
            pull_request,
            result,
            reviewed_head,
            builder=build_preparation_intent_snapshot,
        )

    def revalidate_validation_remediation_descendant(
        self,
        reviewed_head: str,
        remediation_head: str,
    ) -> None:
        """Require one validation remediation to extend its reviewed head."""
        _validate_sha(reviewed_head)
        _validate_sha(remediation_head)
        self.verify_repository()
        self._verify_commit(reviewed_head)
        self._verify_commit(remediation_head)
        if reviewed_head == remediation_head:
            raise RepositorySafetyError(
                "validation remediation must create a descendant commit"
            )
        self._assert_ancestor(
            reviewed_head,
            remediation_head,
            "validation remediation must descend from the reviewed head",
        )

    def checkpoint_curation_generation(
        self,
        pull_request: PullRequest,
        sync: GuardedSyncResult,
        checkpoint_head: str,
        generation_id: str,
        transaction_id: str,
    ) -> CurationCheckpointRefs:
        """Create or verify one exact generation checkpoint transaction."""
        self.revalidate_prepared_result(pull_request, sync, checkpoint_head)
        prefix = (
            f"refs/snowcast-maintainer/curation/pr-{pull_request.number}/"
            f"{generation_id}/{transaction_id}/"
        )
        refs = CurationCheckpointRefs(
            checkpoint_ref=f"{prefix}checkpoint",
            squash_ref=f"{prefix}replay",
        )
        self._create_continuation_checkpoint(
            checkpoint_ref=refs.checkpoint_ref,
            squash_ref=refs.squash_ref,
            checkpoint_head=checkpoint_head,
            base_head=sync.base_head,
            message=(
                f"Snowcast curation generation checkpoint for PR #{pull_request.number}"
            ),
            failure_message="curation generation replay commit cannot be created",
        )
        self._validate_curation_checkpoint_refs(
            checkpoint_head=checkpoint_head,
            sync=sync,
            checkpoint_ref=refs.checkpoint_ref,
            squash_ref=refs.squash_ref,
        )
        return refs

    def prepare_curation_recovery(
        self,
        pull_request: PullRequest,
        recovery: CurationRecoveryCheckpoint,
        *,
        restart_interrupted: bool = False,
    ) -> ContinuationReplayResult:
        """Restore or replay one generation checkpoint onto current main."""
        _validate_pull_request(pull_request)
        self.verify_repository()
        if restart_interrupted:
            self._abort_cherry_pick_if_active()
        if self._cherry_pick_in_progress():
            raise RepositorySafetyError("pre-existing Git operation blocks prepare")
        self._ensure_clean_preflight()
        self.fetch_for_pr(pull_request.head_ref_name)
        fetched_head = self._rev_parse(
            f"refs/remotes/origin/{pull_request.head_ref_name}"
        )
        if (
            recovery.pr_number != pull_request.number
            or fetched_head != pull_request.head_sha
            or fetched_head != recovery.selected_head
        ):
            raise StaleRemoteHeadError("remote PR head changed after checkpoint")
        squash_head = self._validate_curation_checkpoint(recovery)
        base_head = self._rev_parse("refs/remotes/origin/main")
        if base_head == recovery.sync.base_head:
            switch = self._git("switch", "--detach", recovery.checkpoint_ref)
            if switch.returncode != 0:
                raise CurationCheckpointIntegrityError(
                    "cannot restore exact curation checkpoint"
                )
            self._revalidate_prepared_result(
                pull_request,
                recovery.sync,
                recovery.checkpoint_head,
                builder=build_preparation_intent_snapshot,
            )
            return ContinuationReplayResult(
                result="unchanged",
                base_head=base_head,
                head=recovery.checkpoint_head,
                sync=recovery.sync,
            )

        self._assert_ancestor(
            recovery.sync.base_head,
            base_head,
            "current main must descend from the curation checkpoint base",
        )
        switch = self._git("switch", "--detach", base_head)
        if switch.returncode != 0:
            raise RepositorySafetyError("cannot detach at curation replay base")
        replay = self._git("cherry-pick", "--no-edit", recovery.squash_ref)
        if replay.returncode != 0:
            if not self._cherry_pick_in_progress():
                raise RepositorySafetyError(
                    "curation replay failed without conflict state"
                )
            conflict_paths = self._nul_paths(
                "diff",
                "--name-only",
                "--diff-filter=U",
                "-z",
            )
            expected_paths = frozenset(
                entry.path
                for entry in self.diff_entries(
                    recovery.sync.base_head,
                    squash_head,
                )
            )
            if (
                not conflict_paths
                or not set(conflict_paths).issubset(expected_paths)
                or not all(is_allowed_curation_path(path) for path in conflict_paths)
            ):
                self._abort_cherry_pick_if_active()
                raise RepositorySafetyError(
                    "curation conflict includes a disallowed path"
                )
            return ContinuationReplayResult(
                result="conflict",
                base_head=base_head,
                conflict_paths=conflict_paths,
            )
        return self._completed_continuation_replay(
            pull_request,
            recovery.sync,
            base_head,
        )

    def continue_curation_conflict(
        self,
        pull_request: PullRequest,
        recovery: CurationRecoveryCheckpoint,
    ) -> ContinuationReplayResult:
        """Complete one resolved generation-checkpoint replay conflict."""
        _validate_pull_request(pull_request)
        self.verify_repository()
        if not self._cherry_pick_in_progress():
            raise RepositorySafetyError("curation cherry-pick is not active")
        self.fetch_for_pr(pull_request.head_ref_name)
        if (
            self._rev_parse(f"refs/remotes/origin/{pull_request.head_ref_name}")
            != pull_request.head_sha
            or pull_request.head_sha != recovery.selected_head
        ):
            self._abort_cherry_pick_if_active()
            raise StaleRemoteHeadError("remote PR head changed during replay")
        try:
            squash_head = self._validate_curation_checkpoint(recovery)
        except Exception:
            self._abort_cherry_pick_if_active()
            raise
        base_head = self.current_head()
        if self._rev_parse("refs/remotes/origin/main") != base_head:
            self._abort_cherry_pick_if_active()
            raise StaleRemoteHeadError("main moved during curation conflict")
        if self._nul_paths("diff", "--name-only", "--diff-filter=U", "-z"):
            raise RepositorySafetyError("curation conflicts remain unresolved")
        if self._nul_paths("diff", "--name-only", "-z") or self._nul_paths(
            "ls-files", "--others", "--exclude-standard", "-z"
        ):
            self._abort_cherry_pick_if_active()
            raise RepositorySafetyError(
                "curation worktree contains unrelated unstaged changes"
            )
        expected_entries = {
            entry.path: entry
            for entry in self.diff_entries(recovery.sync.base_head, squash_head)
        }
        staged_entries = self._staged_diff_entries()
        staged_paths = frozenset(entry.path for entry in staged_entries)
        if (
            not staged_paths
            or not staged_paths.issubset(expected_entries)
            or any(
                entry.new_mode != expected_entries[entry.path].new_mode
                for entry in staged_entries
            )
        ):
            self._abort_cherry_pick_if_active()
            raise RepositorySafetyError(
                "curation resolution changed a path outside checkpoint scope"
            )
        completed = self._git("cherry-pick", "--continue")
        if completed.returncode != 0:
            self._abort_cherry_pick_if_active()
            raise RepositorySafetyError("curation replay did not complete once")
        return self._completed_continuation_replay(
            pull_request,
            recovery.sync,
            base_head,
        )

    def revalidate_curation_checkpoint(
        self,
        pull_request: PullRequest,
        recovery: CurationRecoveryCheckpoint,
    ) -> None:
        """Recheck one exact generation checkpoint and its private refs."""
        if recovery.pr_number != pull_request.number:
            raise CurationCheckpointIntegrityError(
                "curation checkpoint does not match pull request"
            )
        self.revalidate_prepared_result(
            pull_request,
            recovery.sync,
            recovery.checkpoint_head,
        )
        self._validate_curation_checkpoint(recovery)

    def _revalidate_prepared_result(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        *,
        builder: Callable[[GitRepository, str, str], IntentSnapshot],
    ) -> IntentSnapshot:
        """Revalidate a complete prepared result against current immutable state."""
        _validate_pull_request(pull_request)
        self.verify_repository()
        if (
            result.target_branch != pull_request.head_ref_name
            or result.original_head != pull_request.head_sha
        ):
            raise RepositorySafetyError("prepared result does not match selected PR")
        _validate_target_branch(result.target_branch)
        _validate_sha(result.original_head)
        _validate_sha(result.base_head)
        _validate_sha(result.rebased_head)
        _validate_sha(result.merge_base)
        _validate_sha(reviewed_head)
        _validate_backup_ref(result.backup_ref, result.original_head)
        _validate_prepared_ref(
            result.prepared_ref,
            result.base_head,
            result.rebased_head,
            pull_request.number,
        )
        for sha in (
            result.original_head,
            result.base_head,
            result.rebased_head,
            result.merge_base,
            reviewed_head,
        ):
            self._verify_commit(sha)
        if self._resolve_backup_ref(result.backup_ref) != result.original_head:
            raise RepositorySafetyError(
                "backup ref no longer resolves to the prepared original head"
            )
        if self._resolve_backup_ref(result.prepared_ref) != result.rebased_head:
            raise RepositorySafetyError(
                "prepared ref no longer resolves to the prepared rebased head"
            )
        recomputed_merge_base = self._merge_base(
            result.base_head,
            result.original_head,
        )
        if recomputed_merge_base != result.merge_base:
            raise RepositorySafetyError("prepared merge base no longer matches")
        self._assert_ancestor(
            result.base_head,
            result.rebased_head,
            "prepared base must be an ancestor of rebased head",
        )
        self._assert_ancestor(
            result.rebased_head,
            reviewed_head,
            "reviewed head must descend from rebased head",
        )
        self._ensure_clean_preflight()
        current_head = self._rev_parse("HEAD")
        if current_head != reviewed_head:
            raise RepositorySafetyError("current HEAD does not match the reviewed head")
        try:
            original_intent = builder(
                self,
                result.merge_base,
                result.original_head,
            )
            prepared_intent = builder(
                self,
                result.base_head,
                result.rebased_head,
            )
            reviewed_intent = builder(
                self,
                result.base_head,
                reviewed_head,
            )
            if not all(
                intent.changed_paths
                for intent in (original_intent, prepared_intent, reviewed_intent)
            ):
                raise IntentDriftError("curation diff is empty during revalidation")
        except (IntentDriftError, IntentValidationError, RepositorySafetyError):
            raise RepositorySafetyError(
                "prepared semantic intent does not match reviewed state"
            ) from None
        return reviewed_intent

    def verify_validation_base(self, expected_sha: str) -> None:
        """Verify a clean base checkout at one exact immutable revision."""
        _validate_sha(expected_sha)
        self.verify_repository()
        self._ensure_clean_preflight()
        if self._rev_parse("HEAD") != expected_sha:
            raise RepositorySafetyError(
                "validation base checkout is not at the exact prepared base head"
            )
        for relative_path in _VALIDATION_BASE_FILES:
            self._verify_regular_non_symlink_file(relative_path)

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

    def push_create_only(self, branch: str, reviewed_head: str) -> None:
        self._validate_target_branch(branch)
        _validate_sha(reviewed_head)
        current_head = self._rev_parse("HEAD")
        if current_head != reviewed_head:
            raise RepositorySafetyError(
                f"current HEAD {current_head} does not match "
                f"reviewed head {reviewed_head}"
            )

        self.verify_repository()
        if self.optional_remote_head(branch) is not None:
            raise StaleRemoteHeadError(
                "create-only discovery branch already exists remotely"
            )
        push = self._git(
            "push",
            f"--force-with-lease=refs/heads/{branch}:",
            "origin",
            f"HEAD:refs/heads/{branch}",
            network=True,
        )
        if push.returncode != 0:
            _raise_sanitized_push_error(push.stderr)

    def push_exact_with_lease(
        self,
        branch: str,
        expected_head: str,
        repair_head: str,
    ) -> None:
        """Push one exact repair commit against one exact remote branch head."""
        self._validate_target_branch(branch)
        _validate_sha(expected_head)
        _validate_sha(repair_head)
        self._ensure_clean_preflight()
        if self.current_head() != repair_head:
            raise RepositorySafetyError(
                "current HEAD does not match the exact CI repair head"
            )
        self._assert_ancestor(
            expected_head,
            repair_head,
            "CI repair push must descend from the expected remote head",
        )
        self.verify_repository()
        remote_head = self.remote_head(branch)
        if remote_head != expected_head:
            raise StaleRemoteHeadError(
                f"remote head moved: expected {expected_head}, found {remote_head}"
            )
        push = self._git(
            "push",
            f"--force-with-lease=refs/heads/{branch}:{expected_head}",
            "origin",
            f"{repair_head}:refs/heads/{branch}",
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

    def non_test_tree_digest(self, head: str) -> str:
        """Hash the exact non-repair tree, including object modes and identities."""
        _validate_sha(head)
        result = self._git("ls-tree", "-r", "-z", "--full-tree", head, "--")
        if result.returncode != 0:
            raise RepositorySafetyError("cannot inspect non-test tree")
        if result.stdout and not result.stdout.endswith("\0"):
            raise RepositorySafetyError("Git returned malformed tree metadata")
        tuples: list[tuple[str, str, str]] = []
        for record in result.stdout.removesuffix("\0").split("\0"):
            if not record:
                continue
            header, separator, path = record.partition("\t")
            fields = header.split(" ")
            if (
                not separator
                or len(fields) != 3
                or re.fullmatch(r"[0-7]{6}", fields[0]) is None
                or fields[1] not in {"blob", "commit"}
                or _SHA_PATTERN.fullmatch(fields[2]) is None
                or not path
            ):
                raise RepositorySafetyError("Git returned malformed tree metadata")
            if not is_allowed_ci_repair_path(path):
                tuples.append((fields[0], fields[2], path))
        digest = hashlib.sha256()
        for mode, oid, path in sorted(tuples):
            digest.update(mode.encode("ascii"))
            digest.update(b"\0")
            digest.update(oid.encode("ascii"))
            digest.update(b"\0")
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    def _staged_diff_entries(self) -> tuple[IntentDiffEntry, ...]:
        result = self._git(
            "diff",
            "--cached",
            "--raw",
            "--no-renames",
            "--abbrev=40",
            "-z",
            "HEAD",
            "--",
        )
        if result.returncode != 0:
            raise RepositorySafetyError(
                "cannot inspect remediation resolution metadata"
            )
        if not result.stdout:
            return ()
        tokens = result.stdout.split("\0")
        if tokens[-1] != "" or len(tokens[:-1]) % 2 != 0:
            raise RepositorySafetyError("Git returned malformed remediation metadata")
        entries: list[IntentDiffEntry] = []
        for index in range(0, len(tokens) - 1, 2):
            header = _RAW_DIFF_HEADER.fullmatch(tokens[index])
            if header is None:
                raise RepositorySafetyError(
                    "Git returned malformed remediation metadata"
                )
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

    def read_bounded_immutable_text(
        self,
        revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> str:
        """Read one immutable text blob only after a bounded size preflight."""
        _validate_sha(revision)
        _validate_git_path(path)
        if type(max_bytes) is not int or max_bytes <= 0:
            raise RepositorySafetyError("maximum Git object size must be positive")
        size_result = self._git("cat-file", "-s", f"{revision}:{path}")
        if size_result.returncode != 0:
            raise RepositorySafetyError("cannot inspect required Git object size")
        if _OBJECT_SIZE_PATTERN.fullmatch(size_result.stdout) is None:
            raise RepositorySafetyError("required Git object size is malformed")
        try:
            object_size = int(size_result.stdout)
        except ValueError:
            raise RepositorySafetyError(
                "required Git object size is malformed"
            ) from None
        if not 1 <= object_size <= max_bytes:
            raise RepositorySafetyError(
                "required Git object size is outside the allowed range"
            )
        content = self.show_text(revision, path)
        try:
            encoded_size = len(content.encode("utf-8"))
        except UnicodeEncodeError:
            raise RepositorySafetyError(
                "required Git object is not valid UTF-8 text"
            ) from None
        if not 1 <= encoded_size <= max_bytes:
            raise RepositorySafetyError(
                "required Git object content is outside the allowed range"
            )
        return content

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

    def _create_prepared_ref(
        self,
        pr_number: int,
        base_head: str,
        rebased_head: str,
    ) -> str:
        _validate_pr_number(pr_number)
        _validate_sha(base_head)
        _validate_sha(rebased_head)
        prepared_ref = (
            f"refs/snowcast-maintainer/prepared/pr-{pr_number}/"
            f"{base_head[:12]}-{rebased_head[:12]}"
        )
        result = self._git("update-ref", prepared_ref, rebased_head, "0" * 40)
        if result.returncode != 0:
            try:
                existing_head = self._resolve_backup_ref(prepared_ref)
            except RepositorySafetyError:
                existing_head = None
            if existing_head == rebased_head:
                return prepared_ref
            raise RepositorySafetyError("prepared ref cannot be recorded safely")
        return prepared_ref

    def _completed_continuation_replay(
        self,
        pull_request: PullRequest,
        prior_sync: GuardedSyncResult,
        base_head: str,
    ) -> ContinuationReplayResult:
        head = self.current_head()
        intent = build_preparation_intent_snapshot(self, base_head, head)
        if not intent.changed_paths:
            raise IntentDriftError("replayed curation diff is empty")
        prepared_ref = self._create_prepared_ref(
            pull_request.number,
            base_head,
            head,
        )
        sync = GuardedSyncResult(
            target_branch=pull_request.head_ref_name,
            original_head=pull_request.head_sha,
            rebased_head=head,
            backup_ref=prior_sync.backup_ref,
            prepared_ref=prepared_ref,
            base_head=base_head,
            merge_base=self._merge_base(base_head, pull_request.head_sha),
        )
        self._ensure_clean_preflight()
        return ContinuationReplayResult(
            result="prepared",
            base_head=base_head,
            head=head,
            sync=sync,
        )

    def _create_continuation_checkpoint(
        self,
        *,
        checkpoint_ref: str,
        squash_ref: str,
        checkpoint_head: str,
        base_head: str,
        message: str,
        failure_message: str,
    ) -> None:
        self._create_exact_ref(checkpoint_ref, checkpoint_head)
        if self._optional_ref_head(squash_ref) is not None:
            return
        tree = self._commit_tree(checkpoint_head)
        commit = self._git(
            "commit-tree",
            tree,
            "-p",
            base_head,
            "-m",
            message,
        )
        if commit.returncode != 0:
            raise RepositorySafetyError(failure_message)
        squash_head = commit.stdout.strip()
        _validate_sha(squash_head)
        self._create_exact_ref(squash_ref, squash_head)

    def _validate_curation_checkpoint(
        self,
        recovery: CurationRecoveryCheckpoint,
    ) -> str:
        return self._validate_curation_checkpoint_refs(
            checkpoint_head=recovery.checkpoint_head,
            sync=recovery.sync,
            checkpoint_ref=recovery.checkpoint_ref,
            squash_ref=recovery.squash_ref,
        )

    def _validate_curation_checkpoint_refs(
        self,
        *,
        checkpoint_head: str,
        sync: GuardedSyncResult,
        checkpoint_ref: str,
        squash_ref: str,
    ) -> str:
        resolved_checkpoint = self._optional_ref_head(checkpoint_ref)
        if resolved_checkpoint is None:
            raise CurationCheckpointIntegrityError(
                "curation checkpoint ref cannot be resolved"
            )
        self._verify_commit(resolved_checkpoint)
        if resolved_checkpoint != checkpoint_head:
            raise CurationCheckpointIntegrityError(
                "curation checkpoint ref no longer matches its head"
            )
        squash_head = self._optional_ref_head(squash_ref)
        if squash_head is None:
            raise CurationCheckpointIntegrityError(
                "curation replay ref cannot be resolved"
            )
        self._verify_commit(squash_head)
        if self._commit_tree(squash_head) != self._commit_tree(resolved_checkpoint):
            raise CurationCheckpointIntegrityError(
                "curation replay tree no longer matches checkpoint"
            )
        parents = self._git("show", "-s", "--format=%P", squash_head)
        if parents.returncode != 0 or parents.stdout.strip() != sync.base_head:
            raise CurationCheckpointIntegrityError(
                "curation replay parent no longer matches base"
            )
        try:
            checkpoint_intent = build_preparation_intent_snapshot(
                self,
                sync.base_head,
                resolved_checkpoint,
            )
            replay_intent = build_preparation_intent_snapshot(
                self,
                sync.base_head,
                squash_head,
            )
        except (IntentDriftError, IntentValidationError):
            raise CurationCheckpointIntegrityError(
                "curation checkpoint has unsafe immutable intent"
            ) from None
        if checkpoint_intent.diff_entries != replay_intent.diff_entries:
            raise CurationCheckpointIntegrityError(
                "curation replay diff no longer matches checkpoint"
            )
        return squash_head

    def _commit_tree(self, revision: str) -> str:
        _validate_sha(revision)
        result = self._git("show", "-s", "--format=%T", revision)
        if result.returncode != 0:
            raise RepositorySafetyError("cannot resolve continuation commit tree")
        tree = result.stdout.strip()
        _validate_sha(tree)
        return tree

    def _create_exact_ref(self, ref: str, head: str) -> None:
        _validate_sha(head)
        result = self._git("update-ref", ref, head, "0" * 40)
        if result.returncode == 0:
            return
        if self._optional_ref_head(ref) == head:
            return
        raise RepositorySafetyError("continuation ref collision or creation failure")

    def _optional_ref_head(self, ref: str) -> str | None:
        result = self._git("rev-parse", "--verify", ref)
        if result.returncode != 0:
            return None
        head = result.stdout.strip()
        _validate_sha(head)
        return head

    def _resolve_ref(self, ref: str) -> str:
        head = self._optional_ref_head(ref)
        if head is None:
            raise RepositorySafetyError("continuation ref cannot be resolved")
        return head

    def _nul_paths(self, *arguments: str) -> tuple[str, ...]:
        result = self._git(*arguments)
        if result.returncode != 0:
            raise RepositorySafetyError("cannot inspect continuation paths")
        if not result.stdout:
            return ()
        if not result.stdout.endswith("\0"):
            raise RepositorySafetyError("Git returned malformed continuation paths")
        paths = tuple(result.stdout[:-1].split("\0"))
        for path in paths:
            _validate_git_path(path)
        return tuple(sorted(paths))

    def _verify_commit(self, sha: str) -> None:
        _validate_sha(sha)
        result = self._git("cat-file", "-e", f"{sha}^{{commit}}")
        if result.returncode != 0:
            raise RepositorySafetyError("prepared revision is not an immutable commit")

    def _merge_base(self, left: str, right: str) -> str:
        _validate_sha(left)
        _validate_sha(right)
        result = self._git("merge-base", left, right)
        if result.returncode != 0:
            raise RepositorySafetyError("cannot recompute prepared merge base")
        merge_base = result.stdout.strip()
        _validate_sha(merge_base)
        return merge_base

    def _assert_ancestor(self, ancestor: str, descendant: str, message: str) -> None:
        result = self._git("merge-base", "--is-ancestor", ancestor, descendant)
        if result.returncode == 1:
            raise RepositorySafetyError(message)
        if result.returncode != 0:
            raise RepositorySafetyError("cannot verify prepared commit ancestry")

    def _verify_regular_non_symlink_file(self, relative_path: str) -> None:
        current = self.root
        parts = PurePosixPath(relative_path).parts
        for index, part in enumerate(parts):
            current /= part
            try:
                mode = current.lstat().st_mode
            except OSError as error:
                raise RepositorySafetyError(
                    "required validation base path must be a regular non-symlink file"
                ) from error
            is_last = index == len(parts) - 1
            if (
                stat.S_ISLNK(mode)
                or (is_last and not stat.S_ISREG(mode))
                or (not is_last and not stat.S_ISDIR(mode))
            ):
                raise RepositorySafetyError(
                    "required validation base path must be a regular non-symlink file"
                )

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

    def _cherry_pick_in_progress(self) -> bool:
        result = self._git("rev-parse", "--git-path", "CHERRY_PICK_HEAD")
        if result.returncode != 0:
            raise RepositorySafetyError("cannot inspect Git cherry-pick state")
        state_path = Path(result.stdout.strip())
        if not state_path.is_absolute():
            state_path = self.root / state_path
        return state_path.exists()

    def _abort_cherry_pick_if_active(self) -> None:
        if not self._cherry_pick_in_progress():
            return
        abort = self._git("cherry-pick", "--abort")
        if abort.returncode != 0 or self._cherry_pick_in_progress():
            raise RepositorySafetyError(
                "active continuation replay could not be aborted safely"
            )

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
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        argv = ("git", *arguments)
        return self._command(argv, network=network, stdin=stdin)

    def _command(
        self,
        argv: tuple[str, ...],
        *,
        network: bool = False,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        timeout = NETWORK_GIT_TIMEOUT_SECONDS if network else LOCAL_GIT_TIMEOUT_SECONDS
        try:
            return self._runner.run(
                argv,
                cwd=self.root,
                timeout=timeout,
                stdin=stdin,
            )
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
    if pull_request.lifecycle_state != "OPEN":
        raise RepositorySafetyError("PR must be open")
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


def _validate_tree_digest(digest: str) -> None:
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise RepositorySafetyError("tree digest must be lowercase 64-hex")


def _validate_ci_repair_ref(
    repair_ref: str,
    pr_number: int,
    current_head: str,
    repair_head: str,
) -> None:
    _validate_pr_number(pr_number)
    _validate_sha(current_head)
    _validate_sha(repair_head)
    if not isinstance(repair_ref, str):
        raise RepositorySafetyError("CI repair ref is malformed")
    match = _CI_REPAIR_REF.fullmatch(repair_ref)
    expected_prefix = f"refs/snowcast-maintainer/ci-repairs/pr-{pr_number}/"
    if (
        match is None
        or not repair_ref.startswith(expected_prefix)
        or match.group("current") != current_head[:12]
        or match.group("repair") != repair_head[:12]
    ):
        raise RepositorySafetyError(
            "CI repair ref is not bound to the checkpointed heads"
        )


def _validate_backup_ref(backup_ref: str, original_head: str) -> None:
    if not isinstance(backup_ref, str):
        raise RepositorySafetyError("backup ref is malformed")
    match = _BACKUP_REF.fullmatch(backup_ref)
    if match is None or match.group("prefix") != original_head[:12]:
        raise RepositorySafetyError("backup ref is not bound to original head")


def _validate_prepared_ref(
    prepared_ref: str,
    base_head: str,
    rebased_head: str,
    pr_number: int,
) -> None:
    _validate_pr_number(pr_number)
    if not isinstance(prepared_ref, str):
        raise RepositorySafetyError("prepared ref is malformed")
    match = _PREPARED_REF.fullmatch(prepared_ref)
    expected_prefix = f"refs/snowcast-maintainer/prepared/pr-{pr_number}/"
    if (
        match is None
        or not prepared_ref.startswith(expected_prefix)
        or match.group("base") != base_head[:12]
        or match.group("rebased") != rebased_head[:12]
    ):
        raise RepositorySafetyError("prepared ref is not bound to prepared heads")


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
    if not is_safe_codex_branch(branch):
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

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.data.catalog_curation import (
    load_catalog_curation_report,
    validate_catalog_curation_report,
)
from app.data.catalog_curation_backlog import (
    validate_catalog_curation_backlog_refs,
)
from app.data.catalog_curation_reconciliation import (
    reconcile_catalog_curation_report,
)
from app.data.catalog_loader import load_catalog_from_path
from app.data.catalog_policy import catalog_policy_issues
from ops.maintainer import LABEL_DEFINITIONS, SUMMARY_MARKER
from ops.maintainer.curation import (
    ValidationExecutionError,
    execute_curation_validation,
    is_eligible_for_deep_curation,
    next_cycle_decision,
    reconcile_waiting_ci,
    route_approved_proposal,
    select_curation_work,
)
from ops.maintainer.discovery import (
    CoverageCandidate,
    CoverageRegistry,
    DiscoveryCandidate,
    ProposalRecord,
    catalog_entity_keys,
    discovery_subregion,
    parse_catalog_backlog,
    proposal_record_from_pull_request,
    render_candidate_discovery_origin,
    require_publication_ready,
    select_discovery_candidate,
    verify_origin_cleanup,
    with_official_urls,
)
from ops.maintainer.git_ops import (
    GitAuthenticationError,
    GitOperationTimeoutError,
    GitPushRejectedError,
    GitRemotePolicyError,
    GitRepository,
    GitTransportError,
    GuardedSyncResult,
    RebaseConflictError,
    RepositorySafetyError,
    StaleRemoteHeadError,
)
from ops.maintainer.github import (
    DEFAULT_GH_CONFIG_DIR,
    TRUSTED_MAINTAINER_LOGIN,
    GitHubClient,
    GitHubError,
)
from ops.maintainer.intent import (
    BACKLOG_PATH,
    CATALOG_PATH,
    CURATION_REPORT_PREFIX,
    TRUST_MANIFEST_PATH,
    IntentDriftError,
    IntentSnapshot,
    IntentValidationError,
    is_allowed_curation_path,
)
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)
from ops.maintainer.publication import (
    MaintainerSummary,
    parse_machine_state,
    publish_state,
)
from ops.maintainer.runtime import (
    HeartbeatDetails,
    LockBusyError,
    RunLease,
    RunLeaseError,
)

_SAFE_JSON_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_REPORT_PATH = re.compile(r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_PROPOSAL_BRANCH = re.compile(r"^codex/catalog-curation-[a-z0-9]+(?:-+[a-z0-9]+)*$")
_MAX_ARTIFACT_BYTES = 1_000_000


def _push_authorization_id(
    pr_number: int,
    selected_head: str,
    reviewed_head: str,
    prepared: GuardedSyncResult,
) -> str:
    identity = {
        "pr_number": pr_number,
        "selected_head": selected_head,
        "reviewed_head": reviewed_head,
        "prepared": prepared.model_dump(mode="json"),
    }
    encoded = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_lineage_seed(selected_head: str, lineage_state: MachineState) -> None:
    if lineage_state.head_sha != selected_head:
        raise ValueError("lineage seed head mismatch")
    if lineage_state.completed_cycles < 1:
        raise ValueError("lineage seed must include the current run")
    if lineage_state.last_publication != "none":
        raise ValueError("lineage seed must be unpublished")
    candidate_metadata = (
        lineage_state.candidate_origin_fingerprint,
        lineage_state.candidate_fingerprint,
        lineage_state.regional_graph_key,
    )
    if lineage_state.candidate_key is not None and not all(
        value is not None for value in candidate_metadata
    ):
        raise ValueError("candidate lineage metadata is incomplete")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _AttemptArtifact(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    attempt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    lineage_state: MachineState

    @model_validator(mode="after")
    def validate_attempt(self) -> _AttemptArtifact:
        _validate_lineage_seed(self.selected_head, self.lineage_state)
        return self


class _PreparedArtifact(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    attempt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    prepared: GuardedSyncResult
    lineage_state: MachineState

    @model_validator(mode="after")
    def validate_selected_head(self) -> _PreparedArtifact:
        if self.selected_head != self.prepared.original_head:
            raise ValueError("prepared artifact head mismatch")
        _validate_lineage_seed(self.selected_head, self.lineage_state)
        return self


class _ValidatedArtifact(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    report_path: str
    prepared: GuardedSyncResult

    @model_validator(mode="after")
    def validate_lineage(self) -> _ValidatedArtifact:
        if self.selected_head != self.prepared.original_head:
            raise ValueError("validated artifact lineage mismatch")
        return self


class _PushJournal(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    phase: Literal["authorized", "pushed"]
    authorization_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    prepared: GuardedSyncResult

    @model_validator(mode="after")
    def validate_lineage(self) -> _PushJournal:
        if self.selected_head != self.prepared.original_head:
            raise ValueError("push journal lineage mismatch")
        expected = _push_authorization_id(
            self.pr_number,
            self.selected_head,
            self.reviewed_head,
            self.prepared,
        )
        if self.authorization_id != expected:
            raise ValueError("push journal authorization mismatch")
        return self


class _VisibleSummary(_StrictModel):
    state: MaintainerState
    result: str = Field(min_length=1, max_length=4_000)
    ci_status: str = Field(min_length=1, max_length=1_000)
    owner_action: str = Field(min_length=1, max_length=2_000)
    caveats: tuple[str, ...] = Field(default=(), max_length=20)


class _PublicationArtifact(_StrictModel):
    summary: _VisibleSummary
    managed_body: str = Field(min_length=1, max_length=100_000)


class _ProposalVerification(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    candidate_key: str
    candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    changed_paths: frozenset[str]
    catalog_targets: frozenset[str]
    report_targets: frozenset[str]
    removed_backlog_markers: frozenset[str]
    report_path: str
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class _Dependencies:
    github: object
    repository: object
    base_repository: object | None
    validation_executor: Callable[..., object]
    repository_root: Path
    today: Callable[[], date]


class CLIInputError(ValueError):
    """Raised instead of allowing argparse to emit non-JSON errors."""


class _JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CLIInputError(message)


def _default_state_dir() -> Path:
    return Path.home() / ".local" / "state" / "snowcast-maintainer"


def _parser() -> argparse.ArgumentParser:
    parser = _JSONArgumentParser(prog="snowcast-maintainer")
    parser.add_argument("--state-dir", type=Path, default=_default_state_dir())
    parser.add_argument(
        "--gh-config-dir",
        type=Path,
        default=DEFAULT_GH_CONFIG_DIR,
    )
    families = parser.add_subparsers(dest="family", required=True)

    lock = families.add_parser("lock")
    lock_commands = lock.add_subparsers(dest="command", required=True)
    acquire = lock_commands.add_parser("acquire")
    acquire.add_argument("worker", choices=("curation", "discovery"))
    heartbeat = lock_commands.add_parser("heartbeat")
    heartbeat.add_argument("--phase", required=True)
    lock_commands.add_parser("release")

    github = families.add_parser("github")
    github_commands = github.add_subparsers(dest="command", required=True)
    github_commands.add_parser("ensure-labels")

    curation = families.add_parser("curation")
    curation_commands = curation.add_subparsers(dest="command", required=True)
    curation_commands.add_parser("inventory")
    prepare = curation_commands.add_parser("prepare")
    prepare.add_argument("--pr", type=int, required=True)
    validate = curation_commands.add_parser("validate")
    validate.add_argument("--pr", type=int, required=True)
    validate.add_argument("--report", required=True)
    validate.add_argument("--base-dir", type=Path, required=True)
    push = curation_commands.add_parser("push")
    push.add_argument("--pr", type=int, required=True)
    push.add_argument("--original-head", required=True)
    publish = curation_commands.add_parser("publish")
    publish.add_argument("--pr", type=int, required=True)
    publish.add_argument("--state", required=True)
    publish.add_argument("--summary-file", type=Path, required=True)

    discovery = families.add_parser("discovery")
    discovery_commands = discovery.add_subparsers(dest="command", required=True)
    validate_registry = discovery_commands.add_parser("validate-registry")
    validate_registry.add_argument("--registry", type=Path, required=True)
    next_candidate = discovery_commands.add_parser("next")
    next_candidate.add_argument("--output", type=Path, required=True)
    add_source = discovery_commands.add_parser("add-source")
    add_source.add_argument("--candidate-file", type=Path, required=True)
    add_source.add_argument("--official-url", required=True)
    nominate = discovery_commands.add_parser("nominate")
    nominate.add_argument("--output", type=Path, required=True)
    nominate.add_argument("--candidate-key", required=True)
    nominate.add_argument("--display-name", required=True)
    nominate.add_argument("--country", required=True)
    nominate.add_argument("--alpine-subregion", required=True)
    nominate.add_argument("--regional-graph-key", required=True)
    nominate.add_argument("--official-url", required=True)
    verify = discovery_commands.add_parser("verify-proposal")
    verify.add_argument("--candidate-file", type=Path, required=True)
    verify.add_argument("--base", required=True)
    verify.add_argument("--head", required=True)
    publish_proposal = discovery_commands.add_parser("publish-proposal")
    publish_proposal.add_argument("--pr", type=int, required=True)
    publish_proposal.add_argument("--candidate-file", type=Path, required=True)
    return parser


def _owned_lease(state_dir: Path) -> RunLease:
    lease = RunLease.load(state_dir)
    lease.assert_owner(lease.token)
    return lease


def _artifact_path(state_dir: Path, name: str) -> Path:
    if _SAFE_JSON_NAME.fullmatch(name) is None:
        raise CLIInputError("artifact filename is invalid")
    return state_dir / name


def _candidate_path(state_dir: Path, supplied: Path) -> Path:
    state_root = state_dir.resolve()
    path = supplied if supplied.is_absolute() else state_root / supplied
    if _SAFE_JSON_NAME.fullmatch(path.name) is None:
        raise CLIInputError("candidate filename is invalid")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError:
        raise CLIInputError("candidate parent directory is unavailable") from None
    if parent != state_root:
        raise CLIInputError("candidate artifact must be inside the state directory")
    return path


def _read_text(path: Path) -> str:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CLIInputError("artifact must be a regular non-symlink file")
        if metadata.st_size > _MAX_ARTIFACT_BYTES:
            raise CLIInputError("artifact exceeds size limit")
        with os.fdopen(descriptor, encoding="utf-8") as artifact:
            descriptor = None
            content = artifact.read(_MAX_ARTIFACT_BYTES + 1)
        if len(content.encode("utf-8")) > _MAX_ARTIFACT_BYTES:
            raise CLIInputError("artifact exceeds size limit")
        return content
    except UnicodeDecodeError:
        raise CLIInputError("artifact must be UTF-8") from None
    except OSError:
        raise CLIInputError("artifact cannot be read") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_json_model(path: Path, model: type[_StrictModel]) -> _StrictModel:
    try:
        return model.model_validate_json(_read_text(path), strict=True)
    except ValidationError:
        raise CLIInputError("artifact does not match its schema") from None


def _write_json(path: Path, payload: BaseModel, lease: RunLease) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            os.chmod(temporary_path, 0o600)
            temporary.write(payload.model_dump_json())
            temporary.flush()
            os.fsync(temporary.fileno())
        lease.assert_owner(lease.token)
        if path.exists() and path.is_symlink():
            raise CLIInputError("artifact target must not be a symlink")
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    except OSError:
        raise CLIInputError("artifact cannot be written") from None
    finally:
        temporary_path.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _prepared_path(state_dir: Path, pr_number: int) -> Path:
    return _artifact_path(state_dir, f"curation-pr-{pr_number}-prepared.json")


def _attempt_path(state_dir: Path, pr_number: int) -> Path:
    return _artifact_path(state_dir, f"curation-pr-{pr_number}-attempt.json")


def _validated_path(state_dir: Path, pr_number: int) -> Path:
    return _artifact_path(state_dir, f"curation-pr-{pr_number}-validated.json")


def _push_journal_path(
    state_dir: Path,
    pr_number: int,
    authorization_id: str,
) -> Path:
    if re.fullmatch(r"[0-9a-f]{64}", authorization_id) is None:
        raise CLIInputError("push authorization identity is invalid")
    return _artifact_path(
        state_dir,
        f"curation-pr-{pr_number}-push-{authorization_id}.json",
    )


def _verification_path(state_dir: Path, candidate: DiscoveryCandidate) -> Path:
    safe_key = candidate.key.replace(":", "-")
    return _artifact_path(state_dir, f"proposal-{safe_key}-verified.json")


def _load_candidate(state_dir: Path, supplied: Path) -> DiscoveryCandidate:
    path = _candidate_path(state_dir, supplied)
    try:
        return DiscoveryCandidate.model_validate_json(_read_text(path), strict=True)
    except ValidationError:
        raise CLIInputError("candidate artifact is invalid") from None


def _load_registry(path: Path) -> CoverageRegistry:
    try:
        return CoverageRegistry.model_validate_json(_read_text(path), strict=True)
    except ValidationError:
        raise CLIInputError("coverage registry is invalid") from None


def _proposal_records(
    github: object,
    pull_requests: Sequence[PullRequest],
) -> list[ProposalRecord]:
    records: list[ProposalRecord] = []
    for pull_request in pull_requests:
        comments = github.list_issue_comments(pull_request.number)
        records.append(proposal_record_from_pull_request(pull_request, comments))
    return records


def _declined_fingerprints(
    github: object,
    *,
    catalog_keys: set[str],
) -> set[tuple[str, str]]:
    declined: set[tuple[str, str]] = set()
    seen_prs: set[int] = set()
    for pull_request in github.list_closed_proposal_pull_requests():
        if pull_request.number in seen_prs:
            raise CLIInputError("duplicate closed proposal pull request")
        seen_prs.add(pull_request.number)
        if pull_request.lifecycle_state != "CLOSED":
            continue
        if (
            pull_request.is_cross_repository
            or pull_request.head_repository_owner != "lampssy"
            or pull_request.base_ref_name != "main"
            or pull_request.url.host != "github.com"
            or pull_request.url.path
            != (f"/lampssy/ai-sports-travel-planner/pull/{pull_request.number}")
        ):
            raise CLIInputError("closed proposal provenance is invalid")
        comments = github.list_issue_comments(pull_request.number)
        record = proposal_record_from_pull_request(pull_request, comments)
        if (
            not record.is_discovery_lineage
            or not record.is_proposal
            or record.candidate_key is None
            or record.origin_fingerprint is None
            or record.candidate_key in catalog_keys
        ):
            continue
        declined.add((record.candidate_key, record.origin_fingerprint))
    return declined


def _machine_state(github: object, pull_request: PullRequest) -> MachineState | None:
    marked = [
        comment
        for comment in github.list_issue_comments(pull_request.number)
        if comment.author_login == TRUSTED_MAINTAINER_LOGIN
        and SUMMARY_MARKER in comment.body
    ]
    if not marked:
        return None
    if len(marked) != 1:
        raise CLIInputError("pull request has ambiguous maintainer state")
    machine = parse_machine_state(marked[0].body)
    if machine is None:
        raise CLIInputError("pull request maintainer state is malformed")
    return machine


def _pr_payload(pull_request: PullRequest, lane: MaintainerLane) -> dict[str, object]:
    return {
        "number": pull_request.number,
        "head_sha": pull_request.head_sha,
        "lane": lane.value,
    }


def _discovery_state(
    dependencies: _Dependencies,
) -> tuple[
    list[DiscoveryCandidate],
    CoverageRegistry,
    set[str],
    list[ProposalRecord],
    set[tuple[str, str]],
]:
    root = dependencies.repository_root
    backlog = parse_catalog_backlog(_read_text(root / "docs/product-backlog.md"))
    registry = _load_registry(
        root / "docs/catalog-discovery/alpine-coverage-registry.json"
    )
    catalog_keys = catalog_entity_keys(root / "app/data/catalog.json")
    pull_requests = dependencies.github.list_open_pull_requests()
    records = _proposal_records(dependencies.github, pull_requests)
    return (
        backlog,
        registry,
        catalog_keys,
        records,
        _declined_fingerprints(
            dependencies.github,
            catalog_keys=catalog_keys,
        ),
    )


def _curation_inventory(dependencies: _Dependencies) -> dict[str, object]:
    work = select_curation_work(dependencies.github.list_open_pull_requests())
    waiting: list[dict[str, object]] = []
    for pull_request in work.waiting_ci:
        decision = reconcile_waiting_ci(
            pull_request,
            _machine_state(dependencies.github, pull_request),
        )
        waiting.append(
            {
                "number": pull_request.number,
                "head_sha": pull_request.head_sha,
                "state": decision.state.value,
                "reason": decision.reason.value,
            }
        )
    deep = (
        None
        if work.deep_pr is None
        else _pr_payload(work.deep_pr, MaintainerLane.CATALOG_CURATION)
    )
    return {"status": "inventory", "waiting_ci": waiting, "deep_pr": deep}


def _curation_prepare(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    work = select_curation_work(dependencies.github.list_open_pull_requests())
    selected = work.deep_pr
    if selected is None or selected.number != args.pr:
        raise CLIInputError("requested pull request is not the current deep selection")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if pull_request != selected:
        raise CLIInputError("pull request changed after deterministic selection")
    routed_proposal = route_approved_proposal(pull_request)
    if not (is_eligible_for_deep_curation(pull_request) or routed_proposal is not None):
        raise CLIInputError("pull request is outside curation policy")
    machine = _machine_state(dependencies.github, pull_request)
    if routed_proposal is not None and (
        machine is None or machine.candidate_key is None
    ):
        raise CLIInputError("approved proposal is missing discovery lineage")
    if machine is not None:
        if machine.head_sha != pull_request.head_sha:
            raise CLIInputError("pull request lineage does not match selected head")
        if machine.last_publication != "complete":
            raise CLIInputError("pull request lineage publication is incomplete")
        candidate_metadata = (
            machine.candidate_origin_fingerprint,
            machine.candidate_fingerprint,
            machine.regional_graph_key,
        )
        if machine.candidate_key is not None and not all(
            value is not None for value in candidate_metadata
        ):
            raise CLIInputError("pull request candidate lineage is incomplete")
        cycle = next_cycle_decision(machine, cycles_this_run=0)
        if cycle.state is not MaintainerState.WORKING:
            raise CLIInputError("pull request lineage remediation limit reached")
        lineage_payload = machine.model_dump(mode="json")
        lineage_payload.update(
            {
                "completed_cycles": machine.completed_cycles + 1,
                "last_publication": "none",
            }
        )
        lineage_state = MachineState.model_validate(lineage_payload, strict=True)
    else:
        lineage_state = MachineState(
            head_sha=pull_request.head_sha,
            lineage_id=f"catalog-curation-pr-{pull_request.number}",
            completed_cycles=1,
            last_publication="none",
        )
    attempt = _AttemptArtifact(
        attempt_id=secrets.token_hex(32),
        pr_number=pull_request.number,
        selected_head=pull_request.head_sha,
        lineage_state=lineage_state,
    )
    _write_json(_attempt_path(args.state_dir, args.pr), attempt, lease)
    lease.assert_owner(lease.token)
    prepared = dependencies.repository.prepare_guarded_sync(pull_request)
    artifact = _PreparedArtifact(
        attempt_id=attempt.attempt_id,
        pr_number=pull_request.number,
        selected_head=pull_request.head_sha,
        prepared=prepared,
        lineage_state=lineage_state,
    )
    _write_json(_prepared_path(args.state_dir, args.pr), artifact, lease)
    return {
        "status": "prepared",
        "original_head": prepared.original_head,
        "rebased_head": prepared.rebased_head,
        "base_head": prepared.base_head,
        "backup_ref": prepared.backup_ref,
    }


def _curation_validate(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    if _REPORT_PATH.fullmatch(args.report) is None:
        raise CLIInputError("curation report path is invalid")
    _attempt, raw = _load_promoted_prepare(args.state_dir, args.pr)
    pull_request = dependencies.github.get_pull_request(args.pr)
    if (
        pull_request.head_sha != raw.selected_head
        or args.report not in pull_request.changed_paths
    ):
        raise CLIInputError("pull request no longer matches prepared state")
    reviewed_head = dependencies.repository.current_head()
    base_repository = dependencies.base_repository
    if base_repository is None:
        base_repository = GitRepository(args.base_dir.resolve())
    elif base_repository.root != args.base_dir.resolve():
        raise CLIInputError("base repository does not match requested directory")
    lease.assert_owner(lease.token)
    result = dependencies.validation_executor(
        pull_request,
        raw.prepared,
        reviewed_head,
        dependencies.repository,
        base_repository,
    )
    artifact = _ValidatedArtifact(
        pr_number=args.pr,
        selected_head=raw.selected_head,
        reviewed_head=reviewed_head,
        report_path=args.report,
        prepared=raw.prepared,
    )
    _write_json(_validated_path(args.state_dir, args.pr), artifact, lease)
    return {
        "status": "validated",
        "reviewed_head": reviewed_head,
        "commands_completed": result.commands_completed,
    }


def _curation_push(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    raw = _read_json_model(
        _validated_path(args.state_dir, args.pr),
        _ValidatedArtifact,
    )
    if not isinstance(raw, _ValidatedArtifact):
        raise CLIInputError("validated artifact is invalid")
    _attempt, prepared_artifact = _load_promoted_prepare(
        args.state_dir,
        args.pr,
    )
    if (
        prepared_artifact.selected_head != raw.selected_head
        or prepared_artifact.prepared != raw.prepared
    ):
        raise CLIInputError("validated state does not match prepared attempt")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if (
        args.original_head != raw.selected_head
        or raw.prepared.original_head != raw.selected_head
    ):
        raise CLIInputError("push state no longer matches selected head")
    if pull_request.head_sha not in {raw.selected_head, raw.reviewed_head}:
        raise CLIInputError("pull request moved outside the push authorization")
    if not (
        is_eligible_for_deep_curation(pull_request)
        or route_approved_proposal(pull_request) is not None
    ):
        raise CLIInputError("pull request is outside curation push policy")

    authorization_id = _push_authorization_id(
        args.pr,
        raw.selected_head,
        raw.reviewed_head,
        raw.prepared,
    )
    journal_path = _push_journal_path(
        args.state_dir,
        args.pr,
        authorization_id,
    )
    expected = _PushJournal(
        phase="authorized",
        authorization_id=authorization_id,
        pr_number=args.pr,
        selected_head=raw.selected_head,
        reviewed_head=raw.reviewed_head,
        prepared=raw.prepared,
    )
    try:
        journal_path.lstat()
    except FileNotFoundError:
        _write_json(journal_path, expected, lease)
        journal = expected
    except OSError:
        raise CLIInputError("cannot inspect push authorization state") from None
    else:
        loaded = _read_json_model(journal_path, _PushJournal)
        if not isinstance(loaded, _PushJournal):
            raise CLIInputError("push journal is invalid")
        if loaded.model_copy(update={"phase": "authorized"}) != expected:
            raise CLIInputError("push journal does not match validated state")
        if loaded.phase == "pushed":
            raise CLIInputError("validated push authorization was already consumed")
        journal = loaded

    lease.assert_owner(lease.token)
    if raw.reviewed_head == raw.selected_head:
        if raw.prepared.rebased_head != raw.selected_head:
            raise CLIInputError("no-op push has inconsistent prepared lineage")
        if dependencies.repository.current_head() != raw.reviewed_head:
            raise CLIInputError("no-op push does not match current local head")
        remote_head = dependencies.repository.remote_head(raw.prepared.target_branch)
        if remote_head != raw.selected_head:
            raise CLIInputError("no-op push does not match current remote head")
    else:
        remote_head = dependencies.repository.remote_head(raw.prepared.target_branch)
        if remote_head == raw.selected_head:
            if pull_request.head_sha != raw.selected_head:
                raise CLIInputError("remote and pull request heads disagree")
            dependencies.repository.push_with_lease(raw.prepared, raw.reviewed_head)
        elif remote_head != raw.reviewed_head:
            raise CLIInputError("remote head does not match push authorization")

    pushed = journal.model_copy(update={"phase": "pushed"})
    _write_json(journal_path, pushed, lease)
    return {"status": "pushed", "head_sha": raw.reviewed_head}


def _discovery_next(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    output = _candidate_path(args.state_dir, args.output)
    backlog, registry, catalog_keys, records, declined = _discovery_state(dependencies)
    candidate = select_discovery_candidate(
        backlog,
        registry,
        catalog_keys,
        records,
        declined,
    )
    if candidate is None:
        proposal_count = sum(
            record.lifecycle_state == "OPEN"
            and record.is_discovery_lineage
            and record.is_proposal
            for record in records
        )
        if proposal_count >= 3:
            return {
                "status": "no-candidate",
                "reason": "proposal-cap",
            }
        return {
            "status": "no-candidate",
            "reason": "queue-exhausted",
            "subregion": discovery_subregion(dependencies.today()),
        }
    _write_json(output, candidate, lease)
    return {
        "status": "candidate-selected",
        "candidate_key": candidate.key,
        "candidate_file": output.name,
    }


def _discovery_add_source(
    args: argparse.Namespace,
    lease: RunLease,
) -> dict[str, object]:
    candidate_path = _candidate_path(args.state_dir, args.candidate_file)
    candidate = _load_candidate(args.state_dir, candidate_path)
    updated = with_official_urls(
        candidate,
        (*candidate.official_urls, args.official_url),
    )
    _write_json(candidate_path, updated, lease)
    return {
        "status": "source-added",
        "candidate_key": updated.key,
        "fingerprint": updated.fingerprint,
    }


def _discovery_nominate(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    output = _candidate_path(args.state_dir, args.output)
    expected_subregion = discovery_subregion(dependencies.today())
    if args.alpine_subregion != expected_subregion:
        raise CLIInputError("nomination is outside this run's bounded subregion")
    kind, separator, _identifier = args.candidate_key.partition(":")
    if not separator:
        raise CLIInputError("candidate key is invalid")
    entry = CoverageCandidate.model_validate(
        {
            "candidate_key": args.candidate_key,
            "display_name": args.display_name,
            "country": args.country,
            "alpine_subregion": args.alpine_subregion,
            "regional_graph_key": args.regional_graph_key,
            "candidate_kind": kind,
            "official_urls": (args.official_url,),
        },
        strict=True,
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
    _backlog, registry, catalog_keys, records, declined = _discovery_state(dependencies)
    if any(item.candidate_key == candidate.key for item in registry.entries):
        raise CLIInputError("candidate already exists in registry")
    selected = select_discovery_candidate(
        [candidate],
        CoverageRegistry(schema_version=1, entries=()),
        catalog_keys,
        records,
        declined,
    )
    if selected != candidate:
        raise CLIInputError("candidate is already covered or overlaps active work")
    _write_json(output, candidate, lease)
    return {
        "status": "candidate-nominated",
        "candidate_key": candidate.key,
        "fingerprint": candidate.fingerprint,
    }


def _load_attempt_artifact(
    state_dir: Path,
    pr_number: int,
) -> _AttemptArtifact:
    raw = _read_json_model(
        _attempt_path(state_dir, pr_number),
        _AttemptArtifact,
    )
    if not isinstance(raw, _AttemptArtifact) or raw.pr_number != pr_number:
        raise CLIInputError("curation attempt artifact is invalid")
    return raw


def _load_promoted_prepare(
    state_dir: Path,
    pr_number: int,
) -> tuple[_AttemptArtifact, _PreparedArtifact]:
    attempt = _load_attempt_artifact(state_dir, pr_number)
    raw = _read_json_model(
        _prepared_path(state_dir, pr_number),
        _PreparedArtifact,
    )
    if not isinstance(raw, _PreparedArtifact):
        raise CLIInputError("prepared curation artifact is invalid")
    if (
        raw.pr_number != pr_number
        or raw.attempt_id != attempt.attempt_id
        or raw.selected_head != attempt.selected_head
        or raw.lineage_state != attempt.lineage_state
    ):
        raise CLIInputError("prepared curation artifact does not match attempt")
    return attempt, raw


def _load_push_evidence(
    state_dir: Path,
    pr_number: int,
    pull_request: PullRequest,
) -> tuple[_PreparedArtifact, _ValidatedArtifact, _PushJournal]:
    _attempt, prepared_raw = _load_promoted_prepare(state_dir, pr_number)
    validated_raw = _read_json_model(
        _validated_path(state_dir, pr_number),
        _ValidatedArtifact,
    )
    if not isinstance(validated_raw, _ValidatedArtifact):
        raise CLIInputError("curation evidence artifact is invalid")
    authorization_id = _push_authorization_id(
        pr_number,
        validated_raw.selected_head,
        validated_raw.reviewed_head,
        validated_raw.prepared,
    )
    pushed_raw = _read_json_model(
        _push_journal_path(state_dir, pr_number, authorization_id),
        _PushJournal,
    )
    if not isinstance(pushed_raw, _PushJournal):
        raise CLIInputError("curation push journal is invalid")
    if (
        prepared_raw.pr_number != pr_number
        or validated_raw.pr_number != pr_number
        or pushed_raw.pr_number != pr_number
        or prepared_raw.selected_head != validated_raw.selected_head
        or prepared_raw.prepared != validated_raw.prepared
        or validated_raw.selected_head != pushed_raw.selected_head
        or validated_raw.reviewed_head != pushed_raw.reviewed_head
        or validated_raw.prepared != pushed_raw.prepared
        or pushed_raw.authorization_id != authorization_id
        or pushed_raw.phase != "pushed"
        or pushed_raw.reviewed_head != pull_request.head_sha
    ):
        raise CLIInputError("curation evidence does not match pull request head")
    return prepared_raw, validated_raw, pushed_raw


def _load_prepared_lineage(
    state_dir: Path,
    pr_number: int,
    pull_request: PullRequest,
) -> MachineState:
    _attempt, prepared_raw = _load_promoted_prepare(state_dir, pr_number)
    if pull_request.head_sha == prepared_raw.selected_head:
        return prepared_raw.lineage_state
    pushed_prepared, _validated, _journal = _load_push_evidence(
        state_dir,
        pr_number,
        pull_request,
    )
    if pushed_prepared != prepared_raw:
        raise CLIInputError("prepared lineage does not match pushed evidence")
    return prepared_raw.lineage_state


def _load_safe_stop_lineage(
    state_dir: Path,
    pr_number: int,
    pull_request: PullRequest,
) -> MachineState:
    attempt = _load_attempt_artifact(state_dir, pr_number)
    if attempt.selected_head == pull_request.head_sha:
        return attempt.lineage_state
    return _load_prepared_lineage(state_dir, pr_number, pull_request)


def _published_machine_state(
    lineage: MachineState,
    pull_request: PullRequest,
) -> MachineState:
    lineage_payload = lineage.model_dump(mode="json")
    lineage_payload.update(
        {
            "head_sha": pull_request.head_sha,
            "last_publication": "complete",
        }
    )
    return MachineState.model_validate(lineage_payload, strict=True)


def _curation_publish(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    try:
        requested_state = MaintainerState(args.state)
    except ValueError:
        raise CLIInputError("maintainer state is invalid") from None
    if requested_state is MaintainerState.PROPOSAL:
        raise CLIInputError("proposal state belongs to discovery publication")
    summary_path = _candidate_path(args.state_dir, args.summary_file)
    raw = _read_json_model(summary_path, _PublicationArtifact)
    if not isinstance(raw, _PublicationArtifact):
        raise CLIInputError("publication artifact is invalid")
    if raw.summary.state is not requested_state:
        raise CLIInputError("requested state does not match summary")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if not (
        is_eligible_for_deep_curation(pull_request)
        or route_approved_proposal(pull_request) is not None
    ):
        raise CLIInputError("pull request is outside curation policy")
    if requested_state is MaintainerState.READY:
        machine = _machine_state(dependencies.github, pull_request)
        if machine is None:
            raise CLIInputError("ready publication requires trusted review state")
        decision = reconcile_waiting_ci(pull_request, machine)
        if decision.state is not MaintainerState.READY:
            raise CLIInputError("current pull request is not ready")
        publication_machine = machine
    elif requested_state is MaintainerState.WAITING_CI:
        prepared, _validated, _journal = _load_push_evidence(
            args.state_dir,
            args.pr,
            pull_request,
        )
        lineage = prepared.lineage_state
        publication_machine = _published_machine_state(lineage, pull_request)
    elif requested_state in {
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
    }:
        lineage = _load_safe_stop_lineage(
            args.state_dir,
            args.pr,
            pull_request,
        )
        publication_machine = _published_machine_state(lineage, pull_request)
    else:
        lineage = _load_prepared_lineage(
            args.state_dir,
            args.pr,
            pull_request,
        )
        publication_machine = _published_machine_state(lineage, pull_request)
    summary = MaintainerSummary(
        state=raw.summary.state,
        head_sha=pull_request.head_sha,
        result=raw.summary.result,
        ci_status=raw.summary.ci_status,
        owner_action=raw.summary.owner_action,
        caveats=raw.summary.caveats,
        machine_state=publication_machine,
    )
    refreshed = dependencies.github.get_pull_request(args.pr)
    if refreshed != pull_request:
        raise CLIInputError("pull request changed during publication authorization")
    lease.assert_owner(lease.token)
    publish_state(
        dependencies.github,
        pull_request,
        MaintainerLane.CATALOG_CURATION,
        summary,
        raw.managed_body,
    )
    return {
        "status": "published",
        "state": requested_state.value,
        "head_sha": pull_request.head_sha,
    }


def _catalog_keys_from_text(text: str, state_dir: Path) -> set[str]:
    temporary = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=state_dir,
        prefix=".catalog-verify.",
        suffix=".json",
        delete=False,
    )
    path = Path(temporary.name)
    try:
        with temporary:
            os.chmod(path, 0o600)
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        return catalog_entity_keys(path)
    finally:
        path.unlink(missing_ok=True)


def _write_secure_materialized_file(root: Path, name: str, content: str) -> Path:
    path = root / name
    descriptor: int | None = None
    try:
        payload = content.encode("utf-8")
        if len(payload) > _MAX_ARTIFACT_BYTES:
            raise CLIInputError("immutable proposal file exceeds size limit")
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        written = 0
        while written < len(payload):
            chunk = os.write(descriptor, payload[written:])
            if chunk <= 0:
                raise OSError
            written += chunk
        os.fsync(descriptor)
    except OSError:
        raise CLIInputError("immutable proposal file cannot be materialized") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return path


def _proposal_report_path(snapshot: IntentSnapshot) -> str:
    report_paths = sorted(
        path
        for path in snapshot.changed_paths
        if path.startswith(CURATION_REPORT_PREFIX) and path.endswith(".json")
    )
    if len(report_paths) != 1:
        raise CLIInputError("proposal requires exactly one curation JSON report")
    report_path = report_paths[0]
    matching_markdown = f"{report_path.removesuffix('.json')}.md"
    unrelated_curation = {
        path
        for path in snapshot.changed_paths
        if path.startswith(CURATION_REPORT_PREFIX)
        and path not in {report_path, matching_markdown}
    }
    if unrelated_curation:
        raise CLIInputError("proposal contains an unrelated curation artifact")
    unrelated_discovery = {
        path
        for path in snapshot.changed_paths
        if path.startswith("docs/catalog-discovery/")
        and path != "docs/catalog-discovery/alpine-coverage-registry.json"
    }
    if unrelated_discovery:
        raise CLIInputError("proposal contains an unrelated discovery artifact")
    if CATALOG_PATH not in snapshot.changed_paths:
        raise CLIInputError("proposal must change the catalog")
    if TRUST_MANIFEST_PATH not in snapshot.changed_paths:
        raise CLIInputError("proposal must reconcile catalog trust")
    return report_path


def _validate_materialized_proposal(
    repository: object,
    snapshot: IntentSnapshot,
    candidate: DiscoveryCandidate,
    base: str,
    head: str,
    state_dir: Path,
) -> tuple[str, str, set[str], set[str], str]:
    report_path = _proposal_report_path(snapshot)
    candidate_key = candidate.key
    if candidate_key not in snapshot.catalog_targets:
        raise CLIInputError("candidate is absent from immutable catalog targets")
    if candidate_key not in snapshot.report_targets:
        raise CLIInputError("candidate is absent from immutable report targets")

    with TemporaryDirectory(prefix="proposal-verify-", dir=state_dir) as raw_dir:
        materialized = Path(raw_dir)
        os.chmod(materialized, 0o700)
        base_catalog = _write_secure_materialized_file(
            materialized,
            "base-catalog.json",
            repository.show_text(base, CATALOG_PATH),
        )
        current_catalog = _write_secure_materialized_file(
            materialized,
            "current-catalog.json",
            repository.show_text(head, CATALOG_PATH),
        )
        base_trust = _write_secure_materialized_file(
            materialized,
            "base-trust.json",
            repository.show_text(base, TRUST_MANIFEST_PATH),
        )
        current_trust = _write_secure_materialized_file(
            materialized,
            "current-trust.json",
            repository.show_text(head, TRUST_MANIFEST_PATH),
        )
        current_backlog = _write_secure_materialized_file(
            materialized,
            "current-backlog.md",
            repository.show_text(head, BACKLOG_PATH),
        )
        report_text = repository.show_text(head, report_path)
        report_file = _write_secure_materialized_file(
            materialized,
            "curation-report.json",
            report_text,
        )
        report = load_catalog_curation_report(report_file)
        if report.report_schema_version != 2:
            raise CLIInputError("proposal curation report must use schema version 2")
        validate_catalog_curation_report(report)
        validate_catalog_curation_backlog_refs(report, current_backlog)
        reconcile_catalog_curation_report(
            report,
            base_catalog_path=base_catalog,
            current_catalog_path=current_catalog,
            base_trust_manifest_path=base_trust,
            current_trust_manifest_path=current_trust,
        )
        base_keys = catalog_entity_keys(base_catalog)
        proposed_keys = catalog_entity_keys(current_catalog)
        proposed_snapshot = load_catalog_from_path(current_catalog)
        if any(
            issue.severity == "error"
            for issue in catalog_policy_issues(proposed_snapshot)
        ):
            raise CLIInputError("proposal catalog policy validation failed")
        proposed_backlog = _read_text(current_backlog)

    return (
        report_path,
        hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        base_keys,
        proposed_keys,
        proposed_backlog,
    )


def _validate_nomination_registry_change(
    candidate: DiscoveryCandidate,
    base_registry: CoverageRegistry,
    proposed_registry: CoverageRegistry,
) -> None:
    base_entries = {entry.candidate_key: entry for entry in base_registry.entries}
    proposed_entries = {
        entry.candidate_key: entry for entry in proposed_registry.entries
    }
    if not set(base_entries).issubset(proposed_entries):
        raise CLIInputError("proposal removes an existing registry entry")
    for key, entry in base_entries.items():
        if proposed_entries[key] != entry:
            raise CLIInputError("proposal changes an existing registry entry")
    added_keys = set(proposed_entries) - set(base_entries)
    expected_additions = (
        {candidate.key}
        if candidate.origin == "registry" and candidate.key not in base_entries
        else set()
    )
    if added_keys != expected_additions:
        raise CLIInputError("proposal contains an unrelated registry addition")
    if candidate.origin != "registry":
        return
    entry = proposed_entries.get(candidate.key)
    if entry is None:
        raise CLIInputError("nomination is missing from proposed registry")
    if (
        entry.display_name != candidate.display_name
        or entry.country != candidate.country
        or entry.alpine_subregion != candidate.alpine_subregion
        or entry.regional_graph_key != candidate.regional_graph_key
        or entry.candidate_kind != candidate.candidate_kind
        or entry.official_urls != candidate.official_urls
        or entry.fingerprint != candidate.origin_fingerprint
    ):
        raise CLIInputError("proposed registry entry does not match nomination")


def _is_safe_proposal_publication_pr(pull_request: PullRequest) -> bool:
    valid_branch = _PROPOSAL_BRANCH.fullmatch(pull_request.head_ref_name) is not None
    return (
        pull_request.lifecycle_state == "OPEN"
        and not pull_request.is_cross_repository
        and pull_request.head_repository_owner == "lampssy"
        and pull_request.base_ref_name == "main"
        and valid_branch
        and pull_request.lane in {None, MaintainerLane.CATALOG_DISCOVERY}
        and pull_request.maintainer_state in {None, MaintainerState.PROPOSAL}
        and bool(pull_request.changed_paths)
        and all(is_allowed_curation_path(path) for path in pull_request.changed_paths)
        and pull_request.url.host == "github.com"
        and pull_request.url.path
        == f"/lampssy/ai-sports-travel-planner/pull/{pull_request.number}"
    )


def _derive_proposal_verification(
    candidate: DiscoveryCandidate,
    repository: object,
    base: str,
    head: str,
    state_dir: Path,
) -> _ProposalVerification:
    if (
        re.fullmatch(r"[0-9a-f]{40}", base) is None
        or re.fullmatch(r"[0-9a-f]{40}", head) is None
    ):
        raise CLIInputError("proposal revisions must be immutable commit SHAs")
    if base == head:
        raise CLIInputError("proposal head must differ from base")
    snapshot = repository.verify_immutable_diff(base, head)
    (
        report_path,
        report_sha256,
        base_keys,
        proposed_keys,
        proposed_backlog,
    ) = _validate_materialized_proposal(
        repository,
        snapshot,
        candidate,
        base,
        head,
        state_dir,
    )
    verify_origin_cleanup(
        candidate,
        base_keys,
        proposed_keys,
        proposed_backlog,
    )
    base_registry = CoverageRegistry.model_validate_json(
        repository.show_text(
            base,
            "docs/catalog-discovery/alpine-coverage-registry.json",
        ),
        strict=True,
    )
    proposed_registry = CoverageRegistry.model_validate_json(
        repository.show_text(
            head,
            "docs/catalog-discovery/alpine-coverage-registry.json",
        ),
        strict=True,
    )
    _validate_nomination_registry_change(
        candidate,
        base_registry,
        proposed_registry,
    )
    return _ProposalVerification(
        candidate_key=candidate.key,
        candidate_fingerprint=candidate.fingerprint,
        base_head=base,
        reviewed_head=head,
        changed_paths=snapshot.changed_paths,
        catalog_targets=snapshot.catalog_targets,
        report_targets=snapshot.report_targets,
        removed_backlog_markers=snapshot.removed_backlog_markers,
        report_path=report_path,
        report_sha256=report_sha256,
    )


def _discovery_verify_proposal(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    candidate = require_publication_ready(
        _load_candidate(args.state_dir, args.candidate_file)
    )
    verification = _derive_proposal_verification(
        candidate,
        dependencies.repository,
        args.base,
        args.head,
        args.state_dir,
    )
    _write_json(_verification_path(args.state_dir, candidate), verification, lease)
    return {
        "status": "proposal-verified",
        "candidate_key": candidate.key,
        "head_sha": args.head,
    }


def _discovery_publish_proposal(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    candidate = require_publication_ready(
        _load_candidate(args.state_dir, args.candidate_file)
    )
    raw = _read_json_model(
        _verification_path(args.state_dir, candidate),
        _ProposalVerification,
    )
    if not isinstance(raw, _ProposalVerification):
        raise CLIInputError("proposal verification artifact is invalid")
    if (
        raw.candidate_key != candidate.key
        or raw.candidate_fingerprint != candidate.fingerprint
    ):
        raise CLIInputError("candidate no longer matches verified proposal")
    pull_request = dependencies.github.get_pull_request(args.pr)
    if raw.reviewed_head != pull_request.head_sha:
        raise CLIInputError("pull request head no longer matches verification")
    if pull_request.changed_paths != raw.changed_paths:
        raise CLIInputError("GitHub changed paths do not match verified diff")
    if not _is_safe_proposal_publication_pr(pull_request):
        raise CLIInputError("pull request is outside proposal publication policy")
    lease.assert_owner(lease.token)
    refreshed_verification = _derive_proposal_verification(
        candidate,
        dependencies.repository,
        raw.base_head,
        raw.reviewed_head,
        args.state_dir,
    )
    if refreshed_verification != raw:
        raise CLIInputError("immutable proposal verification artifact is stale")

    catalog_keys = _catalog_keys_from_text(
        dependencies.repository.show_text(
            raw.base_head,
            "app/data/catalog.json",
        ),
        args.state_dir,
    )
    pull_requests = [
        item
        for item in dependencies.github.list_open_pull_requests()
        if item.number != args.pr
    ]
    records = _proposal_records(dependencies.github, pull_requests)
    declined = _declined_fingerprints(
        dependencies.github,
        catalog_keys=catalog_keys,
    )
    selected = select_discovery_candidate(
        [candidate],
        CoverageRegistry(schema_version=1, entries=()),
        catalog_keys,
        records,
        declined,
    )
    if selected != candidate:
        raise CLIInputError("proposal cap or candidate overlap changed")

    machine = MachineState(
        head_sha=pull_request.head_sha,
        lineage_id=f"catalog-discovery-{pull_request.number}",
        completed_cycles=0,
        candidate_key=candidate.key,
        candidate_origin_fingerprint=candidate.origin_fingerprint,
        candidate_fingerprint=candidate.fingerprint,
        regional_graph_key=candidate.regional_graph_key,
        last_publication="complete",
    )
    summary = MaintainerSummary(
        state=MaintainerState.PROPOSAL,
        head_sha=pull_request.head_sha,
        result=f"Catalog discovery proposal prepared for {candidate.display_name}.",
        ci_status="Proposal validation completed; owner onboarding decision pending.",
        owner_action="Remove maintainer:proposal to approve catalog onboarding.",
        caveats=("Catalog inclusion remains an owner decision.",),
        machine_state=machine,
    )
    refreshed_pull_request = dependencies.github.get_pull_request(args.pr)
    if refreshed_pull_request != pull_request:
        raise CLIInputError("pull request changed during proposal authorization")
    lease.assert_owner(lease.token)
    publish_state(
        dependencies.github,
        refreshed_pull_request,
        MaintainerLane.CATALOG_DISCOVERY,
        summary,
        render_candidate_discovery_origin(candidate),
    )
    return {
        "status": "proposal-published",
        "state": MaintainerState.PROPOSAL.value,
        "candidate_key": candidate.key,
        "head_sha": refreshed_pull_request.head_sha,
    }


def _dispatch(
    args: argparse.Namespace,
    dependencies: _Dependencies,
) -> dict[str, object]:
    state_dir = args.state_dir
    if args.family == "lock" and args.command == "acquire":
        lease = RunLease.acquire(state_dir, args.worker)
        return {
            "status": "acquired",
            "worker": lease.worker,
        }
    if args.family == "lock" and args.command == "heartbeat":
        lease = _owned_lease(state_dir)
        lease.write_heartbeat(args.phase, HeartbeatDetails())
        return {"status": "heartbeat", "worker": lease.worker}
    if args.family == "lock" and args.command == "release":
        lease = _owned_lease(state_dir)
        lease.release()
        return {"status": "released", "worker": lease.worker}

    if args.family == "curation" and args.command == "inventory":
        return _curation_inventory(dependencies)
    if args.family == "discovery" and args.command == "validate-registry":
        registry = _load_registry(args.registry)
        return {
            "status": "valid",
            "entries": len(registry.entries),
        }

    lease = _owned_lease(state_dir)

    if args.family == "github" and args.command == "ensure-labels":
        lease.assert_owner(lease.token)
        dependencies.github.ensure_labels(LABEL_DEFINITIONS)
        return {"status": "labels-synchronized"}
    if args.family == "curation" and args.command == "prepare":
        return _curation_prepare(args, dependencies, lease)
    if args.family == "curation" and args.command == "validate":
        return _curation_validate(args, dependencies, lease)
    if args.family == "curation" and args.command == "push":
        return _curation_push(args, dependencies, lease)
    if args.family == "curation" and args.command == "publish":
        return _curation_publish(args, dependencies, lease)
    if args.family == "discovery" and args.command == "next":
        return _discovery_next(args, dependencies, lease)
    if args.family == "discovery" and args.command == "add-source":
        return _discovery_add_source(args, lease)
    if args.family == "discovery" and args.command == "nominate":
        return _discovery_nominate(args, dependencies, lease)
    if args.family == "discovery" and args.command == "verify-proposal":
        return _discovery_verify_proposal(args, dependencies, lease)
    if args.family == "discovery" and args.command == "publish-proposal":
        return _discovery_publish_proposal(args, dependencies, lease)
    raise CLIInputError("command is not implemented")


def _reason(error: Exception) -> str:
    if isinstance(error, LockBusyError):
        return "lock-busy"
    if isinstance(error, RunLeaseError):
        return "lease-ownership-error"
    if isinstance(error, RebaseConflictError):
        return "rebase-conflict"
    if isinstance(error, StaleRemoteHeadError):
        return "stale-head"
    if isinstance(error, IntentDriftError):
        return "intent-drift"
    if isinstance(error, IntentValidationError):
        return "intent-validation"
    if isinstance(error, ValidationExecutionError):
        return "validation-failed"
    if isinstance(error, GitAuthenticationError):
        return "git-auth"
    if isinstance(error, GitTransportError):
        return "git-transport"
    if isinstance(error, GitOperationTimeoutError):
        return "git-timeout"
    if isinstance(error, GitPushRejectedError):
        return "push-rejected"
    if isinstance(error, GitRemotePolicyError):
        return "remote-policy"
    if isinstance(error, RepositorySafetyError):
        return "repository-safety"
    if isinstance(error, (CLIInputError, ValidationError, ValueError, TypeError)):
        return "invalid-command-input"
    if isinstance(error, GitHubError):
        return "github-operation-failed"
    return "operation-failed"


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def main(
    argv: Sequence[str] | None = None,
    *,
    github: object | None = None,
    repository: object | None = None,
    base_repository: object | None = None,
    validation_executor: Callable[..., object] = execute_curation_validation,
    repository_root: Path | None = None,
    today: Callable[[], date] = date.today,
) -> int:
    try:
        args = _parser().parse_args(argv)
        root = (repository_root or Path.cwd()).resolve()
        needs_repository = (args.family, args.command) in {
            ("curation", "prepare"),
            ("curation", "validate"),
            ("curation", "push"),
            ("discovery", "verify-proposal"),
            ("discovery", "publish-proposal"),
        }
        selected_repository = repository
        if selected_repository is None and needs_repository:
            selected_repository = GitRepository(root)
        dependencies = _Dependencies(
            github=github or GitHubClient(gh_config_dir=args.gh_config_dir),
            repository=selected_repository or object(),
            base_repository=base_repository,
            validation_executor=validation_executor,
            repository_root=root,
            today=today,
        )
        payload = _dispatch(args, dependencies)
    except Exception as error:
        failure: dict[str, object] = {
            "status": "error",
            "reason": _reason(error),
        }
        if isinstance(error, ValidationExecutionError):
            failure.update(
                {
                    "validation_stage": error.stage,
                    "validation_failure": error.failure_kind,
                }
            )
        _emit(failure)
        return 2
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

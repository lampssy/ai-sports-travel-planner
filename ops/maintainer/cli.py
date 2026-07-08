from __future__ import annotations

import argparse
import json
import os
import re
import stat
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ops.maintainer import LABEL_DEFINITIONS, SUMMARY_MARKER
from ops.maintainer.curation import (
    execute_curation_validation,
    is_eligible_for_deep_curation,
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
from ops.maintainer.git_ops import GitRepository, GuardedSyncResult
from ops.maintainer.github import TRUSTED_MAINTAINER_LOGIN, GitHubClient, GitHubError
from ops.maintainer.intent import is_allowed_curation_path
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
    RunLease,
    RunLeaseError,
)

_SAFE_JSON_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_REPORT_PATH = re.compile(r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_MAX_ARTIFACT_BYTES = 1_000_000


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _PreparedArtifact(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    prepared: GuardedSyncResult


class _ValidatedArtifact(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    report_path: str
    prepared: GuardedSyncResult


class _PublicationArtifact(_StrictModel):
    summary: MaintainerSummary
    managed_body: str = Field(min_length=1, max_length=100_000)


class _ProposalVerification(_StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    candidate_key: str
    candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


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
    families = parser.add_subparsers(dest="family", required=True)

    lock = families.add_parser("lock")
    lock_commands = lock.add_subparsers(dest="command", required=True)
    acquire = lock_commands.add_parser("acquire")
    acquire.add_argument("worker", choices=("curation", "discovery"))
    heartbeat = lock_commands.add_parser("heartbeat")
    heartbeat.add_argument("--token", required=True)
    heartbeat.add_argument("--phase", required=True)
    release = lock_commands.add_parser("release")
    release.add_argument("--token", required=True)

    github = families.add_parser("github")
    github_commands = github.add_subparsers(dest="command", required=True)
    ensure_labels = github_commands.add_parser("ensure-labels")
    ensure_labels.add_argument("--lock-token", required=True)

    curation = families.add_parser("curation")
    curation_commands = curation.add_subparsers(dest="command", required=True)
    curation_commands.add_parser("inventory")
    prepare = curation_commands.add_parser("prepare")
    prepare.add_argument("--pr", type=int, required=True)
    prepare.add_argument("--lock-token", required=True)
    validate = curation_commands.add_parser("validate")
    validate.add_argument("--pr", type=int, required=True)
    validate.add_argument("--report", required=True)
    validate.add_argument("--base-dir", type=Path, required=True)
    validate.add_argument("--lock-token", required=True)
    push = curation_commands.add_parser("push")
    push.add_argument("--pr", type=int, required=True)
    push.add_argument("--original-head", required=True)
    push.add_argument("--lock-token", required=True)
    publish = curation_commands.add_parser("publish")
    publish.add_argument("--pr", type=int, required=True)
    publish.add_argument("--state", required=True)
    publish.add_argument("--summary-file", type=Path, required=True)
    publish.add_argument("--lock-token", required=True)

    discovery = families.add_parser("discovery")
    discovery_commands = discovery.add_subparsers(dest="command", required=True)
    validate_registry = discovery_commands.add_parser("validate-registry")
    validate_registry.add_argument("--registry", type=Path, required=True)
    next_candidate = discovery_commands.add_parser("next")
    next_candidate.add_argument("--output", type=Path, required=True)
    next_candidate.add_argument("--lock-token", required=True)
    add_source = discovery_commands.add_parser("add-source")
    add_source.add_argument("--candidate-file", type=Path, required=True)
    add_source.add_argument("--official-url", required=True)
    add_source.add_argument("--lock-token", required=True)
    nominate = discovery_commands.add_parser("nominate")
    nominate.add_argument("--output", type=Path, required=True)
    nominate.add_argument("--candidate-key", required=True)
    nominate.add_argument("--display-name", required=True)
    nominate.add_argument("--country", required=True)
    nominate.add_argument("--alpine-subregion", required=True)
    nominate.add_argument("--regional-graph-key", required=True)
    nominate.add_argument("--official-url", required=True)
    nominate.add_argument("--lock-token", required=True)
    verify = discovery_commands.add_parser("verify-proposal")
    verify.add_argument("--candidate-file", type=Path, required=True)
    verify.add_argument("--base", required=True)
    verify.add_argument("--head", required=True)
    verify.add_argument("--lock-token", required=True)
    publish_proposal = discovery_commands.add_parser("publish-proposal")
    publish_proposal.add_argument("--pr", type=int, required=True)
    publish_proposal.add_argument("--candidate-file", type=Path, required=True)
    publish_proposal.add_argument("--lock-token", required=True)
    return parser


def _owned_lease(state_dir: Path, token: str) -> RunLease:
    lease = RunLease.load(state_dir)
    lease.assert_owner(token)
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
    except OSError:
        raise CLIInputError("artifact cannot be written") from None
    finally:
        temporary_path.unlink(missing_ok=True)


def _prepared_path(state_dir: Path, pr_number: int) -> Path:
    return _artifact_path(state_dir, f"curation-pr-{pr_number}-prepared.json")


def _validated_path(state_dir: Path, pr_number: int) -> Path:
    return _artifact_path(state_dir, f"curation-pr-{pr_number}-validated.json")


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


def _declined_fingerprints(github: object) -> set[tuple[str, str]]:
    declined: set[tuple[str, str]] = set()
    for comment in github.list_closed_proposal_comments():
        if comment.author_login != TRUSTED_MAINTAINER_LOGIN:
            continue
        machine = parse_machine_state(comment.body)
        if (
            machine is not None
            and machine.candidate_key is not None
            and machine.candidate_origin_fingerprint is not None
        ):
            declined.add((machine.candidate_key, machine.candidate_origin_fingerprint))
    return declined


def _machine_state(github: object, pull_request: PullRequest) -> MachineState | None:
    marked = [
        comment
        for comment in github.list_issue_comments(pull_request.number)
        if comment.author_login == TRUSTED_MAINTAINER_LOGIN
        and SUMMARY_MARKER in comment.body
    ]
    if len(marked) != 1:
        return None
    return parse_machine_state(marked[0].body)


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
        _declined_fingerprints(dependencies.github),
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
    pull_request = dependencies.github.get_pull_request(args.pr)
    if not (
        is_eligible_for_deep_curation(pull_request)
        or route_approved_proposal(pull_request) is not None
    ):
        raise CLIInputError("pull request is outside curation policy")
    lease.assert_owner(lease.token)
    prepared = dependencies.repository.prepare_guarded_sync(pull_request)
    artifact = _PreparedArtifact(
        pr_number=pull_request.number,
        selected_head=pull_request.head_sha,
        prepared=prepared,
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
    raw = _read_json_model(
        _prepared_path(args.state_dir, args.pr),
        _PreparedArtifact,
    )
    if not isinstance(raw, _PreparedArtifact):
        raise CLIInputError("prepared artifact is invalid")
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
    pull_request = dependencies.github.get_pull_request(args.pr)
    if (
        args.original_head != raw.selected_head
        or raw.prepared.original_head != raw.selected_head
        or pull_request.head_sha != raw.selected_head
    ):
        raise CLIInputError("push state no longer matches selected head")
    if not (
        is_eligible_for_deep_curation(pull_request)
        or route_approved_proposal(pull_request) is not None
    ):
        raise CLIInputError("pull request is outside curation push policy")
    lease.assert_owner(lease.token)
    dependencies.repository.push_with_lease(raw.prepared, raw.reviewed_head)
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
    if raw.summary.head_sha != pull_request.head_sha:
        raise CLIInputError("summary does not match current pull request head")
    if not (
        is_eligible_for_deep_curation(pull_request)
        or route_approved_proposal(pull_request) is not None
    ):
        raise CLIInputError("pull request is outside curation policy")
    lease.assert_owner(lease.token)
    publish_state(
        dependencies.github,
        pull_request,
        MaintainerLane.CATALOG_CURATION,
        raw.summary,
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
    segments = pull_request.head_ref_name.split("/")
    valid_branch = (
        pull_request.head_ref_name.startswith("codex/")
        and len(segments) > 1
        and all(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", segment) is not None
            and not segment.endswith((".", ".lock"))
            for segment in segments
        )
    )
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


def _discovery_verify_proposal(
    args: argparse.Namespace,
    dependencies: _Dependencies,
    lease: RunLease,
) -> dict[str, object]:
    if (
        re.fullmatch(r"[0-9a-f]{40}", args.base) is None
        or re.fullmatch(r"[0-9a-f]{40}", args.head) is None
    ):
        raise CLIInputError("proposal revisions must be immutable commit SHAs")
    if args.base == args.head:
        raise CLIInputError("proposal head must differ from base")
    candidate = require_publication_ready(
        _load_candidate(args.state_dir, args.candidate_file)
    )
    base_keys = _catalog_keys_from_text(
        dependencies.repository.show_text(args.base, "app/data/catalog.json"),
        args.state_dir,
    )
    proposed_keys = _catalog_keys_from_text(
        dependencies.repository.show_text(args.head, "app/data/catalog.json"),
        args.state_dir,
    )
    proposed_backlog = dependencies.repository.show_text(
        args.head,
        "docs/product-backlog.md",
    )
    verify_origin_cleanup(
        candidate,
        base_keys,
        proposed_keys,
        proposed_backlog,
    )
    base_registry = CoverageRegistry.model_validate_json(
        dependencies.repository.show_text(
            args.base,
            "docs/catalog-discovery/alpine-coverage-registry.json",
        ),
        strict=True,
    )
    proposed_registry = CoverageRegistry.model_validate_json(
        dependencies.repository.show_text(
            args.head,
            "docs/catalog-discovery/alpine-coverage-registry.json",
        ),
        strict=True,
    )
    _validate_nomination_registry_change(
        candidate,
        base_registry,
        proposed_registry,
    )
    verification = _ProposalVerification(
        candidate_key=candidate.key,
        candidate_fingerprint=candidate.fingerprint,
        base_head=args.base,
        reviewed_head=args.head,
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
    if not _is_safe_proposal_publication_pr(pull_request):
        raise CLIInputError("pull request is outside proposal publication policy")

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
    declined = _declined_fingerprints(dependencies.github)
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
    lease.assert_owner(lease.token)
    publish_state(
        dependencies.github,
        pull_request,
        MaintainerLane.CATALOG_DISCOVERY,
        summary,
        render_candidate_discovery_origin(candidate),
    )
    return {
        "status": "proposal-published",
        "state": MaintainerState.PROPOSAL.value,
        "candidate_key": candidate.key,
        "head_sha": pull_request.head_sha,
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
            "token": lease.token,
        }
    if args.family == "lock" and args.command == "heartbeat":
        lease = _owned_lease(state_dir, args.token)
        lease.write_heartbeat(args.phase, HeartbeatDetails())
        return {"status": "heartbeat", "worker": lease.worker}
    if args.family == "lock" and args.command == "release":
        lease = _owned_lease(state_dir, args.token)
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

    lock_token = getattr(args, "lock_token", None)
    if lock_token is None:
        raise CLIInputError("mutation command requires a lock token")
    lease = _owned_lease(state_dir, lock_token)

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
    if isinstance(error, RunLeaseError):
        return "lease-ownership-error"
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
        lock_token = getattr(args, "lock_token", None)
        if lock_token is not None:
            _owned_lease(args.state_dir, lock_token)
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
            github=github or GitHubClient(),
            repository=selected_repository or object(),
            base_repository=base_repository,
            validation_executor=validation_executor,
            repository_root=root,
            today=today,
        )
        payload = _dispatch(args, dependencies)
    except Exception as error:
        _emit({"status": "error", "reason": _reason(error)})
        return 2
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

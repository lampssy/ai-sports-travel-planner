from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Sequence, Set
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ops.maintainer import BODY_END, BODY_START, SUMMARY_MARKER
from ops.maintainer.errors import ErrorReason, ErrorStage, MaintainerError
from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.github import TRUSTED_MAINTAINER_LOGIN, GitHubComment
from ops.maintainer.models import (
    MachineState,
    MachineStateV2,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)

if TYPE_CHECKING:
    from ops.maintainer.validation import ProposalValidationResult

_MACHINE_MARKER_PREFIX = "<!-- snowcast-maintainer-state:"
_MACHINE_MARKER_SUFFIX = " -->"
_MACHINE_MARKER = re.compile(
    rf"{re.escape(_MACHINE_MARKER_PREFIX)}(\{{[^\r\n]*\}})"
    rf"{re.escape(_MACHINE_MARKER_SUFFIX)}"
)
_UNSAFE_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MAINTAINER_MARKERS = (
    SUMMARY_MARKER,
    BODY_START,
    BODY_END,
    _MACHINE_MARKER_PREFIX,
)
_HTML_COMMENT_DELIMITERS = ("<!--", "-->")
_SEMANTIC_STATES = frozenset(
    {
        MaintainerState.WORKING,
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
    }
)
_READY_BLOCKING_STATES = frozenset(
    {
        MaintainerState.PROPOSAL,
        MaintainerState.OWNER_DECISION,
        MaintainerState.MANUAL_CHECK,
        MaintainerState.BLOCKED,
    }
)
_PUBLICATION_TEXT_LIMITS = {
    "title": 256,
    "body": 65_536,
    "summary": 16_384,
}


class PublicationInputError(RuntimeError):
    """A caller-selected publication input failed the private-file contract."""


class PublicationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    lane: MaintainerLane
    state: MaintainerState
    machine_state: MachineStateV2


class MaintainerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    state: MaintainerState
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    result: str = Field(min_length=1, max_length=4_000)
    ci_status: str = Field(min_length=1, max_length=1_000)
    owner_action: str = Field(min_length=1, max_length=2_000)
    caveats: tuple[str, ...] = Field(default=(), max_length=20)
    machine_state: MachineState

    @field_validator("result", "ci_status", "owner_action")
    @classmethod
    def validate_visible_text(cls, value: str) -> str:
        return _validate_visible_text(value)

    @field_validator("caveats")
    @classmethod
    def validate_caveats(cls, caveats: tuple[str, ...]) -> tuple[str, ...]:
        for caveat in caveats:
            if len(caveat) > 1_000:
                raise ValueError("caveat exceeds maximum length")
            _validate_visible_text(caveat)
        return caveats

    @model_validator(mode="after")
    def validate_head_matches_machine_state(self) -> Self:
        if self.head_sha != self.machine_state.head_sha:
            raise ValueError("summary head must match machine state head")
        if _machine_state_has_unsafe_strings(self.machine_state):
            raise ValueError("unsafe marker or control in machine state")
        return self


def _validate_visible_text(value: str) -> str:
    if not value.strip():
        raise ValueError("visible summary text must not be blank")
    if _has_unsafe_sequences(value):
        raise ValueError("unsafe maintainer marker or control character")
    return value


def _has_unsafe_sequences(value: str) -> bool:
    return bool(_UNSAFE_CONTROL.search(value)) or any(
        marker in value for marker in _MAINTAINER_MARKERS
    )


def _machine_state_has_unsafe_strings(machine_state: MachineState) -> bool:
    return any(
        isinstance(value, str)
        and (
            _has_unsafe_sequences(value)
            or any(delimiter in value for delimiter in _HTML_COMMENT_DELIMITERS)
        )
        for value in machine_state.model_dump(mode="json").values()
    )


def replace_managed_body(current: str, managed: str) -> str:
    if BODY_START in managed or BODY_END in managed:
        raise ValueError("managed content must not contain managed body markers")

    start_count = current.count(BODY_START)
    end_count = current.count(BODY_END)
    if start_count == 0 and end_count == 0:
        block = _managed_block(managed)
        return block if not current else f"{current}\n\n{block}"
    if start_count != 1 or end_count != 1:
        raise ValueError("managed body markers are malformed or duplicated")

    start = current.index(BODY_START)
    end = current.index(BODY_END)
    if end < start:
        raise ValueError("managed body markers are reversed")
    suffix = end + len(BODY_END)
    return f"{current[:start]}{_managed_block(managed)}{current[suffix:]}"


def _managed_block(managed: str) -> str:
    return f"{BODY_START}\n{managed}\n{BODY_END}"


def render_summary(summary: MaintainerSummary) -> str:
    lines = [
        SUMMARY_MARKER,
        "## Snowcast maintainer summary",
        "",
        f"- **State:** `{summary.state.value}`",
        f"- **Head:** `{summary.head_sha}`",
        f"- **Result:** {summary.result}",
        f"- **CI:** {summary.ci_status}",
        f"- **Owner action:** {summary.owner_action}",
    ]
    if summary.caveats:
        lines.append("- **Caveats:**")
        lines.extend(f"  - {caveat}" for caveat in summary.caveats)
    else:
        lines.append("- **Caveats:** None.")
    lines.extend(("", _render_machine_marker(summary.machine_state)))
    return "\n".join(lines)


def _render_machine_marker(machine_state: MachineState) -> str:
    payload = json.dumps(
        machine_state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{_MACHINE_MARKER_PREFIX}{payload}{_MACHINE_MARKER_SUFFIX}"


def parse_machine_state(comment_body: str) -> MachineState | None:
    if comment_body.count(_MACHINE_MARKER_PREFIX) != 1:
        return None
    matches = _MACHINE_MARKER.findall(comment_body)
    if len(matches) != 1:
        return None
    payload = matches[0]
    try:
        decoded = json.loads(payload)
        state = MachineState.model_validate(decoded)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if _machine_state_has_unsafe_strings(state):
        return None
    if _render_machine_marker(state) != (
        f"{_MACHINE_MARKER_PREFIX}{payload}{_MACHINE_MARKER_SUFFIX}"
    ):
        return None
    return state


def render_machine_state_v2(machine_state: MachineStateV2) -> str:
    if type(machine_state) is not MachineStateV2:
        raise TypeError("machine state must use schema version 2")
    state = MachineStateV2.model_validate(machine_state.model_dump())
    if _machine_state_v2_has_unsafe_strings(state):
        raise ValueError("machine state contains an unsafe string")
    payload = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{_MACHINE_MARKER_PREFIX}{payload}{_MACHINE_MARKER_SUFFIX}"


def parse_machine_state_v2(comment_body: str) -> MachineStateV2 | None:
    if type(comment_body) is not str or _has_strict_control(comment_body):
        return None
    if comment_body.count(_MACHINE_MARKER_PREFIX) != 1:
        return None
    matches = _MACHINE_MARKER.findall(comment_body)
    if len(matches) != 1:
        return None
    payload = matches[0]
    try:
        decoded = json.loads(payload)
        state = MachineStateV2.model_validate(decoded)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    try:
        machine_marker = render_machine_state_v2(state)
    except (TypeError, ValueError):
        return None
    if machine_marker != (f"{_MACHINE_MARKER_PREFIX}{payload}{_MACHINE_MARKER_SUFFIX}"):
        return None
    remainder = comment_body.replace(machine_marker, "", 1)
    if remainder.count(SUMMARY_MARKER) > 1:
        return None
    remainder = remainder.replace(SUMMARY_MARKER, "", 1)
    if any(delimiter in remainder for delimiter in _HTML_COMMENT_DELIMITERS):
        return None
    return state


def trusted_machine_state_v2(
    comments: Sequence[GitHubComment],
) -> MachineStateV2 | None:
    marked_comments = tuple(
        comment
        for comment in comments
        if comment.author_login == TRUSTED_MAINTAINER_LOGIN
        and SUMMARY_MARKER in comment.body
    )
    if len(marked_comments) != 1:
        return None
    body = marked_comments[0].body
    if body.count(SUMMARY_MARKER) != 1:
        return None
    return parse_machine_state_v2(body)


def _machine_state_v2_has_unsafe_strings(machine_state: MachineStateV2) -> bool:
    return any(
        isinstance(value, str)
        and (
            _has_strict_control(value)
            or any(delimiter in value for delimiter in _HTML_COMMENT_DELIMITERS)
        )
        for value in machine_state.model_dump(mode="json").values()
    )


def _has_strict_control(value: str) -> bool:
    return any(
        (ord(character) < 32 and character != "\n") or 127 <= ord(character) <= 159
        for character in value
    )


def publication_plan(
    *,
    requested_state: MaintainerState,
    lane: MaintainerLane,
    pull_request: PullRequest,
    machine_state: MachineStateV2,
    proposal_validation: ProposalValidationResult | None = None,
    discovery_inventory: object | None = None,
) -> PublicationPlan:
    _require_publication_authority(pull_request, lane)
    if type(requested_state) is not MaintainerState:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Requested lifecycle state is not allowlisted",
        )
    if type(machine_state) is not MachineStateV2:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Machine state must use schema version 2",
        )
    machine_state = MachineStateV2.model_validate(machine_state.model_dump())
    if machine_state.reviewed_head != pull_request.head_sha:
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "PR head differs from the reviewed head",
            stage=ErrorStage.READINESS,
        )

    if requested_state in _SEMANTIC_STATES:
        pass
    elif requested_state is MaintainerState.WAITING_CI:
        _require_validated_current_head(pull_request, machine_state)
        if pull_request.check_state != "pending":
            raise _publication_error(
                ErrorReason.NOT_READY,
                "Required checks are not pending",
                stage=ErrorStage.READINESS,
            )
    elif requested_state is MaintainerState.READY:
        require_ready(pull_request, machine_state)
    elif requested_state is MaintainerState.PROPOSAL:
        _require_proposal_plan(
            lane,
            pull_request,
            machine_state,
            proposal_validation,
            discovery_inventory,
        )
    else:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Requested lifecycle state is not allowlisted",
        )
    return PublicationPlan(
        lane=lane,
        state=requested_state,
        machine_state=machine_state,
    )


def require_ready(
    pull_request: PullRequest,
    machine_state: MachineStateV2,
) -> None:
    if (
        type(pull_request) is not PullRequest
        or type(machine_state) is not MachineStateV2
    ):
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Readiness requires strict pull request and machine state",
            stage=ErrorStage.READINESS,
        )
    _require_publication_authority(pull_request, pull_request.lane)
    if machine_state.reviewed_head != pull_request.head_sha:
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "PR head differs from the reviewed head",
            stage=ErrorStage.READINESS,
        )
    _require_validated_current_head(pull_request, machine_state)
    if pull_request.check_state != "success" or pull_request.mergeable != "MERGEABLE":
        raise _publication_error(
            ErrorReason.NOT_READY,
            "Required checks or mergeability are not ready",
            stage=ErrorStage.READINESS,
        )
    if any(state.value in pull_request.labels for state in _READY_BLOCKING_STATES):
        reason = (
            ErrorReason.PROPOSAL_APPROVAL_REQUIRED
            if MaintainerState.PROPOSAL.value in pull_request.labels
            else ErrorReason.NOT_READY
        )
        raise _publication_error(
            reason,
            "Current lifecycle state prevents readiness",
            stage=ErrorStage.READINESS,
        )


def _require_validated_current_head(
    pull_request: PullRequest,
    machine_state: MachineStateV2,
) -> None:
    if machine_state.validated_head != pull_request.head_sha:
        raise _publication_error(
            ErrorReason.VALIDATION_REQUIRED,
            "Current head has no matching validation",
            stage=ErrorStage.READINESS,
        )


def _require_publication_authority(
    pull_request: PullRequest,
    lane: MaintainerLane | None,
) -> None:
    if type(pull_request) is not PullRequest or type(lane) is not MaintainerLane:
        raise _publication_error(
            ErrorReason.INVALID_GITHUB_STATE,
            "Publication authority is incomplete",
        )
    expected_path = f"/lampssy/ai-sports-travel-planner/pull/{pull_request.number}"
    if (
        pull_request.lifecycle_state != "OPEN"
        or pull_request.is_cross_repository
        or pull_request.head_repository_owner != TRUSTED_MAINTAINER_LOGIN
        or pull_request.base_ref_name != "main"
        or not is_safe_codex_branch(pull_request.head_ref_name)
        or pull_request.url.host != "github.com"
        or pull_request.url.path != expected_path
        or (pull_request.lane is not None and pull_request.lane is not lane)
    ):
        raise _publication_error(
            ErrorReason.INVALID_GITHUB_STATE,
            "Pull request is outside publication authority",
        )


def _require_proposal_plan(
    lane: MaintainerLane,
    pull_request: PullRequest,
    machine_state: MachineStateV2,
    proposal_validation: ProposalValidationResult | None,
    discovery_inventory: object | None,
) -> None:
    from ops.maintainer.inspection import DiscoveryInventory
    from ops.maintainer.validation import ProposalValidationResult

    if (
        lane is not MaintainerLane.CATALOG_DISCOVERY
        or type(proposal_validation) is not ProposalValidationResult
        or type(discovery_inventory) is not DiscoveryInventory
    ):
        raise _publication_error(
            ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
            "Proposal publication evidence is incomplete",
        )
    proposal_validation = ProposalValidationResult.model_validate(
        proposal_validation.model_dump()
    )
    inventory = DiscoveryInventory.model_validate(discovery_inventory.model_dump())
    if (
        proposal_validation.validated_head != pull_request.head_sha
        or machine_state.validated_head != pull_request.head_sha
        or machine_state.candidate_key != proposal_validation.candidate_key
        or machine_state.candidate_origin != proposal_validation.candidate_origin
    ):
        raise _publication_error(
            ErrorReason.VALIDATION_REQUIRED,
            "Proposal evidence does not match the current head",
        )
    candidate_key = proposal_validation.candidate_key
    if (
        not inventory.can_create_proposal
        or inventory.open_proposal_count >= 3
        or inventory.has_unknown_proposal_identity
        or inventory.unresolved_pushes
        or candidate_key in inventory.catalog_keys
        or candidate_key in inventory.open_candidate_keys
    ):
        reason = (
            ErrorReason.DUPLICATE_PROPOSAL
            if candidate_key in inventory.open_candidate_keys
            or candidate_key in inventory.catalog_keys
            else ErrorReason.PROPOSAL_CAP
        )
        raise _publication_error(reason, "Current candidate facts block proposal")


def _publication_error(
    reason: ErrorReason,
    detail: str,
    *,
    stage: ErrorStage = ErrorStage.PUBLISH,
) -> MaintainerError:
    return MaintainerError(reason=reason, stage=stage, detail=detail)


def read_publication_text(
    state_dir: str | Path,
    supplied_path: str | Path,
    *,
    kind: Literal["title", "body", "summary"],
) -> str:
    if (
        type(kind) is not str
        or kind not in _PUBLICATION_TEXT_LIMITS
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
    ):
        raise PublicationInputError("publication input is unsafe")
    basename = _publication_basename(supplied_path)
    directory_descriptor: int | None = None
    file_descriptor: int | None = None
    try:
        directory_descriptor = _open_private_state_directory(Path(state_dir))
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        flags |= os.O_NOFOLLOW
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        file_descriptor = os.open(
            basename,
            flags,
            dir_fd=directory_descriptor,
        )
        metadata = os.fstat(file_descriptor)
        limit = _PUBLICATION_TEXT_LIMITS[kind]
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
            or metadata.st_size > limit
        ):
            raise PublicationInputError("publication input is unsafe")
        payload = _read_bounded_bytes(file_descriptor, limit)
    except PublicationInputError:
        raise
    except (OSError, TypeError, ValueError):
        raise PublicationInputError("publication input is unsafe") from None
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)
    try:
        value = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise PublicationInputError("publication input is unsafe") from None
    if kind == "title" and (not value.strip() or "\n" in value or "\r" in value):
        raise PublicationInputError("publication input is unsafe")
    return value


def _publication_basename(supplied_path: str | Path) -> str:
    try:
        raw = os.fspath(supplied_path)
    except TypeError:
        raise PublicationInputError("publication input is unsafe") from None
    if (
        type(raw) is not str
        or not raw
        or raw in {".", ".."}
        or "/" in raw
        or "\\" in raw
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
        or Path(raw).name != raw
    ):
        raise PublicationInputError("publication input is unsafe")
    return raw


def _open_private_state_directory(state_dir: Path) -> int:
    if not state_dir.is_absolute() or any(
        part in {".", ".."} for part in state_dir.parts
    ):
        raise PublicationInputError("publication input is unsafe")
    flags = os.O_RDONLY
    flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    flags |= os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for part in state_dir.parts[1:]:
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise PublicationInputError("publication input is unsafe")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _read_bounded_bytes(descriptor: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit + 1
    while remaining:
        chunk = os.read(descriptor, min(65_536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    if len(payload) > limit:
        raise PublicationInputError("publication input is unsafe")
    return payload


def label_plan(
    current: Set[str],
    lane: MaintainerLane,
    state: MaintainerState,
) -> tuple[set[str], set[str]]:
    desired = {lane.value, state.value}
    controlled = {
        *(item.value for item in MaintainerLane),
        *(item.value for item in MaintainerState),
    }
    current_labels = set(current)
    return desired - current_labels, (current_labels & controlled) - desired


class _PublicationClient(Protocol):
    def list_issue_comments(self, number: int) -> Sequence[GitHubComment]: ...

    def update_pull_request_body(self, number: int, body: str) -> None: ...

    def create_comment(self, number: int, body: str) -> int: ...

    def update_comment(self, comment_id: int, body: str) -> None: ...

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None: ...


def publish_state(
    client: _PublicationClient,
    pull_request: PullRequest,
    lane: MaintainerLane,
    summary: MaintainerSummary,
    managed_body: str,
) -> None:
    if summary.head_sha != pull_request.head_sha:
        raise ValueError("summary head must match pull request head")

    comments = client.list_issue_comments(pull_request.number)
    marked_comments = [
        comment
        for comment in comments
        if comment.author_login == TRUSTED_MAINTAINER_LOGIN
        and SUMMARY_MARKER in comment.body
    ]
    if len(marked_comments) > 1:
        raise ValueError("multiple maintainer summary comments found")

    desired_body = replace_managed_body(pull_request.body, managed_body)
    if desired_body != pull_request.body:
        client.update_pull_request_body(pull_request.number, desired_body)

    desired_comment = render_summary(summary)
    if marked_comments:
        existing = marked_comments[0]
        if existing.body != desired_comment:
            client.update_comment(existing.comment_id, desired_comment)
    else:
        client.create_comment(pull_request.number, desired_comment)

    add, remove = label_plan(pull_request.labels, lane, summary.state)
    if add or remove:
        client.update_labels(pull_request.number, add, remove)

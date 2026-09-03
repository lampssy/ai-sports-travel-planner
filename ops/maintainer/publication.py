from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Callable, Sequence, Set
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ops.maintainer import BODY_END, BODY_START, REPOSITORY, SUMMARY_MARKER
from ops.maintainer.errors import ErrorKind, ErrorReason, ErrorStage, MaintainerError
from ops.maintainer.git_refs import is_safe_codex_branch
from ops.maintainer.github import (
    TRUSTED_MAINTAINER_LOGIN,
    GitHubComment,
    is_safe_catalog_curation_branch,
)
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    OutcomeState,
    PullRequest,
)
from ops.maintainer.runtime import RunLease
from ops.maintainer.state import (
    CiContinuation,
    CiContinuationPhase,
    PushJournal,
    PushPhase,
    StateStore,
)

if TYPE_CHECKING:
    from ops.maintainer.validation import ProposalValidationResult

_MACHINE_MARKER_PREFIX = "<!-- snowcast-maintainer-state:"
_MACHINE_MARKER_SUFFIX = " -->"
_MACHINE_MARKER = re.compile(
    rf"{re.escape(_MACHINE_MARKER_PREFIX)}(\{{[^\r\n]*\}})"
    rf"{re.escape(_MACHINE_MARKER_SUFFIX)}"
)
_OUTCOME_MARKER_PREFIX = "<!-- snowcast-maintainer-outcome:"
_OUTCOME_MARKER_SUFFIX = " -->"
_OUTCOME_MARKER = re.compile(
    rf"{re.escape(_OUTCOME_MARKER_PREFIX)}(\{{[^\r\n]*\}})"
    rf"{re.escape(_OUTCOME_MARKER_SUFFIX)}"
)
_UNSAFE_SUMMARY_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_MAINTAINER_MARKERS = (
    SUMMARY_MARKER,
    BODY_START,
    BODY_END,
    _MACHINE_MARKER_PREFIX,
    _OUTCOME_MARKER_PREFIX,
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
    "inventory-disposition": 32_768,
}

_PUBLICATION_INPUT_CREATE_ATTEMPTS = 8
_CURATION_REPORT_PATH = re.compile(
    r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
)
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_GENERATED_REPORT_LINK = re.compile(
    r"(?:\n\n)?## Full report\n\n"
    r"\[Open the full curation report\]"
    r"\(https://github\.com/lampssy/ai-sports-travel-planner/blob/"
    r"[0-9a-f]{40}/docs/catalog-curation/"
    r"[A-Za-z0-9][A-Za-z0-9._-]*\.md\)$"
)


class PublicationInputError(RuntimeError):
    """A caller-selected publication input failed the private-file contract."""

    def __init__(
        self,
        message: str,
        *,
        kind: ErrorKind = ErrorKind.INVALID_FILE,
    ) -> None:
        self.kind = kind
        super().__init__(message)


def create_publication_text(
    lease: RunLease,
    *,
    kind: Literal["title", "body", "summary", "inventory-disposition"],
    payload: bytes,
) -> str:
    """Create one private, lease-bound publication input and return its basename."""
    if (
        type(kind) is not str
        or kind not in _PUBLICATION_TEXT_LIMITS
        or type(payload) is not bytes
        or not hasattr(os, "O_NOFOLLOW")
    ):
        raise PublicationInputError("publication input is unsafe")
    limit = _PUBLICATION_TEXT_LIMITS[kind]
    if len(payload) > limit:
        raise PublicationInputError("publication input is unsafe")
    try:
        value = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise PublicationInputError("publication input is unsafe") from None
    if kind == "title" and (not value.strip() or "\n" in value or "\r" in value):
        raise PublicationInputError("publication input is unsafe")

    lease.assert_owner()
    directory_descriptor: int | None = None
    file_descriptor: int | None = None
    basename: str | None = None
    created = False
    completed = False
    try:
        directory_descriptor = _open_private_state_directory(lease.state_dir)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        for _attempt in range(_PUBLICATION_INPUT_CREATE_ATTEMPTS):
            candidate = f"publication-input-{uuid4().hex}"
            try:
                file_descriptor = os.open(
                    candidate,
                    flags,
                    0o600,
                    dir_fd=directory_descriptor,
                )
            except FileExistsError:
                continue
            basename = candidate
            created = True
            break
        if file_descriptor is None or basename is None:
            raise PublicationInputError("publication input is unsafe")
        os.fchmod(file_descriptor, 0o600)
        _write_all(file_descriptor, payload)
        os.fsync(file_descriptor)
        lease.assert_owner()
        _fsync_publication_directory(directory_descriptor)
        lease.assert_owner()
        completed = True
        return basename
    except PublicationInputError:
        raise
    except OSError:
        raise PublicationInputError("publication input is unsafe") from None
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if (
            created
            and not completed
            and basename is not None
            and directory_descriptor is not None
        ):
            try:
                os.unlink(basename, dir_fd=directory_descriptor)
                _fsync_publication_directory(directory_descriptor)
            except OSError:
                pass
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def validate_publication_state_directory(state_dir: str | Path) -> None:
    """Require the exact private directory contract before accepting stdin."""
    descriptor = _open_private_state_directory(Path(state_dir))
    os.close(descriptor)


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("publication input write failed")
        offset += written


def _fsync_publication_directory(descriptor: int) -> None:
    os.fsync(descriptor)


class PublicationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    lane: MaintainerLane
    state: MaintainerState
    machine_state: MachineState
    superseded_hold_head: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
    )
    exact_repair_push_handoff: bool = False


class OutcomePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    lane: MaintainerLane
    state: MaintainerState
    machine_state: MachineState
    outcome_state: OutcomeState


def _has_unsafe_sequences(value: str) -> bool:
    return bool(_UNSAFE_SUMMARY_CONTROL.search(value)) or any(
        marker in value for marker in _MAINTAINER_MARKERS
    )


def replace_managed_body(
    current: str,
    managed: str,
    *,
    adopt_unmanaged: bool = False,
) -> str:
    if BODY_START in managed or BODY_END in managed:
        raise ValueError("managed content must not contain managed body markers")

    start_count = current.count(BODY_START)
    end_count = current.count(BODY_END)
    if start_count == 0 and end_count == 0:
        block = _managed_block(managed)
        return block if not current or adopt_unmanaged else f"{current}\n\n{block}"
    if start_count != 1 or end_count != 1:
        raise ValueError("managed body markers are malformed or duplicated")

    start = current.index(BODY_START)
    end = current.index(BODY_END)
    if end < start:
        raise ValueError("managed body markers are reversed")
    suffix = end + len(BODY_END)
    return f"{current[:start]}{_managed_block(managed)}{current[suffix:]}"


def extract_managed_body(current: str) -> str | None:
    """Return trusted managed body content while rejecting malformed markers."""
    start_count = current.count(BODY_START)
    end_count = current.count(BODY_END)
    if start_count == 0 and end_count == 0:
        return None
    if start_count != 1 or end_count != 1:
        raise ValueError("managed body markers are malformed or duplicated")

    start = current.index(BODY_START)
    end = current.index(BODY_END)
    if end < start:
        raise ValueError("managed body markers are reversed")
    content_start = start + len(BODY_START)
    managed = current[content_start:end]
    if managed.startswith("\n"):
        managed = managed[1:]
    if managed.endswith("\n"):
        managed = managed[:-1]
    return managed


def ensure_curation_report_link(
    managed_body: str,
    *,
    reviewed_head: str,
    report_path: str,
) -> str:
    """Append or refresh the exact-head link to the rendered curation report."""
    if (
        type(managed_body) is not str
        or not _GIT_SHA.fullmatch(reviewed_head)
        or not _CURATION_REPORT_PATH.fullmatch(report_path)
    ):
        raise PublicationInputError("curation report link input is unsafe")
    rendered_path = f"{report_path.removesuffix('.json')}.md"
    report_url = f"https://github.com/{REPOSITORY}/blob/{reviewed_head}/{rendered_path}"
    markdown_link = f"[Open the full curation report]({report_url})"
    generated_block = f"## Full report\n\n{markdown_link}"
    if managed_body.endswith(generated_block):
        return managed_body
    body_without_generated_link = _GENERATED_REPORT_LINK.sub("", managed_body).rstrip()
    return f"{body_without_generated_link}\n\n{generated_block}"


def _managed_block(managed: str) -> str:
    return f"{BODY_START}\n{managed}\n{BODY_END}"


def render_machine_state(machine_state: MachineState) -> str:
    if type(machine_state) is not MachineState:
        raise TypeError("machine state must use schema version 2")
    state = MachineState.model_validate(machine_state.model_dump())
    if _machine_state_has_unsafe_strings(state):
        raise ValueError("machine state contains an unsafe string")
    payload = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{_MACHINE_MARKER_PREFIX}{payload}{_MACHINE_MARKER_SUFFIX}"


def render_outcome_state(outcome_state: OutcomeState) -> str:
    if type(outcome_state) is not OutcomeState:
        raise TypeError("outcome state must use schema version 1")
    state = OutcomeState.model_validate(outcome_state.model_dump())
    payload = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{_OUTCOME_MARKER_PREFIX}{payload}{_OUTCOME_MARKER_SUFFIX}"


def _decode_machine_marker(comment_body: str) -> tuple[MachineState, str] | None:
    if comment_body.count(_MACHINE_MARKER_PREFIX) != 1:
        return None
    matches = _MACHINE_MARKER.findall(comment_body)
    if len(matches) != 1:
        return None
    payload = matches[0]
    try:
        state = MachineState.model_validate(json.loads(payload))
        marker = render_machine_state(state)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if marker != f"{_MACHINE_MARKER_PREFIX}{payload}{_MACHINE_MARKER_SUFFIX}":
        return None
    return state, marker


def _decode_outcome_marker(comment_body: str) -> tuple[OutcomeState, str] | None:
    if comment_body.count(_OUTCOME_MARKER_PREFIX) != 1:
        return None
    matches = _OUTCOME_MARKER.findall(comment_body)
    if len(matches) != 1:
        return None
    payload = matches[0]
    try:
        state = OutcomeState.model_validate(json.loads(payload))
        marker = render_outcome_state(state)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if marker != f"{_OUTCOME_MARKER_PREFIX}{payload}{_OUTCOME_MARKER_SUFFIX}":
        return None
    return state, marker


def _canonical_remainder(comment_body: str, markers: Sequence[str]) -> bool:
    remainder = comment_body
    for marker in markers:
        remainder = remainder.replace(marker, "", 1)
    if remainder.count(SUMMARY_MARKER) > 1:
        return False
    remainder = remainder.replace(SUMMARY_MARKER, "", 1)
    return not any(delimiter in remainder for delimiter in _HTML_COMMENT_DELIMITERS)


def parse_machine_state(comment_body: str) -> MachineState | None:
    if type(comment_body) is not str or _has_strict_control(comment_body):
        return None
    decoded = _decode_machine_marker(comment_body)
    if decoded is None:
        return None
    state, machine_marker = decoded
    markers = [machine_marker]
    if _OUTCOME_MARKER_PREFIX in comment_body:
        outcome = _decode_outcome_marker(comment_body)
        if outcome is None:
            return None
        markers.append(outcome[1])
    return state if _canonical_remainder(comment_body, markers) else None


def parse_outcome_state(comment_body: str) -> OutcomeState | None:
    if type(comment_body) is not str or _has_strict_control(comment_body):
        return None
    decoded = _decode_outcome_marker(comment_body)
    if decoded is None:
        return None
    state, outcome_marker = decoded
    markers = [outcome_marker]
    if _MACHINE_MARKER_PREFIX in comment_body:
        machine = _decode_machine_marker(comment_body)
        if machine is None:
            return None
        markers.append(machine[1])
    return state if _canonical_remainder(comment_body, markers) else None


def trusted_machine_state(
    comments: Sequence[GitHubComment],
) -> MachineState | None:
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
    return parse_machine_state(body)


def trusted_outcome_state(
    comments: Sequence[GitHubComment],
) -> OutcomeState | None:
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
    return parse_outcome_state(body)


def trusted_hold_head(
    pull_request: PullRequest,
    comments: Sequence[GitHubComment],
) -> str | None:
    lifecycle_state = pull_request.maintainer_state
    outcome = trusted_outcome_state(comments)
    if (
        lifecycle_state is not None
        and outcome is not None
        and outcome.state == lifecycle_state.value
    ):
        return outcome.observed_head
    machine = trusted_machine_state(comments)
    return machine.reviewed_head if machine is not None else None


def _machine_state_has_unsafe_strings(machine_state: MachineState) -> bool:
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


def ci_publication_machine_state(
    *,
    continuation: CiContinuation,
    pull_request: PullRequest,
    repair_checkpoint_revalidated: bool,
) -> MachineState:
    if (
        type(continuation) is not CiContinuation
        or type(pull_request) is not PullRequest
        or type(repair_checkpoint_revalidated) is not bool
    ):
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "CI publication evidence must use strict helper-owned values",
            stage=ErrorStage.READINESS,
        )
    if continuation.phase not in {
        CiContinuationPhase.INITIAL_WAIT,
        CiContinuationPhase.SECOND_WAIT,
    }:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "CI continuation is not in a publishable wait phase",
            stage=ErrorStage.READINESS,
        )
    if (
        pull_request.number != continuation.pr_number
        or pull_request.head_ref_name != continuation.branch
        or pull_request.head_sha != continuation.current_head
    ):
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "PR identity differs from the CI continuation",
            stage=ErrorStage.READINESS,
        )
    repaired = continuation.phase is CiContinuationPhase.SECOND_WAIT
    if repaired != repair_checkpoint_revalidated:
        raise _publication_error(
            ErrorReason.VALIDATION_REQUIRED,
            "Repaired CI publication requires exact checkpoint revalidation",
            stage=ErrorStage.READINESS,
        )
    return MachineState(
        schema_version=2,
        reviewed_head=continuation.current_head,
        validated_head=continuation.current_head,
        last_operation="published",
    )


def publication_plan(
    *,
    requested_state: MaintainerState,
    lane: MaintainerLane,
    pull_request: PullRequest,
    machine_state: MachineState,
    superseded_hold_head: str | None = None,
    exact_repair_push_handoff: bool = False,
    proposal_validation: ProposalValidationResult | None = None,
    discovery_inventory: object | None = None,
) -> PublicationPlan:
    _require_publication_authority(pull_request, lane)
    if type(requested_state) is not MaintainerState:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Requested lifecycle state is not allowlisted",
        )
    if type(machine_state) is not MachineState:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Machine state must use schema version 2",
        )
    machine_state = MachineState.model_validate(machine_state.model_dump())
    if type(exact_repair_push_handoff) is not bool or (
        exact_repair_push_handoff
        and (
            requested_state is not MaintainerState.WAITING_CI
            or machine_state.last_operation != "published"
        )
    ):
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Exact repair push handoff is limited to published waiting-CI evidence",
            stage=ErrorStage.READINESS,
        )
    if (
        MaintainerState.PROPOSAL.value in pull_request.labels
        and requested_state is not MaintainerState.PROPOSAL
    ):
        stage = (
            ErrorStage.READINESS
            if requested_state in {MaintainerState.WAITING_CI, MaintainerState.READY}
            else ErrorStage.PUBLISH
        )
        raise _publication_error(
            ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
            "Proposal still requires owner approval",
            stage=stage,
        )
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
        if machine_state.last_operation not in {"pushed", "published"}:
            raise _publication_error(
                ErrorReason.VALIDATION_REQUIRED,
                "Current head has no matching pushed evidence",
                stage=ErrorStage.READINESS,
            )
        if pull_request.check_state != "pending" and not exact_repair_push_handoff:
            raise _publication_error(
                ErrorReason.NOT_READY,
                "Required checks are not pending",
                stage=ErrorStage.READINESS,
            )
    elif requested_state is MaintainerState.READY:
        require_ready(
            pull_request,
            machine_state,
            lane,
            superseded_hold_head=superseded_hold_head,
        )
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
        superseded_hold_head=superseded_hold_head,
        exact_repair_push_handoff=exact_repair_push_handoff,
    )


def outcome_plan(
    *,
    requested_state: MaintainerState,
    reason: str,
    lane: MaintainerLane,
    pull_request: PullRequest,
    existing_machine_state: MachineState | None,
) -> OutcomePlan:
    _require_publication_authority(pull_request, lane)
    if requested_state not in {
        MaintainerState.BLOCKED,
        MaintainerState.OWNER_DECISION,
    }:
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Outcome state is not allowlisted",
        )
    if MaintainerState.PROPOSAL.value in pull_request.labels:
        raise _publication_error(
            ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
            "Proposal still requires owner approval",
        )
    machine_state = existing_machine_state or MachineState(
        schema_version=2,
        last_operation="none",
    )
    if type(machine_state) is not MachineState:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Existing machine state is not trusted",
        )
    try:
        outcome_state = OutcomeState(
            schema_version=1,
            observed_head=pull_request.head_sha,
            state=requested_state.value,
            reason=reason,
        )
    except ValueError:
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Outcome state or reason is invalid",
        ) from None
    return OutcomePlan(
        lane=lane,
        state=requested_state,
        machine_state=machine_state,
        outcome_state=outcome_state,
    )


def require_ready(
    pull_request: PullRequest,
    machine_state: MachineState,
    lane: MaintainerLane | None = None,
    *,
    superseded_hold_head: str | None = None,
) -> None:
    if (
        type(pull_request) is not PullRequest
        or type(machine_state) is not MachineState
        or (lane is not None and type(lane) is not MaintainerLane)
    ):
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Readiness requires strict pull request and machine state",
            stage=ErrorStage.READINESS,
        )
    authority_lane = pull_request.lane if lane is None else lane
    _require_publication_authority(pull_request, authority_lane)
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
    blocking_states = {
        state for state in _READY_BLOCKING_STATES if state.value in pull_request.labels
    }
    stale_hold = (
        superseded_hold_head is not None
        and superseded_hold_head != pull_request.head_sha
    )
    if blocking_states and not (
        stale_hold and MaintainerState.PROPOSAL not in blocking_states
    ):
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
    machine_state: MachineState,
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
    accepted_proposal_transition = (
        pull_request.lane is MaintainerLane.CATALOG_DISCOVERY
        and lane is MaintainerLane.CATALOG_CURATION
    )
    if (
        not pull_request.routing_labels_valid
        or pull_request.lifecycle_state != "OPEN"
        or pull_request.is_cross_repository
        or pull_request.head_repository_owner != TRUSTED_MAINTAINER_LOGIN
        or pull_request.base_ref_name != "main"
        or not is_safe_codex_branch(pull_request.head_ref_name)
        or pull_request.url.host != "github.com"
        or pull_request.url.path != expected_path
        or (
            pull_request.lane is not None
            and pull_request.lane is not lane
            and not accepted_proposal_transition
        )
    ):
        raise _publication_error(
            ErrorReason.INVALID_GITHUB_STATE,
            "Pull request is outside publication authority",
        )


def _require_proposal_plan(
    lane: MaintainerLane,
    pull_request: PullRequest,
    machine_state: MachineState,
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
    kind: Literal["title", "body", "summary", "inventory-disposition"],
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
        raise PublicationInputError(
            "publication input is unsafe",
            kind=ErrorKind.NOT_BASENAME,
        )
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


class _StatePublicationClient(_PublicationClient, Protocol):
    def get_pull_request(self, number: int) -> PullRequest: ...


class _ProposalGitHubClient(_StatePublicationClient, Protocol):
    def create_draft_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
    ) -> int: ...

    def find_pull_requests_by_head(
        self,
        branch: str,
        head_sha: str,
    ) -> list[PullRequest]: ...


class _ProposalRepository(Protocol):
    def current_head(self) -> str: ...

    def optional_remote_head(self, branch: str) -> str | None: ...

    def push_create_only(self, branch: str, reviewed_head: str) -> None: ...


def publish_state(
    client: _StatePublicationClient,
    pull_request: PullRequest,
    plan: PublicationPlan,
    managed_body: str | None,
    summary: str,
    *,
    adopt_unmanaged_body: bool = False,
    allow_comment_repair: bool = False,
    mutation_guard: Callable[[], AbstractContextManager[None]] | None = None,
    validate_mutation: Callable[[str, PullRequest], None] | None = None,
    step_hook: Callable[[str], None] | None = None,
    report_path: str | None = None,
) -> bool:
    """Publish one exact-head state with a fresh PR read before every mutation."""
    if type(pull_request) is not PullRequest or type(plan) is not PublicationPlan:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Publication requires strict pull request and plan values",
        )
    if plan.machine_state.reviewed_head != pull_request.head_sha:
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "PR head differs from the reviewed head",
        )
    readiness_states = {MaintainerState.WAITING_CI, MaintainerState.READY}
    if plan.state in readiness_states:
        if managed_body is None:
            raise _publication_error(
                ErrorReason.PUBLICATION_INPUT,
                "Readiness publication requires managed body text",
            )
    if adopt_unmanaged_body and plan.state not in readiness_states:
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Managed body adoption is limited to readiness publication",
        )
    if adopt_unmanaged_body and managed_body is None:
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Managed body adoption requires managed body text",
        )
    if report_path is not None and managed_body is not None:
        reviewed_head = plan.machine_state.reviewed_head
        if reviewed_head is None:
            raise _publication_error(
                ErrorReason.PUBLICATION_INPUT,
                "Curation report links require a reviewed head",
            )
        managed_body = ensure_curation_report_link(
            managed_body,
            reviewed_head=reviewed_head,
            report_path=report_path,
        )
    desired_comment = _render_summary(summary, plan.machine_state)
    mutated = False
    if managed_body is not None:
        if (
            type(managed_body) is not str
            or BODY_START in managed_body
            or BODY_END in managed_body
        ):
            raise _publication_error(
                ErrorReason.PUBLICATION_INPUT,
                "Managed body text is unsafe",
            )

        current = _refetch_publication_target(client, pull_request, plan)
        _canonical_comment_snapshot(
            client.list_issue_comments(current.number),
            allow_comment_repair=allow_comment_repair,
        )
        try:
            desired_body = replace_managed_body(
                current.body,
                managed_body,
                adopt_unmanaged=adopt_unmanaged_body,
            )
        except ValueError:
            raise _publication_error(
                ErrorReason.INVALID_GITHUB_STATE,
                "Managed body markers are not trusted",
            ) from None
        if len(desired_body.encode("utf-8")) > _PUBLICATION_TEXT_LIMITS["body"]:
            raise _publication_error(
                ErrorReason.PUBLICATION_INPUT,
                "Managed pull request body exceeds the allowed limit",
            )
        if desired_body != current.body:
            _run_mutation_validation(validate_mutation, "body", current)
            with _mutation_context(mutation_guard):
                client.update_pull_request_body(current.number, desired_body)
            mutated = True
            _run_step_hook(step_hook, "body")

    current = _refetch_publication_target(client, pull_request, plan)
    comments = tuple(client.list_issue_comments(current.number))
    existing = _canonical_comment_snapshot(
        comments,
        allow_comment_repair=allow_comment_repair,
    )
    if existing is None:
        _run_mutation_validation(validate_mutation, "comment", current)
        with _mutation_context(mutation_guard):
            client.create_comment(current.number, desired_comment)
        mutated = True
        _run_step_hook(step_hook, "comment")
    elif existing.body != desired_comment:
        _run_mutation_validation(validate_mutation, "comment", current)
        with _mutation_context(mutation_guard):
            client.update_comment(existing.comment_id, desired_comment)
        mutated = True
        _run_step_hook(step_hook, "comment")

    current = _refetch_publication_target(client, pull_request, plan)
    add, remove = label_plan(current.labels, plan.lane, plan.state)
    if add or remove:
        _run_mutation_validation(validate_mutation, "labels", current)
        with _mutation_context(mutation_guard):
            client.update_labels(current.number, add, remove)
        mutated = True
        _run_step_hook(step_hook, "labels")
    return mutated


def publish_outcome(
    client: _StatePublicationClient,
    pull_request: PullRequest,
    plan: OutcomePlan,
    summary: str,
    *,
    allow_comment_repair: bool = False,
    mutation_guard: Callable[[], AbstractContextManager[None]] | None = None,
    validate_mutation: Callable[[str, PullRequest], None] | None = None,
    step_hook: Callable[[str], None] | None = None,
) -> bool:
    """Publish a terminal status without changing body or review evidence."""
    if type(pull_request) is not PullRequest or type(plan) is not OutcomePlan:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Outcome publication requires strict pull request and plan values",
        )
    if plan.outcome_state.observed_head != pull_request.head_sha:
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "PR head differs from the observed outcome head",
        )
    desired_comment = _render_summary(
        summary,
        plan.machine_state,
        outcome_state=plan.outcome_state,
    )
    mutated = False

    current = _refetch_outcome_target(client, pull_request, plan)
    comments = tuple(client.list_issue_comments(current.number))
    existing = _canonical_comment_snapshot(
        comments,
        allow_comment_repair=allow_comment_repair,
    )
    current_machine = trusted_machine_state(comments)
    empty_machine = MachineState(schema_version=2, last_operation="none")
    if current_machine != plan.machine_state and not (
        current_machine is None
        and plan.machine_state == empty_machine
        and allow_comment_repair
    ):
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "Canonical review evidence changed during outcome publication",
        )
    if existing is None:
        _run_mutation_validation(validate_mutation, "comment", current)
        with _mutation_context(mutation_guard):
            client.create_comment(current.number, desired_comment)
        mutated = True
        _run_step_hook(step_hook, "comment")
    elif existing.body != desired_comment:
        _run_mutation_validation(validate_mutation, "comment", current)
        with _mutation_context(mutation_guard):
            client.update_comment(existing.comment_id, desired_comment)
        mutated = True
        _run_step_hook(step_hook, "comment")

    current = _refetch_outcome_target(client, pull_request, plan)
    add, remove = label_plan(current.labels, plan.lane, plan.state)
    if add or remove:
        _run_mutation_validation(validate_mutation, "labels", current)
        with _mutation_context(mutation_guard):
            client.update_labels(current.number, add, remove)
        mutated = True
        _run_step_hook(step_hook, "labels")
    return mutated


def validate_outcome_publication_input(
    plan: OutcomePlan,
    summary: str,
) -> None:
    """Validate canonical terminal text without performing external mutation."""
    if type(plan) is not OutcomePlan:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Outcome publication requires a strict plan",
        )
    _render_summary(
        summary,
        plan.machine_state,
        outcome_state=plan.outcome_state,
    )


def publish_discovery_proposal(
    *,
    store: StateStore,
    lease: RunLease,
    repository: _ProposalRepository,
    github: _ProposalGitHubClient,
    work_id: str,
    branch: str,
    proposal_validation: ProposalValidationResult,
    inventory_provider: Callable[[], object],
    title: str,
    initial_body: str,
    managed_body: str,
    summary: str,
    step_hook: Callable[[str], None] | None = None,
) -> PushJournal:
    """Create or recover one validated discovery proposal without duplication."""
    from ops.maintainer.inspection import DiscoveryInventory
    from ops.maintainer.validation import ProposalValidationResult

    lease.assert_owner()
    if type(store) is not StateStore or type(lease) is not RunLease:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Proposal publication requires strict state ownership",
            stage=ErrorStage.PRE_PUSH,
        )
    if type(proposal_validation) is not ProposalValidationResult:
        raise _publication_error(
            ErrorReason.VALIDATION_REQUIRED,
            "Proposal validation evidence is incomplete",
            stage=ErrorStage.PRE_PUSH,
        )
    validation = ProposalValidationResult.model_validate(
        proposal_validation.model_dump()
    )
    _validate_proposal_publication_inputs(
        title=title,
        initial_body=initial_body,
        managed_body=managed_body,
        summary=summary,
        validation=validation,
    )
    if not is_safe_catalog_curation_branch(branch):
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Proposal branch is outside the allowed namespace",
            stage=ErrorStage.PRE_PUSH,
        )

    journal = store.load_push(work_id)
    unresolved = store.list_unresolved_pushes()
    if journal is None:
        if unresolved:
            raise _publication_error(
                ErrorReason.INVALID_COMMAND,
                "Unresolved push journal blocks fresh proposal work",
                stage=ErrorStage.PRE_PUSH,
            )
        inventory = _load_discovery_inventory(inventory_provider, DiscoveryInventory)
        _require_current_proposal_facts(
            validation,
            inventory,
            repository.current_head(),
        )
        if repository.optional_remote_head(branch) is not None:
            raise _publication_error(
                ErrorReason.STALE_HEAD,
                "Proposal branch already exists remotely",
                stage=ErrorStage.PRE_PUSH,
            )
        journal = PushJournal(
            work_id=work_id,
            worker="discovery",
            origin_run_id=lease.run_id,
            recovery_run_id=lease.run_id,
            branch=branch,
            new_head=validation.validated_head,
            candidate_key=validation.candidate_key,
            candidate_origin=validation.candidate_origin,
            report_path=validation.report_path,
            resulting_graph_markdown=validation.resulting_graph_markdown,
            phase=PushPhase.AUTHORIZED,
        )
        store.save_push(journal, lease)
        _run_step_hook(step_hook, "authorized")
    else:
        _require_matching_proposal_journal(journal, branch, validation)
        if journal.phase is PushPhase.PUBLISHED:
            return journal
        if len(unresolved) != 1 or unresolved[0].work_id != work_id:
            raise _publication_error(
                ErrorReason.INVALID_COMMAND,
                "Proposal recovery requires exactly one matching journal",
                stage=ErrorStage.PRE_PUSH,
            )
        if journal.recovery_run_id != lease.run_id:
            observed_remote = repository.optional_remote_head(branch)
            journal = store.adopt_push(work_id, lease, observed_remote)

    _require_matching_proposal_journal(journal, branch, validation)
    if repository.current_head() != journal.new_head:
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "Local head differs from validated proposal head",
            stage=ErrorStage.PRE_PUSH,
        )

    if journal.phase is PushPhase.AUTHORIZED:
        inventory = _load_discovery_inventory(inventory_provider, DiscoveryInventory)
        _require_current_proposal_facts(
            validation,
            inventory,
            repository.current_head(),
        )
        remote_head = repository.optional_remote_head(branch)
        if remote_head is None:
            with store.guard_push_mutation(journal, lease):
                repository.push_create_only(branch, journal.new_head)
            _run_step_hook(step_hook, "push")
        elif remote_head != journal.new_head:
            raise _publication_error(
                ErrorReason.STALE_HEAD,
                "Remote proposal head is not recoverable",
                stage=ErrorStage.PUSH,
            )
        journal = journal.model_copy(update={"phase": PushPhase.PUSHED})
        store.save_push(journal, lease)

    if journal.phase is PushPhase.PUSHED:
        remote_head = repository.optional_remote_head(branch)
        if remote_head != journal.new_head:
            raise _publication_error(
                ErrorReason.STALE_HEAD,
                "Remote proposal head is not recoverable",
                stage=ErrorStage.PROPOSAL_CREATE,
            )
        matches = github.find_pull_requests_by_head(branch, journal.new_head)
        if len(matches) > 1:
            raise _publication_error(
                ErrorReason.INVALID_GITHUB_STATE,
                "Multiple pull requests match the proposal branch",
                stage=ErrorStage.PROPOSAL_CREATE,
            )
        if matches:
            proposal = matches[0]
        else:
            inventory = _load_discovery_inventory(
                inventory_provider,
                DiscoveryInventory,
            )
            _require_current_proposal_facts(
                validation,
                inventory,
                repository.current_head(),
            )
            with store.guard_push_mutation(journal, lease):
                pr_number = github.create_draft_pull_request(
                    branch,
                    title,
                    initial_body,
                )
            _run_step_hook(step_hook, "pr")
            proposal = github.get_pull_request(pr_number)
        _require_exact_draft_proposal(proposal, branch, journal.new_head)
        journal = journal.model_copy(
            update={"phase": PushPhase.PR_CREATED, "pr_number": proposal.number}
        )
        store.save_push(journal, lease)

    if journal.phase is PushPhase.PR_CREATED:
        pr_number = journal.pr_number
        if pr_number is None:
            raise _publication_error(
                ErrorReason.INVALID_COMMAND,
                "Created proposal journal is missing its pull request",
                stage=ErrorStage.PUBLISH,
            )
        if repository.optional_remote_head(branch) != journal.new_head:
            raise _publication_error(
                ErrorReason.STALE_HEAD,
                "Remote proposal head is not recoverable",
                stage=ErrorStage.PUBLISH,
            )
        matches = github.find_pull_requests_by_head(branch, journal.new_head)
        if len(matches) != 1 or matches[0].number != pr_number:
            raise _publication_error(
                ErrorReason.INVALID_GITHUB_STATE,
                "Proposal journal does not have one exact pull request",
                stage=ErrorStage.PUBLISH,
            )
        proposal = github.get_pull_request(pr_number)
        _require_exact_draft_proposal(proposal, branch, journal.new_head)
        proposal_label_was_present = MaintainerState.PROPOSAL.value in proposal.labels
        proposal_comments = tuple(github.list_issue_comments(proposal.number))
        if not proposal_label_was_present and any(
            comment.author_login == TRUSTED_MAINTAINER_LOGIN
            and SUMMARY_MARKER in comment.body
            for comment in proposal_comments
        ):
            raise _publication_error(
                ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
                "Proposal label absence requires owner review",
            )
        inventory = _load_discovery_inventory(inventory_provider, DiscoveryInventory)
        effective_inventory = _inventory_without_bound_proposal(
            inventory,
            proposal,
            proposal_comments,
            validation,
        )
        _require_current_proposal_facts(
            validation,
            effective_inventory,
            repository.current_head(),
        )
        machine_state = _proposal_machine_state(validation)
        plan = publication_plan(
            requested_state=MaintainerState.PROPOSAL,
            lane=MaintainerLane.CATALOG_DISCOVERY,
            pull_request=proposal,
            machine_state=machine_state,
            proposal_validation=validation,
            discovery_inventory=effective_inventory,
        )

        def validate_proposal_mutation(step: str, current: PullRequest) -> None:
            if step != "labels":
                return
            if (
                proposal_label_was_present
                and MaintainerState.PROPOSAL.value not in current.labels
            ):
                raise _publication_error(
                    ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
                    "Proposal label changed during publication",
                )
            latest_inventory = _load_discovery_inventory(
                inventory_provider,
                DiscoveryInventory,
            )
            latest_effective_inventory = _inventory_without_bound_proposal(
                latest_inventory,
                current,
                github.list_issue_comments(current.number),
                validation,
            )
            _require_current_proposal_facts(
                validation,
                latest_effective_inventory,
                repository.current_head(),
            )
            publication_plan(
                requested_state=MaintainerState.PROPOSAL,
                lane=MaintainerLane.CATALOG_DISCOVERY,
                pull_request=current,
                machine_state=machine_state,
                proposal_validation=validation,
                discovery_inventory=latest_effective_inventory,
            )

        publish_state(
            github,
            proposal,
            plan,
            managed_body,
            summary,
            allow_comment_repair=True,
            mutation_guard=lambda: store.guard_push_mutation(journal, lease),
            validate_mutation=validate_proposal_mutation,
            step_hook=step_hook,
            report_path=validation.report_path,
        )
        journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
        store.save_push(journal, lease)
    return journal


def _render_summary(
    summary: str,
    machine_state: MachineState,
    *,
    outcome_state: OutcomeState | None = None,
) -> str:
    if (
        type(summary) is not str
        or len(summary.encode("utf-8")) > _PUBLICATION_TEXT_LIMITS["summary"]
    ):
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Canonical summary text is unsafe",
        )
    summary = summary.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    if (
        not summary.strip()
        or _has_unsafe_sequences(summary)
        or any(delimiter in summary for delimiter in _HTML_COMMENT_DELIMITERS)
    ):
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Canonical summary text is unsafe",
        )
    rendered = (
        f"{SUMMARY_MARKER}\n## Snowcast maintainer summary\n\n{summary}\n\n"
        f"{render_machine_state(machine_state)}"
    )
    if outcome_state is not None:
        rendered = f"{rendered}\n{render_outcome_state(outcome_state)}"
    return rendered


def _validate_proposal_publication_inputs(
    *,
    title: str,
    initial_body: str,
    managed_body: str,
    summary: str,
    validation: ProposalValidationResult,
) -> None:
    if (
        type(title) is not str
        or not title.strip()
        or "\n" in title
        or "\r" in title
        or len(title.encode("utf-8")) > _PUBLICATION_TEXT_LIMITS["title"]
        or type(initial_body) is not str
        or len(initial_body.encode("utf-8")) > _PUBLICATION_TEXT_LIMITS["body"]
        or type(managed_body) is not str
    ):
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Proposal publication text is unsafe",
            stage=ErrorStage.PRE_PUSH,
        )
    try:
        final_body = replace_managed_body(initial_body, managed_body)
    except (TypeError, ValueError):
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Proposal publication text is unsafe",
            stage=ErrorStage.PRE_PUSH,
        ) from None
    if len(final_body.encode("utf-8")) > _PUBLICATION_TEXT_LIMITS["body"]:
        raise _publication_error(
            ErrorReason.PUBLICATION_INPUT,
            "Proposal publication text is unsafe",
            stage=ErrorStage.PRE_PUSH,
        )
    _render_summary(summary, _proposal_machine_state(validation))


def _proposal_machine_state(
    validation: ProposalValidationResult,
) -> MachineState:
    return MachineState(
        schema_version=2,
        reviewed_head=validation.validated_head,
        validated_head=validation.validated_head,
        candidate_key=validation.candidate_key,
        candidate_origin=validation.candidate_origin,
        last_operation="published",
    )


def _refetch_publication_target(
    client: _StatePublicationClient,
    expected: PullRequest,
    plan: PublicationPlan,
) -> PullRequest:
    current = client.get_pull_request(expected.number)
    _require_publication_authority(current, plan.lane)
    immutable_facts = (
        "number",
        "url",
        "base_ref_name",
        "head_ref_name",
        "head_repository_owner",
        "is_cross_repository",
        "is_draft",
        "lifecycle_state",
        "head_sha",
    )
    if any(
        getattr(current, field_name) != getattr(expected, field_name)
        for field_name in immutable_facts
    ):
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "Pull request changed during publication",
        )
    if plan.state is not MaintainerState.PROPOSAL:
        publication_plan(
            requested_state=plan.state,
            lane=plan.lane,
            pull_request=current,
            machine_state=plan.machine_state,
            superseded_hold_head=plan.superseded_hold_head,
            exact_repair_push_handoff=plan.exact_repair_push_handoff,
        )
    return current


def _refetch_outcome_target(
    client: _StatePublicationClient,
    expected: PullRequest,
    plan: OutcomePlan,
) -> PullRequest:
    current = client.get_pull_request(expected.number)
    _require_publication_authority(current, plan.lane)
    immutable_facts = (
        "number",
        "url",
        "base_ref_name",
        "head_ref_name",
        "head_repository_owner",
        "is_cross_repository",
        "is_draft",
        "lifecycle_state",
        "head_sha",
    )
    if any(
        getattr(current, field_name) != getattr(expected, field_name)
        for field_name in immutable_facts
    ):
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "Pull request changed during outcome publication",
        )
    outcome_plan(
        requested_state=plan.state,
        reason=plan.outcome_state.reason,
        lane=plan.lane,
        pull_request=current,
        existing_machine_state=plan.machine_state,
    )
    return current


def _load_discovery_inventory(
    provider: Callable[[], object],
    model_type: type[BaseModel],
) -> BaseModel:
    inventory = provider()
    if type(inventory) is not model_type:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Discovery inventory is missing or untrusted",
            stage=ErrorStage.PRE_PUSH,
        )
    return model_type.model_validate(inventory.model_dump())


def _require_current_proposal_facts(
    validation: ProposalValidationResult,
    inventory: object,
    local_head: str,
) -> None:
    from ops.maintainer.inspection import DiscoveryInventory

    if type(inventory) is not DiscoveryInventory:
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Discovery inventory is missing or untrusted",
            stage=ErrorStage.PRE_PUSH,
        )
    if local_head != validation.validated_head:
        raise _publication_error(
            ErrorReason.STALE_HEAD,
            "Local head differs from validated proposal head",
            stage=ErrorStage.PRE_PUSH,
        )
    if validation.candidate_key in inventory.catalog_keys:
        raise _publication_error(
            ErrorReason.DUPLICATE_PROPOSAL,
            "Candidate already exists in the catalog",
            stage=ErrorStage.PRE_PUSH,
        )
    if validation.candidate_key in inventory.open_candidate_keys:
        raise _publication_error(
            ErrorReason.DUPLICATE_PROPOSAL,
            "Candidate already has an open proposal",
            stage=ErrorStage.PRE_PUSH,
        )
    if (
        inventory.open_proposal_count >= 3
        or inventory.has_unknown_proposal_identity
        or inventory.unresolved_pushes
        or not inventory.can_create_proposal
    ):
        raise _publication_error(
            ErrorReason.PROPOSAL_CAP,
            "Current proposal inventory blocks publication",
            stage=ErrorStage.PRE_PUSH,
        )


def _require_matching_proposal_journal(
    journal: PushJournal,
    branch: str,
    validation: ProposalValidationResult,
) -> None:
    if (
        journal.worker != "discovery"
        or journal.branch != branch
        or journal.expected_remote_head is not None
        or journal.new_head != validation.validated_head
        or journal.candidate_key != validation.candidate_key
        or journal.candidate_origin != validation.candidate_origin
        or journal.report_path != validation.report_path
        or journal.resulting_graph_markdown != validation.resulting_graph_markdown
    ):
        raise _publication_error(
            ErrorReason.INVALID_COMMAND,
            "Push journal does not match proposal evidence",
            stage=ErrorStage.PRE_PUSH,
        )


def _require_exact_draft_proposal(
    pull_request: PullRequest,
    branch: str,
    head_sha: str,
) -> None:
    _require_publication_authority(pull_request, MaintainerLane.CATALOG_DISCOVERY)
    if (
        not pull_request.is_draft
        or pull_request.head_ref_name != branch
        or pull_request.head_sha != head_sha
    ):
        raise _publication_error(
            ErrorReason.INVALID_GITHUB_STATE,
            "Draft proposal does not match its journal",
            stage=ErrorStage.PROPOSAL_CREATE,
        )


def _inventory_without_bound_proposal(
    inventory: object,
    proposal: PullRequest,
    comments: Sequence[GitHubComment],
    validation: ProposalValidationResult,
) -> object:
    from ops.maintainer.inspection import DiscoveryInventory

    if type(inventory) is not DiscoveryInventory:
        return inventory
    desired_labels = {
        MaintainerLane.CATALOG_DISCOVERY.value,
        MaintainerState.PROPOSAL.value,
    }
    state = trusted_machine_state(comments)
    if not desired_labels.issubset(proposal.labels):
        return inventory
    if state is not None and (
        state.reviewed_head != proposal.head_sha
        or state.validated_head != proposal.head_sha
        or state.candidate_key != validation.candidate_key
        or state.candidate_origin != validation.candidate_origin
    ):
        return inventory
    summaries_complete = len(inventory.open_proposals) == inventory.open_proposal_count
    if summaries_complete:
        bound = tuple(
            item
            for item in inventory.open_proposals
            if item.pr_number == proposal.number
        )
        if len(bound) != 1 or (
            bound[0].candidate_key is not None
            and (
                bound[0].candidate_key != validation.candidate_key
                or bound[0].candidate_origin != validation.candidate_origin
            )
        ):
            return inventory
    elif inventory.open_proposal_count != 1:
        return inventory
    open_count = inventory.open_proposal_count - 1
    open_proposals = tuple(
        item for item in inventory.open_proposals if item.pr_number != proposal.number
    )
    open_keys = (
        frozenset(
            item.candidate_key
            for item in open_proposals
            if item.candidate_key is not None
        )
        if summaries_complete
        else inventory.open_candidate_keys - {validation.candidate_key}
    )
    return inventory.model_copy(
        update={
            "open_proposal_count": open_count,
            "open_candidate_keys": open_keys,
            "has_unknown_proposal_identity": any(
                not item.identity_known for item in open_proposals
            ),
            "can_create_proposal": (
                open_count < 3
                and all(item.identity_known for item in open_proposals)
                and not inventory.unresolved_pushes
            ),
            "open_proposals": open_proposals,
        }
    )


def _run_step_hook(
    step_hook: Callable[[str], None] | None,
    step: str,
) -> None:
    if step_hook is not None:
        step_hook(step)


def _canonical_comment_snapshot(
    comments: Sequence[GitHubComment],
    *,
    allow_comment_repair: bool,
) -> GitHubComment | None:
    marked_comments = tuple(
        comment
        for comment in comments
        if comment.author_login == TRUSTED_MAINTAINER_LOGIN
        and SUMMARY_MARKER in comment.body
    )
    if len(marked_comments) > 1:
        raise _publication_error(
            ErrorReason.INVALID_GITHUB_STATE,
            "Multiple canonical maintainer comments are not trusted",
        )
    if trusted_machine_state(comments) is None and not allow_comment_repair:
        raise _publication_error(
            ErrorReason.VALIDATION_REQUIRED,
            "Canonical comment requires a fresh review",
        )
    return marked_comments[0] if marked_comments else None


def _run_mutation_validation(
    validate: Callable[[str, PullRequest], None] | None,
    step: str,
    pull_request: PullRequest,
) -> None:
    if validate is not None:
        validate(step, pull_request)


def _mutation_context(
    guard: Callable[[], AbstractContextManager[None]] | None,
) -> AbstractContextManager[None]:
    return guard() if guard is not None else nullcontext()

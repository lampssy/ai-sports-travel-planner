from __future__ import annotations

import json
import re
from collections.abc import Sequence, Set
from typing import Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ops.maintainer import BODY_END, BODY_START, SUMMARY_MARKER
from ops.maintainer.github import GitHubComment
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)

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
    comments = client.list_issue_comments(pull_request.number)
    marked_comments = [
        comment for comment in comments if SUMMARY_MARKER in comment.body
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

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, Protocol

from ops.maintainer import REPOSITORY
from ops.maintainer.models import PullRequest

PR_FIELDS = (
    "number",
    "title",
    "url",
    "baseRefName",
    "headRefName",
    "headRepositoryOwner",
    "isCrossRepository",
    "createdAt",
    "labels",
    "headRefOid",
    "mergeable",
    "statusCheckRollup",
    "files",
    "body",
)

CheckState = Literal["pending", "success", "failure"]
_FAILURE_CONCLUSIONS = {
    "FAILURE",
    "CANCELLED",
    "TIMED_OUT",
    "ACTION_REQUIRED",
    "ERROR",
    "STARTUP_FAILURE",
    "STALE",
}
_PENDING_CONCLUSIONS = {"PENDING", "EXPECTED"}


class CommandRunner(Protocol):
    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]: ...


def run_command(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        list(argv),
        shell=False,
        check=True,
        text=True,
        capture_output=True,
    )


class GitHubError(RuntimeError):
    """A safe, body-free error raised for GitHub transport failures."""


@dataclass(frozen=True)
class GitHubComment:
    comment_id: int
    body: str


@contextmanager
def _temporary_body(body: str):
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as temporary_file:
        path = Path(temporary_file.name)
        os.chmod(path, 0o600)
        temporary_file.write(body)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def check_state(
    rollup: Sequence[Mapping[str, object]] | None,
) -> CheckState:
    if not rollup:
        return "pending"

    if any(not isinstance(item, Mapping) for item in rollup):
        raise TypeError("check rollup entries must be objects")
    conclusions: list[str | None] = []
    for item in rollup:
        status = item.get("status")
        conclusion = item.get("conclusion")
        if conclusion is None:
            conclusion = item.get("state")
        if status is not None and not isinstance(status, str):
            raise TypeError("check status must be a string")
        if conclusion is not None and not isinstance(conclusion, str):
            raise TypeError("check conclusion must be a string")
        conclusions.append(conclusion)
    if any(
        isinstance(conclusion, str) and conclusion.upper() in _FAILURE_CONCLUSIONS
        for conclusion in conclusions
    ):
        return "failure"

    for item, conclusion in zip(rollup, conclusions, strict=True):
        status = item.get("status")
        if conclusion is None:
            return "pending"
        if isinstance(conclusion, str) and conclusion.upper() in _PENDING_CONCLUSIONS:
            return "pending"
        if isinstance(status, str) and status.upper() != "COMPLETED":
            return "pending"
    return "success"


def parse_pull_request(value: Mapping[str, object]) -> PullRequest:
    try:
        owner = value["headRepositoryOwner"]
        if not isinstance(owner, Mapping):
            raise TypeError
        labels = value["labels"]
        files = value["files"]
        rollup = value["statusCheckRollup"]
        if not isinstance(labels, list) or not isinstance(files, list):
            raise TypeError
        if rollup is not None and not isinstance(rollup, list):
            raise TypeError
        created_at = value["createdAt"]
        if not isinstance(created_at, str):
            raise TypeError
        body = value.get("body")
        if body is None:
            body = ""
        if not isinstance(body, str):
            raise TypeError
        return PullRequest.model_validate(
            {
                "number": value["number"],
                "title": value["title"],
                "url": value["url"],
                "base_ref_name": value["baseRefName"],
                "head_ref_name": value["headRefName"],
                "head_repository_owner": owner["login"],
                "is_cross_repository": value["isCrossRepository"],
                "created_at": datetime.fromisoformat(
                    created_at.removesuffix("Z") + "+00:00"
                    if created_at.endswith("Z")
                    else created_at
                ),
                "labels": frozenset(_object_string(item, "name") for item in labels),
                "head_sha": value["headRefOid"],
                "mergeable": value["mergeable"],
                "check_state": check_state(rollup),
                "changed_paths": frozenset(
                    _object_string(item, "path") for item in files
                ),
                "body": body,
            }
        )
    except (KeyError, TypeError, ValueError):
        raise GitHubError("invalid GitHub response") from None


def _object_string(value: object, key: str) -> str:
    if not isinstance(value, Mapping):
        raise TypeError
    result = value[key]
    if not isinstance(result, str):
        raise TypeError
    return result


def _positive_id(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("identifier must be a positive integer")
    return value


class GitHubClient:
    def __init__(self, runner: CommandRunner = run_command) -> None:
        self._runner = runner

    def list_open_pull_requests(self) -> list[PullRequest]:
        result = self._run(
            (
                "gh",
                "pr",
                "list",
                "--repo",
                REPOSITORY,
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                ",".join(PR_FIELDS),
            )
        )
        payload = self._load_json(result.stdout)
        if not isinstance(payload, list):
            raise GitHubError("invalid GitHub response")
        return [parse_pull_request(item) for item in payload]

    def get_pull_request(self, number: int) -> PullRequest:
        number = _positive_id(number)
        result = self._run(
            (
                "gh",
                "pr",
                "view",
                str(number),
                "--repo",
                REPOSITORY,
                "--json",
                ",".join(PR_FIELDS),
            )
        )
        payload = self._load_json(result.stdout)
        if not isinstance(payload, Mapping):
            raise GitHubError("invalid GitHub response")
        return parse_pull_request(payload)

    def ensure_labels(
        self,
        definitions: Mapping[str, tuple[str, str]],
    ) -> None:
        result = self._run(
            (
                "gh",
                "label",
                "list",
                "--repo",
                REPOSITORY,
                "--limit",
                "100",
                "--json",
                "name,description,color",
            )
        )
        payload = self._load_json(result.stdout)
        if not isinstance(payload, list):
            raise GitHubError("invalid GitHub response")
        existing: dict[str, tuple[str, str]] = {}
        try:
            for item in payload:
                name = _object_string(item, "name")
                if name not in definitions:
                    continue
                if not isinstance(item, Mapping):
                    raise TypeError
                description = item.get("description")
                if description is None:
                    description = ""
                if not isinstance(description, str):
                    raise TypeError
                existing[name] = (description, _object_string(item, "color"))
        except (KeyError, TypeError):
            raise GitHubError("invalid GitHub response") from None

        for name in sorted(definitions):
            description, color = definitions[name]
            current = existing.get(name)
            if current is None:
                operation = "create"
            elif current[0] != description or current[1].lower() != color.lower():
                operation = "edit"
            else:
                continue
            self._run(
                (
                    "gh",
                    "label",
                    operation,
                    name,
                    "--repo",
                    REPOSITORY,
                    "--description",
                    description,
                    "--color",
                    color,
                )
            )

    def list_closed_proposal_comments(self) -> list[GitHubComment]:
        result = self._run(
            (
                "gh",
                "pr",
                "list",
                "--repo",
                REPOSITORY,
                "--state",
                "closed",
                "--label",
                "maintainer:proposal",
                "--limit",
                "200",
                "--json",
                "number",
            )
        )
        payload = self._load_json(result.stdout)
        if not isinstance(payload, list):
            raise GitHubError("invalid GitHub response")
        comments: list[GitHubComment] = []
        try:
            for pull_request in payload:
                if not isinstance(pull_request, Mapping):
                    raise TypeError
                comments.extend(
                    self.list_issue_comments(_positive_id(pull_request["number"]))
                )
        except (KeyError, TypeError, ValueError):
            raise GitHubError("invalid GitHub response") from None
        return comments

    def list_issue_comments(self, number: int) -> list[GitHubComment]:
        number = _positive_id(number)
        result = self._run(
            (
                "gh",
                "api",
                "--paginate",
                f"repos/{REPOSITORY}/issues/{number}/comments",
            )
        )
        comments: list[GitHubComment] = []
        try:
            for page in self._load_json_pages(result.stdout):
                if not isinstance(page, list):
                    raise TypeError
                for item in page:
                    if not isinstance(item, Mapping):
                        raise TypeError
                    comments.append(
                        GitHubComment(
                            comment_id=_positive_id(item["id"]),
                            body=_object_string(item, "body"),
                        )
                    )
        except (KeyError, TypeError, ValueError):
            raise GitHubError("invalid GitHub response") from None
        return comments

    def update_pull_request_body(self, number: int, body: str) -> None:
        number = _positive_id(number)
        with _temporary_body(body) as body_path:
            self._run(
                (
                    "gh",
                    "pr",
                    "edit",
                    str(number),
                    "--repo",
                    REPOSITORY,
                    "--body-file",
                    str(body_path),
                )
            )

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None:
        number = _positive_id(number)
        if not add and not remove:
            return
        argv = [
            "gh",
            "pr",
            "edit",
            str(number),
            "--repo",
            REPOSITORY,
        ]
        for label in sorted(add):
            argv.extend(("--add-label", label))
        for label in sorted(remove):
            argv.extend(("--remove-label", label))
        self._run(argv)

    def create_comment(self, number: int, body: str) -> int:
        number = _positive_id(number)
        with _temporary_body(body) as body_path:
            result = self._run(
                (
                    "gh",
                    "api",
                    "--method",
                    "POST",
                    f"repos/{REPOSITORY}/issues/{number}/comments",
                    "-F",
                    f"body=@{body_path}",
                )
            )
        try:
            payload = self._load_json(result.stdout)
            if not isinstance(payload, Mapping):
                raise TypeError
            return _positive_id(payload["id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise GitHubError("invalid GitHub response") from None

    def update_comment(self, comment_id: int, body: str) -> None:
        comment_id = _positive_id(comment_id)
        with _temporary_body(body) as body_path:
            self._run(
                (
                    "gh",
                    "api",
                    "--method",
                    "PATCH",
                    f"repos/{REPOSITORY}/issues/comments/{comment_id}",
                    "-F",
                    f"body=@{body_path}",
                )
            )

    def _run(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self._runner(argv)
        except (OSError, subprocess.SubprocessError):
            raise GitHubError("GitHub command failed") from None

    @staticmethod
    def _load_json(value: str) -> object:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise GitHubError("invalid GitHub response") from None

    @staticmethod
    def _load_json_pages(value: str) -> list[object]:
        decoder = json.JSONDecoder()
        pages: list[object] = []
        position = 0
        try:
            while position < len(value):
                while position < len(value) and value[position].isspace():
                    position += 1
                if position == len(value):
                    break
                page, position = decoder.raw_decode(value, position)
                pages.append(page)
        except json.JSONDecodeError:
            raise GitHubError("invalid GitHub response") from None
        if not pages:
            raise GitHubError("invalid GitHub response")
        return pages

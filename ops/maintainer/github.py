from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, Protocol
from urllib.parse import quote

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
    "isDraft",
    "state",
    "createdAt",
    "labels",
    "headRefOid",
    "mergeable",
    "statusCheckRollup",
    "files",
    "body",
)

CheckState = Literal["pending", "success", "failure"]
TRUSTED_MAINTAINER_LOGIN = "lampssy"
GITHUB_COMMAND_TIMEOUT_SECONDS = 120.0
DEFAULT_GH_CONFIG_DIR = Path.home() / ".config" / "gh-lampssy-snowcast"

_SUCCESS_CONCLUSIONS = {"SUCCESS"}
_PENDING_CONCLUSIONS = {"PENDING", "EXPECTED"}
_CATALOG_CURATION_BRANCH = re.compile(
    r"^codex/catalog-curation-[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"
)
_HEAD_SHA = re.compile(r"^[0-9a-f]{40}$")
_MAX_TITLE_BYTES = 256
_MAX_BODY_BYTES = 65_536


class CommandRunner(Protocol):
    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]: ...


class GitHubError(RuntimeError):
    """A safe, body-free error raised for GitHub transport failures."""


def run_command(
    argv: Sequence[str],
    *,
    gh_config_dir: Path,
) -> subprocess.CompletedProcess[str]:
    environment = {
        key: value
        for key in ("HOME", "LANG", "LC_ALL", "PATH", "TMPDIR")
        if (value := os.environ.get(key)) is not None
    }
    environment.setdefault("HOME", str(Path.home()))
    environment.setdefault("PATH", os.defpath)
    environment.update(
        {
            "GH_CONFIG_DIR": str(gh_config_dir),
            "GH_PROMPT_DISABLED": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
        }
    )
    try:
        return subprocess.run(  # noqa: S603
            list(argv),
            shell=False,
            check=True,
            text=True,
            capture_output=True,
            timeout=GITHUB_COMMAND_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        raise GitHubError("GitHub command failed") from None


@dataclass(frozen=True)
class GitHubComment:
    comment_id: int
    body: str
    author_login: str


@contextmanager
def _temporary_body(body: str):
    temporary_file = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    path = Path(temporary_file.name)
    try:
        with temporary_file:
            os.chmod(path, 0o600)
            temporary_file.write(body)
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
    has_failure = False
    has_pending = False
    for item, conclusion in zip(rollup, conclusions, strict=True):
        status = item.get("status")
        if isinstance(status, str) and status.upper() != "COMPLETED":
            has_pending = True
            continue
        if conclusion is None or conclusion.upper() in _PENDING_CONCLUSIONS:
            has_pending = True
        elif conclusion.upper() not in _SUCCESS_CONCLUSIONS:
            has_failure = True
    if has_failure:
        return "failure"
    if has_pending:
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
        is_draft = value.get("isDraft", False)
        if not isinstance(is_draft, bool):
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
                "is_draft": is_draft,
                "lifecycle_state": value["state"],
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


def _validated_catalog_curation_branch(branch: str) -> str:
    if not is_safe_catalog_curation_branch(branch):
        raise ValueError("branch is not an allowed catalog-curation branch")
    return branch


def is_safe_catalog_curation_branch(branch: object) -> bool:
    return (
        isinstance(branch, str)
        and _CATALOG_CURATION_BRANCH.fullmatch(branch) is not None
    )


def _validated_title(title: str) -> str:
    if (
        not isinstance(title, str)
        or not title.strip()
        or "\r" in title
        or "\n" in title
        or len(title.encode("utf-8")) > _MAX_TITLE_BYTES
    ):
        raise ValueError("title is invalid")
    return title


def _validated_body(body: str) -> str:
    if not isinstance(body, str) or len(body.encode("utf-8")) > _MAX_BODY_BYTES:
        raise ValueError("body is invalid")
    return body


def _validated_head_sha(head_sha: str) -> str:
    if not isinstance(head_sha, str) or _HEAD_SHA.fullmatch(head_sha) is None:
        raise ValueError("head SHA is invalid")
    return head_sha


class GitHubClient:
    def __init__(
        self,
        *,
        gh_config_dir: Path = DEFAULT_GH_CONFIG_DIR,
        runner: CommandRunner | None = None,
    ) -> None:
        self._gh_config_dir = Path(gh_config_dir).expanduser().resolve()
        self._runner = runner or (
            lambda argv: run_command(argv, gh_config_dir=self._gh_config_dir)
        )
        self._authenticated = False

    def list_all_open_pull_requests(self) -> list[PullRequest]:
        result = self._run(
            (
                "gh",
                "api",
                "--paginate",
                f"repos/{REPOSITORY}/pulls?state=open&per_page=100",
            )
        )
        try:
            numbers: list[int] = []
            seen: set[int] = set()
            for page in self._load_json_pages(result.stdout):
                if not isinstance(page, list):
                    raise TypeError
                for item in page:
                    if not isinstance(item, Mapping):
                        raise TypeError
                    number = _positive_id(item["number"])
                    if number in seen:
                        continue
                    seen.add(number)
                    numbers.append(number)
            pull_requests = [self.get_pull_request(number) for number in numbers]
            if any(item.lifecycle_state != "OPEN" for item in pull_requests):
                raise ValueError
        except (GitHubError, KeyError, TypeError, ValueError):
            raise GitHubError("invalid GitHub response") from None
        return pull_requests

    def create_draft_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
    ) -> int:
        branch = _validated_catalog_curation_branch(branch)
        title = _validated_title(title)
        body = _validated_body(body)
        with _temporary_body(body) as body_path:
            result = self._run(
                (
                    "gh",
                    "api",
                    "--method",
                    "POST",
                    f"repos/{REPOSITORY}/pulls",
                    "-f",
                    f"title={title}",
                    "-f",
                    f"head={branch}",
                    "-f",
                    "base=main",
                    "-F",
                    "draft=true",
                    "-F",
                    f"body=@{body_path}",
                )
            )
        try:
            payload = self._load_json(result.stdout)
            if not isinstance(payload, Mapping):
                raise TypeError
            return _positive_id(payload["number"])
        except (KeyError, TypeError, ValueError):
            raise GitHubError("invalid GitHub response") from None

    def find_pull_requests_by_head(
        self,
        branch: str,
        head_sha: str,
    ) -> list[PullRequest]:
        return self._find_pull_requests_by_head(branch, head_sha)

    def _find_pull_requests_by_head(
        self,
        branch: str,
        head_sha: str,
    ) -> list[PullRequest]:
        branch = _validated_catalog_curation_branch(branch)
        head_sha = _validated_head_sha(head_sha)
        encoded_head = quote(f"{TRUSTED_MAINTAINER_LOGIN}:{branch}", safe="")
        result = self._run(
            (
                "gh",
                "api",
                "--paginate",
                (
                    f"repos/{REPOSITORY}/pulls?state=all&base=main&"
                    f"head={encoded_head}&per_page=100"
                ),
            )
        )
        try:
            numbers: list[int] = []
            seen: set[int] = set()
            for page in self._load_json_pages(result.stdout):
                if not isinstance(page, list):
                    raise TypeError
                for item in page:
                    if not isinstance(item, Mapping):
                        raise TypeError
                    number = _positive_id(item["number"])
                    if number in seen:
                        continue
                    seen.add(number)
                    numbers.append(number)

            pull_requests = [self.get_pull_request(number) for number in numbers]
            if any(
                item.lifecycle_state not in {"OPEN", "CLOSED", "MERGED"}
                or item.base_ref_name != "main"
                or item.head_ref_name != branch
                or item.head_repository_owner != TRUSTED_MAINTAINER_LOGIN
                or item.is_cross_repository
                or item.head_sha != head_sha
                for item in pull_requests
            ):
                raise ValueError
        except (GitHubError, KeyError, TypeError, ValueError):
            raise GitHubError("invalid GitHub response") from None
        return pull_requests

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
    ) -> bool:
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

        mutated = False
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
            mutated = True
        return mutated

    def list_closed_proposal_pull_requests(self) -> list[PullRequest]:
        return self._list_closed_pull_requests_by_label("maintainer%3Aproposal")

    def list_closed_discovery_pull_requests(self) -> list[PullRequest]:
        return self._list_closed_pull_requests_by_label("lane%3Acatalog-discovery")

    def _list_closed_pull_requests_by_label(
        self,
        encoded_label: str,
    ) -> list[PullRequest]:
        result = self._run(
            (
                "gh",
                "api",
                "--paginate",
                (
                    f"repos/{REPOSITORY}/issues"
                    f"?state=closed&labels={encoded_label}&per_page=100"
                ),
            )
        )
        try:
            numbers: list[int] = []
            seen: set[int] = set()
            for page in self._load_json_pages(result.stdout):
                if not isinstance(page, list):
                    raise TypeError
                for item in page:
                    if not isinstance(item, Mapping):
                        raise TypeError
                    if "pull_request" not in item:
                        continue
                    if not isinstance(item["pull_request"], Mapping):
                        raise TypeError
                    number = _positive_id(item["number"])
                    if number in seen:
                        continue
                    seen.add(number)
                    numbers.append(number)
            pull_requests = [self.get_pull_request(number) for number in numbers]
            if any(
                item.lifecycle_state not in {"CLOSED", "MERGED"}
                for item in pull_requests
            ):
                raise ValueError
        except (GitHubError, KeyError, TypeError, ValueError):
            raise GitHubError("invalid GitHub response") from None
        return pull_requests

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
                    user = item["user"]
                    comments.append(
                        GitHubComment(
                            comment_id=_positive_id(item["id"]),
                            body=_object_string(item, "body"),
                            author_login=_object_string(user, "login"),
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
        argv = (
            "gh",
            "pr",
            "edit",
            str(number),
            "--repo",
            REPOSITORY,
        )
        for label in sorted(remove):
            self._run((*argv, "--remove-label", label))
        for label in sorted(add):
            self._run((*argv, "--add-label", label))

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
        self._ensure_trusted_authentication()
        return self._run_raw(argv)

    def _run_raw(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self._runner(argv)
        except (OSError, subprocess.SubprocessError):
            raise GitHubError("GitHub command failed") from None

    def _ensure_trusted_authentication(self) -> None:
        if self._authenticated:
            return
        result = self._run_raw(
            (
                "gh",
                "auth",
                "status",
                "--active",
                "--hostname",
                "github.com",
                "--json",
                "hosts",
            )
        )
        try:
            payload = self._load_json(result.stdout)
            if not isinstance(payload, Mapping):
                raise TypeError
            hosts = payload["hosts"]
            if not isinstance(hosts, Mapping):
                raise TypeError
            accounts = hosts["github.com"]
            if not isinstance(accounts, list):
                raise TypeError
            active = [
                account
                for account in accounts
                if isinstance(account, Mapping) and account.get("active") is True
            ]
            if len(active) != 1:
                raise ValueError
            account = active[0]
            if (
                account.get("login") != TRUSTED_MAINTAINER_LOGIN
                or account.get("state") != "success"
            ):
                raise ValueError
        except (GitHubError, KeyError, TypeError, ValueError):
            raise GitHubError("GitHub authentication identity is not trusted") from None
        self._authenticated = True

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

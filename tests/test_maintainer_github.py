from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import pytest
from pydantic import ValidationError

from ops.maintainer import BODY_END, BODY_START, SUMMARY_MARKER
from ops.maintainer import github as maintainer_github
from ops.maintainer.github import (
    PR_FIELDS,
    GitHubClient,
    GitHubComment,
    GitHubError,
    check_state,
    parse_pull_request,
    run_command,
)
from ops.maintainer.models import MachineState, MaintainerLane, MaintainerState
from ops.maintainer.publication import (
    MaintainerSummary,
    label_plan,
    parse_machine_state,
    publish_state,
    render_summary,
    replace_managed_body,
)

pytestmark = pytest.mark.db_free


def _auth_status(login: str = "lampssy", state: str = "success") -> str:
    return json.dumps(
        {
            "hosts": {
                "github.com": [
                    {
                        "active": True,
                        "login": login,
                        "state": state,
                    }
                ]
            }
        }
    )


class RecordingRunner:
    def __init__(
        self,
        outputs: Sequence[str] = (),
        *,
        failure: Exception | None = None,
        auth_output: str | None = None,
    ) -> None:
        self.outputs = list(outputs)
        self.failure = failure
        self.calls: list[list[str]] = []
        self.auth_calls: list[list[str]] = []
        self.auth_output = auth_output or _auth_status()
        self.body_paths: list[Path] = []
        self.body_contents: list[str] = []

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        command = list(argv)
        if command[:3] == ["gh", "auth", "status"]:
            self.auth_calls.append(command)
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=self.auth_output,
                stderr="",
            )
        self.calls.append(command)
        for index, value in enumerate(command[:-1]):
            if value == "--body-file":
                self._capture_body(Path(command[index + 1]))
        for value in command:
            if value.startswith("body=@"):
                self._capture_body(Path(value.removeprefix("body=@")))
        if self.failure is not None:
            raise self.failure
        stdout = self.outputs.pop(0) if self.outputs else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    def _capture_body(self, path: Path) -> None:
        self.body_paths.append(path)
        self.body_contents.append(path.read_text(encoding="utf-8"))
        assert path.stat().st_mode & 0o777 == 0o600


class StatefulLabelRunner:
    def __init__(self, labels: set[str], *, fail_add: str) -> None:
        self.labels = set(labels)
        self.fail_add = fail_add
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        command = list(argv)
        if command[:3] == ["gh", "auth", "status"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=_auth_status(),
                stderr="",
            )
        self.calls.append(command)
        mutations = [
            (flag, command[index + 1])
            for index, flag in enumerate(command[:-1])
            if flag in {"--add-label", "--remove-label"}
        ]
        assert len(mutations) == 1
        operation, label = mutations[0]
        if operation == "--add-label" and label == self.fail_add:
            raise subprocess.CalledProcessError(1, command)
        if operation == "--add-label":
            self.labels.add(label)
        else:
            self.labels.discard(label)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _raw_pull_request(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Tignes",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "baseRefName": "main",
        "headRefName": "codex/catalog-curation-tignes",
        "headRepositoryOwner": {"login": "lampssy"},
        "isCrossRepository": False,
        "state": "OPEN",
        "createdAt": "2026-07-08T10:00:00Z",
        "labels": [
            {"name": "lane:catalog-curation"},
            {"name": "maintainer:waiting-ci"},
        ],
        "headRefOid": "a" * 40,
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
        "files": [{"path": "app/data/catalog_v2.json"}],
        "body": "Owner text",
    }
    values.update(overrides)
    return values


def _machine_state(**overrides: object) -> MachineState:
    values: dict[str, object] = {
        "head_sha": "a" * 40,
        "lineage_id": "catalog-curation-42",
        "last_publication": "none",
    }
    values.update(overrides)
    return MachineState.model_validate(values)


def _constructed_machine_state(**overrides: object) -> MachineState:
    values = _machine_state().model_dump()
    values.update(overrides)
    return MachineState.model_construct(**values)


def _summary(**overrides: object) -> MaintainerSummary:
    values: dict[str, object] = {
        "state": MaintainerState.WAITING_CI,
        "head_sha": "a" * 40,
        "result": "Catalog validation completed.",
        "ci_status": "Required checks are still running.",
        "owner_action": "Wait for CI to complete.",
        "caveats": ("One source needs a future freshness review.",),
        "machine_state": _machine_state(),
    }
    values.update(overrides)
    return MaintainerSummary.model_validate(values)


class FakePublishingClient:
    def __init__(self, comments: Sequence[GitHubComment] = ()) -> None:
        self.comments = list(comments)
        self.body_updates: list[tuple[int, str]] = []
        self.created_comments: list[tuple[int, str, int]] = []
        self.updated_comments: list[tuple[int, str]] = []
        self.label_updates: list[tuple[int, frozenset[str], frozenset[str]]] = []
        self.operations: list[str] = []
        self.fail_operation: str | None = None

    def list_issue_comments(self, number: int) -> list[GitHubComment]:
        self.operations.append("list-comments")
        return list(self.comments)

    def update_pull_request_body(self, number: int, body: str) -> None:
        self.operations.append("body")
        self.body_updates.append((number, body))
        self._maybe_fail("body")

    def create_comment(self, number: int, body: str) -> int:
        self.operations.append("create-comment")
        comment_id = 100 + len(self.created_comments)
        self.created_comments.append((number, body, comment_id))
        self.comments.append(
            GitHubComment(
                comment_id=comment_id,
                body=body,
                author_login="lampssy",
            )
        )
        self._maybe_fail("comment")
        return comment_id

    def update_comment(self, comment_id: int, body: str) -> None:
        self.operations.append("update-comment")
        self.updated_comments.append((comment_id, body))
        self.comments = [
            GitHubComment(
                comment_id=item.comment_id,
                body=body,
                author_login=item.author_login,
            )
            if item.comment_id == comment_id
            else item
            for item in self.comments
        ]
        self._maybe_fail("comment")

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None:
        self.operations.append("labels")
        self.label_updates.append((number, frozenset(add), frozenset(remove)))
        self._maybe_fail("labels")

    def _maybe_fail(self, operation: str) -> None:
        if self.fail_operation == operation:
            self.fail_operation = None
            raise GitHubError(f"failed {operation}")


def test_default_runner_is_bounded_noninteractive_and_project_scoped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["argv"] = argv
        recorded.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("GH_TOKEN", "ambient-token-must-not-win")
    config_dir = tmp_path / "gh-config"

    run_command(("gh", "--version"), gh_config_dir=config_dir)

    assert recorded["argv"] == ["gh", "--version"]
    assert recorded["shell"] is False
    assert recorded["check"] is True
    assert recorded["text"] is True
    assert recorded["capture_output"] is True
    assert recorded["timeout"] == maintainer_github.GITHUB_COMMAND_TIMEOUT_SECONDS
    assert recorded["stdin"] is subprocess.DEVNULL
    environment = recorded["env"]
    assert isinstance(environment, dict)
    assert environment["GH_PROMPT_DISABLED"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GCM_INTERACTIVE"] == "Never"
    assert environment["GH_CONFIG_DIR"] == str(config_dir)
    assert "GH_TOKEN" not in environment


def test_default_runner_sanitizes_timeout_without_command_or_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "ghp_timeout_secret"

    def time_out(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        raise subprocess.TimeoutExpired(
            argv,
            120,
            output=f"response included {secret}",
            stderr=f"stderr included {secret}",
        )

    monkeypatch.setattr(subprocess, "run", time_out)

    with pytest.raises(GitHubError, match="^GitHub command failed$") as error:
        run_command(
            ("gh", "api", secret),
            gh_config_dir=Path("/tmp/project-scoped-gh"),
        )

    assert secret not in str(error.value)


def test_trusted_maintainer_identity_is_explicit() -> None:
    assert maintainer_github.TRUSTED_MAINTAINER_LOGIN == "lampssy"


def test_client_fails_before_operation_for_wrong_scoped_login(tmp_path: Path) -> None:
    runner = RecordingRunner(auth_output=_auth_status("not-lampssy"))
    client = GitHubClient(gh_config_dir=tmp_path / "gh", runner=runner)

    with pytest.raises(GitHubError, match="authentication identity"):
        client.list_open_pull_requests()

    assert runner.auth_calls == [
        [
            "gh",
            "auth",
            "status",
            "--active",
            "--hostname",
            "github.com",
            "--json",
            "hosts",
        ]
    ]
    assert runner.calls == []


@pytest.mark.parametrize(
    "operation",
    [
        lambda client, body: client.update_pull_request_body(42, body),
        lambda client, body: client.create_comment(42, body),
        lambda client, body: client.update_comment(101, body),
    ],
)
def test_body_text_uses_cleaned_temporary_file(
    operation: Any,
) -> None:
    body = "Untrusted $(touch /tmp/snowcast-pwned) body"
    runner = RecordingRunner(outputs=['{"id":101}'])
    client = GitHubClient(runner=runner)

    operation(client, body)

    assert runner.body_contents == [body]
    assert all(body not in argument for call in runner.calls for argument in call)
    assert all(not path.exists() for path in runner.body_paths)


def test_body_temporary_file_is_cleaned_when_command_fails() -> None:
    body = "Untrusted $(touch /tmp/snowcast-pwned) body"
    runner = RecordingRunner(failure=subprocess.CalledProcessError(1, ["gh"]))
    client = GitHubClient(runner=runner)

    with pytest.raises(RuntimeError, match="GitHub command failed"):
        client.update_pull_request_body(42, body)

    assert runner.body_contents == [body]
    assert all(body not in argument for call in runner.calls for argument in call)
    assert all(not path.exists() for path in runner.body_paths)


def test_body_temporary_file_is_cleaned_when_chmod_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_paths: list[Path] = []

    def fail_chmod(path: str | Path, mode: int) -> None:
        del mode
        created_paths.append(Path(path))
        raise PermissionError("chmod failed")

    monkeypatch.setattr(maintainer_github.os, "chmod", fail_chmod)

    with pytest.raises(PermissionError, match="chmod failed"):
        GitHubClient(runner=RecordingRunner()).update_pull_request_body(42, "body")

    try:
        assert created_paths and all(not path.exists() for path in created_paths)
    finally:
        for path in created_paths:
            path.unlink(missing_ok=True)


def test_body_temporary_file_is_cleaned_when_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = maintainer_github.NamedTemporaryFile
    created_paths: list[Path] = []

    class FailingTemporaryFile:
        def __init__(self, **kwargs: object) -> None:
            self._file = original(**kwargs)
            self.name = self._file.name
            created_paths.append(Path(self.name))

        def __enter__(self) -> FailingTemporaryFile:
            self._file.__enter__()
            return self

        def __exit__(self, *args: object) -> object:
            return self._file.__exit__(*args)

        def write(self, body: str) -> None:
            del body
            raise OSError("write failed")

    monkeypatch.setattr(
        maintainer_github,
        "NamedTemporaryFile",
        FailingTemporaryFile,
    )

    with pytest.raises(OSError, match="write failed"):
        GitHubClient(runner=RecordingRunner()).update_pull_request_body(42, "body")

    try:
        assert created_paths and all(not path.exists() for path in created_paths)
    finally:
        for path in created_paths:
            path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("rollup", "expected"),
    [
        (None, "pending"),
        ([], "pending"),
        ([{"status": "IN_PROGRESS", "conclusion": None}], "pending"),
        ([{"status": "COMPLETED", "conclusion": None}], "pending"),
        ([{"status": "COMPLETED", "conclusion": "FAILURE"}], "failure"),
        ([{"status": "COMPLETED", "conclusion": "CANCELLED"}], "failure"),
        ([{"status": "COMPLETED", "conclusion": "TIMED_OUT"}], "failure"),
        (
            [{"status": "COMPLETED", "conclusion": "ACTION_REQUIRED"}],
            "failure",
        ),
        ([{"status": "COMPLETED", "conclusion": "SUCCESS"}], "success"),
        ([{"state": "SUCCESS"}], "success"),
        ([{"state": "FAILURE"}], "failure"),
        ([{"state": "PENDING"}], "pending"),
        ([{"status": "COMPLETED", "conclusion": "ERROR"}], "failure"),
        (
            [{"status": "COMPLETED", "conclusion": "STARTUP_FAILURE"}],
            "failure",
        ),
        ([{"status": "COMPLETED", "conclusion": "STALE"}], "failure"),
        ([{"status": "COMPLETED", "conclusion": "NEUTRAL"}], "failure"),
        ([{"status": "COMPLETED", "conclusion": "SKIPPED"}], "failure"),
        ([{"status": "COMPLETED", "conclusion": "BOGUS"}], "failure"),
        ([{"status": "IN_PROGRESS", "conclusion": "BOGUS"}], "pending"),
        ([{"state": "ERROR"}], "failure"),
        ([{"state": "STARTUP_FAILURE"}], "failure"),
        ([{"state": "STALE"}], "failure"),
        (
            [
                {"status": "IN_PROGRESS", "conclusion": None},
                {"status": "COMPLETED", "conclusion": "FAILURE"},
            ],
            "failure",
        ),
    ],
)
def test_check_state_classifies_rollups(
    rollup: list[dict[str, object]] | None,
    expected: str,
) -> None:
    assert check_state(rollup) == expected


def test_parse_pull_request_maps_gh_json_to_strict_model() -> None:
    pull_request = parse_pull_request(_raw_pull_request())

    assert pull_request.number == 42
    assert pull_request.lifecycle_state == "OPEN"
    assert pull_request.head_repository_owner == "lampssy"
    assert pull_request.created_at == datetime(2026, 7, 8, 10, tzinfo=UTC)
    assert pull_request.labels == frozenset(
        {"lane:catalog-curation", "maintainer:waiting-ci"}
    )
    assert pull_request.head_sha == "a" * 40
    assert pull_request.check_state == "success"
    assert pull_request.changed_paths == frozenset({"app/data/catalog_v2.json"})
    assert pull_request.body == "Owner text"


@pytest.mark.parametrize("state", ["OPEN", "CLOSED", "MERGED"])
def test_parse_pull_request_preserves_github_lifecycle_state(state: str) -> None:
    pull_request = parse_pull_request(_raw_pull_request(state=state))

    assert pull_request.lifecycle_state == state


def test_parse_pull_request_requires_lifecycle_state_from_github() -> None:
    payload = _raw_pull_request()
    del payload["state"]

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        parse_pull_request(payload)


def test_list_and_get_pull_requests_use_repository_and_declared_fields() -> None:
    payload = json.dumps([_raw_pull_request()])
    runner = RecordingRunner(outputs=[payload, json.dumps(_raw_pull_request())])
    client = GitHubClient(runner=runner)

    listed = client.list_open_pull_requests()
    fetched = client.get_pull_request(42)

    assert listed == [fetched]
    assert runner.calls[0] == [
        "gh",
        "pr",
        "list",
        "--repo",
        "lampssy/ai-sports-travel-planner",
        "--state",
        "open",
        "--limit",
        "100",
        "--json",
        ",".join(PR_FIELDS),
    ]
    assert runner.calls[1] == [
        "gh",
        "pr",
        "view",
        "42",
        "--repo",
        "lampssy/ai-sports-travel-planner",
        "--json",
        ",".join(PR_FIELDS),
    ]


@pytest.mark.parametrize(
    "operation",
    [
        lambda client: client.get_pull_request(0),
        lambda client: client.list_issue_comments(-1),
        lambda client: client.update_pull_request_body(True, "body"),
        lambda client: client.update_labels(0, {"a"}, set()),
        lambda client: client.create_comment(-1, "body"),
        lambda client: client.update_comment(0, "body"),
    ],
)
def test_numeric_ids_must_be_positive_integers(operation: Any) -> None:
    runner = RecordingRunner()

    with pytest.raises(ValueError, match="positive integer"):
        operation(GitHubClient(runner=runner))

    assert runner.calls == []


@pytest.mark.parametrize(
    "output",
    ["not json", "{}", '[{"number":"42"}]'],
)
def test_invalid_pull_request_json_fails_safely(output: str) -> None:
    client = GitHubClient(runner=RecordingRunner(outputs=[output]))

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        client.list_open_pull_requests()


@pytest.mark.parametrize(
    "invalid_field",
    [
        {"body": 17},
        {"statusCheckRollup": [17]},
    ],
)
def test_invalid_nested_pull_request_json_fails_safely(
    invalid_field: dict[str, object],
) -> None:
    client = GitHubClient(
        runner=RecordingRunner(
            outputs=[json.dumps([_raw_pull_request(**invalid_field)])]
        )
    )

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        client.list_open_pull_requests()


def test_invalid_check_conclusion_type_fails_safely() -> None:
    invalid = _raw_pull_request(
        statusCheckRollup=[{"status": "COMPLETED", "conclusion": 17}]
    )
    client = GitHubClient(runner=RecordingRunner(outputs=[json.dumps([invalid])]))

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        client.list_open_pull_requests()


def test_issue_comment_pagination_parses_each_json_page() -> None:
    pages = (
        '[{"id":101,"body":"first","user":{"login":"lampssy"}}]\n'
        '[{"id":102,"body":"second","user":{"login":"other"}},'
        '{"id":103,"body":"third","user":{"login":"lampssy"}}]'
    )
    runner = RecordingRunner(outputs=[pages])

    comments = GitHubClient(runner=runner).list_issue_comments(42)

    assert comments == [
        GitHubComment(comment_id=101, body="first", author_login="lampssy"),
        GitHubComment(comment_id=102, body="second", author_login="other"),
        GitHubComment(comment_id=103, body="third", author_login="lampssy"),
    ]
    assert runner.calls == [
        [
            "gh",
            "api",
            "--paginate",
            "repos/lampssy/ai-sports-travel-planner/issues/42/comments",
        ]
    ]


def test_closed_proposal_pull_requests_are_strict_typed_records() -> None:
    closed = _raw_pull_request(
        number=7,
        url="https://github.com/lampssy/ai-sports-travel-planner/pull/7",
        state="CLOSED",
        labels=[
            {"name": "lane:catalog-discovery"},
            {"name": "maintainer:proposal"},
        ],
    )
    merged = _raw_pull_request(
        number=9,
        url="https://github.com/lampssy/ai-sports-travel-planner/pull/9",
        state="MERGED",
        labels=[
            {"name": "lane:catalog-discovery"},
            {"name": "maintainer:proposal"},
        ],
    )
    history = [
        {"number": 7, "pull_request": {}},
        {"number": 9, "pull_request": {}},
    ]
    runner = RecordingRunner(
        outputs=[json.dumps(history), json.dumps(closed), json.dumps(merged)]
    )

    pull_requests = GitHubClient(runner=runner).list_closed_proposal_pull_requests()

    assert [item.number for item in pull_requests] == [7, 9]
    assert [item.lifecycle_state for item in pull_requests] == ["CLOSED", "MERGED"]
    assert runner.calls[0] == [
        "gh",
        "api",
        "--paginate",
        (
            "repos/lampssy/ai-sports-travel-planner/issues"
            "?state=closed&labels=maintainer%3Aproposal&per_page=100"
        ),
    ]
    assert runner.calls[1][0:4] == ["gh", "pr", "view", "7"]
    assert runner.calls[2][0:4] == ["gh", "pr", "view", "9"]


def test_closed_proposal_history_uses_all_api_pages_and_deduplicates_prs() -> None:
    numbers = list(range(1, 202))
    first_page = [{"number": number, "pull_request": {}} for number in numbers[:100]]
    first_page.append({"number": 999})
    second_page = [{"number": number, "pull_request": {}} for number in numbers[100:]]
    second_page.append({"number": 7, "pull_request": {}})
    pages = "".join(
        (
            json.dumps(first_page),
            json.dumps(second_page),
        )
    )
    runner = RecordingRunner(
        outputs=[
            pages,
            *(
                json.dumps(
                    _raw_pull_request(
                        number=number,
                        url=(
                            "https://github.com/lampssy/"
                            f"ai-sports-travel-planner/pull/{number}"
                        ),
                        state="CLOSED",
                    )
                )
                for number in numbers
            ),
        ]
    )

    pull_requests = GitHubClient(runner=runner).list_closed_proposal_pull_requests()

    assert [item.number for item in pull_requests] == numbers
    assert runner.calls[0] == [
        "gh",
        "api",
        "--paginate",
        (
            "repos/lampssy/ai-sports-travel-planner/issues"
            "?state=closed&labels=maintainer%3Aproposal&per_page=100"
        ),
    ]
    assert all("--limit" not in call for call in runner.calls)
    assert len(runner.calls) == 202
    assert runner.calls[1][0:4] == ["gh", "pr", "view", "1"]
    assert runner.calls[-1][0:4] == ["gh", "pr", "view", "201"]


def test_closed_proposal_query_rejects_unexpected_open_lifecycle() -> None:
    runner = RecordingRunner(
        outputs=[
            json.dumps([{"number": 42, "pull_request": {}}]),
            json.dumps(_raw_pull_request(state="OPEN")),
        ]
    )

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        GitHubClient(runner=runner).list_closed_proposal_pull_requests()


def test_closed_discovery_history_uses_all_pages_and_deduplicates_prs() -> None:
    pages = (
        '[{"number":7,"pull_request":{}},{"number":9,"pull_request":{}}]\n'
        '[{"number":7,"pull_request":{}},{"number":11}]'
    )
    closed = _raw_pull_request(
        number=7,
        url="https://github.com/lampssy/ai-sports-travel-planner/pull/7",
        state="CLOSED",
    )
    merged = _raw_pull_request(
        number=9,
        url="https://github.com/lampssy/ai-sports-travel-planner/pull/9",
        state="MERGED",
    )
    runner = RecordingRunner(outputs=[pages, json.dumps(closed), json.dumps(merged)])

    pull_requests = GitHubClient(runner=runner).list_closed_discovery_pull_requests()

    assert [pull_request.number for pull_request in pull_requests] == [7, 9]
    assert runner.calls[0] == [
        "gh",
        "api",
        "--paginate",
        (
            "repos/lampssy/ai-sports-travel-planner/issues"
            "?state=closed&labels=lane%3Acatalog-discovery&per_page=100"
        ),
    ]
    assert [call[3] for call in runner.calls[1:]] == ["7", "9"]


@pytest.mark.parametrize(
    "outputs",
    [
        ("not json",),
        (
            json.dumps([{"number": 42, "pull_request": {}}]),
            json.dumps(_raw_pull_request(state="OPEN")),
        ),
    ],
)
def test_closed_discovery_history_fails_safely_on_invalid_responses(
    outputs: tuple[str, ...],
) -> None:
    client = GitHubClient(runner=RecordingRunner(outputs=outputs))

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        client.list_closed_discovery_pull_requests()


@pytest.mark.parametrize("output", ['[{"id":"bad"}]', "", "not json"])
def test_invalid_comment_page_fails_safely(output: str) -> None:
    client = GitHubClient(runner=RecordingRunner(outputs=[output]))

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        client.list_issue_comments(42)


@pytest.mark.parametrize("comment_id", [0, -1, "101", True, None])
def test_create_comment_rejects_invalid_response_id(comment_id: object) -> None:
    client = GitHubClient(
        runner=RecordingRunner(outputs=[json.dumps({"id": comment_id})])
    )

    with pytest.raises(GitHubError, match="invalid GitHub response"):
        client.create_comment(42, "body")


def test_ensure_labels_creates_missing_and_edits_only_drifted_definitions() -> None:
    existing = json.dumps(
        [
            {
                "name": "lane:catalog-curation",
                "description": "Catalog curation readiness workflow",
                "color": "1d76db",
            },
            {
                "name": "maintainer:ready",
                "description": "old description",
                "color": "0E8A16",
            },
            {
                "name": "unrelated",
                "description": "leave me",
                "color": "FFFFFF",
            },
        ]
    )
    runner = RecordingRunner(outputs=[existing, "", ""])
    definitions = {
        "lane:catalog-curation": (
            "Catalog curation readiness workflow",
            "1D76DB",
        ),
        "maintainer:ready": ("Reviewed head is green", "0E8A16"),
        "maintainer:blocked": ("Automation cannot progress", "B60205"),
    }

    GitHubClient(runner=runner).ensure_labels(definitions)

    assert runner.calls == [
        [
            "gh",
            "label",
            "list",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--limit",
            "100",
            "--json",
            "name,description,color",
        ],
        [
            "gh",
            "label",
            "create",
            "maintainer:blocked",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--description",
            "Automation cannot progress",
            "--color",
            "B60205",
        ],
        [
            "gh",
            "label",
            "edit",
            "maintainer:ready",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--description",
            "Reviewed head is green",
            "--color",
            "0E8A16",
        ],
    ]


def test_ensure_labels_is_noop_when_all_definitions_are_stable() -> None:
    existing = json.dumps(
        [
            {
                "name": "maintainer:ready",
                "description": "Reviewed head is green",
                "color": "0e8a16",
            }
        ]
    )
    runner = RecordingRunner(outputs=[existing])

    GitHubClient(runner=runner).ensure_labels(
        {"maintainer:ready": ("Reviewed head is green", "0E8A16")}
    )

    assert len(runner.calls) == 1


def test_ensure_labels_ignores_unrelated_label_metadata() -> None:
    existing = json.dumps(
        [
            {
                "name": "unrelated",
                "description": None,
                "color": None,
            },
            {
                "name": "maintainer:ready",
                "description": "Reviewed head is green",
                "color": "0E8A16",
            },
        ]
    )
    runner = RecordingRunner(outputs=[existing])

    GitHubClient(runner=runner).ensure_labels(
        {"maintainer:ready": ("Reviewed head is green", "0E8A16")}
    )

    assert len(runner.calls) == 1


def test_update_labels_skips_empty_plan_and_sorts_each_operation() -> None:
    runner = RecordingRunner(outputs=[""])
    client = GitHubClient(runner=runner)

    client.update_labels(42, set(), set())
    client.update_labels(
        42,
        {"maintainer:ready", "lane:catalog-curation"},
        {"maintainer:working", "lane:catalog-discovery"},
    )

    assert runner.calls == [
        [
            "gh",
            "pr",
            "edit",
            "42",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--remove-label",
            "lane:catalog-discovery",
        ],
        [
            "gh",
            "pr",
            "edit",
            "42",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--remove-label",
            "maintainer:working",
        ],
        [
            "gh",
            "pr",
            "edit",
            "42",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--add-label",
            "lane:catalog-curation",
        ],
        [
            "gh",
            "pr",
            "edit",
            "42",
            "--repo",
            "lampssy/ai-sports-travel-planner",
            "--add-label",
            "maintainer:ready",
        ],
    ]


def test_label_transition_partial_failure_converges_from_refreshed_state() -> None:
    runner = StatefulLabelRunner(
        {
            "unrelated",
            MaintainerLane.CATALOG_DISCOVERY.value,
            MaintainerState.WORKING.value,
        },
        fail_add=MaintainerState.READY.value,
    )
    client = GitHubClient(runner=runner)
    add, remove = label_plan(
        runner.labels,
        MaintainerLane.CATALOG_CURATION,
        MaintainerState.READY,
    )

    with pytest.raises(GitHubError, match="GitHub command failed"):
        client.update_labels(42, add, remove)

    lanes = runner.labels & {lane.value for lane in MaintainerLane}
    states = runner.labels & {state.value for state in MaintainerState}
    assert lanes == {MaintainerLane.CATALOG_CURATION.value}
    assert states == set()
    assert "unrelated" in runner.labels

    runner.fail_add = ""
    refreshed_pr = parse_pull_request(
        _raw_pull_request(labels=[{"name": label} for label in sorted(runner.labels)])
    )
    retry_add, retry_remove = label_plan(
        refreshed_pr.labels,
        MaintainerLane.CATALOG_CURATION,
        MaintainerState.READY,
    )
    client.update_labels(42, retry_add, retry_remove)

    assert runner.labels == {
        "unrelated",
        MaintainerLane.CATALOG_CURATION.value,
        MaintainerState.READY.value,
    }


def test_replace_managed_body_adds_block_without_changing_owner_text() -> None:
    current = "Owner prefix\n\nOwner suffix"

    updated = replace_managed_body(current, "Managed report")

    assert updated == (
        f"Owner prefix\n\nOwner suffix\n\n{BODY_START}\nManaged report\n{BODY_END}"
    )


def test_replace_managed_body_replaces_block_and_preserves_prefix_and_suffix() -> None:
    current = f"Owner prefix\n{BODY_START}\nOld\n{BODY_END}\nOwner suffix"

    updated = replace_managed_body(current, "New")

    assert updated == f"Owner prefix\n{BODY_START}\nNew\n{BODY_END}\nOwner suffix"


@pytest.mark.parametrize(
    "current",
    [
        BODY_START,
        BODY_END,
        f"{BODY_END}\n{BODY_START}",
        f"{BODY_START}\n{BODY_START}\n{BODY_END}",
        f"{BODY_START}\n{BODY_END}\n{BODY_END}",
    ],
)
def test_replace_managed_body_rejects_malformed_markers(current: str) -> None:
    with pytest.raises(ValueError, match="managed body markers"):
        replace_managed_body(current, "Managed")


def test_replace_managed_body_rejects_marker_in_managed_content() -> None:
    with pytest.raises(ValueError, match="managed content"):
        replace_managed_body("Owner", f"bad {BODY_START}")


def test_summary_render_round_trips_only_canonical_machine_state() -> None:
    summary = _summary()

    rendered = render_summary(summary)

    assert rendered.count(SUMMARY_MARKER) == 1
    assert rendered.count("<!-- snowcast-maintainer-state:") == 1
    assert "**State:** `maintainer:waiting-ci`" in rendered
    assert f"**Head:** `{'a' * 40}`" in rendered
    assert "**Result:** Catalog validation completed." in rendered
    assert "**CI:** Required checks are still running." in rendered
    assert "**Owner action:** Wait for CI to complete." in rendered
    assert "One source needs a future freshness review." in rendered
    assert parse_machine_state(rendered) == summary.machine_state


def test_summary_without_caveats_renders_stable_none_value() -> None:
    rendered = render_summary(_summary(caveats=()))

    assert "**Caveats:** None." in rendered


def test_machine_state_parser_rejects_missing_duplicate_and_malformed_markers() -> None:
    rendered = render_summary(_summary())
    machine_marker = next(
        line
        for line in rendered.splitlines()
        if line.startswith("<!-- snowcast-maintainer-state:")
    )

    assert parse_machine_state('{"head_sha":"visible prose only"}') is None
    assert parse_machine_state(f"{rendered}\n{machine_marker}") is None
    assert parse_machine_state(rendered.replace(" -->", "-->")) is None
    assert (
        parse_machine_state(rendered.replace('"schema_version":1', '"extra":1')) is None
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("result", f"bad {SUMMARY_MARKER}"),
        ("ci_status", f"bad {BODY_START}"),
        ("owner_action", "bad\x00control"),
        ("caveats", ("bad\ncontrol",)),
    ],
)
def test_summary_rejects_marker_and_control_injection(
    field: str,
    value: object,
) -> None:
    values = _summary().model_dump()
    values[field] = value

    with pytest.raises(ValidationError, match="unsafe"):
        MaintainerSummary.model_validate(values)


def test_summary_rejects_head_mismatch() -> None:
    with pytest.raises(ValidationError, match="must match machine state"):
        _summary(head_sha="b" * 40)


def test_summary_rejects_marker_in_embedded_machine_state() -> None:
    unsafe_state = _machine_state(lineage_id=f"unsafe {SUMMARY_MARKER}")

    with pytest.raises(ValidationError, match="unsafe"):
        _summary(machine_state=unsafe_state)


@pytest.mark.parametrize(
    "overrides",
    [
        {"lineage_id": "unsafe <!-- nested comment"},
        {"lineage_id": "unsafe --> terminated comment"},
        {"lineage_id": "unsafe\ncontrol"},
        {"candidate_key": "candidate<!--nested"},
        {"candidate_key": "candidate-->terminated"},
    ],
)
def test_summary_rejects_html_delimiters_and_controls_in_machine_strings(
    overrides: dict[str, object],
) -> None:
    unsafe_state = _constructed_machine_state(**overrides)

    with pytest.raises(ValidationError, match="unsafe"):
        _summary(machine_state=unsafe_state)


@pytest.mark.parametrize(
    "overrides",
    [
        {"lineage_id": "unsafe <!-- nested comment"},
        {"lineage_id": "unsafe --> terminated comment"},
        {"lineage_id": "unsafe\ncontrol"},
        {"candidate_key": "candidate<!--nested"},
        {"candidate_key": "candidate-->terminated"},
    ],
)
def test_machine_state_parser_rejects_ambiguous_machine_string_data(
    overrides: dict[str, object],
) -> None:
    unsafe_values = _machine_state().model_dump(mode="json")
    unsafe_values.update(overrides)
    payload = json.dumps(
        unsafe_values,
        sort_keys=True,
        separators=(",", ":"),
    )
    marker = f"<!-- snowcast-maintainer-state:{payload} -->"

    assert parse_machine_state(marker) is None


def test_label_plan_changes_only_controlled_lane_and_state_labels() -> None:
    current = {
        "unrelated",
        MaintainerLane.CATALOG_DISCOVERY.value,
        MaintainerState.WORKING.value,
    }

    add, remove = label_plan(
        current,
        MaintainerLane.CATALOG_CURATION,
        MaintainerState.READY,
    )

    assert add == {
        MaintainerLane.CATALOG_CURATION.value,
        MaintainerState.READY.value,
    }
    assert remove == {
        MaintainerLane.CATALOG_DISCOVERY.value,
        MaintainerState.WORKING.value,
    }
    assert "unrelated" not in remove


def test_publish_creates_summary_after_body_then_updates_labels() -> None:
    client = FakePublishingClient()
    pull_request = parse_pull_request(
        _raw_pull_request(
            labels=[
                {"name": MaintainerLane.CATALOG_DISCOVERY.value},
                {"name": MaintainerState.WORKING.value},
                {"name": "unrelated"},
            ],
            body="Owner prefix\nOwner suffix",
        )
    )

    publish_state(
        client,
        pull_request,
        MaintainerLane.CATALOG_CURATION,
        _summary(),
        "Managed report",
    )

    assert client.operations == ["list-comments", "body", "create-comment", "labels"]
    assert len(client.created_comments) == 1
    assert client.updated_comments == []
    assert client.body_updates[0][1].startswith("Owner prefix\nOwner suffix\n\n")
    assert client.body_updates[0][1].endswith(
        f"{BODY_START}\nManaged report\n{BODY_END}"
    )
    assert client.label_updates == [
        (
            42,
            frozenset(
                {
                    MaintainerLane.CATALOG_CURATION.value,
                    MaintainerState.WAITING_CI.value,
                }
            ),
            frozenset(
                {
                    MaintainerLane.CATALOG_DISCOVERY.value,
                    MaintainerState.WORKING.value,
                }
            ),
        )
    ]


def test_publish_retry_updates_existing_summary_and_then_becomes_noop() -> None:
    client = FakePublishingClient()
    pull_request = parse_pull_request(_raw_pull_request(body="Owner text", labels=[]))
    first = _summary()
    publish_state(
        client,
        pull_request,
        MaintainerLane.CATALOG_CURATION,
        first,
        "Managed report",
    )
    published_body = client.body_updates[-1][1]
    published_labels = frozenset(
        {
            MaintainerLane.CATALOG_CURATION.value,
            MaintainerState.WAITING_CI.value,
        }
    )
    refreshed_pr = pull_request.model_copy(
        update={"body": published_body, "labels": published_labels}
    )
    changed = _summary(result="A later deterministic review completed.")

    publish_state(
        client,
        refreshed_pr,
        MaintainerLane.CATALOG_CURATION,
        changed,
        "Managed report",
    )
    publish_state(
        client,
        refreshed_pr,
        MaintainerLane.CATALOG_CURATION,
        changed,
        "Managed report",
    )

    assert len(client.created_comments) == 1
    assert client.updated_comments == [
        (client.created_comments[0][2], render_summary(changed))
    ]
    assert len(client.body_updates) == 1
    assert len(client.label_updates) == 1


def test_publish_fails_closed_before_mutation_for_duplicate_summary_comments() -> None:
    marked = render_summary(_summary())
    client = FakePublishingClient(
        [
            GitHubComment(comment_id=1, body=marked, author_login="lampssy"),
            GitHubComment(comment_id=2, body=marked, author_login="lampssy"),
        ]
    )
    pull_request = parse_pull_request(_raw_pull_request())

    with pytest.raises(ValueError, match="multiple maintainer summary comments"):
        publish_state(
            client,
            pull_request,
            MaintainerLane.CATALOG_CURATION,
            _summary(),
            "Managed report",
        )

    assert client.operations == ["list-comments"]


def test_publish_retry_after_partial_failure_does_not_duplicate_comment() -> None:
    client = FakePublishingClient()
    client.fail_operation = "labels"
    pull_request = parse_pull_request(_raw_pull_request(body="Owner text", labels=[]))
    summary = _summary(machine_state=_machine_state(last_publication="comment"))

    with pytest.raises(GitHubError, match="failed labels"):
        publish_state(
            client,
            pull_request,
            MaintainerLane.CATALOG_CURATION,
            summary,
            "Managed report",
        )

    refreshed_pr = pull_request.model_copy(update={"body": client.body_updates[-1][1]})
    publish_state(
        client,
        refreshed_pr,
        MaintainerLane.CATALOG_CURATION,
        summary,
        "Managed report",
    )

    assert len(client.created_comments) == 1
    assert client.updated_comments == []
    assert len(client.label_updates) == 2


def test_publish_ignores_forged_marker_and_creates_trusted_comment() -> None:
    forged = GitHubComment(
        comment_id=9,
        body=render_summary(_summary()),
        author_login="attacker",
    )
    client = FakePublishingClient([forged])
    pull_request = parse_pull_request(_raw_pull_request(body="Owner text", labels=[]))

    publish_state(
        client,
        pull_request,
        MaintainerLane.CATALOG_CURATION,
        _summary(),
        "Managed report",
    )

    assert len(client.created_comments) == 1
    assert client.created_comments[0][0] == 42
    assert client.comments[0] == forged
    assert client.comments[1].author_login == "lampssy"


def test_publish_updates_only_legitimate_comment_when_forged_marker_exists() -> None:
    previous = render_summary(_summary(result="Previous result."))
    forged = GitHubComment(
        comment_id=9,
        body=previous,
        author_login="attacker",
    )
    legitimate = GitHubComment(
        comment_id=10,
        body=previous,
        author_login="lampssy",
    )
    client = FakePublishingClient([forged, legitimate])
    pull_request = parse_pull_request(_raw_pull_request(body="Owner text", labels=[]))

    publish_state(
        client,
        pull_request,
        MaintainerLane.CATALOG_CURATION,
        _summary(),
        "Managed report",
    )

    assert client.created_comments == []
    assert [comment_id for comment_id, _ in client.updated_comments] == [10]
    assert client.comments[0] == forged


def test_publish_rejects_head_mismatch_before_any_client_call() -> None:
    client = FakePublishingClient()
    pull_request = parse_pull_request(_raw_pull_request(headRefOid="b" * 40))

    with pytest.raises(ValueError, match="pull request head"):
        publish_state(
            client,
            pull_request,
            MaintainerLane.CATALOG_CURATION,
            _summary(),
            "Managed report",
        )

    assert client.operations == []

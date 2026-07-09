from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from ops.maintainer.capabilities import (
    HANDLERS,
    CLIInputError,
    Dependencies,
    OutcomeTracker,
    Worker,
    dispatch,
    handle_lock,
    safe_error,
)
from ops.maintainer.errors import error_payload
from ops.maintainer.git_ops import GitRepository
from ops.maintainer.github import DEFAULT_GH_CONFIG_DIR, GitHubClient
from ops.maintainer.inspection import catalog_entity_keys
from ops.maintainer.validation import (
    ProposalValidationResult,
    ValidationResult,
    validate_curation,
    validate_proposal,
)

__all__ = ["HANDLERS", "main"]


class _JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CLIInputError("command arguments are invalid")


def _default_state_dir() -> Path:
    return Path.home() / ".local" / "state" / "snowcast-maintainer"


def _run_id(value: str) -> str:
    if len(value) != 32 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise argparse.ArgumentTypeError("run ID is invalid")
    return value


def _sha(value: str) -> str:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise argparse.ArgumentTypeError("commit SHA is invalid")
    return value


def _add_run_id(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", required=True, type=_run_id)


def _parser() -> argparse.ArgumentParser:
    parser = _JSONArgumentParser(prog="snowcast-maintainer")
    parser.add_argument("--state-dir", type=Path, default=_default_state_dir())
    parser.add_argument("--gh-config-dir", type=Path, default=DEFAULT_GH_CONFIG_DIR)
    families = parser.add_subparsers(dest="family", required=True)

    lock = families.add_parser("lock")
    lock_commands = lock.add_subparsers(dest="command", required=True)
    acquire = lock_commands.add_parser("acquire")
    acquire.add_argument("worker", choices=("curation", "discovery"))
    for command in ("heartbeat", "release"):
        operation = lock_commands.add_parser(command)
        operation.add_argument("worker", choices=("curation", "discovery"))
        _add_run_id(operation)

    inspect = families.add_parser("inspect")
    inspect_commands = inspect.add_subparsers(dest="command", required=True)
    inspect_commands.add_parser("curation")
    inspect_commands.add_parser("discovery")

    prepare = families.add_parser("prepare")
    prepare_commands = prepare.add_subparsers(dest="command", required=True)
    prepare_curation = prepare_commands.add_parser("curation")
    prepare_curation.add_argument("--pr", type=int, required=True)
    _add_run_id(prepare_curation)

    validate = families.add_parser("validate")
    validate_commands = validate.add_subparsers(dest="command", required=True)
    validate_curation_parser = validate_commands.add_parser("curation")
    validate_curation_parser.add_argument("--pr", type=int, required=True)
    validate_curation_parser.add_argument("--reviewed-head", type=_sha, required=True)
    validate_curation_parser.add_argument("--report", required=True)
    validate_curation_parser.add_argument("--base-dir", type=Path, required=True)
    _add_run_id(validate_curation_parser)
    validate_proposal_parser = validate_commands.add_parser("proposal")
    validate_proposal_parser.add_argument("--candidate-key", required=True)
    validate_proposal_parser.add_argument(
        "--candidate-origin",
        choices=("backlog", "external"),
        required=True,
    )
    validate_proposal_parser.add_argument("--base", type=_sha, required=True)
    validate_proposal_parser.add_argument("--head", type=_sha, required=True)
    _add_run_id(validate_proposal_parser)

    publish = families.add_parser("publish")
    publish_commands = publish.add_subparsers(dest="command", required=True)
    push = publish_commands.add_parser("push")
    push.add_argument("--pr", type=int, required=True)
    _add_run_id(push)
    manual_check = publish_commands.add_parser("manual-check")
    manual_check.add_argument("--pr", type=int, required=True)
    manual_check.add_argument("--reviewed-head", type=_sha, required=True)
    manual_check.add_argument("--summary-file", required=True)
    manual_check.add_argument("--body-file")
    _add_run_id(manual_check)
    recover = publish_commands.add_parser("recover")
    recover.add_argument("--work-id", required=True)
    _add_run_id(recover)
    proposal = publish_commands.add_parser("proposal")
    proposal.add_argument("--branch", required=True)
    proposal.add_argument("--candidate-key", required=True)
    proposal.add_argument(
        "--candidate-origin",
        choices=("backlog", "external"),
        required=True,
    )
    proposal.add_argument("--head", type=_sha, required=True)
    proposal.add_argument("--title-file", required=True)
    proposal.add_argument("--body-file", required=True)
    proposal.add_argument("--summary-file", required=True)
    _add_run_id(proposal)
    state = publish_commands.add_parser("state")
    state.add_argument("--pr", type=int, required=True)
    state.add_argument("--state", required=True)
    state.add_argument("--reviewed-head", type=_sha, required=True)
    state.add_argument("--summary-file", required=True)
    state.add_argument("--body-file")
    _add_run_id(state)
    ensure_labels = publish_commands.add_parser("ensure-labels")
    ensure_labels.add_argument(
        "--worker",
        choices=("curation", "discovery"),
        required=True,
    )
    _add_run_id(ensure_labels)
    return parser


def _worker_hint(argv: Sequence[str] | None) -> Worker:
    values = tuple(argv or ())
    if "discovery" in values or "proposal" in values:
        return "discovery"
    return "curation"


def _compose_dependencies(
    args: argparse.Namespace,
    tracker: OutcomeTracker,
    *,
    github: object | None,
    repository: object | None,
    base_repository: object | None,
    curation_validator: Callable[..., ValidationResult],
    proposal_validator: Callable[..., ProposalValidationResult],
    catalog_keys_provider: Callable[[], frozenset[str]] | None,
    repository_root: Path | None,
    now: Callable[[], datetime],
) -> Dependencies:
    root = (repository_root or Path.cwd()).resolve()
    needs_repository = (args.family, args.command) in {
        ("prepare", "curation"),
        ("validate", "curation"),
        ("validate", "proposal"),
        ("publish", "push"),
        ("publish", "manual-check"),
        ("publish", "recover"),
        ("publish", "proposal"),
    }
    selected_repository = repository
    if selected_repository is None and needs_repository:
        selected_repository = GitRepository(root)
    return Dependencies(
        github=github or GitHubClient(gh_config_dir=args.gh_config_dir),
        repository=selected_repository or object(),
        base_repository=base_repository,
        curation_validator=curation_validator,
        proposal_validator=proposal_validator,
        catalog_keys_provider=catalog_keys_provider
        or (lambda: catalog_entity_keys(root / "app/data/catalog.json")),
        repository_root=root,
        now=now,
        tracker=tracker,
    )


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def main(
    argv: Sequence[str] | None = None,
    *,
    github: object | None = None,
    repository: object | None = None,
    base_repository: object | None = None,
    curation_validator: Callable[..., ValidationResult] = validate_curation,
    proposal_validator: Callable[..., ProposalValidationResult] = validate_proposal,
    catalog_keys_provider: Callable[[], frozenset[str]] | None = None,
    repository_root: Path | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    tracker = OutcomeTracker(worker=_worker_hint(argv))
    try:
        args = _parser().parse_args(argv)
        if args.family == "lock":
            result = handle_lock(args, tracker, now)
        else:
            dependencies = _compose_dependencies(
                args,
                tracker,
                github=github,
                repository=repository,
                base_repository=base_repository,
                curation_validator=curation_validator,
                proposal_validator=proposal_validator,
                catalog_keys_provider=catalog_keys_provider,
                repository_root=repository_root,
                now=now,
            )
            result = dispatch(args, dependencies)
    except Exception as error:
        safe = safe_error(error, tracker.stage)
        tracker.terminal_reason = safe.reason.value.replace("-", "_")
        payload: dict[str, object] = error_payload(safe)
        payload["outcome"] = tracker.payload()
        _emit(payload)
        return 2
    payload = {"status": "ok", **result, "outcome": tracker.payload()}
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

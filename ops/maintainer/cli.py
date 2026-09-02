from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import NoReturn, Protocol, cast

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
from ops.maintainer.inspection import (
    catalog_entity_keys,
    catalog_entity_keys_from_json,
)
from ops.maintainer.intent import CATALOG_PATH
from ops.maintainer.validation import (
    DeltaValidationResult,
    ProposalValidationResult,
    ValidationResult,
    validate_curation,
    validate_curation_delta,
    validate_proposal,
)

__all__ = ["HANDLERS", "main"]


class _JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CLIInputError("command arguments are invalid")


class _MainCatalogRepository(Protocol):
    def fetch_main(self) -> str: ...

    def show_text(self, revision: str, path: str) -> str: ...


def _fetched_main_catalog_keys(
    repository: _MainCatalogRepository,
) -> frozenset[str]:
    main_head = repository.fetch_main()
    return catalog_entity_keys_from_json(repository.show_text(main_head, CATALOG_PATH))


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
        help_text = (
            "Refresh the lease and active CI-repair budget."
            if command == "heartbeat"
            else "Release the active worker lease."
        )
        operation = lock_commands.add_parser(command, help=help_text)
        operation.add_argument("worker", choices=("curation", "discovery"))
        _add_run_id(operation)

    inspect = families.add_parser("inspect")
    inspect_commands = inspect.add_subparsers(dest="command", required=True)
    inspect_commands.add_parser("curation")
    inspect_commands.add_parser("discovery")

    migrate = families.add_parser("migrate")
    migrate_commands = migrate.add_subparsers(dest="command", required=True)
    migrate_curation_state = migrate_commands.add_parser("curation-state")
    migrate_curation_state.add_argument(
        "--archive-legacy",
        action="store_true",
        required=True,
    )

    publication_input = families.add_parser("publication-input")
    publication_input_commands = publication_input.add_subparsers(
        dest="command",
        required=True,
    )
    publication_input_create = publication_input_commands.add_parser("create")
    publication_input_create.add_argument(
        "--worker",
        choices=("curation", "discovery"),
        required=True,
    )
    publication_input_create.add_argument(
        "--kind",
        choices=("title", "body", "summary"),
        required=True,
    )
    _add_run_id(publication_input_create)

    prepare = families.add_parser("prepare")
    prepare_commands = prepare.add_subparsers(dest="command", required=True)
    prepare_curation = prepare_commands.add_parser("curation")
    prepare_curation.add_argument("--pr", type=int, required=True)
    prepare_curation.add_argument("--continue-conflict", action="store_true")
    _add_run_id(prepare_curation)
    prepare_ci_repair = prepare_commands.add_parser("ci-repair")
    prepare_ci_repair.add_argument("--pr", type=int, required=True)
    _add_run_id(prepare_ci_repair)

    validate = families.add_parser("validate")
    validate_commands = validate.add_subparsers(dest="command", required=True)
    validate_curation_parser = validate_commands.add_parser("curation")
    validate_curation_parser.add_argument("--pr", type=int, required=True)
    validate_curation_parser.add_argument("--generation-id", required=True)
    validate_curation_parser.add_argument("--head", type=_sha, required=True)
    validate_curation_parser.add_argument("--report", required=True)
    validate_curation_parser.add_argument(
        "--base-dir",
        type=Path,
        required=True,
        help=(
            "detached clean checkout at the exact prepare-time base; "
            "must not be the reviewed worktree"
        ),
    )
    _add_run_id(validate_curation_parser)

    validate_boundary_adjudication_parser = validate_commands.add_parser(
        "boundary-adjudication"
    )
    validate_boundary_adjudication_parser.add_argument(
        "--input", type=Path, required=True
    )
    _add_run_id(validate_boundary_adjudication_parser)

    checkpoint = families.add_parser("checkpoint")
    checkpoint_commands = checkpoint.add_subparsers(dest="command", required=True)
    checkpoint_curation = checkpoint_commands.add_parser("curation")
    checkpoint_curation.add_argument("--pr", type=int, required=True)
    checkpoint_curation.add_argument("--generation-id", required=True)
    checkpoint_curation.add_argument("--head", type=_sha, required=True)
    checkpoint_curation.add_argument("--report", required=True)
    checkpoint_curation.add_argument(
        "--stage",
        choices=("delta-validated", "reviewed"),
        required=True,
    )
    checkpoint_curation.add_argument(
        "--base-dir",
        type=Path,
        required=True,
        help=(
            "detached clean checkout at the exact prepare-time base; "
            "must not be the checkpoint worktree"
        ),
    )
    _add_run_id(checkpoint_curation)
    checkpoint_ci_repair = checkpoint_commands.add_parser("ci-repair")
    checkpoint_ci_repair.add_argument("--pr", type=int, required=True)
    checkpoint_ci_repair.add_argument("--head", type=_sha, required=True)
    _add_run_id(checkpoint_ci_repair)

    invalidate = families.add_parser("invalidate")
    invalidate_commands = invalidate.add_subparsers(dest="command", required=True)
    invalidate_ci_continuation = invalidate_commands.add_parser("ci-continuation")
    invalidate_ci_continuation.add_argument("--pr", type=int, required=True)
    _add_run_id(invalidate_ci_continuation)

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
    ci_repair = publish_commands.add_parser("ci-repair")
    ci_repair.add_argument("--pr", type=int, required=True)
    _add_run_id(ci_repair)
    manual_check = publish_commands.add_parser("manual-check")
    manual_check.add_argument("--pr", type=int, required=True)
    manual_check.add_argument("--reviewed-head", type=_sha, required=True)
    manual_check.add_argument("--report", required=True)
    manual_check.add_argument("--summary-file", required=True)
    manual_check.add_argument("--body-file", required=True)
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
    outcome = publish_commands.add_parser("outcome")
    outcome.add_argument("--pr", type=int, required=True)
    outcome.add_argument("--expected-head", type=_sha, required=True)
    outcome.add_argument(
        "--state",
        choices=("maintainer:blocked", "maintainer:owner-decision"),
        required=True,
    )
    outcome.add_argument(
        "--reason",
        choices=(
            "ci-failure",
            "conflict",
            "deadline",
            "non-converging",
            "owner-decision",
            "review-incomplete",
            "validation-failure",
        ),
        required=True,
    )
    outcome.add_argument("--summary-file", required=True)
    _add_run_id(outcome)
    state = publish_commands.add_parser("state")
    state.add_argument("--pr", type=int, required=True)
    state.add_argument("--state", required=True)
    state.add_argument("--reviewed-head", type=_sha, required=True)
    state.add_argument("--summary-file", required=True)
    state.add_argument("--body-file")
    state.add_argument("--adopt-body", action="store_true")
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
    curation_delta_validator: Callable[..., DeltaValidationResult],
    proposal_validator: Callable[..., ProposalValidationResult],
    catalog_keys_provider: Callable[[], frozenset[str]] | None,
    repository_root: Path | None,
    now: Callable[[], datetime],
) -> Dependencies:
    root = (repository_root or Path.cwd()).resolve()
    needs_repository = (args.family, args.command) in {
        ("migrate", "curation-state"),
        ("prepare", "curation"),
        ("prepare", "ci-repair"),
        ("checkpoint", "curation"),
        ("checkpoint", "ci-repair"),
        ("validate", "curation"),
        ("validate", "proposal"),
        ("publish", "push"),
        ("publish", "ci-repair"),
        ("publish", "manual-check"),
        ("publish", "outcome"),
        ("publish", "recover"),
        ("publish", "proposal"),
        ("publish", "state"),
    }
    selected_repository = repository
    if selected_repository is None and needs_repository:
        selected_repository = GitRepository(root)
    selected_catalog_keys_provider = catalog_keys_provider
    if selected_catalog_keys_provider is None:
        if (args.family, args.command) in {
            ("validate", "proposal"),
            ("publish", "proposal"),
        }:
            main_repository = cast(_MainCatalogRepository, selected_repository)
            selected_catalog_keys_provider = partial(
                _fetched_main_catalog_keys,
                main_repository,
            )
        else:
            selected_catalog_keys_provider = partial(
                catalog_entity_keys,
                root / "app/data/catalog.json",
            )
    return Dependencies(
        github=github or GitHubClient(gh_config_dir=args.gh_config_dir),
        repository=selected_repository or object(),
        base_repository=base_repository,
        curation_validator=curation_validator,
        curation_delta_validator=curation_delta_validator,
        proposal_validator=proposal_validator,
        catalog_keys_provider=selected_catalog_keys_provider,
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
    curation_delta_validator: (
        Callable[..., DeltaValidationResult]
    ) = validate_curation_delta,
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
                curation_delta_validator=curation_delta_validator,
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

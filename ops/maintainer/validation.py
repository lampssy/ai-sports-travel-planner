from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
import unicodedata
from collections.abc import Iterable, Sequence
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.data.catalog_curation import (
    CATALOG_BACKLOG_REF_PREFIX,
    CatalogCurationReport,
    catalog_resulting_graph_scope,
    load_catalog_curation_report,
    render_catalog_resulting_graph_markdown,
    validate_catalog_curation_report,
    validate_catalog_resulting_graph,
)
from app.data.catalog_curation_backlog import markdown_heading_anchor
from app.data.catalog_curation_reconciliation import (
    reconcile_catalog_curation_report,
)
from app.data.catalog_loader import load_catalog_from_path
from app.data.catalog_policy import catalog_policy_issues
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import CatalogTrustManifest
from ops.maintainer.curation_state import CurationValidationDiagnostic
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    ErrorStage,
    MaintainerError,
)
from ops.maintainer.git_ops import GitRepository, GuardedSyncResult
from ops.maintainer.inspection import DiscoveryInventory
from ops.maintainer.intent import (
    BACKLOG_PATH,
    CATALOG_PATH,
    CATALOG_SECTIONS,
    CURATION_REPORT_PREFIX,
    TRUST_MANIFEST_PATH,
    IntentSnapshot,
)
from ops.maintainer.models import PullRequest

VALIDATION_COMMAND_TIMEOUT_SECONDS = 600.0
_OUTPUT_OBSERVATION_LIMIT = 4096
_VALIDATION_DIAGNOSTIC_LIMIT = 8_192
_PROCESS_OUTPUT_CAPTURE_LIMIT = _VALIDATION_DIAGNOSTIC_LIMIT * 2
_OUTPUT_TRUNCATION_MARKER = "...[earlier output truncated]...\n"
_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_REPORT_PATH = re.compile(r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_CANDIDATE_KEY = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_PRIVATE_OBJECT_LIMIT = 1_000_000
_DISCOVERY_DOCUMENT_PATH = re.compile(
    r"^docs/catalog-discovery/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
)
_RETIRED_DISCOVERY_REGISTRY_PATH = (
    "docs/catalog-discovery/alpine-coverage-registry.json"
)
_PROCESS_GROUP_GRACE_SECONDS = 0.25
_PROCESS_GROUP_CLEANUP_ERROR = "validation process-group cleanup failed"
_VALIDATION_ENVIRONMENT_KEYS = ("LANG", "LC_ALL", "PATH", "TMPDIR")


class _ValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ValidationCommandObservation(_ValidationModel):
    command_index: int = Field(ge=1, le=3)
    stdout_characters: int = Field(ge=0, le=_OUTPUT_OBSERVATION_LIMIT)
    stderr_characters: int = Field(ge=0, le=_OUTPUT_OBSERVATION_LIMIT)
    output_truncated: bool


class ValidationResult(_ValidationModel):
    validated_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    commands_completed: Literal[3]
    observations: tuple[ValidationCommandObservation, ...]
    resulting_graph_markdown: str | None = Field(
        default=None,
        min_length=1,
        max_length=32768,
    )

    @model_validator(mode="after")
    def validate_observations(self) -> Self:
        if len(self.observations) != self.commands_completed:
            raise ValueError("command observations must cover every command")
        return self


class DeltaValidationResult(_ValidationModel):
    remediation_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    commands_completed: Literal[2]
    observations: tuple[ValidationCommandObservation, ...]

    @model_validator(mode="after")
    def validate_observations(self) -> Self:
        if len(self.observations) != self.commands_completed:
            raise ValueError("command observations must cover every command")
        return self


class ProposalValidationResult(_ValidationModel):
    candidate_key: str = Field(
        min_length=1,
        max_length=128,
        pattern=_CANDIDATE_KEY.pattern,
    )
    candidate_origin: Literal["backlog", "external"]
    validated_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    report_path: str = Field(pattern=_REPORT_PATH.pattern)
    resulting_graph_markdown: str | None = Field(
        default=None,
        min_length=1,
        max_length=32768,
    )


class ValidationCommandRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]: ...


class _SubprocessValidationRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        if os.name != "posix":
            raise OSError("validation subprocess isolation requires POSIX")
        with (
            TemporaryDirectory(prefix="snowcast-maintainer-home-") as directory,
            ExitStack() as stack,
        ):
            private_home = Path(directory)
            os.chmod(private_home, 0o700)
            capture_output = "pytest" in argv
            stdout_target: object = subprocess.DEVNULL
            stderr_target: object = subprocess.DEVNULL
            if capture_output:
                stdout_target = stack.enter_context(TemporaryFile())
                stderr_target = stack.enter_context(TemporaryFile())
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=stdout_target,
                stderr=stderr_target,
                text=False,
                shell=False,
                start_new_session=True,
                env=_validation_environment(private_home),
            )
            process_group = process.pid
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_process_group(process, process_group)
                raise subprocess.TimeoutExpired(list(argv), timeout) from None
            _terminate_process_group(process, process_group)
            stdout = (
                _read_recent_process_output(stdout_target) if capture_output else ""
            )
            stderr = (
                _read_recent_process_output(stderr_target) if capture_output else ""
            )
        return subprocess.CompletedProcess(
            list(argv),
            returncode,
            stdout=stdout,
            stderr=stderr,
        )


def _read_recent_process_output(stream: object) -> str:
    seek = getattr(stream, "seek")
    tell = getattr(stream, "tell")
    read = getattr(stream, "read")
    seek(0, os.SEEK_END)
    size = tell()
    truncated = size > _PROCESS_OUTPUT_CAPTURE_LIMIT
    if truncated:
        seek(size - _PROCESS_OUTPUT_CAPTURE_LIMIT)
    else:
        seek(0)
    payload = read(_PROCESS_OUTPUT_CAPTURE_LIMIT)
    text = payload.decode("utf-8", errors="replace")
    return (_OUTPUT_TRUNCATION_MARKER if truncated else "") + text


def _validation_environment(private_home: Path) -> dict[str, str]:
    environment = {
        key: value
        for key in _VALIDATION_ENVIRONMENT_KEYS
        if (value := os.environ.get(key)) is not None
    }
    environment.setdefault("PATH", os.defpath)
    environment["HOME"] = str(private_home)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONNOUSERSITE"] = "1"
    environment["UV_NO_CONFIG"] = "1"
    return environment


def _terminate_process_group(
    process: subprocess.Popen[bytes],
    process_group: int,
) -> None:
    if process_group <= 1 or process_group == os.getpgrp():
        raise OSError("refusing to signal the parent process group")
    _signal_process_group(process_group, signal.SIGTERM)
    reaped = _bounded_process_wait(process)
    if _wait_for_process_group_exit(process_group, _PROCESS_GROUP_GRACE_SECONDS):
        if reaped or _bounded_process_wait(process):
            return
        raise OSError(_PROCESS_GROUP_CLEANUP_ERROR)
    _signal_process_group(process_group, signal.SIGKILL)
    if not _bounded_process_wait(process):
        _signal_process_group(process_group, signal.SIGKILL)
        if not _bounded_process_wait(process):
            raise OSError(_PROCESS_GROUP_CLEANUP_ERROR)
    if not _wait_for_process_group_exit(
        process_group,
        _PROCESS_GROUP_GRACE_SECONDS,
    ):
        raise OSError(_PROCESS_GROUP_CLEANUP_ERROR)


def _bounded_process_wait(process: subprocess.Popen[bytes]) -> bool:
    try:
        process.wait(timeout=_PROCESS_GROUP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        return False
    return True


def _signal_process_group(process_group: int, requested_signal: int) -> None:
    try:
        os.killpg(process_group, requested_signal)
    except ProcessLookupError:
        return
    except OSError:
        raise OSError(_PROCESS_GROUP_CLEANUP_ERROR) from None


def _wait_for_process_group_exit(process_group: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return True
        except OSError:
            raise OSError(_PROCESS_GROUP_CLEANUP_ERROR) from None
        time.sleep(0.01)
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return True
    except OSError:
        raise OSError(_PROCESS_GROUP_CLEANUP_ERROR) from None
    return False


class _CurationPlan(_ValidationModel):
    report_path: str = Field(pattern=_REPORT_PATH.pattern)
    base_dir: Path
    reviewed_dir: Path
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


def validate_curation(
    *,
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    reviewed_head: str,
    report_path: str,
    repository: GitRepository,
    base_repository: GitRepository,
    runner: ValidationCommandRunner | None = None,
) -> ValidationResult:
    initial = _curation_plan(
        pull_request,
        sync,
        reviewed_head,
        report_path,
        repository,
        base_repository,
        check=ErrorCheck.PREFLIGHT,
    )
    commands = _curation_commands(initial)
    observations = _run_curation_commands(
        initial,
        commands=commands,
        checks=(
            ErrorCheck.CATALOG_VALIDATION,
            ErrorCheck.CURATION_RECONCILIATION,
            ErrorCheck.CATALOG_TESTS,
        ),
        pull_request=pull_request,
        sync=sync,
        reviewed_head=reviewed_head,
        report_path=report_path,
        repository=repository,
        base_repository=base_repository,
        runner=runner,
    )

    final = _curation_plan(
        pull_request,
        sync,
        reviewed_head,
        report_path,
        repository,
        base_repository,
        check=ErrorCheck.POST_VALIDATION,
    )
    if final != initial:
        raise _validation_error(
            ErrorCheck.POST_VALIDATION,
            ErrorKind.MISMATCH,
            "Reviewed validation plan changed",
        )
    try:
        resulting_graph_markdown = immutable_resulting_graph_markdown(
            repository,
            reviewed_head,
            report_path,
        )
    except MaintainerError:
        raise
    except Exception:
        raise _validation_error(
            ErrorCheck.POST_VALIDATION,
            ErrorKind.MISMATCH,
            "Reviewed resulting graph could not be reproduced",
        ) from None
    return ValidationResult(
        validated_head=reviewed_head,
        commands_completed=3,
        observations=observations,
        resulting_graph_markdown=resulting_graph_markdown,
    )


def validate_curation_delta(
    *,
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    remediation_head: str,
    report_path: str,
    repository: GitRepository,
    base_repository: GitRepository,
    runner: ValidationCommandRunner | None = None,
) -> DeltaValidationResult:
    plan = _curation_plan(
        pull_request,
        sync,
        remediation_head,
        report_path,
        repository,
        base_repository,
        check=ErrorCheck.PREFLIGHT,
    )
    observations = _run_curation_commands(
        plan,
        commands=_curation_commands(plan)[:2],
        checks=(
            ErrorCheck.CATALOG_VALIDATION,
            ErrorCheck.CURATION_RECONCILIATION,
        ),
        pull_request=pull_request,
        sync=sync,
        reviewed_head=remediation_head,
        report_path=report_path,
        repository=repository,
        base_repository=base_repository,
        runner=runner,
    )
    return DeltaValidationResult(
        remediation_head=remediation_head,
        commands_completed=2,
        observations=observations,
    )


def _run_curation_commands(
    initial: _CurationPlan,
    *,
    commands: Sequence[tuple[str, ...]],
    checks: Sequence[ErrorCheck],
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    reviewed_head: str,
    report_path: str,
    repository: GitRepository,
    base_repository: GitRepository,
    runner: ValidationCommandRunner | None,
) -> tuple[ValidationCommandObservation, ...]:
    command_runner = runner or _SubprocessValidationRunner()
    expected_commands = _curation_commands(initial)
    observations: list[ValidationCommandObservation] = []
    for index, (command, check) in enumerate(
        zip(commands, checks, strict=True),
        start=1,
    ):
        current = _curation_plan(
            pull_request,
            sync,
            reviewed_head,
            report_path,
            repository,
            base_repository,
            check=check,
        )
        if current != initial or _curation_commands(current) != expected_commands:
            raise _validation_error(
                check,
                ErrorKind.MISMATCH,
                "Reviewed validation plan changed",
            )
        try:
            result = command_runner.run(
                command,
                cwd=Path(repository.root),
                timeout=VALIDATION_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise _validation_error(
                check,
                ErrorKind.TIMEOUT,
                "Validation command timed out",
            ) from None
        except OSError:
            raise _validation_error(
                check,
                ErrorKind.COMMAND_FAILED,
                "Validation command could not start",
            ) from None
        if result.returncode != 0:
            diagnostic = (
                _catalog_test_diagnostic(result, initial)
                if check is ErrorCheck.CATALOG_TESTS
                else None
            )
            raise _validation_error(
                check,
                ErrorKind.COMMAND_FAILED,
                "Validation command failed",
                diagnostic=diagnostic,
            )
        observations.append(_observe_command(index, result))
    return tuple(observations)


def immutable_resulting_graph_markdown(
    repository: GitRepository,
    revision: str,
    report_path: str,
) -> str:
    catalog_payload = json.loads(
        repository.read_bounded_immutable_text(
            revision,
            CATALOG_PATH,
            max_bytes=_PRIVATE_OBJECT_LIMIT,
        )
    )
    report_payload = json.loads(
        repository.read_bounded_immutable_text(
            revision,
            report_path,
            max_bytes=_PRIVATE_OBJECT_LIMIT,
        )
    )
    catalog = CatalogSnapshot.model_validate(catalog_payload)
    report = CatalogCurationReport.model_validate(report_payload)
    _validate_finalized_report(repository, revision, report)
    validate_catalog_resulting_graph(report, catalog, require=True)
    return render_catalog_resulting_graph_markdown(report, catalog)


def _validate_finalized_report(
    repository: GitRepository,
    revision: str,
    report: CatalogCurationReport,
) -> None:
    if report.report_schema_version != 3:
        raise ValueError("finalized curation report must use schema version 3")
    validate_catalog_curation_report(
        report,
        require_resulting_graph=True,
        require_current_destination_policy=True,
        require_bounded_review_inventory=True,
    )
    _require_regional_followup_backlog_anchors(repository, revision, report)


def _require_regional_followup_backlog_anchors(
    repository: GitRepository,
    revision: str,
    report: CatalogCurationReport,
) -> None:
    anchors = tuple(
        assessment.backlog_ref.removeprefix(CATALOG_BACKLOG_REF_PREFIX)
        for assessment in report.entity_scope_assessments
        if assessment.graph_impact == "regional_followup"
        and assessment.backlog_ref is not None
    )
    if not anchors:
        return
    markdown = repository.read_bounded_immutable_text(
        revision,
        BACKLOG_PATH,
        max_bytes=_PRIVATE_OBJECT_LIMIT,
    )
    heading_anchor_counts: dict[str, int] = {}
    for line in markdown.splitlines():
        match = re.fullmatch(r"#{1,6}[ \t]+(.+?)", line)
        if match is None:
            continue
        anchor = markdown_heading_anchor(match.group(1).strip().rstrip("#").strip())
        heading_anchor_counts[anchor] = heading_anchor_counts.get(anchor, 0) + 1
    if not all(heading_anchor_counts.get(anchor) == 1 for anchor in anchors):
        raise ValueError("regional follow-up backlog anchor is missing")


def revalidate_curation_request(
    *,
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    reviewed_head: str,
    report_path: str,
    repository: GitRepository,
    base_repository: GitRepository,
) -> None:
    """Recheck an already-validated request without rerunning validation commands."""
    _curation_plan(
        pull_request,
        sync,
        reviewed_head,
        report_path,
        repository,
        base_repository,
        check=ErrorCheck.POST_VALIDATION,
    )


def validate_proposal(
    *,
    candidate_key: str,
    candidate_origin: Literal["backlog", "external"],
    base: str,
    head: str,
    snapshot: IntentSnapshot,
    discovery_inventory: DiscoveryInventory,
    repository: GitRepository,
) -> ProposalValidationResult:
    _validate_proposal_preflight(
        candidate_key,
        candidate_origin,
        base,
        head,
        snapshot,
        discovery_inventory,
        repository,
    )
    report_path = _proposal_report_path(snapshot)
    try:
        with TemporaryDirectory(prefix="snowcast-maintainer-validation-") as directory:
            root = Path(directory)
            os.chmod(root, 0o700)
            base_catalog_path = root / "base" / CATALOG_PATH
            base_trust_path = root / "base" / TRUST_MANIFEST_PATH
            head_catalog_path = root / "head" / CATALOG_PATH
            head_trust_path = root / "head" / TRUST_MANIFEST_PATH
            report_file = root / "head" / report_path
            for revision, source_path, destination in (
                (base, CATALOG_PATH, base_catalog_path),
                (base, TRUST_MANIFEST_PATH, base_trust_path),
                (head, CATALOG_PATH, head_catalog_path),
                (head, TRUST_MANIFEST_PATH, head_trust_path),
                (head, report_path, report_file),
            ):
                _write_private_object(
                    destination,
                    repository.read_bounded_immutable_text(
                        revision,
                        source_path,
                        max_bytes=_PRIVATE_OBJECT_LIMIT,
                    ),
                )

            base_catalog = load_catalog_from_path(base_catalog_path)
            head_catalog = load_catalog_from_path(head_catalog_path)
            base_trust = _load_trust(base_trust_path)
            head_trust = _load_trust(head_trust_path)
            base_trust.validate_against_catalog(base_catalog)
            head_trust.validate_against_catalog(head_catalog)
            report = load_catalog_curation_report(report_file)
            if report.report_schema_version != 3:
                raise ValueError
            validate_catalog_curation_report(
                report,
                require_resulting_graph=True,
                require_current_destination_policy=True,
                require_bounded_review_inventory=True,
            )
            _require_regional_followup_backlog_anchors(repository, head, report)
            validate_catalog_resulting_graph(
                report,
                head_catalog,
                require=True,
            )
            reconcile_catalog_curation_report(
                report,
                base_catalog_path=base_catalog_path,
                current_catalog_path=head_catalog_path,
                base_trust_manifest_path=base_trust_path,
                current_trust_manifest_path=head_trust_path,
            )
            _validate_catalog_delta(
                candidate_key,
                base_catalog,
                head_catalog,
                report,
            )
            _validate_backlog_destination_proposal_scope(
                candidate_key,
                candidate_origin,
                base_catalog,
                head_catalog,
                report,
            )
            if any(
                issue.severity == "error"
                for issue in catalog_policy_issues(head_catalog)
            ):
                raise ValueError
    except MaintainerError:
        raise
    except Exception:
        raise _validation_error(
            ErrorCheck.CURATION_RECONCILIATION,
            ErrorKind.MISMATCH,
            "Proposal catalog reconciliation failed",
        ) from None

    return ProposalValidationResult(
        candidate_key=candidate_key,
        candidate_origin=candidate_origin,
        validated_head=head,
        report_path=report_path,
        resulting_graph_markdown=render_catalog_resulting_graph_markdown(
            report,
            head_catalog,
        ),
    )


def _curation_plan(
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    reviewed_head: str,
    report_path: str,
    repository: GitRepository,
    base_repository: GitRepository,
    *,
    check: ErrorCheck,
) -> _CurationPlan:
    try:
        snapshot = repository.revalidate_prepared_result(
            pull_request,
            sync,
            reviewed_head,
        )
        base_repository.verify_validation_base(sync.base_head)
        require_single_curation_report_path(snapshot, report_path)
        return _CurationPlan(
            report_path=report_path,
            base_dir=Path(base_repository.root),
            reviewed_dir=Path(repository.root),
            base_sha=sync.base_head,
            reviewed_head=reviewed_head,
        )
    except MaintainerError:
        raise
    except Exception:
        raise _validation_error(
            check,
            ErrorKind.MISMATCH,
            "Reviewed validation state changed",
        ) from None


def require_single_curation_report_path(
    snapshot: IntentSnapshot,
    report_path: str,
) -> None:
    if _REPORT_PATH.fullmatch(report_path) is None:
        raise ValueError("curation report path is invalid")
    if single_curation_report_path(snapshot.changed_paths) != report_path:
        raise ValueError("curation report path is not the single changed report")


def single_curation_report_path(changed_paths: Iterable[str]) -> str:
    report_paths = tuple(
        sorted(
            path for path in changed_paths if _REPORT_PATH.fullmatch(path) is not None
        )
    )
    if len(report_paths) != 1:
        raise ValueError("curation work must contain one report")
    return report_paths[0]


def _curation_commands(plan: _CurationPlan) -> tuple[tuple[str, ...], ...]:
    return (
        (
            "uv",
            "run",
            "--no-config",
            "--no-sync",
            "python",
            "-m",
            "app.data.validate_catalog",
            "--catalog-path",
            CATALOG_PATH,
            "--trust-manifest-path",
            TRUST_MANIFEST_PATH,
        ),
        (
            "uv",
            "run",
            "--no-config",
            "--no-sync",
            "python",
            "-m",
            "app.data.validate_catalog_curation",
            "reconcile",
            plan.report_path,
            "--base-catalog-path",
            str(plan.base_dir / CATALOG_PATH),
            "--current-catalog-path",
            CATALOG_PATH,
            "--base-trust-manifest-path",
            str(plan.base_dir / TRUST_MANIFEST_PATH),
            "--current-trust-manifest-path",
            TRUST_MANIFEST_PATH,
            "--require-report-schema-version",
            "3",
            "--require-markdown-path",
            plan.report_path.removesuffix(".json") + ".md",
            "--skip-product-backlog-validation",
        ),
        (
            "/usr/bin/env",
            f"SNOWCAST_CATALOG_DATA_ROOT={plan.reviewed_dir}",
            "uv",
            "run",
            "--project",
            str(plan.base_dir),
            "--no-config",
            "--no-env-file",
            "--no-sync",
            "pytest",
            "-c",
            str(plan.base_dir / "pyproject.toml"),
            "--rootdir",
            str(plan.base_dir),
            str(plan.base_dir / "tests/test_catalog_curation.py"),
            str(plan.base_dir / "tests/test_catalog_curation_reconciliation.py"),
            str(plan.base_dir / "tests/test_catalog_models.py"),
            str(plan.base_dir / "tests/test_catalog_trust.py"),
            "-q",
            "--tb=short",
            "--no-showlocals",
        ),
    )


def _validate_proposal_preflight(
    candidate_key: str,
    candidate_origin: str,
    base: str,
    head: str,
    snapshot: IntentSnapshot,
    discovery_inventory: DiscoveryInventory,
    repository: GitRepository,
) -> None:
    try:
        if (
            _CANDIDATE_KEY.fullmatch(candidate_key) is None
            or candidate_origin not in {"backlog", "external"}
            or _SHA.fullmatch(base) is None
            or _SHA.fullmatch(head) is None
            or not isinstance(snapshot, IntentSnapshot)
            or not isinstance(discovery_inventory, DiscoveryInventory)
        ):
            raise ValueError
        if repository.current_head() != head:
            raise ValueError
        if repository.verify_immutable_diff(base, head) != snapshot:
            raise ValueError
        if (
            not discovery_inventory.can_create_proposal
            or discovery_inventory.open_proposal_count >= 3
            or discovery_inventory.has_unknown_proposal_identity
            or discovery_inventory.unresolved_pushes
            or candidate_key in discovery_inventory.catalog_keys
            or candidate_key in discovery_inventory.open_candidate_keys
        ):
            raise ValueError
        required = {CATALOG_PATH, TRUST_MANIFEST_PATH}
        if not required.issubset(snapshot.changed_paths):
            raise ValueError
        report_path = _proposal_report_path(snapshot)
        if any(
            not _is_allowed_proposal_path(path, report_path)
            for path in snapshot.changed_paths
        ):
            raise ValueError
        if (
            candidate_key not in snapshot.catalog_targets
            or candidate_key not in snapshot.report_targets
        ):
            raise ValueError
    except MaintainerError:
        raise
    except Exception:
        raise _validation_error(
            ErrorCheck.PREFLIGHT,
            ErrorKind.MISMATCH,
            "Proposal validation preflight failed",
        ) from None


def _is_allowed_proposal_path(path: str, report_path: str) -> bool:
    if path in {
        CATALOG_PATH,
        TRUST_MANIFEST_PATH,
        BACKLOG_PATH,
        report_path,
        report_path.removesuffix(".json") + ".md",
    }:
        return True
    return (
        path != _RETIRED_DISCOVERY_REGISTRY_PATH
        and _DISCOVERY_DOCUMENT_PATH.fullmatch(path) is not None
    )


def _proposal_report_path(snapshot: IntentSnapshot) -> str:
    reports = tuple(
        sorted(
            path
            for path in snapshot.changed_paths
            if path.startswith(CURATION_REPORT_PREFIX)
            and path.endswith(".json")
            and _REPORT_PATH.fullmatch(path) is not None
        )
    )
    if len(reports) != 1:
        raise ValueError("proposal must contain one report")
    return reports[0]


def _write_private_object(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    if not encoded or len(encoded) > _PRIVATE_OBJECT_LIMIT:
        raise ValueError("immutable object size is invalid")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)


def _load_trust(path: Path) -> CatalogTrustManifest:
    return CatalogTrustManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _catalog_keys(catalog: CatalogSnapshot) -> frozenset[str]:
    return frozenset(
        f"{kind}:{getattr(item, id_field)}"
        for section, id_field, kind in CATALOG_SECTIONS
        for item in getattr(catalog, section)
    )


def _validate_catalog_delta(
    candidate_key: str,
    base_catalog: CatalogSnapshot,
    head_catalog: CatalogSnapshot,
    report: CatalogCurationReport,
) -> None:
    base_keys = _catalog_keys(base_catalog)
    head_keys = _catalog_keys(head_catalog)
    if candidate_key in base_keys or candidate_key not in head_keys:
        raise ValueError("catalog candidate delta is invalid")
    removed_keys = base_keys - head_keys
    if removed_keys and not _is_explicit_decision_bearing_rekey(
        candidate_key,
        removed_keys,
        report,
    ):
        raise ValueError("catalog candidate delta is invalid")


def _validate_backlog_destination_proposal_scope(
    candidate_key: str,
    candidate_origin: str,
    base_catalog: CatalogSnapshot,
    head_catalog: CatalogSnapshot,
    report: CatalogCurationReport,
) -> None:
    candidate_kind, candidate_id = candidate_key.split(":", maxsplit=1)
    if candidate_origin != "backlog" or candidate_kind != "stay_destination":
        return

    graph = report.resulting_graph
    if graph is None or graph.focus_stay_destination_ids != [candidate_id]:
        raise ValueError("backlog destination proposal focus is invalid")

    destination = next(
        (
            item
            for item in head_catalog.stay_destinations
            if item.stay_destination_id == candidate_id
        ),
        None,
    )
    if destination is None:
        raise ValueError("backlog destination proposal focus is invalid")

    scope = catalog_resulting_graph_scope(
        head_catalog,
        {candidate_id},
    )

    allowed_keys = {
        candidate_key,
        f"ski_region:{destination.trip_market_region_id}",
        *(f"stay_base:{base_id}" for base_id in scope.base_ids),
        *(f"ski_area_access:{access_id}" for access_id in scope.access_ids),
        *(f"ski_area:{area_id}" for area_id in scope.area_ids),
        *(f"terrain_domain:{domain_id}" for domain_id in scope.domain_ids),
        *(f"lift_pass_product:{pass_id}" for pass_id in scope.pass_ids),
        *(
            f"rental_display_fact:{item.rental_display_fact_id}"
            for item in head_catalog.rental_display_facts
            if item.stay_destination_id == candidate_id
        ),
    }
    if not (_catalog_keys(head_catalog) - _catalog_keys(base_catalog)).issubset(
        allowed_keys
    ):
        raise ValueError("backlog destination proposal contains unrelated additions")


def _is_explicit_decision_bearing_rekey(
    candidate_key: str,
    removed_keys: frozenset[str],
    report: CatalogCurationReport,
) -> bool:
    candidate_kind, _ = candidate_key.split(":", maxsplit=1)
    removed_targets = {
        tuple(removed_key.split(":", maxsplit=1)) for removed_key in removed_keys
    }
    if (
        not report.unresolved_caveats
        or not removed_targets
        or any(target_type != candidate_kind for target_type, _ in removed_targets)
    ):
        return False

    fully_reviewed = {
        target.target_key
        for target in report.reviewed_targets
        if target.scope == "full"
    }
    unresolved_scope_targets = {
        target_ref.target_key
        for assessment in report.entity_scope_assessments
        if assessment.disposition == "unresolved"
        for target_ref in assessment.target_refs
    }
    identity_field_by_kind = {kind: id_field for _, id_field, kind in CATALOG_SECTIONS}
    changes_by_key = {change.target_key: change for change in report.changes}
    for target_type, target_id in removed_targets:
        identity_field = identity_field_by_kind.get(target_type)
        identity_change = changes_by_key.get(
            (target_type, target_id, identity_field or "")
        )
        if (
            identity_field is None
            or (target_type, target_id) not in fully_reviewed
            or (target_type, target_id) not in unresolved_scope_targets
            or identity_change is None
            or identity_change.before != target_id
            or identity_change.after is not None
        ):
            return False
    return True


def _observe_command(
    index: int,
    result: subprocess.CompletedProcess[str],
) -> ValidationCommandObservation:
    stdout = result.stdout if isinstance(result.stdout, str) else ""
    stderr = result.stderr if isinstance(result.stderr, str) else ""
    return ValidationCommandObservation(
        command_index=index,
        stdout_characters=min(len(stdout), _OUTPUT_OBSERVATION_LIMIT),
        stderr_characters=min(len(stderr), _OUTPUT_OBSERVATION_LIMIT),
        output_truncated=(
            len(stdout) > _OUTPUT_OBSERVATION_LIMIT
            or len(stderr) > _OUTPUT_OBSERVATION_LIMIT
        ),
    )


def _validation_error(
    check: ErrorCheck,
    kind: ErrorKind,
    detail: str,
    *,
    diagnostic: CurationValidationDiagnostic | None = None,
) -> MaintainerError:
    return MaintainerError(
        reason=ErrorReason.VALIDATION_FAILED,
        stage=ErrorStage.VALIDATE,
        check=check,
        kind=kind,
        detail=detail,
        diagnostic=diagnostic,
    )


def _catalog_test_diagnostic(
    result: subprocess.CompletedProcess[str],
    plan: _CurationPlan,
) -> CurationValidationDiagnostic | None:
    streams = tuple(
        value
        for value in (result.stdout, result.stderr)
        if isinstance(value, str) and value.strip()
    )
    if not streams:
        return None
    text = "\n".join(streams).replace("\r\n", "\n").replace("\r", "\n")
    for path, replacement in sorted(
        (
            (str(plan.base_dir), "<base>"),
            (str(plan.reviewed_dir), "<reviewed>"),
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        text = text.replace(path, replacement)
    text = _ANSI_ESCAPE.sub("", text)
    text = "".join(
        character
        for character in text
        if unicodedata.category(character) != "Cc" or character in {"\n", "\t"}
    ).strip()
    if not text:
        return None
    truncated = (
        _OUTPUT_TRUNCATION_MARKER.strip() in text
        or len(text) > _VALIDATION_DIAGNOSTIC_LIMIT
    )
    if len(text) > _VALIDATION_DIAGNOSTIC_LIMIT:
        suffix = "\n...[diagnostic truncated]..."
        text = text[: _VALIDATION_DIAGNOSTIC_LIMIT - len(suffix)].rstrip() + suffix
    return CurationValidationDiagnostic(
        format="pytest-short",
        text=text,
        truncated=truncated,
    )

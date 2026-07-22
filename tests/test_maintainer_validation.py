from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest

from app.data.catalog_curation import CANONICAL_FIELD_PATHS, CatalogCurationReport
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import FIELD_GROUPS
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    MaintainerError,
)
from ops.maintainer.git_ops import GuardedSyncResult, RepositorySafetyError
from ops.maintainer.inspection import DiscoveryInventory, inspect_discovery
from ops.maintainer.intent import (
    BACKLOG_PATH,
    CATALOG_SECTIONS,
    IntentDiffEntry,
    IntentSnapshot,
)
from ops.maintainer.models import PullRequest
from ops.maintainer.state import PushJournal, PushPhase
from ops.maintainer.validation import (
    _PROCESS_GROUP_GRACE_SECONDS,
    VALIDATION_COMMAND_TIMEOUT_SECONDS,
    DeltaValidationResult,
    ProposalValidationResult,
    ValidationResult,
    _SubprocessValidationRunner,
    _terminate_process_group,
    _validate_catalog_delta,
    _write_private_object,
    validate_curation,
    validate_curation_delta,
    validate_proposal,
)
from tests.test_catalog_models import minimal_catalog_payload

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
REPORT_PATH = "docs/catalog-curation/nendaz-village.json"
CATALOG_PATH = "app/data/catalog.json"
TRUST_PATH = "app/data/resort_trust_manifest.json"
CANDIDATE_KEY = "stay_destination:nendaz"
REGIONAL_CANDIDATE_KEY = "stay_destination:sample-valley"
REGIONAL_REPORT_PATH = "docs/catalog-curation/sample-valley.json"
REGIONAL_BACKLOG_REF = "docs/product-backlog.md#sample-valley-regional-completion"
REGIONAL_SOURCE_URLS = {
    "destination": "https://example.com/sample-valley/stays",
    "ski_area": "https://example.com/sample-valley/ski-areas",
    "access": "https://example.com/sample-valley/access",
    "pass": "https://example.com/sample-valley/passes",
    "followup": "https://example.com/sample-valley/adjacent-markets",
}


def _pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Nendaz Village",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": "codex/catalog-curation-nendaz-village",
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "lifecycle_state": "OPEN",
        "created_at": datetime(2026, 7, 8, 10, tzinfo=UTC),
        "labels": frozenset({"lane:catalog-curation"}),
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset({CATALOG_PATH, TRUST_PATH, REPORT_PATH}),
        "body": "",
    }
    values.update(overrides)
    return PullRequest.model_validate(values)


def _sync() -> GuardedSyncResult:
    return GuardedSyncResult(
        target_branch="codex/catalog-curation-nendaz-village",
        original_head=SHA_A,
        rebased_head=SHA_B,
        backup_ref=(
            f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{SHA_A[:12]}"
        ),
        prepared_ref=(
            f"refs/snowcast-maintainer/prepared/pr-42/{SHA_C[:12]}-{SHA_B[:12]}"
        ),
        base_head=SHA_C,
        merge_base="d" * 40,
    )


def _entry(path: str, index: int) -> IntentDiffEntry:
    return IntentDiffEntry(
        path=path,
        old_mode="100644",
        new_mode="100644",
        old_oid=f"{index:x}" * 40,
        new_oid=f"{index + 4:x}" * 40,
        status="M",
    )


def _intent(
    *,
    changed_paths: frozenset[str] = frozenset({CATALOG_PATH, TRUST_PATH, REPORT_PATH}),
    catalog_targets: frozenset[str] = frozenset({CANDIDATE_KEY}),
    report_targets: frozenset[str] = frozenset(
        {CANDIDATE_KEY, "trust_manifest:stay_destinations:nendaz"}
    ),
) -> IntentSnapshot:
    return IntentSnapshot(
        changed_paths=changed_paths,
        diff_entries=tuple(
            _entry(path, index)
            for index, path in enumerate(sorted(changed_paths), start=1)
        ),
        catalog_targets=catalog_targets,
        report_targets=report_targets,
    )


def _current_graph_report_payload() -> dict[str, object]:
    return {
        "report_schema_version": 3,
        "title": "Example access review",
        "summary": "Reviews the exact access graph.",
        "resulting_graph": {"focus_stay_destination_ids": ["example"]},
        "reviewed_targets": [
            {
                "target_type": "ski_area_access",
                "target_id": "example-village--example-area",
                "scope": "narrow",
                "required_field_paths": ["distance_m"],
            }
        ],
        "changes": [
            {
                "target_type": "ski_area_access",
                "target_id": "example-village--example-area",
                "field_path": "distance_m",
                "before": 250,
                "after": 300,
                "trust_status": "estimated",
            }
        ],
        "field_coverage": [
            {
                "target_type": "ski_area_access",
                "target_id": "example-village--example-area",
                "field_path": "distance_m",
                "status": "changed",
            }
        ],
        "evidence": [
            {
                "evidence_id": "example-access-scope",
                "target_type": "ski_area_access",
                "target_id": "example-village--example-area",
                "field_path": "source_urls",
                "source_type": "official",
                "source_url": "https://example.com/access",
                "source_title": "Official access",
                "source_value": ["https://example.com/access"],
                "evidence_summary": "Confirms the modeled access relationship.",
            }
        ],
        "entity_scope_assessments": [
            {
                "candidate_id": "example-access",
                "candidate_name": "Example access",
                "candidate_kind": "ski_area_access",
                "disposition": "represented",
                "signals": ["direct_access_relationship"],
                "evidence_refs": ["example-access-scope"],
                "target_refs": [
                    {
                        "target_type": "ski_area_access",
                        "target_id": "example-village--example-area",
                    }
                ],
                "rationale": "The access relationship is represented explicitly.",
                "graph_impact": "graph_blocking",
            }
        ],
        "review_evidence_envelope": [
            {
                "family_id": "example-access",
                "source_kind": "access_transport",
                "source_urls": ["https://example.com/access"],
                "candidate_kinds": ["ski_area_access"],
            }
        ],
    }


class FakeLiveRepository:
    def __init__(self, root: Path, snapshot: IntentSnapshot) -> None:
        self.root = root
        self.snapshot = snapshot
        self.fail = False
        self.revalidate_calls = 0
        self.base_calls = 0
        self.immutable_texts = {
            CATALOG_PATH: json.dumps(minimal_catalog_payload()),
            REPORT_PATH: json.dumps(_current_graph_report_payload()),
        }
        self.immutable_sizes: dict[str, int] = {}
        self.immutable_calls: list[tuple[str, str, int]] = []

    def revalidate_prepared_result(
        self,
        pull_request: PullRequest,
        sync: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot:
        del pull_request, sync, reviewed_head
        self.revalidate_calls += 1
        if self.fail:
            raise RepositorySafetyError("raw reviewed drift")
        return self.snapshot

    def verify_validation_base(self, expected_sha: str) -> None:
        del expected_sha
        self.base_calls += 1
        if self.fail:
            raise RepositorySafetyError("raw base drift")

    def read_bounded_immutable_text(
        self,
        revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> str:
        self.immutable_calls.append((revision, path, max_bytes))
        assert revision == SHA_B
        value = self.immutable_texts.get(path)
        if value is None:
            raise RepositorySafetyError("unexpected immutable object")
        size = self.immutable_sizes.get(path, len(value.encode("utf-8")))
        if not 1 <= size <= max_bytes:
            raise RepositorySafetyError("raw immutable object failed bounds")
        return value


class RecordingRunner:
    def __init__(
        self,
        *,
        returncodes: tuple[int, ...] = (),
        timeout_at: int | None = None,
        mutate_after: int | None = None,
        repository: FakeLiveRepository | None = None,
    ) -> None:
        self.returncodes = returncodes
        self.timeout_at = timeout_at
        self.mutate_after = mutate_after
        self.repository = repository
        self.calls: list[tuple[tuple[str, ...], Path, float]] = []

    def run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((tuple(argv), cwd, timeout))
        index = len(self.calls)
        if self.timeout_at == index:
            raise subprocess.TimeoutExpired(["secret", "command"], timeout)
        if self.mutate_after == index and self.repository is not None:
            self.repository.fail = True
        returncode = (
            self.returncodes[index - 1] if index <= len(self.returncodes) else 0
        )
        return subprocess.CompletedProcess(
            argv,
            returncode,
            "raw private stdout" * 500,
            "raw secret stderr" * 500,
        )


@dataclass
class AlwaysTimeoutProcess:
    wait_calls: list[float | None] = field(default_factory=list)

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        raise subprocess.TimeoutExpired(["raw-secret-command"], timeout)


def test_validate_curation_maps_exhausted_cleanup_without_unbounded_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    process = AlwaysTimeoutProcess()
    signals: list[int] = []
    monkeypatch.setattr(
        "ops.maintainer.validation._signal_process_group",
        lambda process_group, requested_signal: signals.append(requested_signal),
    )
    monkeypatch.setattr(
        "ops.maintainer.validation._wait_for_process_group_exit",
        lambda process_group, timeout: False,
    )

    class CleanupFailureRunner:
        def run(
            self,
            argv: tuple[str, ...],
            *,
            cwd: Path,
            timeout: float,
        ) -> subprocess.CompletedProcess[str]:
            del argv, cwd, timeout
            _terminate_process_group(  # type: ignore[arg-type]
                process,
                987654,
            )
            raise AssertionError("cleanup must not return")

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=CleanupFailureRunner(),
        )

    assert process.wait_calls == [_PROCESS_GROUP_GRACE_SECONDS] * 3
    assert all(timeout is not None for timeout in process.wait_calls)
    assert signals == [signal.SIGTERM, signal.SIGKILL, signal.SIGKILL]
    assert exc_info.value.check is ErrorCheck.CATALOG_VALIDATION
    assert exc_info.value.kind is ErrorKind.COMMAND_FAILED
    assert "raw-secret-command" not in json.dumps(exc_info.value.payload())


def test_default_runner_discards_output_and_secret_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-validation")
    script = (
        "import os,sys\n"
        "assert 'OPENAI_API_KEY' not in os.environ\n"
        "for _ in range(512):\n"
        " os.write(1, b'x' * 4096)\n"
        " os.write(2, b'y' * 4096)\n"
    )

    result = _SubprocessValidationRunner().run(
        (sys.executable, "-c", script),
        cwd=tmp_path,
        timeout=5.0,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def _wait_for_process_exit(pid: int) -> None:
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    pytest.fail(f"descendant process {pid} survived cleanup")


def test_default_runner_kills_process_group_on_timeout(tmp_path: Path) -> None:
    pid_path = tmp_path / "child.pid"
    child = (
        "import signal,time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
    )
    script = (
        "import pathlib,signal,subprocess,sys,time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"child = subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        f"pathlib.Path({str(pid_path)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n"
    )

    with pytest.raises(subprocess.TimeoutExpired):
        _SubprocessValidationRunner().run(
            (sys.executable, "-c", script),
            cwd=tmp_path,
            timeout=0.5,
        )

    _wait_for_process_exit(int(pid_path.read_text(encoding="utf-8")))


def _curation_dependencies(
    tmp_path: Path,
) -> tuple[FakeLiveRepository, FakeLiveRepository]:
    reviewed = FakeLiveRepository(tmp_path / "reviewed", _intent())
    base = FakeLiveRepository(tmp_path / "base", _intent())
    reviewed.root.mkdir()
    base.root.mkdir()
    return reviewed, base


def test_validate_curation_runs_fixed_commands_for_one_exact_head(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    runner = RecordingRunner()

    result = validate_curation(
        pull_request=_pull_request(),
        sync=_sync(),
        reviewed_head=SHA_B,
        report_path=REPORT_PATH,
        repository=reviewed,  # type: ignore[arg-type]
        base_repository=base,  # type: ignore[arg-type]
        runner=runner,
    )

    assert isinstance(result, ValidationResult)
    assert result.validated_head == SHA_B
    assert result.commands_completed == 3
    assert len(result.observations) == 3
    assert all(call[2] == VALIDATION_COMMAND_TIMEOUT_SECONDS for call in runner.calls)
    commands = [call[0] for call in runner.calls]
    assert "app.data.validate_catalog" in commands[0]
    assert "app.data.validate_catalog_curation" in commands[1]
    schema_flag = commands[1].index("--require-report-schema-version")
    assert commands[1][schema_flag + 1] == "3"
    assert "--skip-product-backlog-validation" in commands[1]
    assert "--product-backlog-path" not in commands[1]
    assert "tests/test_catalog_curation_backlog.py" not in commands[2]
    assert reviewed.revalidate_calls == 5
    assert base.base_calls == 5


def test_validate_curation_delta_runs_only_the_two_non_pytest_commands(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    runner = RecordingRunner()

    result = validate_curation_delta(
        pull_request=_pull_request(),
        sync=_sync(),
        remediation_head=SHA_B,
        report_path=REPORT_PATH,
        repository=reviewed,  # type: ignore[arg-type]
        base_repository=base,  # type: ignore[arg-type]
        runner=runner,
    )

    assert isinstance(result, DeltaValidationResult)
    assert result.remediation_head == SHA_B
    assert result.commands_completed == 2
    assert len(result.observations) == 2
    commands = [call[0] for call in runner.calls]
    assert len(commands) == 2
    assert all("pytest" not in command for command in commands)


@pytest.mark.parametrize(
    ("failure", "check", "kind"),
    [
        ("command", ErrorCheck.CATALOG_VALIDATION, ErrorKind.COMMAND_FAILED),
        ("timeout", ErrorCheck.CURATION_RECONCILIATION, ErrorKind.TIMEOUT),
    ],
)
def test_validate_curation_delta_preserves_structured_command_failures(
    tmp_path: Path,
    failure: Literal["command", "timeout"],
    check: ErrorCheck,
    kind: ErrorKind,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    runner = (
        RecordingRunner(returncodes=(1,))
        if failure == "command"
        else RecordingRunner(timeout_at=2)
    )

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation_delta(
            pull_request=_pull_request(),
            sync=_sync(),
            remediation_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=runner,
        )

    assert exc_info.value.check is check
    assert exc_info.value.kind is kind


def test_validate_curation_delta_rejects_plan_drift(tmp_path: Path) -> None:
    reviewed, base = _curation_dependencies(tmp_path)

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation_delta(
            pull_request=_pull_request(),
            sync=_sync(),
            remediation_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(mutate_after=1, repository=reviewed),
        )

    assert exc_info.value.check is ErrorCheck.CURATION_RECONCILIATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


@pytest.mark.parametrize("missing", ["review_evidence_envelope", "graph_impact"])
def test_validate_curation_rejects_incomplete_bounded_review_inventory(
    tmp_path: Path,
    missing: Literal["review_evidence_envelope", "graph_impact"],
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    payload = _current_graph_report_payload()
    if missing == "review_evidence_envelope":
        payload.pop(missing)
    else:
        payload["entity_scope_assessments"][0].pop(missing)  # type: ignore[index]
    reviewed.immutable_texts[REPORT_PATH] = json.dumps(payload)

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(),
        )

    assert exc_info.value.check is ErrorCheck.POST_VALIDATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def _regional_followup_report_payload() -> dict[str, object]:
    payload = _current_graph_report_payload()
    payload["entity_scope_assessments"].append(  # type: ignore[index]
        {
            "candidate_id": "regional-followup",
            "candidate_name": "Regional followup",
            "candidate_kind": "stay_destination",
            "disposition": "deferred",
            "signals": ["independent_stay_market"],
            "evidence_refs": ["example-access-scope"],
            "target_refs": [],
            "backlog_ref": "docs/product-backlog.md#regional-followup",
            "rationale": "A bounded regional followup remains necessary.",
            "graph_impact": "regional_followup",
        }
    )
    return payload


def test_validate_curation_accepts_exact_head_regional_followup_anchor(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    reviewed.immutable_texts[REPORT_PATH] = json.dumps(
        _regional_followup_report_payload()
    )
    reviewed.immutable_texts[BACKLOG_PATH] = (
        "# Product Backlog\n\n## Regional Followup\n"
    )

    result = validate_curation(
        pull_request=_pull_request(),
        sync=_sync(),
        reviewed_head=SHA_B,
        report_path=REPORT_PATH,
        repository=reviewed,  # type: ignore[arg-type]
        base_repository=base,  # type: ignore[arg-type]
        runner=RecordingRunner(),
    )

    assert result.validated_head == SHA_B
    assert (SHA_B, BACKLOG_PATH, 1_000_000) in reviewed.immutable_calls


@pytest.mark.parametrize(
    "backlog",
    [
        "# Product Backlog\n\n## Different Heading\n",
        "{not markdown",
        None,
    ],
)
def test_validate_curation_rejects_missing_or_invalid_regional_followup_backlog(
    tmp_path: Path,
    backlog: str | None,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    reviewed.immutable_texts[REPORT_PATH] = json.dumps(
        _regional_followup_report_payload()
    )
    if backlog is not None:
        reviewed.immutable_texts[BACKLOG_PATH] = backlog

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(),
        )

    assert exc_info.value.check is ErrorCheck.POST_VALIDATION
    assert exc_info.value.kind is ErrorKind.MISMATCH
    assert "markdown" not in json.dumps(exc_info.value.payload())


def test_validate_curation_rejects_oversized_regional_followup_backlog(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    reviewed.immutable_texts[REPORT_PATH] = json.dumps(
        _regional_followup_report_payload()
    )
    reviewed.immutable_texts[BACKLOG_PATH] = "# Product Backlog\n"
    reviewed.immutable_sizes[BACKLOG_PATH] = 1_000_001

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(),
        )

    assert exc_info.value.check is ErrorCheck.POST_VALIDATION
    assert "oversized" not in json.dumps(exc_info.value.payload())


def test_validate_curation_rejects_ambiguous_regional_followup_anchor(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    reviewed.immutable_texts[REPORT_PATH] = json.dumps(
        _regional_followup_report_payload()
    )
    reviewed.immutable_texts[BACKLOG_PATH] = (
        "# Product Backlog\n\n## Regional Followup\n\n### Regional Followup\n"
    )

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(),
        )

    assert exc_info.value.check is ErrorCheck.POST_VALIDATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def test_validate_curation_does_not_read_backlog_without_regional_followup(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)

    validate_curation(
        pull_request=_pull_request(),
        sync=_sync(),
        reviewed_head=SHA_B,
        report_path=REPORT_PATH,
        repository=reviewed,  # type: ignore[arg-type]
        base_repository=base,  # type: ignore[arg-type]
        runner=RecordingRunner(),
    )

    assert all(path != BACKLOG_PATH for _, path, _ in reviewed.immutable_calls)


@pytest.mark.parametrize(
    ("command_index", "check"),
    [
        (1, ErrorCheck.CATALOG_VALIDATION),
        (2, ErrorCheck.CURATION_RECONCILIATION),
        (3, ErrorCheck.CATALOG_TESTS),
    ],
)
def test_validate_curation_maps_each_command_failure_without_raw_output(
    tmp_path: Path,
    command_index: int,
    check: ErrorCheck,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    returncodes = tuple(1 if index == command_index else 0 for index in range(1, 4))

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(returncodes=returncodes),
        )

    assert exc_info.value.reason is ErrorReason.VALIDATION_FAILED
    assert exc_info.value.check is check
    assert exc_info.value.kind is ErrorKind.COMMAND_FAILED
    assert "raw" not in json.dumps(exc_info.value.payload())
    assert "secret" not in json.dumps(exc_info.value.payload())


@pytest.mark.parametrize(
    ("command_index", "check"),
    [
        (1, ErrorCheck.CATALOG_VALIDATION),
        (2, ErrorCheck.CURATION_RECONCILIATION),
        (3, ErrorCheck.CATALOG_TESTS),
    ],
)
def test_validate_curation_maps_each_timeout(
    tmp_path: Path,
    command_index: int,
    check: ErrorCheck,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(timeout_at=command_index),
        )

    assert exc_info.value.check is check
    assert exc_info.value.kind is ErrorKind.TIMEOUT


def test_validate_curation_maps_preflight_and_post_validation_drift(
    tmp_path: Path,
) -> None:
    reviewed, base = _curation_dependencies(tmp_path)
    reviewed.fail = True
    with pytest.raises(MaintainerError) as preflight:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(),
        )
    assert preflight.value.check is ErrorCheck.PREFLIGHT
    assert preflight.value.kind is ErrorKind.MISMATCH

    reviewed.fail = False
    runner = RecordingRunner(mutate_after=3, repository=reviewed)
    with pytest.raises(MaintainerError) as post:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path=REPORT_PATH,
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=runner,
        )
    assert post.value.check is ErrorCheck.POST_VALIDATION
    assert post.value.kind is ErrorKind.MISMATCH


def test_validate_curation_rejects_explicit_report_mismatch(tmp_path: Path) -> None:
    reviewed, base = _curation_dependencies(tmp_path)

    with pytest.raises(MaintainerError) as exc_info:
        validate_curation(
            pull_request=_pull_request(),
            sync=_sync(),
            reviewed_head=SHA_B,
            report_path="docs/catalog-curation/other.json",
            repository=reviewed,  # type: ignore[arg-type]
            base_repository=base,  # type: ignore[arg-type]
            runner=RecordingRunner(),
        )

    assert exc_info.value.check is ErrorCheck.PREFLIGHT
    assert exc_info.value.kind is ErrorKind.MISMATCH


def _catalog_pair() -> tuple[dict[str, object], dict[str, object]]:
    base = json.loads(Path("app/data/catalog.json").read_text(encoding="utf-8"))
    head = deepcopy(base)
    head["stay_destinations"].append(  # type: ignore[union-attr]
        {
            "stay_destination_id": "nendaz",
            "name": "Nendaz",
            "country": "Switzerland",
            "region": "Valais",
            "price_level": "medium",
            "latitude": 46.183,
            "longitude": 7.3,
            "trip_market_region_id": "verbier",
            "regional_data_ids": {},
        }
    )
    CatalogSnapshot.model_validate(base)
    CatalogSnapshot.model_validate(head)
    return base, head


def _trust_pair() -> tuple[dict[str, object], dict[str, object]]:
    base = json.loads(
        Path("app/data/resort_trust_manifest.json").read_text(encoding="utf-8")
    )
    head = deepcopy(base)
    groups = FIELD_GROUPS["stay_destinations"]
    head["entities"]["stay_destinations"]["nendaz"] = {  # type: ignore[index]
        "display_name": "Nendaz",
        "field_statuses": {group: "estimated" for group in groups},
        "field_source_refs": {group: [] for group in groups},
        "notes": [],
    }
    return base, head


def _nested(payload: object, field_path: str) -> object:
    value = payload
    for segment in field_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return value


def _report_payload(
    head_catalog: dict[str, object],
    head_trust: dict[str, object],
) -> dict[str, object]:
    catalog = CatalogSnapshot.model_validate(head_catalog)
    destination = next(
        item
        for item in catalog.stay_destinations
        if item.stay_destination_id == "nendaz"
    ).model_dump(mode="json")
    trust = head_trust["entities"]["stay_destinations"]["nendaz"]  # type: ignore[index]
    targets = (
        ("stay_destination", "nendaz", destination),
        ("trust_manifest", "stay_destinations:nendaz", trust),
    )
    changes: list[dict[str, object]] = []
    coverage: list[dict[str, object]] = []
    for target_type, target_id, payload in targets:
        for field_path in sorted(CANONICAL_FIELD_PATHS[target_type]):
            after = _nested(payload, field_path)
            status = "reviewed-no-change"
            if after is not None:
                changes.append(
                    {
                        "target_type": target_type,
                        "target_id": target_id,
                        "field_path": field_path,
                        "before": None,
                        "after": after,
                        "trust_status": "estimated",
                    }
                )
                status = "changed"
            coverage.append(
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "field_path": field_path,
                    "status": status,
                }
            )
    return {
        "report_schema_version": 3,
        "title": "Nendaz Village onboarding",
        "summary": "Adds a separately represented stay base.",
        "resulting_graph": {
            "focus_stay_destination_ids": ["nendaz"],
        },
        "reviewed_targets": [
            {"target_type": target_type, "target_id": target_id, "scope": "full"}
            for target_type, target_id, _ in targets
        ],
        "changes": changes,
        "field_coverage": coverage,
        "evidence": [
            {
                "evidence_id": "nendaz-identity",
                "boundary_target_ids": ["nendaz"],
                "target_type": "stay_destination",
                "target_id": "nendaz",
                "field_path": "stay_destination_id",
                "source_type": "official",
                "source_url": "https://example.com/nendaz",
                "source_title": "Official Nendaz",
                "source_value": "nendaz",
                "evidence_summary": "Confirms the independently tracked destination.",
            }
        ],
        "entity_scope_assessments": [
            {
                "candidate_id": "nendaz",
                "candidate_name": "Nendaz",
                "candidate_kind": "stay_destination",
                "disposition": "add_entity",
                "signals": ["independent_stay_market"],
                "evidence_refs": ["nendaz-identity"],
                "target_refs": [
                    {"target_type": "stay_destination", "target_id": "nendaz"}
                ],
                "rationale": (
                    "The source supports a separately represented destination."
                ),
                "graph_impact": "graph_blocking",
            }
        ],
        "review_evidence_envelope": [
            {
                "family_id": "nendaz-identity",
                "source_kind": "destination_booking",
                "source_urls": ["https://example.com/nendaz"],
                "candidate_kinds": ["stay_destination"],
            }
        ],
        "destination_boundary_assessments": [
            {
                "candidate_id": "nendaz",
                "gates": [
                    {
                        "gate_name": gate_name,
                        "status": "pass",
                        "notes": "The source supports an independent destination.",
                        "evidence_refs": ["nendaz-identity"],
                    }
                    for gate_name in (
                        "complete_stay_market_scope",
                        "independent_stay_market_ownership",
                        "material_destination_level_separation_value",
                    )
                ],
                "identity_signals": [
                    {
                        "signal_type": "official_stay_market_treatment",
                        "status": "pass",
                        "notes": "The official source names the destination.",
                        "evidence_refs": ["nendaz-identity"],
                    }
                ],
                "failure_route": None,
            }
        ],
        "boundary_decision_targets": ["nendaz"],
    }


@dataclass
class FakeObjectRepository:
    base: str
    head: str
    snapshot: IntentSnapshot
    texts: dict[tuple[str, str], str]
    current: str | None = None
    verified_snapshot: IntentSnapshot | None = None
    reported_sizes: dict[tuple[str, str], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.current = self.current or self.head
        self.show_calls: list[tuple[str, str]] = []
        self.bounded_calls: list[tuple[str, str, int]] = []

    def current_head(self) -> str:
        assert self.current is not None
        return self.current

    def verify_immutable_diff(self, base: str, head: str) -> IntentSnapshot:
        assert (base, head) == (self.base, self.head)
        return self.verified_snapshot or self.snapshot

    def show_text(self, revision: str, path: str) -> str:
        self.show_calls.append((revision, path))
        return self.texts[(revision, path)]

    def read_bounded_immutable_text(
        self,
        revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> str:
        self.bounded_calls.append((revision, path, max_bytes))
        size = self.reported_sizes.get((revision, path))
        if size is None:
            size = len(self.texts[(revision, path)].encode("utf-8"))
        if not 1 <= size <= max_bytes:
            raise RepositorySafetyError("raw oversized immutable object")
        return self.show_text(revision, path)


def _proposal_dependencies() -> tuple[
    FakeObjectRepository,
    IntentSnapshot,
    DiscoveryInventory,
]:
    base_catalog, head_catalog = _catalog_pair()
    base_trust, head_trust = _trust_pair()
    report = _report_payload(head_catalog, head_trust)
    snapshot = _intent()
    repository = FakeObjectRepository(
        base=SHA_A,
        head=SHA_B,
        snapshot=snapshot,
        texts={
            (SHA_A, CATALOG_PATH): json.dumps(base_catalog),
            (SHA_B, CATALOG_PATH): json.dumps(head_catalog),
            (SHA_A, TRUST_PATH): json.dumps(base_trust),
            (SHA_B, TRUST_PATH): json.dumps(head_trust),
            (SHA_B, REPORT_PATH): json.dumps(report),
        },
    )
    inventory = DiscoveryInventory(
        catalog_keys=frozenset(),
        open_proposal_count=0,
        open_candidate_keys=frozenset(),
        has_unknown_proposal_identity=False,
        can_create_proposal=True,
    )
    return repository, snapshot, inventory


@dataclass(frozen=True)
class RegionalProposalContext:
    base: str
    head: str
    snapshot: IntentSnapshot
    discovery_inventory: DiscoveryInventory
    repository: FakeObjectRepository


def _catalog_key_set(payload: dict[str, object]) -> frozenset[str]:
    catalog = CatalogSnapshot.model_validate(payload)
    return frozenset(
        f"{kind}:{getattr(item, id_field)}"
        for section, id_field, kind in CATALOG_SECTIONS
        for item in getattr(catalog, section)
    )


def _trust_payload_for_catalog(payload: dict[str, object]) -> dict[str, object]:
    catalog = CatalogSnapshot.model_validate(payload)
    bases_by_id = {item.stay_base_id: item for item in catalog.stay_bases}
    areas_by_id = {item.ski_area_id: item for item in catalog.ski_areas}
    entities: dict[str, dict[str, object]] = {
        section: {} for section, _, _ in CATALOG_SECTIONS
    }
    for section, id_field, _ in CATALOG_SECTIONS:
        for item in getattr(catalog, section):
            entity_id = getattr(item, id_field)
            display_name = getattr(item, "name", entity_id)
            if section == "ski_area_access":
                display_name = (
                    f"{bases_by_id[item.stay_base_id].name} -> "
                    f"{areas_by_id[item.ski_area_id].name}"
                )
            source_refs = {group: [] for group in FIELD_GROUPS[section]}
            if section == "ski_area_access":
                source_refs["relationship"] = list(item.source_urls)
            entities[section][entity_id] = {
                "display_name": display_name,
                "field_statuses": {
                    group: "estimated" for group in FIELD_GROUPS[section]
                },
                "field_source_refs": source_refs,
                "notes": [],
            }
    return {
        "version": "2",
        "catalog_schema_version": 2,
        "status_values": [
            "verified",
            "verified_with_adjustment",
            "estimated",
            "needs_source",
        ],
        "field_groups": {
            section: list(FIELD_GROUPS[section]) for section, _, _ in CATALOG_SECTIONS
        },
        "entities": entities,
    }


def _regional_catalog_pair(
    *,
    include_unrelated_entity: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    base = minimal_catalog_payload()
    head = deepcopy(base)
    head["stay_destinations"].append(  # type: ignore[union-attr]
        {
            "stay_destination_id": "sample-valley",
            "name": "Sample Valley",
            "country": "Austria",
            "region": "Salzburg",
            "price_level": "medium",
            "latitude": 47.25,
            "longitude": 13.55,
            "trip_market_region_id": "example",
            "regional_data_ids": {},
        }
    )
    head["stay_bases"].extend(  # type: ignore[union-attr]
        [
            {
                "stay_base_id": "sample-village",
                "stay_destination_id": "sample-valley",
                "name": "Sample Village",
                "price_range": "EUR 150-220",
                "price_min": 150,
                "price_max": 220,
                "quality": "standard",
                "latitude": 47.25,
                "longitude": 13.55,
                "elevation_m": 1100,
                "base_type": "village",
            },
            {
                "stay_base_id": "sample-hamlet",
                "stay_destination_id": "sample-valley",
                "name": "Sample Hamlet",
                "price_range": "EUR 120-180",
                "price_min": 120,
                "price_max": 180,
                "quality": "standard",
                "latitude": 47.24,
                "longitude": 13.57,
                "elevation_m": 1250,
                "base_type": "hamlet",
            },
        ]
    )
    head["ski_areas"].extend(  # type: ignore[union-attr]
        [
            {
                "ski_area_id": "sample-local-area",
                "name": "Sample Local Area",
                "latitude": 47.26,
                "longitude": 13.56,
                "base_elevation_m": 1100,
                "summit_elevation_m": 2300,
                "season_start_month": 12,
                "season_end_month": 4,
                "total_piste_km": 42,
                "total_lift_count": 12,
                "supported_skill_levels": ["beginner", "intermediate"],
            },
            {
                "ski_area_id": "sample-linked-area",
                "name": "Sample Linked Area",
                "latitude": 47.28,
                "longitude": 13.6,
                "base_elevation_m": 1250,
                "summit_elevation_m": 2500,
                "season_start_month": 12,
                "season_end_month": 4,
                "total_piste_km": 55,
                "total_lift_count": 15,
                "supported_skill_levels": ["intermediate", "advanced"],
            },
        ]
    )
    if include_unrelated_entity:
        head["ski_regions"].append(  # type: ignore[union-attr]
            {
                "ski_region_id": "unrelated-region",
                "name": "Unrelated Region",
                "grouping_policy": "trip_market",
            }
        )
    head["ski_area_access"].extend(  # type: ignore[union-attr]
        [
            {
                "ski_area_access_id": "sample-village--sample-local-area",
                "stay_base_id": "sample-village",
                "ski_area_id": "sample-local-area",
                "access_mode": "walk",
                "lift_distance": "near",
                "nearest_lift_name": "Sample Gondola",
                "distance_m": 250,
                "duration_minutes": 4,
                "is_direct": True,
                "source_urls": [REGIONAL_SOURCE_URLS["access"]],
            },
            {
                "ski_area_access_id": "sample-village--sample-linked-area",
                "stay_base_id": "sample-village",
                "ski_area_id": "sample-linked-area",
                "access_mode": "ski_bus",
                "lift_distance": "medium",
                "nearest_lift_name": "Linked Area Gondola",
                "distance_m": 3200,
                "duration_minutes": 10,
                "is_direct": False,
                "source_urls": [REGIONAL_SOURCE_URLS["access"]],
            },
            {
                "ski_area_access_id": "sample-hamlet--sample-linked-area",
                "stay_base_id": "sample-hamlet",
                "ski_area_id": "sample-linked-area",
                "access_mode": "walk",
                "lift_distance": "near",
                "nearest_lift_name": "Hamlet Chairlift",
                "distance_m": 400,
                "duration_minutes": 6,
                "is_direct": True,
                "source_urls": [REGIONAL_SOURCE_URLS["access"]],
            },
        ]
    )
    head["lift_pass_products"].extend(  # type: ignore[union-attr]
        [
            {
                "lift_pass_product_id": "sample-local-pass",
                "name": "Sample Local Pass",
                "validity_scope": "single_ski_area",
                "available_from_stay_destination_ids": ["sample-valley"],
                "default_for_stay_destination_ids": ["sample-valley"],
                "valid_ski_area_ids": ["sample-local-area"],
                "terrain_domain_ids": [],
                "prices": [],
            },
            {
                "lift_pass_product_id": "sample-linked-pass",
                "name": "Sample Linked Pass",
                "validity_scope": "local_multi_area",
                "available_from_stay_destination_ids": ["sample-valley"],
                "default_for_stay_destination_ids": [],
                "valid_ski_area_ids": [
                    "sample-local-area",
                    "sample-linked-area",
                ],
                "terrain_domain_ids": [],
                "prices": [],
            },
        ]
    )
    CatalogSnapshot.model_validate(base)
    CatalogSnapshot.model_validate(head)
    return base, head


def _regional_report_payload(
    base_catalog: dict[str, object],
    head_catalog: dict[str, object],
    head_trust: dict[str, object],
    *,
    focus_destination_ids: list[str] | None = None,
) -> dict[str, object]:
    catalog = CatalogSnapshot.model_validate(head_catalog)
    added_keys = _catalog_key_set(head_catalog) - _catalog_key_set(base_catalog)
    targets: list[tuple[str, str, object]] = []
    scope_entities: list[tuple[str, str, str]] = []
    for section, id_field, kind in CATALOG_SECTIONS:
        for item in getattr(catalog, section):
            entity_id = getattr(item, id_field)
            if f"{kind}:{entity_id}" not in added_keys:
                continue
            targets.append((kind, entity_id, item.model_dump(mode="json")))
            if kind not in {"ski_region", "rental_display_fact"}:
                scope_entities.append(
                    (kind, entity_id, getattr(item, "name", entity_id))
                )
            trust = head_trust["entities"][section][entity_id]  # type: ignore[index]
            targets.append(("trust_manifest", f"{section}:{entity_id}", trust))

    changes: list[dict[str, object]] = []
    coverage: list[dict[str, object]] = []
    for target_type, target_id, payload in targets:
        for field_path in sorted(CANONICAL_FIELD_PATHS[target_type]):
            after = _nested(payload, field_path)
            status = "reviewed-no-change"
            if after is not None:
                changes.append(
                    {
                        "target_type": target_type,
                        "target_id": target_id,
                        "field_path": field_path,
                        "before": None,
                        "after": after,
                        "trust_status": "estimated",
                    }
                )
                status = "changed"
            coverage.append(
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "field_path": field_path,
                    "status": status,
                }
            )

    evidence = [
        {
            "evidence_id": "sample-destination",
            "boundary_target_ids": ["sample-valley"],
            "target_type": "stay_destination",
            "target_id": "sample-valley",
            "field_path": "stay_destination_id",
            "source_type": "official",
            "source_url": REGIONAL_SOURCE_URLS["destination"],
            "source_title": "Official Sample Valley accommodation directory",
            "source_value": "sample-valley",
            "evidence_summary": "Defines the complete independent stay market.",
        },
        {
            "evidence_id": "sample-ski-areas",
            "target_type": "ski_area",
            "target_id": "sample-local-area",
            "field_path": "ski_area_id",
            "source_type": "official",
            "source_url": REGIONAL_SOURCE_URLS["ski_area"],
            "source_title": "Official Sample Valley ski-area presentation",
            "source_value": ["sample-local-area", "sample-linked-area"],
            "evidence_summary": "Identifies both independently operated ski areas.",
            "normalization_note": (
                "The cited collection names both areas; this evidence row is "
                "attached to the local-area identity field."
            ),
        },
        {
            "evidence_id": "sample-access",
            "target_type": "ski_area_access",
            "target_id": "sample-village--sample-local-area",
            "field_path": "source_urls",
            "source_type": "official",
            "source_url": REGIONAL_SOURCE_URLS["access"],
            "source_title": "Official Sample Valley access guide",
            "source_value": [REGIONAL_SOURCE_URLS["access"]],
            "evidence_summary": "Supports the three base-to-area access edges.",
        },
        {
            "evidence_id": "sample-passes",
            "target_type": "lift_pass_product",
            "target_id": "sample-local-pass",
            "field_path": "lift_pass_product_id",
            "source_type": "official",
            "source_url": REGIONAL_SOURCE_URLS["pass"],
            "source_title": "Official Sample Valley tariff",
            "source_value": ["sample-local-pass", "sample-linked-pass"],
            "evidence_summary": "Separates the local and linked pass identities.",
            "normalization_note": (
                "The tariff lists both products; this evidence row is attached "
                "to the local-pass identity field."
            ),
        },
        {
            "evidence_id": "sample-followup",
            "target_type": "stay_destination",
            "target_id": "sample-valley",
            "field_path": "name",
            "source_type": "official",
            "source_url": REGIONAL_SOURCE_URLS["followup"],
            "source_title": "Official adjacent-market directory",
            "source_value": "Sample Valley",
            "evidence_summary": "Records one examined adjacent stay market.",
        },
    ]

    scope_assessments: list[dict[str, object]] = []
    for kind, entity_id, display_name in scope_entities:
        if kind == "stay_destination":
            signals = ["independent_stay_market"]
            evidence_refs = ["sample-destination"]
        elif kind == "stay_base":
            signals = ["distinct_access"]
            evidence_refs = ["sample-destination", "sample-access"]
        elif kind == "ski_area":
            signals = [
                "official_independent_identity",
                "separate_operator",
                "independent_weather_presentation",
                "full_local_pass",
            ]
            evidence_refs = ["sample-ski-areas", "sample-passes"]
        elif kind == "ski_area_access":
            signals = ["direct_access_relationship"]
            evidence_refs = ["sample-access"]
        elif kind == "lift_pass_product":
            signals = ["official_product_identity"]
            evidence_refs = ["sample-passes"]
        else:
            raise AssertionError(f"unexpected regional test entity kind: {kind}")
        assessment: dict[str, object] = {
            "candidate_id": entity_id,
            "candidate_name": display_name,
            "candidate_kind": kind,
            "disposition": "add_entity",
            "signals": signals,
            "evidence_refs": evidence_refs,
            "target_refs": [{"target_type": kind, "target_id": entity_id}],
            "rationale": "The bounded regional sources support this graph entity.",
            "graph_impact": "graph_blocking",
        }
        if kind == "ski_area":
            assessment["ski_area_boundary"] = {
                "parent_ski_area_id": None,
                "terrain_scope": "complete",
                "connectivity_to_parent": "not_applicable",
                "operational_scope": "independent",
                "weather_scope": "independent",
                "pass_scope": "full_local",
                "provider_consensus": "separate",
                "separation_value": "material",
                "evidence_refs": ["sample-ski-areas", "sample-passes"],
            }
        scope_assessments.append(assessment)
    scope_assessments.append(
        {
            "candidate_id": "sample-adjacent-market",
            "candidate_name": "Sample Adjacent Market",
            "candidate_kind": "stay_destination",
            "disposition": "deferred",
            "signals": ["independent_stay_market"],
            "evidence_refs": ["sample-followup"],
            "target_refs": [],
            "backlog_ref": REGIONAL_BACKLOG_REF,
            "rationale": "This additive market belongs in a later graph slice.",
            "graph_impact": "regional_followup",
        }
    )

    return {
        "report_schema_version": 3,
        "title": "Sample Valley regional catalog proposal",
        "summary": "Adds one coherent multi-entity destination graph slice.",
        "resulting_graph": {
            "focus_stay_destination_ids": focus_destination_ids
            if focus_destination_ids is not None
            else ["sample-valley"],
        },
        "reviewed_targets": [
            {"target_type": target_type, "target_id": target_id, "scope": "full"}
            for target_type, target_id, _ in targets
        ],
        "changes": changes,
        "field_coverage": coverage,
        "evidence": evidence,
        "entity_scope_assessments": scope_assessments,
        "review_evidence_envelope": [
            {
                "family_id": "sample-destination",
                "source_kind": "destination_booking",
                "source_urls": [REGIONAL_SOURCE_URLS["destination"]],
                "candidate_kinds": ["stay_destination", "stay_base"],
            },
            {
                "family_id": "sample-ski-areas",
                "source_kind": "ski_area_operator",
                "source_urls": [REGIONAL_SOURCE_URLS["ski_area"]],
                "candidate_kinds": ["ski_area"],
            },
            {
                "family_id": "sample-access",
                "source_kind": "access_transport",
                "source_urls": [REGIONAL_SOURCE_URLS["access"]],
                "candidate_kinds": ["ski_area_access"],
            },
            {
                "family_id": "sample-passes",
                "source_kind": "pass_tariff",
                "source_urls": [REGIONAL_SOURCE_URLS["pass"]],
                "candidate_kinds": ["lift_pass_product"],
            },
            {
                "family_id": "sample-followup",
                "source_kind": "destination_booking",
                "source_urls": [REGIONAL_SOURCE_URLS["followup"]],
                "candidate_kinds": ["stay_destination"],
            },
        ],
        "destination_boundary_assessments": [
            {
                "candidate_id": "sample-valley",
                "gates": [
                    {
                        "gate_name": gate_name,
                        "status": "pass",
                        "notes": "Official sources support the bounded stay market.",
                        "evidence_refs": ["sample-destination"],
                    }
                    for gate_name in (
                        "complete_stay_market_scope",
                        "independent_stay_market_ownership",
                        "material_destination_level_separation_value",
                    )
                ],
                "identity_signals": [
                    {
                        "signal_type": "official_stay_market_treatment",
                        "status": "pass",
                        "notes": "The destination owns its accommodation market.",
                        "evidence_refs": ["sample-destination"],
                    }
                ],
                "failure_route": None,
            }
        ],
        "boundary_decision_targets": ["sample-valley"],
        "ranking_impact_summary": (
            "Sample Valley becomes a rankable stay market with two bases, two "
            "ski-area weather owners, three access edges, and two pass choices."
        ),
        "unresolved_caveats": [
            "Both new ski-area weather identities require owner-run history "
            "backfill and climatology after deployment."
        ],
    }


def _make_regional_proposal_context(
    *,
    include_unrelated_entity: bool = False,
    focus_destination_ids: list[str] | None = None,
) -> RegionalProposalContext:
    base_catalog, head_catalog = _regional_catalog_pair(
        include_unrelated_entity=include_unrelated_entity,
    )
    base_trust = _trust_payload_for_catalog(base_catalog)
    head_trust = _trust_payload_for_catalog(head_catalog)
    for ski_area_id in ("sample-local-area", "sample-linked-area"):
        head_trust["entities"]["ski_areas"][ski_area_id]["notes"] = [  # type: ignore[index]
            f"{ski_area_id} is a new weather identity requiring owner-run "
            "history backfill and climatology."
        ]
    report = _regional_report_payload(
        base_catalog,
        head_catalog,
        head_trust,
        focus_destination_ids=focus_destination_ids,
    )
    catalog_targets = _catalog_key_set(head_catalog) - _catalog_key_set(base_catalog)
    report_targets = frozenset(
        f"{target['target_type']}:{target['target_id']}"
        for target in report["reviewed_targets"]  # type: ignore[union-attr]
    )
    changed_paths = frozenset(
        {CATALOG_PATH, TRUST_PATH, REGIONAL_REPORT_PATH, BACKLOG_PATH}
    )
    snapshot = _intent(
        changed_paths=changed_paths,
        catalog_targets=catalog_targets,
        report_targets=report_targets,
    )
    repository = FakeObjectRepository(
        base=SHA_A,
        head=SHA_B,
        snapshot=snapshot,
        texts={
            (SHA_A, CATALOG_PATH): json.dumps(base_catalog),
            (SHA_B, CATALOG_PATH): json.dumps(head_catalog),
            (SHA_A, TRUST_PATH): json.dumps(base_trust),
            (SHA_B, TRUST_PATH): json.dumps(head_trust),
            (SHA_B, REGIONAL_REPORT_PATH): json.dumps(report),
            (SHA_B, BACKLOG_PATH): (
                "# Product Backlog\n\n"
                "## Sample Valley Regional Completion\n\n"
                "Continue with the next coherent destination graph slice.\n"
            ),
        },
    )
    inventory = DiscoveryInventory(
        catalog_keys=_catalog_key_set(base_catalog),
        open_proposal_count=0,
        open_candidate_keys=frozenset(),
        has_unknown_proposal_identity=False,
        can_create_proposal=True,
    )
    return RegionalProposalContext(
        base=SHA_A,
        head=SHA_B,
        snapshot=snapshot,
        discovery_inventory=inventory,
        repository=repository,
    )


@pytest.fixture
def regional_proposal_context() -> RegionalProposalContext:
    return _make_regional_proposal_context()


def test_validate_proposal_accepts_one_coherent_regional_destination_slice(
    regional_proposal_context: RegionalProposalContext,
) -> None:
    result = validate_proposal(
        candidate_key=REGIONAL_CANDIDATE_KEY,
        candidate_origin="backlog",
        base=regional_proposal_context.base,
        head=regional_proposal_context.head,
        snapshot=regional_proposal_context.snapshot,
        discovery_inventory=regional_proposal_context.discovery_inventory,
        repository=regional_proposal_context.repository,  # type: ignore[arg-type]
    )

    assert result.candidate_key == REGIONAL_CANDIDATE_KEY
    assert result.validated_head == regional_proposal_context.head
    assert result.report_path == REGIONAL_REPORT_PATH
    assert result.resulting_graph_markdown is not None
    assert "Stay destination<br/>Sample Valley" in result.resulting_graph_markdown
    assert "Stay base<br/>Sample Village" in result.resulting_graph_markdown
    assert "Stay base<br/>Sample Hamlet" in result.resulting_graph_markdown
    assert "Ski area<br/>Sample Local Area" in result.resulting_graph_markdown
    assert "Ski area<br/>Sample Linked Area" in result.resulting_graph_markdown
    assert "Lift pass<br/>Sample Local Pass" in result.resulting_graph_markdown
    assert "Lift pass<br/>Sample Linked Pass" in result.resulting_graph_markdown


@pytest.mark.parametrize(
    "focus_destination_ids",
    [[], ["sample-valley", "example"], ["example"]],
)
def test_validate_backlog_destination_proposal_requires_one_matching_focus(
    focus_destination_ids: list[str],
) -> None:
    context = _make_regional_proposal_context(
        focus_destination_ids=focus_destination_ids,
    )

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=REGIONAL_CANDIDATE_KEY,
            candidate_origin="backlog",
            base=context.base,
            head=context.head,
            snapshot=context.snapshot,
            discovery_inventory=context.discovery_inventory,
            repository=context.repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.check is ErrorCheck.CURATION_RECONCILIATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def test_validate_backlog_destination_proposal_rejects_unrelated_addition() -> None:
    context = _make_regional_proposal_context(include_unrelated_entity=True)

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=REGIONAL_CANDIDATE_KEY,
            candidate_origin="backlog",
            base=context.base,
            head=context.head,
            snapshot=context.snapshot,
            discovery_inventory=context.discovery_inventory,
            repository=context.repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.check is ErrorCheck.CURATION_RECONCILIATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def test_validate_proposal_accepts_one_coherent_new_catalog_graph() -> None:
    repository, snapshot, inventory = _proposal_dependencies()

    result = validate_proposal(
        candidate_key=CANDIDATE_KEY,
        candidate_origin="external",
        base=SHA_A,
        head=SHA_B,
        snapshot=snapshot,
        discovery_inventory=inventory,
        repository=repository,  # type: ignore[arg-type]
    )

    assert isinstance(result, ProposalValidationResult)
    assert result.candidate_key == CANDIDATE_KEY
    assert result.candidate_origin == "external"
    assert result.validated_head == SHA_B
    assert result.resulting_graph_markdown is not None
    assert "## Resulting Graph" in result.resulting_graph_markdown
    assert "Stay destination<br/>Nendaz" in result.resulting_graph_markdown
    assert all("product-backlog" not in path for _, path in repository.show_calls)
    assert all("registry" not in path for _, path in repository.show_calls)


def test_validate_proposal_requires_resulting_graph_for_schema_three() -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    payload = json.loads(repository.texts[(SHA_B, REPORT_PATH)])
    payload.pop("resulting_graph")
    repository.texts[(SHA_B, REPORT_PATH)] = json.dumps(payload)

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.check is ErrorCheck.CURATION_RECONCILIATION


@pytest.mark.parametrize("missing", ["review_evidence_envelope", "graph_impact"])
def test_validate_proposal_rejects_incomplete_bounded_review_inventory(
    missing: Literal["review_evidence_envelope", "graph_impact"],
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    payload = json.loads(repository.texts[(SHA_B, REPORT_PATH)])
    if missing == "review_evidence_envelope":
        payload.pop(missing)
    else:
        payload["entity_scope_assessments"][0].pop(missing)
    repository.texts[(SHA_B, REPORT_PATH)] = json.dumps(payload)

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.check is ErrorCheck.CURATION_RECONCILIATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def test_validate_proposal_accepts_exact_head_regional_followup_anchor() -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    payload = json.loads(repository.texts[(SHA_B, REPORT_PATH)])
    payload["entity_scope_assessments"].append(
        {
            "candidate_id": "regional-followup",
            "candidate_name": "Regional followup",
            "candidate_kind": "stay_destination",
            "disposition": "deferred",
            "signals": ["independent_stay_market"],
            "evidence_refs": ["nendaz-identity"],
            "target_refs": [],
            "backlog_ref": "docs/product-backlog.md#regional-followup",
            "rationale": "A bounded regional followup remains necessary.",
            "graph_impact": "regional_followup",
        }
    )
    repository.texts[(SHA_B, REPORT_PATH)] = json.dumps(payload)
    repository.texts[(SHA_B, BACKLOG_PATH)] = (
        "# Product Backlog\n\n## Regional Followup\n"
    )

    result = validate_proposal(
        candidate_key=CANDIDATE_KEY,
        candidate_origin="external",
        base=SHA_A,
        head=SHA_B,
        snapshot=snapshot,
        discovery_inventory=inventory,
        repository=repository,  # type: ignore[arg-type]
    )

    assert result.validated_head == SHA_B
    assert (SHA_B, BACKLOG_PATH) in repository.show_calls


def test_validate_proposal_rejects_missing_regional_followup_anchor() -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    payload = json.loads(repository.texts[(SHA_B, REPORT_PATH)])
    payload["entity_scope_assessments"].append(
        {
            "candidate_id": "regional-followup",
            "candidate_name": "Regional followup",
            "candidate_kind": "stay_destination",
            "disposition": "deferred",
            "signals": ["independent_stay_market"],
            "evidence_refs": ["nendaz-identity"],
            "target_refs": [],
            "backlog_ref": "docs/product-backlog.md#regional-followup",
            "rationale": "A bounded regional followup remains necessary.",
            "graph_impact": "regional_followup",
        }
    )
    repository.texts[(SHA_B, REPORT_PATH)] = json.dumps(payload)
    repository.texts[(SHA_B, BACKLOG_PATH)] = "# Product Backlog\n\n## Another Region\n"

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.check is ErrorCheck.CURATION_RECONCILIATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def _rekey_catalog_pair() -> tuple[CatalogSnapshot, CatalogSnapshot]:
    base_payload = minimal_catalog_payload()
    head_payload = deepcopy(base_payload)
    replacement_id = "replacement"
    head_payload["stay_destinations"][0]["stay_destination_id"] = replacement_id
    head_payload["stay_bases"][0]["stay_destination_id"] = replacement_id
    head_payload["lift_pass_products"][0]["available_from_stay_destination_ids"] = [
        replacement_id
    ]
    head_payload["lift_pass_products"][0]["default_for_stay_destination_ids"] = [
        replacement_id
    ]
    return (
        CatalogSnapshot.model_validate(base_payload),
        CatalogSnapshot.model_validate(head_payload),
    )


def _decision_bearing_rekey_report() -> CatalogCurationReport:
    return CatalogCurationReport.model_validate(
        {
            "report_schema_version": 2,
            "title": "Example destination re-key proposal",
            "summary": "Proposes a reviewed existing-model identity replacement.",
            "reviewed_targets": [
                {
                    "target_type": "stay_destination",
                    "target_id": "example",
                    "scope": "full",
                }
            ],
            "changes": [
                {
                    "target_type": "stay_destination",
                    "target_id": "example",
                    "field_path": "stay_destination_id",
                    "before": "example",
                    "after": None,
                    "trust_status": "estimated",
                }
            ],
            "entity_scope_assessments": [
                {
                    "candidate_id": "example-rekey",
                    "candidate_name": "Example destination identity",
                    "candidate_kind": "stay_destination",
                    "disposition": "unresolved",
                    "signals": ["official_independent_identity"],
                    "evidence_refs": ["example-identity"],
                    "target_refs": [
                        {
                            "target_type": "stay_destination",
                            "target_id": "example",
                        }
                    ],
                    "backlog_ref": (
                        "docs/product-backlog.md#example-region-catalog-extension"
                    ),
                    "rationale": "Owner approval is required before replacement.",
                }
            ],
            "unresolved_caveats": [
                "Owner must approve the identity and historical-data migration."
            ],
        }
    )


def test_catalog_delta_accepts_explicit_decision_bearing_rekey() -> None:
    base, head = _rekey_catalog_pair()

    _validate_catalog_delta(
        "stay_destination:replacement",
        base,
        head,
        _decision_bearing_rekey_report(),
    )


def test_catalog_delta_rejects_rekey_without_unresolved_handoff() -> None:
    base, head = _rekey_catalog_pair()
    report = _decision_bearing_rekey_report().model_copy(
        update={"unresolved_caveats": []}
    )

    with pytest.raises(ValueError, match="catalog candidate delta is invalid"):
        _validate_catalog_delta(
            "stay_destination:replacement",
            base,
            head,
            report,
        )


def test_validate_proposal_rejects_oversized_object_before_read_or_materialize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    repository.reported_sizes[(SHA_A, CATALOG_PATH)] = 1_000_001
    materialized: list[Path] = []

    def record_materialization(path: Path, content: str) -> None:
        materialized.append(path)
        _write_private_object(path, content)

    monkeypatch.setattr(
        "ops.maintainer.validation._write_private_object",
        record_materialization,
    )

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )

    assert repository.bounded_calls == [(SHA_A, CATALOG_PATH, 1_000_000)]
    assert repository.show_calls == []
    assert materialized == []
    assert "oversized" not in json.dumps(exc_info.value.payload())


@pytest.mark.parametrize(
    ("optional_path", "candidate_origin"),
    [
        (BACKLOG_PATH, "backlog"),
        ("docs/catalog-discovery/nendaz.json", "external"),
    ],
)
def test_validate_proposal_allows_owned_semantic_documentation_without_reading_it(
    optional_path: str,
    candidate_origin: Literal["backlog", "external"],
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    expanded = _intent(changed_paths=snapshot.changed_paths | {optional_path})
    repository.snapshot = expanded

    result = validate_proposal(
        candidate_key=CANDIDATE_KEY,
        candidate_origin=candidate_origin,
        base=SHA_A,
        head=SHA_B,
        snapshot=expanded,
        discovery_inventory=inventory,
        repository=repository,  # type: ignore[arg-type]
    )

    assert result.validated_head == SHA_B
    assert repository.show_calls == [
        (SHA_A, CATALOG_PATH),
        (SHA_A, TRUST_PATH),
        (SHA_B, CATALOG_PATH),
        (SHA_B, TRUST_PATH),
        (SHA_B, REPORT_PATH),
    ]


@pytest.mark.parametrize(
    "extra_path",
    [
        "docs/catalog-discovery/alpine-coverage-registry.json",
        "docs/catalog-discovery/nendaz.md",
        "docs/catalog-discovery/nested/nendaz.json",
        "docs/catalog-curation/unrelated.json",
        "docs/catalog-curation/unrelated.md",
        "ops/maintainer/discovery.py",
    ],
)
def test_validate_proposal_rejects_retired_or_unowned_extra_paths(
    extra_path: str,
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    expanded = _intent(changed_paths=snapshot.changed_paths | {extra_path})
    repository.snapshot = expanded

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=expanded,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )

    assert exc_info.value.check is ErrorCheck.PREFLIGHT
    assert repository.show_calls == []


@pytest.mark.parametrize(
    "inventory_overrides",
    [
        {"catalog_keys": frozenset({CANDIDATE_KEY})},
        {"open_candidate_keys": frozenset({CANDIDATE_KEY})},
        {"open_proposal_count": 3},
        {"has_unknown_proposal_identity": True},
    ],
)
def test_validate_proposal_rejects_inventory_gates(
    inventory_overrides: dict[str, object],
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    values = inventory.model_dump()
    values.update(inventory_overrides)
    values["can_create_proposal"] = not (
        values["open_proposal_count"] >= 3 or values["has_unknown_proposal_identity"]
    )
    blocked = DiscoveryInventory.model_validate(values)

    with pytest.raises(MaintainerError):
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="backlog",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=blocked,
            repository=repository,  # type: ignore[arg-type]
        )


def _journal() -> PushJournal:
    return PushJournal(
        work_id="discovery-nendaz-village",
        worker="discovery",
        origin_run_id="1" * 32,
        recovery_run_id="2" * 32,
        branch="codex/discovery-nendaz-village",
        expected_remote_head=None,
        new_head=SHA_B,
        candidate_key=CANDIDATE_KEY,
        candidate_origin="external",
        phase=PushPhase.AUTHORIZED,
    )


def test_validate_proposal_rejects_unresolved_push_journal() -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    blocked = inspect_discovery(set(), (), (), {}, (_journal(),))

    with pytest.raises(MaintainerError):
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=blocked,
            repository=repository,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("missing_path", [CATALOG_PATH, TRUST_PATH, REPORT_PATH])
def test_validate_proposal_requires_catalog_trust_and_one_report(
    missing_path: str,
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    changed = snapshot.changed_paths - {missing_path}
    narrowed = _intent(changed_paths=frozenset(changed))
    repository.snapshot = narrowed

    with pytest.raises(MaintainerError):
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=narrowed,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )


def test_validate_proposal_rejects_candidate_already_in_base() -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    repository.texts[(SHA_A, CATALOG_PATH)] = repository.texts[(SHA_B, CATALOG_PATH)]

    with pytest.raises(MaintainerError):
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("mismatch", ["head", "snapshot"])
def test_validate_proposal_rejects_head_or_snapshot_mismatch(mismatch: str) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    if mismatch == "head":
        repository.current = SHA_C
    else:
        repository.verified_snapshot = _intent(
            catalog_targets=frozenset({"stay_base:other"})
        )

    with pytest.raises(MaintainerError):
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("failure", ["schema", "reconciliation", "policy"])
def test_validate_proposal_rejects_report_or_policy_failures(
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, snapshot, inventory = _proposal_dependencies()
    if failure == "schema":
        payload = json.loads(repository.texts[(SHA_B, REPORT_PATH)])
        payload["report_schema_version"] = 1
        repository.texts[(SHA_B, REPORT_PATH)] = json.dumps(payload)
    elif failure == "reconciliation":
        payload = json.loads(repository.texts[(SHA_B, REPORT_PATH)])
        payload["changes"][0]["after"] = "wrong-value"
        repository.texts[(SHA_B, REPORT_PATH)] = json.dumps(payload)
    else:
        monkeypatch.setattr(
            "ops.maintainer.validation.catalog_policy_issues",
            lambda catalog: [SimpleNamespace(severity="error", message="raw policy")],
        )

    with pytest.raises(MaintainerError) as exc_info:
        validate_proposal(
            candidate_key=CANDIDATE_KEY,
            candidate_origin="external",
            base=SHA_A,
            head=SHA_B,
            snapshot=snapshot,
            discovery_inventory=inventory,
            repository=repository,  # type: ignore[arg-type]
        )

    assert "raw policy" not in json.dumps(exc_info.value.payload())

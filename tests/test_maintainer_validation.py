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

from app.data.catalog_curation import CANONICAL_FIELD_PATHS
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import FIELD_GROUPS
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    MaintainerError,
)
from ops.maintainer.git_ops import GuardedSyncResult, RepositorySafetyError
from ops.maintainer.inspection import DiscoveryInventory
from ops.maintainer.intent import BACKLOG_PATH, IntentDiffEntry, IntentSnapshot
from ops.maintainer.models import PullRequest
from ops.maintainer.state import PushJournal, PushPhase
from ops.maintainer.validation import (
    _PROCESS_GROUP_GRACE_SECONDS,
    VALIDATION_COMMAND_TIMEOUT_SECONDS,
    ProposalValidationResult,
    ValidationResult,
    _SubprocessValidationRunner,
    _terminate_process_group,
    _write_private_object,
    validate_curation,
    validate_proposal,
)

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
REPORT_PATH = "docs/catalog-curation/nendaz-village.json"
CATALOG_PATH = "app/data/catalog.json"
TRUST_PATH = "app/data/resort_trust_manifest.json"
CANDIDATE_KEY = "stay_destination:nendaz"


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


class FakeLiveRepository:
    def __init__(self, root: Path, snapshot: IntentSnapshot) -> None:
        self.root = root
        self.snapshot = snapshot
        self.fail = False
        self.revalidate_calls = 0
        self.base_calls = 0

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
    assert commands[1][schema_flag + 1] == "2"
    assert "--skip-product-backlog-validation" in commands[1]
    assert "--product-backlog-path" not in commands[1]
    assert "tests/test_catalog_curation_backlog.py" not in commands[2]
    assert reviewed.revalidate_calls == 5
    assert base.base_calls == 5


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
        "report_schema_version": 2,
        "title": "Nendaz Village onboarding",
        "summary": "Adds a separately represented stay base.",
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
                        "independent_stay_context",
                        "independent_ski_access",
                        "independent_recommendation_value",
                    )
                ],
                "identity_signals": [
                    {
                        "signal_type": "official_destination_treatment",
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
    assert all("product-backlog" not in path for _, path in repository.show_calls)
    assert all("registry" not in path for _, path in repository.show_calls)


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
    blocked = DiscoveryInventory.model_validate(
        {
            **inventory.model_dump(),
            "can_create_proposal": False,
            "unresolved_pushes": (_journal(),),
        }
    )

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

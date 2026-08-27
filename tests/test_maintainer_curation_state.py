from __future__ import annotations

import json
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

import ops.maintainer.curation_state as curation_state
from ops.maintainer.curation_state import (
    CheckpointCompletedEvent,
    CheckpointStartedEvent,
    CurationCheckpointStage,
    CurationGeneration,
    CurationGenerationStore,
    CurationMigrationError,
    GenerationPreparedEvent,
    ValidationFailedEvent,
    ValidationPassedEvent,
    checkpoint_transaction_id,
    curation_state_migration_required,
    migrate_legacy_curation_state,
    project_generation,
)
from ops.maintainer.git_ops import GuardedSyncResult, LegacyCurationRef
from ops.maintainer.runtime import RunLease
from ops.maintainer.state import (
    ContinuationStatus,
    ContinuationValidationStatus,
    PushJournal,
    PushPhase,
    RemediationContinuation,
    RemediationContinuationStatus,
    ReviewedContinuation,
    WorkPhase,
    WorkState,
)

pytestmark = pytest.mark.db_free

NOW = datetime(2026, 8, 15, 10, tzinfo=UTC)
SHA_1 = "1" * 40
SHA_2 = "2" * 40
SHA_3 = "3" * 40
SHA_4 = "4" * 40
GENERATION_ID = "a" * 32
REPORT = "docs/catalog-curation/example.json"


@dataclass
class LegacyRefRepositoryStub:
    refs: tuple[LegacyCurationRef, ...] = ()
    archive_calls: int = 0

    def legacy_curation_refs(
        self,
        archive_id: str,
    ) -> tuple[LegacyCurationRef, ...]:
        del archive_id
        return self.refs

    def archive_legacy_curation_refs(
        self,
        refs: Sequence[LegacyCurationRef],
    ) -> int:
        assert tuple(refs) == self.refs
        self.archive_calls += 1
        return len(refs)


def _sync(*, base_head: str = SHA_4, rebased_head: str = SHA_2) -> GuardedSyncResult:
    return GuardedSyncResult(
        target_branch="codex/catalog-curation-example",
        original_head=SHA_1,
        rebased_head=rebased_head,
        backup_ref="refs/snowcast-maintainer/backups/pr-42/example",
        prepared_ref="refs/snowcast-maintainer/prepared/pr-42/example",
        base_head=base_head,
        merge_base=base_head,
    )


def _generation(
    *events: object,
    generation_number: int = 1,
    generation_id: str = GENERATION_ID,
    sync: GuardedSyncResult | None = None,
) -> CurationGeneration:
    selected_sync = sync or _sync()
    prepared = GenerationPreparedEvent(
        sequence=1,
        recorded_at=NOW,
        prepared_head=selected_sync.rebased_head,
    )
    return CurationGeneration(
        schema_version=2,
        work_id="curation-pr-42",
        pr_number=42,
        generation_number=generation_number,
        generation_id=generation_id,
        created_at=NOW,
        selected_head=SHA_1,
        target_branch=selected_sync.target_branch,
        sync=selected_sync,
        events=(prepared, *events),
    )


def _completed_checkpoint(
    *,
    sequence: int,
    stage: CurationCheckpointStage,
    head: str,
    recorded_at: datetime,
) -> tuple[CheckpointStartedEvent, CheckpointCompletedEvent]:
    transaction_id = checkpoint_transaction_id(
        GENERATION_ID,
        stage,
        head,
        REPORT,
        SHA_4,
    )
    started = CheckpointStartedEvent(
        sequence=sequence,
        recorded_at=recorded_at,
        transaction_id=transaction_id,
        stage=stage,
        head=head,
        report_path=REPORT,
        validation_base=SHA_4,
        expected_checkpoint_ref=(
            f"refs/snowcast-maintainer/curation/pr-42/{GENERATION_ID}/"
            f"{transaction_id}/checkpoint"
        ),
        expected_squash_ref=(
            f"refs/snowcast-maintainer/curation/pr-42/{GENERATION_ID}/"
            f"{transaction_id}/replay"
        ),
    )
    completed = CheckpointCompletedEvent(
        sequence=sequence + 1,
        recorded_at=recorded_at + timedelta(microseconds=1),
        transaction_id=transaction_id,
        checkpoint_ref=started.expected_checkpoint_ref,
        squash_ref=started.expected_squash_ref,
    )
    return started, completed


def _write_private_model(path: Path, model: object) -> bytes:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    raw = (
        json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    ).encode()
    path.write_bytes(raw)
    path.chmod(0o600)
    return raw


def _legacy_models() -> tuple[
    WorkState,
    WorkState,
    ReviewedContinuation,
    RemediationContinuation,
]:
    run_id = "9" * 32
    sync = _sync()
    curation_work = WorkState(
        work_id="curation-pr-42",
        worker="curation",
        run_id=run_id,
        phase=WorkPhase.SELECTED,
        updated_at=NOW,
        pr_number=42,
        selected_head=SHA_1,
    )
    discovery_work = WorkState(
        work_id="proposal-example",
        worker="discovery",
        run_id=run_id,
        phase=WorkPhase.SELECTED,
        updated_at=NOW,
        candidate_key="backlog:example",
        candidate_origin="backlog",
        selected_head=SHA_1,
    )
    reviewed = ReviewedContinuation(
        work_id="curation-pr-42",
        origin_run_id=run_id,
        recovery_run_id=run_id,
        updated_at=NOW,
        pr_number=42,
        selected_head=SHA_1,
        reviewed_head=SHA_2,
        report_path=REPORT,
        sync=sync,
        reviewed_ref="refs/snowcast-maintainer/reviewed/pr-42/example",
        squash_ref="refs/snowcast-maintainer/continuations/pr-42/example",
        status=ContinuationStatus.AVAILABLE,
        validation_status=ContinuationValidationStatus.NOT_RUN,
    )
    remediation = RemediationContinuation(
        work_id="curation-pr-42",
        origin_run_id=run_id,
        recovery_run_id=run_id,
        updated_at=NOW,
        pr_number=42,
        selected_head=SHA_1,
        remediation_head=SHA_2,
        report_path=REPORT,
        sync=sync,
        allowed_paths=frozenset(
            {
                "app/data/catalog.json",
                REPORT,
            }
        ),
        remediation_ref="refs/snowcast-maintainer/remediation/pr-42/example",
        squash_ref=("refs/snowcast-maintainer/remediation-continuations/pr-42/example"),
        completed_stage="delta-validated",
        status=RemediationContinuationStatus.AVAILABLE,
    )
    return curation_work, discovery_work, reviewed, remediation


def test_legacy_migration_archives_only_pre_push_curation_state_and_is_idempotent(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    curation_work, discovery_work, reviewed, remediation = _legacy_models()
    _write_private_model(state_dir / "work/curation-pr-42.json", curation_work)
    discovery_bytes = _write_private_model(
        state_dir / "work/proposal-example.json",
        discovery_work,
    )
    _write_private_model(
        state_dir / "continuations/curation-pr-42.json",
        reviewed,
    )
    _write_private_model(
        state_dir / "remediation-continuations/curation-pr-42.json",
        remediation,
    )
    published_push = PushJournal(
        work_id="curation-pr-99",
        worker="curation",
        origin_run_id="8" * 32,
        recovery_run_id="8" * 32,
        pr_number=99,
        branch="codex/catalog-curation-example",
        expected_remote_head=SHA_1,
        new_head=SHA_2,
        phase=PushPhase.PUBLISHED,
    )
    push_bytes = _write_private_model(
        state_dir / "push/curation-pr-99.json",
        published_push,
    )
    archive_id = "b" * 32
    source_ref = "refs/snowcast-maintainer/reviewed/pr-42/example"
    repository = LegacyRefRepositoryStub(
        refs=(
            LegacyCurationRef(
                source_ref=source_ref,
                archive_ref=(
                    "refs/snowcast-maintainer/archive/legacy-curation-v1/"
                    f"{archive_id}/reviewed/pr-42/example"
                ),
                head=SHA_2,
            ),
        )
    )

    first = migrate_legacy_curation_state(
        state_dir,
        repository,
        now=NOW,
        archive_id_factory=lambda: archive_id,
    )
    second = migrate_legacy_curation_state(
        state_dir,
        repository,
        now=NOW + timedelta(seconds=1),
        archive_id_factory=lambda: "c" * 32,
    )

    assert first.files_archived == 3
    assert first.refs_archived == 1
    assert first.already_migrated is False
    assert second.already_migrated is True
    assert second.archive_id == archive_id
    assert repository.archive_calls == 2
    assert not (state_dir / "work/curation-pr-42.json").exists()
    assert not (state_dir / "continuations/curation-pr-42.json").exists()
    assert not (state_dir / "remediation-continuations/curation-pr-42.json").exists()
    assert (state_dir / "work/proposal-example.json").read_bytes() == discovery_bytes
    assert (state_dir / "push/curation-pr-99.json").read_bytes() == push_bytes
    archive = state_dir / "legacy-curation-v1" / archive_id
    assert (archive / "manifest.json").is_file()
    assert (archive / "work/curation-pr-42.json").is_file()
    assert (state_dir / "curation-state-format.json").is_file()
    assert not (state_dir / "curation-state-migration.json").exists()


def test_legacy_migration_retry_rejects_tampered_completed_archive(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    curation_work, _, _, _ = _legacy_models()
    _write_private_model(state_dir / "work/curation-pr-42.json", curation_work)
    archive_id = "b" * 32
    repository = LegacyRefRepositoryStub()
    migrate_legacy_curation_state(
        state_dir,
        repository,
        now=NOW,
        archive_id_factory=lambda: archive_id,
    )
    archived_work = (
        state_dir / "legacy-curation-v1" / archive_id / "work/curation-pr-42.json"
    )
    archived_work.write_bytes(b"{}\n")

    with pytest.raises(CurationMigrationError, match="format-conflict"):
        migrate_legacy_curation_state(
            state_dir,
            repository,
            now=NOW + timedelta(seconds=1),
        )


def test_migration_required_detects_curation_work_without_continuation(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    curation_work, discovery_work, _, _ = _legacy_models()
    _write_private_model(state_dir / "work/proposal-example.json", discovery_work)

    assert curation_state_migration_required(state_dir) is False

    _write_private_model(state_dir / "work/curation-pr-42.json", curation_work)

    assert curation_state_migration_required(state_dir) is True


def test_legacy_migration_refuses_active_lease(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    lease = RunLease.acquire(state_dir, "curation", now=NOW)

    with pytest.raises(CurationMigrationError, match="active-lease"):
        migrate_legacy_curation_state(
            state_dir,
            LegacyRefRepositoryStub(),
            now=NOW,
        )

    lease.release()


def test_legacy_migration_refuses_rollback_after_generation_started(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    lease = RunLease.acquire(state_dir, "curation", now=NOW)
    CurationGenerationStore(state_dir).start_generation(_generation(), lease)
    lease.release()

    with pytest.raises(CurationMigrationError, match="format-conflict"):
        migrate_legacy_curation_state(
            state_dir,
            LegacyRefRepositoryStub(),
            now=NOW + timedelta(seconds=1),
        )


def test_legacy_migration_refuses_unresolved_push_without_changing_it(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    journal = PushJournal(
        work_id="curation-pr-42",
        worker="curation",
        origin_run_id="8" * 32,
        recovery_run_id="8" * 32,
        pr_number=42,
        branch="codex/catalog-curation-example",
        expected_remote_head=SHA_1,
        new_head=SHA_2,
        phase=PushPhase.AUTHORIZED,
    )
    journal_path = state_dir / "push/curation-pr-42.json"
    original = _write_private_model(journal_path, journal)

    with pytest.raises(CurationMigrationError, match="external-recovery"):
        migrate_legacy_curation_state(
            state_dir,
            LegacyRefRepositoryStub(),
            now=NOW,
        )

    assert journal_path.read_bytes() == original


def test_newer_delta_checkpoint_supersedes_reviewed_head_within_generation() -> None:
    first = _completed_checkpoint(
        sequence=2,
        stage=CurationCheckpointStage.REVIEWED,
        head=SHA_2,
        recorded_at=NOW + timedelta(seconds=1),
    )
    second = _completed_checkpoint(
        sequence=4,
        stage=CurationCheckpointStage.DELTA_VALIDATED,
        head=SHA_3,
        recorded_at=NOW + timedelta(seconds=2),
    )

    projection = project_generation(_generation(*first, *second))

    assert projection.latest_head == SHA_3
    assert projection.latest_stage is CurationCheckpointStage.DELTA_VALIDATED
    assert projection.reviewed_authority is None
    assert projection.checkpoint_authority is not None
    assert projection.checkpoint_authority.reviewed_head == SHA_3
    assert (
        projection.checkpoint_authority.stage is CurationCheckpointStage.DELTA_VALIDATED
    )
    assert projection.next_action is not None
    assert projection.next_action.recipe_id == "checkpoint_curation_reviewed"


def test_validation_projection_requires_latest_reviewed_checkpoint() -> None:
    checkpoint = _completed_checkpoint(
        sequence=2,
        stage=CurationCheckpointStage.REVIEWED,
        head=SHA_2,
        recorded_at=NOW + timedelta(seconds=1),
    )
    passed = ValidationPassedEvent(
        sequence=4,
        recorded_at=NOW + timedelta(seconds=2),
        head=SHA_2,
        report_path=REPORT,
        resulting_graph_markdown="## Resulting Graph\n\n- Example",
    )

    projection = project_generation(_generation(*checkpoint, passed))

    assert projection.latest_stage == "fully-validated"
    assert projection.reviewed_authority is not None
    assert projection.validated_authority is not None
    assert projection.validated_authority.validated_head == SHA_2
    assert projection.validated_authority.resulting_graph_markdown.endswith("- Example")


def test_failed_validation_requires_bounded_remediation() -> None:
    checkpoint = _completed_checkpoint(
        sequence=2,
        stage=CurationCheckpointStage.REVIEWED,
        head=SHA_2,
        recorded_at=NOW + timedelta(seconds=1),
    )
    failed = ValidationFailedEvent(
        sequence=4,
        recorded_at=NOW + timedelta(seconds=2),
        head=SHA_2,
        report_path=REPORT,
    )

    projection = project_generation(_generation(*checkpoint, failed))

    assert projection.latest_stage == "validation-failed"
    assert projection.reviewed_authority is not None
    assert projection.validated_authority is None
    assert projection.next_action is not None
    assert projection.next_action.recipe_id == "prepare_curation"
    assert projection.next_action.substitutions.head == SHA_2


def test_incomplete_checkpoint_projects_exact_retry_action() -> None:
    started, _completed = _completed_checkpoint(
        sequence=2,
        stage=CurationCheckpointStage.REVIEWED,
        head=SHA_2,
        recorded_at=NOW + timedelta(seconds=1),
    )

    projection = project_generation(_generation(started))

    assert projection.incomplete_transaction == started.transaction_id
    assert projection.next_action is not None
    assert projection.next_action.recipe_id == "checkpoint_curation_reviewed"
    assert projection.next_action.substitutions.generation_id == GENERATION_ID
    assert projection.next_action.substitutions.head == SHA_2


def test_generation_rejects_non_monotonic_or_mismatched_events() -> None:
    started, completed = _completed_checkpoint(
        sequence=2,
        stage=CurationCheckpointStage.REVIEWED,
        head=SHA_2,
        recorded_at=NOW + timedelta(seconds=1),
    )
    duplicate_sequence = completed.model_copy(update={"sequence": 2})
    wrong_transaction = completed.model_copy(update={"transaction_id": "b" * 64})

    with pytest.raises(ValidationError):
        _generation(started, duplicate_sequence)
    with pytest.raises(ValidationError):
        _generation(started, wrong_transaction)


def test_caller_created_descendant_requires_delta_checkpoint_recipe() -> None:
    substitutions = curation_state.CurationActionSubstitutions(
        pr=42,
        generation_id=GENERATION_ID,
        head=SHA_2,
        report=REPORT,
        validation_base=SHA_1,
    )

    with pytest.raises(ValidationError):
        curation_state.CurationNextAction(
            recipe_id=curation_state.CurationRecipeId.VALIDATE,
            substitutions=substitutions,
            caller_created_descendant_head=True,
        )


def test_generation_store_persists_private_ordered_generations(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = CurationGenerationStore(tmp_path)
    first = _generation()
    second = _generation(
        generation_number=2,
        generation_id="b" * 32,
        sync=_sync(base_head=SHA_3, rebased_head=SHA_4),
    )

    store.start_generation(first, lease)
    store.start_generation(second, lease)

    assert store.list_generations("curation-pr-42") == (first, second)
    assert store.load_current("curation-pr-42") == second
    work_dir = tmp_path / "curation-generations" / "curation-pr-42"
    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o600 for path in work_dir.iterdir()
    )


def test_generation_store_appends_events_atomically(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = CurationGenerationStore(tmp_path)
    generation = _generation()
    started, completed = _completed_checkpoint(
        sequence=2,
        stage=CurationCheckpointStage.DELTA_VALIDATED,
        head=SHA_2,
        recorded_at=NOW + timedelta(seconds=1),
    )
    store.start_generation(generation, lease)

    store.append_event("curation-pr-42", GENERATION_ID, started, lease)
    updated = store.append_event(
        "curation-pr-42",
        GENERATION_ID,
        completed,
        lease,
    )

    assert updated.events == (generation.events[0], started, completed)
    assert store.load_current("curation-pr-42") == updated


def test_generation_store_enforces_document_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = CurationGenerationStore(tmp_path)
    monkeypatch.setattr(curation_state, "_MAX_GENERATION_BYTES", 500)

    with pytest.raises(ValueError, match="size limit"):
        store.start_generation(_generation(), lease)

from __future__ import annotations

import stat
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
    GenerationPreparedEvent,
    ValidationFailedEvent,
    ValidationPassedEvent,
    checkpoint_transaction_id,
    project_generation,
)
from ops.maintainer.git_ops import GuardedSyncResult
from ops.maintainer.runtime import RunLease

pytestmark = pytest.mark.db_free

NOW = datetime(2026, 8, 15, 10, tzinfo=UTC)
SHA_1 = "1" * 40
SHA_2 = "2" * 40
SHA_3 = "3" * 40
SHA_4 = "4" * 40
GENERATION_ID = "a" * 32
REPORT = "docs/catalog-curation/example.json"


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


def test_failed_validation_remains_reviewed_and_retryable() -> None:
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

    assert projection.latest_stage is CurationCheckpointStage.REVIEWED
    assert projection.reviewed_authority is not None
    assert projection.validated_authority is None
    assert projection.next_action is not None
    assert projection.next_action.recipe_id == "validate_curation"


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

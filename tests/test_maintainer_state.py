from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread

import pytest
from pydantic import ValidationError

from ops.maintainer.git_ops import GuardedSyncResult
from ops.maintainer.runtime import LeaseOwnershipError, RunLease
from ops.maintainer.state import (
    ContinuationStatus,
    ContinuationValidationStatus,
    PushJournal,
    PushPhase,
    ReviewedContinuation,
    RunOutcome,
    StateStore,
    StateStoreError,
    WorkPhase,
    WorkState,
)

pytestmark = pytest.mark.db_free

NOW = datetime(2026, 7, 8, 10, tzinfo=UTC)
SHA_1 = "1" * 40
SHA_2 = "2" * 40
SHA_3 = "3" * 40
SHA_4 = "4" * 40


def _work_state(
    lease: RunLease,
    phase: WorkPhase = WorkPhase.SELECTED,
    *,
    work_id: str = "curation-pr-42",
    worker: str = "curation",
    updated_at: datetime = NOW,
    pr_number: int | None = 42,
    candidate_key: str | None = None,
    candidate_origin: str | None = None,
) -> WorkState:
    phase_index = list(WorkPhase).index(phase)
    backup_ref = (
        "refs/maintainer-backups/pr-42"
        if worker == "curation" and phase_index >= 1
        else None
    )
    sync = (
        GuardedSyncResult(
            target_branch="codex/catalog-curation-42",
            original_head=SHA_1,
            rebased_head=SHA_2,
            backup_ref=backup_ref,
            prepared_ref="refs/maintainer-prepared/pr-42",
            base_head=SHA_4,
            merge_base=SHA_4,
        )
        if worker == "curation" and phase_index >= 1 and backup_ref is not None
        else None
    )
    return WorkState(
        work_id=work_id,
        worker=worker,
        run_id=lease.run_id,
        phase=phase,
        updated_at=updated_at,
        pr_number=pr_number,
        candidate_key=candidate_key,
        candidate_origin=(
            candidate_origin or "backlog" if worker == "discovery" else None
        ),
        report_path=(
            "docs/catalog-curation/fr-les-arcs.json"
            if worker == "discovery" and phase_index >= 3
            else None
        ),
        selected_head=SHA_1,
        prepared_head=SHA_2 if phase_index >= 1 else None,
        reviewed_head=SHA_3 if phase_index >= 2 else None,
        validated_head=SHA_3 if phase_index >= 3 else None,
        backup_ref=backup_ref,
        sync=sync,
    )


def _journal(
    lease: RunLease,
    phase: PushPhase = PushPhase.AUTHORIZED,
    *,
    work_id: str = "curation-pr-42",
    worker: str = "curation",
    origin_run_id: str | None = None,
    recovery_run_id: str | None = None,
    pr_number: int | None = 42,
    expected_remote_head: str | None = SHA_1,
    candidate_key: str | None = None,
    candidate_origin: str | None = None,
    new_head: str = SHA_4,
) -> PushJournal:
    return PushJournal(
        work_id=work_id,
        worker=worker,
        origin_run_id=origin_run_id or lease.run_id,
        recovery_run_id=recovery_run_id or lease.run_id,
        pr_number=pr_number,
        branch="codex/catalog-curation-42",
        expected_remote_head=expected_remote_head,
        new_head=new_head,
        candidate_key=candidate_key,
        candidate_origin=candidate_origin,
        phase=phase,
    )


def _continuation(
    lease: RunLease,
    *,
    status: ContinuationStatus = ContinuationStatus.AVAILABLE,
    validation_status: ContinuationValidationStatus = (
        ContinuationValidationStatus.NOT_RUN
    ),
    updated_at: datetime = NOW,
) -> ReviewedContinuation:
    reviewed = _work_state(lease, WorkPhase.REVIEWED, updated_at=updated_at)
    assert reviewed.sync is not None
    return ReviewedContinuation(
        work_id=reviewed.work_id,
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=updated_at,
        pr_number=42,
        selected_head=SHA_1,
        reviewed_head=SHA_3,
        report_path="docs/catalog-curation/fr-les-arcs.json",
        sync=reviewed.sync,
        reviewed_ref=(
            f"refs/snowcast-maintainer/reviewed/pr-42/{SHA_1[:12]}-{SHA_3[:12]}"
        ),
        squash_ref=(
            f"refs/snowcast-maintainer/continuations/pr-42/{SHA_4[:12]}-{SHA_3[:12]}"
        ),
        status=status,
        validation_status=validation_status,
    )


def _write_model(
    path: Path,
    model: WorkState | PushJournal | ReviewedContinuation,
) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def test_reviewed_continuation_is_strict_and_requires_exact_facts() -> None:
    lease = RunLease("curation", "a" * 32, Path("/tmp/state"))
    continuation = _continuation(lease)

    with pytest.raises(ValidationError, match="frozen"):
        continuation.status = ContinuationStatus.CONSUMED
    with pytest.raises(ValidationError):
        ReviewedContinuation.model_validate(
            {**continuation.model_dump(), "unexpected": True}
        )
    with pytest.raises(ValidationError):
        ReviewedContinuation.model_validate(
            {**continuation.model_dump(), "reviewed_head": "ABC"}
        )
    with pytest.raises(ValidationError):
        ReviewedContinuation.model_validate(
            {**continuation.model_dump(), "pr_number": 43}
        )


def test_successor_adopts_available_continuation_and_fences_origin(
    tmp_path: Path,
) -> None:
    origin = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    continuation = _continuation(origin)
    store.save_continuation(continuation, origin)
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    adopted = store.adopt_continuation("curation-pr-42", successor)

    assert adopted.origin_run_id == origin.run_id
    assert adopted.recovery_run_id == successor.run_id
    assert adopted.updated_at > continuation.updated_at
    assert store.load_continuation("curation-pr-42") == adopted
    with pytest.raises(LeaseOwnershipError):
        store.save_continuation(continuation, origin)


def test_continuation_persistence_is_private_and_lists_only_active_records(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    active = _continuation(lease)
    store.save_continuation(active, lease)
    terminal = _continuation(
        lease,
        status=ContinuationStatus.CONSUMED,
        validation_status=ContinuationValidationStatus.PASSED,
        updated_at=NOW + timedelta(minutes=1),
    )
    _write_model(
        tmp_path / "continuations" / "curation-pr-99.json",
        terminal.model_copy(
            update={
                "work_id": "curation-pr-99",
                "pr_number": 99,
                "reviewed_ref": terminal.reviewed_ref.replace("pr-42", "pr-99"),
                "squash_ref": terminal.squash_ref.replace("pr-42", "pr-99"),
            }
        ),
    )

    assert store.list_continuations_for_inspection() == (active,)
    path = tmp_path / "continuations" / "curation-pr-42.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


def test_continuation_rejects_immutable_drift_and_illegal_transitions(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    continuation = _continuation(lease)
    store.save_continuation(continuation, lease)

    with pytest.raises(StateStoreError, match="immutable"):
        store.save_continuation(
            continuation.model_copy(
                update={
                    "reviewed_head": SHA_4,
                    "updated_at": NOW + timedelta(minutes=1),
                }
            ),
            lease,
        )
    store.save_continuation(
        continuation.model_copy(
            update={
                "status": ContinuationStatus.INVALIDATED,
                "updated_at": NOW + timedelta(minutes=1),
            }
        ),
        lease,
    )
    with pytest.raises(StateStoreError, match="transition"):
        store.save_continuation(
            continuation.model_copy(
                update={
                    "updated_at": NOW + timedelta(minutes=2),
                }
            ),
            lease,
        )


def _advance_work_to_validated(
    store: StateStore,
    lease: RunLease,
) -> None:
    store.begin_work(_work_state(lease), lease)
    for minute, phase in enumerate(
        (WorkPhase.PREPARED, WorkPhase.REVIEWED, WorkPhase.VALIDATED),
        start=1,
    ):
        store.save_work(
            _work_state(
                lease,
                phase,
                updated_at=NOW + timedelta(minutes=minute),
            ),
            lease,
        )


def _advance_work_to_pushed(
    store: StateStore,
    lease: RunLease,
) -> PushJournal:
    _advance_work_to_validated(store, lease)
    authorized = _journal(lease, new_head=SHA_3)
    store.save_push(authorized, lease)
    pushed_journal = authorized.model_copy(update={"phase": PushPhase.PUSHED})
    store.save_push(pushed_journal, lease)
    store.save_work(
        _work_state(
            lease,
            WorkPhase.PUSHED,
            updated_at=NOW + timedelta(minutes=4),
        ),
        lease,
    )
    return pushed_journal


def test_work_state_is_strict_frozen_and_requires_domain_identity() -> None:
    lease = RunLease(
        worker="curation",
        run_id="a" * 32,
        state_dir=Path("/tmp/state"),
    )
    state = _work_state(lease)

    with pytest.raises(ValidationError, match="frozen"):
        state.phase = WorkPhase.PREPARED
    with pytest.raises(ValidationError):
        WorkState.model_validate({**state.model_dump(), "unexpected": True})
    with pytest.raises(ValidationError):
        _work_state(lease, pr_number=None)
    with pytest.raises(ValidationError):
        _work_state(
            lease,
            work_id="discovery-les-arcs",
            worker="discovery",
            pr_number=None,
            candidate_key=None,
        )


@pytest.mark.parametrize(
    ("phase", "missing_field"),
    [
        (WorkPhase.PREPARED, "prepared_head"),
        (WorkPhase.REVIEWED, "reviewed_head"),
        (WorkPhase.VALIDATED, "validated_head"),
        (WorkPhase.PUSHED, "validated_head"),
        (WorkPhase.PUBLISHED, "validated_head"),
    ],
)
def test_work_state_requires_phase_facts(
    phase: WorkPhase,
    missing_field: str,
) -> None:
    lease = RunLease("curation", "a" * 32, Path("/tmp/state"))
    payload = _work_state(lease, phase).model_dump()
    payload[missing_field] = None

    with pytest.raises(ValidationError):
        WorkState.model_validate(payload)


def test_work_state_rejects_invalid_sha_naive_time_and_early_discovery_pr() -> None:
    lease = RunLease("discovery", "a" * 32, Path("/tmp/state"))
    selected = _work_state(
        lease,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        candidate_key="fr-les-arcs",
    )

    for update in (
        {"selected_head": "ABC"},
        {"updated_at": datetime(2026, 7, 8, 10)},
        {"pr_number": 43},
    ):
        with pytest.raises(ValidationError):
            WorkState.model_validate({**selected.model_dump(), **update})

    published = _work_state(
        lease,
        WorkPhase.PUBLISHED,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=43,
        candidate_key="fr-les-arcs",
    )
    assert published.pr_number == 43

    with pytest.raises(ValidationError):
        _work_state(
            lease,
            WorkPhase.PUBLISHED,
            work_id="discovery-les-arcs",
            worker="discovery",
            pr_number=None,
            candidate_key="fr-les-arcs",
        )


def test_curation_report_path_is_recorded_only_after_validation() -> None:
    lease = RunLease("curation", "a" * 32, Path("/tmp/state"))
    report_path = "docs/catalog-curation/nendaz.json"
    prepared = _work_state(lease, WorkPhase.PREPARED)
    validated = _work_state(lease, WorkPhase.VALIDATED)

    with pytest.raises(ValidationError):
        WorkState.model_validate({**prepared.model_dump(), "report_path": report_path})

    recorded = WorkState.model_validate(
        {**validated.model_dump(), "report_path": report_path}
    )
    assert recorded.report_path == report_path


def test_work_state_rejects_facts_from_a_future_phase() -> None:
    lease = RunLease("curation", "a" * 32, Path("/tmp/state"))
    selected = _work_state(lease)

    with pytest.raises(ValidationError):
        WorkState.model_validate({**selected.model_dump(), "prepared_head": SHA_2})


def test_state_store_persists_private_monotonic_work_state(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    selected = _work_state(lease)

    store.begin_work(selected, lease)
    prepared = _work_state(
        lease,
        WorkPhase.PREPARED,
        updated_at=NOW + timedelta(minutes=1),
    )
    store.save_work(prepared, lease)

    work_path = tmp_path / "work" / "curation-pr-42.json"
    assert store.load_work("curation-pr-42") == prepared
    assert work_path.stat().st_mode & 0o777 == 0o600
    assert work_path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(StateStoreError, match="phase"):
        store.save_work(
            _work_state(
                lease,
                WorkPhase.SELECTED,
                updated_at=NOW + timedelta(minutes=2),
            ),
            lease,
        )
    with pytest.raises(StateStoreError, match="updated_at"):
        store.save_work(
            _work_state(
                lease,
                WorkPhase.REVIEWED,
                updated_at=prepared.updated_at,
            ),
            lease,
        )


def test_state_store_requires_exact_current_lease(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    selected = _work_state(lease)
    forged = RunLease("curation", "f" * 32, tmp_path)

    with pytest.raises(LeaseOwnershipError):
        store.begin_work(selected, forged)

    store.begin_work(selected, lease)
    with pytest.raises(LeaseOwnershipError):
        store.save_work(
            _work_state(
                lease,
                WorkPhase.PREPARED,
                updated_at=NOW + timedelta(minutes=1),
            ),
            forged,
        )


def test_state_store_preserves_work_identity_across_phase_transitions(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(lease), lease)
    prepared = _work_state(
        lease,
        WorkPhase.PREPARED,
        updated_at=NOW + timedelta(minutes=1),
    )
    assert prepared.sync is not None
    changed_head = prepared.model_copy(
        update={
            "selected_head": SHA_4,
            "sync": prepared.sync.model_copy(update={"original_head": SHA_4}),
        }
    )

    with pytest.raises(StateStoreError, match="identity"):
        store.save_work(changed_head, lease)


@pytest.mark.parametrize("unsafe_kind", ["symlink", "malformed", "oversized"])
def test_state_store_rejects_unsafe_work_state(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(lease), lease)
    path = tmp_path / "work" / "curation-pr-42.json"
    if unsafe_kind == "symlink":
        replacement = tmp_path / "replacement-work.json"
        replacement.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        replacement.chmod(0o600)
        path.unlink()
        path.symlink_to(replacement)
    elif unsafe_kind == "malformed":
        path.write_text("not-json", encoding="utf-8")
    else:
        path.write_text("x" * 65537, encoding="utf-8")
    if unsafe_kind != "symlink":
        path.chmod(0o600)

    with pytest.raises(StateStoreError):
        store.load_work("curation-pr-42")


@pytest.mark.parametrize(
    "prior_phase",
    [
        WorkPhase.SELECTED,
        WorkPhase.PREPARED,
        WorkPhase.REVIEWED,
        WorkPhase.VALIDATED,
        WorkPhase.PUBLISHED,
    ],
)
def test_begin_work_restarts_inactive_prior_pre_push_or_terminal_state(
    tmp_path: Path,
    prior_phase: WorkPhase,
) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(old), old)
    prior = _work_state(old, prior_phase, updated_at=NOW + timedelta(minutes=1))
    _write_model(tmp_path / "work" / "curation-pr-42.json", prior)
    if prior_phase is WorkPhase.PUBLISHED:
        _write_model(
            tmp_path / "push" / "curation-pr-42.json",
            _journal(old, PushPhase.PUBLISHED),
        )
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )
    restarted = _work_state(
        successor,
        updated_at=NOW + timedelta(hours=7, minutes=1),
    )

    store.begin_work(restarted, successor)

    assert store.load_work("curation-pr-42") == restarted
    if prior_phase is WorkPhase.PUBLISHED:
        replacement = _journal(successor)
        store.save_push(replacement, successor)
        assert store.load_push("curation-pr-42") == replacement
    with pytest.raises(LeaseOwnershipError):
        store.save_work(
            _work_state(
                old,
                WorkPhase.PREPARED,
                updated_at=NOW + timedelta(hours=8),
            ),
            old,
        )


def test_begin_work_rejects_pushed_state_without_journal(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(old), old)
    _write_model(
        tmp_path / "work" / "curation-pr-42.json",
        _work_state(old, WorkPhase.PUSHED, updated_at=NOW + timedelta(minutes=1)),
    )
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="pushed"):
        store.begin_work(
            _work_state(successor, updated_at=NOW + timedelta(hours=7, minutes=1)),
            successor,
        )


def test_begin_work_recovers_published_journal_after_pushed_state_crash(
    tmp_path: Path,
) -> None:
    origin = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    pushed = _advance_work_to_pushed(store, origin)
    recovery = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )
    adopted = store.adopt_push("curation-pr-42", recovery, SHA_3)
    published = adopted.model_copy(update={"phase": PushPhase.PUBLISHED})
    store.save_push(published, recovery)
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=14),
    )
    restarted = _work_state(
        successor,
        updated_at=NOW + timedelta(hours=14, minutes=1),
    )

    store.begin_work(restarted, successor)

    assert pushed.recovery_run_id == origin.run_id
    assert published.recovery_run_id == recovery.run_id
    assert published.recovery_run_id != successor.run_id
    assert store.load_work("curation-pr-42") == restarted


@pytest.mark.parametrize(
    "mismatch",
    ["nonterminal", "work_id", "worker", "new_head"],
)
def test_begin_work_rejects_untrusted_journal_for_pushed_state(
    tmp_path: Path,
    mismatch: str,
) -> None:
    origin = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    pushed = _advance_work_to_pushed(store, origin)
    payload = pushed.model_copy(update={"phase": PushPhase.PUBLISHED}).model_dump()
    if mismatch == "nonterminal":
        payload["phase"] = PushPhase.PUSHED
    elif mismatch == "work_id":
        payload["work_id"] = "curation-pr-99"
    elif mismatch == "worker":
        payload.update(
            {
                "worker": "discovery",
                "pr_number": 99,
                "expected_remote_head": None,
                "candidate_key": "fr-les-arcs",
                "candidate_origin": "external",
            }
        )
    else:
        payload["new_head"] = SHA_4
    journal = PushJournal.model_validate(payload)
    _write_model(tmp_path / "push" / "curation-pr-42.json", journal)
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError):
        store.begin_work(
            _work_state(
                successor,
                updated_at=NOW + timedelta(hours=7, minutes=1),
            ),
            successor,
        )


def test_begin_work_rejects_any_unresolved_push_journal(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(old), old)
    successor = RunLease.acquire(
        tmp_path,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="unresolved"):
        store.begin_work(
            _work_state(
                successor,
                work_id="discovery-les-arcs",
                worker="discovery",
                updated_at=NOW + timedelta(hours=7),
                pr_number=None,
                candidate_key="fr-les-arcs",
            ),
            successor,
        )


def test_push_journal_is_strict_and_requires_recovery_facts() -> None:
    lease = RunLease("discovery", "a" * 32, Path("/tmp/state"))
    base = _journal(
        lease,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="fr-les-arcs",
        candidate_origin="backlog",
    )

    with pytest.raises(ValidationError):
        PushJournal.model_validate({**base.model_dump(), "branch": "main"})
    with pytest.raises(ValidationError):
        PushJournal.model_validate({**base.model_dump(), "candidate_origin": None})
    with pytest.raises(ValidationError):
        PushJournal.model_validate({**base.model_dump(), "new_head": "ABC"})
    with pytest.raises(ValidationError):
        PushJournal.model_validate(
            {**base.model_dump(), "phase": PushPhase.PR_CREATED, "pr_number": None}
        )
    with pytest.raises(ValidationError):
        _journal(lease, worker="curation", expected_remote_head=None)

    with pytest.raises(ValidationError):
        PushJournal.model_validate(
            {**base.model_dump(), "candidate_origin": "backlog:destinations"}
        )


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "codex/../escape",
        "codex//proposal",
        "codex/.hidden",
        "codex/proposal..backup",
        "codex/proposal.lock",
        "codex/foo//bar",
        "codex/foo/",
        "codex/foo/.bar",
        "codex/foo.",
        "codex/foo@{bar",
        "codex/foo bar",
        "codex/foo\\bar",
        "codex/-leading-dash",
        "codex/foo/-nested-dash",
    ],
)
def test_push_journal_requires_safe_codex_branch(branch: str) -> None:
    lease = RunLease("curation", "a" * 32, Path("/tmp/state"))
    payload = _journal(lease).model_dump()
    payload["branch"] = branch

    with pytest.raises(ValidationError):
        PushJournal.model_validate(payload)


def test_save_work_requires_matching_pushed_journal_for_pushed_phase(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    _advance_work_to_validated(store, lease)
    pushed_work = _work_state(
        lease,
        WorkPhase.PUSHED,
        updated_at=NOW + timedelta(minutes=4),
    )

    with pytest.raises(StateStoreError, match="push journal"):
        store.save_work(pushed_work, lease)

    authorized = _journal(lease, new_head=SHA_3)
    store.save_push(authorized, lease)
    with pytest.raises(StateStoreError, match="push journal"):
        store.save_work(pushed_work, lease)

    pushed_journal = authorized.model_copy(update={"phase": PushPhase.PUSHED})
    store.save_push(pushed_journal, lease)
    store.save_work(pushed_work, lease)

    assert store.load_work("curation-pr-42") == pushed_work


@pytest.mark.parametrize(
    "mismatch",
    ["work_id", "worker", "recovery_run_id", "new_head"],
)
def test_save_work_rejects_mismatched_pushed_journal(
    tmp_path: Path,
    mismatch: str,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    _advance_work_to_validated(store, lease)
    payload = _journal(
        lease,
        PushPhase.PUSHED,
        new_head=SHA_3,
    ).model_dump()
    if mismatch == "work_id":
        payload["work_id"] = "curation-pr-99"
    elif mismatch == "worker":
        payload.update(
            {
                "worker": "discovery",
                "pr_number": None,
                "expected_remote_head": None,
                "candidate_key": "fr-les-arcs",
                "candidate_origin": "backlog",
            }
        )
    elif mismatch == "recovery_run_id":
        payload["recovery_run_id"] = "f" * 32
    else:
        payload["new_head"] = SHA_4
    journal = PushJournal.model_validate(payload)
    _write_model(tmp_path / "push" / "curation-pr-42.json", journal)

    with pytest.raises(StateStoreError):
        store.save_work(
            _work_state(
                lease,
                WorkPhase.PUSHED,
                updated_at=NOW + timedelta(minutes=4),
            ),
            lease,
        )


def test_save_work_requires_published_journal_for_published_phase(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    _advance_work_to_validated(store, lease)
    pushed_journal = _journal(
        lease,
        PushPhase.PUSHED,
        new_head=SHA_3,
    )
    _write_model(tmp_path / "push" / "curation-pr-42.json", pushed_journal)
    store.save_work(
        _work_state(
            lease,
            WorkPhase.PUSHED,
            updated_at=NOW + timedelta(minutes=4),
        ),
        lease,
    )
    published_work = _work_state(
        lease,
        WorkPhase.PUBLISHED,
        updated_at=NOW + timedelta(minutes=5),
    )

    with pytest.raises(StateStoreError, match="published push journal"):
        store.save_work(published_work, lease)

    published_journal = pushed_journal.model_copy(update={"phase": PushPhase.PUBLISHED})
    store.save_push(published_journal, lease)
    store.save_work(published_work, lease)

    assert store.load_work("curation-pr-42") == published_work


def test_push_journal_progression_and_unresolved_inventory_are_deterministic(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "discovery", now=NOW)
    store = StateStore(tmp_path)
    authorized = _journal(
        lease,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="fr-les-arcs",
        candidate_origin="backlog",
    )
    second = _journal(
        lease,
        work_id="discovery-zermatt",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="ch-zermatt",
        candidate_origin="backlog",
    )
    store.save_push(authorized, lease)
    _write_model(tmp_path / "push" / "discovery-zermatt.json", second)

    assert tuple(item.work_id for item in store.list_unresolved_pushes()) == (
        "discovery-les-arcs",
        "discovery-zermatt",
    )
    pushed = authorized.model_copy(update={"phase": PushPhase.PUSHED})
    store.save_push(pushed, lease)
    created = PushJournal.model_validate(
        {**pushed.model_dump(), "phase": PushPhase.PR_CREATED, "pr_number": 43}
    )
    store.save_push(created, lease)
    published = created.model_copy(update={"phase": PushPhase.PUBLISHED})
    store.save_push(published, lease)

    assert store.load_push("discovery-les-arcs") == published
    assert tuple(item.work_id for item in store.list_unresolved_pushes()) == (
        "discovery-zermatt",
    )


@pytest.mark.parametrize("unsafe_kind", ["symlink", "malformed", "oversized"])
def test_state_store_rejects_unsafe_push_journal(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(lease), lease)
    path = tmp_path / "push" / "curation-pr-42.json"
    if unsafe_kind == "symlink":
        replacement = tmp_path / "replacement-push.json"
        replacement.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        replacement.chmod(0o600)
        path.unlink()
        path.symlink_to(replacement)
    elif unsafe_kind == "malformed":
        path.write_text("not-json", encoding="utf-8")
    else:
        path.write_text("x" * 65537, encoding="utf-8")
    if unsafe_kind != "symlink":
        path.chmod(0o600)

    with pytest.raises(StateStoreError):
        store.load_push("curation-pr-42")


@pytest.mark.parametrize("observed_remote", [SHA_1, SHA_4])
def test_adopt_push_accepts_old_or_new_remote_and_preserves_origin(
    tmp_path: Path,
    observed_remote: str,
) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    original = _journal(old)
    store.save_push(original, old)
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    adopted = store.adopt_push(
        "curation-pr-42",
        successor,
        observed_remote,
    )

    assert adopted.origin_run_id == old.run_id
    assert adopted.recovery_run_id == successor.run_id
    with pytest.raises(LeaseOwnershipError):
        store.save_push(original, old)


def test_adopt_create_only_discovery_journal_without_work_state(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "discovery", now=NOW)
    store = StateStore(tmp_path)
    journal = _journal(
        old,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="fr-les-arcs",
        candidate_origin="backlog",
    )
    store.save_push(journal, old)
    successor = RunLease.acquire(
        tmp_path,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    adopted = store.adopt_push("discovery-les-arcs", successor, None)

    assert adopted.candidate_key == "fr-les-arcs"
    assert adopted.candidate_origin == "backlog"
    assert adopted.origin_run_id == old.run_id
    assert adopted.recovery_run_id == successor.run_id
    assert store.load_work("discovery-les-arcs") is None


def test_adopt_push_fails_closed_for_same_run_wrong_remote_or_wrong_work(
    tmp_path: Path,
) -> None:
    lease = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(lease), lease)

    with pytest.raises(StateStoreError, match="successor"):
        store.adopt_push("curation-pr-42", lease, SHA_1)

    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )
    with pytest.raises(StateStoreError, match="work"):
        store.adopt_push("curation-pr-99", successor, SHA_1)
    with pytest.raises(StateStoreError, match="remote"):
        store.adopt_push("curation-pr-42", successor, SHA_2)


def test_adopt_push_fails_closed_for_mismatched_worker(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(old), old)
    other_worker = RunLease.acquire(
        tmp_path,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="worker"):
        store.adopt_push("curation-pr-42", other_worker, SHA_1)


def test_adopt_push_fails_closed_with_multiple_unresolved_journals(
    tmp_path: Path,
) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(old), old)
    _write_model(
        tmp_path / "push" / "curation-pr-43.json",
        _journal(old, work_id="curation-pr-43", pr_number=43),
    )
    successor = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="exactly one"):
        store.adopt_push("curation-pr-42", successor, SHA_1)


def test_lease_acquisition_precondition_is_atomic_with_stale_takeover(
    tmp_path: Path,
) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    journal = _journal(old)
    precondition_entered = Event()
    stale_save_started = Event()
    release_precondition = Event()
    successors: list[RunLease] = []
    save_errors: list[Exception] = []

    def precondition() -> None:
        precondition_entered.set()
        assert stale_save_started.wait(timeout=2)
        assert release_precondition.wait(timeout=2)

    def acquire_successor() -> None:
        successors.append(
            RunLease.acquire(
                tmp_path,
                "discovery",
                now=NOW + timedelta(hours=7),
                precondition=precondition,
            )
        )

    def save_from_stale_owner() -> None:
        stale_save_started.set()
        try:
            store.save_push(journal, old)
        except LeaseOwnershipError as error:
            save_errors.append(error)

    acquire_thread = Thread(target=acquire_successor)
    acquire_thread.start()
    assert precondition_entered.wait(timeout=2)
    save_thread = Thread(target=save_from_stale_owner)
    save_thread.start()
    assert stale_save_started.wait(timeout=2)
    release_precondition.set()
    acquire_thread.join(timeout=2)
    save_thread.join(timeout=2)

    assert not acquire_thread.is_alive()
    assert not save_thread.is_alive()
    assert len(successors) == 1
    assert len(save_errors) == 1
    assert isinstance(save_errors[0], LeaseOwnershipError)
    assert store.list_unresolved_pushes() == ()


def test_run_outcome_supports_bounded_prelease_noop_and_work_result() -> None:
    prelease = RunOutcome(
        worker="discovery",
        mutation_occurred=False,
        terminal_reason="no-candidate",
    )
    completed = RunOutcome(
        worker="curation",
        lease_run_id="a" * 32,
        work_id="curation-pr-42",
        pr_number=42,
        last_phase=WorkPhase.PUBLISHED,
        mutation_occurred=True,
        terminal_reason="ready",
    )

    assert prelease.lease_run_id is None
    assert completed.last_phase is WorkPhase.PUBLISHED
    with pytest.raises(ValidationError):
        RunOutcome(
            worker="discovery",
            mutation_occurred=False,
            terminal_reason="full command output\nsecret",
        )
    with pytest.raises(ValidationError):
        RunOutcome(
            worker="curation",
            mutation_occurred=True,
            terminal_reason="ready",
        )
    with pytest.raises(ValidationError):
        RunOutcome.model_validate({**prelease.model_dump(), "unexpected": True})

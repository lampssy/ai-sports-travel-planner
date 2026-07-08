from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from ops.maintainer.runtime import LeaseOwnershipError, SimpleRunLease
from ops.maintainer.state import (
    PushJournal,
    PushPhase,
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
    lease: SimpleRunLease,
    phase: WorkPhase = WorkPhase.SELECTED,
    *,
    work_id: str = "curation-pr-42",
    worker: str = "curation",
    updated_at: datetime = NOW,
    pr_number: int | None = 42,
    candidate_key: str | None = None,
) -> WorkState:
    phase_index = list(WorkPhase).index(phase)
    return WorkState(
        work_id=work_id,
        worker=worker,
        run_id=lease.run_id,
        phase=phase,
        updated_at=updated_at,
        pr_number=pr_number,
        candidate_key=candidate_key,
        selected_head=SHA_1,
        prepared_head=SHA_2 if phase_index >= 1 else None,
        reviewed_head=SHA_3 if phase_index >= 2 else None,
        validated_head=SHA_3 if phase_index >= 3 else None,
        backup_ref="refs/maintainer-backups/pr-42" if worker == "curation" else None,
    )


def _journal(
    lease: SimpleRunLease,
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
) -> PushJournal:
    return PushJournal(
        work_id=work_id,
        worker=worker,
        origin_run_id=origin_run_id or lease.run_id,
        recovery_run_id=recovery_run_id or lease.run_id,
        pr_number=pr_number,
        branch="codex/catalog-curation-42",
        expected_remote_head=expected_remote_head,
        new_head=SHA_4,
        candidate_key=candidate_key,
        candidate_origin=candidate_origin,
        phase=phase,
    )


def _write_model(path: Path, model: WorkState | PushJournal) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def test_work_state_is_strict_frozen_and_requires_domain_identity() -> None:
    lease = SimpleRunLease(
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
    lease = SimpleRunLease("curation", "a" * 32, Path("/tmp/state"))
    payload = _work_state(lease, phase).model_dump()
    payload[missing_field] = None

    with pytest.raises(ValidationError):
        WorkState.model_validate(payload)


def test_work_state_rejects_invalid_sha_naive_time_and_early_discovery_pr() -> None:
    lease = SimpleRunLease("discovery", "a" * 32, Path("/tmp/state"))
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


def test_work_state_rejects_facts_from_a_future_phase() -> None:
    lease = SimpleRunLease("curation", "a" * 32, Path("/tmp/state"))
    selected = _work_state(lease)

    with pytest.raises(ValidationError):
        WorkState.model_validate({**selected.model_dump(), "prepared_head": SHA_2})


def test_state_store_persists_private_monotonic_work_state(tmp_path: Path) -> None:
    lease = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
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
    lease = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    selected = _work_state(lease)
    forged = SimpleRunLease("curation", "f" * 32, tmp_path)

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
    lease = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(lease), lease)
    changed_head = _work_state(
        lease,
        WorkPhase.PREPARED,
        updated_at=NOW + timedelta(minutes=1),
    ).model_copy(update={"selected_head": SHA_4})

    with pytest.raises(StateStoreError, match="identity"):
        store.save_work(changed_head, lease)


@pytest.mark.parametrize("unsafe_kind", ["symlink", "malformed", "oversized"])
def test_state_store_rejects_unsafe_work_state(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    lease = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
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
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(old), old)
    prior = _work_state(old, prior_phase, updated_at=NOW + timedelta(minutes=1))
    _write_model(tmp_path / "work" / "curation-pr-42.json", prior)
    if prior_phase is WorkPhase.PUBLISHED:
        _write_model(
            tmp_path / "push" / "curation-pr-42.json",
            _journal(old, PushPhase.PUBLISHED),
        )
    successor = SimpleRunLease.acquire(
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
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.begin_work(_work_state(old), old)
    _write_model(
        tmp_path / "work" / "curation-pr-42.json",
        _work_state(old, WorkPhase.PUSHED, updated_at=NOW + timedelta(minutes=1)),
    )
    successor = SimpleRunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="pushed"):
        store.begin_work(
            _work_state(successor, updated_at=NOW + timedelta(hours=7, minutes=1)),
            successor,
        )


def test_begin_work_rejects_any_unresolved_push_journal(tmp_path: Path) -> None:
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(old), old)
    successor = SimpleRunLease.acquire(
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
    lease = SimpleRunLease("discovery", "a" * 32, Path("/tmp/state"))
    base = _journal(
        lease,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="fr-les-arcs",
        candidate_origin="backlog:destinations",
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


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "codex/../escape",
        "codex//proposal",
        "codex/.hidden",
        "codex/proposal..backup",
        "codex/proposal.lock",
    ],
)
def test_push_journal_requires_safe_codex_branch(branch: str) -> None:
    lease = SimpleRunLease("curation", "a" * 32, Path("/tmp/state"))
    payload = _journal(lease).model_dump()
    payload["branch"] = branch

    with pytest.raises(ValidationError):
        PushJournal.model_validate(payload)


def test_push_journal_progression_and_unresolved_inventory_are_deterministic(
    tmp_path: Path,
) -> None:
    lease = SimpleRunLease.acquire(tmp_path, "discovery", now=NOW)
    store = StateStore(tmp_path)
    authorized = _journal(
        lease,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="fr-les-arcs",
        candidate_origin="backlog:destinations",
    )
    second = _journal(
        lease,
        work_id="discovery-zermatt",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="ch-zermatt",
        candidate_origin="backlog:destinations",
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
    lease = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
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
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    original = _journal(old)
    store.save_push(original, old)
    successor = SimpleRunLease.acquire(
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
    old = SimpleRunLease.acquire(tmp_path, "discovery", now=NOW)
    store = StateStore(tmp_path)
    journal = _journal(
        old,
        work_id="discovery-les-arcs",
        worker="discovery",
        pr_number=None,
        expected_remote_head=None,
        candidate_key="fr-les-arcs",
        candidate_origin="backlog:destinations",
    )
    store.save_push(journal, old)
    successor = SimpleRunLease.acquire(
        tmp_path,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    adopted = store.adopt_push("discovery-les-arcs", successor, None)

    assert adopted.candidate_key == "fr-les-arcs"
    assert adopted.candidate_origin == "backlog:destinations"
    assert adopted.origin_run_id == old.run_id
    assert adopted.recovery_run_id == successor.run_id
    assert store.load_work("discovery-les-arcs") is None


def test_adopt_push_fails_closed_for_same_run_wrong_remote_or_wrong_work(
    tmp_path: Path,
) -> None:
    lease = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(lease), lease)

    with pytest.raises(StateStoreError, match="successor"):
        store.adopt_push("curation-pr-42", lease, SHA_1)

    successor = SimpleRunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )
    with pytest.raises(StateStoreError, match="work"):
        store.adopt_push("curation-pr-99", successor, SHA_1)
    with pytest.raises(StateStoreError, match="remote"):
        store.adopt_push("curation-pr-42", successor, SHA_2)


def test_adopt_push_fails_closed_for_mismatched_worker(tmp_path: Path) -> None:
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(old), old)
    other_worker = SimpleRunLease.acquire(
        tmp_path,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="worker"):
        store.adopt_push("curation-pr-42", other_worker, SHA_1)


def test_adopt_push_fails_closed_with_multiple_unresolved_journals(
    tmp_path: Path,
) -> None:
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    store = StateStore(tmp_path)
    store.save_push(_journal(old), old)
    _write_model(
        tmp_path / "push" / "curation-pr-43.json",
        _journal(old, work_id="curation-pr-43", pr_number=43),
    )
    successor = SimpleRunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(StateStoreError, match="exactly one"):
        store.adopt_push("curation-pr-42", successor, SHA_1)


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

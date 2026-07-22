from __future__ import annotations

import io
import json
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ops.maintainer.cli import main
from ops.maintainer.publication import (
    PublicationInputError,
    create_publication_text,
    read_publication_text,
)
from ops.maintainer.runtime import LeaseOwnershipError, RunLease, RunLeaseError

pytestmark = pytest.mark.db_free


def _private_state_dir(tmp_path: Path) -> Path:
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    os.chmod(state_dir, 0o700)
    return state_dir


def _lease(state_dir: Path, worker: str = "curation") -> RunLease:
    return RunLease.acquire(state_dir, worker)


def test_writer_uses_exact_mode_despite_a_restrictive_umask(tmp_path: Path) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    old_umask = os.umask(0o022)
    try:
        basename = create_publication_text(lease, kind="summary", payload=b"Safe")
    finally:
        os.umask(old_umask)

    assert stat.S_IMODE((state_dir / basename).stat().st_mode) == 0o600


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        ("body", b"x" * 65_537),
        ("summary", b"\xff"),
        ("title", b" \t"),
        ("title", b"line one\nline two"),
        ("title", b"x" * 257),
    ],
)
def test_writer_rejects_invalid_or_oversized_text(
    tmp_path: Path,
    kind: str,
    payload: bytes,
) -> None:
    state_dir = _private_state_dir(tmp_path)

    with pytest.raises(PublicationInputError):
        create_publication_text(_lease(state_dir), kind=kind, payload=payload)  # type: ignore[arg-type]

    assert not list(state_dir.glob("publication-input-*"))


def test_writer_rejects_missing_or_wrong_lease(tmp_path: Path) -> None:
    state_dir = _private_state_dir(tmp_path)
    owner = _lease(state_dir)
    wrong_worker = RunLease("discovery", owner.run_id, state_dir)

    with pytest.raises(LeaseOwnershipError):
        create_publication_text(wrong_worker, kind="body", payload=b"body")

    owner.release()
    with pytest.raises(RunLeaseError):
        create_publication_text(owner, kind="body", payload=b"body")


def test_writer_rejects_unsafe_state_directory(tmp_path: Path) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    os.chmod(state_dir, 0o755)

    with pytest.raises(PublicationInputError):
        create_publication_text(lease, kind="body", payload=b"body")


def test_writer_retries_collision_without_overwriting_existing_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    existing = state_dir / "publication-input-collision"
    existing.write_bytes(b"existing")
    os.chmod(existing, 0o600)
    generated = iter(("collision", "fresh"))
    monkeypatch.setattr(
        "ops.maintainer.publication.uuid4",
        lambda: SimpleNamespace(hex=next(generated)),
    )

    basename = create_publication_text(_lease(state_dir), kind="body", payload=b"new")

    assert basename == "publication-input-fresh"
    assert existing.read_bytes() == b"existing"
    assert (state_dir / basename).read_bytes() == b"new"


def test_writer_removes_a_partially_written_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    original_write = os.write
    calls = 0

    def partial_then_fail(descriptor: int, payload: bytes) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_write(descriptor, payload[:1])
        raise OSError("injected write failure")

    monkeypatch.setattr("ops.maintainer.publication.os.write", partial_then_fail)

    with pytest.raises(PublicationInputError):
        create_publication_text(_lease(state_dir), kind="body", payload=b"body")

    assert not list(state_dir.glob("publication-input-*"))


def test_writer_removes_input_when_ownership_is_lost_after_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    original_assert_owner = RunLease.assert_owner
    calls = 0

    def lose_ownership_after_write(current: RunLease) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise LeaseOwnershipError("injected ownership loss")
        original_assert_owner(current)

    monkeypatch.setattr(RunLease, "assert_owner", lose_ownership_after_write)

    with pytest.raises(LeaseOwnershipError):
        create_publication_text(lease, kind="body", payload=b"body")

    assert calls == 2
    assert not list(state_dir.glob("publication-input-*"))


def test_cli_creates_a_writer_owned_input_without_disclosing_stdin(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    secret = "private body must not appear in output"
    monkeypatch.setattr(
        sys, "stdin", SimpleNamespace(buffer=io.BytesIO(secret.encode()))
    )

    code = main(
        [
            "--state-dir",
            str(state_dir),
            "publication-input",
            "create",
            "--worker",
            "curation",
            "--kind",
            "body",
            "--run-id",
            lease.run_id,
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert secret not in json.dumps(payload)
    assert set(payload) == {"basename", "outcome", "status"}
    basename = payload["basename"]
    assert isinstance(basename, str)
    assert stat.S_IMODE((state_dir / basename).stat().st_mode) == 0o600
    assert read_publication_text(state_dir, basename, kind="body") == secret


@pytest.mark.parametrize(
    ("kind", "payload", "undisclosed"),
    [
        ("body", b"oversized-bound-marker" + b"x" * 65_515, "oversized-bound-marker"),
        ("body", b"\xffinvalid-utf8-marker", "invalid-utf8-marker"),
        ("title", b" \t ", " \t "),
        ("title", b"multiline-title-marker\nsecond-line", "multiline-title-marker"),
    ],
)
def test_cli_rejects_invalid_stdin_without_creating_or_disclosing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    payload: bytes,
    undisclosed: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(payload)))

    code = main(
        [
            "--state-dir",
            str(state_dir),
            "publication-input",
            "create",
            "--worker",
            "curation",
            "--kind",
            kind,
            "--run-id",
            lease.run_id,
        ]
    )
    output = capsys.readouterr().out
    result = json.loads(output)

    assert len(payload) == 65_537 or kind == "title" or payload.startswith(b"\xff")
    assert code == 2
    assert result["reason"] == "publication-input-invalid"
    assert undisclosed not in output
    assert not list(state_dir.glob("publication-input-*"))


@pytest.mark.parametrize(
    ("worker", "release_first"),
    [("discovery", False), ("curation", True)],
)
def test_cli_rejects_wrong_or_missing_lease_before_writing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    worker: str,
    release_first: bool,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    if release_first:
        lease.release()
    secret = "must not be written"
    monkeypatch.setattr(
        sys, "stdin", SimpleNamespace(buffer=io.BytesIO(secret.encode()))
    )

    code = main(
        [
            "--state-dir",
            str(state_dir),
            "publication-input",
            "create",
            "--worker",
            worker,
            "--kind",
            "body",
            "--run-id",
            lease.run_id,
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["reason"] == "lease-ownership-error"
    assert secret not in json.dumps(payload)
    assert not list(state_dir.glob("publication-input-*"))


def test_cli_rejects_an_unsafe_state_directory_before_writing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = _lease(state_dir)
    os.chmod(state_dir, 0o755)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b"body")))

    code = main(
        [
            "--state-dir",
            str(state_dir),
            "publication-input",
            "create",
            "--worker",
            "curation",
            "--kind",
            "body",
            "--run-id",
            lease.run_id,
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert not list(state_dir.glob("publication-input-*"))

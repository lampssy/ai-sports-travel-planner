from __future__ import annotations

import json

import pytest

from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    ErrorStage,
    MaintainerError,
    error_payload,
    validate_safe_detail,
)

pytestmark = pytest.mark.db_free


def test_maintainer_error_emits_only_allowlisted_fields() -> None:
    error = MaintainerError(
        reason=ErrorReason.STALE_HEAD,
        stage=ErrorStage.PRE_PUSH,
        check=ErrorCheck.REMOTE_HEAD,
        kind=ErrorKind.MISMATCH,
        detail="PR head changed after review",
    )

    assert error.payload() == {
        "status": "error",
        "reason": "stale-head",
        "stage": "pre-push",
        "check": "remote-head",
        "kind": "mismatch",
        "detail": "PR head changed after review",
    }
    assert error_payload(error) == error.payload()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reason", "stale-head"),
        ("stage", "pre-push"),
        ("check", "remote-head"),
        ("kind", "mismatch"),
    ],
)
def test_maintainer_error_requires_enum_instances(field: str, value: str) -> None:
    values: dict[str, object] = {
        "reason": ErrorReason.STALE_HEAD,
        "stage": ErrorStage.PRE_PUSH,
        "check": ErrorCheck.REMOTE_HEAD,
        "kind": ErrorKind.MISMATCH,
    }
    values[field] = value

    with pytest.raises(TypeError, match=f"{field} must be"):
        MaintainerError(**values)  # type: ignore[arg-type]


def test_maintainer_error_allows_optional_diagnostic_fields_to_be_absent() -> None:
    error = MaintainerError(
        reason=ErrorReason.LOCK_BUSY,
        stage=ErrorStage.LOCK,
    )

    assert error.payload() == {
        "status": "error",
        "reason": "lock-busy",
        "stage": "lock",
    }


@pytest.mark.parametrize(
    "detail",
    [
        "",
        "x" * 161,
        "validation failed\nsecret output",
        "validation failed\tsecret output",
        "See https://example.com/private",
        "Fetch ssh://git@example.com/repository",
        "Read file:/Users/owner/private.txt",
        "See www.example.com/private",
        "See example.com/private",
        "See 127.0.0.1/private",
        "See 10.0.0.1:8080/private",
        "/tmp/private-output.txt",
        "Failed at /Users/owner/project/log.txt",
        "Read ~/private-output.txt",
        "failed at ./docs/private",
        "failed at ../private",
        "failed at docs/private.txt",
        r"failed at docs\private.txt",
        r"Failed at C:\Users\owner\private-output.txt",
        "TOKEN=ghp_not-a-real-token",
        "password: not-a-real-password",
        "client_secret = not-a-real-secret",
        "AWS_SECRET_ACCESS_KEY=not-a-real-key",
        "Authorization: Bearer not-a-real-token",
    ],
)
def test_safe_detail_rejects_untrusted_or_sensitive_text(detail: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_safe_detail(detail)

    if detail:
        assert detail not in str(exc_info.value)


def test_safe_detail_accepts_short_repository_authored_diagnostics() -> None:
    details = (
        "Catalog validation command failed",
        "PR head changed after review",
        "Remote head does not match reviewed head",
        "Candidate destination:tignes is already proposed",
        "PR:42 head changed",
        "prepare/push transition failed",
        "See example.com",
    )

    assert tuple(validate_safe_detail(detail) for detail in details) == details


@pytest.mark.parametrize(
    "untrusted_exception",
    [
        RuntimeError("stdout: validation failed\nstderr: database dump"),
        RuntimeError("OPENAI_API_KEY=not-a-real-environment-value"),
        RuntimeError("PR says: visit https://example.com/private-source"),
        RuntimeError("source text is in /Users/owner/private-catalog.json"),
        RuntimeError("password=not-a-real-password"),
    ],
)
def test_unexpected_exceptions_never_emit_raw_content(
    untrusted_exception: BaseException,
) -> None:
    payload = error_payload(untrusted_exception)

    assert payload == {
        "status": "error",
        "reason": "internal-error",
        "stage": "dispatch",
    }
    serialized = json.dumps(payload)
    assert str(untrusted_exception) not in serialized


def test_error_enums_cover_the_accepted_contract() -> None:
    assert {reason.value for reason in ErrorReason} == {
        "invalid-command",
        "invalid-github-state",
        "authentication-failed",
        "lock-busy",
        "lease-ownership-error",
        "stale-head",
        "rebase-conflict",
        "intent-drift",
        "validation-failed",
        "validation-required",
        "proposal-cap",
        "duplicate-proposal",
        "proposal-approval-required",
        "not-ready",
        "push-rejected",
        "transport-failed",
        "publication-input-invalid",
        "internal-error",
    }
    assert {stage.value for stage in ErrorStage} == {
        "dispatch",
        "inspect",
        "lock",
        "prepare",
        "validate",
        "pre-push",
        "push",
        "proposal-create",
        "publish",
        "readiness",
    }
    assert {check.value for check in ErrorCheck} == {
        "preflight",
        "catalog-validation",
        "curation-reconciliation",
        "catalog-tests",
        "post-validation",
        "remote-head",
        "publication-input",
    }
    assert {kind.value for kind in ErrorKind} == {
        "mismatch",
        "command-failed",
        "timeout",
        "transport",
        "invalid-file",
    }

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from ops.maintainer.curation_state import (
    CurationNextAction,
    CurationValidationDiagnostic,
)


class ErrorReason(StrEnum):
    INVALID_COMMAND = "invalid-command"
    INVALID_GITHUB_STATE = "invalid-github-state"
    AUTHENTICATION_FAILED = "authentication-failed"
    LOCK_BUSY = "lock-busy"
    LEASE_OWNERSHIP = "lease-ownership-error"
    STALE_HEAD = "stale-head"
    REBASE_CONFLICT = "rebase-conflict"
    INTENT_DRIFT = "intent-drift"
    CONTINUATION_REQUIRED = "continuation-required"
    STALE_BASE = "stale-base"
    LEASE_CONFLICT = "lease-conflict"
    CHECKPOINT_CONFLICT = "checkpoint-conflict"
    LOCAL_RECOVERY_REQUIRED = "local-recovery-required"
    UNSAFE_REPOSITORY = "unsafe-repository"
    STATE_MIGRATION_REQUIRED = "state-migration-required"
    VALIDATION_FAILED = "validation-failed"
    VALIDATION_REQUIRED = "validation-required"
    PROPOSAL_CAP = "proposal-cap"
    DUPLICATE_PROPOSAL = "duplicate-proposal"
    PROPOSAL_APPROVAL_REQUIRED = "proposal-approval-required"
    NOT_READY = "not-ready"
    PUSH_REJECTED = "push-rejected"
    TRANSPORT_FAILED = "transport-failed"
    PUBLICATION_INPUT = "publication-input-invalid"
    INTERNAL_ERROR = "internal-error"


class ErrorStage(StrEnum):
    DISPATCH = "dispatch"
    INSPECT = "inspect"
    LOCK = "lock"
    PREPARE = "prepare"
    VALIDATE = "validate"
    PRE_PUSH = "pre-push"
    PUSH = "push"
    PROPOSAL_CREATE = "proposal-create"
    PUBLISH = "publish"
    READINESS = "readiness"


class ErrorCheck(StrEnum):
    PREFLIGHT = "preflight"
    CATALOG_VALIDATION = "catalog-validation"
    CURATION_RECONCILIATION = "curation-reconciliation"
    CATALOG_TESTS = "catalog-tests"
    POST_VALIDATION = "post-validation"
    REMOTE_HEAD = "remote-head"
    PUBLICATION_INPUT = "publication-input"


class ErrorKind(StrEnum):
    MISMATCH = "mismatch"
    COMMAND_FAILED = "command-failed"
    TIMEOUT = "timeout"
    TRANSPORT = "transport"
    INVALID_FILE = "invalid-file"
    NOT_BASENAME = "not-basename"


_URL_OR_SCHEME_PATTERN = re.compile(
    r"(?:\b(?:https?|ssh|file|git|ftps?|s3a?|s3n|gs|gcs|az|azure|abfs|abfss|"
    r"oci|oss|swift):[^\s]+|"
    r"\b[a-z][a-z0-9+.-]*://[^\s]+|"
    r"\bwww\.[^\s]+)",
    re.IGNORECASE,
)
_NETWORK_LOCATION_PATTERN = re.compile(
    r"(?<![a-z0-9_-])(?:"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}|"
    r"(?:\d{1,3}\.){3}\d{1,3}|"
    r"localhost"
    r")(?:(?::\d{1,5})(?:[/?#][^\s]*)?|[/?#][^\s]+)(?![a-z0-9_-])",
    re.IGNORECASE,
)
_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?<![a-z0-9_])(?:/|~(?:[^/\s]*)?/|[a-z]:[\\/])",
    re.IGNORECASE,
)
_RELATIVE_PATH_PATTERN = re.compile(
    r"(?<![a-z0-9_.-])(?:"
    r"\.\.?[\\/][^\s]+|"
    r"[a-z0-9_.-]+(?:\\[a-z0-9_.-]+)+|"
    r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*/[a-z0-9_.-]+\.[a-z0-9]+"
    r")(?![a-z0-9_.-])",
    re.IGNORECASE,
)
_CREDENTIAL_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:[a-z0-9]+[_-])*"
    r"(?:api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret|"
    r"authorization|auth|credential|passphrase|password|passwd|pwd|secret|token)"
    r"(?:[_-][a-z0-9]+)*\s*[:=]",
    re.IGNORECASE,
)


def validate_safe_detail(detail: str) -> str:
    if type(detail) is not str or not detail.strip() or len(detail) > 160:
        raise ValueError("safe detail must contain 1-160 characters")
    if any(unicodedata.category(character) == "Cc" for character in detail):
        raise ValueError("safe detail contains a control character")
    if _URL_OR_SCHEME_PATTERN.search(detail):
        raise ValueError("safe detail contains a URL or scheme")
    if _NETWORK_LOCATION_PATTERN.search(detail):
        raise ValueError("safe detail contains a network location")
    if _ABSOLUTE_PATH_PATTERN.search(detail):
        raise ValueError("safe detail contains an absolute or home path")
    if _RELATIVE_PATH_PATTERN.search(detail):
        raise ValueError("safe detail contains a repository-relative path")
    if _CREDENTIAL_ASSIGNMENT_PATTERN.search(detail):
        raise ValueError("safe detail contains a credential-like assignment")
    return detail


@dataclass(frozen=True)
class MaintainerError(Exception):
    reason: ErrorReason
    stage: ErrorStage
    check: ErrorCheck | None = None
    kind: ErrorKind | None = None
    detail: str | None = None
    retryable: bool = False
    next_action: CurationNextAction | None = None
    diagnostic: CurationValidationDiagnostic | None = None

    def __post_init__(self) -> None:
        _require_enum("reason", self.reason, ErrorReason)
        _require_enum("stage", self.stage, ErrorStage)
        _require_optional_enum("check", self.check, ErrorCheck)
        _require_optional_enum("kind", self.kind, ErrorKind)
        if type(self.retryable) is not bool:
            raise TypeError("retryable must be a bool")
        if self.next_action is not None and not isinstance(
            self.next_action,
            CurationNextAction,
        ):
            raise TypeError("next_action must be a CurationNextAction instance")
        if self.next_action is not None and not self.retryable:
            raise ValueError("next_action requires a retryable error")
        if self.diagnostic is not None:
            if not isinstance(self.diagnostic, CurationValidationDiagnostic):
                raise TypeError(
                    "diagnostic must be a CurationValidationDiagnostic instance"
                )
            if (
                self.reason is not ErrorReason.VALIDATION_FAILED
                or self.stage is not ErrorStage.VALIDATE
                or self.check is not ErrorCheck.CATALOG_TESTS
                or self.kind is not ErrorKind.COMMAND_FAILED
            ):
                raise ValueError(
                    "diagnostic is limited to catalog test validation failures"
                )
        if self.detail is not None:
            validate_safe_detail(self.detail)
        Exception.__init__(self, self.reason.value, self.stage.value)

    def payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": "error",
            "reason": self.reason.value,
            "stage": self.stage.value,
        }
        if self.check is not None:
            payload["check"] = self.check.value
        if self.kind is not None:
            payload["kind"] = self.kind.value
        if self.detail is not None:
            payload["detail"] = self.detail
        if self.retryable:
            payload["retryable"] = True
        if self.next_action is not None:
            payload["next_action"] = self.next_action.model_dump(
                mode="json",
                exclude_none=True,
            )
        if self.diagnostic is not None:
            payload["diagnostic"] = self.diagnostic.model_dump(mode="json")
        return payload


def error_payload(error: BaseException) -> dict[str, object]:
    if isinstance(error, MaintainerError):
        return error.payload()
    return {
        "status": "error",
        "reason": ErrorReason.INTERNAL_ERROR.value,
        "stage": ErrorStage.DISPATCH.value,
    }


def _require_enum(name: str, value: object, expected: type[StrEnum]) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"{name} must be a {expected.__name__} instance")


def _require_optional_enum(
    name: str,
    value: object | None,
    expected: type[StrEnum],
) -> None:
    if value is not None:
        _require_enum(name, value, expected)

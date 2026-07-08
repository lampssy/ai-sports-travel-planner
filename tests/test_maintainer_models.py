from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ops.maintainer import (
    BODY_END,
    BODY_START,
    DEFAULT_BASE_BRANCH,
    LABEL_DEFINITIONS,
    REPOSITORY,
    REPOSITORY_SSH_URL,
    SUMMARY_MARKER,
)
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)

pytestmark = pytest.mark.db_free


def _pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Tignes and Val d'Isere",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": "codex/catalog-curation-tignes-val-disere-v2",
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "lifecycle_state": "OPEN",
        "created_at": datetime(2026, 7, 8, 10, tzinfo=UTC),
        "labels": frozenset(
            {
                MaintainerLane.CATALOG_CURATION,
                MaintainerState.WAITING_CI,
            }
        ),
        "head_sha": "a" * 40,
        "mergeable": "MERGEABLE",
        "check_state": "pending",
        "changed_paths": frozenset({"app/data/catalog_v2.json"}),
        "body": "Maintainer summary",
    }
    values.update(overrides)
    return PullRequest.model_validate(values)


def test_package_constants_define_repository_and_label_contract() -> None:
    assert REPOSITORY == "lampssy/ai-sports-travel-planner"
    assert (
        REPOSITORY_SSH_URL
        == "git@github.com-lampss:lampssy/ai-sports-travel-planner.git"
    )
    assert DEFAULT_BASE_BRANCH == "main"
    assert SUMMARY_MARKER == "<!-- snowcast-maintainer-summary -->"
    assert BODY_START == "<!-- snowcast-maintainer-body:start -->"
    assert BODY_END == "<!-- snowcast-maintainer-body:end -->"
    assert LABEL_DEFINITIONS == {
        "lane:catalog-discovery": (
            "Catalog discovery proposal workflow",
            "5319E7",
        ),
        "lane:catalog-curation": (
            "Catalog curation readiness workflow",
            "1D76DB",
        ),
        "maintainer:proposal": (
            "Waiting for owner onboarding decision",
            "D4C5F9",
        ),
        "maintainer:working": (
            "Automated review or remediation in progress",
            "FBCA04",
        ),
        "maintainer:waiting-ci": (
            "Automated work complete; required checks pending",
            "BFDADC",
        ),
        "maintainer:ready": (
            "Reviewed head is green and ready for owner merge",
            "0E8A16",
        ),
        "maintainer:owner-decision": (
            "Blocked on a product or domain decision",
            "D93F0B",
        ),
        "maintainer:manual-check": (
            "Requires focused manual investigation",
            "E99695",
        ),
        "maintainer:blocked": (
            "Automation cannot make safe progress",
            "B60205",
        ),
    }


def test_valid_pull_request_exposes_lane_and_maintainer_state() -> None:
    pull_request = _pull_request()

    assert pull_request.lane is MaintainerLane.CATALOG_CURATION
    assert pull_request.maintainer_state is MaintainerState.WAITING_CI
    assert pull_request.lifecycle_state == "OPEN"
    assert pull_request.created_at.tzinfo is UTC
    assert pull_request.is_draft is False


def test_pull_request_accepts_additive_draft_metadata() -> None:
    assert _pull_request(is_draft=True).is_draft is True


def test_pull_request_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        _pull_request(created_at=datetime(2026, 7, 8, 10))


def test_pull_request_normalizes_created_at_to_utc() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))

    pull_request = _pull_request(created_at=datetime(2026, 7, 8, 15, 30, tzinfo=offset))

    assert pull_request.created_at == datetime(2026, 7, 8, 10, tzinfo=UTC)
    assert pull_request.created_at.tzinfo is UTC


def test_pull_request_rejects_unknown_lifecycle_state() -> None:
    with pytest.raises(ValidationError):
        _pull_request(lifecycle_state="DRAFT")


def test_pull_request_rejects_multiple_maintainer_states() -> None:
    labels = frozenset(
        {
            MaintainerState.WORKING,
            MaintainerState.WAITING_CI,
        }
    )

    with pytest.raises(ValidationError, match="at most one maintainer state"):
        _pull_request(labels=labels)


def test_pull_request_rejects_multiple_lanes() -> None:
    labels = frozenset(
        {
            MaintainerLane.CATALOG_DISCOVERY,
            MaintainerLane.CATALOG_CURATION,
        }
    )

    with pytest.raises(ValidationError, match="at most one maintainer lane"):
        _pull_request(labels=labels)


def test_pull_request_rejects_non_github_url_and_invalid_head_sha() -> None:
    with pytest.raises(ValidationError, match="GitHub URL"):
        _pull_request(url="https://example.com/pull/42")

    with pytest.raises(ValidationError):
        _pull_request(head_sha="A" * 40)


def _machine_state_v2(**overrides: object) -> MachineState:
    values: dict[str, object] = {
        "schema_version": 2,
        "last_operation": "none",
    }
    values.update(overrides)
    return MachineState.model_validate(values)


def test_machine_state_v2_accepts_each_consistent_operation_state() -> None:
    reviewed_head = "c" * 40

    assert _machine_state_v2().last_operation == "none"
    assert (
        _machine_state_v2(
            reviewed_head=reviewed_head,
            last_operation="reviewed",
        ).reviewed_head
        == reviewed_head
    )
    for operation in ("validated", "pushed", "published"):
        state = _machine_state_v2(
            reviewed_head=reviewed_head,
            validated_head=reviewed_head,
            last_operation=operation,
        )
        assert state.reviewed_head == state.validated_head == reviewed_head


@pytest.mark.parametrize("schema_version", [None, 1, 3, "2"])
def test_machine_state_v2_rejects_missing_legacy_or_unknown_schema(
    schema_version: object,
) -> None:
    values: dict[str, object] = {"last_operation": "none"}
    if schema_version is not None:
        values["schema_version"] = schema_version

    with pytest.raises(ValidationError):
        MachineState.model_validate(values)


@pytest.mark.parametrize(
    "values",
    [
        {"candidate_key": "ski_area:tignes"},
        {"candidate_origin": "backlog"},
    ],
)
def test_machine_state_v2_requires_candidate_key_and_origin_together(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="candidate_key and candidate_origin"):
        _machine_state_v2(**values)


def test_machine_state_v2_accepts_optional_candidate_identity() -> None:
    state = _machine_state_v2(
        candidate_key="ski_area:tignes-val-disere",
        candidate_origin="external",
    )

    assert state.candidate_key == "ski_area:tignes-val-disere"
    assert state.candidate_origin == "external"


@pytest.mark.parametrize(
    "candidate_key",
    [
        "",
        "Catalog:tignes",
        "ski_area:tignes_val",
        f"ski_area:{'x' * 120}",
    ],
)
def test_machine_state_v2_rejects_unsafe_or_unbounded_candidate_key(
    candidate_key: str,
) -> None:
    with pytest.raises(ValidationError):
        _machine_state_v2(
            candidate_key=candidate_key,
            candidate_origin="backlog",
        )


@pytest.mark.parametrize(
    "values",
    [
        {"validated_head": "d" * 40, "last_operation": "validated"},
        {
            "reviewed_head": "c" * 40,
            "validated_head": "d" * 40,
            "last_operation": "validated",
        },
        {"reviewed_head": "c" * 40, "last_operation": "none"},
        {
            "reviewed_head": "c" * 40,
            "validated_head": "c" * 40,
            "last_operation": "reviewed",
        },
        {"reviewed_head": "c" * 40, "last_operation": "pushed"},
    ],
)
def test_machine_state_v2_rejects_operation_fact_mismatches(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _machine_state_v2(**values)


def test_machine_state_v2_is_strict_frozen_and_forbids_legacy_or_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _machine_state_v2(reviewed_head="C" * 40, last_operation="reviewed")

    with pytest.raises(ValidationError, match="extra_forbidden"):
        _machine_state_v2(lineage_id="legacy-lineage")

    state = _machine_state_v2()
    with pytest.raises(ValidationError, match="Instance is frozen"):
        state.last_operation = "reviewed"

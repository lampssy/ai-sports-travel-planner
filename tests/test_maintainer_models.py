from __future__ import annotations

from datetime import UTC, datetime

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


@pytest.mark.parametrize("completed_cycles", [-1, 4])
def test_machine_state_rejects_cycles_outside_supported_range(
    completed_cycles: int,
) -> None:
    with pytest.raises(ValidationError):
        MachineState(
            head_sha="b" * 40,
            lineage_id="catalog-curation-42",
            completed_cycles=completed_cycles,
            last_publication="none",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_origin_fingerprint", "c" * 64),
        ("candidate_fingerprint", "d" * 64),
        ("regional_graph_key", "portes-du-soleil"),
    ],
)
def test_machine_state_rejects_candidate_metadata_without_candidate_key(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError, match="require candidate_key"):
        MachineState.model_validate(
            {
                "head_sha": "b" * 40,
                "lineage_id": "catalog-curation-42",
                field: value,
                "last_publication": "none",
            }
        )


def test_machine_state_rejects_blank_candidate_key() -> None:
    with pytest.raises(ValidationError, match="candidate_key must not be blank"):
        MachineState(
            head_sha="b" * 40,
            lineage_id="catalog-curation-42",
            candidate_key="  ",
            last_publication="none",
        )


def test_models_are_strict_frozen_and_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _pull_request(number="42")

    with pytest.raises(ValidationError, match="extra_forbidden"):
        MachineState.model_validate(
            {
                "head_sha": "b" * 40,
                "lineage_id": "catalog-curation-42",
                "last_publication": "none",
                "unexpected": True,
            }
        )

    state = MachineState(
        head_sha="b" * 40,
        lineage_id="catalog-curation-42",
        last_publication="none",
    )
    with pytest.raises(ValidationError, match="Instance is frozen"):
        state.completed_cycles = 1


def test_pull_request_rejects_non_github_url_and_invalid_head_sha() -> None:
    with pytest.raises(ValidationError, match="GitHub URL"):
        _pull_request(url="https://example.com/pull/42")

    with pytest.raises(ValidationError):
        _pull_request(head_sha="A" * 40)

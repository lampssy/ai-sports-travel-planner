from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ops.maintainer.cli import HANDLERS, _parser

pytestmark = pytest.mark.db_free

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPOSITORY_ROOT / "docs/operating-model/maintainer-runtime-command-contract.md"
)
ACTIVATION_PATH = (
    REPOSITORY_ROOT / "docs/operating-model/local-maintainer-activation.md"
)
DESIGN_PATH = (
    REPOSITORY_ROOT
    / "docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md"
)
CONTRACT_PATTERN = re.compile(
    r"<!-- runtime-command-contract:start -->\s*"
    r"```json\s*(?P<contract>\{.*?\})\s*```\s*"
    r"<!-- runtime-command-contract:end -->",
    re.DOTALL,
)
PLACEHOLDERS = {
    "${BASE}": "e" * 40,
    "${BASE_DIR}": "/tmp/exact-base",
    "${BODY_FILE}": "body-example",
    "${BRANCH}": "codex/catalog-curation-example",
    "${CANDIDATE_KEY}": "stay_destination:example",
    "${CANDIDATE_ORIGIN}": "backlog",
    "${EXPECTED_HEAD}": "a" * 40,
    "${HEAD}": "b" * 40,
    "${OUTCOME_REASON}": "non-converging",
    "${OUTCOME_STATE}": "maintainer:blocked",
    "${PR}": "42",
    "${REPORT}": "docs/catalog-curation/example.json",
    "${REVIEWED_HEAD}": "c" * 40,
    "${RUN_ID}": "d" * 32,
    "${STATE}": "maintainer:ready",
    "${SUMMARY_FILE}": "summary-example",
    "${TITLE_FILE}": "title-example",
    "${WORK_ID}": "curation-pr-42",
    "${WORKER}": "curation",
}


def _contract() -> dict[str, object]:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    match = CONTRACT_PATTERN.search(text)
    assert match is not None
    return json.loads(match.group("contract"))


def _substitute(argv: list[str]) -> list[str]:
    return [PLACEHOLDERS.get(value, value) for value in argv]


def test_runtime_contract_documents_every_cli_route_with_parseable_argv() -> None:
    contract = _contract()
    assert contract["command_prefix"] == [
        "uv",
        "run",
        "--no-config",
        "python",
        "-m",
        "ops.maintainer.cli",
        "--state-dir",
        "${STATE_DIR}",
        "--gh-config-dir",
        "${GH_CONFIG_DIR}",
    ]
    recipes = contract["recipes"]
    assert isinstance(recipes, dict)

    documented_routes: set[tuple[str, str]] = set()
    for name, value in recipes.items():
        assert isinstance(name, str)
        assert isinstance(value, dict)
        argv = value["argv"]
        assert isinstance(argv, list)
        assert all(isinstance(argument, str) for argument in argv)
        assert "--help" not in argv
        parsed = _parser().parse_args(
            [
                "--state-dir",
                "/tmp/snowcast-maintainer-state",
                "--gh-config-dir",
                "/tmp/snowcast-maintainer-gh",
                *_substitute(argv),
            ]
        )
        documented_routes.add((parsed.family, parsed.command))

    expected_routes = {
        *HANDLERS,
        ("lock", "acquire"),
        ("lock", "heartbeat"),
        ("lock", "release"),
    }
    assert documented_routes == expected_routes


def test_runtime_contract_freezes_the_critical_sequences() -> None:
    flows = _contract()["flows"]
    assert flows == {
        "curation_journal_recovery_through_continuation": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "publish_recover",
            "lock_heartbeat_curation",
        ],
        "curation_recovery_absent_manual_check_after_recover": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_manual_check",
            "lock_heartbeat_curation",
            "inspect_curation",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_recovery_absent_owner_decision_after_recover": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publish_state_summary_only",
            "lock_heartbeat_curation",
            "inspect_curation",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_reviewed_continuation_through_prepare": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "prepare_continuation",
            "lock_heartbeat_curation",
        ],
        "curation_remediation_continuation_through_prepare": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "prepare_continuation",
            "lock_heartbeat_curation",
        ],
        "curation_ordinary_pr_through_prepare": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "prepare_curation",
            "lock_heartbeat_curation",
        ],
        "curation_waiting_ci_pending": [
            "inspect_curation",
            "inspect_discovery",
        ],
        "curation_waiting_ci_success": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_state_adopt_body",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
    }


def test_runtime_contract_classifies_dispatch_errors_as_orchestration_errors() -> None:
    classification = _contract()["dispatch_error_classification"]
    assert classification == {
        "reason": "invalid-command",
        "stage": "dispatch",
        "classification": "orchestration-command-invalid",
        "retry_policy": {
            "require_completed_dispatch_rejection": True,
            "require_mutation_occurred_false": True,
            "repeat_malformed_argv": False,
            "corrected_registered_recipe_attempts": 1,
            "same_intended_recipe_only": True,
            "allow_help_or_capability_switch": False,
        },
    }


def test_per_cycle_sources_use_the_short_runtime_contract() -> None:
    activation = ACTIVATION_PATH.read_text(encoding="utf-8")
    design = DESIGN_PATH.read_text(encoding="utf-8")
    normalized_activation = " ".join(activation.split())
    normalized_design = " ".join(design.split())

    assert "maintainer-runtime-command-contract.md" in activation
    assert "maintainer-runtime-command-contract.md" in design
    assert "normal scheduled cycle" in normalized_activation
    assert "workflow modification or a contract mismatch" in normalized_activation
    assert (
        "does not prove that the personal runtime is activated" in normalized_activation
    )
    assert "Before merging a change to this runtime source set" in normalized_activation
    for source in (normalized_activation, normalized_design):
        assert "one corrected execution of the same registered recipe" in source
        assert "second dispatch rejection" in source


def test_convergence_contract_tolerates_residuals_and_two_exact_repeats() -> None:
    sources = {
        "activation": " ".join(
            ACTIVATION_PATH.read_text(encoding="utf-8").split()
        ).lower(),
        "design": " ".join(DESIGN_PATH.read_text(encoding="utf-8").split()).lower(),
    }

    for source, text in sources.items():
        assert "candidate inventory and finding ledger are separate views" in text, (
            source
        )
        assert "same assertion key and acceptance criterion" in text, source
        assert "narrower residual" in text, source
        assert "first and second consecutive exact repeats" in text, source
        assert "third consecutive exact repeat" in text, source
        assert "candidate-entry count or percentage" in text, source
        assert "regression or unsafe scope expansion still stops immediately" in text, (
            source
        )
        assert "rewording or changing an id does not reset the streak" in text, source
        assert "resolved subcriterion" in text, source
        assert "parent_finding_id" in text, source
        assert "repeat streak is run-local" in text, source

    assert "finding-family counts" in sources["activation"]
    assert "maximum exact-repeat streak" in sources["activation"]
    assert (
        "never present candidate-entry count as the issue count"
        in sources["activation"]
    )


def test_runtime_helper_does_not_own_semantic_convergence() -> None:
    contract = " ".join(CONTRACT_PATH.read_text(encoding="utf-8").split()).lower()

    assert "does not classify residuals or exact repeats" in contract
    assert "does not count candidate entries" in contract
    assert "codex owns the assertion-level finding ledger" in contract

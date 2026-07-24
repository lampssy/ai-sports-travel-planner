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
CI_REMEDIATION_DESIGN_PATH = (
    REPOSITORY_ROOT / "docs/superpowers/specs/"
    "2026-07-24-maintainer-post-push-ci-remediation-design.md"
)
ENGINEERING_NOTES_PATH = REPOSITORY_ROOT / "docs/engineering-notes.md"
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
        "curation_initial_push_into_ci_wait": [
            "publish_push",
            "lock_heartbeat_curation",
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_state_adopt_body",
            "lock_heartbeat_curation",
        ],
        "curation_ci_continuation_through_initial_wait": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
        ],
        "curation_ci_initial_wait_success": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_state_adopt_body",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_ci_initial_wait_pending": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_state_adopt_body",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_ci_initial_wait_unrepairable_failure": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publish_outcome",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_ci_repair_through_second_wait": [
            "prepare_ci_repair",
            "lock_heartbeat_curation",
            "checkpoint_ci_repair",
            "lock_heartbeat_curation",
            "publish_ci_repair",
            "lock_heartbeat_curation",
        ],
        "curation_ci_second_wait_success": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_state_adopt_body",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_ci_second_wait_pending": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publication_input_body",
            "lock_heartbeat_curation",
            "publish_state_adopt_body",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
        "curation_ci_second_wait_failure": [
            "publication_input_summary",
            "lock_heartbeat_curation",
            "publish_outcome",
            "lock_heartbeat_curation",
            "lock_release_curation",
        ],
    }


def test_runtime_contract_freezes_post_push_ci_repair_policy() -> None:
    contract = _contract()
    recipes = contract["recipes"]
    assert recipes["inspect_curation"]["returns"] == [
        "eligible",
        "ci_continuations",
        "reviewed_continuations",
        "remediation_continuations",
        "unresolved_pushes",
    ]
    assert recipes["prepare_ci_repair"] == {
        "argv": [
            "prepare",
            "ci-repair",
            "--pr",
            "${PR}",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": [
            "work_id",
            "current_head",
            "failed_checks",
            "remaining_repair_seconds",
            "permitted_path_pattern",
        ],
    }
    assert recipes["checkpoint_ci_repair"] == {
        "argv": [
            "checkpoint",
            "ci-repair",
            "--pr",
            "${PR}",
            "--head",
            "${HEAD}",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": ["work_id", "repair_head", "repair_ref", "repair_paths"],
    }
    assert recipes["publish_ci_repair"] == {
        "argv": [
            "publish",
            "ci-repair",
            "--pr",
            "${PR}",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": ["work_id", "push", "continuation"],
    }
    assert contract["ci_continuation_policy"] == {
        "recovery_priority": [
            "push_journal",
            "post_push_ci_continuation",
            "reviewed_continuation",
            "remediation_continuation",
            "ordinary_pr",
        ],
        "first_wait_seconds": 1800,
        "repair_active_seconds": 3600,
        "second_wait_seconds": 1800,
        "heartbeat_max_interval_seconds": 300,
        "repair_attempts": 1,
        "repair_path_pattern": "tests/test_*.py",
        "failed_check_inspection": "read-only-untrusted",
        "execute_target_pr_tests_locally": False,
        "semantic_work_after_initial_push": False,
        "release_lease_between_post_push_phases": False,
        "counts_toward_semantic_240_minute_clock": False,
    }


def test_checked_in_sources_freeze_the_post_push_ci_runtime_contract() -> None:
    sources = {
        "runtime": CONTRACT_PATH.read_text(encoding="utf-8"),
        "activation": ACTIVATION_PATH.read_text(encoding="utf-8"),
        "long_design": DESIGN_PATH.read_text(encoding="utf-8"),
        "ci_design": CI_REMEDIATION_DESIGN_PATH.read_text(encoding="utf-8"),
        "engineering_notes": ENGINEERING_NOTES_PATH.read_text(encoding="utf-8"),
    }
    normalized = {
        name: " ".join(text.split()).lower() for name, text in sources.items()
    }

    for name, text in normalized.items():
        assert "30/60/30" in text, name
        assert "at least every five minutes" in text, name
        assert "no semantic work" in text, name
        assert "does not execute" in text and "tests/test_*.py" in text, name
        assert "never approve or merge" in text or "never approves or merges" in text, (
            name
        )

    for name in ("runtime", "activation", "long_design"):
        text = normalized[name]
        assert (
            "push journal -> post-push ci continuation -> reviewed continuation "
            "-> remediation continuation -> ordinary pr"
        ) in text, name
        assert "automation memory and labels" in text, name
        assert "read-only" in text and "untrusted" in text, name
        assert "same lease" in text, name
        assert "second ci failure" in text, name

    assert (
        "implemented on feature branch, activation pending" in normalized["ci_design"]
    )
    assert "pr #" not in normalized["ci_design"]


def test_runtime_contract_classifies_dispatch_errors_as_orchestration_errors() -> None:
    classification = _contract()["dispatch_error_classification"]
    assert classification == {
        "reason": "invalid-command",
        "stage": "dispatch",
        "classification": "orchestration-command-invalid",
        "retry_same_call": False,
    }


def test_per_cycle_sources_use_the_short_runtime_contract() -> None:
    activation = ACTIVATION_PATH.read_text(encoding="utf-8")
    design = DESIGN_PATH.read_text(encoding="utf-8")
    normalized_activation = " ".join(activation.split())

    assert "maintainer-runtime-command-contract.md" in activation
    assert "maintainer-runtime-command-contract.md" in design
    assert "normal scheduled cycle" in normalized_activation
    assert "workflow modification or a contract mismatch" in normalized_activation
    assert (
        "does not prove that the personal runtime is activated" in normalized_activation
    )
    assert "Before merging a change to this runtime source set" in normalized_activation


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

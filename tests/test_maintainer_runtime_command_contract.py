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
GENERATION_DESIGN_PATH = (
    REPOSITORY_ROOT / "docs/superpowers/specs/"
    "2026-08-15-maintainer-curation-generation-checkpoints-design.md"
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
    "${GENERATION_ID}": "f" * 32,
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


def _parse_recipe_sequence(
    names: list[str],
    *,
    substitutions: dict[str, str] | None = None,
) -> list[object]:
    recipes = _contract()["recipes"]
    values = {**PLACEHOLDERS, **(substitutions or {})}
    parsed = []
    for name in names:
        argv = recipes[name]["argv"]
        parsed.append(
            _parser().parse_args(
                [
                    "--state-dir",
                    "/tmp/snowcast-maintainer-state",
                    "--gh-config-dir",
                    "/tmp/snowcast-maintainer-gh",
                    *(values.get(value, value) for value in argv),
                ]
            )
        )
    return parsed


def _allowed_next_steps() -> dict[str, str]:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    section = text.split("## Allowed Next Steps", 1)[1].split(
        "## Completion And Branching Rules",
        1,
    )[0]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[cells[0].strip("`")] = cells[1]
    return rows


def test_runtime_contract_documents_every_cli_route_with_parseable_argv() -> None:
    contract = _contract()
    assert contract["command_prefix"] == [
        "uv",
        "run",
        "--no-config",
        "python",
        "-m",
        "ops.maintainer.cli",
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


def test_registered_prefix_relies_on_project_cli_directory_defaults() -> None:
    parsed = _parser().parse_args(["inspect", "curation"])

    assert parsed.state_dir == Path.home() / ".local/state/snowcast-maintainer"
    assert parsed.gh_config_dir == Path.home() / ".config/gh-lampssy-snowcast"


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
        "curation_generation_through_prepare": [
            "inspect_curation",
            "inspect_discovery",
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "prepare_curation",
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
        "curation_ci_successor_entry": [
            "lock_acquire_curation",
            "lock_heartbeat_curation",
            "inspect_curation",
            "lock_heartbeat_curation",
        ],
    }


def test_runtime_contract_composes_same_run_ci_waits_before_every_branch() -> None:
    contract = _contract()
    waits = contract["ci_waits"]
    assert set(waits) == {"initial_wait", "second_wait"}
    expected_branches = {
        "initial_wait": {
            "success",
            "pending_timeout",
            "repairable_failure",
            "terminal_failure",
        },
        "second_wait": {"success", "pending_timeout", "terminal_failure"},
    }

    for wait_name, branch_names in expected_branches.items():
        wait = waits[wait_name]
        assert wait["poll"] == [
            "lock_heartbeat_curation",
            "inspect_curation",
            "lock_heartbeat_curation",
        ]
        assert set(wait["branches"]) == branch_names
        for branch_name, branch in wait["branches"].items():
            composed = [*wait["poll"], *branch["sequence"]]
            parsed = _parse_recipe_sequence(
                composed,
                substitutions=branch.get("substitutions"),
            )
            assert [(item.family, item.command) for item in parsed[:3]] == [
                ("lock", "heartbeat"),
                ("inspect", "curation"),
                ("lock", "heartbeat"),
            ]
            assert all(
                (item.family, item.command) != ("lock", "acquire") for item in parsed
            )
            if branch_name == "repairable_failure":
                assert (parsed[3].family, parsed[3].command) == (
                    "prepare",
                    "ci-repair",
                )
                assert all(item.command != "release" for item in parsed)
            else:
                assert (parsed[-1].family, parsed[-1].command) == (
                    "lock",
                    "release",
                )

    successor = _parse_recipe_sequence(contract["flows"]["curation_ci_successor_entry"])
    assert [(item.family, item.command) for item in successor] == [
        ("lock", "acquire"),
        ("lock", "heartbeat"),
        ("inspect", "curation"),
        ("lock", "heartbeat"),
    ]

    state_sequence = [
        "publication_input_summary",
        "lock_heartbeat_curation",
        "publication_input_body",
        "lock_heartbeat_curation",
        "publish_state_adopt_body",
        "lock_heartbeat_curation",
        "lock_release_curation",
    ]
    repair_sequence = [
        "prepare_ci_repair",
        "lock_heartbeat_curation",
        "checkpoint_ci_repair",
        "lock_heartbeat_curation",
        "publish_ci_repair",
        "lock_heartbeat_curation",
    ]
    outcome_sequence = [
        "publication_input_summary",
        "lock_heartbeat_curation",
        "publish_outcome",
        "lock_heartbeat_curation",
        "lock_release_curation",
    ]
    initial = waits["initial_wait"]["branches"]
    assert initial["success"]["sequence"] == state_sequence
    assert initial["pending_timeout"]["sequence"] == state_sequence
    assert initial["repairable_failure"]["sequence"] == repair_sequence
    assert initial["terminal_failure"]["sequence"] == outcome_sequence
    assert initial["success"]["substitutions"] == {"${STATE}": "maintainer:ready"}
    assert initial["pending_timeout"]["substitutions"] == {
        "${STATE}": "maintainer:waiting-ci"
    }
    assert initial["terminal_failure"]["substitutions"] == {
        "${OUTCOME_STATE}": "maintainer:blocked",
        "${OUTCOME_REASON}": "ci-failure",
    }

    second = waits["second_wait"]["branches"]
    assert second["success"]["sequence"] == state_sequence
    assert second["pending_timeout"]["sequence"] == state_sequence
    assert second["terminal_failure"]["sequence"] == outcome_sequence
    assert second["success"]["substitutions"] == {"${STATE}": "maintainer:ready"}
    assert second["pending_timeout"]["substitutions"] == {
        "${STATE}": "maintainer:waiting-ci"
    }
    assert second["terminal_failure"]["substitutions"] == {
        "${OUTCOME_STATE}": "maintainer:blocked",
        "${OUTCOME_REASON}": "ci-failure",
    }
    for branch in second.values():
        assert "prepare_ci_repair" not in branch["sequence"]

    for wait in waits.values():
        for branch_name, branch in wait["branches"].items():
            parsed = _parse_recipe_sequence(
                branch["sequence"],
                substitutions=branch.get("substitutions"),
            )
            publications = [item for item in parsed if item.family == "publish"]
            if branch_name in {"success", "pending_timeout"}:
                assert [(item.command, item.state) for item in publications] == [
                    ("state", branch["substitutions"]["${STATE}"])
                ]
            elif branch_name == "terminal_failure":
                assert [
                    (item.command, item.state, item.reason) for item in publications
                ] == [("outcome", "maintainer:blocked", "ci-failure")]
            else:
                assert [item.command for item in publications] == ["ci-repair"]


def test_runtime_contract_splits_curation_and_discovery_inspection_next_steps() -> None:
    rows = _allowed_next_steps()
    assert "inspect_*" not in rows
    assert rows["inspect_curation"] == (
        "recover one terminal publication first, then one push journal; "
        "otherwise select one CI continuation, current curation generation, "
        "ordinary curation PR, or bounded no-op in that order"
    )
    assert rows["inspect_discovery"] == (
        "recover one journal first; otherwise select preferred retry, merged "
        "regional completion, active backlog, bounded external official-source "
        "scan, or bounded no-op in that order"
    )


def test_runtime_contract_freezes_review_disposition_branches() -> None:
    contract = _contract()

    assert contract["curation_review_disposition"] == {
        "applies_to_results": ["prepared", "review-required"],
        "semantic_entry": "full-normalization-inventory-review-remediation-flow",
        "branches": {
            "clean": {
                "head_source": "prepared-or-allowed-normalization-head",
                "next_recipe": "checkpoint_curation_reviewed",
            },
            "changes_requested": {
                "head_source": "allowed-remediation-head",
                "next_recipe": "checkpoint_curation_delta",
                "after_checkpoint": "fresh-full-review",
            },
        },
        "reviewed_checkpoint_gate": "fresh-clean-exact-head-review",
        "delta_authority": "helper-validation-on-invocation",
    }
    for branch in contract["curation_review_disposition"]["branches"].values():
        recipe = branch["next_recipe"]
        parsed = _parse_recipe_sequence([recipe])
        assert [(item.family, item.command) for item in parsed] == [
            ("checkpoint", "curation")
        ]

    assert _allowed_next_steps()["prepare_curation*"] == (
        "enter the full semantic flow for prepared or review-required work; "
        "a clean review uses checkpoint_curation_reviewed, while requested "
        "changes use checkpoint_curation_delta after bounded remediation"
    )

    sources = {
        "runtime": CONTRACT_PATH,
        "activation": ACTIVATION_PATH,
        "generation_design": GENERATION_DESIGN_PATH,
    }
    for name, path in sources.items():
        normalized = " ".join(path.read_text(encoding="utf-8").split()).lower()
        assert "clean-review branch" in normalized, name
        assert "requested-changes branch" in normalized, name
        assert "fresh clean exact-head review" in normalized, name


def test_runtime_contract_documents_conditional_ci_budget_heartbeat_result() -> None:
    recipes = _contract()["recipes"]
    recipe = recipes["lock_heartbeat_curation"]
    assert recipe == {
        "argv": [
            "lock",
            "heartbeat",
            "curation",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": ["worker"],
        "conditional_returns": {
            "ci_budget": {
                "when": "run-owned active CI continuation exists",
                "fields": [
                    "first_wait_seconds",
                    "repair_active_seconds",
                    "second_wait_seconds",
                ],
            }
        },
    }
    assert recipes["lock_heartbeat_discovery"] == {
        "argv": [
            "lock",
            "heartbeat",
            "discovery",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": ["worker"],
    }


def test_runtime_contract_freezes_post_push_ci_repair_policy() -> None:
    contract = _contract()
    recipes = contract["recipes"]
    assert recipes["inspect_curation"]["returns"] == [
        "eligible",
        "terminal_publications",
        "ci_continuations",
        "generations",
        "unresolved_pushes",
    ]
    assert recipes["publish_recover"] == {
        "argv": [
            "publish",
            "recover",
            "--work-id",
            "${WORK_ID}",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": ["work_id"],
        "conditional_returns": {
            "push-journal": ["push", "continuation"],
            "terminal-publication": ["terminal_publication"],
        },
    }
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
            "phase",
            "resumed",
            "remaining_repair_seconds",
        ],
        "conditional_returns": {
            "repair-active": [
                "current_head",
                "failed_checks",
                "permitted_path_pattern",
            ],
            "repair-reviewed": [
                "repair_head",
                "repair_ref",
                "repair_paths",
            ],
        },
    }
    assert recipes["invalidate_ci_continuation"] == {
        "argv": [
            "invalidate",
            "ci-continuation",
            "--pr",
            "${PR}",
            "--run-id",
            "${RUN_ID}",
        ],
        "returns": [
            "work_id",
            "pr_number",
            "phase",
            "availability_reason",
            "continuation_head",
            "observed_head",
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
            "terminal_publication",
            "push_journal",
            "post_push_ci_continuation",
            "curation_generation",
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
        "repair_successor_resume": "phase-aware-prepare-ci-repair",
        "repair_capability_journal_gate": "unconditional-exact-recovery-only",
        "non_resumable_invalidation": "lease-owned-live-facts",
        "terminal_generation_rollover": "new-validated-pushed-semantic-head-only",
        "terminal_generation_archive": "owner-private-semantic-head-versioned",
        "terminal_publication_intent": "owner-private-before-external-mutation",
        "terminal_publication_completion": (
            "external-publication-then-exact-continuation-block"
        ),
        "terminal_publication_recovery": "idempotent-exact-authority-only",
    }


def test_validated_push_recovery_branches_on_live_ci_state() -> None:
    contract = _contract()

    assert contract["curation_validated_push_recovery"] == {
        "authority": "live-exact-pr-facts-after-publish-recover",
        "branches": {
            "success_mergeable": {
                "substitutions": {"${STATE}": "maintainer:ready"},
                "sequence": [
                    "publication_input_summary",
                    "lock_heartbeat_curation",
                    "publication_input_body",
                    "lock_heartbeat_curation",
                    "publish_state_adopt_body",
                    "lock_heartbeat_curation",
                    "inspect_curation",
                    "lock_heartbeat_curation",
                    "lock_release_curation",
                ],
            },
            "pending": {
                "substitutions": {"${STATE}": "maintainer:waiting-ci"},
                "sequence": [
                    "publication_input_summary",
                    "lock_heartbeat_curation",
                    "publication_input_body",
                    "lock_heartbeat_curation",
                    "publish_state_adopt_body",
                    "lock_heartbeat_curation",
                ],
            },
            "failure_or_cancelled": {
                "action": "stop-without-lifecycle-guess",
            },
            "unknown_or_nonmergeable": {
                "action": "stop-without-lifecycle-guess",
            },
        },
        "unconditional_waiting_ci_fallback": False,
    }

    branches = contract["curation_validated_push_recovery"]["branches"]
    assert branches["success_mergeable"]["substitutions"] == {
        "${STATE}": "maintainer:ready"
    }
    assert branches["pending"]["substitutions"] == {"${STATE}": "maintainer:waiting-ci"}
    for branch_name in ("success_mergeable", "pending"):
        branch = branches[branch_name]
        parsed = _parse_recipe_sequence(
            branch["sequence"],
            substitutions=branch["substitutions"],
        )
        publication = next(item for item in parsed if item.family == "publish")
        assert (publication.command, publication.state) == (
            "state",
            branch["substitutions"]["${STATE}"],
        )

    sources = {
        "runtime": CONTRACT_PATH.read_text(encoding="utf-8"),
        "activation": ACTIVATION_PATH.read_text(encoding="utf-8"),
    }
    for name, text in sources.items():
        normalized = " ".join(text.split()).lower()
        assert (
            "never request `maintainer:waiting-ci` when checks are already successful"
            in normalized
        ), name


def test_runtime_sources_freeze_terminal_publication_recovery() -> None:
    sources = {
        "runtime": CONTRACT_PATH.read_text(encoding="utf-8"),
        "activation": ACTIVATION_PATH.read_text(encoding="utf-8"),
        "ci_design": CI_REMEDIATION_DESIGN_PATH.read_text(encoding="utf-8"),
        "engineering_notes": ENGINEERING_NOTES_PATH.read_text(encoding="utf-8"),
    }
    normalized = {
        name: " ".join(text.split()).lower() for name, text in sources.items()
    }

    for name, text in normalized.items():
        assert "owner-private terminal-publication intent" in text, name
        assert "before any github mutation" in text, name
        assert "idempotent" in text, name
        assert "exact matching continuation" in text, name
        assert "repair cannot resume" in text, name


def test_runtime_sources_document_ci_recovery_and_rollover() -> None:
    sources = {
        "runtime": CONTRACT_PATH.read_text(encoding="utf-8"),
        "activation": ACTIVATION_PATH.read_text(encoding="utf-8"),
        "ci_design": CI_REMEDIATION_DESIGN_PATH.read_text(encoding="utf-8"),
        "engineering_notes": ENGINEERING_NOTES_PATH.read_text(encoding="utf-8"),
    }
    normalized = {
        name: " ".join(text.split()).lower() for name, text in sources.items()
    }
    for name, text in normalized.items():
        assert "invalidate ci-continuation" in text, name
        assert "repair-active" in text and "repair-reviewed" in text, name
        assert "semantic head" in text and "archive" in text, name
        assert "unresolved push journal" in text, name
        assert "does not reset" in text or "never reset" in text, name


def test_runtime_sources_require_repair_handoff_before_second_wait() -> None:
    sources = {
        "runtime": CONTRACT_PATH.read_text(encoding="utf-8"),
        "activation": ACTIVATION_PATH.read_text(encoding="utf-8"),
        "ci_design": CI_REMEDIATION_DESIGN_PATH.read_text(encoding="utf-8"),
    }
    normalized = {
        name: " ".join(text.split()).lower() for name, text in sources.items()
    }

    for name, text in normalized.items():
        assert "canonical waiting-ci" in text, name
        assert "before second-wait inspection" in text, name
        assert "repair push journal" in text and "published" in text, name


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
            "terminal publication -> push journal -> post-push ci continuation "
            "-> current curation generation -> ordinary pr"
        ) in text, name
        assert "automation memory and labels" in text, name
        assert "read-only" in text and "untrusted" in text, name
        assert "same lease" in text, name
        assert "second ci failure" in text, name

    assert (
        "implemented on feature branch, activation pending" in normalized["ci_design"]
    )
    assert "pr #" not in normalized["ci_design"]


def test_activation_rollback_requires_ci_continuation_safe_downgrade() -> None:
    rollback = ACTIVATION_PATH.read_text(encoding="utf-8").split("## Rollback", 1)[1]
    normalized = " ".join(rollback.split()).lower()

    assert "post-push ci continuations" in normalized
    for phase in ("initial-wait", "repair-active", "repair-reviewed", "second-wait"):
        assert phase in normalized
    assert "matching unresolved push journal" in normalized
    assert "completed or safely terminalized" in normalized
    assert "while any active ci continuation remains" in normalized
    assert "helper version that created or understands it" in normalized


def test_runtime_contract_classifies_dispatch_errors_as_orchestration_errors() -> None:
    classification = _contract()["dispatch_error_classification"]
    assert classification == {
        "reason": "invalid-command",
        "stage": "dispatch",
        "classification": "orchestration-command-invalid",
        "retry_policy": {
            "require_completed_dispatch_rejection": True,
            "require_mutation_occurred_false": True,
            "corrected_registered_recipe_required": True,
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
        assert "must execute exactly one corrected attempt" in source
        assert "second dispatch rejection" in source


def test_curation_pr_synopsis_requires_an_exact_head_rendered_report_link() -> None:
    contract = " ".join(
        CONTRACT_PATH.read_text(encoding="utf-8").replace("`", "").split()
    ).lower()

    assert "full report" in contract
    assert "rendered markdown report" in contract
    assert "absolute github blob link" in contract
    assert "exact published head" in contract


def test_eligible_dispatch_rejection_requires_corrected_recipe_before_stop() -> None:
    sources = {
        "contract": " ".join(
            CONTRACT_PATH.read_text(encoding="utf-8").replace("`", "").split()
        ),
        "activation": " ".join(
            ACTIVATION_PATH.read_text(encoding="utf-8").replace("`", "").split()
        ),
        "design": " ".join(
            DESIGN_PATH.read_text(encoding="utf-8").replace("`", "").split()
        ),
    }

    for source, text in sources.items():
        assert "must execute exactly one corrected attempt" in text, source
        assert "not a terminal capability error" in text, source
        assert "missing lock prefix" in text, source
        assert "lock heartbeat curation --run-id" in text, source


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
    assert "retain it as closed history" in sources["activation"]
    assert "classify it as `regressed`" in sources["activation"]
    assert (
        "never present candidate-entry count as the issue count"
        in sources["activation"]
    )


def test_runtime_helper_does_not_own_semantic_convergence() -> None:
    contract = " ".join(CONTRACT_PATH.read_text(encoding="utf-8").split()).lower()

    assert "does not classify residuals or exact repeats" in contract
    assert "does not count candidate entries" in contract
    assert "codex owns the assertion-level finding ledger" in contract

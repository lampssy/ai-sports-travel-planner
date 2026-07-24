# Snowcast Maintainer Runtime Command Contract

## Purpose And Authority

This is the concise executable interface between the local Codex orchestrator
and the merged maintainer helper. It owns command spelling, argument order,
critical lifecycle sequences, bounded output interpretation, and dispatch-error
classification. The activation contract owns operating policy. The long design
spec records rationale and durable behavior, but it is not a command reference
for a normal scheduled cycle.

Use only a recipe below. Substitute values only from the current helper output,
the selected exact-head inventory, or a caller-created exact-base checkout. Do
not invent a family or option, translate semantic wording such as “lease” into a
command, inspect source to discover a command, or call `--help` during a cycle.
If a required operation has no recipe, stop before that operation with
`contract-mismatch`.

## Fixed Invocation

Execute every recipe by appending its `argv` to `command_prefix`. Keep the state
and project-scoped GitHub directories fixed for the whole run. A helper-created
publication input is represented only by its returned direct-child basename.

The JSON block is machine-checked against the real CLI parser. It is deliberately
repetitive where worker identity affects lease ownership so an orchestrator does
not have to derive an invocation.

<!-- runtime-command-contract:start -->
```json
{
  "schema_version": 1,
  "command_prefix": [
    "uv",
    "run",
    "--no-config",
    "python",
    "-m",
    "ops.maintainer.cli",
    "--state-dir",
    "${STATE_DIR}",
    "--gh-config-dir",
    "${GH_CONFIG_DIR}"
  ],
  "recipes": {
    "inspect_curation": {
      "argv": ["inspect", "curation"],
      "returns": ["eligible", "reviewed_continuations", "remediation_continuations", "unresolved_pushes"]
    },
    "inspect_discovery": {
      "argv": ["inspect", "discovery"],
      "returns": ["catalog_keys", "open_proposal_count", "can_create_proposal", "unresolved_pushes"]
    },
    "lock_acquire_curation": {
      "argv": ["lock", "acquire", "curation"],
      "returns": ["worker", "run_id"]
    },
    "lock_acquire_discovery": {
      "argv": ["lock", "acquire", "discovery"],
      "returns": ["worker", "run_id"]
    },
    "lock_heartbeat_curation": {
      "argv": ["lock", "heartbeat", "curation", "--run-id", "${RUN_ID}"],
      "returns": ["worker"]
    },
    "lock_heartbeat_discovery": {
      "argv": ["lock", "heartbeat", "discovery", "--run-id", "${RUN_ID}"],
      "returns": ["worker"]
    },
    "lock_release_curation": {
      "argv": ["lock", "release", "curation", "--run-id", "${RUN_ID}"],
      "returns": ["worker"]
    },
    "lock_release_discovery": {
      "argv": ["lock", "release", "discovery", "--run-id", "${RUN_ID}"],
      "returns": ["worker"]
    },
    "publication_input_title": {
      "argv": ["publication-input", "create", "--worker", "${WORKER}", "--kind", "title", "--run-id", "${RUN_ID}"],
      "stdin": "bounded UTF-8 title",
      "returns": ["basename"]
    },
    "publication_input_body": {
      "argv": ["publication-input", "create", "--worker", "${WORKER}", "--kind", "body", "--run-id", "${RUN_ID}"],
      "stdin": "bounded UTF-8 body",
      "returns": ["basename"]
    },
    "publication_input_summary": {
      "argv": ["publication-input", "create", "--worker", "${WORKER}", "--kind", "summary", "--run-id", "${RUN_ID}"],
      "stdin": "bounded UTF-8 summary",
      "returns": ["basename"]
    },
    "prepare_curation": {
      "argv": ["prepare", "curation", "--pr", "${PR}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "prepared"]
    },
    "prepare_continuation": {
      "argv": ["prepare", "continuation", "--pr", "${PR}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "continuation"]
    },
    "prepare_continuation_conflict": {
      "argv": ["prepare", "continuation", "--pr", "${PR}", "--continue-conflict", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "continuation"]
    },
    "checkpoint_remediation": {
      "argv": ["checkpoint", "remediation", "--pr", "${PR}", "--head", "${HEAD}", "--report", "${REPORT}", "--base-dir", "${BASE_DIR}", "--run-id", "${RUN_ID}"],
      "returns": ["continuation"]
    },
    "validate_curation": {
      "argv": ["validate", "curation", "--pr", "${PR}", "--reviewed-head", "${REVIEWED_HEAD}", "--report", "${REPORT}", "--base-dir", "${BASE_DIR}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "validation"]
    },
    "validate_reviewed": {
      "argv": ["validate", "reviewed", "--pr", "${PR}", "--reviewed-head", "${REVIEWED_HEAD}", "--report", "${REPORT}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "continuation"]
    },
    "validate_reviewed_adopt_existing": {
      "argv": ["validate", "reviewed", "--pr", "${PR}", "--reviewed-head", "${REVIEWED_HEAD}", "--report", "${REPORT}", "--adopt-existing", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "continuation"]
    },
    "validate_proposal": {
      "argv": ["validate", "proposal", "--candidate-key", "${CANDIDATE_KEY}", "--candidate-origin", "${CANDIDATE_ORIGIN}", "--base", "${BASE}", "--head", "${HEAD}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "validation"]
    },
    "publish_push": {
      "argv": ["publish", "push", "--pr", "${PR}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "push"]
    },
    "publish_manual_check": {
      "argv": ["publish", "manual-check", "--pr", "${PR}", "--reviewed-head", "${REVIEWED_HEAD}", "--report", "${REPORT}", "--summary-file", "${SUMMARY_FILE}", "--body-file", "${BODY_FILE}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "pr_number", "state"]
    },
    "publish_recover": {
      "argv": ["publish", "recover", "--work-id", "${WORK_ID}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "push", "continuation"]
    },
    "publish_proposal": {
      "argv": ["publish", "proposal", "--branch", "${BRANCH}", "--candidate-key", "${CANDIDATE_KEY}", "--candidate-origin", "${CANDIDATE_ORIGIN}", "--head", "${HEAD}", "--title-file", "${TITLE_FILE}", "--body-file", "${BODY_FILE}", "--summary-file", "${SUMMARY_FILE}", "--run-id", "${RUN_ID}"],
      "returns": ["work_id", "pr_number"]
    },
    "publish_outcome": {
      "argv": ["publish", "outcome", "--pr", "${PR}", "--expected-head", "${EXPECTED_HEAD}", "--state", "${OUTCOME_STATE}", "--reason", "${OUTCOME_REASON}", "--summary-file", "${SUMMARY_FILE}", "--run-id", "${RUN_ID}"],
      "returns": ["pr_number", "state", "reason"]
    },
    "publish_state": {
      "argv": ["publish", "state", "--pr", "${PR}", "--state", "${STATE}", "--reviewed-head", "${REVIEWED_HEAD}", "--summary-file", "${SUMMARY_FILE}", "--body-file", "${BODY_FILE}", "--run-id", "${RUN_ID}"],
      "returns": ["pr_number", "state"]
    },
    "publish_state_summary_only": {
      "argv": ["publish", "state", "--pr", "${PR}", "--state", "${STATE}", "--reviewed-head", "${REVIEWED_HEAD}", "--summary-file", "${SUMMARY_FILE}", "--run-id", "${RUN_ID}"],
      "returns": ["pr_number", "state"]
    },
    "publish_state_adopt_body": {
      "argv": ["publish", "state", "--pr", "${PR}", "--state", "${STATE}", "--reviewed-head", "${REVIEWED_HEAD}", "--summary-file", "${SUMMARY_FILE}", "--body-file", "${BODY_FILE}", "--adopt-body", "--run-id", "${RUN_ID}"],
      "returns": ["pr_number", "state"]
    },
    "publish_ensure_labels": {
      "argv": ["publish", "ensure-labels", "--worker", "${WORKER}", "--run-id", "${RUN_ID}"],
      "returns": ["worker"]
    }
  },
  "flows": {
    "curation_journal_recovery_through_continuation": [
      "inspect_curation",
      "inspect_discovery",
      "lock_acquire_curation",
      "lock_heartbeat_curation",
      "publish_recover",
      "lock_heartbeat_curation"
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
      "lock_release_curation"
    ],
    "curation_recovery_absent_owner_decision_after_recover": [
      "publication_input_summary",
      "lock_heartbeat_curation",
      "publish_state_summary_only",
      "lock_heartbeat_curation",
      "inspect_curation",
      "lock_heartbeat_curation",
      "lock_release_curation"
    ],
    "curation_reviewed_continuation_through_prepare": [
      "inspect_curation",
      "inspect_discovery",
      "lock_acquire_curation",
      "lock_heartbeat_curation",
      "prepare_continuation",
      "lock_heartbeat_curation"
    ],
    "curation_remediation_continuation_through_prepare": [
      "inspect_curation",
      "inspect_discovery",
      "lock_acquire_curation",
      "lock_heartbeat_curation",
      "prepare_continuation",
      "lock_heartbeat_curation"
    ],
    "curation_ordinary_pr_through_prepare": [
      "inspect_curation",
      "inspect_discovery",
      "lock_acquire_curation",
      "lock_heartbeat_curation",
      "prepare_curation",
      "lock_heartbeat_curation"
    ],
    "curation_waiting_ci_pending": [
      "inspect_curation",
      "inspect_discovery"
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
      "lock_release_curation"
    ]
  },
  "dispatch_error_classification": {
    "reason": "invalid-command",
    "stage": "dispatch",
    "classification": "orchestration-command-invalid",
    "retry_policy": {
      "require_completed_dispatch_rejection": true,
      "require_mutation_occurred_false": true,
      "repeat_malformed_argv": false,
      "corrected_registered_recipe_attempts": 1,
      "same_intended_recipe_only": true,
      "allow_help_or_capability_switch": false
    }
  }
}
```
<!-- runtime-command-contract:end -->

## Placeholder Rules

- `${STATE_DIR}` is `$HOME/.local/state/snowcast-maintainer`.
- `${GH_CONFIG_DIR}` is `$HOME/.config/gh-lampssy-snowcast`.
- `${RUN_ID}` is copied exactly from the successful matching `lock acquire`
  result. It is never generated, shortened, logged publicly, or reused by
  another worker.
- `${PR}`, heads, report path, work ID, candidate identity, and branch come
  from the current helper inventory or the result of the immediately preceding
  helper capability.
- `${BASE_DIR}` is a caller-created detached clean checkout whose `HEAD`
  exactly equals the prepare-time `base_head`.
- `${TITLE_FILE}`, `${BODY_FILE}`, and `${SUMMARY_FILE}` are basenames returned
  by `publication-input create`, not caller-chosen paths.
- `${STATE}`, `${OUTCOME_STATE}`, and `${OUTCOME_REASON}` are chosen only from
  the allowlisted state/reason combinations in the activation contract.

## Allowed Next Steps

| Completed recipe | Only allowed next step |
| --- | --- |
| `inspect_*` | bounded no-op, select one safe item, or acquire the matching worker lock |
| `lock_acquire_*` | copy `run_id`, heartbeat, then run the selected worker capability |
| `lock_heartbeat_*` | continue the already selected sequence; it grants no new authority |
| `prepare_curation` | normalize/review the exact returned prepared head |
| `prepare_continuation*` | obey only the returned continuation kind/result |
| `checkpoint_remediation` | fresh exact-head review, another bounded fix, or safe stop |
| `validate_reviewed*` | final deterministic validation or an allowed reviewed-only handoff |
| `validate_curation` | `publish_push` for the exact validated work |
| `validate_proposal` | create publication inputs, then `publish_proposal` |
| `publication_input_*` | pass that basename only to its selected publication recipe |
| `publish_push` | create fresh inputs, then publish exact-head lifecycle state |
| `publish_recover` | obey its continuation/publication result; never select fresh work |
| other `publish_*` | reinspect when required, then cleanup; never start semantic work |
| `lock_release_*` | final Triage and private diagnostic recording only |

## Completion And Branching Rules

Every helper invocation has one process and one JSON result. If the orchestration
layer yields a cell ID, resume it. If that cell yields an underlying command
session ID, poll that same session until it exits. Accumulate all chunks and
parse JSON only after exit. Never repeat a mutating recipe because an early
chunk was empty.

All successful results contain `status=ok` and a bounded `outcome`. All failures
contain `status=error`, `reason`, `stage`, and a bounded `outcome`; only an
allowlisted `check` and `kind` may accompany them. Recipe-specific `returns`
list the fields that authorize the next semantic branch. Missing fields stop
the cycle; prose, automation memory, or prior conclusions cannot fill them in.

This helper interface does not classify residuals or exact repeats and does not
count candidate entries. Codex owns the assertion-level finding ledger,
candidate inventory, repeat streak, and convergence decision; the helper only
checks objective command, state, head, scope, validation, and publication
preconditions for the resulting requested action.

The five curation lifecycle scenarios freeze their high-risk sequence prefixes;
waiting-CI has separate pending and successful branches:

- journal recovery is exclusive. After `publish recover`, branch only on its
  returned curation `continuation`. For `validation_status=absent`, inspect only
  the exact reviewed report: an explicit unresolved owner/model choice uses the
  `curation_recovery_absent_owner_decision_after_recover` suffix with
  `${STATE}=maintainer:owner-decision`; otherwise use the
  `curation_recovery_absent_manual_check_after_recover` suffix with the exact
  canonical Resulting Graph in the body. An absent, unknown, or mismatched
  continuation stops and releases. Never select fresh work;
- reviewed and remediation continuations use the same helper command, then
  branch only on the returned `continuation.kind` and `continuation.result`;
- an ordinary PR uses `prepare curation`, never `prepare continuation`;
- pending CI is read-only and acquires no lock;
- successful unchanged waiting-CI creates fresh publication inputs before
  requesting `maintainer:ready`.

After every successful acquisition, heartbeat before and after each capability
and at least every five minutes during Codex work. Release exactly once in a
`finally` path if and only if acquisition succeeded. `lock-busy` before
acquisition is a terminal no-op and never triggers release.

## Dispatch Errors

`reason=invalid-command` at `stage=dispatch` means the orchestrator supplied a
command outside this interface or malformed a recipe. Report it as
`orchestration-command-invalid`, not as PR invalidity, validation failure, or
non-convergence. Only after the underlying process has completed and returned
that structured dispatch rejection with
`outcome.mutation_occurred=false`, reload this exact contract and permit one
corrected execution of the same registered recipe with only authorized
substitutions. Never repeat the malformed argv, probe with `--help`, inspect
implementation source, infer a recipe, or switch capabilities. If the intended
recipe cannot be identified exactly, mutation status is missing or true, the
corrected execution returns a second dispatch rejection, or execution/capture
is uncertain, preserve any existing continuation or journal, release only a
lease this run actually acquired, and stop for contract correction.

An `invalid-command` returned after a non-dispatch stage is a helper/state gate,
not this command-authoring classification. It never receives a corrected-recipe
attempt. Preserve the helper’s stage and bounded allowlisted diagnostics.

## Change Rule

Any CLI route or argument change must update this contract and its parser-backed
tests in the same PR. Add deterministic lifecycle code only if this explicit
interface still produces recurring sequencing failures in observed scheduled
runs.

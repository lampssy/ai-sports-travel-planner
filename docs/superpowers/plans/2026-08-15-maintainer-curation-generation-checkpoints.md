# Maintainer Curation Generation Checkpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace brittle pre-push reviewed/remediation continuations with one generation-based, idempotent, recoverable curation checkpoint timeline while preserving all existing external-mutation journals and owner gates.

**Architecture:** Store one bounded Pydantic-validated document per curation generation under the private maintainer state directory and derive the current generation from the highest valid generation number. Record local checkpoints as two-phase append-only events, expose typed recipe IDs and substitutions for retries, and adapt reviewed/validated generation authority into the unchanged push, manual-check, CI, and publication boundaries.

**Tech Stack:** Python 3.12, Pydantic v2, argparse, Git refs, pytest, Ruff, Markdown runtime contract, local Codex skill.

## Global Constraints

- Redesign pre-push curation only; push journals, CI continuations, terminal-publication recovery, discovery, GitHub labels, approval, and merge behavior remain unchanged.
- Archive and reset existing unpublished curation work rather than importing it into generation authority.
- Keep each generation document within the existing 65,536-byte private-state limit.
- Use deterministic logic only; no LLM output may grant helper authority or widen scope.
- Use structured `recipe_id` plus typed substitutions; never emit a shell command as `next_action`.
- Set `mutation_occurred=true` after the first durable local checkpoint mutation.
- Reserve `invalid-command` for malformed CLI syntax or unregistered routes.
- Do not add dependencies.
- Keep external mutation fail-closed and helper-only. The maintainer must never approve or merge.

---

### Task 1: Generation State Model And ADR

**Files:**
- Create: `ops/maintainer/curation_state.py`
- Create: `tests/test_maintainer_curation_state.py`
- Create: `docs/architecture/adr/0020-use-generation-based-pre-push-curation-authority.md`
- Modify: `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- Modify: `docs/superpowers/specs/2026-08-15-maintainer-curation-generation-checkpoints-design.md`

**Interfaces:**
- Produces: `CurationGenerationStore`, `CurationGeneration`, `CurationCheckpointStage`, typed event models, `project_generation()`, `ReviewedCurationAuthority`, and `ValidatedCurationAuthority`.
- Consumes: `GuardedSyncResult`, `RunLease`, and private atomic-state helpers already used by `StateStore`.

- [ ] **Step 1: Write failing strict-model and projection tests**

Cover generation identity, ordered event sequence, incomplete transactions,
latest-head projection, multiple delta/review rounds, validation authority, and
the per-document byte limit. Use concrete event factories and assertions such
as:

```python
def test_newer_delta_checkpoint_supersedes_reviewed_head_within_generation() -> None:
    generation = generation_with_events(
        completed_checkpoint(1, stage="reviewed", head=SHA_B),
        completed_checkpoint(2, stage="delta-validated", head=SHA_C),
    )

    projection = project_generation(generation)

    assert projection.latest_head == SHA_C
    assert projection.reviewed_authority is None
    assert projection.next_action.recipe_id == "checkpoint_curation_reviewed"
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py -q
```

Expected: collection fails because `ops.maintainer.curation_state` does not yet
exist.

- [ ] **Step 3: Implement typed generation events and pure projection**

Define discriminated Pydantic events for:

```python
class CurationCheckpointStage(StrEnum):
    DELTA_VALIDATED = "delta-validated"
    REVIEWED = "reviewed"

class CurationGeneration(BaseModel):
    schema_version: Literal[2]
    work_id: str
    pr_number: int
    generation_number: int
    generation_id: str
    created_at: datetime
    selected_head: str
    target_branch: str
    sync: GuardedSyncResult
    events: tuple[CurationGenerationEvent, ...]

def project_generation(
    generation: CurationGeneration,
) -> CurationGenerationProjection: ...
```

Validate monotonically increasing event sequence numbers, deterministic
transaction IDs, one unmatched `checkpoint_started` at most, exact stage/head
relationships, and terminal-event finality. Produce separate reviewed and
validated authority values so manual-check cannot be mistaken for validated
publication.

- [ ] **Step 4: Implement bounded private generation storage**

Implement `CurationGenerationStore` with:

```python
def list_generations(self, work_id: str) -> tuple[CurationGeneration, ...]: ...
def load_current(self, work_id: str) -> CurationGeneration | None: ...
def start_generation(self, generation: CurationGeneration, lease: RunLease) -> None: ...
def append_event(
    self,
    work_id: str,
    generation_id: str,
    event: CurationGenerationEvent,
    lease: RunLease,
) -> CurationGeneration: ...
```

Store files below
`curation-generations/{work_id}/{generation_number}-{generation_id}.json`, use
the existing private-directory and atomic-write protections, and derive current
authority from the highest validated generation number.

- [ ] **Step 5: Add ADR 0020 and mark the superseded ADR 0011 decision**

Record that ADR 0020 supersedes only ADR 0011's separate reviewed/remediation
continuation design. Preserve ADR 0011's local control plane, helper-only
mutation, external push journals, post-push CI, terminal publication, and
never-approve/never-merge decisions.

- [ ] **Step 6: Run focused model tests and Ruff**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer/curation_state.py tests/test_maintainer_curation_state.py
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add ops/maintainer/curation_state.py tests/test_maintainer_curation_state.py docs/architecture/adr/0011-local-codex-maintainer-control-plane.md docs/architecture/adr/0020-use-generation-based-pre-push-curation-authority.md docs/superpowers/specs/2026-08-15-maintainer-curation-generation-checkpoints-design.md
git commit -m "feat: model curation checkpoint generations"
```

### Task 2: Typed Errors, Retry Actions, And Inspection

**Files:**
- Modify: `ops/maintainer/errors.py`
- Modify: `ops/maintainer/inspection.py`
- Modify: `ops/maintainer/capabilities.py`
- Modify: `tests/test_maintainer_errors.py`
- Modify: `tests/test_maintainer_inspection.py`
- Modify: `tests/test_maintainer_cli.py`

**Interfaces:**
- Consumes: `CurationGenerationStore` and `project_generation()` from Task 1.
- Produces: typed operational error reasons, `CurationGenerationSummary`, and structured `next_action` output.

- [ ] **Step 1: Write failing error-payload and generation-inspection tests**

Add expectations for:

```python
assert payload == {
    "status": "error",
    "reason": "local-recovery-required",
    "stage": "validate",
    "retryable": True,
    "next_action": {
        "recipe_id": "checkpoint_curation_reviewed",
        "substitutions": {
            "pr": 37,
            "generation_id": GENERATION_ID,
            "head": SHA_C,
            "report": REPORT,
        },
    },
}
```

Also assert that curation inspection returns `generations`, not
`reviewed_continuations` or `remediation_continuations`, and that unresolved
push/CI/publication authority still outranks pre-push generation recovery.

- [ ] **Step 2: Run focused tests and confirm failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_errors.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py -k 'generation or retryable or next_action' -q
```

Expected: failures show missing typed reasons and inspection fields.

- [ ] **Step 3: Add explicit operational error reasons**

Extend `ErrorReason` with `STALE_BASE`, `LEASE_CONFLICT`,
`CHECKPOINT_CONFLICT`, `LOCAL_RECOVERY_REQUIRED`, `UNSAFE_REPOSITORY`, and
`STATE_MIGRATION_REQUIRED`. Extend `MaintainerError` with typed `retryable` and
`next_action` fields. Keep `next_action` a discriminated Pydantic model from
`curation_state.py`; do not accept arbitrary argv or shell text.

Update `safe_error()` so `StateStoreError`, `RepositorySafetyError`, and
validation-state conflicts no longer collapse to `invalid-command`. Preserve
existing public-safe detail filtering.

- [ ] **Step 4: Replace continuation summaries with generation summaries**

Update `CurationInventory` and `inspect_curation()` to accept current generation
projections. Suppress ordinary eligibility for a PR with current generation
authority. Return exactly one current generation summary per PR with stage,
head, base, retryability, and next action.

- [ ] **Step 5: Wire read-only generation inspection**

Update `handle_inspect_curation()` to retain current terminal-publication,
push-journal, and CI ordering, then load generation state only when those gates
permit pre-push inspection. Legacy-state detection should return
`state-migration-required` without mutation.

- [ ] **Step 6: Run focused tests and Ruff**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_errors.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer/errors.py ops/maintainer/inspection.py ops/maintainer/capabilities.py tests/test_maintainer_errors.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py
```

- [ ] **Step 7: Commit**

```bash
git add ops/maintainer/errors.py ops/maintainer/inspection.py ops/maintainer/capabilities.py tests/test_maintainer_errors.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py
git commit -m "feat: inspect curation generation recovery"
```

### Task 3: Unified Generation-Aware Preparation

**Files:**
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/git_ops.py`
- Modify: `ops/maintainer/cli.py`
- Modify: `tests/test_maintainer_cli.py`
- Modify: `tests/test_maintainer_git_ops.py`

**Interfaces:**
- Consumes: current generation projection and typed next actions.
- Produces: one `prepare curation` route that creates, restores, replays, or invalidates generations.

- [ ] **Step 1: Write failing preparation-path tests**

Cover:

- first preparation creates generation one;
- same remote head/base plus reviewed authority returns `validation-only`;
- same remote head/base plus a failed validation returns
  `validation-remediation` with a typed descendant-head delta action;
- same remote head with advanced `main` creates generation two and returns
  `review-required`;
- changed remote head starts clean without blending saved local work;
- interrupted conflict resumes only through `--continue-conflict` on
  `prepare curation`; and
- missing checkpoint object invalidates local authority and restarts safely.

The core regression must model PR #37 explicitly but with synthetic SHAs:

```python
assert first.selected_head == second.selected_head
assert first.sync.base_head != second.sync.base_head
assert second.generation_number == first.generation_number + 1
```

- [ ] **Step 2: Run preparation tests and confirm failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py -k 'prepare and generation' -q
```

- [ ] **Step 3: Generalize replay input away from legacy continuation types**

Introduce a small immutable recovery value in `git_ops.py` containing selected
head, base, checkpoint head/ref, squash ref, report path, and guarded sync.
Refactor existing replay mechanics to consume this value. Do not change branch,
path, mode, ancestry, or bounded-conflict protections.

- [ ] **Step 4: Implement generation-aware `handle_prepare_curation()`**

Make `prepare curation` inspect current generation authority and choose one of
the spec outcomes. Begin a fresh run-local `WorkState` for the owned lease, but
do not treat `WorkState` as cross-run recovery authority. Append the new
generation before returning a prepared/review-required result.

- [ ] **Step 5: Remove the `prepare continuation` CLI and handler route**

Delete its parser, `HANDLERS` entry, and active capability path after all replay
logic is reachable through `prepare curation`. Retain only migration-specific
legacy decoding needed by Task 6.

- [ ] **Step 6: Run focused tests and Ruff**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer/capabilities.py ops/maintainer/git_ops.py ops/maintainer/cli.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py
```

- [ ] **Step 7: Commit**

```bash
git add ops/maintainer/capabilities.py ops/maintainer/git_ops.py ops/maintainer/cli.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py
git commit -m "feat: prepare curation generations automatically"
```

### Task 4: Idempotent Two-Phase Checkpoint Capability

**Files:**
- Modify: `ops/maintainer/curation_state.py`
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/git_ops.py`
- Modify: `ops/maintainer/cli.py`
- Modify: `tests/test_maintainer_curation_state.py`
- Modify: `tests/test_maintainer_cli.py`
- Modify: `tests/test_maintainer_git_ops.py`

**Interfaces:**
- Consumes: active generation and exact prepare-time base.
- Produces: `checkpoint curation --stage delta-validated|reviewed` and deterministic generation refs.

- [ ] **Step 1: Write failing happy-path and fault-injection tests**

Test:

- first delta checkpoint;
- reviewed checkpoint on the exact latest head;
- identical retry returns `already-completed`;
- newer delta head creates a new transaction inside the same generation;
- crash after `checkpoint_started` resumes ref creation;
- crash after ref creation resumes `checkpoint_completed`;
- conflicting request returns `checkpoint-conflict`;
- incomplete different request returns `local-recovery-required` with exact
  recipe/substitutions; and
- `mutation_occurred` is true after the started event even when later work
  fails.

- [ ] **Step 2: Run checkpoint tests and confirm failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py -k checkpoint -q
```

- [ ] **Step 3: Add deterministic generation checkpoint refs**

Replace stage-specific reviewed/remediation ref creation with:

```python
def checkpoint_curation_generation(
    self,
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    checkpoint_head: str,
    generation_id: str,
    transaction_id: str,
) -> CurationCheckpointRefs: ...
```

Use helper-owned generation/transaction prefixes and idempotently verify an
existing exact ref. Keep the synthetic squash/replay commit rooted at the
prepare-time base.

- [ ] **Step 4: Implement `handle_checkpoint_curation()`**

Perform pure preflight and delta validation first. Append
`checkpoint_started`, immediately mark the tracker mutated, create/verify refs,
then append `checkpoint_completed`. For `reviewed`, require the requested head
to equal the latest completed delta/prepared head and rely on the caller's
semantic-review declaration exactly as the old reviewed checkpoint did.

- [ ] **Step 5: Replace legacy checkpoint routes**

Add parser arguments `--pr`, `--generation-id`, `--head`, `--report`,
`--base-dir`, `--stage`, and `--run-id`. Remove `checkpoint remediation` and
`validate reviewed` from active parser/handler routes.

- [ ] **Step 6: Run focused tests and Ruff**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer/curation_state.py ops/maintainer/capabilities.py ops/maintainer/git_ops.py ops/maintainer/cli.py tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py
```

- [ ] **Step 7: Commit**

```bash
git add ops/maintainer/curation_state.py ops/maintainer/capabilities.py ops/maintainer/git_ops.py ops/maintainer/cli.py tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py
git commit -m "feat: checkpoint curation generations idempotently"
```

### Task 5: Final Validation And External-Authority Handoff

**Files:**
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/state.py`
- Modify: `ops/maintainer/curation_state.py`
- Modify: `tests/test_maintainer_cli.py`
- Modify: `tests/test_maintainer_state.py`
- Modify: `tests/test_maintainer_validation.py`

**Interfaces:**
- Consumes: latest reviewed generation checkpoint.
- Produces: validation events, `ReviewedCurationAuthority`, `ValidatedCurationAuthority`, and unchanged push/manual-check journal input.

- [ ] **Step 1: Write failing validation and handoff tests**

Cover validation success/failure/idempotency, validation-only resume, bounded
same-generation validation remediation, ordinary push requiring validated
authority, manual-check requiring reviewed authority, push journal winning
after authorization, and generation consumption only after the journal is
durable.

Fault-inject between journal creation and generation consumption and assert
inspection exposes push recovery, never pre-push generation recovery.

- [ ] **Step 2: Run focused tests and confirm failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_cli.py tests/test_maintainer_state.py tests/test_maintainer_validation.py -k 'validation or manual_check or push' -q
```

- [ ] **Step 3: Make final validation generation-aware**

Load the active generation projection, require its exact reviewed authority,
run the existing trusted-base validator, and append either `validation_failed`
or `validation_passed`. Keep run-local `WorkState` populated for unchanged
post-push CI/publication code.

On `validation_failed`, retain the reviewed authority but project a distinct
failed-validation stage. The next owned preparation restores that head and
returns a typed `checkpoint_curation_delta` action whose
`caller_created_descendant_head=true` flag permits only a bounded clean
descendant correction. Require a fresh exact-head review and reviewed
checkpoint before final validation is retried.

- [ ] **Step 4: Adapt push and manual-check publication**

Replace `_consume_continuation_for_journal()` with a generation operation that
accepts either reviewed or validated typed authority as required. Persist the
existing push journal first, then append `generation_consumed`. If interrupted,
the push journal remains the sole recovery authority.

- [ ] **Step 5: Remove active reviewed/remediation dependencies from push paths**

Ensure ordinary push, manual-check, recover, and readiness do not load legacy
reviewed/remediation records. Do not alter `PushJournal`, `CiContinuation`, or
`TerminalPublicationIntent` schemas.

- [ ] **Step 6: Run focused tests and Ruff**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_cli.py tests/test_maintainer_state.py tests/test_maintainer_validation.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer/capabilities.py ops/maintainer/state.py ops/maintainer/curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_state.py tests/test_maintainer_validation.py
```

- [ ] **Step 7: Commit**

```bash
git add ops/maintainer/capabilities.py ops/maintainer/state.py ops/maintainer/curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_state.py tests/test_maintainer_validation.py
git commit -m "feat: hand validated generations to publication"
```

### Task 6: Explicit Legacy-State Archival Migration

**Files:**
- Modify: `ops/maintainer/curation_state.py`
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/git_ops.py`
- Modify: `ops/maintainer/cli.py`
- Modify: `ops/maintainer/state.py`
- Modify: `tests/test_maintainer_curation_state.py`
- Modify: `tests/test_maintainer_cli.py`
- Modify: `tests/test_maintainer_git_ops.py`
- Modify: `tests/test_maintainer_state.py`

**Interfaces:**
- Produces: explicit `migrate curation-state --archive-legacy` capability and state-format marker.
- Consumes: legacy file/ref locations only for validated archival.

- [ ] **Step 1: Write failing migration and rollback-boundary tests**

Test refusal for an active curation lease and unresolved external recovery,
recognized file/ref archival, archive-manifest hashes/counts, byte-identical
discovery/push/CI/publication state, idempotent rerun, read-only
`state-migration-required`, and rollback refusal after any generation starts.

- [ ] **Step 2: Run migration tests and confirm failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py tests/test_maintainer_state.py -k migration -q
```

- [ ] **Step 3: Implement state-format detection and archival**

Add a strict format marker and timestamped
`legacy-curation-v1/{archive_id}/` directory. Validate ownership, regular-file
modes, recognized paths, and bounded file sizes before moving anything. Write a
manifest with SHA-256 digests and counts, then write the format marker
atomically.

- [ ] **Step 4: Implement helper-owned legacy ref archival**

Move only recognized reviewed/remediation/prepared pre-push refs into the
helper archive namespace using one checked Git ref transaction. Do not touch
backup refs needed by an unresolved push or any CI-repair refs. Return bounded
counts only.

- [ ] **Step 5: Add the explicit migration CLI route**

Register `migrate curation-state --archive-legacy`. It must run without an
active lease, take the private transition mutex, refuse unresolved dependent
external recovery, and never contact GitHub.

- [ ] **Step 6: Remove unused active legacy transition code**

After all call sites use generations, delete reviewed/remediation transition,
adoption, promotion, and inspection methods. Retain only the minimal legacy
schema/path recognition needed to archive v1 state. Delete obsolete tests
rather than translating assertions for behavior that no longer exists.

- [ ] **Step 7: Run focused tests and Ruff**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py tests/test_maintainer_state.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer/curation_state.py ops/maintainer/capabilities.py ops/maintainer/git_ops.py ops/maintainer/cli.py ops/maintainer/state.py tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py tests/test_maintainer_state.py
```

- [ ] **Step 8: Commit**

```bash
git add ops/maintainer/curation_state.py ops/maintainer/capabilities.py ops/maintainer/git_ops.py ops/maintainer/cli.py ops/maintainer/state.py tests/test_maintainer_curation_state.py tests/test_maintainer_cli.py tests/test_maintainer_git_ops.py tests/test_maintainer_state.py
git commit -m "feat: archive legacy curation continuations"
```

### Task 7: Runtime Contract, Operating Docs, And Installed Skill

**Files:**
- Modify: `docs/operating-model/maintainer-runtime-command-contract.md`
- Modify: `docs/operating-model/local-maintainer-activation.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/engineering-notes.md`
- Modify: `tests/test_maintainer_runtime_command_contract.py`
- Modify: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`

**Interfaces:**
- Consumes: final CLI routes and payloads from Tasks 2-6.
- Produces: the sole registered command recipes and aligned installed orchestration rules.

- [ ] **Step 1: Write failing runtime-contract tests**

Update expected routes and flows so they contain `prepare_curation`,
`checkpoint_curation_delta`, `checkpoint_curation_reviewed`,
`validate_curation`, and `migrate_curation_state`. Assert legacy
`prepare_continuation`, `checkpoint_remediation`, and `validate_reviewed`
recipes are absent. Assert every retry action references a registered recipe.

- [ ] **Step 2: Run contract tests and confirm failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_runtime_command_contract.py -q
```

- [ ] **Step 3: Rewrite the embedded runtime command contract**

Keep command-prefix and post-push flows unchanged. Replace only pre-push
curation recipes, critical sequences, allowed-next-step rows, retry
classification, and migration activation. The contract must state that typed
`next_action` is authoritative and that only `retryable=true` permits a bounded
pre-push retry.

- [ ] **Step 4: Update operating and architecture documentation**

Replace separate continuation recovery priority with one generation recovery
step after external journals and CI. Document the activation sequence: pause
curation automation, inspect both workers, resolve external recovery, migrate,
inspect, run a manual smoke, then re-enable.

- [ ] **Step 5: Update the installed maintainer skill**

Read the merged-style repo contract from the branch, then replace legacy
pre-push instructions and command names in
`/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`. Keep helper-only
mutation, exact lease, untrusted-input, heartbeat, push/CI/publication, no
approval, and no merge rules unchanged.

- [ ] **Step 6: Verify contract, docs, and skill alignment**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_runtime_command_contract.py -q
git diff --check
rg -n "prepare continuation|checkpoint remediation|validate reviewed" docs/operating-model /Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md
```

Expected: tests pass; any remaining legacy phrases appear only in historical
design/ADR context explicitly marked superseded.

- [ ] **Step 7: Commit repository documentation and tests**

```bash
git add docs/operating-model/maintainer-runtime-command-contract.md docs/operating-model/local-maintainer-activation.md docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/engineering-notes.md tests/test_maintainer_runtime_command_contract.py
git commit -m "docs: activate generation-based curation recovery"
```

### Task 8: Full Verification, Advisory Feature Review, And Activation Handoff

**Files:**
- Modify as required by review findings only.
- Verify: all files changed in Tasks 1-7.

**Interfaces:**
- Produces: release-quality branch, verified installed skill, and explicit owner activation commands.

- [ ] **Step 1: Run the full maintainer test suite**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_cli.py tests/test_maintainer_curation_state.py tests/test_maintainer_errors.py tests/test_maintainer_git_ops.py tests/test_maintainer_inspection.py tests/test_maintainer_runtime.py tests/test_maintainer_runtime_command_contract.py tests/test_maintainer_state.py tests/test_maintainer_validation.py -q
```

- [ ] **Step 2: Run repository-wide static verification**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check ops/maintainer tests/test_maintainer_*.py
UV_CACHE_DIR=.uv-cache uv run --no-config ruff format --check ops/maintainer tests/test_maintainer_*.py
git diff --check
```

- [ ] **Step 3: Run fault-injection and contract tests independently**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_maintainer_curation_state.py tests/test_maintainer_runtime_command_contract.py -q
```

- [ ] **Step 4: Run backend-api, security-privacy, and observability-ops feature reviews**

Review the exact branch diff and classify every finding. Resolve all Blocker and
High findings. Resolve Medium findings that affect state correctness,
idempotency, privacy, or operator recovery; record only genuinely optional
follow-ups.

- [ ] **Step 5: Re-run affected focused and full verification after review fixes**

Repeat Steps 1-3 after the final code change. Do not reuse pre-fix results.

- [ ] **Step 6: Verify the installed skill against the final contract**

Confirm the skill contains only registered pre-push recipes and still retains
all unchanged external mutation and owner-control safeguards.

- [ ] **Step 7: Commit final review fixes if any**

```bash
git add ops/maintainer tests/test_maintainer_*.py docs/architecture/adr docs/operating-model docs/engineering-notes.md docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/superpowers/specs/2026-08-15-maintainer-curation-generation-checkpoints-design.md
git commit -m "fix: harden curation generation recovery"
```

Skip this commit when the review produces no changes.

- [ ] **Step 8: Prepare the activation handoff**

Report exact verification totals and the owner sequence to pause the automation,
inspect for external recovery, run the migration command, inspect the new state,
run one manual maintainer cycle, and re-enable scheduling. Do not run migration
against the owner's live state automatically unless the owner explicitly asks.

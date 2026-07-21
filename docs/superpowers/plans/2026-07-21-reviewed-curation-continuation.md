# Reviewed Curation Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve an exact reviewed-but-unpushed curation result across runs, replay it safely after `main` advances, and permit one bounded allowed-path conflict remediation followed by a fresh independent full review.

**Architecture:** Add an owner-private `ReviewedContinuation` record beside ordinary work state and push journals. The helper checkpoints exact reviewed commits with persistent reviewed and squash refs, exposes safe continuation inventory, and restores or replays the checkpoint under a successor lease. The existing push journal remains the only authority after push authorization.

**Tech Stack:** Python 3.12, Pydantic v2, Git plumbing and worktrees, pytest, Ruff, existing `ops.maintainer` CLI and state store.

## Global Constraints

- Classification: `review-gated`; this changes scheduled-job reliability, local persistence, and branch rewrite safety.
- Developer Decision Checkpoint: resolved by the owner in favor of helper-owned continuation plus one bounded catalog/report conflict-remediation pass.
- Exact unchanged reviewed commits may skip semantic re-review and rerun only missing deterministic/finalization gates.
- Any replayed head receives one fresh independent full review before validation or publication.
- Conflict resolution is limited to the helper-reported allowed curation paths; production code, schema semantics, maintainer control-plane files, and broad conflicts stop.
- The helper owns refs, state transitions, replay completion, scope checks, push authorization, and publication. Codex owns semantic resolution and review.
- Never approve or merge a PR.
- No new dependency.
- ADR status: no new ADR; ADR 0011's Codex/helper ownership boundary is unchanged.
- Advisory design review: AI/LLM reliability, security/privacy, observability/ops, and release/change management completed with no unresolved Blocker or High finding.
- Advisory feature review: required before final handoff.

---

### Task 1: Persist and inspect reviewed continuations

**Files:**
- Modify: `ops/maintainer/state.py`
- Modify: `ops/maintainer/inspection.py`
- Modify: `ops/maintainer/capabilities.py`
- Test: `tests/test_maintainer_state.py`
- Test: `tests/test_maintainer_inspection.py`
- Test: `tests/test_maintainer_cli.py`

**Interfaces:**
- Produces: `ContinuationStatus`, `ContinuationValidationStatus`, `ReviewedContinuation`, `StateStore.load_continuation()`, `StateStore.list_continuations_for_inspection()`, `StateStore.save_continuation()`, `StateStore.adopt_continuation()`, and `CurationInventory.reviewed_continuations`.
- Consumes: existing `RunLease`, `GuardedSyncResult`, owner-private atomic JSON helpers, and curation PR safety facts.

- [ ] **Step 1: Write failing strict-model and transition tests**

Add tests that construct the desired record and prove strict validation, owner-private persistence, one active record per PR, successor adoption, old-run fencing, and terminal-state rejection:

```python
def _continuation(lease: RunLease) -> ReviewedContinuation:
    return ReviewedContinuation(
        work_id="curation-pr-42",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=NOW,
        pr_number=42,
        selected_head=SHA_1,
        reviewed_head=SHA_3,
        report_path="docs/catalog-curation/fr-les-arcs.json",
        sync=_work_state(lease, WorkPhase.REVIEWED).sync,
        reviewed_ref="refs/snowcast-maintainer/reviewed/pr-42/111111111111-333333333333",
        squash_ref="refs/snowcast-maintainer/continuations/pr-42/444444444444-333333333333",
        status=ContinuationStatus.AVAILABLE,
        validation_status=ContinuationValidationStatus.NOT_RUN,
    )

def test_successor_adopts_available_continuation_and_fences_origin(tmp_path: Path):
    origin = RunLease.acquire(tmp_path, "curation")
    store = StateStore(tmp_path)
    store.save_continuation(_continuation(origin), origin)
    origin.release()
    successor = RunLease.acquire(tmp_path, "curation")

    adopted = store.adopt_continuation("curation-pr-42", successor)

    assert adopted.origin_run_id == origin.run_id
    assert adopted.recovery_run_id == successor.run_id
    with pytest.raises(LeaseOwnershipError):
        store.save_continuation(_continuation(origin), origin)
```

- [ ] **Step 2: Run the focused state tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_state.py -k continuation
```

Expected: collection/import failure because continuation models and store methods do not exist.

- [ ] **Step 3: Implement the minimal continuation state model and atomic transitions**

Add strict enums and model:

```python
class ContinuationStatus(StrEnum):
    AVAILABLE = "available"
    RESOLVING = "resolving"
    VALIDATED = "validated"
    CONSUMED = "consumed"
    INVALIDATED = "invalidated"


class ContinuationValidationStatus(StrEnum):
    NOT_RUN = "not-run"
    FAILED = "failed"
    PASSED = "passed"


class ReviewedContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(pattern=_ID_PATTERN.pattern)
    origin_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    recovery_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    updated_at: datetime
    pr_number: int = Field(ge=1)
    selected_head: str = Field(pattern=_SHA_PATTERN)
    reviewed_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    )
    sync: GuardedSyncResult
    reviewed_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)
    status: ContinuationStatus
    validation_status: ContinuationValidationStatus
```

Store records under `state_dir / "continuations"`. Require the active curation lease for creation, adoption, updates, invalidation, and consumption. Allow a successor to replace only `recovery_run_id`, `updated_at`, and a legal status/validation transition. Reject a second active record with different immutable facts.

- [ ] **Step 4: Write failing safe-inventory tests**

Add `ReviewedContinuationSummary` tests proving the curation inventory includes only safe fields, reports whether the current labels permit resumption, and leaves unrelated eligible PRs visible. A matching unresolved push journal must suppress continuation resumption because post-push recovery has priority.

```python
assert summary.model_dump() == {
    "pr_number": 42,
    "selected_head": SHA_A,
    "reviewed_head": SHA_B,
    "base_head": SHA_C,
    "report_path": "docs/catalog-curation/fr-les-arcs.json",
    "validation_status": "failed",
    "resumable": True,
}
```

- [ ] **Step 5: Run the inspection tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_inspection.py -k continuation
```

Expected: failure because `CurationInventory` has no continuation summaries.

- [ ] **Step 6: Implement safe continuation inspection**

Extend `inspect_curation()` to accept reviewed continuations and map them to matching open PRs. Mark a summary resumable only when the PR is otherwise a safe curation candidate and has no pause label. Keep paused summaries visible with `resumable=False`. In `handle_inspect_curation()`, load continuations read-only and pass them into inspection. Do not serialize run IDs, refs, local paths, timestamps, or sync internals.

- [ ] **Step 7: Run Task 1 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_state.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py -k 'continuation or inspect_curation'
uv run --no-config ruff check ops/maintainer/state.py ops/maintainer/inspection.py ops/maintainer/capabilities.py tests/test_maintainer_state.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/state.py ops/maintainer/inspection.py ops/maintainer/capabilities.py tests/test_maintainer_state.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py
git commit -m "feat: persist reviewed curation continuations"
```

### Task 2: Checkpoint reviewed heads and replay one squashed delta

**Files:**
- Modify: `ops/maintainer/git_ops.py`
- Test: `tests/test_maintainer_git_ops.py`

**Interfaces:**
- Consumes: `ReviewedContinuation`, `GuardedSyncResult`, existing intent builders, safe curation-path rules, and repository identity checks.
- Produces: `ReviewedCheckpointRefs`, `ContinuationReplayResult`, `GitRepository.checkpoint_reviewed_continuation()`, `GitRepository.prepare_reviewed_continuation()`, and `GitRepository.continue_reviewed_conflict()`.

- [ ] **Step 1: Write failing real-Git tests for checkpoint refs**

Test that checkpointing verifies the prepared lineage and creates two create-only refs:

```python
refs = repository.checkpoint_reviewed_continuation(
    pull_request,
    sync,
    reviewed_head,
)
assert _git(checkout, "rev-parse", refs.reviewed_ref) == reviewed_head
assert _git(checkout, "rev-parse", f"{refs.squash_ref}^" ) == sync.base_head
assert _git(checkout, "show", "-s", "--format=%T", refs.squash_ref) == _git(
    checkout, "show", "-s", "--format=%T", reviewed_head
)
```

Also test collision with different objects, missing commits, wrong current HEAD, dirty worktree, and non-descendant reviewed heads.

- [ ] **Step 2: Run checkpoint tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_git_ops.py -k reviewed_checkpoint
```

Expected: failure because checkpoint types and methods do not exist.

- [ ] **Step 3: Implement persistent reviewed and synthetic squash refs**

Add strict result models:

```python
class ReviewedCheckpointRefs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    reviewed_ref: str
    squash_ref: str


class ContinuationReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    result: Literal["unchanged", "prepared", "conflict"]
    base_head: str
    head: str | None = None
    conflict_paths: tuple[str, ...] = ()
    sync: GuardedSyncResult | None = None
```

Create the reviewed ref with `git update-ref <ref> <reviewed-head> <zero-sha>`. Create the synthetic commit with the reviewed head's tree, exactly one parent (`sync.base_head`), and a fixed helper-authored message. Store it under `refs/snowcast-maintainer/continuations/pr-<n>/<base12>-<reviewed12>` using create-only `update-ref`.

- [ ] **Step 4: Write failing clean replay and conflict tests**

Cover:

- current `main == sync.base_head` returns `unchanged` and restores the reviewed ref;
- advanced non-overlapping `main` cherry-picks the one squash commit and returns a new prepared sync;
- one catalog/trust conflict returns `conflict` with only the allowlisted paths and leaves exactly one cherry-pick in progress;
- a production/control-plane conflict aborts and cleans the cherry-pick;
- conflict completion rejects unrelated staged changes, moved `main`, missing cherry-pick state, or a second conflict;
- successful completion produces a clean prepared head descending from the frozen current-main base.

- [ ] **Step 5: Run replay tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_git_ops.py -k continuation_replay
```

Expected: failure because replay APIs do not exist.

- [ ] **Step 6: Implement bounded replay and conflict completion**

`prepare_reviewed_continuation()` must fetch and freeze current `origin/main`, verify the selected remote and persistent refs, switch to the frozen main, and cherry-pick the one synthetic commit with editor interaction disabled. On conflict, inspect `git diff --name-only --diff-filter=U`; abort unless every path passes the existing curation allowlist and no schema/control-plane path is present. Return only the normalized conflict paths.

`continue_reviewed_conflict()` must require the same frozen base, active cherry-pick, no unmerged files, no staged path outside the original conflict set, and no unstaged/untracked path. Complete the cherry-pick, reject another conflict, verify the resulting diff, and create a normal prepared ref/sync result.

- [ ] **Step 7: Run Task 2 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_git_ops.py
uv run --no-config ruff check ops/maintainer/git_ops.py tests/test_maintainer_git_ops.py
```

Expected: the full Git helper suite passes and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/git_ops.py tests/test_maintainer_git_ops.py
git commit -m "feat: replay reviewed curation checkpoints"
```

### Task 3: Wire checkpoint, continuation preparation, validation, and push handoff

**Files:**
- Modify: `ops/maintainer/cli.py`
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/errors.py`
- Modify: `ops/maintainer/state.py`
- Test: `tests/test_maintainer_cli.py`
- Test: `tests/test_maintainer_errors.py`
- Test: `tests/test_maintainer_validation.py`
- Test: `tests/test_maintainer_publication.py`

**Interfaces:**
- Consumes: Task 1 continuation state and Task 2 Git checkpoint/replay APIs.
- Produces: `validate reviewed`, `prepare continuation`, `prepare continuation --continue-conflict`, backward adoption of an existing `WorkPhase.REVIEWED` record, validation-status persistence, and transfer to the existing push journal.

- [ ] **Step 1: Write failing CLI contract tests**

Add parser/dispatch tests for:

```text
validate reviewed --pr 42 --reviewed-head <sha> --report <path> --run-id <id>
validate reviewed --pr 42 --reviewed-head <sha> --report <path> --adopt-existing --run-id <id>
prepare continuation --pr 42 --run-id <id>
prepare continuation --pr 42 --continue-conflict --run-id <id>
```

Prove ordinary `prepare curation` returns the safe `continuation-required` reason when an exact active continuation exists.

- [ ] **Step 2: Run CLI tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py -k continuation
```

Expected: parser or handler failure because the commands are absent.

- [ ] **Step 3: Implement reviewed checkpoint capability**

`handle_validate_reviewed()` must require the curation lease, exact PR/head, `PREPARED` work owned by the run, one report path in the resulting diff, and Task 2 checkpoint refs. It advances ordinary work to `REVIEWED` and atomically saves `ReviewedContinuation` before returning success.

With `--adopt-existing`, require no current continuation and an existing ordinary `REVIEWED` record whose selected head, reviewed head, sync lineage, exact commit tree, clean repository, and single report revalidate. The supplied head must equal that record; arbitrary commits are rejected. Create the durable refs and continuation under the successor lease without trusting prior prose or automation memory.

- [ ] **Step 4: Implement continuation preparation capability**

`handle_prepare_continuation()` must require an exact resumable continuation and unchanged PR head, adopt it to the current lease, and begin a fresh ordinary work record. Map Task 2 results as follows:

```python
if replay.result == "unchanged":
    # advance selected -> prepared -> reviewed using exact saved facts
    return {"continuation": {"result": "validation-only", ...}}
if replay.result == "prepared":
    # advance selected -> prepared and require one fresh full review
    return {"continuation": {"result": "review-required", ...}}
return {
    "continuation": {
        "result": "conflict-resolution-required",
        "conflict_paths": list(replay.conflict_paths),
    }
}
```

The `--continue-conflict` form completes Task 2's bounded replay and advances to `PREPARED`. It never marks the replayed head reviewed.

- [ ] **Step 5: Write failing validation and publication transition tests**

Test that:

- `validate curation` requires the exact active checkpoint;
- validator failure leaves the continuation `AVAILABLE/FAILED`;
- validation success records `VALIDATED/PASSED`;
- an exact retry can resume validation after a successor adoption;
- `publish push` creates the journal and then marks the continuation `CONSUMED` before external push;
- journal creation failure leaves the continuation available;
- `publish manual-check` also requires the exact checkpoint and yields to its journal;
- an unresolved journal always wins over a continuation during inspection/recovery.

- [ ] **Step 6: Run lifecycle tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py -k continuation
```

Expected: failures on missing validation and push handoff behavior.

- [ ] **Step 7: Implement validation status and push-journal handoff**

Require a matching current-run continuation in `handle_validate_curation()`. Catch validation errors only to persist `FAILED` before re-raising the original safe error; persist `PASSED` after successful validation. In `handle_publish_push()` and `handle_publish_manual_check()`, save the authorized journal first, then atomically mark the matching continuation consumed before executing the external push. If either local transition fails, do not push.

- [ ] **Step 8: Run Task 3 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py tests/test_maintainer_errors.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py
uv run --no-config ruff check ops/maintainer/cli.py ops/maintainer/capabilities.py ops/maintainer/errors.py ops/maintainer/state.py tests/test_maintainer_cli.py tests/test_maintainer_errors.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py
```

Expected: all selected suites pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/cli.py ops/maintainer/capabilities.py ops/maintainer/errors.py ops/maintainer/state.py tests/test_maintainer_cli.py tests/test_maintainer_errors.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py
git commit -m "feat: resume reviewed curation work"
```

### Task 4: Align repository contracts and the installed skill

**Files:**
- Modify: `docs/operating-model/local-maintainer-activation.md`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify after merged helper verification: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`

**Interfaces:**
- Consumes: the exact CLI and lifecycle behavior from Tasks 1-3.
- Produces: one unambiguous scheduled-worker contract for checkpointing, resumption selection, one full replay review, bounded conflict remediation, and push-journal handoff.

- [ ] **Step 1: Update the versioned operator contract**

Add required skill behavior:

- call `validate reviewed` after every final exact-head independent review and before validation/manual-check;
- prefer an exact resumable continuation over memory-only unpublished follow-up;
- use validation-only continuation without semantic review only when the helper returns `validation-only`;
- run exactly one fresh independent full review when the helper returns `review-required`;
- resolve only helper-returned allowed conflict paths, then call `prepare continuation --continue-conflict` and run one fresh full review;
- stop on any remote drift, disallowed path, repeated conflict, missing ref, or unsafe helper state;
- treat the push journal as sole authority after journal authorization.

Add first-run acceptance cases for validator failure, clean main drift, allowed conflict, interrupted conflict replay, remote-head drift, and continuation-to-journal transfer.

- [ ] **Step 2: Record the durable engineering concept and implementation status**

Add a concise `Reviewed local continuation` entry to `docs/engineering-notes.md`. Update the design gate from “not yet implemented” to the exact verified implementation status only after Task 5 verification succeeds.

- [ ] **Step 3: Verify repository documentation and commit**

Run:

```bash
git diff --check
rg -n "validate reviewed|prepare continuation|conflict-resolution-required|review-required|validation-only" docs/operating-model/local-maintainer-activation.md docs/engineering-notes.md docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md
```

Expected: diff check passes and every lifecycle term appears in the owning docs.

Commit:

```bash
git add docs/operating-model/local-maintainer-activation.md docs/engineering-notes.md docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md
git commit -m "docs: activate reviewed curation continuation"
```

### Task 5: Verify, review, publish, and recover PR #35

**Files:**
- Verify: `ops/maintainer/`
- Verify: `tests/test_maintainer_*.py`
- Modify after repository commit is on `main`: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`
- Use preserved PR #35 reviewed head: `79cf93667cd52b2b0ddf9915379e80d0aa24f5df`

**Interfaces:**
- Consumes: all prior tasks and the preserved legacy `WorkPhase.REVIEWED` record for PR #35.
- Produces: verified repository code, aligned installed skill, and a helper-owned PR #35 continuation ready for bounded replay/review rather than a fresh dual-review cycle.

- [ ] **Step 1: Run complete repository verification**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_state.py tests/test_maintainer_inspection.py tests/test_maintainer_git_ops.py tests/test_maintainer_cli.py tests/test_maintainer_errors.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py
uv run --no-config ruff check ops/maintainer tests/test_maintainer_state.py tests/test_maintainer_inspection.py tests/test_maintainer_git_ops.py tests/test_maintainer_cli.py tests/test_maintainer_errors.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py
uv run --no-config ruff format --check ops/maintainer tests/test_maintainer_state.py tests/test_maintainer_inspection.py tests/test_maintainer_git_ops.py tests/test_maintainer_cli.py tests/test_maintainer_errors.py tests/test_maintainer_validation.py tests/test_maintainer_publication.py
git diff --check
```

Expected: all tests pass, Ruff checks and format checks exit 0, and Git diff check is clean.

- [ ] **Step 2: Run advisory feature review**

Use `snowcast-advisory-review` in `feature-review` mode for AI/LLM reliability, security/privacy, observability/ops, and release/change management. Resolve every Blocker/High finding and rerun Task 5 Step 1.

- [ ] **Step 3: Commit verified implementation and obtain push authority**

Commit any final review fixes with a focused message. If the owner has not explicitly authorized pushing this amendment, present the exact commits and request push approval. Do not update the installed personal skill before the verified repository helper is present on local and remote `main`.

- [ ] **Step 4: Update and verify the installed skill after main contains the helper**

Apply the versioned activation contract to `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`. Verify:

```bash
rg -n "validate reviewed|prepare continuation|conflict-resolution-required|review-required|validation-only" /Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md
```

Expected: all five lifecycle terms appear in the installed skill and no rule still says every unpublished follow-up must start semantic review from scratch.

- [ ] **Step 5: Adopt PR #35's legacy reviewed record without publishing**

After confirming no unresolved push journal, the remote PR #35 head is still `1f97ac60019a71aa87456c3074ad5b5b48d617a2`, the preserved reviewed commit exists, and the owner has removed `maintainer:blocked`, acquire the curation lease and run the exact backward-adoption checkpoint for reviewed head `79cf93667cd52b2b0ddf9915379e80d0aa24f5df` and its single schema-v3 report. Release the lease if adoption stops. Do not push during adoption.

- [ ] **Step 6: Resume PR #35 through the bounded continuation path**

Run `prepare continuation`. For its known allowed-path trust-manifest conflict, resolve only the helper-returned paths through `snowcast-catalog-curation` in maintainer-managed mode, complete continuation preparation, then run one fresh independent full `snowcast-catalog-review`. If clean, checkpoint the new exact head, validate, helper-push, and publish the truthful waiting-CI/ready/manual-check state from current exact facts. Never approve or merge.

- [ ] **Step 7: Verify final recovery state**

Run read-only curation and discovery inspection. Confirm no unresolved journal, no available/resolving PR #35 continuation after push authorization, exact remote head agreement, released lease, clean worktree, and an updated canonical PR comment/label. Report the concise Triage outcome.

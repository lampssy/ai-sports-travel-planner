# Maintainer Post-Push CI Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one curation maintainer run retain its lease through GitHub CI, perform at most one focused test-only repair when CI exposes stale assertions, and publish the exact final CI-green head without repeating semantic catalog review.

**Architecture:** Add a helper-owned `CiContinuation` beside existing reviewed/remediation continuations and push journals. The continuation binds the original semantic head, the current pushed head, the canonical report/graph, cumulative 30/60/30 budgets, and an optional focused test-repair checkpoint. GitHub check interpretation and test editing remain with Codex; the helper owns recovery priority, path/mode/tree enforcement, attempt counting, exact-lease pushes, and GitHub publication.

**Tech Stack:** Python 3.12, Pydantic v2, Git plumbing, GitHub CLI, pytest, Ruff, existing `ops.maintainer` state/capability/publication layers, and the installed Snowcast maintainer skill.

## Global Constraints

- Classification: `review-gated`; this changes scheduled-job reliability, local persistence, GitHub publication, and the trust boundary around PR-supplied tests.
- Developer Decision Checkpoint: resolved by the owner. Retain the lease for CI; use a 30-minute first wait, one 60-active-minute test repair, and a 30-minute second wait outside the 240-minute semantic deadline.
- ADR status: ADR 0011 is already amended; no new ADR is required unless implementation reveals a different ownership boundary.
- Advisory review: focused `feature-review` is required before activation because this affects unattended execution, GitHub mutations, and untrusted test/log handling.
- Recovery priority is fixed: unresolved push journal, then post-push CI continuation, then reviewed continuation, then remediation continuation, then ordinary PR.
- A push journal remains the sole authority while a branch mutation is ambiguous.
- `maintainer:waiting-ci` remains a compatibility/visibility state, never recovery authority.
- Codex may interpret failed-check metadata and bounded read-only GitHub logs, but the helper must not parse test meaning or persist CI prose/logs.
- The unattended local workflow must not execute test modules from the target PR. GitHub CI executes PR-supplied tests.
- Post-push repair may add or modify only regular `tests/test_*.py` files. It must reject deletions, `tests/conftest.py`, configs, scripts, symlinks, executable modes, application/data/docs changes, and any other path.
- The original semantic head and its non-test tree remain immutable. A repaired head may differ only in the allowlisted test files.
- One repair attempt is consumed when `prepare ci-repair` succeeds, not when a later push succeeds. Interruption cannot reset it.
- First/second waits use elapsed wall time. Repair uses cumulative active time recorded by helper-owned heartbeat accounting. A successor receives only the remaining budget.
- Every test repair needs one fresh focused independent review on the exact repair head before checkpoint/push.
- Never approve or merge a PR.
- No new dependency.

---

### Task 1: Persist strict post-push CI continuations

**Files:**
- Modify: `ops/maintainer/intent.py`
- Modify: `ops/maintainer/state.py`
- Test: `tests/test_maintainer_intent.py`
- Test: `tests/test_maintainer_state.py`

**Interfaces:**
- Produces: `is_allowed_ci_repair_path()`, `CiContinuationPhase`, `CiContinuation`, `StateStore.load_ci_continuation()`, `StateStore.list_ci_continuations_for_inspection()`, `StateStore.save_ci_continuation()`, `StateStore.adopt_ci_continuation()`, `StateStore.advance_ci_continuation()`, and `StateStore.record_ci_heartbeat()`.
- Consumes: `RunLease`, private atomic JSON helpers, existing run-ID/SHA/ref validators, and the transition mutex.

- [ ] **Step 1: Write failing CI-repair path-policy tests**

Specify the narrow path class:

```python
@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("tests/test_public_pages.py", True),
        ("tests/api/test_search.py", False),
        ("tests/conftest.py", False),
        ("tests/test_config.yaml", False),
        ("tests/test_helper.sh", False),
        ("app/domain/search_v4_service.py", False),
        ("docs/catalog-curation/example.json", False),
    ],
)
def test_ci_repair_path_policy(path: str, allowed: bool) -> None:
    assert is_allowed_ci_repair_path(path) is allowed
```

The approved contract is intentionally root-level regular modules matching `tests/test_*.py`. Use `PurePosixPath` and an anchored regular expression. Reject path traversal, nested modules, `conftest.py`, non-Python files, and empty components.

- [ ] **Step 2: Run path-policy tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_intent.py -k ci_repair
```

Expected: failure because the predicate does not exist.

- [ ] **Step 3: Implement the path predicate**

Keep this as one small pure function in `intent.py`; both persisted state and Git enforcement must import it.

- [ ] **Step 4: Write failing strict-model tests**

Add the enum and fixture imports, then specify the complete durable record:

```python
def _ci_continuation(
    lease: RunLease,
    *,
    phase: CiContinuationPhase = CiContinuationPhase.INITIAL_WAIT,
) -> CiContinuation:
    return CiContinuation(
        work_id="curation-pr-42",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=NOW,
        pr_number=42,
        branch="codex/catalog-curation-42",
        semantic_head=SHA_3,
        current_head=SHA_3,
        report_path="docs/catalog-curation/fr-les-arcs.json",
        resulting_graph_markdown="```mermaid\ngraph LR\n  a --> b\n```",
        non_test_tree_digest="a" * 64,
        phase=phase,
        repair_attempted=False,
        first_wait_started_at=NOW,
        first_wait_seconds=0,
        repair_active_seconds=0,
        second_wait_seconds=0,
    )
```

Test strict/frozen behavior, timezone normalization, exact `f"curation-pr-{pr_number}"` identity, safe `codex/` branch, SHA/digest/ref patterns, and phase-dependent fields. In particular:

- `INITIAL_WAIT` requires `current_head == semantic_head`, no repair fields, and `repair_attempted=False`.
- `REPAIR_ACTIVE` requires `repair_attempted=True` and `repair_activity_observed_at`.
- `REPAIR_REVIEWED` requires `repair_head`, `repair_ref`, and non-empty allowlisted `repair_paths`.
- `SECOND_WAIT` requires `current_head == repair_head` and `second_wait_started_at`.
- terminal phases may retain evidence but cannot transition back to active work.

- [ ] **Step 5: Run the focused model tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_state.py -k ci_continuation
```

Expected: collection/import failure because the CI continuation types do not exist.

- [ ] **Step 6: Implement the minimal strict model**

Add:

```python
class CiContinuationPhase(StrEnum):
    INITIAL_WAIT = "initial-wait"
    REPAIR_ACTIVE = "repair-active"
    REPAIR_REVIEWED = "repair-reviewed"
    SECOND_WAIT = "second-wait"
    CONSUMED = "consumed"
    BLOCKED = "blocked"
    INVALIDATED = "invalidated"


class CiContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(pattern=_ID_PATTERN.pattern)
    origin_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    recovery_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    updated_at: datetime
    pr_number: int = Field(ge=1)
    branch: str = Field(min_length=1, max_length=200)
    semantic_head: str = Field(pattern=_SHA_PATTERN)
    current_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    )
    resulting_graph_markdown: str = Field(min_length=1, max_length=32768)
    non_test_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase: CiContinuationPhase
    repair_attempted: bool
    first_wait_started_at: datetime
    first_wait_seconds: int = Field(ge=0, le=1800)
    repair_active_seconds: int = Field(ge=0, le=3600)
    repair_activity_observed_at: datetime | None = None
    repair_head: str | None = Field(default=None, pattern=_SHA_PATTERN)
    repair_ref: str | None = Field(default=None, pattern=_REF_PATTERN)
    repair_paths: frozenset[str] = frozenset()
    second_wait_started_at: datetime | None = None
    second_wait_seconds: int = Field(default=0, ge=0, le=1800)
```

Keep phase validation in one model validator. Reuse `is_safe_codex_branch()` and `is_allowed_ci_repair_path()` rather than duplicating path rules.

- [ ] **Step 7: Write failing persistence, adoption, and budget tests**

Cover:

- owner-private mode `0700` directory / `0600` file;
- one active record at `state_dir/ci-continuations/curation-pr-42.json`;
- successor adoption changes only `recovery_run_id` and `updated_at`;
- unresolved push journals prevent ordinary CI adoption;
- legal monotonic phase transitions;
- no decrease or reset of any consumed budget;
- `record_ci_heartbeat()` adds at most 300 seconds while `REPAIR_ACTIVE`;
- a long sleep gap never adds more than one heartbeat interval;
- the previous owner is fenced;
- consumed/blocked/invalidated records disappear from active inspection.

Use a deterministic `now=` parameter for transition/heartbeat methods so tests do not depend on wall clock.

- [ ] **Step 8: Run the persistence tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_state.py -k 'ci_continuation or ci_heartbeat'
```

Expected: failures because the store has no CI continuation directory or transitions.

- [ ] **Step 9: Implement state-store persistence and transitions**

Add `ci_continuation_dir`, load/list/save/adopt/advance APIs, extend `_StateModel`, and preserve the existing atomic-write and lease-fencing rules. Compute wait consumption at transitions:

```python
first_wait_seconds = min(
    1800,
    max(
        continuation.first_wait_seconds,
        int((now - continuation.first_wait_started_at).total_seconds()),
    ),
)
```

For active repair heartbeat accounting:

```python
delta = max(
    0,
    int((now - continuation.repair_activity_observed_at).total_seconds()),
)
repair_active_seconds = min(
    3600,
    continuation.repair_active_seconds + min(delta, 300),
)
```

Always verify the current lease before writing. Do not make `inspect` mutate state.

- [ ] **Step 10: Run Task 1 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_intent.py tests/test_maintainer_state.py
uv run --no-config ruff check ops/maintainer/intent.py ops/maintainer/state.py tests/test_maintainer_intent.py tests/test_maintainer_state.py
```

Expected: all tests pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/intent.py ops/maintainer/state.py tests/test_maintainer_intent.py tests/test_maintainer_state.py
git commit -m "feat: persist post-push CI continuations"
```

### Task 2: Expose live CI continuations before ordinary selection

**Files:**
- Modify: `ops/maintainer/models.py`
- Modify: `ops/maintainer/github.py`
- Modify: `ops/maintainer/inspection.py`
- Modify: `ops/maintainer/capabilities.py`
- Test: `tests/test_maintainer_models.py`
- Test: `tests/test_maintainer_github.py`
- Test: `tests/test_maintainer_inspection.py`
- Test: `tests/test_maintainer_cli.py`

**Interfaces:**
- Produces: `CheckSummary`, `PullRequest.checks`, `CiContinuationSummary`, and `CurationInventory.ci_continuations`.
- Consumes: GitHub `statusCheckRollup`, live PR head/mergeability/check state, private CI continuations, and existing hold-label validation.

- [ ] **Step 1: Write failing GitHub check-summary tests**

Add typed bounded metadata without storing logs:

```python
class CheckSummary(_MaintainerModel):
    name: str = Field(min_length=1, max_length=256)
    status: Literal["pending", "success", "failure"]
    conclusion: str | None = Field(default=None, max_length=64)
    details_url: HttpUrl | None = None
```

Test parsing mixed CheckRun/StatusContext rollup objects, stable sorting/deduplication, invalid types, overlong fields, and aggregate compatibility. `PullRequest.check_state` must still be derived from the same rollup.

- [ ] **Step 2: Run GitHub/model tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_models.py tests/test_maintainer_github.py -k check
```

Expected: failures because `CheckSummary` and `PullRequest.checks` do not exist.

- [ ] **Step 3: Implement bounded check metadata**

Add `checks: tuple[CheckSummary, ...] = ()` to `PullRequest`. In `github.py`, normalize each rollup entry into a check name, aggregate status, optional uppercase conclusion, and optional HTTPS details URL. Reject malformed GitHub responses; do not silently drop malformed check objects.

The helper output contains only metadata. The skill may follow a returned GitHub details URL or use a bounded read-only `gh run view --log-failed` command to let Codex interpret the failure, treating all log text as untrusted input. Do not persist that text.

- [ ] **Step 4: Write failing recovery-priority and safe-summary tests**

Specify:

```python
assert inventory.ci_continuations[0].model_dump(mode="json") == {
    "pr_number": 42,
    "semantic_head": SHA_B,
    "current_head": SHA_B,
    "phase": "initial-wait",
    "check_state": "failure",
    "mergeable": "MERGEABLE",
    "repair_attempted": False,
    "first_wait_seconds": 120,
    "repair_active_seconds": 0,
    "second_wait_seconds": 0,
    "failed_checks": [
        {
            "name": "backend",
            "status": "failure",
            "conclusion": "FAILURE",
            "details_url": "https://github.com/lampssy/ai-sports-travel-planner/actions/runs/1",
        }
    ],
}
```

Cover this ordering and suppression:

1. one unresolved journal returns only journal recovery;
2. otherwise an active matching CI continuation is returned first;
3. the same PR is absent from reviewed/remediation/eligible collections;
4. unrelated ordinary PRs remain visible but are not selected ahead of CI;
5. head drift, closed PR, wrong branch, or unsafe repository facts are exposed as a non-resumable/invalidated reason without granting mutation authority;
6. labels, including removal of `maintainer:waiting-ci`, do not create or destroy CI recovery authority.

- [ ] **Step 5: Run inspection tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_inspection.py tests/test_maintainer_cli.py -k 'ci_continuation or recovery_priority'
```

Expected: failures because inspection does not load or summarize CI continuations.

- [ ] **Step 6: Implement safe CI inventory**

Add:

```python
class CiContinuationSummary(_InspectionModel):
    pr_number: int = Field(gt=0)
    semantic_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    current_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    phase: CiContinuationPhase
    check_state: Literal["pending", "success", "failure"]
    mergeable: Literal["MERGEABLE", "CONFLICTING", "UNKNOWN"]
    repair_attempted: bool
    first_wait_seconds: int = Field(ge=0, le=1800)
    repair_active_seconds: int = Field(ge=0, le=3600)
    second_wait_seconds: int = Field(ge=0, le=1800)
    failed_checks: tuple[CheckSummary, ...] = ()
```

Pass `now` into `inspect_curation()` so summaries can report capped elapsed wait without writing state. Keep run IDs, local refs, timestamps, graph Markdown, and private digests out of inspection JSON.

Update `handle_inspect_curation()` to load CI continuations read-only and pass them after unresolved journals. Maintain the exact recovery ordering in one place.

- [ ] **Step 7: Run Task 2 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_models.py tests/test_maintainer_github.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py -k 'check or ci_continuation or inspect_curation'
uv run --no-config ruff check ops/maintainer/models.py ops/maintainer/github.py ops/maintainer/inspection.py ops/maintainer/capabilities.py tests/test_maintainer_models.py tests/test_maintainer_github.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/models.py ops/maintainer/github.py ops/maintainer/inspection.py ops/maintainer/capabilities.py tests/test_maintainer_models.py tests/test_maintainer_github.py tests/test_maintainer_inspection.py tests/test_maintainer_cli.py
git commit -m "feat: prioritize live CI continuations"
```

### Task 3: Enforce an exact test-only repair checkpoint

**Files:**
- Modify: `ops/maintainer/git_ops.py`
- Test: `tests/test_maintainer_git_ops.py`

**Interfaces:**
- Produces: `CiRepairCheckpoint`, `GitRepository.non_test_tree_digest()`, `GitRepository.prepare_ci_repair()`, `GitRepository.checkpoint_ci_repair()`, `GitRepository.revalidate_ci_repair_checkpoint()`, and `GitRepository.push_exact_with_lease()`.
- Consumes: exact semantic/current/repair heads, live PR branch identity, regular Git diff entries, and create-only persistent refs.

- [ ] **Step 1: Write failing real-Git repair tests**

Create a fixture with:

- a semantic/current head containing the reviewed product and catalog changes;
- one failing old test assertion;
- a one-commit child that modifies only `tests/test_public_pages.py`.

Cover:

- prepare fetches and detaches the exact current PR head without rebasing onto newer `main`;
- checkpoint requires clean worktree and `HEAD == repair_head`;
- current pushed head is an ancestor of repair head;
- semantic-to-repair non-test digest equals the stored digest;
- current-to-repair diff is non-empty and only `A`/`M`, mode `100644`, under `tests/test_*.py`;
- persistent ref format is
  `f"refs/snowcast-maintainer/ci-repairs/pr-{pr_number}/{current_head[:12]}-{repair_head[:12]}"`;
- exact revalidation succeeds from the ref;
- application/catalog/report/config/conftest changes, deletion, rename, symlink, executable mode, extra commits with non-test changes, dirty worktrees, head drift, and ref collisions fail closed;
- `push_exact_with_lease(branch, expected_head, repair_head)` uses the exact remote current head and rejects stale remote state.

The main success assertion should include:

```python
checkpoint = repository.checkpoint_ci_repair(
    pull_request=pull_request,
    semantic_head=SHA_SEMANTIC,
    current_head=SHA_CURRENT,
    repair_head=SHA_REPAIR,
    expected_non_test_tree_digest=expected_digest,
)

assert checkpoint.repair_paths == frozenset({"tests/test_public_pages.py"})
assert _git(checkout, "rev-parse", checkpoint.repair_ref) == SHA_REPAIR
```

- [ ] **Step 2: Run Git tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_git_ops.py -k ci_repair
```

Expected: failure because the repair APIs do not exist.

- [ ] **Step 3: Implement exact checkpoint and push primitives**

Add:

```python
class CiRepairCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    repair_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repair_ref: str = Field(pattern=r"^refs/snowcast-maintainer/ci-repairs/")
    repair_paths: frozenset[str] = Field(min_length=1)
    non_test_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
```

Compute `non_test_tree_digest(head)` as SHA-256 over sorted NUL-safe `git ls-tree -r` mode/OID/path tuples, excluding only paths for which `is_allowed_ci_repair_path()` is true. This makes changes to `conftest.py`, configs, production code, data, docs, or file modes visible in the digest.

Do not run pytest in any of these methods. They validate repository structure only.

- [ ] **Step 4: Run Task 3 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_git_ops.py -k ci_repair
uv run --no-config ruff check ops/maintainer/git_ops.py tests/test_maintainer_git_ops.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/git_ops.py tests/test_maintainer_git_ops.py
git commit -m "feat: checkpoint exact test-only CI repairs"
```

### Task 4: Hand initial push publication to the CI continuation

**Files:**
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/cli.py`
- Modify: `ops/maintainer/state.py`
- Test: `tests/test_maintainer_cli.py`

**Interfaces:**
- Produces: atomic pushed-journal-to-CI handoff and CI-aware curation heartbeat accounting.
- Consumes: validated `WorkState`, matching pushed `PushJournal`, canonical report/graph, exact GitHub PR head, and live curation lease.

- [ ] **Step 1: Write failing handoff tests**

Extend waiting-CI publication coverage to prove:

1. `publish push` still creates the ordinary journal and exact-lease push.
2. The first `publish state --state maintainer:waiting-ci` creates `CiContinuation` only after `_pull_request_after_exact_push()` confirms the journaled head.
3. The continuation is persisted before the external body/comment/label mutation.
4. Only successful publication advances the journal to `PUBLISHED`.
5. If publication fails, the unresolved journal remains first recovery authority even though the pre-created CI continuation exists.
6. Retry/recovery reuses identical continuation facts instead of creating a conflicting record.
7. Canonical graph/body data are copied from trusted work/journal state, never accepted from a different report.
8. A normal curation heartbeat updates the lease and, when phase is `REPAIR_ACTIVE`, the cumulative repair budget in one helper invocation.

- [ ] **Step 2: Run handoff tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py -k 'waiting_ci and (continuation or heartbeat or journal)'
```

Expected: failures because waiting-CI publication does not create durable CI state.

- [ ] **Step 3: Implement the atomic handoff**

In `handle_publish_state()`, before GitHub mutation for the matching first pushed journal:

```python
ci_continuation = CiContinuation(
    work_id=work.work_id,
    origin_run_id=lease.run_id,
    recovery_run_id=lease.run_id,
    updated_at=dependencies.now(),
    pr_number=args.pr,
    branch=journal.branch,
    semantic_head=args.reviewed_head,
    current_head=args.reviewed_head,
    report_path=work.report_path,
    resulting_graph_markdown=work.resulting_graph_markdown,
    non_test_tree_digest=dependencies.repository.non_test_tree_digest(
        args.reviewed_head
    ),
    phase=CiContinuationPhase.INITIAL_WAIT,
    repair_attempted=False,
    first_wait_started_at=dependencies.now(),
    first_wait_seconds=0,
    repair_active_seconds=0,
    second_wait_seconds=0,
)
store.save_ci_continuation(ci_continuation, lease)
```

Require the report path and graph to match the pushed work/journal. Make creation idempotent for the same immutable facts. Keep journal completion after successful GitHub publication.

Update the existing lock heartbeat handler to call `record_ci_heartbeat()` only for the active curation continuation owned by that run. Return safe budget numbers in the heartbeat JSON, not private refs or timestamps.

- [ ] **Step 4: Add interrupted-handoff recovery tests**

Cover:

- journal `PUSHED` + matching CI continuation + remote exact new head;
- successor adopts journal first;
- recovery completes waiting-CI presentation and journal publication;
- only the next inspection exposes the CI continuation;
- no semantic preparation/review command is allowed during this recovery.

- [ ] **Step 5: Run Task 4 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py -k 'waiting_ci or ci_continuation'
uv run --no-config ruff check ops/maintainer/capabilities.py ops/maintainer/cli.py ops/maintainer/state.py tests/test_maintainer_cli.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/capabilities.py ops/maintainer/cli.py ops/maintainer/state.py tests/test_maintainer_cli.py
git commit -m "feat: hand pushed curation work to CI"
```

### Task 5: Add one helper-owned CI repair and second exact push

**Files:**
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/cli.py`
- Modify: `ops/maintainer/publication.py`
- Modify: `ops/maintainer/state.py`
- Test: `tests/test_maintainer_cli.py`
- Test: `tests/test_maintainer_publication.py`

**Interfaces:**
- Produces CLI capabilities:
  - `prepare ci-repair --pr "$PR_NUMBER" --run-id "$RUN_ID"`
  - `checkpoint ci-repair --pr "$PR_NUMBER" --head "$REPAIR_HEAD" --run-id "$RUN_ID"`
  - `publish ci-repair --pr "$PR_NUMBER" --run-id "$RUN_ID"`
- Extends `publish state` and `publish outcome` to consume/terminalize exact CI continuations.
- Consumes: current live checks, repair checkpoint, one-attempt state, existing push journal machinery, and existing idempotent body/comment/label publication.

- [ ] **Step 1: Write failing CLI-dispatch tests**

Add parser/dispatch tests for all three commands, required arguments, worker hint, repository dependency wiring, JSON envelope behavior, and rejection of unknown flags. Keep the command surface mechanical; do not add a caller-supplied phase, attempt count, branch, report, graph, or allowed path.

- [ ] **Step 2: Run parser tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py -k 'prepare_ci_repair or checkpoint_ci_repair or publish_ci_repair'
```

Expected: parser failure because the commands do not exist.

- [ ] **Step 3: Implement `prepare ci-repair`**

The handler must:

- own/adopt the matching CI continuation under the curation lease;
- require `INITIAL_WAIT`, live exact current head, failed checks, mergeable non-conflicting PR, and an unused repair attempt;
- call `repository.prepare_ci_repair()` to detach the exact current pushed head;
- atomically set `repair_attempted=True`, phase `REPAIR_ACTIVE`, and `repair_activity_observed_at=now`;
- return the exact current head, failed check metadata, remaining repair seconds, and permitted path pattern;
- never infer that the failure is repairable.

Codex decides whether to invoke this command after interpreting CI. If it does, the attempt is consumed even when later editing/review fails. A successor may make this transition when a check that was still pending at the first 30-minute boundary later becomes a confirmed failure; the expired first-wait budget authorizes no more waiting but does not reset or erase the unused repair budget.

- [ ] **Step 4: Write failing checkpoint tests**

Cover:

- exact current-head worktree;
- one or more `tests/test_*.py` changes;
- fresh focused-review evidence represented by invoking the checkpoint capability on the exact reviewed repair head;
- Git checkpoint result copied into the continuation;
- elapsed active time recorded before transition;
- rejection after 3600 active seconds, wrong phase, second attempt, dirty tree, head drift, empty diff, or any structural Git violation;
- no local pytest command is executed.

- [ ] **Step 5: Implement `checkpoint ci-repair`**

Call `repository.checkpoint_ci_repair()`, then advance to `REPAIR_REVIEWED` with the returned exact `repair_head`, `repair_ref`, and `repair_paths`. The command itself is the durable focused-review checkpoint; the installed skill must call it only after a newly spawned independent reviewer returns clean on that exact head.

- [ ] **Step 6: Write failing second-push and ambiguous-recovery tests**

Cover:

- `publish ci-repair` creates a new `AUTHORIZED` journal for the same work only after the prior journal is `PUBLISHED`;
- expected remote head is the continuation's `current_head`;
- new head is the checkpointed `repair_head`;
- exact push produces `PUSHED`, GitHub convergence produces `SECOND_WAIT`, and the continuation records `current_head=repair_head`;
- `repair_attempted` remains true;
- interruption before/during/after push recovers through the journal before CI continuation selection;
- recovery revalidates the repair ref, allowed paths, non-test digest, remote head, and continuation identity;
- no second repair command becomes legal after recovery.

- [ ] **Step 7: Implement second exact push using the existing journal**

Generalize `_advance_curation_push()` to accept either:

- validated ordinary `WorkState` evidence for the initial push; or
- a matching `REPAIR_REVIEWED` `CiContinuation` plus revalidated repair checkpoint for the repair push.

Do not add an unjournaled push path. Reuse `StateStore.guard_push_mutation()` and the existing exact remote lease behavior.

- [ ] **Step 8: Write failing final publication tests**

Test:

- initial or second-wait success + exact head + `MERGEABLE` publishes `maintainer:ready`;
- pending at either 30-minute limit retains/publishes `maintainer:waiting-ci`, leaves continuation active, and releases cleanly;
- first failure can enter repair only once;
- non-repairable initial failure and any second failure publish `maintainer:blocked/ci-failure` and terminalize the continuation;
- cancellation/missing/unknown checks, conflict, changed head, or lost lease do not get converted into success or a repair;
- after a test repair, `MachineState.reviewed_head == validated_head == final repair head`, while graph/body are reproduced from the stored original semantic report;
- successful ready publication consumes the continuation;
- label removal alone neither consumes nor reactivates a continuation.

- [ ] **Step 9: Implement CI-aware ready/outcome publication**

Keep `MachineState` schema 2. For a repaired final head, the helper may derive:

```python
MachineState(
    schema_version=2,
    reviewed_head=continuation.current_head,
    validated_head=continuation.current_head,
    last_operation="published",
)
```

This is allowed only after:

- the repair checkpoint was focused-reviewed;
- its non-test digest matches the semantic head;
- its test-only diff revalidates;
- the PR head equals `current_head`;
- checks are successful; and
- GitHub says `MERGEABLE`.

The private continuation retains `semantic_head` so this derived final validation cannot be confused with a fresh semantic catalog review. Reproduce the Resulting Graph from `resulting_graph_markdown` stored at initial handoff.

- [ ] **Step 10: Run Task 5 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_cli.py tests/test_maintainer_publication.py -k 'ci_repair or ci_continuation or waiting_ci or ready or ci_failure'
uv run --no-config ruff check ops/maintainer/capabilities.py ops/maintainer/cli.py ops/maintainer/publication.py ops/maintainer/state.py tests/test_maintainer_cli.py tests/test_maintainer_publication.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add ops/maintainer/capabilities.py ops/maintainer/cli.py ops/maintainer/publication.py ops/maintainer/state.py tests/test_maintainer_cli.py tests/test_maintainer_publication.py
git commit -m "feat: repair one failed CI test migration"
```

### Task 6: Update the runtime and activation contracts

**Files:**
- Modify: `docs/operating-model/maintainer-runtime-command-contract.md`
- Modify: `docs/operating-model/local-maintainer-activation.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/superpowers/specs/2026-07-24-maintainer-post-push-ci-remediation-design.md`
- Modify: `docs/engineering-notes.md`
- Test: `tests/test_maintainer_runtime_command_contract.py`

**Interfaces:**
- Produces the checked-in orchestration contract that the installed `snowcast-maintainer` skill will mirror during activation.
- Consumes the exact CLI JSON envelopes implemented in Tasks 1-5.

- [ ] **Step 1: Write failing contract-recipe tests**

Add exact recipe extraction/parser coverage for:

- CI continuation selection after journal recovery;
- initial 30-minute poll loop with `lock heartbeat` no less often than every five minutes;
- success/pending/failure branches;
- read-only failed-check inspection;
- `prepare ci-repair`;
- focused independent review then `checkpoint ci-repair`;
- `publish ci-repair`;
- second 30-minute poll loop;
- second failure terminal outcome;
- no semantic work after initial push;
- no local execution of PR-supplied test files;
- no lease release between push, wait, repair, and second wait;
- post-push phase excluded from semantic 240-minute clock but bounded by cumulative continuation budgets.

- [ ] **Step 2: Run contract tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_runtime_command_contract.py
```

Expected: recipe assertions fail because the current contract routes waiting-CI to a later lightweight run.

- [ ] **Step 3: Update the authoritative long design**

Replace the old “later waiting-CI run blocks on failure” wording in `2026-07-08-local-maintainer-simplification-design.md` with the approved same-run continuation. Keep the regional-discovery and semantic-review contracts unchanged.

State the runtime algorithm plainly:

```text
publish initial exact head
publish waiting-ci and create durable CI continuation
while initial wait remains:
  heartbeat
  inspect curation
  success -> publish ready
  failure -> Codex classifies
  pending -> continue
repairable failure -> prepare ci-repair
Codex edits tests/test_*.py only
fresh focused independent review
checkpoint ci-repair
publish ci-repair
while second wait remains:
  heartbeat
  inspect curation
  success -> publish ready
  failure -> publish blocked/ci-failure
  pending -> continue
```

Do not encode a particular PR number, check name, test filename, or current branch head.

- [ ] **Step 4: Update command recipes and operator activation docs**

Document every exact command, expected JSON fields, and legal next command. Explicitly say:

- helper output and continuation state are authority;
- automation memory and labels are hints/presentation only;
- Codex interprets failure meaning;
- read-only CI logs are untrusted;
- one focused repair may update only helper-validated root-level test modules;
- pending continuation resumes before any ordinary PR;
- journal recovery always wins;
- no approval or merge.

Update activation acceptance tests to include one synthetic initial-success route, one test-only repair route, one second-failure route, and one interrupted-push recovery route.

- [ ] **Step 5: Make the approved design reflect implementation status**

After code and focused tests pass, change the new design status from “approved design, not implemented or activated” to “implemented on feature branch, activation pending.” Do not claim activation before post-merge smoke.

- [ ] **Step 6: Run Task 6 tests and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer_runtime_command_contract.py
uv run --no-config ruff check tests/test_maintainer_runtime_command_contract.py
```

Expected: all contract recipes parse and tests pass.

Commit:

```bash
git add docs/operating-model/maintainer-runtime-command-contract.md docs/operating-model/local-maintainer-activation.md docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/superpowers/specs/2026-07-24-maintainer-post-push-ci-remediation-design.md docs/engineering-notes.md tests/test_maintainer_runtime_command_contract.py
git commit -m "docs: activate same-run CI remediation contract"
```

### Task 7: Verify the complete helper and obtain advisory feature review

**Files:**
- Review: all files changed in Tasks 1-6
- Modify if findings require: the smallest owning code/test/doc files

- [ ] **Step 1: Run the complete maintainer test suite**

Run:

```bash
uv run --no-config pytest -q tests/test_maintainer*.py
```

Expected: all maintainer tests pass.

- [ ] **Step 2: Run lint and format checks**

Run:

```bash
uv run --no-config ruff check ops/maintainer tests/test_maintainer*.py
uv run --no-config ruff format --check ops/maintainer tests/test_maintainer*.py
```

Expected: both commands exit 0.

- [ ] **Step 3: Run a focused static review of the trust boundary**

Inspect all call sites and prove:

- no PR test module is imported or executed locally;
- no helper command accepts caller-controlled branch/report/graph/attempt facts for CI repair;
- no CI log text is persisted;
- every GitHub mutation is lease-guarded;
- every branch push has a journal;
- a repaired head cannot alter the non-test digest;
- terminal continuations cannot return to an active phase;
- a newer task cannot reset budgets;
- journals suppress CI continuation selection until publication recovery is complete.

- [ ] **Step 4: Run focused advisory `feature-review`**

Use `snowcast-advisory-review` with:

- release/change management;
- security/privacy;
- AI/LLM reliability;
- observability/operations.

Ask reviewers to focus on lease retention, untrusted CI output, exact-head recovery, cumulative budgets, and accidental production-code widening. Fix all Blocker/High findings and rerun the affected focused tests. Record any accepted Medium/Low follow-up explicitly.

- [ ] **Step 5: Test the prospective merge against current `origin/main`**

Fetch current main and create a temporary detached worktree:

```bash
git fetch origin main
feature_head="$(git rev-parse HEAD)"
tmp_dir="$(mktemp -d /tmp/snowcast-ci-remediation-merge.XXXXXX)"
git worktree add --detach "$tmp_dir" origin/main
(
  cd "$tmp_dir"
  git merge --no-commit --no-ff "$feature_head"
  uv run --no-config pytest -q tests/test_maintainer*.py
  git merge --abort
)
git worktree remove "$tmp_dir"
```

Remove the temporary worktree even when the prospective merge or test command fails.

- [ ] **Step 6: Commit any review corrections**

If review or prospective-merge verification required changes:

```bash
git diff --name-only --diff-filter=ACMRTUXB -z | xargs -0 git add --
git commit -m "fix: harden post-push CI remediation"
```

Do not create an empty commit.

### Task 8: Create the implementation PR and perform owner-controlled activation after merge

**Files outside the feature PR, changed only after merge:**
- Modify installed skill: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`
- Modify the existing maintainer automation prompt through the automation update capability

- [ ] **Step 1: Rebase or merge the feature branch onto current main safely**

Refresh `origin/main`, resolve only genuine feature-branch conflicts, and rerun:

```bash
uv run --no-config pytest -q tests/test_maintainer*.py
uv run --no-config ruff check ops/maintainer tests/test_maintainer*.py
uv run --no-config ruff format --check ops/maintainer tests/test_maintainer*.py
```

- [ ] **Step 2: Push the feature branch and create a ready-for-review PR**

Use the repository’s project-scoped GitHub authentication. The PR body must summarize:

- same-run initial CI wait;
- one focused test-only repair;
- durable exact-head recovery;
- 30/60/30 cumulative budgets;
- no local execution of PR-supplied tests;
- retained compatibility `maintainer:waiting-ci` label;
- verification and advisory-review result.

Do not merge the PR unless the owner explicitly asks.

- [ ] **Step 3: After owner merge, pause scheduled automations**

Pause both the curation maintainer and discovery schedules so the installed skill cannot drift while it is replaced. Confirm no active lease or unresolved push journal before activation.

- [ ] **Step 4: Install the merged contract**

Update `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md` to mirror the merged runtime contract exactly:

- recovery priority including CI continuation;
- same-run lease retention;
- heartbeat frequency;
- initial/second wait rules;
- one repair attempt;
- focused review checkpoint;
- no local PR-test execution;
- helper-only mutation/publication;
- no PR-specific wording.

Update the existing automation prompt generically. It should say to use the installed skill’s CI-continuation flow, not mention a specific PR, branch, check, or test.

- [ ] **Step 5: Run read-only and synthetic activation smoke checks**

With schedules still paused:

1. inspect both workers and confirm valid JSON;
2. verify journal-first then CI-continuation selection ordering;
3. acquire/heartbeat/release a test lease without touching GitHub;
4. use fixture-backed helper tests for initial success, repair checkpoint, second failure, and recovery;
5. confirm the installed skill and merged runtime contract contain matching commands and budgets;
6. confirm no unresolved journals or test continuations were left behind.

- [ ] **Step 6: Re-enable schedules gradually**

Enable the curation schedule first. Let one bounded cycle complete and verify:

- it selects a real CI continuation before ordinary PRs when one exists;
- it heartbeats while waiting;
- it does not run PR tests locally;
- it updates only the canonical comment/label/body through the helper;
- it releases the lease with no unresolved journal.

Then re-enable discovery. Do not treat an ordinary `lock-busy` discovery result during a retained curation CI lease as an error.

- [ ] **Step 7: Final practical handoff**

Report:

- exact merged main head;
- installed skill parity check;
- automation status;
- smoke result;
- any active CI continuation or unresolved journal;
- focused/full verification commands and results;
- DDC resolved;
- ADR 0011 amended;
- advisory feature review result;
- no approval or merge performed by the maintainer workflow.

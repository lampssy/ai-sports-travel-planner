# Simplified Local Snowcast Maintainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unactivated thick maintainer policy engine with a smaller local Codex control plane in which Codex owns semantic workflow decisions and deterministic code enforces only objective inspection, branch-safety, validation, publication, proposal, and readiness boundaries.

**Architecture:** Keep the existing project-scoped GitHub adapter and guarded git primitives, but reorganize the helper around four capabilities: `inspect`, `prepare`, `validate`, and `publish`. Replace the credential/token lease and many immutable artifacts with one worker/run-ID lease, one work-item phase record, and one separate push journal; remove deterministic backlog parsing, the runtime coverage registry, duplicated body/comment state, persistent lineage counters, and deterministic workflow-state policy.

**Tech Stack:** Python 3.13, Pydantic v2, standard-library filesystem/subprocess primitives, `git`, GitHub CLI, pytest, Ruff, Markdown Codex skills, Codex App Automations.

---

## Scope Check

This is one plan because curation and discovery share the same authority,
lease, GitHub transport, phase state, validation, publication, and readiness
contracts. Each task leaves a testable capability behind. No personal skill or
schedule is installed in this plan; activation remains a separate post-merge
task.

The authoritative spec is:

`docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`

## Decision And Review Gate

- Classification: review-gated / full design flow.
- Developer Decision Checkpoints: resolved and recorded in the authoritative
  spec.
- ADR: ADR 0011 is amended.
- Required pre-code advisory design review: AI/LLM reliability,
  security/privacy, release/change management, and observability/ops.
- Implementation must not start with unresolved Blocker or High findings.
- No automatic approval, merge, dependency change, deployment, production
  access, personal-skill installation, or automation activation.

## Compatibility And Commit Sequencing

The repository is not activated yet, so runtime data migration is unnecessary,
but every committed refactor point must still leave the checked-in CLI and test
suite runnable. Tasks 2-7 therefore add the new contracts alongside the old
ones or retain narrow compatibility adapters. They must not delete a field,
method, artifact, or command still consumed by the old CLI.

Task 8 is the single atomic cutover: it switches the CLI to the four capability
surface, promotes the new lease/machine-state names, and deletes the old
contracts, modules, tests, parser, and registry in one commit. That commit is
the pre-activation rollback unit. Before every commit that changes an existing
maintainer contract, run the complete `tests/test_maintainer_*.py` suite in
addition to the focused tests.

## Target File Structure

- Keep `ops/maintainer/models.py`: strict PR metadata and the reduced canonical
  GitHub machine state.
- Keep `ops/maintainer/runtime.py`: add the simple worker/run-ID lease beside
  the legacy unactivated lease, then remove the legacy lease at atomic cutover.
- Create `ops/maintainer/state.py`: private atomic work-phase state and the
  separate push journal.
- Create `ops/maintainer/errors.py`: allowlisted safe error reason, stage, and
  detail contracts.
- Create `ops/maintainer/inspection.py`: safe curation inventory and discovery
  proposal/catalog inventory; no prioritization.
- Keep `ops/maintainer/github.py`: explicit scoped-auth GitHub transport.
- Keep `ops/maintainer/git_ops.py`: repository verification, backup, guarded
  rebase, exact-head checks, and exact force-with-lease push.
- Keep `ops/maintainer/intent.py`: allowed path/file-mode and catalog/report
  target scope; remove backlog-marker semantics.
- Create `ops/maintainer/validation.py`: exact-head curation and proposal
  validation plus fixed focused test execution.
- Simplify `ops/maintainer/publication.py`: labels, human body block, one
  canonical machine-state comment, and objective proposal/waiting-CI/ready
  gates.
- Rewrite `ops/maintainer/cli.py`: thin dispatch for `inspect`, `prepare`,
  `validate`, `publish`, and `lock`.
- Delete `ops/maintainer/curation.py` after its retained logic moves to
  inspection/validation/publication.
- Delete `ops/maintainer/discovery.py` after candidate-key and proposal
  validation moves to models/inspection/validation.
- Delete `docs/catalog-discovery/alpine-coverage-registry.json`.
- Replace the broad curation/discovery/CLI test matrices with focused tests for
  the target capability boundaries.

### Task 1: Run The Advisory Design Gate

**Files:**
- Review: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Review: `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- Modify because findings require it: the two files above and this plan

- [x] **Step 1: Run the four focused design reviewers**

Invoke `snowcast-advisory-review` in `design-review` mode for:

```text
ai-llm-reliability
security-privacy
release-change-management
observability-ops
```

Require each reviewer to inspect the authoritative spec, ADR 0011, the current
`ops/maintainer/` implementation, and the failing PR-merge CI evidence.

- [x] **Step 2: Resolve blocking findings**

For every Blocker or High finding that exposes a new owner tradeoff, stop and
return that decision to the owner. Resolve mechanical safety/correctness gaps
directly in the accepted design. For scoped Medium findings, update the spec
when the fix is cheap and does not reopen an owner decision; otherwise record
an accepted follow-up.

- [x] **Step 3: Record review outcome**

Update the spec's `Decision And Review Gate` with reviewer dispositions and
remaining post-implementation review requirements.

- [x] **Step 4: Verify and commit review-only changes**

Run:

```bash
git diff --check
```

Expected: no output.

If documentation changed:

```bash
git add docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/superpowers/plans/2026-07-08-local-maintainer-simplification.md docs/architecture/adr/0011-local-codex-maintainer-control-plane.md
git commit -m "docs: resolve simplified maintainer design review"
```

### Task 2: Add Simple Lease And Phase State Beside Legacy Contracts

**Files:**
- Modify: `ops/maintainer/runtime.py`
- Create: `ops/maintainer/state.py`
- Create: `tests/test_maintainer_state.py`
- Modify: `tests/test_maintainer_runtime.py`

- [x] **Step 1: Write failing simple-lease tests**

Add tests for an interim `SimpleRunLease` contract without changing the legacy
`RunLease` contract consumed by the old CLI:

```python
lease = SimpleRunLease.acquire(state_dir, "curation", now=NOW)
assert lease.worker == "curation"
assert re.fullmatch(r"[0-9a-f]{32}", lease.run_id)

loaded = SimpleRunLease.load_owner(state_dir, "curation", lease.run_id)
loaded.heartbeat(now=NOW + timedelta(minutes=5))
loaded.release()
```

Add explicit regressions:

```python
def test_old_same_worker_run_id_cannot_adopt_stale_successor(tmp_path: Path) -> None:
    old = SimpleRunLease.acquire(tmp_path, "curation", now=NOW)
    new = SimpleRunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(LeaseOwnershipError):
        SimpleRunLease.load_owner(tmp_path, "curation", old.run_id)

    assert SimpleRunLease.load_owner(tmp_path, "curation", new.run_id) == new


def test_other_worker_cannot_use_active_run_id(tmp_path: Path) -> None:
    lease = SimpleRunLease.acquire(tmp_path, "discovery", now=NOW)

    with pytest.raises(LeaseOwnershipError):
        SimpleRunLease.load_owner(tmp_path, "curation", lease.run_id)
```

Keep new-contract tests for 0700 state directory, 0600 owner file, symlink
rejection, fresh lock busy, stale-lock preservation, matching heartbeat, and
matching release. Keep the old token/credential tests unchanged until Task 8;
they prove the intermediate repository still runs.

- [x] **Step 2: Run the lease tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_runtime.py -q
```

Expected: import failure because `SimpleRunLease` does not exist yet.

- [x] **Step 3: Implement the minimal lease model**

Add one strict owner payload and `SimpleRunLease` implementation:

```python
@dataclass(frozen=True)
class _OwnerMetadata:
    worker: str
    run_id: str
    acquired_at: datetime
    heartbeat_at: datetime


@dataclass(frozen=True)
class SimpleRunLease:
    worker: str
    run_id: str
    state_dir: Path

    @property
    def owner_path(self) -> Path:
        return self.state_dir / "run.lock" / "owner.json"
```

`acquire()` atomically creates `run.lock`, writes only the owner payload, and
preserves a stale lock before retrying. `load_owner()` requires exact worker and
run ID. Heartbeat atomically replaces the owner payload after rechecking the
same pair. Release renames the lock directory before deleting it and restores
it if ownership changed. The new implementation has no `token`,
`credential_path`, `assert_credential()`, `_write_worker_credential()`, or
`_remove_matching_credential()`. Leave legacy `RunLease` unchanged until Task
8, where `SimpleRunLease` is promoted to the final `RunLease` name.

- [x] **Step 4: Write failing phase-state tests**

Create strict models:

```python
class WorkPhase(StrEnum):
    SELECTED = "selected"
    PREPARED = "prepared"
    REVIEWED = "reviewed"
    VALIDATED = "validated"
    PUSHED = "pushed"
    PUBLISHED = "published"


class WorkState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    work_id: str
    worker: Literal["curation", "discovery"]
    run_id: str
    phase: WorkPhase
    updated_at: datetime
    pr_number: int | None = None
    candidate_key: str | None = None
    selected_head: str
    prepared_head: str | None = None
    reviewed_head: str | None = None
    validated_head: str | None = None
    backup_ref: str | None = None
```

Test monotonic phase transitions and `updated_at` advancement, exact worker/run
ownership, private atomic writes, malformed/oversized/symlink rejection, and
refusal to skip required fields for a phase. Curation state requires a PR
number; discovery state requires a candidate key and may receive its PR number
only after draft-PR creation.

- [x] **Step 5: Implement phase state and push journal**

In `state.py`, provide a `StateStore` with these exact public methods:

- `load_work(work_id: str) -> WorkState | None`
- `begin_work(state: WorkState, lease: SimpleRunLease) -> None`
- `save_work(state: WorkState, lease: SimpleRunLease) -> None`
- `load_push(work_id: str) -> PushJournal | None`
- `save_push(journal: PushJournal, lease: SimpleRunLease) -> None`
- `list_unresolved_pushes() -> tuple[PushJournal, ...]`
- `adopt_push(work_id: str, lease: SimpleRunLease, observed_remote_head: str | None) -> PushJournal`

`begin_work()` requires a phase-`selected` state owned by the current lease and
no unresolved push journal. It atomically replaces an ordinary record from a
prior inactive run only after its caller has revalidated the exact live PR/head
or candidate/catalog/proposal identity in the same capability invocation. The
old run cannot save over the replacement. A prior `pushed` phase without its
journal is inconsistent and fails closed. Test takeover/restart from selected,
prepared, reviewed, and validated; test old-run fencing and rejection when a
journal exists.

`PushJournal` contains `work_id`, `worker`, immutable `origin_run_id`, current
`recovery_run_id`, optional `pr_number`, `branch`, optional
`expected_remote_head`, `new_head`, optional discovery `candidate_key` and
`candidate_origin`, and
`phase: Literal["authorized", "pushed", "pr-created", "published"]`. A missing
expected remote head means create-only branch publication. The journal must
remain sufficient to resume discovery when ordinary `WorkState` is missing.
Work state is one file per stable work ID; push state remains separate. Reuse
one private atomic JSON helper rather than duplicating filesystem checks.

`list_unresolved_pushes()` is deterministic read-only inventory. Any unresolved
journal blocks fresh work. `adopt_push()` accepts only the worker named by
exactly one unresolved journal, requires the new current lease, verifies the
old recovery run no longer owns the lock, requires the observed remote to equal
the journaled old/absent or new state, preserves `origin_run_id`, and atomically
rebinds `recovery_run_id`. Multiple journals fail closed. Test stale takeover,
safe successor recovery, and rejection of every operation from the old run ID.

Add a bounded run-outcome model for the future skill/Triage handoff containing
worker, optional lease run ID, optional work ID and PR/candidate, optional last
phase, mutation status, and terminal/no-op reason. Pre-lease inspect,
proposal-cap, and no-candidate outcomes have no lease run ID. It is diagnostic
output only.

- [x] **Step 6: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_runtime.py tests/test_maintainer_state.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer/runtime.py ops/maintainer/state.py tests/test_maintainer_runtime.py tests/test_maintainer_state.py
uv run ruff format --check ops/maintainer/runtime.py ops/maintainer/state.py tests/test_maintainer_runtime.py tests/test_maintainer_state.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/runtime.py ops/maintainer/state.py tests/test_maintainer_runtime.py tests/test_maintainer_state.py
git commit -m "refactor: add simplified maintainer runtime state"
```

### Task 3: Add Safe Errors And Reduced Machine State

**Files:**
- Create: `ops/maintainer/errors.py`
- Modify: `ops/maintainer/models.py`
- Modify: `tests/test_maintainer_models.py`
- Create: `tests/test_maintainer_errors.py`

- [x] **Step 1: Write failing safe-error tests**

Define the expected interface in tests:

```python
error = MaintainerError(
    reason="stale-head",
    stage="pre-push",
    check="remote-head",
    kind="mismatch",
    detail="PR head changed after review",
)
assert error.payload() == {
    "status": "error",
    "reason": "stale-head",
    "stage": "pre-push",
    "check": "remote-head",
    "kind": "mismatch",
    "detail": "PR head changed after review",
}
```

Reject control characters, text over 160 characters, unknown reasons/stages,
unknown check/kind values, URLs, absolute paths, and strings containing
token-like assignments. Checks and kinds are optional strict enums that retain
safe diagnostic detail such as `catalog-validation` plus `command-failed`
without exposing subprocess output. Test that an unexpected exception maps
only to:

```json
{"status":"error","reason":"internal-error","stage":"dispatch"}
```

- [x] **Step 2: Run error tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_errors.py -q
```

Expected: import failure because `errors.py` does not exist.

- [x] **Step 3: Implement the safe error contract**

Implement strict allowlists for the reasons and stages used by the four
capabilities. `MaintainerError.payload()` may emit only validated repository-
authored detail. Never include raw exception text, subprocess output, PR text,
source content, or environment values.

Use this shape:

```python
class ErrorReason(StrEnum):
    INVALID_COMMAND = "invalid-command"
    INVALID_GITHUB_STATE = "invalid-github-state"
    AUTHENTICATION_FAILED = "authentication-failed"
    LOCK_BUSY = "lock-busy"
    LEASE_OWNERSHIP = "lease-ownership-error"
    STALE_HEAD = "stale-head"
    REBASE_CONFLICT = "rebase-conflict"
    INTENT_DRIFT = "intent-drift"
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


def validate_safe_detail(detail: str) -> str:
    if not detail or len(detail) > 160:
        raise ValueError("safe detail must contain 1-160 characters")
    if any(ord(character) < 32 for character in detail):
        raise ValueError("safe detail contains a control character")
    lowered = detail.lower()
    if "://" in detail or detail.startswith(("/", "~")):
        raise ValueError("safe detail contains a URL or absolute path")
    if any(term in lowered for term in ("token=", "password=", "secret=")):
        raise ValueError("safe detail contains a credential-like assignment")
    return detail


@dataclass(frozen=True)
class MaintainerError(Exception):
    reason: ErrorReason
    stage: ErrorStage
    check: ErrorCheck | None = None
    kind: ErrorKind | None = None
    detail: str | None = None

    def payload(self) -> dict[str, str]:
        payload = {
            "status": "error",
            "reason": self.reason.value,
            "stage": self.stage.value,
        }
        if self.check is not None:
            payload["check"] = self.check.value
        if self.kind is not None:
            payload["kind"] = self.kind.value
        if self.detail is not None:
            payload["detail"] = validate_safe_detail(self.detail)
        return payload
```

- [x] **Step 4: Write failing reduced-machine-state tests**

Add `MachineStateV2` for the reduced contract while retaining legacy
`MachineState` until atomic cutover:

```python
class MachineStateV2(_MaintainerModel):
    schema_version: Literal[2] = 2
    reviewed_head: str | None = None
    validated_head: str | None = None
    candidate_key: str | None = None
    candidate_origin: Literal["backlog", "external"] | None = None
    last_operation: Literal[
        "none", "reviewed", "validated", "pushed", "published"
    ] = "none"
```

Require `schema_version == 2` and candidate key and origin together. The new
model has no `lineage_id`,
`completed_cycles`, candidate fingerprints, regional graph key, or publication
phase duplication. Task 8 deletes legacy `MachineState` and promotes
`MachineStateV2` to the final name.

- [x] **Step 5: Implement, run tests, and commit**

Run:

```bash
uv run pytest tests/test_maintainer_errors.py tests/test_maintainer_models.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer/errors.py ops/maintainer/models.py tests/test_maintainer_errors.py tests/test_maintainer_models.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/errors.py ops/maintainer/models.py tests/test_maintainer_errors.py tests/test_maintainer_models.py
git commit -m "refactor: add reduced maintainer machine contracts"
```

### Task 4: Replace Policy Selection With Safe Inspection

**Files:**
- Create: `ops/maintainer/inspection.py`
- Create: `tests/test_maintainer_inspection.py`
- Modify: `ops/maintainer/github.py`
- Modify: `tests/test_maintainer_github.py`
- Delete after migration: policy-only selection code from `ops/maintainer/curation.py`

- [x] **Step 1: Write failing curation inventory tests**

Target interface:

```python
inventory = inspect_curation(
    prs,
    comments_by_pr,
    unresolved_pushes=(),
)
assert [item.number for item in inventory.eligible] == [21, 25]
assert inventory.eligible[0].head_sha == SHA_A
```

Verify deterministic filtering only:

- same repository and owner;
- `main` base;
- `codex/*` head;
- catalog-only allowed changed paths;
- not `maintainer:proposal`;
- not paused by `manual-check`, `owner-decision`, or `blocked` for the same head.

Do not sort by age as policy and do not return a selected PR. Return strict
operational `CurationCandidate` summaries without title, body, URL, or other PR
prose; sort by PR number solely for output determinism.

- [x] **Step 2: Write failing discovery inventory tests**

Target interface:

```python
inventory = inspect_discovery(
    catalog_keys,
    open_pull_requests,
    closed_pull_requests,
    comments,
    unresolved_pushes=(),
)
assert inventory.open_proposal_count == 2
assert inventory.open_candidate_keys == frozenset({
    "stay_destination:nendaz",
    "ski_area:thyon-ski-area",
})
assert inventory.can_create_proposal is True
assert inventory.has_unknown_proposal_identity is False
assert inventory.unresolved_pushes == ()
assert inventory.closed_proposals[0].lifecycle_state == "CLOSED"
```

All open proposal-labeled PRs count toward the cap, even when their machine
comment is missing. Candidate keys are included only when exactly one valid
canonical comment provides them. A missing, malformed, or multiple canonical
comment sets `has_unknown_proposal_identity` and makes
`can_create_proposal=False`, even below the numeric cap. Closed summaries expose
safe PR metadata for Codex interpretation but do not produce declined
fingerprints or hard suppression.

Open and closed PRs are separate inputs. Only lifecycle-`OPEN` PRs carrying
`maintainer:proposal` consume the cap. Lifecycle-`CLOSED` or `MERGED` PRs in
`lane:catalog-discovery` appear only in history, even when their old proposal
label remains. Reject a PR appearing in both inputs or with a lifecycle that
does not match its input.

Both curation and discovery inventory include unresolved local push journals.
Any unresolved journal makes every fresh eligible list empty and proposal
creation false. Exactly one journal identifies the worker/work item that must be
recovered; multiple journals expose a fail-closed invalid state for owner
attention rather than selecting one.

- [x] **Step 3: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_inspection.py -q
```

Expected: import failure because `inspection.py` does not exist.

- [x] **Step 4: Implement inspection and GitHub reads**

Create strict frozen inventory models and a private strict schema-version-2
canonical-comment parser. Keep complete GitHub pagination, 120-second bounds,
scoped auth, and exact `lampssy` verification. Add a fully paginated
`list_all_open_pull_requests()` for the simplified CLI while retaining the
legacy capped method until Task 8. Remove helper-side oldest-first selection,
`next_cycle_decision`, declined fingerprints, and discovery fingerprints.

The selection boundary must remain visibly absent from the helper:

```python
def inspect_curation(
    prs: Iterable[PullRequest],
    comments_by_pr: Mapping[int, Sequence[GitHubComment]],
    unresolved_pushes: Sequence[PushJournal],
) -> CurationInventory:
    if unresolved_pushes:
        return CurationInventory.blocked_by_pushes(unresolved_pushes)
    return safe_curation_candidates_without_policy_selection(...)


def inspect_discovery(
    catalog_keys: AbstractSet[str],
    open_pull_requests: Iterable[PullRequest],
    closed_pull_requests: Iterable[PullRequest],
    comments_by_pr: Mapping[int, Sequence[GitHubComment]],
    *,
    unresolved_pushes: Sequence[PushJournal],
) -> DiscoveryInventory:
    if unresolved_pushes:
        return DiscoveryInventory.blocked_by_pushes(
            catalog_keys,
            unresolved_pushes,
        )
    open_prs = require_open_prs(open_pull_requests)
    closed_prs = require_closed_prs(closed_pull_requests)
    require_disjoint_pr_numbers(open_prs, closed_prs)
    open_proposals = tuple(
        proposal_summary(pr, comments_by_pr.get(pr.number, ()))
        for pr in open_prs
        if "maintainer:proposal" in pr.labels
    )
    closed_proposals = tuple(
        proposal_summary(pr, comments_by_pr.get(pr.number, ()))
        for pr in closed_prs
        if "lane:catalog-discovery" in pr.labels
    )
    return DiscoveryInventory.from_current_state(
        catalog_keys,
        open_proposals,
        closed_proposals,
)
```

Normalize unresolved journals before reading PR input; reject duplicate work IDs
or terminal records and return the blocked inventory first. Curation pause
labels exclude the exact reviewed head; one valid trusted V2 comment with a
different reviewed head proves a new commit and permits re-entry. Missing,
malformed, multiple, legacy, or headless pause state remains excluded.

`proposal_summary()` parses only the canonical maintainer comment through the
V2 parser and returns the PR number, lifecycle, current head, and candidate key
when trusted state is valid. `DiscoveryInventory.from_current_state()` counts
every open proposal-labeled PR, derives known open candidate keys from valid
comments, copies the catalog key set, and sets `can_create_proposal` only when
`open_proposal_count < 3` and no open proposal has unknown identity. Test
missing, malformed, and multiple comments explicitly.

- [x] **Step 5: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_inspection.py tests/test_maintainer_github.py tests/test_maintainer_models.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer/inspection.py ops/maintainer/github.py tests/test_maintainer_inspection.py tests/test_maintainer_github.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/inspection.py ops/maintainer/github.py tests/test_maintainer_inspection.py tests/test_maintainer_github.py
git commit -m "refactor: expose safe maintainer inventories"
```

### Task 5: Narrow Guarded Preparation To Objective Scope

**Files:**
- Modify: `ops/maintainer/intent.py`
- Modify: `ops/maintainer/git_ops.py`
- Modify: `tests/test_maintainer_intent.py`
- Modify: `tests/test_maintainer_git_ops.py`

- [x] **Step 1: Write failing intent-scope tests**

Add an `IntentSnapshotV2` contract limited to:

```python
class IntentSnapshotV2(BaseModel):
    changed_paths: frozenset[str]
    diff_entries: tuple[IntentDiffEntry, ...]
    catalog_targets: frozenset[str]
    report_targets: frozenset[str]
```

The V2 snapshot has no `removed_backlog_markers`. Add new tests proving
ordinary backlog prose can change without marker parsing, while an executable
Python/test change, unexpected path, symlink, submodule, or disallowed file mode
remains rejected. Retain the legacy snapshot field and comparison path until
Task 8 so the old CLI remains runnable.

- [x] **Step 2: Run intent tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_intent.py -q
```

Expected: import failures for the missing additive `IntentSnapshotV2` and
`compare_intent_v2` APIs. Existing legacy intent tests must continue to pass.

- [x] **Step 3: Implement objective intent comparison**

The V2 intent comparison must require stable changed-path/file-mode scope and
prevent loss or expansion of catalog/report targets across rebase. It must not
read or interpret backlog Markdown. Keep the allowed catalog, trust, report,
backlog, and owned-doc paths; executable code remains outside curation scope.

The comparison itself stays small:

```python
def compare_intent_v2(
    before: IntentSnapshotV2,
    after: IntentSnapshotV2,
) -> None:
    if before.changed_paths != after.changed_paths:
        raise IntentDriftError("changed path scope changed during preparation")
    if before.diff_entries != after.diff_entries:
        raise IntentDriftError("file mode or change kind changed during preparation")
    if before.catalog_targets != after.catalog_targets:
        raise IntentDriftError("catalog target scope changed during preparation")
    if before.report_targets != after.report_targets:
        raise IntentDriftError("curation report target scope changed during preparation")
```

- [x] **Step 4: Preserve guarded git invariants**

Retain and test:

- approved repository and effective fetch/push remote;
- exact selected head and fetched `origin/main`;
- clean worktree;
- backup ref;
- conflict abort;
- prepared ref bound to selected/base/rebased heads;
- exact remote-head recheck;
- exact `--force-with-lease`;
- new discovery-branch publication only through an atomic create-only push with
  an empty expected-value lease
  (`--force-with-lease=refs/heads/<branch>:` and a normal refspec), never a
  check-then-ordinary-push sequence;
- noninteractive SSH and sanitized timeout/auth/transport errors.

Add a race regression where the ref appears after preflight and prove the push
fails without updating it. Retain legacy entry points consumed by the old CLI;
the V2 caller stores `GuardedSyncResult` in `WorkState`, and Task 8 removes the
old attempt/prepared dependencies.

- [x] **Step 5: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_intent.py tests/test_maintainer_git_ops.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer/intent.py ops/maintainer/git_ops.py tests/test_maintainer_intent.py tests/test_maintainer_git_ops.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/intent.py ops/maintainer/git_ops.py tests/test_maintainer_intent.py tests/test_maintainer_git_ops.py
git commit -m "refactor: narrow maintainer branch preparation"
```

### Task 6: Consolidate Exact-Head Validation

**Files:**
- Create: `ops/maintainer/validation.py`
- Create: `tests/test_maintainer_validation.py`
- Move retained validation code from: `ops/maintainer/curation.py`
- Move retained proposal verification from: `ops/maintainer/cli.py`

- [x] **Step 1: Write failing curation-validation tests**

Target function:

```python
result = validate_curation(
    pull_request=pr,
    sync=prepared,
    reviewed_head=SHA_B,
    report_path="docs/catalog-curation/example.json",
    repository=repository,
    base_repository=base_repository,
)
assert result.validated_head == SHA_B
assert result.commands_completed == 3
```

Retain fixed commands for catalog validation, curation reconciliation, and
focused catalog tests. Retain the minimal allowlisted environment, process
group cleanup, fixed 600-second per-command timeout, bounded observations, and
pre/post live-state revalidation. Preserve safe stages
`preflight`, `catalog-validation`, `curation-reconciliation`, `catalog-tests`,
and `post-validation`.

- [x] **Step 2: Write failing proposal-validation tests**

Target function:

```python
result = validate_proposal(
    candidate_key="stay_destination:nendaz",
    candidate_origin="backlog",
    base=SHA_A,
    head=SHA_B,
    snapshot=intent,
    discovery_inventory=inventory,
    repository=repository,
)
assert result.candidate_key == "stay_destination:nendaz"
assert result.validated_head == SHA_B
```

Require:

- candidate key is newly present in catalog targets;
- exact catalog and trust files changed;
- exactly one schema-version-2 curation JSON report covers the candidate and
  trust target;
- report reconciliation passes;
- proposed catalog loads canonically and has no error-level policy issue;
- candidate is not already in the base catalog;
- current discovery inventory is below cap, has no same-key open proposal, and
  has no proposal with unknown canonical-comment identity.

Do not parse backlog, require marker cleanup, read a registry, compare
fingerprints, rotate regions, or inspect a body origin marker.

- [x] **Step 3: Run validation tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_validation.py -q
```

Expected: import failure because `validation.py` does not exist.

- [x] **Step 4: Implement validation and remove policy coupling**

Move only objective validators into `validation.py`. Raise `MaintainerError`
with safe reason/stage/check/kind/detail. Return strict `ValidationResult` and
`ProposalValidationResult` models. Do not select workflow states. Keep the old
curation validation entry points in place until Task 8; this task adds the V2
module without breaking the old CLI.

Expose only these validation entry points:

```python
def validate_curation(
    *,
    pull_request: PullRequest,
    sync: GuardedSyncResult,
    reviewed_head: str,
    report_path: str,
    repository: GitRepository,
    base_repository: GitRepository,
    runner: ValidationCommandRunner | None = None,
) -> ValidationResult:
    return CurationValidator(runner=runner).validate(
        pull_request=pull_request,
        sync=sync,
        reviewed_head=reviewed_head,
        report_path=report_path,
        repository=repository,
        base_repository=base_repository,
    )


def validate_proposal(
    *,
    candidate_key: str,
    candidate_origin: Literal["backlog", "external"],
    base: str,
    head: str,
    snapshot: IntentSnapshotV2,
    discovery_inventory: DiscoveryInventory,
    repository: GitRepository,
) -> ProposalValidationResult:
    return ProposalValidator().validate(
        candidate_key=candidate_key,
        candidate_origin=candidate_origin,
        base=base,
        head=head,
        snapshot=snapshot,
        discovery_inventory=discovery_inventory,
        repository=repository,
    )
```

- [x] **Step 5: Run focused catalog regressions and commit**

Run:

```bash
uv run pytest tests/test_maintainer_validation.py tests/test_catalog_trust.py tests/test_catalog_models.py tests/test_catalog_schema_v2.py tests/test_catalog_loader_v2.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer/validation.py tests/test_maintainer_validation.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/validation.py tests/test_maintainer_validation.py
git commit -m "refactor: consolidate maintainer validation"
```

### Task 7: Simplify Publication And Readiness

**Files:**
- Modify: `ops/maintainer/publication.py`
- Create: `tests/test_maintainer_publication.py`
- Modify: `ops/maintainer/github.py`
- Modify: `tests/test_maintainer_github.py`

- [x] **Step 1: Write failing canonical-comment tests**

Keep one marker containing an actual versioned JSON object:

```text
<!-- snowcast-maintainer-state:{"schema_version":2,"reviewed_head":"abc123"} -->
```

Test one strict schema-version-2 `MachineStateV2` in the marked `lampssy`
comment. Legacy version 1, missing versions, and unknown versions are untrusted
and require fresh review; they are never silently upgraded. Remove the
discovery-origin body marker and body/comment matching. A missing or malformed
comment returns no trusted review state; it never reconstructs readiness. An
open proposal with a missing, malformed, or multiple canonical comment has
unknown identity and blocks every new proposal publication. A journal-bound
recovery of the same incomplete initial publication is the only path that may
repair the comment directly from its validated candidate evidence.

- [x] **Step 2: Write failing lifecycle request tests**

Target interface:

```python
plan = publication_plan(
    requested_state=MaintainerState.OWNER_DECISION,
    pull_request=pr,
    machine_state=machine,
)
assert plan.state is MaintainerState.OWNER_DECISION
```

For `working`, `owner-decision`, `manual-check`, and `blocked`, enforce only
allowlisted state, exact PR/head authority, and one lifecycle label.

For objective states, add tests that:

- draft proposal creation requires validated proposal evidence, an absent
  remote branch, an open slot, no same-key open proposal, and no unknown open
  proposal identity;
- proposal requires validated proposal evidence, an open slot, and no unknown
  open proposal identity;
- waiting-ci requires exact reviewed/validated/pushed head and pending checks;
- ready requires exact reviewed/validated/current head, successful required
  checks, mergeability, no proposal label, and no owner/manual/blocked request.

Any new head invalidates prior ready evidence.

- [x] **Step 3: Write failing publication-input and crash-recovery tests**

Require `--title-file`, `--body-file`, and `--summary-file` inputs to be
direct-child, owner-owned, owner-private regular files in the mode-0700
maintainer state directory. Accept only a basename with no separators, `.` or
`..`; open the already-validated state-directory descriptor and then open that
basename relative to it with `O_NOFOLLOW`. Verify the opened descriptor with
`fstat`, enforce strict limits (256 bytes title, 64 KiB body, 16 KiB summary),
and decode strict UTF-8. Reject absolute, parent, nested, outside-state,
leaf-symlink, ancestor-symlink, non-regular, group/other-readable, oversized,
and non-UTF-8 inputs without echoing the path or content in errors. Pass only
validated strings to `GitHubClient`; it writes its own mode-0600 temporary files
for `gh`.

Add crash injection immediately after discovery branch push and before PR
creation. On retry with intact journal and missing `WorkState`, require:

- remote absent: retry only the atomic create-only push;
- remote equals journaled new head: find PR by exact repository/head branch;
- no PR: create one draft PR and persist its positive number;
- one PR: persist that number and resume body/comment/labels idempotently;
- multiple PRs or any other remote head: fail closed.

Also inject crashes after PR creation and between each GitHub publication step;
prove retries create neither a second PR nor a second canonical comment.
If recovery finds a canonical proposal comment but no proposal label, fail
closed: that state is indistinguishable from explicit owner acceptance and the
workflow must never restore the label automatically.
Test stale takeover explicitly: read-only inspection blocks fresh work, the
matching successor lease adopts the sole journal after allowed remote
observation, the immutable origin run ID remains, and the old run cannot update
the adopted journal or publish. Multiple unresolved journals fail closed.

- [x] **Step 4: Run publication tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_publication.py -q
```

Expected: failures because current publication expects lineage fields and
duplicated discovery-origin state.

- [x] **Step 5: Implement idempotent publication**

Retain an allowlisted managed human-readable body block so Codex cannot
overwrite text outside the owned block. Publish one canonical comment and one
lane/state label. Refetch the full PR immediately before body/comment/label
writes and reject changed metadata or head. Partial publication is retried by
recomputing the same desired state for the same head.

Add the V2 `GitHubClient.create_draft_pull_request()` path with explicit
repository, `main` base, validated `codex/catalog-curation-*` head branch,
validated title/body strings, and a parsed positive PR number. Before creation,
recheck proposal cap, candidate duplication, unknown proposal identity, local
head, remote branch absence, and validated proposal evidence. Atomically create
the new remote ref with the empty expected-value lease, record `pushed`, find or
create exactly one draft PR, record `pr-created`, then publish the body,
canonical comment, and labels idempotently before recording `published`.

Keep old publication/GitHub methods consumed by the old CLI until Task 8. New
GitHub methods may be added beside them, but caller-selected filesystem paths
must never be passed to `gh`.

The objective readiness branch must be explicit:

```python
def require_ready(
    pull_request: PullRequest,
    machine_state: MachineStateV2,
) -> None:
    if pull_request.head_sha != machine_state.reviewed_head:
        raise MaintainerError(
            reason=ErrorReason.STALE_HEAD,
            stage=ErrorStage.READINESS,
            detail="PR head differs from the reviewed head",
        )
    if machine_state.validated_head != pull_request.head_sha:
        raise MaintainerError(
            reason=ErrorReason.VALIDATION_REQUIRED,
            stage=ErrorStage.READINESS,
            detail="current head has no matching validation",
        )
    if (
        pull_request.check_state != "success"
        or pull_request.mergeable != "MERGEABLE"
    ):
        raise MaintainerError(
            reason=ErrorReason.NOT_READY,
            stage=ErrorStage.READINESS,
            detail="required checks or mergeability are not ready",
        )
    if "maintainer:proposal" in pull_request.labels:
        raise MaintainerError(
            reason=ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
            stage=ErrorStage.READINESS,
            detail="proposal still requires owner approval",
        )
```

- [x] **Step 6: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_publication.py tests/test_maintainer_github.py tests/test_maintainer_models.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer/publication.py ops/maintainer/github.py tests/test_maintainer_publication.py tests/test_maintainer_github.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/publication.py ops/maintainer/github.py tests/test_maintainer_publication.py tests/test_maintainer_github.py
git commit -m "refactor: simplify maintainer publication state"
```

### Task 8: Rewrite The CLI Around Four Capabilities

**Files:**
- Modify: `ops/maintainer/cli.py`
- Modify: `tests/test_maintainer_cli.py`
- Delete: `ops/maintainer/curation.py`
- Delete: `ops/maintainer/discovery.py`
- Delete: `tests/test_maintainer_curation.py`
- Delete: `tests/test_maintainer_discovery.py`
- Delete: `docs/catalog-discovery/alpine-coverage-registry.json`

- [ ] **Step 1: Replace CLI parser contract tests**

The target surface is:

```text
lock acquire <curation|discovery>
lock heartbeat <worker> --run-id <id>
lock release <worker> --run-id <id>

inspect curation
inspect discovery

prepare curation --pr <number> --run-id <id>

validate curation --pr <number> --reviewed-head <sha> --report <path> --base-dir <path> --run-id <id>
validate proposal --candidate-key <key> --candidate-origin <backlog|external> --base <sha> --head <sha> --run-id <id>

publish push --pr <number> --run-id <id>
publish recover --work-id <id> --run-id <id>
publish proposal --branch <branch> --candidate-key <key> --candidate-origin <backlog|external> --head <sha> --title-file <path> --body-file <path> --summary-file <path> --run-id <id>
publish state --pr <number> --state <state> --reviewed-head <sha> --summary-file <path> [--body-file <path>] --run-id <id>
publish ensure-labels --worker <curation|discovery> --run-id <id>
```

`inspect` is read-only and needs no lease. Every mutation requires exact worker
and run ID. Discovery backlog/web research occurs before acquisition; once
Codex chooses a candidate it acquires discovery, re-runs `inspect discovery`,
and then mutates. Publication text files are resolved only within the configured
private state directory through the safe reader specified in Task 7.

Every inspect result includes unresolved push-journal inventory before eligible
work. Fresh selection is forbidden while that inventory is non-empty. With
exactly one journal, only its named worker may acquire/adopt and run
`publish recover`; multiple journals fail closed for owner attention.

- [ ] **Step 2: Write failing capability integration tests**

Cover one happy and one safe-stop path for each capability, not the old full
cross-product:

```python
assert main(["inspect", "curation"], github=fake) == 0
assert output["eligible"] == [{
    "number": 42,
    "head_sha": SHA_A,
    "head_ref_name": "codex/catalog-curation-example",
    "base_ref_name": "main",
    "labels": ["lane:catalog-curation"],
    "check_state": "pending",
    "mergeable": "MERGEABLE",
}]

assert main([
    "prepare", "curation", "--pr", "42", "--run-id", run_id
], github=fake, repository=repo) == 0

assert main([
    "publish", "state", "--pr", "42", "--state", "ready",
    "--reviewed-head", SHA_B, "--summary-file", str(summary),
    "--run-id", run_id,
], github=fake) == 0
```

Test structured safe errors for stale head, conflict, validation failure,
proposal cap, duplicate open key, CI pending, and internal exception. Assert no
token, environment value, raw subprocess output, PR prose, or source content is
printed. Assert every terminal response includes the bounded run-outcome fields:
worker, optional lease run ID, optional work ID and PR/candidate, optional last
phase, mutation status, and terminal/no-op reason. Pre-lease responses omit
lease run ID. Cover success, expected no-op, retryable transport failure,
validation substage failure, and internal error.

- [ ] **Step 3: Run CLI tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_cli.py -q
```

Expected: failures because the old curation/discovery command families and
artifact chain remain.

- [ ] **Step 4: Implement thin dispatch and phase transitions**

Keep `cli.py` as argument parsing and dependency composition only. Delegate
inspection, preparation, validation, publication, state storage, and errors to
their modules. After each successful mutating capability, atomically update the
one `WorkState`. Use the separate push journal for authorization and recovery.
At fresh selection, refetch and revalidate the exact PR/head or discovery facts
before `begin_work()` replaces any inactive pre-push record. Never replace a
work record while an unresolved journal exists; a `pushed` record without its
journal is an owner-visible inconsistent-state error.

This is the atomic compatibility cutover. In the same commit:

- switch every command to the V2 capability contracts;
- rename `SimpleRunLease` to final `RunLease` and remove the legacy token/
  credential lease implementation;
- promote `MachineStateV2` to final `MachineState` and remove legacy fields;
- promote `IntentSnapshotV2`/`compare_intent_v2` to the final intent names and
  remove backlog-marker semantics;
- remove compatibility intent/publication/GitHub adapters;
- delete the old workflow modules, parser, runtime registry, and obsolete
  tests; and
- leave no commit in which the checked-in CLI calls a removed contract.

Dispatch through one explicit table rather than nested workflow policy:

```python
Handler = Callable[[argparse.Namespace, Dependencies], dict[str, object]]

HANDLERS: dict[tuple[str, str], Handler] = {
    ("inspect", "curation"): handle_inspect_curation,
    ("inspect", "discovery"): handle_inspect_discovery,
    ("prepare", "curation"): handle_prepare_curation,
    ("validate", "curation"): handle_validate_curation,
    ("validate", "proposal"): handle_validate_proposal,
    ("publish", "push"): handle_publish_push,
    ("publish", "recover"): handle_publish_recover,
    ("publish", "proposal"): handle_publish_proposal,
    ("publish", "state"): handle_publish_state,
    ("publish", "ensure-labels"): handle_ensure_labels,
}


def dispatch(args: argparse.Namespace, dependencies: Dependencies) -> dict[str, object]:
    handler = HANDLERS.get((args.family, args.command))
    if handler is None:
        raise MaintainerError(
            reason=ErrorReason.INVALID_COMMAND,
            stage=ErrorStage.DISPATCH,
            detail="command is outside the maintainer capability surface",
        )
    return handler(args, dependencies)
```

Do not retain:

- deterministic oldest-first selection;
- backlog parsing or marker cleanup;
- coverage registry validation/selection/nomination;
- candidate fingerprints or regional graph rotation;
- persistent lineage/cycle counters;
- selected/prepared/validated/publication artifact classes;
- body origin marker matching; or
- broad exception-to-lifecycle policy.

- [ ] **Step 5: Delete obsolete modules, tests, and registry**

Move every retained objective function first. Then remove the files listed in
this task and run:

```bash
rg -n "parse_catalog_backlog|CoverageRegistry|origin_fingerprint|completed_cycles|run\.credential|snowcast-discovery-origin" ops tests docs
```

Expected: no runtime/test references; historical superseded documentation may
contain the old names only when clearly marked historical.

Stage this atomic cutover with deletion-aware scoped staging and inspect it:

```bash
git add -A -- ops/maintainer tests docs/catalog-discovery/alpine-coverage-registry.json
git diff --cached --stat
git diff --cached --check
```

- [ ] **Step 6: Run the complete maintainer suite and commit**

Run:

```bash
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check ops/maintainer tests/test_maintainer_*.py
uv run ruff format --check ops/maintainer tests/test_maintainer_*.py
```

Expected: all pass, with materially fewer tests than the old 589-test matrix
while retaining the safety properties enumerated in the spec.

Commit:

```bash
git commit -m "refactor: thin the Snowcast maintainer control plane"
```

### Task 9: Reconcile Documentation And Future Skill Contract

**Files:**
- Modify: `README.md`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/superpowers/plans/2026-07-08-local-maintainer-automation.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- Create: `docs/operating-model/local-maintainer-activation.md`
- Review: `docs/product-backlog.md`
- Do not create yet: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`

- [ ] **Step 1: Update operator documentation**

Document the final CLI, simple owner record, phase state, push journal, safe
errors, canonical comment, readiness contract, Codex-selected PRs, semantic
backlog discovery, no runtime registry, and shorter discovery mutation-window
lease. Document atomic create-only proposal branches, unknown-proposal
fail-closed behavior, private publication files, heartbeat cadence, Triage
outcome fields, and push-before-PR crash recovery.

- [ ] **Step 2: Replace the post-merge skill specification**

The future skill must direct Codex to:

- inspect and choose at most one safe PR;
- acquire curation before prepare and hold through publication;
- inspect unresolved journals before choosing fresh work; recover/adopt exactly
  one matching journal first and escalate multiple journals;
- interpret backlog/research read-only before discovery acquisition;
- acquire discovery, rerun discovery inspection, then mutate;
- perform at most two review/fix cycles and use a fresh independent
  `snowcast-catalog-review` reviewer context after every fix;
- bind each complete review disposition to the exact reviewed head and route
  incomplete/unresolved review to manual-check or owner-decision;
- heartbeat before/after capabilities and at least every five minutes while a
  lease is held;
- request semantic states but rely on helper gates for proposal/waiting/ready;
- report the bounded Triage outcome for every terminal/no-op result, omitting
  lease run ID for pre-lease outcomes;
- never push or publish outside the helper;
- never approve or merge.

Keep installation and automation activation blocked until the refactored PR is
merged and receives post-merge skill/automation review.

- [ ] **Step 3: Write the separate post-merge activation and rollback checklist**

Create `docs/operating-model/local-maintainer-activation.md` as the only future
activation procedure. Fix this order:

1. verify the exact PR head was merged to current `main`;
2. install the simplified personal skill from reviewed merged docs;
3. run read-only helper and project-scoped GitHub-auth smoke checks;
4. provision the allowlisted labels;
5. create curation and discovery schedules disabled where the app supports it;
6. inspect the installed skill and actual automation records;
7. run post-merge security, release, and observability review; and
8. enable only after explicit owner approval.

Rollback begins by pausing/disabling both schedules, preserves the private state
directory and push journals for diagnosis, removes the installed personal skill
when required, and reverts the helper through normal Git history. It must not
reuse executable instructions from the superseded Task 10.

- [ ] **Step 4: Mark implementation status accurately**

Update the authoritative spec from accepted design to implemented only after
all code and verification tasks pass. Retain the old spec/plan as superseded
history; do not leave executable Task 10 instructions that contradict the new
design.

- [ ] **Step 5: Verify docs and commit**

Run:

```bash
git diff --check
rg -n "69-entry|run\.credential|private lease token|deterministic backlog parser" README.md docs/engineering-notes.md docs/superpowers
```

Expected: old terms appear only in clearly marked historical/superseded
sections or the simplification rationale.

Commit:

```bash
git add README.md docs/engineering-notes.md docs/operating-model/local-maintainer-activation.md docs/superpowers docs/product-backlog.md
git commit -m "docs: align simplified maintainer operations"
```

### Task 10: Review, Prospective-Merge Verification, And PR Update

**Files:**
- Review: complete diff from the current PR base through `HEAD`
- No automation or personal-skill files may be installed

- [ ] **Step 1: Run focused advisory feature review**

Invoke:

```text
ai-llm-reliability
security-privacy
release-change-management
observability-ops
```

in `feature-review` mode. Fix Blocker/High findings and cheap scoped Mediums;
record accepted residual Medium/Low findings.

- [ ] **Step 2: Run controlling feature-branch verification**

Run:

```bash
uv run pytest tests/test_maintainer_*.py -q
uv run pytest -q tests/test_catalog_trust.py tests/test_catalog_models.py tests/test_catalog_schema_v2.py tests/test_catalog_loader_v2.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py
uv run --no-config ruff check .
uv run --no-config ruff format --check .
uv run --no-config pytest
git diff --check
git status --short
```

Expected: all tests and checks pass; worktree clean.

- [ ] **Step 3: Verify the prospective merge with current main**

Run from the implementation worktree:

```bash
git fetch origin main
base_sha="$(git rev-parse origin/main)"
feature_sha="$(git rev-parse HEAD)"
merge_dir="$(git rev-parse --show-toplevel)/../local-maintainer-merge-check"
test ! -e "$merge_dir"
cleanup_merge_check() {
  if test -e "$merge_dir"; then
    git -C "$merge_dir" merge --abort >/dev/null 2>&1 || true
    git worktree remove --force "$merge_dir" >/dev/null 2>&1 || true
  fi
}
trap cleanup_merge_check EXIT INT TERM
git worktree add --detach "$merge_dir" "$base_sha"
git -C "$merge_dir" merge --no-commit --no-ff "$feature_sha"
(
  cd "$merge_dir"
  uv sync --dev --no-config
  uv run --no-config ruff check .
  uv run --no-config ruff format --check .
  uv run --no-config pytest
)
cleanup_merge_check
trap - EXIT INT TERM
printf 'verified base=%s feature=%s\n' "$base_sha" "$feature_sha"
```

Expected: the detached worktree starts at the captured current base SHA and
merges the captured feature SHA in the same direction as GitHub's synthetic
merge. The exact CI install, Ruff lint, Ruff format, and pytest commands pass.
Cleanup runs on success and every failure path; record both SHAs in the final
verification and PR body.

- [ ] **Step 4: Recheck PR metadata, push normally, and rewrite PR #43**

Verify the remote branch still points at the previously published PR head
before pushing. Then:

```bash
git push origin codex/local-maintainer-automation-implementation
```

Do not force-push this implementation branch. Confirm PR #43 remains draft and
targets `main`.

Prepare a private temporary body file and explicitly rewrite PR #43 after the
verified push:

```bash
GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast" \
  GH_PROMPT_DISABLED=1 \
  gh pr edit 43 \
    --repo lampssy/ai-sports-travel-planner \
    --body-file "$pr_body_file"
```

The final body must describe the four capability groups, Codex-versus-helper
boundary, deleted parser/registry/token/lineage surfaces, atomic cutover and
rollback unit, design/feature advisory outcomes, captured verified base and
feature SHAs, normal non-force branch update, and continued activation block.
Refetch the PR and assert it is draft, targets `main`, contains the exact SHAs,
and contains none of the obsolete live claims such as a runtime 69-entry
registry, deterministic backlog selection, private lease tokens, or old test
counts.

- [ ] **Step 5: Watch GitHub CI**

Use the project-scoped profile:

```bash
GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast" \
  GH_PROMPT_DISABLED=1 \
  gh pr checks 43 --repo lampssy/ai-sports-travel-planner --watch --interval 10
```

Expected: the push and pull-request merge-state runs pass. Stop without merge
or activation and hand PR #43 back to the owner.

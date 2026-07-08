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

## Target File Structure

- Keep `ops/maintainer/models.py`: strict PR metadata and the reduced canonical
  GitHub machine state.
- Keep `ops/maintainer/runtime.py`: the simple worker/run-ID lease only.
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
- Modify only if findings require it: the two files above

- [ ] **Step 1: Run the four focused design reviewers**

Invoke `snowcast-advisory-review` in `design-review` mode for:

```text
ai-llm-reliability
security-privacy
release-change-management
observability-ops
```

Require each reviewer to inspect the authoritative spec, ADR 0011, the current
`ops/maintainer/` implementation, and the failing PR-merge CI evidence.

- [ ] **Step 2: Resolve blocking findings**

For every Blocker or High finding, stop and return the material decision to the
owner. For scoped Medium findings, update the spec when the fix is cheap and
does not reopen an owner decision; otherwise record an accepted follow-up.

- [ ] **Step 3: Record review outcome**

Update the spec's `Decision And Review Gate` with reviewer dispositions and
remaining post-implementation review requirements.

- [ ] **Step 4: Verify and commit review-only changes**

Run:

```bash
git diff --check
```

Expected: no output.

If documentation changed:

```bash
git add docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/architecture/adr/0011-local-codex-maintainer-control-plane.md
git commit -m "docs: resolve simplified maintainer design review"
```

### Task 2: Replace Lease Credentials With A Simple Run Lease

**Files:**
- Modify: `ops/maintainer/runtime.py`
- Create: `ops/maintainer/state.py`
- Create: `tests/test_maintainer_state.py`
- Modify: `tests/test_maintainer_runtime.py`

- [ ] **Step 1: Write failing simple-lease tests**

Replace token/credential expectations with tests using this public contract:

```python
lease = RunLease.acquire(state_dir, "curation", now=NOW)
assert lease.worker == "curation"
assert re.fullmatch(r"[0-9a-f]{32}", lease.run_id)

loaded = RunLease.load_owner(state_dir, "curation", lease.run_id)
loaded.heartbeat(now=NOW + timedelta(minutes=5))
loaded.release()
```

Add explicit regressions:

```python
def test_old_same_worker_run_id_cannot_adopt_stale_successor(tmp_path: Path) -> None:
    old = RunLease.acquire(tmp_path, "curation", now=NOW)
    new = RunLease.acquire(
        tmp_path,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    with pytest.raises(LeaseOwnershipError):
        RunLease.load_owner(tmp_path, "curation", old.run_id)

    assert RunLease.load_owner(tmp_path, "curation", new.run_id) == new


def test_other_worker_cannot_use_active_run_id(tmp_path: Path) -> None:
    lease = RunLease.acquire(tmp_path, "discovery", now=NOW)

    with pytest.raises(LeaseOwnershipError):
        RunLease.load_owner(tmp_path, "curation", lease.run_id)
```

Keep tests for 0700 state directory, 0600 owner file, symlink rejection, fresh
lock busy, stale-lock preservation, matching heartbeat, and matching release.
Delete tests for secret token output, worker credential files, token/ID
cross-validation, and credential cleanup.

- [ ] **Step 2: Run the lease tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_runtime.py -q
```

Expected: failures because `RunLease` still exposes token and credential-file
semantics rather than the target `run_id` owner record.

- [ ] **Step 3: Implement the minimal lease model**

Use one strict owner payload:

```python
@dataclass(frozen=True)
class _OwnerMetadata:
    worker: str
    run_id: str
    acquired_at: datetime
    heartbeat_at: datetime


@dataclass(frozen=True)
class RunLease:
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
it if ownership changed. Do not retain `token`, `credential_path`,
`assert_credential()`, `_write_worker_credential()`, or
`_remove_matching_credential()`.

- [ ] **Step 4: Write failing phase-state tests**

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
    pr_number: int | None = None
    candidate_key: str | None = None
    selected_head: str
    prepared_head: str | None = None
    reviewed_head: str | None = None
    validated_head: str | None = None
    backup_ref: str | None = None
```

Test monotonic phase transitions, exact worker/run ownership, private atomic
writes, malformed/oversized/symlink rejection, and refusal to skip required
fields for a phase. Curation state requires a PR number; discovery state
requires a candidate key and may receive its PR number only after draft-PR
creation.

- [ ] **Step 5: Implement phase state and push journal**

In `state.py`, provide a `StateStore` with these exact public methods:

- `load_work(work_id: str) -> WorkState | None`
- `save_work(state: WorkState, lease: RunLease) -> None`
- `load_push(work_id: str) -> PushJournal | None`
- `save_push(journal: PushJournal, lease: RunLease) -> None`

`PushJournal` contains `work_id`, optional `pr_number`, `branch`, optional
`expected_remote_head`, `new_head`, and
`phase: Literal["authorized", "pushed"]`. A missing expected remote head means
new-branch creation and is valid only while the remote ref is absent. Work
state is one file per stable work ID; push state remains separate. Reuse one
private atomic JSON helper rather than duplicating filesystem checks.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_runtime.py tests/test_maintainer_state.py -q
uv run ruff check ops/maintainer/runtime.py ops/maintainer/state.py tests/test_maintainer_runtime.py tests/test_maintainer_state.py
uv run ruff format --check ops/maintainer/runtime.py ops/maintainer/state.py tests/test_maintainer_runtime.py tests/test_maintainer_state.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/runtime.py ops/maintainer/state.py tests/test_maintainer_runtime.py tests/test_maintainer_state.py
git commit -m "refactor: simplify maintainer runtime state"
```

### Task 3: Add Safe Errors And Reduced Machine State

**Files:**
- Create: `ops/maintainer/errors.py`
- Modify: `ops/maintainer/models.py`
- Modify: `tests/test_maintainer_models.py`
- Create: `tests/test_maintainer_errors.py`

- [ ] **Step 1: Write failing safe-error tests**

Define the expected interface in tests:

```python
error = MaintainerError(
    reason="stale-head",
    stage="pre-push",
    detail="PR head changed after review",
)
assert error.payload() == {
    "status": "error",
    "reason": "stale-head",
    "stage": "pre-push",
    "detail": "PR head changed after review",
}
```

Reject control characters, text over 160 characters, unknown reasons/stages,
URLs, absolute paths, and strings containing token-like assignments. Test that
an unexpected exception maps only to:

```json
{"status":"error","reason":"internal-error","stage":"dispatch"}
```

- [ ] **Step 2: Run error tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_errors.py -q
```

Expected: import failure because `errors.py` does not exist.

- [ ] **Step 3: Implement the safe error contract**

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
    detail: str | None = None

    def payload(self) -> dict[str, str]:
        payload = {
            "status": "error",
            "reason": self.reason.value,
            "stage": self.stage.value,
        }
        if self.detail is not None:
            payload["detail"] = validate_safe_detail(self.detail)
        return payload
```

- [ ] **Step 4: Write failing reduced-machine-state tests**

Replace lineage/fingerprint fields with:

```python
class MachineState(_MaintainerModel):
    reviewed_head: str | None = None
    validated_head: str | None = None
    candidate_key: str | None = None
    candidate_origin: Literal["backlog", "external"] | None = None
    last_operation: Literal[
        "none", "reviewed", "validated", "pushed", "published"
    ] = "none"
```

Require candidate key and origin together. Remove `lineage_id`,
`completed_cycles`, candidate fingerprints, regional graph key, and publication
phase duplication.

- [ ] **Step 5: Implement, run tests, and commit**

Run:

```bash
uv run pytest tests/test_maintainer_errors.py tests/test_maintainer_models.py -q
uv run ruff check ops/maintainer/errors.py ops/maintainer/models.py tests/test_maintainer_errors.py tests/test_maintainer_models.py
```

Expected: all pass.

Commit:

```bash
git add ops/maintainer/errors.py ops/maintainer/models.py tests/test_maintainer_errors.py tests/test_maintainer_models.py
git commit -m "refactor: reduce maintainer machine contracts"
```

### Task 4: Replace Policy Selection With Safe Inspection

**Files:**
- Create: `ops/maintainer/inspection.py`
- Create: `tests/test_maintainer_inspection.py`
- Modify: `ops/maintainer/github.py`
- Modify: `tests/test_maintainer_github.py`
- Delete after migration: policy-only selection code from `ops/maintainer/curation.py`

- [ ] **Step 1: Write failing curation inventory tests**

Target interface:

```python
inventory = inspect_curation(prs)
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

Do not sort by age as policy and do not return a selected PR. Preserve stable
GitHub order or sort by PR number solely for output determinism.

- [ ] **Step 2: Write failing discovery inventory tests**

Target interface:

```python
inventory = inspect_discovery(catalog_keys, pull_requests, comments)
assert inventory.open_proposal_count == 2
assert inventory.open_candidate_keys == frozenset({
    "stay_destination:nendaz",
    "ski_area:thyon-ski-area",
})
assert inventory.can_create_proposal is True
```

All open proposal-labeled PRs count toward the cap, even when their machine
comment is missing. Candidate keys are included only when a valid canonical
comment provides them. Closed summaries expose safe PR metadata for Codex
interpretation but do not produce declined fingerprints or hard suppression.

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_inspection.py -q
```

Expected: import failure because `inspection.py` does not exist.

- [ ] **Step 4: Implement inspection and GitHub reads**

Create strict frozen inventory models. Reuse `PullRequest` and the canonical
comment parser. Keep GitHub pagination, 120-second bounds, scoped auth, and
exact `lampssy` verification. Remove helper-side oldest-first selection,
`next_cycle_decision`, declined fingerprints, and discovery fingerprints.

The selection boundary must remain visibly absent from the helper:

```python
def inspect_curation(prs: Iterable[PullRequest]) -> CurationInventory:
    eligible = tuple(
        sorted(
            (pr for pr in deduplicate_prs(prs) if is_safe_catalog_candidate(pr)),
            key=lambda pr: pr.number,
        )
    )
    return CurationInventory(eligible=eligible)


def inspect_discovery(
    catalog_keys: AbstractSet[str],
    pull_requests: Iterable[PullRequest],
    comments_by_pr: Mapping[int, Sequence[GitHubComment]],
) -> DiscoveryInventory:
    proposals = tuple(
        proposal_summary(pr, comments_by_pr.get(pr.number, ()))
        for pr in deduplicate_prs(pull_requests)
        if "maintainer:proposal" in pr.labels
    )
    return DiscoveryInventory.from_current_state(catalog_keys, proposals)
```

In the same task, implement the referenced private helpers with these rules:

```python
def deduplicate_prs(prs: Iterable[PullRequest]) -> tuple[PullRequest, ...]:
    by_number: dict[int, PullRequest] = {}
    for pr in prs:
        if pr.number in by_number:
            raise MaintainerError(
                ErrorReason.INVALID_GITHUB_STATE,
                ErrorStage.INSPECT,
                "GitHub returned a duplicate pull request number",
            )
        by_number[pr.number] = pr
    return tuple(by_number.values())


def is_safe_catalog_candidate(pr: PullRequest) -> bool:
    paused = {
        "maintainer:manual-check",
        "maintainer:owner-decision",
        "maintainer:blocked",
        "maintainer:proposal",
    }
    return (
        not pr.is_cross_repository
        and pr.head_repository_owner == "lampssy"
        and pr.base_ref_name == "main"
        and pr.head_ref_name.startswith("codex/")
        and pr.labels.isdisjoint(paused)
        and has_only_owned_catalog_paths(pr.changed_paths)
    )
```

`proposal_summary()` parses only the canonical maintainer comment through
`parse_machine_state()` and returns the PR number, lifecycle, current head, and
candidate key when trusted state is valid. `DiscoveryInventory.from_current_state()`
counts every open proposal-labeled PR, derives known open candidate keys from
valid comments, copies the catalog key set, and sets `can_create_proposal` to
`open_proposal_count < 3`.

- [ ] **Step 5: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_inspection.py tests/test_maintainer_github.py tests/test_maintainer_models.py -q
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

- [ ] **Step 1: Write failing intent-scope tests**

Keep `IntentSnapshot` limited to:

```python
class IntentSnapshot(BaseModel):
    changed_paths: frozenset[str]
    diff_entries: tuple[IntentDiffEntry, ...]
    catalog_targets: frozenset[str]
    report_targets: frozenset[str]
```

Delete `removed_backlog_markers`. Add tests proving ordinary backlog prose can
change without marker parsing, while an executable Python/test change,
unexpected path, symlink, submodule, or disallowed file mode remains rejected.

- [ ] **Step 2: Run intent tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_intent.py -q
```

Expected: failures from obsolete backlog-marker expectations.

- [ ] **Step 3: Implement objective intent comparison**

`compare_intent()` must require stable changed-path/file-mode scope and prevent
loss or expansion of catalog/report targets across rebase. It must not read or
interpret backlog Markdown. Keep the allowed catalog, trust, report, backlog,
and owned-doc paths; executable code remains outside curation scope.

The comparison itself stays small:

```python
def compare_intent(before: IntentSnapshot, after: IntentSnapshot) -> None:
    if before.changed_paths != after.changed_paths:
        raise IntentDriftError("changed path scope changed during preparation")
    if before.diff_entries != after.diff_entries:
        raise IntentDriftError("file mode or change kind changed during preparation")
    if before.catalog_targets != after.catalog_targets:
        raise IntentDriftError("catalog target scope changed during preparation")
    if before.report_targets != after.report_targets:
        raise IntentDriftError("curation report target scope changed during preparation")
```

- [ ] **Step 4: Preserve guarded git invariants**

Retain and test:

- approved repository and effective fetch/push remote;
- exact selected head and fetched `origin/main`;
- clean worktree;
- backup ref;
- conflict abort;
- prepared ref bound to selected/base/rebased heads;
- exact remote-head recheck;
- exact `--force-with-lease`;
- new discovery-branch publication only when the remote branch is absent,
  using a non-force push;
- noninteractive SSH and sanitized timeout/auth/transport errors.

Remove only dependencies on old attempt/prepared artifacts; the caller will
store the `GuardedSyncResult` in `WorkState`.

- [ ] **Step 5: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_intent.py tests/test_maintainer_git_ops.py -q
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

- [ ] **Step 1: Write failing curation-validation tests**

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

- [ ] **Step 2: Write failing proposal-validation tests**

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
- current discovery inventory is below cap and has no same-key open proposal.

Do not parse backlog, require marker cleanup, read a registry, compare
fingerprints, rotate regions, or inspect a body origin marker.

- [ ] **Step 3: Run validation tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_validation.py -q
```

Expected: import failure because `validation.py` does not exist.

- [ ] **Step 4: Implement validation and remove policy coupling**

Move only objective validators into `validation.py`. Raise `MaintainerError`
with safe reason/stage/detail. Return strict `ValidationResult` and
`ProposalValidationResult` models. Do not select workflow states.

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
    snapshot: IntentSnapshot,
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

- [ ] **Step 5: Run focused catalog regressions and commit**

Run:

```bash
uv run pytest tests/test_maintainer_validation.py tests/test_catalog_trust.py tests/test_catalog_models.py tests/test_catalog_schema_v2.py tests/test_catalog_loader_v2.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py -q
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

- [ ] **Step 1: Write failing canonical-comment tests**

Keep one marker containing an actual versioned JSON object:

```text
<!-- snowcast-maintainer-state:{"schema_version":1,"reviewed_head":"abc123"} -->
```

Test one strict `MachineState` in the marked `lampssy` comment. Remove the
discovery-origin body marker and body/comment matching. A missing or malformed
comment returns no trusted review state; it never reconstructs readiness.

- [ ] **Step 2: Write failing lifecycle request tests**

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
  remote branch, an open slot, and no same-key open proposal;
- proposal requires validated proposal evidence and an open slot;
- waiting-ci requires exact reviewed/validated/pushed head and pending checks;
- ready requires exact reviewed/validated/current head, successful required
  checks, mergeability, no proposal label, and no owner/manual/blocked request.

Any new head invalidates prior ready evidence.

- [ ] **Step 3: Run publication tests and verify RED**

Run:

```bash
uv run pytest tests/test_maintainer_publication.py -q
```

Expected: failures because current publication expects lineage fields and
duplicated discovery-origin state.

- [ ] **Step 4: Implement idempotent publication**

Retain an allowlisted managed human-readable body block so Codex cannot
overwrite text outside the owned block. Publish one canonical comment and one
lane/state label. Refetch the full PR immediately before body/comment/label
writes and reject changed metadata or head. Partial publication is retried by
recomputing the same desired state for the same head.

Add `GitHubClient.create_draft_pull_request()` with explicit repository,
`main` base, validated `codex/catalog-curation-*` head branch, title/body files,
and a parsed positive PR number. Before creation, recheck proposal cap,
candidate duplication, local head, remote branch absence, and validated
proposal evidence. Push the new branch non-force, create the draft PR, then
publish the proposal labels and canonical comment.

The objective readiness branch must be explicit:

```python
def require_ready(
    pull_request: PullRequest,
    machine_state: MachineState,
) -> None:
    if pull_request.head_sha != machine_state.reviewed_head:
        raise MaintainerError(
            ErrorReason.STALE_HEAD,
            ErrorStage.READINESS,
            "PR head differs from the reviewed head",
        )
    if machine_state.validated_head != pull_request.head_sha:
        raise MaintainerError(
            ErrorReason.VALIDATION_REQUIRED,
            ErrorStage.READINESS,
            "current head has no matching validation",
        )
    if (
        pull_request.check_state != "success"
        or pull_request.mergeable != "MERGEABLE"
    ):
        raise MaintainerError(
            ErrorReason.NOT_READY,
            ErrorStage.READINESS,
            "required checks or mergeability are not ready",
        )
    if "maintainer:proposal" in pull_request.labels:
        raise MaintainerError(
            ErrorReason.PROPOSAL_APPROVAL_REQUIRED,
            ErrorStage.READINESS,
            "proposal still requires owner approval",
        )
```

- [ ] **Step 5: Run focused tests and commit**

Run:

```bash
uv run pytest tests/test_maintainer_publication.py tests/test_maintainer_github.py tests/test_maintainer_models.py -q
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
publish proposal --branch <branch> --candidate-key <key> --candidate-origin <backlog|external> --head <sha> --title-file <path> --body-file <path> --summary-file <path> --run-id <id>
publish state --pr <number> --state <state> --reviewed-head <sha> --summary-file <path> [--body-file <path>] --run-id <id>
publish ensure-labels --worker <curation|discovery> --run-id <id>
```

`inspect` is read-only and needs no lease. Every mutation requires exact worker
and run ID. Discovery backlog/web research occurs before acquisition; once
Codex chooses a candidate it acquires discovery, re-runs `inspect discovery`,
and then mutates.

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
printed.

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
    ("publish", "proposal"): handle_publish_proposal,
    ("publish", "state"): handle_publish_state,
    ("publish", "ensure-labels"): handle_ensure_labels,
}


def dispatch(args: argparse.Namespace, dependencies: Dependencies) -> dict[str, object]:
    handler = HANDLERS.get((args.family, args.command))
    if handler is None:
        raise MaintainerError(
            ErrorReason.INVALID_COMMAND,
            ErrorStage.DISPATCH,
            "command is outside the maintainer capability surface",
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
git add ops/maintainer tests/test_maintainer_*.py docs/catalog-discovery/alpine-coverage-registry.json
git commit -m "refactor: thin the Snowcast maintainer control plane"
```

### Task 9: Reconcile Documentation And Future Skill Contract

**Files:**
- Modify: `README.md`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/superpowers/plans/2026-07-08-local-maintainer-automation.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- Review: `docs/product-backlog.md`
- Do not create yet: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`

- [ ] **Step 1: Update operator documentation**

Document the final CLI, simple owner record, phase state, push journal, safe
errors, canonical comment, readiness contract, Codex-selected PRs, semantic
backlog discovery, no runtime registry, and shorter discovery mutation-window
lease.

- [ ] **Step 2: Replace the post-merge skill specification**

The future skill must direct Codex to:

- inspect and choose at most one safe PR;
- acquire curation before prepare and hold through publication;
- interpret backlog/research read-only before discovery acquisition;
- acquire discovery, rerun discovery inspection, then mutate;
- perform at most two fresh review/fix cycles;
- request semantic states but rely on helper gates for proposal/waiting/ready;
- never push or publish outside the helper;
- never approve or merge.

Keep installation and automation activation blocked until the refactored PR is
merged and receives post-merge skill/automation review.

- [ ] **Step 3: Mark implementation status accurately**

Update the authoritative spec from accepted design to implemented only after
all code and verification tasks pass. Retain the old spec/plan as superseded
history; do not leave executable Task 10 instructions that contradict the new
design.

- [ ] **Step 4: Verify docs and commit**

Run:

```bash
git diff --check
rg -n "69-entry|run\.credential|private lease token|deterministic backlog parser" README.md docs/engineering-notes.md docs/superpowers
```

Expected: old terms appear only in clearly marked historical/superseded
sections or the simplification rationale.

Commit:

```bash
git add README.md docs/engineering-notes.md docs/superpowers docs/product-backlog.md
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
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
git diff --check
git status --short
```

Expected: all tests and checks pass; worktree clean.

- [ ] **Step 3: Verify the prospective merge with current main**

Run from the implementation worktree:

```bash
git fetch origin main
merge_dir="$(git rev-parse --show-toplevel)/../local-maintainer-merge-check"
test ! -e "$merge_dir"
git worktree add --detach "$merge_dir" HEAD
git -C "$merge_dir" merge --no-commit --no-ff origin/main
(cd "$merge_dir" && /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.worktrees/local-maintainer-automation/.venv/bin/pytest -q)
git -C "$merge_dir" merge --abort
git worktree remove "$merge_dir"
```

Expected: merge succeeds without conflicts and the full suite passes. If the
merge command is already up to date and creates no merge state, skip
`merge --abort` after checking `git rev-parse -q --verify MERGE_HEAD`.

- [ ] **Step 4: Recheck PR metadata and push normally**

Verify the remote branch still points at the previously published PR head
before pushing. Then:

```bash
git push origin codex/local-maintainer-automation-implementation
```

Do not force-push this implementation branch. Confirm PR #43 remains draft and
targets `main`.

- [ ] **Step 5: Watch GitHub CI**

Use the project-scoped profile:

```bash
GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast" \
  GH_PROMPT_DISABLED=1 \
  gh pr checks 43 --repo lampssy/ai-sports-travel-planner --watch --interval 10
```

Expected: the push and pull-request merge-state runs pass. Stop without merge
or activation and hand PR #43 back to the owner.

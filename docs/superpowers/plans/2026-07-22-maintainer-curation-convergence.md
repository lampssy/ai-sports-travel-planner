# Maintainer Curation Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scheduled catalog-PR curation converge around a frozen evidence inventory, preserve safe unfinished remediation, and run only stage-appropriate validation while retaining exact-head and source-trust protections.

**Architecture:** Extend schema-v3 reports with an optional typed evidence envelope and graph-impact classification, then add a private remediation-continuation record beside the existing reviewed continuation. A new checkpoint capability runs the two deterministic delta checks exactly once, stores exact recovery refs, and lets later runs resume with one fresh bounded review; the existing final validation remains the only broad local test gate.

**Tech Stack:** Python 3.13, Pydantic v2, Git refs/commit-tree/cherry-pick, pytest, Ruff, Markdown operating contracts, Codex App skills and automations.

## Global Constraints

- Keep `report_schema_version=3`; do not introduce schema version 4.
- Keep exactly the existing curation and discovery workers, global leases,
  labels, schedules, model choice, proposal cap, and GitHub publication surface.
- Codex decides source meaning, candidate completeness, graph impact, and
  backlog wording; Python validates only typed/objective facts.
- Generic schema-v3 parsing stays backward-compatible, while finalized
  maintainer curation and proposal validation require the complete bounded
  inventory additions.
- Never approve or merge a PR.
- Never publish a remediation continuation merely because it exists.
- A resumed remediation continuation always receives one fresh independent
  bounded full review.
- Every final report URL receives a fresh reachability check; only changed or
  graph-critical claims require repeated semantic source review.
- URL reachability/relevance checks and their run-local cache are orchestration
  responsibilities; helper code validates typed URLs and exact report/backlog
  references without owning network semantics.
- Repository implementation, tests, authoritative docs, and ADR amendment land
  before personal skills or automation prompts are activated.
- No dependency, deployment, production-data, or secret changes.

---

## Scope Check

This is activation slice 1 from
`docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`.
It changes curation report contracts, continuation state, delta validation,
review convergence, and curation activation. Regional discovery prioritization
is intentionally deferred to
`docs/superpowers/plans/2026-07-22-maintainer-regional-completion.md`.

## Decision And Review Gate

- Classification: review-gated / full design flow.
- Developer Decision Checkpoints: resolved in the approved design.
- ADR: amend ADR 0011 in Task 6; no new ADR.
- Required pre-code advisory design review: AI/LLM reliability,
  security/privacy, data trust, release/change management, and observability/ops.
- Implementation must not begin with an unresolved Blocker or High review
  finding.
- Personal skill and automation activation remains post-merge and owner-local.

## Target File Structure

- Modify `app/data/catalog_curation.py`: optional schema-v3 evidence-envelope
  records, graph impact, validation, and deterministic Markdown rendering.
- Modify `ops/maintainer/state.py`: strict private
  `RemediationContinuation` persistence beside `ReviewedContinuation`.
- Modify `ops/maintainer/inspection.py`: safe remediation-continuation summaries
  and push-journal summaries with no lease-authority run IDs, plus
  priority-preserving curation inventory.
- Modify `ops/maintainer/git_ops.py`: exact remediation refs, squash replay, and
  the existing bounded conflict policy.
- Modify `ops/maintainer/validation.py`: two-command delta profile separated
  from the existing three-command final profile.
- Modify `ops/maintainer/capabilities.py`: checkpoint and resume lifecycle.
- Modify `ops/maintainer/cli.py`: `checkpoint remediation` capability and
  continuation-kind-safe output.
- Modify `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`,
  `docs/operating-model/local-maintainer-activation.md`, and ADR 0011: current
  repository authority and post-merge activation.
- Modify the focused existing test modules; do not add a parallel maintainer
  test framework.

### Task 1: Run The Advisory Design Gate

**Files:**
- Review: `docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`
- Review: `docs/superpowers/plans/2026-07-22-maintainer-curation-convergence.md`
- Review: `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- Review: `app/data/catalog_curation.py`
- Review: `ops/maintainer/state.py`
- Review: `ops/maintainer/validation.py`

**Interfaces:**
- Consumes: the owner-approved design and current merged helper contracts.
- Produces: a review-cleared design/plan with no unresolved Blocker or High
  finding.

- [ ] **Step 1: Run focused design reviewers**

Invoke `snowcast-advisory-review` in `design-review` mode for:

```text
ai-llm-reliability
security-privacy
data-trust
release-change-management
observability-ops
```

Require each reviewer to inspect the approved design, this plan, ADR 0011,
schema-v3 report contracts, existing reviewed continuations, and exact-head
validation/publication boundaries.

- [ ] **Step 2: Resolve review findings**

Return any new material owner choice to the owner. Apply mechanical wording or
safety corrections directly to the design and plan. Do not begin code while a
Blocker or High finding remains.

- [ ] **Step 3: Verify and commit review-only changes**

Run:

```bash
git diff --check
```

Expected: no output.

If review changed documentation:

```bash
git add docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md docs/superpowers/plans/2026-07-22-maintainer-curation-convergence.md docs/architecture/adr/0011-local-codex-maintainer-control-plane.md
git commit -m "docs: resolve maintainer convergence design review"
```

### Task 2: Extend Schema V3 With The Bounded Review Envelope

**Files:**
- Modify: `app/data/catalog_curation.py:90-170, 500-630, 807-855, 912-940, 1314-1385, 1988-2040`
- Modify: `tests/test_catalog_curation.py`
- Modify: `tests/test_catalog_curation_backlog.py`
- Modify: `tests/test_catalog_curation_reconciliation.py`

**Interfaces:**
- Consumes: existing `CatalogScopeCandidateKind`, `_safe_source_url`,
  `CatalogEntityScopeAssessment`, and `CatalogCurationReport`.
- Produces: `CatalogReviewSourceFamily`, `CatalogGraphImpact`, optional
  `review_evidence_envelope`, and optional `graph_impact`, plus a strict
  finalized-maintainer validation profile.

- [ ] **Step 1: Write failing model and validation tests**

Add focused tests with these exact payload shapes:

```python
def test_schema_v3_accepts_bounded_review_envelope_and_graph_impact() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    payload["review_evidence_envelope"] = [
        {
            "family_id": "official-booking-directory",
            "source_kind": "destination_booking",
            "source_urls": [payload["evidence"][0]["source_url"]],
            "candidate_kinds": ["stay_destination", "stay_base"],
        }
    ]
    payload["entity_scope_assessments"][0]["graph_impact"] = "graph_blocking"

    report = CatalogCurationReport.model_validate(payload)
    validate_catalog_curation_report(report, require_resulting_graph=True)

    assert report.review_evidence_envelope[0].family_id == (
        "official-booking-directory"
    )
    assert report.entity_scope_assessments[0].graph_impact == "graph_blocking"


def test_regional_followup_requires_deferred_or_unresolved_backlog_item() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    assessment = payload["entity_scope_assessments"][0]
    assessment["graph_impact"] = "regional_followup"

    with pytest.raises(
        CatalogValidationError,
        match="regional_followup requires deferred or unresolved backlog scope",
    ):
        validate_catalog_curation_report(CatalogCurationReport.model_validate(payload))


def test_review_envelope_rejects_unsafe_url() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    payload["review_evidence_envelope"] = [{
        "family_id": "official-booking-directory",
        "source_kind": "destination_booking",
        "source_urls": ["file:///tmp/source"],
        "candidate_kinds": ["stay_base"],
    }]

    with pytest.raises(ValidationError):
        CatalogCurationReport.model_validate(payload)


def test_review_envelope_rejects_duplicate_family() -> None:
    payload = _current_destination_scope_report().model_dump(mode="json")
    family = {
        "family_id": "official-booking-directory",
        "source_kind": "destination_booking",
        "source_urls": [payload["evidence"][0]["source_url"]],
        "candidate_kinds": ["stay_base"],
    }
    payload["review_evidence_envelope"] = [family, family]

    with pytest.raises(
        CatalogValidationError,
        match="review_evidence_envelope contains a duplicate family",
    ):
        validate_catalog_curation_report(
            CatalogCurationReport.model_validate(payload)
        )
```

Add a backlog regression in `tests/test_catalog_curation_backlog.py` proving a
`regional_followup` points to a heading that exists in the supplied product
backlog.

Add two profile tests:

```python
def test_legacy_schema_v3_remains_readable_without_review_inventory() -> None:
    report = CatalogCurationReport.model_validate(_legacy_schema_v3_payload())
    validate_catalog_curation_report(report)


@pytest.mark.parametrize("missing", ["envelope", "graph_impact"])
def test_finalized_maintainer_profile_requires_complete_review_inventory(
    missing: str,
) -> None:
    report = _bounded_review_report(missing=missing)

    with pytest.raises(CatalogValidationError, match="bounded review inventory"):
        validate_catalog_curation_report(
            report,
            require_bounded_review_inventory=True,
        )
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
uv run pytest tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py -q
```

Expected: failures because `review_evidence_envelope` and `graph_impact` are
forbidden fields.

- [ ] **Step 3: Add the strict optional models**

Add these contracts beside the existing scope aliases:

```python
CatalogGraphImpact = Literal["graph_blocking", "regional_followup"]
CatalogReviewSourceKind = Literal[
    "destination_booking",
    "ski_area_operator",
    "pass_tariff",
    "access_transport",
    "linked_pr_dependency",
    "other_official",
]


class CatalogReviewSourceFamily(CatalogCurationContractModel):
    family_id: str = Field(min_length=1)
    source_kind: CatalogReviewSourceKind
    source_urls: list[str] = Field(min_length=1)
    candidate_kinds: list[CatalogScopeCandidateKind] = Field(min_length=1)

    @field_validator("family_id")
    @classmethod
    def validate_family_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "review source family_id")

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        urls = [_safe_source_url(value) for value in values]
        if len(urls) != len(set(urls)):
            raise ValueError("review source URLs must be unique")
        return urls

    @field_validator("candidate_kinds")
    @classmethod
    def validate_candidate_kinds(
        cls, values: list[CatalogScopeCandidateKind]
    ) -> list[CatalogScopeCandidateKind]:
        if len(values) != len(set(values)):
            raise ValueError("review candidate kinds must be unique")
        return values
```

Add:

```python
class CatalogEntityScopeAssessment(CatalogCurationContractModel):
    # existing fields stay unchanged
    graph_impact: CatalogGraphImpact | None = None


class CatalogCurationReport(CatalogCurationContractModel):
    # existing fields stay unchanged
    review_evidence_envelope: list[CatalogReviewSourceFamily] = Field(
        default_factory=list
    )
```

Keep both fields optional so legacy schema-v3 reports remain readable.
Catalog nodes and relationships are already exact in `reviewed_targets`,
`changes`, scope assessments, and the resulting graph; do not duplicate them
as synthetic URL families.

- [ ] **Step 4: Add cross-field validation and rendering**

In `validate_catalog_curation_report`, enforce:

```python
family_ids = [item.family_id for item in report.review_evidence_envelope]
if len(family_ids) != len(set(family_ids)):
    issues.append("review_evidence_envelope contains a duplicate family")

evidence_urls = {item.source_url for item in report.evidence}
for family in report.review_evidence_envelope:
    for source_url in family.source_urls:
        if source_url not in evidence_urls:
            issues.append(
                f"{family.family_id}: review source URL is not referenced by evidence"
            )

for assessment in report.entity_scope_assessments:
    if assessment.graph_impact == "regional_followup":
        if (
            assessment.disposition not in BACKLOG_REQUIRED_SCOPE_DISPOSITIONS
            or assessment.backlog_ref is None
        ):
            issues.append(
                f"{assessment.candidate_id}: regional_followup requires "
                "deferred or unresolved backlog scope"
            )
```

Add `require_bounded_review_inventory: bool = False`. When true, require a
non-empty `review_evidence_envelope` and non-null `graph_impact` on every scope
assessment. Generic loading and pre-review normalization keep the default
false. `candidate_kinds` records categories examined rather than proving that a
candidate exists; candidate claims remain bound through assessment
`evidence_refs`.

Extend deterministic Markdown with a `Review Evidence Envelope` table and a
`Graph Impact` column in `Entity Scope Assessments` when the optional fields
are present. Preserve byte-for-byte rendering for legacy schema-v3 reports
without either optional field; update only fixtures that deliberately exercise
the extension.

- [ ] **Step 5: Run focused schema, backlog, render, and reconciliation tests**

Run:

```bash
uv run pytest tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py tests/test_catalog_curation_reconciliation.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit the schema-v3 extension**

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py tests/test_catalog_curation_reconciliation.py
git commit -m "feat: add bounded curation review envelope"
```

### Task 3: Add Private Remediation-Continuation State And Inspection

**Files:**
- Modify: `ops/maintainer/state.py:45-220, 320-680, 950-980`
- Modify: `ops/maintainer/inspection.py:70-200, 270-330`
- Modify: `tests/test_maintainer_state.py`
- Modify: `tests/test_maintainer_inspection.py`

**Interfaces:**
- Consumes: `GuardedSyncResult`, private atomic state
  helpers, and curation hold-label logic.
- Produces: remediation-specific status, `RemediationContinuation`, state-store
  CRUD/adoption/promotion methods, safe `PushJournalSummary`, and
  `RemediationContinuationSummary` in `CurationInventory`.

- [ ] **Step 1: Write failing strict-state tests**

Add a test helper that builds:

```python
RemediationContinuation(
    work_id="curation-pr-42",
    origin_run_id=lease.run_id,
    recovery_run_id=lease.run_id,
    updated_at=NOW,
    pr_number=42,
    selected_head=SHA_1,
    remediation_head=SHA_3,
    report_path="docs/catalog-curation/pr-42.json",
    sync=_sync(),
    allowed_paths=frozenset(
        {
            "app/data/catalog.json",
            "docs/catalog-curation/pr-42.json",
        }
    ),
    remediation_ref=(
        f"refs/snowcast-maintainer/remediation/pr-42/{SHA_1[:12]}-{SHA_3[:12]}"
    ),
    squash_ref=(
        "refs/snowcast-maintainer/remediation-continuations/pr-42/"
        f"{SHA_4[:12]}-{SHA_3[:12]}"
    ),
    completed_stage="delta-validated",
    status=RemediationContinuationStatus.AVAILABLE,
)
```

Cover strict extra-field rejection, rejection of `validated`/reviewed/
publication-ready status values, PR/work identity, exact ref prefixes,
mode-0600 persistence, successor adoption/fencing, atomic same-PR replacement,
terminal records excluded from inspection, crash-safe reviewed promotion, and
reviewed continuation priority.

Add inspection assertions:

```python
assert inventory.remediation_continuations[0].model_dump(mode="json") == {
    "pr_number": 42,
    "selected_head": SHA_A,
    "remediation_head": SHA_B,
    "base_head": SHA_C,
    "report_path": "docs/catalog-curation/pr-42.json",
    "resumable": True,
    "availability_reason": "available",
}
assert paused.remediation_continuations[0].resumable is False
assert paused.remediation_continuations[0].availability_reason == "hold-label"
```

Also prove unresolved journals hide both continuation kinds and a reviewed
continuation suppresses the same PR's remediation summary. Add inspection JSON
tests proving unresolved journals expose only `PushJournalSummary` and never
`origin_run_id`, `recovery_run_id`, refs, report prose, or canonical graph data.

- [ ] **Step 2: Run state/inspection tests and verify RED**

```bash
uv run pytest tests/test_maintainer_state.py tests/test_maintainer_inspection.py -q
```

Expected: import/attribute failures for the remediation contracts.

- [ ] **Step 3: Implement the strict model and state-store methods**

Add:

```python
class RemediationContinuationStatus(StrEnum):
    AVAILABLE = "available"
    RESOLVING = "resolving"
    CONSUMED = "consumed"
    INVALIDATED = "invalidated"


class RemediationContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    work_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN.pattern)
    origin_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    recovery_run_id: str = Field(pattern=_RUN_ID_PATTERN.pattern)
    updated_at: datetime
    pr_number: int = Field(ge=1)
    selected_head: str = Field(pattern=_SHA_PATTERN)
    remediation_head: str = Field(pattern=_SHA_PATTERN)
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    )
    sync: GuardedSyncResult
    allowed_paths: frozenset[str] = Field(min_length=1)
    remediation_ref: str = Field(pattern=_REF_PATTERN)
    squash_ref: str = Field(pattern=_REF_PATTERN)
    completed_stage: Literal["delta-validated"]
    status: RemediationContinuationStatus
```

Validate UTC timestamps, `curation-pr-<number>` identity, selected-head/sync
agreement, allowed curation paths, and the two exact ref prefixes. The
`remediation_head` is the exact head for which `completed_stage` applies; do
not persist subprocess output or reviewer prose as authority.

Add state-store methods with a separate private
`remediation-continuations/` directory:

```python
load_remediation_continuation(work_id: str) -> RemediationContinuation | None
save_remediation_continuation(state, lease) -> None
replace_remediation_continuation(state, lease) -> None
adopt_remediation_continuation(work_id, lease) -> RemediationContinuation
invalidate_remediation_continuation(work_id, lease) -> RemediationContinuation
promote_remediation_to_reviewed(remediation, reviewed, lease) -> None
list_remediation_continuations_for_inspection() -> tuple[RemediationContinuation, ...]
```

Replacement must accept only the same PR and selected remote head, require the
active lease, atomically replace the JSON file, and never delete old Git refs.
Invalidation must be a one-way lease-owned transition with a later timestamp;
it does not delete refs or state files.

Promotion holds the transition mutex, writes the reviewed continuation first,
then consumes the remediation record. If the second write fails, inspection
still prefers the reviewed continuation and the next identical promotion
finishes cleanup idempotently. Add injected-write-failure tests before the
reviewed write and between the two writes.

- [ ] **Step 4: Extend safe inspection without exposing private refs/run IDs**

Add:

```python
class RemediationContinuationSummary(_InspectionModel):
    pr_number: int = Field(gt=0)
    selected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    remediation_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    report_path: str = Field(
        pattern=r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    )
    resumable: bool
    availability_reason: Literal[
        "available",
        "hold-label",
        "head-drift",
        "closed-or-merged",
        "recovery-authority",
        "invalid-state",
    ]
```

Add a strict `PushJournalSummary` containing only safe recovery-routing facts:
worker, work/PR or candidate identity, phase, and expected/new head where needed
to choose recovery. Do not expose either run ID, private refs, report paths,
publication prose, or resulting-graph data.

`inspect_curation` returns reviewed summaries first and remediation summaries
second, omits a remediation summary for any PR with an active reviewed
continuation, and uses the existing exact-head/hold-label/machine-state rule to
compute `resumable` and the allowlisted availability reason. An exact paused continuation suppresses ordinary selection
for that PR. A continuation whose selected head no longer matches the open PR
is non-resumable but does not suppress the newly changed PR; a closed or merged
PR is routed to lease-owned invalidation and cannot be revived by reopening.

- [ ] **Step 5: Run focused and full maintainer state tests**

```bash
uv run pytest tests/test_maintainer_state.py tests/test_maintainer_inspection.py -q
uv run pytest tests/test_maintainer_*.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit state and inspection**

```bash
git add ops/maintainer/state.py ops/maintainer/inspection.py tests/test_maintainer_state.py tests/test_maintainer_inspection.py
git commit -m "feat: persist remediation continuations"
```

### Task 4: Add Exact Remediation Checkpoint And Replay Git Primitives

**Files:**
- Modify: `ops/maintainer/git_ops.py:120-155, 500-640`
- Modify: `tests/test_maintainer_git_ops.py:1510-1740`

**Interfaces:**
- Consumes: `GuardedSyncResult`, prepared-result intent validation, exact refs,
  `ContinuationReplayResult`, and existing reviewed-continuation replay rules.
- Produces: `RemediationCheckpointRefs`,
  `checkpoint_remediation_continuation`,
  `prepare_remediation_continuation`, and
  `continue_remediation_conflict`.

- [ ] **Step 1: Write failing integration tests**

Mirror the reviewed-continuation integration fixtures but assert remediation
prefixes and semantics:

```python
refs = repository.checkpoint_remediation_continuation(
    local.pull_request,
    prepared,
    remediated_head,
)
assert _git(local.checkout, "rev-parse", refs.remediation_ref) == remediated_head
assert _git(local.checkout, "rev-parse", f"{refs.squash_ref}^") == (
    prepared.base_head
)

replay = repository.prepare_remediation_continuation(
    local.pull_request,
    prepared,
    remediated_head,
    refs,
)
assert replay.result in {"unchanged", "prepared"}
```

Cover dirty state, non-descendant head, remote-head drift, rewritten main,
advanced-main replay, one allowed-path conflict, unrelated staged-path
rejection, missing/tampered refs, and clean abort after unsafe conflict.
Persisted `allowed_paths` are not sufficient evidence: add a tamper regression
proving replay derives paths and file modes again from the immutable exact
squash/remediation commits and rejects a path outside the prepared scope.

- [ ] **Step 2: Run git tests and verify RED**

```bash
uv run pytest tests/test_maintainer_git_ops.py -q
```

Expected: missing remediation checkpoint/replay methods.

- [ ] **Step 3: Implement focused ref types and reuse private replay helpers**

Add:

```python
class RemediationCheckpointRefs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    remediation_ref: str
    squash_ref: str
```

Create refs under:

```text
refs/snowcast-maintainer/remediation/pr-<pr>/<selected>-<head>
refs/snowcast-maintainer/remediation-continuations/pr-<pr>/<base>-<head>
```

Refactor only the duplicated private checkpoint/replay mechanics. Keep public
reviewed methods and their exact behavior unchanged. The remediation squash
commit message is:

```text
Snowcast remediation continuation for PR #<number>
```

- [ ] **Step 4: Run git and intent regression tests**

```bash
uv run pytest tests/test_maintainer_git_ops.py tests/test_maintainer_intent.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit git primitives**

```bash
git add ops/maintainer/git_ops.py tests/test_maintainer_git_ops.py
git commit -m "feat: checkpoint remediation git state"
```

### Task 5: Add Delta Validation And The Remediation Checkpoint Capability

**Files:**
- Modify: `ops/maintainer/validation.py:35-95, 230-360, 500-620`
- Modify: `ops/maintainer/capabilities.py:320-650`
- Modify: `ops/maintainer/cli.py:80-155, 250-340`
- Modify: `tests/test_maintainer_validation.py`
- Modify: `tests/test_maintainer_cli.py`

**Interfaces:**
- Consumes: the Task 3 state model, Task 4 refs/replay, existing
  `_curation_plan`, `_curation_commands`, and `validate reviewed` checkpoint.
- Produces: `DeltaValidationResult`, `validate_curation_delta`, CLI
  `checkpoint remediation`, idempotent remediation replacement, and
  kind-aware `prepare continuation` output.

- [ ] **Step 1: Write failing two-command delta-validation tests**

Add:

```python
result = validate_curation_delta(
    pull_request=pull_request,
    sync=sync,
    remediation_head=SHA_C,
    report_path=REPORT_PATH,
    repository=repository,
    base_repository=base_repository,
    runner=runner,
)

assert result.remediation_head == SHA_C
assert result.commands_completed == 2
assert [call.argv for call in runner.calls] == list(_curation_commands(plan)[:2])
assert all("pytest" not in call.argv for call in runner.calls)
```

Retain final `validate_curation` assertions proving it still runs all three
commands including the fixed catalog test suite. Its immutable report check
must use `require_bounded_review_inventory=True` and validate each
`regional_followup` anchor against the exact-head product backlog.

- [ ] **Step 2: Write failing CLI lifecycle tests**

Add an end-to-end fake-repository test:

```python
code, payload = invoke(
    "checkpoint",
    "remediation",
    "--pr",
    "42",
    "--head",
    SHA_C,
    "--report",
    REPORT_PATH,
    "--base-dir",
    str(base_dir),
    "--run-id",
    lease.run_id,
)
assert code == 0
assert payload["continuation"] == {
    "kind": "remediation",
    "result": "checkpointed",
    "head": SHA_C,
    "report_path": REPORT_PATH,
}
```

Cover exact idempotent repeat, newer same-PR remediation replacement, remote
drift, unsafe scope, invalid delta, active journal, pause-label inspection,
owner label removal, reviewed-continuation priority, unchanged remediation
resume returning `review-required`, advanced-main replay, and conflict resume.
Also prove that a remote-head mismatch invalidates the old private
continuation under the active lease before returning a structured stale result,
so a later ordinary preparation cannot be trapped behind obsolete state.

- [ ] **Step 3: Run validation/CLI tests and verify RED**

```bash
uv run pytest tests/test_maintainer_validation.py tests/test_maintainer_cli.py -q
```

Expected: missing delta validator and `checkpoint remediation` parser/handler.

- [ ] **Step 4: Split delta and final validation profiles**

Add:

```python
class DeltaValidationResult(_ValidationModel):
    remediation_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    commands_completed: Literal[2]
    observations: tuple[ValidationCommandObservation, ...]


def validate_curation_delta(..., remediation_head: str, ...) -> DeltaValidationResult:
    plan = _curation_plan(
        pull_request,
        sync,
        remediation_head,
        report_path,
        repository,
        base_repository,
        check=ErrorCheck.PREFLIGHT,
    )
    observations = _run_curation_commands(
        plan,
        commands=_curation_commands(plan)[:2],
        checks=(
            ErrorCheck.CATALOG_VALIDATION,
            ErrorCheck.CURATION_RECONCILIATION,
        ),
        runner=runner,
    )
    return DeltaValidationResult(
        remediation_head=remediation_head,
        commands_completed=2,
        observations=observations,
    )
```

Extract the command execution loop from `validate_curation` into one private
helper so final validation still runs all three commands once. Do not cache
subprocess results across heads or runs.

- [ ] **Step 5: Add the checkpoint parser and capability**

Add the parser:

```python
checkpoint = families.add_parser("checkpoint")
checkpoint_commands = checkpoint.add_subparsers(dest="command", required=True)
remediation = checkpoint_commands.add_parser("remediation")
remediation.add_argument("--pr", type=int, required=True)
remediation.add_argument("--head", type=_sha, required=True)
remediation.add_argument("--report", required=True)
remediation.add_argument("--base-dir", type=Path, required=True)
_add_run_id(remediation)
```

The handler must:

1. require the active curation lease and prepared work;
2. require the current clean exact head and unchanged selected remote head;
3. run `validate_curation_delta` exactly once;
4. create exact remediation refs;
5. atomically save or replace the same-PR remediation continuation;
6. leave `WorkState.phase=prepared`; and
7. return bounded facts without refs, run IDs, source prose, or command output.

`prepare continuation` loads an active reviewed continuation first and an
active remediation continuation second. A remediation resume always returns:

```python
{
    "kind": "remediation",
    "result": "review-required",
    "prepared_head": replay.head,
    "report_path": continuation.report_path,
}
```

If the PR closed, merged, or changed remote head, or exact refs are missing or
tampered, mark the remediation continuation `invalidated` under the lease and
return the existing structured safe-stop reason. Do not delete private refs or
fall through to fresh semantic work in the same run.

When `validate reviewed` successfully checkpoints the same PR/head, call the
single state-store promotion operation: persist the reviewed continuation
first, make inspection prefer it, then consume remediation idempotently. Add
fault-injection tests for both write boundaries and prove a successor sees
exactly one safe reviewed recovery path.

Final curation and proposal validation must load exact-head
`docs/product-backlog.md` when any `regional_followup` exists and reject a
missing canonical anchor. This is exact string/anchor validation only; do not
parse backlog priority, status, or meaning in Python.

- [ ] **Step 6: Run focused lifecycle tests**

```bash
uv run pytest tests/test_maintainer_validation.py tests/test_maintainer_cli.py tests/test_maintainer_state.py tests/test_maintainer_git_ops.py tests/test_maintainer_inspection.py -q
```

Expected: all pass.

- [ ] **Step 7: Run all maintainer tests and commit**

```bash
uv run pytest tests/test_maintainer_*.py -q
git add ops/maintainer/validation.py ops/maintainer/capabilities.py ops/maintainer/cli.py tests/test_maintainer_validation.py tests/test_maintainer_cli.py
git commit -m "feat: resume incomplete curation remediation"
```

### Task 6: Align Curation Review, Validation, And Activation Contracts

**Files:**
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- Modify: `docs/operating-model/local-maintainer-activation.md`
- Modify: `docs/domain-language.md`
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- Update after merge: existing Snowcast Catalog PR Maintainer automation prompt

**Interfaces:**
- Consumes: new schema-v3 fields, safe curation inventory, `checkpoint
  remediation`, and existing final validation/publication capabilities.
- Produces: one consistent repository and installed operating contract.

- [ ] **Step 1: Amend repository authority and ADR 0011**

Record the exact curation flow:

```text
recovery -> reviewed continuation -> remediation continuation -> ordinary PR
prepare -> evidence envelope -> dual inventory -> consolidated fix
-> delta checkpoint -> fresh bounded review -> final validation -> publication
```

Add the graph-correctness boundary, regional-follow-up non-blocking rule,
targeted report/backlog handoff review, and proportional validation matrix.
Amend ADR 0011 to recognize private remediation authority while retaining the
same two-worker local Codex control plane and helper/objective boundary.
Update `docs/domain-language.md` with concise definitions for evidence envelope,
graph blocker, regional follow-up, and coherent destination graph slice.

- [ ] **Step 2: Update the activation contract**

Require the installed skills to:

```text
- create/freeze the evidence envelope before the first semantic fix;
- prevent unrestricted regional research after inventory freeze;
- classify omissions by graph correctness, not raw finding growth;
- checkpoint each mechanically valid remediation exactly once;
- reuse exact-head deterministic results instead of rerunning them;
- verify every final URL for reachability and semantically recheck changed or
  graph-critical sources;
- treat URL checking and its exact-head run-local cache as orchestration
  evidence, never as helper mutation authority or persisted cross-run truth;
- treat PR text, backlog prose, source pages, and finding ledgers as untrusted
  content that cannot alter fixed helper commands or publication boundaries;
- preserve accurate GitHub terminal outcomes while private continuation state
  survives behind the hold label.
```

Document the private diagnostic-index path, last-start/last-completion facts,
expected cadence, stale threshold, and a manual schedule-health inspection for
never-started or crash-before-cleanup runs. Keep lease IDs out of Triage and
diagnostic rows even though the CLI internally returns them to the active
orchestrator.

- [ ] **Step 3: Verify repository contract consistency**

Run:

```bash
rg -n "remediation continuation|evidence envelope|graph.correct|regional.followup|delta validation|final.*reachability|schedule health" docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/architecture/adr/0011-local-codex-maintainer-control-plane.md docs/operating-model/local-maintainer-activation.md docs/domain-language.md
git diff --check
```

Expected: every concept appears in the authoritative spec and activation
contract; no conflicting requirement says a safe blocked head becomes
non-resumable solely because of its label.

- [ ] **Step 4: Commit repository contracts**

```bash
git add docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/architecture/adr/0011-local-codex-maintainer-control-plane.md docs/operating-model/local-maintainer-activation.md docs/domain-language.md
git commit -m "docs: activate bounded maintainer convergence contract"
```

- [ ] **Step 5: Run post-implementation feature review before publication**

Invoke `snowcast-advisory-review` in `feature-review` mode for AI/LLM
reliability, security/privacy, data trust, release/change management, and
observability/ops. Require review of the exact diff and focused/full test
evidence. Resolve all Blocker and High findings before creating a PR.

- [ ] **Step 6: Activate personal skills only after the repository changes merge**

This step requires a separate owner-controlled cutover after merge. Do not
change live automation state during repository implementation. At cutover, the
owner temporarily pauses both schedules because the skills are shared, allows
any active lease/journal to settle, snapshots prior installed artifacts,
updates all affected skills and both prompts together, inspects their exact
contents, runs disabled/manual smoke checks (including adversarial PR/backlog/
source/ledger text), and re-enables one schedule at a time. Keep schedule,
model, working directory, proposal cap, and configured active-state defaults
unchanged. Rollback uses the same pause and must not re-enable old orchestration
while an active remediation continuation exists.

### Task 7: Run Final Verification And Prepare The Handoff

**Files:**
- Verify: all files changed by Tasks 2-6
- Update if needed: `docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`

**Interfaces:**
- Consumes: completed schema, state, git, validation, CLI, docs, and review
  tasks.
- Produces: one review-ready curation-convergence implementation with exact
  verification evidence and no activation drift.

- [ ] **Step 1: Run focused catalog and maintainer suites**

```bash
uv run pytest tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py tests/test_catalog_curation_reconciliation.py -q
uv run pytest tests/test_maintainer_*.py -q
```

Expected: all pass.

- [ ] **Step 2: Run repository lint and complete tests**

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Expected: all pass. If a complete-suite failure is unrelated and reproducible
on `origin/main`, record it explicitly rather than weakening a focused test.

- [ ] **Step 3: Verify the CLI surface and clean repository**

```bash
uv run --no-config python -m ops.maintainer.cli checkpoint remediation --help
uv run --no-config python -m ops.maintainer.cli prepare continuation --help
uv run --no-config python -m ops.maintainer.cli inspect curation
git diff --check
git status --short
```

Expected: both capability help commands succeed; read-only inspection returns
bounded JSON; diff check is silent; worktree is clean after commits.

- [ ] **Step 4: Record verification in the approved design**

Change design status only after tests and feature review pass:

```text
Status: implemented and feature-reviewed; repository activation pending merge
```

Commit only if the status changed:

```bash
git add docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md
git commit -m "docs: record curation convergence verification"
```

- [ ] **Step 5: Stop for owner-controlled PR publication and merge**

Present the exact branch/head, changed files, test evidence, advisory review
disposition, rollback boundary, and post-merge activation checklist. Do not
push, open, approve, or merge a PR unless the owner requests that external
action.

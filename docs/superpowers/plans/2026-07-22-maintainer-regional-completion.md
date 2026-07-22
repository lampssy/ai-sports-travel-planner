# Maintainer Regional Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing discovery worker preferentially close known regional catalog gaps with one coherent destination-graph proposal at a time, while preserving the existing proposal cap, helper-owned publication, schema-v3 report, and owner review.

**Architecture:** Add no worker, queue, registry, schema version, or deterministic backlog parser. Codex interprets the merged product backlog and selects a bounded regional slice; the existing proposal helper validates objective identity, cap, catalog, trust, schema-v3 reconciliation, resulting graph, and publication facts. The proposal report and backlog update are the durable handoff between runs.

**Tech Stack:** Python 3.13, Pydantic v2, existing catalog/proposal validation, pytest, Markdown operating contracts, Codex App skills and automations.

## Global Constraints

- This plan depends on the curation-convergence slice being merged and its
  repository contracts being authoritative.
- Keep the existing discovery worker, schedule, model, lease, working
  directory, proposal cap of three, labels, and GitHub publication surface.
- Keep `report_schema_version=3`; use the existing `resulting_graph`, entity
  scope assessments, backlog references, and review evidence envelope.
- Final proposal validation requires the non-empty evidence envelope,
  `graph_impact` on every assessment, exact-head backlog anchors, and exactly
  one primary focus destination matching the selected backlog candidate.
- Codex interprets backlog prose and source meaning. The helper validates
  typed/objective facts only.
- One proposal covers one coherent destination graph slice: the destination,
  stay bases, access edges, ski-area ownership, pass products, weather-owner
  implications, and explicit exclusions required to review that slice.
- A proposal may include re-keying, migrations, or owner decisions. Those
  risks must be explicit in the report and PR; they do not prevent proposal
  creation merely because implementation is complex.
- Never approve or merge a PR.
- Repository tests and contracts land before installed-skill or automation
  activation.
- No dependency, deployment, secret, or production-data changes.

---

## Scope Check

This is activation slice 2 from
`docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`.
It changes discovery prioritization and proposal acceptance evidence. Private
remediation continuations and curation review convergence belong to
`docs/superpowers/plans/2026-07-22-maintainer-curation-convergence.md`.

## Decision And Review Gate

- Classification: review-gated / full design flow.
- Developer Decision Checkpoints: resolved in the approved design.
- ADR: amend ADR 0011 only if Task 2 reveals contract wording not already
  covered by the curation-convergence slice; do not add a new ADR.
- Required pre-code advisory design review: data trust, AI/LLM reliability,
  release/change management, and observability/ops.
- Implementation must not begin with an unresolved Blocker or High finding.
- Installed discovery skill and automation activation remains post-merge and
  owner-local.

## Target File Structure

- Modify `tests/test_maintainer_validation.py`: prove that the existing
  proposal validator accepts a coherent multi-entity regional slice and keeps
  all negative publication gates.
- Modify `tests/test_maintainer_cli.py` only if the regression requires a
  helper-boundary lifecycle fixture; do not add semantic selection arguments.
- Modify `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`:
  authoritative discovery selection order and bounded regional proposal
  contract.
- Modify `docs/operating-model/local-maintainer-activation.md`: post-merge
  discovery activation and operator-visible outcomes.
- Modify `docs/product-backlog.md` only for a concise durable convention if the
  current headings cannot express regional follow-up state without ambiguity.
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`
  and `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`.
- Update after merge: the existing Snowcast Catalog Discovery automation
  prompt.

### Task 1: Run The Regional Discovery Advisory Gate

**Files:**
- Review: `docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`
- Review: `docs/superpowers/plans/2026-07-22-maintainer-regional-completion.md`
- Review: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Review: `docs/product-backlog.md`
- Review: `ops/maintainer/validation.py`

**Interfaces:**
- Consumes: the owner-approved regional-completion design and current proposal
  validation/publication boundary.
- Produces: a review-cleared plan with no unresolved Blocker or High finding.

- [ ] **Step 1: Run focused design reviewers**

Invoke `snowcast-advisory-review` in `design-review` mode for:

```text
data-trust
ai-llm-reliability
release-change-management
observability-ops
```

Require reviewers to examine the approved design, this plan, merged backlog
shape, schema-v3 proposal/report validation, proposal-cap enforcement, and the
helper-versus-Codex authority boundary.

- [ ] **Step 2: Resolve findings**

Return any newly exposed material owner choice to the owner. Apply mechanical
wording or safety corrections to the design and plan. Do not begin code while
a Blocker or High finding remains.

- [ ] **Step 3: Verify and commit review-only corrections**

Run:

```bash
git diff --check
```

Expected: no output.

If review changed the docs:

```bash
git add docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md docs/superpowers/plans/2026-07-22-maintainer-regional-completion.md
git commit -m "docs: resolve regional completion design review"
```

### Task 2: Lock The Discovery Selection And Handoff Contract

**Files:**
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/operating-model/local-maintainer-activation.md`
- Modify if needed: `docs/product-backlog.md`
- Modify if needed: `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`

**Interfaces:**
- Consumes: existing discovery inventory, preferred-retry memory hint,
  schema-v3 reports, and the merged product backlog.
- Produces: one deterministic operational priority order around a semantic
  Codex selection step, plus an auditable report/backlog handoff.

- [ ] **Step 1: Write the exact selection order into repository authority**

Document this order without implementing a backlog parser:

```text
1. Recover any unresolved push journal and stop after recovery.
2. Revalidate a viable preferred-retry candidate interrupted only by lock-busy.
3. Interpret merged regional-completion follow-ups and select one coherent
   destination graph slice.
4. Interpret other active backlog candidates.
5. Only when the backlog supplies no viable bounded candidate, perform one
   bounded external official-source scan.
```

At every step retain the existing proposal identity, duplicate, open-cap,
lease, exact-head, validation, and publication gates.

- [ ] **Step 2: Define the human-readable backlog convention**

Use ordinary Markdown headings and prose. A regional follow-up must make these
facts understandable to Codex and the owner, without machine-marker syntax:

```text
- region or parent area;
- known destination/base/ski-area/pass/weather gaps;
- why the gaps matter to graph correctness or desired coverage;
- completed prerequisites;
- remaining prerequisites or owner decisions;
- source/report/PR references;
- current status: active, proposed, parked, or completed.
```

Do not require exact heading names or formatting. If the existing backlog can
already express these facts, change only the authoritative contract and leave
the backlog file untouched.

- [ ] **Step 3: Define one coherent proposal slice**

Require every regional proposal to include, where applicable:

```text
- exactly one primary stay destination;
- the stay bases needed to represent that destination accurately;
- destination-to-base and base-to-ski-area access edges;
- ski-area and pass-product ownership/boundaries;
- weather-owner implications and any migration requirement;
- complete source families and candidate-level dispositions;
- the canonical resulting graph;
- explicit examined exclusions and regional_followup deferrals;
- the merged backlog heading/reference being advanced;
- caveats, owner decisions, and safe rollback boundary.
```

A proposal is reviewable even when it flags re-keying, historical weather
migration, or an owner choice. It must not pretend those issues are already
resolved.

The helper enforces only the objective slice boundary: exactly one focus stay
destination matching `stay_destination:<id>`, exact-head backlog anchors, and
no unrelated graph additions. Codex decides whether bases, ski areas, passes,
access, and weather implications form a coherent product graph.

- [ ] **Step 4: Define durable state transitions**

Document that GitHub proposal identity and the merged schema-v3 report are the
proposal record. The same PR updates the backlog entry to `proposed` and links
the proposal/report. After the owner accepts and merges it, the backlog entry
becomes `completed` or is narrowed to the remaining regional follow-ups.

Do not add a private discovery registry or helper-owned semantic queue.
Automation memory may remember a preferred retry, but remains a revalidated
hint rather than authority.

- [ ] **Step 5: Verify contract consistency**

Run:

```bash
rg -n "preferred.retry|regional.completion|coherent.*graph|external.*scan|regional_followup|proposal cap|product backlog" docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/operating-model/local-maintainer-activation.md docs/product-backlog.md
git diff --check
```

Expected: the authoritative spec and activation doc agree; no wording makes
external research higher priority than actionable merged backlog work; no
deterministic backlog parser or third worker is introduced.

- [ ] **Step 6: Commit the discovery contract**

```bash
git add docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md docs/operating-model/local-maintainer-activation.md docs/product-backlog.md docs/architecture/adr/0011-local-codex-maintainer-control-plane.md
git commit -m "docs: prioritize regional catalog completion"
```

If the backlog and ADR were unchanged, omit them from `git add`.

### Task 3: Prove The Existing Proposal Helper Accepts A Regional Graph Slice

**Files:**
- Modify: `tests/test_maintainer_validation.py`
- Modify if needed: `tests/test_maintainer_cli.py`
- Modify only if a real generic defect is exposed: `ops/maintainer/validation.py`
- Modify only if a real generic defect is exposed: `ops/maintainer/capabilities.py`

**Interfaces:**
- Consumes: existing `validate proposal`, schema-v3 canonical graph validation,
  proposal identity/cap checks, and publication contracts.
- Produces: regression evidence that a proposal may contain a bounded
  multi-entity destination graph without weakening strict inventory, backlog,
  or one-primary-destination gates.

- [ ] **Step 1: Add a realistic regional-slice proposal fixture**

Build a schema-v3 report and catalog delta containing:

```text
primary destination: sample-valley
stay bases: sample-village, sample-hamlet
ski areas: sample-local-area, sample-linked-area
access edges: destination -> bases, bases -> applicable ski areas
pass products: local and linked-area pass identities
weather implication: explicit new owner or migration handoff
scope assessments: included entities plus one regional_followup exclusion
resulting graph: the complete canonical graph for sample-valley
```

The fixture should exercise more than one entity kind and a non-zero delta; it
must not rely on a single-destination-only shortcut.

- [ ] **Step 2: Write the acceptance regression**

Add a test with the existing public validation API:

```python
def test_validate_proposal_accepts_one_coherent_regional_destination_slice(
    regional_proposal_context,
) -> None:
    result = validate_proposal(
        candidate_key="stay_destination:sample-valley",
        candidate_origin="backlog",
        base=regional_proposal_context.base,
        head=regional_proposal_context.head,
        snapshot=regional_proposal_context.snapshot,
        discovery_inventory=regional_proposal_context.discovery_inventory,
        repository=regional_proposal_context.repository,
    )

    assert result.validated_head == regional_proposal_context.head
    assert result.candidate_key == "stay_destination:sample-valley"
    assert "sample-valley" in result.resulting_graph_markdown
```

Implement `regional_proposal_context` as a test fixture or local helper using
the existing fake repository/snapshot/inventory types. Do not invent a new
production context type merely for this test.

- [ ] **Step 3: Retain and extend negative gates**

Keep focused tests proving rejection of:

```text
- duplicate proposal identity;
- proposal cap reached;
- unrelated or missing report path;
- wrong resulting-graph focus destination;
- graph-affecting changes omitted from the canonical graph;
- unsafe or missing source URL evidence;
- stale base or remote head;
- dirty worktree or disallowed file scope;
- report/catalog/trust reconciliation mismatch.
- an empty review evidence envelope or any missing graph impact;
- a `regional_followup` whose exact-head backlog anchor does not exist;
- zero or multiple focus stay destinations;
- a focus stay destination that does not match the selected candidate; and
- an unrelated added destination/entity outside the selected graph and its
  declared linked dependencies.
```

Add only missing regressions. Do not duplicate equivalent existing tests.

- [ ] **Step 4: Run the proposal tests and inspect any failure**

```bash
uv run pytest tests/test_maintainer_validation.py -k "proposal or resulting_graph" -q
```

Expected: the positive fixture may expose the missing proposal-only strict
profile; the negative tests must fail before that implementation exists. First
confirm every fixture obeys generic schema-v3 and exact-base contracts, then
make the narrow generic/proposal-profile correction described below.

- [ ] **Step 5: If needed, make the narrow generic helper fix**

The acceptable implementation boundary is limited to:

```text
- require_bounded_review_inventory=True for proposal validation;
- exact-head existence checks for every regional_followup backlog anchor;
- exactly one focus stay destination matching stay_destination:<id> for a
  backlog-origin regional proposal; and
- rejecting unrelated additions while allowing declared graph dependencies.
```

Retain canonical focus derivation and every negative gate above. Do not add a
region identifier, semantic priority input, backlog parser, or broad file-scope
bypass to the helper.

Run:

```bash
uv run pytest tests/test_maintainer_validation.py tests/test_maintainer_cli.py -q
uv run pytest tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py tests/test_catalog_curation_reconciliation.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit the regression and any narrow helper correction**

```bash
git add tests/test_maintainer_validation.py tests/test_maintainer_cli.py ops/maintainer/validation.py ops/maintainer/capabilities.py
git commit -m "test: cover regional discovery proposals"
```

Stage only files actually changed.

### Task 4: Align And Activate The Existing Discovery Worker

**Files:**
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- Update after merge: existing Snowcast Catalog Discovery automation prompt

**Interfaces:**
- Consumes: merged repository contracts and the unchanged helper CLI.
- Produces: one existing discovery automation that prioritizes regional
  completion and emits precise bounded outcomes.

- [ ] **Step 1: Update installed skill instructions from merged `main`**

Require the discovery cycle to follow:

```text
recovery -> preferred retry -> regional backlog -> other backlog
-> bounded external research
```

The skill must also require one coherent destination graph, under-lease source
and identity revalidation, schema-v3 report, backlog update, migration/owner
flags, helper-only validation/publication, and no approval/merge.

- [ ] **Step 2: Preserve normal lock-busy behavior**

Require a structured `lock-busy` response to end as a normal bounded no-op.
When a viable candidate was interrupted only by lock contention, store it as
the preferred retry hint. The next cycle must re-run normal inventory, cap,
duplicate, catalog, and source checks before using it.

- [ ] **Step 3: Perform only an owner-controlled post-merge cutover**

Do not change live automation state during repository implementation. After
merge, the owner temporarily pauses both schedules because installed skills are
shared, allows active lease/journal state to settle, snapshots old artifacts,
updates all affected skills and both prompts, and inspects them together.
Disabled/manual smoke and prompt-injection checks run before the owner
re-enables one schedule at a time. Keep schedule, model, worktree mode,
proposal cap, lease behavior, and configured active-state defaults unchanged.
Remove candidate-specific/PR-specific wording; prompts defer exact process to
the installed skill and merged repository contracts.

- [ ] **Step 4: Inspect activation consistency**

Verify the installed skill and automation text contain no stale rule that:

```text
- parks backlog candidates until adjacent entities appear accidentally;
- prefers fresh external research over viable regional backlog work;
- forbids proposal creation solely because re-keying or migration is flagged;
- introduces a third worker or separate registry;
- treats lock-busy as a capability error.
```

### Task 5: Run Feature Review, Verification, And One Bounded Smoke Cycle

**Files:**
- Verify: all repository files changed by Tasks 2-3
- Inspect after merge: installed discovery skills and automation prompt
- Update if needed: `docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`

**Interfaces:**
- Consumes: completed regional proposal regression and merged operating
  contract.
- Produces: a review-ready repository slice and, after merge/activation, one
  observed bounded discovery outcome.

- [ ] **Step 1: Run post-implementation feature review**

Invoke `snowcast-advisory-review` in `feature-review` mode for data trust,
AI/LLM reliability, release/change management, and observability/ops. Require
review of the exact diff and focused test evidence. Resolve all Blocker and
High findings before PR publication.

- [ ] **Step 2: Run focused and complete verification**

```bash
uv run pytest tests/test_maintainer_validation.py tests/test_maintainer_cli.py -q
uv run pytest tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py tests/test_catalog_curation_reconciliation.py -q
uv run pytest tests/test_maintainer_*.py -q
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
git diff --check
git status --short
```

Expected: all pass; worktree is clean after commits. If a complete-suite
failure is unrelated and reproducible on `origin/main`, record it explicitly
rather than weakening focused tests.

- [ ] **Step 3: Stop for owner-controlled PR publication and merge**

Present the exact branch/head, changed files, tests, advisory disposition,
rollback boundary, and post-merge activation checklist. Do not push, open,
approve, or merge unless the owner requests it.

- [ ] **Step 4: After merge, activate and run one manual bounded cycle**

Run the existing discovery automation once. A successful outcome may be:

```text
- one regional proposal PR created under the existing cap;
- one precise bounded no-op because no viable regional slice is sourceable;
- one preferred-retry no-op because the lease is busy;
- one exact helper-owned hard stop with no unsafe mutation.
```

Inspect the triage summary, GitHub proposal/body/labels when created, backlog
diff, schema-v3 report, canonical graph, and helper inventory. Do not require a
proposal to claim success when the correct result is a bounded no-op.

- [ ] **Step 5: Record verified activation**

After the repository is merged and installed artifacts are confirmed, update
the approved design status to:

```text
Status: implemented, feature-reviewed, and locally activated
```

Commit the repository status update only on a normal follow-up branch; do not
edit repository docs from the automation worktree merely to record a local
run.

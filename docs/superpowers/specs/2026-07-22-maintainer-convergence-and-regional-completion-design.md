# Maintainer Convergence And Regional Completion

## Status

- Status: owner-approved design; not yet implemented or activated
- Classification: review-gated / full design flow
- Owner: solo-builder
- Related specification:
  `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Related ADR: ADR 0011; amend it during implementation rather than creating a
  separate control-plane ADR
- Developer Decision Checkpoints: resolved in the design conversation
- Advisory design review: completed before implementation; the strict
  finalized-report, safe-inspection, crash-safe-promotion, source-ownership,
  and owner-controlled-cutover findings are incorporated below

Until this design is implemented, merged, and locally activated, the existing
local-maintainer specification and installed skills remain authoritative.

## User Outcome

Scheduled Snowcast catalog maintenance should more often leave the owner with a
ready or narrowly reviewable PR. It must retain the exact-head, source-trust,
owner-gate, and helper-only publication protections that prevent incorrect or
stale branch mutation.

The workflow should stop using every curation review as an unbounded regional
discovery exercise. Curation should finish a correct bounded graph. Regional
coverage expansion should move through the existing discovery worker as a
separate owner-gated proposal loop.

## Problem

The current workflow is operationally safe but semantically inefficient.
Fresh full reviews repeatedly expand destination, stay-base, pass, access, and
source inventories after earlier findings have already been fixed. Exact report
reconciliation proves that declared changes are internally consistent, but it
cannot prove that every relevant adjacent candidate was considered.

This creates three failure patterns:

1. a repair loop becomes a regional research loop and stops as non-converging;
2. valid local fixes become non-resumable even though the remote PR head did
   not change; and
3. identical validation, URL, and broad review work is repeated after every
   small remediation.

Increasing the cycle or time limit alone does not solve these problems. The
workflow needs an explicit semantic boundary, durable unfinished progress, and
stage-specific validation.

## Goals

- Optimize ordinary curation for correct bounded graphs and ready-PR
  throughput.
- Preserve exhaustive regional coverage as a separate discovery responsibility.
- Establish the candidate/source universe before semantic remediation.
- Distinguish graph correctness blockers from additive regional follow-ups.
- Preserve mechanically valid unfinished work without treating it as reviewed.
- Keep independent post-fix review while preventing unrestricted rediscovery.
- Check every final source URL while avoiding repeated unchanged URL work.
- Reuse the existing two workers, global leases, proposal cap, schema-v3 report,
  backlog, labels, canonical comment, and helper publication boundary.

## Non-Goals

- Automatic approval or merge.
- A third worker, third automation, or separate regional-discovery lease.
- A runtime destination coverage registry.
- Deterministic interpretation of backlog prose or source semantics.
- Publishing unreviewed local remediation to the PR branch.
- Claiming complete regional, Alpine, or global coverage from one curation PR.
- Weakening exact-head, mutation-scope, source-trust, CI, mergeability, or owner
  decision gates.

## Design Principles

1. **Curation proves bounded correctness; discovery expands coverage.**
2. **The evidence envelope is frozen before the first fix.**
3. **Graph-invalidating omissions block; additive omissions become follow-ups.**
4. **Independent review rechecks conclusions, not identical subprocess work.**
5. **Mechanically safe unfinished work may be resumed but is never trusted as
   reviewed.**
6. **Each stage runs only the verification needed by its next transition.**

## Workflow Architecture

The local maintainer remains one control plane with the existing curation and
discovery workers.

### Curation worker

For one selected PR, the curation worker:

1. inspects journals and continuation state;
2. resumes a reviewed continuation, resumes a remediation continuation, or
   prepares an ordinary eligible PR;
3. establishes a bounded evidence envelope and complete candidate inventory;
4. runs the independent source/trust and graph/scope lanes;
5. consolidates their candidate-level ledgers into one compatible first fix;
6. runs fresh bounded verification review after each semantic fix;
7. routes additive adjacent coverage into the report and merged backlog;
8. performs one comprehensive final validation; and
9. publishes through the existing helper-only exact-head lifecycle.

### Discovery worker

The existing discovery worker gains a regional-completion selection mode. It:

1. prioritizes actionable regional-completion items merged into the product
   backlog;
2. researches enough of the named region to understand candidate dependencies;
3. selects one coherent destination graph slice;
4. prepares one complete owner-gated proposal for that slice; and
5. falls back to unrelated external discovery only when no regional item is
   actionable.

A coherent graph slice contains one destination plus the bases, ski areas,
terrain domains, access edges, pass products, trust data, and explicit
migration handoffs required to make that destination internally meaningful. It
is neither one entity per PR nor an entire region per PR.

The existing discovery lease, three-open-proposal cap, `maintainer:proposal`
gate, proposal publication capability, and Monday/Wednesday/Friday schedule
remain unchanged.

## Evidence Envelope And Inventory Freeze

Before semantic remediation, Codex defines the evidence envelope that
establishes completeness for the selected PR. It contains:

- official destination and booking directory collections used by the PR;
- operator piste maps, ski-area presentations, and access pages;
- current official pass and tariff listings;
- catalog nodes and relationships touched by the prepared diff;
- candidate entities explicitly named by those sources; and
- linked-PR dependencies found during the two initial review lanes.

Codex interprets sources and candidate meaning. Deterministic code validates
only the typed shape, stable keys, exact-head binding, and referenced report
entities.

The initial source/trust reviewer inventories applicable trust field groups and
their evidence. The initial graph/scope reviewer inventories every concrete
destination, base, ski area, terrain domain, access edge, and pass candidate
visible in the envelope. Before a fix begins, the parent reconciles both outputs
into one frozen candidate-level inventory.

Each inventory entry records:

- stable candidate key and entity kind;
- scope ownership;
- evidence references;
- current disposition;
- graph impact: `graph_blocking` or `regional_followup`; and
- canonical product-backlog reference when it is a follow-up.

The first semantic remediation batches every compatible open blocker inside
the selected PR's mutation scope. It must not fix one representative candidate
while leaving other enumerated members untreated.

## Schema-V3 Extension

The report remains schema version 3. The implementation adds optional typed
fields rather than creating schema version 4:

- top-level `review_evidence_envelope`, a list of source-family records with a
  stable family ID, source kind, bounded URLs, and candidate kinds examined;
- `graph_impact` on each `entity_scope_assessment`, with values
  `graph_blocking` or `regional_followup`.

Existing disposition and `backlog_ref` rules remain authoritative. A
`regional_followup` must use a non-represented disposition and a canonical
backlog reference. A represented or added entity cannot be classified only as
a regional follow-up. Parser support lands before installed skills begin
emitting the new optional fields.

Legacy schema-v3 reports remain readable. A selected report without the new
fields is enriched by the existing pre-review normalization stage; this remains
structural normalization and consumes no semantic remediation cycle.

Generic schema-v3 parsing therefore keeps both additions optional, but the
maintainer's finalized curation and discovery-proposal validation profiles are
strict: they require a non-empty evidence envelope and `graph_impact` on every
scope assessment. This prevents a newly created or normalized report from
silently bypassing the inventory contract while retaining backward-readable
legacy artifacts.

`candidate_kinds` declares which entity categories a source family was used to
examine. It is not deterministic proof that a candidate exists. Candidate-level
claims remain auditable through each scope assessment's `evidence_refs`; the
validator requires every envelope URL to be present in report evidence but does
not invent candidate findings from source-family metadata.

## Graph-Correctness Boundary

A newly found omission blocks the current PR only when it can make the proposed
resulting graph materially wrong or misleading.

Blocking examples include:

- an independently owned stay market represented under the wrong destination;
- a ski area, pass, weather identity, terrain owner, or access edge attached to
  the wrong owner;
- omitted scope that changes the meaning of an existing graph node or edge;
- evidence contradicting a fact added by the PR; and
- a missing dependency without which the selected graph cannot operate or
  validate correctly.

Regional-follow-up examples include:

- another bookable hamlet whose omission does not misstate current ownership;
- an additional local pass not required by the represented access graph;
- an adjacent destination that would extend coverage without changing current
  identities; and
- optional enrichment or source coverage that does not alter current facts.

When evidence is insufficient and the candidate might invalidate the graph,
the workflow uses the existing manual-check, owner-decision, or review-incomplete
route. It must not silently downgrade uncertainty to a follow-up.

## Post-Fix Review And Closure

Every semantic fix still receives a fresh independent review on the exact new
head. The reviewer independently verifies:

- every frozen candidate;
- the complete resulting graph;
- affected trust groups and source ownership; and
- resolution, regression, or movement of prior findings.

The reviewer does not restart unrestricted regional research. It may expand
blocking scope only when evidence shows that the current graph is materially
wrong.

An additive candidate found after the freeze is collected into one final
report/backlog handoff patch. That patch may change only the report, its
deterministic rendering, and the relevant product-backlog item. It receives
delta validation and a targeted independent consistency review that checks the
handoff and confirms the graph did not change. It does not trigger another
unbounded regional audit.

## Backlog Handoff

The product backlog is the initial durable handoff from curation to regional
discovery. The same curation PR:

- classifies the candidate as a regional follow-up in schema v3;
- records its evidence and rationale;
- supplies a canonical `backlog_ref`; and
- adds or updates one concise regional-completion item with the next coherent
  graph slice.

Discovery treats follow-ups in open PRs as pending dependencies and does not
publish proposals from them. The item becomes actionable only after it merges
to `main`. This ensures discovery does not depend on catalog work the owner may
decline.

A dedicated destination coverage registry remains a possible future
improvement. It is not introduced by this design.

Finalized maintainer validation checks every `regional_followup` backlog anchor
against the exact-head `docs/product-backlog.md`. A missing or stale anchor is a
mechanical validation failure. Codex still owns the meaning, priority, wording,
and status of the backlog item; the helper does not parse backlog semantics.

For a backlog-origin regional proposal, the proposal-only mechanical boundary
requires exactly one `resulting_graph.focus_stay_destination_id`, matching the
selected `stay_destination:<id>` candidate. Added bases, ski areas, passes,
access edges, and weather implications must belong to that destination graph or
be declared linked dependencies. This rejects unrelated catalog expansion
without turning coherent-slice selection into deterministic product logic.

## Remediation Continuation

The helper gains one private continuation kind alongside the existing reviewed
continuation.

### Meaning

- A **reviewed continuation** preserves an exact head that passed independent
  semantic review and may need deterministic validation or finalization.
- A **remediation continuation** preserves an exact mechanically valid local
  head whose semantic review is incomplete or still has open findings.

A remediation continuation grants recovery authority only. It never grants
review, validation, publication, or semantic authority. Its status domain is
separate from reviewed continuations and cannot represent `validated` or any
publication-ready state.

### Creation

After a parent-owned local remediation commit, the helper may create or
atomically replace one remediation continuation only when:

- catalog and trust data validate;
- required report reconciliation for the changed data passes;
- changed paths and file modes remain inside the prepared scope;
- the worktree is clean;
- the prepared base and selected remote head remain exact; and
- no push journal already owns the work item.

The record stores the PR, remote head, prepare-time base, exact local squash
commit/ref, allowed paths, report path, and completed stage. Persisted allowed
paths are routing facts only: replay and promotion re-derive the changed paths
and file modes from the immutable exact commit and enforce the prepared scope.
Finding ledgers and review prose may be retained only as untrusted context.

### Selection and resumption

Selection priority is:

1. unresolved push journal;
2. reviewed continuation;
3. remediation continuation;
4. ordinary eligible PR.

The helper replays a remediation continuation onto current `main` using the
same exact-head, ancestry, allowed-path, and bounded-conflict protections as a
reviewed continuation. The resulting head always receives one fresh bounded
full review before another fix or promotion to reviewed state.

Promotion is crash-safe. The helper persists the reviewed continuation first,
while inspection already prefers reviewed recovery for that PR, and only then
marks the remediation record consumed. A crash between those writes leaves the
reviewed continuation authoritative and the older remediation record harmless;
the next exact replay completes cleanup idempotently.

A GitHub pause label prevents automatic resumption. If the owner deliberately
removes the hold while the remote head remains exact, the helper exposes the
continuation as resumable.

### Invalidation

A remediation continuation is invalidated when:

- the remote PR head changes, closes, or merges;
- its persistent ref is missing or tampered with;
- replay requires unsafe or unrelated conflict resolution;
- catalog/trust data or the allowed-path contract no longer validates; or
- a push journal becomes the sole irreversible recovery authority.

It has no time-based expiry. Exact repository and GitHub state determine its
validity.

Read-only inspection exposes only allowlisted summaries. Push journals never
expose origin/recovery run IDs or other lease-authority fields. Remediation
summaries expose an allowlisted availability reason as well as `resumable`, so
operators can distinguish pause labels, head drift, lifecycle invalidation,
missing/tampered refs, and a competing recovery authority without receiving a
lease token. Close/merge reconciliation is a lease-owned invalidation step;
reopening the PR never revives a previously invalidated continuation.

Sleep, deadlines, helper-response capture loss, deterministic validation
interruption, or publication failure do not erase an otherwise valid
continuation.

## Proportional Validation

Validation is staged so each transition proves only what the next stage needs.

| Stage | Required verification | Explicitly deferred |
|---|---|---|
| Inspect and prepare | repository/PR identity, exact heads, lease/journal state, allowed paths, parseable selected files | semantic review, broad tests, URL sweep |
| Inventory freeze | typed envelope/inventory shape, stable keys, source references | catalog test suite, repeated URL checks |
| Each remediation | changed JSON, affected catalog/trust invariants, required exact reconciliation, `git diff --check`, finding-related tests | broad catalog suite, unrelated tests, full URL sweep |
| Remediation checkpoint | reuse successful exact-head delta evidence; verify clean head and persisted refs | rerunning the delta commands |
| Independent review | semantic verification inside the frozen envelope | identical deterministic subprocesses and unrestricted regional research |
| Final reviewed head | full catalog/trust validation, exact reconciliation, render parity, fixed broad catalog suite, changed production tests, final source verification, mergeability/exact-head gates | unrelated repository suites already owned by CI |
| CI/readiness | existing required checks and helper readiness facts | repeated local semantic review |

The expected healthy path is one inventory stage, one consolidated fix, one
bounded full review, and one comprehensive final validation. Additional cycles
exist only for genuine graph blockers.

The final local pytest stage treats the prepared PR as data, not executable
authority. The helper pins the uv project, pytest configuration/root, root
conftest, and fixed test-module paths to a clean exact-base checkout whose
required files are regular and non-symlinked. Those trusted tests read the
prepared head's catalog and trust manifest through one helper-derived data-root
environment value. PR changes under `tests/` remain eligible for review and CI,
but unattended local validation never collects or imports them. Each validation
subprocess also receives a fresh private `HOME`; ambient credential files and
raw subprocess output are unavailable to the test process and helper response.

## Source URL Verification

Source verification belongs to Codex orchestration, not to the deterministic
helper. The helper validates URL syntax, report references, exact heads, and
typed evidence; it does not decide page relevance or make network access a
mutation capability. The curation/review skills own the bounded web checks and
record their result in the review ledger and final triage.

Scoped validation must not weaken source integrity.

### Initial inventory

Every declared source URL is checked for reachability, page relevance, and
semantic support for its cited claim. HTTP 200 alone is insufficient.

### Remediation cycles

Only added, removed, changed, or claim-affected URLs are rechecked. Unchanged
exact-head results may be cached for the duration of the current run.

### Final reviewed head

The workflow performs a parallel reachability check for every URL in the final
report and semantically revalidates all changed, graph-critical, and high-impact
sources. A later scheduled run or resumed continuation performs a fresh final
reachability pass; source cache entries do not survive the run as authority.

The run-local cache is an in-memory orchestration optimization keyed by exact
head, URL, and claim context. It is never persisted as authority. Repository
tests cover typed URL/reference gates; installed-skill acceptance and bounded
prompt-injection dry runs cover orchestration, cache invalidation, and final
fresh-source behavior.

Source failure is classified as follows:

- persistent unreachable or missing source: replace, downgrade, or block when
  it is the only support for a graph-critical claim;
- reachable but irrelevant or stale content: source-trust finding;
- transient timeout: bounded retry, then an explicit caveat or safe pause;
- reachable but non-extractable image/PDF: retain only with corroboration or an
  explicit evidence caveat.

## Helper And Skill Responsibilities

### Repository helper

The deterministic helper owns only objective additions:

- typed schema-v3 envelope/impact validation;
- exact remediation-continuation persistence, replacement, replay,
  invalidation, and safe inventory;
- exact-head/path/mode/base/ref checks;
- existing journal, push, publication, CI, mergeability, and readiness gates.

It does not decide source relevance, semantic completeness, candidate
materiality, backlog priority, or coherent graph-slice boundaries.

### Codex maintainer skill

The orchestration skill owns:

- evidence-envelope construction;
- candidate enumeration and inventory reconciliation;
- graph-impact classification;
- source/trust and graph/scope review;
- consolidated remediation;
- regional-follow-up wording and backlog handoff;
- choosing regional completion before unrelated discovery; and
- interpreting safe helper outcomes.

The catalog review and curation skills receive matching bounded-inventory,
graph-correctness, handoff, and proportional-validation instructions.

## GitHub Behavior

Existing labels, body management, and the canonical maintainer comment remain.
No new label is required for remediation continuations because continuation
state is private mechanical recovery state.

Terminal outcomes remain truthful. A PR may be labelled blocked or
owner-decision while its private remediation continuation survives. The label
prevents scheduled resumption; deliberate owner removal re-enables only an
exact still-valid continuation.

The automation still never approves or merges.

## Failure Handling

- A graph blocker remaining at a cycle/time bound creates or retains a safe
  remediation continuation before terminal status publication.
- A regional follow-up cannot by itself produce non-converging or blocked.
- An unsafe, dirty, invalid, out-of-scope, or remotely drifted head is not
  checkpointed.
- Current-main replay conflict follows the existing single bounded allowed-path
  continuation rule; broader conflicts stop.
- Operational failure after reviewed checkpointing resumes validation or
  finalization without semantic rework.
- Operational failure after helper push remains journal-owned and recovery-first.

## Verification Strategy

Implementation uses test-first coverage for:

- schema-v3 reports with and without the optional evidence envelope and graph
  impact fields;
- required backlog references for regional follow-ups;
- rejection of represented entities classified only as follow-ups;
- evidence-envelope stable-key and source-reference validation;
- remediation-continuation creation, atomic replacement, selection priority,
  replay, pause-label hold, deliberate resume, and invalidation;
- tampered/missing refs, changed remote heads, unsafe paths/modes, dirty state,
  replay conflicts, and competing journals;
- exact-head reuse of delta validation without duplicate command execution;
- strict finalized-report/proposal inventory profiles while legacy reports
  remain readable;
- exact-head backlog-anchor validation and one-focus-destination proposal
  boundaries;
- safe push-journal summaries with no run IDs or private journal fields;
- crash-safe reviewed promotion and remediation-specific status transitions;
- allowlisted continuation availability reasons and close/reopen invalidation;
- backlog-first regional-completion selection and the existing proposal cap;
  and
- end-to-end ordinary, reviewed-continuation, remediation-continuation,
  regional-follow-up, regional-proposal, waiting-CI, ready, blocked,
  owner-decision, and recovery paths.

Repository tests should assert capability outcomes and state transitions rather
than exact Codex prose, live web behavior, or LLM conclusions. Installed-skill
and automation-prompt review, final all-URL behavior, run-local source-cache
invalidation, and adversarial-content dry runs occur separately after merge.

## Rollout

Implementation should be divided into two safe activation slices:

1. **Curation convergence:** schema-v3 additions, inventory freeze,
   graph-correctness routing, proportional validation, and remediation
   continuations.
2. **Regional completion:** merged-backlog handoff and discovery-worker
   prioritization of coherent graph slices.

Repository code, tests, authoritative specs, and ADR 0011 are merged before any
personal skill or automation prompt changes. Installed skills are then updated
and inspected together. Schedules, model choice, working directory, proposal
cap, labels, and configured active-state defaults remain unchanged.

The live cutover is owner-controlled: both schedules are temporarily paused,
any active lease and journal are allowed to settle, prior installed artifacts
are snapshotted, all shared skills and both prompts are replaced and inspected,
and disabled/manual smoke cycles run before the owner re-enables one schedule
at a time. This temporary pause is an operational cutover, not a change to the
configured schedule defaults. The same boundary applies to rollback.

Rollback restores the prior installed skills and automation prompts. Existing
reviewed continuations and push journals retain their current meaning.
Remediation continuations created by the new helper are ignored by the old
orchestrator but remain private until the new helper invalidates or cleans them;
rollback must not delete refs or state records manually. The old schedules must
not be re-enabled while an active remediation continuation remains: recover or
explicitly invalidate it with the new helper first.

Rollback must also inventory every open curation/proposal head and all private
journals and continuations before a pre-change helper or either schedule is
re-enabled. Using the new helper, complete or quarantine every open report that
uses `review_evidence_envelope` or `graph_impact`; if that cannot be done safely,
retain a helper compatible with those report fields. With schedules disabled,
run a manual read-only compatibility smoke against the remaining open heads and
private state. The proposed rollback helper must inspect every remaining shape
without mutation. An unclear report, private record, or smoke result keeps both
schedules disabled; rollback never deletes or rewrites private state manually.

Each bounded Triage result and owner-private mode-`0600` diagnostic row records
the reason, stage, explicit `started_at` and `completed_at` timestamps, and only
allowlisted helper error `check` and `kind` when available. It never persists
helper detail, raw stdout/stderr,
tracebacks, commands, run IDs, private refs, source/PR prose, or caller-authored
text. A `catalog-tests` failure is reproduced from an exact continuation only
through the trusted exact-base test harness; diagnostics may retain a sanitized
fixed test-stage identifier and trusted-harness test count only when the helper
provides them.

## Success Measures

After activation, the owner should evaluate at least the next ten semantic
curation selections using the existing owner-private diagnostic index:

- share reaching waiting-CI, ready, or manual-check;
- share ending non-converging;
- median remediation and review cycles;
- elapsed minutes per lifecycle-advancing run;
- count of resumed remediation continuations versus fresh restarts;
- count of graph blockers versus regional follow-ups; and
- number of regional-completion proposals accepted, declined, or merged.

The design is successful when non-convergence caused only by additive adjacent
coverage disappears, interrupted work resumes without repeating completed
fixes, and ready/manual-check throughput improves without an increase in stale
heads, source-trust failures, unsafe scope, or CI regressions.

## Alternatives Considered

### Keep strict exhaustive curation

This retains one conceptual lane but makes every PR responsible for indefinite
regional completeness. Recent cycles demonstrate that this produces repeated
scope expansion and low throughput.

### Increase time or remediation limits

Longer loops may eventually absorb more findings but do not define closure,
prevent repeated validation, or preserve interrupted local work.

### Push unfinished remediation to the PR branch

This makes progress visible and durable but publishes semantically incomplete
work, causes CI churn, and complicates owner review. Private exact-state
continuations preserve the same work without weakening publication gates.

### Use a private helper-owned discovery queue

Immediate handoff would survive before merge but creates a hidden second source
of product truth that can become stale when a PR changes or is declined.

### Add a destination coverage registry now

A structured registry may become useful after broader coverage research. It is
unnecessary for the immediate convergence problem and would add another
maintained state artifact prematurely.

### Create a third regional worker

A third schedule and lease would duplicate the existing discovery worker's
purpose. Regional completion is a prioritized discovery selection mode, not a
separate mutation authority.

## Decision And Review Gate

- Classification: review-gated / full design flow.
- Developer Decision Checkpoints: resolved. The owner chose the two-lane model,
  coherent graph-slice proposals, merged-backlog handoff, graph-correctness
  blocking, private remediation continuations, proportional validation, and
  complete final URL reachability.
- ADR: amend ADR 0011 during implementation; no new ADR is required because the
  local Codex control plane, two-worker ownership, helper boundary, and owner
  gates remain unchanged.
- Advisory design review: required before implementation begins.
- Approval/merge behavior: unchanged; the automation never approves or merges.

# Feature Spec: Simplified Local Snowcast Maintainer

## Status

- Status: accepted
- Owner: solo-builder
- Classification: review-gated / full design flow
- Supersedes before activation:
  `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- Related ADR: ADR 0011
- Replacement implementation plan:
  `docs/superpowers/plans/2026-07-08-local-maintainer-simplification.md`
- Activation status: blocked; no personal skill or Codex automation may be
  installed from the superseded plan

## User Outcome

Snowcast should have two local Codex workers that reduce the owner's repeated
catalog-maintenance burden:

1. a curation worker that reviews and improves eligible catalog PRs until they
   are ready for the owner's final glance and merge; and
2. a discovery worker that reads the product backlog, researches missing
   catalog coverage, and creates complete owner-gated proposal PRs.

The system should be understandable and proportionate to its real risk. Codex
owns semantic interpretation, prioritization, research, review, remediation,
and workflow decisions. Repository code owns only objective safety boundaries
around identity, concurrency, branch mutation, catalog validity, proposal
volume, exact-head publication, and readiness. The automation never approves
or merges.

## Why The Design Changed

The first implementation put backlog interpretation, a 69-entry coverage
registry, detailed lifecycle policy, multiple local authorization artifacts,
duplicated GitHub machine state, and persistent lineage counters into the
deterministic helper. That implementation is well-tested, but its pull-request
merge CI exposed the cost of the boundary: valid human backlog prose repeated a
typed entity reference in one item, while the parser treated the second mention
as an ambiguous candidate and caused ten downstream test failures.

The failure was safe, but it demonstrated that deterministic code was trying
to interpret semantic documentation. In this owner-gated workflow, a Codex
discovery mistake can delay a candidate or create a proposal for the owner to
decline; it cannot merge catalog truth. The revised design therefore keeps
irreversible and objective gates deterministic while moving reviewable,
reversible interpretation to Codex.

## Design Principle

> Codex makes semantic and workflow decisions. Deterministic code exposes
> narrow safe capabilities and enforces objective mutation boundaries.

Deterministic does not mean that every workflow rule belongs in Python. It is
reserved for facts that code can verify reliably and for operations whose
failure could overwrite work, publish stale state, bypass an owner gate, or
accept structurally invalid catalog data.

## Scope

In scope:

- two local Codex App schedules in isolated worktrees;
- Codex-selected curation work from a deterministically safe PR inventory;
- guarded rebase and exact-lease push for automation-owned `codex/*` catalog
  branches;
- Codex-led review, source research, remediation, CI interpretation, backlog
  interpretation, and discovery selection;
- deterministic catalog, trust, report, scope, proposal-cap, open-duplicate,
  exact-head, CI, mergeability, and readiness checks;
- one simple global run lease, one per-work-item phase record, and one separate
  push-recovery journal;
- labels, a human-readable PR body, and one canonical maintainer comment;
- owner-gated discovery proposals with at most one proposal per run and three
  open proposals;
- safe structured errors that Codex can interpret without exposing secrets or
  untrusted raw output;
- replacement of the unactivated first implementation and its stale plan.

Out of scope:

- automatic approval or merge;
- automatic git conflict resolution;
- forks, non-`codex/*` branches, or ambiguous branch ownership;
- automatic schema changes, stable-ID migrations, or new durable domain
  semantics;
- deterministic interpretation of backlog prose;
- a runtime destination coverage registry;
- claims of complete Alpine or global coverage;
- production deployment, dependencies, secrets, database migrations, or
  production-data mutation;
- future data-quality, canary, documentation-drift, source-integrity, or
  production-investigation lanes.

## Ownership Model

### Codex App

- Runs the curation schedule four times per local day.
- Runs discovery Monday, Wednesday, and Friday.
- Creates isolated background worktrees.
- Delivers concise run outcomes to Triage.
- Does not accumulate catch-up mutations after a missed schedule.

### Codex orchestration skill

- Chooses at most one PR from a safe helper-produced inventory.
- Reads and interprets backlog prose.
- Chooses at most one discovery candidate.
- Researches official and open sources.
- Reviews catalog/domain/source behavior.
- Applies scoped catalog, trust, report, backlog, and owned-doc fixes.
- Interprets CI failures and safe helper errors.
- Chooses `working`, `owner-decision`, `manual-check`, or `blocked`.
- Requests, but cannot unilaterally authorize, `proposal`, `waiting-ci`, or
  `ready`.
- Maintains human-readable PR body and summary prose.
- Never constructs branch-rewrite or GitHub-publication commands outside the
  helper.
- Never approves or merges.

### Deterministic helper

The helper provides four capability groups only:

1. **Inspect**: safe inventory and current objective state.
2. **Prepare**: run lease, backup, fetch, guarded rebase, conflict stop, and
   scope checks.
3. **Validate**: catalog/trust/report/policy/scope validation for an exact
   reviewed head.
4. **Publish**: exact-lease push, constrained labels/comment/body publication,
   and objective proposal/waiting-CI/readiness enforcement.

### GitHub

- Stores branches, PRs, checks, lane/state labels, human-readable PR context,
  and one canonical maintainer comment.
- Does not become the reasoning or interaction control plane.

### Owner

- Removes `maintainer:proposal` to accept a discovery proposal.
- Resolves explicit product, domain, source, migration, or conflict decisions.
- Performs the final review and merge.
- Installs, activates, pauses, or disables local schedules.

## Deterministic Capability Contracts

### Inspect

Read-only inspection returns:

- open PRs that are safe candidates for automation;
- PR number, exact head, branch, base, changed paths, labels, CI state, and
  mergeability;
- current catalog entity keys;
- open and closed discovery proposal summaries;
- current open-proposal count;
- authenticated GitHub identity and repository identity.

The helper filters out forks, non-`main` bases, non-`codex/*` branches,
unapproved proposals, non-catalog scope, and PRs paused by `manual-check`,
`owner-decision`, or `blocked`. It does not rank or select an eligible PR.

### Prepare

For the Codex-selected PR, preparation:

1. verifies the project-scoped GitHub profile and exact `lampssy` identity;
2. acquires the simplified global run lease;
3. refetches and revalidates the selected PR;
4. verifies repository, remote, clean worktree, branch, base, and head;
5. fetches the exact head and current `origin/main`;
6. creates a persistent backup ref for the selected head;
7. rebases with autostash and update-refs disabled;
8. aborts rather than resolving a conflict;
9. verifies allowed changed paths, file modes, and catalog/report scope; and
10. records the prepared head in the single phase record.

The helper does not decide whether a semantic catalog change is good. It
ensures only that the selected automation-owned branch can be changed safely.

### Validate

Validation is bound to one exact Codex-reviewed commit and checks:

- catalog schema and canonical loader;
- catalog trust-manifest consistency;
- schema-version-2 curation report structure and reconciliation;
- error-level catalog policy;
- changed-path and file-mode scope;
- fixed focused catalog tests;
- discovery proposal catalog/trust/report coherence;
- open-proposal cap and same-key open-proposal duplication;
- current local and remote head relationships.

Validation does not parse backlog prose, decide source quality, interpret
candidate boundaries, classify domain findings, or infer that passing tests
make the change semantically correct.

### Publish

Publication can:

- push one exact reviewed head with
  `--force-with-lease=<branch>:<selected-head>`;
- push a new validated discovery branch only when that remote branch is absent
  and create its draft PR against `main`;
- update allowlisted lane and maintainer labels;
- update human-readable PR body content supplied by Codex;
- create or update one canonical maintainer comment;
- publish `proposal`, `waiting-ci`, or `ready` only when their objective gates
  pass.

Immediately before mutation it refetches the complete PR and rejects a changed
head, repository, base, branch, lifecycle, or incompatible objective state.
Plain force, approval, and merge are impossible through the helper.

For a new discovery proposal without a PR yet, it rechecks the proposal cap,
same-key open proposals, candidate absence from the catalog, validated local
head, approved branch namespace, and remote branch absence before a non-force
push and draft-PR creation. It then publishes the proposal label and canonical
comment for the returned PR number.

## Curation Workflow

1. Codex requests the safe curation inventory.
2. Codex chooses at most one PR based on progress potential, failures, age,
   complexity, and current project direction.
3. The helper revalidates and prepares that exact PR.
4. Codex performs a fresh complete catalog review.
5. Codex researches source or domain questions and classifies findings.
6. Codex applies a scoped fix when the issue is inside the existing model and
   source evidence is sufficient.
7. A fresh independent Codex review follows every fix.
8. At most two review/fix cycles occur in one run.
9. If still not clean, Codex requests `maintainer:manual-check`.
10. A PR carrying `manual-check` is excluded until a new commit or deliberate
    label removal makes it eligible again.
11. When Codex declares semantic review complete, the helper validates the
    exact reviewed head.
12. The helper performs the guarded push if needed.
13. Codex requests `waiting-ci` while GitHub checks are pending.
14. A later lightweight run requests readiness for the unchanged reviewed
    head.
15. The owner performs the final review and merge.

Waiting for CI is not a review/fix attempt. Persistent lineage IDs and
three-attempt counters are removed.

## Readiness Contract

`maintainer:ready` means both:

1. Codex has declared semantic review complete for an exact commit; and
2. the helper has independently confirmed the objective readiness facts for
   that same commit.

Before publishing ready, the helper verifies:

- the PR is open, same-repository, `codex/*`, and targets `main`;
- the current head equals the Codex-reviewed and helper-validated head;
- required GitHub checks for that head are green;
- GitHub reports the PR mergeable;
- `maintainer:proposal` is absent;
- no current owner-decision, manual-check, or blocked request remains.

A new commit invalidates prior semantic review, validation, CI, and readiness.
A movement of `main` that makes the PR unmergeable prevents readiness and
routes the PR back through preparation and fresh review. Ready never means
approved or merged.

## Discovery Workflow

1. Codex asks the helper for catalog keys, open proposal keys, proposal count,
   and closed proposal summaries.
2. The helper stops proposal creation at three open proposals.
3. Codex reads `docs/product-backlog.md` semantically and chooses at most one
   useful candidate.
4. When no backlog candidate is appropriate, Codex performs bounded external
   research without claiming completeness.
5. A well-supported, coherent external candidate may go directly to a complete
   owner-gated proposal.
6. A promising but unready candidate may be proposed as a lightweight backlog
   addition for owner review.
7. A weak observation remains only in Triage.
8. Codex checks closed proposal history and decides whether materially new
   evidence justifies reconsidering a declined candidate.
9. Codex researches identity, domain boundaries, sourceability, and coherent
   graph scope.
10. Read-only backlog interpretation and external research do not hold the
    global mutation lease.
11. Once Codex chooses a candidate and is ready to create repository changes,
    it acquires the discovery lease.
12. Under that lease, the helper rechecks catalog membership, open candidate
    keys, proposal count, repository identity, and current GitHub state before
    any branch or PR mutation.
13. Codex prepares the catalog, trust, report, backlog, and owned-doc changes
    while retaining and heartbeating that lease.
14. The helper validates the exact proposal diff and head before a PR exists.
15. Codex requests draft-proposal publication with the validated branch, head,
    candidate key, human-readable body, and summary.
16. The helper rechecks the cap, catalog, open proposal keys, and remote branch;
    pushes the new branch non-force, creates the draft PR, and publishes
    `lane:catalog-discovery` plus `maintainer:proposal`.
17. The owner accepts by removing the proposal label or declines by closing the
    PR.
18. An accepted proposal later enters the normal curation workflow.

The deterministic backlog parser, candidate fingerprints, exact marker cleanup,
declined-fingerprint suppression, Alpine subregion rotation, and runtime
coverage registry are removed. Codex owns whether backlog prose has been
resolved and explains cleanup or reconsideration in the PR summary.

## Destination Coverage Registry

A destination coverage registry remains a valuable future product/data
planning artifact, not a runtime discovery queue. It requires prior research
and owner decisions about geography, entity granularity, inclusion criteria,
priority tiers, authoritative sources, and connected-region counting.

If promoted later, the registry should store the desired coverage universe and
targeting information. Represented, proposed, and missing status should be
derived from the live catalog and GitHub proposal state rather than duplicated
as mutable registry fields. The current 69-entry seed is removed and must not be
treated as a complete or strategically selected universe.

## Runtime State

### Global run lease

One private owner record contains:

```json
{
  "worker": "curation",
  "run_id": "opaque-random-id",
  "acquired_at": "timestamp",
  "heartbeat_at": "timestamp"
}
```

Creating the owner record atomically acquires the mutation slot. Every mutating
command supplies the matching worker and run ID. A fresh different owner
returns `lock-busy`. A stale takeover creates a new run ID, so an older paused
run cannot operate on or release its successor. Heartbeat and release require
the exact pair.

Curation acquires the lease after read-only inventory and retains it through
prepare, review/fix, validation, push, and publication because the branch is
mutable throughout that interval. Discovery performs backlog interpretation
and external research without the lease, then acquires it immediately before
creating repository changes, revalidates catalog/proposal state, and retains it
through proposal publication. This keeps long read-only research from blocking
curation while ensuring only one worker can enter mutation.

The state directory remains owner-private and rejects symlinks and unsafe file
types. Atomic replacement is retained. The separate private token,
worker-credential files, and their cross-validation are removed because they do
not create a meaningful boundary against another same-user full-access process.

### Work-item phase record

One per-work-item record moves through:

```text
selected -> prepared -> reviewed -> validated -> pushed -> published
```

It holds only facts required for the next objective check: PR, run ID, selected
head, prepared head, reviewed head, validation result, and backup ref. If this
ordinary record is lost, the next run recomputes GitHub state, performs a fresh
semantic review when necessary, and reruns validation.

### Push journal

The push journal remains separate because network success is ambiguous across
a process crash. It records exact branch, expected remote head, new head, and
authorization phase. Recovery observes the remote:

- old head: the push did not apply and may be retried;
- new head: the push succeeded and may be recorded consumed;
- any other head: stop because another writer changed the branch.

## GitHub State

- Labels carry exactly one lane and one maintainer lifecycle state.
- The PR body contains human-readable curation/proposal context maintained by
  Codex.
- One `lampssy`-authored maintainer comment contains concise status plus one
  hidden structured record with exact reviewed head, validated head, candidate
  key/origin when applicable, and latest operation.
- Local state contains in-progress execution and push recovery only.

The duplicated discovery-origin marker in the PR body and the requirement that
body and comment machine records match are removed. A missing or malformed
canonical comment invalidates prior semantic-review state and triggers a fresh
review before it can be recreated; stale readiness is never reused.

## Lifecycle State Ownership

Codex requests:

- `maintainer:working`;
- `maintainer:owner-decision`;
- `maintainer:manual-check`;
- `maintainer:blocked`.

The helper accepts only allowlisted labels, verifies exact PR/head authority,
and ensures one lifecycle label. It does not encode source/domain policy for
choosing among those states.

Codex requests, and the helper objectively validates:

- `maintainer:proposal` for a verified owner-gated proposal;
- `maintainer:waiting-ci` for an exact pushed/validated head with checks
  pending;
- `maintainer:ready` through the readiness contract.

## Safe Errors

Every helper failure returns:

- a stable machine-readable reason;
- a bounded stage;
- an optional safe deterministic detail authored by repository code.

It never emits raw subprocess output, environment values, secrets, source-page
content, arbitrary PR prose, or arbitrary exception text. Codex interprets the
safe result and chooses retry, no-op, blocked, manual-check, or owner-decision.
The helper does not map broad exceptions directly to workflow state.

Example:

```json
{
  "status": "error",
  "reason": "stale-head",
  "stage": "pre-push",
  "detail": "PR head changed after review"
}
```

## Failure And Recovery

- **Lock busy:** clean no-op; never touch the other owner record.
- **Missing Codex or GitHub authentication:** no mutation; next run recomputes.
- **Stale selected PR:** reject before preparation.
- **Rebase conflict:** abort, retain backup, and let Codex request manual-check.
- **Source/domain ambiguity:** Codex requests owner-decision.
- **Validation failure:** return safe structured facts for Codex interpretation.
- **Push interruption:** recover only through the separate journal and observed
  remote head.
- **Partial GitHub publication:** repeat idempotent label/comment/body
  publication for the same exact head.
- **Lost ordinary local state:** recompute, review when needed, and revalidate;
  never infer a push without the journal.
- **Missing/malformed maintainer comment:** invalidate review/readiness and run
  a fresh review.
- **CI pending:** waiting-ci without repeated semantic work.
- **CI failure:** Codex interprets it in a later bounded run.
- **New head:** invalidate review, validation, CI, and readiness evidence.

## Security And Trust Boundary

- Codex continues to run with the explicitly accepted inherited
  `danger-full-access` setting on a single-user Mac.
- Helper checks are workflow guardrails, not an OS sandbox.
- PRs, diffs, comments, search results, and source pages remain untrusted data;
  their instructions cannot change repository authority or helper commands.
- GitHub commands use explicit project-scoped configuration, verify active
  login `lampssy`, strip ambient token authority, disable prompts, and use fixed
  timeouts.
- Git commands use validated argv, approved remotes, strict noninteractive
  transport, and exact heads.
- Executable code changes remain outside automatically maintainable catalog
  scope.
- LLM output cannot authorize a branch rewrite, satisfy deterministic catalog
  validation, bypass the proposal cap, approve a proposal, or merge.

## Testing Strategy

Tests focus on safety properties rather than every orchestration narrative.

Keep focused deterministic tests for:

- GitHub/repository identity and branch/base/fork/head eligibility;
- simple worker/run-ID lock ownership and stale takeover;
- conflict stop and backup creation;
- changed-path/file-mode scope;
- exact force-with-lease construction;
- catalog/trust/report/policy validation;
- proposal cap and open-key duplication;
- readiness checks;
- push-journal recovery;
- idempotent label/comment publication; and
- safe structured error output.

Use contract tests around `inspect`, `prepare`, `validate`, and `publish` rather
than reproducing the complete state matrix for every CLI command. Codex skill
tests assert invariants and structured handoff, not exact prose, candidate
choice, or model reasoning.

Remove tests for:

- the 69-entry registry and exact coverage counts;
- Markdown heading/marker parsing matrices;
- registry/catalog/backlog equality;
- private token and worker-credential permutations;
- body/comment machine-marker matching;
- persistent lineage counters; and
- duplicate authorization chains across commands.

Before updating the implementation PR, verification must run both on the
feature branch and on a temporary prospective merge with current `origin/main`,
followed by GitHub PR CI. This directly covers the merge-state drift that
exposed the old backlog parser.

## Migration

The personal skill and schedules are not installed, so no runtime compatibility
migration is required. Replace the unactivated implementation in place:

1. keep PR #43 draft and activation blocked;
2. update ADR 0011 and mark the first spec/plan superseded;
3. refactor the helper to the four capability groups;
4. remove the runtime registry and deterministic backlog parser;
5. simplify lease and operation state;
6. consolidate GitHub machine state;
7. simplify lifecycle, retry, errors, and discovery history;
8. update the future local skill specification;
9. run AI/LLM reliability, security, release, and observability review;
10. verify the feature branch and prospective merge with current main; and
11. push normally without force-pushing the implementation branch.

## Acceptance Criteria

- Codex chooses at most one PR from a deterministically safe inventory.
- Codex semantically interprets backlog and external discovery sources.
- No runtime destination coverage registry or deterministic backlog parser
  remains.
- One run creates at most one proposal and never exceeds three open proposals.
- Discovery research is read-only before lease acquisition; catalog and
  proposal state are revalidated under the lease before mutation.
- Candidates already in the catalog or already open are deterministically
  rejected.
- A new discovery branch is pushed only when its remote ref is absent, and its
  draft PR is created only from validated proposal evidence.
- The lease uses one owner record with worker, run ID, and timestamps; no
  private token or worker credential exists.
- One per-work-item phase record replaces selected/prepared/validated/
  publication artifacts.
- The separate push journal preserves exact network recovery.
- Labels, human-readable body, and one canonical comment are the only durable
  GitHub workflow surfaces.
- Codex chooses semantic lifecycle states; the helper objectively validates
  proposal, waiting-CI, and readiness.
- Manual-check pauses further selection until a new commit or deliberate label
  removal.
- Structured safe errors are actionable without exposing secrets or untrusted
  raw content.
- Guarded rebase, backup refs, conflict stop, changed-path scope, exact
  force-with-lease, catalog/trust/report/policy validation, exact-head checks,
  owner proposal approval, and no-merge rules remain deterministic.
- A PR becomes ready only for the unchanged Codex-reviewed,
  helper-validated, CI-green, mergeable head.
- The branch and prospective merge with current `main` both pass verification.
- No personal skill or automation is activated before merge and post-merge
  review.

## Decision And Review Gate

- Developer Decision Checkpoints: resolved in owner discussion for the
  deterministic/Codex boundary, readiness, registry removal, future coverage
  registry, lease, local state, GitHub state, retry pause, PR selection,
  lifecycle labels, discovery history/backlog cleanup, safe errors, and the
  shorter discovery mutation-window lease.
- ADR: ADR 0011 amended because the local control plane remains but helper
  ownership narrows from workflow policy engine to objective safety guardrails.
- Advisory design review: required before implementation with AI/LLM
  reliability, security/privacy, release/change management, and
  observability/ops.
- Implementation: blocked until the owner reviews this written spec and a
  replacement implementation plan is written.

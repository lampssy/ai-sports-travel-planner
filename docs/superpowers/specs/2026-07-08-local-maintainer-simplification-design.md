# Feature Spec: Simplified Local Snowcast Maintainer

## Status

- Status: implemented on the feature branch; final pre-merge verification pending
- Owner: solo-builder
- Classification: review-gated / full design flow
- Supersedes before activation:
  `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- Related ADR: ADR 0011
- Replacement implementation plan:
  `docs/superpowers/plans/2026-07-08-local-maintainer-simplification.md`
- Activation status: blocked; no personal skill or Codex automation may be
  installed until merge, post-merge review, and explicit owner approval through
  `docs/operating-model/local-maintainer-activation.md`

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
- deterministic catalog, trust, report, resulting-diff path/mode,
  proposal-cap, open-duplicate, exact-head, CI, mergeability, and readiness
  checks;
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

- Inspects unresolved journals before choosing fresh work; exactly one matching
  journal is recovered first and multiple journals are escalated.
- Chooses at most one PR from a safe helper-produced inventory.
- Holds the curation lease from prepare through publication.
- Reads and interprets backlog prose.
- Chooses at most one discovery candidate.
- Researches official and open sources.
- Performs read-only backlog/research work before discovery acquisition, then
  acquires discovery, reruns inspection, and mutates.
- Reviews catalog/domain/source behavior.
- Applies catalog, trust, report, non-control-plane documentation, and test
  fixes while production code, operational code, and maintainer instructions
  remain excluded.
- Performs at most six review/fix cycles and uses a fresh independent
  `snowcast-catalog-review` reviewer context after every fix. Cycles five and
  six run only while remaining findings are in-model and the fresh reviews show
  concrete convergence; the run also stops at two hours.
- Binds a complete review disposition to the exact reviewed head; incomplete
  review routes to `manual-check` or `owner-decision`.
- Heartbeats before and after capabilities and at least every five minutes
  while a lease is held.
- Releases the lease in a `finally` path with the exact run ID if and only if
  acquisition succeeded.
- Interprets CI failures and safe helper errors.
- Chooses `working`, `owner-decision`, `manual-check`, or `blocked`.
- Requests, but cannot unilaterally authorize, `proposal`, `waiting-ci`, or
  `ready`.
- Maintains human-readable PR body and summary prose.
- Reports the bounded Triage outcome for every success, stop, failure, and
  no-op; pre-lease outcomes omit the lease run ID.
- Never constructs branch-rewrite or GitHub-publication commands outside the
  helper.
- Never approves or merges.

### Deterministic helper

The helper provides four capability groups only:

1. **Inspect**: safe inventory and current objective state.
2. **Prepare**: run lease, backup, fetch, guarded rebase, conflict stop, and
   resulting-diff path/mode checks.
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
unapproved proposals, production or operational code scope, maintainer
control-plane instructions, and PRs paused by `manual-check`, `owner-decision`,
or `blocked`. A `ready` PR is also excluded while its current head matches the
trusted reviewed head; a new commit makes it eligible again. `waiting-ci`
remains visible only for the later lightweight readiness transition. Other
documentation and tests are eligible curation scope. The helper does not rank
or select an eligible PR.

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
9. verifies that the resulting diff is non-empty and contains only catalog
   data, non-control-plane documentation, tests, and safe regular-file modes
   while treating incoming report content as schema-independent review input;
   and
10. records the prepared head in the single phase record.

The helper does not decide whether a semantic catalog change is good. It
ensures only that the selected automation-owned branch can be changed safely.
It does not compare whole-file blob IDs, require the original changed-path set,
or freeze the original catalog-target set across rebase and remediation. Codex
reviews the exact resulting head, and report structure becomes authoritative
only after Codex has normalized the reviewed output to the canonical schema.

### Validate

Validation is bound to one exact Codex-reviewed commit and checks:

- catalog schema and canonical loader;
- catalog trust-manifest consistency;
- schema-version-2 curation report structure and reconciliation;
- error-level catalog policy;
- resulting-diff path and file-mode safety;
- fixed focused catalog tests;
- discovery proposal catalog/trust/report coherence;
- open-proposal cap and same-key open-proposal duplication;
- current local and remote head relationships.

Validation does not parse backlog prose, decide source quality, interpret
candidate boundaries, classify domain findings, or infer that passing tests
make the change semantically correct.

### Publish

Publication can:

- push one exact validated head with
  `--force-with-lease=<branch>:<selected-head>`;
- hand off one scope-safe reviewed-but-unvalidated head through the explicit
  `publish manual-check` capability, using the same exact lease before
  publishing the semantic pause;
- create a new validated discovery branch atomically only when that remote ref
  is absent, using an empty expected-value lease, and create its draft PR
  against `main`;
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
head, approved branch namespace, and remote branch absence before an atomic
create-only push and draft-PR creation. The push uses an empty expected-value
lease such as `--force-with-lease=refs/heads/<branch>:` with a normal
`HEAD:refs/heads/<branch>` refspec; it cannot update a ref that appeared after
preflight. It then publishes the proposal label and canonical comment for the
returned PR number.

Any open proposal whose canonical comment is missing, malformed, duplicated,
or otherwise unable to provide a trusted candidate key makes proposal identity
unknown. It still counts toward the cap and blocks all new proposal publication
until that PR is reviewed and its canonical comment is repaired. This preserves
the same-key duplicate gate without trying to infer identity from prose.

## Curation Workflow

1. Codex requests the safe curation inventory.
2. Codex chooses at most one PR based on progress potential, failures, age,
   complexity, and current project direction.
3. The helper revalidates and prepares that exact PR.
4. Codex performs a fresh complete catalog review.
5. Codex researches source or domain questions and classifies findings.
6. Codex applies a fix when the issue is inside the existing model and source
   evidence is sufficient. It may update non-control-plane documentation and
   tests, but not production code, operational code, or the maintainer's own
   instructions.
7. A fresh independent Codex review follows every fix. It runs in a new
   reviewer context, separate from the fixing context, invokes the
   `snowcast-catalog-review` contract against the exact current head, and
   records that head and a complete disposition. Missing or unresolved review
   output routes to `manual-check` or `owner-decision`, never readiness.
8. At most six review/fix cycles occur in one run. Cycles five and six are
   adaptive: continue only when findings remain in-model and the latest review
   shows fewer, lower-severity, or materially narrowed findings. Stop on a
   repeated unchanged finding, loss of progress, or two hours of elapsed work.
9. If still not clean but the reviewed result remains inside the existing
   model and allowed scope, Codex invokes `publish manual-check`; the helper
   revalidates and exact-lease pushes that reviewed head before publishing the
   pause without validation evidence.
10. A PR carrying `manual-check` is excluded until a new commit or deliberate
    label removal makes it eligible again.
11. When Codex declares semantic review complete, the helper validates the
    exact reviewed head.
12. The helper performs the guarded push if needed.
13. Codex requests `waiting-ci` while GitHub checks are pending.
14. A later lightweight run handles the unchanged `waiting-ci` head without
    preparation or semantic review: it requests readiness when checks are green
    and mergeability is clean, remains a bounded no-op while checks are pending,
    and stops on failure or conflict.
15. A `ready` PR stays out of fresh selection while its head remains unchanged;
    a new commit invalidates the hold and makes it eligible again.
16. The owner performs the final review and merge.

Waiting for CI is not a review/fix attempt. Persistent lineage IDs and
three-attempt counters are removed.

Incoming curation reports may use a legacy schema or be incomplete. Codex
treats them as context and upgrades the existing report during remediation.
The final validation and readiness gates continue to require exactly one
schema-version-2 report reconciled to the reviewed catalog and trust changes.

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
6. A promising but unready candidate remains in Triage with enough context for
   the owner to decide whether it is worth preserving in the backlog later; the
   automated lane does not create backlog-only proposal PRs.
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
    creates the new branch atomically with an empty expected-value lease,
    creates the draft PR, and publishes
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
the exact pair. While a lease is held, the orchestration skill heartbeats before
and after every helper capability and at least every five minutes during longer
Codex review, remediation, or research. This remains comfortably below the
six-hour stale-takeover threshold and makes a hung run distinguishable from an
active one.

Read-only inspection surfaces every unresolved push journal before Codex may
select fresh work. Any unresolved journal blocks unrelated mutation. The worker
named by exactly one journal acquires the lease and recovers it first; multiple
unresolved journals or a journal for the other scheduled worker fail closed for
owner attention.

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
head, prepared head, reviewed head, validation result, backup ref, and the
timestamp of the latest phase transition. If this ordinary record is lost, the
next run recomputes GitHub state, performs a fresh semantic review when
necessary, and reruns validation.

The ordinary record never authorizes mutation. If a prior run stops before push
authorization, a new current lease may atomically replace its record at
`selected` only after the helper confirms there is no unresolved push journal
and revalidates the exact current PR/head or candidate/catalog/proposal facts.
The previous run remains fenced by its run ID. A `pushed` record without the
corresponding journal is inconsistent and fails closed for owner attention.

The explicit manual-check handoff is the only exception to the ordinary linear
phase progression: its work record remains `reviewed`, while a separate push
journal records and recovers the exact irreversible branch update. The
canonical GitHub machine state likewise records the reviewed head with no
validated head, so it cannot satisfy waiting-CI or readiness gates.

Every completed, stopped, or failed run emits one bounded Triage outcome with
worker, optional lease run ID, optional work ID plus PR or candidate identity,
last phase when work began, whether a mutation occurred, and a terminal/no-op
reason. The lease run ID is absent for pre-lease inspection, proposal-cap, and
no-candidate outcomes. This is diagnostic output, not an authorization
artifact; a crash can still leave only the lease, phase timestamp, and push
journal.

### Push journal

The push journal remains separate because network success is ambiguous across
a process crash. It records work ID, worker, immutable origin run ID, current
recovery run ID, exact branch, expected remote head, new head, operation phase,
and, for discovery, candidate key, candidate origin, and the returned PR number
once known. Recovery observes the remote:

- old head: the push did not apply and may be retried;
- new head: the push succeeded and recovery continues idempotently;
- any other head: stop because another writer changed the branch.

After a stale takeover, the matching worker may adopt exactly one structurally
valid unresolved journal. Adoption requires the new current lease, confirms the
old run is no longer the owner, observes the remote in one of the allowed states
above, preserves the origin run ID for audit, and atomically replaces only the
current recovery run ID. The old run remains fenced. Fresh work stays blocked
until the adopted journal reaches a terminal phase; multiple unresolved
journals are never auto-adopted.

For discovery, an absent ref is retried only through the atomic create-only
push. When the remote already equals the journaled new head, recovery searches
GitHub by exact repository and head branch. It creates the draft PR if none
exists, binds exactly one returned PR number into the journal, rejects multiple
matches, and resumes the body/comment/label publication steps idempotently.
This works even when ordinary `WorkState` was lost. A journal-bound incomplete
initial publication may repair its own missing comment from validated evidence;
outside that recovery path, missing comment state requires a fresh review.

## GitHub State

- Labels carry exactly one lane and one maintainer lifecycle state.
- The PR body contains human-readable curation/proposal context maintained by
  Codex.
- One `lampssy`-authored maintainer comment contains concise status plus one
  hidden schema-version-2 structured record with exact reviewed head, validated
  head, candidate key/origin when applicable, and latest operation. Legacy,
  missing, and unknown schema versions are untrusted and require fresh review.
- Local state contains in-progress execution and push recovery only.

The duplicated discovery-origin marker in the PR body and the requirement that
body and comment machine records match are removed. A missing or malformed
canonical comment invalidates prior semantic-review state and triggers a fresh
review before it can be recreated; stale readiness is never reused. For an open
proposal it also makes candidate identity unknown and blocks publication of any
new proposal until repaired.

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
- an optional allowlisted check/substage and failure kind for objective
  validation or transport diagnosis;
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
  "check": "remote-head",
  "kind": "mismatch",
  "detail": "PR head changed after review"
}
```

## Failure And Recovery

- **Lock busy:** clean no-op; never touch the other owner record.
- **Unresolved push journal:** block fresh selection; the matching worker
  recovers or safely adopts exactly one journal before unrelated mutation.
- **Missing Codex or GitHub authentication:** no mutation; next run recomputes.
- **Stale selected PR:** reject before preparation.
- **Rebase conflict:** abort, retain backup, and let Codex request manual-check.
- **Source/domain ambiguity:** Codex requests owner-decision.
- **Validation failure:** return the allowlisted check/substage and failure kind
  plus safe structured facts for Codex interpretation.
- **Push interruption:** recover only through the separate journal and observed
  remote head.
- **Discovery push before PR creation:** use the journaled candidate/branch/head
  to find or create exactly one draft PR, persist its number, and resume
  publication idempotently.
- **Partial GitHub publication:** repeat idempotent label/comment/body
  publication for the same exact head.
- **Lost ordinary local state:** recompute, review when needed, and revalidate;
  never infer a push without the journal.
- **Stale pre-push ordinary state:** with no unresolved journal, a current
  successor lease revalidates live identity/head and replaces the record at
  `selected`; the old run remains fenced.
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
- Caller-selected title, body, and summary files must be direct-child,
  owner-private regular files in the maintainer state directory. The helper
  opens the already-validated private directory once and opens a validated
  basename relative to that descriptor with no symlink following; nested paths
  and symlinked ancestors are impossible. Inputs have strict byte limits and
  valid UTF-8. The helper passes only validated strings to the GitHub adapter,
  which writes its own mode-0600 temporary files; caller paths are never passed
  to `gh`.
- Production and operational executable code changes remain outside
  automatically maintainable catalog scope; test code is the explicit
  owner-reviewed exception.
- LLM output cannot authorize a branch rewrite, satisfy deterministic catalog
  validation, bypass the proposal cap, approve a proposal, or merge.

## Testing Strategy

Tests focus on safety properties rather than every orchestration narrative.

Keep focused deterministic tests for:

- GitHub/repository identity and branch/base/fork/head eligibility;
- simple worker/run-ID lock ownership and stale takeover;
- conflict stop and backup creation;
- resulting-diff path/file-mode safety;
- exact force-with-lease construction;
- catalog/trust/report/policy validation;
- proposal cap and open-key duplication;
- fail-closed unknown proposal identity;
- readiness checks;
- push-journal recovery, including a crash after discovery push but before PR
  creation and recovery with lost ordinary phase state;
- unresolved-journal inventory, successor adoption after stale takeover, and
  old-run fencing;
- long-run heartbeat and stale-run fencing;
- direct-child, descriptor-relative, no-symlink publication inputs;
- idempotent label/comment publication; and
- safe structured error output with validation substage/failure kind.

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
3. add the new contracts alongside the old unactivated CLI so every
   intermediate commit remains runnable;
4. perform one atomic CLI/model/runtime cutover and delete the old surfaces;
5. remove the runtime registry and deterministic backlog parser;
6. simplify lease and operation state;
7. consolidate GitHub machine state;
8. simplify lifecycle, retry, errors, and discovery history;
9. update the future local skill and post-merge activation specifications;
10. run AI/LLM reliability, security, release, and observability review;
11. verify the feature branch and exact CI-parity prospective merge with
    current main;
12. rewrite draft PR #43's body to the final contract and push normally without
    force-pushing the implementation branch.

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
- Any open proposal with unknown candidate identity blocks new proposal
  publication until repaired.
- A new discovery branch is created atomically only when its remote ref is
  absent, and its draft PR is created only from validated proposal evidence.
- A crash after discovery push but before PR creation resumes from the separate
  journal without updating an unexpected remote ref or creating duplicate PRs.
- Fresh work is blocked while an unresolved journal exists; one matching
  successor can adopt it after remote observation, while the prior run remains
  fenced and multiple journals fail closed.
- The lease uses one owner record with worker, run ID, and timestamps; no
  private token or worker credential exists.
- One per-work-item phase record replaces selected/prepared/validated/
  publication artifacts and carries a last-transition timestamp.
- The separate push journal preserves exact network recovery.
- Labels, human-readable body, and one canonical comment are the only durable
  GitHub workflow surfaces.
- Codex chooses semantic lifecycle states; the helper objectively validates
  proposal, waiting-CI, and readiness.
- Manual-check pauses further selection until a new commit or deliberate label
  removal.
- Structured safe errors are actionable without exposing secrets or untrusted
  raw content and identify the allowlisted failed validation check when useful.
- Publication inputs cannot read outside private maintainer state or follow a
  symlink, and caller-selected paths are never passed to `gh`.
- Guarded rebase, backup refs, conflict stop, resulting-diff path/mode safety,
  exact force-with-lease, catalog/trust/report/policy validation, exact-head
  checks, owner proposal approval, and no-merge rules remain deterministic.
- Curation PRs that include non-control-plane documentation or tests remain
  eligible; production and operational code, maintainer control-plane
  instructions, workflows, dependencies, migrations, deployment configuration,
  and executable scripts remain excluded.
- Curation preparation accepts schema-independent incoming report content, but
  final validation requires one canonical schema-version-2 reconciled report.
- A PR becomes ready only for the unchanged Codex-reviewed,
  helper-validated, CI-green, mergeable head.
- The branch and prospective merge with current `main` both pass verification.
- Every intermediate refactor commit is runnable; one explicit atomic cutover
  commit is the pre-activation rollback unit.
- PR #43 remains draft and its body describes the final simplified contract,
  exact verified heads, review status, and activation block.
- No personal skill or automation is activated before merge and post-merge
  review.

## Decision And Review Gate

- Developer Decision Checkpoints: resolved in owner discussion for the
  deterministic/Codex boundary, readiness, registry removal, future coverage
  registry, lease, local state, GitHub state, retry pause, PR selection,
  lifecycle labels, discovery history/backlog cleanup, safe errors, and the
  shorter discovery mutation-window lease. The owner also chose
  schema-independent report input with canonical schema-version-2 output, then
  chose resulting-diff safety instead of blob/path/target equality and allowed
  documentation plus tests in curation scope.
- ADR: ADR 0011 amended because the local control plane remains but helper
  ownership narrows from workflow policy engine to objective safety guardrails.
- Advisory design review: complete for AI/LLM reliability, security/privacy,
  release/change management, and observability/ops. The reviews found no
  Blockers. Their High findings are resolved in this contract by atomic
  create-only discovery push, private contained publication inputs, an atomic
  compatibility cutover, explicit crash recovery between push and PR creation,
  and an explicit PR #43 body rewrite. Cheap scoped Medium findings are also
  incorporated: fail-closed unknown proposal identity, verifiable fresh review,
  phase timestamps and heartbeat cadence, validation substage reporting,
  unresolved-journal inventory and successor adoption, CI-parity
  prospective-merge verification, deletion-aware staging, and a reviewed
  post-merge activation/rollback checklist.
- Advisory feature review: complete for the same four domains. AI/LLM
  reliability, security/privacy, and observability/ops recommended shipping.
  Release/change management found one High lifecycle gap: an owner-accepted
  discovery proposal could be selected for curation but could not replace its
  discovery lane label. Commit `690e584` resolves it with a one-way,
  proposal-gated discovery-to-curation transition, test-first coverage, and an
  independent approval. No Blocker, unresolved High, or accepted Medium finding
  remains. Actual Codex schedule delivery and Triage behavior remain a
  post-merge activation-review concern because those records do not exist yet.
- Advisory amendment review: complete for the resulting-diff boundary. The
  review found no unresolved Blocker or High finding after excluding the
  maintainer's own operating instructions from otherwise eligible
  documentation. Exact branch/head/lease checks, backup refs, safe file modes,
  production and operational scope exclusions, validation, CI, and the human
  merge gate remain intact. Allowing test changes retains the documented risk
  that CI assertions can be weakened, but no workflow path can approve or merge
  the resulting PR.
- Implementation: complete on the feature branch through the atomic CLI
  cutover, publication/recovery hardening, focused verification, and advisory
  feature-review fixes. Controlling feature-branch verification passes: 620
  maintainer tests, 241 focused catalog tests, repository-wide Ruff lint and
  formatting, and 1,250 full-suite tests. Final prospective-merge verification,
  PR update, and CI remain required. Activation remains blocked until merge and
  the separate post-merge checklist receives explicit owner approval.

# Feature Spec: Simplified Local Snowcast Maintainer

## Status

- Status: implemented, merged to `main`, and locally activated
- Owner: solo-builder
- Classification: review-gated / full design flow
- Supersedes before activation:
  `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- Related ADR: ADR 0011
- Replacement implementation plan:
  `docs/superpowers/plans/2026-07-08-local-maintainer-simplification.md`
- Activation status: the personal skills and both owner-approved Codex
  automations are installed; the post-merge checklist remains the authoritative
  reactivation and rollback procedure

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
- semantic prioritization of curation PRs whose earlier selected cycle ended
  without any GitHub publication;
- guarded rebase and exact-lease push for automation-owned `codex/*` catalog
  branches;
- Codex-led review, source research, remediation, CI interpretation, backlog
  interpretation, and discovery selection;
- deterministic catalog, trust, report, resulting-diff path/mode,
  proposal-cap, open-duplicate, exact-head, CI, mergeability, and readiness
  checks;
- one simple global run lease, one per-work-item phase record, and one separate
  push-recovery journal, plus one successor-adoptable reviewed continuation
  before push authorization;
- labels, a human-readable PR body, and one canonical maintainer comment;
- owner-gated discovery proposals with at most one proposal per run and three
  open proposals;
- backlog-first discovery with bounded preferred retry after any viable
  source-validated selection and explicit next slices for known regional
  catalog gaps;
- decision-bearing owner-gated proposals for boundary, stable-ID, and
  weather-owner changes expressible by the existing catalog model;
- safe structured errors that Codex can interpret without exposing secrets or
  untrusted raw output;
- replacement of the unactivated first implementation and its stale plan.

Out of scope:

- automatic approval or merge;
- unbounded automatic git conflict resolution. The reviewed-continuation path
  may expose one helper-prepared conflict set limited to existing-model catalog,
  trust, curation-report, backlog, or focused test files. Codex resolves only
  that set locally, and the helper completes and revalidates the replay before
  one fresh independent full review. A conflict involving production code,
  schema semantics, maintainer control-plane files, or any other disallowed
  path still stops;
- forks, non-`codex/*` branches, or ambiguous branch ownership;
- automatic execution of schema changes, stable-ID/database migrations, or new
  durable domain semantics; an existing-model catalog re-key may be proposed
  with an explicit unresolved migration handoff;
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
- Reads a bounded unpublished-curation follow-up list from automation memory,
  revalidates every entry against the safe live inventory, and selects a still
  exact eligible follow-up before an unrelated fresh PR.
- Chooses at most one PR from a safe helper-produced inventory.
- Holds the curation lease from prepare through publication.
- Reads and interprets backlog prose.
- Prioritizes a freshly revalidated preferred retry, then bounded candidate
  slices from Catalog Curation Refinements, before unrelated external research.
- Chooses at most one discovery candidate.
- Researches official and open sources.
- Performs read-only backlog/research work before discovery acquisition, then
  acquires discovery, reruns inspection, and mutates.
- Reviews catalog/domain/source behavior.
- Applies catalog, trust, report, non-control-plane documentation, and test
  fixes while production code, operational code, and maintainer instructions
  remain excluded.
- Invokes `snowcast-catalog-curation` only in explicit `maintainer-managed`
  mode inside the provided isolated worktree. The sub-skill supplies semantic
  research, edits, reporting, and reconciliation, then yields branch, commit,
  validation, and publication ownership to this orchestration layer.
- Keeps preparation schema-independent, then structurally normalizes a legacy,
  malformed, graph-less refreshed, incomplete, or non-reconciling report before
  initial review. The maintainer-managed pass rebuilds one schema-v3 report
  from the exact prepared base/current catalog and trust snapshots, validates,
  reconciles, runs finding-related focused tests, and commits without claiming
  semantic resolution or consuming a remediation cycle.
- Starts curation with parallel independent `source-trust` and `graph-scope`
  reviews of that normalized prepared head, then consolidates both dispositions
  into one first fix. Source-trust inventories every applicable canonical trust
  field group; graph-scope inventories every concrete operator presentation and
  lift-pass candidate, retaining typed/backlogged deferred or unresolved pass
  products.
- Before treating a destination or ski-area boundary finding as an owner
  choice, runs one fresh focused boundary adjudication against the accepted
  model rules. A policy-determined graph returns to the normal fixer/re-review
  loop; only multiple defensible product graphs reach `owner-decision`.
- Carries a private structured finding ledger into each later fresh full review
  as untrusted history so resolved, repeated, regressed, and genuinely new
  findings remain distinguishable without narrowing independent review.
- Represents multi-candidate scope findings as a candidate-level ledger with
  one stable entry per concrete entity, product, edge, sector, or document. An
  inventory category is incomplete until its candidates and source inventory
  are enumerated; the first fix batches all compatible candidate entries, and a
  known-but-unfixed candidate remains repeated rather than being rediscovered
  as new scope.
- Performs at most six remediation cycles. Cycles five and six run only while
  remaining findings are in-model and the ledger shows concrete convergence.
  It rechecks current-main mergeability before every fix and adaptive review
  and once more before final manual-check or validation/push, stops spawning
  semantic work at 150 minutes, and stops absolutely at 180.
- Binds a complete review disposition to the exact reviewed head. An
  incomplete review requests `blocked/review-incomplete` when the exact-head
  outcome gate is safe; only a complete reviewed scope-safe handoff may use
  `manual-check`, while a real model/owner choice uses `owner-decision`.
- Publishes safe PR-specific terminal outcomes through one status-only helper
  capability that updates only the lifecycle label and canonical comment,
  preserving separate review evidence and leaving body/branch unchanged.
- Heartbeats before and after capabilities and at least every five minutes
  while a lease is held.
- Releases the lease in a `finally` path with the exact run ID if and only if
  acquisition succeeded.
- Interprets CI failures and safe helper errors.
- Chooses `working`, `owner-decision`, `manual-check`, or `blocked`.
- Carries existing-model owner/migration decisions inside an explicit proposal
  when a complete catalog diff and handoff can be reviewed, while preventing
  readiness until the decision is resolved.
- Requests, but cannot unilaterally authorize, `proposal`, `waiting-ci`, or
  `ready`.
- Maintains a concise human-readable PR-body synopsis and summary prose while
  keeping the complete curation report checked in as the source of truth. The
  synopsis includes the exact deterministic resulting-graph Mermaid section
  reproduced from the validated catalog/report head.
- Reports the bounded Triage outcome for every success, stop, failure, and
  no-op without exposing the private lease run ID.
- Never constructs branch-rewrite or GitHub-publication commands outside the
  helper.
- Never approves or merges.

### Deterministic helper

The helper provides four capability groups only:

1. **Inspect**: safe inventory and current objective state.
2. **Prepare**: run lease, backup, fetch, guarded rebase, conflict stop, and
   resulting-diff path/mode checks.
3. **Validate**: checkpoint an exact reviewed head and run
   catalog/trust/report/policy/scope validation for that head.
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

Curation inspection also returns safe reviewed-continuation summaries without
run IDs or local paths: PR number, selected remote head, exact reviewed head,
prepare-time base, report path, validation status, and whether the current PR
labels permit owner-requested resumption. These records are distinct from
unresolved push journals and do not block discovery or unrelated curation.

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

Continuation preparation is a guarded variant of preparation. It requires one
exact available reviewed continuation, the unchanged selected remote PR head,
and a successor curation lease. It restores an unchanged reviewed head for
deterministic retry, or replays the helper-owned squash commit onto current
`main`. A clean replay returns a new prepared head requiring one full review.
An allowed-path conflict returns one bounded resolution state; only the helper
may complete the replay after Codex stages exactly those resolutions. Any other
conflict or drift aborts without changing the remote branch.

### Validate

Before running deterministic validation, Codex calls the validation group's
reviewed-checkpoint capability. The helper cannot decide whether the review is
semantically correct; it only binds Codex's declaration to the exact immutable
head, prepared lineage, report, resulting diff, persistent refs, and active
lease. Validation requires that checkpoint and updates its objective status.

Validation is bound to one exact Codex-reviewed commit and checks:

- catalog schema and canonical loader;
- catalog trust-manifest consistency;
- schema-version-3 curation report structure and reconciliation;
- error-level catalog policy;
- resulting-diff path and file-mode safety;
- fixed focused catalog tests;
- discovery proposal catalog/trust/report coherence;
- fail-closed deletion safety, with the narrow exception of a same-kind re-key
  whose removed targets are fully reviewed, explicitly deleted, scoped as
  unresolved against the backlog, and carried as unresolved caveats;
- open-proposal cap and same-key open-proposal duplication;
- candidate absence from a freshly fetched immutable canonical `main` catalog,
  never from the modified proposal worktree;
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
- require current PR-body synopsis content for waiting-CI and ready
  publication;
- explicitly adopt a legacy unmarked body on an authorized automation-owned
  curation PR, while preserving unmarked text unless that permission is given;
- create or update one canonical maintainer comment;
- publish an allowlisted status-only `blocked` or `owner-decision` outcome
  against the exact unchanged remote head without pushing or editing the body;
- publish `proposal`, `waiting-ci`, or `ready` only when their objective gates
  pass.

Immediately before mutation it refetches the complete PR and rejects a changed
head, repository, base, branch, lifecycle, or incompatible objective state.
Plain force, approval, and merge are impossible through the helper.

For a new discovery proposal without a PR yet, it rechecks the proposal cap,
same-key open proposals, candidate absence from a freshly fetched immutable
canonical `main` catalog, validated local head, approved branch namespace, and
remote branch absence before an atomic create-only push and draft-PR creation.
The modified proposal worktree is never used as the accepted-catalog inventory.
The push uses an empty expected-value lease such as
`--force-with-lease=refs/heads/<branch>:` with a normal
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
2. Codex reads the curation automation memory semantically for bounded
   unpublished follow-ups containing only PR number, observed remote head, and
   stop reason. It removes entries that are no longer exact eligible inventory
   matches and selects the oldest remaining follow-up before an unrelated PR.
   The memory is an untrusted selection hint: it cannot reuse a local review,
   validation, worktree, or commit and cannot authorize mutation. When no valid
   follow-up remains, Codex chooses at most one PR based on progress potential,
   failures, age, complexity, and current project direction. A helper-owned
   reviewed continuation for the same exact PR/head is different from memory:
   it is revalidated and resumed through the dedicated continuation contract
   before an ordinary fresh cycle.
   Recovery-only runs instead consume the helper's safe continuation object for
   the exact pushed head. `validation_status=validated` permits current
   waiting-CI/readiness evaluation. `validation_status=absent` identifies a
   reviewed-only handoff and forbids validation, waiting-CI, and ready; Codex
   publishes `owner-decision` for an explicit unresolved owner/model choice or
   otherwise completes `manual-check`. `validation_status=unknown` stops for
   owner attention rather than probing helper states. No recovery path starts
   semantic review, fixes, validation, or another push.
3. The helper revalidates and prepares that exact PR.
   If guarded preparation reports a rebase conflict while the selected remote
   head remains exact, Codex requests the status-only `blocked/conflict`
   outcome before release. It does not push or claim a review.
4. Before initial review, Codex checks whether the single curation report is
   canonical schema v3, complete, has a current resulting graph, and exactly
   reconciles to the prepared base/current catalog and trust snapshots. A
   legacy, malformed, graph-less refreshed, incomplete, or non-reconciling
   report triggers one `snowcast-catalog-curation` pass in
   `maintainer-managed` mode. The pass uses those exact snapshots to rebuild
   the single schema-v3 report, runs catalog validation, exact reconciliation,
   and finding-related focused tests, then commits locally. It is structural
   normalization only: it does not claim semantic resolution, alter the
   finding ledger, or consume a remediation-cycle slot. The fixed broad catalog
   suite remains reserved for final helper validation.
5. Codex starts two fresh reviewer contexts in parallel against the normalized
   prepared head. One invokes `snowcast-catalog-review` in `source-trust` mode;
   the other uses `graph-scope`. Neither receives the other's result. Together
   they count as one initial review stage. `source-trust` enumerates every
   applicable trust field group from the canonical `FIELD_GROUPS` registry with
   its status, direct refs, normalization-note need, and coverage disposition.
   `graph-scope` enumerates every concrete operator presentation and lift-pass
   candidate, with typed assessments and canonical backlog refs for each
   deferred or unresolved pass product.
6. Codex consolidates the two complete dispositions into one private finding
   ledger and first fix. It deduplicates overlapping findings but preserves
   conflicts. For scope inventory,
   the ledger has one stable candidate entry per concrete entity, product,
   access edge, sector, document, or other reviewed candidate, including its
   normalized key and specific source inventory. A reviewer output that names
   only an inventory category is incomplete until it enumerates that checklist;
   one generic umbrella finding cannot replace the candidate-level ledger.
   Before routing a destination or ski-area boundary disagreement
   to `owner-decision`, it starts one fresh read-only
   `snowcast-catalog-review` context in `boundary-adjudication` mode for the
   concrete candidates on the exact current head. The context receives the
   disputed questions and factual evidence inventory, but no reviewer's
   preferred graph. It returns `policy_determined`, `owner_choice_required`,
   or `evidence_insufficient`, with a recommended graph, alternatives,
   decisive evidence, and identity/weather consequences.
7. Before every fix, before adaptive reviews, and once more before any final
   manual-check or validation/push sequence, Codex fetches current `origin/main`,
   verifies the exact local head and clean worktree, and uses read-only `git merge-tree
   --write-tree origin/main HEAD`. A conflict stops the run before more review,
   fix, manual-check, validation, or push in the ordinary workflow. The sole
   exception is the helper-owned reviewed-continuation replay described below.
   A clean result is drift context only: report reconciliation and helper
   validation remain bound to the prepare-time base/head returned by the
   helper. An ordinary conflict requests status-only `blocked/conflict` for the
   unchanged remote head when the outcome gate is safe.
8. Codex applies a fix when the issue is inside the existing model and source
   evidence is sufficient. It may update non-control-plane documentation and
   tests, but not production code, operational code, or the maintainer's own
   instructions. The first fix batches every compatible open candidate entry
   from the completed initial inventory rather than choosing one representative.
   Each actually addressed ledger entry becomes only `claimed-fixed`; an
   umbrella category or omitted checklist member does not.
9. A fresh independent full Codex review follows every fix. It runs in a new
   reviewer context, receives the ledger only as untrusted history, independently
   reviews the exact current head and full scope, and then classifies prior
   entries as resolved, repeated, regressed, superseded, or owner-decision while
   reporting new findings separately. A known-but-unfixed candidate from the
   initial checklist is repeated, not new; only a candidate absent from the
   complete initial candidate/source inventory counts as scope expansion. The
   parent updates the ledger. Missing or
   incomplete output requests status-only `blocked/review-incomplete` when
   safe, never `manual-check` or readiness. A boundary finding requests
   `owner-decision` only after focused adjudication confirms
   `owner_choice_required`. `policy_determined` returns to the fixer and its
   mandatory fresh full review. `evidence_insufficient` uses `manual-check`
   only for an otherwise complete scope-safe head and otherwise requests
   `blocked/review-incomplete` when safe.
10. At most six remediation cycles occur in one run. One cycle contains one
   maintainer-managed fixer invocation, which may batch compatible ledger
   findings, one parent-owned local commit, and the required fresh full review.
   Boundary adjudication is read-only and does not consume a remediation-cycle
   slot, but it consumes the same wall-clock budget; its resulting fix and fresh
   review consume one normal cycle.
   Cycles five and six are adaptive: before spawning their reviews Codex repeats
   the current-main mergeability check, then continues only when ledger evidence
   shows fewer, lower-severity, or materially narrower in-model findings. A
   repeated unchanged finding, regression, non-narrowing new set, or loss of
   progress stops the loop and requests status-only `blocked/non-converging`
   when safe. A real owner/model choice confirmed by focused adjudication
   requests status-only `owner-decision/owner-decision`; its observed remote
   head remains separate from any unpublished local review/fix head.
11. The curation lease acquisition starts a private wall-clock semantic budget.
    Boundary adjudication uses this same budget and never extends the cycle.
    Codex starts it when the possible owner choice first appears and never at or
    after minute 120, preserving time for a policy-determined fix and fresh full
    review. A boundary question first found after that cutoff remains an exact
    unpublished follow-up for the next cycle and is not prematurely published
    as `owner-decision`. At 150 minutes Codex starts no new reviewer or fixer.
    At 180 minutes it
    interrupts active semantic contexts and enters finalization-only mode: no
    research, review, fix, commit, or new test run may begin. After exact local
    head, worktree, remote head, current-main mergeability, and review-evidence
    revalidation, the already-reviewed head may validate, push, publish, or use
    the bounded manual-check handoff. Exact-remote-head terminal outcome,
    recovery, heartbeat, release, cleanup, and Triage are also permitted.
    Finalization has a separate maximum of 30 active minutes after the task is
    running and every helper command retains its own timeout. Sleep does not
    spend this active finalization allowance; interruption leaves recovery to
    the helper journal rather than reopening semantic work.
12. If still not clean but the reviewed result remains inside the existing
   model and allowed scope, Codex invokes `publish manual-check`; the helper
   revalidates and exact-lease pushes that reviewed head before publishing the
   pause without validation evidence.
13. A PR carrying `manual-check` is excluded until a new commit or deliberate
    label removal makes it eligible again.
14. When Codex declares semantic review complete, Codex materializes a detached
    clean checkout at the exact prepare-time base returned by the helper and
    supplies it as the validation base. It never substitutes a later
    `origin/main`. The helper validates the exact reviewed head, after which
    Codex removes only the base checkout it created.
15. The helper performs the guarded push if needed.
16. Codex writes a concise synopsis of the final reviewed scope, evidence,
    verification, and owner caveats and includes the helper-reproduced canonical
    resulting-graph Mermaid section. It then requests `waiting-ci` with that
    body input while GitHub checks are pending. The helper rejects a missing or
    altered canonical graph before publication. The full schema-v3 report
    remains in the repository.
17. A later lightweight run handles the unchanged `waiting-ci` head without
    preparation or semantic review: it requests readiness when checks are green
    and mergeability is clean, supplying the current synopsis again; it remains
    a bounded no-op while checks are pending. Failed checks request the
    status-only `blocked/ci-failure` outcome for the exact unchanged head;
    stale-head and unsafe capability errors remain Triage-only.
18. A `ready` PR stays out of fresh selection while its head remains unchanged;
    a new commit invalidates the hold and makes it eligible again.
19. An unchanged status-only `blocked` or `owner-decision` head is also held out
    of selection. A new commit or deliberate label removal makes it eligible.
20. The owner performs the final review and merge.

Waiting for CI is not a review/fix attempt. Persistent lineage IDs and
three-attempt counters are removed.

Incoming curation reports are schema-independent preparation input. Before the
initial dual review, Codex normalizes any legacy, malformed, graph-less
refreshed, incomplete, or non-reconciling report against the exact prepared
base/current catalog and trust snapshots. This pre-review structural pass
rebuilds and commits exactly one canonical schema-v3 report without claiming a
semantic fix or consuming a remediation cycle. Normalization and every later
remediation run catalog validation, exact reconciliation, and finding-related
focused tests; the fixed broad catalog suite is reserved for final helper
validation. The final validation and readiness gates continue to require that
single schema-version-3 report reconciled to the reviewed catalog and trust
changes.
Historical schema-v3 reports remain readable without `resulting_graph`; any
report newly validated or refreshed by the maintainer must declare one or more
focus stay destinations so the helper can derive the canonical graph. The
declared focus must include every final-catalog destination reached by a
reviewed graph target; validation derives that set rather than trusting the
report's focus declaration alone.
The exceptional reviewed-but-unvalidated `manual-check` path must supply that
report path and the exact derived graph in its body; the helper verifies the
graph against the immutable reviewed commit and verifies that the supplied path
is the PR diff's single curation report before authorizing a push.

### Reviewed-But-Unpushed Continuation

The helper preserves a durable continuation after Codex has completed the
required independent review for an exact local head but before any push journal
exists. This closes the gap where a deterministic validation failure, helper
failure, authentication or transport interruption, local sleep, or
finalization interruption would otherwise discard completed review and
remediation work.

Codex explicitly checkpoints the reviewed head before deterministic validation.
The helper revalidates the unchanged remote PR head, prepared lineage, clean
worktree, allowed resulting diff, and single curation-report path. It then:

1. records the selected remote head, prepare-time base and prepared head,
   reviewed head, report path, guarded-sync facts, and last deterministic gate;
2. creates a persistent reviewed ref for the exact reviewed commit; and
3. creates a helper-owned synthetic squash commit whose parent is the
   prepare-time base and whose tree exactly matches the reviewed head.

The synthetic commit is local recovery material only. It is never pushed and
does not replace the exact reviewed-head identity. Its single-commit shape lets
the helper replay the complete reviewed result onto a later `main` with at most
one bounded conflict set.

Read-only curation inspection exposes safe continuation facts separately from
push journals and ordinary eligible PRs. A continuation never blocks unrelated
work globally, but it is the preferred form of the same exact unpublished
follow-up after the owner removes a pause label. The helper invalidates it when
the remote PR head changed, the PR closed or became unsafe, its persistent refs
or immutable facts no longer match, or a push journal already owns the head.
Automation memory remains only a fallback selection hint and does not duplicate
the continuation's authority. There is at most one active continuation per PR;
ordinary preparation for that exact PR is rejected until the continuation is
resumed, terminalized, or objectively invalidated.

Under a successor curation lease, continuation preparation behaves as follows:

- **Same prepare-time base and exact reviewed tree:** restore the reviewed ref,
  revalidate immutable facts, and rerun only the failed or incomplete
  deterministic gate. No semantic review is repeated because the exact
  reviewed commit is unchanged.
- **Advanced `main`, clean squash replay:** replay the synthetic commit onto
  current `main`, record a new prepared head, and require one fresh independent
  full review of the complete resulting scope. The old finding ledger may be
  supplied only as untrusted context; the two initial review lanes and completed
  remediation history are not repeated.
- **Advanced `main`, bounded allowed-path conflict:** leave exactly one
  helper-owned replay conflict in progress and return only the allowlisted
  conflict paths. Codex may resolve those paths through the maintainer-managed
  curation skill. The helper continuation command verifies that no other path
  was changed or staged, verifies that `main` has not moved since the replay
  began, completes the replay, rechecks current-main ancestry and
  resulting-diff safety, and then requires one fresh independent full review. A
  repeated conflict, disallowed path, schema/control-plane conflict, dirty
  unrelated file, missing ref, moved replay base, or unsafe Git state aborts
  the replay and stops without publication.
- **Changed remote PR head or incompatible identity/scope:** invalidate the
  continuation and return the PR to an ordinary fresh cycle; never blend saved
  work with someone else's new branch head.

The continuation remains available through review, validation, and local
finalization. Once the helper authorizes a push, the existing push journal
becomes the sole recovery authority and the local continuation becomes
terminal. A continuation is never sufficient for waiting-CI, readiness,
approval, or merge.

Continuation status is one of `available`, `resolving`, `validated`,
`consumed`, or `invalidated`, with a bounded last-gate result of `not-run`,
`failed`, or `passed`. A resolving attempt is tied to the current lease and
worktree only. If that attempt is interrupted and its lease later becomes
stale, a successor does not trust or modify the abandoned worktree: it adopts
the immutable continuation record and persistent refs, recreates the one-commit
replay in its own clean worktree, and fences the old run. The same rule handles
sleep or process loss during local conflict remediation.

For compatibility with reviewed work created before this amendment, the helper
may adopt an existing ordinary `reviewed` work record only when its exact commit
still exists, its selected remote head is unchanged, its guarded-sync lineage
and current tree revalidate, and the supplied report is the single changed
curation report. It cannot adopt an arbitrary caller-provided commit. This
bounded compatibility path is sufficient for PR #35's preserved reviewed head.

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
- a current concise body synopsis was supplied through the private publication
  input contract.

An unmarked legacy body is not silently overwritten. Codex must request the
helper's explicit body-adoption permission for an already-authorized
automation-owned curation PR. That one-time adoption replaces the legacy body
with a marked managed synopsis. Once the markers exist, later waiting-CI,
recovery, and ready runs update the same block idempotently; malformed or
duplicated markers always fail closed.

A new commit invalidates prior semantic review, validation, CI, and readiness.
A movement of `main` that makes the PR unmergeable prevents readiness and
routes the PR back through preparation and fresh review. Ready never means
approved or merged.

## Discovery Workflow

1. Codex asks the helper for catalog keys, open proposal keys, proposal count,
   and closed proposal summaries.
2. The helper stops proposal creation at three open proposals.
3. Codex first revalidates any bounded preferred-retry hint saved after a prior
   viable selection. A still-absent, coherent, sourceable retry is selected
   before new research; stale, represented, duplicated, or declined hints are
   cleared.
4. Otherwise Codex reads `Catalog Curation Refinements` semantically and
   prioritizes `Status: candidate` items plus their explicit next bounded slice,
   favoring completion of partially modeled regions. `parked` remains an
   owner-authored dependency stop.
5. Only when no bounded backlog slice is actionable does Codex perform external
   research without claiming completeness.
6. A well-supported, coherent external candidate may go directly to a complete
   owner-gated proposal.
7. A promising but unready candidate remains in Triage with enough context for
   the owner to decide whether it is worth preserving in the backlog later; the
   automated lane does not create backlog-only proposal PRs.
8. A weak observation remains only in Triage.
9. Codex checks closed proposal history and decides whether materially new
   evidence justifies reconsidering a declined candidate.
10. Codex researches identity, domain boundaries, sourceability, and coherent
   graph scope.
11. Read-only retry validation, backlog interpretation, and external research
    do not hold the global mutation lease.
12. Once Codex chooses and source-validates a viable candidate, it records the
    bounded candidate identity, origin, source list, and selected stop reason as
    an untrusted preferred-retry hint. It then acquires the discovery lease.
13. Structured `lock-busy` is a normal terminal no-op. The existing preferred
    retry is retained with a lock-busy stop reason without reading the active
    owner, retrying, or releasing a lease this run never acquired.
14. Under an acquired lease, the helper rechecks catalog membership, open candidate
    keys, proposal count, repository identity, and current GitHub state before
    any branch or PR mutation.
15. Codex invokes `snowcast-catalog-curation` in `maintainer-managed` mode to
    prepare the catalog, trust, report, backlog, and owned-doc changes in the
    isolated worktree while retaining and heartbeating the lease. The sub-skill
    returns before the parent-owned commit, validation, or publication.
16. An existing-model boundary, stable-ID, or weather-owner change may proceed
    as a decision-bearing proposal. Its report and body expose old/new identity,
    affected historical data, preserve/migrate/backfill decision, manual
    commands, merge order, rollback, and unresolved owner decision. Database or
    schema execution remains separate, and unresolved handoffs block readiness.
    An old-key removal must be a same-kind replacement candidate; each removed
    target is fully reviewed, has an exact identity deletion, is referenced by
    an unresolved scoped assessment and backlog item, and carries a caveat.
    Unrelated removals remain invalid.
17. The helper fetches canonical `main`, then validates the exact proposal diff
    and head before a PR exists. Candidate presence in the proposal head is the
    intended delta, not a duplicate; presence in canonical `main` is a
    duplicate.
18. Codex requests draft-proposal publication with the validated branch, head,
    candidate key, human-readable body, and summary.
19. The helper freshly fetches and rechecks canonical `main`, the cap, open
    proposal keys, and the remote branch before each irreversible publication
    step; it creates the new branch atomically with an empty expected-value
    lease, creates the draft PR, and publishes
    `lane:catalog-discovery` plus `maintainer:proposal`.
20. The owner accepts by removing the proposal label or declines by closing the
    PR.
21. An accepted proposal later enters normal curation. Unresolved decision or
    migration handoffs route to `owner-decision`, never readiness.
22. A merged proposal consumes its bounded backlog slice and promotes the next
    remaining slice; the regional item closes only when no useful gap remains.

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
Codex review, remediation, or research. A lease becomes stale after one hour
without a heartbeat. This permits twelve missed heartbeat intervals before a
fenced takeover while preventing an interrupted Codex task from blocking later
scheduled work for most of a day.

The caller treats structured `lock-busy` directly as a bounded no-op. It never
reinterprets the helper envelope, reads the active owner record, retries, or
releases when acquisition failed. Discovery persists a bounded semantic
preferred-retry hint as soon as one source-validated candidate is selected, so
lock-busy, sleep, or task interruption does not silently lose it. The hint
authorizes nothing and must be revalidated on the next run.

Curation automation memory may retain a bounded semantic list of selected PRs
whose cycle ended without any GitHub mutation. Each entry contains only the PR
number, exact remote head observed by the failed run, and bounded stop reason.
The next run revalidates entries against helper inspection, drops stale or
ineligible entries, and prioritizes the oldest valid entry. A successful branch
or lifecycle publication, closed PR, changed head, or loss of eligibility clears
that entry. The list never carries review, validation, or mutation authority.
Resolve the Codex home as `CODEX_HOME` when set and otherwise `$HOME/.codex` so
an unset shell variable does not silently hide the automation memory.

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

The curation parent records a private wall-clock start at successful lease
acquisition. It checks the fixed local clock before each reviewer or fixer
spawn. The 150-minute soft deadline prevents new semantic work. The 180-minute
hard semantic deadline interrupts active semantic work, but exact-state
validation, publication, recovery, lease cleanup, and final Triage retain a
separate 30-minute active-execution allowance. Before finalization the parent
revalidates the local head, clean worktree, remote head, current-main
mergeability, and exact-head review evidence. This orchestration deadline is
independent of the one-hour stale-lock threshold because active work refreshes
the lease at least every five minutes.

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

An exact same-lease curation validation retry at phase `validated` is
idempotent. The helper revalidates the selected remote head, prepared lineage,
reviewed head, prepare-time base, and report path without rerunning the three
validation commands, then returns `already-validated`. Any changed PR, head,
base, report, lease, or later phase still fails closed.

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

A separate reviewed-continuation record is also retained before push. Unlike
the ordinary run-owned phase record, it is successor-adoptable and binds its
exact reviewed and synthetic squash refs to the selected PR/head, guarded-sync
facts, report path, validation status, and terminal/available state. Creating,
adopting, replaying, terminalizing, or invalidating this record requires the
active curation lease and atomic state transitions. It carries no GitHub
mutation authority; a push still requires the ordinary validated work state
and creates the separate push journal first.

Every completed, stopped, or failed run emits one bounded Triage outcome with
worker, optional work ID plus PR or candidate identity, last phase when work
began, whether a mutation occurred, and a terminal/no-op reason. Lease run IDs
remain private and are never included. This is diagnostic output, not an
authorization artifact; a crash can still leave only the lease, phase
timestamp, and push journal.

After cleanup, the worker also appends one owner-private mode-`0600` diagnostic
JSONL row in its automation directory with finish time, selected item, observed
remote and local heads, review-cycle count, last successful stage, helper reason, GitHub mutation
flag, elapsed minutes, and recovery obligation. Missing values are explicit
`null`; lease IDs, credentials, commands, source prose, and raw errors are never
recorded. The index is for operational audits only and cannot authorize
selection, recovery, review reuse, or mutation.

### Push journal

The push journal remains separate because network success is ambiguous across
a process crash. It records work ID, worker, immutable origin run ID, current
recovery run ID, exact branch, expected remote head, new head, operation phase,
and, for discovery, candidate key, candidate origin, validated report path,
canonical resulting graph, and the returned PR number once known. The report
and graph are immutable recovery evidence; journal-only proposal publication
fails closed when either is unavailable. Recovery observes the remote:

- old head: the push did not apply and may be retried;
- new head: the push succeeded and recovery continues idempotently;
- any other head: stop because another writer changed the branch.

For curation recovery the helper also returns a safe continuation derived from
the journaled new head and matching ordinary work evidence: reviewed head plus
`validated`, `absent`, or `unknown` validation status. The continuation exposes
objective evidence only; Codex retains the semantic choice between a reviewed-
only manual check and an explicit owner decision. It must not try readiness as
a validation probe.

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
  Codex. For curation readiness this is a compact synopsis, not the complete
  checked-in report, but it includes the same canonical resulting-graph Mermaid
  section as the rendered report.
- One `lampssy`-authored maintainer comment contains concise status plus one
  hidden schema-version-2 structured record with exact reviewed head, validated
  head, candidate key/origin when applicable, and latest operation. Legacy and
  unknown schema versions are untrusted and require fresh review before prior
  review or readiness evidence can be reused.
- A status-only terminal publication adds a separate hidden schema-version-1
  outcome record to that same comment. It contains only the exact observed
  remote head, `blocked` or `owner-decision` state, and an allowlisted reason;
  it never changes or substitutes for the review/validation record.
- Local state contains in-progress execution and push recovery only.

The duplicated discovery-origin marker in the PR body and the requirement that
body and comment machine records match are removed. A missing or malformed
canonical comment invalidates prior semantic-review state; a status-only
outcome may repair the comment with an explicit empty review record, but cannot
restore review, validation, or readiness evidence. A fresh review is required
before any such evidence is recreated, and stale readiness is never reused.
For an open proposal, missing trusted state also makes candidate identity
unknown and blocks publication of any new proposal until repaired.

## Lifecycle State Ownership

Codex requests:

- `maintainer:working`;
- `maintainer:owner-decision`;
- `maintainer:manual-check`;
- `maintainer:blocked`.

The helper accepts only allowlisted labels, verifies exact PR/head authority,
and ensures one lifecycle label. It does not encode source/domain policy for
choosing among those states.

`publish outcome` is the narrow terminal-status path for `blocked` and
`owner-decision`. It requires the active curation lease, exact unchanged remote
head, and private bounded summary input. It updates only the canonical comment
and lifecycle label. It is not available after lock-busy, stale head,
authentication failure, unknown state, or an unsafe capability error. Semantic
deadline expiry itself permits exact-state deadline outcome finalization.

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

- **Lock busy or interrupted discovery:** clean no-op for lock-busy and no
  inferred mutation after interruption. Discovery records a source-validated
  selected candidate before lease acquisition and revalidates it on the next
  run before new research.
- **Unpublished curation cycle:** retain or upsert the selected PR, observed
  remote head, and bounded stop reason in curation automation memory. If a
  helper-reviewed continuation exists, a later run prefers and revalidates that
  exact continuation instead of restarting semantic work. Without one, the
  memory entry remains only a selection hint and all semantic review and helper
  gates start fresh.
- **Reviewed continuation with unchanged base/head:** restore the exact reviewed
  ref and rerun only the failed or incomplete deterministic/finalization gate.
- **Reviewed continuation after main drift:** replay the helper-owned squash
  commit. A clean replay or one bounded allowed-path conflict remediation is
  followed by one fresh independent full review; broad or unsafe conflicts stop.
- **Reviewed continuation after remote-head drift:** invalidate it and start an
  ordinary fresh cycle only if the new PR head remains eligible.
- **Unresolved push journal:** block fresh selection; the matching worker
  recovers or safely adopts exactly one journal before unrelated mutation.
- **Missing Codex or GitHub authentication:** no mutation; next run recomputes.
- **Stale selected PR:** reject before preparation.
- **Ordinary rebase/current-main conflict:** abort, retain backup, and request
  the status-only `blocked/conflict` outcome when the selected remote head
  remains exact; otherwise Triage only. The reviewed-continuation replay has
  the single allowed-path remediation exception specified above.
- **Destination/ski-area boundary ambiguity:** run focused boundary adjudication
  before minute 120. Return a policy-determined result to the fixer, route an
  evidence gap through the safe manual-check/review-incomplete rules, and
  request status-only `owner-decision/owner-decision` only when multiple
  defensible product graphs remain and exact-head publication is safe.
- **Validation failure:** return the allowlisted check/substage and failure kind
  plus safe structured facts for Codex interpretation; use manual-check only
  for a complete reviewed scope-safe head, otherwise request status-only
  `blocked/validation-failure` when safe.
- **Lost validation response:** poll the original helper process through exit.
  If capture is genuinely lost, an exact same-lease validated request returns
  `already-validated`; changed inputs or phases remain rejected.
- **Push interruption:** recover only through the separate journal and observed
  remote head.
- **Discovery push before PR creation:** use the journaled candidate/branch/head
  to find or create exactly one draft PR, persist its number, and resume
  publication idempotently.
- **Partial GitHub publication:** repeat idempotent label/comment/body
  publication for the same exact head; recovery cannot omit the required
  curation synopsis when completing waiting-CI or ready.
- **Post-push PR API lag:** after an exact journaled push, retry PR-head reads
  for at most 15 seconds only while Git already exposes the new head and the PR
  API still exposes exactly the journaled old head. Continue when both converge;
  stop immediately on any unexpected third head and leave the journal for
  recovery.
- **Lost ordinary local state:** recompute, review when needed, and revalidate;
  never infer a push without the journal.
- **Stale pre-push ordinary state:** with no unresolved journal, a current
  successor lease revalidates live identity/head and replaces the record at
  `selected`; the old run remains fenced.
- **Missing/malformed maintainer comment:** invalidate review/readiness; a
  status-only outcome may recreate an explicit empty review record, but a fresh
  review is required before review or readiness evidence can be restored.
- **CI pending:** waiting-ci without repeated semantic work.
- **CI failure:** a later bounded run requests status-only
  `blocked/ci-failure` for the exact unchanged head.
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
- Lease-bound `publication-input create` receives title, body, or summary bytes
  only on stdin. It validates bounded UTF-8, creates one random direct-child
  basename descriptor-relatively with `O_CREAT|O_EXCL|O_NOFOLLOW` and exact
  mode `0600`, fsyncs it, rechecks the lease, and returns only that basename.
  It accepts no filename/source path and never echoes publication text.
- Workflows pass only helper-created direct-child basenames to publication
  commands. The reader remains fail-closed for unsafe directories, symlinks,
  ownership, modes, UTF-8, and size; caller paths are never passed to `gh`.
- Summary text may use bounded multi-line Markdown. The helper normalizes line
  endings and rejects NUL/unsafe controls, maintainer markers, and raw HTML
  comment delimiters so prose cannot corrupt the canonical machine record.
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
- proposal-head additions versus freshly fetched canonical-main duplicate
  separation, including a main advance before push;
- fail-closed unknown proposal identity;
- readiness checks;
- push-journal recovery, including a crash after discovery push but before PR
  creation and recovery with lost ordinary phase state;
- unresolved-journal inventory, successor adoption after stale takeover, and
  old-run fencing;
- long-run heartbeat and stale-run fencing;
- complementary initial review modes, ledger reconciliation, and incomplete
  lane failure;
- current-main conflict stops before each fix, adaptive review, and final
  manual-check or validation/push sequence;
- reviewed-continuation checkpoint/ref creation, successor adoption, exact-head
  deterministic retry, clean main-drift replay, one bounded allowed-path
  conflict remediation, and fail-closed remote-head/ref/scope drift;
- transition from reviewed continuation to the existing push journal without
  competing recovery authority;
- 150-minute new-semantic-work cutoff, 180-minute semantic stop, and separate
  30-active-minute exact-state finalization allowance;
- status-only outcome exact-head, no-body/no-push, review-evidence-preservation,
  idempotent comment/label, and new-head re-eligibility behavior;
- bounded multi-line summary rendering with line-ending normalization and
  rejection of unsafe controls or reserved marker syntax;
- direct-child basename, descriptor-relative, no-symlink publication inputs
  with safe path-shape diagnostics;
- exact same-lease curation-validation replay after a lost response;
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

The historical implementation verification ran both on the feature branch and
on a temporary prospective merge with then-current `origin/main`, followed by
GitHub PR CI. This covered the merge-state drift that exposed the old backlog
parser.

## Historical Migration Record

The following completed sequence records how the unactivated implementation was
replaced. It is history, not current operational instruction:

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
- A still-exact eligible PR from an unpublished curation cycle is selected
  before unrelated fresh work. A helper-owned reviewed continuation may restore
  its exact reviewed work; otherwise its memory entry supplies no review or
  mutation authority.
- Codex semantically interprets backlog and external discovery sources.
- No runtime destination coverage registry or deterministic backlog parser
  remains.
- One run creates at most one proposal and never exceeds three open proposals.
- Discovery prioritizes a revalidated preferred retry, then actionable bounded
  Catalog Curation Refinements slices, before unrelated external research.
- Discovery research is read-only before lease acquisition; catalog and
  proposal state are revalidated under the lease before mutation.
- Candidates already in freshly fetched canonical `main` or already open on
  GitHub are deterministically rejected; a candidate present only in its
  proposal head is not a duplicate.
- Any open proposal with unknown candidate identity blocks new proposal
  publication until repaired.
- A new discovery branch is created atomically only when its remote ref is
  absent, and its draft PR is created only from validated proposal evidence.
- Existing-model decision-bearing re-key or weather-owner proposals expose
  historical-data impact and migration/rollback handoffs and cannot reach ready
  while the owner decision remains unresolved.
- Proposal validation accepts only explicitly reconciled same-kind re-keys;
  unrelated, cross-kind, or incompletely declared removals fail closed.
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
- Canonical summaries accept bounded multi-line Markdown while rejecting unsafe
  controls and syntax reserved for the maintainer's hidden machine records.
- Waiting-CI and ready require a current curation synopsis, legacy unmarked
  bodies are replaced only through explicit adoption, and malformed managed
  markers fail closed.
- Guarded rebase, backup refs, conflict stop, resulting-diff path/mode safety,
  exact force-with-lease, catalog/trust/report/policy validation, exact-head
  checks, owner proposal approval, and no-merge rules remain deterministic.
- Curation PRs that include non-control-plane documentation or tests remain
  eligible; production and operational code, maintainer control-plane
  instructions, workflows, dependencies, migrations, deployment configuration,
  and executable scripts remain excluded.
- Curation preparation accepts schema-independent incoming report content, but
  a legacy, malformed, graph-less refreshed, incomplete, or non-reconciling
  report is structurally normalized before initial review. The pass uses exact
  prepared catalog/trust snapshots, commits one canonical schema-version-3
  report, runs focused validation/reconciliation, and consumes no remediation
  slot; final helper validation alone runs the fixed broad catalog suite.
- Initial curation review uses complete independent source/trust and graph/scope
  lanes on the same exact normalized prepared head; neither lane sees the
  other's output. Source/trust enumerates every applicable `FIELD_GROUPS`
  entry with status, direct refs, normalization-note need, and coverage
  disposition. Graph/scope enumerates every concrete operator presentation and
  lift-pass candidate; deferred or unresolved pass products require typed
  assessments and canonical backlog refs.
- Initial multi-candidate scope output becomes a candidate-level ledger with an
  enumerated candidate/source checklist; an inventory category alone is
  incomplete, and a known-but-unfixed candidate cannot later be classified as
  newly discovered scope.
- Every post-fix full reviewer independently reconstructs current scope before
  reconciling the parent-owned finding ledger as untrusted history.
- Current-main conflicts stop before every ordinary fix, adaptive review, and
  final manual-check or validation/push sequence. Only a helper-owned reviewed
  continuation may expose one allowed-path squash-replay conflict for bounded
  maintainer-managed resolution, and the resulting exact head receives one
  fresh independent full review before validation or publication.
- An exact reviewed-but-unpushed head survives deterministic validation,
  helper, authentication, transport, sleep, deadline-finalization, and local
  process interruptions through owner-private state and persistent refs. It is
  invalidated on remote-head drift and yields to the push journal before any
  irreversible branch mutation.
- Safe selected-PR terminal outcomes update one canonical comment and lifecycle
  label without pushing, changing the body, or claiming review/validation; the
  hold applies only to the exact observed remote head.
- Curation starts no semantic work after 150 minutes, interrupts active
  semantic contexts at 180 minutes, and then permits only the separate bounded
  exact-state finalization phase.
- A destination or ski-area boundary reaches `owner-decision` only after one
  exact-head focused adjudication confirms multiple defensible graphs; the pass
  starts before minute 120, shares the same 180-minute budget, and returns a
  policy-determined graph to the fixer plus fresh full review.
- A PR becomes ready only for the unchanged Codex-reviewed,
  helper-validated, CI-green, mergeable head.
- The branch and prospective merge with current `main` both pass verification.
- Every intermediate refactor commit is runnable; one explicit atomic cutover
  commit is the pre-activation rollback unit.
- The original cutover PR was merged only after its body described the final
  simplified contract, exact verified heads, review status, and activation
  block; later amendments pass the same focused and prospective-merge gates.
- Personal skills and automations are updated only after the corresponding
  helper contract is merged and verified, with the post-merge checklist as the
  rollback reference.

## Decision And Review Gate

- Developer Decision Checkpoints: resolved in owner discussion for the
  deterministic/Codex boundary, readiness, registry removal, future coverage
  registry, lease, local state, GitHub state, retry pause, PR selection,
  lifecycle labels, discovery history/backlog cleanup, safe errors, and the
  shorter discovery mutation-window lease. The owner initially chose
  schema-independent report input with canonical schema-version-2 output; the
  later ski-area boundary contract upgraded canonical output and final
  validation to schema version 3. The owner then chose resulting-diff safety
  instead of blob/path/target equality and allowed documentation plus tests in
  curation scope. The owner also chose preferred
  retry after viable source-validated selection, backlog-first regional
  completion, and explicit
  decision-bearing catalog proposals whose unresolved migration handoffs block
  readiness rather than proposal creation. For curation convergence, the owner
  chose complementary parallel initial reviews, an untrusted cross-review
  finding ledger, current-main conflict probes before fixes/adaptive reviews
  and final publication, 150/180-minute semantic deadlines, and a separate
  30-active-minute finalization allowance while retaining the current model.
  The owner then chose a pre-review structural normalizer: it preserves
  schema-independent preparation, rebuilds the report from exact prepared
  catalog/trust snapshots, and yields a locally committed canonical v3 report
  to the two initial reviewers without counting as semantic remediation. The
  owner then chose one idempotent status-only GitHub outcome for safe
  PR-specific terminal stops, using existing `blocked`/`owner-decision` labels,
  the canonical comment, exact observed-head holds, and no PR-body updates. For
  discovery duplication, the owner chose the proposal base/head as delta
  evidence, freshly fetched immutable `main` as accepted-catalog authority, and
  GitHub as open-proposal authority. The owner subsequently chose semantic
  prioritization of unpublished curation cycles through revalidated automation
  memory, and relaxed canonical summary validation to normal bounded multi-line
  Markdown while preserving file-containment, exact-head, and reserved-marker
  protections. The owner then chose helper-owned reviewed-but-unpushed
  continuation. Exact unchanged heads rerun only deterministic/finalization
  gates; advanced `main` replays one synthetic squash and requires a fresh full
  review. One helper-prepared conflict set may be resolved only within existing
  allowed catalog/report/test scope, while broader, schema, production, or
  control-plane conflicts still stop.
- ADR: ADR 0011 amended because the local control plane remains but helper
  ownership narrows from workflow policy engine to objective safety guardrails.
  No further ADR is needed for the convergence amendment because it changes
  orchestration review policy without moving the accepted control-plane or
  helper-authority boundary. The canonical-main duplicate correction likewise
  keeps that boundary and only fixes which immutable catalog supplies an
  existing-candidate fact. Reviewed continuation also keeps that boundary:
  Codex resolves semantics, while the helper owns exact refs, state adoption,
  replay completion, scope checks, push authorization, and publication. No new
  ADR is required.
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
- Advisory discovery-policy amendment review: complete for data trust/source
  integrity, AI/LLM reliability, observability/ops, and release/change
  management. No Blocker, High, or accepted Medium finding remains. The review
  exposed and resolved one implementation mismatch: proposal validation had
  still rejected every old-key removal. The helper now permits only a fully
  reviewed and reconciled same-kind re-key with an unresolved migration
  handoff; cross-kind and incompletely reported removals still fail closed.
- Advisory convergence amendment review: complete for data trust/source
  integrity, AI/LLM reliability, observability/ops, and release/change
  management. Forward-testing found and resolved stale activation status,
  lease-ID disclosure, canonical-checkout, live-GitHub-authority, and
  current-main/prepare-base contract mismatches. The resulting workflow keeps
  the two initial reviewers independent, treats the ledger as untrusted,
  rechecks mergeability without changing the validation base, including a final
  probe before manual-check or validation/push. The later reliability amendment
  replaces the five-minute cleanup reserve with bounded post-deadline
  finalization. No unresolved Blocker or High
  finding remains. The residual limitation is explicit: deadlines are
  enforced by the local Codex parent and automation prompt, not an external
  operating-system watchdog.
- Advisory terminal-outcome amendment review: complete for security/privacy,
  observability/ops, and AI/LLM reliability. No Blocker, High, or Medium finding
  remains. Exact-head and lease gates, allowlisted state/reason pairs, private
  summaries, strict marker parsing, and separation from review evidence prevent
  the status path from claiming readiness or changing the branch/body. The
  residual Low operational risk is that the comment and label are separate
  idempotent GitHub mutations: a process interruption between them may cause
  one redundant later review, but cannot push, approve, merge, or reuse stale
  review evidence.
- Advisory canonical-main duplicate amendment review: complete for data
  trust/source integrity, observability/ops, security/privacy, and release/change
  management. No Blocker, High, or Medium finding remains. Proposal delta
  validation stays bound to immutable base/head objects; live duplicate checks
  use an exact fetched `main` object plus GitHub proposal identity; remote-policy
  and sanitized network-error behavior are unchanged; and a newly detected
  duplicate stops before push. The residual Low race is that `main` can advance
  after the final fetch but before atomic create-only branch push; the draft
  proposal owner gate and later curation/readiness checks prevent automatic
  acceptance if that occurs.
- Advisory reviewed-continuation amendment design review: complete for AI/LLM
  reliability, security/privacy, observability/ops, and release/change
  management. The review found and resolved two High design gaps: ordinary
  preparation can no longer overwrite an exact active continuation, and an
  interrupted conflict attempt is recreated from immutable refs in a successor
  worktree rather than trusting an abandoned dirty worktree. Exact review reuse
  is limited to an unchanged commit/base; any replayed head receives a fresh
  independent full review. No unresolved Blocker or High finding remains.
- Advisory reviewed-continuation amendment feature review: complete for AI/LLM
  reliability, security/privacy, observability/ops, and release/change
  management. It found and resolved two High implementation gaps: replay now
  rejects a rewritten `main` that does not descend from the reviewed base, and
  a later legitimate cycle can replace a terminal continuation only after the
  remote PR head changes. Exact checkpoint retries, successor adoption,
  validation failure, clean replay, bounded conflict cleanup, and
  continuation-to-journal handoff are covered by focused tests. No unresolved
  Blocker or High finding remains. The residual Low operational cost is that
  immutable local checkpoint refs are retained for diagnosis until deliberate
  maintenance is introduced; they contain commits only, no credentials or
  authority-bearing lease data.
- Implementation and activation: the base design is complete. Its feature work
  passed the recorded maintainer, focused catalog, lint/format, full-suite,
  prospective-merge, and CI checks before merge. The owner then approved and
  enabled the local schedules; later amendments use this spec and the post-merge
  checklist as their current contract and rollback reference. The
  reviewed-continuation amendment is owner-approved, implemented, feature-
  reviewed, verified, merged through PR #57, and activated in the installed
  personal skill. Scheduled runs use only the generic helper-owned continuation
  inventory and lifecycle; migration of any pre-existing legacy reviewed record
  remains an explicit owner-run operation outside the recurring schedule.

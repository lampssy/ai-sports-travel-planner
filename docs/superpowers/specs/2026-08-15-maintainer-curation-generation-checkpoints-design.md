# Feature Spec: Maintainer Curation Generation Checkpoints

## Status

- Status: accepted
- Owner: solo-builder
- Related docs:
  - `docs/operating-model/local-maintainer-activation.md`
  - `docs/operating-model/maintainer-runtime-command-contract.md`
  - `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Related plan: to be authored after written-spec approval
- Related ADRs:
  - `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
  - planned `ADR 0020`: generation-based pre-push curation authority,
    superseding only the reviewed/remediation-continuation portion of ADR 0011

## User Outcome

The local curation maintainer should preserve safe progress across interruption,
validation failure, and movement of `main` without repeatedly stopping on
internal state combinations that are mechanically recoverable.

The owner should continue to receive the same conservative GitHub behavior:
the maintainer never approves or merges, never guesses across an uncertain
external mutation, and never pushes an unreviewed or unvalidated catalog head.

## Problem

The current pre-push workflow represents one curation attempt through several
overlapping persisted objects:

- run-local curation work;
- reviewed continuations;
- remediation continuations;
- validation status on reviewed continuations; and
- helper-owned Git refs for each continuation type.

Each object has its own status transitions and replacement rules. A valid
operation must satisfy the cross-product of those rules. This has made local,
reversible work fail as if it were an unsafe external mutation.

The PR #37 failure is representative. A reviewed continuation was replayed
against a newer `main`, fresh review found one report-only remediation, and all
focused validation passed. The helper then rejected the new checkpoint because
an older remediation for the unchanged remote PR head had already been
consumed. The older checkpoint used a different prepare-time base, so this was
a new legitimate attempt, but the state store applied a blanket same-head
reopening prohibition.

The current ordering can also create local Git refs before the corresponding
state write. A later state rejection can therefore return
`mutation_occurred=false` despite having changed helper-owned local refs.

## Scope

In scope:

- replace pre-push curation recovery authority with one typed timeline per PR;
- model retries and replay as explicit generations and append-only events;
- replace separate remediation and reviewed checkpoint commands with one
  idempotent curation checkpoint capability;
- make ordinary preparation and continuation preparation one helper decision;
- expose one current generation and one exact next action through inspection;
- make interrupted local checkpoint writes recoverable;
- reserve `invalid-command` for actual command-contract errors;
- archive and reset existing pre-push curation state through an explicit
  migration;
- update the runtime contract and installed maintainer skill together; and
- preserve final validation and push-journal handoff.

Out of scope:

- changing push-journal semantics;
- changing post-push CI continuations or CI-repair budgets;
- changing terminal-publication recovery;
- changing catalog review, source-trust, or graph-scope policy;
- changing GitHub labels, readiness meaning, approval, or merge behavior;
- preserving existing unpublished reviewed or remediation progress; and
- redesigning the discovery worker.

## Product Fit

This is an owner-operations reliability change. It does not alter Snowcast
search, ranking, catalog meaning, or public product language. It reduces the
manual effort required to obtain trustworthy catalog PRs while retaining the
owner as the final reviewer and merger.

## Domain Model

### Bounded Context

The change is owned by the local maintainer control plane. It does not introduce
new ski-catalog domain language.

### Curation Timeline

Each curation PR has at most one logical `CurationTimeline`. The timeline is the
sole cross-run authority for pre-push curation progress.

The timeline contains:

- state schema version;
- work ID and PR number;
- target branch identity; and
- an ordered, non-empty list of immutable generations.

The timeline is stored as a private directory containing one
Pydantic-validated document per generation. A generation document is replaced
atomically only to append events; existing events are never edited or removed.
The current generation is the highest valid generation number, so no separate
mutable current-pointer file is required. Each generation document retains the
existing private-state size limit. The bounded semantic-remediation policy also
bounds events within one generation, while older generation files remain small
diagnostic history without growing the active document.

### Curation Generation

A generation represents one preparation lineage for one selected remote PR
head and one prepare-time base. It contains:

- a monotonically increasing generation number and opaque generation ID;
- selected remote PR head;
- target branch;
- prepare-time base;
- prepared head and guarded-sync facts;
- canonical curation-report path;
- creation timestamp; and
- ordered generation events.

A new generation is required when:

- `main` advances and the saved work is replayed;
- the remote PR head changes;
- a prior generation is explicitly invalidated; or
- immutable preparation lineage no longer matches.

An unchanged remote PR head does not imply the same generation. The
prepare-time base and guarded replay lineage are part of generation identity.

Only one generation is current. Older generations remain immutable audit and
diagnostic history but grant no current recovery or publication authority.

### Generation Events

The initial event records successful preparation. Later events are appended
for:

- `checkpoint_started`;
- `checkpoint_completed`;
- `validation_failed`;
- `validation_passed`;
- `generation_superseded`;
- `generation_invalidated`; and
- `generation_consumed`.

A checkpoint event declares one of these semantic stages:

- `delta_validated`: the exact local head passed bounded deterministic delta
  checks and is safe recovery material, but it is not semantically reviewed;
- `reviewed`: Codex declared the exact head semantically reviewed after the
  required fresh independent review; or
- `fully_validated`: the exact reviewed head passed the final helper-owned
  deterministic suite.

Repeated remediation/review rounds remain inside one generation. A newer
`delta_validated` head supersedes the earlier local head for recovery. A
`reviewed` event must refer to the latest completed checkpoint head. Final
validation must refer to the latest reviewed head.

## Command Contract

### `prepare curation`

`prepare curation --pr <number>` becomes the only pre-push preparation entry
point. Under an owned curation lease, the helper decides whether to:

- create an ordinary first generation;
- restore an unchanged current generation for validation only;
- restore a failed-validation generation for bounded validation remediation;
- replay the latest safe checkpoint onto newer `main` and create a generation;
- continue one bounded helper-owned replay conflict; or
- invalidate stale authority and start from the exact remote PR head.

The caller no longer chooses between ordinary preparation, reviewed
continuation preparation, and remediation continuation preparation.

The result includes:

- generation ID and number;
- selected remote head;
- prepare-time base and prepared head;
- result such as `review-required`, `validation-only`,
  `validation-remediation`,
  `conflict-resolution-required`, or `prepared`;
- exact allowed conflict paths when applicable; and
- exact clean-head next helper action as a registered recipe ID plus typed
  substitutions.

Before synchronization, preparation requires exactly one canonical curation
report in the selected PR inventory. The prepared event records that path so
the returned checkpoint action authorizes the report that review may normalize,
without allowing the caller to choose a different report.

`prepared` and `review-required` generations, whether fresh or resumed, enter
the same complete normalization, inventory, review, and remediation flow. The
returned action is the **clean-review branch**: it may be invoked only after a
fresh clean exact-head review. If review requests changes, the explicit
**requested-changes branch** permits bounded local remediation followed by the
registered `checkpoint_curation_delta` recipe for the exact clean remediation
commit. The checkpoint helper validates the caller-created head, generation,
base, paths, report, and deterministic deltas before granting recovery
authority. After that checkpoint, a new fresh clean exact-head review is still
required before `checkpoint_curation_reviewed`. Codex therefore does not invent
a capability or mark a request-changes head as reviewed.

`validation-remediation` is narrower. It restores the unchanged reviewed head
after the final deterministic suite failed and authorizes correction only of
that concrete validation defect. Its returned `checkpoint_curation_delta`
action sets `caller_created_descendant_head=true`: the caller may replace only
the action's `${HEAD}` with the exact clean descendant commit produced by the
bounded correction. The PR, generation, report, prepare-time base, allowed
paths, remote head, and deterministic deltas remain helper-validated. The
corrected head must pass a fresh exact-head review and the normal reviewed
checkpoint before final validation can run again.

### `checkpoint curation`

`checkpoint curation` replaces `checkpoint remediation` and
`validate reviewed` as pre-push checkpoint capabilities. It accepts the exact
PR, generation, local head, report path, comparison-base checkout, and stage.

Allowed requested stages are:

- `delta-validated`; and
- `reviewed`.

The helper revalidates lease, remote PR head, generation identity, prepare-time
base, repository cleanliness, allowed paths, file modes, and the single
canonical report path before recording the checkpoint.

The capability is idempotent:

- the same completed request returns `already-completed`;
- an interrupted matching request resumes and returns `completed`;
- a request with different facts while a transaction is incomplete returns
  `local-recovery-required` and the exact matching next action; and
- an incompatible request against completed immutable generation facts returns
  `checkpoint-conflict`.

### `validate curation`

Final validation retains its existing trusted-base test boundary and broad
deterministic suite. It may run only for the latest reviewed checkpoint in the
current generation.

Success appends `validation_passed`, makes the generation eligible for the
existing push-journal authorization flow, and preserves the exact resulting
graph and report authority needed after push.

Failure appends `validation_failed` while retaining the reviewed checkpoint as
the remediation base. A later owned run on the unchanged selected head and
prepare-time base returns `validation-remediation`, restores that reviewed
head, and authorizes one bounded descendant correction through the typed delta
checkpoint action. The correction remains in the same generation but requires
a fresh exact-head review, reviewed checkpoint, and final validation. A
validation-only resume remains available only when validation never recorded a
failure. Replay onto newer `main` creates a new generation and requires the
normal full review flow.

### `inspect curation`

Inspection exposes one current pre-push generation per PR rather than separate
reviewed and remediation continuation inventories. It returns:

- current stage and exact head;
- whether a checkpoint transaction is incomplete;
- whether replay or validation is required;
- whether the generation is stale or invalid;
- a typed `retryable` boolean; and
- one registered `next_action` containing a recipe ID and authorized typed
  substitutions, never a shell command string.

Codex no longer reconstructs recovery priority between reviewed and remediation
objects.

## Local Checkpoint Transaction

Checkpoint persistence is a two-phase, idempotent local transaction:

1. Complete all pure preflight checks.
2. Append `checkpoint_started` with a deterministic transaction ID, exact
   generation, requested stage, head, report, expected refs, and validation
   base.
3. Create or verify the deterministic helper-owned refs.
4. Append `checkpoint_completed` with the verified refs.

Once `checkpoint_started` is durable, helper output must report
`mutation_occurred=true`, even though no external mutation occurred.

If execution stops after either persisted step, inspection exposes the exact
incomplete transaction. Repeating the registered command completes the same
transaction. It does not create another generation or another logical
checkpoint.

If the intended commit object is missing before refs can be restored, the
generation is not publishable. A later owned `prepare curation` appends an
invalidation event and restarts from current remote facts. It never reconstructs
semantic review from prose, automation memory, or an untrusted worktree.

## Error Contract

`invalid-command` is reserved for malformed command syntax, unsupported
arguments, or an unregistered recipe.

Operational failures use specific reasons:

- `stale-head`: the remote PR head changed;
- `stale-base`: the authorized prepare-time base moved or mismatched;
- `lease-conflict`: another run owns the operation;
- `checkpoint-conflict`: requested facts contradict completed generation facts;
- `local-recovery-required`: an incomplete local transaction must finish first;
- `validation-failed`: a classified deterministic check failed; its allowlisted
  check and failure kind are durable, while internal validator exceptions do not
  enter this state;
- `unsafe-repository`: paths, modes, refs, ancestry, or worktree state are
  unsafe; and
- `state-migration-required`: legacy pre-push state has not been archived.

Every pre-push error response includes:

- `mutation_occurred`;
- `retryable`;
- bounded stage and reason; and
- an exact `next_action` when retryable.

The maintainer skill may retry only when the helper returns `retryable=true`,
and then only by invoking the returned registered action after inspection. The
current blanket rule that all non-dispatch helper failures are terminal is
removed for pre-push local capabilities.

Immediate hard stops remain for:

- uncertain GitHub mutation;
- any unresolved push or terminal-publication journal;
- remote-head drift that invalidates the selected work;
- lease ownership conflict;
- unsafe or contradictory repository state; and
- helper output that cannot identify an exact registered next action.

Post-push and publication errors retain their existing fail-closed semantics.

## Legacy-State Migration

The new runtime uses an explicit state-format marker. It does not silently
interpret legacy reviewed/remediation records as generation authority.

A one-time registered migration capability will:

1. require no active curation lease;
2. take the private state transition mutex;
3. refuse migration while unresolved external-mutation recovery depends on
   legacy pre-push state;
4. move curation work, reviewed continuations, remediation continuations, and
   their helper refs to a timestamped owner-private archive;
5. leave discovery work, push journals, CI continuations, terminal-publication
   records, GitHub branches, and GitHub PRs unchanged;
6. write the new state-format marker atomically; and
7. return an inventory count without exposing private ref names.

Migration writes an archive manifest containing hashes and bounded counts of
the moved owner-private files and refs. Rollback is permitted only while no new
generation or external mutation authority has been created after migration.
Once generation-based work starts, rollback is forbidden; recovery proceeds
through the new state model instead.

The owner has explicitly accepted restarting unpublished pre-push review and
remediation work from current remote PR heads. Archived state is diagnostic
only and cannot be adopted by the new runtime.

Before migration, `inspect curation` returns
`state-migration-required` without mutating state. Migration is an explicit
activation step after repository code, runtime contract, and installed skill
are aligned.

## External Mutation Boundary

This design intentionally does not unify local checkpoints with irreversible
or ambiguous external side effects.

The existing push journal remains the sole authority once a validated head is
authorized for branch mutation. Existing post-push CI continuations and
terminal-publication intents retain their current meaning, ordering, recovery,
and hard-stop behavior.

The generation supplies immutable input to external mutation through two typed
values. `ReviewedCurationAuthority` contains the work ID, PR, branch, selected
remote head, prepare-time base, reviewed head, report path, guarded-sync facts,
and review timestamp. `ValidatedCurationAuthority` extends that exact authority
with the validated head, resulting graph, and validation timestamp. Ordinary
push requires validated authority; the existing exceptional manual-check path
requires reviewed authority and remains explicitly unvalidated. Existing
push-journal and CI code consumes these values rather than loading reviewed or
remediation continuation records. After the push journal becomes authoritative,
the generation is consumed. It cannot be independently resumed or used to
authorize another push.

## Decision And Review Gate

- Classification: review-gated, full design flow
- High-risk domains touched:
  - scheduled automation;
  - persistent recovery authority;
  - Git mutation preparation; and
  - publication safety boundaries
- Developer Decision Checkpoints:
  - resolved: archive and reset unpublished pre-push state instead of migrating
    active continuations;
  - resolved: limit redesign to pre-push curation;
  - resolved: use one generation timeline and one idempotent checkpoint
    capability;
  - accepted assumptions: existing post-push authority can remain unchanged
    behind a typed adapter from validated generations;
  - unresolved: none
- ADR status: required; add ADR 0020 before implementation
- Advisory design-review:
  - reviewers: backend-api, security-privacy, observability-ops
  - status: completed; storage bounds, structured next actions, validated
    authority handoff, and migration rollback boundary incorporated
- Advisory feature-review before final handoff:
  - reviewers: backend-api, security-privacy, observability-ops
  - status: planned

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Technical | Existing pre-push authority | Preserving old continuations requires compatibility transitions that would carry forward the current complexity | Preserve all; reset pre-push only; selectively import | Reset pre-push only | Cleanest model; repeats review once but leaves GitHub unchanged and preserves external recovery | This spec and ADR |
| Technical | Redesign scope | Rewriting post-push recovery would increase external-mutation risk and implementation scope | Pre-push only; entire lifecycle | Pre-push only | Directly addresses observed failures while retaining proven journal boundaries | This spec and ADR |
| Technical | Helper contract | Separate continuation types force Codex to select state-machine paths | Keep commands; unified checkpoint; derive primarily from Git refs | Unified checkpoint | Explicit stages remain auditable while persistence and retry become simpler | Runtime command contract |

## Architecture Decisions

- Durable decisions:
  - one generation timeline is the sole pre-push cross-run authority;
  - generation history is append-only;
  - local checkpoint writes are two-phase and idempotent;
  - helper responses own retry eligibility and exact next actions;
  - external mutation recovery remains separately journaled and fail-closed; and
  - legacy unpublished pre-push progress is archived, not migrated.
- ADRs needed: add ADR 0020 to supersede ADR 0011's separate
  reviewed/remediation-continuation decision while preserving its local control
  plane and external-journal decisions.
- Existing constraints: helper-only branch mutation/publication, exact-head
  authority, no automatic approval or merge, and untrusted semantic input all
  remain.
- Revisit criteria:
  - discovery needs cross-run local checkpoints;
  - post-push recovery shows equivalent state-fragmentation failures; or
  - multiple concurrent maintainers require stronger distributed ownership.

## API And Client Contract

- Public backend and frontend contracts: unchanged.
- Maintainer CLI contract: intentionally changed for pre-push curation.
- Compatibility: no compatibility promise for unpublished owner-private
  pre-push state; explicit archival migration is required.
- Installed skill: must be updated only after the merged repository contract is
  available in the automation worktrees.

## Data Trust And Source Integrity

Catalog evidence, report reconciliation, graph-scope review, and source-trust
rules are unchanged. A local checkpoint records mechanical authority only. It
does not turn report prose, a finding ledger, or automation memory into source
truth.

## AI / LLM Use

- Timeline transitions, validation, retries, refs, leases, and publication
  gates are deterministic.
- Codex continues to own semantic catalog review and remediation decisions.
- No LLM output can widen helper scope or synthesize checkpoint authority.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| Scheduled or manual maintainer cycle | Review and remediate one curation PR | Local Codex curation maintainer | Uses generation inspection and helper-provided next action |
| One-time owner activation | Archive legacy pre-push authority | Maintainer state migration capability | Must run before the first generation-based curation cycle |

## Security, Privacy, And Abuse

- All timelines, archives, leases, and refs remain owner-private local state.
- Reports, PR prose, web evidence, and automation memory remain untrusted.
- Timeline fields and helper errors must not include credentials, raw source
  bodies, private review prose, or environment values.
- The migration capability may move only recognized helper-owned paths and
  refs under the private state root.
- No new dependency or network service is introduced.

## Observability And Operations

Triage and the private run index should record:

- PR and remote head;
- generation number and bounded stage;
- whether the cycle started, resumed, replayed, or invalidated a generation;
- helper reason, retryability, and last successful stage;
- whether a local or GitHub mutation occurred; and
- whether a recovery obligation remains.

They must not record private ref names, lease IDs, raw evidence, or helper
implementation details.

The migration command should print a bounded archive summary and the required
next action. A runbook section must cover migration, inspection, safe retry,
and rollback before schedules are re-enabled.

## Acceptance Criteria

- One typed timeline replaces reviewed and remediation continuation authority
  for pre-push curation.
- The helper never rejects a legitimate newer-base generation merely because
  the remote PR head is unchanged.
- Repeating an identical checkpoint command is successful and idempotent.
- Interrupted local checkpoint transactions are surfaced and resumable through
  one exact helper action.
- `mutation_occurred` becomes true as soon as a checkpoint-started event is
  persisted.
- `invalid-command` is not used for state or validation conflicts.
- Inspection exposes one current generation and one next action per PR.
- Prepared and review-required generations use the full semantic flow; a clean
  review uses the reviewed checkpoint, while requested changes use the delta
  checkpoint before a fresh review.
- Final validation still executes only trusted exact-base tests and hands off
  only an exact reviewed head to the existing push journal.
- Migration archives only legacy pre-push state and leaves all external
  recovery authority and GitHub state unchanged.
- The installed skill and runtime contract contain no legacy pre-push command
  recipes after activation.
- The maintainer still cannot approve or merge.

## Verification

### Model And State Tests

- strict Pydantic validation for timelines, generations, and events;
- monotonically ordered generations and events;
- immutable prior events;
- exactly one current generation;
- valid stage/head relationships; and
- atomic timeline writes and state-format marker validation.

### Command Tests

- first preparation creates generation one;
- unchanged preparation resumes the latest safe stage;
- newer `main` creates generation two even when the remote PR head is unchanged;
- changed remote PR head invalidates old authority and starts cleanly;
- repeated identical checkpoint returns `already-completed`;
- several delta-validation/review rounds remain in one generation;
- reviewed and final-validation stages require the latest exact head;
- stale head, stale base, lease conflict, checkpoint conflict, and unsafe
  repository return their typed reasons;
- helper output provides a registered next action only when retryable; and
- final validation hands the exact generation facts to unchanged push-journal
  code.

### Fault-Injection Tests

- interruption after `checkpoint_started` and before ref creation;
- interruption after ref creation and before `checkpoint_completed`;
- retry after either interruption completes the same transaction;
- missing intended Git object invalidates local generation authority without
  touching GitHub;
- interruption while superseding a generation leaves one reconstructable
  current projection; and
- no local checkpoint failure can incorrectly report
  `mutation_occurred=false` after persisted state or ref mutation.

### Migration Tests

- migration refuses an active curation lease;
- migration refuses unsafe external-recovery dependencies;
- recognized legacy pre-push files and refs are archived;
- discovery and external recovery state remain byte-identical;
- rerunning migration is idempotent; and
- pre-migration inspection is read-only and returns
  `state-migration-required`.

### Operational Smoke

1. Pause the curation automation.
2. Inspect both workers and resolve any external recovery obligation.
3. Run the explicit legacy-state archival migration.
4. Verify discovery and post-push state inventories are unchanged.
5. Run one manual curation cycle on an open PR.
6. Interrupt and resume one local checkpoint in a disposable state directory.
7. Re-enable the curation schedule only after contract and installed-skill
   inspection agree.

## Alternatives Considered

### Keep Existing Commands And Refactor Internals

This minimizes command-contract churn but leaves Codex responsible for choosing
between reviewed and remediation concepts. It reduces persistence complexity
without removing the orchestration ambiguity that contributed to prior
failures.

### Derive Authority Primarily From Git Refs

This reduces JSON state but makes generation ordering, incomplete transactions,
and corruption diagnosis harder. Git refs remain recovery material, while the
typed timeline remains the clearer source of current local authority.

### Unify The Entire Pre-Push And Post-Push Lifecycle

This could produce one conceptual model, but it would rewrite proven recovery
around ambiguous GitHub mutations. The expected reliability benefit is in
pre-push local state, so the larger external-risk change is not justified.

## Advisory Review

- Design reviewers: backend-api, security-privacy, observability-ops
- Feature reviewers: backend-api, security-privacy, observability-ops
- Known residual risks:
  - the timeline remains a state machine, so transition code must stay small
    and projection-based;
  - explicit migration adds one owner activation step; and
  - post-push state remains separate and may merit its own later simplification
    only if equivalent failures appear.

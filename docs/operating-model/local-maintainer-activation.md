# Local Maintainer Post-Merge Activation And Rollback

## Status And Authority

This is the authoritative reactivation and rollback procedure for the
simplified local Snowcast maintainer. Repository implementation itself does not
install a personal skill, create schedules, provision labels, or enable
automation.

The earlier simplified maintainer may remain locally active, but the
convergence-and-regional-completion amendment is not active while its repository
changes are unmerged. Every activation or reactivation is post-merge,
owner-controlled, and review-gated. Do not copy executable instructions from a
feature branch, superseded plan, or stale installed skill.

## Preconditions

- The exact reviewed implementation PR head is present in current local and
  remote `main`.
- The implementation PR and required CI are green.
- The owner is operating the Snowcast project-scoped `lampssy` GitHub CLI
  profile; no token values or scopes are written to durable output.
- `~/.local/state/snowcast-maintainer` is preserved if it already exists.
- No unresolved push journal is ignored or deleted.
- Both existing schedules are paused before replacing any shared installed
  skill or automation prompt. Wait for an active lease or journal to settle;
  do not force-clear it as part of cutover.

## Activation Order

1. Pause both schedules. Inspect curation and discovery recovery state and let
   any active lease or journal finish through the currently merged helper.
2. Verify the exact PR head was merged to current `main`. Record the PR number,
   reviewed head, merge commit, and current `main` head in the post-merge review.
3. Snapshot the existing installed maintainer, review, and curation skills plus
   both automation prompts and records. The snapshot is rollback material, not
   workflow authority.
4. Replace all affected shared skills and both prompts from the same merged
   contract while schedules remain paused. Remove candidate- or PR-specific
   migration wording; keep model, working directory, cadence, proposal cap,
   labels, and configured active-state defaults unchanged.
5. Inspect the exact installed artifacts, then run read-only smoke checks:
   - verify `codex login status` without exposing credentials;
   - verify the project-scoped GitHub profile is the active `lampssy` account;
   - run `inspect curation` and `inspect discovery` against merged code;
   - confirm inspection does not create a missing state directory or mutate
     GitHub;
   - verify adversarial PR, backlog, source-page, and finding-ledger text cannot
     alter fixed helper commands or publication boundaries.
6. Acquire the appropriate lease and run `publish ensure-labels` once. Inspect
   the bounded outcome and the resulting allowlisted GitHub labels. In a
   `finally` path, release the lease with the exact returned run ID if and only
   if acquisition succeeded.
7. Inspect the installed skill and the actual automation records. Verify repo,
   working directory, schedule, prompt, skill reference, project-scoped GitHub
   profile, and that no credential content is embedded.
8. Run disabled/manual curation and discovery smoke cycles. Confirm curation can
   distinguish reviewed, remediation, and ordinary recovery, and discovery uses
   regional backlog work before external scanning without changing GitHub unless
   the helper authorizes the exact mutation.
9. Run post-merge AI/LLM reliability, security/privacy,
   release/change-management, and observability/ops review against the installed
   skill and real automation records. Resolve Blocker/High findings and record
   accepted residual findings.
10. Enable schedules only after explicit owner approval. Enable one schedule at
   a time, inspect its first bounded Triage outcome, then enable the other.

## Required Personal Skill Contract

The installed skill must:

- inspect unresolved journals before fresh selection; recover exactly one
  matching journal first and escalate multiple journals;
- use curation recovery priority `journal -> reviewed continuation ->
  remediation continuation -> ordinary PR`, never skipping exact private
  recovery in favor of a fresh semantic cycle;
- consume the helper's curation recovery continuation before choosing a state:
  `validated` may use current CI/readiness facts, `absent` must never request
  waiting-CI or ready and instead publishes the honest reviewed-only pause,
  while `unknown` stops without guessing or probing lifecycle capabilities;
- resume any yielded orchestration cell, then poll every long-running helper
  command's underlying session through process exit, accumulate all output
  chunks, and parse helper JSON only after completion instead of retrying a
  still-running mutation;
- inspect and choose at most one safe curation PR;
- prefer an exact resumable reviewed continuation for the selected PR, then an
  exact resumable remediation continuation, over an automation-memory-only
  unpublished follow-up; an unresolved push journal still has global priority;
- treat remediation as recovery authority only. Resume it through the helper,
  require one fresh bounded independent review, and never infer review,
  validation, publication, or readiness from its delta checkpoint;
- read curation automation memory using `CODEX_HOME` or the `$HOME/.codex`
  fallback, revalidate any unpublished-follow-up PR/head against helper
  inspection, and prioritize the oldest still-exact eligible follow-up before
  unrelated fresh work without reusing old review or mutation authority;
- acquire curation before prepare and hold the lease through publication;
- keep preparation schema-independent, but before initial review run one
  maintainer-managed structural normalization pass when the single report is
  legacy, malformed, graph-less after refresh, incomplete, or non-reconciling;
  use the exact prepared base/current catalog and trust snapshots to rebuild
  exactly one canonical schema-v3 report. Validate those snapshots before edit
  and stop without edits if either fails; assert catalog/trust object IDs remain
  identical and locally commit a diff containing only that report path. Do not
  claim semantic resolution or consume a remediation cycle; catalog/trust
  changes begin only after the dual-review ledger as ordinary remediation. A
  finalized report requires a non-empty evidence envelope and graph impact on
  every scope assessment; each `regional_followup` must point to an exact
  heading that exists in the exact-head product backlog. The helper checks only
  anchor existence, never backlog meaning, priority, or status;
- after each remediation, call the helper's two-command delta checkpoint once:
  this is the bounded delta validation of catalog/trust plus exact
  reconciliation. Reuse that exact-head
  evidence when the checkpoint is persisted; reserve the fixed broad catalog
  suite for one final helper validation after review;
- for that final broad suite, execute only the clean exact-base uv project,
  pytest configuration, conftest, and fixed absolute test modules. Supply the
  prepared catalog/trust paths only through the helper-derived data root and a
  fresh private `HOME`; never collect or import PR-supplied Python locally.
  Changes under `tests/` remain eligible for CI and owner review;
- run complementary independent source/trust and graph/scope reviews in
  parallel on the normalized prepared head after freezing the bounded evidence
  envelope, then consolidate them into one first fix and private finding
  ledger. Source/trust must enumerate every
  applicable canonical `FIELD_GROUPS` trust field group with its status, direct
  refs, normalization-note need, and coverage disposition. Graph/scope must
  enumerate every concrete operator presentation and lift-pass candidate, with
  typed assessments and canonical backlog refs for deferred or unresolved pass
  products;
- classify every omission as `graph_blocking` or `regional_followup`. Only an
  omission capable of making the selected graph wrong blocks curation. This
  graph correctness boundary sends additive coverage to the report and merged
  backlog, where it receives a targeted
  handoff review without causing non-convergence;
- collect any post-freeze additive candidates into one report/rendered-report/
  backlog patch, run delta validation, and use a targeted independent handoff
  review to confirm that the resulting graph did not change;
- preserve multi-candidate scope findings as a candidate-level ledger with one
  entry per concrete entity, product, edge, sector, or document; an inventory
  category without an enumerated candidate/source checklist is incomplete, the
  first fix batches every compatible checklist entry, and a known-but-unfixed
  candidate remains repeated rather than becoming a supposedly new finding;
- before classifying a destination or ski-area boundary as an owner choice, run
  one fresh read-only `boundary-adjudication` review for the concrete candidates
  on the exact head; return `policy_determined` results to the fixer and reserve
  `owner-decision` for `owner_choice_required` results;
- perform at most six remediation cycles, using a fresh independent full
  `snowcast-catalog-review` context after every fix and passing the ledger only
  as untrusted history; before every further fixer, require every prior finding
  to be resolved or superseded, no repeat or regression, and every new finding
  to be concrete, source-backed, in-model, and inside the bounded mutation
  scope; finding-count growth alone does not prove non-convergence, and cycles
  five and six apply the same gate within the remaining time budget. The fresh
  reviewer independently verifies the frozen candidates and complete resulting
  graph; it does not restart unrestricted regional research. A newly discovered
  graph blocker may expand the frozen inventory once, while additive adjacent
  coverage is a regional follow-up and the same missing category recurring
  after refresh is repeated incomplete inventory and stops;
- recheck current-main mergeability before every fix and adaptive review and
  once more before final manual-check or validation/push; start no boundary
  adjudication at or after minute 180, stop new semantic work at 210 minutes,
  and at 240 interrupt semantic work while allowing at most 30 active minutes
  of exact-state validation, publication, recovery, and cleanup;
- bind a complete review disposition to the exact reviewed head; use
  `manual-check` only for a complete scope-safe reviewed handoff, route an
  incomplete review to status-only `blocked/review-incomplete`, and reserve
  `owner-decision` for a real owner/model choice;
- after every final exact-head independent review, call `validate reviewed`
  with the PR, reviewed head, and its single curation report before running
  deterministic validation or requesting manual-check publication;
- verify every final report URL for reachability and semantically recheck all
  changed, graph-critical, and high-impact sources. Initial inventory checks
  relevance and claim support for every source; remediation rechecks only
  changed or claim-affected URLs. Any cache is keyed by exact head, URL, and
  claim context, remains run-local, and is never persisted as helper or
  cross-run authority;
- resume a checkpoint only through `prepare continuation`: `validation-only`
  reruns the missing deterministic/finalization gates without semantic review,
  while `review-required` receives exactly one fresh independent full review
  before a new `validate reviewed` checkpoint;
- when continuation preparation returns `conflict-resolution-required`, edit
  only the helper-returned catalog/report/backlog/focused-test paths through
  `snowcast-catalog-curation` in `maintainer-managed` mode, call
  `prepare continuation --continue-conflict`, and then run exactly one fresh
  independent full review; stop on remote drift, a disallowed or unrelated
  path, a repeated conflict, missing checkpoint refs, or unsafe Git state;
- treat the push journal as the sole recovery authority after the helper
  authorizes it; never attempt to resume or recreate the consumed local
  continuation once a journal exists;
- use the helper's explicit `publish manual-check` capability to preserve a
  mechanically valid, scope-safe reviewed head when the cycle or semantic-time
  bound is reached with remaining findings that are only bounded in-model work;
  never push it directly or represent it as validated; an unresolved or moved
  prior finding, repeat, regression, repeatedly incomplete inventory, incomplete
  review, or unsafe scope remains status-only blocked;
- before any safe terminal status for an unpublished mechanically valid local
  head, retain its remediation continuation. A blocked or owner-hold label
  prevents scheduled resumption but does not invalidate the checkpoint;
- use `publish outcome` for safe PR-specific terminal conflict, CI, deadline,
  non-convergence, validation, review-incomplete, or owner-decision stops; bind
  it to the exact unchanged remote head, update only the lifecycle label and
  canonical comment, and keep its outcome record separate from review evidence;
- use discovery order `journal recovery -> preferred retry -> merged regional
  completion -> other active backlog -> bounded external official-source scan`;
  interpret selection read-only before acquisition, then acquire discovery,
  rerun inspection, and mutate at most one candidate;
- treat a structured helper `lock-busy` result as a normal no-op without
  inspecting the active owner's record, retrying acquisition, or attempting
  release when no lease was acquired;
- preserve a viable source-validated discovery candidate as a bounded
  preferred-retry hint before lease acquisition, retain it across `lock-busy`
  or interruption, then revalidate and prioritize it on the next discovery run
  before new backlog or external research;
- make Catalog Curation Refinements backlog-first through ordinary semantic
  prose and bounded slices, without a deterministic parser. Each regional
  proposal has exactly one primary stay destination matching its candidate and
  the applicable bases, access, ski-area/pass ownership, weather/migration
  implications, complete source families and dispositions, canonical graph,
  exclusions, backlog anchor, caveats, owner decisions, and rollback;
- use GitHub proposal identity and the merged schema-v3 report as durable
  proposal authority. The proposal marks its backlog item `proposed`. After the
  owner accepts it by removing the proposal label, normal curation on that same
  PR must mark the item `completed`, or narrow it to the remaining gaps and mark
  the next slice `active`, before readiness and owner merge. Preferred-retry
  memory remains an untrusted revalidated hint;
- allow existing-model boundary, stable-ID, and weather-owner changes to reach
  an owner-gated decision-bearing proposal with explicit historical-data,
  migration/backfill, merge-order, and rollback handoff, while keeping database
  migrations, schema changes, and production code outside the lane;
- permit an old-key removal only as an explicit same-kind replacement with a
  full old-target review, identity deletion, unresolved scope assessment,
  backlog reference, and caveat; reject unrelated removals;
- invoke `snowcast-catalog-curation` only in explicit `maintainer-managed` mode
  inside the provided isolated worktree, with that sub-skill yielding branch,
  commit, helper validation, and publication ownership back to the maintainer;
- heartbeat before and after capabilities and at least every five minutes while
  holding a lease;
- treat a lease as stale after one hour without a heartbeat, preserving its
  archived owner record and fencing the interrupted run during takeover;
- release its lease in a `finally` path with the exact run ID if and only if
  acquisition succeeded;
- request semantic states while relying on helper gates for proposal,
  waiting-CI, and ready;
- allow bounded multi-line Markdown in canonical summaries while retaining
  private-file containment, byte/UTF-8 limits, and rejection of unsafe controls
  or reserved maintainer markers;
- create every trusted title, body, and summary through lease-bound
  `publication-input create`, supplying bounded UTF-8 on stdin and retaining
  only its random mode-`0600` direct-child basename; never supply a source path
  or print the publication text;
- write a concise current PR-body synopsis for every waiting-CI or ready
  request, including recovery and lightweight readiness runs, and explicitly
  adopt an unmarked legacy body only through the helper's `--adopt-body`
  permission;
- tolerate bounded GitHub PR-head propagation only after an exact journaled
  push: retry for at most 15 seconds while Git shows the new head and GitHub
  still shows exactly the journaled old head, but stop immediately on any third
  head;
- report the bounded Triage outcome for every terminal or no-op result without
  exposing the private lease run ID;
- append one owner-private mode-`0600` bounded diagnostic JSON row per completed
  run with explicit `started_at` and `completed_at` timestamps, selected item,
  heads, cycles, last stage, helper reason, mutation flag, elapsed time, and
  recovery obligation; never include a lease ID or treat this index as workflow
  authority;
- never push or publish outside the helper; and
- never approve or merge.

## Schedule Health Inspection

The owner-private diagnostic indexes are:

```text
${CODEX_HOME:-$HOME/.codex}/automations/snowcast-catalog-pr-maintainer/run-index.jsonl
${CODEX_HOME:-$HOME/.codex}/automations/snowcast-catalog-discovery/run-index.jsonl
```

They are mode `0600` operational evidence only. Compare their latest bounded
start/completion facts with Codex automation history; never infer workflow
authority from a row. Expected cadence remains four curation starts per local
day and discovery starts on Monday, Wednesday, and Friday.

Treat curation schedule delivery as stale when no start is visible for 12 hours.
Treat discovery as stale when the next scheduled weekday passes by 24 hours
without a start. Treat either worker as possibly crashed before cleanup when its
latest start has no terminal completion after five hours and no currently
healthy lease-owned run explains it. A missing index plus no automation-history
start is `never-started`, not a successful no-op. Diagnose with read-only
automation history and `inspect curation` / `inspect discovery`; do not expose
or copy lease IDs into Triage or diagnostic rows, and do not clear private state
manually.

## First-Run Acceptance

For each schedule, confirm:

- a no-work run is a bounded no-op, not an error or mutation;
- `lock-busy` is reported directly as a bounded no-op and a viable interrupted
  discovery candidate is available for preferred retry;
- an interrupted source-validated discovery selection remains a preferred
  retry even when interruption occurs before or after lease acquisition;
- wrong-worker or multiple-journal recovery fails before lease acquisition;
- heartbeat and finally-style release use the exact returned run ID;
- a lost first output chunk from a long helper command is recovered by polling
  the original process, not by repeating the capability;
- a competitor remains blocked before 60 minutes without a heartbeat and may
  perform a fenced stale takeover at 60 minutes;
- PR prose, sources, subprocess output, environment values, and credentials do
  not appear in helper output;
- discovery respects the three-open-proposal cap and unknown-identity stop;
- discovery prioritizes preferred retry, merged regional completion, and other
  active backlog candidates before unrelated external research;
- one backlog-origin proposal has exactly one matching primary destination and
  a coherent multi-entity graph; re-keying, weather migration, and owner choices
  are flagged rather than represented as resolved;
- after the owner accepts that proposal by removing its proposal label, normal
  curation on the same PR updates the backlog item to `completed`, or narrows it
  and marks the next slice `active`, before readiness and owner merge;
- a curation cycle with no GitHub mutation remains a semantic follow-up in
  automation memory and is selected first on the next run only while its exact
  PR/head remains eligible;
- a deterministic validation failure leaves an exact resumable continuation,
  and a successor run on the same prepare-time base returns `validation-only`
  without repeating semantic review;
- a delta-validated but not yet reviewed local head leaves a remediation
  continuation, resumes as `review-required`, and survives a safe blocked/hold
  outcome until deliberate label removal;
- clean movement of `main` replays the one reviewed squash and returns
  `review-required`; exactly one fresh full review is completed before any new
  validation or publication;
- an allowlisted replay conflict returns only its bounded paths, survives an
  interrupted attempt by being recreated from immutable refs in a clean
  successor worktree, and reaches `review-required` only after helper-owned
  completion;
- remote PR-head drift, missing/tampered checkpoint refs, a disallowed conflict,
  or an unrelated staged file stops without push; and
- push authorization consumes the continuation before external mutation, after
  which inspection and recovery expose only the matching push journal;
- multi-paragraph owner-decision and blocked summaries publish successfully,
  while unsafe controls and reserved comment markers still fail closed;
- proposal validation accepts an explicitly reported same-kind re-key but still
  rejects an unrelated or incompletely reported catalog deletion;
- proposal validation accepts a candidate present only in its proposal head,
  while validation and publication reject it if freshly fetched canonical
  `main` or an open GitHub proposal already contains the same candidate key;
- curation readiness is tied to the unchanged reviewed, validated, pushed,
  CI-green, mergeable head; and
- a pressure scenario where two prior findings are verified resolved and three
  concrete, source-backed, in-model, bounded findings are newly discovered
  continues when cycle and time remain; raw count growth alone does not stop it;
- a repeated, regressed, unresolved, or moved prior finding and repeatedly
  incomplete inventory stop as non-converging instead of authorizing another
  fix;
- reaching six cycles or the 210-minute new-work cutoff with a mechanically
  valid, scope-safe, exact reviewed head and remaining findings that are only
  bounded in-model work runs `validate reviewed` and preserves the head through
  `manual-check`; an unsafe, incomplete, or unreviewed head is not pushed;
- each remediation runs only the two delta commands, and the reviewed final head
  runs the broad validation plus a fresh all-URL reachability sweep and semantic
  recheck of changed or graph-critical sources;
- the broad local pytest stage ignores modified PR conftest/test modules and PR
  pytest configuration, runs the fixed modules from the verified exact base,
  reads the prepared catalog/trust data, and cannot access the user's `HOME`;
- boundary adjudication stops spawning at minute 180, semantic work stops
  spawning at minute 210, active semantic contexts are interrupted at minute
  240, and only the separate 30-active-minute finalization allowance follows;
- the installed skill and automation prompts contain no obsolete minute-120
  boundary cutoff, 150-minute semantic cutoff, 180-minute hard deadline, or old
  fewer/lower/narrower and non-narrowing-count convergence rule;
- a legacy, malformed, graph-less refreshed, incomplete, or non-reconciling
  report is normalized before initial dual review, without consuming a
  remediation slot, while canonical intent still rejects it until that commit;
- no action approves or merges a PR.

## Rollback

1. Pause or disable both schedules before any diagnosis.
2. Preserve the private state directory, owner record, stale-lock archives,
   work records, reviewed/remediation continuations, push journals, and backup
   refs. Do not edit or delete them.
3. Inspect both inventories and Codex Triage. Recover an irreversible operation
   only through the merged helper; multiple journals require owner review.
4. Restore the snapshotted installed skills and both prompts atomically while
   schedules remain paused. Do not re-enable an older orchestrator while an
   active remediation continuation exists; recover or explicitly invalidate it
   with the helper version that created it first.
5. Revert the repository helper through normal Git history and a reviewed PR.
   Do not use plain `git push --force` and do not execute the superseded Task 10.
6. Keep schedules disabled until the reverted or corrected merged version has
   passed the same post-merge review and the owner explicitly re-approves
   enablement.

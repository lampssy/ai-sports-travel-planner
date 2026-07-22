# Local Maintainer Post-Merge Activation And Rollback

## Status And Authority

This is the authoritative reactivation and rollback procedure for the
simplified local Snowcast maintainer. Repository implementation itself does not
install a personal skill, create schedules, provision labels, or enable
automation.

Initial activation was completed after the implementation merged to `main` and
the owner approved both schedules. Every future reactivation remains
review-gated. Do not copy executable instructions from the superseded
local-maintainer plan or spec.

## Preconditions

- The exact reviewed implementation PR head is present in current local and
  remote `main`.
- The implementation PR and required CI are green.
- The owner is operating the Snowcast project-scoped `lampssy` GitHub CLI
  profile; no token values or scopes are written to durable output.
- `~/.local/state/snowcast-maintainer` is preserved if it already exists.
- No unresolved push journal is ignored or deleted.

## Activation Order

1. Verify the exact PR head was merged to current `main`. Record the PR number,
   reviewed head, merge commit, and current `main` head in the post-merge review.
2. Install the simplified personal `snowcast-maintainer` skill from the reviewed
   merged specification. The skill must implement the contract below; do not
   reuse the superseded skill draft.
3. Run read-only smoke checks before provisioning or scheduling:
   - verify `codex login status` without exposing credentials;
   - verify the project-scoped GitHub profile is the active `lampssy` account;
   - run `inspect curation` and `inspect discovery` against merged code;
   - confirm inspection does not create a missing state directory or mutate
     GitHub.
4. Acquire the appropriate lease and run `publish ensure-labels` once. Inspect
   the bounded outcome and the resulting allowlisted GitHub labels. In a
   `finally` path, release the lease with the exact returned run ID if and only
   if acquisition succeeded.
5. Create the curation schedule (four local runs per day) and discovery schedule
   (Monday, Wednesday, Friday) in a disabled state when Codex App supports it.
   If disabled creation is unavailable, create neither schedule until the owner
   is ready to enable both deliberately.
6. Inspect the installed skill and the actual automation records. Verify repo,
   working directory, schedule, prompt, skill reference, project-scoped GitHub
   profile, and that no credential content is embedded.
7. Run post-merge AI/LLM reliability, security/privacy,
   release/change-management, and observability/ops review against the installed
   skill and real automation records. Resolve Blocker/High findings and record
   accepted residual findings.
8. Enable schedules only after explicit owner approval. Enable one schedule at
   a time, inspect its first bounded Triage outcome, then enable the other.

## Required Personal Skill Contract

The installed skill must:

- inspect unresolved journals before fresh selection; recover exactly one
  matching journal first and escalate multiple journals;
- consume the helper's curation recovery continuation before choosing a state:
  `validated` may use current CI/readiness facts, `absent` must never request
  waiting-CI or ready and instead publishes the honest reviewed-only pause,
  while `unknown` stops without guessing or probing lifecycle capabilities;
- resume any yielded orchestration cell, then poll every long-running helper
  command's underlying session through process exit, accumulate all output
  chunks, and parse helper JSON only after completion instead of retrying a
  still-running mutation;
- inspect and choose at most one safe curation PR;
- prefer an exact resumable `reviewed_continuations` entry for the selected PR
  over an automation-memory-only unpublished follow-up; an unresolved push
  journal still has global priority;
- read curation automation memory using `CODEX_HOME` or the `$HOME/.codex`
  fallback, revalidate any unpublished-follow-up PR/head against helper
  inspection, and prioritize the oldest still-exact eligible follow-up before
  unrelated fresh work without reusing old review or mutation authority;
- acquire curation before prepare and hold the lease through publication;
- keep preparation schema-independent, but before initial review run one
  maintainer-managed structural normalization pass when the single report is
  legacy, malformed, graph-less after refresh, incomplete, or non-reconciling;
  use the exact prepared base/current catalog and trust snapshots to rebuild
  and locally commit exactly one canonical schema-v3 report without claiming
  semantic resolution or consuming a remediation cycle;
- during normalization and remediation, run catalog validation, exact
  reconciliation, and finding-related focused tests; reserve the fixed broad
  catalog suite for final helper validation;
- run complementary independent source/trust and graph/scope reviews in
  parallel on the normalized prepared head, then consolidate them into one
  first fix and private finding ledger. Source/trust must enumerate every
  applicable canonical `FIELD_GROUPS` trust field group with its status, direct
  refs, normalization-note need, and coverage disposition. Graph/scope must
  enumerate every concrete operator presentation and lift-pass candidate, with
  typed assessments and canonical backlog refs for deferred or unresolved pass
  products;
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
  as untrusted history; cycles five and six require demonstrable convergence;
- recheck current-main mergeability before every fix and adaptive review and
  once more before final manual-check or validation/push; start no boundary
  adjudication at or after minute 120, stop new semantic work at 150 minutes,
  and at 180 interrupt semantic work while allowing at most 30 active minutes
  of exact-state validation, publication, recovery, and cleanup;
- bind a complete review disposition to the exact reviewed head; use
  `manual-check` only for a complete scope-safe reviewed handoff, route an
  incomplete review to status-only `blocked/review-incomplete`, and reserve
  `owner-decision` for a real owner/model choice;
- after every final exact-head independent review, call `validate reviewed`
  with the PR, reviewed head, and its single curation report before running
  deterministic validation or requesting manual-check publication;
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
  scope-safe unresolved reviewed head; never push it directly or represent it
  as validated;
- use `publish outcome` for safe PR-specific terminal conflict, CI, deadline,
  non-convergence, validation, review-incomplete, or owner-decision stops; bind
  it to the exact unchanged remote head, update only the lifecycle label and
  canonical comment, and keep its outcome record separate from review evidence;
- interpret backlog and external research read-only before discovery
  acquisition, then acquire discovery, rerun inspection, and mutate at most one
  candidate;
- treat a structured helper `lock-busy` result as a normal no-op without
  inspecting the active owner's record, retrying acquisition, or attempting
  release when no lease was acquired;
- preserve a viable source-validated discovery candidate as a bounded
  preferred-retry hint before lease acquisition, retain it across `lock-busy`
  or interruption, then revalidate and prioritize it on the next discovery run
  before new backlog or external research;
- make Catalog Curation Refinements backlog-first through explicit candidate
  statuses and bounded slices, using external discovery only when none can
  advance;
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
  run with selected item,
  heads, cycles, last stage, helper reason, mutation flag, elapsed time, and
  recovery obligation; never treat this index as workflow authority;
- never push or publish outside the helper; and
- never approve or merge.

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
- discovery prioritizes preferred retry and bounded backlog candidates before
  unrelated external research;
- a curation cycle with no GitHub mutation remains a semantic follow-up in
  automation memory and is selected first on the next run only while its exact
  PR/head remains eligible;
- a deterministic validation failure leaves an exact resumable continuation,
  and a successor run on the same prepare-time base returns `validation-only`
  without repeating semantic review;
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
- a legacy, malformed, graph-less refreshed, incomplete, or non-reconciling
  report is normalized before initial dual review, without consuming a
  remediation slot, while canonical intent still rejects it until that commit;
- no action approves or merges a PR.

## Rollback

1. Pause or disable both schedules before any diagnosis.
2. Preserve the private state directory, owner record, stale-lock archives,
   work records, push journals, and backup refs. Do not edit or delete them.
3. Inspect both inventories and Codex Triage. Recover an irreversible operation
   only through the merged helper; multiple journals require owner review.
4. Remove the installed personal skill if its prompt or behavior is implicated.
5. Revert the repository helper through normal Git history and a reviewed PR.
   Do not use plain `git push --force` and do not execute the superseded Task 10.
6. Keep schedules disabled until the reverted or corrected merged version has
   passed the same post-merge review and the owner explicitly re-approves
   enablement.

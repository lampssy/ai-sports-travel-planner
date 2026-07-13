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
- inspect and choose at most one safe curation PR;
- read curation automation memory using `CODEX_HOME` or the `$HOME/.codex`
  fallback, revalidate any unpublished-follow-up PR/head against helper
  inspection, and prioritize the oldest still-exact eligible follow-up before
  unrelated fresh work without reusing old review or mutation authority;
- acquire curation before prepare and hold the lease through publication;
- run complementary independent source/trust and graph/scope reviews in
  parallel on the initial prepared head, then consolidate them into one first
  fix and private finding ledger;
- perform at most six remediation cycles, using a fresh independent full
  `snowcast-catalog-review` context after every fix and passing the ledger only
  as untrusted history; cycles five and six require demonstrable convergence;
- recheck current-main mergeability before every fix and adaptive review and
  once more before final manual-check or validation/push, stop new semantic work
  at 150 minutes, and enforce a cleanup-only hard stop at 180;
- bind a complete review disposition to the exact reviewed head; use
  `manual-check` only for a complete scope-safe reviewed handoff, route an
  incomplete review to status-only `blocked/review-incomplete`, and reserve
  `owner-decision` for a real owner/model choice;
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
- preserve a viable discovery candidate interrupted only by `lock-busy` as a
  bounded preferred-retry hint, then revalidate and prioritize it on the next
  discovery run before new backlog or external research;
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
- release its lease in a `finally` path with the exact run ID if and only if
  acquisition succeeded;
- request semantic states while relying on helper gates for proposal,
  waiting-CI, and ready;
- allow bounded multi-line Markdown in canonical summaries while retaining
  private-file containment, byte/UTF-8 limits, and rejection of unsafe controls
  or reserved maintainer markers;
- write a concise current PR-body synopsis for every waiting-CI or ready
  request, including recovery and lightweight readiness runs, and explicitly
  adopt an unmarked legacy body only through the helper's `--adopt-body`
  permission;
- report the bounded Triage outcome for every terminal or no-op result without
  exposing the private lease run ID;
- never push or publish outside the helper; and
- never approve or merge.

## First-Run Acceptance

For each schedule, confirm:

- a no-work run is a bounded no-op, not an error or mutation;
- `lock-busy` is reported directly as a bounded no-op and a viable interrupted
  discovery candidate is available for preferred retry;
- wrong-worker or multiple-journal recovery fails before lease acquisition;
- heartbeat and finally-style release use the exact returned run ID;
- PR prose, sources, subprocess output, environment values, and credentials do
  not appear in helper output;
- discovery respects the three-open-proposal cap and unknown-identity stop;
- discovery prioritizes preferred retry and bounded backlog candidates before
  unrelated external research;
- a curation cycle with no GitHub mutation remains a semantic follow-up in
  automation memory and is selected first on the next run only while its exact
  PR/head remains eligible;
- multi-paragraph owner-decision and blocked summaries publish successfully,
  while unsafe controls and reserved comment markers still fail closed;
- proposal validation accepts an explicitly reported same-kind re-key but still
  rejects an unrelated or incompletely reported catalog deletion;
- proposal validation accepts a candidate present only in its proposal head,
  while validation and publication reject it if freshly fetched canonical
  `main` or an open GitHub proposal already contains the same candidate key;
- curation readiness is tied to the unchanged reviewed, validated, pushed,
  CI-green, mergeable head; and
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

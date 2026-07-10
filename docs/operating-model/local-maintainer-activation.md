# Local Maintainer Post-Merge Activation And Rollback

## Status And Authority

This is the only activation procedure for the simplified local Snowcast
maintainer. Repository implementation does not install a personal skill, create
schedules, provision labels, or enable automation.

Activation is blocked until the implementation PR is merged to `main`. Every
step below is review-gated. Do not copy executable instructions from the
superseded local-maintainer plan or spec.

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
- acquire curation before prepare and hold the lease through publication;
- perform at most six review/fix cycles, using a fresh independent
  `snowcast-catalog-review` reviewer context after every fix; cycles five and
  six require demonstrably converging in-model findings, and the run stops at
  two hours;
- bind a complete review disposition to the exact reviewed head and route
  incomplete review to `manual-check` or `owner-decision`;
- use the helper's explicit `publish manual-check` capability to preserve a
  scope-safe unresolved reviewed head; never push it directly or represent it
  as validated;
- interpret backlog and external research read-only before discovery
  acquisition, then acquire discovery, rerun inspection, and mutate at most one
  candidate;
- heartbeat before and after capabilities and at least every five minutes while
  holding a lease;
- release its lease in a `finally` path with the exact run ID if and only if
  acquisition succeeded;
- request semantic states while relying on helper gates for proposal,
  waiting-CI, and ready;
- write a concise current PR-body synopsis for every waiting-CI or ready
  request, including recovery and lightweight readiness runs, and explicitly
  adopt an unmarked legacy body only through the helper's `--adopt-body`
  permission;
- report the bounded Triage outcome for every terminal or no-op result, omitting
  lease run ID before acquisition;
- never push or publish outside the helper; and
- never approve or merge.

## First-Run Acceptance

For each schedule, confirm:

- a no-work run is a bounded no-op, not an error or mutation;
- wrong-worker or multiple-journal recovery fails before lease acquisition;
- heartbeat and finally-style release use the exact returned run ID;
- PR prose, sources, subprocess output, environment values, and credentials do
  not appear in helper output;
- discovery respects the three-open-proposal cap and unknown-identity stop;
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

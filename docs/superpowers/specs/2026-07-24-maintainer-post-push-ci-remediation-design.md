# Maintainer Post-Push CI Remediation Design

Status: approved design, not implemented or activated

Date: 2026-07-24

Related:

- `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- `docs/operating-model/local-maintainer-activation.md`
- `docs/operating-model/maintainer-runtime-command-contract.md`

## Problem

The curation maintainer can semantically review, remediate, validate, and push
an exact catalog head, but its current responsibility ends when GitHub CI
starts. A later scheduled run inspects `maintainer:waiting-ci`: success becomes
`maintainer:ready`, while failure becomes `maintainer:blocked/ci-failure`.

This loses useful continuity. PR #33 demonstrated the common failure shape:
the catalog graph was intentionally changed and locally validated, but two
owner-visible CI tests still asserted the old graph. The maintainer had enough
exact-head context to perform a narrow test migration, yet the current
lifecycle stopped and required another intervention.

The workflow should wait for ordinary CI in the same run and repair one
bounded, test-only failure without reopening the completed source/trust and
graph/scope review. It must remain resumable after task interruption or Mac
sleep, and it must not turn post-push repair into an unbounded extension of the
semantic loop.

## Goals

- Keep the curation lease while waiting up to 30 minutes for the first CI
  result.
- Make post-push waiting and one test-only repair resumable from exact helper
  state.
- Exclude the post-push phase from the 240-minute semantic-review deadline.
- Bound the separate post-push phase to one repair attempt and at most 120
  minutes.
- Preserve the reviewed and validated catalog/trust/report tree exactly.
- Let GitHub CI, rather than the unattended local machine, execute PR-supplied
  test code.
- Publish `maintainer:ready` in the same run when the exact final head is
  CI-green and mergeable.

## Non-goals

- Reopening catalog research, source review, graph review, boundary
  adjudication, or general remediation after the semantic deadline.
- Repairing production code, operational code, dependencies, pytest
  configuration, fixtures with process-wide behavior, or catalog/trust/report
  semantics in the post-push phase.
- Repeated CI repair attempts in one run.
- Automatically rerunning cancelled, missing, unknown, or apparently flaky CI.
- Approving or merging the PR.
- Removing `maintainer:waiting-ci` in the first compatible rollout.

## Decision And Review Gate

- **Classification:** review-gated. This changes scheduled-job reliability,
  exact-head publication state, and the trusted boundary around PR-supplied
  tests.
- **Developer Decision Checkpoint:** resolved by the owner. Hold the lease
  during CI, wait at most 30 minutes, allow one repair attempt, and account for
  the post-push phase outside the four-hour semantic budget.
- **ADR:** amend ADR 0011. The local Codex control plane and helper-only
  mutation boundary remain unchanged.
- **Advisory review:** required as a focused design/feature review before
  activation because the change affects unattended execution and test-trust
  policy.

## Lifecycle

### 1. Initial push

After the ordinary semantic loop produces a clean exact-head review, the
existing helper gates still:

1. checkpoint the reviewed head;
2. run trusted exact-base validation;
3. create an exact push journal;
4. push with the selected remote head as the lease value; and
5. wait for Git and the GitHub PR API to converge on the journaled head.

Once convergence succeeds, the helper atomically creates a post-push CI
continuation and publishes the initial compatible waiting-CI presentation
before completing the push journal. If that sequence is interrupted, the
journal remains the sole recovery authority. After the handoff completes, the
continuation, not a label or automation memory, becomes the authority for later
CI handling.

### 2. First CI wait

The current curation run retains its lease for up to 30 elapsed wall-clock
minutes. It polls the exact PR/head check rollup and heartbeats at least every
five minutes.

- **Success and mergeable:** publish `maintainer:ready`.
- **Pending at 30 minutes:** keep the exact CI continuation, publish or retain
  the compatible `maintainer:waiting-ci` presentation, release the lease, and
  stop. A successor resumes this continuation before ordinary PR selection.
- **Failure:** Codex interprets the bounded check summary and decides whether
  the failure is eligible for the single test-only repair.
- **Cancelled, missing, unknown, conflicting, or changed head:** perform no
  repair. Preserve or terminalize the continuation according to the exact
  helper result and publish only an allowlisted honest state when safe.

The 30-minute wait is wall-clock time. Sleep does not extend it. On wake, the
run first heartbeats and revalidates ownership. If the lease was fenced or the
head changed, it stops without mutation.

### 3. One bounded CI repair

A CI failure is repairable in this phase only when Codex can tie it to stale or
incorrect assertions in ordinary test modules and the intended behavior is
already fixed by the exact reviewed catalog/trust/report tree.

The helper permits changes only to regular `tests/test_*.py` files inside the
curation lane's allowed test scope. A failing test module does not need to have
been changed by the original PR; the repair may add it to the PR diff. Codex
selects the test files from the exact CI failure and repository context, while
the helper enforces the narrow file class and exact repair diff. It rejects:

- application, catalog, trust, report, backlog, operational, or dependency
  changes;
- `conftest.py`, pytest/plugin configuration, executable scripts, generated
  binaries, symlinks, and unsafe file modes; and
- any non-test tree difference from the original reviewed and validated head.

Codex may inspect the exact failed-check summary and relevant repository code,
then prepare one batched test migration. It does not execute the changed PR
test modules locally. A fresh focused reviewer checks that:

- each changed assertion describes the already-reviewed behavior;
- coverage was migrated rather than deleted or weakened;
- unrelated test behavior was not broadened or relaxed; and
- the non-test tree is byte-for-byte identical to the reviewed and validated
  tree.

The helper checkpoints that focused review, verifies the path/mode and
non-test-tree invariants, journals a second exact-lease push, and records that
the continuation's single repair attempt has been consumed.

### 4. Second CI wait

After the repaired head is pushed, the run waits up to another 30 elapsed
wall-clock minutes under the same lease.

- **Success and mergeable:** publish `maintainer:ready`, complete the
  continuation, and release.
- **Pending at 30 minutes:** retain the exact continuation and
  `maintainer:waiting-ci` presentation, then release. A successor performs only
  the remaining exact-head CI/readiness step.
- **Failure:** publish `maintainer:blocked/ci-failure`, terminalize the
  continuation, and release. No second repair is allowed in the same run.
- **Changed head or lost lease:** stop without publication not authorized by
  the current exact state.

## Time Budgets

The existing curation semantic clock remains unchanged:

- no boundary adjudication starts at or after 180 minutes;
- no new semantic reviewer or fixer starts at or after 210 minutes; and
- active semantic work is interrupted at 240 minutes.

The post-push CI phase begins only after an exact reviewed head passes helper
validation and the initial push is confirmed. It has a separate maximum:

- first CI wait: 30 elapsed minutes;
- one CI repair: 60 active minutes; and
- second CI wait: 30 elapsed minutes.

The maximum extension is therefore 120 minutes. Publication, recovery, lease
release, cleanup, and bounded Triage remain exact-state finalization and do not
authorize further semantic work.

The continuation records consumed wait and active-repair time. A successor
receives only the remaining budget; interruption or a new scheduled task never
resets the 30/60/30 limits.

## Durable State And Recovery

The helper stores one owner-private CI continuation containing only facts
needed to resume safely:

- PR, branch, exact reviewed/validated head, and current pushed head;
- prepare-time base and single report path;
- CI phase and whether the one repair attempt was consumed;
- consumed first-wait, active-repair, and second-wait budgets;
- immutable reviewed-tree and non-test-tree identities;
- allowed test paths and focused-review checkpoint when present; and
- bounded timestamps and terminal status.

It stores no CI prose, test logs, model conclusions, credentials, commands, or
automation-memory authority.

Recovery priority becomes:

```text
push journal
-> post-push CI continuation
-> reviewed continuation
-> remediation continuation
-> ordinary PR
```

A push journal remains the sole authority for an ambiguous branch mutation.
The CI continuation becomes authoritative only after exact push convergence
and journal handoff. A successor always re-fetches the current PR head, checks,
mergeability, labels, and lease state; saved CI conclusions are never reused.

If the Mac sleeps longer than the stale-lease interval, a successor may fence
the old run. The waking run must discover lost ownership on its next heartbeat
and stop. The continuation lets the successor resume without repeating catalog
review.

## GitHub Presentation

`maintainer:waiting-ci` remains temporarily as a human-visible compatibility
label and canonical-comment state. It is not recovery or readiness authority.
The exact helper continuation determines whether a run may wait, repair, or
publish readiness.

The canonical comment is updated idempotently at the meaningful transitions:

- initial pushed head awaiting CI;
- one focused CI repair pushed;
- CI still pending and resumable;
- CI failed after the allowed repair; or
- exact final head ready.

The managed PR-body synopsis and Resulting Graph remain bound to the reviewed
catalog/trust/report tree. A test-only repair does not regenerate or semantically
change that graph.

Removing `maintainer:waiting-ci` can be considered after the durable
continuation has operated successfully. That later cleanup must not change the
continuation or readiness contracts.

## Deterministic And Codex Responsibilities

The deterministic helper owns:

- exact PR/head/base identity and lease fencing;
- heartbeat, state persistence, and recovery priority;
- GitHub check-state retrieval and bounded polling inputs;
- repair-attempt counting;
- allowed test paths, regular-file modes, and immutable non-test-tree checks;
- focused-review checkpoint identity;
- push journals, exact-lease pushes, labels, body/comment publication, and
  readiness gates.

Codex owns:

- interpreting whether a failed check represents a stale test assertion;
- reading the relevant application/test context;
- creating the bounded test migration;
- independently reviewing that the migration preserves coverage; and
- writing the concise human-facing transition summary.

The helper does not infer test intent from names or logs. Codex cannot widen
the repair scope, create a second attempt, or authorize readiness.

## Failure Handling

- **Initial CI pending beyond 30 minutes:** durable pending continuation; no
  repair and no repeated semantic review.
- **Non-test or ambiguous failure:** no repair; honest blocked outcome when
  exact-state publication is safe.
- **Focused review incomplete:** no second push; preserve a resumable
  continuation only when the helper has a complete mechanically safe
  checkpoint.
- **Repair command interrupted before push:** successor restores only the
  helper-owned checkpoint and requires a fresh focused review if the exact
  review evidence was not durably recorded.
- **Repair push interrupted:** recover only through the push journal.
- **Second CI failure:** blocked/ci-failure; no same-run retry.
- **Pending after second wait:** exact-head CI continuation for lightweight
  successor readiness.
- **Head drift:** invalidate prior CI evidence; never blend another commit with
  the continuation.
- **Lease loss:** old run stops; successor revalidates from durable state.

## Verification

Implementation must add focused contract coverage for:

- CI-continuation creation only after confirmed initial push convergence;
- journal-to-continuation handoff and recovery priority;
- 30/60/30 budget transitions and one-attempt enforcement;
- heartbeats while polling and lost-lease fencing after sleep;
- exact-head and non-test-tree binding;
- rejection of catalog, trust, report, application, `conftest.py`, config,
  symlink, mode, and unrelated test changes;
- focused-review checkpoint requirements;
- second exact-lease push and ambiguous-push recovery;
- success, pending, failure, cancellation, missing-check, merge-conflict, and
  changed-head outcomes;
- ready publication only for the exact final CI-green mergeable head;
- compatibility-label behavior without using the label as authority; and
- runtime-command and installed-skill contract parity.

The feature branch must pass the focused maintainer suite, the complete
maintainer suite, repository lint/type checks for touched code, and a
prospective-merge test against current `origin/main`. Activation follows the
existing owner-controlled pause, install, inspect, smoke, and gradual re-enable
procedure.

## Alternatives Considered

### Keep failed CI for a later scheduled run

This has the smallest implementation delta but repeatedly loses the exact
context needed to migrate stale tests and leaves otherwise complete PRs
blocked.

### Release the lease while polling

This improves theoretical worker concurrency, but another curation or discovery
run is unlikely to finish before normal CI. Reacquisition, fencing, and
competing mutation add more failure modes than the short wait justifies.

### Allow repeated CI repairs within the post-push budget

This maximizes autonomy but can hide a weak first repair, repeatedly weaken
tests, and turn CI into another open-ended convergence loop. One reviewed
attempt keeps the behavior predictable.

### Execute the modified tests locally

This would give faster feedback but would execute PR-supplied Python on the
owner's full-access machine. GitHub CI remains the execution boundary; local
Codex performs static reasoning and focused review only.

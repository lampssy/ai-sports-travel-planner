# ADR 0011: Use Local Codex As The Maintainer Control Plane

Status: accepted
Date: 2026-07-08
Amended: 2026-08-15

Supersedes: N/A
Superseded in part by:
- `docs/architecture/adr/0020-use-generation-based-pre-push-curation-authority.md`

Related specs:
- `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- `docs/superpowers/specs/2026-07-09-maintainer-manual-check-handoff-design.md`
- `docs/superpowers/specs/2026-07-22-maintainer-convergence-and-regional-completion-design.md`
- `docs/superpowers/specs/2026-07-24-maintainer-post-push-ci-remediation-design.md`

Related docs:
- `docs/operating-model/review-playbook.md`
- `docs/product-backlog.md`
- `docs/architecture/adr/0004-static-catalog-curation-skill.md`

## Context

Snowcast's catalog-curation and review skills can already research, validate,
and prepare source-backed catalog changes, but the owner must manually invoke
their review/fix cycles and track several PRs. Discovery of missing catalog
entities has the same coordination problem. The desired system should maintain
eligible curation PRs repeatedly, create explicitly gated discovery proposals,
and leave the owner with a short ready-to-merge queue.

GitHub Actions would provide an always-on scheduler, but reliable Codex
execution there requires a non-interactive hosted authentication design and
would move secrets and the control plane into GitHub. The current Codex App can
run scheduled work locally using the owner's existing Codex login and local
project-scoped GitHub authentication. The machine is normally powered on, so
local availability is acceptable for this maintenance workload.

Codex automations currently inherit the user's default sandbox settings. The
app does not expose a per-automation sandbox override. The owner's default is
`danger-full-access`, and changing that global interactive default is not
desired.

## Decision

Use two local Codex App automations as the Snowcast maintainer control plane:

- a catalog PR maintainer that reconciles CI and deeply reviews/remediates at
  most one eligible PR per run;
- a catalog discovery worker that creates explicitly gated proposal PRs from
  Codex-interpreted backlog and external research.

Run both in isolated background worktrees. Use GitHub only for branch transport,
checks, labels, synchronized PR content, and one idempotent maintainer-summary
comment. Keep detailed reasoning and run diagnostics in Codex Triage.

Treat same-repository `codex/*` branches as automation owned when their lane is
implemented. Use a thin repository-owned helper for objective safety
capabilities: inspect safe candidates, prepare a selected branch, validate an
exact reviewed head, and publish or push under exact authority. Codex owns
semantic interpretation, prioritization, review, remediation, backlog reading,
discovery selection, CI interpretation, and non-objective lifecycle decisions.

Retain exactly these two workers while separating their semantic purposes more
clearly. Curation proves one bounded destination graph correct against a frozen
evidence envelope. It treats omissions that can invalidate that graph as
blockers and hands additive adjacent coverage to the merged product backlog as
regional follow-ups. The existing discovery worker prioritizes those merged
regional items and prepares one coherent, one-primary-destination graph proposal
before it considers unrelated external research. Do not add a regional worker,
semantic queue, runtime registry, schema version, or deterministic backlog
parser.

Add private remediation continuations beside reviewed continuations. The helper
may preserve one exact mechanically valid local head after the two-command delta
checkpoint, but that record grants recovery authority only. A successor must
perform a fresh bounded independent review before the helper can promote it to
reviewed recovery; final validation and publication retain their existing
exact-head gates. Codex still owns evidence meaning, graph impact, backlog
wording, coherent-slice selection, URL reachability/relevance checks, and any
run-local URL cache. The helper owns only typed shape, exact identity,
path/mode/ref safety, exact backlog-anchor existence, one-focus proposal
identity, and mutation/publication boundaries.

This separate remediation/reviewed-continuation design is retained here as
historical context. ADR 0020 supersedes it for pre-push curation authority with
one generation timeline and one idempotent checkpoint capability. The
post-push CI, push-journal, terminal-publication, approval, and merge decisions
in this ADR remain in force.

After a reviewed and validated curation head is pushed, keep the curation lease
for a bounded same-run CI phase. Wait up to 30 minutes for the first exact-head
CI result. When CI exposes only stale assertions in ordinary test modules,
allow one focused, independently reviewed, test-only repair with a 60-minute
active-execution budget, followed by one final 30-minute CI wait. This phase is
separate from the 240-minute catalog-semantic deadline and may extend one run
by at most 120 minutes.

Persist that phase as an exact helper-owned post-push CI continuation. It binds
the reviewed and validated non-test tree, pushed head, attempt count, and
focused-review checkpoint; it never stores CI prose or model conclusions.
Recovery order is push journal, post-push CI continuation, reviewed
continuation, remediation continuation, then ordinary PR. Keep
`maintainer:waiting-ci` initially as presentation and compatibility state, not
as recovery authority.

Do not execute modified PR test modules on the unattended local full-access
machine. Codex may statically migrate assertions and a focused reviewer must
confirm that coverage was not weakened. The helper permits only regular
`tests/test_*.py` changes, proves the non-test tree is identical to the reviewed
and validated tree, enforces one attempt, and uses the existing journaled
exact-lease boundary for the repair push. Production, operational, dependency,
pytest-configuration, catalog, trust, report, and backlog changes remain outside
this post-push phase.

Rewrite stale catalog branches only through the helper, which creates a local
backup ref, rebases onto selected `origin/main`, verifies that the resulting
diff contains only catalog data, non-control-plane documentation, tests, and
safe regular-file modes, rechecks the remote SHA, and performs one exact-SHA
`--force-with-lease` push. Never use plain force or automatic conflict
resolution. Do not require whole-file blob IDs, changed paths, or catalog
targets to remain identical across rebase and Codex remediation; the fresh
semantic review and final validation own content correctness.

Test changes remain allowed in curation PRs, but they are not executable
authority for unattended local validation. The final pytest stage uses only
the exact-base uv project, pytest configuration, conftest, and fixed absolute
test-module paths. It supplies the prepared catalog/trust files as data to
those trusted tests and runs with a fresh private `HOME`. PR-supplied Python and
pytest configuration execute only in owner-visible CI or deliberate review,
not in the local maintainer.
The bounded post-push CI repair may edit ordinary test modules after static
reasoning and focused independent review, but still does not execute those
modified modules locally; owner-visible GitHub CI remains their execution
boundary.

Do not parse human backlog prose deterministically and do not use the initial
69-entry Alpine registry as a runtime discovery gate. Preserve a researched
destination-coverage registry as a future backlog idea. A well-supported
external candidate may go directly to an owner-gated proposal. A promising but
unready candidate remains a Triage observation for an owner decision; the
automated lane does not create backlog-only proposal PRs.

Use one private run owner record containing worker, run ID, and timestamps; one
per-work-item phase record; and one separate push journal for ambiguous network
recovery. GitHub durable state consists of lane/state labels, a human-readable
PR body, and one canonical maintainer comment. Codex requests lifecycle state,
while the helper independently enforces proposal, waiting-CI, and readiness
facts for the exact current head.

Create new discovery refs atomically with an empty expected-value lease, never
through a check-then-ordinary-push sequence. Bind the push journal to candidate,
branch, head, and returned PR number so a crash after branch creation can find
or create exactly one draft PR and resume publication idempotently. Treat an
open proposal with unknown canonical-comment identity as a fail-closed block on
new proposal publication.

When a bounded curation run exhausts its review/fix allowance with an unresolved
issue inside the existing model, allow one separate reviewed-but-unvalidated
handoff. The helper revalidates the exact local reviewed head and scope, records
an exact-lease push journal, pushes only against the originally selected remote
head, and then publishes `maintainer:manual-check`. Its canonical machine state
retains `last_operation=reviewed` and no validated head. Normal push and
readiness paths still require successful validation of the current head.

Surface unresolved push journals before fresh work selection. Fresh mutation
is blocked until the matching worker recovers exactly one journal; after stale
takeover, the new run may adopt it only after validating current lease ownership
and observed remote state, while preserving the origin run ID and fencing the
old run. Multiple unresolved journals require owner attention.

Accept inherited `danger-full-access` for the local first version rather than
changing the owner's global default or adding a separate OS sandbox. This is an
explicit risk acceptance, not a claim that helper checks create a security
boundary. The helper must fail closed on repository, remote, branch, base, SHA,
unsafe file mode, production or operational code, maintainer control-plane
instructions, or an empty resulting diff.
Automation instructions prohibit unrelated filesystem access, credential
inspection, downloaded-script execution, dependency changes, deployment, and
production operations.

Repository implementation and documentation merge before any installed skill
or automation prompt changes. Cutover is owner-controlled and atomic across the
shared skills and both prompts: pause both schedules, let active lease/journal
state settle, snapshot the previous installed artifacts, replace and inspect
them together, run disabled/manual smoke checks, and then re-enable one schedule
at a time. Rollback uses the same paused boundary and never deletes private
continuation refs or state manually.

The automation never merges or approves PRs. Discovery proposals require the
owner to remove `maintainer:proposal` before the curation maintainer can act on
them.

## Consequences

The workflow can reuse the proven local skills and existing authenticated
sessions without storing an OpenAI API key or GitHub credential in the
repository. The owner gets a durable GitHub queue while retaining Codex as the
interaction surface.

The machine must be powered on with Codex running. Missed runs are acceptable
because the workflow recomputes state and does not depend on exact execution
time.

Repository-owned helper safety capabilities can be tested independently of the
personal orchestration skill. Semantic workflow behavior remains visible in
Codex Triage and the one canonical GitHub comment rather than being duplicated
across parser state, a registry, body markers, comments, and local artifacts.

Full-access unattended execution carries host-level risk. Malicious or
misinterpreted PR and web content could have broader impact if the model ignored
its workflow constraints. Fail-closed helper APIs, fixed command templates,
isolated worktrees, bounded branch ownership, and untrusted-content rules reduce
but do not eliminate this risk.

Automation-owned branch history may be rewritten. Exact leases prevent
overwriting a newly changed remote head, and local backup refs provide recovery
for the selected original SHA. Conflicts and unsafe resulting paths require
owner intervention. Non-control-plane documentation and tests may expand
during remediation; tests are executable in CI and may be weakened
accidentally, but the local maintainer does not execute their PR versions. The
remaining CI/review risk is accepted for same-repository `codex/*` branches
because the workflow never approves or merges and the owner reviews the final
PR.

Codex may choose different eligible PRs or discovery candidates across runs.
That variability is acceptable because proposal volume, branch authority,
exact heads, catalog validity, readiness, approval, and merge remain bounded by
deterministic checks or the owner. Moving semantic prose interpretation out of
Python reduces brittle coupling to document format.

Mechanically safe curation progress now survives sleep, deadlines, validation
failure, and truthful blocked or owner-decision publication without being
mistaken for reviewed work. This adds private state and refs, but prevents
repeating completed remediation. Additive regional findings no longer expand an
otherwise correct curation indefinitely; they become visible owner-gated
backlog/proposal work. GitHub proposal identity and the merged schema-v3 report,
not private memory, remain the durable proposal record.

A normal CI wait now delays discovery or another curation run for up to 30
minutes because the current curation run retains the global lease. The accepted
tradeoff is simpler exact-head ownership: normal CI is shorter than another
useful mutation cycle, while heartbeats and stale-owner fencing still recover
from sleep or task loss. One post-push repair can extend the run by at most two
hours without reopening catalog-semantic work.

## Alternatives Considered

- **GitHub Actions with hosted Codex authentication.** This is more available
  and centralized, but introduces non-interactive authentication and secret
  management concerns and is not needed while the local machine is reliably
  available.
- **`launchd` plus `codex exec`.** This offers lower-level scheduling control
  but duplicates capabilities already present in the Codex App and produces a
  less convenient local review and Triage experience.
- **Manual skill invocation only.** This has the smallest automation risk but
  preserves the repeated review/fix and queue-management burden the design is
  intended to remove.
- **A thick deterministic workflow policy engine.** This maximizes
  reproducibility but requires code to interpret evolving Markdown, duplicate
  catalog/backlog/registry state, and persist detailed lifecycle policy. The
  unactivated first implementation demonstrated that this boundary is too
  brittle and costly for owner-gated local workflows.
- **A fully model-controlled shell.** This minimizes helper code but allows
  model output to choose branch authority, push shape, readiness, and proposal
  limits. The decision keeps these irreversible or objective gates
  deterministic.
- **Change the global sandbox default to `workspace-write`.** This would reduce
  risk for automations but would also change the owner's preferred interactive
  default because Codex currently has no per-automation override.
- **Wrap each run in a separate container or operating-system sandbox.** This
  can provide a stronger boundary without changing the global Codex default,
  but adds environment, authentication, worktree, and browser/network
  complexity disproportionate to the local first version.
- **Merge rather than rebase automation-owned branches.** This avoids history
  rewrites but leaves noisier curation histories and does not use the ownership
  guarantee the owner explicitly granted to `codex/*` branches.

## Revisit When

Revisit this decision when Codex supports a reliable per-automation sandbox,
the owner wants an always-on hosted worker, local machine availability becomes a
material bottleneck, multiple humans start writing to automation-owned
branches, GitHub-hosted Codex authentication becomes operationally preferable,
or any security incident shows that workflow-level controls are insufficient.

# ADR 0011: Use Local Codex As The Maintainer Control Plane

Status: accepted
Date: 2026-07-08

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`
- `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`

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

Rewrite stale catalog branches only through the helper, which creates a local
backup ref, rebases onto selected `origin/main`, verifies allowed scope,
rechecks the remote SHA, and performs one exact-SHA `--force-with-lease` push.
Never use plain force or automatic conflict resolution.

Do not parse human backlog prose deterministically and do not use the initial
69-entry Alpine registry as a runtime discovery gate. Preserve a researched
destination-coverage registry as a future backlog idea. A well-supported
external candidate may go directly to an owner-gated proposal; a promising but
unready candidate may be proposed as backlog work.

Use one private run owner record containing worker, run ID, and timestamps; one
per-work-item phase record; and one separate push journal for ambiguous network
recovery. GitHub durable state consists of lane/state labels, a human-readable
PR body, and one canonical maintainer comment. Codex requests lifecycle state,
while the helper independently enforces proposal, waiting-CI, and readiness
facts for the exact current head.

Accept inherited `danger-full-access` for the local first version rather than
changing the owner's global default or adding a separate OS sandbox. This is an
explicit risk acceptance, not a claim that helper checks create a security
boundary. The helper must fail closed on repository, remote, branch, base, SHA,
or scope mismatch, while automation instructions prohibit unrelated filesystem
access, credential inspection, downloaded-script execution, dependency changes,
deployment, and production operations.

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
for the selected original SHA. Conflicts and semantic drift require owner
intervention.

Codex may choose different eligible PRs or discovery candidates across runs.
That variability is acceptable because proposal volume, branch authority,
exact heads, catalog validity, readiness, approval, and merge remain bounded by
deterministic checks or the owner. Moving semantic prose interpretation out of
Python reduces brittle coupling to document format.

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

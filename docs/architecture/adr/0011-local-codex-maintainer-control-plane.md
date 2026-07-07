# ADR 0011: Use Local Codex As The Maintainer Control Plane

Status: accepted
Date: 2026-07-08

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-08-local-maintainer-automation-design.md`

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
- a catalog discovery worker that creates explicitly gated proposal PRs from a
  bounded backlog and coverage universe.

Run both in isolated background worktrees. Use GitHub only for branch transport,
checks, labels, synchronized PR content, and one idempotent maintainer-summary
comment. Keep detailed reasoning and run diagnostics in Codex Triage.

Treat same-repository `codex/*` branches as automation owned when their lane is
implemented. Rewrite stale catalog branches only through a repository-owned
deterministic helper that creates a local backup ref, rebases onto the selected
`origin/main`, verifies pre/post intent, rechecks the remote SHA, and performs
one exact-SHA `--force-with-lease` push. Never use plain force or automatic
conflict resolution.

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

Repository-owned helper code can be tested and reviewed independently of the
personal orchestration skill. GitHub state remains recoverable even if a Codex
thread is hard to locate.

Full-access unattended execution carries host-level risk. Malicious or
misinterpreted PR and web content could have broader impact if the model ignored
its workflow constraints. Fail-closed helper APIs, fixed command templates,
isolated worktrees, bounded branch ownership, and untrusted-content rules reduce
but do not eliminate this risk.

Automation-owned branch history may be rewritten. Exact leases prevent
overwriting a newly changed remote head, and local backup refs provide recovery
for the selected original SHA. Conflicts and semantic drift require owner
intervention.

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

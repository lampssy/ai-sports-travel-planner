# Feature Spec: Local Snowcast Maintainer Automation (Superseded)

## Status

- Status: superseded before activation
- Superseded by:
  `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Implementation status: historical helper superseded and replaced on the
  feature branch before activation; this design must not be installed or
  scheduled. Historical repository-scoped
  advisory and quality-review conditions resolved by commits `090ec67`,
  `e2e1b92`, `910c2ee`, and this documentation. Its personal-skill and
  activation instructions are retired and must not be used
- Owner: solo-builder
- Related docs: `docs/operating-model/review-playbook.md`,
  `docs/operating-model/advisory-reviewers.md`, `docs/product-backlog.md`,
  `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`,
  `docs/superpowers/specs/2026-07-07-catalog-curation-backlog-deferrals-design.md`
- Related plan: `docs/superpowers/plans/2026-07-08-local-maintainer-automation.md`
- Related ADRs: ADR 0004 and ADR 0011

> This document is retained as the historical first design. Do not use its
> runtime registry, deterministic backlog parser, credential-based lease,
> duplicated GitHub machine-state, or activation instructions. The
> simplification spec above and
> `docs/operating-model/local-maintainer-activation.md` are authoritative.

## User Outcome

Snowcast should have a local maintainer that repeatedly brings eligible catalog
curation PRs to a state where the owner can approve and merge them after, at
most, a quick final glance. It should independently review each PR, apply
source-backed fixes within an approved scope, repeat the review/fix cycle when
needed, reconcile CI, and make unresolved domain or source decisions visible
instead of silently guessing.

The maintainer should also inspect a bounded discovery queue for missing
destinations, stay bases, ski areas, access edges, terrain domains, and catalog
facts. It may open complete but explicitly gated proposal PRs. The owner decides
whether each proposed catalog addition should proceed by removing one proposal
label; accepted proposals then enter the normal review/fix workflow.

GitHub provides durable branch transport and concise workflow visibility.
Codex on the owner's machine remains the control plane and the place for full
reasoning and investigation.

## Scope

In scope:

- two standalone Codex App automations running locally in isolated worktrees;
- automated readiness maintenance for same-repository catalog PRs on
  `codex/*` branches;
- guarded synchronization with `main`, fresh catalog review, source-backed
  remediation, validation, CI reconciliation, and GitHub status publication;
- one idempotently updated maintainer-summary comment per PR, a synchronized PR
  body, and two-axis GitHub labels;
- backlog-first discovery followed by a finite Alpine coverage registry;
- creation of at most one catalog proposal per discovery run, with at most
  three open proposal PRs;
- atomic removal of an originating backlog marker when the corresponding
  catalog addition merges;
- deterministic, repository-owned helper code for locks, eligibility, guarded
  git mutation, state transitions, and GitHub publication;
- a machine-local Codex skill for orchestration and semantic judgment;
- post-merge installation and direct scheduled operation after implementation
  verification, without a staged dry-run or manual-pilot rollout.

Out of scope for the first implementation:

- automatic merge, GitHub approval, or bypass of branch protection;
- automatic semantic conflict resolution;
- fork PRs, non-`codex/*` branches, or branches whose ownership is ambiguous;
- automatic schema changes, stable-ID migrations, new domain boundaries, or
  other owner decisions described below;
- a general-purpose readiness lane for every code PR;
- data-quality follow-up, production-canary investigation, documentation drift,
  source-integrity, or production-investigation lanes;
- claiming that open-web search can prove Alpine or global catalog
  completeness;
- production deployment, dependency installation, secret rotation, database
  migration, or production-data mutation;
- GitHub Actions as the scheduler or Codex execution environment.

The future lanes remain extension points and are intentionally unranked until
the current project direction makes one of them useful.

## Product Fit

- The workflow strengthens Snowcast's catalog and source integrity rather than
  adding generic travel or generic-agent functionality.
- Catalog proposals stay review-gated, and missing or contradictory source
  evidence remains visible to the owner.
- The discovery universe is explicit and bounded. The workflow does not present
  open-web search as proof that all relevant ski destinations have been found.

## Domain Model

- Bounded contexts touched: Catalog, Data Trust, and Maintainer Operations.
- Domain terms introduced:
  - `maintainer lane`: the workflow responsible for a PR;
  - `maintainer state`: the PR's current automation lifecycle state;
  - `proposal PR`: a complete catalog curation PR that is blocked on an owner
    decision about whether to onboard its candidate;
  - `head lineage`: the sequence of automation rewrites descended from the
    head SHA first observed for one maintenance attempt;
  - `origin marker`: an exact backlog candidate marker that a proposal resolves;
  - `coverage registry`: a finite reviewed universe against which catalog
    coverage can be assessed without claiming open-world completeness.
- Existing catalog entities and their ownership rules do not change.
- A proposal does not become catalog truth until its PR is merged.
- A catalog candidate removed from the backlog must be added in the same merge.

Maintainer invariants:

- GitHub PRs and git refs are the durable state; no private database is added.
- At most one `lane:*` label and one `maintainer:*` state label are active on a
  managed PR.
- `maintainer:proposal` is the only owner-approval gate. Removing it is the
  approval action.
- The automation never merges or approves a PR.
- Only one mutation-capable maintainer run may operate at a time.
- One scheduled curation run deeply processes at most one PR.
- One discovery run creates at most one proposal and never exceeds three open
  proposal PRs.
- A network push is authorized at most once for one exact selected/prepared/
  reviewed state and only with an exact remote-head lease. A no-op maintenance
  path performs no network push.

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: scheduled jobs, unattended full-access execution,
  GitHub branch mutation, catalog source integrity, external web content, and
  future maintenance conventions
- Developer Decision Checkpoints:
  - resolved: use local Codex App automations rather than GitHub Actions;
  - resolved: use two independent automations, one for PR readiness and one for
    discovery;
  - resolved: all eligible same-repository `codex/*` branches are automation
    owned without a separate `maintainer:managed` label;
  - resolved: synchronize automation-owned branches through guarded rebase,
    backup refs, intent comparison, and exact-SHA `--force-with-lease`;
  - resolved: use `lane:*` for routing and `maintainer:*` for state;
  - resolved: publish an idempotent GitHub summary comment in addition to
    labels, synchronized PR body content, and Codex Triage output;
  - resolved: run curation four times per day and discovery on Monday,
    Wednesday, and Friday;
  - resolved: allow one discovery proposal per run and at most three open
    proposals;
  - resolved: keep one global lease throughout discovery research and require
    mutable commands to correlate the current run with a nonsecret lease ID and
    prove ownership through private state-file credential transport, rather
    than exposing the token on stdout/argv or redesigning those artifacts as
    concurrent immutable outputs;
  - resolved: remove an originating backlog marker in the proposal PR so merge
    applies the catalog addition and backlog cleanup atomically;
  - resolved: skip a staged operational rollout but retain automated
    verification for newly introduced mutation code;
  - resolved: accept the current Codex behavior in which automations inherit
    the owner's `danger-full-access` default because no per-automation sandbox
    override is available;
  - accepted assumptions: the machine is normally powered on with Codex
    running, project GitHub authentication remains available locally, the
    owner is the only writer to automation-owned curation branches, and no
    other local OS account currently shares the machine;
  - unresolved: none.
- ADR status: ADR 0011 records the local control-plane, authority, and inherited
  permission decision.
- Advisory design-review:
  - reviewers: data-trust-source-integrity, security-privacy,
    release-change-management, observability-ops
  - status: completed; the review made the coverage-registry contract explicit,
    placed head-lineage state in the marked GitHub comment, narrowed security
    guarantees to the deterministic boundary, and added activation ordering
  - skipped reason: N/A
- Advisory feature-review before final handoff:
  - reviewers: data-trust-source-integrity, security-privacy,
    release-change-management, observability-ops
  - status: completed; repository-scoped ship-after-fixes conditions resolved
    by commits `090ec67`, `e2e1b92`, `910c2ee`, and this documentation; the
    installed personal skill and actual automation records still require the
    replacement post-merge activation review
  - skipped reason: N/A

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Technical | Execution control plane | Determines authentication, reliability, and where credentials live | GitHub Actions is always-on but needs hosted Codex authentication; local Codex reuses interactive login but depends on the machine | Local Codex App automations | Appropriate for the current solo-builder workflow; machine uptime is an explicit dependency | ADR 0011 |
| Technical | Branch synchronization | Curation branches can become stale, while history rewrites can destroy work | Merge preserves history; guarded rebase produces clean PRs but rewrites branch history; no sync leaves avoidable drift | Guarded rebase with backup ref and exact lease | Safe only because eligible branches are automation owned; conflicts and head changes must stop the run | ADR 0011 |
| Mixed | Proposal approval | Discovery must help without silently changing the product catalog | Auto-onboard is fast but unsafe; comment commands add ceremony; a negative label gate is visible and reversible | Remove `maintainer:proposal` to approve | Keeps product decisions owner-controlled and makes approval independent of Codex conversation history | This spec |
| Technical | Unattended permissions | A full-access background agent can affect the whole machine | Change the global default; build an external OS sandbox; accept inherited full access with workflow controls | Accept inherited full access without changing the owner's default | This is operationally simple but carries real host-level risk; helper checks are fail-closed workflow controls, not a security sandbox | ADR 0011 |
| Product / Domain | Discovery breadth | Open-web search cannot prove completeness and can flood the catalog | Free-form web discovery; backlog-only; backlog plus finite registry and controlled nominations | Backlog first, then a finite Alpine registry; web research only nominates candidates | Gives a comparison universe and preserves explicit uncertainty | This spec |
| Technical | Discovery artifact concurrency | Candidate selection and source enrichment write local state while research may take time | Retain one private worker-owned lease throughout research; or redesign outputs as immutable, uniquely named artifacts with version arbitration | Retain and heartbeat one lease; subsequent commands pass its nonsecret lease ID and validate the matching token from owner-only state | This is simpler and keeps one mutation authority; the ID prevents a stale same-worker run from adopting a successor lease, while the six-hour threshold makes heartbeat discipline part of the worker contract | This spec |

## Architecture Decisions

### Runtime split

Two Codex App cron automations run against this repository in separate
background worktrees:

1. **Catalog PR Maintainer** runs four times per local day. It first performs a
   lightweight reconciliation of PRs waiting for CI, then deeply processes the
   oldest eligible catalog PR that can make progress.
2. **Catalog Discovery** runs Monday, Wednesday, and Friday. It stops when three
   proposal PRs are already open; otherwise it selects at most one candidate and
   creates at most one complete proposal PR.

The app schedule is machine-local and follows the local timezone. The initial
curation schedule should be spaced approximately six hours apart; exact clock
times are operational configuration, not product behavior.

### Ownership split

- `ops/maintainer/` contains versioned and tested deterministic helper code.
  It owns locks, eligibility checks, state parsing, safe git operations, command
  construction, state transitions, and idempotent GitHub publication.
- After the repository helper is merged, a personal `snowcast-maintainer` skill
  under `~/.codex/skills/` owns semantic orchestration and invokes the existing
  Snowcast curation, catalog-review, and advisory-review skills. It remains
  machine-specific and contains no secrets. This repository change does not
  install it.
- Codex App owns schedules, background worktrees, model settings, and Triage
  delivery.
- GitHub owns branches, PRs, checks, labels, and the durable summary comment.
- Local configuration owns project-scoped GitHub authentication, Codex login,
  the global lock, and non-secret runtime state. Nothing in these locations is
  committed.

The deterministic helper is the only approved path for branch rewrites and
GitHub state publication. Semantic skills may prepare changes and review
results, but they do not construct force-push commands or improvise lifecycle
transitions.

### Deterministic CLI and local state

The repository entry point is:

```text
python -m ops.maintainer.cli \
  --state-dir <path> \
  --gh-config-dir <project-scoped-gh-config> \
  <family> <command>
```

Its fixed command surface is:

- `lock acquire <worker>`;
- `lock heartbeat <worker> --phase <phase> --lease-id <id>`;
- `lock release <worker> --lease-id <id>`;
- `github ensure-labels --worker <worker> --lease-id <id>`;
- read-only `curation inventory`; `curation prepare`, `validate`, `push`, and
  `publish` each require `--lease-id <id>`;
- read-only `discovery validate-registry`; `discovery next`, `add-source`,
  `nominate`, `verify-proposal`, and `publish-proposal` each require
  `--lease-id <id>`.

`curation inventory` and `discovery validate-registry` are read-only. Every
automation invocation must pass the global `--gh-config-dir` option before its
command family. The repository default is the Snowcast-specific GitHub CLI
profile, but the schedule still supplies it explicitly so ambient global GitHub
configuration is never authority.

After `lock acquire` creates the global lease, it returns a nonsecret
32-character lowercase-hex `lease_id`. Every subsequent command that mutates
local artifacts, git, or GitHub requires that ID through `--lease-id`, then
loads the private worker credential and correlates worker, token, and lease ID
with `run.lock/owner.json`. Curation commands can load only the curation
credential, discovery commands only the discovery credential, and label
provisioning names the owning worker explicitly. Heartbeat and release likewise
name the expected worker. The private token is never returned on stdout and is
never accepted on argv; the nonsecret lease ID may appear in bounded local
output and Triage. The discovery worker retains and heartbeats the same lease
while it researches a candidate, so `next`, `add-source`, and `nominate` all
require its current lease ID.

The default state directory is
`~/.local/state/snowcast-maintainer`, with an override available only through
the global `--state-dir` option. The helper writes strict, size-bounded JSON
artifacts for selected attempts, guarded preparation, validation, push
authorization/consumption, candidate research, and immutable proposal
verification. State directories and files are current-user-owned and private;
atomic replacement and directory `fsync` make durable transitions explicit.
The active owner record and `run.credential-<worker>.json` must be private,
regular, current-user files with matching worker, token, and lease ID. A stale
same-worker ID cannot operate on or release a successor lease after takeover.
Lease paths reject unsafe ownership or permissions; artifact reads reject
symlinks, non-direct-child candidate paths, oversized files, and schema drift.

The CLI derives attempt IDs, lineage, maintenance-attempt counts, candidate
provenance, and publication machine state from prepared artifacts and trusted
current PR state. Caller-authored summary prose cannot create, reset, or
override those authorization fields.

Operational command output, excluding `--help`, is one JSON object for success
or failure. `lock acquire` returns `status`, `worker`, and the nonsecret
`lease_id`; the private token never appears in stdout or argv. Failure payloads
use bounded static reason codes such as `lock-busy`, `lease-ownership-error`, `stale-head`,
`intent-drift`, `validation-failed`, `git-timeout`, and
`invalid-command-input`; command output, authentication credentials, arbitrary
exception text, and untrusted PR/source content are not emitted. Validation
failures add only an allowlisted `validation_stage` and a
`validation_failure` of `failed` or `timeout`.

The CLI itself returns a nonzero JSON result for `lock-busy`, while the
orchestration skill treats that distinct reason as a successful no-op: another
fresh worker owns the mutation slot, so the scheduled run ends normally without
an alert or mutation.

### GitHub visibility contract

Routing labels:

- `lane:catalog-discovery`
- `lane:catalog-curation`

Maintainer states:

- `maintainer:proposal`
- `maintainer:working`
- `maintainer:waiting-ci`
- `maintainer:ready`
- `maintainer:owner-decision`
- `maintainer:manual-check`
- `maintainer:blocked`

The namespaces have no special GitHub semantics. They make routing and state
machine-readable and easy to filter. Future lanes may add labels such as
`lane:pr-readiness`, `lane:data-quality`, `lane:canary`, `lane:docs-drift`,
`lane:source-integrity`, or `lane:production-investigation` without changing
the state vocabulary.

The PR body continues to render the canonical curation report and stable
proposal context inside explicit maintainer-owned start/end markers. The helper
replaces only that managed block and preserves any text outside it. One comment
containing the marker
`<!-- snowcast-maintainer-summary -->` is created or updated idempotently. It
shows the current state, head SHA reviewed, latest review/fix result, CI status,
remaining owner action, important caveats, and last maintainer run. The helper
edits that comment rather than adding run-by-run comments. Detailed reasoning
and no-op diagnostics stay in Codex Triage.

The marked comment also contains a hidden, versioned machine-state block with
the reviewed head SHA, head-lineage identifier, completed maintenance-attempt
count, candidate key when applicable, and last publication operation. A
discovery PR body additionally carries exactly one canonical
`snowcast-discovery-origin` marker with the candidate key, origin fingerprint,
proposal fingerprint, and regional graph key. Routing a proposal or suppressing
a duplicate requires that marker to match exactly one trusted maintainer
summary authored by `lampssy`, including the PR's current head SHA. Removing
the proposal label does not erase this discovery provenance.

The helper validates machine state before use. Missing or stale curation state
routes the current head through a fresh review; malformed or ambiguous trusted
state fails closed, and no missing-state recovery repeats an already evidenced
push. Human-visible prose is never parsed as control data.

## Curation PR Workflow

### Eligibility and selection

A PR is eligible only when all of the following hold:

- it is open in the Snowcast repository and targets `main`;
- its head repository is the Snowcast repository, not a fork;
- its head branch starts with `codex/`;
- it is a catalog-curation PR identified by `lane:catalog-curation` or by a
  deterministic catalog-change classifier that can assign that lane;
- it does not carry `maintainer:proposal`;
- no other maintainer mutation lock is held;
- the current remote head SHA matches the SHA selected for the run.

An ambiguous multi-lane diff is not auto-classified. It receives
`maintainer:manual-check`. Among eligible PRs, the oldest PR able to make
progress is selected. Waiting-CI reconciliation remains lightweight and does
not consume the one deep-processing slot.

### Guarded synchronization

Before semantic review, the helper:

1. writes a selected-attempt artifact containing an opaque attempt ID, selected
   head, and CLI-owned lineage/cycle seed before git preparation begins;
2. validates the repository, effective fetch and push URLs, current worktree,
   clean state, PR provenance, branch, base, and exact selected head;
3. fetches the exact PR head and current `origin/main`;
4. records the original head SHA and creates a persistent local backup ref;
5. rebases the branch onto the fetched `origin/main` with autostash and
   update-refs disabled in the isolated worktree;
6. stops without conflict resolution if rebase reports a conflict;
7. compares pre- and post-rebase intent, including changed paths, file modes,
   catalog targets, curation-report targets, and backlog markers;
8. promotes the attempt to a prepared artifact only when preparation completes;
9. runs the fixed catalog validator, schema-version-2 report/backlog/trust
   reconciliation, and focused catalog tests against the prepared and reviewed
   state; executable Python/test changes are outside automated curation scope;
10. revalidates the immutable prepared intent before and after every validation
   command and rechecks the remote PR head before any push.

Any conflict, remote-head mismatch, missing target, unexpected file expansion,
or semantic drift stops the mutation path. The original branch remains remote,
and the backup ref preserves its selected SHA locally.

### Review and remediation

After synchronization, a fresh catalog review evaluates the complete rebased
diff against the repository, report contracts, source evidence, and official
source pages. A remediation cycle may automatically fix:

- source-backed corrections within the existing catalog model;
- missing in-scope destinations, stay bases, ski areas, access edges, domains,
  pass relationships, evidence records, trust-manifest entries, and report
  coverage when their boundaries are already established;
- curation-report, validation, focused test, and owned documentation defects;
- straightforward CI failures caused by the PR's own catalog changes.

The run must stop for owner review when a fix requires:

- splitting, merging, deleting, or re-keying durable catalog identities;
- a weather-identity or historical-data migration;
- a new schema, domain entity, ownership rule, or product semantic;
- choosing between genuinely conflicting or insufficient sources;
- relying on inaccessible evidence that cannot be independently reviewed;
- expanding beyond the coherent candidate or regional scope;
- resolving a git conflict or overriding another writer's new head;
- changing dependencies, deployment, production configuration, or secrets.

Each remediation is followed by a new independent review. The post-merge skill
allows at most two review/fix cycles inside one scheduled run. Independently,
the helper permits at most three maintenance attempts for one durable head
lineage; the CLI owns and increments that count, and caller-supplied summary
content cannot reset it. Exceeding either limit produces
`maintainer:manual-check` or `maintainer:owner-decision`; it never relaxes the
gate.

### Push and CI reconciliation

If the final review has no blocking finding and all pre-push checks pass, the
helper rechecks the PR policy and remote head. Before network mutation it writes
an exact-authorization push journal bound to the PR, selected head, prepared
state, and reviewed head, then performs at most one push shaped as:

```text
git push --force-with-lease=refs/heads/<branch>:<original-head-sha> \
  origin HEAD:refs/heads/<branch>
```

Plain `--force` is forbidden. When synchronization and review produce the same
head as the selected remote head, the helper verifies local and remote equality,
records consumed authorization, and performs zero network pushes. If a process
stops after authorization or after the network succeeds, a later invocation
uses the journal and observed remote head to retry safely or recover the
already-pushed result without repeating a successful push. A later lineage has
a different authorization identity and is not blocked by the completed
journal.

Publishing `maintainer:waiting-ci` requires matching promoted preparation,
validation, and consumed-push evidence for the PR's current head. Later
scheduled runs reconcile current checks without rewriting the branch. A PR
becomes `maintainer:ready` only when trusted machine state matches the unchanged
reviewed head, required checks pass, the PR is mergeable, and no owner decision
remains. Immediately before any publication, the CLI refetches the complete PR
and rejects changed metadata, paths, labels, state, or head; it then
idempotently synchronizes the canonical report/body/comment and labels.

If checks fail, a later deep run may remediate an in-scope deterministic
failure. Infrastructure failures, ambiguous failures, stale check contracts,
or failures outside the catalog lane produce `maintainer:manual-check` or
`maintainer:blocked` with a concise reason.

## Discovery Workflow

### Candidate funnel

Discovery uses three ordered sources:

1. exact typed `deferred` and `unresolved` markers and regional refinements in
   `docs/product-backlog.md`;
2. entries in a versioned Alpine coverage registry that are not represented by
   the current catalog or an open proposal;
3. open-web research that may nominate a candidate for the registry but cannot
   claim completeness or directly bypass the registry gate.

The coverage registry is a reviewed comparison universe, not a workflow
database. It stores stable candidate keys, geographic grouping, candidate kind,
and source hints. Current state is derived from the catalog, backlog, and GitHub
PR history rather than duplicated in mutable registry status fields.

The initial registry lives at
`docs/catalog-discovery/alpine-coverage-registry.json`. Its versioned entries
contain a stable candidate key, display name, country, Alpine subregion,
candidate kind, and one or more official identity/source URLs. It deliberately
contains no mutable `proposed`, `accepted`, or `rejected` state. A schema
validator rejects duplicate keys, malformed URLs, and unsupported candidate
kinds.

The checked-in seed is a strict 69-entry universe: 52 destination or ski-area
identities already represented in the catalog, with official source hints
inherited from their identity source groups, plus 17 of the 19 active typed
backlog markers. Registry membership and source hints do not assert each
catalog entity's trust status; the corresponding trust group remains
independent and may still be `estimated` or `needs_source`.
`ski_area:gaisberg-kirchberg` and
`ski_area:bichlalm` remain backlog-only because they do not yet have the stable,
reviewable official identity evidence required for registry selection. Registry
validation checks canonical structure, URL safety, and checked-in provenance;
it is not a live availability probe. In particular, the Hintertux registry
identity URLs are retained from the reviewed trust sources, but selection still
requires a fresh live source check and must stop if those pages are unavailable
or no longer support the modeled boundary.

Open-web research may nominate a new candidate only by adding a valid registry
entry inside the same gated proposal PR that contains its full catalog
curation. It cannot modify the registry directly on `main`, create an ungated
catalog PR, or record a candidate supported only by popularity or secondary
listings. Merging the proposal therefore accepts the candidate into both the
comparison universe and the catalog in one owner-reviewed change.

A candidate is skipped when it already exists in the catalog, overlaps an open
proposal's regional graph, lacks a stable official identity or reviewable
sources, or was declined in a closed proposal without new evidence. Proposal
PR bodies carry the candidate key and source/backlog fingerprint so a changed
source record can deliberately reopen consideration without immediate
rediscovery loops. Decline history is read from all paginated closed PRs that
still carry `maintainer:proposal`; suppression requires valid Snowcast PR
provenance, the canonical origin marker, and its matching trusted current-head
summary rather than title or human prose.

Candidate selection, backlog-source enrichment, and bounded nominations write
candidate artifacts in the private state directory. `discovery next`,
`discovery add-source`, and `discovery nominate` therefore require the active
discovery-worker lease ID, which the helper binds to owner-only state. The
worker keeps that lease and heartbeats through the source research phase; it
does not release the lease between selection and enrichment. When the queue is
exhausted, the CLI deterministically rotates one Alpine subregion for a bounded
nomination scan.

### Proposal creation and approval

For one selected candidate, the discovery automation runs the existing full
catalog-curation workflow on an exact `codex/catalog-curation-<scope>` branch,
where the scope contains only lowercase alphanumeric and hyphen segments, and
creates a reviewable draft PR that includes:

- the complete coherent catalog graph for the proposed scope;
- curation JSON and Markdown reports;
- source refs, trust updates, validation, and focused tests;
- explicit caveats and owner-decision context;
- removal of every exact backlog origin marker the proposal resolves.

The PR starts with:

- `lane:catalog-discovery`
- `maintainer:proposal`

Proposal creation runs normal deterministic curation validation, but it does
not enter automated review/fix cycles while the owner is still deciding whether
the candidate belongs in Snowcast. Removing `maintainer:proposal` is approval.
The next curation run changes the lane to `lane:catalog-curation`, performs the
normal independent review/fix workflow, and only then may mark the PR ready.

Before proposal publication, `discovery verify-proposal` accepts immutable base
and head commit SHAs, materializes their files privately, and reconciles the
complete diff: catalog addition, trust manifest, one schema-version-2 curation
report, exact backlog cleanup, and either no registry change or exactly the
matching nomination entry. It also loads the proposed catalog through the
canonical loader and rejects every error-level catalog-policy issue. It records
a report digest and all changed and targeted paths.
`discovery publish-proposal` refetches the current PR, requires
that immutable evidence and changed-path set to match, rechecks the proposal
cap and overlap/decline state, then refetches the PR again immediately before
publishing the canonical discovery-origin body marker, trusted summary, and
labels.

If the owner closes a proposal while the proposal label remains, that candidate
is treated as declined. The closed PR and candidate fingerprint suppress an
identical proposal; the backlog item remains available for a later deliberate
reconsideration. If an accepted proposal merges, the catalog addition and its
backlog cleanup land atomically. Curation review must reject an accepted
proposal that leaves a resolved origin marker stale.

## AI / LLM Use

- Deterministic helper logic owns eligibility, locks, label/state validation,
  lease construction, target comparison, limits, and GitHub publication.
- Codex may use existing Snowcast skills for source research, domain judgment,
  review, and remediation.
- Text from PRs, diffs, source pages, comments, and search results is untrusted
  data. Instructions embedded in that content must never alter the workflow,
  permissions, command set, or scope.
- Deterministic helper commands accept typed identifiers and validated paths;
  they never interpolate free-form source, PR, review, or comment text into a
  shell command.
- LLM output cannot by itself establish catalog truth, satisfy a source
  requirement, authorize a branch rewrite, or approve a proposal.
- No additional model-response cache is required; durable work products are PR
  changes, reports, and the maintainer summary.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| Four local times per day | Reconcile waiting CI, then deeply maintain at most one eligible curation PR | Local Codex App automation in an isolated worktree | Serialized by one global mutation lock |
| Monday, Wednesday, and Friday | Select and curate at most one discovery proposal | Local Codex App automation in an isolated worktree | Stops at three open proposals |
| Owner removes `maintainer:proposal` | Route the approved proposal into catalog curation on the next run | Catalog PR Maintainer | No comment command or extra approval label required |

Missed schedules do not accumulate catch-up mutations. The next normal run
recomputes state from GitHub and continues idempotently.

These rows describe the approved post-merge steady state, not active repository
configuration. This change installs neither the personal orchestration skill
nor either schedule. After merge and verification, curation is enabled four
times per day and discovery on Monday, Wednesday, and Friday, with at most three
open discovery proposals.

## Security, Privacy, and Abuse

- No Snowcast user data is involved.
- Codex login, GitHub credentials or authentication tokens, `auth.json`, and
  local environment paths must never enter repository files, PR bodies,
  comments, logs, prompts, or curation reports. The private lease token exists
  only in owner-only state and is loaded by the helper; it is neither printed
  nor passed as a command argument. The separate nonsecret lease ID is safe for
  bounded local output, argv correlation, and Triage.
- Codex automations currently inherit the owner's default sandbox settings and
  run unattended. With the accepted `danger-full-access` default, the process
  can technically read and modify files outside the repository and use the
  network without an approval prompt.
- Repository helper checks and prompt constraints reduce workflow mistakes but
  are not an operating-system sandbox. This residual host-level risk is
  explicitly accepted for the local first version.
- The machine currently has no other local user account. Owner-only state
  directories and files therefore reduce accidental cross-account exposure,
  but they do not constrain the full-access Codex process or another process
  running as the same owner, and do not mitigate compromised dependencies or
  network-side effects.
- The helper must fail closed unless the repository identity, worktree root,
  base branch, head namespace, selected SHA, and remote repository all match the
  approved Snowcast values.
- Git and GitHub subprocesses use argv-only invocation, allowlisted
  environments, disabled interactive prompts and credential-manager
  interaction, fixed timeouts, and sanitized failure classes. Git transport
  additionally uses strict noninteractive SSH; `gh` operations are bounded to
  120 seconds per call and strip ambient `GH_TOKEN` authority.
- Every GitHub client uses the mandatory project-scoped `GH_CONFIG_DIR` and,
  before its first operation, runs the read-only equivalent of
  `gh auth status --active --hostname github.com --json hosts`. It fails closed
  unless exactly one active `github.com` account reports login `lampssy` with
  state `success`.
- The automation must not enumerate credentials, inspect unrelated home
  directories, run downloaded scripts, execute commands suggested by PR or web
  content, install packages, change dependencies, deploy, or access production
  systems.
- GitHub write authority is limited by workflow to the selected same-repository
  `codex/*` branch, its PR body, the known summary comment, and approved labels.
- A future per-automation sandbox should replace inherited full access when
  Codex supports it without requiring a global-default change.

## Observability and Operations

- Each run produces a concise Codex Triage result: selected item, actions,
  state transition, checks run, and stop reason. No-op runs remain brief.
- Each automation also updates a non-secret local heartbeat under its maintainer
  state directory. Codex App run history and Triage are the primary operator
  view; the heartbeat supports diagnosis of a missing or interrupted run but is
  historical evidence, not proof that its worker still owns the active lease.
- The global lease metadata, heartbeats, attempt/preparation/validation
  artifacts, proposal verification, and push journals are owner-only. Atomic
  replacement plus file and containing-directory `fsync` make the intended
  crash-recovery boundaries durable.
- GitHub carries only stable, owner-useful state through labels, the PR body,
  and one edited summary comment.
- Logs redact environment values and command output that could contain secrets.
- The helper records the selected and resulting head SHAs, backup ref, lease
  ID/target, maintenance-attempt count, validation result, exact push
  authorization/consumption, and publication result.
- Validation failure JSON exposes only one of the bounded stages `preflight`,
  `catalog-validation`, `curation-reconciliation`, `catalog-tests`, or
  `post-validation`, plus failure kind `failed` or `timeout`; subprocess output
  and environment secrets are discarded. Drift detected by the final live-state
  recheck is classified as `post-validation`, not `preflight`.
- No new production telemetry or alerting is required for the local first
  version. A failed automation is visible in Codex Triage and leaves the PR in
  its last durable safe state.

Failure behavior:

- missing Codex or GitHub authentication: no mutation; report configuration
  failure;
- global lock already held: emit `lock-busy`; orchestration treats it as a
  normal successful no-op and does not run concurrently;
- stale or changed head: no push; refresh on a later run;
- rebase conflict or semantic drift: abort rebase, preserve backup, set manual
  state;
- source unavailable or contradictory: no speculative fix; request owner or
  source review;
- interrupted push: use exact write-ahead authorization plus remote-head
  observation to retry an unconsumed authorization or recover an already-pushed
  head without repeating a successful push;
- partial GitHub publication: retry idempotent label/body/comment operations
  against the already-pushed SHA; never repeat the force-push;
- CI pending: retain `maintainer:waiting-ci`;
- automation limit reached: stop and expose the limit and remaining issue.

## Acceptance Criteria

- The two local automations can be configured without storing a Codex API key
  or GitHub token in the repository.
- The curation automation runs four times per day, reconciles waiting CI, and
  deeply processes at most one PR per run.
- The discovery automation runs Monday, Wednesday, and Friday, creates at most
  one proposal per run, and never exceeds three open proposal PRs.
- An eligible same-repository `codex/*` catalog PR needs no opt-in management
  label.
- Forks, non-`codex/*` branches, non-`main` bases, proposals, ambiguous lanes,
  and stale heads cannot reach the mutation path.
- Rebase conflict, unexpected intent change, or remote-head movement prevents a
  push.
- Every rewrite creates a backup ref and uses an exact-SHA force-with-lease;
  plain force is impossible through the helper.
- Review/fix cycles are fresh and bounded to two per run; deterministic
  maintenance attempts are bounded to three per lineage, and both limits stop
  for the listed domain and source decisions.
- A PR is ready only for the exact reviewed SHA with green required checks and
  no unresolved owner action.
- Labels, PR body, and the single marked summary comment remain idempotent and
  mutually consistent.
- Removing `maintainer:proposal` routes an approved proposal into curation;
  no merge or approval occurs automatically.
- A backlog-origin proposal cannot merge while leaving its resolved candidate
  marker behind.
- Closed declined proposals are not recreated from an unchanged candidate
  fingerprint.
- The checked-in Alpine registry contains exactly 69 entries, covers 17 of 19
  active backlog markers, distinguishes source hints from catalog trust status,
  and leaves Gaisberg and Bichlalm backlog-only until sourceability is
  established.
- `discovery next`, `add-source`, and `nominate` cannot mutate candidate
  artifacts without the current discovery lease ID bound to the matching
  state-file token. The ID is nonsecret and may use stdout/argv; the private
  token cannot.
- Proposal publication accepts only exact `codex/catalog-curation-*` branches
  and matching immutable catalog/report/trust/backlog/registry evidence whose
  proposed catalog has no error-level policy issue.
- Every automation command uses the project-scoped GitHub CLI profile and all
  GitHub operations fail before mutation unless the active successful login is
  exactly `lampssy`.
- The deterministic helper does not derive policy, authorized repositories,
  branch scope, or command templates from untrusted PR or web text. Full-access
  model execution remains an explicitly accepted residual risk rather than an
  enforceable helper guarantee.
- The repository change does not install the personal skill or schedules. Only
  after merge and post-merge verification do the automations begin at the
  approved steady-state frequencies; no staged operational pilot is required.

## Verification

- Unit tests for PR eligibility, state transitions, proposal limits, candidate
  fingerprinting, cycle limits, and summary rendering.
- Temporary-repository integration tests for successful rebase, rebase
  conflict, backup-ref creation, intent drift, stale remote head, and exact
  lease construction.
- Mocked GitHub tests for label exclusivity, body synchronization, idempotent
  comment update, partial publication retry, CI transitions, and closed-proposal
  suppression.
- Catalog integration tests for discovery proposal validation and atomic
  backlog-marker cleanup.
- Security tests proving helper rejection of the wrong repository, fork heads,
  non-`codex/*` branches, unexpected remotes, and command data derived from
  untrusted content.
- Focused lint and test commands use existing `uv run` conventions.
- Scoped post-review evidence: all 589 maintainer tests passed after the stale
  lease-adoption fix in commit `910c2ee` (following `e2e1b92` and the broader
  advisory fixes in `090ec67`). This is focused evidence for the helper changes,
  not the final full repository verification required before publication.
- A current read-only check of the project-scoped GitHub CLI profile found
  exactly one active successful `lampssy` login backed by the local keyring; no
  token value or scopes were recorded. The replacement activation checklist
  repeats that check after merge before activation.
- One final configuration inspection verifies the two Codex App schedules,
  worktree mode, repository path, model settings, Triage destination, and local
  authentication availability before enabling them.
- Activation order is fixed: merge the repository helper and contracts; install
  the personal orchestration skill; run automated verification and configuration
  inspection; then enable both automations immediately at their steady-state
  frequencies.
- No dry-run-only week, manual-per-PR pilot, or gradual frequency ramp is part
  of rollout.

## Advisory Review

- Design reviewers: Data Trust & Source Integrity; Security & Privacy; Release
  & Change Management; Observability & Operations.
- Design-review result: completed with no Blocker or High findings. Medium
  ambiguities around registry ownership, durable cycle state, security wording,
  activation order, and interrupted-run diagnosis were resolved in this spec.
- Repository feature-review outcomes:
  - Data Trust & Source Integrity: **Ship; address both Medium findings before
    enabling the post-merge automations.** Proposal verification now enforces
    catalog policy, and this spec now distinguishes registry source hints from
    independent catalog trust status.
  - Security & Privacy: **Ship after fixes.** Commit `090ec67` removed raw lease
    credentials from stdout/argv, bound GitHub to an exact verified `lampssy`
    profile, removed executable test paths from automated curation scope, and
    constrained validation environments and failure output; commit `e2e1b92`
    then bound private credentials to the expected worker, and `910c2ee` added
    per-acquisition lease-ID correlation without exposing the token.
  - Release & Change Management: **Ship after fixes.** Commits `090ec67` and
    `e2e1b92`, the `910c2ee` stale-adoption fix, and the operations/recovery
    runbook resolve the repository-scoped conditions, while activation remains
    blocked behind merge, installation, verification, and the replacement
    activation review.
  - Observability & Operations: **Ship after fixes.** Commit `090ec67` adds
    bounded validation stage/failure output and a distinct `lock-busy` no-op;
    this documentation clarifies historical heartbeat semantics and recovery.
- Follow-up quality review: the **High** stale same-worker lease-adoption risk is
  resolved by requiring the new nonsecret lease ID to match both private state
  records, so an old ID cannot operate on a successor lease. The **Low** final
  validation-drift classification is resolved by emitting
  `validation_stage=post-validation`. Both fixes are in `910c2ee`.
- All repository-scoped High findings and directly scoped Medium conditions
  are resolved by commits `090ec67`, `e2e1b92`, `910c2ee`, and this
  documentation. The runbook handles the scoped Low recovery/heartbeat concern.
  Exact Codex App pause-control UI wording, the installed personal skill, and
  the actual automation records do not exist yet and remain mandatory inputs to
  the replacement post-merge activation review; this feature review does not
  claim to cover them.
- Known residual risks:
  - inherited `danger-full-access` is a host-level risk that workflow checks
    cannot eliminate;
  - local scheduling depends on machine and Codex availability;
  - source research can still miss a candidate or misread a boundary, so owner
    proposal review and fresh catalog review remain necessary;
  - local backup refs do not replace external backups if the machine is lost;
  - GitHub and source-site behavior can change independently of the helper.

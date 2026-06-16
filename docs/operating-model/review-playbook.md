# Snowcast Advisory Review Playbook

Use this playbook to choose advisory reviewers without slowing down normal solo
development. Reviewer definitions live in
`docs/operating-model/advisory-reviewers.md`. Feature-spec guidance lives in
`docs/operating-model/feature-spec-template.md`. Candidate ideas that are not
active commitments live in `docs/product-backlog.md`. Durable decisions live in
`docs/architecture/adr/`, and shared domain terms live in
`docs/domain-language.md`.

## Framework Maintenance

When changing the operating model itself, keep the framework entry points aligned:

- update `AGENTS.md` when the default Codex behavior, Superpowers usage, advisory
  review trigger, or documentation ownership rule changes
- update this playbook when routing, checkpoints, Superpowers integration, or
  workflow sequencing changes
- update `docs/operating-model/feature-spec-template.md` when specs need a new
  required section, decision gate, or review input
- update `docs/operating-model/advisory-reviewers.md` when reviewer contracts,
  modes, severities, or review gates change
- update `README.md` and `PROJECT.md` when the docs map or primary entry points
  change
- update `docs/engineering-notes.md` when the change creates durable engineering
  vocabulary, repo-specific learning, or a framework convention worth preserving
- update `docs/architecture/adr/` when the framework change is a durable decision
  with meaningful alternatives or long-lived consequences
- update `docs/domain-language.md` only when the change introduces or changes
  durable product/domain terms, bounded contexts, or invariants
- update the Snowcast advisory skill only when skill invocation, required context,
  or routing behavior changes; reviewer definitions must remain in repo docs

## Default Routing

Before non-trivial implementation, classify the task as either `fast path` or
`review-gated`.

- `fast path`: small, local, reversible, and outside high-risk domains.
- `review-gated`: affects durable product behavior, user trust, data
  correctness, persistence, shared API contracts, request-path performance,
  production reliability, security/privacy, observability, external
  integrations, or future maintenance patterns.

If unsure, choose `review-gated`. The project prefers reviewers being invoked
too often rather than too rarely.

For `review-gated` work, record a Decision and Review Gate in the spec, plan, or
final handoff before implementation starts. The gate should state:

- classification: `review-gated`
- high-risk domains touched
- Developer Decision Checkpoint status
- ADR status
- advisory design-review status
- advisory feature-review status before final handoff
- reason for any skipped advisory review

Skipping advisory review for `review-gated` work should be explicit and rare.

### Small Scoped Fix

Examples:

- copy tweaks
- focused test updates
- one-file bug fixes
- minor docs cleanup

Default:

- no advisory review
- inspect directly relevant files
- run focused tests or lint

Fast path applies only when the change is small, local, reversible, and outside
high-risk domains.

Examples that normally make a change `review-gated`:

- database schema, indexes, migrations, or repository query shape
- request-path performance, memory pressure, or production reliability
- planning, ranking, scoring, evidence selection, or model semantics
- auth, user data, public endpoints, deploy config, scheduled jobs, or
  privacy-sensitive logging
- evidence/trust wording, LLM behavior, acquisition pipelines, telemetry, or
  external integrations

If a change hits any review-gated domain, do not treat it as a small scoped fix.
Record at least a lightweight Decision and Review Gate before implementation.

Fast-path small changes do not need reviewers. If a small change touches a
high-risk domain such as auth, user data, planning/ranking semantics, catalog
trust, deploy config, or privacy-sensitive logging, classify it as
`review-gated` and use the relevant reviewer set.

### Normal Feature

Default:

- run one to three relevant reviewers manually
- create or update a short feature spec before coding when the feature creates
  durable product behavior or touches a high-risk domain
- capture Developer Decision Checkpoints for material technical, product/domain,
  or mixed choices that should stay owner-visible before implementation
- if the idea came from `docs/product-backlog.md`, link the backlog item from
  the feature spec and update its status
- identify whether the spec needs an ADR or domain-language update
- use `design-review` before coding when the feature changes architecture,
  product behavior, or user-facing model semantics
- use `feature-review` before final handoff when the feature touches a critical
  path

Examples:

```text
Run backend-api and security-privacy design-review on this proposal.
```

```text
Run data-trust-source-integrity feature-review on the current diff.
```

### Sprint-Sized Feature

Default:

- create a feature spec under `docs/superpowers/specs/` using the existing
  date-prefixed naming style
- resolve or explicitly accept Developer Decision Checkpoints before planning
- add proposed ADRs for durable architecture decisions when the spec needs them
- run the core panel in `design-review` before implementation
- convert the accepted spec into a Superpowers implementation plan
- run selected reviewers in `feature-review` before final handoff

Core panel:

- product-strategy
- backend-api
- data-trust-source-integrity
- ui-ux
- security-privacy
- observability-ops

### High-Risk Change

Always use `review-gated` classification and relevant advisory review when
touching:

- auth, sessions, identity, or user trip data
- planning, ranking, scoring, thresholds, or model wording
- catalog data, source refs, acquisition, or trust manifests
- parser, narrative, prompts, LLM fallback, or LLM-assisted extraction
- deploy, CI/CD, migrations, production config, or secrets
- observability, logging, metrics, traces, or telemetry
- public SEO pages, sitemap/robots, or booking handoff
- mobile companion flows, device registration, or push-readiness

## Developer Decision Checkpoints

Use checkpoints to preserve solo-builder ownership and learning. They apply to:

- `Technical`: indexes, schema boundaries, API contracts, caching, background
  work, migrations, deploy shape, observability, and error handling.
- `Product / Domain`: ranking semantics, thresholds, source trust, uncertainty
  display, alert policy, booking handoff, and product positioning.
- `Mixed`: choices that affect both product behavior and system shape, such as
  request-path versus background evaluation or deterministic logic versus LLM
  assistance.

Before non-trivial implementation, classify the work with this quick checklist:

- Is it small, local, reversible, and outside high-risk domains?
- Does it affect durable product behavior or user trust?
- Does it affect data correctness, persistence, shared API contracts,
  request-path performance, production reliability, security/privacy,
  observability, external integrations, or future maintenance patterns?

If the answer is not clearly fast path, classify the work as `review-gated`.
Present checkpoints before coding or explicitly record accepted assumptions.
Checkpoints can be short in chat for focused changes; they do not always require
a full feature spec.

For non-trivial work, present one to three meaningful checkpoints before
implementation. Include close-to-default technical choices when they are useful
for learning, but group them and keep the decision surface proportional.

Use this table in feature specs and, when needed, in implementation plans:

```markdown
| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
```

If no material checkpoints exist, state the rationale briefly. If a checkpoint
has long-lived consequences, add or link an ADR after the owner accepts the
decision.

## Change-Type Routing

| Change type | Reviewers |
| --- | --- |
| Search/API behavior | backend-api, product-strategy, performance |
| Planning/ranking model | data-trust-source-integrity, product-strategy, backend-api |
| Catalog/source acquisition | data-trust-source-integrity, backend-api, ai-llm-reliability when LLM extraction changes |
| Parser/narrative/LLM | ai-llm-reliability, backend-api, security-privacy when user text/logging is involved |
| Web planning UI | ui-ux, accessibility, product-strategy |
| Public resort pages | growth-seo, data-trust-source-integrity, accessibility |
| Auth/current-trip/user data | security-privacy, backend-api, mobile-companion when mobile is affected |
| Mobile companion | mobile-companion, security-privacy, backend-api |
| Deploy/ops/config | observability-ops, release-change-management, security-privacy |
| Booking/affiliate handoff | monetization-partnerships, product-strategy, security-privacy |

## Superpowers Integration

### Brainstorming

For non-trivial features, use brainstorming to shape the feature spec and
identify Developer Decision Checkpoints. Present meaningful options neutrally
first when the purpose is owner learning; review the owner's chosen direction
before converging on the design.

Run relevant reviewers in `design-review` before the design is finalized when
the feature touches high-risk domains.

Do not run broad `domain-audit` automatically.

### Planning

Implementation plans should be derived from the accepted feature spec when one
exists. Plans should include the Decision and Review Gate for `review-gated`
work. If the spec introduced ADRs or domain-language updates, the plan should
include the corresponding doc edits.

Before writing or executing a Superpowers plan, confirm that Developer Decision
Checkpoints are resolved or explicitly accepted as assumptions. For
review-gated, sprint-sized, or high-risk plans, add a short section near the
plan header:

```markdown
## Decision Gate Before Execution

- Classification: fast path / review-gated
- High-risk domains touched:
- Resolved owner decisions:
  - ...
- Accepted assumptions:
  - ...
- Unresolved owner decisions:
  - None
- ADR status:
- Advisory review status:
```

If unresolved owner decisions remain, stop before task decomposition and ask the
user to choose or accept an assumption.

### Implementation

Before final handoff, run relevant reviewers in `feature-review` for
sprint-sized, product-facing, high-risk, or otherwise `review-gated` changes.

Small focused fast-path fixes can skip advisory review.

For medium/high-risk changes, final handoff should include:

- fast path or review-gated classification
- Developer Decision Checkpoint resolved, or explicitly accepted as an assumption
- ADR added, linked, or explicitly not needed
- advisory review run, or explicitly skipped with reason
- verification run and unresolved blockers listed

When executing with subagents, include the resolved checkpoint context in
subagent prompts. Subagents should return `BLOCKED` instead of silently choosing
when a task exposes a new material owner decision.

## Invocation Examples

```text
Use $snowcast-advisory-review to run product-strategy, backend-api, and
data-trust-source-integrity design-review on
docs/superpowers/specs/2026-06-15-trip-watch-alerts-design.md.
```

```text
Use $snowcast-advisory-review to run backend-api and security-privacy
feature-review on the current diff.
```

```text
Use $snowcast-advisory-review to run the core panel in design-review mode for
this sprint proposal.
```

```text
Use $snowcast-advisory-review to run a data-trust-source-integrity domain-audit
and identify the top five trust improvements.
```

```text
Use $snowcast-advisory-review to run ui-ux, accessibility, and performance
feature-review on the web route changes.
```

## Dry-Run Standard

When validating the advisory system:

1. Run one `feature-review` against a recent diff or committed feature.
2. Run one `domain-audit` against a single reviewer.
3. Confirm the reviewer reads the repo docs first.
4. Confirm the output uses the required format.
5. Confirm it does not edit code unless explicitly asked.

# Snowcast Feature Spec Convention

Use this convention when a feature is `review-gated`: it creates durable product
behavior, changes a core model, touches a high-risk domain, or would benefit
from explicit owner decisions before implementation. The goal is to give
Superpowers plans and advisory reviewers a concrete artifact to inspect before
implementation.

This is not required for fast-path work: small, local, reversible fixes outside
high-risk domains. If unsure whether the work is fast path or review-gated,
choose `review-gated`.

Feature specs do not replace ADRs or the domain-language document. If a feature
creates a durable architecture decision, add an ADR under
`docs/architecture/adr/`. If a feature introduces or changes core domain terms,
update `docs/domain-language.md`.

## When to Create a Spec

Create or update a short feature spec before coding when the work is
`review-gated`. That includes work affecting durable product behavior, user
trust, data correctness, persistence, shared API contracts, request-path
performance, production reliability, security/privacy, observability, external
integrations, or future maintenance patterns.

Common examples:

- saved trips, trip watches, alerts, or current-trip companion behavior
- planning, ranking, scoring, thresholds, evidence profiles, or canonical model
  wording
- catalog acquisition, source trust, provider data, or public resort claims
- auth, user trip data, sessions, identity, or privacy-sensitive logging
- parser, narrative, prompts, LLM fallback, or LLM-assisted extraction
- database schema, indexes, repository query shape, request-path performance,
  memory pressure, or production reliability
- background jobs, notifications, deploy behavior, migrations, or production
  config
- public SEO pages, sitemap/robots, booking handoff, or affiliate behavior
- mobile companion flows, device registration, push-readiness, or offline state
- monetization, provider partnerships, or user-visible commercial claims

For sprint-sized work, store the spec under `docs/superpowers/specs/` using the
existing date-prefixed naming style. For smaller design-review work, a short
proposal in the chat is acceptable if it answers the same questions.

## Workflow

1. Classify the task as `fast path` or `review-gated`.
2. For `review-gated` work, record the Decision and Review Gate.
3. Use brainstorming to shape the feature and identify the main decisions.
4. Record Developer Decision Checkpoints for material technical, product/domain,
   or mixed choices that need owner review or are useful learning moments.
5. Resolve checkpoints before implementation planning, or mark them as explicit
   assumptions accepted by the owner.
6. If the work comes from `docs/product-backlog.md`, move the backlog item to
   `next` or `spec-ready` and link the new spec from the item.
7. Write or update the feature spec.
8. Identify any ADRs or domain-language updates required by the spec.
9. Run relevant advisory reviewers in `design-review` mode against the spec,
   unless skipped with an explicit reason.
10. Convert the accepted spec into an implementation plan.
11. Implement with focused tests and verification.
12. Run relevant advisory reviewers in `feature-review` mode before final handoff
   when the feature is product-facing, sprint-sized, high-risk, or otherwise
   review-gated.
13. After implementation, mark the backlog item `closed` when keeping that
   history is useful, or remove it if the feature spec and implementation plan
   are enough.

The spec should be concise. Prefer clear decisions and acceptance criteria over
long narrative. Mark sections as `N/A` when they do not apply.

Developer Decision Checkpoints are not only for unusual architecture choices.
Include close-to-default technical choices when they are useful for learning, but
group related choices so the spec does not become a checklist of trivia. If no
material checkpoints exist, state `No material owner checkpoints; rationale: ...`.

## Template

```markdown
# Feature Spec: <Feature Name>

## Status

- Status: draft / accepted / implemented
- Owner: solo-builder
- Related docs:
- Related plan:
- Related ADRs:

## User Outcome

What user-visible outcome should this feature create?

## Scope

In scope:

- ...

Out of scope:

- ...

## Product Fit

- How does this reinforce Snowcast as a ski-only, conditions-smart planner?
- What uncertainty must stay visible to the user?
- What generic travel, generic AI, or unsupported marketplace drift is avoided?

## Domain Model

- Bounded contexts touched:
- Domain terms introduced or changed:
- New or changed entities:
- Important state transitions:
- Invariants that must hold:
- Existing model/spec docs that must stay aligned:

## Decision and Review Gate

- Classification: fast path / review-gated
- High-risk domains touched:
- Developer Decision Checkpoints:
  - resolved:
  - accepted assumptions:
  - unresolved:
- ADR status:
- Advisory design-review:
  - reviewers:
  - status: pending / completed / skipped
  - skipped reason:
- Advisory feature-review before final handoff:
  - reviewers:
  - status: planned / completed / skipped
  - skipped reason:

## Developer Decision Checkpoints

Capture choices that should stay owner-visible before planning locks in the
implementation. Use `Technical`, `Product / Domain`, or `Mixed`.

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| N/A | No material owner checkpoints | Rationale: ... | N/A | N/A | N/A | N/A |

## Architecture Decisions

- Durable decisions made:
- ADRs needed:
- Existing ADRs that constrain this feature:
- Revisit criteria:

## API and Client Contract

- Backend endpoints or response fields:
- Web UI states:
- Mobile companion states:
- Backward compatibility notes:

## Data Trust and Source Integrity

- Data sources:
- Freshness requirements:
- Source refs or evidence required:
- Behavior when data is missing, stale, estimated, or conflicting:

## AI / LLM Use

- Deterministic logic that must not use an LLM:
- Allowed LLM use:
- Prompt/output boundaries:
- Caching, fallback, and cost controls:

## Background Work

Describe any async or scheduled work with the Worker / Function / Trigger
vocabulary from `docs/engineering-notes.md`.

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| N/A | N/A | N/A | N/A |

## Security, Privacy, and Abuse

- User data involved:
- Sensitive fields that must not enter logs, metrics, traces, or prompts:
- Permission or session assumptions:
- Abuse or rate-limit concerns:

## Observability and Operations

- Logs, metrics, traces, or freshness signals:
- Failure modes:
- Retry/idempotency expectations:
- Runbook or alerting updates:

## Acceptance Criteria

- ...

## Verification

- Unit tests:
- API/integration tests:
- UI/manual checks:
- Operational checks:

## Advisory Review

- Design reviewers:
- Feature reviewers:
- Known residual risks:
```

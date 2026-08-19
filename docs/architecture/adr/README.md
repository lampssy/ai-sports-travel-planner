# Architecture Decision Records

Architecture Decision Records capture durable technical and product-architecture
decisions for Snowcast.

Use ADRs when a decision has meaningful alternatives, long-lived consequences,
or future revisit criteria. Do not use ADRs for every task, UI copy choice, or
small implementation detail.

## Relationship To Other Docs

- Feature specs answer: what should this feature do?
- Implementation plans answer: what files, tasks, and tests will change?
- ADRs answer: what durable decision did we make, why, and what tradeoff did we
  accept?
- Developer Decision Checkpoints in feature specs answer: what meaningful
  options should the owner review before implementation planning?
- `docs/engineering-notes.md` remains a curated knowledge file. It may summarize
  a decision, but the ADR is the stable source for the decision record.
- `docs/domain-language.md` defines core Snowcast terms, bounded contexts, and
  invariants. ADRs should use those terms consistently.

## When To Write An ADR

Create an ADR when a decision affects:

- backend architecture or domain boundaries
- persistence model, migration strategy, or database access pattern
- request-path versus background work
- ranking, planning, trust, source integrity, or model semantics
- LLM ownership, prompt boundaries, fallback policy, or AI safety constraints
- deploy, observability, production operations, or failure handling
- mobile versus web product responsibility
- provider, booking, affiliate, or integration boundaries

Concrete examples that usually need an ADR:

- adding a request-path database index or changing index strategy
- moving filtering, aggregation, or ranking evidence selection across SQL,
  Python, cache, or background-job boundaries
- changing how planning evidence is selected, summarized, labeled, or trusted
- changing whether work runs during an API request, scheduled job, or manual
  operator command
- introducing or removing a cache that changes freshness, invalidation, or
  fallback behavior
- changing public-page rendering, sitemap, or booking-handoff architecture

Do not create an ADR for:

- routine bug fixes
- narrow refactors that do not change a boundary or policy
- temporary implementation details already captured in a plan
- feature behavior that is fully covered by a feature spec and has no durable
  architecture consequence

## Naming

Use monotonically increasing numbers:

```text
docs/architecture/adr/
  0001-adopt-lightweight-adrs.md
  0002-keep-ranking-deterministic.md
```

Use lowercase kebab-case after the number.

## Status

Use one of:

- `proposed`: not accepted yet
- `accepted`: current decision
- `superseded`: replaced by a later ADR
- `deprecated`: no longer recommended, but not directly replaced

Prefer adding a new ADR when a decision changes. Update the old ADR status and
link to the replacement instead of rewriting history.

The current highest ADR number is `0021`.

## Workflow

1. During brainstorming or feature-spec work, identify durable decisions that
   need owner review through Developer Decision Checkpoints.
2. Run relevant advisory reviewers in `design-review` mode when the decision is
   high-risk or cross-domain.
3. Write the ADR once the owner accepts a durable decision with meaningful
   alternatives or long-lived consequences.
4. Link the ADR from the feature spec, implementation plan, or engineering note
   that depends on it.
5. Revisit the ADR only when its stated revisit criteria happen or a later
   decision supersedes it.

## Template

Copy `0000-template.md` and replace the number and title.

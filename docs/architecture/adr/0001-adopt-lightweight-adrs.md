# ADR 0001: Adopt Lightweight ADRs

Status: accepted
Date: 2026-06-15

Supersedes: N/A
Superseded by: N/A

Related specs:
- N/A

Related docs:
- `docs/operating-model/feature-spec-template.md`
- `docs/engineering-notes.md`
- `docs/domain-language.md`

## Context

Snowcast already uses feature specs, implementation plans, engineering notes,
and advisory review. Those docs cover feature behavior, execution steps, and
curated technical knowledge, but they do not separately preserve durable
decisions with their alternatives and consequences.

As the project grows, decisions such as request-path versus background work,
deterministic ranking versus LLM ownership, provider boundaries, and persistence
strategy need to remain easy to find and revisit without turning every feature
spec into a permanent architecture record.

## Decision

Use lightweight Architecture Decision Records under
`docs/architecture/adr/` for durable architecture and product-architecture
decisions.

ADRs are required only when a decision has meaningful alternatives, long-lived
consequences, or explicit revisit criteria. Feature specs may identify that an
ADR is needed, but they do not replace the ADR when the decision is durable.

## Consequences

Durable decisions get a stable home with context, consequences, alternatives,
and revisit criteria.

Feature specs can stay focused on user outcomes and behavior instead of
becoming long-term architecture logs.

The process adds one more documentation artifact, so ADRs must stay selective.
Routine implementation choices, small fixes, and temporary plan details should
not become ADRs.

## Alternatives Considered

- Keep decisions only in feature specs. This is simple, but makes old specs carry
  permanent architecture weight and makes decisions harder to find later.
- Keep decisions only in `docs/engineering-notes.md`. This keeps one knowledge
  file, but does not force alternatives, consequences, or revisit criteria.
- Use a heavier RFC process. This is too much ceremony for a solo-builder
  project at the current stage.

## Revisit When

Reconsider this convention if ADRs become mostly unused, if they duplicate
feature specs without adding decision value, or if the project grows enough to
need a fuller RFC process.

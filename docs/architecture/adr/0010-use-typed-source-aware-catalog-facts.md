# ADR 0010: Use Typed Source-Aware Catalog Facts

Status: accepted
Date: 2026-07-04

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md`

Related docs:
- `docs/domain-language.md`
- `docs/data-trust-model.md`
- `docs/architecture/adr/0009-normalized-trip-market-catalog.md`

## Context

`StayBase.base_type` is an unconstrained string and destination/base
`atmosphere_tags` mix settlement form, character, access, terrain, amenities,
and geography. Missing evidence must remain distinguishable from verified
absence, and independently sourced facts need independent trust state.

## Decision

Use small frozen Pydantic value objects owned by `SkiArea`, `StayBase`, and
`TerrainDomain`. Store typed values in the canonical catalog and keep source
references plus verification status in the trust manifest. Mirror each nested
fact through a dedicated JSON projection column. Replace free-form atmosphere
tags with controlled `BaseType`, `BaseCharacterFact`, and scoped apres profiles.
Move catalog and trust contracts together from version 1 to version 2 through a
deterministic audited migration.

## Consequences

Values become constrained, source scope remains visible, and missing data is
explicit. Curation and persistence gain more fields and validation. Existing
atmosphere tags are retired rather than retained as an untyped compatibility
escape hatch.

## Alternatives Considered

- Nullable booleans cannot preserve unknown, season, count, percentage basis,
  or intensity consistently.
- A generic attribute registry weakens typing, ownership, persistence clarity,
  and exact curation coverage.
- Relational child tables for every small fact are disproportionate to this
  static catalog and its current projection pattern.

## Revisit When

- Venue-level requirements justify first-class venue entities.
- One base/area pair needs independently queryable parallel access modes.
- Fact volume or query patterns make JSON projection unsuitable.
- A fact needs operational freshness beyond review-time season metadata.

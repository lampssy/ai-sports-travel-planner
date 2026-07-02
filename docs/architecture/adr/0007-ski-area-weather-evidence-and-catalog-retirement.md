# ADR 0007: Use Ski Areas As Weather Evidence Entities And Retire Catalog Rows

Status: accepted
Date: 2026-06-25

Supersedes: N/A
Superseded by: ADR 0009 for catalog topology; ski-area evidence keys and soft
retirement remain active

Related specs:
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`

Related ADRs:
- `docs/architecture/adr/0009-normalized-trip-market-catalog.md`

Related docs:
- `docs/domain-language.md`
- `docs/planning-model.md`
- `docs/snow-evidence-model.md`

## Context

Snowcast stores slow-changing destination and terrain catalog data in
`app/data/resorts.json` and bootstraps that seed into Postgres during deploy.
Historical weather archive rows and derived snow climatology are expensive to
build and are used as planning evidence.

The original bootstrap sync deleted catalog resorts and ski areas that were no
longer present in the current seed. Historical weather tables referenced
`ski_areas(ski_area_id)` with `ON DELETE CASCADE`, so catalog reshaping could
silently delete archive and climatology evidence. This risk became visible while
refining the Chamonix and shared-domain model: changing ski-area structure is a
normal catalog evolution, but it must not destroy weather history unless that is
an explicit rebuild or migration.

At the same time, Snowcast needs clear domain semantics:

- Chamonix Mont-Blanc is a destination with multiple distinct local ski areas.
- Tignes and Val d'Isere are separate destinations and ski areas inside a shared
  linked terrain domain.
- Weather evidence should describe the selected skiable terrain, not a broad
  marketing destination label.

## Decision

Use `ski_area_id` as the durable weather evidence entity.

Normal archive history, current weather refresh, and derived climatology are
keyed to ski areas. Destination, terrain-group, and terrain-domain records can
organize display, accessible terrain, lift-pass coverage, and grouping, but they
do not own weather rows.

Current condition rows keep the ski-area display name as metadata only.
Refresh, search, public resort pages, and current-trip summaries retrieve them
by `ski_area_id`. The display name is not unique and must not be used as a
durable lookup key.

Make normal catalog bootstrap non-destructive for resorts and ski areas:

- current seed rows are inserted or updated with `is_active = TRUE`;
- missing seed resorts and ski areas are marked `is_active = FALSE`;
- normal catalog reads return only active resorts and ski areas;
- historical weather foreign keys use `ON DELETE RESTRICT` instead of
  `ON DELETE CASCADE`;
- `reset_database()` remains the explicit destructive full rebuild path.

If a ski area is split, merged, or renamed, existing evidence stays attached to
the old inactive `ski_area_id`. Moving evidence to a new ID requires a reviewed
data migration because the semantics may have changed.

## Consequences

Deploy bootstrap can safely reflect catalog changes without deleting archive or
climatology rows.

Search, data-quality audit, weather backfill, and climatology rebuild continue to
operate on active catalog ski areas by default through repository reads.

Retired ski areas remain in Postgres. They are hidden from normal product reads
but preserve evidence for auditability and future reviewed migration.

Catalog ID changes now need care. Reusing or renaming IDs is no longer a casual
cleanup; it is a data migration decision.

The database retains more rows over time. A future explicit maintenance command
may be needed to list retired entities and delete them only after evidence has
been intentionally migrated or deemed obsolete.

## Alternatives Considered

- Keep cascade deletes and rely on careful catalog edits. Rejected because
  deploy-time bootstrap should not be able to destroy costly evidence silently.
- Change only the foreign keys to `ON DELETE RESTRICT`. This prevents silent
  deletion, but normal deploys would fail whenever the catalog removes or
  reshapes a weather-backed ski area.
- Attach weather to destinations or terrain domains. Rejected because broad
  destination/domain labels can hide materially different terrain, elevation,
  operations, and snow behavior, especially for multi-area destinations such as
  Chamonix.
- Add a separate immutable weather-entity table now. This is cleaner long term
  but larger than needed while Snowcast's catalog entities can still serve as the
  evidence identity with active retirement semantics.

## Revisit When

Revisit when Snowcast needs explicit historical evidence migration tooling,
provider-backed operational status history for inactive ski areas, or a larger
entity model that separates weather identities from catalog ski-area display
entities.

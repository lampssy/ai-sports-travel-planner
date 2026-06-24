# ADR 0006: Model Cross-Destination Terrain Domains

Status: accepted
Date: 2026-06-24

Supersedes: N/A
Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0005-catalog-scope-model.md`

Related docs:
- `docs/data-trust-model.md`
- `docs/domain-language.md`

## Context

Some ski products and official terrain facts describe a linked domain that spans
destinations Snowcast models separately. Tignes and Val d'Isere are separate
destinations, but their shared pass and 300 km domain facts describe the linked
Tignes-Val d'Isere terrain rather than one local child ski area.

Destination-local `terrain_groups` solve aggregate facts inside one destination,
but they cannot reference ski areas owned by another destination. Copying the
same shared terrain totals onto both local ski areas would double count and
misrepresent source scope.

## Decision

Add a separate static `terrain_domains` catalog in
`app/data/terrain_domains.json`.

A terrain domain has:

- a stable `terrain_domain_id`;
- a display name;
- explicit `ski_area_refs` as `{resort_id, ski_area_id}` pairs;
- `metric_scope=aggregate`;
- optional aggregate piste, lift, elevation, difficulty, season-window, and
  source URL facts.

Add optional `terrain_domain_ids` to `lift_pass_products` so regional pass
products can reference modeled cross-destination terrain while still listing the
local `valid_ski_area_ids` owned by the destination.

Catalog validation checks that terrain-domain members reference existing
destination/ski-area pairs and that pass-product terrain-domain references
exist.

## Consequences

Shared domains can be reviewed once and reused by multiple destinations without
corrupting local ski-area facts.

Ranking remains unchanged until a later ranking checkpoint decides how to use
shared domains to avoid multi-ski-area destinations occupying multiple result
slots or to summarize accessible terrain.

The first modeled shared domain is Tignes-Val d'Isere. Its 300 km and elevation
facts are stored as aggregate domain facts. Its lift count uses
`total_lift_count=72` from a Bergfex linked-skiregion category breakdown because
the reviewed official sources disagree on the same linked-domain metric and no
official source is clearly authoritative for the shared terrain-domain scope.

## Alternatives Considered

- Keep linked-domain facts only in curation reports. This preserves caution but
  leaves no validated static truth for future ranking or display.
- Add cross-destination ids to `terrain_groups`. This would overload a
  destination-local concept and make ownership unclear.
- Copy linked-domain totals onto both Tignes and Val d'Isere ski areas. This
  would be easiest for ranking but would double count and hide source scope.

## Revisit When

Revisit when ranking starts grouping destination/ski-area options by shared
domain, when a provider offers authoritative per-local-area splits, or when UI
needs a first-class linked-domain display.

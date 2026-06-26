# ADR 0005: Model Scoped Pass Products And Aggregate Terrain Groups

Status: accepted
Date: 2026-06-23

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-06-20-resort-fit-data-model-design.md`
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`

Related docs:
- `docs/data-trust-model.md`
- `docs/catalog-curation/2026-06-23-zell-am-see-kaprun.md`

## Context

Some source-backed ski facts do not belong cleanly to one modeled ski area.
Zell am See-Kaprun exposes two common cases:

- Ski ALPIN CARD prices are useful for Zell am See-Kaprun users, but the pass
  is a regional product. It covers modeled local ski areas and external terrain
  outside the destination.
- Reviewed terrain sources can publish aggregate Kitzsteinhorn/Maiskogel
  metrics, while official child-area pages do not publish the same difficulty
  split for each separate modeled ski area.

Copying regional pass prices onto each ski area would hide the pass scope.
Copying aggregate terrain metrics onto child ski areas would double-count or
misrepresent source meaning.

## Decision

Add explicit destination-level `lift_pass_products` and `terrain_groups` to the
static catalog model.

`lift_pass_products` describe named pass products with:

- a stable product id;
- validity scope;
- whether it is the default representative planning product;
- modeled local ski-area ids covered by the pass;
- optional external validity summary;
- reviewed price examples.

`terrain_groups` describe aggregate terrain facts with:

- a stable group id;
- linked modeled ski-area ids;
- `metric_scope=aggregate`;
- aggregate piste, lift, and difficulty metrics when source-backed;
- reviewed source URLs supporting the aggregate values.

Child `ski_areas[]` remain single ski-area facts. Aggregate terrain values must
not be copied into child ski-area fields unless a source explicitly supports the
child value.

When child-scoped fallback sources publish piste or lift metrics but the sum
does not exactly match an official pass-accessible aggregate, keep both scopes
visible instead of forcing the catalog to reconcile them arithmetically.

Trust-manifest field groups include both `lift_pass_products` and
`terrain_groups` so these high-impact facts cannot bypass source-trust review.

## Consequences

Catalog curation can represent multi-area pass products and aggregate linked
terrain without corrupting child ski-area facts.

Reviewers can see whether a value is local, regional, or aggregate before
accepting it into catalog truth.

Production ranking remains unchanged until a later ranking-integration
checkpoint chooses how, or whether, to consume terrain-group facts.

The static catalog no longer accepts destination-level `lift_pass_prices`.
Reviewed pass prices live under `lift_pass_products[].prices`; the old database
column remains only as empty compatibility storage until a separate persistence
cleanup removes it.

## Alternatives Considered

- Store pass scope directly on each `LiftPassPrice`. This is smaller, but
  repeats product metadata on every duration/season price row.
- Copy aggregate Kitzsteinhorn/Maiskogel terrain into one child ski area. This
  would make ranking inputs look complete but would misrepresent the source.
- Leave aggregate and regional facts only in curation reports. This avoids
  schema changes but loses approved catalog truth for useful source-backed
  planning facts.

## Revisit When

Revisit this decision when production ranking or UI display starts consuming
terrain groups or pass products directly, or when a provider API offers cleaner
per-area terrain and pass-validity metadata.

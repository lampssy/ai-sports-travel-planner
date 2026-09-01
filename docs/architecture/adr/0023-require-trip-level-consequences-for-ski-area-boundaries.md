# ADR 0023: Require Trip-Level Consequences For Ski-Area Boundaries

Status: accepted
Date: 2026-09-01

Supersedes: N/A
Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
- `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`
- `docs/architecture/adr/0021-gate-ski-area-weather-sampling.md`
- `docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md`

Related docs:
- `docs/domain-language.md`
- `docs/data-trust-model.md`
- `docs/superpowers/specs/2026-09-01-ski-area-trip-consequence-boundaries-design.md`

## Context

ADRs 0016 and 0022 require complete terrain, evidence ownership, and material
separation value. Before schema version 4, the typed report recorded only
`material`, `redundant`, or `unresolved` for the third gate. The validator could
therefore prove terrain and owner structure but could not distinguish a useful skier-facing split from one
created by operator names, status pages, provider listings, or internal map
sectors.

This is especially visible when a normal trip market contains several lift
companies. Evidence ownership determines where facts can attach, but it does
not by itself show that another ranked or weather-owning ski-area identity is
useful to a skier.

## Decision

A `SkiArea` that partitions or competes within a larger ski system must pass
three independent gates:

1. complete, coherent lift-served downhill terrain;
2. independent or coordinated evidence ownership;
3. at least one evidence-backed material trip-level consequence.

The allowed trip-level consequence categories are:

- pass price or coverage;
- stay access or transfer mechanics for a primary selectable ski day;
- weather or season suitability;
- terrain character or party skill fit.

Every consequence names the normal-trip decision it can change: selected ski
area, stay-to-ski configuration, lift-pass choice, or conditions evidence
profile. The candidate must be a substantial primary ski-day option compared
with its nearest parent or sibling. Same-day route preference, ordinary sector
variation, a novelty or individual-lift ticket, temporary closure, one forecast,
or an isolated incident is not material.

A destination's sole root downhill area has no parent or sibling boundary to
compare. Its consequence instead uses `comparison_basis=stay_market_baseline`
with `comparison_target_id` naming the represented stay destination, and
establishes a durable trip-relevant difference between ski-terrain evidence and
the accommodation-market baseline. A parentless candidate that competes with a
sibling uses `comparison_basis=sibling_ski_area` and names that assessed sibling.

Operator identity, a dedicated website, map or status presentation, provider
consensus, a stay-market boundary, connectivity, disconnection, transfer
requirements, or a shared pass remains supporting evidence. None establishes
trip-level value by itself.

Schema-version-4 curation reports record typed `material_trip_consequences`.
Each item owns its `consequence_type`, affected `decision_effect`, typed
`comparison_basis`, concrete `comparison_target_id`, `durability_basis`, direct
`evidence_refs`, and comparison-relative `rationale`. A comparative ski-area
boundary requires at least one item. Consequence evidence must be known, verification-capable,
included in the boundary and scope evidence sets, and explicitly scoped to the
assessed candidate through `boundary_target_ids`.

Comparison targets are checked against the report graph. A parent comparison
must name the declared parent and differ from the subject. A sibling comparison
must name another represented or added ski-area assessment with the same parent.
A stay-market comparison must name a represented or added stay destination, may
identify only one root ski area for that destination, and cannot coexist with a
sibling comparison involving that root. All comparison IDs resolve uniquely
through typed assessment `target_refs`; a report-local `candidate_id` alias is
not a catalog comparison target.

Materiality is assessed independently from the other two gates. A
`not_separate` child may therefore retain a verified material consequence when
it lacks complete terrain or evidence ownership. It is invalid to fold a
candidate only when complete terrain, evidence ownership, and material
trip-level value all pass.

Ordinary coordinated-child viability evaluates the new third gate as well as
terrain and owner evidence. A child can therefore remain inside a coordinated
parent even when it has a company, page, or candidate-scoped operations
presentation, provided it lacks material trip-level value. Conversely, a child
that passes all three gates cannot be hidden inside the parent.

Failure of the third gate also permits schema-version-4 component membership to
be reproducibly derived under ADR 0022. The derivation still requires complete
official terrain topology, exact roster and operations accounting, and a unique
parent; it does not permit grouping by pass, branding, or proximity alone.

Historical report schemas 1-3 remain parseable under their original contract.
Schema version 4 preserves schema-version-3 invariants but replaces its literal
direct-assignment family with ADR 0022's current generic component-assignment
family. Newly finalized maintainer reports use schema version 4, and
normalization from an in-flight schema-version-3 generation requires fresh
semantic review.

## Consequences

- Ski-area identity follows user-visible trip choices rather than company or
  provider structure.
- Evidence ownership and user value remain explicit, separate concerns.
- Connected and disconnected candidates still use ADR 0016 owner thresholds,
  but connectivity no longer substitutes for materiality.
- Coordinated areas can contain operational components without manufacturing
  runtime weather identities.
- Curation reports add compact typed consequence records instead of a runtime
  sub-area model.
- Existing catalog IDs are unchanged by this contract-only decision; any later
  split or merge remains an owner-reviewed weather-ID migration.

## Alternatives Considered

- **Treat evidence ownership as sufficient.** Rejected because it over-splits
  multi-operator skier products.
- **Treat a different town or required transfer as sufficient.** Rejected
  because accepted areas such as KitzSki, Laax, Mayrhofen, and Verbier show that
  stay and transfer boundaries can coexist with one skier-facing area.
- **Follow one provider's area boundaries.** Rejected because editorial and
  commercial boundaries do not own Snowcast recommendations or weather.
- **Add runtime ski sub-areas now.** Rejected because current search and weather
  behavior does not need that granularity.
- **Amend schema version 3 in place.** Rejected because it would invalidate
  previously reviewed evidence packets.

## Revisit When

- piste-level availability or hotel-to-sector matching becomes a first-class
  product capability;
- a reliable provider supplies canonical component status and weather scopes;
- repeated audits show that the consequence categories cannot express material
  skier choices without inconsistent judgment.

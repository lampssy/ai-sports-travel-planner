# ADR 0022: Allow Coordinated Multi-Operator Ski Areas

Status: accepted
Date: 2026-08-26

Supersedes: N/A
Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
- `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`
- `docs/architecture/adr/0021-gate-ski-area-weather-sampling.md`

Related docs:
- `docs/domain-language.md`
- `docs/data-trust-model.md`
- `docs/superpowers/specs/2026-08-26-coordinated-multi-operator-ski-areas-design.md`

## Context

ADR 0016 requires a ski area to have complete terrain scope, independent
evidence ownership, and material separation value. That prevents named sectors,
individual lift companies, and provider pages from manufacturing runtime weather
identities.

The word `independent` is too narrow when several lift companies collectively
publish one complete skier-facing area. Livigno's west side is the motivating
case: Carosello, Sitas, and smaller lift presentations can plausibly form one
terrain, pass, status, and weather unit even though no single legal company owns
all lifts. Requiring one company would over-split the skier product. Ignoring
operations ownership would instead permit arbitrary pass or marketing
aggregations.

## Decision

Evidence ownership may be either:

1. **independent**, where one durable area-level owner publishes operations,
   weather, or a full local pass; or
2. **coordinated**, where several operators collectively form one durable,
   complete area-level publication boundary.

The existing complete-terrain and material-separation gates remain unchanged.
A coordinated area additionally requires all of the following:

- an official complete map or lift inventory defining the terrain scope
  (`official_complete_lift_inventory`);
- an official exhaustive operator/component roster;
- one official current lift-status or operating-schedule presentation
  (`coordinated_status_or_schedule`) covering the area, or a broader official
  presentation in which every coordinated component is exactly addressable;
- one pass covering every component (`common_full_coverage_pass`); the pass may
  also cover a separately modeled adjacent ski area and cannot define the
  boundary by itself, so the coordinated area's pass scope may be full-local or
  shared-only;
- each coordinated child assessed exactly once with
  `disposition=not_separate`, `parent_ski_area_id` equal to the coordinated
  parent, a target reference to that parent, and `operational_scope=coordinated`;
- direct component-to-parent assignment evidence for every component; common
  official sources may supply it when they make every assignment explicit;
- no material component-level weather or season semantics that require a
  separate identity;
- no component that independently passes the ordinary separate-ski-area gates.

Minor nursery or satellite lifts may belong to the coordinated area even when
they are not literally piste-connected. They must share the complete local map,
status system, pass, and stay market; they must not have material independent
recommendation, operations, weather, season, or pass value.

A substantial transfer-required, weather-distinct, or independently operated
complete area remains a separate `SkiArea`. Shared branding, a shared pass, an
operator directory, geographical proximity, or one website is insufficient
without the complete coordinated evidence packet.

The curation contract represents this decision explicitly rather than changing
the meaning of `independent`. A schema-version-3 coordinated parent owns
`component_candidate_ids`, `coordination_evidence_families`, and aggregate
`coordination_evidence_refs`. Each typed family item records `family`, non-empty
`evidence_refs`, and `covered_component_candidate_ids`. The five allowed family
values are `complete_terrain_lift_inventory`,
`exhaustive_component_operator_roster`,
`component_addressable_operations_status`,
`every_component_pass_coverage`, and
`direct_component_parent_assignment`.

Every family covers exactly the parent's component IDs. Its evidence resolves
to `source_type=official` items included in both boundary and scope evidence,
and the aggregate refs equal the union of the family refs. The metadata belongs
only to a `represented` or `add_entity` parent; coordinated `not_separate`
children retain the coordinated operational scope and parent target but no
parent metadata. Schema versions 1 and 2 cannot claim coordinated scope or
metadata. Existing non-coordinated schema-version-3 reports remain valid and
retain their legacy Markdown. Operations and weather use separate report-only
type aliases so `coordinated` is valid only for `operational_scope`; it is not a
weather-scope classification.

Coordinated operations do not activate weather sampling. `weather_scope` and
the complete area's coordinate and elevation evidence must pass ADR 0021
independently; otherwise `weather_sampling_status` remains deferred.

## Consequences

- Snowcast can model a skier-coherent area without creating one runtime ski area
  per lift company.
- The model distinguishes legal operator plurality from missing area-level
  operations evidence.
- Regional pass networks and marketing umbrellas remain outside `SkiArea`
  unless they satisfy the much narrower coordinated-area gates.
- Curation reports become slightly larger because they reconcile every component
  to its parent.
- Deterministic validation can verify declared component closure but cannot
  prove that internet research found every component; independent source review
  remains required.
- Existing weather history is not automatically moved or re-keyed when a
  coordinated area is introduced.

## Alternatives Considered

- **Require one legal operator.** Rejected because it over-splits coherent areas
  and confuses company ownership with evidence ownership.
- **Broaden `independent` to include any multi-operator area.** Rejected because
  it obscures which evidence path justified the boundary and weakens reviewability.
- **Remove the operations-owner gate when terrain and weather look coherent.**
  Rejected because it permits arbitrary map, pass, or marketing aggregates.
- **Add `SkiSubArea` now.** Rejected because component-level runtime ranking,
  weather, and status are not yet product requirements.

## Revisit When

- Snowcast exposes component-level lift or piste status;
- hotel-level recommendations need direct component-terrain selection;
- one weather identity proves materially misleading for coordinated areas; or
- a reliable operational provider supplies a canonical component ownership
  graph.

# ADR 0016: Require Evidence-Owner Boundaries For Ski Areas

Status: accepted
Date: 2026-07-17

Supersedes: N/A
Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
- `docs/architecture/adr/0009-normalized-trip-market-catalog.md`
- `docs/architecture/adr/0023-require-trip-level-consequences-for-ski-area-boundaries.md`

Related docs:
- `docs/domain-language.md`
- `docs/engineering-notes.md`
- `docs/data-trust-model.md`

## Context

Snowcast stores weather, climatology, current conditions, operating evidence,
terrain metrics, and season geometry by `ski_area_id`. The previous curation
contract allowed a new ski area when any one of several signals was present.
Those signals mixed strong ownership evidence, such as an independent status
feed, with weaker discovery evidence, such as child-scoped terrain metrics or a
dedicated official page.

That rule allowed two defensible interpretations of connected named sectors.
For example, a sector can have its own website, lift inventory, and local
metrics while the parent ski area still owns the complete pass, status, weather,
and connected terrain. Creating another ski area in that case would manufacture
a weather owner rather than describe one.

## Decision

A separate `SkiArea` must pass three gates:

1. **Complete terrain scope:** the candidate is a coherent lift-served downhill
   product with a defensible complete boundary, not only a named sector, lift
   cluster, piste group, webcam, status filter, or marketing page.
2. **Independent evidence ownership:** the candidate owns at least one durable
   operations, weather, or full-local-pass scope. Child metrics, a dedicated
   identity, individual lift tickets, and a separate lift company are supporting
   signals and cannot satisfy ownership alone.
3. **Material separation value:** a separate ID prevents misleading attribution
   of weather, operations, season, pass coverage, or terrain facts. A redundant
   child remains inside its parent area. ADR 0023 refines this gate for current
   reports by requiring a typed, evidence-backed trip-level consequence.

Connected terrain receives a stronger default. A connected candidate that the
parent reports as one operational area remains `not_separate` unless it has two
independent owner categories across operations, weather, and full local pass;
at least one category must be operations or weather. A disconnected or
transfer-required complete area may qualify with one owner category because the
parent cannot accurately represent its direct terrain access.

Operations ownership is an evidence-scope conclusion, not a website-boundary
test. Before deciding that operations evidence is absent, curation and review
must inspect the candidate's official publication neighborhood: the destination
or resort page, the operator or consortium member directory and candidate
member page, and a candidate-scoped live status or opening presentation. An
official candidate operator/member page and an official current operations
presentation may jointly establish operations ownership even when a regional
network hosts the status page or the sources use different hostnames. A
separate hostname is not required. A separate company or member page alone,
without candidate-scoped current operations evidence, remains supporting
evidence only.

Schema version 3 introduced the typed ski-area boundary assessment. Each
ski-area candidate
records complete-versus-sector scope, parent connectivity, operations ownership,
weather ownership, pass scope, provider consensus, separation value, parent ID,
and direct evidence references. Provider listings corroborate the decision but
do not vote an entity into or out of existence. The report validator enforces
the structural gates; owner review remains responsible for whether the cited
sources truthfully support each classification.

`represented` and `add_entity` require resolved parent connectivity.
`not_separate` names its parent and targets that parent ski area, so a merge
decision cannot exist without an explicit owner scope.

Historical schema versions 1-3 remain parseable. ADR 0023 adds the material
trip-consequence gate in schema version 4, which the maintainer requires for
newly remediated or published curation work.

## Consequences

- Dedicated sector pages and child metrics no longer create weather identities
  by themselves.
- Connected child areas require stronger evidence than disconnected areas.
- Curation must review the nearest parent owner scope before adding or retaining
  a ski area.
- Curation and review must exhaust the bounded official operator/member and
  candidate-scoped operations source families before treating ownership
  evidence as unavailable.
- Reports become slightly larger but make boundary reasoning directly
  reviewable in the checked-in evidence packet linked from the concise PR
  synopsis.
- Existing ski-area IDs that fail the new test require an owner-reviewed model
  migration; validation does not silently merge or re-key historical weather.

## Alternatives Considered

- **Keep the one-of signal rule.** Rejected because signals with very different
  evidentiary strength produced inconsistent splits.
- **Use lift connectivity as the boundary.** Rejected because independently
  operated and weather-distinct areas can be connected.
- **Follow Bergfex or Skiresort.info boundaries exactly.** Rejected because
  provider scopes are useful corroboration but may follow commercial or
  editorial aggregation rather than Snowcast evidence ownership.
- **Introduce `SkiSubArea` immediately.** Rejected because named sectors do not
  yet need their own runtime weather, ranking, or operational identity. The
  concept remains available for a later product need.

## Revisit When

- Sub-area status, piste availability, hotel-level terrain choice, or localized
  forecast presentation becomes a first-class product requirement.
- Repeated catalog audits show that two owner categories systematically reject
  connected terrain that users and operators treat as independently selectable.
- A reliable operational provider supplies a more precise canonical ownership
  graph than reviewed static sources.

# ADR 0018: Require Independent Stay-Market Boundaries

Status: accepted
Date: 2026-07-20

Supersedes:
- The stay-destination gate in
  `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`.

Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0009-normalized-trip-market-catalog.md`
- `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`

Related docs:
- `docs/domain-language.md`
- `docs/engineering-notes.md`
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`

## Context

The previous destination rule combined bookable stay identity, direct ski
access, recommendation value, and several terrain-oriented identity signals.
It could classify the same valley either as one umbrella destination with
several bases or as several destinations with one base each. Official place
names and access to a lift did not reliably resolve that ambiguity.

Snowcast needs a destination boundary that describes accommodation markets,
while `SkiAreaAccess`, `SkiArea`, `TerrainDomain`, and `SkiRegion` independently
describe access, terrain evidence, connected terrain, and familiar umbrellas.

## Decision

A candidate is a separate `StayDestination` only when all three gates pass:

1. **Complete stay-market scope.** The candidate is a coherent multi-night
   accommodation and arrival market. Its modeled bases form a complete
   defensible market boundary; the candidate is not merely a neighborhood,
   piste-side sector, isolated lodging cluster, pass label, or incomplete
   fragment of a wider market.
2. **Independent stay-market ownership.** Authoritative sources treat the
   candidate as owning a distinct lodging, visitor, booking, or destination-
   management scope. A place name, dedicated page, lift access, or separate
   municipality is supporting evidence but does not establish ownership by
   itself.
3. **Material destination-level separation value.** Returning the candidate as
   a separate stay choice can materially change accommodation supply or price,
   arrival effort, atmosphere, practical ski access, local services, or another
   destination-owned trip-fit factor. Minor variation between neighborhoods of
   one market is not enough.

Independent ownership must be supported by at least one direct official stay-
market signal: official stay-market treatment, independently presented
accommodation inventory, or independent destination management.
Terrain operators, weather pages, and lift-pass products may corroborate the
graph but do not own the stay market.

Apply these routing rules consistently:

- A useful accommodation place that fails any gate is normally a `StayBase`
  under the nearest qualifying stay destination.
- Several places that each pass all three gates remain separate stay
  destinations even when they share a ski area, terrain domain, or pass.
- A familiar umbrella whose qualifying children are separate stay destinations
  is a `SkiRegion`, not another overlapping ranked stay destination.
- A coherent umbrella that passes the gates while its named components do not
  is one stay destination with multiple stay bases.
- Ski access is represented only through explicit `SkiAreaAccess` edges. Direct
  lift access is not a fourth destination gate.

Boundary adjudication returns `policy_determined` whenever one graph follows
these rules more closely. `owner_choice_required` is reserved for the unusual
case where two materially different graphs both pass all three gates with
comparable evidence. Missing evidence is not an owner preference; it remains
`evidence_insufficient` and must be researched, deferred, or blocked.

Stay-destination changes do not move weather evidence because weather belongs
to `ski_area_id`. Preserve an existing ski-area ID when its evidence-owning
terrain is semantically unchanged. When a graph migration introduces a new ski-
area ID, existing archive and climatology remain on the old ID and the new ID
starts empty. After merge, the separate Complete Historical Weather workflow
discovers active new IDs, resumes archive backfill across scheduled runs, and
rebuilds climatology when archive coverage is complete. The catalog maintainer
records this handoff but does not execute production database jobs.

A material weather-geometry change on a retained ski-area ID remains different:
it requires an explicit forced refetch and climatology rebuild rather than being
inferred from archive completeness.

## Consequences

- Similar valleys are classified by accommodation-market ownership rather than
  by naming, municipal boundaries, or lift connectivity.
- Stay bases can remain detailed without multiplying ranked destinations.
- Shared ski terrain and passes do not collapse independently useful stay
  markets.
- Most boundary findings become policy-determined fixes instead of owner
  decisions.
- Curation reports and reviews need direct stay-market evidence for every new,
  retained, split, or merged destination boundary.
- Historical weather remains isolated from catalog reshaping and is completed
  asynchronously after merge.

## Alternatives Considered

- **Keep direct ski access as a destination gate.** Rejected because access is
  already an explicit relationship and does not establish accommodation-market
  ownership.
- **Use municipalities or official destination names as boundaries.** Rejected
  because administrative and marketing scopes do not consistently match a
  useful booking market.
- **Treat every named village as a destination.** Rejected because it would
  over-split coherent markets and crowd ranking with near-duplicate choices.
- **Let the owner decide every ambiguous valley.** Rejected because repeated
  owner decisions indicate missing policy, not valuable product discretion.

## Revisit When

- Accommodation inventory is modeled at hotel or property level and shows that
  the three gates systematically merge materially different booking markets.
- Search begins ranking stay bases independently rather than grouping them
  within a destination.
- A reliable provider supplies a canonical accommodation-market graph that is
  more precise than reviewed destination sources.

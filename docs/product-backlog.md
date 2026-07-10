# Snowcast Product Backlog

This backlog captures valuable product, data, UX, platform, and technical ideas
that are not active implementation work yet. It is a structured parking lot, not
a commitment list.

Use `PROJECT.md` for the short product charter and current roadmap snapshot. Use
feature specs and Superpowers plans when work is ready to design and implement.

## Backlog Convention

Backlog items should stay lightweight and decision-oriented. Each item should
answer:

- why the idea matters
- what a plausible first scope could include
- what should explicitly stay out of scope for now
- what signal would justify promoting it into a feature spec

Statuses:

- `idea`: captured but not evaluated
- `candidate`: likely relevant, needs shaping
- `next`: likely near-term
- `spec-ready`: enough context exists to write a feature spec
- `parked`: intentionally deferred
- `closed`: rejected, superseded, or implemented elsewhere

Areas:

- Product / Strategy
- Data Trust
- Planning / Ranking
- Web UX
- Mobile Companion
- AI / LLM
- Booking / Monetization
- Growth / SEO
- Ops / Observability
- Release
- Security / Privacy
- Technical Debt

Promotion flow:

1. Capture promising but non-active ideas here.
2. Move an item to `next` or `spec-ready` only when it fits the current product
   stage and constraints.
3. Create a feature spec under `docs/superpowers/specs/` before implementation
   when the item creates durable product behavior or touches a high-risk domain.
4. When promoting an item, carry forward any likely Developer Decision
   Checkpoints so technical and product/domain tradeoffs are owner-reviewed
   before planning.
5. Link the feature spec back to the backlog item.
6. After implementation, mark the backlog item `closed` with a short note or
   remove it if the history is not useful.

## Catalog Curation Refinements

This section tracks destination-specific catalog extensions discovered during
curation and review. Add further resorts here when a focused curation pass
reveals useful entities, relationships, or boundary work that should be handled
separately from the active PR.

Full curation should add sourceable, in-scope missing entities in the active PR.
Use this section only when the extension would make the PR unmanageably broad,
mix a separate model concern, depend on uncurated graph nodes, require a weather
identity migration, or remain genuinely unresolved. Time pressure or
convenience alone do not justify deferral.

Schema-version-2 `deferred` and `unresolved` scope assessments reference one
consolidated regional item through `backlog_ref`. Each item must include the
exact markers used by its reports, for example:

- `ski_area:kitzbuheler-horn`
- `stay_destination:kirchberg`

Update an existing regional item rather than creating one item per sector.
`not_separate` decisions do not belong here.

Discovery treats this section as a semantic backlog-clearing queue:

1. First retry a previously sourceable candidate interrupted only by
   `lock-busy`, after fresh inventory and source checks.
2. Then prefer `Status: candidate` items and their explicit
   `Next bounded slice`, prioritizing completion of partially modeled regions.
3. Keep `Status: parked` authoritative for genuine dependencies; automation
   must not silently override it.
4. Use external discovery only when no bounded backlog slice is actionable.
5. When an accepted proposal merges, remove or mark its slice complete and
   promote the next remaining slice. Close the regional item only when no
   useful modeled gap remains.

A bounded slice may be an explicit decision-bearing proposal for a boundary,
stable-ID, or weather-owner change when the existing catalog model can express
the intended result. The proposal must expose the owner decision, affected
historical data, migration/backfill handoff, merge order, and rollback. Actual
database migrations, catalog-schema changes, and production-code changes remain
separate work and block readiness rather than proposal creation.

### Jungfrau Region Catalog Extension

Status: candidate
Area: Data Trust
Source: Grindelwald-Wengen catalog review; PR #22

Next bounded slice:

- Add the complete Mürren destination/base/Mürren-Schilthorn ski-area/access
  graph with local pass coverage and an explicit new weather identity. Keep the
  wider Jungfrau pass as pass-only context because the systems are not
  ski-connected.

Why it matters:

- PR #22 models Grindelwald and Wengen as separate stay destinations, retains
  the connected Grindelwald-Wengen ski area, and adds Grindelwald-First as its
  own operator and weather identity.
- The Jungfrau Ski Region pass also covers Mürren-Schilthorn, which official
  sources present as a third independently operated ski area and accommodation
  market outside the two-destination graph in this PR.

Candidate inventory:

- `stay_destination:murren` and `stay_base:murren-murren` — independent
  car-free accommodation market and village base.
- `ski_area:murren-schilthorn-ski-area` — independently operated terrain with
  its own schedule, status, 56 km / 13-lift inventory, and weather identity.
- `ski_area_access:murren-murren--murren-schilthorn-ski-area` — direct local
  access relationship from the Mürren base.

Why it was deferred from the source PR:

- Adding Mürren requires a new destination boundary, base, weather identity,
  access evidence, trust entries, and pass-coverage update. That is a coherent
  destination curation rather than a small completion of the Grindelwald and
  Wengen correction.

Not now:

- Do not copy the 211 km Jungfrau pass aggregate onto Mürren-Schilthorn or
  either modeled Grindelwald child area.
- Do not create a terrain domain merely from shared ticket validity; the three
  ski areas require transport between their distinct ski systems.

Discovery progression:

- Close this item when the Mürren proposal is accepted and merged, or retain
  only any concrete source-backed gap discovered during that curation.

### KitzSki Regional Extension

Status: candidate
Area: Data Trust
Source: Kitzbühel catalog review; PR #14

Next bounded slice:

- Complete Mittersill and Hollersbach as related stay destinations, bases, and
  Panoramabahn/Pass Thurn access edges to the retained KitzSki ski-area owner.
  Do not change terrain or weather ownership in this slice.

Remaining slices:

- Review Reith and Aurach as stay destinations and Aschau as a Kirchberg stay
  base, adding only boundaries and access edges that pass the source gates.
- Prepare a decision-bearing Kitzbüheler Horn ski-area/weather-owner proposal.
- Review Gaisberg and Bichlalm terrain ownership and local-pass relationships in
  a later decision-bearing slice.

Why it matters:

- PR #14 now models Kitzbühel, Kirchberg, and Jochberg as distinct stay
  destinations sharing the retained KitzSki ski-area owner, but official sources
  also expose disconnected local terrain and additional accommodation markets.
- Adding those remaining entities safely requires a deliberate weather-identity
  and aggregate-metric migration rather than copying KitzSki-wide facts onto
  narrower areas.

Candidate inventory:

- `ski_area:kitzbuheler-horn` — standalone family ski area with the local Horn
  Special ticket and independent access lifts.
- `ski_area:gaisberg-kirchberg` — disconnected Kirchberg terrain with a local
  special ticket and distinct evening piste-touring and toboggan offer.
- `ski_area:bichlalm` — separate Kitzbühel touring area with its own local
  special ticket and access pattern.
- `stay_destination:mittersill` — independent accommodation market with KitzSki
  access through the western Panoramabahn/Pass Thurn side.
- `stay_destination:hollersbach` — independent accommodation market and
  Panoramabahn access point.
- `stay_base:mittersill-pass-thurn` — Pass Thurn accommodation/access base for
  the connected Resterhöhe sector.
- `stay_base:hollersbach-hollersbach` — Hollersbach accommodation base and
  Panoramabahn access edge.
- `stay_destination:reith-bei-kitzbuhel` — official Kitzbühel-region lodging
  village whose independent recommendation boundary and stable ski access need
  a focused review.
- `stay_destination:aurach-bei-kitzbuhel` — official Kitzbühel-region lodging
  village whose independent recommendation boundary and access edge remain to
  be established.
- `stay_base:kirchberg-aschau` — named Spertental accommodation village linked
  to Kirchberg but requiring a source-backed access edge.

Why it was deferred from the source PR:

- The disconnected terrain candidates require re-scoping the retained
  `kitzbuhel-ski-area` weather owner and deciding whether KitzSki-wide metrics
  move to pass-accessible terrain, a connected domain, or narrower child areas.
- Adding the remaining western and village markets would take PR #14 beyond the
  three-destination curation batch and introduce several new access and trust
  dependencies.

Not now:

- Do not split Pengelstein, Jochberg, Pass Thurn, or Resterhöhe merely because
  they appear as named map sectors; official sources present them as connected
  parts of the retained KitzSki terrain owner.
- Automation may prepare an explicit decision-bearing re-key proposal, but do
  not mark it ready or merge it until the owner checkpoint, weather-history
  handoff, and advisory review are resolved.

Discovery progression:

- After each merged slice, update this item to the next remaining slice. Keep
  terrain-owner proposals explicitly separate from destination/access
  completions.

### Skicircus Saalbach Hinterglemm Leogang Fieberbrunn Extension

Status: candidate
Area: Data Trust
Source: Saalbach Hinterglemm catalog review; PR #15

Next bounded slice:

- Prepare one connected-domain decision-bearing proposal containing Leogang and
  Fieberbrunn destinations, bases, independent ski-area/weather owners, local
  access edges, the shared Skicircus terrain domain, aggregate-fact ownership,
  and Ski ALPIN CARD coverage. Include the historical-weather and migration
  handoff for every new or changed owner.

Why it matters:

- PR #15 retains Saalbach Hinterglemm as the existing local weather owner, but
  official sources expose independent Leogang and Fieberbrunn destination,
  operator, and weather contexts inside one ski-connected Skicircus.
- The published 270 km, 70-lift, difficulty, season, and piste-map inventory
  describes that connected aggregate rather than the retained local owner.

Candidate inventory:

- `stay_destination:leogang` and `stay_base:leogang-leogang` — independent
  accommodation market with direct Leoganger Bergbahnen access.
- `ski_area:leogang-ski-area` and
  `ski_area_access:leogang-leogang--leogang-ski-area` — separate operator and
  weather owner with an explicit local access edge.
- `stay_destination:fieberbrunn` and `stay_base:fieberbrunn-fieberbrunn` —
  independent Tyrolean accommodation market with direct lift access.
- `ski_area:fieberbrunn-ski-area` and
  `ski_area_access:fieberbrunn-fieberbrunn--fieberbrunn-ski-area` — separate
  operator, snow report, weather presentation, and local access edge.
- `terrain_domain:skicircus-saalbach-hinterglemm-leogang-fieberbrunn` — the
  ski-connected aggregate owning the official 270 km / 70-lift inventory and
  whole-domain piste map.

Why it was deferred from the source PR:

- The complete extension requires two new weather identities, their destination
  and access graphs, a connected terrain domain, and reassignment of aggregate
  facts and Ski ALPIN CARD coverage. Adding only the lodging nodes would create
  an incomplete or misleading graph.

Not now:

- Do not broaden `saalbach-hinterglemm-ski-area` into the whole Skicircus or
  copy domain-wide snowmaking, park, freeride-route, season, or terrain totals
  onto that local weather owner.

Discovery progression:

- Close this item after the complete connected-domain proposal is accepted and
  merged; do not split out lodging-only nodes that would leave the graph
  misleading.

### St Anton And Ski Arlberg Extension

Status: candidate
Area: Data Trust
Source: St Anton catalog review; PR #11

Next bounded slice:

- Add a source-backed Lech-Oberlech-Zürs destination/base/ski-area/access graph
  while preserving the retained St Anton identity. Keep full connected-domain
  totals and topology out until the Warth-Schröcken owner is represented.

Remaining slices:

- Add the Warth-Schröcken destination and weather-owner graph.
- Add Sonnenkopf and Klösterle as a separate pass-valid but ski-bus-connected
  graph.
- Complete the Ski Arlberg regional parent, connected terrain domain, pass
  coverage, and any decision-bearing St Anton ownership migration.

Why it matters:

- The current catalog models St Anton and the Ski Arlberg pass, but not the
  complete connected Ski Arlberg topology.
- The wider 300 km and 85-lift claim describes connected terrain and therefore
  ultimately belongs to a reviewed terrain domain rather than the St Anton ski
  area or a temporary pass aggregate.
- Explicit linked entities would replace the current external-validity summary
  with source-backed modeled coverage as the related destinations are curated.

Potential scope:

- Review whether the retained `st-anton-am-arlberg-ski-area` identity represents
  St Anton alone or the wider St Anton-St Christoph-Stuben operational unit;
  preserve the stable ID unless an approved weather-evidence migration says
  otherwise.
- Assess St Christoph and Stuben as separate stay destinations versus stay bases
  within the existing St Anton trip market.
- Add source-backed ski areas, stay markets, bases, and access edges for Lech-
  Oberlech-Zurs and Warth-Schroecken.
- Add Sonnenkopf as a separate ski area and Klosterle stay context; keep it
  outside the connected terrain domain because access from Ski Arlberg is by
  ski bus, while representing its official Ski Arlberg pass validity directly.
- Add a `ski-arlberg` regional-network parent and a connected Ski Arlberg terrain
  domain for the reviewed St Anton, Lech-Zurs, and Warth-Schroecken member
  areas.
- Update the Ski Arlberg pass coverage and availability relationships when the
  member entities exist.

Not now:

- Do not expand PR #11 into a multi-destination topology migration.
- Do not create a one-member terrain domain or copy the connected-domain totals
  onto the current St Anton ski-area record.
- Automation may prepare an explicit decision-bearing split or re-key proposal,
  but do not mark it ready or merge it until the owner checkpoint, advisory
  review, and weather-history handoff are resolved.

Discovery progression:

- Advance one complete owner graph at a time, then finish connected-domain and
  pass ownership after all required member areas exist.

### Verbier 4 Vallees Extension

Status: candidate
Area: Data Trust
Source: Verbier catalog review; PR #18

Next bounded slice:

- Add Nendaz and Veysonnaz destinations/bases/access together with their shared
  independently operated ski-area owner and local product evidence. Keep the
  full 4 Vallées terrain domain external until Thyon is represented.

Remaining slices:

- Add the Thyon destination, three reviewed bases, access edges, and ski-area
  weather owner.
- Add the regional-network parent, 4 Vallées terrain domain, aggregate facts,
  complete piste map, and explicit wider-pass coverage.

Why it matters:

- PR #18 now models the official 106 km Verbier sector as one ski-area owner
  spanning Verbier, La Tzoumaz-Savoleyres, and Bruson, with separate sourced
  stay destinations, bases, and access edges for all three accommodation
  markets.
- The official 4 Vallees offer is a wider ski-connected domain joining that
  sector to Nendaz, Veysonnaz, and Thyon. Its 410 km aggregate, 82-lift count,
  and full piste map must not be copied onto the narrower Verbier-sector owner.
- Completing the graph crosses multiple lift operators and independent trip
  markets, so it requires a coordinated domain, destination, access, pass, and
  weather-owner review.

Candidate inventory:

- `ski_region:4-vallees` — add a `regional_network` parent for the independent
  Verbier, Nendaz, Veysonnaz, and Thyon trip-market regions.
- `stay_destination:nendaz`, `stay_base:nendaz-haute-nendaz`, and
  `stay_base:nendaz-siviez` — review one destination with two materially
  different accommodation and access contexts.
- `ski_area_access:nendaz-haute-nendaz--nendaz-veysonnaz-ski-area` and
  `ski_area_access:nendaz-siviez--nendaz-veysonnaz-ski-area` — add the direct
  gondola and Siviez connection edges without treating the two bases as
  interchangeable.
- `stay_destination:veysonnaz` and `stay_base:veysonnaz-veysonnaz` — add the
  village accommodation market.
- `ski_area_access:veysonnaz-veysonnaz--nendaz-veysonnaz-ski-area` — add its
  direct gondola access.
- `stay_destination:thyon` with `stay_base:thyon-thyon-2000`,
  `stay_base:thyon-les-collons`, and `stay_base:thyon-les-masses` — review the
  three altitude and accommodation contexts before deciding whether they all
  remain bases of one destination.
- `ski_area_access:thyon-thyon-2000--thyon-ski-area`,
  `ski_area_access:thyon-les-collons--thyon-ski-area`, and
  `ski_area_access:thyon-les-masses--thyon-ski-area` — add explicit local lift
  or ski-bus access for each accepted base.
- `ski_area:nendaz-veysonnaz-ski-area` — assess the independently operated NVRM
  terrain and status owner, including its shared Mont-Fort operating boundary.
- `ski_area:thyon-ski-area` — assess the independent Tele-Thyon terrain,
  schedule, and weather owner.
- `terrain_domain:4-vallees` — connect the retained
  `ski_area:verbier-ski-area` with the reviewed Nendaz-Veysonnaz and Thyon ski
  areas; own the official 410 km / 82-lift aggregate and full 2025/26 piste map.
- `lift_pass_product:verbier-4-vallees-pass` — replace the external-only wider
  summary with explicit terrain-domain coverage and add availability from the
  new stay destinations when their entities exist.
- Review the official local/sector products for Verbier, Nendaz-Veysonnaz,
  Printse, and Thyon as separate pass candidates without changing the current
  default-pass policy in this curation pass.

Why it was deferred from the source PR:

- The remaining topology adds three recommendation markets, multiple bases and
  access edges, at least two independently justified ski-area owners, a
  cross-destination connected terrain domain, and multi-operator pass coverage.
  Folding that migration into PR #18 would make the focused Verbier correction
  unmanageably wide.

Not now:

- Do not attach the 410 km / 82-lift aggregate or the complete 4 Vallees map to
  `ski_area:verbier-ski-area`.
- Do not split the jointly published 106 km Verbier sector into separate
  Verbier, La Tzoumaz, and Bruson ski-area owners solely because the operator
  exposes named sectors and local products.
- Do not create a one-member terrain domain or model pass validity as physical
  connectivity before the NVRM and Tele-Thyon owners are represented.

Discovery progression:

- Advance Nendaz/Veysonnaz first, then Thyon, then the complete regional/domain
  ownership slice; update this item after each merged proposal.

### Mayrhofen Hippach And Tux Finkenberg Completion

Status: parked
Area: Data Trust
Source: Mayrhofen catalog review; PR #16

Blocking dependency:

- The Ski Region Trail Map Ownership schema refinement must land before the
  shared map and regional parent can be represented safely. This item remains
  intentionally ineligible for discovery until that dependency is resolved.

Next bounded slice after unblock:

- Complete the Zillertal 3000 regional parent/shared map plus the reviewed
  Mayrhofen-Hippach and Tux-Finkenberg stay/access graph as one decision-bearing
  proposal with compatibility handling for retained Hintertux identities.

Why it matters:

- PR #16 correctly retains the 142 km Mayrhofen ski-area owner for Ahorn,
  Penken, Finkenberg, Rastkogel, and Eggalm, while official sources also expose
  direct access and accommodation contexts in Hippach, Schwendau,
  Hochschwendberg, and Finkenberg.
- The current catalog already contains a separate Hintertux destination and ski
  area. Completing Tux-Finkenberg therefore needs a deliberate destination and
  access-boundary migration rather than attaching the whole 202 km Ski &
  Glacier World aggregate to Mayrhofen.
- The available official piste map covers both the Mayrhofen terrain and
  Hintertux Glacier. It needs a wider regional owner so that the catalog keeps
  the document without misrepresenting it as a Mayrhofen-only map.

Candidate inventory:

- `ski_region:ski-glacier-world-zillertal-3000` — add the officially named Ski
  & Glacier World Zillertal 3000 umbrella with
  `grouping_policy=regional_network` and the shared official trail map.
- `ski_region:mayrhofen` and `ski_region:hintertux` — retain both trip-market
  regions and assign the new Zillertal 3000 region as their contextual parent.
- `ski_area:mayrhofen-ski-area` and `ski_area:hintertux-glacier` — retain the
  independent weather, season, terrain, and operational owners. Leave
  Mayrhofen's local `official_trail_map` null unless a genuinely child-scoped
  map becomes available.
- `stay_destination:mayrhofen-hippach` — decide whether Hippach remains a
  separate recommendation market or becomes the destination owner for the
  lower-valley bases.
- `stay_base:mayrhofen-schwendau` and
  `ski_area_access:mayrhofen-schwendau--mayrhofen-ski-area` — accommodation
  base with direct Horbergbahn access.
- `stay_base:mayrhofen-hochschwendberg` and
  `ski_area_access:mayrhofen-hochschwendberg--mayrhofen-ski-area` — mountain
  accommodation base with direct Moeslbahn access.
- `stay_destination:tux-finkenberg` — review the wider Tux-Finkenberg stay
  market against the existing Hintertux destination before changing ownership.
- `stay_base:tux-finkenberg-finkenberg` and
  `ski_area_access:tux-finkenberg-finkenberg--mayrhofen-ski-area` — Finkenberg
  accommodation base with direct Almbahnen access to the modeled Mayrhofen
  terrain.

Why it was deferred from the source PR:

- Adding one isolated base would leave the official Mayrhofen-Hippach and
  Tux-Finkenberg accommodation graph incomplete. The full extension requires
  two destination-boundary decisions, three sourced bases, three access edges,
  and compatibility handling for the existing Hintertux identities.
- Regional map ownership depends on the separate Ski Region Trail Map Ownership
  schema refinement before the shared map and parent relationships can be
  represented without weakening current ski-area and terrain-domain semantics.

Not now:

- Do not copy the disconnected 202 km Ski & Glacier World product aggregate or
  the whole-domain piste map onto `ski_area:mayrhofen-ski-area`.
- Do not create a `TerrainDomain` for the complete Zillertal 3000 umbrella:
  Hintertux requires a ski-bus connection from Eggalm, while a regional-network
  `SkiRegion` does not assert physical ski connectivity.
- Do not attach regional piste, lift, elevation, season, or difficulty totals
  to the new SkiRegion; retain those facts on ski areas, connected terrain
  domains, or pass-accessible aggregates according to their source scope.
- Automation may prepare an explicit decision-bearing Hintertux re-key
  proposal after the blocking schema dependency lands, but do not mark it ready
  or merge it until the owner checkpoint and compatibility handoff are resolved.

Promotion trigger:

- Promote after Ski Region Trail Map Ownership lands, then complete the Zillertal
  3000 parent region, shared map, and regional stay/access graph in one reviewed
  sequence.

### Upper Engadin Catalog Extension

Status: candidate
Area: Data Trust
Source: St. Moritz catalog review; PR #19

Next bounded slice:

- Add Corvatsch-Furtschellas as its own ski-area/weather owner with Silvaplana
  and Sils destination/base/access graphs and reviewed Snow-Deal pass context.

Remaining slices:

- Add Diavolezza-Lagalb with the Pontresina stay graph after resolving its
  combined owner boundary.
- Review Zuoz, Samedan, La Punt, Maloja, and S-chanf as separate bounded
  destination/area slices rather than one pass-defined domain.

Why it matters:

- The Upper Engadin Snow-Deal covers several disconnected ski areas and distinct
  accommodation markets beyond the focused St. Moritz/Celerina/Corviglia graph.
- Each area needs its own weather/operations identity, stay destinations, bases,
  access edges, and local-source review rather than being collapsed into one
  pass-defined terrain domain.

Candidate inventory:

- `ski_area:corvatsch-furtschellas-ski-area`
- `ski_area:diavolezza-lagalb-ski-area`
- `ski_area:zuoz-ski-area`
- `ski_area:pontresina-languard-ski-area`
- `ski_area:samedan-ski-area`
- `ski_area:la-punt-ski-area`
- `ski_area:maloja-ski-area`
- `ski_area:s-chanf-ski-area`
- `stay_destination:silvaplana`
- `stay_destination:sils`
- `stay_destination:pontresina`
- `stay_destination:zuoz`
- `stay_destination:samedan`
- `stay_destination:la-punt-chamues-ch`
- `stay_destination:maloja`
- `stay_destination:s-chanf`

Why it was deferred from the source PR:

- Completing these candidates would turn the focused PR into an eight-area,
  multi-destination weather-identity and access-graph migration.
- Several candidates still need owner-boundary review, especially the combined
  Diavolezza/Lagalb presentation and the smaller village lift areas.

Not now:

- Do not create one Upper Engadin terrain domain from pass-only connectivity.
- Treat Muottas Muragl as pass context unless downhill ski-area evidence emerges.
- Keep Provulèr inside the Corviglia owner scope unless durable independent-owner
  evidence stronger than its limited children's ticket appears.

Discovery progression:

- Advance one independently justified destination/area graph at a time and
  update this item after every merged slice; never create one terrain domain
  from Snow-Deal validity alone.

## Current Backlog

### Destination Coverage Registry

Status: parked
Area: Product / Strategy; Data Trust
Source: simplified local maintainer design

Why it matters:

- Snowcast may eventually need a researched definition of the destinations and
  ski markets it deliberately wants to cover, rather than relying only on
  opportunistic catalog growth.
- A defensible desired-coverage universe could show what the catalog already
  represents, what is currently proposed, and which strategically relevant
  gaps remain.

Potential scope:

- Define the geographic scope before collecting entries: Alpine, European, or
  eventual global coverage.
- Decide whether coverage is measured at ski-region, stay-destination,
  ski-area, stay-base, or layered graph level.
- Establish owner-reviewed inclusion and priority criteria such as market
  relevance, conditions value, sourceability, transport context, and booking
  usefulness.
- Research authoritative sources and rules for connected resorts,
  multi-destination domains, and small local areas.
- Store the desired universe and targeting metadata only; derive represented,
  proposed, declined, and missing status from the live catalog and GitHub
  proposal history.

Not now:

- Do not treat the initial 69-entry maintainer seed as a complete or
  strategically selected universe.
- Do not use an unresearched registry as a runtime discovery queue or proposal
  gate.
- Do not duplicate mutable catalog or proposal status in the registry.

Promotion trigger:

- Promote when Snowcast moves from opportunistic catalog growth to deliberate
  market-coverage planning and the owner is ready to define geographic,
  entity-granularity, inclusion, and prioritization policy.

### Operational Resort Status Acquisition

Status: candidate
Area: Data Trust; Planning / Ranking; Ops / Observability
Source: recovered from old `PROJECT.md` backlog; `docs/data-trust-model.md`;
`docs/engineering-notes.md`

Why it matters:

- Exact-date planning gets stronger when Snowcast can distinguish weather-derived
  disruption signals from reported operational status.
- Lift and piste availability could materially change trip recommendations for
  near-term windows.

Potential scope:

- Build a separate frequent acquisition pipeline for current and historical
  operational status instead of mixing live snow-report data into static catalog
  acquisition.
- Store observations with source URL, provider, fetched timestamp, reported
  timestamp when available, confidence/trust tier, and freshness status.
- Track high-impact fields where sources support them:
  - open lift count and total lift count
  - open piste km and total piste km
  - open piste count and total piste count
  - snow depth and last reported update
- Prefer official resort status pages and open/regional APIs.
- Use proprietary public pages such as Bergfex only as a last-resort,
  lower-trust fallback with strict rate limits, no raw-page storage, and clear
  provenance.

Not now:

- Do not fetch provider data inside `/api/search`.
- Do not present weather-derived disruption as official lift-operation status.
- Do not require human review for every daily refresh; reserve review for source
  onboarding, source mapping changes, parser changes, or recurring source-quality
  problems.

Promotion trigger:

- Promote when operational status becomes the next meaningful improvement to
  near-term trip confidence or companion alerts.

### Catalog Source Integrity Improvements

Status: candidate
Area: Data Trust
Source: current roadmap; `docs/data-trust-model.md`

Why it matters:

- Snowcast's value depends on users trusting catalog facts, source labels, and
  evidence quality.
- Weak or estimated high-impact fields can become product risk when surfaced in
  public pages, ranking, or booking handoff.

Potential scope:

- Identify high-impact `estimated` or `needs_source` trust-manifest fields.
- Prioritize fields that affect ranking, public claims, conditions matching, or
  booking decisions.
- Add source-backed corrections through the existing catalog validation process.
- Explore broader use of OpenSkiMap data as reviewable catalog-curation evidence.
- Keep LLM extraction proposal-only unless facts are reviewed and promoted.

Not now:

- Do not expand to many new resorts before the current high-impact trust gaps are
  understood.
- Do not make acquisition artifacts runtime inputs.

Promotion trigger:

- Promote when a product surface depends on a weak field or when a catalog audit
  shows repeated trust gaps in important destinations.

### Ski Region Trail Map Ownership

Status: parked
Area: Data Trust; Catalog Model
Source: Mayrhofen catalog review; PR #16

Why it matters:

- Official trail maps do not always match one ski area or one physically
  connected terrain domain. Some represent a named trip market or regional
  network containing multiple or partly disconnected ski areas.
- Discarding such maps loses useful official information, while attaching them
  to a narrower ski area overstates the document's scope.

Proposed ownership rule:

1. Store a map on `SkiArea` when it covers exactly that ski-area owner.
2. Store a map on `TerrainDomain` when it covers a physically ski-connected
   aggregate represented by that domain.
3. Store a map on `SkiRegion`, regardless of whether its grouping policy is
   `trip_market` or `regional_network`, when it covers that named market or
   network across multiple or disconnected ski areas.
4. Use the most specific truthful owner and do not duplicate one map across
   narrower entities merely for discoverability.

Proposed schema and contract work:

- Add optional `official_trail_map: OfficialLinkFact` to `SkiRegion`.
- Persist and load `official_trail_map_json` for ski regions through the
  database schema, synchronization, and repository boundaries.
- Add a ski-region `official_documents` trust group whose source refs match the
  stored map URL exactly.
- Add `official_trail_map.url` and `official_trail_map.season_label` to canonical
  ski-region curation coverage.
- Allow `ski_region` candidates in schema-version-2 entity-scope assessments so
  new trip-market and regional-network umbrellas are reviewed explicitly.
- Update domain language, the relevant ADR, catalog curation/review skills, and
  validation tests with the ownership hierarchy above.

Not now:

- Do not make SkiRegion a terrain-metric, weather, season, or operational-status
  owner.
- Do not infer map coverage from a shared pass alone; require an official map
  whose published scope matches the region.
- Do not weaken the physical-connectivity requirement for `TerrainDomain`.

Promotion trigger:

- Promote before the Zillertal 3000 regional-network completion or whenever a
  reviewed official map spans a named trip market/network but cannot truthfully
  belong to one ski area or connected terrain domain.

### Pass Product Selection Refinement

Status: parked
Area: Planning / Ranking; Data Trust; Web UX
Source: pass-product review during catalog curation

Why it matters:

- A curated default pass can make a presentation choice look like an intrinsic
  property of a destination even when several valid local and wider products
  exist.
- Pass recommendation should depend on the trip context, while destination
  terrain potential and the terrain actually included in a pass should remain
  clearly distinguishable.

Potential scope:

- Retire or deprecate `default_for_stay_destination_ids` as a curated catalog
  relationship.
- Keep all available pass products as catalog facts and derive a recommended
  product only when dates, applicable prices, coverage, and other required trip
  context are sufficient.
- When context is insufficient, present pass options without implying that one
  product is recommended by default.
- Review the API and client assumption that every trip configuration has a
  mandatory `selected_pass`.
- Make explanations clear when full connected-domain terrain requires a wider
  pass than a local product.

Not now:

- Do not change existing default-pass values or add new default-pass curation
  guidance during the current catalog PR review cycle.
- Do not combine this refinement with the current destination-curation PRs.
- Do not change pass-related ranking behavior without a separate model review.

Promotion trigger:

- Promote after the current catalog curation review cycle, when pass-product
  selection and comparison becomes an active product/API priority.

### Comparable Piste And Marked-Route Terrain Metrics

Status: parked
Area: Data Trust; Planning / Ranking; Catalog
Source: Sölden catalog review and cross-resort marked-route comparison

Why it matters:

- `total_piste_km` currently carries incompatible publisher meanings. Some
  operators use it for classified pistes only, while others include marked ski
  routes, park terrain, or a broader managed ski offer in the headline total.
- `piste_km_by_difficulty` should preserve the published classified-piste
  breakdown. Adding ungroomed ski routes to `advanced` would make an advanced
  skier's terrain opportunity easier to infer, but would mislabel those routes
  as advanced pistes and make resort comparisons inconsistent.
- Sölden publishes 137.2 km of blue, red, and black pistes, 6.7 km of ski
  routes, and 1.7 km of fun-park terrain within a rounded 146 km headline.
  Stubai instead publishes its 65 km piste inventory separately from roughly
  31 km of ski routes. St Anton currently has a local marked-route count but no
  source-backed local piste-kilometre total.

Proposed direction:

- Separate normalized classified-piste inventory from marked-route inventory
  and from the operator's published headline total.
- Introduce `classified_piste_total_km` and validate
  `piste_km_by_difficulty` against that value rather than against a potentially
  broader headline total.
- Extend `marked_freeride_routes` with optional `route_km`, independent from
  optional `route_count`, because operators may publish either measurement.
- Preserve an optional source-aware published terrain total with a controlled
  coverage basis such as `classified_pistes_only`,
  `pistes_and_marked_routes`, `broader_managed_ski_offer`, or
  `publisher_unspecified`.
- Keep marked routes distinct from black or advanced pistes. Downstream
  advanced-terrain suitability may consider both facts without changing their
  catalog meanings or claiming that marked routes are black pistes.
- Keep generic lift-accessible off-piste terrain separate from marked-route
  inventory. Powder or backcountry marketing does not establish marked,
  secured, or controlled route kilometres.

Validation and migration:

- Require a difficulty split to approximately match
  `classified_piste_total_km` when both are present.
- Require positive `route_count` or `route_km` values to have
  `marked_freeride_routes.availability=available`.
- Treat reconciliation between an operator headline and its components as a
  source-aware warning or curation note rather than a hard equality rule,
  because publishers use different measurement methods and rounding.
- Add the new fields before changing consumers. Migrate resorts only when
  direct sources establish the component boundaries; do not bulk-assume that
  existing `total_piste_km` values mean classified pistes.
- After normalized coverage is sufficient, move comparable terrain consumers
  to classified-piste totals and retire or rename the ambiguous legacy field.

Illustrative normalized outcomes:

- Sölden: 137.2 km classified pistes, 6.7 km marked routes, and a 146 km
  broader published headline.
- Stubai Glacier: 65 km classified pistes and roughly 31 km marked routes.
- St Anton local area: classified piste kilometres unresolved, 19 marked
  routes, and marked-route kilometres unresolved; wider Ski Arlberg figures
  remain on their appropriate aggregate scope.

Not now:

- Do not change terrain fields, validation, curation guidance, or downstream
  behavior in the active destination-curation PR review cycle.
- Do not fold marked routes or park terrain into `advanced` as a one-off
  normalization for Sölden.
- Do not treat Ski Arlberg's broad powder/backcountry kilometres as a measured
  inventory of marked routes.

Promotion trigger:

- Promote after the current catalog curation review cycle, together with a
  focused audit of publisher terrain-total semantics and marked-route distance
  availability across the curated catalog.

### Lift-Accessible Off-Piste Terrain Fact

Status: parked
Area: Data Trust; Planning / Ranking
Source: Ischgl catalog review and catalog-wide freeride evidence audit

Why it matters:

- The catalog currently represents only officially marked or controlled
  freeride routes. This is precise but omits useful terrain at destinations
  that officially document lift-accessible off-piste skiing without presenting
  it as a marked-route inventory.
- Across the 35 ski areas reviewed so far, ten have source-backed marked-route
  availability while many other prominent destinations publish credible
  off-piste or backcountry offers. The two concepts overlap and should remain
  independently representable.
- A separate fact would allow Snowcast to describe the broader freeride offer
  without implying that open terrain is marked, secured, patrolled, or safe on
  a particular day.

Potential scope:

- Add a small source-aware `LiftAccessibleOffPisteFact` on `SkiArea` with
  `availability` and an optional `season_label`.
- Keep `marked_freeride_routes` unchanged; one ski area may legitimately have
  marked routes, lift-accessible open terrain, both, or neither established.
- Require an official ski-area or destination source that explicitly documents
  off-piste, backcountry, powder, or freeride terrain within the modeled ski
  area and establishes practical lift access.
- Add a dedicated trust-manifest group, typed curation coverage, and matching
  curation/review guidance before populating the field.
- After the current PR review cycle, run a focused recuration sweep rather than
  opportunistically changing the open destination PRs.

Not now:

- Do not modify the current catalog schema, curation skills, or open curation
  PRs during the active review cycle.
- Do not add route, area, kilometre, or terrain-quality counts in the first
  version; published measurements are sparse and not comparable.
- Do not treat heliskiing, ski-touring ascents, guide-only services, temporarily
  ungroomed pistes, or generic freeride marketing as sufficient evidence.
- Do not infer current safety, avalanche control, patrol status, or operational
  availability from this slow-changing catalog fact.

Promotion trigger:

- Promote after the current catalog curation review cycle, when broader
  freeride/off-piste discovery becomes an active catalog or search priority.

### Web Authentication And Cross-Surface Continuity

Status: candidate
Area: Web UX; Mobile Companion; Security / Privacy
Source: recovered from old `PROJECT.md` backlog; `docs/strategy.md`

Why it matters:

- Authenticated web state could connect anonymous planning with saved trips,
  mobile companion context, and trip-date editing.

Potential scope:

- Add optional Google sign-in to the React web app when authenticated continuity
  is valuable enough to justify login friction.
- Keep anonymous web search available for demos and sharing.
- Reuse the existing backend `/api/auth/google/sign-in` exchange pattern with a
  web OAuth client id.
- Use web auth for saved-trip ownership, trip-date editing, and continuity
  between web planning and the mobile companion.

Not now:

- Do not make search require login.
- Do not create a separate web-specific auth/session model.
- Do not turn the anonymous planning surface into a broad account dashboard.

Promotion trigger:

- Promote when users need to return to saved web plans or when web-to-mobile trip
  continuity becomes a core workflow.

### Mobile Companion Parity And Production Readiness

Status: candidate
Area: Mobile Companion; Security / Privacy; Release
Source: recovered from old `PROJECT.md` backlog; mobile audit notes

Why it matters:

- The Flutter app is the long-term companion surface, but it should stay focused
  on companion utility rather than duplicating the full web planner.

Potential scope:

- Apply parsed filters consistently where mobile exposes matching controls:
  - travel window
  - lift distance
  - quality tier
  - budget flexibility if kept in mobile
- Register mobile devices against the existing backend device-registration
  endpoint when real notification delivery gets closer.
- Reconcile Android package identifiers, signing config, and other release
  readiness details before treating mobile as production-ready.
- Keep UI cleanup companion-specific.

Already handled:

- Mobile exact-date search support is implemented; mobile can send
  `trip_start_date` and `trip_end_date` when both date fields are present.

Not now:

- No broad mobile redesign.
- No push-provider delivery until useful alert decisions and notification targets
  are ready.

Promotion trigger:

- Promote when companion events, push delivery, or saved-trip flows become the
  next active product bet.

### Search Origin, Distance, And Travel-Cost Refinement

Status: candidate
Area: Planning / Ranking
Source: recovered from old `PROJECT.md` backlog; `docs/engineering-notes.md`

Why it matters:

- Travel effort affects whether a recommendation is realistic, especially for
  car-first Alpine trips.

Potential scope:

- Continue preferring explicit user-provided origin or drive-time preference.
- Refine provider-backed routing when approximate deterministic drive estimates
  are not good enough.
- Consider travel-cost modeling only when duration, party size, lodging, and
  route assumptions can be combined without false precision.
- Consider user-location convenience later, when mobile/auth and permission UX
  can be handled cleanly.

Already handled:

- A first explicit origin and travel-effort flow exists.

Not now:

- No inferred device location by default.
- No flights, trains, transfers, live traffic, or full itinerary planning until
  ski recommendation quality clearly needs them.

Promotion trigger:

- Promote when travel effort becomes a repeated reason recommendations feel wrong
  or when route accuracy materially affects ranking.

### Operational Status And Companion Alert Push Delivery

Status: candidate
Area: Mobile Companion; Ops / Observability; Security / Privacy
Source: `docs/engineering-notes.md`; current roadmap

Why it matters:

- Companion events become more valuable when they can reach the user at the right
  time without requiring manual app checks.

Potential scope:

- Connect existing device-registration persistence to APNs/FCM or an equivalent
  provider.
- Keep alert decisions backend-owned, deterministic, and deduplicated.
- Add delivery status, retry/idempotency behavior, and operational visibility.
- Use operational resort status only when provenance supports it.

Not now:

- Do not add push delivery before alerts are useful enough.
- Do not send noisy weather updates that duplicate generic forecast apps.

Promotion trigger:

- Promote when current-trip companion events show enough value to justify real
  notification delivery.

### Accommodation Filter Enhancements

Status: parked
Area: Web UX; Booking / Monetization; Data Trust
Source: recovered from old `PROJECT.md` backlog

Why it matters:

- Stay preferences such as board type, wellness, ski bus, and ski-in/ski-out can
  improve trip fit once Snowcast has reliable accommodation-side data.

Potential scope:

- Add accommodation-side filters only after the stay-base/provider data model can
  support them credibly.
- Keep filters tied to source-backed or clearly caveated data.

Not now:

- Do not expose filters that imply property-level knowledge Snowcast does not
  have.
- Do not turn the product into a generic accommodation marketplace.

Promotion trigger:

- Promote when provider-backed or curated stay data makes these filters truthful
  enough to affect recommendations.

### Accommodation Price And Quality Realism

Status: candidate
Area: Data Trust; Booking / Monetization; Planning / Ranking
Source: recovered from old `PROJECT.md` backlog

Why it matters:

- Current stay-base prices and quality tiers are useful planning heuristics, but
  users may eventually expect provider-backed price and quality realism.

Potential scope:

- Decide whether accommodation price ranges and quality tiers should become
  provider-backed, curated with stronger evidence, or explicitly heuristic.
- Preserve current semantics: `min_price` and `max_price` are nightly stay-base
  budget estimates, not package totals.
- Keep rental prices separate until real package/provider data exists.

Not now:

- No fake package prices.
- No hotel-star claims from internal quality tiers.

Promotion trigger:

- Promote when booking handoff or richer stay options make current heuristics a
  trust risk.

### Lift-Distance Semantics

Status: candidate
Area: Planning / Ranking; Data Trust; Web UX
Source: recovered from old `PROJECT.md` backlog

Why it matters:

- `lift_distance` is valuable only when stay-base granularity makes the near,
  medium, or far distinction meaningful.

Potential scope:

- Reassess whether `lift_distance` should stay prominent while Snowcast models
  coarse stay bases.
- Improve, de-emphasize, or replace the filter depending on stay-base data
  quality.
- Keep the concept only where the selected stay base is meaningfully near,
  medium, or clearly far from lift access.

Not now:

- Do not overstate lift access precision.
- Do not add detailed transfer modeling until the product has enough stay-base
  and lift-access evidence.

Promotion trigger:

- Promote when stay-base enrichment or user feedback shows the current filter is
  misleading or too coarse.

### Booking Deep-Link And Affiliate Evolution

Status: candidate
Area: Booking / Monetization
Source: `docs/engineering-notes.md`

Why it matters:

- Booking handoff is the first revenue and intent signal, but Snowcast should
  remain provider-agnostic.

Potential scope:

- Move from resort-level outbound accommodation links to area-level deep links
  when the product can support that specificity reliably.
- Add affiliate-backed variants behind the existing backend redirect boundary.
- Add property-level links only once Snowcast can credibly recommend a specific
  accommodation with provider and freshness evidence.

Not now:

- No provider lock-in.
- No direct frontend links that bypass click tracking.
- No property-level recommendation claims without supporting data.

Promotion trigger:

- Promote when booking intent becomes a primary metric or when affiliate partner
  setup is ready.

### User Acquisition And Geography Strategy

Status: candidate
Area: Product / Strategy; Growth / SEO
Source: `docs/strategy.md`

Why it matters:

- A useful planner still needs a path to the first real users.
- Geography affects catalog priorities, currency, language, partner selection,
  and community channels.

Potential scope:

- Decide whether launch focus is explicitly Europe-first, North America-first,
  or staged.
- Evaluate first-user channels:
  - SEO via conditions-calendar and public resort pages
  - ski communities and clubs
  - Product Hunt / Hacker News launch
  - ski influencer outreach
- Tie acquisition strategy to data coverage and season timing.

Not now:

- No broad paid acquisition before retention and planning quality are credible.
- No launch promises before catalog and conditions claims are trustworthy.

Promotion trigger:

- Promote before the next growth-oriented stage or before investing heavily in
  SEO/public content expansion.

### Stay-Base Transfer And Internal Travel Graph

Status: idea
Area: Planning / Ranking; Data Trust
Source: `docs/engineering-notes.md`

Why it matters:

- Linked destinations may have multiple ski areas and stay bases where transfer
  effort affects the best trip option.

Potential scope:

- Model explicit stay-base-to-ski-area transfer effort.
- Use source-backed or provider-backed travel evidence where available.
- Keep search grouping around destination, ski area, stay base, and trip option.

Not now:

- Do not add a travel graph while current stay-base granularity is still coarse.
- Do not create false precision for internal resort transfers.

Promotion trigger:

- Promote when multi-area destinations produce confusing or unrealistic trip
  options.

### Ski Sub-Areas And Terrain Sectors

Status: parked
Area: Data Trust; Planning / Ranking; Ops / Observability
Source: destination-boundary design discussion;
`docs/superpowers/specs/2026-06-29-destination-boundaries-and-connected-terrain-design.md`

Why it matters:

- Large connected ski areas contain recognizable sectors with different
  elevation, access, terrain character, webcams, snow reports, and operational
  status.
- Examples include Grande Motte and Toviere within Tignes, Solaise and
  Bellevarde within Val d'Isere, and Groste or Spinale within Madonna di
  Campiglio.
- A sector layer could improve hotel-to-terrain access, localized live status,
  and explanation without turning every named mountain into a destination or
  full ski-area weather entity.

Potential scope:

- Add a destination-local `ski_sub_areas` or `terrain_sectors` model under a
  parent ski area.
- Keep stable ids, display names, parent ski-area ids, access points, optional
  elevation bounds, source refs, and provider status identifiers.
- Use sectors first for descriptive access and operational-status mapping.
- Add separate weather or ranking ownership only after an explicit model review.

Not now:

- Do not split historical weather or climatology by sector.
- Do not make sectors top-level recommendation candidates.
- Do not use map labels alone as evidence that a sector is a durable entity.
- Do not implement the layer while destination and ski-area boundaries are still
  being audited.

Promotion trigger:

- Promote when operational-status ingestion, accommodation-level access, or
  repeated user questions require trustworthy intra-ski-area detail.

### Future AI Companion Orchestration

Status: parked
Area: AI / LLM; Mobile Companion
Source: `docs/engineering-notes.md`

Why it matters:

- A grounded assistant may become useful after Snowcast has saved-trip context,
  live/reported status, and companion events.

Potential scope:

- Consider LangGraph or another orchestration approach for stateful companion
  workflows such as:
  - trip-specific chat grounded in saved trip and conditions context
  - plan-B guidance when conditions deteriorate
  - multi-step on-trip advice

Not now:

- Do not use orchestration frameworks for deterministic ranking, conditions
  scoring, simple parsing, or single narrative calls.
- Do not add generic chat just to look AI-native.

Promotion trigger:

- Promote when static companion screens cannot answer important saved-trip
  questions and the needed data is available.

### Observability Expansion

Status: candidate
Area: Ops / Observability
Source: `docs/observability-plan.md`

Why it matters:

- The main runtime path is observable, but acquisition, alerting, and future
  background work will need their own visibility as they become product-critical.

Potential scope:

- Expand telemetry to catalog curation validation/reporting and future
  operational-status acquisition.
- Add richer alerting around stale data, failed jobs, and provider degradation.
- Add log export if local/Fly logs stop being enough.
- Consider Sentry when error triage and release regression workflows justify it.

Not now:

- No self-hosted telemetry stack.
- No high-cardinality metrics.
- No vendor-specific coupling inside domain logic.

Promotion trigger:

- Promote when background acquisition or push/alert workflows become critical
  enough that failure cannot be diagnosed from current logs and metrics.

### Client Maintainability Refactors

Status: candidate
Area: Technical Debt; Web UX; Mobile Companion
Source: repo audit

Why it matters:

- The React and Flutter clients are functional, but large all-in-one files make
  future product changes slower and riskier.

Potential scope:

- Split `frontend/src/App.tsx` into route, state, and presentation modules when
  the next meaningful web feature touches those areas.
- Split `mobile/lib/main.dart` into API/auth, models, and screen modules when
  companion work resumes.
- Keep tests focused on behavior rather than snapshotting layout.

Not now:

- Do not do broad cosmetic refactors without feature pressure.
- Do not change API contracts just to make client structure cleaner.

Promotion trigger:

- Promote alongside the next sizable web or mobile feature, especially if the
  implementation would otherwise expand the all-in-one files further.

## Recovered But Not Active

These ideas appeared in older backlog or sprint notes but should not be treated
as open backlog now:

- Routeable web redesign, design-language pass, and public resort pages were
  promoted into later work and implemented.
- Mobile exact-date search support is implemented.
- The first explicit origin/travel-effort flow is implemented; remaining travel
  work is captured as refinement above.

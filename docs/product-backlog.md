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

### KitzSki Regional Extension

Status: parked
Area: Data Trust
Source: Kitzbühel catalog review; PR #14

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

Why deferred:

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
- Do not re-key or narrow the existing ski-area ID without an owner checkpoint,
  weather-history handling, and advisory review.

Promotion trigger:

- Promote when curating Mittersill, Hollersbach, Reith, Aurach, or Aschau, or
  when the product needs Kitzbüheler Horn, Gaisberg, or Bichlalm to own separate
  weather and operating evidence.

### St Anton And Ski Arlberg Extension

Status: parked
Area: Data Trust
Source: St Anton catalog review; PR #11

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
- Do not split or re-key the existing ski area without an owner checkpoint,
  advisory review, and explicit weather-history handling.

Promotion trigger:

- Promote when curation starts for Lech-Zurs, Warth-Schroecken, Sonnenkopf, St
  Christoph, or Stuben, or when explicit Ski Arlberg connected coverage becomes
  necessary in the catalog graph.

## Current Backlog

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
- Keep LLM extraction proposal-only unless facts are reviewed and promoted.

Not now:

- Do not expand to many new resorts before the current high-impact trust gaps are
  understood.
- Do not make acquisition artifacts runtime inputs.

Promotion trigger:

- Promote when a product surface depends on a weak field or when a catalog audit
  shows repeated trust gaps in important destinations.

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

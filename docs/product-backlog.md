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

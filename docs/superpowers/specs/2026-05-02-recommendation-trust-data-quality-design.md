# Recommendation Trust and Data Quality Design

## Status

Approved for Sprint 28 planning.

## Objective

Make Snowcast's current recommendation engine and 26-destination catalog trustworthy enough to support the next growth and companion sprints. This sprint should improve the truthfulness, provenance, and maintainability of existing recommendations before adding more resorts, web auth, browser push, or broader public SEO surfaces.

`PROJECT.md` carries the sprint-level roadmap entry. This document is the implementation handoff: it defines what "recommendation trust and data quality" means, what should be included, what is out of scope, and how another agent should verify the work.

## Why This Sprint Exists

The product promise is trusted ski-trip decision support under uncertainty. The project already has useful foundations:

- deterministic ranking owned by backend domain code
- weather forecast and archive evidence from Open-Meteo
- planning evidence profiles: `forecast_assisted`, `archive_backed`, and `fallback_heavy`
- routeable web recommendation surfaces and public resort pages
- a previous Sprint 17 resort audit record

The remaining risk is that later growth work could amplify weak or ambiguous data. Sprint 28 should close the most important trust gaps in the existing catalog and model semantics before the product asks more users to rely on its recommendations.

## Current Trust Gaps To Address

- Most destinations still rely on loader-generated default ski areas. The current catalog has 26 destinations, but only a small subset has explicit `ski_areas`.
- `availability_status` reads like operational resort status, but current weather-provider logic derives it from weather and season signals rather than official lift/open data.
- The current `stars` parameter represents internal quality tiers, not hotel-star ratings.
- Package price scoring combines accommodation and rental ranges without a clear unit policy.
- Audit evidence exists in sprint notes, but critical field provenance is not yet a durable data-quality contract.
- Public pages and app recommendations expose trust cues, but source semantics are still broad enough to mislead when evidence is estimated or fallback-heavy.

## Design Principles

- Do not use LLMs to create resort facts, prices, elevations, season windows, or operational status.
- Keep deterministic ranking as the source of truth.
- Make uncertainty explicit instead of hiding it behind polished copy.
- Prefer improving the current 26 destinations over expanding the catalog.
- Treat source licensing as part of data quality. A fact that cannot be used responsibly is not production-ready data.
- Keep data-quality checks automated where possible; use manual audit records only where source judgment is required.

## Source Policy

Use source categories deliberately:

- Official resort sources: preferred for official names, season windows, resort facts, and reported operational information when available.
- Open-Meteo: acceptable for forecast and archive weather evidence such as snow depth, snowfall, temperature, wind, and weather codes. It must not be presented as official resort operations status.
- OpenStreetMap or OpenSkiMap-derived data: useful for geospatial cross-checks, ski-area shape, piste/lift context, and stay-base anchoring. Any use must respect OSM attribution and ODbL obligations.
- Secondary sources such as Skiresort.info: useful for manual cross-checking, but do not scrape or ingest proprietary datasets unless permissions and terms are explicitly reviewed.
- Manual estimates: allowed only when labeled as estimated and not allowed to masquerade as verified facts.

## Data Trust Contract

For each destination, Sprint 28 should define or record source status for these critical fields:

- `resort_id`
- destination display name
- country and region
- destination coordinates
- destination base and summit elevation
- season start and end months
- explicit `ski_areas`
- each ski area's coordinates, base elevation, summit elevation, and season window
- explicit `stay_bases`
- stay-base quality tier
- stay-base lift-distance/proximity bucket
- supported skill levels
- rental example names and quality tiers
- accommodation and rental price ranges with defined units

Each critical field group should have an audit status:

- `verified`
- `verified_with_adjustment`
- `estimated`
- `needs_source`

Sprint 28 does not need a heavy database provenance model unless the implementation naturally calls for one. A dedicated audit document or structured validation manifest is enough if it is durable, reviewed, and linked from the relevant model docs.

## Database Model Guardrail

Sprint 28 should not require another historical-conditions schema migration. The current banded weather-history model already supports the needed trust work:

- `raw_weather_history` has `elevation_band` values for `base`, `mid`, and `upper`
- `raw_weather_history` stores the requested `elevation_m`
- archive and forecast rows are separated by `record_type`
- uniqueness is per `resort_id`, `elevation_band`, `observed_on`, and `source`

Do not add or reshape `raw_weather_history`, `resort_conditions`, or `resort_condition_history` for this sprint unless the user explicitly approves a separate migration.

The main rebuild risk is catalog identity, not table shape. Historical rows reference `ski_areas.ski_area_id`; changing or deleting a ski-area ID can cascade-delete or orphan historical weather evidence. Changing ski-area weather coordinates or elevations can also make an existing backfill semantically stale even if the rows still exist.

To avoid repeated backfills:

- complete the Sprint 28 catalog identity lock before a full historical rebuild when possible
- lock explicit `ski_area_id`, weather lookup coordinates, base/summit elevations, and season windows for every destination before rebuilding archive history
- preserve existing generated single-area IDs such as `{resort_id}-ski-area` when making them explicit, unless there is a strong reason to rename and the rebuild cost is accepted
- treat any post-rebuild ski-area ID, coordinate, or elevation change as a data invalidation event that needs an explicit backfill decision
- keep audit/provenance in docs, a structured manifest, or seed-side metadata rather than new operational tables unless a later sprint needs queryable provenance

## Recommendation Semantics

The sprint should make these semantics explicit in code, docs, and UI copy:

- Quality tier: `budget`, `standard`, and `premium` are internal quality tiers, not hotel-star ratings.
- Price fit: accommodation and rental ranges need defined units before being combined. If units differ, ranking should either normalize them through a clear trip-cost model or score them separately.
- Operational availability: only use `reported` operational availability when the source is an actual resort/lift/status provider.
- Weather disruption risk: weather-derived status should be labeled as estimated conditions or disruption risk, not as official open/closed lift status.
- Evidence profile: `fallback_heavy` should be visible enough that users and developers know not to over-trust that recommendation.

## Automation And Validation

Add or extend validation so data-quality failures are caught early:

- every destination has explicit `ski_areas`
- every destination has explicit `stay_bases`
- IDs are unique and stable
- coordinates are valid and plausible for the catalog region
- elevation ranges are ordered and plausible
- season months are valid
- price ranges parse and have documented units
- quality tiers and lift-distance buckets use allowed values
- critical field audit coverage exists
- current conditions freshness can be checked
- weather-history coverage can be reported by ski area and travel window
- no `reported` source type is emitted without a real reported source

## Golden Recommendation Scenarios

Add tests or fixtures that protect user-facing ranking behavior. Include scenarios such as:

- late-spring Austria or Switzerland searches where glacier/high-altitude terrain should not be treated the same as lower non-glacier areas
- beginner searches where skill fit should outweigh raw snow confidence when terrain is unsuitable
- budget-constrained searches where price semantics are clear and not distorted by rental/accommodation unit mixing
- sparse-evidence searches where fallback-heavy results remain visibly less certain
- exact-date searches where near-term forecast assistance is distinct from archive-backed seasonal planning

## Trust UX

User-facing surfaces should remain clean, but they need honest trust signals:

- source/evidence badges where they help decision-making
- last-updated information for current conditions
- clear wording for forecast-backed, archive-backed, and estimated signals
- no implication that Snowcast has official lift operations status unless it does
- methodology documentation that explains scoring without exposing raw internals as the main UI

## Out Of Scope

- Adding new resorts before the current 26 pass the trust contract
- Browser push notifications
- Web auth, except for tiny copy or interface decisions needed to avoid conflicts with trust UX
- Official lift-status ingestion across the whole catalog unless a small pilot source is already legally and technically clear
- Accommodation marketplace/provider integration
- Large frontend redesign
- Generic AI chat or LLM-driven ranking

## Expected Deliverables

- Updated `PROJECT.md` Sprint 28 entry.
- A durable trust/data-quality model or methodology doc linked from the roadmap.
- Current-catalog audit updates for all critical field groups.
- Explicit ski-area modeling for every current destination.
- Clarified quality-tier, price-unit, and availability/disruption semantics.
- Validation checks for catalog integrity and provenance coverage.
- Golden recommendation tests.
- Updated user-facing copy where current labels could overstate confidence.
- Updated planning/model documentation where scoring or evidence semantics change.

## Verification

The implementation agent should run the normal project verification for any code changes:

- backend tests
- backend lint and format checks
- frontend tests and build if web copy/API types change
- Playwright smoke tests if user-facing web trust labels or recommendation surfaces change
- mobile tests if API contract wording/types affect Flutter

Manual acceptance should include:

- inspect a few representative resort recommendations and confirm trust labels match the evidence source
- inspect a fallback-heavy result and confirm the UI does not overstate confidence
- inspect current conditions wording and confirm weather-derived signals do not imply official lift operations status
- inspect the data-quality report or validator output and confirm all current destinations are covered

## Agent Pickup Notes

Start by reading:

- `PROJECT.md` Sprint 28
- this spec
- `docs/planning-model.md`
- `docs/engineering-notes.md`
- `docs/sprint-17-resort-audit-results.md`
- `app/data/resorts.json`
- `app/data/loader.py`
- `app/domain/models.py`
- `app/domain/ranking.py`
- `app/domain/planning.py`
- `app/domain/search_service.py`
- `app/integrations/open_meteo.py`

Preserve existing architecture boundaries:

- AI logic stays in `app/ai`
- business/ranking/planning logic stays in `app/domain`
- weather/provider fetching stays in `app/integrations`
- persistence stays behind repositories in `app/data`

If the work grows too large, split it in this order:

1. Data trust contract and audit/validation.
2. Recommendation semantics and tests.
3. UI copy/methodology/trust presentation.

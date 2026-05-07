# Sprint 32 Design: Car-First Travel Effort

## Summary

Sprint 32 adds car-first travel effort to ski-trip recommendations. It uses the Sprint 31 trip context, especially origin, dates/duration, and budget mode, to estimate whether a resort or stay base is practical for the user's trip.

Travel remains a recommendation input, not a general itinerary planner.

## Product Boundary

Allowed:

- estimate drive effort from a user origin to a destination or stay base
- score and explain travel effort as part of ski-trip ranking
- apply user tolerance such as "within 5 hours" or "flexible"
- include approximate car travel cost in total-trip estimates when enough inputs are known

Out of scope:

- flight search
- train itinerary search
- airport selection
- transfer scheduling
- traffic-aware departure planning
- turn-by-turn routing UI
- hotel-level access scoring

## Goals

- Add car-first origin-aware travel effort to search.
- Use a routing-ready provider boundary so the implementation can start with approximation or use a real provider without touching ranking code.
- Add persistent geocode and route-estimate caching to control cost, latency, quota usage, and repeatability.
- Add travel-effort result fields, provenance, and user-facing tradeoff explanations.
- Keep fallback behavior useful when routing fails or origin is missing.

## Non-Goals

- No multi-modal travel planner.
- No live traffic or departure-time optimization.
- No booking or transport-provider integration.
- No requirement to know exact stay-base coordinates for every resort before launch.

## Data Model

Core value objects:

- `TravelOrigin`
  - label
  - latitude
  - longitude
  - source: user-provided, geocoded, or fallback
- `TravelDestinationPoint`
  - entity type: destination or stay base
  - entity id
  - label
  - latitude
  - longitude
  - precision/trust note
- `TravelRouteEstimate`
  - origin label and coordinates
  - destination label and coordinates
  - mode: `car`
  - distance km
  - duration minutes
  - provider
  - provenance: provider-backed or estimated fallback
  - fetched/cache timestamp
- `TravelGeocodeCacheEntry`
  - normalized origin text
  - resolved label
  - latitude
  - longitude
  - provider
  - confidence or precision when available
  - fetched/cache timestamp
- `TravelRouteCacheEntry`
  - origin coordinate key
  - destination entity key and coordinate key
  - mode: `car`
  - normalized route estimate
  - provider
  - provenance
  - fetched/cache timestamp
  - optional expiry or refresh policy
- `TravelEffortAssessment`
  - score
  - label: easy, moderate, long, very_long
  - user-facing summary
  - caveats

Stay-base coordinates are valuable but not mandatory for the first release. If a stay base lacks coordinates, the system may use destination coordinates and mark the estimate as destination-level.

## Provider Boundary

Ranking and search code should consume normalized route estimates, not provider-specific payloads.

Suggested interfaces:

- `TravelGeocoder`
  - resolves origin text to coordinates
- `TravelTimeProvider`
  - estimates car route from origin to destination
- `TravelGeocodeCache`
  - stores reusable origin resolutions by normalized origin text and provider
- `TravelRouteCache`
  - stores reusable route estimates by origin, destination, and mode

The first provider can be one of:

- approximate haversine-based estimator with mountain/road multiplier
- OpenRouteService
- GraphHopper
- another provider hidden behind the same interface

If a paid or quota-limited provider is used, the implementation must check caches before provider calls, persist successful estimates, and fall back to approximation on provider errors.

The cache is not a catalog acquisition pipeline. It is request-path support infrastructure for repeatable travel estimates. Cached values should carry provider/provenance metadata so the UI can distinguish provider-backed routes from approximate fallback routes.

## Ranking

Travel effort should behave as a soft recommendation signal by default.

Inputs:

- origin
- max drive duration preference when supplied
- travel tolerance: short, medium, flexible
- route estimate

Behavior:

- If no origin is known, do not penalize results for travel.
- If origin is known and no max drive duration is supplied, apply a moderate score/penalty based on duration buckets.
- If max drive duration is supplied, exclude or strongly penalize results above the threshold depending on chosen strictness.
- If routing fails, use fallback estimate with lower provenance confidence.

Travel effort should be explainable:

- "Approx. 4h 20m drive from Munich."
- "Longer travel, but stronger March snow reliability."
- "Within your 5h drive preference."
- "Travel estimate is approximate because routing provider data was unavailable."

## Total-Trip Cost

When the user selects total-trip budget and origin is known, Sprint 32 can add an approximate car-travel cost component.

Initial cost components:

- lodging range
- lift-pass examples when available
- rental examples when available
- car travel estimate when origin and route are known

Travel cost should be approximate and clearly labeled. It should not pretend to include all tolls, parking, fuel-price changes, flights, trains, or transfers.

## API And UI

Search inputs may add:

- origin text or coordinates
- max drive duration minutes
- travel tolerance
- travel mode fixed to `car` for this sprint

Search results may add:

- travel effort summary
- drive distance km
- drive duration minutes
- travel effort score/label
- route provenance
- total-trip estimate caveat when applicable

UI placement:

- Origin and travel tolerance should appear as clarification cards first.
- Advanced filters may expose them for manual adjustment.
- Result cards should show compact travel badges.
- Detail view should show the tradeoff between travel effort and snow/window fit.

## Error Handling

- Missing origin: no travel penalty, prompt for origin when useful.
- Geocoding ambiguity: ask the user to choose from candidate origins.
- Routing failure: fall back to approximate estimator and mark provenance.
- Provider quota/auth errors: keep search usable and surface compact debug info.
- Cache misses: call the configured provider only when the search has enough origin/destination context, then persist the result.
- Stale or missing cached values: fall back to approximation when provider refresh fails.

## Testing

Unit tests:

- origin validation and geocoding candidate handling
- geocode cache hit/miss behavior
- route cache keying
- route cache hit/miss behavior
- provider fallback behavior
- travel effort scoring buckets
- max drive threshold behavior
- total-trip estimate including/excluding travel cost correctly

Integration/API tests:

- search without origin remains compatible
- search with origin returns travel fields
- provider failure does not fail the whole search

Frontend tests:

- origin clarification card
- travel effort filter/chip
- result travel badge
- fallback/provenance wording

## Acceptance Criteria

- Users can provide an origin and see car-first travel effort in search results.
- Results remain useful when origin is missing.
- Travel effort affects ranking only when context is available.
- Geocode and route estimates are cached or otherwise bounded to avoid excessive provider calls.
- The UI stays ski-trip-focused and does not expose itinerary-planning controls.

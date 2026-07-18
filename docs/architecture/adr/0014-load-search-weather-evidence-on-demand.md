# ADR 0014: Load Search Weather Evidence On Demand

Status: accepted
Date: 2026-07-16

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`

Related docs:
- `docs/superpowers/plans/2026-07-16-search-v4-web-experience.md`
- `docs/planning-model.md`
- `docs/search-ranking-model.md`
- `docs/data-trust-model.md`
- `docs/architecture/adr/0012-versioned-search-factor-registry-and-ranking-policy.md`
- `docs/architecture/adr/0013-versioned-forecast-runs-and-latest-run-serving.md`

## Context

The recommendation dossier needs typed historical and target-date weather
profiles for the selected ski area. The first implementation attached a full
weather summary to every `SearchV4Configuration` in the grouped search
response. That preserved one-request navigation, but duplicated the same
ski-area profile across configurations and recommendation groups.

An uncapped current-catalog benchmark produced 25 groups, 60 configurations,
and 39 weather-summary builds. Full profiles added 1,092,264 serialized bytes,
made the response 2.133 times its no-summary size, and took 32.510 ms at p95 to
construct in memory. Those values exceeded the accepted 512 KiB, 2x, and 25 ms
guardrails. The ranking projection was identical with and without the detailed
profiles, so the extra cost did not improve result ordering.

The detailed profile is used only after a person opens a dossier. Keeping it
in the global search response would make every search pay for data that most
results do not display.

## Decision

Snowcast will load detailed search weather evidence on demand for one selected
ski area through `POST /api/search/weather-evidence`.

The request contains the applied typed `SearchIntent` and one catalog
`ski_area_id`. The response is a versioned, status-discriminated envelope
containing that identifier, server-owned `evaluated_at` and
`cache_valid_until` timestamps, and either one `SearchWeatherEvidence` value or
a bounded unavailable reason and limitations. Unknown ski-area identifiers are
rejected before repository access.

The endpoint reuses the same versioned Search V4 weather policy, stored
climatology rows, latest complete forecast heads, freshness test, source
selection, and deterministic presentation mapper used by ranking. It does not
call Open-Meteo or another provider, invoke an LLM, rerun ranking, or parse
generic factor payloads. Historical and forecast provenance remains typed;
mixed sources are represented explicitly rather than collapsed into synthetic
metadata.

`POST /api/search` remains the only ranking and reranking boundary and will not
serialize detailed weather profiles. Result cards continue to use the bounded
decision summaries already produced by Search V4. The dossier starts the
weather request when opened or when its selected ski area changes, shows a
locally announced loading/error/unavailable state, and caches available or
unavailable responses for the current browser session by the applied travel
window and ski-area ID. Cached entries are reusable only before the
server-owned `cache_valid_until`; expired entries are revalidated and transport
failures are never cached. It does not silently show evidence from a previous
intent.

For forecast-assisted evidence, `cache_valid_until` is the earliest freshness
expiry of the forecast runs selected into the response. Responses without a
usable forecast, including month-only climatology and unavailable evidence,
use a five-minute revalidation interval. This may perform an occasional extra
stored-data read, but it prevents a browser session from preserving forecast
evidence after the server would classify it as stale.

The detailed contract remains bounded to 31 historical points, 31 forecast
points, and 31 typed source records per evidence section. A maximum-cardinality
one-area route response must remain at or below 128 KiB of
uncompressed serialized JSON, and p95 in-memory service construction over 100
warm iterations must remain at or below 25 ms. These are engineering
guardrails, not external protocol limits or user-facing latency SLOs. Database
and HTTP latency are measured separately through the existing bounded-route
HTTP duration metric.

## Consequences

Benefits:

- Search response size and mapping cost no longer scale with the number of
  detailed weather profiles.
- Every recommendation can still expose complete evidence when inspected.
- The UI pays for one selected ski area and can reuse it while the dossier is
  revisited in the same browser session.
- Ranking and presentation continue to share deterministic weather selection
  and freshness semantics.
- Provider and LLM availability remain outside the dossier request path.

Costs and constraints:

- Opening or switching a dossier adds a second HTTP request and requires
  explicit loading, failure, and retry behavior.
- Evidence is loaded at dossier-open time and may be fresher than the data used
  by an earlier search. Provenance and issue times must remain visible; the UI
  must not claim the response is a frozen copy of the original ranking input.
- The API gains a durable evidence boundary that needs integration tests,
  endpoint observability, and browser-session cache-key discipline.
- Forecast-assisted cache lifetime follows provider schedule metadata; other
  responses are revalidated after five minutes even when climatology itself
  changes less frequently.
- Direct dossier URLs without an in-memory search session cannot reconstruct a
  recommendation or its applied intent; they retain the existing `Run a search
  first` recovery state.

## Alternatives Considered

- **Attach evidence to every configuration.** One request and simple client
  state, but it failed all full-catalog response-cost guardrails and duplicates
  ski-area profiles.
- **Deduplicate summaries into a top-level map keyed by ski area.** Removes
  configuration-level duplication but still builds and transfers every
  eligible area's profile before the user selects one.
- **Attach full evidence only to the first few results.** Keeps the first
  response bounded but makes lower-ranked dossiers incomplete and couples
  evidence availability to an arbitrary display cap.
- **Fetch a provider when the dossier opens.** Potentially freshest, but makes
  user latency, rate limits, cost, and availability depend on an external
  service and would diverge from stored ranking evidence.
- **Persist a server-side search-result snapshot token.** Could freeze evidence
  exactly to one search, but introduces persistence, expiry, privacy, and
  invalidation complexity not justified by the current anonymous web flow.

## Revisit When

- Dossier evidence becomes necessary for most visible results before users
  choose one.
- Measured endpoint latency or repository cost requires a server cache or a
  precomputed presentation table.
- Search sessions become authenticated and persist across devices, making a
  server-owned frozen evidence snapshot useful.
- Catalog scale, profile resolution, or forecast horizons exceed the one-area
  payload and construction guardrails.

# Task 3 Report: Typed Weather Evidence Without Ranking Changes

## Status

Implemented and verified in `d098bc3` (`feat: expose typed Search V4 weather
evidence`).

Classification: `review-gated` because this is additive source-trust and Search
V4 response-contract work.

- Developer Decision Checkpoint: resolved by the accepted Task 3 brief. The
  summary is optional, deterministic, built once per ski area from already
  preloaded rows, and does not feed ranking.
- ADR: not needed. Ranking policy, persistence, acquisition ownership, provider
  integration, repository shape, and LLM behavior are unchanged.
- Advisory feature review: skipped because the owner explicitly requested a
  focused self-review for this bounded task. The self-review evidence is below.

## RED Evidence

### Mapper boundary

Command:

```bash
uv run pytest tests/test_search_weather_evidence.py -q
```

Initial result: exit 2 during collection with one expected error.

```text
ModuleNotFoundError: No module named 'app.domain.search_weather_evidence'
```

This established the missing typed presentation-adapter boundary before any
production mapper code existed.

### Service and API boundary

Command:

```bash
uv run pytest tests/test_search_v4_service.py tests/test_api.py -q \
  -k 'month_service_serializes_climatology or exact_date_weather_is_built_once or stale_forecasts_produce_climatology or typed_weather_evidence'
```

Result: exit 1, `4 failed, 48 deselected in 2.08s`.

Expected failures:

- `SearchV4Configuration` had no `weather_evidence` field;
- `search_v4_service` had no imported weather-evidence builder;
- populated weather evidence was rejected as an extra response field.

One intermediate mapper run had `7 passed, 2 failed`: one failure was the still
missing service response field, and the other exposed a test fixture that used
the preferred short-range source beyond its accepted 15-day window. The fixture
was corrected to use the existing long-range fallback source for lead days
16-30; production selection policy was not changed.

## GREEN Evidence

### New mapper and service behavior

Command:

```bash
uv run pytest tests/test_search_weather_evidence.py tests/test_search_v4_service.py \
  tests/test_api.py -q \
  -k 'search_weather_evidence or month_service_serializes_climatology or exact_date_weather_is_built_once or stale_forecasts_produce_climatology or typed_weather_evidence or representative_grouped_response_cost'
```

Result: exit 0, `13 passed, 48 deselected in 2.64s`.

### Final focused Python verification

Command:

```bash
uv run pytest tests/test_search_weather_evidence.py \
  tests/test_search_weather_factors.py tests/test_search_v4_service.py \
  tests/test_api.py -q
```

Final result: exit 0, `68 passed in 26.12s`.

Coverage includes:

- latest `normal_30y` selection with `recent_15y` fallback only when normal is
  absent;
- month-only climatology serialization;
- fresh preferred-source exact-date forecasts;
- partial, stale, incomplete, and missing evidence;
- null snow-depth preservation and policy-normalized rain/thaw risk;
- 31-point hard bounds and frozen response models;
- no cross-area summary leakage and same-object pass-through per ski area;
- optional null summaries through FastAPI serialization;
- unchanged ranking order, scores, group breakdowns, and factor breakdowns.

### Response-cost benchmark

Command:

```bash
uv run pytest tests/test_search_weather_evidence.py -q -s \
  -k representative_grouped_response_cost
```

Final result: exit 0, `1 passed, 8 deselected in 0.78s`.

Representative maximum shape: three recommendation regions, four
configurations per region, 31 historical points per configuration, 14 forecast
points per configuration, and 100 warm-process mapper iterations.

```text
baseline_bytes=2190606
complete_bytes=2337210
additive_bytes=146604
p95_ms=6.137
```

Guardrails:

- additive weather payload: `146,604` bytes, below `512 KiB` (`524,288` bytes);
- complete/baseline ratio: approximately `1.067x`, below `2x`;
- p95 summary construction: `6.137 ms`, below `25 ms`.

Both cost guardrails pass, so the summary remains enabled by default.

### Ruff and format

Commands:

```bash
uv run ruff check app/domain/search_weather_evidence.py \
  app/domain/search_factors/weather.py app/domain/search_v4_service.py \
  tests/test_search_weather_evidence.py tests/test_search_weather_factors.py \
  tests/test_search_v4_service.py tests/test_api.py

uv run ruff format --check app/domain/search_weather_evidence.py \
  app/domain/search_factors/weather.py app/domain/search_v4_service.py \
  tests/test_search_weather_evidence.py tests/test_search_weather_factors.py \
  tests/test_search_v4_service.py tests/test_api.py
```

Final result: `All checks passed!` and `7 files already formatted`.

### Frontend build

Command:

```bash
npm --prefix frontend run build
```

Final result: exit 0. TypeScript and Vite completed successfully, 29 modules
were transformed, and the production bundle built in 761 ms.

## Calls And Acquisition Evidence

- Exact-date service regression: climatology repository called once in bulk;
  forecast repository called once in bulk.
- Month service regression: climatology repository called once; forecast
  repository not called.
- The builder call spy records exactly one call per unique eligible ski area.
- Configurations sharing a ski area retain the same frozen summary object.
- The ranking projection with summaries populated equals the projection with
  the builder forced to return `None`.
- `generate_refinement_proposals` is replaced with a fail-fast stub in the
  focused no-refinement service test, proving the summary path adds no LLM call.
- `app/domain/search_weather_evidence.py` imports no repository, provider,
  acquisition, data-layer, or AI/LLM module.
- The only forecast-selection code change is the public rename of the existing
  helper and its two ranking call sites; source preference, freshness,
  completeness, elevation, lead-time, and blend-share rules are unchanged.

## Changed Files

- `app/domain/search_weather_evidence.py`
  - Added frozen typed weather response models.
  - Added deterministic historical/forecast mapping, finite interpretations and
    limitations, null preservation, and 31-point profile bounds.
- `app/domain/search_factors/weather.py`
  - Renamed the existing private selector to
    `select_usable_forecast_rows_by_date` and reused it from both ranking
    factors and the presentation mapper.
- `app/domain/search_v4_service.py`
  - Bound one timezone-aware search reference time.
  - Built one summary per unique ski area immediately after bulk weather load.
  - Passed the same summary through both frozen candidate states into the
    optional configuration response field.
- `frontend/src/types.ts`
  - Mirrored all four weather evidence interfaces and the optional nullable
    configuration field.
- `tests/test_search_weather_evidence.py`
  - Added mapper-mode, trust, null, immutability, bounds, and response-cost
    coverage.
- `tests/test_search_v4_service.py`
  - Added bulk-call, once-per-area, no-leakage, stale fallback, same-object,
    no-LLM, and ranking-invariance coverage.
- `tests/test_api.py`
  - Added populated and null typed weather serialization coverage.

No `.superdesign/` file was read, modified, staged, or committed.

## Self-Review

- Ranking integrity: `score_factor_evaluations` still receives the same
  evaluation tuple. Weather evidence is carried beside ranking state and is not
  read by ranking or grouping.
- Blend integrity: the forecast-share and snowpack policy functions are reused;
  no threshold, source preference, staleness, completeness, elevation, or
  lead-time rule changed.
- Trust boundary: stale and incomplete forecasts cannot create
  `forecast_assisted`; absence of trustworthy historical rows returns `None`
  even when forecasts exist.
- Determinism: row selection, profile ordering, provenance aggregation,
  interpretation, and limitations use finite deterministic helpers.
- Cost: summaries are built once per area, never per configuration, and all
  response/time limits pass with margin.
- Contract parity: Python and TypeScript field names, nullability, literals,
  and nested shapes align.
- Worktree hygiene: only the seven Task 3 files are intended for the commit;
  pre-existing untracked `.superdesign/` remains untouched.

## Concerns

No blocking concern. The representative complete response is still about
`2.34 MB`, primarily because the no-summary baseline already serializes about
`2.19 MB` of existing factor detail. Task 3 adds about `143.2 KiB` and remains
inside both accepted guardrails, but the absolute pre-existing response size is
worth tracking separately if Search V4 payload optimization becomes a future
task.

## Important Review Findings Follow-Up

### Status

`BLOCKED` on the required real-cardinality performance gate. The focused mixed
provenance correction is implemented and its regression slice passes, but the
uncapped current-catalog benchmark crosses all three owner checkpoints. No
architecture workaround was attempted and no follow-up commit was created.

Classification remains `review-gated` because this follow-up affects the Search
V4 evidence contract, source-trust semantics, and request-path response cost.

- Developer Decision Checkpoint: the provenance direction was resolved by the
  review finding. The implementation uses typed source records mapped to exact
  profile dates, preserves exact existing top-level metadata for homogeneous
  rows, and emits `mixed` plus nullable top-level scalar provenance for
  heterogeneous rows.
- ADR: not needed for the focused provenance correction. The benchmark failure
  now requires an owner checkpoint before any result cap, ownership change,
  on-demand evidence design, or evidence reduction.
- Advisory feature review: not run because the mandatory benchmark stop occurred
  before final verification and commit readiness.

### RED Evidence

Command:

```bash
uv run pytest tests/test_search_weather_evidence.py -q -k 'provenance or mixed'
```

Initial result: exit 1, `3 failed, 7 deselected in 0.18s`.

The failures were the expected missing-contract failures:

- homogeneous historical evidence had no `provenance_status` or typed sources;
- mixed historical rows exposed a synthetic combined source model, latest
  computed time, and min/max baseline;
- mixed forecast rows exposed combined producer/model labels and claimed the
  latest issue time (`2027-01-01T06:00:00+00:00`) even though it did not apply
  to every forecast point.

### Focused Provenance GREEN Evidence

Command:

```bash
uv run pytest tests/test_search_weather_evidence.py -q -k 'provenance or mixed'
```

Result: exit 0, `3 passed, 7 deselected in 0.08s`.

The uncommitted focused correction now provides:

- `HistoricalWeatherSource` records with exact model, computed time, baseline,
  evidence-season, archive-year, row-count, and profile-date provenance;
- `ForecastWeatherSource` records with exact run, source key, producer, model,
  issue time, row-count, and profile-date provenance;
- `provenance_status: homogeneous | mixed` on both top-level evidence types;
- exact existing top-level provenance for homogeneous rows;
- `null` top-level model/time/baseline scalar provenance for mixed rows instead
  of synthesized claims;
- aligned Python/API fixture and TypeScript field names and nullability.

### Real-Cardinality Benchmark Evidence

The original 3-region/12-configuration fixture benchmark was removed. Its
replacement executes `search_trip_configurations` against the current catalog
without a location cap for a 31-day exact window beginning `2027-02-01`.

Command:

```bash
uv run pytest \
  tests/test_search_v4_service.py::test_current_catalog_uncapped_grouped_response_cost \
  -q -s
```

Result: exit 1 after the mandatory guardrail assertion.

```text
current_catalog_uncapped_grouped_response_cost groups=25 configurations=60 summary_builds=39 baseline_bytes=964040 complete_bytes=2056304 additive_bytes=1092264 complete_to_baseline_ratio=2.133007 p95_ms=32.510 iterations=100
```

Guardrail outcome:

| Measure | Result | Limit | Outcome |
| --- | ---: | ---: | --- |
| Additive serialized bytes | 1,092,264 | 524,288 | FAIL |
| Complete/baseline ratio | 2.133007x | 2x | FAIL |
| p95 summary construction | 32.510 ms | 25 ms | FAIL |

The benchmark also established:

- 25 uncapped recommendation groups and 60 serialized configurations;
- 81 eligible candidates and 39 once-per-area summary builds;
- 31 historical and 31 forecast profile points on every returned
  configuration;
- one bulk climatology-repository call and one bulk forecast-repository call in
  both complete and no-summary runs;
- identical ranking projections between complete and no-summary responses;
- injected in-memory repositories only, with fail-fast guards on default
  catalog/weather repositories and the refinement LLM path; no provider,
  acquisition, or LLM call was introduced.

### Mandatory Stop

Per the accepted Task 3 guardrail, work stopped without capping production,
changing API ownership, moving weather evidence on demand, weakening the
evidence contract, running an architecture workaround, or committing the
follow-up. The broader focused suite, Ruff/format, frontend build, and final
exact-head advisory review were not run after the guardrail failure because the
brief requires an immediate owner checkpoint at this point.

The focused provenance implementation, mixed-row tests, real-cardinality
benchmark, aligned TypeScript/API fixture, and this report update remain
uncommitted as evidence for that checkpoint. Untracked `.superdesign/` remains
untouched.

## Revised On-Demand Dossier Implementation

Classification: `review-gated`. The accepted revised brief resolves the
Developer Decision Checkpoint: detailed evidence is a bounded one-area dossier,
not a grouped-search configuration field. Accepted ADR 0014 owns the new
on-demand evidence boundary and expiry-aware browser cache. A focused advisory
design review covered Backend/API, Data Trust, Performance, UI/UX, and
Accessibility; its High cache-validity and Medium contract findings were
resolved in the revised spec and brief before implementation. An independent
exact-head task review follows this report.

### RED Evidence

```bash
uv run pytest tests/test_search_weather_evidence.py -q
```

Initial result: exit 2 during collection. The expected missing revised-contract
failure was:

```text
ImportError: cannot import name 'SearchWeatherEvidenceAvailableResponse'
```

After the frozen response models were added, the retained grouped-search tests
failed as expected because `SearchV4Configuration.weather_evidence` had been
removed. This proved the presentation contract had moved out of `/api/search`
rather than being omitted accidentally.

### GREEN Evidence

```bash
uv run pytest tests/test_search_weather_evidence.py \
  tests/test_search_weather_factors.py tests/test_search_v4_service.py \
  tests/test_api.py tests/test_observability.py -q
```

Final result: exit 0, `108 passed in 28.04s`.

```bash
uv run pytest tests/test_search_weather_evidence.py -q -s \
  -k one_area_endpoint_cost
```

Result: exit 0, `1 passed, 13 deselected in 1.17s`.

```text
one_area_endpoint_cost route_envelope_bytes=32809 p95_ms=7.342 iterations=100
```

The benchmark uses the current catalog snapshot, injected one-area in-memory
repositories, 31 historical points, 31 forecast points, 31 exact historical
source records, 31 exact forecast source records, and mixed provenance. It
serializes the actual FastAPI route once and measures 100 warm domain-service
constructions. `32,809` bytes is below `131,072`, and `7.342 ms` p95 is below
`25 ms`.

### Revised Contract And Verification

- `POST /api/search/weather-evidence` now returns the versioned discriminated
  `available | unavailable` response and bounded `422` errors.
- Unknown ski areas are rejected after catalog/trust validation and before
  weather repository access. A month without a travel window returns the typed
  `travel_window_missing` response; missing trustworthy history returns the
  typed `historical_evidence_unavailable` response.
- `SearchV4Configuration` no longer contains `weather_evidence`. Search
  ranking still bulk-loads weather once and retains its score, grouping, factor,
  and repository-call behavior.
- The dossier reuses ranking's usable forecast selector, carries fresh complete
  forecast rows only, labels date completeness as `coverage_status`, computes
  expiry from the earliest selected forecast run, and otherwise uses a
  server-owned five-minute validity.
- Historical and forecast provenance preserve exact per-source fields and
  dates. Mixed scalar provenance and elevation are null at the top level;
  source records carry exact elevations and both source collections and profiles
  are capped at 31.
- The HTTP duration metric records `/api/search/weather-evidence` as a bounded
  route label. TypeScript mirrors the request, source, evidence, and
  discriminated response contracts; `npm --prefix frontend run build` passed.

### Files Changed

- `app/domain/search_weather_evidence.py`
- `app/domain/search_v4_service.py`
- `app/api/routes.py`
- `frontend/src/types.ts`
- `tests/test_search_weather_evidence.py`
- `tests/test_search_v4_service.py`
- `tests/test_api.py`

### Self-Review And Concern

The dossier does not rank candidates, generate refinements, call a provider, or
invoke an LLM. It makes at most one call to each injected repository and only
for the requested area. The only concern is intentional: validity is exposed
to clients but no server cache was added, per the accepted brief; a request
after expiry re-reads the latest repository head rather than retaining a stale
in-process result. `.superdesign/` remains untracked and untouched.

## Exact-Head Review Fixes

Implemented the two Important findings from `.superpowers/sdd/task-3-review.md`
in commit `a0e75fe` (`fix: align weather evidence validity provenance`).

### RED Evidence

```bash
uv run pytest tests/test_search_v4_service.py -q \
  -k 'uses_presented_forecast_rows_for_validity_and_elevation or preserves_nullable_historical_elevation'
```

Initial result: exit 1, `2 failed, 21 deselected in 0.88s`.

- The long exact-date case returned the generic five-minute validity
  (`2027-01-09T12:05:00+00:00`) instead of the accepted forecast run expiry
  (`2027-01-09T13:10:00+00:00`).
- A schema-valid historical row with `elevation_m=None` raised a Pydantic
  `int_type` validation error while constructing `HistoricalWeatherSource`.

### Fix

- One provider-relative accepted-forecast-row collection now drives forecast
  presentation, cache expiry, and top-level elevation provenance.
- Historical source elevation is nullable in Python and TypeScript.
- Elevation provenance now distinguishes `exact`, `mixed`, and `unavailable`;
  no known selected elevation returns `null` plus `unavailable`, while known
  plus unknown or differing known elevations remain `mixed`.
- Ranking, grouped Search V4 repository access, on-demand route ownership, and
  source/profile caps are unchanged.

### Final Verification

```bash
uv run pytest tests/test_search_weather_evidence.py \
  tests/test_search_weather_factors.py tests/test_search_v4_service.py \
  tests/test_api.py -q
```

Result: exit 0, `84 passed in 29.57s`.

```bash
uv run ruff check app/domain/search_weather_evidence.py \
  app/domain/search_v4_service.py tests/test_search_weather_evidence.py \
  tests/test_search_v4_service.py

uv run ruff format --check app/domain/search_weather_evidence.py \
  app/domain/search_v4_service.py tests/test_search_weather_evidence.py \
  tests/test_search_v4_service.py
```

Result: `All checks passed!` and `4 files already formatted`.

```bash
npm --prefix frontend run build
```

Result: exit 0; TypeScript and Vite completed successfully, 29 modules were
transformed, and the production bundle built in 769 ms.

```bash
uv run pytest tests/test_search_weather_evidence.py -q -s \
  -k one_area_endpoint_cost
```

Result: exit 0, `1 passed, 14 deselected in 1.26s`.

```text
one_area_endpoint_cost route_envelope_bytes=32809 p95_ms=9.089 iterations=100
```

The route envelope remains below `131,072` bytes and warm domain construction
remains below `25 ms` p95.

### Files Changed

- `app/domain/search_weather_evidence.py`
- `app/domain/search_v4_service.py`
- `frontend/src/types.ts`
- `tests/test_search_weather_evidence.py`
- `tests/test_search_v4_service.py`

`.superdesign/` was not read, modified, staged, or committed.

## Bounded Second Review Fix

### RED Evidence

```bash
uv run pytest tests/test_search_weather_evidence.py -q \
  -k repeated_calendar_dates_in_historical_evidence
```

Result: exit 1, `1 failed, 15 deselected`. The complete `2027-01-01` through
`2028-01-01` exact-date case returned `282.25068493150684` instead of the
date-weighted `282.5`, proving the repeated January 1 occurrence was omitted.

### Fix

Exact-date selection now resolves one latest normal/recent climatology row for
each requested date occurrence. Month-mode selection remains one row per
available calendar date. Aggregation and coverage can use all 366 selected
rows, while the existing 31-point profile and 31-source caps remain unchanged.

### GREEN Evidence

```bash
uv run pytest tests/test_search_weather_evidence.py -q \
  -k repeated_calendar_dates_in_historical_evidence
```

Result: exit 0, `1 passed, 15 deselected`. The regression proves a `282.5`
average, `row_count == 366`, and no `365 of 366` limitation.

```bash
uv run pytest tests/test_search_weather_evidence.py tests/test_search_v4_service.py -q
```

Result: exit 0, `39 passed in 4.57s`.

```bash
uv run ruff check app/domain/search_weather_evidence.py \
  tests/test_search_weather_evidence.py tests/test_search_v4_service.py
uv run ruff format --check app/domain/search_weather_evidence.py \
  tests/test_search_weather_evidence.py tests/test_search_v4_service.py
```

Result: Ruff check passed and all 3 files were already formatted.

```bash
uv run pytest tests/test_search_weather_evidence.py -q -s \
  -k one_area_endpoint_cost
```

Result: exit 0, `1 passed, 15 deselected`; route envelope remained `32809`
bytes and warm domain p95 was `7.273 ms` over 100 iterations.

### Files And Commit

- `app/domain/search_weather_evidence.py`
- `tests/test_search_weather_evidence.py`

Fix commit: `9a6a236b3d4d79bc0322bde76073f71df92451ef` (`fix: weight repeated
dates in weather evidence`). `.superdesign/` remained untouched and untracked.

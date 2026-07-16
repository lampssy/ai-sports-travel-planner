# Search V4 Web Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the temporary Search V4 form-and-empty-canvas UI with the
accepted Snowcast homepage, grouped recommendation board, and evidence-led
dossier while preserving deterministic Search V4 ranking and honest weather
and accommodation evidence.

**Architecture:** Keep `POST /api/search` as the only search and rerank
boundary. Add two optional, typed server-owned presentation contracts for
refinement previews and weather evidence, then decompose the React client into
a thin application orchestrator, pure search/session helpers, and focused page
components. Use browser history and in-memory session state for dossier
navigation; do not add a router or persistence layer.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, React 18, TypeScript 5,
Vite 6, Tailwind 3, Vitest, Testing Library, Playwright, and the approved
`lucide-react` icon library.

## Global Constraints

- Classification: `review-gated`, using the full design flow.
- High-risk domains: planning explainability, source and estimate trust,
  shared Search V4 response contracts, request-path response cost, and
  product-facing navigation.
- Developer Decision Checkpoints: resolved. The owner approved the complete
  design in
  `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`,
  including the dedicated dossier route, typed refinement/weather summaries,
  browser-session return state, and `lucide-react` as the sole new frontend
  dependency.
- ADR status: no new ADR is required under the accepted design. Stop for a new
  owner checkpoint and reassess ADR need before adding a router, persistent
  search state, an on-demand evidence endpoint, a new provider request, or a
  new evidence-aggregation ownership boundary.
- Advisory design review: completed on 2026-07-16 for the accepted spec and
  this plan. The plan review's current-trip test, response-cost gate, and
  task-local accessibility gaps are resolved below; no Blocker or High finding
  remains open. Advisory feature review is required before final handoff.
- Preserve Search V4 ranking weights, eligibility, factor semantics, forecast
  blending, and catalog acquisition. Presentation adapters may summarize only
  evidence already loaded for the ranking request.
- Do not parse `FactorScoreBreakdown.raw_value` or `explanation_inputs` in the
  browser. User-facing weather charts consume only the new typed summary.
- Do not add provider-backed hotels, invented properties, live availability,
  current conditions for month searches, or score-delta claims.
- Use deterministic templates for rank movement, evidence interpretation,
  limitations, trip essentials, strengths, and watchouts. LLM output remains
  limited to the existing bounded refinement proposal path.
- Use `lucide-react` for interface icons. Icons inside labelled controls are
  decorative with `aria-hidden`; icon-only controls require an accessible
  name and tooltip. Do not add another UI, routing, chart, or animation
  dependency.
- Build weather charts with semantic React and a bounded inline SVG plus an
  equivalent structured value list. Do not hand-author decorative SVG assets.
- Keep `.superdesign/` untracked. The accepted visual pack in
  `docs/ui-concepts/2026-07-16-search-v4-web-experience/` is the visual oracle.
- Current-trip behavior remains compatible and outside the redesign scope.
- Known baseline at plan creation: `npm --prefix frontend test` and
  `npm --prefix frontend run build` pass; all five existing Playwright tests
  fail because they mock the removed pre-V4 response and query old selectors.
  Task 1 repairs that contract baseline before feature assertions are added.
- Execute each task test-first, run its focused checks, inspect the diff, and
  commit before starting the next task. Never commit generated `dist/`,
  `test-results/`, TypeScript build-info churn, or `.superdesign/` files.

## Execution Notes

Keep this section append-only while executing the plan. Record the exact commit
for each completed task, the representative weather-summary byte/time
measurement from Task 3, advisory findings and resolutions, and the final
verification commands. At plan creation, frontend unit tests and build were
green while the stale five-test E2E suite was red as described above.

- 2026-07-16 plan review: resolved a High current-trip regression-coverage gap
  by making its repaired E2E smoke mandatory in Task 1 and every routing
  verification; resolved Medium findings by adding a maximum-shape response
  budget and task-local keyboard/focus assertions.

---

### Task 1: Establish The Search V4 Frontend Contract And Icon Baseline

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/tests/e2e/fixtures/searchV4.ts`
- Modify: `frontend/tests/e2e/app.spec.ts`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Install the approved icon dependency**

Run:

```bash
npm --prefix frontend install lucide-react
```

Expected: `frontend/package.json` and `frontend/package-lock.json` add
`lucide-react`; no other dependency changes.

- [ ] **Step 2: Replace the stale E2E fixture with an exact Search V4 fixture**

Create `frontend/tests/e2e/fixtures/searchV4.ts` exporting:

```ts
import type { SearchResponse } from "../../../src/types";

export const monthSearchResponse: SearchResponse = {
  search_model_version: "search-v4",
  ranking_policy_version: "search-v4-policy-1",
  ranking_status: "ranked",
  unscored_reason: null,
  applied_intent: {
    constraints: {
      location: { country: "France" },
      travel_window: { month: 3 },
    },
    party: { skill_levels: ["intermediate"] },
    travel_context: {},
    objectives: [{ factor_id: "pass_terrain_value", importance: "normal" }],
    group_priorities: [],
    factor_preferences: [],
    assumptions: [],
  },
  eligible_candidate_count: 7,
  excluded_candidate_count: 3,
  results: [/* two fully typed recommendation groups */],
  refinements: [],
};
```

Populate two recommendation groups and at least one alternative configuration
using the current `SearchV4Configuration` fields from `frontend/src/types.ts`.
The first configuration must have pass coverage, price, near-lift access, an
estimated lodging range, ranked groups/factors, and no weather summary yet.

- [ ] **Step 3: Write a current-contract E2E smoke test before redesign work**

Replace the stale pre-V4 API route and selectors in
`frontend/tests/e2e/app.spec.ts` with one contract smoke test:

```ts
test("submits a typed Search V4 request and renders grouped results", async ({ page }) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.goto("/");
  await page.getByRole("button", { name: /search and rank/i }).click();
  await expect(page.getByText("Tignes - Val d'Isere")).toBeVisible();
  expect(searchRequests[0].intent.constraints.location)
    .toEqual({ country: "France" });
});
```

Delete fixture fields from removed Search V3 contracts. Repair and retain a
mandatory anonymous current-trip regression test using the live contract:

```ts
test("anonymous current-trip route remains available", async ({ page }) => {
  await mockSearchV4Api(page, monthSearchResponse, []);
  await page.goto("/current-trip");
  await expect(
    page.locator("main").getByText("Trip companion", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/save a ranked configuration/i)).toBeVisible();
  await page.getByRole("button", { name: /back to search/i }).click();
  await expect(page).toHaveURL(/\/$/);
});
```

This test must be repaired if the retained current-trip copy uses a different
semantic element; it must not be deleted during the routing redesign.

- [ ] **Step 4: Run E2E and confirm the stale baseline has been repaired**

Run:

```bash
npm --prefix frontend run test:e2e
```

Expected: the current-contract smoke passes and no test refers to
`configuration_id`, `score_components`, `planning_summary`, or
`GET /api/search?...`.

- [ ] **Step 5: Reuse the fixture shape in unit tests**

Refactor the local factory in `frontend/src/App.test.tsx` only enough to align
its data with the E2E fixture categories. Do not change product behavior in
this task.

- [ ] **Step 6: Run frontend unit and build checks**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: seven existing unit tests pass and the production build succeeds.

- [ ] **Step 7: Commit the repaired baseline**

```bash
git add frontend/package.json frontend/package-lock.json \
  frontend/tests/e2e/fixtures/searchV4.ts frontend/tests/e2e/app.spec.ts \
  frontend/src/App.test.tsx
git commit -m "test: establish Search V4 web contract baseline"
```

### Task 2: Add Deterministic Refinement Preview Metadata

**Files:**

- Modify: `app/domain/search_refinement.py`
- Modify: `app/domain/search_v4_service.py`
- Modify: `frontend/src/types.ts`
- Modify: `tests/test_search_refinement.py`
- Modify: `tests/test_search_v4_service.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing domain tests for per-option variant outcomes**

Add tests proving that validation returns one outcome per option, ordered to
match the proposal options, without exposing scores:

```python
def test_validated_refinement_preserves_each_variant_ranking() -> None:
    validated = validate_refinement_proposal(...)

    assert len(validated.variant_outcomes) == len(validated.proposal.options)
    assert validated.variant_outcomes[0].ordered_candidate_ids[0] == "candidate-b"
    assert not hasattr(validated.variant_outcomes[0], "scores")
```

Run:

```bash
uv run pytest tests/test_search_refinement.py -q
```

Expected: fail because `variant_outcomes` does not exist.

- [ ] **Step 2: Preserve bounded variant outcomes at the validation boundary**

Add a frozen response-neutral model in `app/domain/search_refinement.py`:

```python
class RefinementVariantOutcome(_RefinementModel):
    ordered_candidate_ids: tuple[str, ...]
    eligible_candidate_ids: frozenset[str]


class ValidatedRefinementProposal(_RefinementModel):
    proposal: RefinementProposal
    impact: RefinementImpact
    variant_outcomes: tuple[RefinementVariantOutcome, ...]
```

Construct it from each existing `_VariantRanking`. Keep score mappings private
inside validation; do not add them to `RefinementVariantOutcome`.

- [ ] **Step 3: Write failing service tests for grouped rank previews**

Add tests covering:

- a region moving from rank 3 to rank 2;
- a region entering or leaving the visible top three with a `None` rank;
- no more than three changed regions in a preview;
- candidate-level changes within one region not creating duplicate region rows;
- `eligible_candidate_count_delta` relative to the baseline;
- absent refinements when the LLM path returns no validated proposal.

Run:

```bash
uv run pytest tests/test_search_v4_service.py -q -k refinement
```

Expected: fail because response options do not have `preview`.

- [ ] **Step 4: Add response-only refinement models and mapping**

In `app/domain/search_v4_service.py`, introduce additive response models rather
than adding server-computed fields to the LLM-authored `RefinementOption`:

```python
class SearchV4RefinementRankChange(_SearchV4Model):
    ski_region_id: str
    previous_rank: int | None = Field(default=None, gt=0)
    preview_rank: int | None = Field(default=None, gt=0)


class SearchV4RefinementPreview(_SearchV4Model):
    top_rank_changes: tuple[SearchV4RefinementRankChange, ...] = Field(max_length=3)
    eligible_candidate_count_delta: int


class SearchV4RefinementOption(_SearchV4Model):
    label: str
    description: str
    group_priority_patches: tuple[GroupPriorityPatch, ...] = ()
    factor_preference_patches: tuple[FactorPreferencePatch, ...] = ()
    objective_patches: tuple[SearchObjective, ...] = ()
    preview: SearchV4RefinementPreview | None = None
```

Add the corresponding proposal model and change `SearchV4Response.refinements`
to that response-only type. Update `_refinements` to retain validated items,
deduplicate candidate order into ski-region order, compare baseline and each
option's grouped rank, and include only movements touching the visible top
three. The applied patch payload remains unchanged.

- [ ] **Step 5: Mirror the additive contract in TypeScript**

Add `RefinementRankChange` and `RefinementPreview` interfaces and optional
`preview` to `frontend/src/types.ts`. Do not expose score deltas, candidate IDs,
factor IDs beyond the existing typed patches, or policy internals.

- [ ] **Step 6: Verify API serialization and backward compatibility**

Add API assertions that the response serializes `preview`, remains valid when
`preview` is `null`, and preserves existing refinement patch fields.

Run:

```bash
uv run pytest tests/test_search_refinement.py tests/test_search_v4_service.py \
  tests/test_api.py -q
uv run ruff check app/domain/search_refinement.py app/domain/search_v4_service.py \
  tests/test_search_refinement.py tests/test_search_v4_service.py tests/test_api.py
npm --prefix frontend run build
```

Expected: all focused tests pass, Ruff reports no errors, and TypeScript accepts
the additive response field.

- [ ] **Step 7: Commit the refinement contract**

```bash
git add app/domain/search_refinement.py app/domain/search_v4_service.py \
  frontend/src/types.ts tests/test_search_refinement.py \
  tests/test_search_v4_service.py tests/test_api.py
git commit -m "feat: expose deterministic refinement previews"
```

### Task 3: Add Typed Weather Evidence Without Changing Ranking

**Files:**

- Create: `app/domain/search_weather_evidence.py`
- Modify: `app/domain/search_factors/weather.py`
- Modify: `app/domain/search_v4_service.py`
- Modify: `frontend/src/types.ts`
- Create: `tests/test_search_weather_evidence.py`
- Modify: `tests/test_search_v4_service.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing mapper tests for every evidence mode**

Create `tests/test_search_weather_evidence.py` with fixtures for:

- a month-only intent with `normal_30y` and `recent_15y` climatology rows;
- exact dates with fresh, complete preferred-source forecast rows;
- exact dates with partial usable coverage;
- stale forecast rows;
- incomplete forecast rows;
- missing climatology and forecast evidence;
- null snow depth and bounded 31-point profiles.

Assert the accepted rules directly:

```python
assert summary.mode == "climatology"
assert summary.forecast is None
assert summary.historical.daily_profile[0].snow_depth_cm_p50 is not None

assert assisted.mode == "forecast_assisted"
assert assisted.forecast.usable_date_count == 3
assert assisted.historical is not None
assert len(assisted.forecast.daily_profile) <= 31
```

Run:

```bash
uv run pytest tests/test_search_weather_evidence.py -q
```

Expected: fail because the module does not exist.

- [ ] **Step 2: Share the forecast-row selection used by ranking**

Rename `_forecast_rows_by_date` in
`app/domain/search_factors/weather.py` to
`select_usable_forecast_rows_by_date` and keep its existing source preference,
freshness, completeness, elevation, and lead-time rules unchanged. Use the
public helper from `_trip_window_snow_fit`,
`_trip_window_snowpack_outlook`, and the new presentation mapper. Add focused
weather-factor regression tests if the rename exposes an untested branch.

- [ ] **Step 3: Implement frozen weather presentation models and mapper**

In `app/domain/search_weather_evidence.py`, define the exact accepted response
types:

```python
class WeatherEvidencePoint(_WeatherEvidenceModel):
    date_or_month_day: str
    snow_depth_cm: float | None = None
    snow_depth_cm_p25: float | None = None
    snow_depth_cm_p50: float | None = None
    snow_depth_cm_p75: float | None = None
    snowfall_cm: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    rain_risk: float | None = None
    thaw_risk: float | None = None
    wind_gust_kmh: float | None = None


class SearchWeatherEvidence(_WeatherEvidenceModel):
    mode: Literal["climatology", "forecast_assisted"]
    window_label: str
    elevation_band: Literal["mid_mountain"] = "mid_mountain"
    elevation_m: int | None = None
    interpretation: str
    limitations: tuple[str, ...] = ()
    historical: HistoricalWeatherEvidence
    forecast: ForecastWeatherEvidence | None = None
```

Implement `build_search_weather_evidence(...)` with these rules:

- select latest `normal_30y` rows per month/day, falling back to latest
  `recent_15y` only when normal rows are absent;
- preserve source model, computed time, baseline years, seasons, and nulls;
- use `select_usable_forecast_rows_by_date` for exact dates;
- count a forecast date only when `forecast_share_for_lead_days(...) > 0`;
- derive `average_forecast_share` only from usable dates;
- reuse `snowpack_outlook(...)` for policy-normalized forecast rain and thaw
  risk when a complete snowpack row exists, preserving `null` otherwise;
- emit deterministic interpretation and limitation strings from finite helper
  functions;
- order profiles chronologically and cap both profiles at 31 points;
- return `None` only when no trustworthy historical summary can be built.

- [ ] **Step 4: Build each ski-area summary once per request**

In `search_trip_configurations`, bind one timezone-aware
`search_reference_time`, preload weather as today, and construct
`weather_evidence_by_area` immediately afterward. Add
`weather_evidence: SearchWeatherEvidence | None` to
`_FactorEvaluatedCandidate`, `_EvaluatedCandidate`, and the optional
`SearchV4Configuration.weather_evidence` field. Pass the same immutable summary
through grouping; do not rebuild it per configuration and do not query a
repository from `_configuration`.

- [ ] **Step 5: Mirror the weather contract in TypeScript**

Add the accepted `WeatherEvidencePoint`, `HistoricalWeatherEvidence`,
`ForecastWeatherEvidence`, and `SearchWeatherEvidence` interfaces to
`frontend/src/types.ts`, and add:

```ts
weather_evidence?: SearchWeatherEvidence | null;
```

to `SearchV4Configuration`.

- [ ] **Step 6: Add service/API tests and measure response cost**

Extend service and API tests to prove:

- month requests serialize climatology only;
- exact-date requests use only fresh usable forecasts;
- stale forecasts produce a climatology fallback and explicit limitation;
- one ski area's summary cannot leak into another configuration;
- omitted summaries remain schema-valid;
- repositories are still called once in bulk and no provider/LLM call is
  added.

Add one representative test that constructs a complete grouped response with
four configurations in each of three regions, 31 historical points per
configuration, and 14 forecast points where applicable. Print the serialized
byte count and mapper duration under `pytest -s`. Measure the no-summary
response with the same configuration fixture, then enforce both guardrails:

- p95 summary-construction time over 100 warm-process iterations is at most
  `25 ms` for the maximum-shape response;
- the additive serialized weather payload is at most `512 KiB` and the complete
  response is at most twice the no-summary baseline size.

Also assert the contract's hard profile bounds and absence of additional
acquisitions. Record the baseline bytes, complete bytes, additive bytes, and p95
duration in this plan's execution notes. If either guardrail fails, do not
enable the summary by default; stop for the accepted owner checkpoint instead
of weakening the evidence or adding an on-demand endpoint automatically.

Run:

```bash
uv run pytest tests/test_search_weather_evidence.py \
  tests/test_search_weather_factors.py tests/test_search_v4_service.py \
  tests/test_api.py -q
uv run pytest tests/test_search_weather_evidence.py -q -s \
  -k representative_grouped_response_cost
uv run ruff check app/domain/search_weather_evidence.py \
  app/domain/search_factors/weather.py app/domain/search_v4_service.py \
  tests/test_search_weather_evidence.py tests/test_search_weather_factors.py \
  tests/test_search_v4_service.py tests/test_api.py
npm --prefix frontend run build
```

Expected: all focused tests pass; the benchmark prints one byte count and one
mapping duration; Ruff and TypeScript pass.

- [ ] **Step 7: Commit the weather contract**

```bash
git add app/domain/search_weather_evidence.py app/domain/search_factors/weather.py \
  app/domain/search_v4_service.py frontend/src/types.ts \
  tests/test_search_weather_evidence.py tests/test_search_weather_factors.py \
  tests/test_search_v4_service.py tests/test_api.py
git commit -m "feat: expose typed Search V4 weather evidence"
```

### Task 4: Build The Application Shell, Session Model, And Homepage

**Files:**

- Create: `frontend/src/navigation.ts`
- Create: `frontend/src/navigation.test.ts`
- Create: `frontend/src/search/searchSession.ts`
- Create: `frontend/src/search/searchSession.test.ts`
- Create: `frontend/src/search/searchPresentation.ts`
- Create: `frontend/src/search/Homepage.tsx`
- Create: `frontend/src/search/SearchCommandHeader.tsx`
- Create: `frontend/src/search/SearchFiltersDrawer.tsx`
- Create: `frontend/src/ui/AppShell.tsx`
- Modify: `frontend/src/ui/SnowcastLogo.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing pure-helper and homepage tests**

Cover:

- `/`, `/current-trip`, and
  `/recommendations/:region?candidate=:candidate` route parsing;
- invalid dossier route recovery;
- preservation of query, intent, response, selected candidates, expanded group
  IDs, and scroll position in an in-memory `SearchSession`;
- initial homepage headline and persistent trip-brief label;
- one `Example recommendation` label and no process-step cards;
- parse/search submission preserves the brief and moves focus to the results
  heading after success;
- loading disables duplicate submission and names the work;
- `Adjust filters` opens a labelled drawer and closes with Escape/focus return;
- removable parsed chips have names such as `Remove France`.

Run:

```bash
npm --prefix frontend test -- src/navigation.test.ts \
  src/search/searchSession.test.ts src/App.test.tsx
```

Expected: fail because the route/session modules and homepage do not exist.

- [ ] **Step 2: Implement browser-history routing without a router package**

Define:

```ts
export type AppRoute =
  | { name: "search" }
  | { name: "currentTrip" }
  | { name: "dossier"; skiRegionId: string; candidateId: string | null };

export function parseAppRoute(location: Location): AppRoute;
export function buildDossierHref(regionId: string, candidateId: string): string;
export function navigate(href: string): void;
```

`navigate` must call `history.pushState` and dispatch one local navigation
event. `App` subscribes to that event and `popstate`. Do not monkey-patch
`history`, persist results to storage, or rerun search on dossier navigation.

- [ ] **Step 3: Extract pure search/session transformations from `App.tsx`**

Move intent building, parsed-filter merging, filter validation, selected
candidate lookup, and rerank state reconciliation into
`searchSession.ts`/`searchPresentation.ts`. Define `SearchSession` with:

```ts
export interface SearchSession {
  brief: string;
  intent: SearchIntent;
  response: SearchResponse;
  expandedGroupIds: Set<string>;
  selectedCandidateIdByGroup: Record<string, string>;
  resultsScrollY: number;
}
```

Keep this object in React state for the current tab only. Add pure helpers that
preserve still-present expanded groups and always expand a new winner after
rerank.

- [ ] **Step 4: Implement the shared shell and homepage command stage**

Build the accepted first viewport using:

- `AppShell` for the shared max-width canvas and midnight navigation;
- `Homepage` for the literal product offer, planning signal, command input,
  parsed chips, and example recommendation;
- `SearchFiltersDrawer` for manual exact controls;
- Lucide `Search`, `CalendarDays`, `SlidersHorizontal`, `MountainSnow`,
  `ShieldCheck`, `TrendingUp`, and `AlertTriangle` icons.

Use text beside semantic status icons. Preserve the existing Snowcast logo but
remove duplicated inline tool icons that Lucide now owns.

- [ ] **Step 5: Add the accepted visual tokens**

In `frontend/src/index.css`, define CSS custom properties for midnight,
alpine blue, alpenglow, powder, ice, snow, pine, amber, borders, shadows, focus,
content width, and density. Use a restrained page-edge pink/blue atmosphere;
cards stay white or neutral. Add responsive rules, `prefers-reduced-motion`,
and stable focus-visible outlines. Do not use viewport-scaled type or negative
letter spacing.

- [ ] **Step 6: Make `App.tsx` a thin orchestrator**

`App` owns API calls, session state, current-trip state, current route, and
page-level error/loading state. Page components receive typed data and event
callbacks. Remove the permanent left filter form from the initial screen.

- [ ] **Step 7: Update E2E for homepage-to-results transition**

Add desktop and mobile tests that submit the labelled brief, confirm one POST
to `/api/search`, preserve the brief in the compact results header, and focus
the results heading. Add drawer keyboard behavior and no-horizontal-overflow
assertions. The focused test must prove Escape closes the drawer, focus returns
to `Adjust filters`, and successful search focuses the results heading.

- [ ] **Step 8: Verify and commit the homepage increment**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Expected: unit, build, and homepage/current-contract E2E checks pass.

```bash
git add frontend/src/navigation.ts frontend/src/navigation.test.ts \
  frontend/src/search/searchSession.ts frontend/src/search/searchSession.test.ts \
  frontend/src/search/searchPresentation.ts frontend/src/search/Homepage.tsx \
  frontend/src/search/SearchCommandHeader.tsx \
  frontend/src/search/SearchFiltersDrawer.tsx frontend/src/ui/AppShell.tsx \
  frontend/src/ui/SnowcastLogo.tsx frontend/src/App.tsx \
  frontend/src/App.test.tsx frontend/src/index.css \
  frontend/tests/e2e/app.spec.ts
git commit -m "feat: build Snowcast Search V4 command stage"
```

### Task 5: Build The Hybrid Recommendation Board And Refinement Flow

**Files:**

- Create: `frontend/src/search/RecommendationBoard.tsx`
- Create: `frontend/src/search/SearchContextRail.tsx`
- Create: `frontend/src/search/SearchContextRail.test.tsx`
- Create: `frontend/src/search/RecommendationCard.tsx`
- Create: `frontend/src/search/RecommendationCard.test.tsx`
- Create: `frontend/src/search/RefinementCard.tsx`
- Create: `frontend/src/search/RefinementCard.test.tsx`
- Create: `frontend/src/search/TripEssentials.tsx`
- Create: `frontend/src/search/ScoringDetails.tsx`
- Modify: `frontend/src/search/searchPresentation.ts`
- Create: `frontend/src/search/searchPresentation.test.ts`
- Modify: `frontend/src/search/searchSession.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing deterministic presentation tests**

Test `selectTripEssentialCategories` and formatters for:

- active objectives/preferences/constraints first;
- default terrain, pass value, lift access, lodging, travel order;
- one category set shared across visible top-three groups;
- at most three categories;
- exact pass price per day only when amount and duration exist;
- ranges remain ranges;
- `estimated` labels remain explicit;
- missing/`needs_source` values are omitted rather than replaced by empty
  tiles;
- factor-derived rationale/watchout uses only deterministic typed fields and
  approved copy maps.

Also test refinement preview copy for movement, entry, exit, eligibility-only,
and absent preview.

Run:

```bash
npm --prefix frontend test -- src/search/searchPresentation.test.ts
```

Expected: fail because the selection/preview helpers do not exist.

- [ ] **Step 2: Implement the pure presentation layer**

Add:

```ts
export type TripEssentialCategory =
  | "terrain"
  | "passValue"
  | "liftAccess"
  | "lodging"
  | "travelEffort";

export function selectTripEssentialCategories(
  intent: SearchIntent,
  groups: SearchV4RecommendationGroup[],
): TripEssentialCategory[];

export function refinementPreviewCopy(preview?: RefinementPreview | null): string;
```

Keep all labels finite and deterministic. Do not infer user-facing evidence
from arbitrary JSON fields.

- [ ] **Step 3: Write failing board interaction tests**

Cover:

- result 1 open initially and later results collapsed;
- results 1 and 2 remain open simultaneously;
- each toggle has `aria-expanded` and `aria-controls`;
- `View dossier`, save, and alternative controls do not toggle expansion;
- selecting an alternative updates stay base, pass, essentials, dossier href,
  and save target without changing group rank;
- changed ranks are announced after rerank;
- existing results remain visible while rerank is busy;
- no-results names hard constraints and offers reversible adjustment;
- the decision rail separates hard constraints from preferences, opens manual
  adjustment, and renders at most one contextual refinement;
- raw model/policy versions and filtered-out counts are absent from the board.

- [ ] **Step 4: Implement the board and independently expandable cards**

Use `Set<string>` for expansion state and a group-to-candidate map for selected
configurations. The non-action card header and Lucide `ChevronDown` control
toggle expansion. Expanded cards use one semantic anatomy at every rank:
verdict, trip essentials, evidence quality, selected pass, one strength, one
watchout, dossier/save actions, alternatives, and scoring disclosure.

Use existing `EvidenceQualityBadge`, `TripEntityStack`, and `snowcastCopy`
where their semantics still match. Refactor or remove obsolete helpers instead
of duplicating them.

`SearchContextRail` renders `Search understood` as compact user-language hard
constraints and preferences, followed by `Adjust` and at most one primary
`RefinementCard`. It becomes normal document flow above results on mobile; it
must not recreate the permanent Search V4 form.

The response may contain several validated refinements. Keep them in response
order but display only the first still-relevant question. `Skip for now` or
dismiss advances to the next queued question without a request; applying one
reruns Search V4 and replaces the queue with refinements from the new response.
Never carry an unanswered question across rerank where its materiality may have
changed.

- [ ] **Step 5: Implement preview-then-apply refinement behavior**

`RefinementCard` holds a selected option without mutating intent. Render the
typed preview when present, generic material-impact copy otherwise, and expose
`Apply and rerank`, `Clear`, and `Skip for now`. On apply:

- preserve current results and viewport;
- POST the patched typed intent;
- reconcile expansion/selection against returned groups;
- mark changed ranks briefly and announce them in a polite live region;
- preserve the selected option on failure and offer retry;
- offer Undo only while the prior typed intent remains in memory.

- [ ] **Step 6: Add E2E comparison and refinement coverage**

Mock two search responses and verify multi-card expansion, nested-control
isolation, alternative selection, preview copy, rerank rank movement, and
failed-apply recovery. Verify that keyboard activation changes `aria-expanded`
without moving focus, and that applying/skipping advances or replaces the
refinement queue correctly. Test at desktop and narrow mobile widths.

- [ ] **Step 7: Verify and commit the result board**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Expected: all frontend checks pass.

```bash
git add frontend/src/search/RecommendationBoard.tsx \
  frontend/src/search/SearchContextRail.tsx \
  frontend/src/search/SearchContextRail.test.tsx \
  frontend/src/search/RecommendationCard.tsx \
  frontend/src/search/RecommendationCard.test.tsx \
  frontend/src/search/RefinementCard.tsx \
  frontend/src/search/RefinementCard.test.tsx \
  frontend/src/search/TripEssentials.tsx \
  frontend/src/search/ScoringDetails.tsx \
  frontend/src/search/searchPresentation.ts \
  frontend/src/search/searchPresentation.test.ts \
  frontend/src/search/searchSession.ts frontend/src/App.tsx \
  frontend/src/App.test.tsx frontend/src/index.css \
  frontend/tests/e2e/app.spec.ts
git commit -m "feat: build hybrid Search V4 recommendation board"
```

### Task 6: Restore The Dedicated Recommendation Dossier And Results Navigator

**Files:**

- Create: `frontend/src/search/RecommendationDossier.tsx`
- Create: `frontend/src/search/RecommendationDossier.test.tsx`
- Create: `frontend/src/search/RecommendationNavigator.tsx`
- Create: `frontend/src/search/DossierVerdict.tsx`
- Modify: `frontend/src/navigation.ts`
- Modify: `frontend/src/search/searchSession.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing dossier route and restoration tests**

Cover:

- `View dossier` opens
  `/recommendations/:ski_region_id?candidate=:candidate_id`;
- selected alternative candidate is used in the query;
- desktop navigator shows top three, or top two plus the current out-of-band
  group;
- navigator collapse changes from `260px` to the compact rank rail without
  hiding dossier content;
- mobile renders a bounded recommendation switcher instead of the desktop
  rail;
- switching recommendations does not rerun search, resets detail scroll, and
  announces the new heading;
- `All results` restores query, selected candidates, expansion state, and
  results scroll;
- browser Back restores the same state;
- direct dossier load without session state shows `Run a search first` and a
  working return action.

Run:

```bash
npm --prefix frontend test -- src/search/RecommendationDossier.test.tsx \
  src/navigation.test.ts src/search/searchSession.test.ts src/App.test.tsx
```

Expected: fail because dossier components do not exist.

- [ ] **Step 2: Implement the dossier master-detail shell**

Build a compact command header followed by:

- `RecommendationNavigator` at wide desktop;
- a `Recommendation N of M` switcher below the breakpoint;
- `DossierVerdict` naming ski region and selected stay base first;
- trip fit, snow window, evidence quality, selected entities, one strength,
  and one watchout;
- a `Save as current trip` action using the currently selected candidate;
- progressive section anchors for snow evidence, trip configuration,
  alternatives, accommodation, and scoring details.

Use Lucide `PanelLeftClose`, `PanelLeftOpen`, `ArrowLeft`, `ChevronDown`, and
semantic evidence icons. The navigator row is a navigation control, not a card
expansion control.

- [ ] **Step 3: Preserve browser-session result context**

Before dossier navigation, capture `window.scrollY` in `SearchSession`.
Switching a dossier updates only route and selected group/candidate. Returning
to results schedules `window.scrollTo(0, savedY)` after board render. A missing
group or candidate falls back to the group's top configuration and replaces
the invalid URL without a search request.

- [ ] **Step 4: Add dossier E2E flows**

Assert no additional `/api/search` call during dossier open/switch/back, focus
or live announcement after a switch, desktop collapse behavior, mobile switcher
keyboard/touch behavior, direct-load recovery, scroll restoration, and the
mandatory anonymous current-trip route regression from Task 1.

- [ ] **Step 5: Verify and commit the dossier shell**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Expected: all frontend checks pass and dossier switching performs no search.

```bash
git add frontend/src/search/RecommendationDossier.tsx \
  frontend/src/search/RecommendationDossier.test.tsx \
  frontend/src/search/RecommendationNavigator.tsx \
  frontend/src/search/DossierVerdict.tsx frontend/src/navigation.ts \
  frontend/src/search/searchSession.ts frontend/src/App.tsx \
  frontend/src/App.test.tsx frontend/src/index.css \
  frontend/tests/e2e/app.spec.ts
git commit -m "feat: restore recommendation dossier navigation"
```

### Task 7: Add Conditional Snow Evidence And Honest Accommodation Handoff

**Files:**

- Create: `frontend/src/search/SnowEvidence.tsx`
- Create: `frontend/src/search/SnowEvidence.test.tsx`
- Create: `frontend/src/search/SnowEvidenceChart.tsx`
- Create: `frontend/src/search/AccommodationHandoff.tsx`
- Create: `frontend/src/search/AccommodationHandoff.test.tsx`
- Create: `frontend/src/search/DecisionEvidenceLedger.tsx`
- Create: `frontend/src/search/TripConfigurationDetails.tsx`
- Modify: `frontend/src/search/RecommendationDossier.tsx`
- Modify: `frontend/src/search/searchPresentation.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing snow-mode and handoff tests**

Cover:

- month-only summary renders `Historical pattern`, climatology provenance,
  mid-mountain elevation, evidence seasons, supported depth/snowfall/
  temperature metrics, and no forecast tab;
- exact-date usable forecast renders `Forecast-assisted`, issue time,
  freshness, usable-date coverage, and separate `Forecast` / `Historical
  context` controls;
- stale or missing forecast renders climatology and the server limitation;
- missing weather summary renders a bounded unavailable state and never reads
  generic factor JSON;
- chart has a textual interpretation and structured value disclosure;
- color is not the only distinction between range, median, forecast, and risk;
- stay copy says `Stay-base estimate, not live hotel inventory`;
- `needs_source` lodging does not render a numeric estimate;
- accommodation URL is built from selected stay base through the existing API
  helper and contains no invented property.

Run:

```bash
npm --prefix frontend test -- src/search/SnowEvidence.test.tsx \
  src/search/AccommodationHandoff.test.tsx src/App.test.tsx
```

Expected: fail because the components do not exist.

- [ ] **Step 2: Implement accessible conditional evidence views**

`SnowEvidence` trusts `weather_evidence.mode` and does not infer it. Use a
labelled tab pattern only when forecast and historical views both exist.
`SnowEvidenceChart` renders a responsive bounded SVG with shapes/strokes plus
an adjacent interpretation and a disclosed semantic list/table containing all
plotted values and units. Empty numeric values are omitted, not zero-filled.

- [ ] **Step 3: Implement trip details and accommodation handoff**

Show destination, ski area, stay base, selected pass, access, and shared trip
essentials. Keep alternatives inside the region. For lodging, preserve
`verified`, `verified_with_adjustment`, `estimated`, and `needs_source` wording.
Use the existing outbound accommodation redirect builder; do not introduce a
provider card grid.

`DecisionEvidenceLedger` groups the selected configuration's supported source
summaries, warnings, and limitations in user language. Keep raw factor IDs,
weights, contribution points, and policy versions inside the separately
collapsed `ScoringDetails`; do not duplicate the snow chart.

- [ ] **Step 4: Add all dossier evidence variants to E2E**

Create month, forecast-assisted, stale-fallback, and missing-evidence fixture
variants. Verify tabs/keyboard behavior, chart alternative, estimate wording,
outbound URL, no horizontal overflow, and no provider claims. The focused test
must prove arrow-key or tab/activation behavior for the chosen tab semantics and
must keep focus on a valid control when a forecast view is unavailable.

- [ ] **Step 5: Verify and commit the complete dossier**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Expected: all frontend checks pass across evidence variants.

```bash
git add frontend/src/search/SnowEvidence.tsx \
  frontend/src/search/SnowEvidence.test.tsx \
  frontend/src/search/SnowEvidenceChart.tsx \
  frontend/src/search/AccommodationHandoff.tsx \
  frontend/src/search/AccommodationHandoff.test.tsx \
  frontend/src/search/DecisionEvidenceLedger.tsx \
  frontend/src/search/TripConfigurationDetails.tsx \
  frontend/src/search/RecommendationDossier.tsx \
  frontend/src/search/searchPresentation.ts frontend/src/api.ts \
  frontend/src/App.test.tsx frontend/src/index.css \
  frontend/tests/e2e/app.spec.ts
git commit -m "feat: add dossier snow evidence and stay handoff"
```

### Task 8: Match The Accepted Visuals, Close Accessibility Gaps, And Review

**Files:**

- Create: `frontend/tests/e2e/visual.spec.ts`
- Create: `frontend/tests/e2e/visual.spec.ts-snapshots/*`
- Modify: `frontend/playwright.config.ts`
- Modify: `frontend/src/index.css`
- Modify: frontend components from Tasks 4-7 only where verification exposes a
  concrete defect
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`
- Modify: this plan's execution notes while work is in progress

- [ ] **Step 1: Add deterministic visual states and screenshot tests**

In `visual.spec.ts`, mock stable font/data/time inputs and capture:

- homepage at `1440x900`, `1024x768`, and `390x844`;
- results with results 1 and 2 open at the same widths;
- month dossier with expanded navigator at desktop;
- exact-date dossier with collapsed navigator at desktop;
- dossier mobile switcher and snow evidence at `390x844`.

Use `expect(page).toHaveScreenshot(...)` after waiting for fonts and the main
heading. Store snapshots in Playwright's standard snapshot folder.

- [ ] **Step 2: Compare each state with the accepted visual pack**

Use:

- `docs/ui-concepts/2026-07-16-search-v4-web-experience/01-homepage-command-stage.png`
- `docs/ui-concepts/2026-07-16-search-v4-web-experience/02-hybrid-results-expanded-desktop.jpg`
- `docs/ui-concepts/2026-07-16-search-v4-web-experience/03-dossier-results-navigator.jpg`
- `docs/ui-concepts/2026-07-16-search-v4-web-experience/04-dossier-snow-evidence.jpg`
- `docs/ui-concepts/2026-07-16-search-v4-web-experience/05-dossier-full-page.png`

Inspect screenshots with Playwright and `view_image`. Correct grid alignment,
content density, hierarchy, colors, borders, type scale, stable metric tracks,
control overflow, and mobile reflow. Do not copy illustrative values into
product fixtures solely to make pixels match.

- [ ] **Step 3: Run manual accessibility and resilience checks**

At desktop and mobile widths verify:

- keyboard-only search, drawer, card expansion, alternatives, dossier
  navigator/switcher, weather tabs, scoring disclosure, and return flow;
- visible focus and logical order;
- focus after search and dossier switch;
- polite rank-change and route-change announcements;
- 200% zoom without overlap or horizontal scrolling;
- reduced motion;
- grayscale-readable semantic status;
- failed initial search, failed rerank, no results, missing dossier state,
  missing metrics, stale forecast, and missing evidence;
- no raw brief or weather values added to logging/telemetry.

- [ ] **Step 4: Run the complete automated verification suite**

Run:

```bash
uv run pytest -q
uv run ruff check .
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Expected: all backend, lint, frontend unit, build, E2E, and visual checks pass.

- [ ] **Step 5: Run Snowcast advisory feature review**

Use `snowcast-advisory-review` in `feature-review` mode for:

- Product / Strategy;
- Backend / API;
- Data Trust & Source Integrity;
- UI / UX;
- Security & Privacy;
- Observability / Ops;
- Accessibility;
- Performance;
- Monetization / Partnerships.

Inspect the exact implementation diff and complete verification evidence.
Resolve every Blocker and High finding, rerun affected checks, and record Medium
or Low follow-ups in `docs/product-backlog.md` only when they are concrete and
worth preserving.

- [ ] **Step 6: Update durable documentation**

In `docs/engineering-notes.md`, record:

- `lucide-react` as the presentation icon system;
- browser-history/in-memory dossier routing and its reload limitation;
- server-owned refinement/weather presentation summaries;
- semantic SVG plus structured-list chart accessibility;
- actual representative response byte/time measurements.

Mark the feature spec implemented only after feature review and all checks are
green. Update this plan's progress/outcome notes with exact verification and
residual limitations.

- [ ] **Step 7: Commit close-out changes**

```bash
git add frontend/tests/e2e/visual.spec.ts \
  frontend/tests/e2e/visual.spec.ts-snapshots frontend/playwright.config.ts \
  frontend/src/index.css docs/engineering-notes.md \
  docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md \
  docs/superpowers/plans/2026-07-16-search-v4-web-experience.md \
  docs/product-backlog.md
git commit -m "test: verify Search V4 web experience"
```

Before staging, omit `docs/product-backlog.md` when feature review created no
durable follow-up. If visual verification required a component fix, add only
that reviewed component path explicitly to this commit. Confirm
`.superdesign/`, `frontend/dist/`, `frontend/test-results/`, and build-info
files remain untracked or unstaged.

## Final Local Acceptance

Start the product with the repository's normal local stack:

```bash
uv run uvicorn app.main:app --reload --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Then verify:

1. Open `http://127.0.0.1:5173/` and submit a month search.
2. Confirm the homepage becomes the compact command header plus the decision
   board, with the first group expanded.
3. Expand the second group without collapsing the first, switch its stay-base
   alternative, and confirm rank is unchanged.
4. Select a refinement, inspect its preview, apply it, and hear/see the rank
   update without losing the board.
5. Open a dossier, collapse the desktop navigator, switch result, and return to
   the restored board position.
6. Confirm month evidence is historical only.
7. Run an exact-date search inside usable forecast coverage and confirm the
   separate Forecast and Historical context views.
8. Confirm the accommodation section is an estimate/handoff, not hotel
   inventory.
9. Repeat the core flow at a narrow mobile viewport with keyboard or touch and
   confirm there is no horizontal overflow.

## Execution Handoff

- Recommended execution: `superpowers:subagent-driven-development` in the
  current task, one fresh implementation subagent per task, followed by spec
  compliance and code-quality review before moving on.
- Alternative execution: `superpowers:executing-plans` inline, preserving the
  same task boundaries, focused verification, and commits.
- Use `superpowers:test-driven-development` for every behavioral step,
  `superpowers:systematic-debugging` for any unexpected failure,
  `superpowers:verification-before-completion` before completion claims,
  `superpowers:requesting-code-review` after advisory review, and
  `superpowers:finishing-a-development-branch` for the final integration
  choice.

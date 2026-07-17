# Search V4 Trust And UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the accepted Search V4 web experience reliable and consistent by
clarifying refinement availability, repairing client/API boundaries, replacing
internal evidence language with traveller-facing explanations, rebuilding the
snow/weather visualization, and encoding repeated interface behavior in a small
Snowcast-owned React UI foundation.

**Architecture:** Search V4 continues to own ranking, refinement materiality,
and evidence interpretation. `POST /api/search` returns a complete usable
ranking without invoking Gemini and stores a typed, lightweight
evaluated-baseline snapshot in a bounded process-local store. After those
results render, the client starts an independently cancellable
`POST /api/search/refinements` request using the returned `applied_intent` and
baseline fingerprint. That endpoint reads only the exact stored baseline bound
to the canonical intent SHA-256 digest, reports refinement availability, and may
produce one deterministic group-priority fallback only through the existing
typed validation and variant-ranking path. It never reruns deterministic search.
The React client projects response models back to request models at API
boundaries, composes Snowcast-owned UI primitives inside feature components, and
lazy-loads one-metric-at-a-time Recharts views plus an equivalent accessible
table.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, React 18, TypeScript 5,
Vite 6, Tailwind 3, Vitest, Testing Library, Playwright, Lucide React, and
Recharts 3.9.x.

## Global Constraints

- Classification: `review-gated`, full design flow.
- Developer Decision Checkpoints: resolved by the owner on 2026-07-17. The
  owner approved explicit
  refinement outcomes, one deterministic fallback only after materiality
  validation, plain-language `Why this trip`, collapsed technical provenance,
  Recharts, a subtle creamy-pink/snow/powder canvas, and a small internal UI kit
  without a full shadcn migration. The owner additionally approved segmented
  Snow depth / Fresh snow / Temperature chart views and post-search refinement
  loading with a five-second total budget. The approved exact-view handoff uses
  a typed, lightweight process-local evaluated-baseline snapshot with a
  60-second TTL and maximum 64 entries. The owner approved an initial
  application-local admission guard of
  two concurrent requests and six requests per minute per client with burst two
  for the current one-machine deployment.
- ADR status: required and recorded by accepted ADR 0015, which owns post-search
  refinement loading and the evaluated-baseline handoff. ADR 0012
  continues to own the versioned ranking/refinement policy and ADR 0014
  continues to own on-demand weather evidence. Stop and reassess if
  implementation changes ranking thresholds, persists or shares search state,
  stores full catalog/trust snapshots, scales to multiple web processes without
  approved sticky routing, shared state, or redesign, moves evidence
  interpretation to the client, or adds provider acquisition.
- Advisory review: completed on the exact implementation state after all
  follow-up fixes. Product, backend/API, data trust, UI/UX, AI reliability,
  accessibility, performance, security/privacy, observability, release, and
  independent code-review lanes reported no remaining Blocker, High, Medium,
  or Low findings.
- Preserve ranking weights, factor semantics, materiality thresholds, candidate
  eligibility, weather composition, and catalog acquisition.
- A deterministic fallback may emit at most one question. It uses only a
  configured clarifiable group, typed `GroupPriorityPatch` variants, answered-
  question suppression, and `validate_refinement_proposal`.
- `refinement_status` values are exactly `questions_available`, `not_needed`,
  and `temporarily_unavailable`.
- `questions_available` requires a non-empty validated queue. `not_needed`
  means no material question exists. `temporarily_unavailable` means the exact
  baseline handoff is unavailable or mismatched, or provider/output failure has
  no validated deterministic fallback.
- Primary evidence copy must not contain raw factor IDs, trust enums,
  `Catalog field-group evidence`, source-reference counts, or internal model
  terminology. Verbatim provenance is allowed only inside the collapsed
  `Sources and calculation details` disclosure.
- Weather charts consume only `SearchWeatherEvidenceResponse` points. Do not
  interpolate, smooth across nulls, invent observations, or derive new weather
  claims in the browser.
- `POST /api/search` never invokes an LLM. The web client requests refinements
  only after a successful ranking and cancels or ignores stale refinement
  responses when the applied intent changes.
- `POST /api/search/refinements` has one provider attempt within a five-second
  end-to-end monotonic deadline measured from route ingress. Snapshot lookup,
  provider work, and fallback checks all share that deadline. At
  2.5 seconds the client changes only the loading message; it does not cancel
  the request. No retry may extend the five-second budget.
- After deterministic ranking, `POST /api/search` stores the minimum typed
  evaluated candidate/ranking state needed for refinement validation and
  previews. The thread-safe process-local store uses LRU eviction, a 60-second
  TTL, and a maximum of 64 entries. It stores only the canonical intent SHA-256
  digest plus the public baseline fingerprint, not a full `SearchIntent`, origin
  text, full `CatalogSnapshot`, `CatalogTrustManifest`, brief, or provider
  secrets.
- `POST /api/search/refinements` accepts a snapshot only when the stored
  fingerprint and the SHA-256 digest recomputed from canonical request intent
  both match. Canonical serialization supplies the equality binding; no full
  intent is stored and no second typed-equality check occurs. The public
  fingerprint alone is not trusted. Miss, expiry, eviction, process restart, or
  mismatch returns `temporarily_unavailable` and invokes neither deterministic
  search nor Gemini. Ranked results remain usable, and deliberate ranking
  refresh creates a new snapshot.
- The 60-second TTL is only the server handoff window for generating a question.
  A delivered question remains answerable after expiry. Applying it reruns full
  search with the updated intent, stores a new baseline, and immediately
  requests the next refinement from that snapshot.
- The process-local design is accepted for the current single-instance
  deployment. Horizontal scaling requires sticky routing, shared state, or a
  redesigned handoff. Deploy or restart clears the store.
- The refinement endpoint rejects before snapshot lookup when more than two
  requests are executing or one client exceeds six requests per minute with
  burst two.
  Admission state is thread-safe, per-machine, monotonic, bounded/cleaned up,
  and never records client identity in logs or metric labels.
- During migration `/api/search` accepts legacy `brief`,
  `generate_refinements`, and `already_answered_question_ids` fields but ignores
  them, and retains `refinements: []` in its response. Remove this compatibility
  only after web and mobile contract verification.
- Recharts `^3.9.2` is the only new dependency. Do not initialize shadcn, add a
  router, add Storybook, or introduce another chart/UI/state library.
- The internal UI foundation lives under `frontend/src/ui`; domain components
  remain under `frontend/src/search`. Do not introduce a generic `Card`
  abstraction or nested-card layout.
- Use the accepted visual pack in
  `docs/ui-concepts/2026-07-16-search-v4-web-experience/` as the visual oracle.
- Keep `.superdesign/`, generated `dist/`, `test-results/`, and transient build
  artifacts untracked.
- Execute every behavior change test-first: add the focused failing test, run it
  and confirm the expected failure, implement the minimum change, rerun focused
  tests, then run the task-level regression set.

## Execution Notes

Append one line per completed task with commit range, review status, and focused
verification. Record advisory findings and their resolutions. Do not rewrite
historical entries in the completed July 16 plan.

- 2026-07-17: Tasks 1-6 completed in the uncommitted working tree. Focused
  backend verification passed 187 tests; frontend verification passed 146 unit
  tests, the production build, and 44 Playwright journeys. The dense mobile
  forecast chart also passed 20 repeated runs with six workers.
- 2026-07-17: Task 7 completed. Exact-state advisory and independent code
  review cleared all findings after the final fixture-contract correction.
  Ruff check, Ruff format check, deploy-workflow YAML parsing, and
  `git diff --check` passed. The authoritative full backend rerun passed 1,486
  tests. An earlier run had one PostgreSQL concurrent-DDL setup error while
  1,485 tests passed; the affected test passed alone and the complete quiescent
  rerun passed, confirming a transient shared-test-database collision rather
  than a product assertion failure.
- 2026-07-17: Visual baselines were inspected at desktop, tablet, and mobile
  sizes, including the 31-point mobile forecast chart. All weather points remain
  in the chart and accessible table while the axis deterministically labels the
  first, middle, and last dates. No commit was created because the owner did not
  request one.

---

### Task 1: Separate Refinement Loading And Make Its Outcome Explicit

**Files:**

- Modify: `app/domain/search_refinement.py`
- Modify: `app/ai/search_refinement.py`
- Modify: `app/domain/search_v4_service.py`
- Modify: `app/ai/gemini_client.py`
- Modify: `app/api/routes.py`
- Create or Modify: `app/api/refinement_admission.py`
- Modify: `frontend/src/types.ts`
- Modify: `tests/test_search_refinement.py`
- Modify: `tests/test_ai_search_refinement.py`
- Modify: `tests/test_search_v4_service.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_search_v4_api.py`
- Modify: `tests/test_env.py`
- Modify: `tests/test_observability.py`
- Modify: `ops/canary/search_canary.py`
- Modify: `docs/search-ranking-model.md`

**Interfaces:**

- Produces: `POST /api/search/refinements` with request fields `intent`,
  `baseline_fingerprint`, `brief`, and `already_answered_question_ids`.
- Produces: `SearchV4RefinementResponse.refinement_status` with the three exact
  values in Global Constraints plus `search_model_version`,
  `ranking_policy_version`, `baseline_fingerprint`, `baseline_status`, and
  `refinements`.
- Preserves: `POST /api/search` as a ranking-only endpoint that does not create
  a Gemini client or wait for refinement generation; after deterministic
  ranking it stores and returns the handoff for a typed lightweight evaluated
  baseline.
- Preserves: legacy search request fields as accepted-but-ignored and an empty
  legacy `refinements` response field during client migration.
- Produces: `build_deterministic_refinement_fallback(...) ->
  ValidatedRefinementProposal | None` in `app/domain/search_refinement.py`.
- Preserves: existing serialized `RefinementProposal`, option preview, and
  client queue behavior.

- [x] **Step 1: Write failing route and contract tests for request separation**

Prove that `/api/search` never constructs or invokes a Gemini client and returns
ranking results with `refinements: []`, including for the current mobile-shaped
legacy request. Prove that it stores a baseline only after deterministic ranking
and returns the associated fingerprint. Prove that `/api/search/refinements`
accepts the canonical applied intent, baseline fingerprint, brief, and answered
IDs; returns the ranking-policy version; rejects invalid intent with the existing
safe 422 contract; maps a missing or reset store to typed
`temporarily_unavailable` without deterministic search or Gemini; and never
exposes provider messages, prompts, tokens, or internal exception text in 5xx
responses.

Run:

```bash
uv run pytest tests/test_search_v4_api.py tests/test_api.py -q
```

Expected: fail until the exact evaluated-baseline handoff and missing-store
outcome are implemented.

- [x] **Step 2: Write failing domain tests for the fallback boundary**

Add tests proving that the fallback:

1. returns the first policy-ordered clarifiable group proposal whose two
   variants pass `validate_refinement_proposal` and materiality;
2. uses question ID `fallback-group-<group_id>`;
3. emits exactly two options using `GroupPriorityPatch` values `important` and
   `secondary`;
4. returns `None` when no group variant is material;
5. suppresses a question ID already present in
   `already_answered_question_ids`.

Run:

```bash
uv run pytest tests/test_search_refinement.py -q
```

Expected: fail because `build_deterministic_refinement_fallback` does not exist.

- [x] **Step 3: Implement the fallback through existing validation**

Create policy-ordered proposals with this copy shape:

```text
question: How strongly should <group label lowercased> influence your ranking?
reason: Your leading options differ on <group label lowercased>, so this choice could change their order.
option 1: Make it a priority / Give <group label lowercased> more influence in the ranking.
option 2: Keep it secondary / Keep <group label lowercased> secondary to the overall trip balance.
```

Call `validate_refinement_proposal` for each proposal and return only the first
validated material result. Catch `RefinementValidationError`, `ValueError`, and
Pydantic validation errors per candidate proposal; do not duplicate ranking or
materiality logic.

- [x] **Step 4: Write failing AI outcome and timeout tests**

Add a frozen `RefinementGenerationResult` expectation with:

```python
status: Literal[
    "questions_available",
    "not_needed",
    "temporarily_unavailable",
]
proposals: tuple[ValidatedRefinementProposal, ...]
```

Test provider/auth/network/quota errors and exhausted invalid output as
`temporarily_unavailable`, an accepted empty provider response as `not_needed`,
and validated proposals as AI-local generation outcomes rather than public
Search V4 statuses. Test that successful HTTP responses containing malformed
provider JSON become a bounded `provider_error`, and that one provider attempt
cannot retry beyond the shared five-second endpoint deadline.

Run:

```bash
uv run pytest tests/test_ai_search_refinement.py -q
```

Expected: fail because generation currently returns only a tuple.

- [x] **Step 5: Implement typed AI generation outcomes**

Change `generate_refinement_proposals` to return
`RefinementGenerationResult`. Normalize malformed provider response JSON to
`LLMClientError(reason="provider_error")`. Keep raw provider errors and prompts
out of API responses and logs. The user-facing endpoint performs one provider
attempt; it does not apply the old per-attempt retry loop.

- [x] **Step 6: Write failing service tests for baseline, status, and fallback**

Cover:

- validated AI proposal -> `questions_available`;
- empty AI proposal plus material fallback -> `questions_available` and one
  fallback question;
- invalid/provider failure with no fallback -> `temporarily_unavailable`;
- valid no-question outcome with no fallback -> `not_needed`;
- a ranking-only search never calls the refinement path;
- schema invariant rejecting `questions_available` with an empty list and any
  other status with a non-empty list;
- final public status and orthogonal `fallback_used` telemetry without question
  text or IDs.
- ranking stores a typed lightweight evaluated baseline with only the canonical
  intent SHA-256 digest, not a full `SearchIntent`, origin text, full
  `CatalogSnapshot`, `CatalogTrustManifest`, brief, or provider secrets;
- the thread-safe store expires entries at 60 seconds, holds at most 64, and
  evicts the least-recently-used entry when full;
- concurrent reads/writes preserve entry integrity, bounds, expiry, and LRU
  order;
- matching fingerprint plus SHA-256 digest recomputed from canonical request
  intent -> normal generation from the stored baseline without deterministic
  search;
- a matching caller-supplied fingerprint with a different canonical-intent
  digest, cache miss, expiry, eviction, or process-reset store -> no
  deterministic search, no provider call, no questions, and
  `temporarily_unavailable`;
- zero eligible candidates -> no provider call and `not_needed`;
- slow snapshot lookup leaves only the measured remaining provider timeout,
  while an exhausted deadline skips the provider and fallback work;
- deliberate ranking refresh replaces the handoff with a newly evaluated
  baseline.

Run:

```bash
uv run pytest tests/test_search_v4_service.py tests/test_api.py tests/test_observability.py -q
```

Expected: fail until refinement consumes the exact stored baseline without
rerunning deterministic search.

- [x] **Step 7: Extract reusable evaluation and integrate both endpoints**

Extract the minimum typed evaluated-baseline value needed by refinement without
retaining the full catalog/trust snapshot. After deterministic evaluation,
`/api/search` stores that value in the thread-safe process-local 60-second,
64-entry LRU store, then groups and serializes ranked results. The snapshot is
bound to its public fingerprint and canonical intent SHA-256 digest; the full
intent is not stored and no separate typed-equality check occurs.
`/api/search/refinements` reads only that exact value, never reruns deterministic
search, calls the LLM only after a successful lookup, applies the fallback only
when AI returns no validated proposal, and serializes the typed status. Miss,
expiry, eviction, restart, or mismatch returns `temporarily_unavailable`.
Add the separate TypeScript request/response types.

- [x] **Step 8: Add bounded observability and verify**

Record separate endpoint duration and bounded status
(`questions_available`, `not_needed`, `temporarily_unavailable`) plus
orthogonal `fallback_used=true|false` without question text, IDs, brief text, or
provider payloads. Record bounded evaluated-baseline `hit`, `miss`, `expired`,
and `evicted` outcomes without fingerprint, intent, candidate, or client labels.
Update
`docs/search-ranking-model.md` with request separation, status semantics,
fallback invariants, exact baseline handoff, 60-second/64-entry store bounds,
compatibility window, admission policy, and five-second end-to-end deadline.
Update the product canary to call the
separate endpoint and accept all three typed statuses while failing unsafe
contract or latency behavior.

- [x] **Step 9: Add failing admission-control tests and implement the guard**

Use an injected monotonic clock and isolated guard instance. Prove burst two is
accepted, request three is `429`, six requests in a rolling minute are accepted
when concurrency is released, the next is rejected, capacity returns after the
window, and a rejected request invokes neither snapshot lookup nor Gemini. Prove
concurrent capacity is returned on success and exception. Do not
trust arbitrary `X-Forwarded-For` values or emit client identity in telemetry.

Update `docs/search-ranking-model.md` with the status semantics and fallback
invariants. Run:

```bash
uv run pytest tests/test_search_refinement.py tests/test_ai_search_refinement.py tests/test_search_v4_service.py tests/test_api.py tests/test_observability.py -q
uv run ruff check app/domain/search_refinement.py app/ai/search_refinement.py app/ai/gemini_client.py app/domain/search_v4_service.py app/api/routes.py tests/test_search_refinement.py tests/test_ai_search_refinement.py tests/test_search_v4_service.py tests/test_search_v4_api.py tests/test_api.py tests/test_env.py tests/test_observability.py
```

- [ ] **Step 10: Commit (deferred; no commit requested)**

```bash
git add app/domain/search_refinement.py app/ai/search_refinement.py \
  app/ai/gemini_client.py app/domain/search_v4_service.py app/api/routes.py \
  frontend/src/types.ts \
  tests/test_search_refinement.py tests/test_ai_search_refinement.py \
  tests/test_search_v4_service.py tests/test_search_v4_api.py tests/test_api.py \
  tests/test_env.py tests/test_observability.py \
  docs/search-ranking-model.md
git commit -m "feat: load Search V4 refinements separately"
```

### Task 2: Repair Search And Weather API Boundaries

**Files:**

- Modify: `frontend/src/api.ts`
- Create: `frontend/src/api.test.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/search/RecommendationBoard.tsx`
- Modify: `frontend/src/search/SnowEvidence.test.tsx`
- Modify: `tests/test_search_v4_service.py`

**Interfaces:**

- Produces: `searchIntentRequestPayload(intent: SearchIntent): SearchIntent`.
- Produces: action-scoped search update copy that preserves previous results.
- Consumes: `SearchV4RefinementResponse` from Task 1.

- [x] **Step 1: Write failing serializer and error-parser tests**

Test that `searchIntentRequestPayload` strips response-only
`travel_window.mode`, `travel_window.ski_day_count`,
`lodging_budget.effective_flex`, and
`lodging_budget.effective_maximum` without mutating the source object. Test that
FastAPI string details and validation-detail arrays become readable messages
rather than `[object Object]`.

Run:

```bash
npm --prefix frontend test -- src/api.test.ts
```

Expected: fail because the serializer is absent and array details are coerced.

- [x] **Step 2: Implement the request projection and readable errors**

Use an explicit structural copy for the two computed-field-bearing constraint
objects. Do not use JSON string replacement or maintain a blacklist outside the
API module. For validation arrays, join each item's `loc` and `msg` in response
order and fall back to the endpoint-specific message when parsing fails.

- [x] **Step 3: Write a failing search-response-to-weather-route integration test**

Run a real Search V4 request, take its `applied_intent`, project it to request
shape, and prove `/api/search/weather-evidence` accepts it without 422. The test
must exercise month and exact-date shapes.

Run:

```bash
uv run pytest tests/test_search_v4_service.py -q
```

Expected: fail against the unprojected response-shaped intent fixture.

- [x] **Step 4: Write failing tests for progressive refinement loading**

Prove that a successful search renders results before the refinement promise
resolves; the request uses `response.applied_intent` and
`response.baseline_fingerprint`; the initial message is
`Checking whether one answer could improve these results...`; after 2.5 seconds
it becomes `Still checking for a useful follow-up...`; a new search aborts or
invalidates the old request; a ranking-policy mismatch is discarded; and a
delivered answer remains applicable after the server snapshot TTL. Prove that
applying an answer reranks with the updated intent before immediately requesting
the next refinement from the new response baseline.

- [x] **Step 5: Scope client failures to the attempted action**

Add tests proving:

- returning from dossier to results performs no search request and shows no
  unrelated prior error;
- a failed compact-header update keeps existing results and renders
  `Couldn't update results. Showing the previous ranking.` plus the readable
  cause;
- refinement failures remain in the refinement card;
- save failures do not become a results-loading failure;
- a successful later action clears only its own error.

Implement separate state for initial/search-update, refinement, and save
failures. Do not clear valid results on network failure.

- [x] **Step 6: Render refinement availability truthfully**

When the queue is empty, render one compact rail state:

- `not_needed`: `No follow-up needed` / `Your current trip decisions are enough to rank these options.`
- `temporarily_unavailable`: `Refinement unavailable` / `You can keep comparing these results or adjust the trip details manually.`

Do not display either state when a refinement card is present.

- [x] **Step 7: Verify (commit deferred)**

```bash
npm --prefix frontend test -- src/api.test.ts src/App.test.tsx src/search/SnowEvidence.test.tsx
uv run pytest tests/test_search_v4_service.py -q
npm --prefix frontend run build
git add frontend/src/api.ts frontend/src/api.test.ts frontend/src/App.tsx \
  frontend/src/App.test.tsx frontend/src/search/RecommendationBoard.tsx \
  frontend/src/search/SnowEvidence.test.tsx tests/test_search_v4_service.py
git commit -m "fix: harden Search V4 client API boundaries"
```

### Task 3: Establish The Snowcast UI Foundation

**Files:**

- Create: `frontend/src/ui/Action.tsx`
- Create: `frontend/src/ui/Alert.tsx`
- Create: `frontend/src/ui/Badge.tsx`
- Create: `frontend/src/ui/Disclosure.tsx`
- Create: `frontend/src/ui/MetricTile.tsx`
- Create: `frontend/src/ui/SectionHeader.tsx`
- Create: `frontend/src/ui/SegmentedTabs.tsx`
- Create: `frontend/src/ui/AsyncState.tsx`
- Create: `frontend/src/ui/uiPrimitives.test.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**

- Produces semantic variants consumed by Tasks 4-6.
- Does not own search data, ranking copy, chart data, routing, or page layout.

- [x] **Step 1: Write failing component-contract tests**

Cover:

- button `primary`, `secondary`, `ghost`, and `danger` variants plus `sm` and
  `md` sizes;
- icon-only button requiring `aria-label` and optional title tooltip;
- badge `neutral`, `info`, `supported`, `warning`, and `brand` variants;
- alert `info`, `success`, `warning`, and `error` roles;
- metric values wrapping without changing the tile's grid footprint;
- disclosure native keyboard operation and accessible name;
- segmented tabs with roving focus, ArrowLeft/ArrowRight/Home/End, and linked
  tabpanel IDs;
- async states with polite loading announcements and retry actions.

Run:

```bash
npm --prefix frontend test -- src/ui/uiPrimitives.test.tsx
```

Expected: fail because the primitives do not exist.

- [x] **Step 2: Implement minimal semantic primitives**

Use native `button`, `details/summary`, and ARIA tab semantics. Components
accept explicit variants rather than arbitrary visual style props. `className`
may be used for layout placement only. Lucide icons remain supplied by feature
components and are decorative inside labelled controls.

- [x] **Step 3: Add token-backed styles**

Extend existing CSS variables for shared control heights, radii, focus ring,
metric minimum sizes, and semantic state colors. Keep card/page layout out of
primitive selectors. Do not migrate unrelated existing CSS in this task.

- [x] **Step 4: Verify (commit deferred)**

```bash
npm --prefix frontend test -- src/ui/uiPrimitives.test.tsx
npm --prefix frontend run build
git add frontend/src/ui frontend/src/index.css
git commit -m "feat: add Snowcast UI primitives"
```

### Task 4: Replace The Evidence Ledger With Why This Trip

**Files:**

- Modify: `frontend/src/search/DecisionEvidenceLedger.tsx`
- Modify: `frontend/src/search/searchPresentation.ts`
- Modify: `frontend/src/search/searchPresentation.test.ts`
- Modify: `frontend/src/search/RecommendationDossier.tsx`
- Modify: `frontend/src/search/RecommendationDossier.test.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**

- Consumes: Task 3 `Alert`, `Badge`, `Disclosure`, and `SectionHeader`.
- Preserves: section anchor ID `decision-evidence` for route/scroll
  compatibility.

- [x] **Step 1: Write failing deterministic-copy tests**

Add pure presentation tests for supported and uncertain findings across:

- trip-window snow fit;
- party skill fit;
- pass-accessible or ski-area-only terrain;
- stay-base access;
- pass price/value;
- lodging estimate.

Assert that primary findings never contain `verified_with_adjustment`,
`Catalog field-group evidence`, `source reference`, raw factor IDs, or evidence
cap numbers.

- [x] **Step 2: Implement `decisionEvidencePresentation`**

Return:

```ts
{
  supports: Array<{ id: string; title: string; detail: string }>;
  uncertainties: Array<{ id: string; detail: string }>;
  technicalDetails: Array<{
    id: string;
    label: string;
    provenance: string;
    evidenceLabel: string;
  }>;
}
```

Limit supports to four, deduplicate uncertainties, and keep technical
provenance verbatim only in `technicalDetails`.

- [x] **Step 3: Write failing dossier semantics tests**

Assert headings `Why this trip`, `What supports this choice`, and
`What remains uncertain`; a collapsed `Sources and calculation details`
disclosure; absence of primary internal terminology; and preserved section
anchor.

- [x] **Step 4: Recompose the section**

Use open section layout, compact finding rows, one warning alert when needed,
and one disclosure for technical detail. Keep `Scoring details` separate and
collapsed. Rename dossier navigation labels to `Snow & weather`, `Trip details`,
`Why this trip`, and `How ranking works` without changing anchor IDs.

- [x] **Step 5: Verify (commit deferred)**

```bash
npm --prefix frontend test -- src/search/searchPresentation.test.ts src/search/RecommendationDossier.test.tsx
npm --prefix frontend run build
git add frontend/src/search/DecisionEvidenceLedger.tsx \
  frontend/src/search/searchPresentation.ts \
  frontend/src/search/searchPresentation.test.ts \
  frontend/src/search/RecommendationDossier.tsx \
  frontend/src/search/RecommendationDossier.test.tsx frontend/src/index.css
git commit -m "feat: explain recommendation evidence in plain language"
```

### Task 5: Complete Weather Rows And Rebuild Snow Evidence With Recharts

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `app/domain/search_weather_evidence.py`
- Modify: `app/domain/search_v4_service.py`
- Modify: `tests/test_search_weather_evidence.py`
- Modify: `tests/test_search_v4_service.py`
- Modify: `frontend/src/search/SnowEvidenceChart.tsx`
- Modify: `frontend/src/search/SnowEvidence.tsx`
- Modify: `frontend/src/search/SnowEvidence.test.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tests/e2e/visual.spec.ts`

**Interfaces:**

- Consumes: Task 3 metrics, tabs, disclosure, alert, async state.
- Consumes: the existing typed `SearchWeatherEvidenceResponse` only.
- Produces: one point per requested date/month-day, preserving absent source
  dates as explicit all-null rows.
- Produces: lazy-loaded, responsive `Snow depth`, `Fresh snow`, and
  `Temperature` Recharts views plus an equivalent accessible table.

- [x] **Step 1: Write failing backend coverage-gap tests**

For both historical and forecast-assisted windows, remove a source row in the
middle of the requested range and prove the response still contains that
date/month-day with null values. Keep rows ordered and bounded to 31. Verify the
coverage count remains source-derived rather than counting synthesized gap
rows.

```bash
uv run pytest tests/test_search_weather_evidence.py tests/test_search_v4_service.py -q
```

Expected: fail because missing source dates are currently omitted.

- [x] **Step 2: Emit explicit missing rows**

Build the requested date/month-day axis first, then left-join stored evidence.
Do not manufacture zero values, interpolate, or alter provenance and coverage
counts.

- [x] **Step 3: Add the approved dependency**

```bash
npm --prefix frontend install recharts@^3.9.2
```

Expected: only Recharts and its transitive runtime dependencies change the
package manifests.

- [x] **Step 4: Write failing chart data and semantics tests**

Test:

- historical p25/p50/p75 values map to a range-area tuple and median line;
- null observations remain null and segment the series;
- forecast depth, snowfall, and temperature retain their API values and dates;
- the 30 cm reference appears only when depth data exists;
- axes and tooltip labels include units;
- the accessible table contains every point and value, including `Not available`;
- source/freshness details start collapsed.
- only one unit is plotted at a time through the `Snow depth`, `Fresh snow`,
  and `Temperature` segmented control;
- forecast issue time, freshness, requested-date coverage, and partial/stale
  limitations remain visible in the primary summary;
- the chart module is loaded only when the dossier snow section renders.

Run:

```bash
npm --prefix frontend test -- src/search/SnowEvidence.test.tsx
```

Expected: fail against the inline SVG implementation.

- [x] **Step 5: Implement segmented Recharts views without interpolation**

Lazy-load the chart module. Use `ResponsiveContainer`, `ComposedChart`, `Area`,
`Line`, `XAxis`, `YAxis`, `CartesianGrid`, `Tooltip`, `Legend`, and
`ReferenceLine`. Set `connectNulls={false}` on every series. Use a range `Area`
for historical p25/p75 and a separate median `Line`. Each segmented view has
one unit and one labelled Y axis. Keep chart labels and tooltip copy in the
feature module, not in generic primitives.

- [x] **Step 6: Recompose Snow & Weather hierarchy**

Order:

1. conclusion and mode;
2. representative elevation/window context;
3. stable metric row;
4. forecast/historical tabs when applicable;
5. Snow depth / Fresh snow / Temperature metric tabs;
6. chart;
7. limitations alert;
8. collapsed `Sources and daily values` disclosure containing provenance and
   the accessible table.

Remove traveller-facing `Typed weather evidence` language. Keep unavailable
states honest and retryable.

- [x] **Step 7: Update visual fixtures and inspect actual rows**

Visual fixtures may remain deterministic, but their schema must match the real
typed endpoint. Add one E2E assertion proving the chart values shown in the
tooltip/table equal fixture API values rather than generated presentation data.

- [x] **Step 8: Verify (commit deferred)**

```bash
uv run pytest tests/test_search_weather_evidence.py tests/test_search_v4_service.py -q
npm --prefix frontend test -- src/search/SnowEvidence.test.tsx
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- visual.spec.ts
git add app/domain/search_weather_evidence.py app/domain/search_v4_service.py \
  tests/test_search_weather_evidence.py tests/test_search_v4_service.py \
  frontend/package.json frontend/package-lock.json \
  frontend/src/search/SnowEvidenceChart.tsx \
  frontend/src/search/SnowEvidence.tsx \
  frontend/src/search/SnowEvidence.test.tsx frontend/src/index.css \
  frontend/tests/e2e/visual.spec.ts
git commit -m "feat: rebuild snow evidence charts with Recharts"
```

### Task 6: Apply Responsive And Visual Polish

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/search/SearchCommandHeader.tsx`
- Modify: `frontend/src/search/RecommendationCard.tsx`
- Modify: `frontend/src/search/RecommendationCard.test.tsx`
- Modify: `frontend/src/search/RecommendationDossier.tsx`
- Modify: `frontend/src/search/RecommendationNavigator.tsx`
- Modify: `frontend/src/ui/AppShell.tsx`
- Modify: `frontend/src/ui/EvidenceQualityBadge.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/tests/e2e/app.spec.ts`
- Modify: `frontend/tests/e2e/visual.spec.ts`

**Interfaces:**

- Consumes: Task 3 action, badge, alert, and metric primitives where repeated
  semantics match.
- Preserves: accepted content hierarchy, browser-session return state, and
  independent card expansion.

- [x] **Step 1: Add failing regression assertions**

Cover:

- sticky dossier controls offset below the 84 px compact command header;
- anchor navigation scrolls sections below both sticky layers;
- `Unknown` and long metric values wrap inside their tile at 1024 px and 200%
  zoom-equivalent width;
- search completion focuses a visible results heading without a large visual
  outline or hidden sticky-header position;
- mobile results place the active refinement before the recommendation heading
  without focusing an off-screen element;
- `View dossier` uses an internal navigation icon, not `ExternalLink`;
- compact header brief and `Current trip` do not clip or wrap incoherently;
- badges use the shared 6-8 px geometry;
- no horizontal overflow at 390, 768, 1024, and 1440 px.

- [x] **Step 2: Apply layout and interaction fixes**

Use CSS variables for command-header and dossier-sticky offsets. Apply
`scroll-margin-top` to dossier anchors. Move focus only after the target is
visible and use `:focus-visible` so programmatic focus does not create a large
mouse-style ring. Replace the dossier link icon with `ArrowRight` or `FileText`.

- [x] **Step 3: Apply the approved canvas atmosphere**

Replace disconnected homepage side bands and flat app-shell snow background
with one restrained creamy alpenglow -> snow -> powder blend. Keep cards,
alerts, badges, and charts neutral. Verify text contrast in browser computed
styles rather than relying on screenshot appearance.

- [x] **Step 4: Reuse primitives without broad refactoring**

Migrate only touched repeated controls/statuses to Task 3 primitives. Do not
rewrite stable feature components or the filters drawer merely to maximize
primitive adoption.

- [x] **Step 5: Verify (commit deferred)**

```bash
npm --prefix frontend test -- src/App.test.tsx src/search/RecommendationCard.test.tsx src/search/RecommendationDossier.test.tsx src/ui/uiPrimitives.test.tsx
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- app.spec.ts visual.spec.ts
git add frontend/src/App.tsx frontend/src/search/SearchCommandHeader.tsx \
  frontend/src/search/RecommendationCard.tsx \
  frontend/src/search/RecommendationCard.test.tsx \
  frontend/src/search/RecommendationDossier.tsx \
  frontend/src/search/RecommendationNavigator.tsx frontend/src/ui/AppShell.tsx \
  frontend/src/ui/EvidenceQualityBadge.tsx frontend/src/index.css \
  frontend/tests/e2e/app.spec.ts frontend/tests/e2e/visual.spec.ts
git commit -m "fix: polish Search V4 responsive experience"
```

### Task 7: Verify The Complete Flow And Close The Review Gate

**Files:**

- Modify: `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`
- Modify: `docs/superpowers/plans/2026-07-17-search-v4-trust-and-ui-polish.md`
- Modify when needed: `docs/engineering-notes.md`
- Modify when needed: `docs/product-backlog.md`

**Interfaces:**

- Consumes: all prior tasks.
- Produces: exact-head advisory approval, browser evidence, and practical local
  verification handoff.

- [x] **Step 1: Run full automated verification**

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

- [x] **Step 2: Run live functional acceptance**

Start:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1
```

Verify:

1. France/February search renders results before the separate refinement
   request completes, then shows a question, `No follow-up needed`, or
   `Refinement unavailable` with the correct endpoint status. Restarting the
   backend between ranking and refinement produces the unavailable state and
   leaves the displayed ranking usable.
2. A failed update preserves old results with action-scoped copy.
3. Opening and returning from a dossier sends no extra search request and
   restores result/scroll/expansion state.
4. `Why this trip` is understandable before opening technical details.
5. Month and exact-date dossiers display only real endpoint values in separate
   Snow depth / Fresh snow / Temperature views.
6. Missing weather rows create chart gaps and remain visible in the table.
7. Keyboard-only refinement, tabs, disclosures, result expansion, dossier
   switching, and return flow work.
8. A delivered question remains answerable after 60 seconds; applying it reruns
   full search, returns a new baseline fingerprint, and immediately starts the
   next refinement request against that baseline.

- [x] **Step 3: Capture and inspect fidelity screenshots**

Capture homepage, results with multiple expanded cards, month dossier, exact-
date dossier, error/refinement states, and mobile equivalents at 1440x900,
1024x768, and 390x844. Use `view_image` on both the accepted concept and latest
browser screenshots. Record at least five concrete comparison points for
hierarchy, palette, typography, spacing, chart/data fidelity, and responsive
behavior.

- [x] **Step 4: Run exact-head advisory feature-review and code review**

Use Product / Strategy, Backend / API, Data Trust & Source Integrity, UI / UX,
AI / LLM Reliability, Accessibility, Performance, Security, Observability, and
Release / Change Management. Resolve every Blocker/High and every
Critical/Important code-review finding, rerun focused tests after each fix, and
re-review the exact new head.

- [x] **Step 5: Close documentation (commit deferred)**

Set the spec follow-up status to implemented only after all required checks and
reviews pass. Append exact commands, counts, screenshot paths, findings, and
limitations to Execution Notes. Preserve worthwhile non-blocking follow-ups in
`docs/product-backlog.md`.

```bash
git add docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md \
  docs/superpowers/plans/2026-07-17-search-v4-trust-and-ui-polish.md \
  docs/engineering-notes.md docs/product-backlog.md
git commit -m "docs: close Search V4 trust and UI polish"
```

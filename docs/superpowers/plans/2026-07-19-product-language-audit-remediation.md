# Product Language Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` to implement this plan task by task.
> Use one writer at a time. Every implementation head must receive a fresh
> independent review before the next task begins.

**Goal:** Make every current Snowcast customer surface use clear, trustworthy
B2-level American English, stable public error codes, honest booking language,
and layered evidence explanations without changing ranking behavior.

**Architecture:** Keep deterministic planning, typed refinement patches, and
existing success payloads stable. Add a code-only public API error boundary;
map codes to platform-local copy in React and Flutter. Centralize web
presentation wording in existing copy/view-model modules, keep registry-owned
refinement text on the server, keep shared factual companion prose on the
server, and place raw scoring/statistical details behind one advanced
disclosure.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, React 18, TypeScript, Vitest,
Testing Library, Recharts, Playwright, Flutter 3.41, Dart 3.11.

## Global Constraints

- Classification: `review-gated`, full design flow.
- Accepted spec:
  `docs/superpowers/specs/2026-07-19-product-language-audit-remediation-design.md`.
- Accepted ADR: `docs/architecture/adr/0017-use-stable-public-api-error-codes.md`.
- Design review: approved by content-language, UI/UX, mobile companion,
  backend/API, data-trust/source-integrity, and accessibility on exact head
  `a5b5855`.
- Public terms are `Trip option`, `Trip details`, `Must-haves`, `Preferences`,
  `One more question`, `Update results`, and `Keep these results`.
- Do not rename internal models, database fields, route names, typed IDs, or
  ranking enums solely to match display copy.
- Do not change ranking weights, materiality, candidate eligibility, weather
  calculations, provider selection, or refinement patch semantics.
- Public JSON errors contain only `{"error":{"code":"<code>"}}`; no message,
  `detail`, validation path, internal ID, or request ID.
- Existing HTTP statuses remain stable. Operational health/readiness routes
  retain their diagnostic contracts.
- Valid accommodation links remain direct redirects; invalid links return
  branded HTML recovery.
- `30 cm snow-depth reference` is a comparison aid only. Never imply piste
  coverage, opening, comfort, or safety.
- Never present `evaluated_at` as data freshness.
- Work test-first for behavior. Add no dependency.
- Preserve untracked `.superdesign/` and unrelated user changes.
- Use project-scoped GitHub auth through
  `GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast"`.

## Decision Gate Before Execution

- Developer Decision Checkpoints: all resolved.
- Accepted owner decisions: public vocabulary, American English, destination-
  level accommodation, existing-surface mobile parity, layered weather and
  scoring disclosure, stable client-mapped error codes, atomic migration,
  factual 30 cm wording, mobile session/partial-state recovery, and backend HTML
  recovery for stale accommodation links.
- ADR status: ADR 0017 accepted.
- Advisory design-review: complete with no open Blocker or High findings.
- Advisory feature-review: required after each relevant implementation task and
  on the final exact head.

---

### Task 1: Implement The Public API Error Contract

**Files:**

- Create: `app/api/public_errors.py`
- Modify: `app/main.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_api.py`
- Test: `tests/test_search_v4_api.py`
- Test: `tests/test_main.py` or the existing application-factory test owner

**Contract:**

- Define the ADR 0017 code enum, response models, typed exception, customer-route
  predicate, and handlers.
- Convert explicit customer failures to registered codes while retaining current
  statuses and `Retry-After`.
- Normalize malformed JSON, request validation, residual HTTP exceptions, and
  unexpected customer failures without changing operational diagnostics.
- Return branded HTML for unknown public destinations and invalid accommodation
  handoffs. Valid accommodation behavior remains a `307` redirect.
- Declare the public envelope in OpenAPI for covered endpoints.

- [ ] Add failing tests for every registry status/code pair, malformed JSON,
  unknown/missing routes, unexpected failures, operational-route exclusion,
  OpenAPI schemas, `Retry-After`, branded destination 404, branded accommodation
  recovery, and successful redirect.
- [ ] Implement the smallest centralized public-error module and route changes.
- [ ] Run:

```bash
uv run pytest tests/test_search_v4_api.py tests/test_api.py tests/test_public_pages.py -q
uv run ruff check app/api/public_errors.py app/api/routes.py app/main.py tests
uv run ruff format --check app/api/public_errors.py app/api/routes.py app/main.py tests
```

- [ ] Commit as `feat: add stable public API errors`.
- [ ] Run fresh Backend/API and Security/Privacy feature reviews on the exact
  commit; fix and re-review any finding before Task 2.

---

### Task 2: Map Web Errors And Preserve Recovery State

**Files:**

- Create: `frontend/src/apiErrors.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/search/SearchContextRail.tsx`
- Modify: `frontend/src/search/RefinementCard.tsx`
- Modify: `frontend/src/search/SnowEvidence.tsx`
- Modify: `frontend/src/ui/AppShell.tsx`
- Test: `frontend/src/api.test.ts`
- Test: `frontend/src/App.test.tsx`
- Test: relevant component tests above

**Contract:**

- Parse only stable codes; unknown, absent, malformed, non-JSON, transport, and
  decoding failures use operation-specific safe fallback copy.
- Never render server `detail` or validation paths.
- Preserve prior results during updated-search, refinement-discovery, and
  refinement-application failures.
- Keep terminal refinement failure visibly reachable with retry and
  `Keep these results`; keep weather and current-trip failures local.
- Errors use visible non-color-only alert/status semantics without duplicate
  announcements or unexpected focus movement.

- [ ] Add failing mapper and state-transition tests for every operation and all
  malformed/unknown failure categories.
- [ ] Implement typed code parsing, operation copy, and UI state preservation.
- [ ] Run focused Vitest and production build:

```bash
cd frontend
npm test -- --run src/api.test.ts src/App.test.tsx \
  src/search/SearchContextRail.test.tsx \
  src/search/RefinementCard.test.tsx src/search/SnowEvidence.test.tsx
npm run build
```

- [ ] Commit as `fix: make web failures recoverable`.
- [ ] Run fresh UI/UX, Content & Language, and Accessibility feature reviews;
  fix and re-review any finding before Task 3.

---

### Task 3: Apply The Product-Wide Public Language Contract

**Files:**

- Modify: `app/config/search-refinement/presentation-v2.toml`
- Modify: `app/domain/trip_companion.py`
- Modify: `app/public_pages.py`
- Modify: `frontend/src/ui/snowcastCopy.ts`
- Modify: `frontend/src/search/searchPresentation.ts`
- Modify: `frontend/src/search/SearchFiltersDrawer.tsx`
- Modify: `frontend/src/search/SearchContextRail.tsx`
- Modify: `frontend/src/search/RefinementCard.tsx`
- Modify: `frontend/src/search/RecommendationBoard.tsx`
- Modify: `frontend/src/search/AccommodationHandoff.tsx`
- Modify: `frontend/src/ui/AppShell.tsx`
- Modify: `README.md`
- Test: content, presentation, refinement, public-page, accommodation, and
  companion tests that own these surfaces

**Contract:**

- Apply the canonical public glossary while retaining internal IDs and models.
- Rewrite every v2 refinement question, option, and reason so it stands alone,
  asks one decision, and uses mutually exclusive directly comparable answers.
- Keep destination-level booking truth and recommended-base guidance separate.
- Rewrite backend factual companion prose in B2 American English; clients own
  labels, actions, state names, and recovery guidance.
- Replace internal public-page and README product language. Public HTML never
  exposes stable IDs or internal quality tiers as customer labels.
- Add content-contract tests for forbidden primary terms and American spelling.

- [ ] Add failing content-contract and focused behavior tests.
- [ ] Implement copy in its existing owner modules/config; do not reconstruct
  domain meaning in leaf components.
- [ ] Run:

```bash
uv run pytest tests/test_search_refinement_presentation.py \
  tests/test_ai_search_refinement.py tests/test_public_pages.py tests/test_api.py -q
cd frontend
npm test -- --run src/search/contentLanguage.test.ts \
  src/search/searchPresentation.test.ts \
  src/search/SearchFiltersDrawer.test.tsx \
  src/search/SearchContextRail.test.tsx \
  src/search/RefinementCard.test.tsx \
  src/search/AccommodationHandoff.test.tsx src/App.test.tsx
npm run build
```

- [ ] Commit as `fix: align Snowcast public language`.
- [ ] Run fresh Content & Language, Product/Strategy, UI/UX, and
  Monetization/Partnerships feature reviews; fix and re-review before Task 4.

---

### Task 4: Simplify Trip Details And Weather Evidence

**Files:**

- Modify: `frontend/src/search/RecommendationCard.tsx`
- Modify: `frontend/src/search/DossierVerdict.tsx`
- Modify: `frontend/src/search/RecommendationDossier.tsx`
- Modify: `frontend/src/search/DecisionEvidenceLedger.tsx`
- Modify: `frontend/src/search/ScoringDetails.tsx`
- Modify: `frontend/src/search/SnowEvidence.tsx`
- Modify: `frontend/src/search/SnowEvidenceChart.tsx`
- Modify: `frontend/src/search/searchPresentation.ts`
- Modify: `frontend/src/index.css`
- Modify: `docs/snow-evidence-model.md`
- Modify: `docs/domain-language.md`
- Test: corresponding recommendation, evidence, chart, dossier, presentation,
  content-language, and visual/E2E tests

**Contract:**

- Keep one primary explanation and one collapsed `Technical calculation
  details` disclosure; remove duplicate evidence/scoring hierarchy.
- Keep a concrete rationale and snow/evidence cue visible on collapsed 390 px
  cards.
- Derive recommendation claims only from trust states allowed by the spec.
- Present source type, source currency, coverage, expected conditions, and
  limitations separately. Never label `evaluated_at` as freshness.
- Use real response values in charts. Preserve programmatic summary, equivalent
  table, keyboard metric switching, and visible 30 cm limitation text.

- [ ] Add failing hierarchy, trust-claim, weather-mode, 30 cm, accessibility,
  and mobile-card tests.
- [ ] Implement typed view models and component/CSS changes.
- [ ] Run focused Vitest, build, and dossier/search Playwright tests.
- [ ] Capture and inspect desktop and 390 px screenshots for archive-only,
  forecast-assisted, partial, unavailable, expanded/collapsed, and technical-
  disclosure states.
- [ ] Commit as `fix: clarify trip evidence and details`.
- [ ] Run fresh Data Trust, UI/UX, Content & Language, and Accessibility feature
  reviews; fix and re-review before Task 5.

---

### Task 5: Bring Existing Flutter Surfaces To Language And Recovery Parity

**Files:**

- Create: `mobile/lib/public_copy.dart`
- Create: `mobile/lib/api_errors.dart`
- Modify: `mobile/lib/main.dart`
- Modify: `mobile/test/smoke_test.dart`
- Add focused mobile test files when separation improves ownership

**Contract:**

- Remove API-base/debug presentation, numeric quality tiers, raw dates where a
  customer format is expected, and audited internal ranking/companion terms.
- Parse the exact error-code envelope and use operation-specific copy for server,
  unknown, malformed, transport, and decoding failures.
- Clear persisted state and return to sign-in for `session_expired`.
- Load trip summary and events independently; retain summary/events when a
  secondary request or mark-checked action fails.
- Add semantic announcements, labelled recovery actions, standard touch targets,
  and enlarged-text reflow coverage.
- Do not add refinements, detailed dossier weather, or accommodation handoff to
  Flutter in this task.

- [ ] Add failing mapper, widget-state, session-expiry, partial-data, semantics,
  and enlarged-text tests.
- [ ] Extract the smallest reusable copy and error modules and update screens.
- [ ] Run:

```bash
cd mobile
flutter analyze
flutter test
flutter build apk --debug
```

- [ ] Commit as `fix: clarify mobile planning flows`.
- [ ] Run fresh Mobile Companion, Content & Language, Accessibility, and
  Backend/API feature reviews; fix and re-review before Task 6.

---

### Task 6: Cross-Platform Verification And PR Closeout

**Files:**

- Modify: `docs/engineering-notes.md`
- Modify: accepted spec status and this plan's completion state
- Modify: `docs/advisory-reviews/` with final scoped review records
- Modify: E2E/visual tests or fixtures only where final verification exposes a
  real gap

- [ ] Run the full backend suite and Ruff check/format.
- [ ] Run all frontend Vitest tests, production build, and full Playwright suite.
- [ ] Run Flutter analyze/test/build smoke.
- [ ] Start `./scripts/run-built-app.sh`; manually inspect desktop and mobile
  search, repeated refinements, all cards, trip details, weather modes,
  technical disclosure, accommodation success/failure, current trip, public
  destination, public 404, and backend-unavailable recovery.
- [ ] Check no text overlaps, clipped actions, broken icon alignment, decorative
  chart data, inaccessible chart state, missing background pink tint, or raw
  internal/error language remains.
- [ ] Run final exact-head feature reviews for content-language, UI/UX,
  backend/API, data-trust/source-integrity, mobile companion, accessibility,
  security/privacy, and release/change-management.
- [ ] Run a fresh independent whole-branch code review. Fix every defensible
  finding and repeat exact-head reviews.
- [ ] Update spec to `implemented`, mark this plan and SDD ledger complete, and
  commit as `docs: close product language remediation`.
- [ ] Push the branch and update existing draft PR #52. Do not merge or mark it
  ready without an explicit owner request.

## Local Acceptance Path

```bash
./scripts/run-built-app.sh
```

Open the URL printed by the script. Search for a trip, answer at least two
successive one-topic questions, expand every result card, open Trip details,
inspect archive and forecast weather, open/close technical calculations, test a
valid and stale accommodation link, and inspect Current trip. Repeat the core
path at 390 px. For Flutter, run the debug app against the same API and verify
sign-in, search, save/current-trip, expired-session, and secondary-failure
states.

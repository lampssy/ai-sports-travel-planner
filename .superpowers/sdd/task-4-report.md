# Task 4 Report: Trip Details and Weather Evidence

Status: DONE

## Scope and gates

- Starting HEAD: `9c32dccb52688b8111ef9d9c06eb19bb39284cb5`
- Classification: review-gated, full design flow.
- Developer Decision Checkpoint: resolved by the accepted Task 4 brief and product-language remediation design. No new owner decision was introduced.
- ADR: no new ADR required; component ownership and presentation boundaries follow the accepted design and existing architecture.
- Advisory design review: complete before implementation, as recorded by the accepted design.
- Advisory feature review: fresh Data Trust & Source Integrity, UI / UX, Content & Language, and Accessibility reviews completed with no defensible findings.

## Implementation

- Added one typed weather-evidence presentation view model for source type, source currency, coverage, expected conditions, and the main limitation.
- Kept forecast currency owned by `issued_at` and archive currency owned by `latest_archive_year` plus baseline years. `evaluated_at` and `cache_valid_until` remain cache/request metadata only.
- Reworked trip details to share one candidate narrative across the verdict and Why this trip sections, removing verbatim repetition.
- Consolidated raw scoring, policy IDs, trust internals, statistical methods, source rows, and daily values under one collapsed `Technical calculation details` disclosure.
- Added actual-value chart summaries, keyboard-operable metric controls, an equivalent daily-values table, and the exact visible 30 cm explanation.
- Kept collapsed 390 px cards focused on destination/stay, trip fit, snow evidence, and one concrete rationale.
- Preserved request, ranking, evidence selection, cache, weather-selection, and API semantics. Recharts remains in the lazy weather-chart chunk.

## Test-first record

- Initial focused red run: 79 tests, 67 passed and 12 failed on the old hierarchy/currency/disclosure expectations.
- Migrated the recommendation, dossier, weather, presentation, and Playwright assertions before completing the implementation.
- Final focused Vitest command:

  `npm test -- --run src/search/RecommendationCard.test.tsx src/search/RecommendationDossier.test.tsx src/search/DecisionEvidenceLedger.test.tsx src/search/SnowEvidence.test.tsx src/search/searchPresentation.test.ts src/search/contentLanguage.test.ts src/search/weatherEvidenceCache.test.ts`

  Result: 7 files passed, 95 tests passed, duration 2.37 s.

- Production build command: `npm run build`

  Result: passed; Vite 6.4.1, 2,397 modules, 2.48 s. Main JS 276.04 kB (82.27 kB gzip); lazy `SnowEvidenceChart` chunk 395.54 kB (114.19 kB gzip).

## Browser and Playwright verification

- Browser-first: succeeded with the Codex in-app browser against `http://127.0.0.1:4173/`. Verified the search surface at the default viewport and 390 x 844; no browser warnings or errors. Playwright fallback was not needed.
- Functional dossier/search Playwright:

  `npx playwright test tests/e2e/app.spec.ts --grep "month dossier|forecast dossier|stale fallback|cache"`

  Result: 6 passed in 9.5 s. Covers archive, forecast-assisted partial coverage, unavailable/fallback, retry, cache isolation, and cache expiry.

- Deliberate visual baseline update:

  `npx playwright test tests/e2e/visual.spec.ts --update-snapshots`

  Result: 15 passed in 16.5 s after fixture/assertion corrections and image inspection.

- Final visual diff check:

  `npx playwright test tests/e2e/visual.spec.ts`

  Result: 15 passed in 11.2 s with no snapshot differences.

## Screenshots inspected

- Accepted inputs: `.superdesign/search-v4-dossier-recommended.png`, `.superdesign/search-v4-dossier-full-page.png`, and the prior desktop/mobile dossier baselines.
- Desktop: homepage, expanded archive dossier, full archive dossier, collapsed partial-forecast dossier, and expanded technical calculation details.
- 390 px: expanded results, collapsed results, archive weather evidence, complete forecast chart, unavailable weather evidence, and mobile dossier switcher.
- Review result: no incoherent overlap, clipped actions, or horizontal page overflow. Technical value tables intentionally scroll within their bounded container; the reviewed desktop layout gives them full disclosure width.

## Feature reviews

### Data Trust & Source Integrity

No defensible findings. Public claims are derived from existing typed response values, source currency is correctly separated from request/cache metadata, and uncertainty remains visible.

### UI / UX

No defensible findings. Primary trip details retain one explanation, advanced data is collapsed, and the reviewed desktop/390 px states preserve the expected decision cues and controls.

### Content & Language

No defensible findings. Public copy follows the accepted vocabulary, avoids internal ranking terms in the primary flow, and uses the approved 30 cm wording exactly.

### Accessibility

No defensible findings. Metric controls implement tab keyboard behavior, charts have programmatic summaries, equivalent semantic tables are available, status is not conveyed by color alone, and mobile labels remain visible.

## Changed areas

- Presentation and composition: `frontend/src/search/searchPresentation.ts`, recommendation/dossier components, `SnowEvidence.tsx`, `SnowEvidenceChart.tsx`, and `WeatherEvidenceTechnicalDetails.tsx`.
- Styling: `frontend/src/index.css`.
- Tests: focused search Vitest files plus `frontend/tests/e2e/app.spec.ts`, `frontend/tests/e2e/visual.spec.ts`, and 16 reviewed Darwin baselines.
- Documentation: `docs/domain-language.md`, `docs/snow-evidence-model.md`, and this SDD progress/report.

## Concerns and residual risk

- Native assistive-technology behavior and non-Chromium engines were not available in this environment. The semantic and keyboard contracts are covered by Vitest and Chromium Playwright.
- The technical daily-values tables are intentionally horizontally scrollable because they expose every response metric; this is confined to the collapsed advanced disclosure.
- Existing npm `always-auth` deprecation warnings remain unrelated to Task 4.
- `.superdesign/` was preserved and not staged.

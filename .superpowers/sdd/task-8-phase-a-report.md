# Search V4 Task 8 Phase A Report

## Outcome

- Status: `DONE_WITH_CONCERNS`
- Starting head: `1e231846d91160603e321eac342c70a437d98c20`
- Phase A implementation and evidence commit:
  `78548427020532ecdd4d803635037528d81ffece`
- Scope: deterministic visual baselines, reference comparison, concrete frontend
  corrections, accessibility/resilience QA, durable notes, and full local
  verification. Independent advisory feature review remains a later phase.

## Changed Files In The Phase A Implementation Commit

1. `docs/engineering-notes.md`
2. `docs/superpowers/plans/2026-07-16-search-v4-web-experience.md`
3. `frontend/playwright.config.ts`
4. `frontend/src/App.tsx`
5. `frontend/src/index.css`
6. `frontend/tests/e2e/app.spec.ts`
7. `frontend/tests/e2e/visual.spec.ts`
8. `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-dates-collapsed-desktop-darwin.png`
9. `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-mobile-snow-evidence-darwin.png`
10. `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-mobile-switcher-darwin.png`
11. `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-month-expanded-desktop-darwin.png`
12. `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-month-full-desktop-darwin.png`
13. `frontend/tests/e2e/visual.spec.ts-snapshots/homepage-desktop-darwin.png`
14. `frontend/tests/e2e/visual.spec.ts-snapshots/homepage-mobile-darwin.png`
15. `frontend/tests/e2e/visual.spec.ts-snapshots/homepage-tablet-darwin.png`
16. `frontend/tests/e2e/visual.spec.ts-snapshots/results-expanded-desktop-darwin.png`
17. `frontend/tests/e2e/visual.spec.ts-snapshots/results-expanded-mobile-darwin.png`
18. `frontend/tests/e2e/visual.spec.ts-snapshots/results-expanded-tablet-darwin.png`

This report is committed separately so it can cite the immutable Phase A
implementation commit rather than attempting to embed its own commit SHA.

## Deterministic Visual Inputs

- Chromium locale `en-GB`, UTC timezone, light color scheme, and reduced motion.
- Browser time fixed at `2026-07-16T12:00:00Z`.
- Typed Search V4, refinement-preview, month climatology, and exact-date
  forecast-assisted fixtures; no oracle values copied into product fixtures.
- `document.fonts.ready` and the state-specific main heading awaited before
  capture.
- Animation, transition, caret, and smooth-scroll variance disabled for capture.
- Standard Playwright snapshot folder and `toHaveScreenshot` assertions used.

## Screenshot Inventory

All hashes are SHA-256.

| Snapshot | Dimensions | SHA-256 |
| --- | --- | --- |
| `dossier-dates-collapsed-desktop-darwin.png` | 1440x900 | `28aaec96ee148d5b56ca7d7afaed8cd14bd4c3d0499954d4e1fc6641bf63c552` |
| `dossier-mobile-snow-evidence-darwin.png` | 390x844 | `7f55e9394d0f5026ef76c6058b7b151f794173bebd381a4bf6154c7538c5a14e` |
| `dossier-mobile-switcher-darwin.png` | 390x844 | `1b42fa56a418d95dc7effad85de85e004c8f3ffc034ad4b21b3e1bb45bcac1a9` |
| `dossier-month-expanded-desktop-darwin.png` | 1440x900 | `2a12ad6ff166acbdb8b96db2e7507e44872ec46e513548704948dd43f7eee603` |
| `dossier-month-full-desktop-darwin.png` | 1440x3535 | `71fdb2f9c003a06693ad90cb274d5bebfcc22d1a8b1e2448421bd761e008af50` |
| `homepage-desktop-darwin.png` | 1440x900 | `135f78d129bc987efbf4401ec8517861d4cb934554a37ed9b25d0cb6d2f3e6cd` |
| `homepage-mobile-darwin.png` | 390x844 | `6aeb40fdf4f12cf0e9ad5b095518c4c525a3c3643616632cb486bc4027d15f94` |
| `homepage-tablet-darwin.png` | 1024x768 | `d0308e1442133cc7f3fd02b365d26eea1f928b6a45e1fcc493ebd5e7d86a68bb` |
| `results-expanded-desktop-darwin.png` | 1440x900 | `35b3fdfa3c537ab674e1e6d26aeb16e3230ac53aef77a58e24ca7a817a916cdf` |
| `results-expanded-mobile-darwin.png` | 390x844 | `5e818ba956833d77f0b4475843799ff84ae0a17b67166f14e51cff3cac15e2b4` |
| `results-expanded-tablet-darwin.png` | 1024x768 | `5133a513cb373943aaed68f4cba2f3d56fb2d3cf9b4c80d0efa41657a353c0b1` |

## Accepted-Oracle Comparison

All five accepted references and all produced screenshots were inspected with
`view_image` at original detail.

- `01-homepage-command-stage.png`: the implementation preserves the dark
  midnight brand shell, large command-stage hierarchy, restrained pink planning
  signal, light command surface, parsed chips, and concrete example result.
  Product wording and fixture values remain typed/current rather than copied
  from the illustration.
- `02-hybrid-results-expanded-desktop.jpg`: the implementation preserves the
  compact command header, context/refinement rail, grouped recommendation board,
  independent card expansion, stable score tracks, alternatives, evidence,
  actions, and progressive scoring disclosure. The first inspection exposed
  character-level metric wrapping at 1024 px; the 70 rem layout now uses a
  narrower context rail/action column and readable metric tracks.
- `03-dossier-results-navigator.jpg`: expanded and collapsed desktop snapshots
  preserve master-detail orientation, bounded result switching, selected-result
  identity, progressive anchors, and an evidence-led content hierarchy.
- `04-dossier-snow-evidence.jpg`: month evidence remains explicitly historical,
  with provenance, a semantic chart, equivalent structured values, metrics,
  interpretation, and limitations/status text. No live/current claim is added.
- `05-dossier-full-page.png`: the full-page snapshot preserves verdict,
  evidence, selected trip configuration, alternatives, estimate-only stay
  handoff, evidence ledger, and scoring disclosure in the accepted order.

## Concrete Frontend Corrections

- Narrowed the 1024 px results rail and action column so metric values no longer
  collapse into character-level wrapping.
- Moved focus to the results heading after rerank/undo with
  `preventScroll: true`, preserving viewport restoration while providing a
  stable keyboard and screen-reader destination.
- No ranking, fixture semantics, evidence policy, or visual motif was changed.

## Accessibility And Resilience Evidence

Automated Chromium evidence covers:

- keyboard submission, filter drawer Escape/return focus, independent card
  toggles, alternative selection, scoring disclosure, dossier link, desktop
  navigator, mobile switcher, weather tabs, dossier switch, and return flow;
- focused results heading after initial search and rerank, focused dossier
  heading after route switches, and focus preservation around asynchronous
  weather evidence;
- polite rank-change, route-change, and weather-load/retry announcements;
- no page horizontal overflow at desktop, 1024 px, 390 px, and a 720 CSS-pixel
  layout representing a 1440 px browser at 200% zoom;
- reduced-motion media behavior under Playwright's reduced-motion context;
- text labels for ranked/unranked, evidence quality, forecast/historical mode,
  limitations, stale evidence, and unavailable evidence, so meaning does not
  depend on color;
- failed initial search with brief-preserving resubmit, failed rerank with
  selected-option retry, no results, direct/missing dossier context, missing
  metrics, stale forecast limitation, typed unavailable evidence, weather
  transport retry, cache expiry, and stale/late response isolation;
- month searches never expose a Forecast tab; exact-date forecast and
  historical context remain separate.

Static logging/telemetry inspection found no frontend analytics/logger calls,
no request-body logging in the Search or weather-evidence routes, and only
method/route/status/duration/request-id request completion fields. Weather
observability remains aggregate metrics; raw brief and raw weather payload
values are not emitted.

## Verification

| Command | Result |
| --- | --- |
| `uv run pytest -q` | PASS: 1,417 passed in 396.52 s |
| `uv run ruff check .` | PASS: all checks passed |
| `npm --prefix frontend test` | PASS: 12 files, 74 tests |
| `npm --prefix frontend run build` | PASS: TypeScript and Vite production build |
| `npm --prefix frontend run test:e2e` | PASS: 35 Chromium journeys, including 11 snapshot baselines |

The final post-staging frontend rerun also passed all 74 unit tests, production
build, and all 35 Chromium E2E journeys.

## Concerns And Limitations

- Independent Snowcast advisory feature review has not run; the feature spec is
  intentionally not marked implemented.
- The configured Playwright WebKit path is
  `/Users/awownysz/Library/Caches/ms-playwright/webkit-2272/pw_run.sh`, but the
  executable is absent. WebKit was not installed, per task constraints.
- The 200% automated check uses the equivalent 720 CSS-pixel responsive layout
  for a 1440 px browser. It is not an OS/browser-chrome zoom-control recording.
- Browser assertions and semantic inspection are not a native screen-reader
  session. Independent accessibility review should retain that manual check.
- Baselines are Darwin Chromium snapshots. Cross-platform CI would need an
  explicit owner decision on platform-specific baselines or a pinned screenshot
  environment before enabling visual comparison elsewhere.

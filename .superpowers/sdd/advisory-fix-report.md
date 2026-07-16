# Search V4 Advisory Fix Report

## Outcome

- Status: `DONE`
- Classification: `review-gated`
- Starting head: `67912d3869f9fbfc3745cfcc07a78b12be1d2ef7`
- Developer Decision Checkpoint: resolved by the owner. Terrain remains a core metric, with field-level trust and provenance preserved and visibly qualified.
- ADR: no new ADR required. ADR 0014 continues to own on-demand weather evidence loading; this patch does not change that boundary.
- Advisory review: lane A, B, and C Blocker/High findings plus the adjacent weather-provenance Medium were implemented. The Observability Medium was intentionally excluded as directed.

## Decision And Trust Contract

`SearchV4PassSummary.accessible_piste_km_evidence` is a required nullable typed field containing:

- `trust_status`: the owning manifest field status
- `scope`: `pass`, `terrain_domain`, or `ski_area`
- `source_entity_id`: the entity that owns the terrain value
- `field_group`: `pass_accessible_terrain`, `aggregate_terrain`, or `terrain_metrics`

The server remains the calculation owner. It selects pass-level terrain first, then a single covered terrain-domain aggregate, then a bounded ski-area fallback. Each non-null value carries evidence derived from the same owning manifest field. Pinzolo therefore returns `31 km` with `estimated`, `ski_area`, `pinzolo-ski-area`, and `terrain_metrics`, rather than promoting the estimate to verified pass-accessible terrain.

The TypeScript contract preserves the field. Shared presentation logic labels pass, domain, and ski-area scope consistently across the result card, trip essentials, dossier, and evidence ledger. Estimated and needs-source figures remain visible but explicitly qualified; ski-area fallback never claims pass-wide coverage.

## Changed Files

Backend and API:

- `app/domain/search_v4_service.py`
- `tests/test_search_v4_service.py`
- `tests/test_search_v4_api.py`
- `tests/test_api.py`

Frontend implementation:

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/types.ts`
- `frontend/src/search/DecisionEvidenceLedger.tsx`
- `frontend/src/search/RecommendationCard.tsx`
- `frontend/src/search/RecommendationNavigator.tsx`
- `frontend/src/search/ScoringDetails.tsx`
- `frontend/src/search/SearchFiltersDrawer.tsx`
- `frontend/src/search/SnowEvidence.tsx`
- `frontend/src/search/searchPresentation.ts`

Frontend unit and browser coverage:

- `frontend/src/App.test.tsx`
- `frontend/src/search/AccommodationHandoff.test.tsx`
- `frontend/src/search/RecommendationCard.test.tsx`
- `frontend/src/search/RecommendationDossier.test.tsx`
- `frontend/src/search/SnowEvidence.test.tsx`
- `frontend/src/search/searchPresentation.test.ts`
- `frontend/tests/e2e/app.spec.ts`
- `frontend/tests/e2e/fixtures/searchV4.ts`

Documentation:

- `docs/data-trust-model.md`
- `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`
- `.superpowers/sdd/advisory-fix-report.md`

Deterministic visual baselines:

- `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-mobile-snow-evidence-darwin.png`
- `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-mobile-switcher-darwin.png`
- `frontend/tests/e2e/visual.spec.ts-snapshots/dossier-month-full-desktop-darwin.png`
- `frontend/tests/e2e/visual.spec.ts-snapshots/results-expanded-desktop-darwin.png`
- `frontend/tests/e2e/visual.spec.ts-snapshots/results-expanded-mobile-darwin.png`
- `frontend/tests/e2e/visual.spec.ts-snapshots/results-expanded-tablet-darwin.png`

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q tests/test_search_v4_service.py tests/test_search_v4_api.py tests/test_api.py`: 68 passed.
- `UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_v4_service.py tests/test_search_v4_service.py tests/test_search_v4_api.py tests/test_api.py`: passed.
- `npm test -- --run`: 12 files, 82 tests passed.
- `npx playwright test tests/e2e/app.spec.ts --grep "expired forecast cache" --repeat-each=5 --workers=1`: 5 passed after an isolated load-sensitive failure in an earlier concurrent verification run.
- `npx playwright test tests/e2e/app.spec.ts --grep "browser Back restores" --repeat-each=10`: 10 passed under six-worker load.
- `npx playwright test tests/e2e/visual.spec.ts --update-snapshots`: 10 passed; deterministic baselines updated.
- `npx playwright test tests/e2e/app.spec.ts tests/e2e/visual.spec.ts`: 40 passed on the final source.
- `npm run build`: TypeScript and Vite production build passed.
- `git diff --check`: passed.

## Screenshot Evidence

Updated dimensions and SHA-256 hashes:

| Baseline | Dimensions | SHA-256 |
| --- | ---: | --- |
| `results-expanded-desktop-darwin.png` | 1440x900 | `a154fb3dec12a150d9910d7b24d2d64298ee4fa57d5c94d280506671c2577506` |
| `results-expanded-tablet-darwin.png` | 1024x768 | `4887125f8a1ad63cc62cf487683ff25e584df3bb125e01fb85005636fa399fd2` |
| `results-expanded-mobile-darwin.png` | 390x844 | `88cbb7080a334e90d0b2d158f6f1c51ebfd6f2c02c3502f0e824658dbf8ebc70` |
| `dossier-month-full-desktop-darwin.png` | 1440x3535 | `a072ebddfcf078a7dabd527cc0bcdcdd65fdf5b55ed7d9b635b426f4b0c136c2` |
| `dossier-mobile-switcher-darwin.png` | 390x844 | `5f835a0b399825b8269cb91557752374df6c19b41482e01c757b106be7f7cde5` |
| `dossier-mobile-snow-evidence-darwin.png` | 390x844 | `2672f00a10393daf1c7e333892aabd6e5d68d500b03fb3b6be90f1d645c7ee30` |

Visual inspection notes:

- 1440: desktop results and dossier remain aligned; qualified terrain wording fits without overlap or layout shift.
- 1024: `Current trip` remains visible in the compact header and the search controls remain contained.
- 390: `Current trip` remains visible in results and dossier headers; the two-row header, mobile switcher, selected stay-base label, and snow evidence remain readable without horizontal overflow.
- The mobile switcher and snow-evidence images were inspected independently at original resolution; no blank canvas or overlapping controls are present.

## Commit

- Commit subject: `fix: resolve Search V4 advisory findings`
- Final commit SHA: recorded in the Git commit metadata and final handoff. A commit cannot embed its own final SHA in tracked content because changing this report changes the commit object.

## Concerns

- The requested Observability Medium is not implemented or added to the backlog in this patch; it remains for the post-fix re-review workflow.
- Browser verification used the repository's configured Chromium/Darwin Playwright project; no separate Firefox or WebKit run was requested.
- npm emitted existing `always-auth` deprecation warnings; they did not affect tests or the build.
- No unresolved Blocker or High finding remains in this fix wave.

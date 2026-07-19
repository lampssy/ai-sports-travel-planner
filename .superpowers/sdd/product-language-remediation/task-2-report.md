# Task 2 Report: Recoverable Web Errors

## Outcome

Implemented the Task 2 web error boundary and recovery behavior from baseline
`b76aef4`.

- Added a typed client boundary for the stable public API error envelope.
- Removed backend `detail` and validation-path parsing from the React API client.
- Added operation-specific client copy for known, unknown, malformed, transport,
  abort, and response-decoding failures.
- Preserved usable search results and selected refinement answers when updates
  fail.
- Added a visible terminal refinement error with `Try again` and
  `Keep these results` actions without duplicate live announcements.
- Kept weather and current-trip failures local while preserving already loaded
  data.

## Changed Files

- `frontend/src/apiErrors.ts`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/search/RecommendationBoard.tsx`
- `frontend/src/search/SearchContextRail.tsx`
- `frontend/src/search/RefinementCard.tsx`
- `frontend/src/search/SnowEvidence.tsx`
- `frontend/src/api.test.ts`
- `frontend/src/App.test.tsx`
- `frontend/src/search/SearchContextRail.test.tsx`
- `frontend/src/search/RefinementCard.test.tsx`
- `frontend/src/search/SnowEvidence.test.tsx`
- `.superpowers/sdd/product-language-remediation/task-2-report.md`

## Verification

- TDD red phase confirmed the missing mapper and recovery behavior before the
  implementation.
- Focused Vitest command from the task brief: passed, 146 tests across 5 files.
- `npx tsc -b --pretty false`: passed.
- `npm run build`: passed; Vite production build completed.
- No frontend lint script or ESLint configuration is present in the repository.
- `git diff --check`: passed.

## Scope

Task 3's broader terminology rewrite was not included. `.superdesign/` was not
modified.

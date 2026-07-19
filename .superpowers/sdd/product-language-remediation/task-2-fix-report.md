# Task 2 Advisory Fix Report

## Outcome

Resolved the UI/UX, Content & Language, and Accessibility findings on `14e72e3`.

## Changes

- Made API-declared and transport refinement failures visible and recoverable.
- Added `Update results` and `Keep these results` to failed refinement application without starting another question on exit.
- Kept refinement and Current trip retry controls mounted, busy, disabled, and focused while requests run.
- Localized save failures by candidate on result cards and Trip details, and cleared all stale save failures after a successful save or result refresh.
- Removed duplicate snow/weather live announcements.
- Replaced misleading or internal error wording with neutral B2 American English and the accepted public vocabulary.
- Updated the failed-refinement Playwright journey and added focused state, copy, and accessibility tests.

## Verification

- Focused Vitest: 172 tests passed across 6 files.
- Targeted Playwright failed-refinement journey: 1 passed.
- `npx tsc -b --pretty false`: passed.
- `npm run build`: passed.
- `git diff --check`: passed.

## Review status

Fresh exact-head UI/UX, Content & Language, and Accessibility re-review required after commit.

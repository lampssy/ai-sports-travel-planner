# Task 2 Advisory Fix Report

## Outcome

Resolved the UI/UX, Content & Language, and Accessibility findings on `14e72e3`.

## Changes

- Made API-declared and transport refinement failures visible and recoverable.
- Added `Update results` and `Keep these results` to failed refinement application without starting another question on exit.
- Kept refinement and Current trip retry controls mounted, busy, focusable, and semantically unavailable while requests run; guarded repeat activation in code.
- Localized save failures by candidate on result cards and Trip details, and cleared all stale save failures after a successful save or result refresh.
- Removed duplicate snow/weather live announcements.
- Replaced misleading or internal error wording with neutral B2 American English and the accepted public vocabulary.
- Updated the failed-refinement Playwright journey, added real-browser focus coverage for all three retry paths, and covered failed manual search updates preserving results and focus.

## Verification

- Focused Vitest: 173 tests passed across 6 files.
- Targeted Playwright recovery journeys: 4 passed.
- `npx tsc -b --pretty false`: passed.
- `npm run build`: passed.
- `git diff --check`: passed.

## Review status

Content & Language approved `be62a2b`. Exact-head UI/UX and Accessibility
re-reviews on `834ea1b` found a final bounded fix wave: successful retry focus
and announcements, failed-apply focus, stale refinement error cleanup, duplicate
weather recovery actions, pending-control styling, and three stale E2E
assertions. These findings must be fixed and re-reviewed before Task 2 closes.

# Task 2 Final Recovery Fix Wave Report

## Scope

Completed the bounded Task 2 recovery fix wave from starting head `d508ef8`.
`.superdesign/` remained untracked and untouched. No Task 3 language work was
started.

## Implementation

- Corrected the stale Current trip and weather Playwright acceptance assertions
  to use the approved empty-state copy and alert-owned unavailable/error state.
- Kept refinement controls mounted and focusable while pending with guarded
  `aria-disabled` behavior. Pending controls now use the same reduced-emphasis,
  non-pointer presentation as native disabled controls.
- Returned focus to the visible recovery action after a failed refinement apply;
  terminal no-question retries now return focus to the results heading.
- Added success-only Current trip recovery events. Saved-trip recovery focuses
  the trip heading and current-conditions recovery focuses the conditions
  region; each has one local polite announcement.
- Cleared obsolete terminal refinement failure copy when a retry resolves to a
  stale baseline.
- Kept repeated unavailable weather responses to the single `Check again`
  recovery action rather than rendering an additional reload action.

## TDD Evidence

Focused tests were added before implementation. The initial red run exposed the
missing terminal-retry focus and the duplicate weather recovery action. A
stale-baseline regression test also verified that the former terminal failure
copy could remain after the stale state. The implementation was then kept to
the minimum needed for those tests and the existing browser journeys to pass.

## Verification

- `npm test -- --run src/api.test.ts src/App.test.tsx src/search/SearchContextRail.test.tsx src/search/RefinementCard.test.tsx src/search/SnowEvidence.test.tsx src/ui/uiPrimitives.test.tsx`: 175 passed.
- `npx tsc -b --pretty false`: passed.
- `npm run build`: passed.
- `npm run test:e2e -- --grep "anonymous current-trip route remains available|retry keeps keyboard focus|failed refinement apply preserves results|weather evidence"`: 5 passed.
- Existing weather acceptance journeys for typed unavailability and transport
  recovery: 2 passed.
- `git diff --check`: passed.

## Review Gate

- Classification: review-gated accessibility and recovery behavior.
- Developer Decision Checkpoint: resolved by the binding requirements; no new
  material product or architecture decision was introduced.
- ADR: not needed for this narrow UI recovery repair.
- Advisory review: skipped because this is a prescriptive final fix wave over
  an existing review finding; independent self-review of focus, announcement,
  stale-state, and duplicate-action paths completed.

## Concerns

The npm commands emit existing `always-auth` configuration deprecation
warnings. They did not affect the test, typecheck, build, or browser results.

---

# Task 2 Review Fix Wave 2 Report

## Scope

Completed the exact-head Task 2 follow-up from starting head `1bfbff3`.
`.superdesign/` remained untracked and untouched, and no unrelated files were
modified.

## Implementation

- Kept the focused weather `Check again` action mounted during retry, exposed
  its pending state with `aria-disabled` and `aria-busy`, guarded duplicate
  activation, and restored focus to the one valid recovery control after both
  successful and repeatedly unavailable outcomes.
- Replaced sticky saved-trip and current-conditions recovery flags with keyed
  per-request announcements, so every successful recovery in the same mounted
  Current trip view creates one fresh live-region event while preserving the
  required focus destination.
- Made the entire selected refinement option visibly unavailable while pending,
  including a wait cursor and reduced opacity, while keeping its radio mounted,
  focusable, and `aria-disabled`.
- Excluded native-disabled and ARIA-disabled Snowcast actions from hover and
  active color/press selectors while retaining their focus treatment, opacity,
  and wait cursor.

## TDD Evidence

Tests were written before production changes. The initial unit run failed
because weather retry replaced the focused action with the loading state and
because both Current trip recovery announcements reused their original DOM
nodes on a second success. The initial Chromium run also showed the pending
refinement label retained a pointer cursor and the weather recovery action
unmounted. The narrow tests passed after the scoped implementation.

## Verification

- `npm test -- --run src/api.test.ts src/App.test.tsx src/search/SearchContextRail.test.tsx src/search/RefinementCard.test.tsx src/search/SnowEvidence.test.tsx src/ui/uiPrimitives.test.tsx`: 177 passed.
- `npx tsc -b --pretty false`: passed.
- `npm run build`: passed.
- `npm run test:e2e -- --grep "saved-trip retry keeps keyboard focus|current-conditions retry keeps keyboard focus|failed refinement apply preserves results|transport failure is not cached|weather retry keeps focus while pending"`: 5 passed.
- `git diff --check`: passed.

## Review Gate

- Classification: review-gated accessibility and recovery behavior.
- Developer Decision Checkpoint: resolved by the binding follow-up findings; no
  material product or architecture decision remained open.
- ADR: not needed for this narrow UI state and accessibility correction.
- Advisory review: skipped because the follow-up brief prescribed the behavior
  and verification contract; self-review covered request races, repeat-event
  announcements, focus restoration, disabled interaction styles, and scoped
  file ownership.

## Concerns

The npm commands continue to emit the existing `always-auth` configuration
deprecation warning. It did not affect unit, typecheck, build, or Chromium
results.

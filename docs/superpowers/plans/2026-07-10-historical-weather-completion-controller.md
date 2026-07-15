# Historical Weather Completion Controller Implementation Plan

## Objective

Implement the accepted fixed-window, coverage-driven completion controller from
`docs/superpowers/specs/2026-07-10-historical-weather-completion-controller-design.md`.

## Decision and Review Gate

- Classification: review-gated
- Developer Decision Checkpoints: resolved by the owner
- ADR: not needed; no new persisted orchestration boundary
- Advisory design-review: completed with backend-api,
  data-trust-source-integrity, and observability-ops
- Advisory feature-review: required before final handoff

## Implementation

1. Add failing tests for provider-request budgets and explicit backfill outcomes.
2. Extend `backfill_historical_weather` so retries count against a bounded remote
   request budget and expected throttling is distinguishable from hard failure.
3. Add repository coverage needed to identify current climatology and replace
   one ski area's rows transactionally; update climatology rebuild to use it.
4. Add controller tests for complete, work-remaining, throttled, and hard-failure
   outcomes plus the three-band climatology gate.
5. Implement `app.data.complete_historical_weather` as a deterministic
   coordinator over catalog selection, backfill, archive coverage, and
   climatology rebuild.
6. Add a daily/manual GitHub Actions workflow with a conservative request
   budget, job summary, timeout, and shared archive-provider concurrency group.
   Apply the same group to manual backfill and recent reconciliation workflows.
7. Document operation, progress, expected 429 handling, fixed campaign bounds,
   and the non-commercial free-tier caveat.

## Verification

- `pytest tests/test_open_meteo.py tests/test_snow_climatology.py tests/test_repository.py tests/test_historical_weather_completion.py -q`
- focused Ruff checks for changed Python/tests
- workflow static assertions and YAML parse through tests
- broader data and observability tests affected by repository/result changes
- advisory feature-review of the final diff
- `git diff --check`

## Risks

- Open-Meteo weighted-call accounting is not identical to HTTP request count;
  the request budget is intentionally conservative and operator-tunable.
- Expected throttling must not hide permanent failures. Tests will require
  separate typed outcomes and hard-failure precedence.
- Existing archive writers must share one concurrency group or scheduled jobs
  can amplify quota pressure.
- Climatology replacement must remain atomic even when row insertion fails.

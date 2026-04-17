# Sprints 17–19: Merged Proposal (Quality First)

## Summary

The next three sprints should prioritize **recommendation trust before public launch**. The product
already has the right shape: explainable search, provenance cues, booking handoff, and a basic
current-trip view. The problem is that the underlying seed data and month-aware planning model are
still too coarse for public exposure. The immediate priority should be a **data-quality and
planning-calibration sprint**, followed by deployment and scheduled freshness, then historical
backfill plus selective expansion.

The recommended sequence is:
- **Sprint 17:** planning/data quality calibration
- **Sprint 18:** deployment + scheduled freshness
- **Sprint 19:** historical backfill + selective resort expansion

## Why This Sequence

This merged plan keeps the stronger sequencing from the existing quality-first proposal while
pulling in the best concrete observations from the more detailed Claude draft.

What it keeps:
- deployment follows the first data-quality/calibration sprint because recommendation trust is the
  gating issue
- broad resort expansion is deferred until the product can support it credibly
- `PROJECT.md` stays concise while this document holds the richer tactical proposal

What it incorporates:
- synthetic area names are a real trust problem and need explicit cleanup
- one-area-per-resort coverage is thin and should be treated honestly, not hidden
- sparse-history planning is too heuristic-heavy and must become more conservative

What it deliberately does **not** lock in yet:
- `glacier_served` as the only late-season modeling fix
- a fixed expansion target such as “add 10 resorts”
- stale assumptions like replacing an `example.com` booking stub that is no longer present in the
  repo

## Sprint 17 — Planning Calibration and Seed Data Quality

**Goal:** Existing resort recommendations become materially more credible before launch.

Sprint 17 is explicitly split into two phases:

### Phase 1 — Source-backed resort data audit

- Audit all current resorts against official sources using
  [sprint-17-resort-audit-template.md](./sprint-17-resort-audit-template.md).
- Verify the fields that materially affect planning and naming realism:
  - seasonality
  - elevations
  - coordinates
  - area naming
- Replace obviously synthetic area naming with real resort zone names where the data can be
  verified.
- Treat area/rental pricing, quality labels, lift-distance labels, and rental-provider choice as
  product-curated unless they are separately verified.
- Produce:
  - a correction list for factual fields
  - an unresolved-issues list for product decisions
  - a shortlist of key realism-test resorts for phase 2

### Phase 2 — Planning calibration and realism fixes

- Recalibrate the month-aware planning model so **season-edge months degrade more aggressively**,
  especially when evidence is sparse.
- Change sparse-history behavior so “history is sparse” is not just wording:
  - low-evidence months should receive a stronger score/confidence penalty
  - edge-month openness should not come from elevation alone
- Investigate late-season reliability modeling options during the sprint, then choose one in
  implementation once the audited data confirms the best shape.
- Add realism tests for known problematic cases, including:
  - Ischgl in May should not surface as a strong recommendation
  - high-altitude resorts can remain viable in late season, but not automatically `fair/open`
  - out-of-season and edge-season behavior stays explainable and deterministic
- Keep public APIs stable; this sprint should improve output quality, not introduce new user-facing
  product surfaces.

Implementation note:
- most of the code/model work can be implemented directly in chat
- the dataset correction pass must be **source-backed**, not memory-based
- the exact late-season mechanism should remain open until the audited data clarifies the best
  model shape

### Important interfaces / changes

- No required new public endpoint.
- Internal planning behavior should be tightened in the deterministic planning layer and seed
  metadata.
- Existing `/api/search` response shape should remain stable; only output values and explanations
  should change.

## Sprint 18 — Public Deployment and Scheduled Freshness

**Goal:** The app becomes publicly reachable and operationally trustworthy after the most obvious
recommendation-quality issues are fixed.

- Deploy the single-URL app publicly using the existing built-frontend + FastAPI shape.
- Add a **scheduled conditions refresh job** outside the search request path.
- Keep search read-only and fast:
  - stale data remains visible through provenance
  - no synchronous refresh during search
- Add minimal production observability:
  - app health/readiness
  - refresh success/failure
  - outbound booking click volume
- Keep persistence pragmatic:
  - SQLite on a persistent volume is acceptable if the deployment remains single-instance
  - defer Postgres unless hosting constraints make it necessary
- Produce a small production runbook:
  - deploy command/path
  - scheduled refresh job
  - manual refresh fallback
  - where to inspect freshness and failures
- Do not broaden the data model in this sprint; the goal is operationalization, not coverage work.

### Important interfaces / changes

- No major product-contract changes required.
- Runtime/deployment changes should support:
  - built frontend + API together
  - persistent DB path
  - scheduled `refresh_conditions`

## Sprint 19 — Historical Backfill and Selective Resort Expansion

**Goal:** Strengthen planning evidence so month-aware recommendations depend less on coarse
heuristics and can support broader coverage credibly.

- Add a **planning-focused historical weather backfill** to reduce dependence on the current
  heuristic:
  - backfill enough historical data to materially improve month-aware planning and edge-month
    realism
  - do not treat this as a full long-term warehouse project yet
- Add an internal/operator historical backfill path or extend the existing refresh tooling with a
  historical mode.
- Likely introduce a monthly aggregation path for planning use, but treat the final storage/read
  shape as an implementation decision rather than a roadmap promise.
- Use the backfill to improve:
  - month-level planning confidence
  - best-month selection
  - comparative “where/when to ski” output
- Add **selective** resort expansion only after calibration and backfill foundations are in place:
  - prioritize meaningful Alps coverage gaps first
  - do not expand resort count faster than the metadata can stay credible
  - do not commit to a target count in the roadmap unless each resort passes a credibility
    checklist
- Apply a validation checklist to each newly added resort before it enters the product:
  - verified coordinates
  - verified season dates
  - sane elevation data
  - real area naming
  - real rental/provider naming where included
- Keep public-facing SEO/content surfaces behind this work unless the improved planning outputs are
  already trustworthy enough to publish.

### Important interfaces / changes

- No major public API changes should be promised here.
- If historical planning evidence needs one new explainability field later, add it only when the
  implementation proves it is necessary.
- Keep the search contract stable wherever possible.

## Test Plan

### Sprint 17
- realism tests for late-season edge cases
- seed metadata sanity checks
- regression tests confirming sparse-history months become more conservative

### Sprint 18
- deployed smoke coverage for `/`, `/api/healthz`, `/api/readyz`, `/api/search`
- scheduled refresh verification
- stale-but-available search behavior verification

### Sprint 19
- backfill ingestion and monthly aggregation tests
- scenario comparisons before vs after backfill for edge-month planning
- validation checklist enforcement for every newly added resort

## Assumptions

- **Quality-first sequencing** is preferred over launch-first sequencing.
- `PROJECT.md` should remain **concise and roadmap-oriented**; it should not absorb the full
  tactical detail of this proposal.
- Sprint 17 should define the goal of fixing late-season realism, but the specific modeling
  mechanism should remain open until implementation review confirms the best approach.
- Resort expansion remains **selective and credibility-driven**, not a headline “add many resorts”
  commitment.

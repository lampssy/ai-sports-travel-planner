# Next 3 Sprints: 17–19

## Summary
The next three sprints should optimize for **launch + traction first**, not deeper companion complexity yet. The product already has a credible wedge: trust-first ski planning with booking handoff and a lightweight current-trip view. What it lacks now is a real operating loop: public availability, scheduled data freshness, and acquisition/booking feedback strong enough to learn from real usage.

The recommended sequence is:
- **Sprint 17:** go live and make the app operationally trustworthy
- **Sprint 18:** turn planning data into public acquisition surfaces
- **Sprint 19:** strengthen monetization and learning loops around booking handoff

## Sprint 17 — Live Deployment and Scheduled Freshness
- Execute the actual single-URL deployment using the existing deployment-ready shape.
- Add a **scheduled conditions refresh job** running outside the search request path.
- Keep search read-only and fast; stale data should remain visible through provenance rather than triggering synchronous refreshes.
- Add minimal production observability around:
  - refresh job success/failure
  - app health/readiness
  - outbound booking click volume
- Keep persistence pragmatic:
  - SQLite on a persistent volume is acceptable if the deployment remains single-instance
  - do not force a Postgres migration yet unless hosting constraints require it
- Add a small operator workflow for freshness:
  - one documented command for manual refresh
  - one scheduled production command/job
- Close the sprint with a real public URL and a short production runbook.

### Important interfaces / changes
- No major public product-contract change required.
- Infra/runtime changes should support:
  - built frontend + API together
  - scheduled `refresh_conditions`
  - persistent DB path
- Keep `/api/search`, `/api/current-trip`, and companion endpoints unchanged unless hosting exposes a concrete issue.

## Sprint 18 — Public Resort Pages and SEO Planning Surfaces
- Introduce **public resort landing pages** powered by the existing deterministic planning/provenance model.
- Use them as acquisition surfaces for queries like:
  - best time to ski `[resort]`
  - snow confidence for `[resort]`
  - best months for `[resort]`
- Reuse existing planning outputs rather than inventing a second content model.
- Each page should emphasize:
  - best travel months
  - current conditions freshness
  - planning confidence framing
  - clear estimated vs forecast distinctions
- Add basic SEO plumbing:
  - metadata
  - sitemap
  - stable page paths
- Keep this read-only and search-adjacent; do not turn it into a blog/content program yet.

### Important interfaces / changes
- Add public frontend page routes or a server-served equivalent for resort pages.
- Add a backend/page-data read model if needed for:
  - resort metadata
  - best months
  - current provenance
  - planning summary
- Avoid exposing raw internal history rows publicly.

## Sprint 19 — Booking Handoff Optimization and Product Learning Loop
- Improve the booking/referral path now that the app is live:
  - keep resort-level deep links as the floor
  - move to area-level handoff where data and provider URL behavior are reliable enough
- Add basic product analytics/reporting around:
  - search count
  - selected result CTR
  - booking CTA clicks
  - current-trip saves
- Add a lightweight feedback loop in-product or operator-side to learn from usage:
  - which resorts are being selected
  - where users drop before booking
  - whether travel-month usage correlates with booking clicks
- Keep the trip model provider-agnostic.
- Do **not** add accommodation-preference filters yet unless the data model is ready to support them credibly.

### Important interfaces / changes
- Outbound redirect API can stay stable while link generation becomes more specific behind it.
- Add internal analytics/event reporting surfaces, but keep the user-facing API narrow.
- If needed, extend tracked click metadata rather than changing the search result contract.

## Test Plan
- **Sprint 17**
  - smoke-test deployed app: `/`, `/api/healthz`, `/api/readyz`, `/api/search`
  - verify scheduled refresh updates `updated_at` and snapshot history
  - verify stale-but-available search behavior when refresh is delayed
- **Sprint 18**
  - page-data tests for resort pages
  - browser smoke for public resort page load and search handoff from a resort page
  - provenance/SEO assertions where feasible
- **Sprint 19**
  - backend tests for deeper booking link generation and tracked events
  - scenario coverage: search -> select result -> booking CTA -> tracked click
  - analytics/reporting validation for the new events

## Assumptions
- **Europe/Alps-first** remains the operating default.
- Resort dataset expansion continues as a background track, not as a headline sprint.
- Postgres is deferred unless deployment/platform constraints force it.
- The next 3 sprints optimize for **real usage and learning**, not bigger AI orchestration or a richer assistant.
- LangGraph remains deferred; it still does not belong on the immediate roadmap.

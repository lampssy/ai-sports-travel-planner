# Sprints 17–19: Claude Proposal

## Context

After Sprint 16 the product has: trust-visible conditions, resort-level booking handoff, a trip-context
model, and a basic current-trip companion view. The deployment infra is ready but the app is not yet
publicly hosted. The resort dataset sits at 23 curated resorts with no historical backfill.

The next pressure points are:
- The product isn't publicly accessible yet — everything built is invisible to real users
- 23 resorts is thin; notable geography gaps (Dolomites, Pyrenees, Scandinavia, NA)
- No historical conditions data to back the planning/calendar feature with real evidence
- Accommodation preferences (full board, sauna, etc.) are a real user pain point with no coverage yet
- SEO acquisition hasn't started — public pages need to be indexed before the October planning season

---

## Sprint 17 — Deploy + Resort Dataset Expansion

**Goal:** The product has a real URL and enough resort coverage to be non-embarrassing to share.

- Provision Fly.io: app, secrets, persistent volume, custom domain
- Confirm end-to-end live flow: trip brief → search → booking CTA → outbound redirect
- Expand resort dataset from 23 to 40–50 resorts:
  - Fill main gaps: Dolomites (Cortina, Alta Badia), Pyrenees (Font Romeu, Grandvalira), Scandinavia
    (Åre, Trysil), 2–3 more NA resorts (Whistler, Banff, Park City)
  - Manual curation only — no LLM-generated resort facts
- Backfill 6–12 months of Open-Meteo historical snapshots per resort to seed the conditions calendar
  with real data rather than heuristics

**Why this first:** Everything built since Sprint 11 is deployable. The dataset expansion makes the
product credible enough to share. Both tasks are blocking the sprints that follow.

---

## Sprint 18 — Accommodation Preference Filters

**Goal:** Make hotel search genuinely useful and differentiated from ChatGPT wrappers.

The booking handoff layer exists (Sprint 15) and the resort data is expanding (Sprint 17). This is the
right moment for accommodation filters — not before, because the data wasn't there.

- Add filter dimensions to the area/accommodation schema:
  - board type: full board / half board / B&B / self-catering
  - wellness: sauna, spa, jacuzzi (as tags)
  - practical: ski bus available, ski-in/ski-out
- Manually curate these attributes for the expanded dataset
- Surface relevant filters in the UI dynamically — show only the subset that matches what the user
  typed in the query box (inferred from NL parse output); start with a fixed relevant subset
- Encode preference filters into Booking.com deep link params so the CTA lands pre-filtered
- Extend the NL parser to extract accommodation preferences from trip briefs
  ("I want full board with a sauna", "needs to have ski bus")

**Note on dynamic filter pool:** The intent is a large pool of filter dimensions, with only a relevant
subset shown in the UI per query. This sprint introduces the first 5–6 dimensions. The pattern scales
as the dataset grows — see `engineering-notes.md` for the full design rationale.

**Why this sprint:** Structured accommodation preference matching is the clearest differentiator vs.
generic AI travel planners. A "sauna + full board near Verbier" deep link that actually works is
something no ChatGPT wrapper produces.

---

## Sprint 19 — SEO Content Layer + Conditions Calendar Public Pages

**Goal:** Start the organic acquisition loop before the October planning season.

After Sprint 17's backfill, the conditions calendar has real historical data. This sprint makes it
publicly discoverable.

- Public resort pages (`/resort/chamonix`, `/resort/verbier`) with:
  - best months to ski (from snapshot history)
  - current conditions + freshness timestamp
  - planning confidence framing
  - clear forecast vs reported vs estimated labelling
- "Best resorts for [month]" landing pages (`/best-resorts/february`)
- Basic SEO plumbing: meta tags, structured data, sitemap
- Pages reuse existing deterministic planning output — no second content model

**Timing constraint:** Pages need to be indexed by September to have any SEO benefit before the
October–November planning season. Sprint 19 should ship by August at the latest.

**Why last:** Depends on both the expanded dataset (Sprint 17) and credible historical data backing
the planning summaries. Thin data makes these pages weak; rich data makes them a genuine acquisition
asset.

---

## What this plan does not include

- Native mobile app / Flutter — Stage 3, not yet
- Push notifications — needs mobile infrastructure first
- Full property-level accommodation recommender — deferred until area data is richer
- LangGraph / multi-step AI orchestration — no clear product need yet
- Social/group features — Stage 4

---

## Seasonal fit

| Period | Sprint | Status |
|---|---|---|
| April–May 2026 | Sprint 17: Deploy + dataset | On track |
| June–July 2026 | Sprint 18: Accommodation filters | Off-season, good time to build |
| August 2026 | Sprint 19: SEO pages | Must ship before September |
| September 2026 | Soft launch in ski communities | Reddit, ski clubs, Product Hunt |
| October 2026 | Planning season begins | First real user traffic |

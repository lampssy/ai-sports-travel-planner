# Portfolio and Career Plan

Notes on using this project as a learning vehicle and resume asset, alongside the longer-term
business goals. Written April 2026.

---

## Context

This project serves two parallel goals:
1. **Near-term (3–6 months):** A strong portfolio piece and resume asset for AI/backend engineering roles
2. **Long-term:** A real product with a viable business model (documented in `docs/strategy.md`)

Both goals are compatible and reinforce each other. The business picture keeps product decisions grounded.
The near-term goal forces deployment and real-world quality that a purely theoretical project would not.

---

## What Makes This Strong as a Portfolio Piece

The project already demonstrates:

- **LLM integration with discipline** — the AI is a thin interpretation layer over deterministic logic,
  not a black box. Results are predictable and testable. This is exactly what senior engineers want to see.
- **Real external data integration** — Open-Meteo conditions pipeline, staleness handling, fallback behaviour
- **Production-quality backend patterns** — FastAPI, typed Pydantic models, repository pattern, SQLite/Postgres
- **Testing discipline** — unit tests, mocked LLM calls, repository-level tests, CI with GitHub Actions
- **Product thinking** — the roadmap, stage sequencing, and architectural decisions show engineering judgement
  beyond just writing code

**What it is still missing for a complete portfolio piece: a live public URL.**

---

## The Interview Story (Use This Now)

Even before deployment, the project is already interviewable. A strong 2-minute summary:

> "I'm building a conditions-smart ski trip planner. It takes a free-text trip brief, uses an LLM to
> extract structured filters, runs deterministic ranking against a curated resort database with real
> weather signals from Open-Meteo, and generates a grounded recommendation narrative. The backend is
> FastAPI with SQLite moving to Postgres in production. I've kept AI as a thin interpretation layer
> over deterministic logic so results are predictable and testable, with full fallback behaviour when
> the LLM is unavailable."

This hits: LLM integration, external APIs, database design, testing discipline, product thinking.
Sufficient for an AI/backend engineer role at mid-to-senior level.

Expand with specifics depending on the interview focus:
- **AI depth:** "The parser uses Gemini with structured output and confidence scoring. I cache both
  parser and narrative outputs to control latency and cost. The LLM never decides ranking."
- **Backend depth:** "The repository layer abstracts SQLite from domain logic. Conditions refresh
  runs as a separate command with configurable staleness thresholds and degraded-mode fallbacks."
- **Product depth:** "I deliberately sequenced features to avoid building personalization before
  having real user history data. The AI layer can only narrate what the deterministic layer already decided."

---

## Revised Sprint Priorities

Original sprints 11–13 are good features but defer deployment too long. Resequenced for the portfolio goal:

### Sprint 11 — Deployment-ready launch prep
**Goal:** A launch-ready app that can be hosted and shared as soon as the timing makes sense for the CV/portfolio push.

What this involves:
- Choose a hosting stack: **Fly.io or Railway** for FastAPI + Postgres (free tier available), **Vercel** for React frontend
- Environment config: secrets management, `.env` handling in production
- Database migration: SQLite → Postgres (or keep SQLite on Fly.io volume for first deploy)
- CI/CD: connect GitHub Actions to auto-deploy on merge to main
- Domain: a simple custom domain lifts the impression significantly (e.g. `snowmatch.app` or similar)

Why this sprint first:
- Forces you to solve real production problems (the most valuable learning for the resume goal)
- Makes the product easy to host the moment you want to start sharing it
- A deployed product with a real URL still reads completely differently to a GitHub repo on a CV, but the actual hosting step can wait until the app is about to be shown

Estimated cost: €0–15/month on free tiers.

### Sprint 12 — One working affiliate booking link
**Goal:** A single end-to-end booking referral that earns real (if tiny) revenue.

What this involves:
- Sign up for the Booking.com Affiliate Partner Program
- Generate a deep-link to the resort's area for each search result
- Track clicks (simple event logging is sufficient)
- Display as a "Book accommodation" CTA on the result card

Why this matters for the portfolio:
- "Monetized product with affiliate integration" is a resume line that signals product thinking
- The implementation is a 2–3 day task, not a full sprint — pair it with deployment hardening
- Gives you a concrete talking point: "I integrated an affiliate API and tracked conversions through
  the recommendation flow"

### Sprint 13 — Time-aware planning + conditions calendar
**Goal:** The technically impressive AI feature, now grounded in real usage data.

What this involves (as originally planned):
- Travel window input → conditions confidence for that window
- Historical Open-Meteo data backfilled per resort
- "Best resorts for this window" and "best windows for this resort" comparative views
- NL parser extended to extract timing intent

Why this is sprint 13, not 11:
- By this point the product is live and you may have early user feedback
- The conditions calendar doubles as an SEO content asset (indexed pages per resort)
- The feature story is stronger in interviews when you can say "users were asking for this"

---

## Seasonal Timeline

Ski season and planning behaviour are highly seasonal. Plan around it:

| Period | What's Happening | What to Do |
|---|---|---|
| **April–May 2026** | End of ski season, off-season begins | Deploy Sprint 11, get live URL |
| **June–August 2026** | Full off-season, low organic interest | Sprint 12–13, harden product, add content |
| **September 2026** | Pre-season buzz starts | Soft launch: share in ski communities, Reddit, ski clubs |
| **October 2026** | Planning season begins in earnest | Active user acquisition, first affiliate conversions |
| **Nov–Dec 2026** | Peak planning season | Real usage data, iterate on weak points |
| **Jan–Mar 2027** | Active ski season | Stage 3 (trip companion) development informed by real users |

**Key insight:** You have ~5 months of off-season to get to a solid deployed state before the season
matters. This is enough time if deployment is prioritised now.

---

## What to Put on Your Resume/LinkedIn

Once Sprint 11 is complete, update your profile with:

**Project entry:**
> **AI Ski Trip Planner** | [live URL] | FastAPI · Python · Gemini API · SQLite/PostgreSQL · React
>
> Conditions-aware ski resort recommendation engine. LLM-backed query parsing converts free-text trip
> briefs into structured filters; deterministic ranking engine scores resorts against real-time weather
> data from Open-Meteo; grounded narrative layer explains recommendations in natural language. Deployed
> on [Fly.io/Railway] with CI/CD via GitHub Actions.

**Skills demonstrated (for AI/backend roles):**
- LLM integration (Gemini API, structured output, caching, fallback handling)
- External API integration with staleness handling and degraded-mode behavior
- FastAPI, Pydantic, repository pattern, SQLite/PostgreSQL
- Testing: Pytest, mocked LLM calls, CI pipeline
- End-to-end product ownership: data pipeline, backend, frontend, deployment, monetization

---

## Learning Goals This Project Covers

Track these explicitly — they are the "AI/backend engineer" skills being developed:

- [x] LLM API integration (Gemini) with structured output
- [x] Prompt engineering with testable, grounded outputs
- [x] External data pipeline (Open-Meteo integration, refresh, staleness)
- [x] Repository pattern and database abstraction
- [x] FastAPI: routing, Pydantic models, dependency injection patterns
- [x] Testing strategy: unit, integration, mocked external dependencies
- [ ] Production deployment: hosting, secrets management, CI/CD to prod
- [ ] Postgres in production
- [ ] Affiliate API integration
- [ ] Mobile client (Flutter) — Stage 3
- [ ] Push notification pipeline — Stage 3

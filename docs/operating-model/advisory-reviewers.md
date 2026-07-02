# Snowcast Advisory Reviewers

This document is the source of truth for Snowcast's advisory reviewer system.
Reviewers are bounded review contracts, not personalities. They help a solo
builder apply focused expert scrutiny without turning normal development into
process overhead.

## Principles

- Advisory review is manual by default and automation-ready by design.
- Repo docs are the source of truth; skills and workflow prompts must point back
  here instead of duplicating reviewer definitions.
- Reviewers do not edit code unless the user explicitly asks for implementation.
- `feature-review` is the default mode for concrete diffs or changes.
- Broad `domain-audit` work is opt-in only.
- When routing is ambiguous, prefer invoking the smallest relevant reviewer set
  over skipping advisory review.
- For normal development, only Blocker and High findings stop the change by
  default.
- Reviewers should not manufacture findings. If there are no defensible issues,
  say so clearly.
- In `design-review`, check related ADRs and `docs/domain-language.md` when a
  proposal changes durable architecture decisions, domain terms, bounded
  contexts, or invariants.
- In `design-review`, check Developer Decision Checkpoints from the feature spec
  or proposal. Flag material technical, product/domain, or mixed choices that
  were silently decided instead of owner-reviewed.

## Modes

### `feature-review`

Default mode for a concrete change, diff, PR, branch, or sprint deliverable.

Use this mode to:

- inspect the actual changed behavior
- find concrete bugs, regressions, missing verification, and domain risks
- stay scoped to the requested change

Avoid broad roadmap advice unless the change directly creates that risk.

### `design-review`

Pre-implementation review of a feature spec, proposal, design doc,
implementation plan, or feature concept.

Use this mode to:

- test whether the design fits Snowcast's architecture and product direction
- identify missing requirements, weak assumptions, and sequencing risks
- identify missing, unresolved, or over-collapsed Developer Decision Checkpoints
- recommend focused verification before coding begins

Missing owner decision checkpoints are usually **Medium** findings. Raise the
severity when the hidden choice affects safety, privacy, user trust, ranking,
source integrity, API compatibility, deploy reliability, or a durable
architecture boundary.

### `domain-audit`

Broad project advice from one domain.

Use this mode to:

- inspect current product/docs/implementation from that domain's perspective
- summarize strengths, gaps, and opportunities
- propose prioritized next actions

Do not run domain audits automatically during implementation flows.

## Severity Model

- **Blocker**: likely user-visible breakage, unsafe behavior, broken contract,
  data trust violation, secret/privacy risk, or deploy failure.
- **High**: serious regression risk or missing verification on a critical path.
- **Medium**: meaningful maintainability, UX, observability, or correctness
  concern.
- **Low**: polish, clarity, or follow-up improvement.

Default solo-builder gate:

```text
Only Blocker and High findings stop the change by default.
Medium and Low findings become backlog or follow-up unless the user decides
otherwise.
```

## Output Formats

### Feature and Design Review

```markdown
## <Reviewer Name> Review

Mode:
Scope reviewed:
Evidence inspected:
Assumptions / limits:

Findings:
- [Blocker] Describe blocking issue with file evidence and expected impact.
- [High] Describe serious risk with file evidence and required fix.
- [Medium] Describe meaningful concern and recommended follow-up.
- [Low] Describe polish or clarity issue.

Missing checks:

Recommendation:
- Ship / ship after fixes / do not ship yet
```

If there are no defensible findings:

```markdown
## <Reviewer Name> Review

Mode:
Scope reviewed:
Evidence inspected:
Assumptions / limits:

No defensible findings.

Main residual risks:
- Describe the remaining risk or test gap.

Recommendation:
- Ship / ship after fixes / do not ship yet
```

### Domain Audit

```markdown
## <Reviewer Name> Audit

Scope reviewed:
Current strengths:
Risks / gaps:
Top opportunities:
Suggested next actions:
```

## Core Reviewers

### Product / Strategy

**Slug:** `product-strategy`

**Purpose:** Check whether the work supports Snowcast as a ski-only,
conditions-smart planning product rather than drifting into generic travel,
generic AI chat, or unsupported marketplace polish.

**Invoke for:**

- sprint proposals
- product-facing features
- public copy or positioning changes
- workflow changes that alter what Snowcast appears to be
- broad roadmap/domain-audit questions

**Inspect first:**

- `PROJECT.md`
- `docs/product-backlog.md`
- `docs/strategy.md`
- `docs/engineering-notes.md`
- relevant UI/API behavior

**Questions to answer:**

- Does this reinforce ski-only, conditions-aware planning?
- Does it preserve trusted decision support under uncertainty?
- Does it avoid generic itinerary/chat/marketplace drift?
- Does the feature match the product maturity and current data quality?
- Does it support the discovery -> booking handoff -> companion sequence?

**Blocking conditions:**

- The change makes unsupported claims about resort, hotel, snow, or provider data.
- The change turns Snowcast into generic travel planning without a deliberate
  product decision.
- The change hides uncertainty that users need for booking decisions.

### Backend / API

**Slug:** `backend-api`

**Purpose:** Review API contracts, FastAPI boundaries, domain/service
separation, error handling, persistence behavior, and client reliability.

**Invoke for:**

- API request/response changes
- domain model changes
- repository/database behavior changes
- backend performance or error-handling changes
- any change consumed by web or mobile clients

**Inspect first:**

- `app/api/`
- `app/domain/`
- `app/data/repositories.py`
- `tests/test_api.py`
- `tests/test_services.py`
- `tests/test_repository.py`
- `frontend/src/types.ts`
- `mobile/lib/` when mobile behavior is involved

**Questions to answer:**

- Is the API contract backward-compatible or intentionally migrated?
- Are domain logic, AI logic, and integrations still separated?
- Are errors explicit and testable?
- Can web/mobile clients rely on the response shape?
- Are persistence reads/writes scoped and predictable?

**Blocking conditions:**

- Broken API compatibility without a deliberate migration path.
- Domain logic moved into AI, integration, or presentation layers.
- Unhandled errors on critical endpoints.
- Missing tests for critical API or transformation behavior.

### Data Trust & Source Integrity

**Slug:** `data-trust-source-integrity`

**Purpose:** Review normalized catalog truth, source refs, curation reports,
trust-manifest changes, planning semantics, and whether user-facing claims are
backed by evidence.

**Invoke for:**

- `app/data/catalog.json`
- `app/data/resort_trust_manifest.json`
- `docs/catalog-curation/`
- planning/ranking evidence changes
- public snow/weather/source wording
- source-backed catalog proposals

**Inspect first:**

- `docs/data-trust-model.md`
- `docs/planning-model.md`
- `app/data/catalog.json`
- `app/data/resort_trust_manifest.json`
- `app/data/catalog_curation.py`
- `tests/test_catalog_models.py`
- `tests/test_catalog_trust.py`

**Questions to answer:**

- Are verified fields backed by real source refs?
- Are estimated values labeled honestly?
- Does curation remain review-gated where source quality is weak?
- Are ski-region, stay-destination, ski-area, access, and stay-base concepts
  kept distinct?
- Does the UI/API avoid presenting weather-derived disruption as official lift
  status?

**Blocking conditions:**

- Source-backed trust statuses without source refs.
- LLM-generated facts promoted as catalog truth without review.
- User-facing copy presenting estimates as verified facts.
- Changes that make planning/ranking semantics contradict
  `docs/planning-model.md`.

### UI / UX

**Slug:** `ui-ux`

**Purpose:** Review the web planning experience, recommendation hierarchy,
current-trip surface, state visibility, trust cues, and whether UI polish matches
real product maturity.

**Invoke for:**

- `frontend/src/` changes
- routeable web app changes
- selected-result detail/dossier changes
- forms, chips, drawers, empty states, and current-trip UI
- product-facing copy that affects user decisions

**Inspect first:**

- `frontend/src/`
- `frontend/tests/e2e/`
- `docs/ui-concepts/`
- `docs/strategy.md`
- backend fields consumed by the UI

**Questions to answer:**

- Can users see the structured state behind AI-assisted planning?
- Is Ski region -> stay destination/base -> selected ski area hierarchy clear?
- Are evidence quality and uncertainty visible without becoming debug output?
- Does the UI avoid fake marketplace completeness?
- Does the interaction work on expected desktop/mobile viewport widths?

**Blocking conditions:**

- Users cannot understand or control important applied filters.
- UI presents unsupported hotel/provider/resort facts as real inventory.
- Trust/risk cues are hidden or semantically misleading.
- Critical flows are inaccessible or broken at common viewport sizes.

### Security & Privacy

**Slug:** `security-privacy`

**Purpose:** Review auth, tokens, sessions, user trip data, public endpoints,
logs, secrets, privacy-sensitive telemetry, and accidental data exposure.

**Invoke for:**

- auth/session/user identity changes
- current-trip or user data persistence
- logging/observability changes
- public endpoint changes
- deploy/CI secret handling
- LLM prompt/response handling that may include user text

**Inspect first:**

- `app/auth/`
- authenticated API routes in `app/api/`
- trip-context persistence in `app/data/repositories.py`
- logging/observability docs and code
- `.github/workflows/`
- `docs/production-runbook.md`
- `.env.example`

**Questions to answer:**

- Are tokens and secrets excluded from logs and responses?
- Are user-owned resources scoped to authenticated users?
- Do public endpoints expose only intended information?
- Is telemetry sanitized and low-risk?
- Are deploy secrets documented without being committed?

**Blocking conditions:**

- Secret/token leakage in code, docs, logs, or telemetry.
- User trip data accessible across users.
- Auth bypass or ambiguous ownership checks.
- Raw LLM prompts/responses or free-text trip briefs logged by default.

### Observability / Ops

**Slug:** `observability-ops`

**Purpose:** Review deployability, runbook impact, health/readiness behavior,
scheduled jobs, logs/metrics/traces, refresh visibility, and operational failure
modes.

**Invoke for:**

- deploy, CI/CD, Fly, Docker, or config changes
- health/readiness behavior
- scheduled refresh/backfill/acquisition jobs
- observability/logging/telemetry implementation
- performance-sensitive backend paths

**Inspect first:**

- `docs/production-runbook.md`
- `docs/observability-plan.md`
- `.github/workflows/`
- `fly.toml`
- `Dockerfile`
- health/readiness routes
- refresh/backfill commands under `app/data/`

**Questions to answer:**

- Can an operator detect and diagnose likely production failures?
- Are health/readiness checks aligned with runtime dependencies?
- Are scheduled jobs observable and safely retryable?
- Does the runbook need an update?
- Are metrics/log labels low-cardinality and privacy-safe?

**Blocking conditions:**

- Deploy/release can fail silently or cannot be diagnosed.
- Readiness reports healthy when required dependencies are unavailable.
- Scheduled data freshness can fail without a visible signal.
- Operational docs contradict implemented behavior.

## Triggered Specialists

### AI / LLM Reliability

**Slug:** `ai-llm-reliability`

**Purpose:** Review parser prompts, LLM fallback, cache, schema validation, and
request-path model behavior.

**Invoke for:**

- `app/ai/` changes
- parser tests
- prompt or schema validation changes
- cache, fallback, cost, or latency behavior

**Inspect first:**

- `app/ai/`
- `tests/test_parser.py`
- API behavior that exposes parser output

**Questions to answer:**

- Are LLM calls isolated from deterministic planning and data-fetching logic?
- Are prompt outputs schema-validated and handled on failure?
- Does fallback preserve critical flows without hiding uncertainty?
- Are LLM-generated facts blocked from catalog truth unless reviewed?
- Are cost, latency, and cache behavior bounded for the request path?

**Blocking conditions:**

- LLM controls ranking directly without review.
- Hallucinated facts become user-facing truth.
- Fallback failure breaks critical flows.
- Tests assert exact LLM prose instead of structure.

### Mobile Companion

**Slug:** `mobile-companion`

**Purpose:** Review Flutter, authenticated mobile flows, saved-trip behavior,
exact-date companion logic, device registration, and push-readiness.

**Invoke for:**

- `mobile/lib/` changes
- `mobile/test/` changes
- auth or session exchange
- current-trip endpoints
- companion events
- device registration or push-related models

**Inspect first:**

- `mobile/lib/`
- `mobile/test/`
- current-trip API routes in `app/api/`
- auth/session exchange code
- device registration and companion event persistence

**Questions to answer:**

- Are mobile auth and session flows aligned with backend ownership checks?
- Can saved and current trips only be read or changed by the owning user?
- Does exact-date trip state drive companion relevance where needed?
- Are device registration and push-readiness semantics server-backed enough?
- Do mobile states handle loading, empty, and error conditions clearly?

**Blocking conditions:**

- Mobile can save or read another user's trip.
- Exact-date trip state is ignored where companion relevance depends on it.
- Device registration semantics become client-only.

### Performance

**Slug:** `performance`

**Purpose:** Review latency, database query shape, frontend runtime risk,
provider calls, LLM cost, and cache-sensitive code.

**Invoke for:**

- search request path changes
- repository query changes
- frontend bundle or runtime changes
- provider or LLM loops
- cache policy changes

**Inspect first:**

- `app/api/routes.py`
- `app/domain/`
- `app/data/repositories.py`
- `app/integrations/`
- `app/ai/`
- `frontend/src/`
- `docs/superpowers/plans/2026-06-11-search-performance.md`
- relevant backend, frontend, or parser tests

**Questions to answer:**

- Does the change add request-path loops, remote calls, or DB round trips?
- Are expensive provider or LLM calls cached, bounded, or moved out of the path?
- Is repository query shape predictable for expected catalog size?
- Does frontend runtime work scale with displayed results rather than raw data?
- Is there measurement or focused testing for performance-sensitive behavior?

**Blocking conditions:**

- Critical paths add unbounded loops, remote calls, or DB round trips without
  tests or measurement.
- Expensive LLM or provider calls run repeatedly without caching or limits.
- A known performance budget is violated without a deliberate product tradeoff.

### Growth / SEO

**Slug:** `growth-seo`

**Purpose:** Review public pages, sitemap/robots, public copy, demo/share
surfaces, and conversion paths.

**Invoke for:**

- `/ski-resorts/{resort_id}`
- sitemap or robots changes
- public page copy
- booking CTA changes
- public share or demo surfaces

**Inspect first:**

- `frontend/src/`
- `app/api/routes.py`
- `tests/test_public_pages.py`
- `docs/strategy.md`
- catalog and trust fields displayed on public pages
- sitemap or robots files when present

**Questions to answer:**

- Are public claims backed by catalog/trust evidence?
- Do public routes render and remain crawlable where intended?
- Are titles, copy, and CTAs specific to Snowcast's ski-planning value?
- Do booking CTAs avoid implying unsupported provider coverage?
- Does public copy avoid generic travel-planner drift?

**Blocking conditions:**

- Public pages expose stale or false claims.
- Sitemap routes break.
- Conversion CTAs imply unsupported provider coverage.

### Release / Change Management

**Slug:** `release-change-management`

**Purpose:** Review deploy order, migration risk, rollback, config changes, CI,
and production cutover.

**Invoke for:**

- migrations
- deploy workflows
- production config
- release commands
- broad dependency or infrastructure changes

**Inspect first:**

- `.github/workflows/`
- `Dockerfile`
- `fly.toml`
- `docs/production-runbook.md`
- `.env.example`
- migration or seed-data scripts when present

**Questions to answer:**

- Is there a safe deploy order for app, schema, config, and data changes?
- Is rollback possible without corrupting or orphaning user/catalog data?
- Are new production config values documented without exposing secrets?
- Do CI and deploy workflows exercise the changed runtime path?
- Does the runbook reflect any changed operational steps?

**Blocking conditions:**

- No safe deploy order for required schema or app changes.
- Rollback would corrupt data.
- Production secrets or config changes are unclear.

### Accessibility

**Slug:** `accessibility`

**Purpose:** Review forms, routes, modals/drawers, navigation, color, focus,
keyboard use, labels, and screen-reader semantics.

**Invoke for:**

- meaningful UI changes
- routeable pages
- modals or drawers
- forms and chips
- interactive cards
- color-system changes

**Inspect first:**

- `frontend/src/`
- `frontend/tests/e2e/`
- `frontend/src/App.test.tsx`
- UI copy and state components under `frontend/src/ui/`
- rendered behavior for affected viewports when practical

**Questions to answer:**

- Are critical actions reachable by keyboard?
- Are form controls, chips, and interactive cards named clearly?
- Does focus move predictably through modals, drawers, and route changes?
- Is risk or status information conveyed without relying only on color?
- Does responsive layout preserve labels and controls at expected widths?

**Blocking conditions:**

- Critical actions are mouse-only.
- Focus is trapped or lost.
- Form controls lack labels.
- Risk or status information relies only on color.

### Monetization / Partnerships

**Slug:** `monetization-partnerships`

**Purpose:** Review booking handoff, affiliate assumptions, provider
abstraction, attribution, rental/lift-pass integrations, and revenue-facing
copy.

**Invoke for:**

- booking redirects
- affiliate or provider integration
- accommodation copy
- rental or lift-pass referral ideas
- monetization roadmap decisions

**Inspect first:**

- `docs/strategy.md`
- `docs/planning-model.md`
- booking CTA and handoff UI under `frontend/src/`
- provider or integration code under `app/integrations/`
- trip and recommendation models under `app/domain/`

**Questions to answer:**

- Does the handoff preserve Snowcast as decision support rather than inventory?
- Are provider claims and attribution accurate?
- Do provider-specific fields stay out of core trip models unless deliberate?
- Does revenue copy avoid promising unsupported booking capabilities?
- Is the booking handoff sequence compatible with discovery-first planning?

**Blocking conditions:**

- Provider-specific assumptions leak into core trip models.
- Attribution is misleading.
- Revenue copy promises unsupported booking capabilities.

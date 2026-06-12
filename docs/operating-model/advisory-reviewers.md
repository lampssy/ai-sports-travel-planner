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
- For normal development, only Blocker and High findings stop the change by
  default.
- Reviewers should not manufacture findings. If there are no defensible issues,
  say so clearly.

## Modes

### `feature-review`

Default mode for a concrete change, diff, PR, branch, or sprint deliverable.

Use this mode to:

- inspect the actual changed behavior
- find concrete bugs, regressions, missing verification, and domain risks
- stay scoped to the requested change

Avoid broad roadmap advice unless the change directly creates that risk.

### `design-review`

Pre-implementation review of a proposal, design doc, implementation plan, or
feature concept.

Use this mode to:

- test whether the design fits Snowcast's architecture and product direction
- identify missing requirements, weak assumptions, and sequencing risks
- recommend focused verification before coding begins

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

No blocking findings.

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

**Purpose:** Review catalog truth, source refs, acquisition artifacts, trust
manifest changes, planning semantics, and whether user-facing claims are backed
by evidence.

**Invoke for:**

- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`
- `app/data/resort_acquisition/`
- planning/ranking evidence changes
- public snow/weather/source wording
- source-backed catalog proposals

**Inspect first:**

- `docs/data-trust-model.md`
- `docs/planning-model.md`
- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`
- `app/data/resort_acquisition/`
- `tests/test_catalog_validation.py`
- `tests/test_resort_acquisition.py`

**Questions to answer:**

- Are verified fields backed by real source refs?
- Are estimated values labeled honestly?
- Does acquisition remain review-only where source quality is weak?
- Are destination, ski-area, and stay-base concepts kept distinct?
- Does the UI/API avoid presenting weather-derived disruption as official lift
  status?

**Blocking conditions:**

- Source-backed trust statuses without source refs.
- LLM-generated facts promoted as catalog truth without review.
- User-facing copy presenting estimates as verified facts.
- Changes that make planning/ranking semantics contradict
  `docs/planning-model.md`.

### UI / UX

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
- Is Destination -> Ski area -> Stay base hierarchy clear?
- Are evidence quality and uncertainty visible without becoming debug output?
- Does the UI avoid fake marketplace completeness?
- Does the interaction work on expected desktop/mobile viewport widths?

**Blocking conditions:**

- Users cannot understand or control important applied filters.
- UI presents unsupported hotel/provider/resort facts as real inventory.
- Trust/risk cues are hidden or semantically misleading.
- Critical flows are inaccessible or broken at common viewport sizes.

### Security & Privacy

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

**Purpose:** Review parser, narrative, prompt, LLM fallback, cache, schema
validation, and LLM-assisted acquisition behavior.

**Invoke for:** `app/ai/`, parser/narrative tests, LLM extraction, prompt
changes, schema validation, cache/fallback logic, LLM cost/latency behavior.

**Inspect first:** `app/ai/`, `tests/test_parser.py`, `tests/test_narrative.py`,
LLM-related acquisition modules, parser API behavior, prompt/schema boundaries.

**Blocking conditions:** LLM controls ranking directly without review,
hallucinated facts become user-facing truth, fallback failure breaks critical
flows, or tests assert exact LLM prose instead of structure.

### Mobile Companion

**Purpose:** Review Flutter, authenticated mobile flows, saved-trip behavior,
exact-date companion logic, device registration, and push-readiness.

**Invoke for:** `mobile/lib/`, `mobile/test/`, auth/session exchange,
current-trip endpoints, companion events, device registration, push-related
models.

**Inspect first:** `mobile/lib/`, `mobile/test/`, current-trip API routes,
auth/session exchange, device registration and companion event persistence.

**Blocking conditions:** mobile can save/read another user's trip, exact-date
trip state is ignored where companion relevance depends on it, or device
registration semantics become client-only.

### Performance

**Purpose:** Review latency, database query shape, frontend runtime risk,
provider calls, LLM cost, and cache-sensitive code.

**Invoke for:** search request path changes, repository query changes, frontend
bundle/runtime changes, provider/LLM loops, cache policy changes.

**Blocking conditions:** critical paths add unbounded loops, remote calls, or DB
round trips without tests or measurement.

### Growth / SEO

**Purpose:** Review public pages, sitemap/robots, public copy, demo/share
surfaces, and conversion paths.

**Invoke for:** `/ski-resorts/{resort_id}`, sitemap/robots, public page copy,
booking CTA, public share/demo surfaces.

**Blocking conditions:** public pages expose stale/false claims, sitemap routes
break, or conversion CTAs imply unsupported provider coverage.

### Release / Change Management

**Purpose:** Review deploy order, migration risk, rollback, config changes, CI,
and production cutover.

**Invoke for:** migrations, deploy workflows, production config, release
commands, broad dependency or infrastructure changes.

**Blocking conditions:** no safe deploy order for required schema/app changes,
rollback would corrupt data, or production secrets/config changes are unclear.

### Accessibility

**Purpose:** Review forms, routes, modals/drawers, navigation, color, focus,
keyboard use, labels, and screen-reader semantics.

**Invoke for:** meaningful UI changes, routeable pages, modals/drawers, forms,
chips, interactive cards, color-system changes.

**Blocking conditions:** critical actions are mouse-only, focus is trapped or
lost, form controls lack labels, or risk/status information relies only on
color.

### Monetization / Partnerships

**Purpose:** Review booking handoff, affiliate assumptions, provider
abstraction, attribution, rental/lift-pass integrations, and revenue-facing
copy.

**Invoke for:** booking redirects, affiliate/provider integration, accommodation
copy, rental/lift-pass referral ideas, monetization roadmap decisions.

**Blocking conditions:** provider-specific assumptions leak into core trip
models, attribution is misleading, or revenue copy promises unsupported booking
capabilities.

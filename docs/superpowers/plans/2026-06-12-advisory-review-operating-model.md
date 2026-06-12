# Snowcast Advisory Review Operating Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved manual-but-automation-ready advisory reviewer system for Snowcast.

**Architecture:** Keep reviewer definitions in repo docs as the source of truth, then create one thin Codex skill that reads those docs and routes review requests. `AGENTS.md` only gets lightweight trigger guidance so normal development and Superpowers flows know when to invoke advisory review without duplicating reviewer contracts.

**Tech Stack:** Markdown project docs, Codex skill format, `agents/openai.yaml`, shell validation, existing repo conventions.

---

## Scope

This implementation creates:

- `docs/operating-model/advisory-reviewers.md`
- `docs/operating-model/review-playbook.md`
- an advisory routing section in `AGENTS.md`
- `/Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md`
- `/Users/awownysz/.codex/skills/snowcast-advisory-review/agents/openai.yaml`

This implementation does not create autonomous implementation agents, CI jobs,
or automated PR checks. It only creates the manual reviewer system and makes the
shape automation-ready.

## File Structure

### Repo Docs

`docs/operating-model/advisory-reviewers.md`

- source of truth for reviewer contracts
- shared modes and severity model
- core and triggered reviewer definitions
- required output formats
- reviewer-specific evidence paths and blocking conditions

`docs/operating-model/review-playbook.md`

- practical routing guide
- change-type to reviewer mapping
- Superpowers integration guidance
- invocation examples
- dry-run expectations

`AGENTS.md`

- short trigger policy only
- points to `docs/operating-model/`
- does not duplicate reviewer contracts

### Codex Skill

`/Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md`

- thin invocation layer
- requires reading repo docs first
- supports reviewer selection and mode selection
- refuses to edit code unless explicitly asked

`/Users/awownysz/.codex/skills/snowcast-advisory-review/agents/openai.yaml`

- UI metadata for the skill
- no extra tool dependencies
- explicit default prompt

## Task 1: Create Reviewer Contract Docs

**Files:**

- Create: `docs/operating-model/advisory-reviewers.md`

- [ ] **Step 1: Create the operating-model directory**

Run:

```bash
mkdir -p docs/operating-model
```

Expected: command exits `0`.

- [ ] **Step 2: Create `advisory-reviewers.md`**

Add this file:

```markdown
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
```

- [ ] **Step 3: Verify the reviewer doc has no unresolved markers**

Run:

```bash
rg -n 'T''BD|TO''DO|FIX''ME|[.][.][.]' docs/operating-model/advisory-reviewers.md
```

Expected: no output and exit code `1`.

- [ ] **Step 4: Commit reviewer contracts**

Run:

```bash
git add docs/operating-model/advisory-reviewers.md
git commit -m "docs: add Snowcast advisory reviewer contracts"
```

Expected: commit succeeds.

## Task 2: Add Review Playbook and AGENTS Routing

**Files:**

- Create: `docs/operating-model/review-playbook.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Create `review-playbook.md`**

Add this file:

```markdown
# Snowcast Advisory Review Playbook

Use this playbook to choose advisory reviewers without slowing down normal solo
development. Reviewer definitions live in
`docs/operating-model/advisory-reviewers.md`.

## Default Routing

### Small Scoped Fix

Examples:

- copy tweaks
- focused test updates
- one-file bug fixes
- minor docs cleanup

Default:

- no advisory review
- inspect directly relevant files
- run focused tests or lint

Use a reviewer only when the small change touches a high-risk domain such as
auth, user data, planning/ranking semantics, catalog trust, deploy config, or
privacy-sensitive logging.

### Normal Feature

Default:

- run one to three relevant reviewers manually
- use `design-review` before coding when the feature changes architecture,
  product behavior, or user-facing model semantics
- use `feature-review` before final handoff when the feature touches a critical
  path

Examples:

```text
Run backend-api and security-privacy design-review on this proposal.
```

```text
Run data-trust-source-integrity feature-review on the current diff.
```

### Sprint-Sized Feature

Default:

- run the core panel in `design-review` before implementation
- run selected reviewers in `feature-review` before final handoff

Core panel:

- product-strategy
- backend-api
- data-trust-source-integrity
- ui-ux
- security-privacy
- observability-ops

### High-Risk Change

Always consider relevant advisory review when touching:

- auth, sessions, identity, or user trip data
- planning, ranking, scoring, thresholds, or model wording
- catalog data, source refs, acquisition, or trust manifests
- parser, narrative, prompts, LLM fallback, or LLM-assisted extraction
- deploy, CI/CD, migrations, production config, or secrets
- observability, logging, metrics, traces, or telemetry
- public SEO pages, sitemap/robots, or booking handoff
- mobile companion flows, device registration, or push-readiness

## Change-Type Routing

| Change type | Reviewers |
| --- | --- |
| Search/API behavior | backend-api, product-strategy, performance |
| Planning/ranking model | data-trust-source-integrity, product-strategy, backend-api |
| Catalog/source acquisition | data-trust-source-integrity, backend-api, ai-llm-reliability when LLM extraction changes |
| Parser/narrative/LLM | ai-llm-reliability, backend-api, security-privacy when user text/logging is involved |
| Web planning UI | ui-ux, accessibility, product-strategy |
| Public resort pages | growth-seo, data-trust-source-integrity, accessibility |
| Auth/current-trip/user data | security-privacy, backend-api, mobile-companion when mobile is affected |
| Mobile companion | mobile-companion, security-privacy, backend-api |
| Deploy/ops/config | observability-ops, release-change-management, security-privacy |
| Booking/affiliate handoff | monetization-partnerships, product-strategy, security-privacy |

## Superpowers Integration

### Brainstorming

For non-trivial features, run relevant reviewers in `design-review` before the
design is finalized when the feature touches high-risk domains.

Do not run broad `domain-audit` automatically.

### Planning

Implementation plans should include advisory review checkpoints when the plan
touches high-risk domains.

### Implementation

Before final handoff, run relevant reviewers in `feature-review` for
sprint-sized, product-facing, or high-risk changes.

Small focused fixes can skip advisory review.

## Invocation Examples

```text
Use $snowcast-advisory-review to run backend-api and security-privacy
feature-review on the current diff.
```

```text
Use $snowcast-advisory-review to run the core panel in design-review mode for
this sprint proposal.
```

```text
Use $snowcast-advisory-review to run a data-trust-source-integrity domain-audit
and identify the top five trust improvements.
```

```text
Use $snowcast-advisory-review to run ui-ux, accessibility, and performance
feature-review on the web route changes.
```

## Dry-Run Standard

When validating the advisory system:

1. Run one `feature-review` against a recent diff or committed feature.
2. Run one `domain-audit` against a single reviewer.
3. Confirm the reviewer reads the repo docs first.
4. Confirm the output uses the required format.
5. Confirm it does not edit code unless explicitly asked.
```

- [ ] **Step 2: Insert a concise routing section in `AGENTS.md`**

Add this section after `## Working speed and scope` and before
`## Architecture rules`:

```markdown
## Advisory review

- Use the Snowcast advisory review system for non-trivial, product-facing, or
  high-risk work when it improves decision quality.
- Reviewer definitions live in
  `docs/operating-model/advisory-reviewers.md`; routing guidance lives in
  `docs/operating-model/review-playbook.md`.
- Use `feature-review` for concrete diffs or completed changes, `design-review`
  for specs/plans before coding, and `domain-audit` only when the user asks for
  broad product/domain advice.
- Small scoped fixes do not need advisory review unless they touch auth, user
  data, planning/ranking semantics, catalog trust, LLM behavior, deploy/config,
  observability, public SEO/booking surfaces, mobile companion flows, or
  privacy-sensitive logging.
- During Superpowers brainstorming, planning, or implementation, include
  relevant advisory checkpoints for sprint-sized or high-risk changes; do not
  run broad domain audits automatically.
- Advisory reviewers are reviewers, not implementers. Do not let advisory review
  modify code unless the user explicitly asks for follow-up implementation.
```

- [ ] **Step 3: Verify AGENTS links and no duplicated contracts**

Run:

```bash
rg -n "advisory-reviewers|review-playbook|domain-audit|feature-review|design-review" AGENTS.md docs/operating-model
```

Expected: output includes the new `AGENTS.md` routing section and both
operating-model docs.

- [ ] **Step 4: Commit playbook and routing**

Run:

```bash
git add AGENTS.md docs/operating-model/review-playbook.md
git commit -m "docs: add advisory review playbook"
```

Expected: commit succeeds.

## Task 3: Create the Thin Codex Skill

**Files:**

- Create: `/Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md`
- Create: `/Users/awownysz/.codex/skills/snowcast-advisory-review/agents/openai.yaml`

**Required skill:** Before executing this task, use the `skill-creator` skill
because this task creates a new Codex skill.

- [ ] **Step 1: Create skill directories**

Run:

```bash
mkdir -p /Users/awownysz/.codex/skills/snowcast-advisory-review/agents
```

Expected: command exits `0`.

- [ ] **Step 2: Create `SKILL.md`**

Add this file at
`/Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md`:

```markdown
---
name: snowcast-advisory-review
description: Use for Snowcast ai-sports-travel-planner advisory reviews in feature-review, design-review, or domain-audit mode across product, backend/API, data trust/source integrity, UI/UX, security/privacy, observability/ops, AI/LLM reliability, mobile companion, performance, SEO/growth, release, accessibility, and monetization domains.
---

# Snowcast Advisory Review

Use this skill to run advisory reviews for the Snowcast project at:

```text
/Users/awownysz/repos/personal_projects/ai-sports-travel-planner
```

This skill is an invocation layer. The repo docs are the source of truth.

## Required Context

Before reviewing, read:

```text
docs/operating-model/advisory-reviewers.md
```

If reviewer selection, workflow routing, or Superpowers integration is unclear,
also read:

```text
docs/operating-model/review-playbook.md
```

Do not duplicate or override those docs from memory. If this skill and the repo
docs conflict, follow the repo docs and mention the mismatch.

## Review Modes

Supported modes:

- `feature-review`: default for a concrete diff, PR, branch, or completed change
- `design-review`: for a proposal, design doc, implementation plan, or feature concept
- `domain-audit`: broad project/domain advice, only when explicitly requested

If no mode is specified, use `feature-review` when there is a concrete change
scope. Ask one concise clarification question only when the request is broad and
the mode cannot be inferred safely.

## Reviewer Selection

Accept reviewer names as natural language or slugs:

- product-strategy
- backend-api
- data-trust-source-integrity
- ui-ux
- security-privacy
- observability-ops
- ai-llm-reliability
- mobile-companion
- performance
- growth-seo
- release-change-management
- accessibility
- monetization-partnerships
- core panel

For `core panel`, run:

- Product / Strategy
- Backend / API
- Data Trust & Source Integrity
- UI / UX
- Security & Privacy
- Observability / Ops

If the user asks which reviewers are needed, inspect the scope first and choose
the smallest useful set from `docs/operating-model/review-playbook.md`.

## Evidence Rules

For each reviewer:

1. Read that reviewer contract in `docs/operating-model/advisory-reviewers.md`.
2. Inspect the listed primary evidence files when they exist.
3. For `feature-review`, inspect the requested diff, files, branch, or commit.
4. For `design-review`, inspect the proposal/spec/plan and relevant project docs.
5. For `domain-audit`, inspect enough current product/docs/code to support
   prioritized advice.

Use source-backed reasoning. Prefer concrete file references and test gaps over
general opinions.

## Output Rules

Use the output format from `docs/operating-model/advisory-reviewers.md`.

For `feature-review` and `design-review`, findings must be defensible and
severity-tagged:

- `[Blocker]`
- `[High]`
- `[Medium]`
- `[Low]`

If there are no defensible findings, say so clearly. Do not manufacture review
comments.

For `domain-audit`, produce strengths, risks/gaps, top opportunities, and
suggested next actions.

## Boundaries

- Do not edit code, docs, config, or skills unless the user explicitly asks for
  follow-up implementation.
- Do not run broad `domain-audit` work automatically.
- Do not turn small scoped fixes into mandatory panel reviews.
- Do not post external comments or reviews unless explicitly asked.
- Do not expose secrets, tokens, raw prompts, or sensitive user text in review
  output.
```

- [ ] **Step 3: Create `agents/openai.yaml`**

Add this file at
`/Users/awownysz/.codex/skills/snowcast-advisory-review/agents/openai.yaml`:

```yaml
interface:
  display_name: "Snowcast Advisory Review"
  short_description: "Project reviewer panel for Snowcast changes"
  brand_color: "#0B1F3A"
  default_prompt: "Use $snowcast-advisory-review to run a focused advisory review for Snowcast."

policy:
  allow_implicit_invocation: true
```

- [ ] **Step 4: Validate skill files exist**

Run:

```bash
test -f /Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md
test -f /Users/awownysz/.codex/skills/snowcast-advisory-review/agents/openai.yaml
```

Expected: both commands exit `0`.

- [ ] **Step 5: Validate skill frontmatter and metadata**

Run:

```bash
python /Users/awownysz/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/awownysz/.codex/skills/snowcast-advisory-review
```

Expected: validation succeeds. If the validator output identifies a schema issue,
fix the named file and rerun the command.

## Task 4: Dry-Run and Finalize

**Files:**

- Read: `docs/operating-model/advisory-reviewers.md`
- Read: `docs/operating-model/review-playbook.md`
- Read: `/Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md`

- [ ] **Step 1: Verify repo docs are the only source of reviewer contracts**

Run:

```bash
rg -n "Product / Strategy|Backend / API|Data Trust & Source Integrity|Blocking conditions" \
  AGENTS.md \
  docs/operating-model \
  /Users/awownysz/.codex/skills/snowcast-advisory-review
```

Expected:

- full reviewer definitions appear in `docs/operating-model/advisory-reviewers.md`
- `AGENTS.md` only has routing guidance
- the skill points to the docs and does not duplicate full contracts

- [ ] **Step 2: Run a feature-review dry-run**

Use the skill manually in the conversation:

```text
Use $snowcast-advisory-review to run backend-api feature-review on the last commit.
```

Expected:

- it reads `docs/operating-model/advisory-reviewers.md`
- it inspects the last commit
- it returns the feature/design review output format
- it does not edit files

- [ ] **Step 3: Run a domain-audit dry-run**

Use the skill manually in the conversation:

```text
Use $snowcast-advisory-review to run observability-ops domain-audit for the current project.
```

Expected:

- it reads `docs/operating-model/advisory-reviewers.md`
- it may read `docs/operating-model/review-playbook.md`
- it returns the domain audit output format
- it does not edit files

- [ ] **Step 4: Run final repo checks**

Run:

```bash
rg -n 'T''BD|TO''DO|FIX''ME|[.][.][.]' docs/operating-model AGENTS.md
python /Users/awownysz/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/awownysz/.codex/skills/snowcast-advisory-review
```

Expected:

- unresolved-marker scan has no output and exits `1`
- skill validation succeeds

- [ ] **Step 5: Check git status**

Run:

```bash
git status --short
```

Expected:

- repo changes are limited to `AGENTS.md` and `docs/operating-model/`
- the skill files under `/Users/awownysz/.codex/skills/` do not appear because
  they live outside the repo

- [ ] **Step 6: Commit repo workflow docs**

If Task 2 was not already committed, run:

```bash
git add AGENTS.md docs/operating-model
git commit -m "docs: wire advisory reviews into project workflow"
```

If Task 1 and Task 2 were committed separately, skip this step.

## Final Verification Handoff

After implementation, report:

- created repo docs
- created skill path
- validation commands and results
- dry-run review modes tested
- commits created
- any limitations, especially that the skill may require a new Codex session or
  skill reload before implicit invocation appears in the UI

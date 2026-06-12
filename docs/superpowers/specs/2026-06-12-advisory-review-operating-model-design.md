# Snowcast Advisory Review Operating Model Design

## Summary

Create a lightweight advisory-review system for Snowcast so a solo builder can
bring focused expert scrutiny into product and engineering work without turning
development into process overhead.

The system should start manual and become automation-ready:

- repo-owned reviewer specs define the source of truth
- one thin Codex skill provides a convenient invocation layer
- project workflow instructions explain when to use advisory review
- reviewers operate as bounded review contracts, not broad personalities

The first version is advisory only. Reviewers identify risks, missing checks,
and domain-specific concerns. They do not own implementation or modify code
unless the user explicitly asks for follow-up changes.

## Goals

- Give Snowcast repeatable expert lenses for serious product work.
- Keep the process manageable for a solo builder.
- Make reviews manually invokable today and scriptable later.
- Keep reviewer definitions versioned with the project.
- Prevent review drift by using one source of truth.
- Support both scoped feature review and broader domain advice without mixing
  the two accidentally.

## Non-Goals

- Do not create autonomous implementation agents in the first version.
- Do not require every small change to run through a review panel.
- Do not duplicate full reviewer definitions in `AGENTS.md` or skill files.
- Do not make broad domain audits automatic.
- Do not replace Superpowers brainstorming, planning, or implementation flows.

## Operating Architecture

The system has two layers.

### Repo-Owned Reviewer Specs

Repo docs are the source of truth for reviewer behavior:

```text
docs/operating-model/
  advisory-reviewers.md
  review-playbook.md
```

`advisory-reviewers.md` defines:

- shared review modes
- shared severity model
- core reviewers
- triggered specialists
- one compact contract per reviewer
- likely files and docs to inspect first
- required output formats

`review-playbook.md` defines:

- when to run advisory reviews
- which reviewers to choose for common change types
- how advisory review fits Superpowers workflows
- examples of manual invocations
- expectations for solo-builder speed

### Thin Codex Skill

One Codex skill provides the invocation layer:

```text
/Users/awownysz/.codex/skills/snowcast-advisory-review/
  SKILL.md
  agents/openai.yaml
```

The skill must stay thin. It should:

- apply only to Snowcast / `ai-sports-travel-planner`
- read `docs/operating-model/advisory-reviewers.md`
- read `docs/operating-model/review-playbook.md` when routing is unclear
- determine requested reviewer modes and scopes
- inspect the files and docs named by the relevant reviewer contracts
- return the required structured output
- avoid code edits unless the user explicitly asks for implementation

The skill must not duplicate reviewer definitions. If behavior needs to change,
the repo docs change first.

## Review Modes

Each reviewer supports three modes.

### `feature-review`

Default mode for a concrete change, diff, PR, branch, or sprint deliverable.

Behavior:

- stay scoped to the requested change
- report concrete bugs, regressions, missing verification, and domain risks
- avoid broad roadmap advice unless the change directly raises it

### `design-review`

Pre-implementation review of a proposal, design doc, plan, or feature concept.

Behavior:

- check architectural fit
- identify missing requirements and risks
- challenge weak assumptions
- recommend focused verification
- catch contradictions with Snowcast product strategy or project conventions

### `domain-audit`

Broader project advice from one domain.

Behavior:

- inspect current product, docs, and relevant implementation
- summarize current strengths
- identify gaps and risks
- propose prioritized improvements
- avoid pretending everything must be fixed immediately

Domain audits are opt-in only. They should not run automatically during normal
development.

## Reviewer Panel

### Core Reviewers

Core reviewers cover the failure modes most likely to matter for a serious
Snowcast product.

#### Product / Strategy

Checks whether a change supports the ski-only, conditions-smart planning
product instead of drifting into generic travel, generic AI chat, or unsupported
marketplace polish.

Primary evidence:

- `PROJECT.md`
- `docs/strategy.md`
- `docs/engineering-notes.md`
- relevant UI/API behavior

#### Backend / API

Reviews API contracts, FastAPI boundaries, domain/service separation, error
handling, persistence behavior, and whether clients can rely on response
shapes.

Primary evidence:

- `app/api/`
- `app/domain/`
- `app/data/repositories.py`
- API tests under `tests/`
- client types in `frontend/src/types.ts` and mobile API usage when relevant

#### Data Trust & Source Integrity

Reviews resort catalog truth, source refs, acquisition artifacts, trust
manifest changes, planning model semantics, and whether user-facing claims are
backed by evidence.

Primary evidence:

- `docs/data-trust-model.md`
- `docs/planning-model.md`
- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`
- `app/data/resort_acquisition/`
- catalog validation tests

#### UI / UX

Reviews web planning experience, selected-resort hierarchy, current-trip
surface, state visibility, trust cues, and whether the interface matches the
real product maturity.

Primary evidence:

- `frontend/src/`
- `frontend/tests/e2e/`
- `docs/ui-concepts/`
- `docs/strategy.md`
- web-facing API fields

#### Security & Privacy

Reviews auth, tokens, session handling, user trip data, public endpoints, logs,
secrets, privacy-sensitive telemetry, and accidental data exposure.

Primary evidence:

- `app/auth/`
- authenticated API routes
- trip-context persistence
- logging/observability code and docs
- `.github/workflows/`
- deployment and env docs

#### Observability / Ops

Reviews deployability, runbook impact, health/readiness behavior, scheduled
jobs, logging/metrics/tracing expectations, refresh visibility, and operational
failure modes.

Primary evidence:

- `docs/production-runbook.md`
- `docs/observability-plan.md`
- `.github/workflows/`
- `fly.toml`
- `Dockerfile`
- health/readiness routes
- refresh and backfill commands

### Triggered Specialists

Triggered specialists are invoked when a change touches their domain.

#### AI / LLM Reliability

Triggered for parser, narrative, prompt, LLM fallback, cache, schema validation,
and LLM-assisted acquisition changes.

Primary evidence:

- `app/ai/`
- parser and narrative tests
- LLM-related acquisition modules
- cache/fallback behavior
- prompt and schema boundaries

#### Mobile Companion

Triggered for Flutter, authenticated mobile flows, saved-trip behavior,
exact-date companion logic, device registration, and future push-readiness.

Primary evidence:

- `mobile/lib/`
- `mobile/test/`
- current-trip API routes
- auth/session exchange
- device registration and companion event models

#### Performance

Triggered for search latency, database query shape, frontend runtime risk,
provider calls, expensive LLM paths, and cache-sensitive code.

#### Growth / SEO

Triggered for public resort pages, sitemap/robots, public copy, booking or
conversion paths, and shareable demo surfaces.

#### Release / Change Management

Triggered before production deploys, migrations, large config changes, CI/CD
changes, or anything needing rollback thinking.

#### Accessibility

Triggered for meaningful UI changes, especially forms, routeable pages, modals,
drawers, navigation, color, focus, and screen-reader semantics.

#### Monetization / Partnerships

Triggered for booking handoff, affiliate assumptions, provider abstraction,
attribution, rental/lift-pass integrations, and revenue-facing copy.

## Output Contracts

### Feature and Design Reviews

```markdown
## <Reviewer Name> Review

Mode:
Scope reviewed:
Evidence inspected:
Assumptions / limits:

Findings:
- [Blocker] ...
- [High] ...
- [Medium] ...
- [Low] ...

Missing checks:

Recommendation:
- Ship / ship after fixes / do not ship yet
```

If there are no defensible findings, the reviewer should say so clearly:

```markdown
No blocking findings.
Main residual risks:
- ...
```

Reviewers should not manufacture issues to justify their existence.

### Domain Audits

```markdown
## <Reviewer Name> Audit

Scope reviewed:
Current strengths:
Risks / gaps:
Top opportunities:
Suggested next actions:
```

## Severity Model

- **Blocker**: likely user-visible breakage, unsafe behavior, broken contract,
  data trust violation, secret/privacy risk, or deploy failure.
- **High**: serious regression risk or missing verification on a critical path.
- **Medium**: meaningful maintainability, UX, observability, or correctness
  concern.
- **Low**: polish, clarity, or follow-up improvement.

Solo-builder gate:

```text
Only Blocker and High findings stop the change by default.
Medium and Low findings become backlog or follow-up unless the user decides
otherwise.
```

## Workflow Integration

Add a short advisory-review routing section to `AGENTS.md`. It should point to
the operating-model docs rather than embedding full reviewer definitions.

### Trigger Policy

Small scoped fixes:

- no advisory review by default
- use focused inspection and tests

Normal features:

- run one to three relevant reviewers manually
- prefer `design-review` before coding for architectural or product-facing
  decisions
- prefer `feature-review` before final handoff when risk is meaningful

Sprint-sized features:

- run the core panel in `design-review` before implementation
- run selected reviewers in `feature-review` before final handoff

High-risk domains:

- always consider relevant reviewers when touching auth/session/user trip data
- always consider relevant reviewers when touching planning/ranking/scoring
- always consider relevant reviewers when touching catalog trust/source refs
- always consider relevant reviewers when touching LLM behavior
- always consider relevant reviewers when touching deploy, CI/CD, migrations,
  or production config
- always consider relevant reviewers when touching observability, logging, or
  telemetry
- always consider relevant reviewers when touching public SEO pages or booking
  handoff
- always consider relevant reviewers when touching mobile companion flows or
  push-readiness

### Superpowers Integration

Brainstorming:

- relevant reviewers may run in `design-review` before the design is finalized
- broad domain audits do not run automatically

Planning:

- implementation plans should include advisory review checkpoints for
  high-risk domains

Implementation:

- relevant reviewers may run in `feature-review` before final handoff for
  sprint-sized, product-facing, or high-risk changes

## Example Invocations

```text
Run a backend-api and security-privacy feature-review on the current diff.
```

```text
Run the core advisory panel in design-review mode for this sprint proposal.
```

```text
Run a data-trust-source-integrity domain-audit and tell me what to improve next.
```

```text
Before final handoff, run UI/UX, accessibility, and performance reviewers on
the web route changes.
```

## Automation-Ready Contract

The review system should be shaped so later automation can pass structured
inputs:

```text
reviewer: backend-api
mode: feature-review
scope: git diff / PR / specific files / current sprint plan
gating: blocker+high
output: markdown findings
```

Automation should still respect the same rules:

- repo docs are the source of truth
- advisory review does not edit code by default
- broad domain audits are opt-in
- small changes do not require ceremony

## Rollout Plan

1. Create `docs/operating-model/advisory-reviewers.md`.
2. Create `docs/operating-model/review-playbook.md`.
3. Add a concise advisory-review routing section to `AGENTS.md`.
4. Create the thin `snowcast-advisory-review` Codex skill.
5. Dry-run the skill on one existing feature diff and one domain audit.
6. Tighten reviewer contracts based on the dry-run output.

## Verification

Implementation should be verified by:

- checking that reviewer definitions live only in repo docs
- confirming `AGENTS.md` contains routing guidance but no duplicated contracts
- invoking the skill for at least one `feature-review`
- invoking the skill for at least one `domain-audit`
- confirming outputs follow the required formats
- confirming reviewers do not edit code unless explicitly asked

## Open Decisions

No open decisions remain for the first version. Later revisions can split the
single router skill into separate reviewer skills if one reviewer becomes
important enough to justify dedicated maintenance.

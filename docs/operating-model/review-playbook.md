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

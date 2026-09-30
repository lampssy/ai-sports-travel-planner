---
name: snowcast-advisory-review
description: Use for Snowcast ai-sports-travel-planner advisory reviews in feature-review, design-review, or domain-audit mode across product, backend/API, data trust/source integrity, UI/UX, content/language, security/privacy, observability/ops, AI/LLM reliability, mobile companion, performance, SEO/growth, release, accessibility, and monetization domains.
---

# Snowcast Advisory Review

Use this skill to run advisory reviews for the
`lampssy/ai-sports-travel-planner` repository. Resolve the checkout from the
active project or workspace; do not assume a machine-specific absolute path.

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
- content-language
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

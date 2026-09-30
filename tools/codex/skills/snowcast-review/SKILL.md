---
name: snowcast-review
description: Use when the user asks for a scoped Snowcast review of a current diff, branch, PR, completed change, feature spec, implementation plan, proposal, or advisory reviewer selection.
---

# Snowcast Review

Run a scoped Snowcast advisory review. This is a convenience wrapper around the
existing Snowcast reviewer system.

**REQUIRED SUB-SKILL:** Use `snowcast-advisory-review` for the actual reviewer
contract and output format.

## Repository

Use this skill only for the `lampssy/ai-sports-travel-planner` repository.
Resolve the checkout from the active project or workspace; do not assume a
machine-specific absolute path. If needed, switch to that repo before inspecting
files. Do not edit code or docs unless the user explicitly asks for follow-up
implementation.

## Reviewers

Available reviewer slugs:

- `product-strategy`
- `backend-api`
- `data-trust-source-integrity`
- `ui-ux`
- `content-language`
- `security-privacy`
- `observability-ops`
- `ai-llm-reliability`
- `mobile-companion`
- `performance`
- `growth-seo`
- `release-change-management`
- `accessibility`
- `monetization-partnerships`
- `core panel`

`core panel` means `product-strategy`, `backend-api`,
`data-trust-source-integrity`, `ui-ux`, `security-privacy`, and
`observability-ops`.

## Mode Selection

Infer the advisory mode from the target:

- current diff, branch, PR, committed feature, or completed change:
  `feature-review`
- feature concept, proposal, feature spec, implementation plan, or architecture
  design before coding:
  `design-review`

If the user provides no target or reviewer, list the reviewers above and ask one
concise question for the missing scope. If a current diff exists and the user
gave no reviewers, inspect the diff and choose the smallest useful reviewer set
from `docs/operating-model/review-playbook.md`.

## Workflow

1. Read `docs/operating-model/advisory-reviewers.md`.
2. Read `docs/operating-model/review-playbook.md` when routing is unclear.
3. Use `snowcast-advisory-review` with the selected reviewers and inferred mode.
4. Keep findings concrete, source-backed, severity-tagged, and ready to act on.

Do not run broad `domain-audit` from this skill. Use `snowcast-audit` instead.

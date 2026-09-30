---
name: snowcast-audit
description: Use when the user asks for a broad Snowcast domain audit, overall project direction from one advisory domain, or available advisory reviewer domains for audit.
---

# Snowcast Audit

Run a broad Snowcast `domain-audit`. This is a convenience wrapper around the
existing Snowcast reviewer system.

**REQUIRED SUB-SKILL:** Use `snowcast-advisory-review` for the actual reviewer
contract and output format.

## Repository

Use this skill only for the `lampssy/ai-sports-travel-planner` repository.
Resolve the checkout from the active project or workspace; do not assume a
machine-specific absolute path. If needed, switch to that repo before inspecting
files. Do not edit code or docs unless the user explicitly asks for follow-up
implementation.

## Domains

Available domain reviewer slugs:

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

If no domain is provided, print this list and ask which domain to audit.

## Workflow

1. Read `docs/operating-model/advisory-reviewers.md`.
2. Read the selected reviewer contract.
3. Inspect enough current product docs and implementation to support
   prioritized advice.
4. Use `snowcast-advisory-review` in `domain-audit` mode only.
5. Use the `Domain Audit` output format.

Keep this broad and strategic within the chosen domain. Do not turn it into a
diff review; use `snowcast-review` for scoped changes.

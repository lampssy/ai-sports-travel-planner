---
name: snowcast-idea
description: Use when the user wants to shape a Snowcast product or technical idea, backlog candidate, not-now concept, or pre-spec question before implementation planning.
---

# Snowcast Idea

Shape a Snowcast idea before implementation. This skill helps decide whether an
idea belongs in backlog, a feature spec, a Developer Decision Checkpoint, an ADR,
or a parked/not-now state.

## Repository

Use this skill only for the `lampssy/ai-sports-travel-planner` repository.
Resolve the checkout from the active project or workspace; do not assume a
machine-specific absolute path. If needed, switch to that repo before inspecting
files. Do not edit code or docs unless the user explicitly asks for follow-up
implementation.

## Source Docs

Read these first:

- `AGENTS.md`
- `docs/operating-model/review-playbook.md`
- `docs/product-backlog.md`

Read these when relevant:

- `PROJECT.md`
- `docs/strategy.md`
- `docs/domain-language.md`
- `docs/engineering-notes.md`
- relevant model docs such as `docs/planning-model.md`

## Advisory Reviewers

Likely reviewer domains include `product-strategy`, `backend-api`,
`data-trust-source-integrity`, `ui-ux`, `content-language`,
`security-privacy`, `observability-ops`, `ai-llm-reliability`,
`mobile-companion`, `performance`, `growth-seo`, `release-change-management`,
`accessibility`, and `monetization-partnerships`. Use the repository playbook
to select the smallest relevant set.

## Workflow

1. Understand the idea and ask at most one concise clarification question when it
   cannot be shaped safely from context.
2. Classify product area, likely scope size, risk level, and whether the idea
   should enter backlog, feature spec, or stay parked.
3. Surface one to three Developer Decision Checkpoints when useful for learning.
4. Identify likely advisory reviewers and documentation impact.
5. Do not create a spec, backlog item, ADR, or code change unless the user asks
   for that follow-up explicitly.

## Output

Use this structure:

```markdown
## Idea Shape

Summary:
Recommended home:
Why now / why not:
Likely first scope:
Out of scope:

Developer Decision Checkpoints:
- ...

Likely reviewers:
- ...

Docs impact:
- ...

Next action:
```

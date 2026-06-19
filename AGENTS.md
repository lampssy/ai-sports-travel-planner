# AI Sports Travel Planner – AGENTS.md

## Goal
Build a production-grade backend with AI components.

---

## Working speed and scope

- Before non-trivial implementation, classify the task as either `fast path` or
  `review-gated`.
- Use `fast path` only when the change is clearly small, local, reversible, and
  outside high-risk domains.
- Use `review-gated` when the change affects durable product behavior, user
  trust, data correctness, persistence, shared API contracts, request-path
  performance, production reliability, security/privacy, observability,
  external integrations, or future maintenance patterns.
- If unsure, choose `review-gated`.
- For small, well-scoped bugs or copy/docs tweaks, use a fast path:
  - inspect only the directly relevant files
  - patch narrowly
  - run focused tests or lint for the touched area
  - skip broad sprint-level verification unless the change touches shared behavior or the user asks for it
- Examples that normally make a change `review-gated`:
  - database schema, indexes, migrations, or repository query shape
  - request-path performance, memory pressure, or production reliability
  - planning, ranking, scoring, evidence selection, or model semantics
  - evidence/trust wording, LLM behavior, auth, user data, public endpoints,
    deploy config, scheduled jobs, acquisition pipelines, telemetry, or
    privacy-sensitive logging
  In these cases, record a lightweight Decision and Review Gate before
  implementation. The gate must state Developer Decision Checkpoint status,
  ADR status, and advisory review status. Advisory review should be skipped only
  with an explicit reason.
- Use the full planning / Superpowers / subagent workflow only for sprint-sized changes, architectural work, risky refactors, or when explicitly requested.
- This project is normally single-agent. Do not spend extra time assuming parallel repo edits during small tasks, but still do not revert, delete, or overwrite unrelated existing changes.
- Keep final handoffs shorter for small changes: summarize the cause, the patch, and the exact focused verification that ran.

---

## Developer Decision Checkpoints

- Trigger Developer Decision Checkpoints whenever a meaningful implementation,
  architecture, product, operational, or technical choice exists. This applies
  to both `fast path` and `review-gated` work.
- A checkpoint is required when the choice affects how the project will be
  shaped, maintained, operated, or understood later, even if the code change is
  small.
- Checkpoints are interactive by default: stop and ask the owner before choosing
  unless the decision is truly mechanical, low-impact, and not useful as a
  learning moment.
- Do not satisfy a checkpoint only by recording it in a document. If owner input
  would be useful, ask first, then record the chosen direction if it is durable.
- Do not silently convert a material decision into an assumption. Use
  assumptions only for low-impact defaults, or when the owner explicitly accepts
  continuing with an assumption.
- Present meaningful options and tradeoffs neutrally. After the owner chooses,
  briefly review consequences and risks before implementation.
- Group related checkpoints so the owner is not overwhelmed, but do not hide
  materially different decisions inside one broad recommendation.
- Good checkpoint examples:
  - database index shape, query ownership, or migration strategy
  - framework/library/provider choice
  - cache ownership, invalidation, or request-path vs background execution
  - alert thresholds, severity, notification routing, or no-data behavior
  - ranking/scoring/evidence thresholds or trust wording
  - API contract shape, schema boundaries, or compatibility behavior
  - LLM-vs-deterministic parsing behavior or fallback policy
- Low-value boilerplate choices, narrow copy edits, simple formatting, and
  obvious bug fixes can proceed without a checkpoint when they do not affect the
  above concerns.

---

## Advisory review

- Use the Snowcast advisory review system for `review-gated` work by default.
  Bias toward invoking reviewers too often rather than too rarely.
- Reviewer definitions live in
  `docs/operating-model/advisory-reviewers.md`; routing guidance lives in
  `docs/operating-model/review-playbook.md`.
- Use `feature-review` for concrete diffs or completed changes, `design-review`
  for specs/plans before coding, and `domain-audit` only when the user asks for
  broad product/domain advice.
- For non-trivial product features, create or update a short feature spec before
  advisory `design-review`; use
  `docs/operating-model/feature-spec-template.md` as the template and store
  sprint-sized specs under `docs/superpowers/specs/`.
- Fast-path small scoped fixes do not need advisory review. If a small change
  touches auth, user data, planning/ranking semantics, catalog trust, LLM
  behavior, deploy/config, observability, public SEO/booking surfaces, mobile
  companion flows, or privacy-sensitive logging, treat it as `review-gated`.
- Skipping advisory review for `review-gated` work must be recorded in the
  spec, plan, or final handoff with the reason.
- During Superpowers brainstorming, planning, or implementation, include
  relevant advisory checkpoints for sprint-sized or high-risk changes; do not
  run broad domain audits automatically.
- Advisory reviewers are reviewers, not implementers. Do not let advisory review
  modify code unless the user explicitly asks for follow-up implementation.

---

## Architecture rules

- Separate:
  - AI logic
  - business logic
  - integrations (weather, maps)
- Do not mix LLM calls with data fetching logic

---

## AI usage

- Do NOT use LLM if deterministic logic is sufficient
- Always suggest caching for expensive LLM calls
- Prefer simple prompts over complex chains

---

## Code rules

- Type-safe code
- No hidden side effects
- Explicit error handling
- Small functions
- Keep important model logic and calculation policy centralized rather than scattering literals and summary wording across multiple modules.
- When a feature has tunable thresholds, weights, evidence-profile labels, or canonical user-facing model wording, prefer a dedicated policy/config layer plus a visible human-readable spec over ad hoc hardcoding.

---

## Safety

Ask before:
- installing packages
- modifying dependencies
- deleting files

---

## Testing rules

- Write tests for:
  - business logic
  - data transformations
  - critical API endpoints

- Do NOT write tests for:
  - simple glue code
  - LLM outputs (mock instead)

- Prefer:
  - unit tests for logic
  - integration tests for APIs

- When adding new logic:
  - suggest test cases BEFORE implementation

---

## AI testing

- Do not test exact LLM responses
- Test:
  - structure of response
  - presence of key fields
  - validation logic

- Mock LLM calls in unit tests
- Keep prompts testable (small, composable)

---

## Verification handoff

- After implementing a sprint or any major product-facing addition, always include a clear "how to test this locally" handoff in the final response.
- For medium/high-risk changes, include a short process handoff:
  - fast path or review-gated classification
  - Developer Decision Checkpoint resolved, or explicitly accepted as an assumption
  - ADR added, linked, or explicitly not needed
  - advisory review run, or explicitly skipped with reason
  - verification run and unresolved blockers listed
- That handoff should be practical and product-oriented, not just a list of automated checks.
- Include:
  - exact commands to run the relevant backend/frontend/build/test flow
  - the preferred command for seeing the latest product state locally
  - a short manual acceptance path describing where to click or what to inspect in the UI/API
  - any important caveats such as needing a rebuild, seeded data refresh, or env vars
- Prefer commands that match the current repo conventions rather than generic placeholders.
- If the change is backend-only, include a concrete curl/API verification example.
- If the change is frontend or full-stack, include the shortest reliable path for the user to see the change in the running product.

---

## Documentation
Update the documentation artifact that owns the changed concern:
- `README.md` for setup, local development, product usage, and deployment entry points.
- `PROJECT.md` for the short product charter and current roadmap snapshot.
- `docs/product-backlog.md` for candidate ideas and future work that are worth preserving but are not active implementation commitments yet.
- Maintain `docs/engineering-notes.md` as a curated project knowledge file for technical concepts, architecture notes, tradeoffs, and clarification-driven learning.
- Update `docs/engineering-notes.md` when a non-trivial technical decision is made, a new framework/tool is introduced, or a follow-up clarification reveals a concept worth preserving.
- When a discussion produces a useful "not now" idea, add or update a concise item in `docs/product-backlog.md` instead of expanding `PROJECT.md` or creating a feature spec prematurely.
- Promote backlog items into `docs/superpowers/specs/` only when they are ready for design review and likely implementation.
- For durable architecture or product-architecture decisions with meaningful alternatives or long-lived consequences, add an ADR under `docs/architecture/adr/` and link it from the related spec, plan, or engineering note.
- Common ADR-worthy examples include adding request-path database indexes, moving filtering or aggregation across SQL/Python boundaries, changing cache ownership, changing background-versus-request-path execution, or changing where planning evidence is selected or summarized.
- Maintain `docs/domain-language.md` as the shared Snowcast domain-language and bounded-context reference. Update it when introducing durable domain terms, changing term meanings, or moving ownership between contexts.
- When changes touch important domain models, planning/ranking logic, scoring formulas, evidence profiles, thresholds, or other product-facing calculation behavior, update the relevant dedicated model/spec docs as part of the same change.
- Prefer a visible dedicated doc for major model logic (for example `docs/planning-model.md`) and keep code, policy, and doc wording aligned.
- Keep knowledge notes concise and topic-based; summarize rather than transcript.
- Prefer durable, time-agnostic engineering notes over sprint-specific or changelog-style phrasing; mention a sprint only when the timing materially explains a temporary constraint or tradeoff.
- Keep README.md focused on setup/product usage and PROJECT.md focused on charter/current-roadmap context.
- Do not bloat the knowledge file with minor implementation details or temporary debugging notes.

## Learning-oriented collaboration
- For any work with meaningful choices, surface the main technical,
  architectural, product, or operational decisions before implementation.
- Before non-trivial implementation, classify the work as `fast path` or
  `review-gated`. If it is `review-gated`, pause for a Decision and Review Gate
  and state whether Developer Decision Checkpoints, ADRs, and advisory reviews
  are resolved, required, or intentionally skipped with a reason.
- Surface more technical decisions rather than collapsing them too early into a single proposed direction.
- Present meaningful options and tradeoffs neutrally by default; do not recommend first unless explicitly asked or the user is clearly blocked.
- Use Developer Decision Checkpoints for material choices that are useful for owner review or learning. These include pure technical choices, product/domain logic choices, and mixed choices that affect both.
- Include close-to-default or conventional technical choices when they are useful learning moments, but keep them concise and grouped so process overhead stays proportional.
- For non-trivial specs or plans, ask at most one to three owner decision prompts before implementation. If there are more, group related choices or split the work.
- During implementation work, actively raise concrete technical choices that materially affect the design, such as:
  - database indexing and query shape
  - schema/model boundaries
  - caching strategy
  - API contract shape
  - background job vs request-path work
  - compatibility or migration tradeoffs
- Also raise product/domain choices that materially affect user-facing behavior, such as:
  - ranking weights, scoring thresholds, and evidence-profile policy
  - source trust tiers, freshness rules, and uncertainty display
  - alert severity, notification noise, and booking-handoff semantics
  - deterministic logic versus LLM-assisted interpretation
- Do not skip these questions just because implementation has already started; surface them as soon as they become relevant.
- When useful for learning, ask open questions instead of forcing every discussion into predefined options.
- Let the user propose or choose an approach first when the goal is learning.
- Always review the user's proposed design or implementation critically before proceeding.
- Use the review and discussion as a teaching step; point out weak assumptions, risks, and better alternatives when needed.
- Do not recommend the “best” option first when multiple reasonable implementation choices exist. Present the meaningful options neutrally, let the user choose, then review that choice critically and discuss consequences before proceeding.
- Do not finalize a plan immediately after the user picks options; first review the chosen decisions, discuss consequences, and only then converge on the implementation plan.
- When using Superpowers, unresolved Developer Decision Checkpoints must be resolved or explicitly accepted as assumptions before writing the implementation plan or dispatching subagents.
- Subagents must not silently make unresolved owner decisions. If an implementation task exposes a new material decision, return it as a blocker for the main agent to resolve with the user.
- After decisions are discussed and aligned, implement efficiently and keep momentum.
- Act directly only for low-value boilerplate or routine changes that are not useful learning moments.

## Code implementation
- For non-trivial work, discuss and confirm key decisions before implementation
- For non-trivial implementation details, prefer concise Developer Decision Checkpoints rather than silently choosing defaults
- After the user answers, review the chosen approach before coding instead of immediately endorsing it
- Prefer test-first (TDD) approach

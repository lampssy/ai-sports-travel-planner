# AI Sports Travel Planner – AGENTS.md

## Goal
Build a production-grade backend with AI components.

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

## Documentation
Remember to update documentation - PROJECT.md and README.md - with any architectural decisions, new features, or changes in the roadmap.
- Maintain `docs/engineering-notes.md` as a curated project knowledge file for technical concepts, architecture notes, tradeoffs, and clarification-driven learning.
- Update `docs/engineering-notes.md` when a non-trivial technical decision is made, a new framework/tool is introduced, or a follow-up clarification reveals a concept worth preserving.
- Keep knowledge notes concise and topic-based; summarize rather than transcript.
- Keep README.md focused on setup/product usage and PROJECT.md focused on roadmap/status.
- Do not bloat the knowledge file with minor implementation details or temporary debugging notes.

## Learning-oriented collaboration
- For non-trivial features, surface the main technical and architectural decisions before implementation.
- Surface more technical decisions rather than collapsing them too early into a single proposed direction.
- Present meaningful options and tradeoffs neutrally by default; do not recommend first unless explicitly asked or the user is clearly blocked.
- When useful for learning, ask open questions instead of forcing every discussion into predefined options.
- Let the user propose or choose an approach first when the goal is learning.
- Always review the user's proposed design or implementation critically before proceeding.
- Use the review and discussion as a teaching step; point out weak assumptions, risks, and better alternatives when needed.
- Do not finalize a plan immediately after the user picks options; first review the chosen decisions, discuss consequences, and only then converge on the implementation plan.
- After decisions are discussed and aligned, implement efficiently and keep momentum.
- Act directly only for low-value boilerplate or routine changes that are not useful learning moments.

## Code implementation
- For non-trivial work, discuss and confirm key decisions before implementation
- Prefer test-first (TDD) approach

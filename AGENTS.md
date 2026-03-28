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

## Code implementation
- Provide code only after confirming requirements
- Prefer test-first (TDD) approach


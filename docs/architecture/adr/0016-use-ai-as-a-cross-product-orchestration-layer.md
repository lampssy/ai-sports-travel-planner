# ADR 0016: Use AI As A Cross-Product Orchestration Layer

Status: accepted
Date: 2026-07-17

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-17-snowcast-ai-orchestration-architecture-design.md`
- `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`

Related docs:
- `PROJECT.md`
- `docs/domain-language.md`
- `docs/search-ranking-model.md`

## Context

Snowcast already uses LLM assistance to parse trip briefs and propose Search V4
refinements, while deterministic Planning owns candidate evaluation and
ranking. The product roadmap also includes saved-trip and current-trip companion
behavior. If each surface develops an independent AI feature, prompts, context,
wording, and actions will fragment. If the product instead becomes one general
chat agent backed by broad RAG, structured domain truth and user-visible
decisions become difficult to validate, explain, and operate reliably.

Snowcast needs a coherent AI direction that supports continuity from discovery
to companion without making chat the primary product or asking a future LLM to
own ranking, catalog facts, conditions, alerts, or persistence.

## Decision

Snowcast will evolve toward one shared AI orchestration and interaction layer
across its structured product surfaces. The layer assembles minimal relevant
context, chooses registered domain capabilities, composes grounded language, and
hands typed actions to their owning domains. Structured search, comparison,
dossier, current-trip, companion, and booking flows remain first-class. Chat may
be an optional surface over the same capabilities but is not the product shell.

Planning, Catalog And Data Trust, Conditions And Weather Evidence, Companion,
Booking Handoff, and explicit preference customization remain authoritative for
their respective decisions and state. The AI layer cannot reproduce or replace
their business logic in prompts. Every proposed state change or ranking change
passes through a typed capability and deterministic validation.

Structured current data is retrieved directly from domain capabilities.
Retrieval-augmented generation is used selectively for unstructured,
source-attributed material and does not promote retrieved prose into catalog
truth or ranking evidence.

Durable user preferences are explicitly managed in assistant customization.
Search refinements are search-scoped by default, and deliberate trip decisions
may be trip-scoped. Neither silently updates the durable preference profile.
Persistent preferences must be user-visible, editable, deletable, and scoped to
the authenticated owner.

Search refinement is the first embedded assistant interaction. It will move
toward a bounded clarification capability context and UI-independent validated
opportunities with approved answer vocabulary and typed patches. The AI may
dynamically choose which registered factor to clarify, compose legal answer
variants, and phrase a question using exact registered selected-topic semantic
phrases inside an approved outer grammar.
Planning owns the public reason, rejects unsafe or ungrounded wording to a
deterministic fallback, validates materiality, applies the selected patch, and
reranks. This does not introduce a fixed registry of possible questions. The
same validated interaction may later be rendered as a card or optional chat
exchange.

Adoption remains incremental. This decision does not introduce a generic agent
framework, vector database, persistent free-form memory, universal interaction
schema, or chat interface before demonstrated product needs require them.

## Consequences

AI behavior can remain coherent across planning and companion while primary
journeys retain explicit structure and deterministic fallbacks. Search
refinement can be improved now without creating a results-page-only AI island
or prematurely building the complete assistant.

The orchestration layer must remain thin. Its cross-product position creates a
risk of becoming a god service that accumulates domain decisions. Typed
capability contracts, explicit context ownership, and deterministic validation
are therefore architecture constraints rather than optional implementation
style.

Context assembly becomes a product and privacy boundary. Snowcast must select
the least context needed for a task, distinguish durable, search, trip, and
conversation scopes, and keep sensitive prompts and user context out of
telemetry. User-owned reads and actions must remain authenticated, and
persistent assistant state must be inspectable and deletable.

Document retrieval requires source, freshness, scope, and trust metadata.
Structured domain retrieval and RAG need separate implementations and failure
semantics.

Core flows must work when the AI provider is slow or unavailable. This requires
typed fallback states and prevents essential domain operations from depending
on generated prose.

## Alternatives Considered

- **General chat agent with universal RAG:** offers one obvious interface but
  makes structured truth, current data, actions, and deterministic decisions
  harder to control and explain.
- **Independent AI feature per product surface:** enables local delivery but
  duplicates prompts and context, fragments the assistant experience, and makes
  planning-to-companion continuity expensive to recover later.
- **No shared AI layer:** preserves strict simplicity but cannot support the
  intended context-aware continuity or reuse refinement and explanation
  behavior across product surfaces.

## Decision And Review Gate

- Classification: `review-gated`, full design flow.
- High-risk domains touched: LLM ownership, user context and privacy, Search V4
  refinement semantics, future companion behavior, and cross-product API
  boundaries.
- Developer Decision Checkpoint: resolved by the owner on 2026-07-17.
- ADR status: accepted after owner written-spec review on 2026-07-18.
- Advisory design review: completed on 2026-07-17 with Product / Strategy,
  Backend / API, AI / LLM Reliability, and Security & Privacy. No findings
  remain after the related spec was revised.

## Revisit When

Revisit this decision if structured surfaces cease to be the primary user
journey, if multiple AI capabilities demonstrate that per-turn orchestration is
insufficient, if cross-device conversation continuity becomes a validated need,
or if document-retrieval requirements justify selecting shared indexing and
retrieval infrastructure. Those events may change implementation choices but do
not by themselves transfer domain ownership to the LLM.

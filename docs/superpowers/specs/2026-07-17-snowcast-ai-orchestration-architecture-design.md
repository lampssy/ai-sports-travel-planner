# Snowcast AI Orchestration Architecture

## Status

- Status: proposed for written review
- Owner: solo-builder
- Date: 2026-07-17
- Related ADR: `docs/architecture/adr/0016-use-ai-as-a-cross-product-orchestration-layer.md`
- Related docs:
  - `PROJECT.md`
  - `docs/domain-language.md`
  - `docs/search-ranking-model.md`
  - `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`

## Purpose

Define the compact target architecture for AI across Snowcast so current search
refinement can evolve into the wider product without making Snowcast a
chat-centric application or prematurely designing a general autonomous agent.

Snowcast remains a structured conditions-smart decision product. AI is a shared
orchestration and interaction layer that binds Planning, Catalog, Conditions,
Companion, and Booking Handoff capabilities together while those bounded
contexts remain authoritative for their own decisions and data.

## Product Outcome

A user can move from discovery through a planned and current trip with coherent
Snowcast assistance. The product may ask a useful refinement, explain a ranked
result, summarize a conditions change, or offer a typed next action using the
relevant user and trip context. Structured search, result, dossier, trip, and
companion surfaces remain first-class; optional chat is one interaction surface,
not the product shell or source of truth.

## Decisions

1. Snowcast uses one shared AI orchestration and interaction boundary across
   planning and companion flows.
2. Deterministic domain capabilities continue to own ranking, catalog truth,
   weather derivation, alert eligibility, trip persistence, and booking handoff.
3. The AI layer receives a minimal task-specific context assembled from typed
   sources. It does not receive an indiscriminate dump of all user or product
   state.
4. Structured current data is retrieved through typed domain capabilities.
   Retrieval-augmented generation is reserved for relevant unstructured,
   source-attributed material.
5. Durable user preferences are changed explicitly in assistant customization.
   Search refinements remain search-scoped by default; deliberate trip choices
   may be trip-scoped. Neither silently becomes a permanent preference.
6. Search refinement is the first embedded assistant interaction. The AI may
   dynamically select which registered factors are useful to clarify, while
   Planning supplies bounded capabilities and validates the resulting proposal.
   The validated interaction must be UI-independent so it can later be rendered
   as a card, optional chat exchange, or another client interaction.
7. The initial runtime should be bounded and per-turn. A generic autonomous
   agent framework, persistent free-form memory, and a universal vector store
   are not prerequisites.

## Target Architecture

### Structured Product Surfaces

Web and mobile retain dedicated experiences for search, comparison, dossiers,
current trip, companion conditions, and booking handoff. AI interactions may be
embedded in those experiences. A future `Ask Snowcast` surface may use the same
capabilities, but primary journeys must remain understandable and usable without
chat and must degrade safely when an LLM is unavailable.

### AI Orchestration And Interaction

The target layer has five responsibilities:

- **Context assembly:** select only the explicit profile, active search, planned
  or current trip, conditions, and recent interaction state needed for the
  current task.
- **Capability selection:** choose among registered typed Snowcast operations;
  do not reproduce their internal business logic in prompts.
- **Interaction planning:** choose whether a clarification, explanation,
  comparison, suggestion, or no AI interaction is useful.
- **Language composition:** express grounded capability results in
  traveller-facing language and approved presentation vocabulary.
- **Typed action handoff:** propose only registered actions and send them to the
  owning domain for authorization, validation, and execution.

The layer may maintain bounded conversation state for continuity, but durable
state lives in the owning domain stores rather than in an LLM transcript.

### Authoritative Domain Capabilities

- **Planning** owns constraints, candidate generation, factor evaluation,
  ranking, refinement materiality, typed intent patches, and explanations.
- **Catalog And Data Trust** owns normalized entities, facts, provenance, and
  trust state.
- **Conditions And Weather Evidence** owns current observations, versioned
  forecasts, climatology, freshness, and weather-derived evidence.
- **Companion** owns saved/current trip state, change detection, event and alert
  eligibility, and last-checked semantics.
- **Booking Handoff** owns provider-specific outbound actions.
- **Future Assistant Customization** owns explicit durable user preferences.
  Search or conversation state can read these preferences but cannot silently
  rewrite them. Persistent preferences must be user-visible, editable,
  deletable, and scoped to the authenticated owner.

### Retrieval Policy

Use direct typed retrieval for catalog facts, search state, ranking evidence,
forecasts, current trips, companion events, and explicit preferences. These
values are current or structured and must not be approximately rediscovered
through embeddings.

Use document retrieval when the task needs relevant unstructured material such
as curated guides, source excerpts, Snowcast help, or operational guidance.
Retrieved material must retain source, scope, freshness, and trust metadata.
Document retrieval may support explanation; it cannot become catalog truth,
ranking evidence, or an executed action without the owning domain's rules.

Conversation history may be summarized or retrieved later, but it is not a
permanent preference store. Sensitive context, raw prompts, raw model responses,
and raw trip briefs remain outside logs, metrics, and traces.

## Search Refinement As The First Embedded Interaction

Planning should expose a bounded clarification capability context containing
the registered factors that may be clarified, traveller-facing meanings,
approved answer vocabulary, legal typed patch shapes, and the evaluated
candidate state needed for impact simulation. The AI layer may dynamically
select a useful unresolved topic, compose its answer variants within that
context, and phrase the question naturally. It must not invent factor IDs,
controlled values, ranking effects, evidence, or candidate facts.

Planning then validates the proposal and its current-search materiality. Only a
validated proposal becomes the UI-independent clarification opportunity shown
to the user. This preserves dynamic LLM topic selection without creating a
deterministic registry of every possible question.

The selected answer is returned as a stable option or typed patch reference.
Planning validates it, applies it to the canonical intent, and reranks. The same
interaction contract can be rendered in a search rail without chat history or
used later inside an optional assistant conversation.

Approved answer labels and meanings come from a presentation-aware registry.
The LLM sees that vocabulary so it can write a coherent question; the server
resolves authoritative answer copy from the registry and clients render the
returned copy. Question wording may remain dynamic after presentation and
unsupported-claim checks. A deterministic question remains available when the
provider fails or its output is invalid.

The current short-lived exact-ranking handoff remains an implementation detail
of Search V4. A future cross-device or long-running assistant session may need a
durable or reproducible search-session model, but this design does not choose
that persistence architecture prematurely.

## Companion Interaction

Companion logic deterministically detects trip relevance and meaningful
conditions changes. The AI layer may explain a detected change, answer a
saved-trip question using current evidence, or present a typed next action. It
does not independently decide that an alert is eligible, label unsupported
conditions as safe or dangerous, or mutate the trip without a validated domain
action.

Proactive companion communication starts from a deterministic event. Chat is
not required for event delivery, and the event remains understandable without
LLM-authored prose.

## Interaction Contract Direction

Future clients should be able to consume one UI-independent interaction
envelope containing, as applicable:

- grounded message text;
- interaction kind and context scope;
- choice or clarification options;
- typed action references;
- related result, trip, or evidence references;
- provenance, uncertainty, and freshness information;
- fallback-safe presentation state.

This design intentionally does not freeze the final API schema. Search
refinement should first establish the smallest reusable clarification shape;
later assistant capabilities can generalize the envelope from demonstrated
needs.

## Failure And Trust Boundaries

- Structured flows remain usable when the LLM or document retrieval is
  unavailable.
- Domain validation occurs after every AI-proposed action and before any state
  mutation or ranking change.
- The assistant distinguishes verified, forecast, estimated, stale, unknown,
  and retrieved explanatory evidence.
- Prompt-injected content from trip briefs, retrieved documents, or provider
  text is data, not executable instruction.
- Context assembly follows least-context principles and explicit authorization.
- Every user-owned context read and action is scoped to the authenticated owner;
  persistent assistant preferences and state must be inspectable and deletable.
- Observability records bounded operational outcomes, not sensitive prompts or
  user context.

## Evaluation Direction

- Deterministic tests own context scoping, capability authorization, legal typed
  actions, ranking and trip mutations, and fallback behavior.
- Provider tests validate schemas and failure handling with mocked LLM output;
  they do not assert exact generated prose.
- A small versioned scenario set should evaluate interaction usefulness,
  repeated or irrelevant questions, unsupported claims, capability selection,
  and correct search-versus-trip-versus-durable scope.
- Production telemetry may measure bounded outcomes such as interaction type,
  validation result, fallback use, latency, and abandonment. It must not attach
  raw user context, prompts, retrieved passages, or model responses.

## Incremental Adoption

1. Align Search V4 refinement with approved answer vocabulary, dynamic safe
   questions, bounded clarification capability context, deterministically
   validated opportunities, and UI-independent semantics.
2. Introduce shared interaction and context-scope concepts only when a second
   real consumer, such as result explanation or companion, requires them.
3. Add explicit assistant customization for durable preferences independently
   of search refinement.
4. Add an optional conversational surface after typed capabilities and context
   boundaries are proven; do not make chat a prerequisite for core journeys.
5. Add document retrieval only for identified unstructured knowledge needs with
   source and trust requirements.

## Non-Goals

- Designing every future assistant capability or conversation flow.
- Making the LLM the ranking, alerting, catalog, weather, or persistence owner.
- Replacing structured Snowcast screens with a universal chat interface.
- Persisting inferred preferences from search or conversation automatically.
- Choosing a vector database, agent framework, model provider, or long-term
  conversation-memory implementation.
- General travel itinerary generation outside Snowcast's ski-trip scope.

## Decision And Review Gate

- Classification: `review-gated`, full design flow.
- High-risk domains touched: LLM ownership, user context and privacy, Search V4
  refinement semantics, future companion behavior, and cross-product API
  boundaries.
- Developer Decision Checkpoint: resolved by the owner on 2026-07-17. Snowcast
  AI is a cross-product operational orchestration layer, not a chat-centric
  product; durable preferences belong to separate explicit customization.
- ADR status: proposed ADR 0016 records the accepted architectural direction;
  it becomes accepted after written-spec review.
- Advisory design review: completed on 2026-07-17 with Product / Strategy,
  Backend / API, AI / LLM Reliability, and Security & Privacy. Review findings
  about dynamic refinement ownership, preference lifecycle, and evaluation were
  resolved in this draft; no findings remain.

## Acceptance Criteria For The Architecture

- Search refinement can evolve into an assistant interaction without moving
  ranking ownership into the LLM.
- The LLM can select useful registered refinement topics dynamically without a
  fixed question-variant registry.
- Structured search and companion flows work without chat and fail safely
  without an LLM.
- Durable, search-scoped, and trip-scoped context have explicit owners.
- Structured retrieval and document RAG have distinct purposes and trust rules.
- The design guides incremental work without requiring a generic assistant
  platform now.

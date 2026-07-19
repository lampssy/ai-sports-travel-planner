# Feature Spec: Content Language And Refinement Clarity

## Status

- Status: implemented and feature-reviewed on 2026-07-19
- Owner: solo-builder
- Related specs:
  - `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`
  - `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`
  - `docs/superpowers/specs/2026-07-17-snowcast-ai-orchestration-architecture-design.md`
- Related plan:
  `docs/superpowers/plans/2026-07-19-content-language-and-refinement-clarity.md`
- Related ADRs:
  - `docs/architecture/adr/0015-load-search-refinements-after-ranking.md`
  - `docs/architecture/adr/0016-use-ai-as-a-cross-product-orchestration-layer.md`

This spec supersedes the previous Search V4 rule that allowed one to three
topics in one refinement question. Where the related specs or implementation
plan differ, a refinement question now contains exactly one topic.

## User Outcome

A skier can read every important Snowcast question, option, recommendation,
warning, and evidence summary without learning internal ranking or data-model
language. Refinements ask one clear decision at a time, do not repeat a topic
that the user already answered or skipped, and do not fill the search sidebar
with a chip for every interaction.

The experience should let a user answer these questions without relying on
secondary explanatory text:

- What decision is Snowcast asking me to make?
- How do the available answers differ?
- Which preferences are currently affecting my results?
- Why does this trip lead, and what should I be careful about?
- Which values are measured, estimated, or based on limited evidence?
- Where can I inspect detailed sources and calculations if I need them?

## Scope

In scope:

- a first-class `Content & Language` advisory reviewer with slug
  `content-language`;
- `feature-review`, `design-review`, and opt-in `domain-audit` modes for that
  reviewer;
- a product-wide B2-English ceiling for user-facing content;
- one registered topic per Search V4 refinement question;
- topic-level suppression after an answer or skip;
- deterministic reset rules for the current refinement context;
- directly comparable and mutually exclusive options for each question;
- a compact preference summary in the Search V4 context rail;
- plain-language remediation of the active Search V4 results, refinement,
  dossier, error, evidence, and status copy;
- central ownership for reusable copy and registered refinement vocabulary;
- focused automated content-contract and interaction tests;
- a `content-language` domain audit that records remaining product-wide copy
  issues as follow-up work rather than silently expanding this sprint.

Out of scope:

- changes to ranking weights, factor definitions, materiality thresholds,
  candidate eligibility, or recommendation ordering;
- a general chat interface, persistent conversation memory, or unbounded
  LLM-generated copy;
- changing weather, catalog, pass, stay, or travel evidence calculations;
- translating Snowcast into additional languages;
- a full rewrite of current-trip, mobile-companion, homepage, public resort,
  booking, or accommodation surfaces in this implementation slice;
- a generic content-management system or runtime localization framework;
- a new UI component library or dependency.

The reviewer and B2 language standard apply product-wide. The implementation
slice remediates the active Search V4 web and dossier surfaces that exposed the
current problems. Other surfaces enter a prioritized follow-up list only when
the explicit domain audit finds concrete issues.

## Product Fit

Snowcast should sound like a knowledgeable ski-trip planner, not an internal
ranking console or a generic AI assistant. Plain language must preserve the
product's useful distinctions: trip configuration, ski area, stay base, pass,
snow outlook, evidence quality, and uncertainty.

Simplification must not remove material limits. Estimated distances, adjusted
catalog values, limited evidence, month-only climatology, and forecast
freshness remain visible, but their internal storage and trust names do not
belong in primary decision copy.

The product avoids two opposite failures:

- exposing implementation phrases such as `covered terrain domain`,
  `selected pass context`, or `verified_with_adjustment`;
- replacing those phrases with confident marketing language that hides an
  estimate, missing evidence, or uncertainty.

## Content Standard

### B2-English ceiling

All user-facing content should be understandable to a competent non-native
English speaker at approximately B2 level. This is a ceiling, not a target for
complexity. Simpler wording is preferred when it preserves the meaning.

User-facing content must:

- use short, direct, active sentences;
- use familiar words before specialist or abstract alternatives;
- name the subject and decision explicitly;
- keep one main idea per sentence, label, option, or question;
- make a control label understandable without requiring its description;
- use consistent terms for the same product concept;
- explain uncertainty with concrete consequences;
- avoid unnecessary idioms, metaphors, noun stacks, and internal taxonomies;
- avoid joining unrelated answer meanings with `+`;
- avoid asking users to infer the comparison from option descriptions.

Standard ski terms such as `ski area`, `lift pass`, `snowmaking`, `glacier
terrain`, and `apres-ski` are allowed when they are the clearest familiar term.
Proper names, source names, measurements, and legally or technically required
terms are also allowed. Supporting copy should clarify a term when its meaning
may not be obvious in context.

### Progressive disclosure

Primary content answers the decision question. Secondary content explains the
evidence. Technical provenance remains available in an explicit details
disclosure.

Examples:

| Avoid | Prefer in primary content | Optional detail |
| --- | --- | --- |
| `Adjusted 239 km (ski area only)` | `About 239 km covered by this pass` | `Estimated from source data for the selected ski area.` |
| `Adjusted Walk` | `About 324 m walk to the lifts` | `The walking distance is an estimate based on the mapped stay base and lift access point.` |
| `Party skill coverage needs a closer terrain review.` | `Some terrain may not suit every skier in your group.` | Explain which skill level has limited evidence. |
| `Available snow evidence supports the requested travel window.` | `Snow conditions usually fit this month.` | Show historical seasons, snow depth, and temperature when available. |
| `Fallback-heavy` without explanation | `Limited evidence` | Explain which conclusion relies on fallback data. |
| `Backend API is not reachable.` | `Snowcast could not update these results.` | Offer retry and state whether previous results remain visible. |

The exact final wording remains subject to Content & Language and Data Trust
review against the real response data.

## Domain Model

- Bounded contexts touched: AI Orchestration And Assistance, Planning, Web
  Presentation, and the advisory-review operating model.
- Existing durable terms retained: refinement topic, refinement proposal,
  typed preference patch, current search context, recommendation group, trip
  configuration, evidence quality.
- New durable term: `resolved refinement topic`, meaning a registered topic the
  user answered or explicitly skipped in the current refinement context.
- No ranking entity or score changes.

### Refinement state

Each delivered refinement proposal has:

- one stable registered `topic_id`;
- one registered `target_factor_id` used for deterministic preference updates
  and reset behavior;
- one `question_id` that identifies the exact rendered interaction;
- one plain-language question;
- two to five approved options for that topic;
- one plain-language reason explaining why the decision could matter.

Each refinement request returns at most one proposal. After an answer, Snowcast
reranks and requests the next unresolved material topic from the new baseline.
After a skip, Snowcast records the topic and requests the next unresolved topic
from the same valid baseline without reranking. The user can leave the optional
card unanswered at any time. This design adds no arbitrary total-question cap;
the finite registered topic set, topic suppression, materiality validation,
and explicit user choice bound the sequence.

`topic_id` owns repetition control. `question_id` remains useful for exact UI
identity, accessibility announcements, telemetry, and compatibility with the
existing answered-question contract. A changed answer set does not make an
already resolved topic eligible again.

The current refinement context contains a set of resolved topic IDs. A topic
enters that set when the user applies an answer or chooses `Skip for now`.

A resolved topic becomes eligible again only when:

- a successful ordinary search changes the canonical trip brief or any hard
  constraint, which starts a new refinement context; or
- the user manually removes or changes the preference owned by that topic.

Applying another refinement and reranking does not reset resolved topics.
Returning from a dossier does not reset them. A baseline-cache expiry does not
reset them. A provider retry does not reset them.

Manual factor or objective edits clear only resolved topics whose
`target_factor_id` changed. Unrelated manual preference edits preserve the
remaining resolved-topic set. Applying a refinement is not treated as an
ordinary manual edit: it adds the current topic to the resolved set and
preserves every previously resolved topic. Re-submitting an unchanged search
does not reset the set.

### Refinement invariants

- every provider selection and deterministic fallback contains exactly one
  topic;
- at most one question is returned and displayed at a time;
- every option contains exactly one approved answer for that topic;
- option labels are mutually exclusive and directly comparable;
- the question names the decision before the user reads the options;
- a resolved topic is removed before provider invocation and fallback
  selection;
- one topic cannot reappear under a new question ID or answer combination;
- applying a new answer for a factor replaces the previous active preference
  for that factor rather than creating a duplicate visible preference;
- skipped topics affect repetition only and never change ranking intent;
- the LLM selects a registered topic and may phrase a bounded question, but
  authoritative answers and typed patches remain server-owned;
- materiality validation remains deterministic and unchanged.

## Decision And Review Gate

- Classification: `review-gated`, full design flow.
- High-risk domains touched: Search V4 refinement semantics, LLM output
  contract, shared API behavior, ranking-input transparency, evidence wording,
  and user trust.
- Developer Decision Checkpoints:
  - resolved: add `Content & Language` as a first-class reviewer rather than a
    subsection of UI / UX;
  - resolved: support the same `feature-review`, `design-review`, and opt-in
    `domain-audit` modes as other reviewers;
  - resolved: use B2 English as the product-wide maximum complexity level;
  - resolved: ask exactly one topic per refinement question;
  - resolved: suppress answered and skipped topics for the current search
    context;
  - resolved: make a topic eligible again after a materially different search
    or a manual change to its related preference;
  - resolved: compact accumulated preferences in the context rail;
  - resolved: keep technical provenance available in secondary details while
    removing internal labels from primary content;
  - unresolved: none.
- ADR status: no new ADR proposed. This design narrows the interaction contract
  within ADR 0016 and preserves the separate post-ranking request boundary from
  ADR 0015. Revisit if refinement state becomes durable or cross-device.
- Advisory design-review:
  - reviewers: Product / Strategy, Backend / API, UI / UX, AI / LLM
    Reliability, Accessibility, Data Trust & Source Integrity, and a
    provisional Content & Language review using the proposed contract;
  - status: completed on 2026-07-19; no Blocker or High findings remain.
- Advisory feature-review before final handoff:
  - reviewers: Content & Language, Backend / API, UI / UX, AI / LLM
    Reliability, Accessibility, and Data Trust & Source Integrity;
  - status: planned.

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | Reviewer ownership | Language quality recurs across UI, evidence, AI, and product flows. | Keep under UI / UX; add a first-class peer reviewer; create a separate framework. | First-class `Content & Language` peer in the existing framework. | Clear ownership without duplicating review workflow. | Advisory reviewers and playbook. |
| Product / Domain | Language level | Internal language and complex phrasing reduce comprehension. | No formal level; B2 maximum; stricter B1 maximum. | B2 maximum with simpler wording preferred. | Preserves useful ski terms without permitting needless complexity. | Reviewer contract and content standard. |
| Mixed | Question shape | Multi-topic answers can capture the wrong intent and produce artificial labels. | One to three topics; one topic only; free-form follow-up. | Exactly one registered topic per question. | More sequential questions are acceptable because each answer remains precise and optional. | Refinement presentation policy and API contract. |
| Mixed | Repetition boundary | Exact question IDs do not stop the same topic returning in another combination. | Suppress exact questions; suppress topics forever; suppress topics for the current context with explicit reset rules. | Context-scoped topic suppression with reset after a materially different search or related manual preference change. | Prevents repetition without making an old answer permanent. | Domain language and search-session contract. |
| UI / UX | Preference density | Sequential answers currently create a long, noisy chip list. | Show every chip; show a compact summary with full edit access; hide preferences. | Compact summary with full access through the existing adjustment flow. | Keeps applied state visible without allowing the rail to dominate results. | Search V4 web spec. |

## Architecture Decisions

### Advisory framework

`docs/operating-model/advisory-reviewers.md` remains the source of truth. Add a
`Content & Language` reviewer contract with slug `content-language`. Update the
playbook routing table and the existing Snowcast advisory skills so the slug is
available through normal review, audit, and idea workflows. Do not create a new
command or parallel review framework.

The reviewer owns:

- comprehension and naturalness;
- B2 complexity;
- question and option semantics;
- terminology consistency;
- user-visible context and action clarity;
- the boundary between primary plain language and secondary provenance.

It does not own interaction layout, product priority, factual truth, or LLM
safety. Those remain with UI / UX, Product / Strategy, Data Trust, and AI / LLM
Reliability respectively.

Severity guidance:

- **High:** wording can capture the wrong intent, cause an unintended hard
  requirement, materially misstate evidence, or block task completion;
- **Medium:** internal language, missing context, repeated concepts, or option
  semantics make an important decision hard to understand;
- **Low:** isolated grammar, style, or consistency issue with no likely
  decision impact.

### Copy ownership

Use the narrowest authoritative owner:

- refinement questions, answers, descriptions, and traveller-topic vocabulary
  live in a versioned server presentation policy;
- data-dependent result and dossier sentences live in typed presentation
  builders, not JSX fragments;
- reusable status, action, and empty-state copy lives in a small search copy
  module;
- components receive display-ready view models and should not reconstruct
  domain meaning from raw enums;
- source and calculation disclosures may expose more detail, but must translate
  internal enums and calculations into plain language.

Create `search-refinement-presentation-2` rather than silently rewriting the
version-1 vocabulary. Version 2 enforces one topic and the approved language
standard. Version 1 remains readable for tests or compatibility but is no
longer the default.

### Preference summary

The search context rail keeps every hard constraint visible and individually
removable. It shows at most three active preference chips in stable registry
display order, followed by `View all N preferences` when more are active. That
control opens the existing adjustment surface, where every active preference
is visible, editable, and removable.

The full-detail control is a real button with an accessible count and predictable
focus transfer into the adjustment surface. Closing that surface restores focus
to the control. The summary and full list must not rely on color alone to
communicate active state.

The summary represents current factor state, not refinement history. Repeated
updates to one factor therefore occupy one entry. No active preference may be
hidden without the total count and full-detail control being available.

### Provenance presentation

Primary cards and dossier summaries must never display raw trust enums,
calculation implementation labels, or phrases such as `adjusted walk`,
`selected pass context`, or `covered terrain domain`.

When an adjustment or estimate is material, primary content uses an estimate
cue such as `about` or `estimated`. The details disclosure explains the basis
and limitation. Existing trust and source fields remain authoritative; this
change only improves their presentation.

## API And Client Contract

Additive public fields:

- `SearchV4RefinementProposal.topic_id: string`;
- `SearchV4RefinementProposal.target_factor_id: string`;
- `SearchV4RefinementRequest.resolved_topic_ids: string[]`;
- `SearchV4Request.resolved_topic_ids: string[]` for compatibility with its
  existing refinement-generation fields.

Compatibility:

- retain `already_answered_question_ids` during this Search V4 compatibility
  window;
- the backend honors both exact question suppression and topic suppression;
- updated clients send resolved topic IDs and may continue sending answered
  question IDs;
- old clients remain valid but cannot receive the stronger repetition
  guarantee;
- both ID collections are bounded, unique, and treated as untrusted input;
- known current topic IDs suppress matching topics; unknown or retired IDs are
  ignored so a deployment or old client state cannot break refinement;
- the baseline fingerprint and cache ownership from ADR 0015 do not change.

Client state records the topic ID when a question is answered or skipped. It
also records the proposal's target factor so a related manual edit can clear
the correct topic without duplicating the server presentation registry in the
client. It preserves that state through refinement reranks and dossier
navigation. A new baseline caused by applying an answer does not by itself
create a new refinement context.

## AI / LLM Use

Deterministic logic must own:

- eligible-topic filtering;
- topic suppression;
- approved answer copy and typed patches;
- option legality and mutual exclusivity;
- materiality validation;
- fallback selection;
- preference replacement and reranking.

The LLM may select one eligible registered topic and phrase one question using
the approved vocabulary boundary. It cannot pair topics, invent answer labels,
emit raw patches, or decide that a resolved topic is eligible again.

Provider schema changes from `topic_ids` plus answer-ID combinations to one
`topic_id` plus one answer ID per option. Invalid multi-topic output fails
closed and falls back through the existing deterministic path.

The provider and public API each return at most one proposal for a request.
Sequential refinement is driven by a new bounded request after each answer or
skip, not by rendering stale sibling questions generated for the previous
intent.

No additional LLM request, dependency, or model is introduced.

## Data Trust And Source Integrity

- No evidence value or source changes.
- Estimates remain estimates even when internal wording is removed.
- Missing or limited evidence must stay visible in primary content when it can
  change the trip decision.
- Source counts, raw trust enums, and calculation details move behind an
  explicit disclosure; they are not deleted.
- Plain-language summaries must be derived from typed evidence state and must
  not infer stronger certainty than the underlying data permits.

## Security, Privacy, And Abuse

- Resolved topic IDs contain no free-form user content.
- Existing limits on trip briefs and identifier collections remain.
- Raw prompts, answers, and trip briefs stay out of logs, metrics, and traces.
- The new reviewer and copy rules do not change authentication or persistence.

## Observability And Operations

- Preserve existing refinement outcome and latency metrics.
- Add no raw visible copy or user answer text to telemetry.
- Topic IDs may be counted only through an existing bounded, approved metric
  dimension; otherwise keep them out of metrics.
- Provider-invalid multi-topic output uses the existing invalid-output and
  fallback behavior.
- Old clients without resolved topic IDs remain observable through the existing
  answered-question path during compatibility.

## Acceptance Criteria

- Every generated and fallback refinement contains exactly one topic.
- Option labels never contain mechanically combined `A + B` meanings.
- Selecting an option changes only the registered topic's typed factor or
  objective state.
- Answered and skipped topics do not reappear after reranking, provider retry,
  baseline expiry, or dossier navigation.
- A skip requests the next unresolved material topic without reranking when the
  current baseline remains valid.
- An answer reranks before requesting the next unresolved material topic.
- A materially new search resets resolved topics.
- Manually changing or removing the related preference makes that topic
  eligible again.
- Applying multiple sequential refinements does not create duplicate active
  preferences for one factor.
- Hard constraints remain visible in the context rail.
- The rail shows no more than three preference chips and exposes a clear path to
  inspect and edit all active preferences.
- Search V4 results and dossier primary content contain no known internal-only
  phrases from the approved blocked vocabulary.
- Estimate and evidence limitations remain visible after copy simplification.
- Labels and questions are understandable without their descriptions at the
  agreed B2 ceiling.
- Refinement, search, and dossier failure states explain what happened, whether
  previous results are still usable, and the next available action.
- The new `content-language` reviewer can run in all three advisory modes.
- A focused `content-language` domain audit produces a prioritized follow-up
  list without editing code.

## Verification

Unit tests:

- presentation-policy loading and version-2 vocabulary;
- provider schema rejects multiple topics or multiple answers per option;
- deterministic fallback skips resolved topics;
- proposal validation exposes one topic ID;
- request validation bounds and deduplicates resolved topic IDs;
- related preference changes clear only the relevant resolved topic;
- presentation builders translate known trust and provenance states into plain
  language;
- blocked internal phrases do not appear in primary view-model copy.

API and integration tests:

- updated refinement request and response contract;
- compatibility with `already_answered_question_ids`;
- sequential answer, skip, rerank, and next-question flow;
- no repeat after a different answer set is generated for the same topic;
- baseline expiry does not reset client topic state;
- provider failure preserves usable rankings and deterministic fallback.

Frontend tests:

- context rail preference limit and `View all N preferences` behavior;
- preference replacement rather than event-history accumulation;
- answer and skip update resolved topic state;
- manual related-preference removal re-enables the topic;
- unrelated edits do not re-enable it;
- primary dossier and recommendation copy uses plain-language view models;
- status and error copy preserves previous usable state.

Browser acceptance:

- desktop and mobile search-result flows with zero, one, three, and more than
  three preferences;
- three sequential refinements without repeated topics or sidebar overflow;
- dossier navigation and return-to-results state preservation;
- keyboard and screen-reader operation for the preference disclosure and
  refinement options;
- screenshots checked for text overflow, clipped controls, and awkward copy
  wrapping.

### Verification outcome

Implementation verification completed on 2026-07-19:

- backend: Ruff passed and the full suite passed with 2,393 tests;
- frontend: 216 Vitest tests, the production build, and 47 Playwright tests
  passed;
- focused refinement, API, evidence, trust, focus, overflow, and visual tests
  passed after review fixes;
- desktop and 390 px built-app acceptance confirmed sequential answer and skip
  flows, no repeated topics, preserved dossier navigation, no backend error on
  return to results, and no horizontal overflow;
- `mypy` could not run because it is not available in the project environment;
  no dependency was installed without owner approval.

## Documentation Impact

Implementation must align:

- `AGENTS.md` for the new default reviewer routing on language-sensitive work;
- `docs/operating-model/advisory-reviewers.md`;
- `docs/operating-model/review-playbook.md`;
- the Snowcast advisory review, review, audit, and idea skills;
- `docs/domain-language.md` for resolved refinement topics and the one-topic
  invariant;
- `docs/engineering-notes.md` for the durable B2 content and copy-ownership
  convention;
- `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md` where
  its answered-question wording is now narrower than topic suppression;
- the active implementation plan derived after this spec is accepted.

No feature-spec template change is required. The existing template already
captures advisory reviewers and user-facing model wording.

## Advisory Review

- Design reviewers: Product / Strategy, Backend / API, UI / UX, AI / LLM
  Reliability, Accessibility, Data Trust & Source Integrity, and provisional
  Content & Language.
- Feature reviewers: Content & Language, Backend / API, UI / UX, AI / LLM
  Reliability, Accessibility, and Data Trust & Source Integrity.
- Domain audit: Content & Language after the first implementation pass, only
  because the owner explicitly approved broader product-language review.
- Known residual risk: B2 is a review standard, not a mechanically reliable
  readability score. Automated checks can catch banned phrases and structural
  regressions, but human review remains authoritative for naturalness and
  context.

### Design-review outcome

The design review completed on 2026-07-19. No Blocker or High findings remain.
The review produced these spec changes before owner review:

- Backend / API required an explicit `target_factor_id`, defined reset triggers,
  and compatibility behavior for unknown or retired topic IDs.
- UI / UX and Accessibility required one displayed proposal at a time and
  predictable focus transfer for the full preference list.
- AI / LLM Reliability required sequential questions to come from a new
  bounded request rather than stale sibling proposals generated before rerank.
- Data Trust required visible estimate cues in primary copy while detailed
  adjustment provenance remains available secondarily.
- Product / Strategy confirmed that the work strengthens conditions-aware
  planning and does not create generic chat or marketplace scope.
- The provisional Content & Language review confirmed the one-idea question
  and option rules, while retaining human review as the authority for
  naturalness.

Main residual risks:

- existing Search V4 copy is distributed across registry, presentation-builder,
  and component layers, so implementation must inventory the actual rendered
  strings rather than relying only on a blocked-word list;
- sequential one-topic questions may create more turns, but each remains
  optional, materially validated, and bounded by the finite unresolved topic
  set;
- old clients receive compatibility rather than the full topic-level repetition
  guarantee until they send `resolved_topic_ids`.

### Feature-review outcome

Feature review completed on exact implementation head
`2107fcf84f26141f81f3b037a698d2afbc13f09e`. Content & Language, Backend / API,
UI / UX, AI / LLM Reliability, Accessibility, and Data Trust & Source Integrity
reported no remaining defensible findings after the blocking focus and intent
capture issues and the overflow-test gap were fixed. Medium language-polish
opportunities outside the accepted implementation slice are deferred to the
explicit product-wide Content & Language domain audit.

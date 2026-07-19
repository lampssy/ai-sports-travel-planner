# Content Language And Refinement Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class Content & Language advisory, make Search V4 refinements precise and non-repeating, compact accumulated preference state, and replace internal product language with trustworthy B2-level copy.

**Architecture:** Keep deterministic Planning and the versioned refinement-presentation registry authoritative. A refinement response gains stable topic and target-factor identity, while the client owns search-scoped resolved-topic lifecycle and sends it to the separate refinement endpoint. User-facing copy stays in the existing server registry, typed frontend presentation builders, and reusable copy module instead of being reconstructed in components.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, TOML, Gemini structured JSON output, React 18, TypeScript, Vitest, Testing Library, Playwright, Markdown advisory contracts.

## Global Constraints

- Classification: `review-gated`, full design flow.
- Accepted spec: `docs/superpowers/specs/2026-07-19-content-language-and-refinement-clarity-design.md`.
- Ask exactly one registered topic per refinement request and display at most one question at a time.
- Return two to five mutually exclusive options, each containing one approved answer for the selected topic.
- A topic answered or skipped remains suppressed through reranks, provider retries, baseline expiry, and dossier navigation.
- Reset all resolved topics only after a changed trip brief or hard constraint; clear only the related topic after a manual factor or objective change.
- Keep `already_answered_question_ids` for compatibility and add bounded `resolved_topic_ids`.
- Unknown or retired resolved topic IDs are ignored, not treated as request errors.
- The LLM selects an eligible registered topic and phrases its question; it never owns answer copy, typed patches, materiality, ranking, or reset behavior.
- Use the `search-refinement-presentation-2` registry as the new default; do not silently rewrite version 1.
- User-facing content uses B2 English as a maximum complexity level, with simpler language preferred.
- Primary copy must not expose internal trust enums or phrases such as `adjusted walk`, `selected pass context`, or `covered terrain domain`.
- Estimates and evidence limitations remain visible in primary copy; source and calculation detail stays available secondarily.
- Hard constraints remain individually visible; show at most three preference chips and a count-bearing control for the complete list.
- Add no dependency and do not change ranking weights, materiality thresholds, candidate eligibility, or evidence calculations.
- Work test-first for behavior changes. Documentation/configuration-only changes use focused consistency checks.
- Preserve the untracked `.superdesign/` directory and unrelated user changes.
- Use project-scoped GitHub auth with `GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast"` for PR operations.

## Decision Gate Before Execution

- Classification: `review-gated`.
- High-risk domains touched: Search V4 refinement semantics, LLM contract, shared API behavior, ranking-input transparency, evidence wording, and user trust.
- Resolved owner decisions:
  - first-class `Content & Language` reviewer in the existing advisory framework;
  - `feature-review`, `design-review`, and opt-in `domain-audit` modes;
  - product-wide B2-English ceiling;
  - one topic per refinement question;
  - topic-level suppression with explicit search-context reset rules;
  - compact preference summary with full edit access;
  - technical provenance in secondary details rather than primary labels;
  - create a PR after implementation and run the product-wide domain audit against that branch.
- Accepted assumptions: none.
- Unresolved owner decisions: none.
- ADR status: no new ADR. ADR 0015 and ADR 0016 remain authoritative; revisit if refinement state becomes durable or cross-device.
- Advisory design review status: completed on 2026-07-19 with no open Blocker or High findings.

---

### Task 1: Add The Content & Language Advisory Contract

**Files:**

- Modify: `AGENTS.md`
- Modify: `docs/operating-model/advisory-reviewers.md`
- Modify: `docs/operating-model/review-playbook.md`
- Modify: `docs/engineering-notes.md`
- Modify outside repo: `/Users/awownysz/.codex/skills/snowcast-advisory-review/SKILL.md`
- Modify outside repo: `/Users/awownysz/.codex/skills/snowcast-review/SKILL.md`
- Modify outside repo: `/Users/awownysz/.codex/skills/snowcast-audit/SKILL.md`
- Modify outside repo: `/Users/awownysz/.codex/skills/snowcast-idea/SKILL.md`
- Include in first commit: `docs/superpowers/specs/2026-07-19-content-language-and-refinement-clarity-design.md`
- Include in first commit: `docs/superpowers/plans/2026-07-19-content-language-and-refinement-clarity.md`

**Interfaces:**

- Produces reviewer slug `content-language` in all existing advisory entry points.
- Produces the same three modes as every peer reviewer: `feature-review`, `design-review`, and `domain-audit`.
- Keeps `docs/operating-model/advisory-reviewers.md` as the only reviewer-contract source of truth.

- [ ] **Step 1: Add a failing consistency check for the new reviewer slug**

Run this before editing:

```bash
python - <<'PY'
from pathlib import Path

paths = [
    Path("docs/operating-model/advisory-reviewers.md"),
    Path("docs/operating-model/review-playbook.md"),
    Path.home() / ".codex/skills/snowcast-advisory-review/SKILL.md",
    Path.home() / ".codex/skills/snowcast-review/SKILL.md",
    Path.home() / ".codex/skills/snowcast-audit/SKILL.md",
    Path.home() / ".codex/skills/snowcast-idea/SKILL.md",
]
missing = [str(path) for path in paths if "content-language" not in path.read_text()]
assert not missing, f"missing content-language: {missing}"
PY
```

Expected: FAIL and list all six files.

- [ ] **Step 2: Add the reviewer contract and routing**

Add this peer section after UI / UX in `advisory-reviewers.md`:

```markdown
### Content & Language

**Slug:** `content-language`

**Purpose:** Review whether user-facing Snowcast language is natural, direct,
consistent, and understandable to a non-native English speaker at B2 level or
below without hiding evidence limits or changing product meaning.

**Invoke for:**

- refinement questions and answer options
- recommendation, dossier, evidence, weather, and error copy
- new user-visible domain terms or status labels
- broad copy consistency or comprehension audits
- generated or registry-owned presentation vocabulary

**Inspect first:**

- affected rendered surfaces and tests
- `frontend/src/ui/snowcastCopy.ts`
- `frontend/src/search/searchPresentation.ts`
- `app/config/search-refinement/`
- `docs/domain-language.md`
- evidence and trust fields behind the copy

**Questions to answer:**

- Can a user understand the label or question without decoding supporting text?
- Does each sentence, option, or control carry one main idea?
- Are options mutually exclusive, directly comparable, and natural?
- Are internal taxonomies, implementation phrases, and unnecessary idioms absent?
- Are the same product concepts named consistently?
- Does simplification preserve estimates, uncertainty, and evidence limits?

**Blocking conditions:**

- Wording can capture the wrong user intent or create an unintended requirement.
- Primary copy materially overstates evidence or hides a decision-relevant limit.
- Critical actions or errors do not explain what happened and what the user can do.
- Important controls require secondary prose to reveal their meaning.
```

Add `content-language` to every reviewer/domain list in the four skills. Add
`Content / language changes | content-language, ui-ux, data-trust-source-integrity when evidence wording changes` to the playbook routing table. Add a concise AGENTS.md rule that language-sensitive review-gated work routes to the reviewer and that B2 is the default maximum complexity.

- [ ] **Step 3: Record the durable content convention**

Add an engineering note with these boundaries:

```markdown
### User-facing content ownership

- B2 English is the maximum product-language complexity; simpler is preferred.
- Refinement vocabulary is server-owned and versioned.
- Data-dependent recommendation and dossier sentences are built from typed view models.
- Reusable actions, statuses, and empty states use the shared frontend copy module.
- Components do not translate raw trust enums or reconstruct domain meaning.
- Human Content & Language review remains authoritative; readability scores and blocked-word checks are supporting tools only.
```

- [ ] **Step 4: Re-run the consistency check**

Run the Step 1 command again.

Expected: PASS.

Also run:

```bash
rg -n "content-language|B2 English|Content & Language" \
  AGENTS.md docs/operating-model docs/engineering-notes.md \
  "$HOME/.codex/skills/snowcast-advisory-review/SKILL.md" \
  "$HOME/.codex/skills/snowcast-review/SKILL.md" \
  "$HOME/.codex/skills/snowcast-audit/SKILL.md" \
  "$HOME/.codex/skills/snowcast-idea/SKILL.md"
```

Expected: every repo entry point and all four skill wrappers include the new reviewer.

- [ ] **Step 5: Commit the repo-owned contract and accepted design artifacts**

```bash
git add AGENTS.md docs/operating-model/advisory-reviewers.md \
  docs/operating-model/review-playbook.md docs/engineering-notes.md \
  docs/superpowers/specs/2026-07-19-content-language-and-refinement-clarity-design.md \
  docs/superpowers/plans/2026-07-19-content-language-and-refinement-clarity.md
git commit -m "docs: add content language advisory"
```

Do not stage `.superdesign/`. The four user-level skill files are intentionally
outside the repository commit.

---

### Task 2: Make Refinements Single-Topic And Topic-Aware

**Files:**

- Create: `app/config/search-refinement/presentation-v2.toml`
- Modify: `app/config/search-ranking/search-v4.toml`
- Modify: `app/domain/search_policy.py`
- Modify: `app/domain/search_refinement.py`
- Modify: `app/domain/search_refinement_presentation.py`
- Modify: `app/ai/search_refinement.py`
- Modify: `app/domain/search_v4_service.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_search_policy.py`
- Test: `tests/test_search_refinement.py`
- Test: `tests/test_search_refinement_presentation.py`
- Test: `tests/test_ai_search_refinement.py`
- Test: `tests/test_search_refinement_scenarios.py`
- Test: `tests/test_search_v4_models.py`
- Test: `tests/test_search_v4_service.py`
- Test: `tests/test_search_v4_api.py`

**Interfaces:**

- `RefinementProposal` gains `topic_id: str` and `target_factor_id: str`.
- Provider selection changes to one `topic_id` and one `answer_id` per option.
- `generate_refinement_proposals(...)` and fallback construction consume `resolved_topic_ids: frozenset[str]`.
- `SearchV4RefinementProposal` exposes topic and factor identity.
- Both Search V4 request models accept unique `resolved_topic_ids` with maximum length 50.

- [ ] **Step 1: Write failing domain and API tests**

Add tests equivalent to:

```python
def test_refinement_proposal_requires_topic_and_target_factor() -> None:
    proposal = RefinementProposal(
        topic_id="night_skiing",
        target_factor_id="night_skiing",
        question_id="night-skiing",
        question="Would you like night skiing?",
        reason="This can change which trip suits you best.",
        options=_night_skiing_options(),
    )
    assert proposal.topic_id == "night_skiing"


def test_resolved_topic_is_rejected_even_with_new_question_id() -> None:
    proposal = _proposal(topic_id="night_skiing", question_id="new-shape")
    with pytest.raises(RefinementValidationError, match="topic already resolved"):
        validate_refinement_proposal(
            proposal=proposal,
            intent=_intent(),
            candidates=_candidates(),
            policy=_policy(),
            resolved_topic_ids=frozenset({"night_skiing"}),
        )


def test_refinement_request_accepts_unique_resolved_topic_ids() -> None:
    request = SearchV4RefinementRequest(
        intent=_intent(),
        baseline_fingerprint="a" * 64,
        resolved_topic_ids=("night_skiing", "glacier_terrain"),
    )
    assert request.resolved_topic_ids == ("night_skiing", "glacier_terrain")
```

Add a duplicate-ID request test, a fallback-suppression test, a provider-output
test proving `topic_ids` and `answer_ids` are rejected, and a response test
proving `topic_id` and `target_factor_id` are serialized.

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
uv run pytest \
  tests/test_search_refinement.py \
  tests/test_search_refinement_presentation.py \
  tests/test_ai_search_refinement.py \
  tests/test_search_v4_models.py \
  tests/test_search_v4_service.py \
  tests/test_search_v4_api.py -q
```

Expected: FAIL because the topic fields, singular provider schema, and request
collection do not exist.

- [ ] **Step 3: Add topic identity and suppression to deterministic models**

Change the model and validator shape to:

```python
class RefinementProposal(_RefinementModel):
    topic_id: _QuestionId
    target_factor_id: _QuestionId
    question_id: _QuestionId
    question: _BoundedDisplayText
    reason: _BoundedDisplayText
    options: tuple[RefinementOption, ...] = Field(min_length=2, max_length=5)
```

Add `resolved_topic_ids: frozenset[str] = frozenset()` to
`validate_refinement_proposal`. Reject a proposal when its topic is resolved.
Validate that every option targets exactly `target_factor_id`, through either
one factor-preference patch or one objective patch, and never both. Continue to
honor exact `already_answered_question_ids` for compatibility.

- [ ] **Step 4: Introduce presentation policy version 2**

Create `presentation-v2.toml` from the complete version-1 registry, set:

```toml
presentation_policy_version = "search-refinement-presentation-2"
```

Make version 2 the default loader path. Preserve version 1. Rewrite the active
labels and descriptions to satisfy the accepted spec, including:

```text
Use the standard balance -> A balanced choice
Low-key -> Quiet
Keep terrain size secondary -> Terrain size is less important
It doesn't matter -> Not important for this trip
```

Every fallback question names one decision. Every option label is meaningful
without its description. Keep the existing typed patches unchanged.

Add `resolve_answer_id(answer_id: str) -> ResolvedRefinementAnswer` for the
single-topic active path. Retain `resolve_answer_ids` only for reading and
testing version-1 compatibility; active v2 compilation never calls it and
therefore never reaches compound `" + ".join(...)` output. Fallback proposals
set `topic_id=topic.topic_id` and `target_factor_id=topic.factor_id`.

- [ ] **Step 5: Replace the provider schema with singular IDs**

Use this structural shape in `app/ai/search_refinement.py`:

```python
class _RefinementOptionSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    answer_id: _ProviderIdentifier


class _RefinementQuestionSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    topic_id: _ProviderIdentifier
    question: _ProviderDisplayText
    options: Annotated[
        tuple[_RefinementOptionSelection, ...],
        Field(min_length=2, max_length=5),
    ]


class _RefinementOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    questions: Annotated[
        tuple[_RefinementQuestionSelection, ...],
        Field(max_length=1),
    ]
```

Filter `eligible_provider_topics` before prompt construction:

```python
eligible_provider_topics = tuple(
    topic
    for topic in presentation.provider_topics(clarifiable_factor_ids)
    if topic["topic_id"] not in resolved_topic_ids
)
```

Compile each option from `(option.answer_id,)`. Validate that the selected
answer belongs to the selected topic and its factor. Update the system prompt
to prohibit comparisons or paired topics and require one answer ID per option.

- [ ] **Step 6: Make the public Search V4 contract additive and bounded**

Add to both request models:

```python
resolved_topic_ids: tuple[SearchIdentifier, ...] = Field(default=(), max_length=50)
```

Reject duplicates but do not reject unknown registered values. Pass the
collection through routes, service generation, deterministic fallback, and
legacy combined refinement generation. Serialize at most one validated
proposal and include its topic and target factor fields.

Set the active policy values to:

```toml
[refinement]
max_questions = 1
max_options_per_question = 4
max_factor_patches_per_option = 1
```

Keep the Pydantic upper bounds permissive enough to read historical policy
fixtures, but make the active default and tests assert `1`.

- [ ] **Step 7: Run focused tests and verify GREEN**

```bash
uv run pytest \
  tests/test_search_policy.py \
  tests/test_search_refinement.py \
  tests/test_search_refinement_presentation.py \
  tests/test_ai_search_refinement.py \
  tests/test_search_refinement_scenarios.py \
  tests/test_search_v4_models.py \
  tests/test_search_v4_service.py \
  tests/test_search_v4_api.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/config/search-refinement/presentation-v2.toml \
  app/config/search-ranking/search-v4.toml app/domain/search_policy.py \
  app/domain/search_refinement.py app/domain/search_refinement_presentation.py \
  app/ai/search_refinement.py app/domain/search_v4_service.py app/api/routes.py \
  tests/test_search_policy.py tests/test_search_refinement.py \
  tests/test_search_refinement_presentation.py tests/test_ai_search_refinement.py \
  tests/test_search_refinement_scenarios.py tests/test_search_v4_models.py \
  tests/test_search_v4_service.py tests/test_search_v4_api.py
git commit -m "feat: make refinements topic aware"
```

---

### Task 3: Track Resolved Topics Across The Web Search Session

**Files:**

- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/search/searchSession.ts`
- Modify: `frontend/src/search/RefinementCard.tsx`
- Modify: `frontend/src/search/SearchContextRail.tsx`
- Test: `frontend/src/api.test.ts`
- Test: `frontend/src/App.test.tsx`
- Test: `frontend/src/search/searchSession.test.ts`
- Test: `frontend/src/search/RefinementCard.test.tsx`
- Test: `frontend/src/search/SearchContextRail.test.tsx`

**Interfaces:**

- `RefinementProposal` gains `topic_id` and `target_factor_id`.
- Client state uses `ResolvedRefinementTopic = { topicId, targetFactorId, questionId }`.
- Refinement callbacks receive the complete proposal so answer and skip can
  persist topic identity.
- Every refinement request sends both compatibility question IDs and resolved
  topic IDs.

- [ ] **Step 1: Write failing lifecycle tests**

Add tests for these behaviors:

```typescript
test("skipping a topic requests the next question from the same baseline", async () => {
  // Resolve the first refinement response, click Skip this question, and assert
  // a second /api/search/refinements request uses the same baseline fingerprint
  // with resolved_topic_ids containing the skipped topic.
});

test("reranking preserves all resolved topics", async () => {
  // Apply one answer, return a new ranking baseline, and assert the next
  // refinement request contains the previously resolved topic ID.
});

test("changing one related preference re-enables only its topic", () => {
  const next = clearResolvedTopicsForManualChange(resolved, {
    changedFactorIds: new Set(["night_skiing"]),
    startsNewContext: false,
  });
  expect(next.map((item) => item.topicId)).toEqual(["glacier_terrain"]);
});

test("a changed hard constraint starts a new refinement context", () => {
  expect(
    clearResolvedTopicsForManualChange(resolved, {
      changedFactorIds: new Set(),
      startsNewContext: true,
    }),
  ).toEqual([]);
});
```

Update fixtures to include `topic_id` and `target_factor_id`.

- [ ] **Step 2: Run the focused frontend tests and verify RED**

```bash
npm --prefix frontend test -- \
  src/api.test.ts src/App.test.tsx src/search/searchSession.test.ts \
  src/search/RefinementCard.test.tsx src/search/SearchContextRail.test.tsx
```

Expected: FAIL because topic fields and lifecycle state do not exist.

- [ ] **Step 3: Add typed topic state and request serialization**

Add:

```typescript
export interface RefinementProposal {
  topic_id: string;
  target_factor_id: string;
  question_id: string;
  question: string;
  reason: string;
  options: RefinementOption[];
}

export interface ResolvedRefinementTopic {
  topicId: string;
  targetFactorId: string;
  questionId: string;
}
```

Derive request arrays from this one state collection:

```typescript
const resolvedTopicIds = resolvedTopics.map((item) => item.topicId);
const answeredQuestionIds = resolvedTopics.map((item) => item.questionId);
```

Keep resolved state in `PreviousSearchState` so Undo restores the exact prior
refinement context.

- [ ] **Step 4: Make answer and skip sequential**

Change the card contract to:

```typescript
onApply: (refinement: RefinementProposal, option: RefinementOption) => void;
onSkip: (refinement: RefinementProposal) => void;
```

On answer, upsert the topic, rerank if intent changes, and let the successful
search request the next topic from the new baseline. If the chosen option keeps
the same intent, request the next topic from the existing baseline.

Make skip asynchronous: upsert the topic, dismiss the card, and call
`loadRefinements` with the current response, brief, and next topic state. Use
`Skip this question` as the action label because the topic does not return in
the current context.

- [ ] **Step 5: Implement deterministic reset rules**

Create a pure helper:

```typescript
export function clearResolvedTopicsForManualChange(
  current: ResolvedRefinementTopic[],
  change: { changedFactorIds: Set<string>; startsNewContext: boolean },
): ResolvedRefinementTopic[] {
  if (change.startsNewContext) return [];
  return current.filter(
    (item) => !change.changedFactorIds.has(item.targetFactorId),
  );
}
```

Use canonical applied session state to distinguish:

- changed brief, location, travel window, lodging budget, stay quality, travel
  origin/limit, or skill -> new context, clear all;
- manual factor preference or objective change -> clear matching target factor;
- refinement apply, dossier navigation, retry, or unchanged submit -> preserve;
- chip removal uses the chip action to choose all-versus-related reset.

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
npm --prefix frontend test -- \
  src/api.test.ts src/App.test.tsx src/search/searchSession.test.ts \
  src/search/RefinementCard.test.tsx src/search/SearchContextRail.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/App.tsx \
  frontend/src/search/searchSession.ts frontend/src/search/RefinementCard.tsx \
  frontend/src/search/SearchContextRail.tsx frontend/src/api.test.ts \
  frontend/src/App.test.tsx frontend/src/search/searchSession.test.ts \
  frontend/src/search/RefinementCard.test.tsx \
  frontend/src/search/SearchContextRail.test.tsx
git commit -m "feat: preserve refinement topic decisions"
```

---

### Task 4: Compact The Search Preference Summary

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/search/SearchContextRail.tsx`
- Modify: `frontend/src/search/SearchFiltersDrawer.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/search/SearchContextRail.test.tsx`
- Test: `frontend/src/search/SearchFiltersDrawer.test.tsx`
- Test: `frontend/src/App.test.tsx`

**Interfaces:**

- Hard constraints keep the existing removable-chip behavior.
- Preferences show at most three removable chips.
- More than three active preferences produce a `View all N preferences` button
  that opens the existing drawer and returns focus to that exact trigger.

- [ ] **Step 1: Write failing summary and focus tests**

Add tests equivalent to:

```typescript
test("shows three preferences and a full-list count", async () => {
  renderRailWithPreferences(5);
  const preferences = screen.getByRole("group", { name: "Preferences" });
  expect(within(preferences).getAllByRole("button", { name: /^Remove / })).toHaveLength(3);
  expect(screen.getByRole("button", { name: "View all 5 preferences" })).toBeVisible();
});

test("returns drawer focus to the full-list trigger", async () => {
  const user = userEvent.setup();
  const trigger = screen.getByRole("button", { name: "View all 5 preferences" });
  await user.click(trigger);
  await user.click(screen.getByRole("button", { name: "Close filters" }));
  expect(trigger).toHaveFocus();
});
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
npm --prefix frontend test -- \
  src/search/SearchContextRail.test.tsx \
  src/search/SearchFiltersDrawer.test.tsx src/App.test.tsx
```

Expected: FAIL because all preferences render and drawer return focus is fixed
to the Adjust button.

- [ ] **Step 3: Limit visible preferences and expose the total**

In `SearchContextRail`, use:

```typescript
const visiblePreferences = preferences.slice(0, 3);
const hasHiddenPreferences = preferences.length > visiblePreferences.length;
```

Render `ContextGroup` with `visiblePreferences`. When hidden preferences exist,
render a text button whose accessible and visible label is
`View all ${preferences.length} preferences`.

- [ ] **Step 4: Make drawer return focus trigger-specific**

Change the open callback to accept the actual trigger:

```typescript
onOpenFilters: (trigger: HTMLButtonElement) => void;
```

Pass `event.currentTarget` from both Adjust and View-all controls. Store it in
a mutable `drawerReturnFocusRef` in `App` and pass that ref to
`SearchFiltersDrawer`. Keep Escape, backdrop, and close-button restoration
behavior unchanged.

Ensure the drawer's active-preference controls show all current factor and
objective choices; do not create a second preference editor.

- [ ] **Step 5: Add stable responsive styling**

Add a compact footer/action row within the preference group. Keep its button
height stable, allow the count label to wrap at narrow widths, and do not place
a new card inside the context rail.

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
npm --prefix frontend test -- \
  src/search/SearchContextRail.test.tsx \
  src/search/SearchFiltersDrawer.test.tsx src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/search/SearchContextRail.tsx \
  frontend/src/search/SearchFiltersDrawer.tsx frontend/src/styles.css \
  frontend/src/search/SearchContextRail.test.tsx \
  frontend/src/search/SearchFiltersDrawer.test.tsx frontend/src/App.test.tsx
git commit -m "feat: compact active search preferences"
```

---

### Task 5: Replace Internal Search And Dossier Language

**Files:**

- Modify: `frontend/src/ui/snowcastCopy.ts`
- Modify: `frontend/src/search/searchPresentation.ts`
- Modify: `frontend/src/search/DecisionEvidenceLedger.tsx`
- Modify: `frontend/src/search/DossierVerdict.tsx`
- Modify: `frontend/src/search/TripConfigurationDetails.tsx`
- Modify: `frontend/src/api.ts`
- Test: `frontend/src/search/searchPresentation.test.ts`
- Test: `frontend/src/search/DecisionEvidenceLedger.test.tsx`
- Test: `frontend/src/search/RecommendationDossier.test.tsx`
- Test: `frontend/src/api.test.ts`
- Create test: `frontend/src/search/contentLanguage.test.ts`

**Interfaces:**

- Shared evidence-quality and status labels stay in `snowcastCopy.ts`.
- Typed data-dependent copy stays in `searchPresentation.ts`.
- JSX components render display-ready copy and do not translate trust enums.
- Technical details remain available through the existing disclosure.

- [ ] **Step 1: Write failing copy-contract tests**

Test actual presentation outputs, not raw source text alone:

```typescript
const INTERNAL_PRIMARY_PHRASES = [
  "adjusted walk",
  "selected pass context",
  "covered terrain domain",
  "uncertainty kept explicit",
  "closer terrain review",
  "fallback-heavy",
  "backend api",
];

test.each(primaryPresentationFixtures())(
  "keeps internal language out of $name",
  ({ renderedCopy }) => {
    const normalized = renderedCopy.join(" ").toLowerCase();
    for (const phrase of INTERNAL_PRIMARY_PHRASES) {
      expect(normalized).not.toContain(phrase);
    }
  },
);
```

Add focused expectations for:

```text
About 239 km covered by this pass
About 324 m walk to the lifts
Some terrain may not suit every skier in your group.
Limited evidence
Why this trip
Why Snowcast recommends this trip, including important limits.
Snowcast could not update these results.
```

Also assert that an estimated or adjusted value retains `About` or `Estimated`
in primary presentation and retains a plain provenance sentence in technical
details.

- [ ] **Step 2: Run focused copy tests and verify RED**

```bash
npm --prefix frontend test -- \
  src/search/searchPresentation.test.ts \
  src/search/DecisionEvidenceLedger.test.tsx \
  src/search/RecommendationDossier.test.tsx src/api.test.ts \
  src/search/contentLanguage.test.ts
```

Expected: FAIL on the current internal phrases.

- [ ] **Step 3: Centralize reusable labels and statuses**

Update `evidenceQualityCopy.fallbackHeavy` to:

```typescript
fallbackHeavy: {
  label: "Limited evidence",
  description: "Some parts of this recommendation rely on limited data.",
},
```

Keep errors action-scoped. A failed update says what failed, whether prior
results remain, and how to retry. Do not surface `backend`, `API`, model
versions, or service-startup assumptions in product copy.

- [ ] **Step 4: Rewrite typed terrain, access, and evidence presentation**

Use estimate cues instead of internal prefixes:

```typescript
function approximatePrefix(trust: TrustStatus): string {
  return trust === "estimated" || trust === "verified_with_adjustment"
    ? "About "
    : "";
}
```

Primary terrain copy uses `About N km covered by this pass` for estimated or
adjusted data and `N km covered by this pass` for verified pass-scoped data.
When the scope is narrower, say `About N km in the selected ski area` or
`About N km in the connected area covered by this pass`. Technical details say
why the value is estimated and which scope it covers.

Primary access copy uses `About N m walk to the lifts`, `About N min by shuttle`,
or the corresponding verified form. It never says `Adjusted Walk`.

Replace the skill watchout with `Some terrain may not suit every skier in your
group.` Replace the decision-evidence introduction with `Why Snowcast recommends
this trip, including important limits.` Rewrite pass and access support
sentences as direct statements about the selected trip.

- [ ] **Step 5: Keep source truth visible in secondary details**

Translate trust states as:

```text
verified -> Based on source data.
verified_with_adjustment -> Estimated from source data for this trip configuration.
estimated -> Estimated from available catalog data.
needs_source -> Source confirmation is still needed.
```

Do not remove source links, provenance summaries, evidence warnings, missing
states, or the `Sources and calculation details` disclosure.

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
npm --prefix frontend test -- \
  src/search/searchPresentation.test.ts \
  src/search/DecisionEvidenceLedger.test.tsx \
  src/search/RecommendationDossier.test.tsx src/api.test.ts \
  src/search/contentLanguage.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/ui/snowcastCopy.ts \
  frontend/src/search/searchPresentation.ts \
  frontend/src/search/DecisionEvidenceLedger.tsx \
  frontend/src/search/DossierVerdict.tsx \
  frontend/src/search/TripConfigurationDetails.tsx frontend/src/api.ts \
  frontend/src/search/searchPresentation.test.ts \
  frontend/src/search/DecisionEvidenceLedger.test.tsx \
  frontend/src/search/RecommendationDossier.test.tsx frontend/src/api.test.ts \
  frontend/src/search/contentLanguage.test.ts
git commit -m "fix: clarify search decision language"
```

Stage only files that actually changed.

---

### Task 6: Align Durable Docs And Verify The Complete Change

**Files:**

- Modify: `docs/domain-language.md`
- Modify: `docs/search-ranking-model.md`
- Modify: `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`
- Modify: `docs/superpowers/specs/2026-07-19-content-language-and-refinement-clarity-design.md`
- Modify: `docs/superpowers/plans/2026-07-19-content-language-and-refinement-clarity.md`
- Modify only if setup changes: `README.md`

**Interfaces:**

- Documents `resolved refinement topic` and the one-topic invariant.
- Marks the accepted spec implemented only after verification and feature review.
- Leaves ADR 0015 and ADR 0016 unchanged.

- [ ] **Step 1: Update domain and model documentation**

Add to `docs/domain-language.md`:

```markdown
- resolved refinement topic: a registered clarification topic answered or
  skipped in the current search context; it remains suppressed until the
  context changes or its related preference is manually changed
```

Replace prior multi-topic wording in `docs/search-ranking-model.md` and the Web
Experience spec. Document one question per request, topic-versus-question
identity, sequential answer/skip behavior, compatibility IDs, and reset rules.

- [ ] **Step 2: Run backend quality gates**

```bash
uv run ruff check app tests
uv run mypy app
uv run pytest -q
```

Expected: all commands PASS.

- [ ] **Step 3: Run frontend quality gates**

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: PASS with no TypeScript or Vite build errors.

- [ ] **Step 4: Run focused browser acceptance**

Start the built app using the repo convention:

```bash
./scripts/run-built-app.sh
```

Run the relevant Playwright suite or focused tests for homepage, results,
refinement, and dossier. Manually verify desktop and 390 px mobile widths for:

```text
- one refinement topic at a time
- answer then next question
- skip then next question
- no repeated topic
- no more than three preference chips
- View all N preferences and focus return
- recommendation and dossier primary copy
- estimate and limited-evidence cues
- no text overlap, clipping, or inaccessible icon-only action
```

Capture screenshots under `.superpowers/sdd/`; do not add generated screenshots
to git.

- [ ] **Step 5: Run advisory feature reviews on the exact head**

Run these reviewers in `feature-review` mode:

```text
content-language
backend-api
ui-ux
ai-llm-reliability
accessibility
data-trust-source-integrity
```

Fix every Blocker and High finding, rerun affected tests, and obtain a fresh
review of the exact fixed head. Record Medium/Low follow-ups in the audit or
product backlog rather than silently expanding scope.

- [ ] **Step 6: Mark implementation artifacts complete**

Set the spec status to implemented with the verification and advisory-review
date. Check every completed plan checkbox. Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors and no accidental `.superdesign/` staging.

- [ ] **Step 7: Commit**

```bash
git add docs/domain-language.md docs/search-ranking-model.md \
  docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md \
  docs/superpowers/specs/2026-07-19-content-language-and-refinement-clarity-design.md \
  docs/superpowers/plans/2026-07-19-content-language-and-refinement-clarity.md
git commit -m "docs: finalize refinement language contract"
```

---

### Task 7: Create The Draft PR And Run The Product-Wide Domain Audit

**Files:**

- Create: `docs/advisory-reviews/2026-07-19-content-language-domain-audit.md`
- Modify: pull-request body after the report is pushed

**Interfaces:**

- Produces one draft PR from `codex/content-language-refinement-clarity` to
  `main`.
- Produces a `content-language` domain audit across the whole product.
- Keeps audit recommendations in the same PR without implementing them until
  the owner reviews the audit.

- [ ] **Step 1: Push the verified branch and create a draft PR**

```bash
export GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast"
unset GH_TOKEN GITHUB_TOKEN
git push -u origin codex/content-language-refinement-clarity
gh pr create --repo lampssy/ai-sports-travel-planner --base main \
  --head codex/content-language-refinement-clarity --draft \
  --title "Improve refinement clarity and product language" \
  --body-file /tmp/snowcast-content-language-pr.md
```

The body must summarize user outcomes, API compatibility, verification,
Decision and Review Gate, and how to test locally.

- [ ] **Step 2: Run the explicit product-wide domain audit**

Use `snowcast-advisory-review` in `domain-audit` mode with reviewer
`content-language`. Inspect at minimum:

```text
homepage and search parsing
Search V4 constraints, preferences, refinements, cards, errors, and states
dossier, weather evidence, scoring details, accommodation handoff
current-trip web surface
public resort pages
mobile companion copy
backend user-visible API errors
README/product usage copy where it affects users
```

Use the required domain-audit format: current strengths, risks/gaps, top
opportunities, and suggested next actions. Ground every proposed change in a
file path or rendered surface and distinguish decision-impacting language from
style-only polish.

- [ ] **Step 3: Save the audit report without implementing its recommendations**

Create:

```markdown
# Content & Language Domain Audit

Date: 2026-07-19
Mode: domain-audit
Scope reviewed: whole Snowcast product

## Current Strengths

Record the strongest current language patterns with file or rendered-surface
evidence.

## Risks And Gaps

List concrete user-comprehension or decision risks, ordered by severity and
grounded in file or rendered-surface evidence.

## Top Opportunities

Prioritize the changes with the largest comprehension and trust benefit.

## Suggested Next Actions

Separate immediate fixes, grouped follow-up work, and style-only polish.

## Deferred Pending Owner Review

List every recommendation that has not been implemented in this PR.
```

The report may recommend changes but must not modify product code in this step.

- [ ] **Step 4: Commit and push the audit to the same PR**

```bash
git add docs/advisory-reviews/2026-07-19-content-language-domain-audit.md
git commit -m "docs: add product language domain audit"
git push
```

Update the draft PR body with a link to the audit report and state that audit
fixes are pending owner selection.

- [ ] **Step 5: Report PR and audit state**

Return the PR URL, exact head SHA, check status, audit report path, top audit
findings, and the local validation command. Do not mark the PR ready or merge it.

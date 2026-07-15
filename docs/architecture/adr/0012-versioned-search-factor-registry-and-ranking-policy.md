# ADR 0012: Use A Versioned Search Factor Registry And Ranking Policy

Status: accepted
Date: 2026-07-10

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`
- `docs/superpowers/specs/2026-07-13-trip-window-weather-forecast-evidence-design.md`

Related docs:
- `docs/search-ranking-model.md`
- `docs/planning-model.md`
- `docs/data-trust-model.md`
- `docs/domain-language.md`
- `docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md`
- `docs/architecture/adr/0013-versioned-forecast-runs-and-latest-run-serving.md`

## Context

Search V3 has a small hardcoded component dictionary and a narrow filter
contract. Recent catalog curation added source-aware facts for terrain
facilities, marked freeride routes, night skiing, ski-day apres, stay-base
character, and local apres. Future planning may also have time-scoped
predictions for open pistes, open lifts, and snow coverage.

Adding every new signal directly to the scorer would scatter model semantics,
make the score harder to explain, allow the score range to drift, and risk
rewarding destinations merely because they have more populated fields. Keeping
weights only in prose would make documentation and runtime behavior diverge.
Letting an LLM decide weights or ranking would make recommendations
non-reproducible and would cross the Planning and AI Assistance boundary.

Search also needs adaptive follow-up questions. Predefining every possible
question variant would be brittle because one useful question may contrast any
combination of registered factors. Fully unconstrained LLM questions would be
equally unsafe if their answers could create arbitrary filters or weights.

## Decision

Search V4 will use five cooperating boundaries.

1. **Declarative versioned policy**

   A human-readable policy file, initially targeted as
   `app/config/search-ranking/search-v4.toml`, is the executable source of truth
   for factor and constraint metadata, group and factor weights, lifecycle,
   activation, roles, controlled values, trust and missing-data behavior,
   evidence mode and readiness rules, typed factor composition, importance
   multipliers, correlation caps, and clarification-impact policy.
   The policy contains no provider calls or executable business expressions.

   Search responses expose separate search-model and ranking-policy versions. A
   reviewed weight or activation change increments the policy version without
   implying that the API or scorer algorithm changed.

2. **Typed evaluator registry**

   Stable factor IDs map to typed code evaluators. Evaluators derive one
   candidate's raw value, normalized utility, trust or confidence, scope, and
   explanation inputs. Static catalog, catalog-derived, planning-evidence,
   weather, and future operational-prediction evaluators use the same result
   contract while preserving their distinct provenance and freshness.

3. **Generic deterministic grouped scorer**

   Constraints are evaluated before ranking. The scorer combines registered
  factor evaluations using the exact grouped equation published in
  `docs/search-ranking-model.md`. Group budgets remain bounded, optional
  group-specific maximum effective shares are enforced during normalization,
  factors are normalized inside their group, and related signals may share an
  explicit correlation cap. The score is deterministic, bounded, versioned,
  and described as fit rather than probability.

   Correlation policy produces visible effective weights before group
   aggregation. Per-result breakdowns expose actual factor contributions, while
   the generated policy report exposes default maximum contributions.

   Bounded policy-defined group-priority multipliers allow user priorities to
   change a group's share of the overall score. The LLM may select a controlled
   importance label but cannot supply its numeric multiplier.

4. **Bounded LLM refinement proposals**

   The LLM may choose which registered factors are worth clarifying and may
   dynamically compose question text, answer options, reasons, and typed
   preference patches. No question-variant registry is required. Deterministic
   code validates all factors, operations, values, coverage, repetition, and
   simulated ranking impact before showing a proposal. The LLM cannot provide
   weights, utilities, trust, candidate scores, or catalog facts. Search remains
   functional when no proposal is produced.

   User briefs are untrusted planning text and cannot override the structured
   contract. Candidate summaries, available factors, proposals, answer options,
   retries, and simulated reranks are bounded by policy. Simulation reuses
   existing evaluations and performs no remote call per option.

5. **Generated model visibility**

   `docs/search-ranking-model.md` is the prominent human-readable model. A
   policy-explanation command will render the active model version, exact
   equation, group weights, factor count, factor weights, maximum
   contributions, roles, lifecycle, missing-data policy, and evaluator status.
   CI will verify that generated inventory matches the active policy.

The following semantic rules are part of the decision:

- constraints and ranking factors remain separate even when one capability can
  serve both roles;
- `prefer` and `avoid` are ranking instructions, `ignore` deactivates a factor,
  and `require` becomes a typed eligibility constraint;
- unknown is not unavailable;
- weak trust moves a factor toward its declared neutral or fallback utility;
- evidence readiness is factor-shaped rather than one universal completeness
  threshold: comparative factors need coverage, positive-presence factors need
  enough verified positives, categorical factors need trusted match variation,
  and prediction factors retain time-scoped confidence policy;
- sparse verified positive features may reward an explicit preference while
  unknown remains neutral; catalog silence never becomes verified absence;
- a registered capability may modify another factor only through a named typed
  composition rule visible in policy and breakdowns; snowmaking resilience is
  the initial case and has no hidden independent weight;
- planned, diagnostic, and measured-not-ranked factors cannot affect production
  ranking;
- adding a factor redistributes a stable group budget rather than increasing
  the maximum score;
- clarification eligibility is independent from initial score activation, so
  every runtime-ready `clarifiable` factor may be proposed even when its
  `when_requested` or `objective_selected` activation is currently inactive;
- Search V4 directly replaces Search V3 through `POST /api/search`; the old GET
  contract, hardcoded scorer, model-selection flags, and V3-only tests are
  removed without a compatibility or shadow path;
- predicted operational factors remain time-scoped planning evidence and never
  become slow-changing catalog facts merely because they share the registry.

Initial numeric weights are deliberately not fixed by this ADR because they are
versioned product policy rather than architecture. The owner-approved initial
values live in `docs/search-ranking-model.md` and the Search V4 feature spec;
future changes still require a policy-version diff and golden ranking scenarios.
The initial evidence-mode readiness rules live in
`docs/search-ranking-model.md`. Future activation thresholds and promotion of
new factor families remain versioned reviewed policy decisions.

## Consequences

Benefits:

- The owner can inspect one policy and one generated document to understand
  every active factor and its maximum influence.
- New factors have a standard path from planned to diagnostic, measured, and
  active without redesigning the scorer.
- Group budgets and correlation rules reduce score inflation and
  double-counting.
- Catalog trust and prediction confidence become explicit scoring inputs.
- LLM-generated refinements can be conversational and combinatorial without
  granting the LLM ranking authority.
- Search behavior remains reproducible and supports golden scenario tests.
- Search V4 directly replaces the unused Search V3 contract and implementation;
  no compatibility endpoint, runtime model switch, shadow comparison, or V3
  rollback path is retained.

Costs and constraints:

- Policy parsing, schema validation, generated documentation, and registry
  completeness checks add implementation work.
- Factor normalization and neutral utilities require deliberate product-policy
  decisions; a registry cannot make weak semantics trustworthy.
- Impact simulation and an optional LLM call add latency that must remain
  bounded and must reuse existing factor evaluations.
- Versioned policy changes need review because changing a weight changes
  durable recommendation behavior even without code changes.
- Configuration cannot express arbitrary factor logic; new behavior still
  requires typed evaluator code and tests.

## Alternatives Considered

- **Continue the hardcoded Search V3 scorer.** Simple for a few factors, but it
  scatters future policy, inflates the score as factors are added, and makes a
  complete active-factor audit difficult.
- **Make documentation the canonical policy and duplicate values in code.**
  Easy to read, but inevitably vulnerable to runtime/documentation drift.
- **Use a flat weighted sum.** Easy to state, but adding another correlated or
  well-curated factor changes total influence and can reward data completeness
  rather than user fit.
- **Put all evaluator expressions in configuration.** Maximally declarative,
  but creates an unsafe mini-language, weakens typing, and makes domain logic
  harder to test and refactor.
- **Let the LLM rank candidates or assign weights.** Conversationally flexible,
  but non-deterministic, hard to audit, and incompatible with the Planning
  boundary.
- **Predefine every clarification question variant.** Deterministic but brittle;
  it cannot anticipate useful combinations of factors or natural ambiguity in
  future briefs.
- **Let the LLM generate unconstrained questions and filters.** Flexible but
  allows unsupported operations and cannot guarantee that an answer maps to
  valid, useful, deterministic behavior.
- **Run Search V3 and Search V4 in parallel.** Useful for an established product
  migration, but unnecessary here because there are no users or external API
  consumers. Reviewed golden scenarios define intended behavior directly.

## Revisit When

- Search learns a calibrated ranking model from sufficient representative user
  preference and outcome data.
- Factor count or request-path cost makes in-process evaluation unsuitable.
- A policy-management UI or experimentation platform becomes necessary.
- Operational predictions require a different confidence-composition model
  from static and weather-derived evidence.
- Search preferences become user-persisted or personalized across trips.
- A later model demonstrates that grouped weighted utility cannot express an
  important, evidence-backed ranking interaction transparently.

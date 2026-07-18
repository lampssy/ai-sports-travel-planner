# ADR 0015: Load Search Refinements After Ranking

Status: accepted
Date: 2026-07-17
Updated: 2026-07-18

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-16-search-v4-hybrid-results-design.md`
- `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`

Related docs:
- `docs/search-ranking-model.md`
- `docs/superpowers/plans/2026-07-17-search-v4-trust-and-ui-polish.md`

Related ADRs:
- `docs/architecture/adr/0016-use-ai-as-a-cross-product-orchestration-layer.md`

## Context

Search V4 currently generates optional LLM-assisted refinement questions inside
`POST /api/search`. Ranking therefore waits for a remote Gemini request even
though the ranked response is complete and useful without a follow-up question.
The provider call has variable network and inference latency, structured output
may require validation or recovery, and provider failure should not make search
appear unavailable.

Refinement materiality still depends on server-owned candidate evaluations and
variant ranking. Moving that logic to the browser or sending internal candidate
state to the client would weaken the ranking boundary. Rerunning deterministic
search for the refinement request can also evaluate a different catalog,
weather, model, or policy state from the ranking the user is viewing. A public
baseline fingerprint can identify a handoff, but it is not by itself a trusted
proof that the caller supplied the same canonical intent or that the exact
evaluated baseline still exists.

Snowcast currently runs as one application instance. It therefore needs a
short-lived exact-view handoff, not durable search-session persistence. A later
owner checkpoint resolved that exact preview/apply consistency requires the
handoff to retain the evaluator inputs used by the delivered ranking, rather
than only utilities calculated under the original intent.

## Decision

`POST /api/search` remains the ranking-only endpoint and does not invoke an LLM.
After deterministic ranking, it returns a complete Search V4 result with the
canonical `applied_intent` and stores a typed evaluated-baseline snapshot in the
web process.

The snapshot contains the canonical intent SHA-256 digest, the public baseline
fingerprint, policy and compact baseline scores, constraint facts, and the exact
in-memory static and weather evaluator inputs used for each retained candidate.
Those replay inputs include immutable candidate catalog entities, trust
resolver state, normalized weather rows, selected numeric bounds, and evaluator
contexts. They do not include the full `SearchIntent` or origin text, trip
brief, provider credentials, prompts, tokens, responses, or other provider
secrets. The state is process-local and is not serialized or persisted.

The store is thread-safe and process-local, uses LRU eviction, expires entries
60 seconds after insertion, and holds at most 64 entries. The limit is a server
handoff window for starting refinement generation, not a user answer timeout.
The store records bounded `hit`, `miss`, `expired`, and `evicted` outcomes
without attaching intent, brief, fingerprint, candidate, or client identifiers.

After results render, the web client calls `POST /api/search/refinements` with
the canonical applied intent, public baseline fingerprint, brief, and already
answered question IDs. The endpoint reads the exact stored baseline. A usable
handoff must match the stored fingerprint and the SHA-256 digest recomputed from
the request's canonical intent. Canonical serialization defines the equality
binding; no full intent is stored and no separate typed-equality check occurs.
The public fingerprint alone is never trusted. The endpoint generates and
validates optional refinement proposals from that snapshot. For every answer
variant it rebinds the retained contexts to the variant `SearchIntent`, calls
the same registered static and weather factor evaluators as ranking, and then
scores those replayed evaluations. Replayed static snowmaking evidence is
supplied to the existing weather evaluator so cross-factor trip-window snow
effects remain exact. Refinement never reruns candidate acquisition, catalog
loading, climatology or forecast repository queries, routing, or any
provider/network acquisition.

A cache miss, expired entry, fingerprint or canonical-intent digest mismatch,
or process restart returns the typed `temporarily_unavailable` refinement
outcome. These paths do not rerun deterministic search and do not invoke Gemini.
The ranked response remains usable, and a deliberate ranking refresh creates a
new snapshot and handoff.

The complete refinement endpoint has a five-second monotonic deadline measured
from ingress, including snapshot lookup, provider work, and fallback validation.
The single provider attempt receives only the remaining budget. The UI changes
its loading message after 2.5 seconds but continues waiting until the hard
deadline. A provider or output failure may use only the existing
deterministically validated material fallback; ranked results remain usable.
When the captured policy sets `max_questions = 0`, the endpoint returns
`not_needed` before constructing a provider client or attempting deterministic
fallback.

Once a question has been delivered, its typed answer remains applicable after
the snapshot expires. Applying an answer reruns the full ranking search with the
updated intent, stores a new evaluated-baseline snapshot, renders that ranking,
and immediately requests the next refinement from the new snapshot. Unanswered
questions from the previous baseline are not carried forward.

The anonymous endpoint has an application-local admission guard for the current
single-machine deployment: at most two concurrent requests, at most six
requests per minute per client, and burst capacity two. Rejections occur before
snapshot lookup or Gemini and return a bounded `429`. Client identity is never a
metric label or application log field. The guard is intentionally per-machine
and resets on restart; a shared limiter is deferred until Snowcast scales beyond
one machine.

During client migration, `/api/search` continues to accept the legacy `brief`,
`generate_refinements`, and `already_answered_question_ids` fields but ignores
them, and its response retains `refinements: []`. This prevents existing mobile
and browser clients from failing while the web moves to the separate endpoint.
Derived intent values remain plain domain properties rather than Pydantic API
fields, and the web client independently projects typed objects back to the
request schema before posting them. This makes the compatibility boundary
explicit on both sides instead of relying on structural similarity between
response and request objects.

Accepted ADR 0016 supersedes and refines only this ADR's original
provider-boundary clause; the endpoint deadline, snapshot lifecycle, and
admission limits above remain unchanged. The refinement LLM emits bounded
registered factor or objective topic IDs, approved answer IDs, and a dynamic
question whose semantic body uses exact registered topic phrases inside an
approved outer grammar. The server rejects unsafe
or ungrounded wording to deterministic fallback, owns all reason and option
copy, and resolves the selected IDs to typed factor-preference or objective
patches. Raw provider patches never cross this boundary, and group-priority
refinement questions are not generated in this slice. Every option in a
multi-topic question contains exactly one registered answer for every selected
topic; asymmetric options are rejected independently from valid siblings.

Deterministic zero-result recovery remains part of the ranking response because
it is necessary to explain hard-constraint failure. Optional preference
questions use the separate refinement endpoint.

The process-local design is accepted for the current single-instance
deployment. A horizontal deployment requires sticky routing, shared state, or a
redesigned handoff before refinement requests can be served safely by multiple
web processes. Deploy or process restart clears all stored baselines.

## Decision And Review Gate

- Classification: `review-gated`, full design flow.
- Developer Decision Checkpoint: resolved by the owner on 2026-07-18 in favor
  of exact evaluator replay from the bounded snapshot.
- ADR status: required; this accepted ADR records the decision.
- Advisory review: final follow-up findings were accepted on 2026-07-18 and
  resolved by this implementation; fresh exact-head review remains the release
  gate.

## Consequences

Ranked results render without Gemini latency and remain available when the
provider fails. Search and refinement have separate error states, cancellation,
latency metrics, admission limits, and release checks. The frontend gains an
explicit progressive loading lifecycle.

Refinement proposals, actionability, materiality, and previews use evaluator
results replayed from the exact bounded baseline behind the ranking the user
sees. Achieving that consistency intentionally retains referenced catalog,
trust, and normalized weather evaluator inputs in process for up to 60 seconds
and adds bounded memory, expiry, eviction, and concurrency behavior that must
be tested and observed.

Expiry, eviction, deploy, or restart can make optional refinement temporarily
unavailable, but never invalidates the displayed ranking or triggers hidden
recomputation. The local snapshot store and admission guard are not
cross-machine coordination mechanisms and require replacement, shared state, or
sticky routing before horizontal scale.

## Alternatives Considered

- Keep refinement inside `POST /api/search`: simplest contract, but optional
  provider latency and failure continue to block every ranking.
- Start search and refinement in parallel from the draft intent: lower total
  latency, but the question can be based on an intent that differs from the
  backend's canonical applied intent.
- Rerun deterministic search and compare a stateless baseline digest: avoids
  server state, but repeats work and cannot guarantee that refinement uses the
  evaluated view already shown to the user.
- Trust the public fingerprint without canonical intent binding: simpler
  lookup, but lets caller-controlled request data select a baseline without
  proving exact intent equality.
- Persist the evaluated baseline or put it in a shared cache: supports a longer
  or multi-instance handoff, but adds invalidation, serialization,
  compatibility, and operational ownership that the current single-instance
  product does not require.
- Stream one combined response: avoids a second client request but introduces a
  streaming protocol and more complex recovery for a small optional payload.

## Revisit When

Reconsider the 60-second TTL, 64-entry bound, and process-local ownership only
from measured hit, miss, expiry, eviction, memory, and latency evidence. Choose
sticky routing, shared state, or a redesigned stateless handoff before running
multiple web processes, and reconsider persistence only if cross-device or
long-lived exact search sessions become a product requirement. Replace the
local limiter with a shared edge or datastore-backed limiter before horizontal
scale or when measured legitimate traffic approaches its configured bounds.

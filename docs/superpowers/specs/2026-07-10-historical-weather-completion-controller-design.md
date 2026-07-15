# Feature Spec: Historical Weather Completion Controller

## Status

- Status: implemented
- Owner: solo-builder
- Related docs:
  - `README.md`
  - `docs/engineering-notes.md`
  - `docs/planning-model.md`
- Related plan:
  - `docs/superpowers/plans/2026-07-10-historical-weather-completion-controller.md`
- Related ADRs: none

## User Outcome

The owner can start one GitHub Actions workflow and leave it running. Scheduled
runs progressively fill historical weather for every active ski area, resume
from persisted archive coverage after provider throttling or interruption, and
build derived climatology only when an area's archive is complete.

## Scope

In scope:

- Complete archive weather for every active `ski_area_id` from `1991-01-01`
  through `2025-12-31` at base, mid, and upper elevation bands.
- Bound each scheduled run by a configurable provider-request budget.
- Treat stored archive rows as the durable completion checkpoint.
- Stop cleanly on exhausted Open-Meteo rate limits and resume on the next run.
- Rebuild climatology per ski area after all required archive days are present.
- Keep the existing targeted manual backfill and climatology workflows.
- Serialize all Open-Meteo archive-writing workflows through one repository-wide
  concurrency group.
- Expose progress and outcomes in logs, GitHub job summaries, and existing data
  quality metrics.

Out of scope:

- Automatically advancing the climatology baseline after 2025.
- Automatically refetching history after ski-area coordinates or elevation
  bands change.
- A persistent workflow queue, cursor, or provider-quota table.
- Changing historical variables, weather-provider choice, or planning scores.
- Parallel provider requests or GitHub Actions matrix fan-out.

## Product Fit

- Reliable archive coverage restores the evidence required by Snowcast's
  conditions-aware planning model.
- Incomplete archive and climatology remain visible through existing data
  quality metrics; partial data is never reported as complete.
- The controller is deterministic and provider-specific. It adds no generic AI
  or travel-planning behavior.

## Domain Model

- Bounded contexts touched: weather evidence, derived climatology, operations.
- Domain terms introduced or changed: none.
- New or changed entities: no persisted domain entity; a completion result is an
  operational value object.
- Important state transitions:
  - archive chunk missing -> stored
  - campaign work remaining -> complete
  - archive-complete ski area with stale/missing climatology -> climatology ready
  - provider available -> throttled -> next scheduled retry
- Invariants that must hold:
  - Weather remains keyed by `ski_area_id`; destinations only select reachable
    ski areas.
  - A scheduled completion run never deletes archive observations.
  - Existing complete chunks are not fetched again.
  - Provider-request budgets count attempted remote requests, not skipped chunks.
  - A 429 stops further provider requests in that run.
  - Climatology is replaced only after all expected archive days exist for all
    three elevation bands.
  - Climatology replacement for one ski area is atomic.
- Existing model/spec docs that must stay aligned:
  - `docs/planning-model.md`
  - `docs/engineering-notes.md`

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: scheduled production job, external integration,
  persisted weather evidence, climatology correctness, observability.
- Developer Decision Checkpoints:
  - resolved: archive coverage is the durable checkpoint; no orchestration table
  - resolved: fixed archive campaign window of `1991-01-01` to `2025-12-31`
  - resolved: serialized daily scheduled runs with bounded provider requests
  - integration adjustment: the daily archive run starts at `01:15 UTC`, after
    PR #49's midnight conditions and forecast refresh windows, so fresh forecast
    evidence is not forced to compete with the bulk completion campaign
  - accepted assumptions: approximately 200 yearly provider requests per run is
    a conservative initial budget and remains manually configurable
  - unresolved: none
- ADR status: not needed; the controller composes existing persistence and job
  boundaries without introducing a new durable architecture boundary.
- Advisory design-review:
  - reviewers: backend-api, data-trust-source-integrity, observability-ops
  - status: completed
  - skipped reason: N/A
- Advisory feature-review before final handoff:
  - reviewers: backend-api, data-trust-source-integrity, observability-ops
  - status: completed
  - skipped reason: N/A

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Technical | Durable resume state | Determines schema and recovery complexity | Archive coverage as checkpoint is simple and truthful; a queue table preserves cursors and cooldowns but duplicates completion state | Archive coverage | Daily scheduling makes a persisted provider cooldown unnecessary; deterministic scanning prevents lost work | `docs/engineering-notes.md` |
| Mixed | Campaign window | Controls evidence semantics and future automatic changes | Fixed 1991-2025 is stable; automatic annual advancement changes model baselines without owner review | Fixed 1991-2025 | This safely completes the current evidence baseline while leaving annual advancement explicit | `docs/planning-model.md` |
| Technical | Provider concurrency | Controls throughput and rate-limit risk | Serialized requests are slower but predictable; parallel jobs increase 429 risk and complicate quotas | Serialized bounded runs | This matches the free-tier constraint and current resilient client behavior | `README.md` |

## Architecture Decisions

- Durable decisions made:
  - PostgreSQL archive coverage is the queue and checkpoint.
  - The controller is a deterministic composition layer over existing backfill,
    catalog, coverage, and climatology services.
  - Completion, targeted historical backfill, and recent archive reconciliation
    share one GitHub Actions concurrency group.
  - Normal incomplete or throttled runs are successful operational outcomes;
    malformed configuration, permanent provider errors, and database failures
    remain workflow failures.
- ADRs needed: none.
- Existing ADRs that constrain this feature: none directly.
- Revisit criteria:
  - The provider cannot be kept below quota with a conservative request budget.
  - Multiple providers or concurrent workers are introduced.
  - Coordinate/elevation changes need automatic evidence invalidation.
  - Automatic annual climatology advancement is approved.

## API and Client Contract

- Backend endpoints or response fields: unchanged.
- Web UI states: unchanged.
- Mobile companion states: unchanged.
- Backward compatibility notes: existing manual CLIs and workflow inputs remain
  supported.

## Data Trust and Source Integrity

- Data sources: Open-Meteo Historical Weather API through the existing client.
- Freshness requirements: fixed archive end date `2025-12-31` for this campaign.
- Source refs or evidence required: existing raw rows retain provider source and
  source-model metadata.
- Behavior when data is missing, stale, estimated, or conflicting:
  - Missing chunks remain eligible for a later run.
  - Partial ski areas do not receive rebuilt climatology.
  - Existing data-quality coverage metrics continue to expose missing days.

## AI / LLM Use

- Deterministic logic that must not use an LLM: all controller planning,
  coverage checks, retries, completion decisions, and climatology rebuilds.
- Allowed LLM use: none.
- Prompt/output boundaries: N/A.
- Caching, fallback, and cost controls: N/A.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| Daily GitHub Actions schedule at 01:15 UTC or manual dispatch | Complete missing historical archive chunks and eligible climatology | GitHub-hosted Python worker | Runs after the midnight conditions and forecast refresh windows; archive writers are serialized by workflow concurrency and bounded by provider-request count and job timeout |

## Security, Privacy, and Abuse

- User data involved: none.
- Sensitive fields that must not enter logs, metrics, traces, or prompts:
  `DATABASE_URL` and telemetry credentials.
- Permission or session assumptions: workflow has read-only repository contents
  permission and receives database/telemetry credentials through Actions secrets.
- Abuse or rate-limit concerns: no provider parallelism; successful requests are
  paced and jittered; retries honor `Retry-After`; exhausted 429 responses stop
  the run.

## Observability and Operations

- Logs, metrics, traces, or freshness signals:
  - structured completion result in CLI logs
  - GitHub job summary with attempted, stored, skipped, failed, remaining, and
    rebuilt-area counts
  - existing archive and climatology data-quality metrics
- Failure modes:
  - expected: request budget exhausted, provider throttled, work remains
  - hard: invalid catalog target, malformed provider response, permanent HTTP
    failure, database failure, atomic climatology replacement failure
- Retry/idempotency expectations:
  - Rerunning with the same window does not refetch complete chunks.
  - The next scheduled run resumes from current database coverage.
  - 429 responses do not busy-loop or trigger parallel recovery runs.
- Runbook or alerting updates: document initial launch, progress interpretation,
  manual dispatch, and hard-failure recovery in `README.md` and
  `docs/engineering-notes.md`.

## Acceptance Criteria

- A daily and manually dispatchable workflow targets every active ski area when
  no filter is supplied.
- One run attempts no more than its configured provider-request budget.
- Complete archive chunks are skipped and do not consume the request budget.
- Exhausted 429 responses stop provider work, report `throttled`, and do not
  make the workflow fail solely because work remains.
- Non-rate-limit failed chunks produce a hard-failure outcome.
- A ski area is eligible for climatology only after complete 1991-2025 coverage
  across base, mid, and upper bands.
- Complete current climatology is skipped; missing or stale climatology is
  rebuilt once per eligible ski area.
- Per-area climatology replacement is transactional.
- No archive deletion occurs in the completion controller.
- The workflow cannot overlap with itself.
- Completion, manual historical backfill, and recent archive reconciliation
  cannot issue Open-Meteo archive requests concurrently.
- Unit tests cover budget stopping, resumability, 429 behavior, completeness
  gates, climatology selection, and atomic replacement behavior.

## Verification

- Unit tests:
  - historical backfill budget and outcomes
  - controller coverage and rebuild selection
  - repository climatology completeness and replacement
- API/integration tests: repository tests against the configured test database.
- UI/manual checks: N/A.
- Operational checks:
  - workflow YAML validation/static assertions
  - controller dry run or stub-client smoke check
  - inspect GitHub job summary rendering

## Advisory Review

- Design reviewers: backend-api, data-trust-source-integrity, observability-ops.
- Feature reviewers: backend-api, data-trust-source-integrity, observability-ops.
- Design-review outcome:
  - Backend / API: no blocking findings; keep completion outcomes typed and
    preserve existing manual CLI behavior.
  - Data Trust & Source Integrity: no blocking findings; require complete
    three-band archive coverage before climatology replacement.
  - Observability / Ops: addressed one High finding by requiring a shared
    concurrency group across every Open-Meteo archive-writing workflow.
  - Residual Medium risk: a long sequence of expected throttled runs is visible
    through job outcomes and coverage metrics but does not yet have a dedicated
    stalled-progress alert.
- Feature-review outcome:
  - Backend / API: no defensible blocking findings; existing CLI behavior is
    preserved, provider attempts are bounded, and per-area replacement is
    transactional.
  - Data Trust & Source Integrity: no defensible blocking findings; the
    controller requires complete three-band archive coverage and validates the
    expected 2,196 climatology rows before replacing current evidence.
  - Observability / Ops: no defensible blocking findings; archive writers are
    serialized, expected continuation outcomes stay green, hard failures stay
    red, and progress is available in job summaries and low-cardinality metrics.
- Known residual risks:
  - Open-Meteo weights long requests dynamically, so the initial request budget
    remains conservative and operator-tunable.
  - Coordinate/elevation changes require an explicit targeted rebuild until a
    source-geometry fingerprint is designed.

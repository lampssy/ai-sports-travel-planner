# ADR 0017: Use Stable Public API Error Codes

Status: accepted
Date: 2026-07-19

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-19-product-language-audit-remediation-design.md`

Related docs:
- `docs/advisory-reviews/2026-07-19-content-language-domain-audit.md`
- `docs/domain-language.md`

## Context

Snowcast has customer-facing React and Flutter clients. Both currently risk
displaying FastAPI `detail`, provider failures, validation paths, policy
identifiers, or transport exceptions directly. Those strings are unstable,
may disclose implementation details, and are often unnatural for customers.

The two clients also need different recovery presentation. A browser can keep
ranked results visible while a refinement fails; a mobile screen may need a
native sign-in or retry action. Making HTTP status alone carry that meaning
duplicates brittle endpoint-specific inference. Making the backend own final
English sentences couples API behavior to interface writing and future
localization.

## Decision

Customer-facing API failures expose a stable, language-neutral public error
code. Web and Flutter clients map that code, together with the operation being
performed, to platform-appropriate public copy and recovery actions.

The public response body is exactly:

```json
{"error": {"code": "invalid_request"}}
```

`code` is selected from the bounded registry below. The body contains no final
message, `detail`, validation path, provider text, stack information, or request
identifier.

Raw exception messages, provider responses, validation paths, internal factor
or group identifiers, and stack details do not form part of the public contract.
They remain in bounded server logs when operationally useful and safe.

Clients must:

- maintain exhaustive mappings for known codes used by their operations
- use a safe generic message for an unknown, absent, or malformed code
- distinguish transport and decoding failures locally because no server code is
  available in those cases

The shared source of conceptual truth is human-readable documentation and API
tests. TypeScript and Dart keep platform-local typed mappings. Snowcast does not
introduce runtime shared copy files, code generation, or a new dependency for
this migration.

Backend, web, and Flutter switch atomically. Snowcast has no deployed users, so
there is no legacy error-body compatibility period. Existing success schemas
and HTTP statuses stay unchanged. Each code has exactly one HTTP status; several
codes may share a status.

## Initial Registry

The canonical code enum lives in `app/api/public_errors.py`. This ADR owns each
code's meaning; tests own route/status coverage.

| Code | HTTP | Operations | Retry / action intent |
| --- | ---: | --- | --- |
| `invalid_request` | 422 | FastAPI validation and malformed JSON on customer routes | Review the entered fields and submit again |
| `authentication_required` | 401 | Protected route without bearer credentials | Sign in |
| `session_expired` | 401 | Protected route with an unknown or expired session | Clear protected client state and sign in |
| `sign_in_failed` | 401 | Google identity rejected | Try sign-in again |
| `sign_in_unavailable` | 503 | Sign-in provider/configuration unavailable | Retry later |
| `search_request_invalid` | 422 | Search, refinement, or weather policy rejection | Review trip choices and submit again |
| `weather_area_not_found` | 422 | Weather evidence requested for an unknown ski area | Return to current trip options |
| `refinement_rate_limited` | 429 | Refinement admission rejection | Preserve results; retry after required `Retry-After` |
| `trip_option_invalid` | 422 | Saving inconsistent or stale trip-option entities | Return to results and choose the option again |
| `current_trip_not_found` | 404 | Current-trip summary or mark-checked with no saved trip | Return to search or the current-trip empty state |
| `not_found` | 404 | Unknown customer API route | Return to the previous product surface |
| `method_not_allowed` | 405 | Unsupported method on a customer API route | Use the supported action |
| `request_failed` | 500 | Unexpected customer-route failure | Preserve usable state and retry |

`Retry-After` remains mandatory for `refinement_rate_limited`. Codes do not
change status or meaning without a new compatibility decision and ADR update.

## Handler Boundary

The JSON contract covers every non-operational `/api/*` route except the
accommodation browser-navigation boundary. This includes unknown routes, which
return `not_found`, and unsupported methods on known routes, which return
`method_not_allowed` while retaining framework headers such as `Allow`. A typed
public exception and application-level handlers normalize explicit domain
failures, dependency/auth failures,
`RequestValidationError` including malformed JSON, remaining `HTTPException`
paths, and unexpected exceptions.

`/api/outbound/accommodation` and all descendant paths are intentionally outside
the JSON boundary because they are opened through direct browser navigation.
Valid requests retain the provider redirect. Missing or extra path segments,
unsupported methods, and invalid or stale requests return branded HTML with the
original status and headers plus a return-to-trip-details link, so the browser
never exposes an API payload.

Operational `/api/healthz`, `/api/readyz`, and `/api/search-readiness` retain
their diagnostic contracts and are not consumed by customer clients. Public
HTML destination routes own branded HTML failures separately.

## Decision And Review Gate

- Classification: review-gated, full design flow.
- Developer Decision Checkpoint: resolved by the owner on 2026-07-19 in favor
  of stable backend codes with client-owned messages.
- ADR status: required; this accepted ADR records the decision.
- Advisory design review: required before implementation planning.
- Advisory feature review: required on the implemented exact head.

## Consequences

Public wording can change independently in web and mobile without changing the
backend contract. Clients can give context-appropriate recovery guidance, and a
future localized client can translate the same error code.

The backend must maintain a bounded error registry and tests for status/code
pairings. Each client must maintain mappings and a safe fallback. Copy can drift
between platforms, so shared vocabulary, contract tests, and content-language
review become ongoing controls.

Changing an existing code's meaning is a breaking API change. Adding a code is
compatible because clients have a generic fallback, but the relevant clients
should add specific mappings in the same release whenever practical.

The first release is an intentional atomic contract replacement. Backend, web,
and Flutter tests must pass against the same registry before deployment.

## Alternatives Considered

- Infer messages from endpoint and HTTP status in each client: smaller backend
  change, but duplicates ambiguous logic and leaves no stable reason contract.
- Return final user-facing English messages from the backend: centralizes copy,
  but couples domain/API code to interface context and localization.
- Return both a stable code and require clients to display a server message:
  weakens ownership because clients may continue exposing unsuitable text. A
  safe server fallback may be added later for external API consumers, but
  Snowcast clients do not display it directly.
- Keep `detail` temporarily for older clients: unnecessary because Snowcast has
  no deployed users; it would preserve the unsafe behavior this change removes.

## Revisit When

Reconsider the documentation-only shared registry when Snowcast supports
multiple languages, publishes a third-party API, or adds enough clients that
generated typed contracts materially reduce drift. Reconsider correlation
metadata only from support and observability needs, with privacy review.

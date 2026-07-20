# Product Language Remediation Design Review

Date: 2026-07-19
Mode: `design-review`
Accepted head: `a5b5855`

Reviewed artifacts:

- `docs/superpowers/specs/2026-07-19-product-language-audit-remediation-design.md`
- `docs/architecture/adr/0017-use-stable-public-api-error-codes.md`
- `docs/advisory-reviews/2026-07-19-content-language-domain-audit.md`

Reviewers:

- Content & Language
- UI / UX
- Mobile Companion
- Backend / API
- Data Trust & Source Integrity
- Accessibility

## Initial Findings

The first review found no Blockers but identified High design gaps in four
areas:

- the proposed 30 cm label implied piste or snow-cover meaning that modeled
  point snow depth does not support;
- the public error envelope lacked an exact schema, initial registry, route
  boundary, and operation-level recovery states;
- mobile session expiry, secondary current-trip failures, and accessibility
  announcements were not defined;
- dossier hierarchy, weather currency/coverage language, responsive rationale,
  claim eligibility, and chart alternatives were under-specified.

The Backend/API follow-up also found that the accommodation endpoint is direct
browser navigation and therefore cannot rely on a client-parsed JSON error.

## Resolutions

- The public chart term is `30 cm snow-depth reference`, with visible text that
  it does not show snow coverage, open ski runs, comfort, or safety.
- ADR 0017 defines the exact `{"error":{"code":"<code>"}}` schema, bounded
  code/status registry, customer-route handler boundary, and atomic migration.
- The spec defines operation-level state preservation, message placement,
  actions, focus/live-region behavior, and unknown-code fallback.
- Expired Flutter sessions return to sign-in. Event and mark-checked failures
  preserve successfully loaded current-trip information.
- Mobile parity is limited to language and recovery parity on current Flutter
  surfaces; it does not add web-only features.
- Weather source type, source currency, evidence coverage, expected conditions,
  and limitations have separate presentation rules. `evaluated_at` is not
  source freshness.
- The trip-details page has one primary explanation and one collapsed technical
  disclosure. Charts retain equivalent tables and keyboard operation.
- Valid accommodation requests keep their provider redirect. Invalid or stale
  requests return a branded HTML recovery page with a return link.

## Final Result

All six reviewers approved implementation planning. The final Backend/API
follow-up confirmed that exact head `a5b5855` has no remaining planning
blockers. Implementation fidelity remains subject to scoped exact-head feature
reviews and a final whole-branch review.

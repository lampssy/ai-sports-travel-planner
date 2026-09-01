# Ski-Area Trip-Consequence Boundaries Implementation Plan

## Decision Gate Before Execution

- Classification: review-gated
- High-risk domains touched: catalog correctness, source trust, weather-owner
  boundaries, maintainer publication contract
- Resolved owner decisions:
  - complete terrain + evidence ownership + material trip-level consequence;
  - provider/operator/transfer/stay-market signals are supporting only;
  - no ski-sub-area layer;
  - preserve historical reports through schema version 4.
- Accepted assumptions: none
- Unresolved owner decisions: none
- ADR status: ADR 0023 accepted in this change
- Advisory review status: design review before implementation; feature review
  before final handoff

## Tasks

1. Add failing schema-v4 validation and rendering tests.
2. Extend the typed curation contract with claim-scoped material trip
   consequences and schema-v4 enforcement while preserving schema-v3 behavior.
3. Update maintainer intent/finalization to require schema version 4.
4. Align domain language, trust documentation, ADRs, engineering notes, runtime
   contract, and installed curation/review skills.
5. Run focused tests, complete relevant suites, catalog validation, and
   advisory feature review.

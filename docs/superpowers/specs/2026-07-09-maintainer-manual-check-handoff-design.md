# Maintainer Manual-Check Handoff And Access-Source Validation

## Status

- Status: implemented on the feature branch; final verification pending
- Classification: review-gated
- Owner decision: push the exact scope-safe reviewed head before publishing
  `maintainer:manual-check`
- Related design: `2026-07-08-local-maintainer-simplification-design.md`
- Related ADR: ADR 0011 amended by this implementation

## Outcome

The catalog maintainer should:

1. validate ski-area-access evidence without attributing one field group's
   sources to every other group;
2. allow at most four review/fix cycles per curation run; and
3. preserve unresolved reviewed work on the automation-owned PR branch before
   pausing it for manual review.

The automation still never approves or merges a PR.

## Access-Source Ownership Contract

`SkiAreaAccess.source_urls` is the entity-level roll-up of the access trust
entry's field-group sources. For every access entry:

```text
set(catalog source_urls)
    == union(set(field-group source refs))
```

The existing field-level rules remain independent:

- `relationship` evidence does not prove `access_mode_distance`;
- `verified` and `verified_with_adjustment` require at least one direct source
  on that exact group;
- `needs_source` may have zero or more reviewed-but-insufficient sources; and
- one URL may appear in multiple groups when it genuinely supports each group.

`CatalogTrustManifest.validate_against_catalog()` will enforce the union rule
and distinguish two errors:

- catalog URLs with no field-group owner; and
- trust-group URLs absent from the catalog roll-up.

No schema, persistence, or API migration is required.

## Four-Cycle Bound

The current two-cycle limit becomes four in the active repository contract,
activation checklist, installed `snowcast-maintainer` skill, and persisted
curation automation prompt. Every fix still requires a fresh independent
`snowcast-catalog-review` context. Owner decisions, schema/domain expansion,
conflicts, and capability errors still stop immediately; the higher limit is
not permission to retry those conditions mechanically.

## Reviewed-Head Manual Check

Add an explicit helper capability:

```text
publish manual-check
```

It accepts the selected PR, exact reviewed head, trusted summary/body inputs,
and the current curation lease. It performs one bounded handoff:

1. verify repository, PR, branch, base, selected remote head, current local
   head, work record, lease, ancestry, allowed resulting paths, and safe file
   modes;
2. record the reviewed head in the work record if validation has not already
   advanced it to `reviewed`;
3. create or resume a curation push journal whose new head is the reviewed head;
4. push with the existing exact `--force-with-lease` protection;
5. refetch the PR and require its head to equal the reviewed head;
6. publish `maintainer:manual-check`, the managed body, and the canonical
   summary comment for that head; and
7. mark the journal published.

The published machine state records:

- `reviewed_head=<pushed head>`;
- `validated_head=null`; and
- `last_operation=reviewed`.

`last_operation` represents the highest objective evidence phase, not whether
GitHub prose was written. Publishing a semantic pause must therefore preserve
`reviewed` instead of falsely promoting an unvalidated head to `published`.

The ordinary work record may remain at `reviewed`; it must not be advanced to
`validated`, `pushed`, or `published` because those phases currently represent
successful objective validation. Readiness already requires
`validated_head == current PR head`, so a manual-check handoff cannot request
`waiting-ci` or `ready` without a later successful validation.

## Failure And Recovery

- A stale remote head stops before rewriting the branch.
- A rebase/ancestry/scope/file-mode failure stops before push.
- A crash before push leaves an authorized journal that recovery may retry.
- A crash after push leaves a pushed journal; fresh work remains blocked until
  the curation worker recovers it and reruns the idempotent manual-check
  capability with trusted publication inputs.
- Any remote head other than the selected or reviewed head fails closed.
- A completed manual-check journal is terminal and does not authorize a future
  branch mutation.

## Testing

Test-first coverage will include:

- split, shared, catalog-only, and trust-only access sources;
- unchanged verified-group source requirements;
- reviewed-head handoff from both `prepared` and failed-validation `reviewed`
  work;
- exact-lease push construction and stale-head rejection;
- crash recovery before and after the push;
- publication failure leaving an unresolved journal;
- manual-check machine state without validation evidence;
- semantic-state publication preserving `last_operation=reviewed`;
- deterministic rejection of `waiting-ci` and `ready`; and
- four-cycle wording across active repository and installed local contracts.

## Rollout

Implementation will be merged through a normal reviewed PR. After the merge:

1. update and re-inspect the installed personal skill;
2. update and re-inspect the existing curation automation record without
   changing its schedule, model, working directory, or active state; and
3. leave the preserved PR #31 head `e51a11a` untouched until the owner starts
   the separate recovery step.

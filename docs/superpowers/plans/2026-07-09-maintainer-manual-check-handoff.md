# Maintainer Manual-Check Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce field-group-aware ski-area-access source ownership, allow four bounded review/fix cycles, and safely push an unresolved reviewed head before publishing `maintainer:manual-check`.

**Architecture:** Keep the existing schemas and capability boundaries. The catalog trust validator will reconcile each access-level source roll-up with the union of field-group refs. A new explicit `publish manual-check` command will reuse guarded reviewed-head revalidation, the exact-lease push journal, and canonical publication while deliberately retaining reviewed-but-unvalidated evidence state.

**Tech Stack:** Python 3.13, Pydantic v2, argparse, pytest, Git/GitHub CLI adapters, Codex App automation records.

---

## File Map

- `app/domain/catalog_trust.py`: enforce the cross-file access-source union invariant.
- `tests/test_catalog_trust.py`: specify partitioned, shared, missing-owner, and missing-roll-up behavior.
- `ops/maintainer/cli.py`: expose the explicit `publish manual-check` capability.
- `ops/maintainer/capabilities.py`: reviewed-head push, recovery-journal reuse, and semantic-state publication.
- `ops/maintainer/publication.py`: preserve reviewed evidence state when semantic publication has no validation.
- `tests/test_maintainer_cli.py`: exercise fresh, failed-validation, stale-head, and recovery paths.
- `tests/test_maintainer_publication.py`: prove unvalidated semantic states cannot become waiting-CI or ready.
- `docs/data-trust-model.md`: define access `source_urls` as a field-group union.
- `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`: record reviewed-but-unvalidated exact-lease handoff authority.
- `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`: update the active capability and four-cycle contract.
- `docs/operating-model/local-maintainer-activation.md`: update the installed-skill acceptance contract.
- `docs/engineering-notes.md`: summarize the durable source-ownership and manual-check behavior.
- `docs/superpowers/specs/2026-07-09-maintainer-manual-check-handoff-design.md`: mark implementation and verification status.
- `~/.codex/skills/snowcast-maintainer/SKILL.md`: post-merge local update from two to four cycles and the new handoff command.
- `~/.codex/automations/snowcast-catalog-pr-maintainer/automation.toml`: post-merge prompt update through the Codex automation API, preserving all other fields.

### Task 1: Enforce access-source union ownership

**Files:**
- Modify: `tests/test_catalog_trust.py`
- Modify: `app/domain/catalog_trust.py`
- Modify: `docs/data-trust-model.md`

- [ ] **Step 1: Write the failing validator tests**

Update the minimal access fixture so its catalog URL is owned by the
`relationship` group, then add these tests:

```python
def test_access_sources_may_be_partitioned_across_trust_groups() -> None:
    snapshot = _minimal_snapshot()
    access = snapshot.ski_area_access[0]
    payload = _manifest_payload()
    entry = payload["entities"]["ski_area_access"][access.ski_area_access_id]
    relationship_url = access.source_urls[0]
    mode_url = "https://www.openstreetmap.org/node/2"
    snapshot = snapshot.model_copy(
        update={
            "ski_area_access": (
                access.model_copy(
                    update={"source_urls": (relationship_url, mode_url)}
                ),
            )
        }
    )
    entry["field_source_refs"]["relationship"] = [relationship_url]
    entry["field_source_refs"]["access_mode_distance"] = [mode_url]

    CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)


def test_access_source_rollup_rejects_catalog_url_without_group_owner() -> None:
    snapshot = _minimal_snapshot()
    payload = _manifest_payload()
    access = snapshot.ski_area_access[0]
    payload["entities"]["ski_area_access"][access.ski_area_access_id][
        "field_source_refs"
    ]["relationship"] = []

    with pytest.raises(ValueError, match="catalog sources without field-group ownership"):
        CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)


def test_access_source_rollup_rejects_group_url_missing_from_catalog() -> None:
    snapshot = _minimal_snapshot()
    payload = _manifest_payload()
    access = snapshot.ski_area_access[0]
    entry = payload["entities"]["ski_area_access"][access.ski_area_access_id]
    entry["field_source_refs"]["relationship"] = list(access.source_urls)
    entry["field_source_refs"]["access_mode_distance"] = [
        "https://www.openstreetmap.org/node/2"
    ]

    with pytest.raises(ValueError, match="field-group sources absent from catalog source_urls"):
        CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)
```

Retain a shared-source case where both groups cite the same URL and the catalog
contains it once.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest -q \
  tests/test_catalog_trust.py::test_access_sources_may_be_partitioned_across_trust_groups \
  tests/test_catalog_trust.py::test_access_source_rollup_rejects_catalog_url_without_group_owner \
  tests/test_catalog_trust.py::test_access_source_rollup_rejects_group_url_missing_from_catalog
```

Expected: the invalid cases do not raise because `validate_against_catalog()`
does not yet reconcile access sources.

- [ ] **Step 3: Implement the minimal production invariant**

Add a focused helper and call it for `ski_area_access` entries inside
`validate_against_catalog()`:

```python
def _validate_access_source_rollup(
    access: SkiAreaAccess,
    entry: EntityTrustEntry,
    entity_id: str,
) -> None:
    catalog_sources = set(access.source_urls)
    grouped_sources = {
        source
        for sources in entry.field_source_refs.values()
        for source in sources
    }
    unowned = sorted(catalog_sources - grouped_sources)
    if unowned:
        raise ValueError(
            f"ski_area_access/{entity_id}: catalog sources without "
            f"field-group ownership: {', '.join(unowned)}"
        )
    absent = sorted(grouped_sources - catalog_sources)
    if absent:
        raise ValueError(
            f"ski_area_access/{entity_id}: field-group sources absent from "
            f"catalog source_urls: {', '.join(absent)}"
        )
```

Import `SkiAreaAccess` beside `CatalogSnapshot` from `app.domain.catalog`.

- [ ] **Step 4: Verify GREEN and update the trust documentation**

Run `uv run pytest -q tests/test_catalog_trust.py`, then document the exact
union rule and independent group semantics in `docs/data-trust-model.md`.

- [ ] **Step 5: Commit Task 1**

```bash
git add app/domain/catalog_trust.py tests/test_catalog_trust.py docs/data-trust-model.md
git commit -m "Validate access source ownership"
```

### Task 2: Add exact-lease reviewed-head manual-check handoff

**Files:**
- Modify: `tests/test_maintainer_cli.py`
- Modify: `tests/test_maintainer_publication.py`
- Modify: `ops/maintainer/cli.py`
- Modify: `ops/maintainer/capabilities.py`
- Modify: `ops/maintainer/publication.py`

- [ ] **Step 1: Extend the CLI fakes and write failing happy-path tests**

Add `FakeRepository.revalidate_prepared_result()` with call tracking. Add a
test that prepares curation work, creates owner-private summary/body files, and
invokes:

```text
publish manual-check --pr 42 --reviewed-head <SHA_B>
  --summary-file summary.md --body-file body.md --run-id <run>
```

Assert:

```python
assert code == 0
assert repository.push_calls == 1
assert repository.revalidate_calls == 1
assert github.pull_requests[42].head_sha == SHA_B
assert MaintainerState.MANUAL_CHECK.value in github.pull_requests[42].labels
machine = trusted_machine_state(github.list_issue_comments(42))
assert machine is not None
assert machine.reviewed_head == SHA_B
assert machine.validated_head is None
assert machine.last_operation == "reviewed"
journal = StateStore(state_dir).load_push("curation-pr-42")
work = StateStore(state_dir).load_work("curation-pr-42")
assert journal is not None and journal.phase is PushPhase.PUBLISHED
assert work is not None and work.phase is WorkPhase.REVIEWED
```

Add a second test where `validate curation` advances the work to `reviewed`
and then returns a safe `validation-failed` error; `publish manual-check` must
reuse that exact reviewed head.

- [ ] **Step 2: Run the new CLI tests and verify RED**

Expected: argparse rejects `publish manual-check` because the command and
handler do not exist.

- [ ] **Step 3: Add the explicit command and dependency routing**

In `ops/maintainer/cli.py`, add required `--pr`, `--reviewed-head`,
`--summary-file`, optional `--body-file`, and `--run-id` arguments. Include
`("publish", "manual-check")` in repository dependency composition and map it
to `handle_publish_manual_check` in `HANDLERS`.

- [ ] **Step 4: Generalize curation journaling without weakening validated push**

Refactor journal construction to accept an explicit new head:

```python
def _matching_curation_journal(
    work: WorkState,
    lease: RunLease,
    new_head: str,
) -> PushJournal:
    if work.sync is None or work.pr_number is None:
        raise StateStoreError("curation push facts are incomplete")
    if new_head not in {work.reviewed_head, work.validated_head}:
        raise StateStoreError("curation push head lacks reviewed evidence")
    return PushJournal(
        work_id=work.work_id,
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=work.pr_number,
        branch=work.sync.target_branch,
        expected_remote_head=work.selected_head,
        new_head=new_head,
        phase=PushPhase.AUTHORIZED,
    )
```

Keep `handle_publish_push()` restricted to `WorkPhase.VALIDATED` and pass
`work.validated_head`. Permit `_advance_curation_push()` to push a journal head
that matches either the reviewed or validated work evidence.

- [ ] **Step 5: Implement `handle_publish_manual_check`**

The handler must:

1. load the exact curation lease/work/journal;
2. read trusted publication files before irreversible mutation;
3. refetch and require the remote PR head to equal the selected head unless a
   matching recovery journal already records the reviewed head;
4. call `revalidate_prepared_result()` for a fresh local handoff;
5. advance `prepared -> reviewed` when necessary;
6. create/resume the reviewed-head journal and exact-lease push;
7. refetch and require the PR head to equal the reviewed head;
8. publish a `PublicationPlan` with `MANUAL_CHECK` and this state:

```python
MachineState(
    schema_version=2,
    reviewed_head=args.reviewed_head,
    validated_head=None,
    last_operation="reviewed",
)
```

9. advance `PushPhase.PUSHED -> PushPhase.PUBLISHED`; and
10. leave ordinary work at `WorkPhase.REVIEWED`.

- [ ] **Step 6: Preserve semantic evidence state in normal publication**

Replace the unconditional `last_operation="published"` promotion in
`handle_publish_state()` with:

```python
if plan.machine_state.validated_head is not None:
    plan = plan.model_copy(
        update={
            "machine_state": plan.machine_state.model_copy(
                update={"last_operation": "published"}
            )
        }
    )
```

An unvalidated semantic pause must retain `last_operation="reviewed"`.

- [ ] **Step 7: Add fail-closed and recovery tests**

Cover:

- stale remote head before push;
- unsafe/revalidation failure before journal creation;
- publication failure after push leaving `PushPhase.PUSHED`;
- successor lease adoption via `publish recover`, followed by idempotent
  `publish manual-check` completion;
- any remote head other than selected/reviewed returning `stale-head`;
- `waiting-ci` and `ready` rejecting a machine state with
  `validated_head=None`.

- [ ] **Step 8: Run focused maintainer tests and verify GREEN**

```bash
uv run pytest -q \
  tests/test_maintainer_cli.py \
  tests/test_maintainer_publication.py \
  tests/test_maintainer_state.py \
  tests/test_maintainer_git_ops.py
```

- [ ] **Step 9: Commit Task 2**

```bash
git add ops/maintainer/cli.py ops/maintainer/capabilities.py \
  ops/maintainer/publication.py tests/test_maintainer_cli.py \
  tests/test_maintainer_publication.py
git commit -m "Add reviewed-head manual-check handoff"
```

### Task 3: Update the active contract to four cycles

**Files:**
- Modify: `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- Modify: `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- Modify: `docs/operating-model/local-maintainer-activation.md`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-07-09-maintainer-manual-check-handoff-design.md`

- [ ] **Step 1: Amend durable contracts**

Document:

- four review/fix cycles with a fresh independent review after every fix;
- immediate hard stops for owner decisions, model/schema changes, conflicts,
  stale heads, and capability failures;
- reviewed-head exact-lease push only for `manual-check`;
- reviewed-but-unvalidated machine evidence;
- push-journal recovery and the impossibility of readiness without validation;
- access-level source URLs as the union of access trust group refs.

Mark the focused design as implemented only after code verification passes.

- [ ] **Step 2: Verify active wording and stale wording boundaries**

```bash
rg -n "two review/fix|at most two" \
  docs/operating-model/local-maintainer-activation.md \
  docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md
rg -n "four review/fix|at most four" \
  docs/operating-model/local-maintainer-activation.md \
  docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md
```

Expected: no active two-cycle wording and explicit four-cycle wording. Do not
rewrite the superseded design or historical implementation plan.

- [ ] **Step 3: Commit Task 3**

```bash
git add docs/architecture/adr/0011-local-codex-maintainer-control-plane.md \
  docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md \
  docs/operating-model/local-maintainer-activation.md \
  docs/engineering-notes.md \
  docs/superpowers/specs/2026-07-09-maintainer-manual-check-handoff-design.md
git commit -m "Document resumable manual-check curation"
```

### Task 4: Verify, review, merge, and activate locally

**Files:**
- Verify all files above
- Modify after merge: `~/.codex/skills/snowcast-maintainer/SKILL.md`
- Update after merge through Codex automation API: `snowcast-catalog-pr-maintainer`

- [ ] **Step 1: Run fresh focused verification**

```bash
uv run pytest -q tests/test_catalog_trust.py
uv run pytest -q tests/test_maintainer_*.py
uv run ruff check app/domain/catalog_trust.py ops/maintainer tests/test_catalog_trust.py tests/test_maintainer_*.py
uv run ruff format --check app/domain/catalog_trust.py ops/maintainer tests/test_catalog_trust.py tests/test_maintainer_*.py
git diff --check
```

- [ ] **Step 2: Run the complete repository test suite**

```bash
uv run pytest -q
```

- [ ] **Step 3: Run scoped advisory feature review**

Review security/privacy, AI reliability, release/change management, and
observability/ops. Resolve every Blocker/High finding before publication.

- [ ] **Step 4: Publish and merge normally**

Push `codex/maintainer-manual-check-handoff`, open a ready PR against `main`,
wait for all required GitHub checks, and merge only the unchanged reviewed
head. Verify local and remote `main` contain the merge commit.

- [ ] **Step 5: Update the installed skill**

Change the installed curation worker contract to four cycles and require
`publish manual-check` whenever unresolved reviewed work must be pushed and
paused. Validate the skill without exposing credentials or unrelated files.

- [ ] **Step 6: Update the persisted automation through the app API**

Preserve name, schedule, model, reasoning effort, execution environment,
working directory, destination, and active state. Change only the prompt phrase
from “at most two review/fix cycles” to “at most four review/fix cycles” and
require the merged `publish manual-check` handoff for unresolved reviewed work.
Read the persisted TOML afterward to verify the actual stored record.

- [ ] **Step 7: Leave PR #31 recovery untouched**

Confirm `/Users/awownysz/.codex/worktrees/1180/ai-sports-travel-planner` remains
clean at `e51a11a`. Do not push, rebase, label, or otherwise recover it until
the owner starts the separate recovery step.

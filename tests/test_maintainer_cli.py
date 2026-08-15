from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.cli import HANDLERS, main
from ops.maintainer.curation_state import (
    CheckpointCompletedEvent,
    CheckpointStartedEvent,
    CurationCheckpointStage,
    CurationGeneration,
    CurationGenerationStore,
    GenerationPreparedEvent,
    checkpoint_transaction_id,
    project_generation,
)
from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    ErrorStage,
    MaintainerError,
)
from ops.maintainer.git_ops import (
    CiRepairCheckpoint,
    ContinuationReplayResult,
    CurationCheckpointIntegrityError,
    CurationCheckpointRefs,
    CurationRecoveryCheckpoint,
    GitTransportError,
    GuardedSyncResult,
    LegacyCurationRef,
    RebaseConflictError,
    RemediationCheckpointRefs,
    RepositorySafetyError,
    ReviewedCheckpointRefs,
    StaleRemoteHeadError,
)
from ops.maintainer.github import GitHubComment, GitHubError
from ops.maintainer.intent import IntentDiffEntry, IntentSnapshot
from ops.maintainer.models import (
    CheckSummary,
    MachineState,
    MaintainerState,
    PullRequest,
)
from ops.maintainer.publication import (
    create_publication_text,
    render_machine_state,
    trusted_machine_state,
    trusted_outcome_state,
)
from ops.maintainer.runtime import RunLease
from ops.maintainer.state import (
    CiContinuation,
    CiContinuationPhase,
    ContinuationStatus,
    ContinuationValidationStatus,
    PushJournal,
    PushPhase,
    ReviewedContinuation,
    StateStore,
    StateStoreError,
    TerminalPublicationIntent,
    TerminalPublicationPhase,
    WorkPhase,
)
from ops.maintainer.validation import (
    DeltaValidationResult,
    ProposalValidationResult,
    ValidationCommandObservation,
    ValidationResult,
)

pytestmark = pytest.mark.db_free

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
NOW = datetime(2026, 7, 8, 10, tzinfo=UTC)
CANDIDATE = "stay_destination:nendaz"
CANONICAL_GRAPH = (
    "## Resulting Graph\n\n"
    "```mermaid\n"
    "flowchart LR\n"
    '  destination_1["Stay destination<br/>Nendaz"]\n'
    "```\n"
)
BRANCH = "codex/catalog-curation-nendaz"
GENERATION_ID = "1" * 32


@pytest.fixture(autouse=True)
def _stub_manual_check_resulting_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ops.maintainer.capabilities.immutable_resulting_graph_markdown",
        lambda _repository, _revision, _report_path: CANONICAL_GRAPH,
    )


def _catalog_json(*, include_candidate: bool = False) -> str:
    ski_regions: list[dict[str, object]] = []
    stay_destinations: list[dict[str, object]] = []
    if include_candidate:
        ski_regions.append(
            {
                "ski_region_id": "nendaz",
                "name": "Nendaz",
                "grouping_policy": "trip_market",
            }
        )
        stay_destinations.append(
            {
                "stay_destination_id": "nendaz",
                "name": "Nendaz",
                "country": "Switzerland",
                "region": "Valais",
                "price_level": "medium",
                "latitude": 46.18,
                "longitude": 7.29,
                "trip_market_region_id": "nendaz",
            }
        )
    return json.dumps(
        {
            "schema_version": 2,
            "ski_regions": ski_regions,
            "stay_destinations": stay_destinations,
            "stay_bases": [],
            "ski_areas": [],
            "ski_area_access": [],
            "terrain_domains": [],
            "lift_pass_products": [],
            "rental_display_facts": [],
        }
    )


def _pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "number": 42,
        "title": "Curate Nendaz",
        "url": "https://github.com/lampssy/ai-sports-travel-planner/pull/42",
        "base_ref_name": "main",
        "head_ref_name": BRANCH,
        "head_repository_owner": "lampssy",
        "is_cross_repository": False,
        "is_draft": False,
        "lifecycle_state": "OPEN",
        "created_at": NOW,
        "labels": frozenset({"lane:catalog-curation"}),
        "head_sha": SHA_A,
        "mergeable": "MERGEABLE",
        "check_state": "success",
        "changed_paths": frozenset(
            {
                "app/data/catalog.json",
                "docs/catalog-curation/nendaz.json",
            }
        ),
        "body": "Owner text",
    }
    values.update(overrides)
    number = int(values["number"])
    if "url" not in overrides:
        values["url"] = (
            f"https://github.com/lampssy/ai-sports-travel-planner/pull/{number}"
        )
    return PullRequest.model_validate(values)


def _sync() -> GuardedSyncResult:
    return GuardedSyncResult(
        target_branch=BRANCH,
        original_head=SHA_A,
        rebased_head=SHA_B,
        backup_ref=(
            f"refs/snowcast-maintainer/backups/pr-42/20260708T100000Z-{SHA_A[:12]}"
        ),
        prepared_ref=(
            f"refs/snowcast-maintainer/prepared/pr-42/{SHA_D[:12]}-{SHA_B[:12]}"
        ),
        base_head=SHA_D,
        merge_base=SHA_C,
    )


def _curation_generation() -> CurationGeneration:
    report = "docs/catalog-curation/nendaz.json"
    transaction_id = checkpoint_transaction_id(
        GENERATION_ID,
        CurationCheckpointStage.REVIEWED,
        SHA_C,
        report,
        SHA_D,
    )
    checkpoint_ref = (
        f"refs/snowcast-maintainer/curation/pr-42/{GENERATION_ID}/"
        f"{transaction_id}/checkpoint"
    )
    squash_ref = (
        f"refs/snowcast-maintainer/curation/pr-42/{GENERATION_ID}/"
        f"{transaction_id}/replay"
    )
    sync = _sync()
    return CurationGeneration(
        schema_version=2,
        work_id="curation-pr-42",
        pr_number=42,
        generation_number=1,
        generation_id=GENERATION_ID,
        created_at=NOW,
        selected_head=SHA_A,
        target_branch=BRANCH,
        sync=sync,
        events=(
            GenerationPreparedEvent(
                sequence=1,
                recorded_at=NOW,
                prepared_head=sync.rebased_head,
            ),
            CheckpointStartedEvent(
                sequence=2,
                recorded_at=NOW + timedelta(seconds=1),
                transaction_id=transaction_id,
                stage=CurationCheckpointStage.REVIEWED,
                head=SHA_C,
                report_path=report,
                validation_base=SHA_D,
                expected_checkpoint_ref=checkpoint_ref,
                expected_squash_ref=squash_ref,
            ),
            CheckpointCompletedEvent(
                sequence=3,
                recorded_at=NOW + timedelta(seconds=2),
                transaction_id=transaction_id,
                checkpoint_ref=checkpoint_ref,
                squash_ref=squash_ref,
            ),
        ),
    )


def _legacy_reviewed_continuation(lease: RunLease) -> ReviewedContinuation:
    sync = _sync()
    return ReviewedContinuation(
        work_id="curation-pr-42",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=NOW,
        pr_number=42,
        selected_head=SHA_A,
        reviewed_head=SHA_C,
        report_path="docs/catalog-curation/nendaz.json",
        sync=sync,
        reviewed_ref=(
            f"refs/snowcast-maintainer/reviewed/pr-42/{SHA_A[:12]}-{SHA_C[:12]}"
        ),
        squash_ref=(
            f"refs/snowcast-maintainer/continuations/pr-42/{SHA_D[:12]}-{SHA_C[:12]}"
        ),
        status=ContinuationStatus.AVAILABLE,
        validation_status=ContinuationValidationStatus.NOT_RUN,
    )


def test_curation_checkpoint_help_requires_exact_prepare_time_base(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["checkpoint", "curation", "--help"])

    assert exc_info.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "detached clean checkout at the exact prepare-time base" in help_text
    assert "must not be the checkpoint worktree" in help_text


def test_curation_validation_help_requires_exact_prepare_time_base(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["validate", "curation", "--help"])

    assert exc_info.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "detached clean checkout at the exact prepare-time base" in help_text
    assert "must not be the reviewed worktree" in help_text


def _snapshot() -> IntentSnapshot:
    changed_paths = frozenset(
        {
            "app/data/catalog.json",
            "app/data/resort_trust_manifest.json",
            "docs/catalog-curation/nendaz.json",
        }
    )
    entries = tuple(
        IntentDiffEntry(
            path=path,
            old_mode="100644",
            new_mode="100644",
            old_oid=SHA_A,
            new_oid=SHA_B,
            status="M",
        )
        for path in sorted(changed_paths)
    )
    return IntentSnapshot(
        changed_paths=changed_paths,
        diff_entries=entries,
        catalog_targets=frozenset({CANDIDATE}),
        report_targets=frozenset({CANDIDATE}),
    )


def _validation_result() -> ValidationResult:
    return ValidationResult(
        validated_head=SHA_B,
        commands_completed=3,
        observations=tuple(
            ValidationCommandObservation(
                command_index=index,
                stdout_characters=0,
                stderr_characters=0,
                output_truncated=False,
            )
            for index in range(1, 4)
        ),
        resulting_graph_markdown=CANONICAL_GRAPH,
    )


def _delta_validation_result() -> DeltaValidationResult:
    return DeltaValidationResult(
        remediation_head=SHA_C,
        commands_completed=2,
        observations=tuple(
            ValidationCommandObservation(
                command_index=index,
                stdout_characters=0,
                stderr_characters=0,
                output_truncated=False,
            )
            for index in range(1, 3)
        ),
    )


@dataclass
class FakeGitHub:
    pull_requests: dict[int, PullRequest] = field(
        default_factory=lambda: {42: _pull_request()}
    )
    comments: dict[int, list[GitHubComment]] = field(default_factory=dict)
    closed: list[PullRequest] = field(default_factory=list)
    labels_changed: bool = True
    ensured_labels: int = 0
    body_writes: int = 0
    comment_creates: int = 0
    label_writes: int = 0
    pr_creates: int = 0
    get_pull_request_calls: int = 0
    pull_request_head_reads: list[str] = field(default_factory=list)
    failure: Exception | None = None
    before_mutation: Callable[[], None] | None = None

    def _fail(self) -> None:
        if self.failure is not None:
            raise self.failure

    def _before_mutation(self) -> None:
        self._fail()
        if self.before_mutation is not None:
            self.before_mutation()

    def list_all_open_pull_requests(self) -> list[PullRequest]:
        self._fail()
        return [
            item
            for item in self.pull_requests.values()
            if item.lifecycle_state == "OPEN"
        ]

    def list_closed_discovery_pull_requests(self) -> list[PullRequest]:
        self._fail()
        return list(self.closed)

    def get_pull_request(self, number: int) -> PullRequest:
        self._fail()
        self.get_pull_request_calls += 1
        pull_request = self.pull_requests[number]
        if self.pull_request_head_reads:
            return pull_request.model_copy(
                update={"head_sha": self.pull_request_head_reads.pop(0)}
            )
        return pull_request

    def list_issue_comments(self, number: int) -> Sequence[GitHubComment]:
        self._fail()
        return tuple(self.comments.get(number, ()))

    def ensure_labels(self, definitions: object) -> bool:
        self._before_mutation()
        self.ensured_labels += 1
        return self.labels_changed

    def update_pull_request_body(self, number: int, body: str) -> None:
        self._before_mutation()
        self.body_writes += 1
        self.pull_requests[number] = self.pull_requests[number].model_copy(
            update={"body": body}
        )

    def create_comment(self, number: int, body: str) -> int:
        self._before_mutation()
        self.comment_creates += 1
        comment_id = 100 + self.comment_creates
        self.comments.setdefault(number, []).append(
            GitHubComment(comment_id, body, "lampssy")
        )
        return comment_id

    def update_comment(self, comment_id: int, body: str) -> None:
        self._before_mutation()
        for number, comments in self.comments.items():
            for index, comment in enumerate(comments):
                if comment.comment_id == comment_id:
                    comments[index] = GitHubComment(comment_id, body, "lampssy")
                    self.comments[number] = comments
                    return
        raise AssertionError("comment not found")

    def update_labels(
        self,
        number: int,
        add: set[str] | frozenset[str],
        remove: set[str] | frozenset[str],
    ) -> None:
        self._before_mutation()
        self.label_writes += 1
        labels = (set(self.pull_requests[number].labels) - set(remove)) | set(add)
        self.pull_requests[number] = self.pull_requests[number].model_copy(
            update={"labels": frozenset(labels)}
        )

    def create_draft_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
    ) -> int:
        self._before_mutation()
        self.pr_creates += 1
        number = 70 + self.pr_creates
        self.pull_requests[number] = _pull_request(
            number=number,
            title=title,
            body=body,
            head_ref_name=branch,
            head_sha=SHA_B,
            labels=frozenset(),
            is_draft=True,
        )
        return number

    def find_pull_requests_by_head(
        self,
        branch: str,
        head_sha: str,
    ) -> list[PullRequest]:
        self._fail()
        return [
            item
            for item in self.pull_requests.values()
            if item.head_ref_name == branch and item.head_sha == head_sha
        ]


@dataclass
class FakeRepository:
    head: str = SHA_A
    remote: str | None = SHA_A
    prepared: GuardedSyncResult = field(default_factory=_sync)
    snapshot: IntentSnapshot = field(default_factory=_snapshot)
    prepare_error: Exception | None = None
    revalidate_error: Exception | None = None
    push_error: Exception | None = None
    after_push: Callable[[], None] | None = None
    after_push_error: Exception | None = None
    prepare_calls: int = 0
    revalidate_calls: int = 0
    push_calls: int = 0
    create_only_calls: int = 0
    github: FakeGitHub | None = None
    root: Path = Path("/tmp/snowcast-test-repository")
    main_head: str = SHA_A
    main_catalog_json: str = field(default_factory=_catalog_json)
    fetch_main_calls: int = 0
    continuation_result: str = "unchanged"
    curation_recovery_error: Exception | None = None
    curation_recovery_calls: list[tuple[CurationRecoveryCheckpoint, bool]] = field(
        default_factory=list
    )
    curation_continue_calls: list[CurationRecoveryCheckpoint] = field(
        default_factory=list
    )
    curation_checkpoint_calls: list[tuple[str, str]] = field(default_factory=list)
    curation_checkpoint_error: Exception | None = None
    remediation_replay_error: Exception | None = None
    remediation_prepare_calls: int = 0
    remediation_continue_calls: int = 0
    remediation_restart_flags: list[bool] = field(default_factory=list)
    non_test_tree_digest_calls: list[str] = field(default_factory=list)
    ci_repair_prepare_calls: list[PullRequest] = field(default_factory=list)
    ci_repair_checkpoint_calls: list[dict[str, object]] = field(default_factory=list)
    ci_repair_revalidate_calls: list[dict[str, object]] = field(default_factory=list)
    ci_repair_checkpoint_error: Exception | None = None
    ci_repair_revalidate_error: Exception | None = None
    ci_repair_paths: frozenset[str] = frozenset({"tests/test_catalog_models.py"})
    push_exact_calls: list[tuple[str, str, str]] = field(default_factory=list)
    push_exact_error: Exception | None = None
    push_exact_after_error: Exception | None = None
    legacy_refs: tuple[LegacyCurationRef, ...] = ()
    legacy_archive_calls: int = 0

    def legacy_curation_refs(
        self,
        archive_id: str,
    ) -> tuple[LegacyCurationRef, ...]:
        del archive_id
        return self.legacy_refs

    def archive_legacy_curation_refs(
        self,
        refs: Sequence[LegacyCurationRef],
    ) -> int:
        assert tuple(refs) == self.legacy_refs
        self.legacy_archive_calls += 1
        return len(refs)

    def current_head(self) -> str:
        return self.head

    def verify_validation_base(self, expected_head: str) -> None:
        assert self.head == expected_head

    def fetch_main(self) -> str:
        self.fetch_main_calls += 1
        return self.main_head

    def show_text(self, revision: str, path: str) -> str:
        assert revision == self.main_head
        assert path == "app/data/catalog.json"
        return self.main_catalog_json

    def prepare_guarded_sync(self, pull_request: PullRequest) -> GuardedSyncResult:
        self.prepare_calls += 1
        if self.prepare_error is not None:
            raise self.prepare_error
        self.head = self.prepared.rebased_head
        return self.prepared

    def verify_immutable_diff(self, base: str, head: str) -> IntentSnapshot:
        assert base == SHA_A
        assert head == SHA_B
        return self.snapshot

    def revalidate_prepared_result(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> IntentSnapshot:
        self.revalidate_calls += 1
        if self.revalidate_error is not None:
            raise self.revalidate_error
        assert pull_request.number == 42
        assert result == self.prepared
        assert reviewed_head == self.head
        return self.snapshot

    def checkpoint_reviewed_continuation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
    ) -> ReviewedCheckpointRefs:
        assert pull_request.number == 42
        assert result == self.prepared
        assert reviewed_head == self.head
        return ReviewedCheckpointRefs(
            reviewed_ref=(
                f"refs/snowcast-maintainer/reviewed/pr-42/"
                f"{result.original_head[:12]}-{reviewed_head[:12]}"
            ),
            squash_ref=(
                f"refs/snowcast-maintainer/continuations/pr-42/"
                f"{result.base_head[:12]}-{reviewed_head[:12]}"
            ),
        )

    def revalidate_reviewed_checkpoint(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        refs: ReviewedCheckpointRefs,
    ) -> None:
        assert pull_request.number == 42
        assert result == self.prepared
        assert reviewed_head == self.head
        assert refs.reviewed_ref.startswith("refs/snowcast-maintainer/reviewed/pr-42/")

    def prepare_curation_recovery(
        self,
        pull_request: PullRequest,
        recovery: CurationRecoveryCheckpoint,
        *,
        restart_interrupted: bool = False,
    ) -> ContinuationReplayResult:
        assert pull_request.number == recovery.pr_number
        self.curation_recovery_calls.append((recovery, restart_interrupted))
        if self.curation_recovery_error is not None:
            raise self.curation_recovery_error
        if self.continuation_result == "conflict":
            return ContinuationReplayResult(
                result="conflict",
                base_head=SHA_D,
                conflict_paths=("app/data/catalog.json",),
            )
        if self.continuation_result == "prepared":
            replay_sync = recovery.sync.model_copy(
                update={"base_head": SHA_C, "rebased_head": SHA_D}
            )
            self.prepared = replay_sync
            self.head = SHA_D
            return ContinuationReplayResult(
                result="prepared",
                base_head=SHA_C,
                head=SHA_D,
                sync=replay_sync,
            )
        self.head = recovery.checkpoint_head
        return ContinuationReplayResult(
            result="unchanged",
            base_head=recovery.sync.base_head,
            head=recovery.checkpoint_head,
            sync=recovery.sync,
        )

    def continue_curation_conflict(
        self,
        pull_request: PullRequest,
        recovery: CurationRecoveryCheckpoint,
    ) -> ContinuationReplayResult:
        self.curation_continue_calls.append(recovery)
        self.continuation_result = "prepared"
        return self.prepare_curation_recovery(pull_request, recovery)

    def checkpoint_curation_generation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        checkpoint_head: str,
        generation_id: str,
        transaction_id: str,
    ) -> CurationCheckpointRefs:
        assert pull_request.number == 42
        assert result == self.prepared
        assert checkpoint_head == self.head
        self.curation_checkpoint_calls.append((generation_id, transaction_id))
        if self.curation_checkpoint_error is not None:
            raise self.curation_checkpoint_error
        prefix = (
            f"refs/snowcast-maintainer/curation/pr-42/{generation_id}/{transaction_id}/"
        )
        return CurationCheckpointRefs(
            checkpoint_ref=f"{prefix}checkpoint",
            squash_ref=f"{prefix}replay",
        )

    def revalidate_curation_checkpoint(
        self,
        pull_request: PullRequest,
        recovery: CurationRecoveryCheckpoint,
    ) -> None:
        assert pull_request.number == recovery.pr_number
        assert recovery.sync == self.prepared

    def prepare_reviewed_continuation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        refs: ReviewedCheckpointRefs,
    ) -> ContinuationReplayResult:
        self.revalidate_reviewed_checkpoint(pull_request, result, reviewed_head, refs)
        if self.continuation_result == "conflict":
            return ContinuationReplayResult(
                result="conflict",
                base_head=SHA_D,
                conflict_paths=("app/data/catalog.json",),
            )
        if self.continuation_result == "prepared":
            replay_sync = result.model_copy(
                update={"base_head": SHA_C, "rebased_head": SHA_D}
            )
            self.prepared = replay_sync
            self.head = SHA_D
            return ContinuationReplayResult(
                result="prepared",
                base_head=SHA_C,
                head=SHA_D,
                sync=replay_sync,
            )
        self.head = reviewed_head
        return ContinuationReplayResult(
            result="unchanged",
            base_head=result.base_head,
            head=reviewed_head,
            sync=result,
        )

    def continue_reviewed_conflict(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        reviewed_head: str,
        refs: ReviewedCheckpointRefs,
    ) -> ContinuationReplayResult:
        self.continuation_result = "prepared"
        return self.prepare_reviewed_continuation(
            pull_request, result, reviewed_head, refs
        )

    def checkpoint_remediation_continuation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        remediation_head: str,
    ) -> RemediationCheckpointRefs:
        assert pull_request.number == 42
        assert result == self.prepared
        assert remediation_head == self.head
        return RemediationCheckpointRefs(
            remediation_ref=(
                f"refs/snowcast-maintainer/remediation/pr-42/"
                f"{result.original_head[:12]}-{remediation_head[:12]}"
            ),
            squash_ref=(
                "refs/snowcast-maintainer/remediation-continuations/pr-42/"
                f"{result.base_head[:12]}-{remediation_head[:12]}"
            ),
        )

    def prepare_remediation_continuation(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        remediation_head: str,
        refs: RemediationCheckpointRefs,
        *,
        restart_interrupted: bool = False,
    ) -> ContinuationReplayResult:
        self.remediation_prepare_calls += 1
        self.remediation_restart_flags.append(restart_interrupted)
        return self._remediation_replay(
            pull_request,
            result,
            remediation_head,
            refs,
        )

    def _remediation_replay(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        remediation_head: str,
        refs: RemediationCheckpointRefs,
    ) -> ContinuationReplayResult:
        assert pull_request.number == 42
        assert result == self.prepared
        assert refs.remediation_ref.startswith(
            "refs/snowcast-maintainer/remediation/pr-42/"
        )
        if self.remediation_replay_error is not None:
            raise self.remediation_replay_error
        if self.continuation_result == "conflict":
            return ContinuationReplayResult(
                result="conflict",
                base_head=SHA_D,
                conflict_paths=("app/data/catalog.json",),
            )
        if self.continuation_result == "prepared":
            replay_sync = result.model_copy(
                update={"base_head": SHA_C, "rebased_head": SHA_D}
            )
            self.prepared = replay_sync
            self.head = SHA_D
            return ContinuationReplayResult(
                result="prepared",
                base_head=SHA_C,
                head=SHA_D,
                sync=replay_sync,
            )
        self.head = remediation_head
        return ContinuationReplayResult(
            result="unchanged",
            base_head=result.base_head,
            head=remediation_head,
            sync=result,
        )

    def continue_remediation_conflict(
        self,
        pull_request: PullRequest,
        result: GuardedSyncResult,
        remediation_head: str,
        refs: RemediationCheckpointRefs,
    ) -> ContinuationReplayResult:
        self.remediation_continue_calls += 1
        self.continuation_result = "prepared"
        return self._remediation_replay(pull_request, result, remediation_head, refs)

    def push_with_lease(self, sync: GuardedSyncResult, reviewed_head: str) -> None:
        self.push_calls += 1
        if self.push_error is not None:
            raise self.push_error
        assert sync == self.prepared
        assert reviewed_head == self.head
        self.remote = reviewed_head
        if self.github is not None:
            current = self.github.pull_requests[42]
            self.github.pull_requests[42] = current.model_copy(
                update={"head_sha": reviewed_head}
            )
            if self.after_push is not None:
                self.after_push()
            self.github.failure = self.after_push_error

    def remote_head(self, branch: str) -> str:
        assert branch == BRANCH
        if self.remote is None:
            raise AssertionError("remote is absent")
        return self.remote

    def optional_remote_head(self, branch: str) -> str | None:
        assert branch == BRANCH
        return self.remote

    def non_test_tree_digest(self, revision: str) -> str:
        self.non_test_tree_digest_calls.append(revision)
        return "d" * 64

    def prepare_ci_repair(self, pull_request: PullRequest) -> str:
        self.ci_repair_prepare_calls.append(pull_request)
        self.head = pull_request.head_sha
        return self.head

    def checkpoint_ci_repair(
        self,
        *,
        pull_request: PullRequest,
        semantic_head: str,
        current_head: str,
        repair_head: str,
        expected_non_test_tree_digest: str,
    ) -> CiRepairCheckpoint:
        self.ci_repair_checkpoint_calls.append(
            {
                "pull_request": pull_request,
                "semantic_head": semantic_head,
                "current_head": current_head,
                "repair_head": repair_head,
                "expected_non_test_tree_digest": expected_non_test_tree_digest,
            }
        )
        if self.ci_repair_checkpoint_error is not None:
            raise self.ci_repair_checkpoint_error
        if self.head != repair_head:
            raise RepositorySafetyError(
                "current HEAD does not match the requested CI repair head"
            )
        return CiRepairCheckpoint(
            repair_head=repair_head,
            repair_ref=(
                f"refs/snowcast-maintainer/ci-repairs/pr-{pull_request.number}/"
                f"{current_head[:12]}-{repair_head[:12]}"
            ),
            repair_paths=self.ci_repair_paths,
            non_test_tree_digest=expected_non_test_tree_digest,
        )

    def revalidate_ci_repair_checkpoint(
        self,
        *,
        pull_request: PullRequest,
        semantic_head: str,
        current_head: str,
        checkpoint: CiRepairCheckpoint,
    ) -> CiRepairCheckpoint:
        self.ci_repair_revalidate_calls.append(
            {
                "pull_request": pull_request,
                "semantic_head": semantic_head,
                "current_head": current_head,
                "checkpoint": checkpoint,
            }
        )
        if self.ci_repair_revalidate_error is not None:
            raise self.ci_repair_revalidate_error
        self.head = checkpoint.repair_head
        return checkpoint

    def push_create_only(self, branch: str, reviewed_head: str) -> None:
        assert branch == BRANCH
        assert self.remote is None
        assert reviewed_head == SHA_B
        self.create_only_calls += 1
        self.remote = reviewed_head

    def push_exact_with_lease(
        self,
        branch: str,
        expected_head: str,
        repair_head: str,
    ) -> None:
        self.push_exact_calls.append((branch, expected_head, repair_head))
        if self.push_exact_error is not None:
            raise self.push_exact_error
        if self.remote != expected_head:
            raise StaleRemoteHeadError("remote head moved")
        if self.head != repair_head:
            raise RepositorySafetyError(
                "current HEAD does not match the exact CI repair head"
            )
        self.remote = repair_head
        if self.github is not None:
            current = self.github.pull_requests[42]
            self.github.pull_requests[42] = current.model_copy(
                update={"head_sha": repair_head}
            )
            if self.after_push is not None:
                self.after_push()
            self.github.failure = self.after_push_error
        if self.push_exact_after_error is not None:
            raise self.push_exact_after_error


def _private_state_dir(tmp_path: Path) -> Path:
    path = tmp_path / "state"
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


def _private_text(state_dir: Path, name: str, text: str) -> str:
    path = state_dir / name
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return name


def _invoke(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    *,
    github: FakeGitHub | None = None,
    repository: FakeRepository | None = None,
    base_repository: FakeRepository | None = None,
    curation_validator: Callable[..., ValidationResult] | None = None,
    delta_validator: Callable[..., DeltaValidationResult] | None = None,
    proposal_validator: Callable[..., ProposalValidationResult] | None = None,
    catalog_keys_provider: Callable[[], frozenset[str]] | None = None,
    repository_root: Path | None = None,
) -> tuple[int, dict[str, object]]:
    result = main(
        argv,
        github=github,
        repository=repository,
        base_repository=base_repository,
        curation_validator=curation_validator,
        curation_delta_validator=delta_validator,
        proposal_validator=proposal_validator,
        catalog_keys_provider=catalog_keys_provider,
        repository_root=repository_root,
        now=lambda: NOW,
    )
    output = capsys.readouterr().out
    assert output.count("\n") == 1
    return result, json.loads(output)


def _acquire(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    worker: str,
) -> str:
    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", worker],
    )
    assert code == 0, payload
    outcome = payload["outcome"]
    assert isinstance(outcome, dict)
    run_id = outcome["lease_run_id"]
    assert isinstance(run_id, str)
    return run_id


def _assert_outcome(
    payload: dict[str, object],
    *,
    worker: str,
    mutation: bool,
    run_id: str | None,
) -> dict[str, object]:
    outcome = payload["outcome"]
    assert isinstance(outcome, dict)
    assert outcome["worker"] == worker
    assert outcome["mutation_occurred"] is mutation
    assert outcome.get("lease_run_id") == run_id
    assert isinstance(outcome["terminal_reason"], str)
    return outcome


def _ci_continuation_for_cli(lease: RunLease) -> CiContinuation:
    return CiContinuation(
        work_id="curation-pr-42",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        updated_at=NOW - timedelta(minutes=2),
        pr_number=42,
        branch=BRANCH,
        semantic_head=SHA_B,
        current_head=SHA_B,
        report_path="docs/catalog-curation/nendaz.json",
        resulting_graph_markdown=CANONICAL_GRAPH,
        non_test_tree_digest="d" * 64,
        phase=CiContinuationPhase.INITIAL_WAIT,
        repair_attempted=False,
        first_wait_started_at=NOW - timedelta(minutes=2),
        first_wait_seconds=0,
        repair_active_seconds=0,
        second_wait_seconds=0,
    )


EXPECTED_HANDLERS = {
    ("migrate", "curation-state"),
    ("inspect", "curation"),
    ("inspect", "discovery"),
    ("prepare", "curation"),
    ("prepare", "ci-repair"),
    ("checkpoint", "curation"),
    ("checkpoint", "ci-repair"),
    ("invalidate", "ci-continuation"),
    ("validate", "curation"),
    ("validate", "proposal"),
    ("publish", "push"),
    ("publish", "ci-repair"),
    ("publish", "manual-check"),
    ("publish", "recover"),
    ("publish", "proposal"),
    ("publish", "outcome"),
    ("publish", "state"),
    ("publish", "ensure-labels"),
    ("publication-input", "create"),
}


@pytest.mark.parametrize(
    ("family", "extra_args", "expected"),
    (
        ("prepare", (), {"pr": 42}),
        ("checkpoint", ("--head", SHA_C), {"pr": 42, "head": SHA_C}),
        ("publish", (), {"pr": 42}),
    ),
)
def test_prepare_ci_repair_checkpoint_ci_repair_publish_ci_repair_dispatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    extra_args: tuple[str, ...],
    expected: dict[str, object],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    repository = FakeRepository()
    observed: dict[str, object] = {}

    def handler(args: object, dependencies: object) -> dict[str, object]:
        observed.update(
            {
                "pr": getattr(args, "pr"),
                "head": getattr(args, "head", None),
                "repository": getattr(dependencies, "repository"),
            }
        )
        return {"command": f"{family}-ci-repair"}

    monkeypatch.setitem(HANDLERS, (family, "ci-repair"), handler)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            family,
            "ci-repair",
            "--pr",
            "42",
            *extra_args,
            "--run-id",
            "1" * 32,
        ],
        repository=repository,
    )

    assert code == 0
    assert payload["status"] == "ok"
    assert payload["command"] == f"{family}-ci-repair"
    assert payload["outcome"]["worker"] == "curation"
    assert observed["repository"] is repository
    assert {key: observed[key] for key in expected} == expected


def test_invalidate_ci_continuation_dispatches_only_pr_and_run_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    observed: dict[str, object] = {}

    def handler(args: object, dependencies: object) -> dict[str, object]:
        observed.update(
            {
                "pr": getattr(args, "pr"),
                "repository": getattr(dependencies, "repository"),
            }
        )
        return {"command": "invalidate-ci-continuation"}

    monkeypatch.setitem(HANDLERS, ("invalidate", "ci-continuation"), handler)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "invalidate",
            "ci-continuation",
            "--pr",
            "42",
            "--run-id",
            "1" * 32,
        ],
    )

    assert code == 0
    assert payload["command"] == "invalidate-ci-continuation"
    assert payload["outcome"]["worker"] == "curation"
    assert observed["pr"] == 42
    assert type(observed["repository"]) is object


@pytest.mark.parametrize(
    ("family", "arguments"),
    (
        ("prepare", ("--run-id", "1" * 32)),
        ("prepare", ("--pr", "42")),
        ("checkpoint", ("--head", SHA_C, "--run-id", "1" * 32)),
        ("checkpoint", ("--pr", "42", "--run-id", "1" * 32)),
        ("checkpoint", ("--pr", "42", "--head", SHA_C)),
        ("publish", ("--run-id", "1" * 32)),
        ("publish", ("--pr", "42")),
    ),
)
def test_prepare_ci_repair_checkpoint_ci_repair_publish_ci_repair_require_arguments(
    capsys: pytest.CaptureFixture[str],
    family: str,
    arguments: tuple[str, ...],
) -> None:
    code, payload = _invoke(
        capsys,
        [family, "ci-repair", *arguments],
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert payload["outcome"]["worker"] == "curation"


@pytest.mark.parametrize(
    "arguments",
    (
        ("--run-id", "1" * 32),
        ("--pr", "42"),
    ),
)
def test_invalidate_ci_continuation_requires_pr_and_run_id(
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    code, payload = _invoke(
        capsys,
        ["invalidate", "ci-continuation", *arguments],
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert payload["outcome"]["worker"] == "curation"


@pytest.mark.parametrize("family", ("prepare", "checkpoint", "publish"))
def test_prepare_ci_repair_checkpoint_ci_repair_publish_ci_repair_reject_policy_flags(
    capsys: pytest.CaptureFixture[str],
    family: str,
) -> None:
    arguments = [
        family,
        "ci-repair",
        "--pr",
        "42",
        "--run-id",
        "1" * 32,
        "--phase",
        "repair-active",
    ]
    if family == "checkpoint":
        arguments[4:4] = ["--head", SHA_C]

    code, payload = _invoke(capsys, arguments)

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert payload["outcome"]["worker"] == "curation"


def _failed_ci_pull_request(**overrides: object) -> PullRequest:
    values: dict[str, object] = {
        "head_sha": SHA_B,
        "check_state": "failure",
        "checks": (
            CheckSummary(
                name="backend",
                status="failure",
                conclusion="failure",
                details_url="https://github.com/lampssy/ai-sports-travel-planner/actions/runs/1",
            ),
        ),
    }
    values.update(overrides)
    return _pull_request(**values)


def test_prepare_ci_repair_consumes_attempt_and_detaches_exact_failed_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _ci_continuation_for_cli(lease)
    store.save_ci_continuation(continuation, lease)
    pull_request = _failed_ci_pull_request()
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(head=SHA_A, remote=SHA_B)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert payload["current_head"] == SHA_B
    assert payload["failed_checks"] == [
        {
            "name": "backend",
            "status": "failure",
            "conclusion": "failure",
            "details_url": (
                "https://github.com/lampssy/ai-sports-travel-planner/actions/runs/1"
            ),
        }
    ]
    assert payload["remaining_repair_seconds"] == 3600
    assert payload["permitted_path_pattern"] == "tests/test_*.py"
    assert repository.ci_repair_prepare_calls == [pull_request]
    active = store.load_ci_continuation(continuation.work_id)
    assert active is not None
    assert active.phase is CiContinuationPhase.REPAIR_ACTIVE
    assert active.repair_attempted is True
    assert active.repair_activity_observed_at == NOW
    assert active.current_head == SHA_B


def test_prepare_ci_repair_successor_adopts_expired_initial_wait_after_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=40),
    )
    continuation = _ci_continuation_for_cli(origin).model_copy(
        update={
            "updated_at": NOW - timedelta(minutes=31),
            "first_wait_started_at": NOW - timedelta(minutes=31),
        }
    )
    store = StateStore(state_dir)
    store.save_ci_continuation(continuation, origin)
    origin.release()
    run_id = _acquire(capsys, state_dir, "curation")
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(remote=SHA_B)

    code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    active = store.load_ci_continuation(continuation.work_id)
    assert active is not None
    assert active.recovery_run_id == run_id
    assert active.phase is CiContinuationPhase.REPAIR_ACTIVE
    assert active.first_wait_seconds == 1800
    assert active.repair_attempted is True


def test_prepare_ci_repair_successor_resumes_active_attempt_then_checkpoints(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=20),
    )
    store = StateStore(state_dir)
    active = _save_active_ci_continuation(
        store,
        origin,
        activity_started_at=NOW - timedelta(minutes=10),
        active_seconds=120,
    )
    origin.release()
    successor = _acquire(capsys, state_dir, "curation")
    pull_request = _failed_ci_pull_request()
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(head=SHA_A, remote=SHA_B)

    prepare_code, prepared = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert prepare_code == 0, prepared
    assert prepared["phase"] == "repair-active"
    assert prepared["resumed"] is True
    assert repository.ci_repair_prepare_calls == [pull_request]
    resumed = store.load_ci_continuation(active.work_id)
    assert resumed is not None
    assert resumed.recovery_run_id == successor
    assert resumed.phase is CiContinuationPhase.REPAIR_ACTIVE
    assert resumed.repair_attempted is True
    assert resumed.first_wait_seconds == active.first_wait_seconds
    assert resumed.repair_active_seconds == active.repair_active_seconds + 300

    repository.head = SHA_C
    checkpoint_code, checkpointed = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "checkpoint",
            "ci-repair",
            "--pr",
            "42",
            "--head",
            SHA_C,
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert checkpoint_code == 0, checkpointed
    reviewed = store.load_ci_continuation(active.work_id)
    assert reviewed is not None
    assert reviewed.phase is CiContinuationPhase.REPAIR_REVIEWED
    assert reviewed.repair_head == SHA_C
    assert reviewed.recovery_run_id == successor


def test_prepare_ci_repair_successor_resumes_reviewed_attempt_then_publishes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=20),
    )
    store = StateStore(state_dir)
    _save_published_initial_push(store, origin)
    reviewed = _save_reviewed_ci_repair(
        store,
        origin,
        reviewed_at=NOW - timedelta(minutes=5),
    )
    origin.release()
    successor = _acquire(capsys, state_dir, "curation")
    pull_request = _failed_ci_pull_request()
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(
        head=SHA_C,
        remote=SHA_B,
        github=github,
    )

    prepare_code, prepared = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert prepare_code == 0, prepared
    assert prepared["phase"] == "repair-reviewed"
    assert prepared["resumed"] is True
    assert prepared["repair_head"] == SHA_C
    assert repository.ci_repair_prepare_calls == []
    assert len(repository.ci_repair_revalidate_calls) == 1
    adopted = store.load_ci_continuation(reviewed.work_id)
    assert adopted is not None
    assert adopted.recovery_run_id == successor
    assert adopted.phase is CiContinuationPhase.REPAIR_REVIEWED
    assert adopted.repair_head == reviewed.repair_head
    assert adopted.repair_ref == reviewed.repair_ref
    assert adopted.repair_paths == reviewed.repair_paths
    assert adopted.first_wait_seconds == reviewed.first_wait_seconds
    assert adopted.repair_active_seconds == reviewed.repair_active_seconds

    publish_code, published = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert publish_code == 0, published
    waiting = store.load_ci_continuation(reviewed.work_id)
    assert waiting is not None
    assert waiting.phase is CiContinuationPhase.SECOND_WAIT
    assert waiting.recovery_run_id == successor
    assert waiting.current_head == SHA_C


def test_prepare_ci_repair_retries_after_successor_adoption_was_persisted(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=20),
    )
    store = StateStore(state_dir)
    reviewed = _save_reviewed_ci_repair(
        store,
        origin,
        reviewed_at=NOW - timedelta(minutes=5),
    )
    origin.release()
    successor = _acquire(capsys, state_dir, "curation")
    repository = FakeRepository(head=SHA_B, remote=SHA_B)
    command = [
        "--state-dir",
        str(state_dir),
        "prepare",
        "ci-repair",
        "--pr",
        "42",
        "--run-id",
        successor,
    ]
    original_adopt = StateStore.adopt_ci_continuation
    injected = False

    def adopt_then_fail_once(
        self: StateStore,
        work_id: str,
        lease: RunLease,
        *,
        now: datetime | None = None,
    ) -> CiContinuation:
        nonlocal injected
        adopted = original_adopt(self, work_id, lease, now=now)
        if not injected:
            injected = True
            raise StateStoreError("injected post-adoption recovery failure")
        return adopted

    monkeypatch.setattr(
        StateStore,
        "adopt_ci_continuation",
        adopt_then_fail_once,
    )

    first_code, first = _invoke(
        capsys,
        command,
        github=FakeGitHub(pull_requests={42: _failed_ci_pull_request()}),
        repository=repository,
    )

    assert first_code == 2
    assert first["reason"] == "invalid-command"
    adopted = store.load_ci_continuation(reviewed.work_id)
    assert adopted is not None
    assert adopted.recovery_run_id == successor
    assert adopted.phase is CiContinuationPhase.REPAIR_REVIEWED
    assert adopted.repair_attempted is True
    assert adopted.first_wait_seconds == reviewed.first_wait_seconds
    assert adopted.repair_active_seconds == reviewed.repair_active_seconds
    assert adopted.repair_head == reviewed.repair_head
    assert adopted.repair_ref == reviewed.repair_ref
    assert adopted.repair_paths == reviewed.repair_paths

    second_code, second = _invoke(
        capsys,
        command,
        github=FakeGitHub(pull_requests={42: _failed_ci_pull_request()}),
        repository=repository,
    )

    assert second_code == 0, second
    assert second["phase"] == "repair-reviewed"
    assert second["resumed"] is True
    retried = store.load_ci_continuation(reviewed.work_id)
    assert retried is not None
    assert retried.recovery_run_id == successor
    assert retried.phase is CiContinuationPhase.REPAIR_REVIEWED
    assert retried.repair_attempted is True
    assert retried.first_wait_seconds == reviewed.first_wait_seconds
    assert retried.repair_active_seconds == reviewed.repair_active_seconds
    assert retried.repair_head == reviewed.repair_head
    assert retried.repair_ref == reviewed.repair_ref
    assert retried.repair_paths == reviewed.repair_paths


@pytest.mark.parametrize(
    "pull_request",
    (
        _pull_request(
            head_sha=SHA_B,
            check_state="pending",
            checks=(CheckSummary(name="backend", status="pending"),),
        ),
        _failed_ci_pull_request(mergeable="CONFLICTING"),
        _failed_ci_pull_request(
            checks=(
                CheckSummary(
                    name="backend",
                    status="failure",
                    conclusion="CANCELLED",
                ),
            ),
        ),
        _failed_ci_pull_request(head_sha=SHA_C),
        _failed_ci_pull_request(head_ref_name="codex/catalog-curation-other"),
    ),
)
def test_prepare_ci_repair_rejects_nonmatching_or_ineligible_live_ci(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pull_request: PullRequest,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    StateStore(state_dir).save_ci_continuation(
        _ci_continuation_for_cli(lease),
        lease,
    )
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(remote=SHA_B)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] in {
        "invalid-command",
        "invalid-github-state",
        "stale-head",
    }
    assert repository.ci_repair_prepare_calls == []


def test_prepare_ci_repair_rejects_second_attempt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    StateStore(state_dir).save_ci_continuation(
        _ci_continuation_for_cli(lease),
        lease,
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(remote=SHA_B)
    command = [
        "--state-dir",
        str(state_dir),
        "prepare",
        "ci-repair",
        "--pr",
        "42",
        "--run-id",
        run_id,
    ]

    first_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )
    second_code, second = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert first_code == 0
    assert second_code == 2
    assert second["reason"] == "invalid-command"
    assert len(repository.ci_repair_prepare_calls) == 1


def _save_active_ci_continuation(
    store: StateStore,
    lease: RunLease,
    *,
    activity_started_at: datetime,
    active_seconds: int = 0,
) -> CiContinuation:
    initial = _ci_continuation_for_cli(lease).model_copy(
        update={
            "updated_at": activity_started_at - timedelta(seconds=1),
            "first_wait_started_at": activity_started_at - timedelta(minutes=1),
        }
    )
    store.save_ci_continuation(initial, lease)
    active = initial.model_copy(
        update={
            "phase": CiContinuationPhase.REPAIR_ACTIVE,
            "repair_attempted": True,
            "repair_activity_observed_at": activity_started_at,
        }
    )
    active = store.advance_ci_continuation(
        active,
        lease,
        now=activity_started_at,
    )
    observed_at = activity_started_at
    while active.repair_active_seconds < active_seconds:
        observed_at += timedelta(
            seconds=min(300, active_seconds - active.repair_active_seconds)
        )
        active = store.record_ci_heartbeat(
            active.work_id,
            lease,
            now=observed_at,
        )
    return active


def test_checkpoint_ci_repair_records_reviewed_exact_test_only_checkpoint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    active = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(minutes=5),
    )
    pull_request = _failed_ci_pull_request()
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(
        head=SHA_C,
        remote=SHA_B,
        ci_repair_paths=frozenset(
            {
                "tests/test_catalog_models.py",
                "tests/test_catalog_trust.py",
            }
        ),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "checkpoint",
            "ci-repair",
            "--pr",
            "42",
            "--head",
            SHA_C,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert payload["repair_head"] == SHA_C
    assert payload["repair_ref"].endswith(f"{SHA_B[:12]}-{SHA_C[:12]}")
    assert payload["repair_paths"] == [
        "tests/test_catalog_models.py",
        "tests/test_catalog_trust.py",
    ]
    assert len(repository.ci_repair_checkpoint_calls) == 1
    assert repository.ci_repair_checkpoint_calls[0] == {
        "pull_request": pull_request,
        "semantic_head": SHA_B,
        "current_head": SHA_B,
        "repair_head": SHA_C,
        "expected_non_test_tree_digest": "d" * 64,
    }
    reviewed = store.load_ci_continuation(active.work_id)
    assert reviewed is not None
    assert reviewed.phase is CiContinuationPhase.REPAIR_REVIEWED
    assert reviewed.repair_active_seconds == 300
    assert reviewed.repair_head == SHA_C
    assert reviewed.repair_ref == payload["repair_ref"]
    assert reviewed.repair_paths == frozenset(payload["repair_paths"])
    assert reviewed.repair_activity_observed_at == NOW


def test_checkpoint_ci_repair_recovers_after_checkpoint_ref_precedes_state_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    active = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(minutes=5),
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(head=SHA_C, remote=SHA_B)
    original_advance = StateStore.advance_ci_continuation
    injected = False

    def fail_first_reviewed_state_write(
        self: StateStore,
        continuation: CiContinuation,
        owned_lease: RunLease,
        *,
        now: datetime,
    ) -> CiContinuation:
        nonlocal injected
        if continuation.phase is CiContinuationPhase.REPAIR_REVIEWED and not injected:
            injected = True
            raise StateStoreError("injected state write failure after checkpoint ref")
        return original_advance(self, continuation, owned_lease, now=now)

    monkeypatch.setattr(
        StateStore,
        "advance_ci_continuation",
        fail_first_reviewed_state_write,
    )
    command = [
        "--state-dir",
        str(state_dir),
        "checkpoint",
        "ci-repair",
        "--pr",
        "42",
        "--head",
        SHA_C,
        "--run-id",
        run_id,
    ]

    first_code, first_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert first_code == 2
    assert first_payload["reason"] == "invalid-command"
    after_failure = store.load_ci_continuation(active.work_id)
    assert after_failure is not None
    assert after_failure.phase is CiContinuationPhase.REPAIR_ACTIVE
    assert len(repository.ci_repair_checkpoint_calls) == 1

    retry_code, retry_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert retry_code == 0, retry_payload
    recovered = store.load_ci_continuation(active.work_id)
    assert recovered is not None
    assert recovered.recovery_run_id == run_id
    assert recovered.phase is CiContinuationPhase.REPAIR_REVIEWED
    assert recovered.repair_head == SHA_C
    assert len(repository.ci_repair_checkpoint_calls) == 2


def test_checkpoint_ci_repair_rejects_exhausted_active_budget_before_git(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    active = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(hours=1),
        active_seconds=3600,
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(head=SHA_C, remote=SHA_B)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "checkpoint",
            "ci-repair",
            "--pr",
            "42",
            "--head",
            SHA_C,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert repository.ci_repair_checkpoint_calls == []
    assert store.load_ci_continuation(active.work_id) == active


@pytest.mark.parametrize(
    "repository",
    (
        FakeRepository(
            head=SHA_C,
            remote=SHA_B,
            ci_repair_checkpoint_error=RepositorySafetyError("worktree must be clean"),
        ),
        FakeRepository(head=SHA_D, remote=SHA_B),
        FakeRepository(
            head=SHA_C,
            remote=SHA_B,
            ci_repair_checkpoint_error=RepositorySafetyError(
                "CI repair diff must not be empty"
            ),
        ),
        FakeRepository(
            head=SHA_C,
            remote=SHA_B,
            ci_repair_checkpoint_error=RepositorySafetyError(
                "CI repair diff contains a disallowed path or file shape"
            ),
        ),
    ),
)
def test_checkpoint_ci_repair_rejects_structurally_invalid_git_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repository: FakeRepository,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    active = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(minutes=1),
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "checkpoint",
            "ci-repair",
            "--pr",
            "42",
            "--head",
            SHA_C,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "unsafe-repository"
    persisted = store.load_ci_continuation(active.work_id)
    assert persisted is not None
    assert persisted.phase is CiContinuationPhase.REPAIR_ACTIVE


def test_checkpoint_ci_repair_rejects_wrong_phase_and_repeat_checkpoint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    store.save_ci_continuation(_ci_continuation_for_cli(lease), lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(head=SHA_C, remote=SHA_B)
    command = [
        "--state-dir",
        str(state_dir),
        "checkpoint",
        "ci-repair",
        "--pr",
        "42",
        "--head",
        SHA_C,
        "--run-id",
        run_id,
    ]

    wrong_phase_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert wrong_phase_code == 2
    assert repository.ci_repair_checkpoint_calls == []

    initial = store.load_ci_continuation("curation-pr-42")
    assert initial is not None
    active = initial.model_copy(
        update={
            "phase": CiContinuationPhase.REPAIR_ACTIVE,
            "repair_attempted": True,
            "repair_activity_observed_at": NOW,
        }
    )
    store.advance_ci_continuation(
        active,
        lease,
        now=NOW,
    )
    first_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )
    second_code, second = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert first_code == 0
    assert second_code == 2
    assert second["reason"] == "invalid-command"
    assert len(repository.ci_repair_checkpoint_calls) == 1


@pytest.mark.parametrize("family", ("prepare", "checkpoint", "publish"))
def test_ci_repair_capabilities_reject_any_unresolved_journal_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    family: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    if family == "prepare":
        continuation = _ci_continuation_for_cli(lease)
        store.save_ci_continuation(continuation, lease)
        repository = FakeRepository(head=SHA_A, remote=SHA_B)
    elif family == "checkpoint":
        continuation = _save_active_ci_continuation(
            store,
            lease,
            activity_started_at=NOW - timedelta(minutes=1),
        )
        repository = FakeRepository(head=SHA_C, remote=SHA_B)
    else:
        _save_published_initial_push(store, lease)
        continuation = _save_reviewed_ci_repair(store, lease)
        repository = FakeRepository(head=SHA_C, remote=SHA_B)
    blocker = PushJournal(
        work_id="curation-pr-43",
        worker="curation",
        origin_run_id=run_id,
        recovery_run_id=run_id,
        pr_number=43,
        branch="codex/catalog-curation-43",
        expected_remote_head=SHA_A,
        new_head=SHA_D,
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(blocker, lease)
    own_journal_before = store.load_push("curation-pr-42")
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    arguments = [
        "--state-dir",
        str(state_dir),
        family,
        "ci-repair",
        "--pr",
        "42",
        "--run-id",
        run_id,
    ]
    if family == "checkpoint":
        arguments[6:6] = ["--head", SHA_C]

    code, payload = _invoke(
        capsys,
        arguments,
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert store.load_ci_continuation(continuation.work_id) == continuation
    assert store.load_push(blocker.work_id) == blocker
    assert store.load_push("curation-pr-42") == own_journal_before
    assert repository.head == (SHA_A if family == "prepare" else SHA_C)
    assert repository.ci_repair_prepare_calls == []
    assert repository.ci_repair_checkpoint_calls == []
    assert repository.ci_repair_revalidate_calls == []
    assert repository.push_exact_calls == []


def test_invalidate_ci_continuation_terminalizes_head_drift_then_exposes_new_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=20),
    )
    store = StateStore(state_dir)
    continuation = _ci_continuation_for_cli(origin)
    store.save_ci_continuation(continuation, origin)
    origin.release()
    successor = _acquire(capsys, state_dir, "curation")
    pull_request = _pull_request(head_sha=SHA_C)
    github = FakeGitHub(pull_requests={42: pull_request})

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "invalidate",
            "ci-continuation",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
    )

    assert code == 0, payload
    assert payload["phase"] == "invalidated"
    assert payload["availability_reason"] == "head-drift"
    invalidated = store.load_ci_continuation(continuation.work_id)
    assert invalidated is not None
    assert invalidated.phase is CiContinuationPhase.INVALIDATED
    assert invalidated.recovery_run_id == successor
    assert invalidated.origin_run_id == continuation.origin_run_id
    assert invalidated.semantic_head == continuation.semantic_head
    assert invalidated.current_head == continuation.current_head
    assert invalidated.first_wait_seconds == 120

    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    assert inspect_code == 0
    assert inventory["ci_continuations"] == []
    assert [candidate["number"] for candidate in inventory["eligible"]] == [42]


@pytest.mark.parametrize(
    ("pull_request", "reason"),
    (
        (_pull_request(head_sha=SHA_B, lifecycle_state="CLOSED"), "closed-or-merged"),
        (
            _pull_request(
                head_sha=SHA_B,
                head_ref_name="codex/catalog-curation-other",
            ),
            "branch-drift",
        ),
        (
            _pull_request(head_sha=SHA_B, is_cross_repository=True),
            "invalid-state",
        ),
    ),
)
def test_invalidate_ci_continuation_uses_refreshed_non_resumable_live_reason(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pull_request: PullRequest,
    reason: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    continuation = _ci_continuation_for_cli(lease)
    store = StateStore(state_dir)
    store.save_ci_continuation(continuation, lease)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "invalidate",
            "ci-continuation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={42: pull_request}),
    )

    assert code == 0, payload
    assert payload["availability_reason"] == reason
    invalidated = store.load_ci_continuation(continuation.work_id)
    assert invalidated is not None
    assert invalidated.phase is CiContinuationPhase.INVALIDATED


@pytest.mark.parametrize(
    "pull_request",
    [
        _pull_request(
            head_sha=SHA_B,
            labels=frozenset(
                {
                    "lane:catalog-curation",
                    "maintainer:working",
                    "maintainer:waiting-ci",
                }
            ),
        ),
        _pull_request(head_sha=SHA_B, mergeable="UNKNOWN"),
    ],
)
def test_invalidate_ci_continuation_rejects_non_authoritative_live_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pull_request: PullRequest,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    continuation = _ci_continuation_for_cli(lease)
    store = StateStore(state_dir)
    store.save_ci_continuation(continuation, lease)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "invalidate",
            "ci-continuation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={42: pull_request}),
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert store.load_ci_continuation(continuation.work_id) == continuation


@pytest.mark.parametrize("live_case", ["conflicting", "recovered-checks"])
def test_invalidate_ci_continuation_terminalizes_helper_owned_phase_aware_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    live_case: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    if live_case == "conflicting":
        continuation = _ci_continuation_for_cli(lease)
        pull_request = _pull_request(head_sha=SHA_B, mergeable="CONFLICTING")
        store.save_ci_continuation(continuation, lease)
    else:
        continuation = _save_active_ci_continuation(
            store,
            lease,
            activity_started_at=NOW - timedelta(minutes=5),
            active_seconds=120,
        )
        pull_request = _pull_request(
            head_sha=SHA_B,
            check_state="success",
            checks=(
                CheckSummary(
                    name="backend",
                    status="success",
                    conclusion="SUCCESS",
                ),
            ),
        )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "invalidate",
            "ci-continuation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={42: pull_request}),
    )

    assert code == 0, payload
    assert payload["availability_reason"] == "invalid-state"
    invalidated = store.load_ci_continuation(continuation.work_id)
    assert invalidated is not None
    assert invalidated.phase is CiContinuationPhase.INVALIDATED
    assert invalidated.repair_attempted is continuation.repair_attempted
    assert invalidated.first_wait_seconds >= continuation.first_wait_seconds
    assert invalidated.repair_active_seconds >= continuation.repair_active_seconds


def test_invalidate_active_ci_continuation_does_not_reuse_saved_failure_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(minutes=5),
        active_seconds=120,
    )
    pull_request = _pull_request(
        head_sha=SHA_B,
        check_state="pending",
        checks=(CheckSummary(name="backend", status="pending"),),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "invalidate",
            "ci-continuation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={42: pull_request}),
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert store.load_ci_continuation(continuation.work_id) == continuation


def test_invalidate_ci_continuation_rejects_available_or_journal_blocked_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    continuation = _ci_continuation_for_cli(lease)
    store = StateStore(state_dir)
    store.save_ci_continuation(continuation, lease)
    github = FakeGitHub(pull_requests={42: _pull_request(head_sha=SHA_B)})
    command = [
        "--state-dir",
        str(state_dir),
        "invalidate",
        "ci-continuation",
        "--pr",
        "42",
        "--run-id",
        run_id,
    ]

    available_code, available = _invoke(
        capsys,
        command,
        github=github,
    )

    assert available_code == 2
    assert available["reason"] == "invalid-command"
    assert store.load_ci_continuation(continuation.work_id) == continuation

    blocker = PushJournal(
        work_id="curation-pr-43",
        worker="curation",
        origin_run_id=run_id,
        recovery_run_id=run_id,
        pr_number=43,
        branch="codex/catalog-curation-43",
        expected_remote_head=SHA_A,
        new_head=SHA_D,
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(blocker, lease)
    github.pull_requests[42] = _pull_request(head_sha=SHA_C)
    journal_code, journal_blocked = _invoke(
        capsys,
        command,
        github=github,
    )

    assert journal_code == 2
    assert journal_blocked["reason"] == "invalid-command"
    assert store.load_ci_continuation(continuation.work_id) == continuation
    assert store.load_push(blocker.work_id) == blocker


def _save_published_initial_push(
    store: StateStore,
    lease: RunLease,
) -> PushJournal:
    journal = PushJournal(
        work_id="curation-pr-42",
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=42,
        branch=BRANCH,
        expected_remote_head=SHA_A,
        new_head=SHA_B,
        report_path="docs/catalog-curation/nendaz.json",
        resulting_graph_markdown=CANONICAL_GRAPH,
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(journal, lease)
    journal = journal.model_copy(update={"phase": PushPhase.PUSHED})
    store.save_push(journal, lease)
    journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
    store.save_push(journal, lease)
    return journal


def _save_reviewed_ci_repair(
    store: StateStore,
    lease: RunLease,
    *,
    reviewed_at: datetime = NOW - timedelta(minutes=5),
) -> CiContinuation:
    active = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=reviewed_at - timedelta(minutes=5),
    )
    checkpoint = CiRepairCheckpoint(
        repair_head=SHA_C,
        repair_ref=(
            f"refs/snowcast-maintainer/ci-repairs/pr-42/{SHA_B[:12]}-{SHA_C[:12]}"
        ),
        repair_paths=frozenset({"tests/test_catalog_models.py"}),
        non_test_tree_digest="d" * 64,
    )
    reviewed = active.model_copy(
        update={
            "phase": CiContinuationPhase.REPAIR_REVIEWED,
            "repair_head": checkpoint.repair_head,
            "repair_ref": checkpoint.repair_ref,
            "repair_paths": checkpoint.repair_paths,
        }
    )
    return store.advance_ci_continuation(
        reviewed,
        lease,
        now=reviewed_at,
    )


def _save_second_ci_wait(
    store: StateStore,
    lease: RunLease,
    *,
    started_at: datetime = NOW - timedelta(minutes=1),
    publish_journal: bool = True,
) -> CiContinuation:
    _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(
        store,
        lease,
        reviewed_at=started_at - timedelta(minutes=1),
    )
    journal = _matching_repair_push_for_test(reviewed, lease)
    store.save_push(journal, lease)
    journal = journal.model_copy(update={"phase": PushPhase.PUSHED})
    store.save_push(journal, lease)
    waiting = reviewed.model_copy(
        update={
            "phase": CiContinuationPhase.SECOND_WAIT,
            "current_head": SHA_C,
            "second_wait_started_at": started_at,
        }
    )
    waiting = store.advance_ci_continuation(
        waiting,
        lease,
        now=started_at,
    )
    if publish_journal:
        journal = journal.model_copy(update={"phase": PushPhase.PUBLISHED})
        store.save_push(journal, lease)
    return waiting


def _matching_repair_push_for_test(
    continuation: CiContinuation,
    lease: RunLease,
) -> PushJournal:
    assert continuation.repair_head is not None
    return PushJournal(
        work_id=continuation.work_id,
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=continuation.pr_number,
        branch=continuation.branch,
        expected_remote_head=continuation.current_head,
        new_head=continuation.repair_head,
        report_path=continuation.report_path,
        resulting_graph_markdown=continuation.resulting_graph_markdown,
        phase=PushPhase.AUTHORIZED,
    )


def test_publish_ci_repair_journals_exact_second_push_and_enters_second_wait(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(
        head=SHA_C,
        remote=SHA_B,
        github=github,
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert repository.push_exact_calls == [(BRANCH, SHA_B, SHA_C)]
    expected_revalidation = {
        "pull_request": _failed_ci_pull_request(),
        "semantic_head": SHA_B,
        "current_head": SHA_B,
        "checkpoint": CiRepairCheckpoint(
            repair_head=SHA_C,
            repair_ref=reviewed.repair_ref,
            repair_paths=reviewed.repair_paths,
            non_test_tree_digest=reviewed.non_test_tree_digest,
        ),
    }
    assert repository.ci_repair_revalidate_calls == [
        expected_revalidation,
        expected_revalidation,
    ]
    journal = store.load_push(reviewed.work_id)
    assert journal is not None
    assert journal.phase is PushPhase.PUBLISHED
    assert journal.expected_remote_head == SHA_B
    assert journal.new_head == SHA_C
    assert journal.branch == BRANCH
    continuation = store.load_ci_continuation(reviewed.work_id)
    assert continuation is not None
    assert continuation.phase is CiContinuationPhase.SECOND_WAIT
    assert continuation.current_head == SHA_C
    assert continuation.repair_head == SHA_C
    assert continuation.repair_attempted is True
    assert continuation.second_wait_started_at == NOW
    assert payload["push"]["phase"] == "published"
    assert payload["continuation"]["phase"] == "second-wait"
    published_pull_request = github.pull_requests[42]
    assert published_pull_request.maintainer_state is MaintainerState.WAITING_CI
    assert CANONICAL_GRAPH.strip() in published_pull_request.body
    machine = trusted_machine_state(github.comments[42])
    assert machine is not None
    assert machine.reviewed_head == SHA_C
    assert machine.validated_head == SHA_C
    assert machine.last_operation == "published"

    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    assert inspect_code == 0
    assert inventory["unresolved_pushes"] == []
    assert inventory["ci_continuations"][0]["phase"] == "second-wait"


@pytest.mark.parametrize(
    ("branch", "expected_phase", "expected_state"),
    (
        ("pending", CiContinuationPhase.SECOND_WAIT, MaintainerState.WAITING_CI),
        ("ready", CiContinuationPhase.CONSUMED, MaintainerState.READY),
        ("failure", CiContinuationPhase.BLOCKED, MaintainerState.BLOCKED),
    ),
)
def test_repair_push_handoff_exposes_complete_second_wait_branches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    branch: str,
    expected_phase: CiContinuationPhase,
    expected_state: MaintainerState,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(
        head=SHA_C,
        remote=SHA_B,
        github=github,
    )

    publish_code, publish_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert publish_code == 0, publish_payload

    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert inspect_code == 0
    assert inventory["unresolved_pushes"] == []
    assert inventory["ci_continuations"][0]["phase"] == "second-wait"

    if branch in {"pending", "ready"}:
        github.pull_requests[42] = github.pull_requests[42].model_copy(
            update={
                "check_state": "pending" if branch == "pending" else "success",
                "checks": (),
            }
        )
        summary = _private_text(
            state_dir,
            f"{branch}-second-wait-summary.md",
            "GitHub CI is still running."
            if branch == "pending"
            else "The repaired head passed GitHub CI.",
        )
        body = _private_text(
            state_dir,
            f"{branch}-second-wait-body.md",
            f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
        )
        branch_code, branch_payload = _invoke(
            capsys,
            [
                "--state-dir",
                str(state_dir),
                "publish",
                "state",
                "--pr",
                "42",
                "--state",
                (
                    MaintainerState.WAITING_CI.value
                    if branch == "pending"
                    else MaintainerState.READY.value
                ),
                "--reviewed-head",
                SHA_C,
                "--summary-file",
                summary,
                "--body-file",
                body,
                "--run-id",
                run_id,
            ],
            github=github,
            repository=repository,
        )
    else:
        summary = _private_text(
            state_dir,
            "failed-second-wait-summary.md",
            "The repaired head failed GitHub CI.",
        )
        branch_code, branch_payload = _invoke(
            capsys,
            [
                "--state-dir",
                str(state_dir),
                "publish",
                "outcome",
                "--pr",
                "42",
                "--expected-head",
                SHA_C,
                "--state",
                MaintainerState.BLOCKED.value,
                "--reason",
                "ci-failure",
                "--summary-file",
                summary,
                "--run-id",
                run_id,
            ],
            github=github,
            repository=repository,
        )

    assert branch_code == 0, branch_payload
    persisted = store.load_ci_continuation(reviewed.work_id)
    assert persisted is not None
    assert persisted.phase is expected_phase
    assert github.pull_requests[42].maintainer_state is expected_state


def test_repair_push_publication_failure_keeps_journal_first_until_recovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})

    def fail_publication() -> None:
        raise GitHubError("injected repair handoff publication failure")

    github.before_mutation = fail_publication
    repository = FakeRepository(
        head=SHA_C,
        remote=SHA_B,
        github=github,
    )

    failed_code, failed_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert failed_code == 2
    assert failed_payload["reason"] == "transport-failed"
    pushed = store.load_push(reviewed.work_id)
    assert pushed is not None and pushed.phase is PushPhase.PUSHED
    hidden_wait = store.load_ci_continuation(reviewed.work_id)
    assert hidden_wait is not None
    assert hidden_wait.phase is CiContinuationPhase.SECOND_WAIT
    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert inspect_code == 0
    assert inventory["unresolved_pushes"][0]["work_id"] == reviewed.work_id
    assert inventory["ci_continuations"] == []

    github.before_mutation = None
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            reviewed.work_id,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert recover_code == 0, recover_payload
    recovered_journal = store.load_push(reviewed.work_id)
    assert recovered_journal is not None
    assert recovered_journal.phase is PushPhase.PUBLISHED
    assert recover_payload["continuation"]["phase"] == "second-wait"
    assert github.pull_requests[42].maintainer_state is MaintainerState.WAITING_CI
    assert CANONICAL_GRAPH.strip() in github.pull_requests[42].body


def test_publish_ci_repair_revalidates_before_replacing_published_journal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    prior_journal = _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    repository = FakeRepository(
        head=SHA_B,
        remote=SHA_B,
        ci_repair_revalidate_error=RepositorySafetyError(
            "injected immutable checkpoint failure"
        ),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={42: _failed_ci_pull_request()}),
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "unsafe-repository"
    assert store.load_push(reviewed.work_id) == prior_journal
    assert store.load_ci_continuation(reviewed.work_id) == reviewed
    assert repository.head == SHA_B
    assert repository.remote == SHA_B
    assert repository.push_exact_calls == []
    assert len(repository.ci_repair_revalidate_calls) == 1


@pytest.mark.parametrize(
    ("live_head", "remote_head", "mergeable", "expected_reason"),
    (
        pytest.param(
            SHA_C,
            SHA_C,
            "MERGEABLE",
            "stale-head",
            id="externally-pre-pushed-repair-head",
        ),
        pytest.param(
            SHA_B,
            SHA_D,
            "MERGEABLE",
            "stale-head",
            id="live-remote-mismatch",
        ),
        pytest.param(
            SHA_B,
            SHA_B,
            "CONFLICTING",
            "invalid-github-state",
            id="conflicting-mergeability",
        ),
    ),
)
def test_publish_ci_repair_rejects_untrusted_new_push_provenance_before_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    live_head: str,
    remote_head: str,
    mergeable: str,
    expected_reason: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    prior_journal = _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    pull_request = _failed_ci_pull_request().model_copy(
        update={
            "head_sha": live_head,
            "mergeable": mergeable,
        }
    )
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(
        head=SHA_B,
        remote=remote_head,
        github=github,
    )
    journal_before = store.load_push(reviewed.work_id)
    continuation_before = store.load_ci_continuation(reviewed.work_id)
    github_before = github.pull_requests[42]

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == expected_reason
    assert journal_before == prior_journal
    assert store.load_push(reviewed.work_id) == journal_before
    assert store.load_ci_continuation(reviewed.work_id) == continuation_before
    assert repository.head == SHA_B
    assert repository.remote == remote_head
    assert repository.ci_repair_revalidate_calls == []
    assert repository.push_exact_calls == []
    assert github.pull_requests[42] == github_before
    assert github.body_writes == 0
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_publish_ci_repair_requires_prior_journal_to_be_published(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    journal = _save_published_initial_push(store, lease).model_copy(
        update={"phase": PushPhase.PUSHED}
    )
    journal_path = store.push_dir / "curation-pr-42.json"
    journal_path.write_text(journal.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.chmod(journal_path, 0o600)
    _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(head=SHA_C, remote=SHA_B, github=github)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert repository.push_exact_calls == []
    assert store.load_push("curation-pr-42") == journal


@pytest.mark.parametrize(
    ("interruption", "expected_phase", "expected_remote"),
    (
        ("before", PushPhase.AUTHORIZED, SHA_B),
        ("during", PushPhase.AUTHORIZED, SHA_C),
        ("after", PushPhase.PUSHED, SHA_C),
    ),
)
def test_publish_ci_repair_interruption_recovers_journal_before_continuation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    interruption: str,
    expected_phase: PushPhase,
    expected_remote: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin_run = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", origin_run)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(
        head=SHA_C,
        remote=SHA_B,
        github=github,
    )
    if interruption == "before":
        repository.push_exact_error = GitTransportError("interrupted before push")
    elif interruption == "during":
        repository.push_exact_after_error = GitTransportError("interrupted during push")
    else:
        repository.after_push_error = GitHubError("interrupted after push")

    failed_code, failed = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            origin_run,
        ],
        github=github,
        repository=repository,
    )

    assert failed_code == 2
    assert failed["reason"] == "transport-failed"
    journal = store.load_push(reviewed.work_id)
    assert journal is not None and journal.phase is expected_phase
    assert repository.remote == expected_remote
    assert store.load_ci_continuation(reviewed.work_id) == reviewed
    github.failure = None
    repository.push_exact_error = None
    repository.push_exact_after_error = None

    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert inspect_code == 0
    assert inventory["unresolved_pushes"][0]["work_id"] == reviewed.work_id
    assert inventory["ci_continuations"] == []

    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            origin_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            reviewed.work_id,
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert recover_code == 0, recover
    assert recover["continuation"]["phase"] == "second-wait"
    recovered_journal = store.load_push(reviewed.work_id)
    assert recovered_journal is not None
    assert recovered_journal.recovery_run_id == successor
    assert recovered_journal.phase is PushPhase.PUBLISHED
    recovered = store.load_ci_continuation(reviewed.work_id)
    assert recovered is not None
    assert recovered.recovery_run_id == successor
    assert recovered.phase is CiContinuationPhase.SECOND_WAIT
    assert recovered.current_head == SHA_C
    assert len(repository.ci_repair_revalidate_calls) >= 2

    second_attempt_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert second_attempt_code == 2
    assert repository.ci_repair_prepare_calls == []


@pytest.mark.parametrize("endpoint", ("state", "outcome"))
@pytest.mark.parametrize("journal_phase", (PushPhase.AUTHORIZED, PushPhase.PUSHED))
def test_generic_publication_cannot_bypass_non_converged_ci_repair_journal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    endpoint: str,
    journal_phase: PushPhase,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    reviewed = _save_reviewed_ci_repair(store, lease)
    journal = _matching_repair_push_for_test(reviewed, lease)
    store.save_push(journal, lease)
    if journal_phase is PushPhase.PUSHED:
        journal = journal.model_copy(update={"phase": PushPhase.PUSHED})
        store.save_push(journal, lease)
    live_head = SHA_C if journal_phase is PushPhase.PUSHED else SHA_B
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request(head_sha=live_head)})
    repository = FakeRepository(
        head=SHA_C,
        remote=live_head,
        github=github,
    )
    summary = _private_text(
        state_dir,
        f"generic-{endpoint}-{journal_phase.value}.md",
        "This generic publication must not bypass repair recovery.",
    )
    if endpoint == "state":
        command = [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            MaintainerState.BLOCKED.value,
            "--reviewed-head",
            live_head,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ]
    else:
        command = [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            live_head,
            "--state",
            MaintainerState.BLOCKED.value,
            "--reason",
            "deadline",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ]
    journal_before = store.load_push(reviewed.work_id)
    continuation_before = store.load_ci_continuation(reviewed.work_id)
    github_before = github.pull_requests[42]

    code, payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert store.load_push(reviewed.work_id) == journal_before
    assert store.load_ci_continuation(reviewed.work_id) == continuation_before
    assert github.pull_requests[42] == github_before
    assert github.body_writes == 0
    assert github.comment_creates == 0
    assert github.label_writes == 0


@pytest.mark.parametrize(
    "phase",
    (CiContinuationPhase.REPAIR_ACTIVE, CiContinuationPhase.REPAIR_REVIEWED),
)
def test_blocked_outcome_terminalizes_active_or_reviewed_ci_repair(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    phase: CiContinuationPhase,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    if phase is CiContinuationPhase.REPAIR_ACTIVE:
        continuation = _save_active_ci_continuation(
            store,
            lease,
            activity_started_at=NOW - timedelta(minutes=5),
        )
    else:
        continuation = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    summary = _private_text(
        state_dir,
        f"blocked-{phase.value}-summary.md",
        "The focused CI repair stopped safely.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            MaintainerState.BLOCKED.value,
            "--reason",
            "deadline",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 0, payload
    terminal = store.load_ci_continuation(continuation.work_id)
    terminal_publication = store.load_terminal_publication(continuation.work_id)
    assert terminal is not None
    assert terminal.phase is CiContinuationPhase.BLOCKED
    assert terminal_publication is not None
    assert terminal_publication.phase is TerminalPublicationPhase.COMPLETED
    assert github.pull_requests[42].maintainer_state is MaintainerState.BLOCKED
    assert trusted_outcome_state(github.comments[42]) is not None

    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            run_id,
        ],
    )
    assert release_code == 0
    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert inspect_code == 0
    assert inventory["ci_continuations"] == []


@pytest.mark.parametrize(
    "phase",
    (CiContinuationPhase.REPAIR_ACTIVE, CiContinuationPhase.REPAIR_REVIEWED),
)
def test_blocked_repair_outcome_publication_failure_keeps_phase_resumable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    phase: CiContinuationPhase,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    if phase is CiContinuationPhase.REPAIR_ACTIVE:
        continuation = _save_active_ci_continuation(
            store,
            lease,
            activity_started_at=NOW - timedelta(minutes=5),
        )
    else:
        continuation = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})

    def fail_publication() -> None:
        raise GitHubError("injected terminal publication failure")

    github.before_mutation = fail_publication
    summary = _private_text(
        state_dir,
        f"failed-blocked-{phase.value}-summary.md",
        "The focused CI repair stopped safely.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            MaintainerState.BLOCKED.value,
            "--reason",
            "deadline",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "transport-failed"
    persisted = store.load_ci_continuation(continuation.work_id)
    assert persisted is not None
    assert persisted.phase is phase
    intent = store.load_terminal_publication(continuation.work_id)
    assert intent is not None
    assert intent.phase is TerminalPublicationPhase.AUTHORIZED
    assert github.pull_requests[42].maintainer_state is not MaintainerState.BLOCKED


def test_terminal_repair_outcome_validates_summary_before_authorization(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    continuation = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(minutes=5),
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    summary = _private_text(
        state_dir,
        "unsafe-terminal-summary.md",
        f"Unsafe reserved marker: {SUMMARY_MARKER}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            MaintainerState.BLOCKED.value,
            "--reason",
            "deadline",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert store.load_terminal_publication(continuation.work_id) is None
    assert store.load_ci_continuation(continuation.work_id) == continuation
    assert github.comment_creates == 0
    assert github.label_writes == 0


@pytest.mark.parametrize(
    "phase",
    (CiContinuationPhase.REPAIR_ACTIVE, CiContinuationPhase.REPAIR_REVIEWED),
)
@pytest.mark.parametrize(
    "crash_point",
    ("after-comment", "after-labels", "before-continuation-write"),
)
def test_terminal_repair_publication_crash_recovers_only_exact_intent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    phase: CiContinuationPhase,
    crash_point: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin_run = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", origin_run)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    if phase is CiContinuationPhase.REPAIR_ACTIVE:
        continuation = _save_active_ci_continuation(
            store,
            lease,
            activity_started_at=NOW - timedelta(minutes=5),
        )
    else:
        continuation = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    repository = FakeRepository(github=github)
    injected = False
    if crash_point == "after-comment":
        create_comment = github.create_comment

        def create_comment_then_crash(number: int, body: str) -> int:
            nonlocal injected
            comment_id = create_comment(number, body)
            if not injected:
                injected = True
                raise GitHubError("injected crash after comment publication")
            return comment_id

        github.create_comment = create_comment_then_crash
    elif crash_point == "after-labels":
        update_labels = github.update_labels

        def update_labels_then_crash(
            number: int,
            add: set[str] | frozenset[str],
            remove: set[str] | frozenset[str],
        ) -> None:
            nonlocal injected
            update_labels(number, add, remove)
            if not injected:
                injected = True
                raise GitHubError("injected crash after label publication")

        github.update_labels = update_labels_then_crash
    else:
        complete_terminal_publication = StateStore.complete_terminal_publication

        def fail_before_continuation_write(
            self: StateStore,
            intent: TerminalPublicationIntent,
            owned_lease: RunLease,
            *,
            now: datetime,
        ) -> tuple[TerminalPublicationIntent, CiContinuation]:
            nonlocal injected
            if not injected:
                injected = True
                raise StateStoreError("injected crash before continuation state write")
            return complete_terminal_publication(
                self,
                intent,
                owned_lease,
                now=now,
            )

        monkeypatch.setattr(
            StateStore,
            "complete_terminal_publication",
            fail_before_continuation_write,
        )
    summary_text = "The focused CI repair stopped safely."
    summary = _private_text(
        state_dir,
        f"crash-{phase.value}-{crash_point}.md",
        summary_text,
    )
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "outcome",
        "--pr",
        "42",
        "--expected-head",
        SHA_B,
        "--state",
        MaintainerState.BLOCKED.value,
        "--reason",
        "deadline",
        "--summary-file",
        summary,
        "--run-id",
        origin_run,
    ]

    failed_code, failed = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert failed_code == 2
    assert failed["reason"] in {"transport-failed", "invalid-command"}
    persisted = store.load_ci_continuation(continuation.work_id)
    intent = store.load_terminal_publication(continuation.work_id)
    assert persisted == continuation
    assert intent is not None
    assert intent.phase is TerminalPublicationPhase.AUTHORIZED
    assert intent.continuation == continuation
    assert intent.summary == summary_text
    assert intent.target_state is MaintainerState.BLOCKED
    assert intent.reason == "deadline"
    assert trusted_outcome_state(github.comments[42]) is not None
    if crash_point == "after-comment":
        assert github.pull_requests[42].maintainer_state is not MaintainerState.BLOCKED
    else:
        assert github.pull_requests[42].maintainer_state is MaintainerState.BLOCKED

    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            origin_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    github.failure = GitHubError(
        "terminal publication inspection must not require GitHub"
    )
    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    github.failure = None
    assert inspect_code == 0
    assert inventory["terminal_publications"][0]["work_id"] == continuation.work_id
    assert inventory["unresolved_pushes"] == []
    assert inventory["ci_continuations"] == []
    assert inventory["reviewed_continuations"] == []
    assert inventory["remediation_continuations"] == []
    assert inventory["eligible"] == []

    prepare_code, prepare_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "ci-repair",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert prepare_code == 2
    assert prepare_payload["reason"] == "invalid-command"
    assert repository.ci_repair_prepare_calls == []
    assert repository.ci_repair_revalidate_calls == []

    recover_code, recovered = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            continuation.work_id,
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert recover_code == 0, recovered
    assert recovered["terminal_publication"] == {
        "work_id": continuation.work_id,
        "pr_number": 42,
        "state": MaintainerState.BLOCKED.value,
        "reason": "deadline",
        "phase": TerminalPublicationPhase.COMPLETED.value,
    }
    terminal = store.load_ci_continuation(continuation.work_id)
    completed = store.load_terminal_publication(continuation.work_id)
    assert terminal is not None
    assert terminal.phase is CiContinuationPhase.BLOCKED
    assert terminal.recovery_run_id == successor
    assert completed is not None
    assert completed.phase is TerminalPublicationPhase.COMPLETED
    assert completed.recovery_run_id == successor
    assert store.list_unresolved_terminal_publications() == ()
    assert github.pull_requests[42].maintainer_state is MaintainerState.BLOCKED
    assert trusted_outcome_state(github.comments[42]) is not None
    assert github.comment_creates == 1
    assert github.label_writes == 1


def test_unresolved_terminal_publication_rejects_changed_canonical_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    continuation = _save_active_ci_continuation(
        store,
        lease,
        activity_started_at=NOW - timedelta(minutes=5),
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    original_complete = StateStore.complete_terminal_publication
    injected = False

    def fail_once(
        self: StateStore,
        intent: TerminalPublicationIntent,
        owned_lease: RunLease,
        *,
        now: datetime,
    ) -> tuple[TerminalPublicationIntent, CiContinuation]:
        nonlocal injected
        if not injected:
            injected = True
            raise StateStoreError("injected crash before continuation state write")
        return original_complete(self, intent, owned_lease, now=now)

    monkeypatch.setattr(StateStore, "complete_terminal_publication", fail_once)
    first_summary = _private_text(
        state_dir,
        "terminal-original-summary.md",
        "The focused CI repair stopped safely.",
    )
    base_command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "outcome",
        "--pr",
        "42",
        "--expected-head",
        SHA_B,
        "--state",
        MaintainerState.BLOCKED.value,
        "--reason",
        "deadline",
        "--summary-file",
        first_summary,
        "--run-id",
        run_id,
    ]
    first_code, _ = _invoke(capsys, base_command, github=github)
    assert first_code == 2
    comment_creates = github.comment_creates
    label_writes = github.label_writes
    changed_summary = _private_text(
        state_dir,
        "terminal-changed-summary.md",
        "A different terminal explanation.",
    )
    changed_command = list(base_command)
    changed_command[changed_command.index(first_summary)] = changed_summary

    retry_code, retry = _invoke(capsys, changed_command, github=github)

    assert retry_code == 2
    assert retry["reason"] == "invalid-command"
    assert store.load_ci_continuation(continuation.work_id) == continuation
    intent = store.load_terminal_publication(continuation.work_id)
    assert intent is not None
    assert intent.phase is TerminalPublicationPhase.AUTHORIZED
    assert intent.summary == "The focused CI repair stopped safely."
    assert github.comment_creates == comment_creates
    assert github.label_writes == label_writes


@pytest.mark.parametrize("drift", ("head", "branch", "generation"))
def test_terminal_publication_recovery_fails_closed_on_exact_authority_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin_run = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", origin_run)
    store = StateStore(state_dir)
    _save_published_initial_push(store, lease)
    continuation = _save_reviewed_ci_repair(store, lease)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request()})
    complete = StateStore.complete_terminal_publication
    injected = False

    def fail_once(
        self: StateStore,
        intent: TerminalPublicationIntent,
        owned_lease: RunLease,
        *,
        now: datetime,
    ) -> tuple[TerminalPublicationIntent, CiContinuation]:
        nonlocal injected
        if not injected:
            injected = True
            raise StateStoreError("injected crash before continuation state write")
        return complete(self, intent, owned_lease, now=now)

    monkeypatch.setattr(StateStore, "complete_terminal_publication", fail_once)
    summary = _private_text(
        state_dir,
        f"terminal-drift-{drift}.md",
        "The focused CI repair stopped safely.",
    )
    first_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            MaintainerState.BLOCKED.value,
            "--reason",
            "deadline",
            "--summary-file",
            summary,
            "--run-id",
            origin_run,
        ],
        github=github,
    )
    assert first_code == 2
    if drift == "head":
        github.pull_requests[42] = github.pull_requests[42].model_copy(
            update={"head_sha": SHA_C}
        )
    elif drift == "branch":
        github.pull_requests[42] = github.pull_requests[42].model_copy(
            update={"head_ref_name": "codex/catalog-curation-other"}
        )
    else:
        drifted = continuation.model_copy(update={"origin_run_id": "f" * 32})
        path = store.ci_continuation_dir / f"{continuation.work_id}.json"
        path.write_text(drifted.model_dump_json(indent=2) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
    comment_creates = github.comment_creates
    label_writes = github.label_writes
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            origin_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")

    recover_code, recover = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            continuation.work_id,
            "--run-id",
            successor,
        ],
        github=github,
    )

    assert recover_code == 2
    assert recover["reason"] in {"stale-head", "invalid-command"}
    intent = store.load_terminal_publication(continuation.work_id)
    assert intent is not None
    assert intent.phase is TerminalPublicationPhase.AUTHORIZED
    persisted = store.load_ci_continuation(continuation.work_id)
    assert persisted is not None
    assert persisted.phase is not CiContinuationPhase.BLOCKED
    assert github.comment_creates == comment_creates
    assert github.label_writes == label_writes


def _save_ci_wait_for_publication(
    store: StateStore,
    lease: RunLease,
    phase: CiContinuationPhase,
    *,
    started_at: datetime | None = None,
) -> CiContinuation:
    if phase is CiContinuationPhase.INITIAL_WAIT:
        _save_published_initial_push(store, lease)
        continuation = _ci_continuation_for_cli(lease)
        if started_at is not None:
            continuation = continuation.model_copy(
                update={
                    "updated_at": started_at,
                    "first_wait_started_at": started_at,
                }
            )
        store.save_ci_continuation(continuation, lease)
        return continuation
    assert phase is CiContinuationPhase.SECOND_WAIT
    return _save_second_ci_wait(
        store,
        lease,
        started_at=started_at or NOW - timedelta(minutes=1),
    )


@pytest.mark.parametrize(
    ("phase", "head"),
    (
        (CiContinuationPhase.INITIAL_WAIT, SHA_B),
        (CiContinuationPhase.SECOND_WAIT, SHA_C),
    ),
)
def test_ci_continuation_ready_publication_consumes_exact_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    phase: CiContinuationPhase,
    head: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(store, lease, phase)
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(
                head_sha=head,
                check_state="success",
                mergeable="MERGEABLE",
            )
        }
    )
    repository = FakeRepository(head=head, remote=head, github=github)
    summary = _private_text(state_dir, "ready-summary.md", "Ready for owner merge.")
    body = _private_text(
        state_dir,
        "ready-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            head,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0, payload
    assert MaintainerState.READY.value in github.pull_requests[42].labels
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine == MachineState(
        schema_version=2,
        reviewed_head=head,
        validated_head=head,
        last_operation="published",
    )
    consumed = store.load_ci_continuation(continuation.work_id)
    assert consumed is not None
    assert consumed.phase is CiContinuationPhase.CONSUMED
    if phase is CiContinuationPhase.SECOND_WAIT:
        assert len(repository.ci_repair_revalidate_calls) == 1
        assert CANONICAL_GRAPH.strip() in github.pull_requests[42].body
        journal = store.load_push(continuation.work_id)
        assert journal is not None and journal.phase is PushPhase.PUBLISHED


@pytest.mark.parametrize(
    ("phase", "head"),
    (
        (CiContinuationPhase.INITIAL_WAIT, SHA_B),
        (CiContinuationPhase.SECOND_WAIT, SHA_C),
    ),
)
def test_waiting_ci_at_limit_publishes_and_keeps_continuation_active(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    phase: CiContinuationPhase,
    head: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(
        store,
        lease,
        phase,
        started_at=NOW - timedelta(minutes=31),
    )
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(
                head_sha=head,
                check_state="pending",
                mergeable="MERGEABLE",
            )
        }
    )
    repository = FakeRepository(head=head, remote=head, github=github)
    summary = _private_text(state_dir, "waiting-summary.md", "Checks remain pending.")
    body = _private_text(
        state_dir,
        "waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--reviewed-head",
            head,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0, payload
    persisted = store.load_ci_continuation(continuation.work_id)
    assert persisted is not None and persisted.phase is phase
    assert (
        persisted.first_wait_seconds
        if phase is CiContinuationPhase.INITIAL_WAIT
        else persisted.second_wait_seconds
    ) == 1800
    assert MaintainerState.WAITING_CI.value in github.pull_requests[42].labels
    if phase is CiContinuationPhase.SECOND_WAIT:
        journal = store.load_push(continuation.work_id)
        assert journal is not None and journal.phase is PushPhase.PUBLISHED


@pytest.mark.parametrize(
    ("phase", "head"),
    (
        (CiContinuationPhase.INITIAL_WAIT, SHA_B),
        (CiContinuationPhase.SECOND_WAIT, SHA_C),
    ),
)
def test_ci_failure_outcome_terminalizes_initial_or_second_wait(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    phase: CiContinuationPhase,
    head: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(store, lease, phase)
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request(head_sha=head)})
    repository = FakeRepository(head=head, remote=head, github=github)
    summary = _private_text(
        state_dir,
        "blocked-summary.md",
        "CI failed and no further repair is authorized.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            head,
            "--state",
            "maintainer:blocked",
            "--reason",
            "ci-failure",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0, payload
    terminal = store.load_ci_continuation(continuation.work_id)
    assert terminal is not None
    assert terminal.phase is CiContinuationPhase.BLOCKED
    assert MaintainerState.BLOCKED.value in github.pull_requests[42].labels
    if phase is CiContinuationPhase.SECOND_WAIT:
        journal = store.load_push(continuation.work_id)
        assert journal is not None and journal.phase is PushPhase.PUBLISHED


def test_publish_outcome_second_wait_constructs_repository_dependency(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    _save_ci_wait_for_publication(
        store,
        lease,
        CiContinuationPhase.SECOND_WAIT,
    )
    github = FakeGitHub(pull_requests={42: _failed_ci_pull_request(head_sha=SHA_C)})
    repository = FakeRepository(head=SHA_C, remote=SHA_C, github=github)
    constructed_roots: list[Path] = []

    def construct_repository(root: Path) -> FakeRepository:
        constructed_roots.append(root)
        return repository

    monkeypatch.setattr(
        "ops.maintainer.cli.GitRepository",
        construct_repository,
    )
    summary = _private_text(
        state_dir,
        "wired-outcome-summary.md",
        "Confirmed second CI failure.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_C,
            "--state",
            "maintainer:blocked",
            "--reason",
            "ci-failure",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository_root=tmp_path,
    )

    assert code == 0, payload
    assert constructed_roots == [tmp_path.resolve()]
    assert len(repository.ci_repair_revalidate_calls) == 1


@pytest.mark.parametrize(
    "conclusion",
    ("CANCELLED", "ACTION_REQUIRED", None, "UNKNOWN"),
)
def test_ci_failure_outcome_rejects_ambiguous_only_conclusions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    conclusion: str | None,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(
        store,
        lease,
        CiContinuationPhase.INITIAL_WAIT,
    )
    github = FakeGitHub(
        pull_requests={
            42: _failed_ci_pull_request(
                checks=(
                    CheckSummary(
                        name="backend",
                        status="failure",
                        conclusion=conclusion,
                    ),
                )
            )
        }
    )
    summary = _private_text(
        state_dir,
        "ambiguous-outcome-summary.md",
        "Ambiguous check conclusion.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            "maintainer:blocked",
            "--reason",
            "ci-failure",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "invalid-github-state"
    assert store.load_ci_continuation(continuation.work_id) == continuation
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_ci_failure_outcome_accepts_mixed_rollup_with_confirmed_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(
        store,
        lease,
        CiContinuationPhase.INITIAL_WAIT,
    )
    github = FakeGitHub(
        pull_requests={
            42: _failed_ci_pull_request(
                checks=(
                    CheckSummary(
                        name="cancelled",
                        status="failure",
                        conclusion="CANCELLED",
                    ),
                    CheckSummary(
                        name="backend",
                        status="failure",
                        conclusion="FAILURE",
                    ),
                )
            )
        }
    )
    summary = _private_text(
        state_dir,
        "mixed-outcome-summary.md",
        "Confirmed CI failure.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            "maintainer:blocked",
            "--reason",
            "ci-failure",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 0, payload
    terminal = store.load_ci_continuation(continuation.work_id)
    assert terminal is not None
    assert terminal.phase is CiContinuationPhase.BLOCKED


def test_recover_persisted_second_wait_without_repeating_transition(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin_run = _acquire(capsys, state_dir, "curation")
    origin_lease = RunLease.load_owner(state_dir, "curation", origin_run)
    store = StateStore(state_dir)
    waiting = _save_second_ci_wait(
        store,
        origin_lease,
        started_at=NOW - timedelta(minutes=31),
        publish_journal=False,
    )
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(
                head_sha=SHA_C,
                check_state="pending",
            )
        }
    )
    repository = FakeRepository(head=SHA_C, remote=SHA_C, github=github)
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            origin_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")

    recover_code, recover = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            waiting.work_id,
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert recover_code == 0, recover
    assert recover["continuation"]["phase"] == "second-wait"
    recovered = store.load_ci_continuation(waiting.work_id)
    assert recovered is not None
    assert recovered.recovery_run_id == successor
    assert recovered.phase is CiContinuationPhase.SECOND_WAIT
    assert recovered.second_wait_started_at == waiting.second_wait_started_at
    assert recovered.current_head == SHA_C
    assert len(repository.ci_repair_revalidate_calls) == 1
    journal = store.load_push(waiting.work_id)
    assert journal is not None and journal.phase is PushPhase.PUBLISHED

    summary = _private_text(
        state_dir,
        "recovered-waiting-summary.md",
        "Checks remain pending.",
    )
    body = _private_text(
        state_dir,
        "recovered-waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )
    publish_code, publish_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--reviewed-head",
            SHA_C,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert publish_code == 0, publish_payload
    published_journal = store.load_push(waiting.work_id)
    assert published_journal is not None
    assert published_journal.phase is PushPhase.PUBLISHED
    persisted = store.load_ci_continuation(waiting.work_id)
    assert persisted is not None
    assert persisted.phase is CiContinuationPhase.SECOND_WAIT
    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert inspect_code == 0
    assert inventory["unresolved_pushes"] == []
    assert inventory["ci_continuations"][0]["phase"] == "second-wait"


@pytest.mark.parametrize(
    "pull_request",
    (
        _failed_ci_pull_request(
            head_sha=SHA_B,
            checks=(
                CheckSummary(
                    name="backend",
                    status="failure",
                    conclusion="CANCELLED",
                ),
            ),
        ),
        _pull_request(head_sha=SHA_B, check_state="pending", checks=()),
        _pull_request(
            head_sha=SHA_B,
            check_state="success",
            mergeable="UNKNOWN",
        ),
        _pull_request(head_sha=SHA_C, check_state="success"),
    ),
)
def test_ci_continuation_invalid_live_state_neither_readies_nor_repairs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pull_request: PullRequest,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(
        store,
        lease,
        CiContinuationPhase.INITIAL_WAIT,
    )
    github = FakeGitHub(pull_requests={42: pull_request})
    repository = FakeRepository(head=SHA_B, remote=SHA_B, github=github)
    summary = _private_text(state_dir, "invalid-summary.md", "Not ready.")
    body = _private_text(
        state_dir,
        "invalid-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert store.load_ci_continuation(continuation.work_id) == continuation
    assert repository.ci_repair_prepare_calls == []
    assert MaintainerState.READY.value not in github.pull_requests[42].labels


def test_ci_continuation_label_removal_does_not_consume_or_reactivate_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    continuation = _save_ci_wait_for_publication(
        store,
        lease,
        CiContinuationPhase.INITIAL_WAIT,
    )
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(
                head_sha=SHA_B,
                check_state="pending",
                labels=frozenset({"lane:catalog-curation"}),
            )
        }
    )

    inspect_code, inventory = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    assert inspect_code == 0
    assert inventory["ci_continuations"][0]["phase"] == "initial-wait"
    assert store.load_ci_continuation(continuation.work_id) == continuation


def test_cli_exposes_only_the_bounded_capabilities_and_explicit_dispatch_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert set(HANDLERS) == EXPECTED_HANDLERS

    code, payload = _invoke(capsys, ["curation", "inventory"])

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert payload["stage"] == "dispatch"
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)


def test_final_machine_state_contract_is_reduced() -> None:
    assert set(MachineState.model_fields) == {
        "schema_version",
        "reviewed_head",
        "validated_head",
        "candidate_key",
        "candidate_origin",
        "last_operation",
    }


def test_publish_outcome_reports_prepare_conflict_without_push_or_body_change(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        prepare_error=RebaseConflictError("untrusted conflict detail"),
    )
    run_id = _acquire(capsys, state_dir, "curation")
    prepare_code, prepare = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    summary = _private_text(
        state_dir,
        "outcome-summary.md",
        (
            "Automation stopped because current main conflicts with this PR.\n\n"
            "- No branch update was attempted.\n"
            "- Resolve the conflict before the next review.\n"
        ),
    )

    outcome_code, outcome_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_A,
            "--state",
            "maintainer:blocked",
            "--reason",
            "conflict",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert prepare_code == 2
    assert prepare["reason"] == "rebase-conflict"
    assert outcome_code == 0
    assert github.body_writes == 0
    assert github.pull_requests[42].body == "Owner text"
    assert github.pull_requests[42].labels == frozenset(
        {"lane:catalog-curation", "maintainer:blocked"}
    )
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine == MachineState(schema_version=2, last_operation="none")
    outcome = trusted_outcome_state(github.list_issue_comments(42))
    assert outcome is not None
    assert outcome.observed_head == SHA_A
    assert outcome.state == "maintainer:blocked"
    assert outcome.reason == "conflict"
    assert "- Resolve the conflict before the next review." in (
        github.list_issue_comments(42)[0].body
    )
    _assert_outcome(
        outcome_payload,
        worker="curation",
        mutation=True,
        run_id=run_id,
    )


def test_publish_outcome_rejects_stale_expected_head_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    run_id = _acquire(capsys, state_dir, "curation")
    summary = _private_text(state_dir, "outcome-summary.md", "CI failed.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "outcome",
            "--pr",
            "42",
            "--expected-head",
            SHA_B,
            "--state",
            "maintainer:blocked",
            "--reason",
            "ci-failure",
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert github.body_writes == 0
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_lock_lifecycle_uses_worker_and_run_id_without_credentials(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")

    heartbeat_code, heartbeat = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "heartbeat",
            "curation",
            "--run-id",
            run_id,
        ],
    )
    release_code, release = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            run_id,
        ],
    )

    assert heartbeat_code == release_code == 0
    _assert_outcome(heartbeat, worker="curation", mutation=True, run_id=run_id)
    _assert_outcome(release, worker="curation", mutation=True, run_id=run_id)
    assert {path.name for path in state_dir.rglob("*") if path.is_file()} <= {
        "run.transition.lock"
    }


def test_lock_acquire_allows_only_worker_named_by_unresolved_journal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "discovery", now=NOW)
    journal = PushJournal(
        work_id="proposal-stay-destination-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch=BRANCH,
        new_head=SHA_B,
        candidate_key=CANDIDATE,
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    StateStore(state_dir).save_push(journal, lease)
    lease.release()

    rejected_code, rejected = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", "curation"],
    )

    assert rejected_code == 2
    assert rejected["reason"] == "lease-ownership-error"
    assert not (state_dir / "run.lock").exists()
    accepted_code, accepted = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", "discovery"],
    )
    assert accepted_code == 0
    outcome = accepted["outcome"]
    assert isinstance(outcome, dict)
    _assert_outcome(
        accepted,
        worker="discovery",
        mutation=True,
        run_id=outcome["lease_run_id"],
    )


def test_lock_acquire_fails_closed_for_multiple_unresolved_journals(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "discovery", now=NOW)
    first = PushJournal(
        work_id="proposal-stay-destination-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch=BRANCH,
        new_head=SHA_B,
        candidate_key=CANDIDATE,
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    second = first.model_copy(
        update={
            "work_id": "proposal-stay-destination-verbier",
            "branch": "codex/catalog-curation-verbier",
            "candidate_key": "stay_destination:verbier",
        }
    )
    store = StateStore(state_dir)
    store.save_push(first, lease)
    store.save_push(second, lease)
    lease.release()

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "lock", "acquire", "discovery"],
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert not (state_dir / "run.lock").exists()


def test_mutation_rejects_wrong_worker_or_run_before_dependency_access(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    github = FakeGitHub(failure=AssertionError("must not access GitHub"))

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ensure-labels",
            "--worker",
            "discovery",
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 2
    assert payload["reason"] == "lease-ownership-error"
    _assert_outcome(payload, worker="discovery", mutation=False, run_id=run_id)
    assert "must not access" not in json.dumps(payload)


def test_inspect_curation_is_read_only_and_returns_all_safe_candidates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(),
            43: _pull_request(number=43, head_sha=SHA_C),
        }
    )

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    assert code == 0
    assert [item["number"] for item in payload["eligible"]] == [42, 43]
    assert payload["unresolved_pushes"] == []
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)
    assert not (state_dir / "run.lock").exists()


def test_inspect_curation_exposes_ci_continuation_before_ordinary_selection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "curation", now=NOW - timedelta(minutes=2))
    continuation = _ci_continuation_for_cli(lease)
    StateStore(state_dir).save_ci_continuation(continuation, lease)
    lease.release()
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(
                head_sha=SHA_B,
                check_state="failure",
                checks=(
                    {
                        "name": "backend",
                        "status": "failure",
                        "conclusion": "FAILURE",
                        "details_url": (
                            "https://github.com/lampssy/"
                            "ai-sports-travel-planner/actions/runs/1"
                        ),
                    },
                ),
            ),
            43: _pull_request(
                number=43,
                head_sha=SHA_C,
                changed_paths=frozenset({"app/data/catalog.json"}),
            ),
        }
    )

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    assert code == 0, payload
    assert payload["ci_continuations"][0]["pr_number"] == 42
    assert payload["ci_continuations"][0]["first_wait_seconds"] == 120
    assert payload["ci_continuations"][0]["failed_checks"][0]["name"] == "backend"
    assert [item["number"] for item in payload["eligible"]] == [43]
    serialized = json.dumps(payload)
    for private_value in (
        continuation.origin_run_id,
        continuation.recovery_run_id,
        continuation.report_path,
        continuation.resulting_graph_markdown,
        continuation.non_test_tree_digest,
    ):
        assert private_value not in serialized
    assert StateStore.list_ci_continuations_for_inspection_path(state_dir) == (
        continuation,
    )
    assert not (state_dir / "run.lock").exists()


def test_inspect_curation_exposes_generation_retry_action(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "curation", now=NOW)
    CurationGenerationStore(state_dir).start_generation(
        _curation_generation(),
        lease,
    )
    lease.release()

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=FakeGitHub(),
    )

    assert code == 0, payload
    assert payload["generations"] == [
        {
            "pr_number": 42,
            "generation_number": 1,
            "generation_id": GENERATION_ID,
            "selected_head": SHA_A,
            "base_head": SHA_D,
            "latest_head": SHA_C,
            "stage": "reviewed",
            "retryable": True,
            "availability_reason": "available",
            "next_action": {
                "recipe_id": "validate_curation",
                "substitutions": {
                    "pr": 42,
                    "generation_id": GENERATION_ID,
                    "head": SHA_C,
                    "report": "docs/catalog-curation/nendaz.json",
                    "validation_base": SHA_D,
                    "continue_conflict": False,
                },
            },
        }
    ]
    assert payload["eligible"] == []


def test_inspect_curation_requires_legacy_state_migration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "curation", now=NOW)
    store = StateStore(state_dir)
    store.save_continuation(_legacy_reviewed_continuation(lease), lease)
    lease.release()

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=FakeGitHub(),
    )

    assert code == 2
    assert payload["reason"] == "state-migration-required"
    assert payload["stage"] == "inspect"


def test_migrate_curation_state_archives_legacy_without_lease_or_github(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    repository = FakeRepository()
    github = FakeGitHub(failure=AssertionError("migration contacted GitHub"))

    first_code, first = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "migrate",
            "curation-state",
            "--archive-legacy",
        ],
        repository=repository,
        github=github,
    )
    second_code, second = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "migrate",
            "curation-state",
            "--archive-legacy",
        ],
        repository=repository,
        github=github,
    )

    assert first_code == second_code == 0
    assert first["migration"]["already_migrated"] is False
    assert second["migration"]["already_migrated"] is True
    assert first["next_action"] == {
        "recipe_id": "inspect_curation",
        "substitutions": {},
    }
    _assert_outcome(first, worker="curation", mutation=True, run_id=None)
    _assert_outcome(second, worker="curation", mutation=False, run_id=None)
    assert repository.legacy_archive_calls == 1


def test_migrate_curation_state_refuses_active_lease(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "curation", now=NOW)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "migrate",
            "curation-state",
            "--archive-legacy",
        ],
        repository=FakeRepository(),
    )

    assert code == 2
    assert payload["reason"] == "lease-conflict"
    assert payload["stage"] == "lock"
    lease.release()


def test_inspect_does_not_create_missing_state_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = tmp_path / "missing-state"

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=FakeGitHub(),
    )

    assert code == 0
    assert not state_dir.exists()
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)


def test_inspect_surfaces_unresolved_journal_before_any_fresh_selection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "curation", now=NOW)
    journal = PushJournal(
        work_id="curation-pr-42",
        worker="curation",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        pr_number=42,
        branch=BRANCH,
        expected_remote_head=SHA_A,
        new_head=SHA_B,
        phase=PushPhase.AUTHORIZED,
    )
    StateStore(state_dir).save_push(journal, lease)
    lease.release()

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=FakeGitHub(),
    )

    assert code == 0
    assert payload["eligible"] == []
    assert payload["unresolved_pushes"][0]["work_id"] == "curation-pr-42"
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)


def test_inspect_discovery_reports_live_cap_keys_and_unknown_identity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    proposal = _pull_request(
        labels=frozenset({"lane:catalog-discovery", MaintainerState.PROPOSAL.value})
    )
    github = FakeGitHub(pull_requests={42: proposal})

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "discovery"],
        github=github,
        catalog_keys_provider=lambda: frozenset({"ski_area:tignes"}),
    )

    assert code == 0
    assert payload["catalog_keys"] == ["ski_area:tignes"]
    assert payload["open_proposal_count"] == 1
    assert payload["has_unknown_proposal_identity"] is True
    assert payload["can_create_proposal"] is False
    _assert_outcome(payload, worker="discovery", mutation=False, run_id=None)


def test_prepare_curation_persists_one_phase_record_for_requested_safe_pr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    github = FakeGitHub()
    repository = FakeRepository(github=github)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert payload["prepared"]["base_head"] == repository.prepared.base_head
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert generation is not None
    assert generation.generation_number == 1
    assert generation.selected_head == SHA_A
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None
    assert work.phase is WorkPhase.PREPARED
    assert work.selected_head == SHA_A
    assert work.prepared_head == SHA_B
    assert work.sync == _sync()
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_prepare_curation_rejects_before_sync_when_another_ci_continuation_is_active(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    store = StateStore(state_dir)
    store.save_ci_continuation(_ci_continuation_for_cli(lease), lease)
    github = FakeGitHub(
        pull_requests={
            42: _pull_request(head_sha=SHA_B),
            43: _pull_request(number=43, head_sha=SHA_C),
        }
    )
    repository = FakeRepository(github=github)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "43",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert repository.prepare_calls == 0
    assert store.load_work("curation-pr-43") is None


def test_prepare_curation_restores_reviewed_generation_for_validation_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(state_dir, "curation", now=NOW)
    CurationGenerationStore(state_dir).start_generation(
        _curation_generation(),
        origin,
    )
    origin.release()
    run_id = _acquire(capsys, state_dir, "curation")
    repository = FakeRepository()

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(),
        repository=repository,
    )

    assert code == 0, payload
    assert payload["generation"]["generation_number"] == 1
    assert payload["generation"]["result"] == "validation-only"
    assert len(repository.curation_recovery_calls) == 1
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.REVIEWED
    assert work.reviewed_head == SHA_C


def test_prepare_curation_replays_same_pr_head_into_new_generation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(state_dir, "curation", now=NOW)
    generation_store = CurationGenerationStore(state_dir)
    first = _curation_generation()
    generation_store.start_generation(first, origin)
    origin.release()
    run_id = _acquire(capsys, state_dir, "curation")
    repository = FakeRepository(continuation_result="prepared")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(),
        repository=repository,
    )

    assert code == 0, payload
    assert payload["generation"]["generation_number"] == 2
    assert payload["generation"]["result"] == "review-required"
    generations = generation_store.list_generations("curation-pr-42")
    assert generations[0].selected_head == generations[1].selected_head == SHA_A
    assert generations[0].sync.base_head != generations[1].sync.base_head
    assert project_generation(generations[0]).latest_stage == "superseded"


def test_prepare_curation_remote_head_change_starts_clean_generation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(state_dir, "curation", now=NOW)
    generation_store = CurationGenerationStore(state_dir)
    generation_store.start_generation(_curation_generation(), origin)
    origin.release()
    run_id = _acquire(capsys, state_dir, "curation")
    github = FakeGitHub(pull_requests={42: _pull_request(head_sha=SHA_B)})
    repository = FakeRepository(
        prepared=_sync().model_copy(update={"original_head": SHA_B})
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0, payload
    assert payload["generation"]["generation_number"] == 2
    assert payload["generation"]["selected_head"] == SHA_B
    assert repository.curation_recovery_calls == []
    assert (
        project_generation(
            generation_store.list_generations("curation-pr-42")[0]
        ).latest_stage
        == "invalidated"
    )


def test_prepare_curation_conflict_continues_only_with_explicit_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(state_dir, "curation", now=NOW)
    CurationGenerationStore(state_dir).start_generation(
        _curation_generation(),
        origin,
    )
    origin.release()
    run_id = _acquire(capsys, state_dir, "curation")
    repository = FakeRepository(continuation_result="conflict")
    command = [
        "--state-dir",
        str(state_dir),
        "prepare",
        "curation",
        "--pr",
        "42",
        "--run-id",
        run_id,
    ]

    first_code, first = _invoke(
        capsys,
        command,
        github=FakeGitHub(),
        repository=repository,
    )
    retry_code, retry = _invoke(
        capsys,
        command,
        github=FakeGitHub(),
        repository=repository,
    )
    continue_code, continued = _invoke(
        capsys,
        [*command, "--continue-conflict"],
        github=FakeGitHub(),
        repository=repository,
    )

    assert first_code == 0, first
    assert first["generation"]["result"] == "conflict-resolution-required"
    assert retry_code == 2
    assert retry["reason"] == "local-recovery-required"
    assert retry["retryable"] is True
    assert retry["next_action"]["substitutions"]["continue_conflict"] is True
    assert continue_code == 0, continued
    assert continued["generation"]["generation_number"] == 2
    assert repository.curation_continue_calls


def test_prepare_curation_missing_checkpoint_invalidates_and_restarts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(state_dir, "curation", now=NOW)
    generation_store = CurationGenerationStore(state_dir)
    generation_store.start_generation(_curation_generation(), origin)
    origin.release()
    run_id = _acquire(capsys, state_dir, "curation")
    repository = FakeRepository(
        curation_recovery_error=CurationCheckpointIntegrityError("missing")
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(),
        repository=repository,
    )

    assert code == 0, payload
    assert payload["generation"]["generation_number"] == 2
    assert payload["generation"]["result"] == "prepared"
    assert (
        project_generation(
            generation_store.list_generations("curation-pr-42")[0]
        ).latest_stage
        == "invalidated"
    )


def _checkpoint_curation_generation(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    state_dir: Path,
    run_id: str,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    stage: str,
    head: str = SHA_B,
) -> tuple[int, dict[str, object]]:
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert generation is not None
    return _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "checkpoint",
            "curation",
            "--pr",
            "42",
            "--generation-id",
            generation.generation_id,
            "--head",
            head,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--stage",
            stage,
            "--base-dir",
            str(tmp_path),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        delta_validator=lambda **_kwargs: _delta_validation_result().model_copy(
            update={"remediation_head": head}
        ),
    )


def test_checkpoint_curation_completes_delta_review_and_idempotent_retry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository()
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    delta_code, delta = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="delta-validated",
    )
    review_code, reviewed = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="reviewed",
    )
    retry_code, retry = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="reviewed",
    )

    assert delta_code == review_code == retry_code == 0
    assert delta["generation"]["result"] == "completed"
    assert reviewed["generation"]["result"] == "completed"
    assert retry["generation"]["result"] == "already-completed"
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert generation is not None
    projection = project_generation(generation)
    assert projection.latest_stage is CurationCheckpointStage.REVIEWED
    assert projection.reviewed_authority is not None


def test_checkpoint_curation_new_delta_supersedes_reviewed_authority(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository()
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="reviewed",
    )
    repository.head = SHA_C

    code, payload = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="delta-validated",
        head=SHA_C,
    )

    assert code == 0, payload
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert generation is not None
    projection = project_generation(generation)
    assert projection.latest_head == SHA_C
    assert projection.latest_stage is CurationCheckpointStage.DELTA_VALIDATED
    assert projection.reviewed_authority is None


def test_checkpoint_curation_resumes_after_started_event(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        curation_checkpoint_error=RepositorySafetyError("interrupted")
    )
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    first_code, first = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="delta-validated",
    )
    repository.curation_checkpoint_error = None
    retry_code, retry = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="delta-validated",
    )

    assert first_code == 2
    assert first["reason"] == "unsafe-repository"
    assert first["outcome"]["mutation_occurred"] is True
    assert retry_code == 0, retry
    assert retry["generation"]["result"] == "completed"


def test_checkpoint_curation_incomplete_transaction_fences_different_request(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        curation_checkpoint_error=RepositorySafetyError("interrupted")
    )
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="delta-validated",
    )

    code, payload = _checkpoint_curation_generation(
        capsys,
        tmp_path,
        state_dir,
        run_id,
        github,
        repository,
        stage="reviewed",
    )

    assert code == 2
    assert payload["reason"] == "local-recovery-required"
    assert payload["retryable"] is True
    assert payload["next_action"]["recipe_id"] == "checkpoint_curation_delta"


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (RebaseConflictError("untrusted conflict prose"), "rebase-conflict"),
        (StaleRemoteHeadError("untrusted stale prose"), "stale-head"),
        (GitTransportError("untrusted transport prose"), "transport-failed"),
    ],
)
def test_prepare_safe_stops_are_structured_without_exception_prose(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    reason: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "curation")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(),
        repository=FakeRepository(prepare_error=error),
    )

    assert code == 2
    assert payload["reason"] == reason
    assert "untrusted" not in json.dumps(payload)
    outcome = _assert_outcome(
        payload,
        worker="curation",
        mutation=True,
        run_id=run_id,
    )
    assert outcome["last_phase"] == "selected"


def _prepare_curation(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    github: FakeGitHub,
    repository: FakeRepository,
) -> str:
    run_id = _acquire(capsys, state_dir, "curation")
    code, _payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert code == 0
    return run_id


def _validate_curation_command(
    state_dir: Path,
    run_id: str,
    *,
    head: str = SHA_B,
    report: str = "docs/catalog-curation/nendaz.json",
    base_dir: Path | None = None,
) -> list[str]:
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert generation is not None
    return [
        "--state-dir",
        str(state_dir),
        "validate",
        "curation",
        "--pr",
        "42",
        "--generation-id",
        generation.generation_id,
        "--head",
        head,
        "--report",
        report,
        "--base-dir",
        str(base_dir or state_dir.parent / "base"),
        "--run-id",
        run_id,
    ]


def test_validate_curation_binds_reviewed_head_and_objective_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert generation is not None
    reviewed = project_generation(generation).reviewed_authority
    assert reviewed is not None
    assert reviewed.reviewed_head == SHA_B
    observed: dict[str, object] = {}

    def validator(**kwargs: object) -> ValidationResult:
        observed.update(kwargs)
        return _validation_result()

    code, payload = _invoke(
        capsys,
        _validate_curation_command(state_dir, run_id, base_dir=tmp_path / "base"),
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=validator,
    )

    assert observed.get("reviewed_head") == SHA_B, (payload, observed)
    assert code == 0, payload
    assert observed["sync"] == _sync()
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.VALIDATED
    assert work.reviewed_head == work.validated_head == SHA_B
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_validate_curation_exact_retry_returns_existing_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    validator_calls = 0

    def validator(**kwargs: object) -> ValidationResult:
        nonlocal validator_calls
        validator_calls += 1
        return _validation_result()

    command = _validate_curation_command(
        state_dir,
        run_id,
        base_dir=tmp_path / "base",
    )
    first_code, _first_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=validator,
    )
    retry_code, retry_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=validator,
    )

    assert first_code == retry_code == 0, retry_payload
    assert validator_calls == 1
    assert retry_payload["validation"] == {
        "result": "already-validated",
        "validated_head": SHA_B,
    }
    outcome = _assert_outcome(
        retry_payload,
        worker="curation",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "already_validated"


def test_validate_curation_retry_rejects_a_different_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    first_code, _first_payload = _invoke(
        capsys,
        _validate_curation_command(state_dir, run_id, base_dir=tmp_path / "base"),
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **kwargs: _validation_result(),
    )
    retry_code, retry_payload = _invoke(
        capsys,
        _validate_curation_command(
            state_dir,
            run_id,
            report="docs/catalog-curation/other.json",
            base_dir=tmp_path / "base",
        ),
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **kwargs: _validation_result(),
    )

    assert first_code == 0
    assert retry_code == 2
    assert retry_payload["reason"] == "checkpoint-conflict"
    assert retry_payload["stage"] == "validate"


def test_validate_curation_retry_rejects_a_changed_validation_base(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    command = _validate_curation_command(
        state_dir,
        run_id,
        base_dir=tmp_path / "base",
    )
    first_code, _first_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=lambda **kwargs: _validation_result(),
    )
    retry_code, retry_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_A),
        curation_validator=lambda **kwargs: _validation_result(),
    )

    assert first_code == 0
    assert retry_code == 2
    assert retry_payload["reason"] == "validation-failed"
    assert retry_payload["check"] == "post-validation"
    assert retry_payload["kind"] == "mismatch"


def test_validate_failure_exposes_only_allowlisted_check_and_kind(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    def fail(**kwargs: object) -> ValidationResult:
        raise MaintainerError(
            ErrorReason.VALIDATION_FAILED,
            ErrorStage.VALIDATE,
            ErrorCheck.CATALOG_TESTS,
            ErrorKind.COMMAND_FAILED,
            "Validation command failed",
        )

    code, payload = _invoke(
        capsys,
        _validate_curation_command(state_dir, run_id, base_dir=tmp_path / "base"),
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=fail,
    )

    assert code == 2
    assert payload["reason"] == "validation-failed"
    assert payload["check"] == "catalog-tests"
    assert payload["kind"] == "command-failed"
    assert "kwargs" not in json.dumps(payload)


def test_validate_proposal_rechecks_inventory_and_persists_candidate_facts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None)

    def validator(**kwargs: object) -> ProposalValidationResult:
        return ProposalValidationResult(
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            validated_head=SHA_B,
            report_path="docs/catalog-curation/nendaz.json",
        )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        proposal_validator=validator,
        catalog_keys_provider=frozenset,
    )

    assert code == 0
    work_id = str(payload["work_id"])
    work = StateStore(state_dir).load_work(work_id)
    assert work is not None and work.phase is WorkPhase.VALIDATED
    assert work.candidate_key == CANDIDATE
    assert work.candidate_origin == "backlog"
    assert work.report_path == "docs/catalog-curation/nendaz.json"
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_validate_proposal_checks_fetched_main_not_the_modified_worktree(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = tmp_path / "proposal-worktree"
    catalog_path = repository_root / "app/data/catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(_catalog_json(include_candidate=True), encoding="utf-8")
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(
        head=SHA_B,
        remote=None,
        root=repository_root,
        main_catalog_json=_catalog_json(),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "external",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        proposal_validator=lambda **kwargs: ProposalValidationResult(
            candidate_key=CANDIDATE,
            candidate_origin="external",
            validated_head=SHA_B,
            report_path="docs/catalog-curation/nendaz.json",
        ),
        repository_root=repository_root,
    )

    assert code == 0
    assert payload["status"] == "ok"
    assert repository.fetch_main_calls == 1


def test_validate_proposal_rejects_candidate_in_fetched_main(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = tmp_path / "proposal-worktree"
    catalog_path = repository_root / "app/data/catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(_catalog_json(include_candidate=True), encoding="utf-8")
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    repository = FakeRepository(
        head=SHA_B,
        remote=None,
        root=repository_root,
        main_catalog_json=_catalog_json(include_candidate=True),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "external",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=FakeGitHub(pull_requests={}),
        repository=repository,
        proposal_validator=lambda **kwargs: pytest.fail(
            "main duplicate must stop before proposal validation"
        ),
        repository_root=repository_root,
    )

    assert code == 2
    assert payload["reason"] == "duplicate-proposal"
    assert repository.fetch_main_calls == 1


@pytest.mark.parametrize(
    ("catalog_keys", "open_key", "reason"),
    [
        (frozenset({CANDIDATE}), False, "duplicate-proposal"),
        (frozenset(), True, "duplicate-proposal"),
    ],
)
def test_validate_proposal_stops_for_catalog_or_open_key_duplicate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    catalog_keys: frozenset[str],
    open_key: bool,
    reason: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(pull_requests={})
    if open_key:
        proposal = _pull_request(
            labels=frozenset(
                {"lane:catalog-discovery", MaintainerState.PROPOSAL.value}
            ),
            head_sha=SHA_B,
        )
        machine = MachineState(
            schema_version=2,
            reviewed_head=SHA_B,
            validated_head=SHA_B,
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            last_operation="published",
        )
        github.pull_requests[42] = proposal
        github.comments[42] = [
            GitHubComment(
                1,
                f"{SUMMARY_MARKER}\nReviewed.\n{render_machine_state(machine)}",
                "lampssy",
            )
        ]

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=FakeRepository(head=SHA_B, remote=None),
        proposal_validator=lambda **kwargs: pytest.fail("must stop before validation"),
        catalog_keys_provider=lambda: catalog_keys,
    )

    assert code == 2
    assert payload["reason"] == reason
    _assert_outcome(payload, worker="discovery", mutation=False, run_id=run_id)


def _validated_curation(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    resulting_graph_markdown: str | None = None,
) -> str:
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
        reviewed_head=repository.head,
    )
    code, _payload = _invoke(
        capsys,
        _validate_curation_command(state_dir, run_id),
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=lambda **kwargs: _validation_result().model_copy(
            update={
                "resulting_graph_markdown": (
                    resulting_graph_markdown or CANONICAL_GRAPH
                )
            }
        ),
    )
    assert code == 0
    return run_id


def _checkpoint_reviewed(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    run_id: str,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    reviewed_head: str = SHA_B,
    adopt_existing: bool = False,
    expect_success: bool = True,
) -> tuple[int, dict[str, object]]:
    if not adopt_existing:
        generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
        assert generation is not None
        if project_generation(generation).latest_head != reviewed_head:
            delta = _checkpoint_curation_generation(
                capsys,
                state_dir.parent,
                state_dir,
                run_id,
                github,
                repository,
                stage="delta-validated",
                head=reviewed_head,
            )
            if delta[0] != 0:
                return delta
        result = _checkpoint_curation_generation(
            capsys,
            state_dir.parent,
            state_dir,
            run_id,
            github,
            repository,
            stage="reviewed",
            head=reviewed_head,
        )
        if expect_success:
            assert result[0] == 0, result[1]
        return result
    arguments = [
        "--state-dir",
        str(state_dir),
        "validate",
        "reviewed",
        "--pr",
        "42",
        "--reviewed-head",
        reviewed_head,
        "--report",
        "docs/catalog-curation/nendaz.json",
        "--run-id",
        run_id,
    ]
    if adopt_existing:
        arguments.insert(-2, "--adopt-existing")
    code, payload = _invoke(
        capsys,
        arguments,
        github=github,
        repository=repository,
    )
    if expect_success:
        assert code == 0, payload
    return code, payload


def _manual_check_publication_files(state_dir: Path) -> tuple[str, str]:
    return (
        _private_text(state_dir, "manual-check-summary.md", "Owner review required."),
        _private_text(
            state_dir,
            "manual-check-body.md",
            f"Reviewed unresolved work.\n\n{CANONICAL_GRAPH}",
        ),
    )


def _publish_manual_check(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    run_id: str,
    github: FakeGitHub,
    repository: FakeRepository,
    reviewed_head: str = SHA_B,
) -> tuple[int, dict[str, object]]:
    work = StateStore(state_dir).load_work("curation-pr-42")
    if work is not None and work.phase is WorkPhase.PREPARED:
        checkpoint_code, checkpoint_payload = _checkpoint_reviewed(
            capsys,
            state_dir,
            run_id,
            github,
            repository,
            reviewed_head=reviewed_head,
            expect_success=False,
        )
        if checkpoint_code != 0:
            return checkpoint_code, checkpoint_payload
    summary, body = _manual_check_publication_files(state_dir)
    return _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            reviewed_head,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )


def test_publish_manual_check_pushes_reviewed_unvalidated_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 0
    assert repository.push_calls == 1
    assert repository.revalidate_calls == 2
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
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_publish_manual_check_accepts_writer_created_graph_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    lease = RunLease.load_owner(state_dir, "curation", run_id)
    summary = create_publication_text(
        lease,
        kind="summary",
        payload=b"Owner review required.",
    )
    body = create_publication_text(
        lease,
        kind="body",
        payload=f"Reviewed unresolved work.\n\n{CANONICAL_GRAPH}".encode(),
    )

    code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert CANONICAL_GRAPH in github.pull_requests[42].body


def test_publish_manual_check_reuses_head_recorded_before_validation_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    def fail_validation(**_kwargs: object) -> ValidationResult:
        raise MaintainerError(
            ErrorReason.VALIDATION_FAILED,
            ErrorStage.VALIDATE,
        )

    validation_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "curation",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--base-dir",
            str(tmp_path / "base"),
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        base_repository=FakeRepository(),
        curation_validator=fail_validation,
    )
    assert validation_code == 2
    reviewed = StateStore(state_dir).load_work("curation-pr-42")
    assert reviewed is not None and reviewed.phase is WorkPhase.REVIEWED

    code, _ = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 0
    assert repository.revalidate_calls == 2
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.last_operation == "reviewed"


def test_publish_manual_check_accepts_reviewed_descendant_from_prepared_work(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    store = StateStore(state_dir)
    prepared = store.load_work("curation-pr-42")
    assert prepared is not None and prepared.phase is WorkPhase.PREPARED
    repository.head = SHA_C

    code, _ = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
        reviewed_head=SHA_C,
    )

    assert code == 0
    assert github.pull_requests[42].head_sha == SHA_C
    work = store.load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.REVIEWED
    assert work.reviewed_head == SHA_C
    journal = store.load_push("curation-pr-42")
    assert journal is not None and journal.new_head == SHA_C
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.reviewed_head == SHA_C


def test_publish_manual_check_rejects_stale_remote_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github, remote=SHA_C)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert repository.push_calls == 0
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.AUTHORIZED
    assert github.pull_requests[42].head_sha == SHA_A


def test_publish_manual_check_revalidation_failure_prevents_push_authorization(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        revalidate_error=RepositorySafetyError("untrusted local detail"),
    )
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    repository.head = SHA_C

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
        reviewed_head=SHA_C,
    )

    assert code == 2
    assert payload["reason"] == "unsafe-repository"
    assert repository.push_calls == 0
    assert StateStore(state_dir).load_push("curation-pr-42") is None
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.PREPARED
    assert "untrusted" not in json.dumps(payload)


def test_publish_manual_check_binds_publication_text_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    summary_name = _private_text(
        state_dir,
        "manual-check-summary.md",
        "Original reviewed summary.",
    )
    body_name = _private_text(
        state_dir,
        "manual-check-body.md",
        f"Original reviewed body.\n\n{CANONICAL_GRAPH}",
    )

    def replace_publication_text() -> None:
        _private_text(
            state_dir,
            "manual-check-summary.md",
            "Replacement after push.",
        )
        _private_text(
            state_dir,
            "manual-check-body.md",
            "Replacement body after push.",
        )

    repository = FakeRepository(github=github, after_push=replace_publication_text)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)

    code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary_name,
            "--body-file",
            body_name,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert "Original reviewed body." in github.pull_requests[42].body
    assert "Replacement body after push." not in github.pull_requests[42].body
    comments = github.list_issue_comments(42)
    assert len(comments) == 1
    assert "Original reviewed summary." in comments[0].body
    assert "Replacement after push." not in comments[0].body


def test_publish_manual_check_requires_canonical_graph_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    summary = _private_text(state_dir, "summary.md", "Owner review required.")
    body = _private_text(state_dir, "body.md", "Reviewed unresolved work.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/nendaz.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert repository.push_calls == 0
    assert github.body_writes == 0


def test_publish_manual_check_rejects_report_outside_the_prepared_diff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    _checkpoint_reviewed(capsys, state_dir, run_id, github, repository)
    summary, body = _manual_check_publication_files(state_dir)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "manual-check",
            "--pr",
            "42",
            "--reviewed-head",
            SHA_B,
            "--report",
            "docs/catalog-curation/unrelated.json",
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert repository.push_calls == 0
    assert github.body_writes == 0


def test_publish_manual_check_waits_for_github_to_observe_exact_pushed_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def delay_pr_head() -> None:
        github.pull_request_head_reads.extend((SHA_A, SHA_B))

    repository = FakeRepository(github=github, after_push=delay_pr_head)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "ops.maintainer.capabilities.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    code, _ = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 0
    assert sleeps == [3.0]
    assert MaintainerState.MANUAL_CHECK.value in github.pull_requests[42].labels


def test_publish_manual_check_rejects_unexpected_pr_head_without_waiting(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def expose_unexpected_pr_head() -> None:
        github.pull_request_head_reads.append(SHA_C)

    repository = FakeRepository(
        github=github,
        after_push=expose_unexpected_pr_head,
    )
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "ops.maintainer.capabilities.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert sleeps == []
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.label_writes == 0


def test_publish_manual_check_stops_after_bounded_pr_head_wait(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def keep_old_pr_head() -> None:
        github.pull_request_head_reads.extend([SHA_A] * 6)

    repository = FakeRepository(github=github, after_push=keep_old_pr_head)
    run_id = _prepare_curation(capsys, state_dir, github, repository)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "ops.maintainer.capabilities.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    assert sleeps == [3.0] * 5
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED


def test_publish_manual_check_rejects_remote_drift_during_pr_head_wait(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()

    def delay_pr_head() -> None:
        github.pull_request_head_reads.extend((SHA_A, SHA_B))

    repository = FakeRepository(github=github, after_push=delay_pr_head)
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    def move_remote(_seconds: float) -> None:
        repository.remote = SHA_C

    monkeypatch.setattr("ops.maintainer.capabilities.sleep", move_remote)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.label_writes == 0


def test_publish_manual_check_rejects_remote_drift_when_pr_api_is_current(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)

    def move_remote() -> None:
        repository.remote = SHA_C

    repository.after_push = move_remote
    run_id = _prepare_curation(capsys, state_dir, github, repository)

    code, payload = _publish_manual_check(
        capsys,
        state_dir,
        run_id,
        github,
        repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.label_writes == 0


def test_publish_manual_check_recovers_publication_after_successful_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        after_push_error=GitHubError("untrusted publication detail"),
    )
    old_run = _prepare_curation(capsys, state_dir, github, repository)

    failed_code, failed_payload = _publish_manual_check(
        capsys,
        state_dir,
        old_run,
        github,
        repository,
    )

    assert failed_code == 2
    assert failed_payload["reason"] == "transport-failed"
    assert repository.push_calls == 1
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    work = StateStore(state_dir).load_work("curation-pr-42")
    assert work is not None and work.phase is WorkPhase.REVIEWED
    assert "untrusted" not in json.dumps(failed_payload)

    github.failure = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    assert recover_payload["continuation"] == {
        "reviewed_head": SHA_B,
        "validation_status": "absent",
    }

    publish_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        successor,
        github,
        repository,
    )
    retry_code, retry_payload = _publish_manual_check(
        capsys,
        state_dir,
        successor,
        github,
        repository,
    )

    assert publish_code == 0
    assert retry_code == 0
    assert repository.push_calls == 1
    recovered = StateStore(state_dir).load_push("curation-pr-42")
    assert recovered is not None and recovered.phase is PushPhase.PUBLISHED
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.last_operation == "reviewed"
    outcome = _assert_outcome(
        retry_payload,
        worker="curation",
        mutation=False,
        run_id=successor,
    )
    assert outcome["terminal_reason"] == "manual-check"


def test_recovered_reviewed_only_journal_can_publish_owner_decision(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        after_push_error=GitHubError("untrusted publication detail"),
    )
    old_run = _prepare_curation(capsys, state_dir, github, repository)
    failed_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        old_run,
        github,
        repository,
    )
    assert failed_code == 2
    github.failure = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    assert recover_payload["continuation"]["validation_status"] == "absent"
    summary = _private_text(
        state_dir,
        "owner-decision-summary.md",
        "Owner must choose the weather identity boundary.",
    )
    monkeypatch.setattr(
        "ops.maintainer.cli.GitRepository",
        lambda _root: repository,
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:owner-decision",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--run-id",
            successor,
        ],
        github=github,
    )

    assert code == 0
    assert payload["status"] == "ok"
    assert MaintainerState.OWNER_DECISION.value in github.pull_requests[42].labels
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None
    assert machine.reviewed_head == SHA_B
    assert machine.validated_head is None


def test_publish_manual_check_recovers_authorized_journal_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        push_error=GitTransportError("untrusted transport detail"),
    )
    old_run = _prepare_curation(capsys, state_dir, github, repository)
    failed_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        old_run,
        github,
        repository,
    )
    assert failed_code == 2
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.AUTHORIZED

    repository.push_error = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    recovered = StateStore(state_dir).load_push("curation-pr-42")
    assert recovered is not None and recovered.phase is PushPhase.PUSHED
    assert github.pull_requests[42].head_sha == SHA_B

    publish_code, _ = _publish_manual_check(
        capsys,
        state_dir,
        successor,
        github,
        repository,
    )
    assert publish_code == 0
    published = StateStore(state_dir).load_push("curation-pr-42")
    assert published is not None and published.phase is PushPhase.PUBLISHED


def test_publish_recover_rejects_unrelated_remote_head_as_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    old = RunLease.acquire(state_dir, "curation", now=NOW)
    store = StateStore(state_dir)
    authorized = PushJournal(
        work_id="curation-pr-42",
        worker="curation",
        origin_run_id=old.run_id,
        recovery_run_id=old.run_id,
        pr_number=42,
        branch=BRANCH,
        expected_remote_head=SHA_A,
        new_head=SHA_B,
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(authorized, old)
    store.save_push(authorized.model_copy(update={"phase": PushPhase.PUSHED}), old)
    successor = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW + timedelta(hours=7),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor.run_id,
        ],
        github=FakeGitHub(),
        repository=FakeRepository(remote=SHA_C),
    )

    assert code == 2
    assert payload["reason"] == "stale-head"


def test_publish_push_journals_before_exact_force_with_lease_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert repository.push_calls == 1
    journal = StateStore(state_dir).load_push("curation-pr-42")
    work = StateStore(state_dir).load_work("curation-pr-42")
    generation = CurationGenerationStore(state_dir).load_current("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert work is not None and work.phase is WorkPhase.PUSHED
    assert generation is not None
    assert project_generation(generation).latest_stage == "consumed"
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_publish_push_rejects_archived_semantic_head_before_any_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    origin = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=10),
    )
    store = StateStore(state_dir)
    archived = CiContinuation.model_validate(
        {
            **_ci_continuation_for_cli(origin).model_dump(),
            "phase": CiContinuationPhase.CONSUMED,
        }
    )
    archive_dir = store.ci_continuation_archive_dir
    archive_dir.mkdir(mode=0o700)
    archive_path = archive_dir / f"{archived.work_id}-{archived.semantic_head}.json"
    archive_path.write_text(archived.model_dump_json(), encoding="utf-8")
    os.chmod(archive_path, 0o600)
    current = CiContinuation.model_validate(
        {
            **_ci_continuation_for_cli(origin).model_dump(),
            "semantic_head": SHA_C,
            "current_head": SHA_C,
        }
    )
    store.save_ci_continuation(current, origin)
    current = store.advance_ci_continuation(
        current.model_copy(update={"phase": CiContinuationPhase.CONSUMED}),
        origin,
        now=NOW - timedelta(minutes=1),
    )
    prior_journal = _save_published_initial_push(store, origin)
    origin.release()
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    work_before = store.load_work("curation-pr-42")
    continuation_before = store.load_ci_continuation("curation-pr-42")
    archive_before = archive_path.read_bytes()
    head_before = repository.head
    remote_before = repository.remote

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert store.load_push("curation-pr-42") == prior_journal
    assert store.load_work("curation-pr-42") == work_before
    assert store.load_ci_continuation("curation-pr-42") == continuation_before
    assert continuation_before == current
    assert archive_path.read_bytes() == archive_before
    assert repository.head == head_before
    assert repository.remote == remote_before
    assert repository.push_calls == 0
    assert repository.push_exact_calls == []


def test_terminal_ci_generation_can_start_a_new_validated_push_generation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    first_run = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    first_push, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            first_run,
        ],
        github=github,
        repository=repository,
    )
    assert first_push == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    summary = _private_text(state_dir, "summary.md", "First cycle ready.")
    body = _private_text(
        state_dir,
        "body.md",
        f"First cycle synopsis.\n\n{CANONICAL_GRAPH}",
    )
    waiting_command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:waiting-ci",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        first_run,
    ]
    first_waiting, waiting_payload = _invoke(
        capsys,
        waiting_command,
        github=github,
        repository=repository,
    )
    assert first_waiting == 0, waiting_payload
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "success"}
    )
    waiting_command[7] = "maintainer:ready"
    first_publish, _ = _invoke(
        capsys,
        waiting_command,
        github=github,
        repository=repository,
    )
    assert first_publish == 0
    first_generation = StateStore(state_dir).load_ci_continuation("curation-pr-42")
    assert first_generation is not None
    assert first_generation.phase is CiContinuationPhase.CONSUMED
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            first_run,
        ],
    )
    assert release_code == 0

    second_run = _acquire(capsys, state_dir, "curation")
    sync = GuardedSyncResult(
        target_branch=BRANCH,
        original_head=SHA_B,
        rebased_head=SHA_C,
        backup_ref=(
            f"refs/snowcast-maintainer/backups/pr-42/20260708T110000Z-{SHA_B[:12]}"
        ),
        prepared_ref=(
            f"refs/snowcast-maintainer/prepared/pr-42/{SHA_D[:12]}-{SHA_C[:12]}"
        ),
        base_head=SHA_D,
        merge_base=SHA_A,
    )
    store = StateStore(state_dir)
    repository.prepared = sync
    repository.remote = SHA_B
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"labels": frozenset({"lane:catalog-curation"})}
    )
    prepare_code, prepare_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            second_run,
        ],
        github=github,
        repository=repository,
    )
    assert prepare_code == 0, prepare_payload
    _checkpoint_reviewed(
        capsys,
        state_dir,
        second_run,
        github,
        repository,
        reviewed_head=SHA_C,
    )
    validate_code, validate_payload = _invoke(
        capsys,
        _validate_curation_command(state_dir, second_run, head=SHA_C),
        github=github,
        repository=repository,
        base_repository=FakeRepository(head=SHA_D),
        curation_validator=lambda **_kwargs: _validation_result().model_copy(
            update={"validated_head": SHA_C}
        ),
    )
    assert validate_code == 0, validate_payload

    second_push, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            second_run,
        ],
        github=github,
        repository=repository,
    )

    assert second_push == 0
    journal = store.load_push("curation-pr-42")
    assert journal is not None
    assert journal.origin_run_id == second_run
    assert journal.new_head == SHA_C
    assert journal.phase is PushPhase.PUSHED
    assert repository.push_calls == 2
    _assert_outcome(payload, worker="curation", mutation=True, run_id=second_run)
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    second_summary = _private_text(
        state_dir,
        "second-summary.md",
        "Second generation checks pending.",
    )
    second_body = _private_text(
        state_dir,
        "second-body.md",
        f"Second cycle synopsis.\n\n{CANONICAL_GRAPH}",
    )

    second_waiting, second_waiting_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--reviewed-head",
            SHA_C,
            "--summary-file",
            second_summary,
            "--body-file",
            second_body,
            "--adopt-body",
            "--run-id",
            second_run,
        ],
        github=github,
        repository=repository,
    )

    assert second_waiting == 0, second_waiting_payload
    second_generation = store.load_ci_continuation("curation-pr-42")
    assert second_generation is not None
    assert second_generation.phase is CiContinuationPhase.INITIAL_WAIT
    assert second_generation.semantic_head == SHA_C
    assert second_generation.current_head == SHA_C
    assert second_generation.origin_run_id == second_run
    assert second_generation.first_wait_seconds == 0
    assert second_generation.repair_active_seconds == 0
    assert second_generation.second_wait_seconds == 0
    archived = store.ci_continuation_archive_dir / f"curation-pr-42-{SHA_B}.json"
    assert CiContinuation.model_validate_json(archived.read_text()) == first_generation


def test_publish_push_stale_remote_is_safe_and_journal_remains_authorized(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(
        github=github,
        push_error=StaleRemoteHeadError("untrusted remote value"),
    )
    run_id = _validated_curation(capsys, state_dir, github, repository)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.AUTHORIZED
    assert "untrusted" not in json.dumps(payload)


def test_publish_recover_adopts_one_journal_and_reconciles_observed_new_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    old = RunLease.acquire(state_dir, "curation", now=NOW)
    store = StateStore(state_dir)
    store.save_push(
        PushJournal(
            work_id="curation-pr-42",
            worker="curation",
            origin_run_id=old.run_id,
            recovery_run_id=old.run_id,
            pr_number=42,
            branch=BRANCH,
            expected_remote_head=SHA_A,
            new_head=SHA_B,
            phase=PushPhase.AUTHORIZED,
        ),
        old,
    )
    successor = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW + timedelta(hours=7),
    )
    repository = FakeRepository(head=SHA_B, remote=SHA_B)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor.run_id,
        ],
        github=FakeGitHub(),
        repository=repository,
    )

    assert code == 0
    recovered = store.load_push("curation-pr-42")
    assert recovered is not None
    assert recovered.origin_run_id == old.run_id
    assert recovered.recovery_run_id == successor.run_id
    assert recovered.phase is PushPhase.PUSHED
    assert payload["continuation"] == {
        "reviewed_head": SHA_B,
        "validation_status": "unknown",
    }
    _assert_outcome(
        payload,
        worker="curation",
        mutation=True,
        run_id=successor.run_id,
    )


def test_recovered_discovery_journal_can_finish_publication_with_successor(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=SHA_B, github=github)
    old_run_id, work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    old = RunLease.load_owner(state_dir, "discovery", old_run_id)
    store = StateStore(state_dir)
    store.save_push(
        PushJournal(
            work_id=work_id,
            worker="discovery",
            origin_run_id=old.run_id,
            recovery_run_id=old.run_id,
            branch=BRANCH,
            new_head=SHA_B,
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            report_path="docs/catalog-curation/nendaz.json",
            resulting_graph_markdown=CANONICAL_GRAPH,
            phase=PushPhase.AUTHORIZED,
        ),
        old,
    )
    successor = RunLease.acquire(
        state_dir,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    recover_code, _recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            work_id,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )
    assert recover_code == 0

    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")
    publish_code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert publish_code == 0
    assert github.pr_creates == 1
    journal = store.load_push(work_id)
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    _assert_outcome(
        payload,
        worker="discovery",
        mutation=True,
        run_id=successor.run_id,
    )


def test_recovered_discovery_journal_without_graph_evidence_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    old_run_id, work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    old = RunLease.load_owner(state_dir, "discovery", old_run_id)
    store = StateStore(state_dir)
    store.save_push(
        PushJournal(
            work_id=work_id,
            worker="discovery",
            origin_run_id=old.run_id,
            recovery_run_id=old.run_id,
            branch=BRANCH,
            new_head=SHA_B,
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            phase=PushPhase.AUTHORIZED,
        ),
        old,
    )
    (state_dir / "work" / f"{work_id}.json").unlink()
    successor = RunLease.acquire(
        state_dir,
        "discovery",
        now=NOW + timedelta(hours=7),
    )

    recover_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            work_id,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )
    assert recover_code == 0
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    publish_code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            successor.run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert publish_code == 2
    assert payload["reason"] == "invalid-command"
    assert github.pr_creates == 0


def test_publish_recover_fails_closed_for_multiple_journals(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(state_dir, "discovery", now=NOW)
    store = StateStore(state_dir)
    first = PushJournal(
        work_id="proposal-nendaz",
        worker="discovery",
        origin_run_id=lease.run_id,
        recovery_run_id=lease.run_id,
        branch=BRANCH,
        new_head=SHA_B,
        candidate_key=CANDIDATE,
        candidate_origin="backlog",
        phase=PushPhase.AUTHORIZED,
    )
    store.save_push(first, lease)
    store.save_push(
        first.model_copy(
            update={
                "work_id": "proposal-verbier",
                "branch": "codex/catalog-curation-verbier",
                "candidate_key": "stay_destination:verbier",
            }
        ),
        lease,
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "proposal-nendaz",
            "--run-id",
            lease.run_id,
        ],
        github=FakeGitHub(pull_requests={}),
        repository=FakeRepository(head=SHA_B, remote=None),
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"


def _validated_proposal(
    capsys: pytest.CaptureFixture[str],
    state_dir: Path,
    github: FakeGitHub,
    repository: FakeRepository,
    *,
    catalog_keys_provider: Callable[[], frozenset[str]] | None = frozenset,
    repository_root: Path | None = None,
    resulting_graph_markdown: str | None = CANONICAL_GRAPH,
) -> tuple[str, str]:
    run_id = _acquire(capsys, state_dir, "discovery")
    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "validate",
            "proposal",
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--base",
            SHA_A,
            "--head",
            SHA_B,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        proposal_validator=lambda **kwargs: ProposalValidationResult(
            candidate_key=CANDIDATE,
            candidate_origin="backlog",
            validated_head=SHA_B,
            report_path="docs/catalog-curation/nendaz.json",
            resulting_graph_markdown=resulting_graph_markdown,
        ),
        catalog_keys_provider=catalog_keys_provider,
        repository_root=repository_root,
    )
    assert code == 0
    return run_id, str(payload["work_id"])


def test_publish_proposal_rechecks_fetched_main_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository_root = tmp_path / "proposal-worktree"
    catalog_path = repository_root / "app/data/catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(_catalog_json(include_candidate=True), encoding="utf-8")
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(
        head=SHA_B,
        remote=None,
        github=github,
        root=repository_root,
        main_catalog_json=_catalog_json(),
    )
    run_id, _work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        catalog_keys_provider=None,
        repository_root=repository_root,
    )
    repository.main_catalog_json = _catalog_json(include_candidate=True)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        repository_root=repository_root,
    )

    assert code == 2
    assert payload["reason"] == "duplicate-proposal"
    assert repository.create_only_calls == 0
    assert repository.fetch_main_calls == 2


def test_publish_proposal_uses_only_private_state_files_and_finishes_work(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, work_id = _validated_proposal(capsys, state_dir, github, repository)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 0
    assert github.pr_creates == 1
    assert github.comment_creates == 1
    work = StateStore(state_dir).load_work(work_id)
    assert work is not None and work.phase is WorkPhase.PUBLISHED
    assert work.pr_number == 71
    journal = StateStore(state_dir).load_push(work_id)
    assert journal is not None
    assert journal.report_path == "docs/catalog-curation/nendaz.json"
    assert journal.resulting_graph_markdown == CANONICAL_GRAPH
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_publish_proposal_requires_the_validated_canonical_graph_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, _work_id = _validated_proposal(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(state_dir, "body.md", "Owner proposal context")
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            title,
            "--body-file",
            body,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert repository.create_only_calls == 0
    assert github.pr_creates == 0


def test_publish_proposal_idempotent_retry_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None, github=github)
    run_id, _work_id = _validated_proposal(capsys, state_dir, github, repository)
    title = _private_text(state_dir, "title.txt", "Curate Nendaz")
    body = _private_text(
        state_dir,
        "body.md",
        f"Owner proposal context\n\n{CANONICAL_GRAPH}",
    )
    summary = _private_text(state_dir, "summary.md", "Validated candidate.")
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "proposal",
        "--branch",
        BRANCH,
        "--candidate-key",
        CANDIDATE,
        "--candidate-origin",
        "backlog",
        "--head",
        SHA_B,
        "--title-file",
        title,
        "--body-file",
        body,
        "--summary-file",
        summary,
        "--run-id",
        run_id,
    ]
    first_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )
    assert first_code == 0

    code, payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 0
    assert github.pr_creates == 1
    assert github.comment_creates == 1
    outcome = _assert_outcome(
        payload,
        worker="discovery",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "proposal-unchanged"


def test_publish_proposal_rejects_absolute_publication_file_before_push(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub(pull_requests={})
    repository = FakeRepository(head=SHA_B, remote=None)
    run_id, _work_id = _validated_proposal(capsys, state_dir, github, repository)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret source", encoding="utf-8")
    os.chmod(outside, 0o600)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "proposal",
            "--branch",
            BRANCH,
            "--candidate-key",
            CANDIDATE,
            "--candidate-origin",
            "backlog",
            "--head",
            SHA_B,
            "--title-file",
            str(outside),
            "--body-file",
            "body.md",
            "--summary-file",
            "summary.md",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
        catalog_keys_provider=frozenset,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert payload["check"] == "publication-input"
    assert payload["kind"] == "not-basename"
    assert "secret source" not in json.dumps(payload)
    assert repository.create_only_calls == 0


def test_publish_state_ready_adopts_legacy_body_with_explicit_permission(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.\n")
    body = _private_text(
        state_dir,
        "body.md",
        f"## Snowcast catalog review\n\nCurrent concise synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert "Owner text" not in github.pull_requests[42].body
    assert "Current concise synopsis." in github.pull_requests[42].body
    assert github.pull_requests[42].body.count("snowcast-maintainer-body:start") == 1
    assert github.pull_requests[42].body.count("snowcast-maintainer-body:end") == 1
    assert MaintainerState.READY.value in github.pull_requests[42].labels
    machine = trusted_machine_state(github.list_issue_comments(42))
    assert machine is not None and machine.reviewed_head == SHA_B
    journal = StateStore(state_dir).load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUBLISHED
    _assert_outcome(payload, worker="curation", mutation=True, run_id=run_id)


def test_publish_state_requires_the_validated_canonical_graph_before_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.\n")
    body = _private_text(
        state_dir,
        "body.md",
        "## Snowcast catalog review\n\nCurrent concise synopsis.",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert github.pull_requests[42].body == "Owner text"
    assert MaintainerState.READY.value not in github.pull_requests[42].labels


def test_publish_state_accepts_the_exact_validated_canonical_graph(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.\n")
    body = _private_text(
        state_dir,
        "body.md",
        f"## Snowcast catalog review\n\nCurrent concise synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, _payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert CANONICAL_GRAPH.strip() in github.pull_requests[42].body
    assert MaintainerState.READY.value in github.pull_requests[42].labels


@pytest.mark.parametrize(
    ("state", "check_state"),
    [("ready", "success"), ("waiting-ci", "pending")],
)
def test_publish_state_readiness_requires_synopsis_before_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    state: str,
    check_state: str,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": check_state}
    )
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.")

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            f"maintainer:{state}",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "publication-input-invalid"
    assert github.pull_requests[42].body == "Owner text"
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_publish_state_ready_stops_for_pending_ci_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    summary = _private_text(state_dir, "summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "not-ready"
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_waiting_ci_journal_handoff_persists_continuation_before_publication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, push_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    store = StateStore(state_dir)
    pushed = store.load_push("curation-pr-42")
    assert push_code == 0, push_payload
    assert pushed is not None and pushed.phase is PushPhase.PUSHED
    assert store.load_ci_continuation("curation-pr-42") is None
    assert repository.push_calls == 1
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    summary = _private_text(state_dir, "waiting-summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )
    observed_phases: list[tuple[PushPhase, CiContinuationPhase]] = []

    def observe_persisted_handoff() -> None:
        journal = store.load_push("curation-pr-42")
        continuation = store.load_ci_continuation("curation-pr-42")
        assert journal is not None
        assert continuation is not None
        observed_phases.append((journal.phase, continuation.phase))

    github.before_mutation = observe_persisted_handoff
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:waiting-ci",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        run_id,
    ]

    publish_code, publish_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert publish_code == 0, publish_payload
    assert observed_phases
    assert set(observed_phases) == {
        (PushPhase.PUSHED, CiContinuationPhase.INITIAL_WAIT)
    }
    continuation = store.load_ci_continuation("curation-pr-42")
    assert continuation is not None
    assert continuation.origin_run_id == run_id
    assert continuation.recovery_run_id == run_id
    assert continuation.semantic_head == SHA_B
    assert continuation.current_head == SHA_B
    assert continuation.branch == BRANCH
    assert continuation.report_path == "docs/catalog-curation/nendaz.json"
    assert continuation.resulting_graph_markdown == CANONICAL_GRAPH
    assert continuation.non_test_tree_digest == "d" * 64
    assert repository.non_test_tree_digest_calls == [SHA_B]
    published = store.load_push("curation-pr-42")
    assert published is not None and published.phase is PushPhase.PUBLISHED

    retry_code, retry_payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert retry_code == 0, retry_payload
    assert store.load_ci_continuation("curation-pr-42") == continuation
    assert repository.non_test_tree_digest_calls == [SHA_B]


def test_waiting_ci_journal_does_not_create_continuation_before_exact_pr_head(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    github.pull_request_head_reads.extend([SHA_A] * 6)
    monkeypatch.setattr("ops.maintainer.capabilities.sleep", lambda _seconds: None)
    summary = _private_text(state_dir, "waiting-summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    store = StateStore(state_dir)
    assert store.load_ci_continuation("curation-pr-42") is None
    journal = store.load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert repository.non_test_tree_digest_calls == []


def test_waiting_ci_journal_rejects_same_head_from_different_branch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={
            "check_state": "pending",
            "head_ref_name": "codex/catalog-curation-other",
        }
    )
    summary = _private_text(state_dir, "waiting-summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "stale-head"
    store = StateStore(state_dir)
    assert store.load_ci_continuation("curation-pr-42") is None
    journal = store.load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED
    assert github.body_writes == 0
    assert github.comment_creates == 0
    assert github.label_writes == 0
    assert repository.non_test_tree_digest_calls == []


def test_waiting_ci_continuation_keeps_journal_first_during_recovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    origin_run = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            origin_run,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    summary = _private_text(state_dir, "waiting-summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )
    store = StateStore(state_dir)

    def fail_after_handoff_is_durable() -> None:
        journal = store.load_push("curation-pr-42")
        continuation = store.load_ci_continuation("curation-pr-42")
        assert journal is not None and journal.phase is PushPhase.PUSHED
        assert continuation is not None
        raise GitHubError("untrusted publication failure")

    github.before_mutation = fail_after_handoff_is_durable
    waiting_command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:waiting-ci",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        origin_run,
    ]
    failed_code, failed_payload = _invoke(
        capsys,
        waiting_command,
        github=github,
        repository=repository,
    )

    assert failed_code == 2
    assert failed_payload["reason"] == "transport-failed"
    continuation = store.load_ci_continuation("curation-pr-42")
    assert continuation is not None
    journal = store.load_push("curation-pr-42")
    assert journal is not None and journal.phase is PushPhase.PUSHED

    github.before_mutation = None
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            origin_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0, recover_payload
    adopted_journal = store.load_push("curation-pr-42")
    assert adopted_journal is not None
    assert adopted_journal.recovery_run_id == successor
    assert adopted_journal.phase is PushPhase.PUSHED
    assert store.load_ci_continuation("curation-pr-42") == continuation

    inspect_code, during_recovery = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert inspect_code == 0
    assert during_recovery["unresolved_pushes"][0]["work_id"] == "curation-pr-42"
    assert during_recovery["ci_continuations"] == []
    prepare_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "prepare",
            "curation",
            "--pr",
            "42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert prepare_code == 2
    assert repository.prepare_calls == 1

    waiting_command[-1] = successor
    publish_code, publish_payload = _invoke(
        capsys,
        waiting_command,
        github=github,
        repository=repository,
    )

    assert publish_code == 0, publish_payload
    published = store.load_push("curation-pr-42")
    recovered_continuation = store.load_ci_continuation("curation-pr-42")
    assert published is not None and published.phase is PushPhase.PUBLISHED
    assert recovered_continuation == continuation.model_copy(
        update={
            "recovery_run_id": successor,
            "updated_at": continuation.updated_at + timedelta(microseconds=1),
        }
    )
    next_inspect_code, after_handoff = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )
    assert next_inspect_code == 0
    assert after_handoff["unresolved_pushes"] == []
    assert after_handoff["ci_continuations"][0]["pr_number"] == 42
    assert repository.non_test_tree_digest_calls == [SHA_B, SHA_B]


def test_waiting_ci_continuation_rejects_journal_report_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    store = StateStore(state_dir)
    journal = store.load_push("curation-pr-42")
    assert journal is not None
    drifted = journal.model_copy(
        update={"report_path": "docs/catalog-curation/other.json"}
    )
    journal_path = store.push_dir / "curation-pr-42.json"
    journal_path.write_text(drifted.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.chmod(journal_path, 0o600)
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending"}
    )
    summary = _private_text(state_dir, "waiting-summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "waiting-body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:waiting-ci",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "invalid-command"
    assert store.load_ci_continuation("curation-pr-42") is None
    assert github.body_writes == 0
    assert github.comment_creates == 0
    assert github.label_writes == 0


@pytest.mark.parametrize(
    ("phase", "expected_first_wait", "expected_second_wait"),
    [
        (CiContinuationPhase.INITIAL_WAIT, 600, 0),
        (CiContinuationPhase.SECOND_WAIT, 60, 300),
    ],
)
def test_waiting_ci_heartbeat_updates_elapsed_wait_budget(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    phase: CiContinuationPhase,
    expected_first_wait: int,
    expected_second_wait: int,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=20),
    )
    store = StateStore(state_dir)
    continuation = _ci_continuation_for_cli(lease).model_copy(
        update={
            "updated_at": NOW - timedelta(minutes=10),
            "first_wait_started_at": NOW - timedelta(minutes=10),
        }
    )
    store.save_ci_continuation(continuation, lease)
    if phase is CiContinuationPhase.SECOND_WAIT:
        active_at = NOW - timedelta(minutes=9)
        continuation = store.advance_ci_continuation(
            continuation.model_copy(
                update={
                    "phase": CiContinuationPhase.REPAIR_ACTIVE,
                    "repair_attempted": True,
                    "repair_activity_observed_at": active_at,
                }
            ),
            lease,
            now=active_at,
        )
        reviewed_at = NOW - timedelta(minutes=8)
        continuation = store.advance_ci_continuation(
            continuation.model_copy(
                update={
                    "phase": CiContinuationPhase.REPAIR_REVIEWED,
                    "repair_head": SHA_C,
                    "repair_ref": (
                        "refs/snowcast-maintainer/ci-repair/pr-42/checkpoint"
                    ),
                    "repair_paths": frozenset({"tests/test_public_pages.py"}),
                }
            ),
            lease,
            now=reviewed_at,
        )
        second_wait_at = NOW - timedelta(minutes=5)
        store.advance_ci_continuation(
            continuation.model_copy(
                update={
                    "phase": CiContinuationPhase.SECOND_WAIT,
                    "current_head": SHA_C,
                    "second_wait_started_at": second_wait_at,
                }
            ),
            lease,
            now=second_wait_at,
        )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "heartbeat",
            "curation",
            "--run-id",
            lease.run_id,
        ],
    )

    assert code == 0, payload
    heartbeat = store.load_ci_continuation(continuation.work_id)
    assert heartbeat is not None
    assert heartbeat.first_wait_seconds == expected_first_wait
    assert heartbeat.second_wait_seconds == expected_second_wait
    assert payload["ci_budget"] == {
        "first_wait_seconds": expected_first_wait,
        "repair_active_seconds": 0,
        "second_wait_seconds": expected_second_wait,
    }


def test_waiting_ci_heartbeat_updates_lease_and_repair_budget_together(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    lease = RunLease.acquire(
        state_dir,
        "curation",
        now=NOW - timedelta(minutes=10),
    )
    store = StateStore(state_dir)
    initial = _ci_continuation_for_cli(lease).model_copy(
        update={
            "updated_at": NOW - timedelta(minutes=10),
            "first_wait_started_at": NOW - timedelta(minutes=10),
        }
    )
    store.save_ci_continuation(initial, lease)
    active = store.advance_ci_continuation(
        initial.model_copy(
            update={
                "phase": CiContinuationPhase.REPAIR_ACTIVE,
                "repair_attempted": True,
                "repair_activity_observed_at": NOW - timedelta(seconds=3),
            }
        ),
        lease,
        now=NOW - timedelta(seconds=3),
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "heartbeat",
            "curation",
            "--run-id",
            lease.run_id,
        ],
    )

    assert code == 0, payload
    heartbeat = store.load_ci_continuation(active.work_id)
    assert heartbeat is not None
    assert heartbeat.repair_active_seconds == 3
    assert payload["ci_budget"] == {
        "first_wait_seconds": 597,
        "repair_active_seconds": 3,
        "second_wait_seconds": 0,
    }
    owner = json.loads((state_dir / "run.lock" / "owner.json").read_text())
    assert owner["heartbeat_at"] == NOW.isoformat()
    serialized = json.dumps(payload)
    for private_value in (
        heartbeat.report_path,
        heartbeat.resulting_graph_markdown,
        heartbeat.non_test_tree_digest,
        heartbeat.first_wait_started_at.isoformat(),
        heartbeat.updated_at.isoformat(),
    ):
        assert private_value not in serialized


def test_waiting_ci_requires_pushed_evidence_not_only_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(
        capsys,
        state_dir,
        github,
        repository,
        resulting_graph_markdown=CANONICAL_GRAPH,
    )
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"check_state": "pending", "head_sha": SHA_B}
    )
    summary = _private_text(state_dir, "summary.md", "Checks pending.")
    body = _private_text(
        state_dir,
        "body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:waiting-ci",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        run_id,
    ]

    rejected_code, rejected = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert rejected_code == 2
    assert rejected["reason"] == "validation-required"
    assert github.comment_creates == 0
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"head_sha": SHA_A}
    )
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0

    accepted_code, accepted = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert accepted_code == 0
    assert MaintainerState.WAITING_CI.value in github.pull_requests[42].labels
    _assert_outcome(accepted, worker="curation", mutation=True, run_id=run_id)


def test_publish_state_rejects_stale_work_from_prior_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    old_run = _validated_curation(capsys, state_dir, github, repository)
    github.pull_requests[42] = github.pull_requests[42].model_copy(
        update={"head_sha": SHA_B}
    )
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    summary = _private_text(state_dir, "summary.md", "Ready.")
    body = _private_text(
        state_dir,
        "body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert code == 2
    assert payload["reason"] == "validation-required"
    assert github.comment_creates == 0
    assert github.label_writes == 0


def test_adopted_pushed_journal_authorizes_successor_state_publication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    old_run = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            old_run,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    release_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "lock",
            "release",
            "curation",
            "--run-id",
            old_run,
        ],
    )
    assert release_code == 0
    successor = _acquire(capsys, state_dir, "curation")
    recover_code, recover_payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "recover",
            "--work-id",
            "curation-pr-42",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )
    assert recover_code == 0
    assert recover_payload["continuation"] == {
        "reviewed_head": SHA_B,
        "validation_status": "validated",
    }
    summary = _private_text(state_dir, "summary.md", "Ready.")
    body = _private_text(
        state_dir,
        "body.md",
        f"Recovered review synopsis.\n\n{CANONICAL_GRAPH}",
    )

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "state",
            "--pr",
            "42",
            "--state",
            "maintainer:ready",
            "--reviewed-head",
            SHA_B,
            "--summary-file",
            summary,
            "--body-file",
            body,
            "--adopt-body",
            "--run-id",
            successor,
        ],
        github=github,
        repository=repository,
    )

    assert code == 0
    assert MaintainerState.READY.value in github.pull_requests[42].labels
    _assert_outcome(payload, worker="curation", mutation=True, run_id=successor)


def test_publish_state_idempotent_retry_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    github = FakeGitHub()
    repository = FakeRepository(github=github)
    run_id = _validated_curation(capsys, state_dir, github, repository)
    push_code, _ = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "push",
            "--pr",
            "42",
            "--run-id",
            run_id,
        ],
        github=github,
        repository=repository,
    )
    assert push_code == 0
    summary = _private_text(state_dir, "summary.md", "Ready for owner merge.")
    body = _private_text(
        state_dir,
        "body.md",
        f"Current review synopsis.\n\n{CANONICAL_GRAPH}",
    )
    command = [
        "--state-dir",
        str(state_dir),
        "publish",
        "state",
        "--pr",
        "42",
        "--state",
        "maintainer:ready",
        "--reviewed-head",
        SHA_B,
        "--summary-file",
        summary,
        "--body-file",
        body,
        "--adopt-body",
        "--run-id",
        run_id,
    ]
    first_code, _ = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )
    assert first_code == 0
    bodies_before = github.body_writes
    comments_before = github.comment_creates
    labels_before = github.label_writes

    code, payload = _invoke(
        capsys,
        command,
        github=github,
        repository=repository,
    )

    assert code == 0
    assert github.body_writes == bodies_before
    assert github.comment_creates == comments_before
    assert github.label_writes == labels_before
    outcome = _assert_outcome(
        payload,
        worker="curation",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "ready-unchanged"


def test_ensure_labels_is_a_leased_publish_capability(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub()

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ensure-labels",
            "--worker",
            "discovery",
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 0
    assert github.ensured_labels == 1
    _assert_outcome(payload, worker="discovery", mutation=True, run_id=run_id)


def test_ensure_labels_noop_reports_no_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_dir = _private_state_dir(tmp_path)
    run_id = _acquire(capsys, state_dir, "discovery")
    github = FakeGitHub(labels_changed=False)

    code, payload = _invoke(
        capsys,
        [
            "--state-dir",
            str(state_dir),
            "publish",
            "ensure-labels",
            "--worker",
            "discovery",
            "--run-id",
            run_id,
        ],
        github=github,
    )

    assert code == 0
    outcome = _assert_outcome(
        payload,
        worker="discovery",
        mutation=False,
        run_id=run_id,
    )
    assert outcome["terminal_reason"] == "labels-unchanged"


def test_internal_error_and_sensitive_values_never_leak(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_dir = _private_state_dir(tmp_path)
    secret = "token=super-secret-value"
    monkeypatch.setenv("SNOWCAST_SECRET_TEST", secret)
    github = FakeGitHub(failure=RuntimeError(f"{secret} raw subprocess prose"))

    code, payload = _invoke(
        capsys,
        ["--state-dir", str(state_dir), "inspect", "curation"],
        github=github,
    )

    rendered = json.dumps(payload)
    assert code == 2
    assert payload["reason"] == "internal-error"
    assert secret not in rendered
    assert "subprocess" not in rendered
    assert "Owner text" not in rendered
    _assert_outcome(payload, worker="curation", mutation=False, run_id=None)

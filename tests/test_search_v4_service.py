from __future__ import annotations

import math
import statistics
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import fields, is_dataclass, replace
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

import app.domain.search_refinement_snapshot as refinement_snapshot_module
from app.api.routes import router
from app.data.audit_search_factor_readiness import DEFAULT_TRUST_MANIFEST_PATH
from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.domain import search_v4_service
from app.domain.catalog import AggregateTerrainMetrics, CatalogSnapshot
from app.domain.catalog_graph import CatalogGraph
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.models import SnowClimatologyDaily
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_ranking import (
    RankedScore,
    UnscoredAllocation,
    score_factor_evaluations,
)
from app.domain.search_refinement import (
    RefinementCandidateState,
    RefinementImpact,
    RefinementOption,
    RefinementProposal,
    RefinementValidationError,
    RefinementVariantOutcome,
    ValidatedRefinementProposal,
    apply_refinement_option,
    validate_refinement_proposal,
)
from app.domain.search_refinement_presentation import (
    load_refinement_presentation_policy,
)
from app.domain.search_refinement_snapshot import (
    RefinementBaselineCandidate,
    SearchRefinementSnapshotStore,
    canonical_search_intent_digest,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    LocationScope,
    LodgingBudgetConstraint,
    PartyContext,
    PassPriceCeilingConstraint,
    SearchConstraints,
    SearchIntent,
    TravelContext,
    TravelLimitConstraint,
    TravelWindow,
)
from app.domain.search_v4_service import (
    SearchV4RefinementResponse,
    SearchV4Response,
    UnknownSearchWeatherAreaError,
    forecast_run_is_fresh,
    generate_v4_candidate_records,
    get_search_refinements,
    get_search_weather_evidence,
    search_trip_configurations,
)
from app.domain.weather_forecast import (
    ServedWeatherForecastDaily,
    WeatherForecastDaily,
    WeatherForecastRun,
)
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)

pytestmark = pytest.mark.db_free


class _ClimatologyRepository:
    def __init__(
        self,
        rows: tuple[SnowClimatologyDaily, ...] = (),
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.rows = rows

    def list_daily_rows_for_ski_areas_window(self, ski_area_ids, **kwargs):
        self.calls.append({"ski_area_ids": ski_area_ids, **kwargs})
        grouped = {
            (ski_area_id, "mid", baseline): ()
            for ski_area_id in ski_area_ids
            for baseline in ("normal_30y", "recent_15y")
        }
        for row in self.rows:
            key = (row.ski_area_id, row.elevation_band, row.baseline_period)
            if row.ski_area_id in ski_area_ids:
                grouped[key] = (*grouped.get(key, ()), row)
        return grouped


class _ForecastRepository:
    def __init__(
        self,
        rows: tuple[ServedWeatherForecastDaily, ...] = (),
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.rows = rows

    def list_latest_daily_rows(self, **kwargs):
        self.calls.append(kwargs)
        area_ids = frozenset(kwargs["ski_area_ids"])
        source_keys = frozenset(kwargs["source_keys"])
        return tuple(
            row
            for row in self.rows
            if row.daily.ski_area_id in area_ids
            and row.run.forecast_source_key in source_keys
            and kwargs["start_date"] <= row.daily.valid_local_date <= kwargs["end_date"]
            and row.daily.elevation_band == kwargs["elevation_band"]
        )


def _catalog_and_trust():
    snapshot = load_catalog_from_path(CATALOG_PATH)
    manifest = CatalogTrustManifest.model_validate_json(
        DEFAULT_TRUST_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    return snapshot, manifest


def _intent(**constraint_updates: object) -> SearchIntent:
    return SearchIntent(
        constraints=SearchConstraints(
            location=LocationScope(country="France"),
            travel_window=TravelWindow(
                start_date=date(2027, 1, 10),
                end_date=date(2027, 1, 12),
            ),
            **constraint_updates,
        ),
        party=PartyContext(skill_levels=("intermediate",)),
    )


def _country_area_ids(snapshot, country: str) -> tuple[str, ...]:
    destination_ids = {
        destination.stay_destination_id
        for destination in snapshot.stay_destinations
        if destination.country == country
    }
    base_ids = {
        base.stay_base_id
        for base in snapshot.stay_bases
        if base.stay_destination_id in destination_ids
    }
    return tuple(
        sorted(
            {
                access.ski_area_id
                for access in snapshot.ski_area_access
                if access.stay_base_id in base_ids
            }
        )
    )


def _walk_object_graph(root: object) -> Iterator[object]:
    """Traverse retained snapshot data without invoking arbitrary properties."""

    seen: set[int] = set()

    def visit(value: object) -> Iterator[object]:
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        yield value
        if is_dataclass(value) and not isinstance(value, type):
            for field in fields(value):
                yield from visit(getattr(value, field.name))
        elif isinstance(value, BaseModel):
            for field_name in type(value).model_fields:
                yield from visit(getattr(value, field_name))
        elif isinstance(value, Mapping):
            for key, item in value.items():
                yield from visit(key)
                yield from visit(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                yield from visit(item)

    yield from visit(root)


def _assert_all_option_replay_matches_full_search(
    *,
    validated: ValidatedRefinementProposal,
    intent: SearchIntent,
    baseline_candidates: Sequence[RefinementBaselineCandidate],
    catalog_snapshot: CatalogSnapshot,
    trust_manifest: CatalogTrustManifest,
    policy: SearchPolicy,
    climatology_rows: tuple[SnowClimatologyDaily, ...] = (),
    forecast_rows: tuple[ServedWeatherForecastDaily, ...] = (),
    reference_time: datetime = datetime(2027, 1, 1, 12, tzinfo=UTC),
) -> None:
    serialized = search_v4_service._serialized_refinements(
        validated=(validated,),
        intent=intent,
        candidates=baseline_candidates,
    )[0]
    baseline_ordered_candidate_ids = tuple(
        candidate.candidate_id for candidate in baseline_candidates
    )
    baseline_unscored_candidate_ids = frozenset(
        candidate.candidate_id
        for candidate in baseline_candidates
        if candidate.unscored
    )
    candidate_region_ids = {
        candidate.candidate_id: candidate.ski_region_id
        for candidate in baseline_candidates
    }

    for option, outcome, public_option in zip(
        validated.proposal.options,
        validated.variant_outcomes,
        serialized.options,
        strict=True,
    ):
        variant_intent = apply_refinement_option(
            intent,
            option,
            policy,
        )
        expected = search_v4_service._evaluate_search(
            intent=variant_intent,
            catalog_snapshot=catalog_snapshot,
            trust_manifest=trust_manifest,
            climatology_repository=_ClimatologyRepository(climatology_rows),
            forecast_repository=_ForecastRepository(forecast_rows),
            reference_time=reference_time,
            policy=policy,
        )
        expected_outcome = RefinementVariantOutcome(
            ordered_candidate_ids=tuple(
                item.record.candidate_id
                for item in expected.ordered
                if isinstance(item.ranking, RankedScore)
            ),
            eligible_candidate_ids=frozenset(
                item.record.candidate_id for item in expected.ordered
            ),
            intent_changed=variant_intent != intent,
        )
        assert outcome.ordered_candidate_ids == expected_outcome.ordered_candidate_ids
        assert outcome.eligible_candidate_ids == expected_outcome.eligible_candidate_ids
        expected_preview = search_v4_service._refinement_preview(
            intent=intent,
            option=option,
            baseline_ordered_candidate_ids=baseline_ordered_candidate_ids,
            baseline_unscored_candidate_ids=baseline_unscored_candidate_ids,
            candidate_region_ids=candidate_region_ids,
            variant_outcome=expected_outcome,
        )
        assert public_option.model_dump(mode="json")["preview"] == (
            expected_preview.model_dump(mode="json")
            if expected_preview is not None
            else None
        )


def _registered_positive_presence_proposal(factor_id: str) -> RefinementProposal:
    presentation = load_refinement_presentation_policy()
    topic = presentation.topic_by_id[factor_id]
    options = []
    for answer_id in topic.fallback_answer_ids:
        resolved = presentation.resolve_answer_ids((answer_id,))
        options.append(
            RefinementOption(
                label=resolved.label,
                description=resolved.description,
                factor_preference_patches=resolved.factor_preferences,
                objective_patches=resolved.objectives,
            )
        )
    return RefinementProposal(
        topic_id=factor_id,
        target_factor_id=factor_id,
        question_id=f"{factor_id}-require-equivalence",
        question=topic.fallback_question,
        reason=topic.fallback_reason,
        options=tuple(options),
    )


def _climatology_row(
    *,
    ski_area_id: str,
    day: date,
    snow_depth_cm_p50: float,
    baseline_period: str = "normal_30y",
    source_model: str = "snowcast_empirical_v1",
    computed_at: str = "2026-07-01T00:00:00+00:00",
    elevation_m: int | None = 2000,
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id=ski_area_id,
        resort_name=ski_area_id,
        elevation_band="mid",
        elevation_m=elevation_m,
        month=day.month,
        day=day.day,
        baseline_period=baseline_period,
        baseline_start_year=1991 if baseline_period == "normal_30y" else 2011,
        baseline_end_year=2020 if baseline_period == "normal_30y" else 2025,
        evidence_seasons=25 if baseline_period == "normal_30y" else 14,
        latest_archive_year=2025,
        snow_depth_cm_p25=snow_depth_cm_p50 - 20,
        snow_depth_cm_p50=snow_depth_cm_p50,
        snow_depth_cm_p75=snow_depth_cm_p50 + 20,
        prob_snow_depth_ge_30cm=0.8,
        prob_snow_depth_ge_50cm=0.65,
        avg_daily_snowfall_cm=4,
        prob_rain_risk=0.1,
        prob_freeze_thaw=0.2,
        avg_max_temperature_c=-1,
        avg_wind_gust_kmh=30,
        avg_snow_confidence_score=0.75,
        avg_conditions_score=0.7,
        source_model=source_model,
        computed_at=computed_at,
    )


def _forecast_rows(
    *,
    ski_area_ids: tuple[str, ...],
    requested_dates: tuple[date, ...],
) -> tuple[ServedWeatherForecastDaily, ...]:
    initialized_at = datetime(2027, 1, 9, tzinfo=UTC)
    result: list[ServedWeatherForecastDaily] = []
    for area_index, ski_area_id in enumerate(ski_area_ids):
        run = WeatherForecastRun(
            forecast_run_id=f"run-{ski_area_id}",
            forecast_source_key="ecmwf_ifs025_ensemble_mean",
            provider_gateway="open-meteo",
            producer="ecmwf",
            provider_model_id="ifs025",
            forecast_kind="ensemble_mean",
            model_initialization_time=initialized_at,
            provider_availability_time=initialized_at + timedelta(hours=7),
            ingested_at=initialized_at + timedelta(hours=7, minutes=10),
            completed_at=initialized_at + timedelta(hours=7, minutes=15),
            first_valid_date=requested_dates[0],
            last_valid_date=requested_dates[-1],
            status="complete",
            schema_version="forecast-v1",
            parser_version="open-meteo-v1",
            aggregation_policy_version="local-day-v1",
            provider_metadata={"update_interval_seconds": 21_600},
        )
        for valid_date in requested_dates:
            result.append(
                ServedWeatherForecastDaily(
                    run=run,
                    daily=WeatherForecastDaily(
                        forecast_run_id=run.forecast_run_id,
                        ski_area_id=ski_area_id,
                        valid_local_date=valid_date,
                        provider_timezone="Europe/Paris",
                        representative_elevation_m=2000,
                        request_latitude=45,
                        request_longitude=6,
                        snow_depth_cm=60 + area_index,
                        snow_depth_spread_cm=8,
                        snowfall_cm=10,
                        rain_mm=2,
                        positive_degree_hours=3,
                        temperature_2m_min_c=-6,
                        temperature_2m_max_c=1,
                        wind_speed_10m_max_kmh=30,
                        wind_gusts_10m_max_kmh=50,
                        is_complete=True,
                        completeness_metadata={"expected_hour_count": 24},
                    ),
                )
            )
    return tuple(result)


class _MaximumShapeClimatologyRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_daily_rows_for_ski_areas_window(self, ski_area_ids, **kwargs):
        self.calls.append({"ski_area_ids": ski_area_ids, **kwargs})
        start = kwargs["trip_start_date"]
        end = kwargs["trip_end_date"]
        assert isinstance(start, date) and isinstance(end, date)
        requested_dates = tuple(
            start + timedelta(days=offset) for offset in range((end - start).days + 1)
        )
        grouped = {
            (ski_area_id, "mid", baseline): []
            for ski_area_id in ski_area_ids
            for baseline in ("normal_30y", "recent_15y")
        }
        for ski_area_id in ski_area_ids:
            for offset, valid_date in enumerate(requested_dates):
                baseline = "normal_30y" if offset < 16 else "recent_15y"
                grouped[(ski_area_id, "mid", baseline)].append(
                    _climatology_row(
                        ski_area_id=ski_area_id,
                        day=valid_date,
                        snow_depth_cm_p50=80,
                        baseline_period=baseline,
                        source_model=(
                            f"snowcast-normal-v1-{offset}"
                            if baseline == "normal_30y"
                            else f"snowcast-recent-v1-{offset}"
                        ),
                        computed_at=(
                            datetime(2026, 7, 1, tzinfo=UTC)
                            .replace(day=min(28, offset + 1))
                            .isoformat()
                        ),
                    )
                )
        return {key: tuple(rows) for key, rows in grouped.items()}


class _MaximumShapeForecastRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_latest_daily_rows(self, **kwargs):
        self.calls.append(kwargs)
        start = kwargs["start_date"]
        end = kwargs["end_date"]
        assert isinstance(start, date) and isinstance(end, date)
        initialized_at = datetime(start.year, start.month, start.day, tzinfo=UTC)
        requested_dates = tuple(
            start + timedelta(days=offset) for offset in range((end - start).days + 1)
        )
        result: list[ServedWeatherForecastDaily] = []
        for area_index, ski_area_id in enumerate(kwargs["ski_area_ids"]):
            for offset, valid_date in enumerate(requested_dates):
                source_key = (
                    "ecmwf_ifs025_ensemble_mean"
                    if offset <= 15
                    else "ncep_gefs05_ensemble_mean"
                )
                run = WeatherForecastRun(
                    forecast_run_id=f"benchmark-{ski_area_id}-{offset}",
                    forecast_source_key=source_key,
                    provider_gateway="open-meteo",
                    producer=(
                        "ecmwf"
                        if source_key == "ecmwf_ifs025_ensemble_mean"
                        else "noaa-ncep"
                    ),
                    provider_model_id=(
                        "ifs025"
                        if source_key == "ecmwf_ifs025_ensemble_mean"
                        else "gefs05"
                    ),
                    forecast_kind="ensemble_mean",
                    model_initialization_time=initialized_at,
                    provider_availability_time=initialized_at + timedelta(hours=7),
                    ingested_at=initialized_at + timedelta(hours=7, minutes=10),
                    completed_at=initialized_at + timedelta(hours=7, minutes=15),
                    first_valid_date=start,
                    last_valid_date=end,
                    status="complete",
                    schema_version="forecast-v1",
                    parser_version="open-meteo-v1",
                    aggregation_policy_version="local-day-v1",
                    provider_metadata={"update_interval_seconds": 21_600},
                )
                result.append(
                    ServedWeatherForecastDaily(
                        run=run,
                        daily=WeatherForecastDaily(
                            forecast_run_id=run.forecast_run_id,
                            ski_area_id=ski_area_id,
                            valid_local_date=valid_date,
                            provider_timezone="Europe/Paris",
                            representative_elevation_m=2000,
                            request_latitude=45,
                            request_longitude=6,
                            snow_depth_cm=60 + area_index,
                            snow_depth_spread_cm=8,
                            snowfall_cm=10,
                            rain_mm=2,
                            positive_degree_hours=3,
                            temperature_2m_min_c=-6,
                            temperature_2m_max_c=1,
                            wind_speed_10m_max_kmh=30,
                            wind_gusts_10m_max_kmh=50,
                            is_complete=True,
                            completeness_metadata={"expected_hour_count": 24},
                        ),
                    )
                )
        return tuple(result)


def _configurations(result: SearchV4Response):
    return tuple(
        configuration
        for group in result.results
        for configuration in (
            group.top_configuration,
            *group.alternative_configurations,
        )
    )


def _ranking_projection(result: SearchV4Response) -> tuple[object, ...]:
    return tuple(
        (
            group.ski_region_id,
            group.rank,
            tuple(
                (
                    configuration.candidate_id,
                    configuration.ranking_status,
                    configuration.fit_score,
                    configuration.groups,
                    configuration.factors,
                )
                for configuration in (
                    group.top_configuration,
                    *group.alternative_configurations,
                )
            ),
        )
        for group in result.results
    )


def _validated_refinement(
    *outcomes: tuple[tuple[str, ...], frozenset[str]],
) -> ValidatedRefinementProposal:
    proposal = RefinementProposal(
        topic_id="accessible_terrain_scale",
        target_factor_id="accessible_terrain_scale",
        question_id="terrain-vs-access",
        question="Which tradeoff should lead the ranking?",
        reason="The leading regions trade terrain scale against base access.",
        options=(
            RefinementOption(
                label="Terrain",
                description="Prioritize ski-area scale.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="ski_experience",
                        importance="very_high",
                    ),
                ),
            ),
            RefinementOption(
                label="Access",
                description="Prioritize stay-base access.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="stay_practicality",
                        importance="very_high",
                    ),
                ),
            ),
        ),
    )
    return ValidatedRefinementProposal(
        proposal=proposal,
        impact=RefinementImpact(
            material=True,
            eligibility_changed=True,
            winner_changed=True,
            top_three_membership_changed=True,
            top_three_order_changed=True,
            top_five_score_changed=True,
        ),
        variant_outcomes=tuple(
            RefinementVariantOutcome(
                ordered_candidate_ids=ordered_ids,
                eligible_candidate_ids=eligible_ids,
                intent_changed=True,
            )
            for ordered_ids, eligible_ids in outcomes
        ),
    )


def test_serialized_refinements_bounds_legacy_supplied_queue() -> None:
    validated = _validated_refinement(
        (("first", "second"), frozenset({"first", "second"})),
        (("second", "first"), frozenset({"first", "second"})),
    )
    candidates = (
        SimpleNamespace(candidate_id="first", unscored=False, ski_region_id="region"),
        SimpleNamespace(candidate_id="second", unscored=False, ski_region_id="region"),
    )

    serialized = search_v4_service._serialized_refinements(
        validated=(validated, validated),
        intent=_intent(),
        candidates=candidates,
    )

    assert len(serialized) == 1


def _ordered_candidate(
    candidate_id: str,
    ski_region_id: str,
    *,
    ranking: object | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        record=SimpleNamespace(
            candidate_id=candidate_id,
            region=SimpleNamespace(ski_region_id=ski_region_id),
            constraint_facts=object(),
        ),
        evaluations=(),
        ranking=ranking if ranking is not None else SimpleNamespace(),
        replay_state=SimpleNamespace(evaluate=lambda _intent: ()),
    )


def test_refinement_previews_group_candidate_ranks_and_preserve_patches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordered = (
        _ordered_candidate("candidate-a", "region-a"),
        _ordered_candidate("candidate-b", "region-b"),
        _ordered_candidate("candidate-c", "region-c"),
        _ordered_candidate("candidate-d", "region-d"),
    )
    validated = _validated_refinement(
        (
            ("candidate-a", "candidate-c", "candidate-b", "candidate-d"),
            frozenset(item.record.candidate_id for item in ordered),
        ),
        (
            ("candidate-a", "candidate-b", "candidate-d", "candidate-c"),
            frozenset(item.record.candidate_id for item in ordered),
        ),
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: (validated,),
    )

    refinements = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(),
        ordered=ordered,
        policy=load_search_policy(),
        client=object(),
        already_answered_question_ids=frozenset(),
    )

    assert refinements[0].topic_id == "accessible_terrain_scale"
    assert refinements[0].target_factor_id == "accessible_terrain_scale"
    serialized = refinements[0].model_dump(mode="json")
    assert serialized["topic_id"] == "accessible_terrain_scale"
    assert serialized["target_factor_id"] == "accessible_terrain_scale"
    assert refinements[0].options[0].group_priority_patches == (
        GroupPriorityPatch(group_id="ski_experience", importance="very_high"),
    )
    assert refinements[0].options[0].preview is not None
    assert refinements[0].options[0].preview.top_rank_changes == (
        search_v4_service.SearchV4RefinementRankChange(
            ski_region_id="region-c",
            previous_rank=3,
            preview_rank=2,
        ),
        search_v4_service.SearchV4RefinementRankChange(
            ski_region_id="region-b",
            previous_rank=2,
            preview_rank=3,
        ),
    )
    assert refinements[0].options[1].preview is not None
    assert refinements[0].options[1].preview.top_rank_changes == (
        search_v4_service.SearchV4RefinementRankChange(
            ski_region_id="region-d",
            previous_rank=None,
            preview_rank=3,
        ),
        search_v4_service.SearchV4RefinementRankChange(
            ski_region_id="region-c",
            previous_rank=3,
            preview_rank=None,
        ),
    )


def test_refinement_response_marks_baseline_choice_without_material_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordered = (
        _ordered_candidate("candidate-a", "region-a"),
        _ordered_candidate("candidate-b", "region-b"),
    )
    validated = _validated_refinement(
        (
            ("candidate-a", "candidate-b"),
            frozenset({"candidate-a", "candidate-b"}),
        ),
        (
            ("candidate-b", "candidate-a"),
            frozenset({"candidate-a", "candidate-b"}),
        ),
    )
    validated = validated.model_copy(
        update={
            "variant_outcomes": (
                validated.variant_outcomes[0].model_copy(
                    update={"intent_changed": False}
                ),
                validated.variant_outcomes[1].model_copy(
                    update={"intent_changed": True}
                ),
            )
        }
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: (validated,),
    )

    refinement = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(),
        ordered=ordered,
        policy=load_search_policy(),
        client=object(),
        already_answered_question_ids=frozenset(),
    )[0]

    assert refinement.options[0].intent_changed is False
    assert refinement.options[0].preview == search_v4_service.SearchV4RefinementPreview(
        top_rank_changes=(),
        eligible_candidate_count_delta=0,
    )
    assert refinement.options[1].intent_changed is True


def test_refinements_use_full_eligible_set_beyond_llm_summary_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = load_search_policy()
    ordered = tuple(
        _ordered_candidate(f"candidate-{index:02d}", f"region-{index:02d}")
        for index in range(policy.refinement.max_candidate_summaries + 1)
    )
    baseline_ids = tuple(item.record.candidate_id for item in ordered)
    outside_summary_id = baseline_ids[-1]
    validated = _validated_refinement(
        (
            (outside_summary_id, *baseline_ids[:-1]),
            frozenset(baseline_ids),
        ),
        (baseline_ids, frozenset(baseline_ids)),
    )
    captured_candidate_ids: list[str] = []

    def generate(**kwargs: object) -> tuple[ValidatedRefinementProposal, ...]:
        candidates = cast(
            tuple[RefinementCandidateState, ...],
            kwargs["candidates"],
        )
        captured_candidate_ids.extend(item.candidate_id for item in candidates)
        return (validated,)

    monkeypatch.setattr(search_v4_service, "generate_refinement_proposals", generate)

    refinements = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(),
        ordered=ordered,
        policy=policy,
        client=object(),
        already_answered_question_ids=frozenset(),
    )

    assert captured_candidate_ids == list(baseline_ids)
    preview = refinements[0].options[0].preview
    assert preview is not None
    assert preview.top_rank_changes[0] == (
        search_v4_service.SearchV4RefinementRankChange(
            ski_region_id=f"region-{policy.refinement.max_candidate_summaries:02d}",
            previous_rank=None,
            preview_rank=1,
        )
    )


def test_refinement_previews_are_omitted_for_unscored_visible_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordered = (
        _ordered_candidate("candidate-a", "region-a"),
        _ordered_candidate("candidate-b", "region-b"),
        _ordered_candidate(
            "candidate-c",
            "region-c",
            ranking=UnscoredAllocation(
                reason="infeasible_group_caps",
                active_group_ids=("ski_experience",),
            ),
        ),
    )
    validated = _validated_refinement(
        (
            ("candidate-a", "candidate-b"),
            frozenset({"candidate-a", "candidate-b", "candidate-c"}),
        ),
        (
            ("candidate-b", "candidate-a"),
            frozenset({"candidate-a", "candidate-b", "candidate-c"}),
        ),
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: (validated,),
    )

    refinements = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(),
        ordered=ordered,
        policy=load_search_policy(),
        client=object(),
        already_answered_question_ids=frozenset(),
    )

    assert all(option.preview is None for option in refinements[0].options)


def test_refinement_preview_is_omitted_for_unscored_option_top_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_ids = ("candidate-a", "candidate-b", "candidate-c")
    validated = _validated_refinement(
        (
            ("candidate-a", "candidate-b"),
            frozenset(candidate_ids),
        ),
        (
            ("candidate-b", "candidate-a", "candidate-c"),
            frozenset(candidate_ids),
        ),
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: (validated,),
    )

    refinements = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(),
        ordered=tuple(
            _ordered_candidate(candidate_id, f"region-{candidate_id[-1]}")
            for candidate_id in candidate_ids
        ),
        policy=load_search_policy(),
        client=object(),
        already_answered_question_ids=frozenset(),
    )

    assert refinements[0].options[0].preview is None
    assert refinements[0].options[1].preview is not None


def test_refinement_previews_omit_expanding_require_changes_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = RefinementProposal(
        topic_id="local_pace",
        target_factor_id="local_pace",
        question_id="pace-requirement",
        question="How strict should the local pace requirement be?",
        reason="The current requirement can be narrowed or relaxed.",
        options=(
            RefinementOption(
                label="Relax pace",
                description="Prefer rather than require the selected local pace.",
                factor_preference_patches=(
                    FactorPreferencePatch(factor_id="local_pace", mode="prefer"),
                ),
            ),
            RefinementOption(
                label="Allow lively bases",
                description="Widen the accepted local pace values.",
                factor_preference_patches=(
                    FactorPreferencePatch(
                        factor_id="local_pace",
                        mode="require",
                        values=("quiet", "balanced", "lively"),
                    ),
                ),
            ),
            RefinementOption(
                label="Quiet only",
                description="Narrow the accepted local pace values.",
                factor_preference_patches=(
                    FactorPreferencePatch(
                        factor_id="local_pace",
                        mode="require",
                        values=("quiet",),
                    ),
                ),
            ),
            RefinementOption(
                label="More terrain",
                description="Give ski experience more ranking influence.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="ski_experience",
                        importance="very_high",
                    ),
                ),
            ),
        ),
    )
    candidate_ids = ("candidate-a", "candidate-b", "candidate-c")
    validated = ValidatedRefinementProposal(
        proposal=proposal,
        impact=RefinementImpact(
            material=True,
            eligibility_changed=True,
            winner_changed=True,
            top_three_membership_changed=False,
            top_three_order_changed=True,
            top_five_score_changed=True,
        ),
        variant_outcomes=tuple(
            RefinementVariantOutcome(
                ordered_candidate_ids=(
                    candidate_ids[index % 3],
                    *candidate_ids[: index % 3],
                    *candidate_ids[index % 3 + 1 :],
                ),
                eligible_candidate_ids=frozenset(candidate_ids),
                intent_changed=True,
            )
            for index in range(4)
        ),
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: (validated,),
    )

    refinements = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="local_pace",
                    mode="require",
                    values=("quiet", "balanced"),
                ),
            )
        ),
        ordered=tuple(
            _ordered_candidate(candidate_id, f"region-{candidate_id[-1]}")
            for candidate_id in candidate_ids
        ),
        policy=load_search_policy(),
        client=object(),
        already_answered_question_ids=frozenset(),
    )

    options = refinements[0].options
    assert options[0].preview is None
    assert options[1].preview is None
    assert options[2].preview is not None
    assert options[3].preview is not None


def test_refinement_preview_caps_changes_and_deduplicates_regions() -> None:
    candidate_region_ids = {
        "a-1": "region-a",
        "a-2": "region-a",
        "b-1": "region-b",
        "c-1": "region-c",
        "d-1": "region-d",
        "e-1": "region-e",
        "f-1": "region-f",
    }
    outcome = RefinementVariantOutcome(
        ordered_candidate_ids=("d-1", "e-1", "f-1", "a-2", "a-1", "b-1", "c-1"),
        eligible_candidate_ids=frozenset(candidate_region_ids),
        intent_changed=True,
    )

    preview = search_v4_service._refinement_preview(
        baseline_ordered_candidate_ids=(
            "a-1",
            "b-1",
            "a-2",
            "c-1",
            "d-1",
            "e-1",
            "f-1",
        ),
        candidate_region_ids=candidate_region_ids,
        variant_outcome=outcome,
    )

    assert len(preview.top_rank_changes) == 3
    assert [change.ski_region_id for change in preview.top_rank_changes] == [
        "region-d",
        "region-e",
        "region-f",
    ]
    assert len({change.ski_region_id for change in preview.top_rank_changes}) == 3


def test_refinement_preview_does_not_duplicate_candidate_changes_in_one_region() -> (
    None
):
    preview = search_v4_service._refinement_preview(
        baseline_ordered_candidate_ids=("a-1", "b-1", "a-2", "c-1"),
        candidate_region_ids={
            "a-1": "region-a",
            "a-2": "region-a",
            "b-1": "region-b",
            "c-1": "region-c",
        },
        variant_outcome=RefinementVariantOutcome(
            ordered_candidate_ids=("a-2", "a-1", "c-1", "b-1"),
            eligible_candidate_ids=frozenset({"a-1", "a-2", "b-1", "c-1"}),
            intent_changed=True,
        ),
    )

    assert [change.ski_region_id for change in preview.top_rank_changes] == [
        "region-c",
        "region-b",
    ]


def test_refinement_preview_reports_eligible_candidate_delta_from_baseline() -> None:
    preview = search_v4_service._refinement_preview(
        baseline_ordered_candidate_ids=("a", "b", "c", "d"),
        candidate_region_ids={
            "a": "region-a",
            "b": "region-b",
            "c": "region-c",
            "d": "region-d",
        },
        variant_outcome=RefinementVariantOutcome(
            ordered_candidate_ids=("a", "b", "c"),
            eligible_candidate_ids=frozenset({"a", "b", "c"}),
            intent_changed=True,
        ),
    )

    assert preview.eligible_candidate_count_delta == -1


def test_refinements_are_absent_when_llm_returns_no_validated_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: (),
    )

    refinements = search_v4_service._refinements(
        include=True,
        brief=None,
        intent=SearchIntent(),
        ordered=(),
        policy=load_search_policy(),
        client=object(),
        already_answered_question_ids=frozenset(),
    )

    assert refinements == ()


def test_ranking_only_search_never_generates_refinements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: pytest.fail("ranking must not call refinement generation"),
    )

    result = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
    )

    assert result.refinements == ()


def test_refinement_response_requires_status_consistent_queue() -> None:
    with pytest.raises(ValueError, match="questions_available"):
        SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            refinement_status="questions_available",
        )

    with pytest.raises(ValueError, match="non-current baselines"):
        SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            baseline_status="stale",
            refinement_status="not_needed",
        )

    with pytest.raises(ValueError, match="non-current baselines"):
        SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            baseline_status="unverified",
            refinement_status="not_needed",
        )

    with pytest.raises(ValueError, match="must not include refinements"):
        SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            refinement_status="not_needed",
            refinements=(
                search_v4_service.SearchV4RefinementProposal(
                    topic_id="accessible_terrain_scale",
                    target_factor_id="accessible_terrain_scale",
                    question_id="question",
                    question="Which option?",
                    reason="The leading options differ.",
                    options=(
                        search_v4_service.SearchV4RefinementOption(
                            label="First option",
                            description="Choose the first option.",
                            intent_changed=True,
                        ),
                        search_v4_service.SearchV4RefinementOption(
                            label="Second option",
                            description="Choose the second option.",
                            intent_changed=True,
                        ),
                    ),
                ),
            ),
        )


def test_baseline_fingerprint_detects_same_order_evidence_and_intent_drift() -> None:
    snapshot, manifest = _catalog_and_trust()
    evaluated = search_v4_service._evaluate_search(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
    )
    original = search_v4_service._baseline_fingerprint(evaluated)
    first = evaluated.ordered[0]
    changed_evaluation = first.evaluations[0].model_copy(
        update={"effective_evidence_cap": 0.123}
    )
    evidence_changed = replace(
        evaluated,
        ordered=(
            replace(
                first,
                evaluations=(changed_evaluation, *first.evaluations[1:]),
            ),
            *evaluated.ordered[1:],
        ),
    )
    intent_changed = replace(
        evaluated,
        intent=evaluated.intent.model_copy(update={"assumptions": ("Changed",)}),
    )

    assert search_v4_service._baseline_fingerprint(evidence_changed) != original
    assert search_v4_service._baseline_fingerprint(intent_changed) != original


def test_refinement_snapshot_compaction_preserves_scores() -> None:
    snapshot, manifest = _catalog_and_trust()
    intent = _intent()
    evaluated = search_v4_service._evaluate_search(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
    )
    compact_candidates = search_v4_service._refinement_baseline_candidates(
        evaluated.ordered
    )
    variant_intent = intent.model_copy(
        update={
            "group_priorities": (
                GroupPriorityPatch(
                    group_id="ski_experience",
                    importance="very_high",
                ),
            )
        }
    )

    for original, compact in zip(
        evaluated.ordered,
        compact_candidates,
        strict=True,
    ):
        for evaluation in compact.evaluations:
            assert set(evaluation.__dataclass_fields__) == {
                "factor_id",
                "raw_utility",
                "neutral_utility",
                "effective_evidence_cap",
            }

        for candidate_intent in (intent, variant_intent):
            original_score = score_factor_evaluations(
                evaluations=original.evaluations,
                intent=candidate_intent,
                policy=evaluated.policy,
            )
            compact_score = score_factor_evaluations(
                evaluations=tuple(
                    evaluation.materialize() for evaluation in compact.evaluations
                ),
                intent=candidate_intent,
                policy=evaluated.policy,
            )
            assert type(compact_score) is type(original_score)
            if isinstance(original_score, RankedScore):
                assert isinstance(compact_score, RankedScore)
                assert compact_score.fit_score == pytest.approx(
                    original_score.fit_score
                )


def test_refinement_snapshot_replay_graph_excludes_intent_and_origin_text() -> None:
    snapshot, manifest = _catalog_and_trust()
    private_origin = "Flat 17, 991 Distinctive Private Avenue, Krakow"
    intent = _intent().model_copy(
        update={
            "travel_context": TravelContext(
                origin_text=private_origin,
                mode="car",
            )
        }
    )
    store = SearchRefinementSnapshotStore()

    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    lookup = store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )

    assert lookup.snapshot is not None
    retained_values = tuple(_walk_object_graph(lookup.snapshot))
    assert not any(isinstance(value, SearchIntent) for value in retained_values)
    assert not any(isinstance(value, CatalogTrustManifest) for value in retained_values)
    assert private_origin not in {
        value for value in retained_values if isinstance(value, str)
    }


def test_apres_replay_matches_full_evaluator_reruns_without_acquisition() -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot = snapshot.model_copy(
        update={
            "stay_bases": tuple(
                base.model_copy(
                    update={
                        "local_apres_profile": base.local_apres_profile.model_copy(
                            update={"intensity": "low_key"}
                        )
                    }
                )
                if base.stay_base_id == "jochberg-jochberg"
                else base
                for base in snapshot.stay_bases
            )
        }
    )
    intent = _intent().model_copy(
        update={
            "constraints": _intent().constraints.model_copy(
                update={"location": LocationScope(country="Austria")}
            )
        }
    )
    climate_repository = _ClimatologyRepository()
    forecast_repository = _ForecastRepository()
    store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climate_repository,
        forecast_repository=forecast_repository,
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    lookup = store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    assert lookup.snapshot is not None
    states = search_v4_service._refinement_states(lookup.snapshot.candidates)
    proposal = RefinementProposal(
        topic_id="local_apres",
        target_factor_id="local_apres",
        question_id="local-apres-intensity",
        question="What evening atmosphere would you prefer near where you stay?",
        reason="The trusted local atmosphere varies between the trip options.",
        options=tuple(
            RefinementOption(
                label=label,
                description=description,
                factor_preference_patches=(
                    FactorPreferencePatch(
                        factor_id="local_apres",
                        mode=mode,
                        values=values,
                    ),
                ),
            )
            for label, description, mode, values in (
                (
                    "Low-key",
                    "Prefer a low-key evening near the accommodation base.",
                    "prefer",
                    ("low_key",),
                ),
                (
                    "Lively",
                    "Prefer a lively evening near the accommodation base.",
                    "prefer",
                    ("lively",),
                ),
                (
                    "It doesn't matter",
                    "Do not use the local evening atmosphere as a preference.",
                    "ignore",
                    (),
                ),
            )
        ),
    )
    acquisition_counts = (
        len(climate_repository.calls),
        len(forecast_repository.calls),
    )

    validated = validate_refinement_proposal(
        proposal=proposal,
        intent=intent,
        candidates=states,
        policy=lookup.snapshot.policy,
    )

    assert len({item.ordered_candidate_ids for item in validated.variant_outcomes}) > 1
    _assert_all_option_replay_matches_full_search(
        validated=validated,
        intent=intent,
        baseline_candidates=lookup.snapshot.candidates,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        policy=lookup.snapshot.policy,
    )
    assert (
        len(climate_repository.calls),
        len(forecast_repository.calls),
    ) == acquisition_counts


def test_refinement_replay_makes_neutral_categorical_raw_variation_actionable() -> None:
    snapshot, manifest = _catalog_and_trust()
    intent = _intent().model_copy(
        update={
            "constraints": _intent().constraints.model_copy(
                update={"location": LocationScope(country="Austria")}
            )
        }
    )
    store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    lookup = store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    assert lookup.snapshot is not None
    states = search_v4_service._refinement_states(lookup.snapshot.candidates)
    proposal = RefinementProposal(
        topic_id="development_style",
        target_factor_id="development_style",
        question_id="development-style",
        question="What kind of place would you prefer to stay in?",
        reason="Trusted development styles vary between the trip options.",
        options=(
            RefinementOption(
                label="Traditional mountain village",
                description="Prefer a base with traditional settlement character.",
                factor_preference_patches=(
                    FactorPreferencePatch(
                        factor_id="development_style",
                        mode="prefer",
                        values=("traditional",),
                    ),
                ),
            ),
            RefinementOption(
                label="A mix of old and new",
                description="Prefer a base mixing traditional and modern development.",
                factor_preference_patches=(
                    FactorPreferencePatch(
                        factor_id="development_style",
                        mode="prefer",
                        values=("mixed",),
                    ),
                ),
            ),
            RefinementOption(
                label="It doesn't matter",
                description="Do not use development style as an extra preference.",
                factor_preference_patches=(
                    FactorPreferencePatch(
                        factor_id="development_style",
                        mode="ignore",
                    ),
                ),
            ),
        ),
    )

    validated = validate_refinement_proposal(
        proposal=proposal,
        intent=intent,
        candidates=states,
        policy=lookup.snapshot.policy,
    )

    assert validated.impact.material is True
    assert len({item.ordered_candidate_ids for item in validated.variant_outcomes}) > 1
    _assert_all_option_replay_matches_full_search(
        validated=validated,
        intent=intent,
        baseline_candidates=lookup.snapshot.candidates,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        policy=lookup.snapshot.policy,
    )


@pytest.mark.parametrize(
    "factor_id",
    (
        "marked_freeride_routes",
        "snow_park",
        "night_skiing",
        "glacier_terrain",
        "snowmaking_availability",
    ),
)
def test_require_answer_replay_matches_full_narrowed_cohort(
    factor_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    intent = _intent().model_copy(
        update={
            "constraints": _intent().constraints.model_copy(
                update={"location": LocationScope(country="Austria")}
            )
        }
    )
    store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    lookup = store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    assert lookup.snapshot is not None
    proposal = _registered_positive_presence_proposal(factor_id)
    derive_calls: list[int] = []
    original_derive_numeric_bounds = refinement_snapshot_module.derive_numeric_bounds

    def derive_numeric_bounds(**kwargs):
        derive_calls.append(len(kwargs["candidates"]))
        return original_derive_numeric_bounds(**kwargs)

    monkeypatch.setattr(
        refinement_snapshot_module,
        "derive_numeric_bounds",
        derive_numeric_bounds,
    )

    validated = validate_refinement_proposal(
        proposal=proposal,
        intent=intent,
        candidates=search_v4_service._refinement_states(lookup.snapshot.candidates),
        policy=lookup.snapshot.policy,
    )
    assert len(derive_calls) == len(proposal.options)

    _assert_all_option_replay_matches_full_search(
        validated=validated,
        intent=intent,
        baseline_candidates=lookup.snapshot.candidates,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        policy=lookup.snapshot.policy,
    )


def test_production_refinement_rejects_relaxing_synthesized_require() -> None:
    snapshot, manifest = _catalog_and_trust()
    base_intent = _intent().model_copy(
        update={
            "constraints": _intent().constraints.model_copy(
                update={"location": LocationScope(country="Austria")}
            )
        }
    )
    intent = base_intent.model_copy(
        update={
            "factor_preferences": (
                FactorPreferencePatch(
                    factor_id="marked_freeride_routes",
                    mode="require",
                ),
            )
        }
    )
    store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    lookup = store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    assert lookup.snapshot is not None
    proposal = _registered_positive_presence_proposal("marked_freeride_routes")
    relaxed_intent = apply_refinement_option(
        intent,
        proposal.options[-1],
        lookup.snapshot.policy,
    )
    relaxed = search_v4_service._evaluate_search(
        intent=relaxed_intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        policy=lookup.snapshot.policy,
    )
    assert len(relaxed.ordered) > len(lookup.snapshot.candidates)

    with pytest.raises(RefinementValidationError, match="widen"):
        validate_refinement_proposal(
            proposal=proposal,
            intent=intent,
            candidates=search_v4_service._refinement_states(lookup.snapshot.candidates),
            policy=lookup.snapshot.policy,
        )


def test_exact_date_snowmaking_replay_updates_trip_window_snow_fit() -> None:
    snapshot, manifest = _catalog_and_trust()
    intent = _intent().model_copy(
        update={
            "constraints": _intent().constraints.model_copy(
                update={"location": LocationScope(country="Austria")}
            )
        }
    )
    requested_dates = (date(2027, 1, 10), date(2027, 1, 11), date(2027, 1, 12))
    climate_rows = tuple(
        _climatology_row(
            ski_area_id=ski_area_id,
            day=day,
            snow_depth_cm_p50=25,
        ).model_copy(update={"avg_snow_confidence_score": 0.2})
        for ski_area_id in _country_area_ids(snapshot, "Austria")
        for day in requested_dates
    )
    store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(climate_rows),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    lookup = store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    assert lookup.snapshot is not None
    replay_candidate = next(
        item
        for item in lookup.snapshot.candidates
        if item.replay_state is not None
        and next(
            evaluation
            for evaluation in item.replay_state.evaluate(intent)
            if evaluation.factor_id == "snowmaking_availability"
        ).effective_evidence_cap
        > 0
    )
    prefer_option = RefinementOption(
        label="Useful backup",
        description="Prefer snowmaking backup when natural snow is weak.",
        factor_preference_patches=(
            FactorPreferencePatch(
                factor_id="snowmaking_availability",
                mode="prefer",
            ),
        ),
    )
    ignore_option = RefinementOption(
        label="It doesn't matter",
        description="Do not use snowmaking as an extra preference.",
        factor_preference_patches=(
            FactorPreferencePatch(
                factor_id="snowmaking_availability",
                mode="ignore",
            ),
        ),
    )
    proposal = RefinementProposal(
        topic_id="snowmaking_availability",
        target_factor_id="snowmaking_availability",
        question_id="snowmaking-backup",
        question="How important is snowmaking backup for these dates?",
        reason="Trusted snowmaking support varies across the trip options.",
        options=(prefer_option, ignore_option),
    )
    states = search_v4_service._refinement_states(lookup.snapshot.candidates)
    validated = validate_refinement_proposal(
        proposal=proposal,
        intent=intent,
        candidates=states,
        policy=lookup.snapshot.policy,
    )
    _assert_all_option_replay_matches_full_search(
        validated=validated,
        intent=intent,
        baseline_candidates=lookup.snapshot.candidates,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        policy=lookup.snapshot.policy,
        climatology_rows=climate_rows,
    )

    prefer_intent = apply_refinement_option(
        intent,
        prefer_option,
        lookup.snapshot.policy,
    )
    ignore_intent = apply_refinement_option(
        intent,
        ignore_option,
        lookup.snapshot.policy,
    )
    assert replay_candidate.replay_state is not None

    prefer_snow = next(
        evaluation
        for evaluation in replay_candidate.replay_state.evaluate(prefer_intent)
        if evaluation.factor_id == "trip_window_snow_fit"
    )
    ignore_snow = next(
        evaluation
        for evaluation in replay_candidate.replay_state.evaluate(ignore_intent)
        if evaluation.factor_id == "trip_window_snow_fit"
    )

    assert prefer_snow.effective_utility > ignore_snow.effective_utility
    expected = search_v4_service._evaluate_search(
        intent=prefer_intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(climate_rows),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        policy=lookup.snapshot.policy,
    )
    expected_candidate = next(
        item
        for item in expected.ordered
        if item.record.candidate_id == replay_candidate.candidate_id
    )
    expected_snow = next(
        evaluation
        for evaluation in expected_candidate.evaluations
        if evaluation.factor_id == "trip_window_snow_fit"
    )
    assert prefer_snow == expected_snow


@pytest.mark.parametrize(
    ("evidence_cap", "forecast_coverage", "expected"),
    (
        (0.0, 0.0, "fallback_heavy"),
        (1.0, 0.0, "archive_backed"),
        (1.0, 0.5, "forecast_assisted"),
    ),
)
def test_evidence_profile_is_derived_from_backend_weather_evidence(
    evidence_cap: float,
    forecast_coverage: float,
    expected: str,
) -> None:
    evaluation = FactorEvaluation(
        factor_id="trip_window_snow_fit",
        scope="ski_area",
        entity_ids=("area",),
        raw_value=None,
        raw_utility=0.7,
        neutral_utility=0.5,
        effective_evidence_cap=evidence_cap,
        evidence_cap_components={
            "climatology_date_coverage": evidence_cap,
            "forecast_date_coverage": forecast_coverage,
        },
        warnings=(),
        provenance_summary="Test weather evidence.",
        explanation_inputs={},
    )

    assert search_v4_service._evidence_profile((evaluation,)) == expected


def test_refinement_service_uses_fallback_and_records_bounded_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    presentations: list[object] = []

    def generate(**kwargs: object) -> search_v4_service.RefinementGenerationResult:
        presentations.append(kwargs["presentation"])
        return search_v4_service.RefinementGenerationResult(
            outcome="no_proposals",
            proposals=(),
        )

    def fallback(**kwargs: object) -> ValidatedRefinementProposal:
        presentations.append(kwargs["presentation"])
        return _validated_refinement(
            (
                tuple(item.candidate_id for item in kwargs["candidates"]),
                frozenset(item.candidate_id for item in kwargs["candidates"]),
            ),
            (
                tuple(
                    reversed(tuple(item.candidate_id for item in kwargs["candidates"]))
                ),
                frozenset(item.candidate_id for item in kwargs["candidates"]),
            ),
        )

    monkeypatch.setattr(search_v4_service, "generate_refinement_proposals", generate)
    monkeypatch.setattr(
        search_v4_service,
        "build_deterministic_refinement_fallback",
        fallback,
    )

    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        response = get_search_refinements(
            intent=_intent(),
            brief="Help us decide.",
            baseline_fingerprint=baseline.baseline_fingerprint,
            already_answered_question_ids=frozenset(),
            llm_client_factory=lambda _remaining_seconds: object(),
            refinement_snapshot_store=snapshot_store,
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert response.refinement_status == "questions_available"
    assert response.refinement_presentation_policy_version == (
        "search-refinement-presentation-2"
    )
    assert response.fallback_used is True
    assert len(response.refinements) == 1
    assert len(presentations) == 2
    assert presentations[0] is presentations[1]
    assert (
        "snowcast_search_refinement_requests_total",
        {
            "search_model": "search-v4",
            "ranking_policy_version": "search-v4-policy-1",
            "status": "questions_available",
            "reason": "deterministic_fallback",
            "fallback_used": True,
            "window_type": "exact_dates",
            "has_origin": False,
        },
        1,
    ) in recorder.counters
    assert (
        "snowcast_search_refinement_fallbacks_total",
        {"search_model": "search-v4"},
        1,
    ) in recorder.counters


def test_refinement_service_treats_invalid_presentation_as_configuration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        search_v4_service,
        "load_refinement_presentation_policy",
        lambda: (_ for _ in ()).throw(ValueError("invalid presentation config")),
    )

    with pytest.raises(ValueError, match="invalid presentation config"):
        get_search_refinements(
            intent=_intent(),
            brief="Help us decide.",
            baseline_fingerprint="a" * 64,
            already_answered_question_ids=frozenset(),
            llm_client_factory=lambda _remaining: pytest.fail(
                "configuration failure must skip provider"
            ),
            refinement_snapshot_store=SearchRefinementSnapshotStore(),
        )


def test_refinement_service_returns_not_needed_for_zero_result_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot_store = SearchRefinementSnapshotStore()
    zero_intent = SearchIntent(
        constraints=SearchConstraints(location=LocationScope(country="Norway"))
    )
    baseline = search_trip_configurations(
        intent=zero_intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )

    response = get_search_refinements(
        intent=zero_intent,
        brief="No candidates expected.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail("must skip provider"),
        refinement_snapshot_store=snapshot_store,
    )

    assert baseline.eligible_candidate_count == 0
    assert response.refinement_status == "not_needed"
    assert response.refinements == ()


def test_all_resolved_topics_need_no_provider_completion_in_refinement_service() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()
    policy = load_search_policy()
    presentation = load_refinement_presentation_policy()
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        policy=policy,
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    provider_completions = 0

    class _Client:
        model = "test-model"

        def complete(self, **_kwargs: object) -> str:
            nonlocal provider_completions
            provider_completions += 1
            raise AssertionError("resolved topics must skip provider completion")

    resolved_topic_ids = frozenset(
        topic.topic_id
        for topic in presentation.topics
        if policy.factor(topic.factor_id).clarifiable
    )

    response = get_search_refinements(
        intent=_intent(),
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        resolved_topic_ids=resolved_topic_ids,
        llm_client_factory=lambda _remaining: _Client(),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.refinement_status == "not_needed"
    assert response.refinements == ()
    assert provider_completions == 0


@pytest.mark.parametrize(
    ("max_questions", "expected_generation_calls"),
    ((0, 0), (1, 1)),
)
def test_refinement_service_respects_zero_and_nearby_nonzero_question_limits(
    monkeypatch: pytest.MonkeyPatch,
    max_questions: int,
    expected_generation_calls: int,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    base_policy = load_search_policy()
    policy = base_policy.model_copy(
        update={
            "refinement": base_policy.refinement.model_copy(
                update={"max_questions": max_questions}
            )
        }
    )
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        policy=policy,
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    generation_calls = 0
    client_factory_calls = 0
    fallback_calls = 0

    def generate(**_kwargs: object) -> search_v4_service.RefinementGenerationResult:
        nonlocal generation_calls
        generation_calls += 1
        return search_v4_service.RefinementGenerationResult(
            outcome="no_proposals",
            proposals=(),
        )

    def client_factory(_remaining: float) -> object:
        nonlocal client_factory_calls
        client_factory_calls += 1
        return object()

    def fallback(**_kwargs: object) -> None:
        nonlocal fallback_calls
        fallback_calls += 1
        return None

    monkeypatch.setattr(search_v4_service, "generate_refinement_proposals", generate)
    monkeypatch.setattr(
        search_v4_service,
        "build_deterministic_refinement_fallback",
        fallback,
    )

    response = get_search_refinements(
        intent=_intent(),
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=client_factory,
        refinement_snapshot_store=snapshot_store,
    )

    assert response.refinement_status == "not_needed"
    assert response.refinements == ()
    assert generation_calls == expected_generation_calls
    assert client_factory_calls == expected_generation_calls
    assert fallback_calls == expected_generation_calls


def test_refinement_service_fails_closed_on_snapshot_miss_without_reevaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_store = SearchRefinementSnapshotStore()
    monkeypatch.setattr(
        search_v4_service,
        "_evaluate_search",
        lambda **_kwargs: pytest.fail("snapshot miss must not rerun search"),
    )

    response = get_search_refinements(
        intent=_intent(),
        brief="Help us decide.",
        baseline_fingerprint="a" * 64,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail(
            "snapshot miss must skip provider"
        ),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.baseline_status == "unverified"
    assert response.refinement_status == "temporarily_unavailable"
    assert response.fallback_used is False
    assert response.refinements == ()


def test_refinement_service_fails_closed_when_snapshot_lacks_replay_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    intent = _intent()
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    lookup = snapshot_store.get(
        baseline.baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    assert lookup.snapshot is not None
    damaged_candidate = replace(
        lookup.snapshot.candidates[0],
        replay_state=None,
    )
    snapshot_store.put(
        replace(
            lookup.snapshot,
            candidates=(damaged_candidate, *lookup.snapshot.candidates[1:]),
        )
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: pytest.fail("missing replay must skip provider"),
    )
    monkeypatch.setattr(
        search_v4_service,
        "build_deterministic_refinement_fallback",
        lambda **_kwargs: pytest.fail("missing replay must skip fallback"),
    )

    response = get_search_refinements(
        intent=intent,
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail(
            "missing replay must skip client construction"
        ),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.baseline_status == "current"
    assert response.refinement_status == "temporarily_unavailable"
    assert response.fallback_used is False
    assert response.refinements == ()


def test_capacity_rejection_keeps_search_results_and_refinement_fails_closed() -> None:
    snapshot, manifest = _catalog_and_trust()
    intent = _intent()
    snapshot_store = SearchRefinementSnapshotStore(max_candidate_replay_states=1)
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        baseline = search_trip_configurations(
            intent=intent,
            catalog_snapshot=snapshot,
            trust_manifest=manifest,
            climatology_repository=_ClimatologyRepository(),
            forecast_repository=_ForecastRepository(),
            reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
            refinement_snapshot_store=snapshot_store,
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert baseline.results
    assert snapshot_store.usage().entry_count == 0
    assert (
        "snowcast_search_refinement_snapshot_outcomes_total",
        {"search_model": "search-v4", "outcome": "capacity_rejected"},
        1,
    ) in recorder.counters

    refinement = get_search_refinements(
        intent=intent,
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail(
            "capacity rejection must skip provider"
        ),
        refinement_snapshot_store=snapshot_store,
    )

    assert refinement.baseline_status == "unverified"
    assert refinement.refinement_status == "temporarily_unavailable"


def test_refinement_service_fails_closed_after_snapshot_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    now = [0.0]
    snapshot_store = SearchRefinementSnapshotStore(clock=lambda: now[0])
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    now[0] = 60.0
    monkeypatch.setattr(
        search_v4_service,
        "_evaluate_search",
        lambda **_kwargs: pytest.fail("expired snapshot must not rerun search"),
    )

    response = get_search_refinements(
        intent=_intent(),
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail(
            "expired snapshot must skip provider"
        ),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.baseline_status == "unverified"
    assert response.refinement_status == "temporarily_unavailable"


def test_refinement_service_fails_closed_after_snapshot_eviction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot_store = SearchRefinementSnapshotStore(max_entries=1)
    initial_intent = _intent()
    initial = search_trip_configurations(
        intent=initial_intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    search_trip_configurations(
        intent=initial_intent.model_copy(update={"assumptions": ("New search",)}),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    monkeypatch.setattr(
        search_v4_service,
        "_evaluate_search",
        lambda **_kwargs: pytest.fail("evicted snapshot must not rerun search"),
    )

    response = get_search_refinements(
        intent=initial_intent,
        brief="Help us decide.",
        baseline_fingerprint=initial.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail(
            "evicted snapshot must skip provider"
        ),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.baseline_status == "unverified"
    assert response.refinement_status == "temporarily_unavailable"


def test_refinement_service_rejects_fingerprint_reuse_with_another_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    changed_intent = _intent().model_copy(update={"assumptions": ("Changed",)})
    monkeypatch.setattr(
        search_v4_service,
        "_evaluate_search",
        lambda **_kwargs: pytest.fail("intent mismatch must not rerun search"),
    )

    response = get_search_refinements(
        intent=changed_intent,
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail(
            "intent mismatch must skip provider"
        ),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.baseline_status == "stale"
    assert response.refinement_status == "temporarily_unavailable"


def test_refinement_service_skips_provider_when_request_budget_is_exhausted() -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    clock_values = iter((0.0, 5.0, 5.0, 5.0))

    response = get_search_refinements(
        intent=_intent(),
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda _remaining: pytest.fail("deadline skips provider"),
        clock=lambda: next(clock_values),
        refinement_snapshot_store=snapshot_store,
    )

    assert response.refinement_status == "temporarily_unavailable"
    assert response.refinements == ()


def test_refinement_service_passes_only_remaining_deadline_to_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    snapshot_store = SearchRefinementSnapshotStore()
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    monkeypatch.setattr(
        search_v4_service,
        "_evaluate_search",
        lambda **_kwargs: pytest.fail("refinement must reuse the snapshot"),
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: search_v4_service.RefinementGenerationResult(
            outcome="no_proposals",
            proposals=(),
        ),
    )
    remaining: list[float] = []
    clock_values = iter((10.0, 11.0, 11.0, 11.0))

    get_search_refinements(
        intent=_intent(),
        brief="Help us decide.",
        baseline_fingerprint=baseline.baseline_fingerprint,
        already_answered_question_ids=frozenset(),
        llm_client_factory=lambda budget: remaining.append(budget) or object(),
        clock=lambda: next(clock_values),
        refinement_snapshot_store=snapshot_store,
    )

    assert remaining == [4.0]


def test_each_rerank_stores_a_fresh_refinement_snapshot_after_prior_expiry() -> None:
    snapshot, manifest = _catalog_and_trust()
    now = [0.0]
    snapshot_store = SearchRefinementSnapshotStore(
        ttl_seconds=60,
        max_entries=64,
        clock=lambda: now[0],
    )
    initial_intent = _intent()
    initial = search_trip_configurations(
        intent=initial_intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )
    initial_lookup = snapshot_store.get(
        initial.baseline_fingerprint,
        canonical_search_intent_digest(initial_intent),
    )
    assert initial_lookup.outcome == "hit"

    now[0] = 61.0
    refined_intent = initial_intent.model_copy(
        update={"assumptions": ("Prefer the quieter option",)}
    )
    refined = search_trip_configurations(
        intent=refined_intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=snapshot_store,
    )

    assert refined.baseline_fingerprint != initial.baseline_fingerprint
    assert (
        snapshot_store.get(
            refined.baseline_fingerprint,
            canonical_search_intent_digest(refined_intent),
        ).outcome
        == "hit"
    )
    assert (
        snapshot_store.get(
            initial.baseline_fingerprint,
            canonical_search_intent_digest(initial_intent),
        ).outcome
        == "expired"
    )


def test_service_constrains_then_bulk_loads_weather_once_and_ranks() -> None:
    snapshot, manifest = _catalog_and_trust()
    climatology = _ClimatologyRepository()
    forecast = _ForecastRepository()

    result = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
        include_refinements=False,
    )

    assert isinstance(result, SearchV4Response)
    assert result.search_model_version == "search-v4"
    assert result.ranking_policy_version == "search-v4-policy-1"
    assert result.ranking_status == "ranked"
    assert result.eligible_candidate_count > 0
    assert result.excluded_candidate_count > 0
    assert result.results
    assert result.results[0].top_configuration.fit_score is not None
    assert len(climatology.calls) == 1
    assert len(forecast.calls) == 1
    assert {
        configuration.evidence_profile for configuration in _configurations(result)
    } == {"fallback_heavy"}
    assert forecast.calls[0]["source_keys"] == (
        "ecmwf_ifs025_ensemble_mean",
        "ncep_gefs05_ensemble_mean",
    )
    assert len(forecast.calls[0]["ski_area_ids"]) == len(
        set(forecast.calls[0]["ski_area_ids"])
    )

    argentiere_balme = next(
        configuration
        for configuration in _configurations(result)
        if configuration.access.ski_area_access_id
        == "chamonix-mont-blanc-argentiere--balme-le-tour-vallorcine"
    )
    assert argentiere_balme.access.relationship_trust_status == "estimated"
    assert argentiere_balme.access.access_mode_distance_trust_status == "needs_source"


def test_service_qualifies_ski_area_terrain_fallback_with_owning_trust() -> None:
    snapshot, manifest = _catalog_and_trust()

    result = search_trip_configurations(
        intent=SearchIntent(
            constraints=SearchConstraints(
                location=LocationScope(country="Italy"),
                pass_price_ceiling=PassPriceCeilingConstraint(
                    maximum=320,
                    currency="EUR",
                    duration_days=6,
                    audience="adult",
                    season="high season 2025/26",
                ),
            )
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        include_refinements=False,
    )

    pinzolo = next(
        configuration
        for group in result.results
        for configuration in (
            group.top_configuration,
            *group.alternative_configurations,
        )
        if configuration.selected_pass.lift_pass_product_id == "pinzolo-local-pass"
    )

    assert pinzolo.selected_pass.accessible_piste_km == 31
    assert pinzolo.selected_pass.accessible_piste_km_evidence.model_dump() == {
        "trust_status": "estimated",
        "scope": "ski_area",
        "source_entity_id": "pinzolo-ski-area",
        "field_group": "terrain_metrics",
    }


def test_service_uses_verified_domain_when_pass_aggregate_is_unusable() -> None:
    snapshot, manifest = _catalog_and_trust()
    synthetic_aggregate = AggregateTerrainMetrics.model_validate(
        {
            "total_piste_km": 999,
            "source_urls": ["https://example.com/untrusted-pass-aggregate"],
        },
        context={"source_owner_usable": False},
    )
    snapshot = snapshot.model_copy(
        update={
            "lift_pass_products": tuple(
                product.model_copy(
                    update={"pass_accessible_terrain": synthetic_aggregate}
                )
                if product.lift_pass_product_id == "tignes-val-disere-ski-pass"
                else product
                for product in snapshot.lift_pass_products
            )
        }
    )

    result = search_trip_configurations(
        intent=SearchIntent(
            constraints=SearchConstraints(location=LocationScope(country="France")),
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        include_refinements=False,
    )

    tignes = next(
        configuration
        for group in result.results
        for configuration in (
            group.top_configuration,
            *group.alternative_configurations,
        )
        if configuration.selected_pass.lift_pass_product_id
        == "tignes-val-disere-ski-pass"
    )
    factor = next(
        item for item in tignes.factors if item.factor_id == "accessible_terrain_scale"
    )

    assert factor.raw_value == 300
    assert factor.effective_evidence_cap == 1
    assert tignes.selected_pass.accessible_piste_km == factor.raw_value
    assert tignes.selected_pass.accessible_piste_km_evidence.model_dump() == {
        "trust_status": "verified_with_adjustment",
        "scope": "terrain_domain",
        "source_entity_id": "tignes-val-disere",
        "field_group": "aggregate_terrain",
    }


def test_one_area_dossier_loads_only_the_requested_area_once() -> None:
    snapshot, manifest = _catalog_and_trust()
    ski_area_id = snapshot.ski_areas[0].ski_area_id
    climatology = _ClimatologyRepository(
        (
            _climatology_row(
                ski_area_id=ski_area_id,
                day=date(2027, 1, 2),
                snow_depth_cm_p50=70,
            ),
        )
    )
    forecast = _ForecastRepository()

    result = get_search_weather_evidence(
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=TravelWindow(month=1)),
        ),
        ski_area_id=ski_area_id,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
    )

    assert result.status == "available"
    assert result.ski_area_id == ski_area_id
    assert result.evidence.mode == "climatology"
    assert result.evidence.forecast is None
    assert climatology.calls[0]["ski_area_ids"] == (ski_area_id,)
    assert len(climatology.calls) == 1
    assert forecast.calls == []


def test_one_area_dossier_rejects_unknown_area_before_repository_access() -> None:
    snapshot, manifest = _catalog_and_trust()
    climatology = _ClimatologyRepository()
    forecast = _ForecastRepository()

    with pytest.raises(UnknownSearchWeatherAreaError):
        get_search_weather_evidence(
            intent=SearchIntent(),
            ski_area_id="unknown-area",
            catalog_snapshot=snapshot,
            trust_manifest=manifest,
            climatology_repository=climatology,
            forecast_repository=forecast,
        )

    assert climatology.calls == []
    assert forecast.calls == []


def test_one_area_dossier_forecast_validity_uses_earliest_selected_run_expiry() -> None:
    snapshot, manifest = _catalog_and_trust()
    ski_area_id = snapshot.ski_areas[0].ski_area_id
    requested_dates = tuple(
        date(2027, 1, 10) + timedelta(days=offset) for offset in range(3)
    )
    climatology = _ClimatologyRepository(
        tuple(
            _climatology_row(
                ski_area_id=ski_area_id,
                day=valid_date,
                snow_depth_cm_p50=70,
            )
            for valid_date in requested_dates
        )
    )
    forecast = _ForecastRepository(
        _forecast_rows(ski_area_ids=(ski_area_id,), requested_dates=requested_dates)
    )
    intent = SearchIntent(
        constraints=SearchConstraints(
            travel_window=TravelWindow(
                start_date=requested_dates[0],
                end_date=requested_dates[-1],
            )
        )
    )

    fresh = get_search_weather_evidence(
        intent=intent,
        ski_area_id=ski_area_id,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 9, 12, tzinfo=UTC),
    )
    expired = get_search_weather_evidence(
        intent=intent,
        ski_area_id=ski_area_id,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 9, 22, 10, 1, tzinfo=UTC),
    )

    assert fresh.status == "available"
    assert fresh.evidence.mode == "forecast_assisted"
    assert fresh.cache_valid_until == "2027-01-09T13:10:00+00:00"
    assert expired.status == "available"
    assert expired.evidence.mode == "climatology"
    assert len(climatology.calls) == 2
    assert len(forecast.calls) == 2


def test_one_area_dossier_uses_presented_forecast_rows_for_validity_and_elevation() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()
    ski_area_id = snapshot.ski_areas[0].ski_area_id
    forecast_dates = tuple(
        date(2027, 1, 9) + timedelta(days=offset) for offset in range(4)
    )
    climatology = _ClimatologyRepository(
        tuple(
            _climatology_row(
                ski_area_id=ski_area_id,
                day=valid_date,
                snow_depth_cm_p50=70,
            )
            for valid_date in forecast_dates
        )
    )
    forecast_rows = tuple(
        row.model_copy(
            update={
                "daily": row.daily.model_copy(
                    update={"representative_elevation_m": 2200}
                )
            }
        )
        for row in _forecast_rows(
            ski_area_ids=(ski_area_id,),
            requested_dates=forecast_dates,
        )
    )
    forecast = _ForecastRepository(forecast_rows)
    intent = SearchIntent(
        constraints=SearchConstraints(
            travel_window=TravelWindow(
                start_date=date(2026, 12, 1),
                end_date=forecast_dates[-1],
            )
        )
    )

    result = get_search_weather_evidence(
        intent=intent,
        ski_area_id=ski_area_id,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 9, 12, tzinfo=UTC),
    )

    assert result.status == "available"
    assert result.evidence.mode == "forecast_assisted"
    assert result.evidence.forecast is not None
    assert result.evidence.forecast.usable_date_count == 4
    assert result.cache_valid_until == "2027-01-09T13:10:00+00:00"
    assert result.evidence.elevation_status == "mixed"
    assert result.evidence.elevation_m is None
    assert {source.elevation_m for source in result.evidence.forecast.sources} == {2200}


def test_one_area_dossier_preserves_nullable_historical_elevation() -> None:
    snapshot, manifest = _catalog_and_trust()
    ski_area_id = snapshot.ski_areas[0].ski_area_id
    row = _climatology_row(
        ski_area_id=ski_area_id,
        day=date(2027, 1, 2),
        snow_depth_cm_p50=70,
        elevation_m=None,
    )

    result = get_search_weather_evidence(
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=TravelWindow(month=1)),
        ),
        ski_area_id=ski_area_id,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository((row,)),
        forecast_repository=_ForecastRepository(),
        reference_time=datetime(2027, 1, 1, 12, tzinfo=UTC),
    )

    assert result.status == "available"
    assert result.evidence.elevation_status == "unavailable"
    assert result.evidence.elevation_m is None
    assert result.evidence.historical.sources[0].elevation_m is None


def test_month_search_keeps_grouped_response_compact_without_loading_forecasts() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()
    area_ids = _country_area_ids(snapshot, "France")
    rows = tuple(
        _climatology_row(
            ski_area_id=ski_area_id,
            day=date(2027, 1, 2),
            snow_depth_cm_p50=70 + index,
        )
        for index, ski_area_id in enumerate(area_ids)
    )
    climatology = _ClimatologyRepository(rows)
    forecast = _ForecastRepository()

    result = search_trip_configurations(
        intent=SearchIntent(
            constraints=SearchConstraints(
                location=LocationScope(country="France"),
                travel_window=TravelWindow(month=1),
            )
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        include_refinements=False,
    )

    assert result.results
    assert all(
        "weather_evidence" not in configuration.model_dump()
        for configuration in _configurations(result)
    )
    assert len(climatology.calls) == 1
    assert forecast.calls == []


def test_exact_date_search_does_not_map_weather_evidence_without_changing_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, manifest = _catalog_and_trust()
    area_ids = _country_area_ids(snapshot, "France")
    requested_dates = tuple(
        date(2027, 1, 10) + timedelta(days=offset) for offset in range(3)
    )
    depth_by_area = {
        ski_area_id: 70 + index for index, ski_area_id in enumerate(area_ids)
    }
    climate_rows = tuple(
        _climatology_row(
            ski_area_id=ski_area_id,
            day=valid_date,
            snow_depth_cm_p50=depth_by_area[ski_area_id],
        )
        for ski_area_id in area_ids
        for valid_date in requested_dates
    )
    forecast_rows = _forecast_rows(
        ski_area_ids=area_ids,
        requested_dates=requested_dates,
    )
    climatology = _ClimatologyRepository(climate_rows)
    forecast = _ForecastRepository(forecast_rows)
    build_calls: list[str] = []
    monkeypatch.setattr(
        search_v4_service,
        "build_search_weather_evidence",
        lambda **_kwargs: pytest.fail("grouped search must not map weather evidence"),
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: pytest.fail("refinement LLM path must not be called"),
    )

    result = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        reference_time=datetime(2027, 1, 9, 12, tzinfo=UTC),
        include_refinements=False,
    )

    configurations = _configurations(result)
    assert configurations
    assert build_calls == []
    assert all(
        "weather_evidence" not in configuration.model_dump()
        for configuration in configurations
    )
    assert len(climatology.calls) == 1
    assert len(forecast.calls) == 1

    baseline_climatology = _ClimatologyRepository(climate_rows)
    baseline_forecast = _ForecastRepository(forecast_rows)
    baseline = search_trip_configurations(
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=baseline_climatology,
        forecast_repository=baseline_forecast,
        reference_time=datetime(2027, 1, 9, 12, tzinfo=UTC),
        include_refinements=False,
    )

    assert _ranking_projection(result) == _ranking_projection(baseline)
    assert len(baseline_climatology.calls) == 1
    assert len(baseline_forecast.calls) == 1


def test_maximum_shape_search_snapshot_fits_global_replay_budgets() -> None:
    snapshot, manifest = _catalog_and_trust()
    start = date(2027, 2, 1)
    end = start + timedelta(days=30)
    intent = SearchIntent(
        constraints=SearchConstraints(
            travel_window=TravelWindow(start_date=start, end_date=end),
        ),
        party=PartyContext(skill_levels=("intermediate",)),
    )
    store = SearchRefinementSnapshotStore()

    started_at = time.perf_counter()
    result = search_trip_configurations(
        intent=intent,
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_MaximumShapeClimatologyRepository(),
        forecast_repository=_MaximumShapeForecastRepository(),
        reference_time=datetime(2027, 2, 1, 12, tzinfo=UTC),
        refinement_snapshot_store=store,
    )
    elapsed_ms = (time.perf_counter() - started_at) * 1_000

    usage = store.usage()
    print(
        "maximum-shape snapshot: "
        f"candidates={usage.candidate_replay_state_count}, "
        f"weather_rows={usage.weather_row_count}, elapsed_ms={elapsed_ms:.1f}"
    )
    assert result.results
    assert usage.entry_count == 1
    assert usage.candidate_replay_state_count == result.eligible_candidate_count
    assert 0 < usage.candidate_replay_state_count <= 2_048
    assert 0 < usage.weather_row_count <= 8_192
    assert (
        store.get(
            result.baseline_fingerprint,
            canonical_search_intent_digest(intent),
        ).outcome
        == "hit"
    )


def test_one_area_endpoint_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot, manifest = _catalog_and_trust()
    ski_area_id = snapshot.ski_areas[0].ski_area_id
    start = date(2027, 2, 1)
    end = start + timedelta(days=30)
    intent = SearchIntent(
        constraints=SearchConstraints(
            travel_window=TravelWindow(start_date=start, end_date=end),
        ),
    )
    reference_time = datetime(2027, 2, 1, 12, tzinfo=UTC)
    complete_climatology = _MaximumShapeClimatologyRepository()
    complete_forecast = _MaximumShapeForecastRepository()

    def build_response():
        return get_search_weather_evidence(
            intent=intent,
            ski_area_id=ski_area_id,
            catalog_snapshot=snapshot,
            trust_manifest=manifest,
            climatology_repository=complete_climatology,
            forecast_repository=complete_forecast,
            reference_time=reference_time,
        )

    warm_response = build_response()
    durations_ms: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        response = build_response()
        durations_ms.append((time.perf_counter() - started) * 1_000)
    p95_ms = statistics.quantiles(durations_ms, n=100, method="inclusive")[94]
    route_app = FastAPI()
    route_app.include_router(router, prefix="/api")
    monkeypatch.setattr(
        "app.api.routes.get_search_weather_evidence",
        lambda **_kwargs: response,
    )
    with TestClient(route_app) as route_client:
        route_response = route_client.post(
            "/api/search/weather-evidence",
            json={
                "ski_area_id": ski_area_id,
                "intent": {
                    "constraints": {
                        "travel_window": {
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                        }
                    }
                },
            },
        )
    serialized_bytes = len(route_response.content)

    assert warm_response.status == "available"
    assert response.status == "available"
    assert response.evidence.mode == "forecast_assisted"
    assert len(response.evidence.historical.daily_profile) == 31
    assert response.evidence.forecast is not None
    assert len(response.evidence.forecast.daily_profile) == 31
    assert len(response.evidence.historical.sources) <= 31
    assert len(response.evidence.forecast.sources) <= 31
    assert len(response.evidence.historical.sources) == 31
    assert len(response.evidence.forecast.sources) == 31
    assert route_response.status_code == 200
    assert all(
        call["ski_area_ids"] == (ski_area_id,) for call in complete_climatology.calls
    )
    assert all(
        call["ski_area_ids"] == (ski_area_id,) for call in complete_forecast.calls
    )
    assert not math.isnan(p95_ms)
    print(
        "one_area_endpoint_cost "
        f"route_envelope_bytes={serialized_bytes} p95_ms={p95_ms:.3f} iterations=100"
    )
    assert serialized_bytes <= 131_072
    assert p95_ms <= 25


def test_stale_forecasts_produce_dossier_climatology_fallback_and_limitation() -> None:
    snapshot, manifest = _catalog_and_trust()
    ski_area_id = _country_area_ids(snapshot, "France")[0]
    requested_dates = tuple(
        date(2027, 1, 10) + timedelta(days=offset) for offset in range(3)
    )
    result = get_search_weather_evidence(
        ski_area_id=ski_area_id,
        intent=_intent(),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=_ClimatologyRepository(
            tuple(
                _climatology_row(
                    ski_area_id=ski_area_id,
                    day=valid_date,
                    snow_depth_cm_p50=70,
                )
                for valid_date in requested_dates
            )
        ),
        forecast_repository=_ForecastRepository(
            _forecast_rows(
                ski_area_ids=(ski_area_id,),
                requested_dates=requested_dates,
            )
        ),
        reference_time=datetime(2027, 1, 10, 0, tzinfo=UTC),
    )
    assert result.status == "available"
    assert result.evidence.mode == "climatology"
    assert result.evidence.forecast is None
    assert any(
        "stale" in limitation.lower() for limitation in result.evidence.limitations
    )


def test_candidate_generation_expands_each_applicable_pass_without_default_bias() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()
    records = generate_v4_candidate_records(
        graph=CatalogGraph.from_snapshot(snapshot),
        intent=SearchIntent(),
        trust_manifest=manifest,
    )

    pass_ids_by_access: dict[str, set[str]] = {}
    for record in records:
        pass_ids_by_access.setdefault(record.access.ski_area_access_id, set()).add(
            record.selected_pass.lift_pass_product_id
        )

    assert any(len(pass_ids) > 1 for pass_ids in pass_ids_by_access.values())
    assert len({record.candidate_id for record in records}) == len(records)
    graph = CatalogGraph.from_snapshot(snapshot)
    for record in records:
        expected = set(record.selected_pass.valid_ski_area_ids)
        for domain_id in record.selected_pass.terrain_domain_ids:
            expected.update(graph.domains_by_id[domain_id].ski_area_ids)
        assert record.pass_covered_ski_area_ids == tuple(sorted(expected))
        expected_domain_ids = set(record.selected_pass.terrain_domain_ids)
        expected_domain_ids.update(
            domain.terrain_domain_id
            for domain in snapshot.terrain_domains
            if record.ski_area.ski_area_id in domain.ski_area_ids
        )
        assert {domain.terrain_domain_id for domain in record.terrain_domains} == (
            expected_domain_ids
        )


def test_estimate_aware_lodging_and_hard_travel_limits_filter_before_scoring() -> None:
    snapshot, manifest = _catalog_and_trust()
    climatology = _ClimatologyRepository()
    forecast = _ForecastRepository()
    budget_result = search_trip_configurations(
        intent=_intent(
            lodging_budget=LodgingBudgetConstraint(
                mode="lodging_nightly",
                maximum=1,
                currency="EUR",
            )
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        include_refinements=False,
    )
    travel_result = search_trip_configurations(
        intent=SearchIntent(
            constraints=SearchConstraints(
                location=LocationScope(country="France"),
                travel_limit=TravelLimitConstraint(
                    maximum_duration_hours=1,
                    mode="car",
                ),
            ),
            travel_context=TravelContext(origin_text="Berlin", mode="car"),
        ),
        catalog_snapshot=snapshot,
        trust_manifest=manifest,
        climatology_repository=climatology,
        forecast_repository=forecast,
        include_refinements=False,
    )

    assert budget_result.eligible_candidate_count == 0
    assert budget_result.results == ()
    assert travel_result.eligible_candidate_count == 0
    assert travel_result.results == ()


def test_forecast_freshness_uses_provider_update_interval_and_consistency_delay() -> (
    None
):
    available = datetime(2027, 1, 1, 7, tzinfo=UTC)
    run = WeatherForecastRun(
        forecast_run_id="run",
        forecast_source_key="ecmwf_ifs025_ensemble_mean",
        provider_gateway="open-meteo",
        producer="ecmwf",
        provider_model_id="ifs025",
        forecast_kind="ensemble_mean",
        model_initialization_time=datetime(2027, 1, 1, tzinfo=UTC),
        provider_availability_time=available,
        ingested_at=available + timedelta(minutes=10),
        completed_at=available + timedelta(minutes=15),
        first_valid_date=date(2027, 1, 1),
        last_valid_date=date(2027, 1, 16),
        status="complete",
        schema_version="forecast-v1",
        parser_version="open-meteo-v1",
        aggregation_policy_version="local-day-v1",
        provider_metadata={"update_interval_seconds": 21_600},
    )

    assert forecast_run_is_fresh(
        run,
        available + timedelta(hours=6, minutes=9),
    )
    assert not forecast_run_is_fresh(
        run,
        available + timedelta(hours=6, minutes=11),
    )


def test_service_validates_intent_even_when_constraints_exclude_every_candidate() -> (
    None
):
    snapshot, manifest = _catalog_and_trust()

    with pytest.raises(ValueError, match="unknown factor ID"):
        search_trip_configurations(
            intent=SearchIntent(
                constraints=SearchConstraints(
                    location=LocationScope(country="Nowhere")
                ),
                factor_preferences=(
                    FactorPreferencePatch(
                        factor_id="invented",
                        mode="prefer",
                    ),
                ),
            ),
            catalog_snapshot=snapshot,
            trust_manifest=manifest,
            climatology_repository=_ClimatologyRepository(),
            forecast_repository=_ForecastRepository(),
            include_refinements=False,
        )

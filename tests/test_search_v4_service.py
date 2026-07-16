from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.data.audit_search_factor_readiness import DEFAULT_TRUST_MANIFEST_PATH
from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.domain import search_v4_service
from app.domain.catalog_graph import CatalogGraph
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement import (
    RefinementImpact,
    RefinementOption,
    RefinementProposal,
    RefinementVariantOutcome,
    ValidatedRefinementProposal,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    LocationScope,
    LodgingBudgetConstraint,
    PartyContext,
    SearchConstraints,
    SearchIntent,
    TravelContext,
    TravelLimitConstraint,
    TravelWindow,
)
from app.domain.search_v4_service import (
    SearchV4Response,
    forecast_run_is_fresh,
    generate_v4_candidate_records,
    search_trip_configurations,
)
from app.domain.weather_forecast import WeatherForecastRun

pytestmark = pytest.mark.db_free


class _ClimatologyRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_daily_rows_for_ski_areas_window(self, ski_area_ids, **kwargs):
        self.calls.append({"ski_area_ids": ski_area_ids, **kwargs})
        return {
            (ski_area_id, "mid", baseline): ()
            for ski_area_id in ski_area_ids
            for baseline in ("normal_30y", "recent_15y")
        }


class _ForecastRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_latest_daily_rows(self, **kwargs):
        self.calls.append(kwargs)
        return ()


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


def _validated_refinement(
    *outcomes: tuple[tuple[str, ...], frozenset[str]],
) -> ValidatedRefinementProposal:
    proposal = RefinementProposal(
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
            )
            for ordered_ids, eligible_ids in outcomes
        ),
    )


def _ordered_candidate(candidate_id: str, ski_region_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        record=SimpleNamespace(
            candidate_id=candidate_id,
            region=SimpleNamespace(ski_region_id=ski_region_id),
            constraint_facts=object(),
        ),
        evaluations=(),
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
    assert forecast.calls[0]["source_keys"] == (
        "ecmwf_ifs025_ensemble_mean",
        "ncep_gefs05_ensemble_mean",
    )
    assert len(forecast.calls[0]["ski_area_ids"]) == len(
        set(forecast.calls[0]["ski_area_ids"])
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

from app.data.compare_ranking import (
    build_factor_inputs_for_results,
    run_ranking_comparison_for_results,
)
from app.domain.models import (
    ConfidenceContributor,
    Destination,
    ExplanationItem,
    PisteKmByDifficulty,
    ProvenanceInfo,
    Rental,
    SearchExplanation,
    SearchResult,
    SkiArea,
    StayBase,
    TravelEffort,
)
from app.domain.ranking_comparison import (
    CandidateScoreBreakdown,
    FactorComparisonInput,
    candidate_score_for_result,
    compare_rankings,
)


def _explanation() -> SearchExplanation:
    return SearchExplanation(
        highlights=[ExplanationItem(label="Good trip fit.")],
        risks=[],
        confidence_contributors=[
            ConfidenceContributor(label="Stable evidence.", direction="positive")
        ],
    )


def _provenance() -> ProvenanceInfo:
    return ProvenanceInfo(
        source_name="test",
        source_type="forecast",
        updated_at="2026-06-22T10:00:00+00:00",
        freshness_status="fresh",
        basis_summary="Synthetic test provenance.",
    )


def _search_result(
    *,
    resort_id: str = "tignes",
    ski_area_id: str | None = None,
    stay_base_name: str = "Village Base",
    score: float = 2.5,
    quality: int = 2,
    lift_distance: str = "near",
    snow_confidence_score: float = 0.8,
    conditions_score: float = 0.75,
    budget_penalty: float = 0.0,
    travel_effort: TravelEffort | None = None,
) -> SearchResult:
    return SearchResult(
        resort_id=resort_id,
        resort_name=resort_id.replace("-", " ").title(),
        region="Test Alps",
        selected_ski_area_id=ski_area_id or f"{resort_id}-ski-area",
        selected_ski_area_name=f"{(ski_area_id or resort_id).title()} Ski Area",
        selected_stay_base_name=stay_base_name,
        selected_stay_base_lift_distance=lift_distance,
        stay_base_price_range="EUR 180-240",
        selected_area_name="Village Base",
        selected_area_lift_distance=lift_distance,
        area_price_range="EUR 180-240",
        rental_name="Rental Desk",
        rental_price_range="EUR 35-55",
        rating_estimate=quality,
        link="https://example.com",
        score=score,
        budget_penalty=budget_penalty,
        conditions_summary="Stable test conditions.",
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label="good",
        availability_status="open",
        conditions_score=conditions_score,
        conditions_provenance=_provenance(),
        explanation=_explanation(),
        recommendation_confidence=0.8,
        travel_effort=travel_effort,
    )


def _destination_with_factor_inputs() -> Destination:
    return Destination(
        resort_id="tignes",
        name="Tignes",
        country="France",
        region="French Alps",
        price_level="medium",
        latitude=45.47,
        longitude=6.9,
        base_elevation_m=1550,
        summit_elevation_m=3456,
        season_start_month=11,
        season_end_month=5,
        ski_areas=[
            SkiArea(
                ski_area_id="grande-motte",
                name="Grande Motte",
                latitude=45.47,
                longitude=6.9,
                base_elevation_m=2100,
                summit_elevation_m=3456,
                season_start_month=11,
                season_end_month=5,
                total_piste_km=300,
                total_lift_count=75,
                piste_km_by_difficulty=PisteKmByDifficulty(
                    beginner=170,
                    intermediate=78,
                    advanced=52,
                ),
            )
        ],
        stay_bases=[
            StayBase(
                stay_base_id="val-claret",
                name="Val Claret",
                price_range="EUR 180-260",
                price_min=180,
                price_max=260,
                quality="premium",
                lift_distance="near",
                supported_skill_levels=["intermediate", "advanced"],
                nearest_lift_name="Funiculaire Grande Motte",
                nearest_lift_distance_m=250,
                access_mode="walk",
            )
        ],
        rentals=[
            Rental(
                name="Rental Desk",
                price_range="EUR 35-55",
                price_min=35,
                price_max=55,
                quality="standard",
                lift_distance="near",
            )
        ],
    )


def test_candidate_score_keeps_trip_option_components_separate() -> None:
    result = _search_result(
        score=2.5,
        quality=2,
        lift_distance="near",
        snow_confidence_score=0.8,
        conditions_score=0.75,
        budget_penalty=0.0,
    )

    breakdown = candidate_score_for_result(
        result,
        terrain_scale="large",
        terrain_trust_cap=1.0,
        skill_fit=("intermediate", "advanced"),
        skill_trust_cap=1.0,
        stay_base_access="walkable",
        access_trust_cap=1.0,
    )

    assert isinstance(breakdown, CandidateScoreBreakdown)
    assert set(breakdown.components) == {
        "legacy_base",
        "terrain",
        "skill_fit",
        "stay_base_access",
        "snow_evidence",
        "conditions",
        "budget",
        "travel_effort",
    }
    assert breakdown.components["terrain"] > 0
    assert breakdown.components["skill_fit"] > 0
    assert breakdown.components["stay_base_access"] > 0
    assert breakdown.components["snow_evidence"] > 0
    assert breakdown.total == sum(breakdown.components.values())
    assert result.score == 2.5


def test_candidate_score_applies_trust_caps_without_weak_boost() -> None:
    result = _search_result(score=2.5)

    trusted = candidate_score_for_result(
        result,
        terrain_scale="mega",
        terrain_trust_cap=1.0,
        skill_fit=("intermediate",),
        skill_trust_cap=1.0,
        stay_base_access="walkable",
        access_trust_cap=1.0,
    )
    untrusted = candidate_score_for_result(
        result,
        terrain_scale="mega",
        terrain_trust_cap=0.0,
        skill_fit=("intermediate",),
        skill_trust_cap=0.0,
        stay_base_access="walkable",
        access_trust_cap=0.0,
    )

    assert trusted.total > untrusted.total
    assert untrusted.components["terrain"] == 0
    assert untrusted.components["skill_fit"] == 0
    assert untrusted.components["stay_base_access"] == 0


def _factor_inputs(
    *,
    terrain_scale: str = "medium",
    terrain_trust_cap: float = 1.0,
    skill_fit: tuple[str, ...] = ("intermediate",),
    skill_trust_cap: float = 1.0,
    access: str = "shuttle_easy",
    access_trust_cap: float = 1.0,
) -> FactorComparisonInput:
    return FactorComparisonInput(
        terrain_scale=terrain_scale,
        terrain_trust_cap=terrain_trust_cap,
        skill_fit=skill_fit,
        skill_trust_cap=skill_trust_cap,
        stay_base_access=access,
        access_trust_cap=access_trust_cap,
    )


def test_compare_rankings_reports_current_and_candidate_rank_delta() -> None:
    weak_current_top = _search_result(
        resort_id="legacy-top",
        score=3.0,
        quality=1,
        snow_confidence_score=0.35,
        conditions_score=0.35,
    )
    strong_candidate = _search_result(
        resort_id="candidate-top",
        score=2.8,
        quality=3,
        snow_confidence_score=0.9,
        conditions_score=0.85,
    )

    report = compare_rankings(
        [weak_current_top, strong_candidate],
        factor_inputs={
            "legacy-top": _factor_inputs(
                terrain_scale="small",
                skill_fit=("beginner",),
                access="car_recommended",
            ),
            "candidate-top": _factor_inputs(
                terrain_scale="mega",
                skill_fit=("intermediate", "advanced"),
                access="walkable",
            ),
        },
    )

    candidate_row = next(row for row in report.rows if row.resort_id == "candidate-top")

    assert candidate_row.current_rank == 2
    assert candidate_row.candidate_rank == 1
    assert candidate_row.rank_delta == -1
    assert candidate_row.current_score == 2.8
    assert candidate_row.candidate_score > 0
    assert "terrain" in candidate_row.top_candidate_components
    assert weak_current_top.score == 3.0
    assert strong_candidate.score == 2.8


def test_compare_rankings_keeps_trip_options_for_same_destination_separate() -> None:
    main_area = _search_result(
        resort_id="tignes",
        ski_area_id="tignes-main",
        stay_base_name="Le Lac",
        score=3.0,
    )
    glacier_area = _search_result(
        resort_id="tignes",
        ski_area_id="grande-motte",
        stay_base_name="Val Claret",
        score=2.8,
    )

    report = compare_rankings(
        [main_area, glacier_area],
        factor_inputs={
            "tignes--tignes-main--le-lac": _factor_inputs(terrain_scale="small"),
            "tignes--grande-motte--val-claret": _factor_inputs(
                terrain_scale="mega",
                access="walkable",
            ),
        },
    )

    assert len(report.rows) == 2
    assert {row.option_key for row in report.rows} == {
        "tignes--tignes-main--le-lac",
        "tignes--grande-motte--val-claret",
    }


def test_build_factor_inputs_for_results_uses_trip_option_key() -> None:
    result = _search_result(
        resort_id="tignes",
        ski_area_id="grande-motte",
        stay_base_name="Val Claret",
    )

    inputs = build_factor_inputs_for_results(
        [result],
        resorts=(_destination_with_factor_inputs(),),
    )

    factor_input = inputs["tignes--grande-motte--val-claret"]

    assert factor_input.terrain_scale == "mega"
    assert factor_input.terrain_trust_cap == 1.0
    assert factor_input.skill_fit == ("beginner", "intermediate", "advanced")
    assert factor_input.skill_trust_cap == 1.0
    assert factor_input.stay_base_access == "walkable"
    assert factor_input.access_trust_cap == 1.0


def test_run_ranking_comparison_for_results_writes_artifacts(tmp_path) -> None:
    result = _search_result(
        resort_id="tignes",
        ski_area_id="grande-motte",
        stay_base_name="Val Claret",
    )

    report = run_ranking_comparison_for_results(
        [result],
        resorts=(_destination_with_factor_inputs(),),
        output_dir=tmp_path,
    )

    assert report.rows[0].option_key == "tignes--grande-motte--val-claret"
    assert (tmp_path / "ranking-comparison-summary.json").exists()
    assert (tmp_path / "ranking-comparison-report.md").exists()

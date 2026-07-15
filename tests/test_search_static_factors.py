from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain.catalog import (
    ApresProfileFact,
    BaseCharacterFact,
    CatalogLiftPassPrice,
    CatalogPisteKmByDifficulty,
    LiftPassProduct,
    SkiArea,
    SkiAreaAccess,
    SkiRegion,
    SnowParkFact,
    StayBase,
    StayDestination,
)
from app.domain.search_factors.static import (
    NumericBounds,
    ResolvedCatalogEvidence,
    StaticEvaluationContext,
    StaticFactorCandidate,
    build_static_factor_registry,
    derive_numeric_bounds,
)
from app.domain.search_policy import load_search_policy
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    PartyContext,
    SearchIntent,
    SearchObjective,
)

pytestmark = pytest.mark.db_free


class VerifiedTrustResolver:
    def resolve(
        self, entity_type: str, entity_id: str, field_group: str
    ) -> ResolvedCatalogEvidence:
        return ResolvedCatalogEvidence(
            status="verified",
            source_refs=(
                f"https://example.com/{entity_type}/{entity_id}/{field_group}",
            ),
        )


class UntrustedNamedEntitiesResolver(VerifiedTrustResolver):
    def resolve(
        self, entity_type: str, entity_id: str, field_group: str
    ) -> ResolvedCatalogEvidence:
        if entity_id.startswith("untrusted-"):
            return ResolvedCatalogEvidence(status="needs_source", source_refs=())
        return super().resolve(entity_type, entity_id, field_group)


def _candidate() -> StaticFactorCandidate:
    region = SkiRegion(
        ski_region_id="region",
        name="Region",
        grouping_policy="trip_market",
    )
    destination = StayDestination(
        stay_destination_id="destination",
        name="Destination",
        country="France",
        region="Savoie",
        price_level="medium",
        latitude=45,
        longitude=6,
        trip_market_region_id="region",
    )
    base = StayBase(
        stay_base_id="base",
        stay_destination_id="destination",
        name="Base",
        price_range="EUR 150-250",
        price_min=150,
        price_max=250,
        quality="standard",
        base_type="village",
        base_character=BaseCharacterFact(
            development_style="traditional",
            local_pace="quiet",
        ),
        local_apres_profile=ApresProfileFact(
            availability="available",
            intensity="low_key",
        ),
    )
    area = SkiArea(
        ski_area_id="area",
        name="Area",
        latitude=45,
        longitude=6,
        base_elevation_m=1200,
        summit_elevation_m=2800,
        season_start_month=12,
        season_end_month=4,
        total_piste_km=100,
        total_lift_count=25,
        piste_km_by_difficulty=CatalogPisteKmByDifficulty(
            beginner=15,
            intermediate=20,
            advanced=65,
        ),
        supported_skill_levels=("beginner", "intermediate", "advanced"),
        snow_park=SnowParkFact(availability="available", park_count=1),
        ski_day_apres_profile=ApresProfileFact(
            availability="available",
            intensity="lively",
        ),
    )
    access = SkiAreaAccess(
        ski_area_access_id="access",
        stay_base_id="base",
        ski_area_id="area",
        access_mode="ski_bus",
        lift_distance="medium",
        duration_minutes=10,
        is_direct=True,
        source_urls=("https://example.com/access",),
    )
    selected_pass = LiftPassProduct(
        lift_pass_product_id="pass",
        name="Pass",
        validity_scope="single_ski_area",
        available_from_stay_destination_ids=("destination",),
        valid_ski_area_ids=("area",),
        prices=(
            CatalogLiftPassPrice(
                duration_days=6,
                audience="adult",
                amount=300,
                currency="EUR",
                price_kind="fixed",
                season_label="2026-2027",
                source_url="https://example.com/price",
            ),
        ),
    )
    return StaticFactorCandidate(
        region=region,
        destination=destination,
        stay_base=base,
        ski_area=area,
        access=access,
        selected_pass=selected_pass,
        terrain_domains=(),
        travel_duration_minutes=600,
        travel_evidence_cap=1,
    )


def _context(intent: SearchIntent) -> StaticEvaluationContext:
    return StaticEvaluationContext(
        intent=intent,
        policy=load_search_policy(),
        trust_resolver=VerifiedTrustResolver(),
        numeric_bounds={
            "accessible_terrain_scale": NumericBounds(minimum=0, maximum=200),
            "terrain_potential_scale": NumericBounds(minimum=0, maximum=200),
            "lift_network_scale": NumericBounds(minimum=0, maximum=50),
            "pass_price_per_day": NumericBounds(minimum=30, maximum=70),
            "pass_terrain_value": NumericBounds(minimum=0.1, maximum=0.5),
            "travel_effort": NumericBounds(minimum=300, maximum=900),
        },
        pass_duration_days=6,
        pass_audience="adult",
        pass_season_label="2026-2027",
    )


def test_party_skill_uses_balanced_share_and_amount_then_party_minimum() -> None:
    registry = build_static_factor_registry()
    evaluation = registry.get("party_skill_coverage").evaluate(
        _context(
            SearchIntent(party=PartyContext(skill_levels=("beginner", "advanced")))
        ),
        _candidate(),
    )

    assert evaluation.raw_utility == pytest.approx(0.675)
    assert evaluation.effective_evidence_cap == 1
    assert evaluation.explanation_inputs["fits_by_level"] == pytest.approx(
        {"beginner": 0.675, "advanced": 1}
    )


def test_numeric_and_access_evaluators_preserve_scope_and_trust() -> None:
    registry = build_static_factor_registry()
    context = _context(SearchIntent())
    terrain = registry.get("accessible_terrain_scale").evaluate(context, _candidate())
    access = registry.get("stay_base_access").evaluate(context, _candidate())

    assert terrain.raw_value == 100
    assert terrain.raw_utility == pytest.approx(0.5)
    assert terrain.scope == "ski_area_pass_terrain_domain"
    assert terrain.entity_ids == ("pass", "area")
    assert terrain.effective_evidence_cap == 1
    assert access.raw_utility == pytest.approx(0.7)


def test_positive_presence_distinguishes_verified_presence_and_unknown() -> None:
    registry = build_static_factor_registry()
    context = _context(
        SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="snow_park",
                    mode="prefer",
                ),
            )
        )
    )
    available = registry.get("snow_park").evaluate(context, _candidate())
    unknown_candidate = replace(
        _candidate(),
        ski_area=_candidate().ski_area.model_copy(
            update={"snow_park": SnowParkFact(availability="unknown")}
        ),
    )
    unknown = registry.get("snow_park").evaluate(context, unknown_candidate)

    assert available.raw_utility == 1
    assert unknown.raw_utility == 0.5
    assert "unknown" in unknown.warnings


def test_categorical_and_apres_qualifiers_match_requested_values() -> None:
    registry = build_static_factor_registry()
    context = _context(
        SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="local_pace",
                    mode="prefer",
                    values=("quiet",),
                ),
                FactorPreferencePatch(
                    factor_id="ski_day_apres",
                    mode="prefer",
                    values=("lively",),
                ),
            )
        )
    )

    assert registry.get("local_pace").evaluate(context, _candidate()).raw_utility == 1
    assert (
        registry.get("ski_day_apres").evaluate(context, _candidate()).raw_utility == 1
    )


def test_pass_objectives_use_comparable_price_slice() -> None:
    registry = build_static_factor_registry()
    context = _context(
        SearchIntent(
            objectives=(
                SearchObjective(factor_id="pass_price_per_day"),
                SearchObjective(factor_id="pass_terrain_value"),
            )
        )
    )

    price = registry.get("pass_price_per_day").evaluate(context, _candidate())
    value = registry.get("pass_terrain_value").evaluate(context, _candidate())

    assert price.raw_value == 50
    assert price.raw_utility == pytest.approx(0.5)
    assert value.raw_value == pytest.approx(1 / 3)
    assert value.raw_utility == pytest.approx((1 / 3 - 0.1) / 0.4)


def test_numeric_bounds_exclude_values_without_source_backed_evidence() -> None:
    trusted = _candidate()
    untrusted_area = trusted.ski_area.model_copy(
        update={
            "ski_area_id": "untrusted-area",
            "total_piste_km": 1_000,
            "total_lift_count": 200,
        }
    )
    untrusted_pass = trusted.selected_pass.model_copy(
        update={
            "lift_pass_product_id": "untrusted-pass",
            "valid_ski_area_ids": ("untrusted-area",),
        }
    )
    untrusted = replace(
        trusted,
        ski_area=untrusted_area,
        selected_pass=untrusted_pass,
    )

    bounds = derive_numeric_bounds(
        candidates=(trusted, untrusted),
        pass_duration_days=6,
        pass_audience="adult",
        pass_season_label="2026-2027",
        trust_resolver=UntrustedNamedEntitiesResolver(),
    )

    assert bounds["terrain_potential_scale"] == NumericBounds(100, 100)
    assert bounds["lift_network_scale"] == NumericBounds(25, 25)


def test_pass_price_bounds_do_not_compare_different_currencies() -> None:
    eur = _candidate()
    chf_price = eur.selected_pass.prices[0].model_copy(update={"currency": "CHF"})
    chf_pass = eur.selected_pass.model_copy(
        update={"lift_pass_product_id": "chf-pass", "prices": (chf_price,)}
    )
    chf = replace(eur, selected_pass=chf_pass)

    bounds = derive_numeric_bounds(
        candidates=(eur, chf),
        pass_duration_days=6,
        pass_audience="adult",
        pass_season_label="2026-2027",
        trust_resolver=VerifiedTrustResolver(),
    )

    assert "pass_price_per_day" not in bounds
    assert "pass_terrain_value" not in bounds


def test_pass_price_is_unresolved_when_multiple_seasons_are_ambiguous() -> None:
    candidate = _candidate()
    old_price = candidate.selected_pass.prices[0].model_copy(
        update={"amount": 270, "season_label": "2025-2026"}
    )
    ambiguous = replace(
        candidate,
        selected_pass=candidate.selected_pass.model_copy(
            update={"prices": (old_price, candidate.selected_pass.prices[0])}
        ),
    )
    context = replace(
        _context(
            SearchIntent(objectives=(SearchObjective(factor_id="pass_price_per_day"),))
        ),
        pass_season_label=None,
    )

    result = (
        build_static_factor_registry()
        .get("pass_price_per_day")
        .evaluate(
            context,
            ambiguous,
        )
    )

    assert result.raw_value is None
    assert result.effective_evidence_cap == 0


def test_static_registry_contains_every_non_weather_evaluator() -> None:
    registry = build_static_factor_registry()

    assert set(registry.factor_ids) == {
        factor.factor_id
        for factor in load_search_policy().factors_requiring_evaluators
        if factor.factor_id
        not in {
            "trip_window_snow_fit",
            "climatological_snow_reliability",
            "trip_window_snowpack_outlook",
        }
    }

from app.domain.models import (
    Destination,
    PisteKmByDifficulty,
    Rental,
    SkiArea,
    StayBase,
    TerrainDomain,
)
from app.domain.resort_fit import (
    accessible_terrain_factor_for_option,
    ranking_cap_for_trust_state,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
    terrain_scale_factor_for_ski_area,
    trust_state_for_manifest_status,
)


def _ski_area(
    *,
    total_piste_km: float | None = None,
    beginner: float | None = None,
    intermediate: float | None = None,
    advanced: float | None = None,
    summit_elevation_m: int = 2600,
) -> SkiArea:
    difficulty = None
    if beginner is not None and intermediate is not None and advanced is not None:
        difficulty = PisteKmByDifficulty(
            beginner=beginner,
            intermediate=intermediate,
            advanced=advanced,
        )
    return SkiArea(
        ski_area_id="test-ski-area",
        name="Test Ski Area",
        latitude=45.5,
        longitude=6.7,
        base_elevation_m=1200,
        summit_elevation_m=summit_elevation_m,
        season_start_month=12,
        season_end_month=4,
        total_piste_km=total_piste_km,
        total_lift_count=20,
        piste_km_by_difficulty=difficulty,
    )


def _stay_base(
    *,
    nearest_lift_distance_m: int | None = None,
    access_mode: str = "unknown",
    lift_distance: str = "medium",
) -> StayBase:
    return StayBase(
        stay_base_id="test-village",
        name="Test Village",
        price_range="EUR 150-220",
        price_min=150,
        price_max=220,
        quality="standard",
        lift_distance=lift_distance,
        supported_skill_levels=["beginner", "intermediate"],
        nearest_lift_distance_m=nearest_lift_distance_m,
        access_mode=access_mode,
    )


def _rental() -> Rental:
    return Rental(
        name="Test Rental",
        price_range="EUR 35-55",
        price_min=35,
        price_max=55,
        quality="standard",
        lift_distance="near",
    )


def _destination_with_tignes_val_disere_pass() -> Destination:
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
        lift_pass_products=[
            {
                "lift_pass_product_id": "tignes-val-disere-pass",
                "name": "Tignes - Val d'Isere",
                "validity_scope": "regional_network",
                "is_default": True,
                "valid_ski_area_ids": ["tignes-ski-area"],
                "terrain_domain_ids": ["tignes-val-disere"],
                "external_validity_summary": "Linked Tignes - Val d'Isere domain.",
            }
        ],
        ski_areas=[
            _ski_area(total_piste_km=None).model_copy(
                update={"ski_area_id": "tignes-ski-area", "name": "Tignes"}
            )
        ],
        stay_bases=[_stay_base()],
        rentals=[_rental()],
    )


def _tignes_val_disere_domain(*, total_piste_km: float) -> TerrainDomain:
    return TerrainDomain(
        terrain_domain_id="tignes-val-disere",
        name="Tignes - Val d'Isere",
        ski_area_refs=[
            {"resort_id": "tignes", "ski_area_id": "tignes-ski-area"},
            {"resort_id": "val-disere", "ski_area_id": "val-disere-ski-area"},
        ],
        total_piste_km=total_piste_km,
        total_lift_count=72,
        source_urls=["https://example.com/tignes-val-disere"],
    )


def _destination_with_chamonix_le_pass_group() -> Destination:
    return Destination(
        resort_id="chamonix-mont-blanc",
        name="Chamonix Mont-Blanc",
        country="France",
        region="French Alps",
        price_level="medium",
        latitude=45.92,
        longitude=6.86,
        base_elevation_m=1035,
        summit_elevation_m=3275,
        season_start_month=12,
        season_end_month=5,
        lift_pass_products=[
            {
                "lift_pass_product_id": "chamonix-le-pass",
                "name": "Chamonix Le Pass",
                "validity_scope": "local_multi_area",
                "is_default": True,
                "valid_ski_area_ids": ["brevent-flegere", "balme"],
            }
        ],
        ski_areas=[
            _ski_area(total_piste_km=56).model_copy(
                update={"ski_area_id": "brevent-flegere", "name": "Brevent-Flegere"}
            ),
            _ski_area(total_piste_km=44).model_copy(
                update={"ski_area_id": "balme", "name": "Balme"}
            ),
        ],
        terrain_groups=[
            {
                "terrain_group_id": "chamonix-le-pass-terrain",
                "name": "Chamonix Le Pass Terrain",
                "ski_area_ids": ["brevent-flegere", "balme"],
                "total_piste_km": 100,
                "total_lift_count": 23,
                "source_urls": ["https://example.com/chamonix-le-pass"],
            }
        ],
        stay_bases=[_stay_base()],
        rentals=[_rental()],
    )


def test_accessible_terrain_prefers_shared_domain_from_default_pass() -> None:
    destination = _destination_with_tignes_val_disere_pass()
    terrain_domains = (_tignes_val_disere_domain(total_piste_km=300),)

    factor = accessible_terrain_factor_for_option(
        destination=destination,
        selected_ski_area_id="tignes-ski-area",
        terrain_domains=terrain_domains,
    )

    assert factor.value == "mega"
    assert factor.scope == "ski_area"
    assert factor.entity_id == "tignes-ski-area"
    assert factor.raw_inputs["terrain_source_scope"] == "terrain_domain"
    assert factor.raw_inputs["terrain_source_id"] == "tignes-val-disere"
    assert (
        factor.raw_inputs["terrain_source_label"]
        == "shared-domain/pass-accessible terrain"
    )
    assert factor.raw_inputs["total_piste_km"] == 300
    assert factor.raw_inputs["total_lift_count"] == 72
    assert destination.ski_areas[0].total_piste_km is None


def test_accessible_terrain_uses_destination_group_from_default_pass() -> None:
    destination = _destination_with_chamonix_le_pass_group()

    factor = accessible_terrain_factor_for_option(
        destination=destination,
        selected_ski_area_id="brevent-flegere",
        terrain_domains=(),
    )

    assert factor.value == "medium"
    assert factor.raw_inputs["terrain_source_scope"] == "terrain_group"
    assert factor.raw_inputs["terrain_source_id"] == "chamonix-le-pass-terrain"
    assert (
        factor.raw_inputs["terrain_source_label"] == "aggregate/pass-accessible terrain"
    )
    assert factor.raw_inputs["total_piste_km"] == 100
    assert factor.raw_inputs["total_lift_count"] == 23


def test_terrain_scale_uses_source_backed_total_piste_km() -> None:
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=30)).value == "small"
    )
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=80)).value
        == "medium"
    )
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=180)).value
        == "large"
    )
    mega = terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=320))
    assert mega.value == "mega"
    assert mega.trust_state == "source_backed"
    assert mega.lifecycle_state == "active"


def test_terrain_scale_marks_missing_total_piste_km_as_needs_source() -> None:
    factor = terrain_scale_factor_for_ski_area(_ski_area())

    assert factor.value is None
    assert factor.trust_state == "needs_source"
    assert factor.lifecycle_state == "planned"
    assert factor.missing_inputs == ("total_piste_km",)


def test_skill_fit_profile_uses_piste_difficulty_mix() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=130,
            beginner=50,
            intermediate=55,
            advanced=25,
        )
    )

    assert factor.value == ("beginner", "intermediate")
    assert factor.trust_state == "source_backed"
    assert factor.lifecycle_state == "active"


def test_skill_fit_profile_uses_total_piste_for_intermediate_threshold() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=80,
            beginner=18,
            intermediate=2,
            advanced=1,
        )
    )

    assert factor.value == ("beginner", "intermediate")


def test_skill_fit_profile_can_mark_advanced_from_large_high_terrain() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=180,
            beginner=25,
            intermediate=20,
            advanced=5,
            summit_elevation_m=3000,
        )
    )

    assert factor.value == ("beginner", "intermediate", "advanced")


def test_skill_fit_profile_treats_zero_total_piste_as_present_value() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=0,
            beginner=190,
            intermediate=5,
            advanced=5,
            summit_elevation_m=3000,
        )
    )

    assert factor.value == ("beginner",)


def test_skill_fit_profile_requires_difficulty_mix_for_source_backed_profile() -> None:
    factor = skill_fit_factor_for_ski_area(_ski_area(total_piste_km=90))

    assert factor.value == ("intermediate",)
    assert factor.trust_state == "derived_from_partial_data"
    assert factor.missing_inputs == ("piste_km_by_difficulty",)


def test_stay_base_access_prefers_distance_and_access_mode() -> None:
    walkable = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="unknown")
    )
    shuttle = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=1200, access_mode="unknown")
    )
    car = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=2200, access_mode="unknown")
    )
    explicit_walk = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=2200, access_mode="walk")
    )
    explicit_bus = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="ski_bus")
    )
    explicit_car = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="car_recommended")
    )

    assert walkable.value == "walkable"
    assert shuttle.value == "shuttle_easy"
    assert car.value == "car_recommended"
    assert explicit_walk.value == "walkable"
    assert explicit_bus.value == "shuttle_easy"
    assert explicit_car.value == "car_recommended"
    assert walkable.trust_state == "source_backed"


def test_stay_base_access_falls_back_to_legacy_bucket_with_partial_trust() -> None:
    factor = stay_base_access_factor(_stay_base(lift_distance="near"))

    assert factor.value == "walkable"
    assert factor.trust_state == "derived_from_partial_data"
    assert factor.missing_inputs == ("nearest_lift_distance_m", "access_mode")


def test_trust_state_and_ranking_caps_map_current_manifest_statuses() -> None:
    assert trust_state_for_manifest_status("verified") == "source_backed"
    assert (
        trust_state_for_manifest_status("verified_with_adjustment") == "source_backed"
    )
    assert trust_state_for_manifest_status("estimated") == "manual_estimate"
    assert trust_state_for_manifest_status("needs_source") == "needs_source"
    assert trust_state_for_manifest_status(None) == "needs_source"

    assert ranking_cap_for_trust_state("source_backed") == 1.0
    assert ranking_cap_for_trust_state("derived_from_partial_data") == 0.7
    assert ranking_cap_for_trust_state("manual_estimate") == 0.25
    assert ranking_cap_for_trust_state("needs_source") == 0.0

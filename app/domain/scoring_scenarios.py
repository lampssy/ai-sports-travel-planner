from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.ranking_comparison import FactorAvailabilityState

ScenarioTodayStatus = Literal["executable", "proxy_only", "blocked_by_missing_data"]
PreferenceWeight = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ScoringScenario:
    scenario_id: str
    user_intent: str
    expected_today_status: ScenarioTodayStatus
    expected_today_winner_key: str | None
    hard_constraints: dict[str, str]
    weighted_preferences: dict[str, PreferenceWeight]
    expected_group_behavior: str
    factor_availability: dict[str, FactorAvailabilityState]
    missing_factor_notes: dict[str, str]
    target_behavior: str


def _scenario(
    *,
    scenario_id: str,
    user_intent: str,
    expected_today_status: ScenarioTodayStatus,
    expected_today_winner_key: str | None,
    hard_constraints: dict[str, str],
    weighted_preferences: dict[str, PreferenceWeight],
    expected_group_behavior: str,
    factor_availability: dict[str, FactorAvailabilityState],
    missing_factor_notes: dict[str, str],
    target_behavior: str,
) -> ScoringScenario:
    if expected_today_status == "executable" and expected_today_winner_key is None:
        raise ValueError(f"{scenario_id}: executable scenarios require a winner")
    return ScoringScenario(
        scenario_id=scenario_id,
        user_intent=user_intent,
        expected_today_status=expected_today_status,
        expected_today_winner_key=expected_today_winner_key,
        hard_constraints=hard_constraints,
        weighted_preferences=weighted_preferences,
        expected_group_behavior=expected_group_behavior,
        factor_availability=factor_availability,
        missing_factor_notes=missing_factor_notes,
        target_behavior=target_behavior,
    )


SCORING_SCENARIOS = [
    _scenario(
        scenario_id="snow_sure_late_season_intermediate",
        user_intent="Find a reliable late-season trip for intermediate skiers.",
        expected_today_status="executable",
        expected_today_winner_key="snow-sure-glacier--glacier-area--walkable-base",
        hard_constraints={
            "season": "late season",
            "skill_level": "intermediate",
        },
        weighted_preferences={
            "snow_reliability": "high",
            "terrain_scale": "medium",
            "open_piste_share": "low",
        },
        expected_group_behavior="Prefer the snow-sure glacier option over "
        "lower-altitude alternatives in the same result set.",
        factor_availability={
            "snow_reliability": "active_now",
            "season_fit": "active_now",
            "terrain_scale": "active_now",
            "open_piste_share": "future_candidate",
        },
        missing_factor_notes={
            "open_piste_share": "Would distinguish nominal terrain from terrain "
            "actually open late in the season.",
        },
        target_behavior="Use snow and season signals as the primary ranking driver "
        "while leaving open-piste coverage as future refinement.",
    ),
    _scenario(
        scenario_id="beginner_first_trip_low_hassle",
        user_intent="Choose an easy first ski trip with minimal logistics friction.",
        expected_today_status="executable",
        expected_today_winner_key="easy-beginner--learning-area--walkable-base",
        hard_constraints={
            "skill_level": "beginner",
            "access": "walkable base",
        },
        weighted_preferences={
            "skill_fit": "high",
            "stay_base_access": "high",
            "beginner_terrain": "medium",
            "ski_school_quality": "medium",
        },
        expected_group_behavior="Keep the learning-area option ahead of larger but "
        "less beginner-oriented terrain.",
        factor_availability={
            "skill_fit": "active_now",
            "stay_base_access": "active_now",
            "beginner_terrain": "proxy_only",
            "ski_school_quality": "known_missing",
            "beginner_package_availability": "future_candidate",
        },
        missing_factor_notes={
            "ski_school_quality": "No structured ski-school quality signal exists.",
            "beginner_package_availability": "Packages are a future enrichment "
            "candidate rather than a current scoring input.",
        },
        target_behavior="Reward beginner fit and low-friction base access before "
        "using package or ski-school attributes.",
    ),
    _scenario(
        scenario_id="family_children_mixed_confidence",
        user_intent="Find a family-friendly destination for children and mixed "
        "confidence levels.",
        expected_today_status="proxy_only",
        expected_today_winner_key="family-easy-access--main-area--walkable-base",
        hard_constraints={
            "party": "family with children",
            "access": "easy base access",
        },
        weighted_preferences={
            "skill_fit": "high",
            "stay_base_access": "high",
            "childcare": "medium",
            "family_rooms": "medium",
        },
        expected_group_behavior="Use base access and skill-fit proxies until "
        "family-specific lodging and childcare data exists.",
        factor_availability={
            "skill_fit": "active_now",
            "stay_base_access": "active_now",
            "childcare": "known_missing",
            "family_rooms": "future_candidate",
        },
        missing_factor_notes={
            "childcare": "Childcare availability is not modeled.",
            "family_rooms": "Family-room inventory is a future lodging factor.",
        },
        target_behavior="Surface family-ready results without overstating confidence "
        "from missing childcare data.",
    ),
    _scenario(
        scenario_id="advanced_big_terrain",
        user_intent="Prioritize a large advanced terrain domain.",
        expected_today_status="executable",
        expected_today_winner_key="advanced-domain--linked-domain--central-base",
        hard_constraints={
            "skill_level": "advanced",
            "terrain": "large linked domain",
        },
        weighted_preferences={
            "terrain_scale": "high",
            "skill_fit": "high",
            "terrain_domain": "medium",
            "lift_queue_time": "low",
        },
        expected_group_behavior="Group linked-domain options together and favor the "
        "advanced-capable central base.",
        factor_availability={
            "terrain_scale": "active_now",
            "skill_fit": "active_now",
            "terrain_domain": "near_term",
            "lift_queue_time": "known_missing",
        },
        missing_factor_notes={
            "lift_queue_time": "Queue time is not available for tie-breaking busy "
            "advanced terrain.",
        },
        target_behavior="Rank advanced terrain scale first, then refine with domain "
        "and lift-pressure signals as they mature.",
    ),
    _scenario(
        scenario_id="short_break_no_car",
        user_intent="Pick a compact short-break destination without needing a car.",
        expected_today_status="executable",
        expected_today_winner_key="compact-car-free--main-area--station-base",
        hard_constraints={
            "trip_length": "short break",
            "car": "not available",
        },
        weighted_preferences={
            "stay_base_access": "high",
            "travel_effort": "high",
            "bus_frequency": "medium",
            "transfer_reliability": "medium",
        },
        expected_group_behavior="Prefer the station-base option with low travel "
        "effort over car-dependent alternatives.",
        factor_availability={
            "stay_base_access": "active_now",
            "travel_effort": "active_now",
            "bus_frequency": "known_missing",
            "transfer_reliability": "future_candidate",
        },
        missing_factor_notes={
            "bus_frequency": "Structured local transit frequency is absent.",
            "transfer_reliability": "Reliability scoring is a future travel factor.",
        },
        target_behavior="Use current access and travel-effort signals for no-car "
        "short breaks without implying transit schedule precision.",
    ),
    _scenario(
        scenario_id="value_optimizer",
        user_intent="Maximize ski value across lodging budget and terrain size.",
        expected_today_status="proxy_only",
        expected_today_winner_key="balanced-value--main-area--standard-base",
        hard_constraints={
            "budget": "value-oriented",
            "terrain": "meaningful ski mileage",
        },
        weighted_preferences={
            "lodging_budget_fit": "high",
            "terrain_scale": "medium",
            "lift_pass_price": "medium",
            "total_trip_cost": "high",
        },
        expected_group_behavior="Favor balanced value over the absolute cheapest "
        "or largest terrain when current cost signals are incomplete.",
        factor_availability={
            "lodging_budget_fit": "active_now",
            "terrain_scale": "active_now",
            "lift_pass_price": "near_term",
            "lift_pass_price_per_km": "near_term",
            "total_trip_cost": "known_missing",
        },
        missing_factor_notes={
            "total_trip_cost": "End-to-end trip cost is not available yet.",
        },
        target_behavior="Treat lodging budget and terrain as current proxies until "
        "lift-pass and full-trip cost factors become reliable.",
    ),
    _scenario(
        scenario_id="crowd_averse_quiet_slopes",
        user_intent="Avoid queues and crowded slopes even if snow is reliable.",
        expected_today_status="blocked_by_missing_data",
        expected_today_winner_key=None,
        hard_constraints={
            "crowds": "quiet slopes preferred",
        },
        weighted_preferences={
            "snow_reliability": "medium",
            "crowding": "high",
            "lift_queue_time": "high",
            "review_derived_crowd_signal": "medium",
        },
        expected_group_behavior="Do not claim a deterministic winner until crowd "
        "or queue signals exist.",
        factor_availability={
            "snow_reliability": "active_now",
            "crowding": "known_missing",
            "lift_queue_time": "known_missing",
            "review_derived_crowd_signal": "future_candidate",
        },
        missing_factor_notes={
            "crowding": "Crowding level is not structured.",
            "lift_queue_time": "Lift queue time is not available.",
            "review_derived_crowd_signal": "Review-derived crowd evidence is a "
            "future candidate input.",
        },
        target_behavior="Block confident crowd-averse ranking until quiet-slope "
        "evidence can be represented.",
    ),
    _scenario(
        scenario_id="non_skier_partner",
        user_intent="Plan a ski trip that also works well for a non-skier partner.",
        expected_today_status="blocked_by_missing_data",
        expected_today_winner_key=None,
        hard_constraints={
            "party": "includes non-skier",
        },
        weighted_preferences={
            "stay_base_quality": "medium",
            "non_ski_activities": "high",
            "restaurants": "medium",
            "wellness": "medium",
        },
        expected_group_behavior="Avoid selecting a winner from ski-fit factors "
        "alone when non-ski suitability is the main intent.",
        factor_availability={
            "stay_base_quality": "proxy_only",
            "non_ski_activities": "known_missing",
            "restaurants": "known_missing",
            "wellness": "future_candidate",
        },
        missing_factor_notes={
            "non_ski_activities": "Non-ski activity coverage is not modeled.",
            "restaurants": "Restaurant depth and quality are not modeled.",
            "wellness": "Wellness facilities are a future enrichment candidate.",
        },
        target_behavior="Require explicit non-ski amenity evidence before ranking "
        "this scenario confidently.",
    ),
    _scenario(
        scenario_id="luxury_wellness_hotel_trip",
        user_intent="Find a snow-reliable premium hotel trip with wellness focus.",
        expected_today_status="blocked_by_missing_data",
        expected_today_winner_key=None,
        hard_constraints={
            "lodging": "luxury hotel",
            "amenity": "wellness or spa",
        },
        weighted_preferences={
            "snow_reliability": "medium",
            "stay_base_quality": "high",
            "hotel_spa": "high",
            "half_board": "medium",
        },
        expected_group_behavior="Do not let snow reliability alone choose a luxury "
        "wellness winner.",
        factor_availability={
            "snow_reliability": "active_now",
            "stay_base_quality": "proxy_only",
            "hotel_spa": "future_candidate",
            "half_board": "future_candidate",
        },
        missing_factor_notes={
            "hotel_spa": "Hotel spa facilities are not available as structured data.",
            "half_board": "Meal-plan availability is not available as structured data.",
        },
        target_behavior="Wait for hotel and wellness factors before making premium "
        "trip recommendations.",
    ),
    _scenario(
        scenario_id="late_booking_conditions_chaser",
        user_intent="Book late based on current ski conditions.",
        expected_today_status="proxy_only",
        expected_today_winner_key="fresh-conditions--main-area--walkable-base",
        hard_constraints={
            "booking_window": "late booking",
            "conditions": "current conditions matter",
        },
        weighted_preferences={
            "current_conditions": "high",
            "open_lifts": "medium",
            "open_pistes": "medium",
            "recent_snowfall": "medium",
        },
        expected_group_behavior="Use current conditions as the best available "
        "proxy while live operations data remains unavailable.",
        factor_availability={
            "current_conditions": "active_now",
            "open_lifts": "known_missing",
            "open_pistes": "known_missing",
            "recent_snowfall": "future_candidate",
        },
        missing_factor_notes={
            "open_lifts": "Open-lift counts are not integrated.",
            "open_pistes": "Open-piste counts are not integrated.",
            "recent_snowfall": "Recent snowfall feed is a future candidate.",
        },
        target_behavior="Support late-booking diagnostics with current-condition "
        "proxies, clearly short of live operations scoring.",
    ),
    _scenario(
        scenario_id="mixed_skill_group",
        user_intent="Choose a destination that works for mixed skier abilities.",
        expected_today_status="proxy_only",
        expected_today_winner_key="mixed-skill-balanced--main-area--central-base",
        hard_constraints={
            "party": "mixed skill group",
        },
        weighted_preferences={
            "skill_fit": "high",
            "terrain_scale": "medium",
            "difficulty_mix": "high",
            "terrain_connectivity": "medium",
        },
        expected_group_behavior="Favor balanced terrain breadth over a narrow "
        "single-skill match.",
        factor_availability={
            "skill_fit": "active_now",
            "terrain_scale": "active_now",
            "difficulty_mix": "near_term",
            "terrain_connectivity": "known_missing",
        },
        missing_factor_notes={
            "terrain_connectivity": "Inter-skill terrain connectivity is not modeled.",
        },
        target_behavior="Use current skill and terrain proxies until difficulty mix "
        "and connectivity can separate better group-fit options.",
    ),
    _scenario(
        scenario_id="shared_domain_multi_ski_area_grouping",
        user_intent="Compare ski areas that share the same broader terrain domain.",
        expected_today_status="executable",
        expected_today_winner_key="tignes-domain--tignes-ski-area--val-claret",
        hard_constraints={
            "domain": "shared multi-area ski domain",
        },
        weighted_preferences={
            "result_group_key": "high",
            "terrain_domain": "medium",
            "nested_alternatives": "medium",
        },
        expected_group_behavior="Group sibling ski-area results under the shared "
        "domain while preserving the selected stay-base option.",
        factor_availability={
            "result_group_key": "active_now",
            "terrain_domain": "near_term",
            "nested_alternatives": "known_missing",
        },
        missing_factor_notes={
            "nested_alternatives": "Nested same-domain alternatives are not yet "
            "represented in the result surface.",
        },
        target_behavior="Exercise grouping diagnostics for shared-domain results "
        "without changing production search behavior.",
    ),
]

SCORING_SCENARIOS_BY_ID: dict[str, ScoringScenario] = {
    scenario.scenario_id: scenario for scenario in SCORING_SCENARIOS
}

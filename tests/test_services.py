from app.domain.models import SearchFilters
from app.domain.search_service import search_resorts


def test_recommend_activities_returns_matching_activities() -> None:
    from app.domain.services import recommend_activities

    activities = recommend_activities(
        sport="ski",
        region="Alps",
        difficulty="beginner",
    )

    assert len(activities) == 1
    assert activities[0].name == "Alpine Start"
    assert activities[0].sport == "ski"
    assert activities[0].region == "Alps"
    assert activities[0].difficulty == "beginner"


def test_recommend_activities_filters_by_difficulty() -> None:
    from app.domain.services import recommend_activities

    activities = recommend_activities(
        sport="ski",
        region="Alps",
        difficulty="advanced",
    )

    assert len(activities) == 1
    assert all(activity.difficulty == "advanced" for activity in activities)
    assert all(activity.name != "Alpine Start" for activity in activities)


def test_recommend_activities_returns_empty_list_when_no_match() -> None:
    from app.domain.services import recommend_activities

    activities = recommend_activities(
        sport="windsurf",
        region="Baltic",
        difficulty="advanced",
    )

    assert activities == []


def test_recommend_activities_filters_by_region() -> None:
    from app.domain.services import recommend_activities

    activities = recommend_activities(
        sport="windsurf",
        region="Atlantic",
        difficulty="intermediate",
    )

    assert len(activities) == 1
    assert all(activity.region == "Atlantic" for activity in activities)
    assert all(activity.name != "Baltic Breeze" for activity in activities)


def test_search_resorts_matches_location_case_insensitively() -> None:
    results = search_resorts(
        SearchFilters(
            location="france",
            min_price=150,
            max_price=260,
            stars=2,
            skill_level="intermediate",
        )
    )

    assert results
    assert all("france" in result.link.lower() for result in results)
    assert all(result.conditions_summary for result in results)
    assert all(result.recommendation_reasons for result in results)
    assert all(
        result.snow_confidence_label in {"poor", "fair", "good"} for result in results
    )


def test_search_resorts_excludes_unsuitable_skill_levels() -> None:
    results = search_resorts(
        SearchFilters(
            location="Switzerland",
            min_price=200,
            max_price=320,
            stars=2,
            skill_level="beginner",
        )
    )

    assert results == []


def test_search_resorts_uses_lift_distance_filter_and_ranking() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=260,
            stars=1,
            skill_level="intermediate",
            lift_distance="near",
        )
    )

    assert results
    assert all(result.selected_area_lift_distance == "near" for result in results)
    assert results[0].selected_area_name == "Pine Chalet Zone"


def test_search_resorts_allows_budget_flex_with_penalty() -> None:
    strict_results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=90,
            max_price=110,
            stars=2,
            skill_level="intermediate",
        )
    )
    flex_results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=90,
            max_price=110,
            stars=2,
            skill_level="intermediate",
            budget_flex=0.2,
        )
    )

    assert strict_results == []
    assert [result.resort_name for result in flex_results] == ["Tyrol Summit"]
    assert flex_results[0].budget_penalty > 0


def test_search_resorts_returns_stable_descending_order() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            lift_distance="medium",
        )
    )

    assert [result.resort_name for result in results] == [
        "Alpine Horizon",
        "Mont Blanc Escape",
        "Savoy Snowfield",
    ]
    assert results[0].score > results[1].score > results[2].score


def test_search_resorts_includes_confidence_and_tradeoff_summary() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert results
    top_result = results[0]
    assert 0 <= top_result.recommendation_confidence <= 1
    assert top_result.tradeoff_summary
    assert 0 <= top_result.snow_confidence_score <= 1
    assert any(
        "snow" in reason.lower() or "conditions" in reason.lower()
        for reason in top_result.recommendation_reasons
    )


def test_search_resorts_uses_conditions_signal_in_ranking() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert [result.resort_name for result in results[:2]] == [
        "Alpine Horizon",
        "Mont Blanc Escape",
    ]
    assert results[0].conditions_score >= results[1].conditions_score
    assert results[0].snow_confidence_score >= results[1].snow_confidence_score


def test_search_resorts_excludes_out_of_season_resorts() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=110,
            max_price=180,
            stars=1,
            skill_level="beginner",
        )
    )

    assert all(result.resort_name != "Pyrenees Drift" for result in results)


def test_search_resorts_keeps_temporarily_closed_resorts_with_penalty() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=140,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        )
    )

    savoy = next(
        result for result in results if result.resort_name == "Savoy Snowfield"
    )

    assert savoy.availability_status == "temporarily_closed"
    assert "temporary closure" in savoy.tradeoff_summary.lower()
    assert any(
        "temporarily closed" in reason.lower()
        for reason in savoy.recommendation_reasons
    )


def test_search_resorts_falls_back_when_conditions_are_missing(monkeypatch) -> None:
    class EmptyConditionsProvider:
        def get_conditions_for_resort(self, resort_name: str) -> None:
            return None

    monkeypatch.setattr(
        "app.domain.search_service.get_conditions_provider",
        lambda: EmptyConditionsProvider(),
    )

    results = search_resorts(
        SearchFilters(
            location="Austria",
            min_price=90,
            max_price=220,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert results
    assert (
        results[0].conditions_summary
        == "No live conditions signal available for this resort."
    )
    assert results[0].snow_confidence_label == "fair"
    assert results[0].availability_status == "limited"


def test_search_resorts_returns_empty_list_when_no_resorts_match() -> None:
    results = search_resorts(
        SearchFilters(
            location="Italy",
            min_price=100,
            max_price=150,
            stars=3,
            skill_level="advanced",
        )
    )

    assert results == []

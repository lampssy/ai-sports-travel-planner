from app.domain.services import recommend_activities, search_resorts


def test_recommend_activities_returns_matching_activities() -> None:
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
    activities = recommend_activities(
        sport="ski",
        region="Alps",
        difficulty="advanced",
    )

    assert len(activities) == 1
    assert all(activity.difficulty == "advanced" for activity in activities)
    assert all(activity.name != "Alpine Start" for activity in activities)


def test_recommend_activities_returns_empty_list_when_no_match() -> None:
    activities = recommend_activities(
        sport="windsurf",
        region="Baltic",
        difficulty="advanced",
    )

    assert activities == []


def test_recommend_activities_filters_by_region() -> None:
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
        location="austria",
        min_price=150,
        max_price=220,
        stars=2,
    )

    assert results
    assert all("austria" in result.link.lower() for result in results)


def test_search_resorts_maps_stars_to_minimum_quality() -> None:
    results = search_resorts(
        location="Austria",
        min_price=150,
        max_price=260,
        stars=3,
    )

    assert results
    assert all(result.rating_estimate >= 3 for result in results)


def test_search_resorts_filters_out_resorts_below_requested_quality() -> None:
    results = search_resorts(
        location="Switzerland",
        min_price=180,
        max_price=320,
        stars=3,
    )

    assert [result.resort_name for result in results] == ["Matterhorn Peak"]


def test_search_resorts_filters_by_package_price() -> None:
    results = search_resorts(
        location="Austria",
        min_price=150,
        max_price=220,
        stars=2,
    )

    assert [result.resort_name for result in results] == ["Tyrol Summit"]


def test_search_resorts_returns_sorted_top_three_results() -> None:
    results = search_resorts(
        location="France",
        min_price=160,
        max_price=320,
        stars=1,
    )

    assert len(results) == 3
    assert [result.resort_name for result in results] == [
        "Alpine Horizon",
        "Mont Blanc Escape",
        "Savoy Snowfield",
    ]
    assert results[0].score > results[1].score > results[2].score


def test_search_resorts_returns_empty_list_when_no_resorts_match() -> None:
    results = search_resorts(
        location="Italy",
        min_price=100,
        max_price=150,
        stars=3,
    )

    assert results == []

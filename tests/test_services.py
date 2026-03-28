from app.domain.services import recommend_activities


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

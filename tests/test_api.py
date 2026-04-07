from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_recommend_activities_rejects_invalid_sport() -> None:
    response = client.get(
        "/recommend-activities",
        params={
            "sport": "cycling",
            "region": "Alps",
            "difficulty": "beginner",
        },
    )

    assert response.status_code == 422


def test_search_returns_ranked_results_with_new_filters() -> None:
    response = client.get(
        "/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "lift_distance": "medium",
            "budget_flex": 0.1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert payload["results"][0]["selected_area_lift_distance"] in {"near", "medium"}
    assert payload["results"][0]["budget_penalty"] >= 0
    assert payload["results"][0]["conditions_summary"]
    assert 0 <= payload["results"][0]["snow_confidence_score"] <= 1
    assert payload["results"][0]["snow_confidence_label"] in {"poor", "fair", "good"}
    assert payload["results"][0]["availability_status"] in {
        "open",
        "limited",
        "temporarily_closed",
        "out_of_season",
    }
    assert payload["results"][0]["explanation"]["highlights"]
    assert payload["results"][0]["recommendation_confidence"] >= 0
    assert payload["results"][0]["resort_id"]
    assert payload["results"][0]["region"]


def test_search_rejects_invalid_skill_level() -> None:
    response = client.get(
        "/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 2,
            "skill_level": "expert",
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_lift_distance() -> None:
    response = client.get(
        "/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 2,
            "skill_level": "intermediate",
            "lift_distance": "walkable",
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_budget_flex() -> None:
    response = client.get(
        "/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 2,
            "skill_level": "intermediate",
            "budget_flex": 0.6,
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_price_interval() -> None:
    response = client.get(
        "/search",
        params={
            "location": "Austria",
            "min_price": 250,
            "max_price": 200,
            "stars": 2,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 422


def test_parse_query_returns_structured_filters_and_confidence() -> None:
    response = client.post(
        "/parse-query",
        json={"query": "cheap france ski trip close to lift for intermediate"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "filters" in payload
    assert "confidence" in payload
    assert "unknown_parts" in payload
    assert 0 <= payload["confidence"] <= 1


def test_search_contract_returns_required_semantic_fields() -> None:
    response = client.get(
        "/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert "recommendation_reasons" not in result
    assert "tradeoff_summary" not in result
    assert result["explanation"]["highlights"]
    assert isinstance(result["explanation"]["risks"], list)
    assert result["explanation"]["confidence_contributors"]
    assert {
        contributor["direction"]
        for contributor in result["explanation"]["confidence_contributors"]
    } <= {"positive", "negative"}
    assert 0 <= result["conditions_score"] <= 1
    assert 0 <= result["snow_confidence_score"] <= 1
    assert result["snow_confidence_label"] in {"poor", "fair", "good"}
    assert result["availability_status"] in {
        "open",
        "limited",
        "temporarily_closed",
        "out_of_season",
    }
    assert 0 <= result["recommendation_confidence"] <= 1
    assert result["budget_penalty"] >= 0

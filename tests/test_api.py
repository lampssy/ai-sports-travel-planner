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


def test_search_returns_ranked_results() -> None:
    response = client.get(
        "/search",
        params={
            "location": "France",
            "min_price": 160,
            "max_price": 320,
            "stars": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 3
    assert payload["results"][0]["resort_name"] == "Alpine Horizon"
    assert "selected_area_name" in payload["results"][0]
    assert "rental_name" in payload["results"][0]


def test_search_rejects_invalid_stars() -> None:
    response = client.get(
        "/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 4,
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
        },
    )

    assert response.status_code == 422

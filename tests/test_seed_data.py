from app.data.loader import load_resorts


def test_all_seeded_resorts_have_stable_metadata() -> None:
    resorts = load_resorts()

    assert resorts
    assert all(resort.resort_id for resort in resorts)
    assert all(resort.region for resort in resorts)
    assert all(resort.latitude for resort in resorts)
    assert all(resort.longitude for resort in resorts)
    assert all(
        resort.summit_elevation_m > resort.base_elevation_m for resort in resorts
    )
    assert all(1 <= resort.season_start_month <= 12 for resort in resorts)
    assert all(1 <= resort.season_end_month <= 12 for resort in resorts)
    assert 20 <= len(resorts) <= 30


def test_seeded_resorts_cover_multiple_alpine_countries() -> None:
    resorts = load_resorts()
    countries = {resort.country for resort in resorts}

    assert countries == {"Austria", "France", "Italy", "Switzerland"}


def test_seed_data_supports_coherent_france_ranking_demo() -> None:
    resorts = {resort.name: resort for resort in load_resorts()}

    tignes = resorts["Tignes"]
    la_plagne = resorts["La Plagne"]

    assert tignes.region == "Savoie"
    assert la_plagne.region == "Savoie"
    assert any("intermediate" in area.supported_skill_levels for area in tignes.areas)
    assert any(
        "intermediate" in area.supported_skill_levels for area in la_plagne.areas
    )

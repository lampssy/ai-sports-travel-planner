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
    assert any(
        "intermediate" in stay_base.supported_skill_levels
        for stay_base in tignes.stay_bases
    )
    assert any(
        "intermediate" in stay_base.supported_skill_levels
        for stay_base in la_plagne.stay_bases
    )


def test_seeded_area_names_do_not_use_known_placeholder_labels() -> None:
    resorts = load_resorts()
    placeholder_names = {
        "Centre Village",
        "Dorf Core",
        "Galzig Base",
        "Giggijoch Quarter",
        "Hahnenkamm Side",
        "Penken Base",
        "Matterhorn Village",
        "Jakobshorn Base",
        "Terminal Side",
        "Corso Italia Stay",
        "Mottolino Side",
        "Ortisei Core",
        "Breuil Base",
        "Corvara Core",
    }

    assert all(
        stay_base.name not in placeholder_names
        for resort in resorts
        for stay_base in resort.stay_bases
    )


def test_seed_data_includes_new_glacier_validation_destinations() -> None:
    resorts = {resort.resort_id: resort for resort in load_resorts()}

    assert "hintertux" in resorts
    assert "stubai-glacier" in resorts
    assert "zell-am-see-kaprun" in resorts

    zell_kaprun = resorts["zell-am-see-kaprun"]
    assert {ski_area.name for ski_area in zell_kaprun.ski_areas} == {
        "Kitzsteinhorn",
        "Maiskogel",
        "Schmittenhoehe",
    }
    assert {stay_base.name for stay_base in zell_kaprun.stay_bases} == {
        "Kaprun",
        "Zell am See",
    }


def test_seed_data_uses_real_rental_names_for_current_destinations() -> None:
    resorts = {resort.resort_id: resort for resort in load_resorts()}

    expected_rentals = {
        "chamonix-mont-blanc": "Cham'Sport",
        "val-disere": "Val Ski Shop",
        "tignes": "Tignes Spirit",
        "les-arcs": "INTERSPORT Le Chantel - Edenarc Arc 1800",
        "la-plagne": "INTERSPORT Plagne Centre",
        "st-anton-am-arlberg": "Intersport Arlberg Shop St. Anton",
        "ischgl": "Ischgl Rent / Shop Zentrum",
        "solden": "Grizzly Sports",
        "kitzbuhel": "element3 - Sport Noichl",
        "saalbach-hinterglemm": "Sport Hagleitner",
        "mayrhofen": "MANNI Rental",
        "zermatt": "Glacier Sport Zermatt",
        "verbier": "Mountain Air",
        "st-moritz": "Ski Service Corvatsch St. Moritz Dorf",
        "davos-klosters": "Bardill Sport Shop Davos",
        "laax": "LAAX Rental",
        "grindelwald-wengen": "Buri Sport Grindelwald",
        "cortina-dampezzo": "Cortina Pro Sport",
        "madonna-di-campiglio": "Ski Rent Campiglio",
        "livigno": "Silene Sport Livigno",
        "val-gardena": "Everestski Ortisei",
        "cervinia": "WhiteRent",
        "alta-badia": "Marcello Varallo Sport",
        "hintertux": "INTERSPORT Hintertux",
        "stubai-glacier": "Intersport Okay Stubai Glacier",
        "zell-am-see-kaprun": "Bründl Sports Kitzsteinhorn Alpincenter",
    }

    assert {
        resort_id: resorts[resort_id].rentals[0].name for resort_id in expected_rentals
    } == expected_rentals

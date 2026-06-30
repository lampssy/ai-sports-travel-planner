import json
from pathlib import Path

from app.data.loader import load_resorts, load_terrain_domains


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
    assert len(resorts) >= 20


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


def test_seed_data_models_campiglio_as_three_destinations_and_one_domain() -> None:
    resorts = {resort.resort_id: resort for resort in load_resorts()}
    domains = {domain.terrain_domain_id: domain for domain in load_terrain_domains()}

    assert {
        "madonna-di-campiglio",
        "pinzolo",
        "folgarida-marilleva",
    } <= resorts.keys()
    assert {
        ski_area.ski_area_id for ski_area in resorts["madonna-di-campiglio"].ski_areas
    } == {"madonna-di-campiglio-ski-area"}
    assert {ski_area.ski_area_id for ski_area in resorts["pinzolo"].ski_areas} == {
        "pinzolo-ski-area"
    }
    assert {
        ski_area.ski_area_id for ski_area in resorts["folgarida-marilleva"].ski_areas
    } == {"folgarida-marilleva-ski-area"}

    domain = domains["campiglio-dolomiti-di-brenta"]
    assert {(ref.resort_id, ref.ski_area_id) for ref in domain.ski_area_refs} == {
        ("madonna-di-campiglio", "madonna-di-campiglio-ski-area"),
        ("pinzolo", "pinzolo-ski-area"),
        ("folgarida-marilleva", "folgarida-marilleva-ski-area"),
    }
    assert domain.total_piste_km == 156
    assert all(
        ski_area.total_piste_km != 156
        for resort_id in (
            "madonna-di-campiglio",
            "pinzolo",
            "folgarida-marilleva",
        )
        for ski_area in resorts[resort_id].ski_areas
    )


def test_seed_data_models_campiglio_pass_scope() -> None:
    resorts = {resort.resort_id: resort for resort in load_resorts()}
    local_ski_area_ids = {
        "madonna-di-campiglio": "madonna-di-campiglio-ski-area",
        "pinzolo": "pinzolo-ski-area",
        "folgarida-marilleva": "folgarida-marilleva-ski-area",
    }
    shared_product_common_facts = {}

    for resort_id, ski_area_id in local_ski_area_ids.items():
        products = resorts[resort_id].lift_pass_products
        default_products = [product for product in products if product.is_default]

        assert len(default_products) == 1
        shared_product = default_products[0]
        assert shared_product.lift_pass_product_id == (
            f"{resort_id}-campiglio-skiarea-pass"
        )
        assert shared_product.name == "Campiglio Dolomiti di Brenta Skiarea Skipass"
        assert shared_product.validity_scope == "regional_network"
        assert shared_product.valid_ski_area_ids == [ski_area_id]
        assert shared_product.terrain_domain_ids == ["campiglio-dolomiti-di-brenta"]
        assert "Pejo" in shared_product.external_validity_summary
        assert "disconnected" in shared_product.external_validity_summary.lower()
        common_facts = shared_product.model_dump(
            exclude={"lift_pass_product_id", "valid_ski_area_ids"}
        )
        common_facts["terrain_domain_ids"] = sorted(common_facts["terrain_domain_ids"])
        common_facts["prices"] = sorted(
            common_facts["prices"],
            key=lambda price: json.dumps(price, sort_keys=True),
        )
        shared_product_common_facts[resort_id] = common_facts

    expected_common_facts = shared_product_common_facts["madonna-di-campiglio"]
    for resort_id, common_facts in shared_product_common_facts.items():
        assert common_facts == expected_common_facts, resort_id

    assert len(resorts["madonna-di-campiglio"].lift_pass_products) == 1
    for resort_id in ("pinzolo", "folgarida-marilleva"):
        local_products = [
            product
            for product in resorts[resort_id].lift_pass_products
            if not product.is_default
        ]
        assert len(local_products) == 1
        assert local_products[0].validity_scope == "single_ski_area"
        assert local_products[0].valid_ski_area_ids == [local_ski_area_ids[resort_id]]
        assert local_products[0].terrain_domain_ids == []
        assert local_products[0].external_validity_summary is None


def test_campiglio_seed_uses_price_range_as_canonical_input() -> None:
    catalog = json.loads(Path("app/data/resorts.json").read_text())
    campiglio_resort_ids = {
        "madonna-di-campiglio",
        "pinzolo",
        "folgarida-marilleva",
    }

    for resort in catalog:
        if resort["resort_id"] not in campiglio_resort_ids:
            continue
        for priced_item in [*resort["rentals"], *resort["stay_bases"]]:
            assert "price_range" in priced_item
            assert "price_min" not in priced_item
            assert "price_max" not in priced_item


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
        "madonna-di-campiglio": "Campiglio Ski Rent - Lorenzetti",
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

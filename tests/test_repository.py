from app.data.database import bootstrap_database, connect
from app.data.repositories import ResortConditionsRepository, ResortRepository
from app.domain.models import SearchFilters
from app.domain.search_service import search_resorts


def test_bootstrap_database_creates_schema_and_seeds_data() -> None:
    bootstrap_database()

    with connect() as connection:
        resort_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resorts"
        ).fetchone()["count"]
        ski_area_count = connection.execute(
            "SELECT COUNT(*) AS count FROM ski_areas"
        ).fetchone()["count"]
        stay_base_count = connection.execute(
            "SELECT COUNT(*) AS count FROM stay_bases"
        ).fetchone()["count"]
        rental_count = connection.execute(
            "SELECT COUNT(*) AS count FROM rentals"
        ).fetchone()["count"]
        conditions_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resort_conditions"
        ).fetchone()["count"]

    assert 20 <= resort_count <= 30
    assert ski_area_count > 0
    assert stay_base_count > 0
    assert rental_count > 0
    assert conditions_count == 0


def test_resort_repository_returns_nested_models() -> None:
    repository = ResortRepository()

    resorts = repository.list_resorts()
    chamonix = next(
        resort for resort in resorts if resort.name == "Chamonix Mont-Blanc"
    )

    assert chamonix.resort_id == "chamonix-mont-blanc"
    assert chamonix.region == "Haute-Savoie"
    assert chamonix.latitude > 0
    assert chamonix.summit_elevation_m > chamonix.base_elevation_m
    assert chamonix.stay_bases
    assert chamonix.ski_areas
    assert chamonix.rentals
    assert chamonix.stay_bases[0].supported_skill_levels


def test_conditions_repository_returns_none_before_refresh() -> None:
    repository = ResortConditionsRepository()

    conditions = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert conditions is None


def test_bootstrap_keeps_conditions_table_empty_in_fresh_database() -> None:
    bootstrap_database()
    bootstrap_database()

    with connect() as connection:
        conditions_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resort_conditions"
        ).fetchone()["count"]

    assert conditions_count == 0


def test_search_resorts_works_with_postgres_backed_repositories() -> None:
    resorts = ResortRepository()
    conditions = ResortConditionsRepository()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        resorts=resorts.list_resorts(),
        conditions_provider=conditions,
    )

    assert results
    assert (
        results[0].conditions_summary
        == "No live conditions signal available for this ski area."
    )

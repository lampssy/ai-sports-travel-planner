from app.data.database import bootstrap_database, connect
from app.data.repositories import ResortConditionsRepository, ResortRepository
from app.domain.models import SearchFilters
from app.domain.search_service import search_resorts


def test_bootstrap_database_creates_schema_and_seeds_data(tmp_path) -> None:
    db_path = tmp_path / "planner.db"

    bootstrap_database(db_path)

    with connect(db_path) as connection:
        resort_count = connection.execute("SELECT COUNT(*) FROM resorts").fetchone()[0]
        area_count = connection.execute("SELECT COUNT(*) FROM areas").fetchone()[0]
        rental_count = connection.execute("SELECT COUNT(*) FROM rentals").fetchone()[0]
        conditions_count = connection.execute(
            "SELECT COUNT(*) FROM resort_conditions"
        ).fetchone()[0]

    assert 20 <= resort_count <= 30
    assert area_count > 0
    assert rental_count > 0
    assert conditions_count == 0


def test_resort_repository_returns_nested_models(tmp_path) -> None:
    repository = ResortRepository(tmp_path / "planner.db")

    resorts = repository.list_resorts()
    chamonix = next(
        resort for resort in resorts if resort.name == "Chamonix Mont-Blanc"
    )

    assert chamonix.resort_id == "chamonix-mont-blanc"
    assert chamonix.region == "Haute-Savoie"
    assert chamonix.latitude > 0
    assert chamonix.summit_elevation_m > chamonix.base_elevation_m
    assert chamonix.areas
    assert chamonix.rentals
    assert chamonix.areas[0].supported_skill_levels


def test_conditions_repository_returns_none_before_refresh(tmp_path) -> None:
    repository = ResortConditionsRepository(tmp_path / "planner.db")

    conditions = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert conditions is None


def test_bootstrap_keeps_conditions_table_empty_in_fresh_database(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    bootstrap_database(db_path)
    bootstrap_database(db_path)

    with connect(db_path) as connection:
        conditions_count = connection.execute(
            "SELECT COUNT(*) FROM resort_conditions"
        ).fetchone()[0]

    assert conditions_count == 0


def test_search_resorts_works_with_sqlite_backed_repositories(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    resorts = ResortRepository(db_path)
    conditions = ResortConditionsRepository(db_path)

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
        == "No live conditions signal available for this resort."
    )

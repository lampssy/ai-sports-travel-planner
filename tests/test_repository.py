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

    assert resort_count == 7
    assert area_count > 0
    assert rental_count > 0
    assert conditions_count == 7


def test_resort_repository_returns_nested_models(tmp_path) -> None:
    repository = ResortRepository(tmp_path / "planner.db")

    resorts = repository.list_resorts()
    alpine = next(resort for resort in resorts if resort.name == "Alpine Horizon")

    assert alpine.resort_id == "alpine-horizon"
    assert alpine.region == "Northern Alps"
    assert alpine.areas
    assert alpine.rentals
    assert alpine.areas[0].supported_skill_levels


def test_conditions_repository_returns_seeded_conditions(tmp_path) -> None:
    repository = ResortConditionsRepository(tmp_path / "planner.db")

    conditions = repository.get_conditions_for_resort("Savoy Snowfield")

    assert conditions is not None
    assert conditions.availability_status == "temporarily_closed"
    assert conditions.snow_confidence_label == "fair"


def test_bootstrap_seeds_empty_conditions_table_in_partially_seeded_database(
    tmp_path,
) -> None:
    db_path = tmp_path / "planner.db"
    bootstrap_database(db_path)

    with connect(db_path) as connection:
        connection.execute("DELETE FROM resort_conditions")

    bootstrap_database(db_path)

    with connect(db_path) as connection:
        conditions_count = connection.execute(
            "SELECT COUNT(*) FROM resort_conditions"
        ).fetchone()[0]

    assert conditions_count == 7


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
    assert results[0].resort_name == "Alpine Horizon"

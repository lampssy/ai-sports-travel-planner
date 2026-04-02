from app.data.loader import load_resorts
from app.integrations.conditions import get_conditions_provider


def test_all_seeded_resorts_have_stable_metadata() -> None:
    resorts = load_resorts()

    assert resorts
    assert all(resort.resort_id for resort in resorts)
    assert all(resort.region for resort in resorts)


def test_all_seeded_resorts_have_conditions_records() -> None:
    resorts = load_resorts()
    provider = get_conditions_provider()

    missing = [
        resort.name
        for resort in resorts
        if provider.get_conditions_for_resort(resort.name) is None
    ]

    assert missing == []


def test_seed_data_supports_coherent_france_ranking_demo() -> None:
    resorts = {resort.name: resort for resort in load_resorts()}

    alpine = resorts["Alpine Horizon"]
    mont_blanc = resorts["Mont Blanc Escape"]

    assert alpine.region == "Northern Alps"
    assert mont_blanc.region == "Northern Alps"
    assert any("intermediate" in area.supported_skill_levels for area in alpine.areas)
    assert any(
        "intermediate" in area.supported_skill_levels for area in mont_blanc.areas
    )

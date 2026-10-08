"""AD2-01 registry, Gym, and empty-session acceptance tests."""

import pytest
from openmdbench.api.sessions import SessionStore
from openmdbench.scenarios.loader import load_scenario_id

IDS = ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD")


@pytest.mark.parametrize("scenario_id", IDS)
def test_variant_loads_and_creates_empty_session_with_config_metadata(scenario_id: str) -> None:
    assert load_scenario_id(scenario_id).scenario_id == scenario_id
    session = SessionStore().create(scenario_id, seed=7)
    assert session.env._ad2_combat is not None
    assert session.env.config_metadata == {
        "scenario_id": scenario_id,
        "config_version": "2.0.0",
        "config_hash": session.env.scenario_hash,
        "catalog_hash": session.env._ad2_combat.catalog.content_hash,
    }


def test_retired_placeholder_has_actionable_migration_error() -> None:
    with pytest.raises(ValueError, match="deprecated.*EASY.*MEDIUM.*HARD"):
        load_scenario_id("MD-AD-002")

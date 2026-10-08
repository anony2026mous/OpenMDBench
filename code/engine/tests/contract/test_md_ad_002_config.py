"""AD2-01 strict configuration contract for the three MD-AD-002 variants."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from openmdbench.scenarios.md_ad_002_config import (
    MDAD002_CONFIG_PATHS,
    MDAD002Config,
    load_md_ad_002_config,
)
from pydantic import ValidationError


def test_three_configs_are_independent_and_round_trip() -> None:
    loaded = [load_md_ad_002_config(scenario_id) for scenario_id in MDAD002_CONFIG_PATHS]
    assert [item.config.scenario_id for item in loaded] == list(MDAD002_CONFIG_PATHS)
    assert len({item.sha256 for item in loaded}) == 3
    for item in loaded:
        assert len(item.config.deployments) == 7
        assert [wave.count for wave in item.config.waves] == [4, 5, 6]
        assert item.config.config_version == "2.0.0"
        uavs = [
            deployment
            for deployment in item.config.deployments
            if deployment.platform == "interceptor_uav"
        ]
        assert [deployment.inventory for deployment in uavs] == [12, 12, 12]
        missile = next(
            weapon
            for weapon in item.config.weapons
            if weapon.component == "uav_interceptor_missile"
        )
        assert missile.inventory == 36
        assert missile.damage == 1.0
        assert MDAD002Config.model_validate(item.config.model_dump()) == item.config


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ("duplicate", "duplicate"),
        ("coordinate", "less than or equal"),
        ("terrain", "requires land"),
        ("wave_time", "time limit"),
        ("inventory", "greater than or equal"),
        ("probability", "less than or equal"),
        ("component", "Input should be"),
        ("range", "minimum range"),
        ("unit", "Input should be"),
        ("map_hash", "map hash"),
        ("sensor_range", "low-altitude"),
        ("sensor_assignment", "incompatible"),
    ),
)
def test_invalid_configuration_fails_closed(change: str, message: str) -> None:
    path = Path(__file__).parents[2] / MDAD002_CONFIG_PATHS["MD-AD-002-EASY"]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    bad = deepcopy(data)
    if change == "duplicate":
        bad["deployments"][1]["id"] = bad["deployments"][0]["id"]
    elif change == "coordinate":
        bad["deployments"][0]["lon_deg"] = 181
    elif change == "terrain":
        bad["deployments"][0]["terrain"] = "water"
    elif change == "wave_time":
        bad["waves"][2]["time_seconds"] = 4000
    elif change == "inventory":
        bad["weapons"][0]["inventory"] = -1
    elif change == "probability":
        bad["weapons"][0]["hit_probability"] = 2
    elif change == "component":
        bad["communications"][0]["component"] = "magic_link"
    elif change == "range":
        bad["weapons"][1]["minimum_range_m"] = 3000
    elif change == "unit":
        bad["denial_zone"]["radius_unit"] = "kilometre"
    else:
        if change == "map_hash":
            bad["map"]["raw_sha256"] = "sha256:000"
        elif change == "sensor_range":
            bad["sensors"][0]["low_altitude_range_m"] = 50000
        else:
            bad["sensors"][0]["assigned_entities"] = ["red-picket-usv-1"]
    with pytest.raises(ValidationError, match=message):
        MDAD002Config.model_validate(bad)

"""Built-in policy modules depend only on public observation/action contracts."""

import inspect

import openmdbench.policies.blue as blue
import openmdbench.policies.red as red
import pytest
from openmdbench.core.entities import Domain
from openmdbench.policies import RedIngressAgent
from openmdbench.schemas.observation import (
    EnvironmentObservation,
    FriendlyAsset,
    Observation,
    SituationalData,
)
from pydantic import ValidationError


def test_rule_agents_do_not_import_internal_world_state() -> None:
    source = inspect.getsource(blue) + inspect.getsource(red)
    assert "WorldState" not in source
    assert "EntityRegistry" not in source
    assert "referee_intent" not in source
    assert "future_events" not in source


def test_policy_receives_frozen_dto_without_hidden_attributes() -> None:
    observation = Observation(
        session_id="sandbox",
        timestamp=0,
        mission_briefing="public",
        situational_data=SituationalData(
            friendly_assets=(
                FriendlyAsset(
                    id="red-uav-1",
                    type="uav",
                    domain=Domain.AIR,
                    position=(10_000.0, 0.0, 1_500.0),
                    velocity=(-40.0, 0.0, 0.0),
                    heading=270.0,
                    health=1.0,
                    energy=1.0,
                    sensor_mode="active_search",
                    weapon_count=0,
                    comm_status="connected",
                ),
            ),
            detected_contacts=(),
            environment=EnvironmentObservation(
                weather="clear",
                weather_trend="stable",
                sea_state=0,
                visibility_km=20.0,
                wind_speed=0.0,
                wind_direction=0.0,
            ),
        ),
        time_remaining=900,
        mission_status="in_progress",
    )
    assert not hasattr(observation, "world")
    assert not hasattr(observation, "referee_intent")
    with pytest.raises(ValidationError):
        observation.timestamp = 10
    RedIngressAgent((0.0, 0.0, 0.0)).act(observation)

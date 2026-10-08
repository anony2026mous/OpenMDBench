"""Validated public and referee-only scenario configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.core.entities import Side
from openmdbench.systems.weather import Weather

PlatformType = Literal["uav", "usv", "shore_radar", "auv"]
Category = str


class ScenarioModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EntityDeployment(ScenarioModel):
    id: str = Field(min_length=1)
    side: Side
    type: PlatformType
    position: tuple[float, float, float]


class ForceComposition(ScenarioModel):
    uav: int = Field(default=0, ge=0)
    usv: int = Field(default=0, ge=0)
    shore_radar: int = Field(default=0, ge=0)
    auv: int = Field(default=0, ge=0)


class WorldConfig(ScenarioModel):
    bounds: tuple[float, float, float, float]
    map_id: str = "weihai"

    @model_validator(mode="after")
    def validate_bounds(self) -> WorldConfig:
        if self.bounds[0] >= self.bounds[2] or self.bounds[1] >= self.bounds[3]:
            raise ValueError("world bounds must have increasing min/max coordinates")
        return self


class PublicScenario(ScenarioModel):
    name: str
    background: str
    primary_objectives: tuple[str, ...]
    secondary_objectives: tuple[str, ...] = ()
    known_intelligence: tuple[str, ...] = ()
    weather_forecast: str
    constraints: tuple[str, ...] = ()


class ScheduledScenarioEvent(ScenarioModel):
    tick: int = Field(ge=0)
    event_type: str
    payload: dict[str, str | int | float | bool] = Field(default_factory=dict)


class RefereeScenario(ScenarioModel):
    opponent_intent: str
    hidden_events: tuple[ScheduledScenarioEvent, ...] = ()
    ground_truth: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ScoringConfig(ScenarioModel):
    weights: dict[str, float]
    baseline_version: str
    baseline: dict[str, float]

    @model_validator(mode="after")
    def validate_weights(self) -> ScoringConfig:
        if any(weight < 0.0 for weight in self.weights.values()):
            raise ValueError("scoring weights cannot be negative")
        if self.weights and abs(sum(self.weights.values()) - 1.0) > 1e-6:
            raise ValueError("scoring weights must sum to 1")
        return self


class Scenario(ScenarioModel):
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str = Field(max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    category: Category
    difficulty: Literal["easy", "medium", "hard"]
    world: WorldConfig
    public: PublicScenario
    entities: tuple[EntityDeployment, ...]
    spawn_counts: dict[Side, ForceComposition]
    time_limit_ticks: int = Field(gt=0)
    roe: tuple[str, ...]
    initial_weather: Weather
    weather_timeline: tuple[ScheduledScenarioEvent, ...] = ()
    success_conditions: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    scoring: ScoringConfig
    referee: RefereeScenario

    @model_validator(mode="after")
    def validate_deployments(self) -> Scenario:
        ids = [entity.id for entity in self.entities]
        if len(ids) != len(set(ids)):
            raise ValueError("entity IDs must be unique within a scenario")
        if Side.BLUE not in self.spawn_counts or Side.RED not in self.spawn_counts:
            raise ValueError("scenario spawn_counts require blue and red forces")
        min_x, min_y, max_x, max_y = self.world.bounds
        for entity in self.entities:
            x, y, z = entity.position
            if not min_x <= x <= max_x or not min_y <= y <= max_y:
                raise ValueError(f"entity {entity.id} is outside world bounds")
            if entity.type in {"usv", "shore_radar"} and z != 0.0:
                raise ValueError(f"surface/shore entity {entity.id} must have z=0")
            if entity.type == "uav" and z < 0.0:
                raise ValueError(f"UAV {entity.id} cannot have negative altitude")
            if entity.type == "auv" and not -300.0 <= z <= 0.0:
                raise ValueError(f"AUV {entity.id} has invalid depth")
        return self

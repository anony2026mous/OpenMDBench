"""RF-01 acceptance contract for scenario-independent public schema v2.

These tests intentionally import the target public module.  They must remain
independent of every MD scenario and of the legacy red/blue ``Side`` enum.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from openmdbench.schemas.core_v2 import (
    ConditionV2,
    CoreScenarioV2,
    EntitySpecV2,
    EventSpecV2,
    FactionV2,
    FormationSpecV2,
    InitialStateV2,
    MissionRuleV2,
    MissionSelectorV2,
    ObservationV2,
    RelationshipV2,
    ScoreMetricV2,
    VisualizationFrameV2,
    WorldSpecV2,
    ZoneV2,
)
from pydantic import ValidationError


def _state(**changes: Any) -> InitialStateV2:
    values: dict[str, Any] = {
        "schema_version": "2.0",
        "position_m": (100.0, 200.0, 300.0),
        "velocity_mps": (4.0, 5.0, 0.0),
        "heading_deg": 45.0,
        "health": 1.0,
        "component_states": {"sensor.primary": {"health": 1.0, "mode": "search"}},
    }
    values.update(changes)
    return InitialStateV2(**values)


def _entity(faction_id: str = "coalition.alpha", **changes: Any) -> EntitySpecV2:
    values: dict[str, Any] = {
        "schema_version": "2.0",
        "id": "aircraft-001",
        "faction_id": faction_id,
        "platform_ref": "platforms.generic-aircraft@2.0.0",
        "dynamics_ref": "dynamics.fixed-wing@2.0.0",
        "loadout_ref": "loadouts.recon@2.0.0",
        "initial_state": _state(),
        "controller_slot": "training-team/flight-lead/slot-17",
        "tags": ("air", "recon"),
    }
    values.update(changes)
    return EntitySpecV2(**values)


def _factions(count: int) -> tuple[FactionV2, ...]:
    return tuple(
        FactionV2(schema_version="2.0", id=f"team.{index}", display_name=f"Team {index}")
        for index in range(count)
    )


@pytest.mark.parametrize("count", (1, 3, 4))
def test_arbitrary_faction_cardinality_and_relationships(count: int) -> None:
    factions = _factions(count)
    relationships = tuple(
        RelationshipV2(
            schema_version="2.0",
            source_faction_id=factions[index].id,
            target_faction_id=factions[(index + 1) % count].id,
            relation="hostile" if count > 1 else "friendly",
        )
        for index in range(count)
    )
    scenario = CoreScenarioV2(
        schema_version="2.0",
        scenario_id=f"generic.exercise.{count}",
        factions=factions,
        relationships=relationships,
        entities=(_entity(factions[0].id),),
        formations=(),
        world=WorldSpecV2(schema_version="2.0", coordinate_system="local_m", zones=()),
        events=(),
        mission_rules=(),
        score_metrics=(),
    )

    assert tuple(item.id for item in scenario.factions) == tuple(
        f"team.{index}" for index in range(count)
    )
    assert "red" not in scenario.model_dump_json()
    assert "blue" not in scenario.model_dump_json()


def test_unknown_relationship_endpoint_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown.*faction|faction.*unknown"):
        CoreScenarioV2(
            schema_version="2.0",
            scenario_id="generic.relationship.validation",
            factions=_factions(1),
            relationships=(
                RelationshipV2(
                    schema_version="2.0",
                    source_faction_id="team.0",
                    target_faction_id="not-declared",
                    relation="neutral",
                ),
            ),
            entities=(_entity("team.0"),),
            world=WorldSpecV2(schema_version="2.0", coordinate_system="local_m", zones=()),
        )


@pytest.mark.parametrize("count", (1, 10, 100))
def test_formation_schema_accepts_required_scale_boundaries(count: int) -> None:
    formation = FormationSpecV2(
        schema_version="2.0",
        id=f"formation-{count}",
        count=count,
        id_pattern="member-{index:03d}",
        entity_template=_entity(id="template"),
        offsets_m=((0.0, 0.0, 0.0),),
    )

    assert formation.count == count
    assert formation.entity_template.controller_slot == "training-team/flight-lead/slot-17"


def test_world_zone_event_mission_and_score_contract() -> None:
    selector = MissionSelectorV2(
        schema_version="2.0",
        factions=("coalition.alpha",),
        tags=("protected",),
        domains=("surface",),
        capabilities=("communication.relay",),
    )
    condition = ConditionV2(
        schema_version="2.0",
        operator="all",
        operands=(
            ConditionV2(
                schema_version="2.0",
                operator="count",
                selector=selector,
                parameters={"comparison": ">=", "value": 1},
            ),
            ConditionV2(
                schema_version="2.0",
                operator="not",
                operands=(
                    ConditionV2(
                        schema_version="2.0",
                        operator="event",
                        parameters={"event_type": "protected.destroyed"},
                    ),
                ),
            ),
        ),
    )
    rule = MissionRuleV2(
        schema_version="2.0",
        id="protect-and-survive",
        priority=50,
        condition=condition,
        outcome="success",
        latch=True,
    )
    metric = ScoreMetricV2(
        schema_version="2.0",
        id="relay-availability",
        value=None,
        available=False,
        weight=0.25,
    )
    zone = ZoneV2(
        schema_version="2.0",
        id="safe-zone",
        geometry_type="polygon",
        coordinates_m=((0.0, 0.0), (100.0, 0.0), (0.0, 100.0)),
        tags=("protected",),
    )
    world = WorldSpecV2(
        schema_version="2.0",
        coordinate_system="local_m",
        zones=(zone,),
        boundary_policy="constrain_motion",
    )
    event = EventSpecV2(
        schema_version="2.0",
        id="weather-front",
        event_type="weather_change",
        trigger={"tick": 300},
        payload={"environment_ref": "environments.rain@2.0.0"},
    )

    assert rule.condition.operands[0].selector == selector
    assert metric.value is None and metric.available is False
    assert world.zones[0].id == "safe-zone"
    assert event.trigger["tick"] == 300


@pytest.mark.parametrize("bad", (math.nan, math.inf, -math.inf))
def test_nonfinite_numbers_are_rejected_recursively(bad: float) -> None:
    with pytest.raises(ValidationError, match="finite"):
        EventSpecV2(
            schema_version="2.0",
            id="invalid-number",
            event_type="message",
            trigger={"tick": 1},
            payload={"nested": {"value": bad}},
        )


def test_unknown_fields_are_rejected_at_every_public_boundary() -> None:
    with pytest.raises(ValidationError, match="extra"):
        FactionV2.model_validate(
            {
                "schema_version": "2.0",
                "id": "any.valid-faction",
                "secret_legacy_side": "blue",
            }
        )


def test_observation_and_frame_are_dynamic_and_deeply_immutable() -> None:
    observation = ObservationV2(
        schema_version="2.0",
        session_id="session-1",
        tick=7,
        observer_faction_id="coalition.alpha",
        own_entities=({"id": "asset-1", "components": {"health": 1.0}},),
        contacts_by_faction={"opposition.zulu": ({"contact_id": "contact-9"},)},
        metadata={"permissions": {"truth": False}},
    )
    frame = VisualizationFrameV2(
        schema_version="2.0",
        session_id="session-1",
        scenario_id="generic.exercise",
        tick=7,
        view="faction",
        view_faction_id="coalition.alpha",
        entities=({"id": "asset-1", "faction_id": "coalition.alpha"},),
        contacts_by_faction={"opposition.zulu": ({"contact_id": "contact-9"},)},
        scores_by_faction={"coalition.alpha": {"total": 0.5}},
    )

    with pytest.raises((TypeError, AttributeError)):
        observation.metadata["permissions"]["truth"] = True
    with pytest.raises((TypeError, AttributeError)):
        observation.contacts_by_faction["opposition.zulu"][0]["contact_id"] = "truth-id"
    with pytest.raises((TypeError, AttributeError)):
        frame.scores_by_faction["coalition.alpha"]["total"] = 1.0

    payload = frame.model_dump_json()
    assert "coalition.alpha" in payload
    assert "opposition.zulu" in payload
    assert '"red"' not in payload and '"blue"' not in payload

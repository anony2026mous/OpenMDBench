"""RF-01 remediation contracts for the complete generic domain schema."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

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
    RelationshipV2,
    ScoreMetricV2,
    VisualizationFrameV2,
    WorldSpecV2,
    ZoneV2,
)
from openmdbench.schemas.domain_v2 import (
    BoundaryPolicyV2,
    CheckpointEnvelopeV2,
    ComponentProfileV2,
    DamageIntentV2,
    DamageResultV2,
    DynamicsProfileV2,
    EffectProfileV2,
    LifecycleStateV2,
    LoadoutProfileV2,
    PlatformProfileV2,
    SchemaMigrationV2,
    WeaponProfileV2,
)
from openmdbench.schemas.interface_v2 import CheckpointMetadataV2, StableErrorV2
from pydantic import ValidationError

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _state() -> InitialStateV2:
    return InitialStateV2(
        schema_version="2.0",
        position_m=(0.0, 0.0, 100.0),
        heading_deg=0.0,
    )


def _entity(identifier: str, controller_slot: str | None = None) -> EntitySpecV2:
    return EntitySpecV2(
        schema_version="2.0",
        id=identifier,
        faction_id="faction.any",
        platform_ref="platforms.air.generic@2.0.0",
        dynamics_ref="dynamics.air.generic@2.0.0",
        loadout_ref="loadouts.any@2.0.0",
        initial_state=_state(),
        controller_slot=controller_slot,
    )


def _scenario(
    entities: tuple[EntitySpecV2, ...] = (),
    formations: tuple[FormationSpecV2, ...] = (),
    events: tuple[EventSpecV2, ...] = (),
    mission_rules: tuple[MissionRuleV2, ...] = (),
    score_metrics: tuple[ScoreMetricV2, ...] = (),
) -> CoreScenarioV2:
    return CoreScenarioV2(
        schema_version="2.0",
        scenario_id="generic.domain.contract",
        factions=(FactionV2(schema_version="2.0", id="faction.any"),),
        entities=entities,
        formations=formations,
        world=WorldSpecV2(schema_version="2.0", coordinate_system="local_m"),
        events=events,
        mission_rules=mission_rules,
        score_metrics=score_metrics,
    )


def test_domain_profiles_are_versioned_composable_and_engine_bounded() -> None:
    platform = PlatformProfileV2(
        schema_version="2.0",
        id="platforms.air.generic",
        version="2.1.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        domain="air",
        component_slots=("sensor", "communication", "payload"),
        allowed_dynamics=("dynamics.air.generic@2.0.0",),
    )
    dynamics = DynamicsProfileV2(
        schema_version="2.0",
        id="dynamics.air.generic",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="kinematic.fixed-wing.v2",
        parameters={"maximum_speed_mps": 120.0, "turn_rate_deg_s": 10.0},
    )
    component = ComponentProfileV2(
        schema_version="2.0",
        id="components.radar.generic",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        capability="sensor.radar",
        slot_type="sensor",
        parameters={"range_m": 25_000.0},
    )
    loadout = LoadoutProfileV2(
        schema_version="2.0",
        id="loadouts.any",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        component_refs=("components.radar.generic@2.0.0",),
        ammunition={"weapons.interceptor@2.0.0": 2},
    )

    assert platform.domain == "air"
    assert dynamics.model_id == "kinematic.fixed-wing.v2"
    assert component.capability == "sensor.radar"
    assert loadout.ammunition["weapons.interceptor@2.0.0"] == 2


def test_weapon_effect_damage_and_lifecycle_are_separate_dtos() -> None:
    weapon = WeaponProfileV2(
        schema_version="2.0",
        id="weapons.interceptor",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        target_domains=("air",),
        minimum_range_m=100.0,
        maximum_range_m=20_000.0,
        hit_model_id="probability.distance.v2",
        effect_ref="effects.fragmentation@2.0.0",
    )
    effect = EffectProfileV2(
        schema_version="2.0",
        id="effects.fragmentation",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        damage_model_id="damage.component-health.v2",
        parameters={"damage_fraction": 0.4},
    )
    intent = DamageIntentV2(
        schema_version="2.0",
        intent_id="damage-1",
        tick=7,
        source_entity_id="attacker-any",
        target_entity_id="target-any",
        effect_ref="effects.fragmentation@2.0.0",
        parameters={"damage_fraction": 0.4},
    )
    result = DamageResultV2(
        schema_version="2.0",
        target_entity_id="target-any",
        tick=7,
        applied_intent_ids=("damage-1",),
        health_before=1.0,
        health_after=0.6,
        component_health={"propulsion": 0.5},
        lifecycle_before=LifecycleStateV2.ACTIVE,
        lifecycle_after=LifecycleStateV2.DEGRADED,
    )

    assert weapon.effect_ref == "effects.fragmentation@2.0.0"
    assert effect.damage_model_id == "damage.component-health.v2"
    assert intent.target_entity_id == result.target_entity_id
    assert result.lifecycle_after is LifecycleStateV2.DEGRADED


def test_boundary_policy_and_checkpoint_envelope_round_trip() -> None:
    policy = BoundaryPolicyV2(
        schema_version="2.0",
        id="policy.constrain-airspace",
        violation_actions=("constrain_motion", "emit_event", "apply_effect"),
        effect_ref="effects.boundary-impact@2.0.0",
        tolerance_m=0.01,
    )
    metadata = CheckpointMetadataV2(
        schema_version="2.0",
        session_id="session-any",
        scenario_id="generic.domain.contract",
        tick=77,
        engine_version="2.0.0",
        seed=73,
        resolved_hash=SHA_A,
        catalog_hashes={"platform@2.0.0": SHA_B},
        plugin_hashes={"model@2.0.0": SHA_C},
        map_hash=SHA_D,
        checkpoint_hash=SHA_E,
        rng_streams=("combat", "sensor"),
    )
    envelope = CheckpointEnvelopeV2(
        schema_version="2.0",
        metadata=metadata,
        world_state={"entities": [{"id": "entity-any", "health": 1.0}]},
        command_state={"persistent": []},
        system_state={"mission": {"latched": False}},
        rng_state={"combat": {"state": [1, 2, 3]}},
    )

    assert policy.violation_actions[0] == "constrain_motion"
    assert CheckpointEnvelopeV2.model_validate_json(envelope.model_dump_json()) == envelope


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_scenario_supports_required_entity_boundaries_and_json_roundtrip(count: int) -> None:
    scenario = _scenario(tuple(_entity(f"entity-{index:03d}") for index in range(count)))

    assert len(scenario.entities) == count
    assert CoreScenarioV2.model_validate_json(scenario.model_dump_json()) == scenario


@pytest.mark.parametrize(
    ("field", "values"),
    (
        ("entities", (_entity("duplicate"), _entity("duplicate"))),
        (
            "formations",
            (
                FormationSpecV2(
                    schema_version="2.0",
                    id="duplicate",
                    count=1,
                    id_pattern="member-{index}",
                    entity_template=_entity("template-a"),
                ),
                FormationSpecV2(
                    schema_version="2.0",
                    id="duplicate",
                    count=1,
                    id_pattern="other-{index}",
                    entity_template=_entity("template-b"),
                ),
            ),
        ),
        (
            "events",
            (
                EventSpecV2(schema_version="2.0", id="duplicate", event_type="message", trigger={}),
                EventSpecV2(schema_version="2.0", id="duplicate", event_type="message", trigger={}),
            ),
        ),
        (
            "score_metrics",
            (
                ScoreMetricV2(schema_version="2.0", id="duplicate"),
                ScoreMetricV2(schema_version="2.0", id="duplicate"),
            ),
        ),
    ),
)
def test_every_scenario_aggregate_rejects_duplicate_ids(
    field: str, values: tuple[Any, ...]
) -> None:
    kwargs = {field: values}
    with pytest.raises(ValidationError, match="duplicate"):
        _scenario(**kwargs)


def test_controller_slot_conflict_is_rejected() -> None:
    with pytest.raises(ValidationError, match="controller.*slot|slot.*controller"):
        _scenario(
            (
                _entity("entity-1", "agent/team-a/slot-1"),
                _entity("entity-2", "agent/team-a/slot-1"),
            )
        )


@pytest.mark.parametrize(
    "changes",
    (
        {"id_pattern": "member-without-placeholder"},
        {"offsets_m": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), "count": 3},
    ),
)
def test_formation_pattern_and_offset_contract(changes: dict[str, Any]) -> None:
    values: dict[str, Any] = {
        "schema_version": "2.0",
        "id": "formation-any",
        "count": 1,
        "id_pattern": "member-{index:03d}",
        "entity_template": _entity("template"),
        "offsets_m": ((0.0, 0.0, 0.0),),
    }
    values.update(changes)
    with pytest.raises(ValidationError, match="pattern|offset"):
        FormationSpecV2(**values)


def test_score_metric_na_state_is_consistent() -> None:
    with pytest.raises(ValidationError, match="available|value|N/A"):
        ScoreMetricV2(schema_version="2.0", id="metric-any", value=0.7, available=False)
    with pytest.raises(ValidationError, match="available|value|N/A"):
        ScoreMetricV2(schema_version="2.0", id="metric-any", value=None, available=True)


def test_mapping_keys_must_be_strings_and_payloads_must_be_json_values() -> None:
    with pytest.raises(ValidationError, match="string|key"):
        ComponentProfileV2(
            schema_version="2.0",
            id="components.any",
            version="2.0.0",
            engine_compatibility=">=2.0.0,<3.0.0",
            capability="sensor.any",
            slot_type="sensor",
            parameters=cast(dict[str, Any], {1: "not-a-string-key"}),
        )
    with pytest.raises(ValidationError, match="finite|JSON|json"):
        ComponentProfileV2(
            schema_version="2.0",
            id="components.any",
            version="2.0.0",
            engine_compatibility=">=2.0.0,<3.0.0",
            capability="sensor.any",
            slot_type="sensor",
            parameters={"not_json": Decimal("NaN")},
        )


def test_schema_migration_rejects_unsupported_versions_with_stable_error() -> None:
    migration = SchemaMigrationV2(current_version="2.0", supported_sources=("2.0",))
    result = migration.migrate({"schema_version": "99.0", "scenario_id": "generic.unsupported"})

    assert isinstance(result, StableErrorV2)
    assert result.code == "schema.version_unsupported"
    assert result.path == ("schema_version",)
    assert result.value == "99.0"
    assert result.suggestion


def test_v1_is_explicitly_unsupported_until_a_real_migration_exists() -> None:
    with pytest.raises(ValidationError, match="1.0|unsupported|supported"):
        SchemaMigrationV2(current_version="2.0", supported_sources=("1.0", "2.0"))

    migration = SchemaMigrationV2(current_version="2.0", supported_sources=("2.0",))
    result = migration.migrate({"schema_version": "1.0", "scenario_id": "legacy.input"})
    assert isinstance(result, StableErrorV2)
    assert result.code == "schema.version_unsupported"
    assert result.value == "1.0"


def test_zone_ids_are_unique_in_world_aggregate() -> None:
    zone = ZoneV2(
        schema_version="2.0",
        id="zone-duplicate",
        geometry_type="polygon",
        coordinates_m=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
    )
    with pytest.raises(ValidationError, match="duplicate.*zone|zone.*duplicate"):
        WorldSpecV2(
            schema_version="2.0",
            coordinate_system="local_m",
            zones=(zone, zone),
        )


def test_mission_rule_ids_are_unique_in_scenario_aggregate() -> None:
    condition = ConditionV2(schema_version="2.0", operator="time", parameters={"tick": 1})
    rule = MissionRuleV2(
        schema_version="2.0", id="rule-duplicate", condition=condition, outcome="success"
    )
    with pytest.raises(ValidationError, match="duplicate.*rule|rule.*duplicate"):
        _scenario(mission_rules=(rule, rule))


def test_static_and_formation_expanded_entity_ids_cannot_overlap() -> None:
    formation = FormationSpecV2(
        schema_version="2.0",
        id="formation-a",
        count=2,
        id_pattern="member-{index:03d}",
        entity_template=_entity("template-a"),
    )
    with pytest.raises(ValidationError, match="entity.*duplicate|duplicate.*entity|overlap"):
        _scenario(entities=(_entity("member-000"),), formations=(formation,))


def test_two_formations_cannot_expand_to_the_same_entity_ids() -> None:
    formation_a = FormationSpecV2(
        schema_version="2.0",
        id="formation-a",
        count=2,
        id_pattern="member-{index:03d}",
        entity_template=_entity("template-a"),
    )
    formation_b = FormationSpecV2(
        schema_version="2.0",
        id="formation-b",
        count=2,
        id_pattern="member-{index:03d}",
        entity_template=_entity("template-b"),
    )
    with pytest.raises(ValidationError, match="entity.*duplicate|duplicate.*entity|overlap"):
        _scenario(formations=(formation_a, formation_b))


def test_controller_slot_conflict_is_checked_across_static_and_formation_entities() -> None:
    formation = FormationSpecV2(
        schema_version="2.0",
        id="formation-controller",
        count=1,
        id_pattern="formed-{index:03d}",
        entity_template=_entity("template", "controller/shared-slot"),
    )
    with pytest.raises(ValidationError, match="controller.*slot|slot.*controller"):
        _scenario(
            entities=(_entity("static", "controller/shared-slot"),),
            formations=(formation,),
        )


@pytest.mark.parametrize(
    "factory",
    (
        lambda: RelationshipV2(
            schema_version="2.0",
            source_faction_id="faction.any",
            target_faction_id="faction.other",
            relation=cast(Any, "typo_hostill"),
        ),
        lambda: EventSpecV2(
            schema_version="2.0",
            id="event-invalid",
            event_type=cast(Any, "execute_arbitrary_python"),
            trigger={"tick": 1},
        ),
        lambda: ConditionV2(schema_version="2.0", operator=cast(Any, "unknown_condition")),
        lambda: VisualizationFrameV2(
            schema_version="2.0",
            session_id="session-any",
            scenario_id="generic.any",
            tick=1,
            view=cast(Any, "admin_truth_bypass"),
        ),
        lambda: BoundaryPolicyV2(
            schema_version="2.0",
            id="boundary-invalid",
            violation_actions=cast(Any, ("teleport_without_evidence",)),
        ),
    ),
)
def test_controlled_identifiers_reject_unknown_spellings(factory: Any) -> None:
    with pytest.raises(ValidationError):
        factory()

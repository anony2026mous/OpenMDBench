"""Formal collision intent, attribution, lifecycle, and isolation semantics."""

import copy

import pytest
from openmdbench.core.entities import Domain, Lifecycle, PlatformAsset, Side
from openmdbench.core.world import ContactTrack
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import ActionBatch, PlatformAction


def _platform(env: OpenMDBenchEnv, entity_id: str) -> PlatformAsset:
    assert env.world is not None
    entity = env.world.registry.get(entity_id)
    assert isinstance(entity, PlatformAsset)
    return entity


def _co_locate_opponents(env: OpenMDBenchEnv) -> tuple[str, str, tuple[float, float, float]]:
    assert env.world is not None
    blue_id = "blue-striker-uav-01"
    red_id = "red-interceptor-uav-1"
    blue = env.world.registry.get(blue_id)
    red = env.world.registry.get(red_id)
    position = blue.position
    env.world.registry.update(blue.model_copy(update={"velocity": (0.0, 0.0, 0.0)}))
    env.world.registry.update(
        red.model_copy(update={"position": position, "velocity": (0.0, 0.0, 0.0)})
    )
    return blue_id, red_id, position


def test_declared_ramming_is_attributed_and_destroys_both_participants() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=101)
    env.reset(seed=101)
    blue_id, red_id, position = _co_locate_opponents(env)
    assert env.world is not None
    initial_ammo = dict(_platform(env, red_id).components.weapon_inventory)
    blue = ActionBatch(
        timestamp=0,
        actions=(
            PlatformAction(
                entity_id=blue_id,
                navigation="move_to",
                target=position,
                speed_mps=1.0,
                ram_target_id=red_id,
            ),
        ),
    )
    red = ActionBatch(
        timestamp=0,
        actions=(
            PlatformAction(
                entity_id=red_id,
                navigation="hold_position",
                engage_contact_id="contact-missing",
                weapon_id="uav_interceptor_missile",
            ),
        ),
    )
    _blue, _red, _terminated, info = env.step_bilateral(blue, red)
    assert env.world is not None
    assert env.world.registry.get(blue_id).lifecycle is Lifecycle.DESTROYED
    assert env.world.registry.get(red_id).lifecycle is Lifecycle.DESTROYED
    events = info["collision_events"]
    assert isinstance(events, tuple)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, dict)
    assert event["classification"] == "deliberate_ramming"
    assert event["participants"] == (blue_id, red_id)
    assert event["aggressor_ids"] == (blue_id,)
    assert event["intended_targets"] == {blue_id: red_id}
    assert event["relative_speed_mps"] >= 0.0
    assert event in env.wave_events
    assert _platform(env, red_id).components.weapon_inventory == initial_ammo
    assert env.last_combat_audit[0]["rejection_code"] == "contact_not_owned"


def test_collision_does_not_cancel_an_already_legal_same_tick_shot() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=106)
    env.reset(seed=106)
    collision_blue_id, red_id, collision_position = _co_locate_opponents(env)
    assert env.world is not None and env._ad2_perception is not None
    target_id = "blue-striker-uav-02"
    target = env.world.registry.get(target_id)
    target_position = (
        collision_position[0] + 1_000.0,
        collision_position[1],
        collision_position[2],
    )
    env.world.registry.update(
        target.model_copy(update={"position": target_position, "velocity": (0.0, 0.0, 0.0)})
    )
    contact_id = "contact-red-collision-shot"
    contact = ContactTrack(
        contact_id=contact_id,
        owner_side=Side.RED,
        estimated_domain=Domain.AIR,
        position=target_position,
        velocity=(0.0, 0.0, 0.0),
        uncertainty_m=1.0,
        confidence=1.0,
        first_detected_tick=0,
        detected_by=("test-sensor",),
        inferred_type="hostile_uav",
        last_update_tick=0,
    )
    env._ad2_perception.contact_ids[target_id] = contact_id
    env._ad2_perception.tracks[target_id] = contact
    env.world.contacts[Side.RED] = [contact]
    ammunition_before = _platform(env, red_id).components.weapon_inventory[
        "uav_interceptor_missile"
    ]

    env.step_bilateral(
        ActionBatch(
            timestamp=0,
            actions=(
                PlatformAction(entity_id=collision_blue_id, navigation="hold_position"),
                PlatformAction(entity_id=target_id, navigation="hold_position"),
            ),
        ),
        ActionBatch(
            timestamp=0,
            actions=(
                PlatformAction(
                    entity_id=red_id,
                    navigation="hold_position",
                    engage_contact_id=contact_id,
                    weapon_id="uav_interceptor_missile",
                ),
            ),
        ),
    )

    assert env.world.registry.get(red_id).lifecycle is Lifecycle.DESTROYED
    assert env.world.registry.get(collision_blue_id).lifecycle is Lifecycle.DESTROYED
    assert (
        _platform(env, red_id).components.weapon_inventory["uav_interceptor_missile"]
        == ammunition_before - 1
    ), env.last_combat_audit[0]["rejection_code"]
    assert any(event["event_type"] == "combat_round" for event in env.last_combat_audit)


def test_collision_damage_does_not_prevent_same_tick_breach_latching() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=105)
    env.reset(seed=105)
    assert env.world is not None and env._ad2_adjudicator is not None
    blue_id = "blue-striker-uav-01"
    red_id = "red-interceptor-uav-1"
    position = (float(env._protected_point[0]), float(env._protected_point[1]), 100.0)
    for entity_id in (blue_id, red_id):
        entity = env.world.registry.get(entity_id)
        env.world.registry.update(
            entity.model_copy(update={"position": position, "velocity": (0.0, 0.0, 0.0)})
        )
    env.step_bilateral(
        ActionBatch(
            timestamp=0,
            actions=(PlatformAction(entity_id=blue_id, navigation="hold_position"),),
        ),
        ActionBatch(
            timestamp=0,
            actions=(PlatformAction(entity_id=red_id, navigation="hold_position"),),
        ),
    )
    assert env.world.registry.get(blue_id).lifecycle is Lifecycle.DESTROYED
    assert blue_id in env._ad2_adjudicator.breached_ids


def test_collision_without_declared_intent_is_classified_accidental() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=102)
    env.reset(seed=102)
    blue_id, red_id, _position = _co_locate_opponents(env)
    blue = ActionBatch(
        timestamp=0,
        actions=(PlatformAction(entity_id=blue_id, navigation="hold_position"),),
    )
    red = ActionBatch(
        timestamp=0,
        actions=(PlatformAction(entity_id=red_id, navigation="hold_position"),),
    )
    env.step_bilateral(blue, red)
    assert env.last_collision_events[0]["classification"] == "accidental_collision"
    assert env.last_collision_events[0]["aggressor_ids"] == ()


def test_invalid_friendly_ramming_target_fails_before_world_advances() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=103)
    env.reset(seed=103)
    assert env.world is not None
    before = copy.deepcopy(env.export_state())
    attacker = env.world.registry.get("blue-striker-uav-01")
    action = ActionBatch(
        timestamp=0,
        actions=(
            PlatformAction(
                entity_id=attacker.id,
                navigation="move_to",
                target=attacker.position,
                speed_mps=1.0,
                ram_target_id="blue-striker-uav-02",
            ),
        ),
    )
    with pytest.raises(ValueError, match="opposing side"):
        env.step_bilateral(action, ActionBatch(timestamp=0, actions=()))
    assert env.export_state() == before


def test_collision_evidence_survives_json_checkpoint_round_trip() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=104)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=104)
    env.reset(seed=104)
    restored.reset(seed=104)
    blue_id, red_id, _position = _co_locate_opponents(env)
    env.step_bilateral(
        ActionBatch(
            timestamp=0,
            actions=(PlatformAction(entity_id=blue_id, navigation="hold_position"),),
        ),
        ActionBatch(
            timestamp=0,
            actions=(PlatformAction(entity_id=red_id, navigation="hold_position"),),
        ),
    )
    restored.import_state(env.export_state())
    assert restored.last_collision_events == env.last_collision_events

"""MD3-07 data-only scenario and public rule-agent acceptance contracts."""

from __future__ import annotations

import copy
import inspect
from pathlib import Path
from typing import Any

import yaml
from openmdbench.catalog.formal_v2 import load_catalog_bundle_v2
from openmdbench.policies.rule_v2 import (
    FormalRuleAgentTeamV2,
    load_formal_rule_agent_profile_v2,
)
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2, formal_scenario_registry_v2
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.sessions.gateway_v2 import (
    AgentGatewayV2,
    GymnasiumAdapterV2,
    StructuredPythonAdapterV2,
)
from openmdbench.sessions.lifecycle_v2 import RunnerModeV2, SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2

PUBLIC_IDS = ("MD-INT-003-EASY", "MD-INT-003-MEDIUM", "MD-INT-003-HARD")


def _spawned_entities(resolved: Any) -> tuple[Any, ...]:
    return tuple(
        event.payload.values["entity"] for event in resolved.events if event.event_type == "spawn"
    )


def _deployed_entities(resolved: Any) -> tuple[Any, ...]:
    return (*resolved.entities, *_spawned_entities(resolved))


def test_packages_bind_only_their_immutable_level_profiles() -> None:
    expected_versions = {
        "MD-INT-003-EASY": "2.1.0",
        "MD-INT-003-MEDIUM": "2.2.0",
        "MD-INT-003-HARD": "2.3.0",
    }
    sensor_ids = {
        "sensor.defender-usv-surface-radar",
        "sensor.defender-usv-eo-ir",
        "sensor.isuav-surface-radar",
        "sensor.isuav-eo-ir",
        "sensor.shore-surface-radar",
        "sensor.attacker-navigation-radar",
    }
    for public_id, version in expected_versions.items():
        resolved, _catalog = compile_formal_scenario_v2(public_id)
        deployed = _deployed_entities(resolved)
        sensor_refs = {
            binding.exact_ref
            for entity in deployed
            for binding in entity.resource_bindings.get("sensors", ())
        }
        assert sensor_refs == {f"{sensor_id}@{version}" for sensor_id in sensor_ids}

        defender_entities = [
            entity for entity in deployed if entity.faction_id == "faction.defender"
        ]
        usv_or_shore = [
            entity
            for entity in defender_entities
            if entity.id.startswith("unit.guard.usv.") or entity.id == "unit.guard.shore.01"
        ]
        uavs = [entity for entity in defender_entities if entity.id.startswith("unit.guard.uav.")]
        assert usv_or_shore and uavs
        assert all(
            [binding.exact_ref for binding in entity.resource_bindings["communications"]]
            == ["communication.defender-surface-tactical@2.1.0"]
            for entity in usv_or_shore
        )
        assert all(
            [binding.exact_ref for binding in entity.resource_bindings["communications"]]
            == ["communication.defender-uav-surface-tactical@2.1.0"]
            for entity in uavs
        )

    hard, _catalog = compile_formal_scenario_v2("MD-INT-003-HARD")
    weather = next(event for event in hard.events if event.id == "event.weather.high-sea")
    assert (
        weather.payload.values["environment_binding"].exact_ref == "environment.md3-high-sea@2.1.0"
    )
    suppression = next(event for event in hard.events if event.id == "event.suppress.usv-radar")
    assert suppression.payload.values["component_ref"] == "sensor.defender-usv-surface-radar@2.3.0"


def _short_timeout_session(session_id: str) -> tuple[SessionLifecycleV2, Any, Any]:
    """Compile a two-tick copy of the public package without changing its source data."""

    payload = yaml.safe_load(Path("scenarios/formal/md_int_003_easy/scenario.yaml").read_bytes())
    scenario = payload["scenario"]
    scenario["world"]["duration_ticks"] = 2
    timeout_event = next(item for item in scenario["events"] if item["id"] == "event.timeout")
    timeout_event["trigger"]["tick"] = 1
    timeout_rule = next(item for item in scenario["mission_rules"] if item["id"] == "rule.timeout")
    timeout_rule["condition"]["parameters"]["tick"] = 2
    catalog = load_catalog_bundle_v2(Path("catalog/v2/md_int_003.yaml"))
    resolved = ScenarioCompilerV2(catalog=catalog).compile(ScenarioPackageV2.from_mapping(payload))
    session = SessionLifecycleV2.create(
        session_id=session_id,
        seed=73,
        resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash,
        catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode=RunnerModeV2.LOCKSTEP,
        physics_dt_seconds=float(resolved.world.tick_seconds or 1.0),
        decision_interval_ticks=1,
    )
    return session, resolved, catalog


def test_three_data_only_packages_compile_to_expected_force_and_level_differences() -> None:
    registry = formal_scenario_registry_v2()
    assert set(PUBLIC_IDS).issubset(registry)
    resolved = {public_id: compile_formal_scenario_v2(public_id)[0] for public_id in PUBLIC_IDS}

    for public_id, item in resolved.items():
        entry = registry[public_id]
        assert not any(path.suffix == ".py" for path in entry.package_root.rglob("*"))
        assert len((*item.entities, *_spawned_entities(item))) == 9
        assert item.world.map_ref == "map.weihai-local@2.0.0"
        assert item.world.duration_ticks == 1500
        assert item.world.tick_seconds == 1.0
        assert {entity.faction_id for entity in (*item.entities, *_spawned_entities(item))} == {
            "faction.defender",
            "faction.attacker",
        }

    assert not _spawned_entities(resolved["MD-INT-003-EASY"])
    assert [
        event.trigger.tick
        for event in resolved["MD-INT-003-MEDIUM"].events
        if event.event_type == "spawn"
    ] == [30, 540]
    hard_events = {event.id: event for event in resolved["MD-INT-003-HARD"].events}
    assert hard_events["event.forecast.high-sea"].trigger.tick == 240
    assert hard_events["event.weather.high-sea"].trigger.tick == 300
    assert hard_events["event.suppress.usv-radar"].trigger.tick == 400
    assert (
        len(resolved["MD-INT-003-EASY"].events)
        < len(resolved["MD-INT-003-MEDIUM"].events)
        < len(resolved["MD-INT-003-HARD"].events)
    )


def test_packages_rename_without_changing_logical_configuration() -> None:
    path = Path("scenarios/formal/md_int_003_easy/scenario.yaml")
    payload = yaml.safe_load(path.read_bytes())
    package = ScenarioPackageV2.from_mapping(payload)
    renamed = copy.deepcopy(payload)
    renamed["scenario"]["scenario_id"] = "third-party.surface.example"
    renamed["scenario"]["display_name"] = "第三方水面任务"
    assert ScenarioPackageV2.from_mapping(renamed).logical_hash == package.logical_hash


def test_public_rule_profiles_express_level_behaviour_without_worldstate_access() -> None:
    profiles = {public_id: load_formal_rule_agent_profile_v2(public_id) for public_id in PUBLIC_IDS}
    assert profiles["MD-INT-003-EASY"].attack.pattern == "direct"
    assert profiles["MD-INT-003-MEDIUM"].attack.turn_on_first_contact is True
    assert profiles["MD-INT-003-MEDIUM"].attack.contact_turn_deg == 20.0
    assert profiles["MD-INT-003-HARD"].attack.pattern == "multi_axis_serpentine"
    assert profiles["MD-INT-003-HARD"].attack.speed_cycle_mps == (10.0, 12.0, 12.9)

    import openmdbench.policies.rule_v2 as module

    source = inspect.getsource(module)
    assert "WorldState" not in source
    assert "scenario_id ==" not in source
    assert "MD-INT-003" not in source


def test_rule_agent_submits_public_actions_and_moves_l1_raiders() -> None:
    session = create_formal_session_v2(
        "MD-INT-003-EASY", session_id="md3.public-rule-agent", seed=73
    )
    team = FormalRuleAgentTeamV2.for_scenario("MD-INT-003-EASY", seed=73)
    session.load().start()
    try:
        before = {
            item["entity_id"]: tuple(item["position_m"])
            for item in session.world_view.observation(
                observer_faction_id="faction.attacker"
            ).own_entities
        }
        team(session)
        receipt = session.step(operation_id="md3.rule.tick.0", expected_tick=0)
        for tick in range(1, 6):
            receipt = session.step(operation_id=f"md3.rule.tick.{tick}", expected_tick=tick)
        after = {
            item["entity_id"]: tuple(item["position_m"])
            for item in session.world_view.observation(
                observer_faction_id="faction.attacker"
            ).own_entities
        }
        assert receipt.tick == 6
        assert team.last_decision is not None
        assert team.last_decision.attack_command_ids
        assert all(after[entity_id] != position for entity_id, position in before.items())
    finally:
        session.stop().close()


def test_usvs_materially_advance_under_the_public_mmg_navigation_profile() -> None:
    session = create_formal_session_v2(
        "MD-INT-003-EASY", session_id="md3.mmg.material-motion", seed=73
    )
    session.load().start()
    try:
        start = session.world_view.get("unit.raid.usv.02").state
        authority = next(
            token
            for token, grant in session.world_view.authority_tokens.items()
            if grant.controller_id == "agent.attack"
            and grant.entity_id == ""
            and "unit.raid.usv.02" in grant.entity_ids
        )
        command = PersistentCommandV2(
            schema_version="2.0",
            command_id="command.mmg.material-motion",
            command_type="navigation",
            entity_id="unit.raid.usv.02",
            faction_id="faction.attacker",
            based_on_tick=0,
            valid_until_tick=20,
            payload={"speed_mps": 18.0, "heading_deg": 270.0},
        )
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id="batch.mmg.material-motion",
                idempotency_key="idem.mmg.material-motion",
                faction_id="faction.attacker",
                based_on_tick=0,
                valid_until_tick=20,
                persistent_commands=(command,),
            ),
            authority_token=authority,
            operation_id="md3.mmg.material-motion.submit",
            expected_tick=0,
        )
        for tick in range(20):
            session.step(operation_id=f"md3.mmg.material-motion.{tick}", expected_tick=tick)
        end = session.world_view.get("unit.raid.usv.02").state
        displacement = sum(
            (after - before) ** 2
            for before, after in zip(start.position_m, end.position_m, strict=True)
        ) ** 0.5
        speed = sum(value * value for value in end.velocity_mps) ** 0.5
        assert displacement > 100.0
        assert speed > 10.0
    finally:
        session.stop().close()


def test_timeout_latches_post_interval_and_gym_marks_it_truncated_after_restore() -> None:
    session, resolved, catalog = _short_timeout_session("md3.timeout.original")
    restored: SessionLifecycleV2 | None = None
    session.load().start()
    try:
        first = session.step(operation_id="md3.timeout.original.0", expected_tick=0)
        assert first.world_receipt.mission_receipts[-1].terminal_result is None
        checkpoint = session.checkpoint()
        second = session.step(operation_id="md3.timeout.original.1", expected_tick=1)

        restored = SessionLifecycleV2.restore(
            checkpoint=checkpoint,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=resolved,
            expected_resolved_hash=resolved.resolved_hash,
            model_registry=catalog.model_registry,
            expected_model_registry_hash=resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        )
        restored_second = restored.step(operation_id="md3.timeout.original.1", expected_tick=1)
        terminal = second.world_receipt.mission_receipts[-1].terminal_result
        assert terminal is not None
        assert terminal.outcome == "timeout"
        assert terminal.tick == 2
        assert restored_second.world_receipt.mission_receipts[-1].terminal_result == terminal

        gym_session, _gym_resolved, _gym_catalog = _short_timeout_session("md3.timeout.gym")
        gateway = AgentGatewayV2()
        gateway.attach(gym_session)
        gateway.control(gym_session.session_id, "load")
        gateway.control(gym_session.session_id, "start")
        adapter = StructuredPythonAdapterV2(
            gateway, session_id=gym_session.session_id, faction_id="faction.defender"
        )
        gym = GymnasiumAdapterV2(adapter, authority_token="unused-without-action")
        try:
            _observation, _reward, terminated, truncated, _info = gym.step(None)
            assert terminated is False and truncated is False
            _observation, _reward, terminated, truncated, info = gym.step(None)
            assert terminated is False and truncated is True
            assert info["terminal_result"]["outcome"] == "timeout"
        finally:
            gym_session.stop().close()
    finally:
        if restored is not None:
            restored.stop().close()
        session.stop().close()


def test_each_public_rule_profile_submits_actions_against_its_own_package() -> None:
    for public_id in PUBLIC_IDS:
        session = create_formal_session_v2(
            public_id, session_id=f"md3.public-rule-agent.{public_id.lower()}", seed=73
        )
        team = FormalRuleAgentTeamV2.for_scenario(public_id, seed=73)
        session.load().start()
        try:
            team(session)
            receipt = session.step(operation_id="md3.rule.profile.tick.0", expected_tick=0)
            assert receipt.tick == 1
            assert team.last_decision is not None
            assert team.last_decision.attack_command_ids
        finally:
            session.stop().close()

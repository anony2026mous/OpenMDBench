"""Native V2 migration gates for all three MD-AD-002 difficulty packages."""

from __future__ import annotations

import copy
import inspect
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from openmdbench.catalog.formal_v2 import load_md_ad_002_catalog_v2
from openmdbench.dynamics.native_v2 import MMG_MODEL_REF
from openmdbench.scenarios.declarative_v2 import (
    ResolvedEntityV2,
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)
from openmdbench.scenarios.formal_v2 import (
    compile_formal_scenario_v2,
    formal_scenario_registry_v2,
)
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from openmdbench.sessions.formal_v2 import create_formal_gateway_v2, create_formal_session_v2
from openmdbench.visualization.live_formal_v2 import run_live_formal_v2
from openmdbench.world.missile_v2 import GuidedMissileProfileV2

FORMAL_ROOT = Path("scenarios/formal")
PUBLIC_IDS = ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD")


def test_three_difficulties_are_independent_data_only_v2_packages() -> None:
    registry = formal_scenario_registry_v2()
    assert set(PUBLIC_IDS).issubset(registry)
    for public_id in PUBLIC_IDS:
        entry = registry[public_id]
        assert not any(path.suffix == ".py" for path in entry.package_root.rglob("*"))
        package = ScenarioPackageV2.from_directory(entry.package_root)
        assert package.document["schema_version"] == "2.0"
        assert package.document["scenario_id"].endswith(".v2")
        assert "md_ad_002" not in package.document
        resolved, _catalog = compile_formal_scenario_v2(public_id)
        assert isinstance(resolved, ResolvedScenarioV2)
        assert len(resolved.entities) == 7
        assert sum(event.event_type == "spawn" for event in resolved.events) == 15
        assert len(cast(Any, resolved.mission_rules[0]).selector_resolution.entity_ids) == 15


def test_package_rename_does_not_change_logical_semantics() -> None:
    path = FORMAL_ROOT / "md_ad_002_easy" / "scenario.yaml"
    payload = yaml.safe_load(path.read_bytes())
    package = ScenarioPackageV2.from_mapping(payload)
    renamed = copy.deepcopy(payload)
    renamed["scenario"]["scenario_id"] = "third-party.area-denial.example"
    renamed["scenario"]["display_name"] = "第三方区域防御示例"
    renamed_package = ScenarioPackageV2.from_mapping(renamed)
    assert renamed_package.logical_hash == package.logical_hash
    resolved = ScenarioCompilerV2(catalog=load_md_ad_002_catalog_v2()).compile(renamed_package)
    assert resolved.scenario_id == "third-party.area-denial.example"
    assert len(resolved.entities) == 7
    assert sum(event.event_type == "spawn" for event in resolved.events) == 15


def test_difficulty_is_declared_by_resources_and_events_not_runtime_branches() -> None:
    resolved = {public_id: compile_formal_scenario_v2(public_id)[0] for public_id in PUBLIC_IDS}
    medium_refs = {
        binding.exact_ref
        for entity in cast(tuple[ResolvedEntityV2, ...], resolved["MD-AD-002-MEDIUM"].entities)
        for binding in entity.resource_bindings.get("sensors", ())
    }
    assert medium_refs and all(reference.startswith("sensor.") for reference in medium_refs)
    assert {
        "sensor.shore-early-warning@2.1.1",
        "sensor.picket-radar@2.1.1",
    } <= medium_refs
    assert all(reference.endswith(("@2.1.0", "@2.1.1")) for reference in medium_refs)
    assert "event.weather-cloudy" in {event.id for event in resolved["MD-AD-002-MEDIUM"].events}
    hard_types = {event.event_type for event in resolved["MD-AD-002-HARD"].events}
    assert {"weather_change", "jamming_start", "jamming_end", "component_suppression"} <= hard_types
    assert (
        len(resolved["MD-AD-002-EASY"].events)
        < len(resolved["MD-AD-002-MEDIUM"].events)
        < len(resolved["MD-AD-002-HARD"].events)
    )


def test_interceptor_missile_uses_data_driven_guided_flight_profile() -> None:
    catalog = load_md_ad_002_catalog_v2()
    weapon = catalog.resolve("weapons", "weapon.interceptor-missile@2.0.0")

    assert weapon.content["delivery_model"] == "guided_missile"
    profile = GuidedMissileProfileV2.model_validate(weapon.content["missile"])
    assert profile.cruise_speed_mps > profile.launch_speed_mps
    assert profile.max_flight_ticks > 1
    assert profile.seeker_detection_probability == pytest.approx(0.95)


@pytest.mark.parametrize("public_id", PUBLIC_IDS)
def test_all_deployed_entities_have_communication_endpoints_and_valid_jamming_targets(
    public_id: str,
) -> None:
    """Keep the simple faction-wide communications policy data-compatible."""

    resolved, _catalog = compile_formal_scenario_v2(public_id)
    spawned = tuple(
        event.payload.values["entity"] for event in resolved.events if event.event_type == "spawn"
    )
    deployed = tuple(cast(ResolvedEntityV2, entity) for entity in (*resolved.entities, *spawned))
    deployed_ids = {entity.id for entity in deployed}
    assert len(deployed) == 22
    assert all(entity.resource_bindings.get("communications", ()) for entity in deployed)

    starts = {
        event.payload.values["session_id"]: event.payload.values
        for event in resolved.events
        if event.event_type == "jamming_start"
    }
    ends = {
        event.payload.values["session_id"]
        for event in resolved.events
        if event.event_type == "jamming_end"
    }
    assert set(starts) == ends
    assert all(
        values["source_entity_id"] in deployed_ids and values["target_entity_id"] in deployed_ids
        for values in starts.values()
    )


@pytest.mark.parametrize("public_id", PUBLIC_IDS)
def test_native_v2_gateway_builds_steps_checkpoints_and_restores(public_id: str) -> None:
    gateway = create_formal_gateway_v2(public_id)
    session_id = f"session.{public_id.lower()}"
    gateway.create(session_id=session_id, seed=73)
    gateway.control(session_id, "load")
    gateway.control(session_id, "start")
    first = gateway.step(session_id, operation_id="tick.000", expected_tick=0)
    assert first.tick == 1
    observation = gateway.observation(session_id, faction_id="coalition.defender")
    assert observation.tick == 1
    assert len(observation.own_entities) == 7
    checkpoint = gateway.checkpoint(session_id)
    gateway.close(session_id)
    assert gateway.restore(checkpoint) == session_id
    assert gateway.checkpoint(session_id).checkpoint_hash == checkpoint.checkpoint_hash
    gateway.close(session_id)


@pytest.mark.parametrize("public_id", PUBLIC_IDS)
def test_formal_tick_uses_append_only_memory_records_not_durable_checkpoint(
    public_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All MD-AD-002 data packages share the no-rollback tick path."""

    session = create_formal_session_v2(
        public_id,
        session_id=f"session.{public_id.lower()}.tick-transaction",
        seed=73,
    )
    session.load().start()
    world = session._mutable_world()
    try:

        def durable_checkpoint_is_forbidden() -> Any:
            raise AssertionError("normal tick must not construct WorldCheckpointV2")

        monkeypatch.setattr(world, "checkpoint", durable_checkpoint_is_forbidden)
        receipt = session.step(operation_id="tick.in-memory", expected_tick=0)
        assert receipt.tick == 1
    finally:
        session.stop().close()


def test_formal_v2_authority_does_not_import_legacy_scenario_modules() -> None:
    import openmdbench.catalog.formal_v2 as catalog_module
    import openmdbench.scenarios.formal_v2 as scenario_module
    import openmdbench.sessions.formal_v2 as session_module

    source = "\n".join(
        inspect.getsource(module) for module in (catalog_module, scenario_module, session_module)
    )
    assert "openmdbench.scenarios.legacy" not in source
    assert "md_ad_002_config" not in source
    assert "OpenMDBenchEnv" not in source
    assert "SessionRuntime" not in source
    assert "scenario_id ==" not in source
    assert load_md_ad_002_catalog_v2().content_hash.startswith("sha256:")
    assert ScenarioCompilerV2 is not None


def test_spawned_intruder_is_controllable_through_public_v2_action_batch() -> None:
    session = create_formal_session_v2(
        "MD-AD-002-EASY", session_id="session.agent-example", seed=73
    )
    session.load().start()
    try:
        session.step(operation_id="tick.spawn", expected_tick=0)
        entity_id = "intruder.wave-1-001"
        token = next(
            token
            for token, grant in session.world_view.authority_tokens.items()
            if grant.entity_id == entity_id
        )
        before = session.world_view.get(entity_id).state.position_m[0]
        command = PersistentCommandV2(
            schema_version="2.0",
            command_id="navigation.intruder.wave-1-001.1",
            command_type="navigation",
            entity_id=entity_id,
            faction_id="coalition.intruder",
            based_on_tick=1,
            valid_until_tick=2,
            payload={"speed_mps": 45.0, "heading_deg": 270.0},
        )
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id="batch.intruder.wave-1-001.1",
                idempotency_key="idem.intruder.wave-1-001.1",
                faction_id="coalition.intruder",
                based_on_tick=1,
                valid_until_tick=2,
                persistent_commands=(command,),
            ),
            authority_token=token,
            operation_id="submit.intruder.wave-1-001.1",
            expected_tick=1,
        )
        session.step(operation_id="tick.controlled", expected_tick=1)
        assert session.world_view.get(entity_id).state.position_m[0] < before
    finally:
        session.stop().close()


def test_surface_picket_uses_isolated_mmg_through_public_navigation() -> None:
    resolved, _catalog = compile_formal_scenario_v2("MD-AD-002-EASY")
    picket = next(
        entity
        for entity in resolved.entities
        if isinstance(entity, ResolvedEntityV2) and entity.id == "defender.picket-001"
    )
    binding = picket.resource_bindings["dynamics"][0]
    assert binding.model_ref == MMG_MODEL_REF

    session = create_formal_session_v2(
        "MD-AD-002-EASY", session_id="session.surface-mmg-navigation", seed=73
    )
    session.load().start()
    try:
        entity_id = "defender.picket-001"
        authority = next(
            token
            for token, grant in session.world_view.authority_tokens.items()
            if grant.entity_id == entity_id
        )
        before = session.world_view.get(entity_id).state.position_m
        command = PersistentCommandV2(
            schema_version="2.0",
            command_id="navigation.surface-picket.001",
            command_type="navigation",
            entity_id=entity_id,
            faction_id="coalition.defender",
            based_on_tick=0,
            valid_until_tick=1,
            payload={"speed_mps": 6.45, "heading_deg": 90.0},
        )
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id="batch.surface-picket.001",
                idempotency_key="idem.surface-picket.001",
                faction_id="coalition.defender",
                based_on_tick=0,
                valid_until_tick=1,
                persistent_commands=(command,),
            ),
            authority_token=authority,
            operation_id="submit.surface-picket.001",
            expected_tick=0,
        )
        receipt = session.step(operation_id="tick.surface-picket.001", expected_tick=0)
        dynamics = tuple(
            item for item in receipt.world_receipt.dynamics_receipts if item.entity_id == entity_id
        )
        assert dynamics and dynamics[0].model_ref == MMG_MODEL_REF
        assert session.world_view.get(entity_id).state.position_m != before
        snapshots = session.checkpoint().world_checkpoint["native_adapter_snapshots"]
        picket_snapshot = next(item for item in snapshots if item["entity_id"] == entity_id)
        assert picket_snapshot["native_state"]["core"]["state"] is not None
    finally:
        session.stop().close()


def test_headless_live_runner_continues_mmg_after_world_adjudication() -> None:
    """A real live-style second tick must retain the MMG continuation state."""

    assert (
        run_live_formal_v2(
            "MD-AD-002-EASY",
            seed=73,
            speed=10.0,
            max_ticks=3,
            block_on_finish=False,
        )
        is None
    )

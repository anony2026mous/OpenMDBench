"""EF-03 contracts for MD-AD-002 environment Catalog versions."""

from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest
import yaml
from openmdbench.catalog.formal_v2 import load_md_ad_002_catalog_v2
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.world.capability_modifier_v2 import modifiers_from_environment_content_v2

ENVIRONMENTS = (
    ("environment.clear", "MD-AD-002-EASY", "event.weather-initial", 1.0),
    ("environment.cloudy", "MD-AD-002-MEDIUM", "event.weather-cloudy", 0.88),
    ("environment.rain-fog", "MD-AD-002-HARD", "event.weather-rain-fog", 0.65),
)


@pytest.mark.parametrize(("resource_id", "_scenario_id", "_event_id", "multiplier"), ENVIRONMENTS)
def test_new_environment_versions_materialize_only_declared_sensor_range_modifier(
    resource_id: str,
    _scenario_id: str,
    _event_id: str,
    multiplier: float,
) -> None:
    """S4-01/S4-03: old metadata stays inert; the versioned replacement is explicit."""

    catalog = load_md_ad_002_catalog_v2()
    legacy = catalog.resolve("environments", f"{resource_id}@2.0.0")
    current = catalog.resolve("environments", f"{resource_id}@2.1.0")

    assert (
        modifiers_from_environment_content_v2(
            environment_ref=legacy.exact_ref,
            content=legacy.content,
            source_event_id="event.legacy",
            active_from_tick=0,
        )
        == ()
    )

    modifiers = modifiers_from_environment_content_v2(
        environment_ref=current.exact_ref,
        content=current.content,
        source_event_id="event.current",
        active_from_tick=7,
    )
    assert [(item.capability, item.operation, item.value) for item in modifiers] == [
        ("sensor.range", "multiply", multiplier)
    ]
    assert modifiers[0].active_from_tick == 7
    assert current.content["metadata_only_fields"] == ("weather", "visibility_scale", "sea_state")
    assert current.content["sensor_range_multiplier"] == multiplier
    assert set(current.content["parameter_annotations"]) == {
        "visibility_scale",
        "sea_state",
        "sensor_range_multiplier",
    }
    for annotation in current.content["parameter_annotations"].values():
        assert annotation["source"]
        assert annotation["unit"] == "1"
        assert annotation["scope"]
        assert annotation["fidelity"] == "UNVALIDATED_BENCHMARK"


@pytest.mark.parametrize(("_resource_id", "scenario_id", "event_id", "multiplier"), ENVIRONMENTS)
def test_formal_scenarios_bind_versioned_environment_resources_and_hashes(
    _resource_id: str,
    scenario_id: str,
    event_id: str,
    multiplier: float,
) -> None:
    """S4-04: the resource identity is resolved, not lazily interpreted."""

    resolved, catalog = compile_formal_scenario_v2(scenario_id)
    binding = next(
        event for event in resolved.events if event.id == event_id
    ).payload.environment_binding
    assert binding.exact_ref.endswith("@2.1.0")
    assert binding.normalized_content["sensor_range_multiplier"] == multiplier

    scenario_path = (
        Path("scenarios/formal") / scenario_id.lower().replace("-", "_") / "scenario.yaml"
    )
    legacy_document = yaml.safe_load(scenario_path.read_bytes())
    for event in legacy_document["scenario"]["events"]:
        payload = event.get("payload", {})
        if payload.get("environment_ref") == binding.exact_ref:
            payload["environment_ref"] = binding.exact_ref.replace("@2.1.0", "@2.0.0")
    legacy = ScenarioCompilerV2(catalog=catalog).compile(
        ScenarioPackageV2.from_mapping(copy.deepcopy(legacy_document))
    )
    assert legacy.catalog_hash == resolved.catalog_hash
    assert legacy.resolved_hash != resolved.resolved_hash
    legacy_binding = next(
        event for event in legacy.events if event.id == event_id
    ).payload.environment_binding
    assert legacy_binding.exact_ref.endswith("@2.0.0")


def test_cloudy_switch_changes_sensor_range_at_the_declared_tick_and_survives_restore() -> None:
    """S4-02/S4-04: generic sensor consumption, event receipt, and checkpoint agree."""

    session = create_formal_session_v2("MD-AD-002-MEDIUM", session_id="ef03.cloudy", seed=113)
    session.load().start()
    try:
        world = session._mutable_world()
        entity = world._entities["defender.shore-ew"]
        sensor = entity.definition.resource_bindings["sensors"][0]

        before = world._profile_with_capability_modifiers(
            entity=entity, role="sensors", binding=sensor, tick=world.tick
        )
        assert before["range_m"] == pytest.approx(40000.0)

        last_receipt = None
        for tick in range(600):
            last_receipt = session.step(operation_id=f"ef03.cloudy.{tick}", expected_tick=tick)
        assert last_receipt is not None and last_receipt.tick == 600
        after = world._profile_with_capability_modifiers(
            entity=entity, role="sensors", binding=sensor, tick=world.tick
        )
        assert after["range_m"] == pytest.approx(40000.0 * 0.88)

        typed = [
            item
            for event_receipt in last_receipt.world_receipt.event_receipts
            for item in event_receipt.typed_event_receipts
            if item.event_id == "event.weather-cloudy"
        ]
        assert len(typed) == 1
        assert typed[0].payload["environment_binding"].exact_ref == "environment.cloudy@2.1.0"

        checkpoint = world.checkpoint()
        restored_world = session.world_factory.restore_checkpoint(
            checkpoint,
            resolved=session.resolved,
            model_registry=session.world_factory._model_registry,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            expected_session_id=session.session_id,
            expected_seed=session.seed,
        )
        restored_entity = restored_world._entities["defender.shore-ew"]
        restored_sensor = restored_entity.definition.resource_bindings["sensors"][0]
        restored_profile = restored_world._profile_with_capability_modifiers(
            entity=restored_entity,
            role="sensors",
            binding=restored_sensor,
            tick=restored_world.tick,
        )
        assert restored_profile["range_m"] == pytest.approx(after["range_m"])
        assert restored_world.checkpoint().checkpoint_hash == checkpoint.checkpoint_hash
        restored_world.close()
    finally:
        session.stop().close()


def test_environment_contract_uses_generic_modifier_pipeline_without_visibility_scale_branch() -> (
    None
):
    """S4-02: the only functional declaration is the standard capability key."""

    import openmdbench.world.factory_v2 as factory

    source = inspect.getsource(factory)
    assert "MD-AD-002" not in source
    assert "visibility_scale" not in source

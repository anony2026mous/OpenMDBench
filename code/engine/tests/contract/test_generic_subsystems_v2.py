"""RF-09 capability-driven subsystem contracts."""

from __future__ import annotations

from openmdbench.systems.generic_v2 import GenericSubsystemEngineV2, SubsystemEntityFactV2
from openmdbench.world.factory_v2 import WorldCheckpointV2
from tests.integration.test_session_action_world_v2 import _session


def _facts(reverse: bool = False) -> tuple[SubsystemEntityFactV2, ...]:
    values = (
        SubsystemEntityFactV2(
            entity_id="entity.alpha",
            faction_id="faction.alpha",
            position_m=(0.0, 0.0, 0.0),
            velocity_mps=(10.0, 0.0, 0.0),
            energy=1.0,
            sensors=(
                {
                    "exact_ref": "sensor.generic@2.0.0",
                    "range_m": 100.0,
                    "detection_probability": 1.0,
                },
            ),
            communications=({"exact_ref": "comm.generic@2.0.0"},),
            energy_profiles=(
                {
                    "exact_ref": "energy.generic@2.0.0",
                    "idle_rate_per_second": 0.01,
                    "motion_rate_per_meter": 0.001,
                },
            ),
        ),
        SubsystemEntityFactV2(
            entity_id="entity.beta",
            faction_id="faction.beta",
            position_m=(50.0, 0.0, 0.0),
            velocity_mps=(0.0, 0.0, 0.0),
            energy=None,
        ),
    )
    return tuple(reversed(values)) if reverse else values


def test_subsystems_are_order_independent_and_use_named_sensor_substreams() -> None:
    engine = GenericSubsystemEngineV2()
    first = engine.evaluate(
        entities=_facts(), tick=3, dt_seconds=1.0, seed=73, queued_message_count=0
    )
    second = engine.evaluate(
        entities=_facts(True), tick=3, dt_seconds=1.0, seed=73, queued_message_count=0
    )
    assert first == second
    assert first.contacts[0].detected
    assert first.contacts[0].rng_substream.startswith("sensor:")
    assert first.contacts[0].sensor_position_m == (0.0, 0.0, 0.0)
    assert first.contacts[0].target_position_m == (50.0, 0.0, 0.0)
    assert first.contacts[0].target_velocity_mps == (0.0, 0.0, 0.0)
    assert first.contacts[0].bearing_deg == 90.0
    assert first.contacts[0].elevation_deg == 0.0
    assert first.contacts[0].sensor_range_m == 100.0
    assert first.contacts[0].coordinate_frame == "local-m"
    assert first.energy[0].after == 0.98


def test_missing_capability_or_explicit_parameters_skips_without_platform_guessing() -> None:
    receipt = GenericSubsystemEngineV2().evaluate(
        entities=(
            SubsystemEntityFactV2(
                entity_id="facility.any",
                faction_id="neutral.any",
                position_m=(0.0, 0.0, 0.0),
                velocity_mps=(0.0, 0.0, 0.0),
                energy=None,
            ),
        ),
        tick=0,
        dt_seconds=1.0,
        seed=0,
        queued_message_count=0,
    )
    assert receipt.contacts == () and receipt.energy == ()
    assert receipt.communication.endpoint_ids == ()


def test_world_tick_publishes_subsystem_receipt_and_checkpoint_restores_it() -> None:
    session = _session("session.subsystems").load().start()
    applied = session.step(operation_id="tick.subsystems", expected_tick=0)
    subsystem = applied.world_receipt.subsystem_receipts[0]
    assert subsystem.stage_order == ("energy", "sensing", "communications")
    assert subsystem.communication.endpoint_ids == ("asset.000", "asset.001")
    checkpoint = session.world_view.checkpoint()
    restored = session.world_factory.restore_checkpoint(
        WorldCheckpointV2.model_validate(checkpoint),
        resolved=session.resolved,
        model_registry=session.world_factory._model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_session_id=session.session_id,
        expected_seed=session.seed,
    )
    restored_receipt = restored._world_tick_ledger["tick.subsystems"][1]
    assert restored_receipt.subsystem_receipts == applied.world_receipt.subsystem_receipts
    restored.close()
    session.stop().close()


def test_faction_observation_is_detached_and_does_not_expose_contact_truth_ids() -> None:
    session = _session("session.observation").load().start()
    before = session.world_view.tick
    observation = session.world_view.observation(observer_faction_id="coalition.alpha")
    assert observation.tick == before == session.world_view.tick
    assert tuple(item["entity_id"] for item in observation.own_entities) == ("asset.000",)
    encoded = observation.model_dump_json()
    assert "target_entity_id" not in encoded
    assert "asset.001" not in encoded
    session.stop().close()

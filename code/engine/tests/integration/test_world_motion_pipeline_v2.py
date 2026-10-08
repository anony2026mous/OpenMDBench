"""RF-05 World single-writer motion adjudication integration contracts."""

from __future__ import annotations

from typing import Any

import pytest
from tests.contract import test_world_checkpoint_v2 as checkpoint_fixture


def _api() -> Any:
    from openmdbench.world import factory_v2

    return factory_v2


def _candidate(world: Any, entity_id: str, x: float) -> Any:
    view = world.get(entity_id)
    resource_ref = view.definition.composition.dynamics_ref
    assert resource_ref is not None
    evidence = view.adapter_diagnostics[resource_ref]
    return _api().MotionCandidateV2.from_adapter_output(
        entity_id=entity_id,
        position_m=(x, 2.0, 3.0),
        velocity_mps=(10.0, 0.0, 0.0),
        dynamics_resource_ref=resource_ref,
        model_ref=evidence.model_ref,
        adapter_instance_id=evidence.instance_id,
        resolved_hash=world.resolved_hash,
        provider_receipt=evidence.last_output_receipt,
    )


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_world_applies_motion_candidates_atomically_and_order_independently(count: int) -> None:
    forward, _resolved, _registry, _factory = checkpoint_fixture._built(count)
    reverse, _resolved2, _registry2, _factory2 = checkpoint_fixture._built(count)
    candidates = tuple(
        _candidate(forward, f"asset.{index:03d}", float(index + 1)) for index in range(count)
    )
    reverse_candidates = tuple(
        _candidate(reverse, f"asset.{index:03d}", float(index + 1)) for index in range(count)
    )
    first = forward.apply_motion_candidates(
        candidates, expected_tick=0, operation_id="motion.000", dt_seconds=0.1
    )
    second = reverse.apply_motion_candidates(
        tuple(reversed(reverse_candidates)),
        expected_tick=0,
        operation_id="motion.000",
        dt_seconds=0.1,
    )
    assert first == second
    forward_snapshot = forward.semantic_snapshot()
    reverse_snapshot = reverse.semantic_snapshot()
    assert len(forward_snapshot.pop("consumed_provider_receipts")) == count
    assert len(reverse_snapshot.pop("consumed_provider_receipts")) == count
    assert forward_snapshot == reverse_snapshot
    assert tuple(view.id for view in forward.entities_stable()) == tuple(
        f"asset.{index:03d}" for index in range(count)
    )


def test_motion_pipeline_rolls_back_all_entities_and_checkpoint_on_one_invalid_candidate() -> None:
    world, _resolved, _registry, _factory = checkpoint_fixture._built(10)
    before = world.checkpoint()
    candidates = tuple(
        _candidate(world, f"asset.{index:03d}", float(index + 1)) for index in range(10)
    )
    invalid = replace_candidate(candidates[7], position_m=(float("nan"), 0.0, 0.0))
    with pytest.raises(_api().MotionPipelineErrorV2) as captured:
        world.apply_motion_candidates(
            (*candidates[:7], invalid, *candidates[8:]),
            expected_tick=0,
            operation_id="motion.rollback",
            dt_seconds=0.1,
        )
    assert captured.value.code == "world.motion_candidate_invalid"
    assert world.checkpoint() == before


def replace_candidate(candidate: Any, **changes: Any) -> Any:
    from dataclasses import replace

    return replace(candidate, **changes)


def test_motion_collision_only_emits_damage_intents_and_never_mutates_health() -> None:
    world, _resolved, _registry, _factory = checkpoint_fixture._built(2)
    before_health = {view.id: view.state.health for view in world.entities_stable()}
    receipt = world.apply_motion_candidates(
        (_candidate(world, "asset.000", 1.0), _candidate(world, "asset.001", 1.0)),
        expected_tick=0,
        operation_id="motion.collision",
        dt_seconds=0.1,
    )
    assert receipt.collision_events
    assert {item.target_entity_id for item in receipt.damage_intents} == {
        "asset.000",
        "asset.001",
    }
    assert {view.id: view.state.health for view in world.entities_stable()} == before_health


def test_motion_pipeline_checkpoint_roundtrip_preserves_dynamic_zone_state() -> None:
    world, resolved, registry, factory = checkpoint_fixture._built(1)
    world.set_zone_activation(
        zone_id="zone.synthetic", active=False, expected_tick=0, operation_id="zone.000"
    )
    world.apply_motion_candidates(
        (_candidate(world, "asset.000", 4.0),),
        expected_tick=0,
        operation_id="motion.checkpoint",
        dt_seconds=0.1,
    )
    checkpoint = world.checkpoint()
    restored = factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    assert restored.semantic_snapshot() == world.semantic_snapshot()
    assert restored.zone_activation_snapshot() == world.zone_activation_snapshot()


def test_checkpoint_freezes_motion_spatial_clock_zone_topology_and_ledger() -> None:
    world, resolved, registry, factory = checkpoint_fixture._built(1)
    world.set_zone_activation(
        zone_id="zone.synthetic", active=False, expected_tick=0, operation_id="zone.anchor"
    )
    world.apply_motion_candidates(
        (_candidate(world, "asset.000", 8.0),),
        expected_tick=0,
        operation_id="motion.anchor",
        dt_seconds=0.25,
        tick_start_time_seconds=12.5,
    )
    checkpoint = world.checkpoint()
    assert checkpoint.zone_activation_state
    assert checkpoint.motion_ledger[0].operation_id == "motion.anchor"
    assert checkpoint.spatial_clock.tick_start_time_seconds == pytest.approx(12.5)
    assert checkpoint.boundary_topology_hash == world.boundary_topology_hash
    restored = factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    assert restored.checkpoint() == checkpoint


@pytest.mark.parametrize(
    "attack",
    ("fake_ref", "other_entity", "wrong_model", "wrong_adapter", "wrong_resolved", "replay"),
)
def test_motion_candidate_requires_exact_dynamics_adapter_and_resolved_anchor_with_rollback(
    attack: str,
) -> None:
    world, resolved, _registry, _factory = checkpoint_fixture._built(2)
    before = world.checkpoint()
    resource_ref = world.get("asset.000").definition.composition.dynamics_ref
    assert resource_ref is not None
    evidence = world.get("asset.000").adapter_diagnostics[resource_ref]
    candidate = _api().MotionCandidateV2.from_adapter_output(
        entity_id="asset.000",
        position_m=(4.0, 2.0, 3.0),
        velocity_mps=(10.0, 0.0, 0.0),
        dynamics_resource_ref=evidence.resource_ref,
        model_ref=evidence.model_ref,
        adapter_instance_id=evidence.instance_id,
        resolved_hash=resolved.resolved_hash,
        provider_receipt=evidence.last_output_receipt,
    )
    changes = {
        "fake_ref": {"dynamics_resource_ref": "dynamics.fake@2.0.0"},
        "other_entity": {"entity_id": "asset.001"},
        "wrong_model": {"model_ref": "model.fake@2.0.0"},
        "wrong_adapter": {"adapter_instance_id": "adapter.fake"},
        "wrong_resolved": {"resolved_hash": "sha256:" + "0" * 64},
        "replay": {"provider_receipt": evidence.previous_output_receipt},
    }[attack]
    forged = replace_candidate(candidate, **changes)
    with pytest.raises(_api().MotionPipelineErrorV2) as captured:
        world.apply_motion_candidates(
            (forged,),
            expected_tick=0,
            operation_id=f"motion.attack.{attack}",
            dt_seconds=0.1,
            tick_start_time_seconds=0.0,
        )
    assert captured.value.code.startswith("world.motion_")
    assert world.checkpoint() == before


@pytest.mark.parametrize(
    "omitted", ("resource_ref", "model_ref", "adapter_id", "resolved_hash", "receipt")
)
def test_dynamics_motion_candidate_requires_complete_provenance_all_or_none(omitted: str) -> None:
    api = _api()
    values: dict[str, Any] = {
        "entity_id": "entity.dynamic",
        "position_m": (1.0, 2.0, 3.0),
        "velocity_mps": (4.0, 5.0, 6.0),
        "dynamics_resource_ref": "dynamics.synthetic@2.0.0",
        "model_ref": "model.synthetic@2.0.0",
        "adapter_instance_id": "adapter.synthetic.001",
        "resolved_hash": "sha256:" + "3" * 64,
        "provider_receipt": "receipt.synthetic.001",
    }
    field = {
        "resource_ref": "dynamics_resource_ref",
        "model_ref": "model_ref",
        "adapter_id": "adapter_instance_id",
        "resolved_hash": "resolved_hash",
        "receipt": "provider_receipt",
    }[omitted]
    values[field] = None
    with pytest.raises(api.MotionPipelineErrorV2) as captured:
        api.MotionCandidateV2(**values)
    assert captured.value.code == "world.motion_provenance_partial"


def test_no_dynamics_candidate_has_explicit_distinct_type_and_path() -> None:
    api = _api()
    candidate = api.KinematicMotionCandidateV2(
        entity_id="entity.kinematic",
        position_m=(1.0, 2.0, 3.0),
        velocity_mps=(0.0, 0.0, 0.0),
        resolved_hash="sha256:" + "4" * 64,
    )
    assert candidate.provenance_kind == "no_dynamics"
    with pytest.raises(api.MotionPipelineErrorV2):
        api.MotionCandidateV2(
            entity_id=candidate.entity_id,
            position_m=candidate.position_m,
            velocity_mps=candidate.velocity_mps,
        )


@pytest.mark.parametrize("receipt", ("", "forged", "receipt.previous"))
def test_motion_provider_receipt_invalid_or_replayed_rolls_back(receipt: str) -> None:
    world, _resolved, _registry, _factory = checkpoint_fixture._built(1)
    before = world.checkpoint()
    with pytest.raises(_api().MotionPipelineErrorV2):
        world.apply_motion_candidates(
            (
                _api().MotionCandidateV2(
                    entity_id="asset.000",
                    position_m=(1, 2, 3),
                    velocity_mps=(0, 0, 0),
                    dynamics_resource_ref="dynamics.synthetic@2.0.0",
                    model_ref="model.synthetic@2.0.0",
                    adapter_instance_id="adapter.synthetic",
                    resolved_hash=world.resolved_hash,
                    provider_receipt=receipt,
                ),
            ),
            expected_tick=0,
            operation_id=f"motion.receipt.{receipt or 'empty'}",
            dt_seconds=0.1,
            tick_start_time_seconds=0.0,
        )
    assert world.checkpoint() == before

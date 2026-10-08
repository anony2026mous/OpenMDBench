"""BUG-V2-001 lifecycle-to-motion eligibility contract regressions.

The fixture is deliberately generic: it uses the existing two-entity resolved
scenario, then applies typed World damage at a tick boundary.  It must never
depend on MD-AD-002 names, faction labels, or a scene-specific lifecycle path.
"""

from __future__ import annotations

from typing import Any

import pytest
from openmdbench.schemas.domain_v2 import DamageIntentV2
from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2
from openmdbench.sessions.lifecycle_v2 import (
    DiscreteActionStatusV2,
    PersistentCommandStatusV2,
    SessionLifecycleV2,
)


def _session(identifier: str = "session.motion-eligibility") -> SessionLifecycleV2:
    from tests.integration import test_session_action_world_v2 as fixture

    return fixture._session(identifier).load().start()


def _authority(session: SessionLifecycleV2, entity_id: str) -> str:
    from tests.integration import test_session_action_world_v2 as fixture

    return fixture._authority(session, entity_id)


def _navigation_batch(
    session: SessionLifecycleV2,
    *,
    command_id: str,
    action_id: str | None = None,
    valid_until_tick: int = 4,
) -> Any:
    from tests.integration import test_session_action_world_v2 as fixture

    batch = fixture._batch(
        session,
        batch_id=f"batch.{command_id}",
        idempotency_key=f"idem.{command_id}",
        command_id=command_id,
        action_id=action_id or f"action.{command_id}",
        valid_until_tick=valid_until_tick,
    )
    if action_id is None:
        return batch.model_copy(update={"discrete_actions": ()})
    return batch


def _typed_damage(
    session: SessionLifecycleV2,
    *,
    target_id: str,
    magnitude: float,
    intent_id: str,
) -> Any:
    """Commit typed weapon damage at the current World boundary."""

    world = session._mutable_world()
    other_id = "asset.001" if target_id == "asset.000" else "asset.000"
    intent = DamageIntentV2(
        intent_id=intent_id,
        tick=world.tick,
        source_entity_id=other_id,
        target_entity_id=target_id,
        effect_ref="effect.arbitrary@2.4.1",
        damage_model_ref="damage.arbitrary@2.4.1",
        magnitude=magnitude,
        evidence_hash="sha256:" + "1" * 64,
        source_kind="weapon",
    )
    return world.apply_damage_transaction(
        intents={f"weapon:{intent_id}": intent},
        expected_tick=world.tick,
        operation_id=f"damage.{intent_id}",
    )


def _step(session: SessionLifecycleV2, operation_id: str) -> Any:
    return session.step(operation_id=operation_id, expected_tick=session.world_view.tick)


def _children(receipt: Any) -> dict[str, Any]:
    return {child.child_id: child for child in receipt.child_receipts}


def test_b01_destroyed_or_disabled_in_prior_tick_is_not_motion_eligible() -> None:
    """B01: a disabled dynamics entity cannot create a next-tick command hole."""

    session = _session("session.b01")
    damage = _typed_damage(
        session, target_id="asset.000", magnitude=0.75, intent_id="b01.disabled"
    )
    assert damage.results[0].lifecycle_after.value == "disabled"

    receipt = _step(session, "tick.b01")

    assert receipt.world_receipt.tick == 1
    assert tuple(item.entity_id for item in receipt.world_receipt.dynamics_receipts) == ("asset.001",)
    assert session.world_view.get("asset.000").state.lifecycle == "disabled"


def test_b02_pre_motion_invalidation_cancels_queued_children_deterministically() -> None:
    """B02: queued motion/fire children become cancellation/rejection evidence."""

    session = _session("session.b02")
    batch = _navigation_batch(session, command_id="command.b02", action_id="action.b02")
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session, "asset.000"),
        operation_id="submit.b02",
        expected_tick=0,
    )
    _typed_damage(session, target_id="asset.000", magnitude=0.75, intent_id="b02.disabled")

    receipt = _step(session, "tick.b02")
    children = _children(receipt)

    assert children["command.b02"].status == PersistentCommandStatusV2.CANCELLED.value
    assert children["command.b02"].error_code == "session.entity_lifecycle_invalid"
    assert children["action.b02"].status == DiscreteActionStatusV2.REJECTED.value
    assert children["action.b02"].error_code == "session.entity_lifecycle_invalid"
    assert receipt.consumed_discrete_action_ids == ("action.b02",)
    assert receipt.world_receipt.combat_receipts == ()


def test_b03_persistent_command_is_cancelled_once_and_never_resurrects() -> None:
    """B03: prior active navigation is removed at the first ineligible boundary."""

    session = _session("session.b03")
    batch = _navigation_batch(session, command_id="command.b03", valid_until_tick=5)
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session, "asset.000"),
        operation_id="submit.b03",
        expected_tick=0,
    )
    first = _step(session, "tick.b03.0")
    assert first.activated_command_ids == ("command.b03",)
    _typed_damage(session, target_id="asset.000", magnitude=0.75, intent_id="b03.disabled")

    cancelled = _step(session, "tick.b03.1")
    assert _children(cancelled)["command.b03"].status == PersistentCommandStatusV2.CANCELLED.value
    assert tuple(item.command_id for item in session.queue_view.persistent_commands) == ()

    later = _step(session, "tick.b03.2")
    assert "command.b03" not in _children(later)
    assert tuple(item.command_id for item in session.queue_view.persistent_commands) == ()


def test_b04_tick_start_eligible_move_and_fire_remain_exactly_once_before_damage() -> None:
    """B04: a legal tick is not retroactively cancelled by later lifecycle change."""

    session = _session("session.b04")
    batch = _navigation_batch(session, command_id="command.b04", action_id="action.b04")
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session, "asset.000"),
        operation_id="submit.b04",
        expected_tick=0,
    )
    before = dict(session.world_view.get("asset.000").state.ammunition)
    first = _step(session, "tick.b04.0")
    assert first.consumed_discrete_action_ids == ("action.b04",)
    assert _children(first)["action.b04"].status in {
        DiscreteActionStatusV2.EXECUTED.value,
        DiscreteActionStatusV2.REJECTED.value,
    }

    _typed_damage(session, target_id="asset.000", magnitude=0.75, intent_id="b04.disabled")
    second = _step(session, "tick.b04.1")
    assert second.consumed_discrete_action_ids == ()
    assert dict(session.world_view.get("asset.000").state.ammunition) != before or (
        _children(first)["action.b04"].status == DiscreteActionStatusV2.REJECTED.value
    )


@pytest.mark.parametrize("policy", ("wreck", "despawn"))
def test_b05_b06_destroyed_policy_preserves_only_configured_wreck_behavior(
    monkeypatch: pytest.MonkeyPatch, policy: str
) -> None:
    """B05/B06: a data policy, rather than dynamics presence, selects wreck/despawn."""

    from tests.contract import test_md_int_003_damage_lifecycle as lifecycle_fixture
    from tests.contract import test_md_int_003_surface_combat as surface_fixture

    system = lifecycle_fixture._surface_system_with_destroyed_policy(monkeypatch, policy=policy)
    world = system.world
    target_id = "renamed.surface.001"
    world._entities[target_id].state.health = 0.4
    world.advance_tick(surface_fixture._tick_input(world, 0, requests=(surface_fixture._request(),)))
    world.advance_tick(surface_fixture._tick_input(world, 1))

    record = world.destroyed_lifecycle_ledger[target_id]
    assert record["policy"] == policy
    if policy == "wreck":
        assert world.get(target_id).state.lifecycle == "destroyed"
        assert world._is_static_wreck(target_id)
    else:
        assert world.get_optional(target_id) is None
        assert target_id in world.tombstones


def test_b07_checkpoint_at_invalidation_boundary_restores_same_cancellation() -> None:
    """B07: checkpoint restoration derives the same eligibility and receipt evidence."""

    session = _session("session.b07")
    batch = _navigation_batch(session, command_id="command.b07", action_id="action.b07")
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session, "asset.000"),
        operation_id="submit.b07",
        expected_tick=0,
    )
    _typed_damage(session, target_id="asset.000", magnitude=0.75, intent_id="b07.disabled")
    checkpoint = session.checkpoint()
    restored = SessionLifecycleV2.restore(
        checkpoint=checkpoint,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        resolved=session.resolved,
        expected_resolved_hash=session.resolved.resolved_hash,
        model_registry=session.world_factory._model_registry,
        expected_model_registry_hash=session.model_registry_hash,
        world_factory=session.world_factory,
    )

    original = _step(session, "tick.b07.replay")
    recovered = _step(restored, "tick.b07.replay")
    assert original.child_receipts == recovered.child_receipts
    assert original.world_receipt == recovered.world_receipt


def test_b08_nonactive_queued_action_is_rejected_without_combat_side_effect() -> None:
    """B08: rejection is consumed evidence, not a later replay opportunity."""

    session = _session("session.b08")
    batch = _navigation_batch(session, command_id="command.b08", action_id="action.b08")
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session, "asset.000"),
        operation_id="submit.b08",
        expected_tick=0,
    )
    ammunition_before = dict(session.world_view.get("asset.000").state.ammunition)
    _typed_damage(session, target_id="asset.000", magnitude=0.75, intent_id="b08.disabled")

    receipt = _step(session, "tick.b08")
    assert _children(receipt)["action.b08"].status == DiscreteActionStatusV2.REJECTED.value
    assert receipt.world_receipt.combat_receipts == ()
    assert dict(session.world_view.get("asset.000").state.ammunition) == ammunition_before
    assert session.queue_view.consumed_discrete_action_ids == ("action.b08",)


def test_b09_lifecycle_spawn_with_no_explicit_action_has_one_safe_control() -> None:
    """B09: a new dynamic entity has a complete command set at its first boundary."""

    from tests.contract import test_combat_damage_v2 as combat_fixture
    from tests.contract import test_world_lifecycle_v2 as lifecycle_fixture
    from openmdbench.sessions.lifecycle_v2 import RunnerModeV2
    from openmdbench.world.factory_v2 import WorldFactoryV2

    template = combat_fixture._native_lifecycle_world(lifecycle_fixture._spawn_events(1, tick=1))
    registry = template._entity_factory._model_registry
    resolved = template._resolved_scenario
    session = SessionLifecycleV2.create(
        session_id="session.b09",
        seed=73,
        resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash,
        catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=registry),
        runner_mode=RunnerModeV2.LOCKSTEP,
        physics_dt_seconds=1.0,
        decision_interval_ticks=1,
    )
    session.load().start()
    receipt = _step(session, "tick.b09")

    assert receipt.world_receipt.dynamics_receipts[-1].entity_id == "future.asset.000"
    assert session.world_view.get("future.asset.000").state.lifecycle == "active"


def test_b10_simultaneous_damage_is_stable_when_source_mapping_order_changes() -> None:
    """B10: multi-entity lifecycle outcomes do not depend on source-map traversal."""

    def apply(order: tuple[str, str]) -> tuple[Any, Any]:
        session = _session(f"session.b10.{order[0]}")
        world = session._mutable_world()
        intents: dict[str, DamageIntentV2] = {}
        for index, target_id in enumerate(order):
            source_id = "asset.001" if target_id == "asset.000" else "asset.000"
            intent_id = f"b10.{index}.{target_id}"
            intents[f"weapon:{intent_id}"] = DamageIntentV2(
                intent_id=intent_id,
                tick=0,
                source_entity_id=source_id,
                target_entity_id=target_id,
                effect_ref="effect.arbitrary@2.4.1",
                damage_model_ref="damage.arbitrary@2.4.1",
                magnitude=0.75,
                evidence_hash="sha256:" + f"{index + 2:064x}",
                source_kind="weapon",
            )
        receipt = world.apply_damage_transaction(
            intents=intents, expected_tick=0, operation_id=f"damage.b10.{order[0]}"
        )
        return receipt, tuple(
            (entity_id, world.get(entity_id).state.lifecycle)
            for entity_id in ("asset.000", "asset.001")
        )

    forward, forward_states = apply(("asset.000", "asset.001"))
    reverse, reverse_states = apply(("asset.001", "asset.000"))
    assert forward_states == reverse_states == (("asset.000", "disabled"), ("asset.001", "disabled"))
    assert tuple(result.target_entity_id for result in forward.results) == tuple(
        result.target_entity_id for result in reverse.results
    )


def test_expired_command_fallback_remains_checkpoint_consistent() -> None:
    """A synthesized safe hold is audit evidence with a matching status entry."""

    session = _session("session.fallback-checkpoint")
    batch = _navigation_batch(
        session,
        command_id="command.fallback-checkpoint",
        valid_until_tick=0,
    )
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session, "asset.000"),
        operation_id="submit.fallback-checkpoint",
        expected_tick=0,
    )
    _step(session, "tick.fallback-checkpoint.0")
    receipt = _step(session, "tick.fallback-checkpoint.1")

    assert receipt.fallback_command_ids == ("fallback.safe_hold.asset.000",)
    assert session.action_status_view.statuses["fallback.safe_hold.asset.000"] == "active"
    assert session.checkpoint().child_ledger

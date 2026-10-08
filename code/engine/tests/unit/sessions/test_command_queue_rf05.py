"""RF-05 command lifecycle and tick-boundary semantics."""

from __future__ import annotations

import math

import pytest
from openmdbench.schemas.platform import (
    ActionBatch,
    CommandStatus,
    DiscreteAction,
    PersistentCommand,
    StableErrorCode,
)
from openmdbench.sessions.commands import CommandConflictError, CommandQueue, CommandRejectedError


def persistent(
    command_id: str = "nav-1", *, entity: str = "blue-1", until: int = 10
) -> PersistentCommand:
    return PersistentCommand(
        schema_version="1.0",
        command_id=command_id,
        command_type="navigation",
        entity_id=entity,
        based_on_tick=0,
        valid_until_tick=until,
        payload={"speed_mps": 30.0, "heading_deg": 90.0},
    )


def discrete(action_id: str = "fire-1", *, until: int = 10) -> DiscreteAction:
    return DiscreteAction(
        schema_version="1.0",
        action_id=action_id,
        action_type="fire_weapon",
        entity_id="blue-1",
        based_on_tick=0,
        valid_until_tick=until,
        payload={"target_id": "red-1", "weapon_id": "missile"},
    )


def batch(
    command_id: str = "batch-1",
    *,
    persistent_commands: tuple[PersistentCommand, ...] = (),
    discrete_actions: tuple[DiscreteAction, ...] = (),
    until: int = 10,
) -> ActionBatch:
    return ActionBatch(
        schema_version="1.0",
        session_id="session-1",
        command_id=command_id,
        based_on_tick=0,
        valid_until_tick=until,
        persistent_commands=persistent_commands,
        discrete_actions=discrete_actions,
    )


def test_persistent_holds_discrete_consumes_once_and_receipt_is_idempotent() -> None:
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue", "red-1": "red"})
    submitted = batch(persistent_commands=(persistent(),), discrete_actions=(discrete(),))
    first = queue.submit(submitted, current_tick=0, actor_side="blue")
    duplicate = queue.submit(submitted, current_tick=0, actor_side="blue")
    assert duplicate == first
    tick_one = queue.apply_tick(1)
    tick_two = queue.apply_tick(2)
    assert [item.command_id for item in tick_one.persistent_commands] == ["nav-1"]
    assert [item.action_id for item in tick_one.discrete_actions] == ["fire-1"]
    assert [item.command_id for item in tick_two.persistent_commands] == ["nav-1"]
    assert tick_two.discrete_actions == ()
    assert queue.result("fire-1").status is CommandStatus.APPLIED
    queue.complete_action("fire-1", 1, executed=True)
    assert queue.result("fire-1").status is CommandStatus.EXECUTED


def test_same_id_different_content_conflicts_without_side_effect() -> None:
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue"})
    queue.submit(batch(persistent_commands=(persistent(),)), current_tick=0, actor_side="blue")
    changed = batch(persistent_commands=(persistent(until=9),), until=9)
    with pytest.raises(CommandConflictError):
        queue.submit(changed, current_tick=0, actor_side="blue")
    assert queue.pending_count == 1


def test_replacement_occurs_at_tick_boundary_and_old_result_is_replaced() -> None:
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue"})
    queue.submit(batch(persistent_commands=(persistent(),)), current_tick=0, actor_side="blue")
    queue.apply_tick(1)
    replacement = persistent("nav-2")
    queue.submit(batch("batch-2", persistent_commands=(replacement,)), 1, actor_side="blue")
    applied = queue.apply_tick(2)
    assert [item.command_id for item in applied.persistent_commands] == ["nav-2"]
    assert queue.result("nav-1").status is CommandStatus.REPLACED


@pytest.mark.parametrize(
    ("candidate", "tick", "side", "error_code"),
    (
        (batch(until=0), 1, "blue", StableErrorCode.ACTION_STALE),
        (
            batch(persistent_commands=(persistent(entity="unknown"),)),
            0,
            "blue",
            StableErrorCode.COMMAND_REJECTED,
        ),
        (
            batch(persistent_commands=(persistent(entity="blue-1"),)),
            0,
            "red",
            StableErrorCode.ACTION_UNAUTHORIZED,
        ),
    ),
)
def test_stale_unknown_and_wrong_side_batches_are_atomically_rejected(
    candidate: ActionBatch, tick: int, side: str, error_code: StableErrorCode
) -> None:
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue"})
    with pytest.raises(CommandRejectedError) as error:
        queue.submit(candidate, tick, actor_side=side)
    assert error.value.error_code is error_code
    assert queue.pending_count == 0


def test_nonfinite_payload_is_rejected_by_schema_before_queue() -> None:
    raw = persistent().model_dump(mode="json")
    raw["payload"]["speed_mps"] = math.nan
    with pytest.raises(ValueError, match="finite"):
        PersistentCommand.model_validate(raw)


def test_expired_discrete_does_not_execute_after_connectivity_recovers() -> None:
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue"})
    queue.submit(batch(discrete_actions=(discrete(until=1),), until=1), 0, actor_side="blue")
    assert queue.apply_tick(1, connected_entities=frozenset()).discrete_actions == ()
    assert queue.apply_tick(2, connected_entities=frozenset({"blue-1"})).discrete_actions == ()
    assert queue.result("fire-1").status is CommandStatus.EXPIRED


def test_input_order_does_not_change_stable_application_order() -> None:
    one = persistent("z", entity="blue-2")
    two = persistent("a", entity="blue-1")
    outputs = []
    for commands in ((one, two), (two, one)):
        queue = CommandQueue("session-1", entity_sides={"blue-1": "blue", "blue-2": "blue"})
        queue.submit(batch(persistent_commands=commands), 0, actor_side="blue")
        outputs.append(queue.apply_tick(1).persistent_commands)
    assert outputs[0] == outputs[1]


def test_destroyed_entity_terminates_command_with_safe_hold() -> None:
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue"})
    queue.submit(batch(persistent_commands=(persistent(),)), 0, actor_side="blue")
    queue.apply_tick(1)
    applied = queue.apply_tick(2, available_entities=frozenset())
    assert applied.persistent_commands == ()
    assert applied.fallbacks == (("blue-1", "safe_hold"),)
    assert queue.result("nav-1").status is CommandStatus.FAILED


def test_request_stops_navigation_and_sensor_hold_without_repeated_ammo_use() -> None:
    sensor = PersistentCommand(
        schema_version="1.0",
        command_id="sensor-1",
        command_type="sensor_mode",
        entity_id="blue-1",
        based_on_tick=0,
        valid_until_tick=10,
        payload={"mode": "active_search"},
    )
    queue = CommandQueue("session-1", entity_sides={"blue-1": "blue"})
    queue.submit(
        batch(
            persistent_commands=(persistent(), sensor),
            discrete_actions=(discrete(),),
        ),
        0,
        actor_side="blue",
    )
    ammo = 2
    modes = []
    for tick in range(1, 5):
        applied = queue.apply_tick(tick)
        ammo -= len(applied.discrete_actions)
        for action in applied.discrete_actions:
            queue.complete_action(action.action_id, tick, executed=True)
        modes.append(tuple(item.command_type for item in applied.persistent_commands))
    assert modes == [("navigation", "sensor_mode")] * 4
    assert ammo == 1

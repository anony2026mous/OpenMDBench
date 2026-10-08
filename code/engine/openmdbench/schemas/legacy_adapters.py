"""One-way adapters from pre-RF-01 action DTOs to the platform 1.0 contract."""

from __future__ import annotations

from typing import Any

from openmdbench.policies.actions import ActionBatch as LegacyActionBatch
from openmdbench.schemas.md_ad_002_interface import RedActionBatch
from openmdbench.schemas.platform import ActionBatch, DiscreteAction, PersistentCommand


def _persistent(
    *,
    command_id: str,
    entity_id: str,
    tick: int,
    valid_until_tick: int,
    command_type: str,
    payload: dict[str, Any],
) -> PersistentCommand:
    return PersistentCommand.model_validate(
        {
            "schema_version": "1.0",
            "command_id": command_id,
            "entity_id": entity_id,
            "command_type": command_type,
            "based_on_tick": tick,
            "valid_until_tick": valid_until_tick,
            "payload": payload,
        }
    )


def legacy_action_batch_to_platform(
    batch: LegacyActionBatch,
    *,
    session_id: str,
    command_id: str,
    valid_until_tick: int,
) -> ActionBatch:
    """Adapt the original built-in-agent batch without mutating it."""
    persistent: list[PersistentCommand] = []
    discrete: list[DiscreteAction] = []
    for index, action in enumerate(batch.actions):
        persistent.append(
            _persistent(
                command_id=f"{command_id}:p:{index}",
                entity_id=action.entity_id,
                tick=batch.timestamp,
                valid_until_tick=valid_until_tick,
                command_type="navigation",
                payload={
                    "mode": action.navigation,
                    "target_m": action.target,
                    "speed_mps": action.speed_mps,
                },
            )
        )
        if action.engage_contact_id is not None and action.weapon_id is not None:
            discrete.append(
                DiscreteAction(
                    schema_version="1.0",
                    action_id=f"{command_id}:d:{index}:fire",
                    entity_id=action.entity_id,
                    action_type="fire_weapon",
                    based_on_tick=batch.timestamp,
                    valid_until_tick=valid_until_tick,
                    payload={
                        "contact_id": action.engage_contact_id,
                        "weapon_id": action.weapon_id,
                        "count": action.count,
                    },
                )
            )
        if action.ram_target_id is not None:
            discrete.append(
                DiscreteAction(
                    schema_version="1.0",
                    action_id=f"{command_id}:d:{index}:ram",
                    entity_id=action.entity_id,
                    action_type="ram",
                    based_on_tick=batch.timestamp,
                    valid_until_tick=valid_until_tick,
                    payload={"target_id": action.ram_target_id},
                )
            )
    return ActionBatch(
        schema_version="1.0",
        session_id=session_id,
        command_id=command_id,
        based_on_tick=batch.timestamp,
        valid_until_tick=valid_until_tick,
        persistent_commands=tuple(persistent),
        discrete_actions=tuple(discrete),
        extensions={"legacy_high_level_intent": batch.high_level_intent},
    )


def red_action_batch_to_platform(
    batch: RedActionBatch,
    *,
    session_id: str,
    command_id: str,
    valid_until_tick: int,
) -> ActionBatch:
    """Adapt the MD-AD-002 red-agent DTO into the platform 1.0 lifecycle model."""
    persistent: list[PersistentCommand] = []
    discrete: list[DiscreteAction] = []
    for index, action in enumerate(batch.actions):
        payload: dict[str, Any] = {
            "mode": action.navigation.mode,
            "target_m": action.navigation.target_m,
            "speed_mps": action.navigation.speed_mps,
        }
        if action.sensor is not None:
            payload["sensor_mode"] = action.sensor.mode
        if action.communication is not None:
            payload["relay_enabled"] = action.communication.relay_enabled
        if action.ciws_auto is not None:
            payload["ciws_auto"] = action.ciws_auto
        persistent.append(
            _persistent(
                command_id=f"{command_id}:p:{index}",
                entity_id=action.entity_id,
                tick=batch.timestamp,
                valid_until_tick=valid_until_tick,
                command_type="navigation",
                payload=payload,
            )
        )
        if action.engagement is not None:
            discrete.append(
                DiscreteAction(
                    schema_version="1.0",
                    action_id=f"{command_id}:d:{index}:fire",
                    entity_id=action.entity_id,
                    action_type="fire_weapon",
                    based_on_tick=batch.timestamp,
                    valid_until_tick=valid_until_tick,
                    payload=action.engagement.model_dump(mode="json"),
                )
            )
    return ActionBatch(
        schema_version="1.0",
        session_id=session_id,
        command_id=command_id,
        based_on_tick=batch.timestamp,
        valid_until_tick=valid_until_tick,
        persistent_commands=tuple(persistent),
        discrete_actions=tuple(discrete),
        extensions={
            "legacy_scenario_id": batch.scenario_id,
            "legacy_high_level_intent": batch.high_level_intent,
        },
    )


__all__ = ["legacy_action_batch_to_platform", "red_action_batch_to_platform"]

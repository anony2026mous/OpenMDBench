"""RF-01 RED contracts for generic action, event, replay, and error DTOs."""

from __future__ import annotations

import math
from typing import Any

import pytest
from openmdbench.schemas.interface_v2 import (
    ActionBatchV2,
    AuthorityEventV2,
    CheckpointMetadataV2,
    DiscreteActionV2,
    PersistentCommandV2,
    ReplayMetadataV2,
    StableErrorV2,
)
from pydantic import ValidationError

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64


def _persistent(**changes: Any) -> PersistentCommandV2:
    values: dict[str, Any] = {
        "schema_version": "2.0",
        "command_id": "navigation-17",
        "entity_id": "aircraft/arbitrary-47",
        "faction_id": "coalition.alpha",
        "command_type": "navigation",
        "based_on_tick": 40,
        "valid_until_tick": 80,
        "payload": {"target": {"position_m": [10.0, 20.0, 300.0]}},
    }
    values.update(changes)
    return PersistentCommandV2(**values)


def _discrete(**changes: Any) -> DiscreteActionV2:
    values: dict[str, Any] = {
        "schema_version": "2.0",
        "action_id": "fire-88",
        "entity_id": "aircraft/arbitrary-47",
        "faction_id": "coalition.alpha",
        "action_type": "fire_weapon",
        "based_on_tick": 40,
        "valid_until_tick": 41,
        "payload": {"weapon_ref": "weapons.interceptor@2.0.0", "contact_id": "opaque-9"},
    }
    values.update(changes)
    return DiscreteActionV2(**values)


def test_action_batch_separates_persistent_and_discrete_and_freezes_idempotency() -> None:
    batch = ActionBatchV2(
        schema_version="2.0",
        session_id="session-1",
        batch_id="batch-100",
        idempotency_key="client-attempt-100",
        faction_id="coalition.alpha",
        based_on_tick=40,
        valid_until_tick=80,
        persistent_commands=(_persistent(),),
        discrete_actions=(_discrete(),),
    )

    assert batch.persistent_commands[0].command_id == "navigation-17"
    assert batch.discrete_actions[0].action_id == "fire-88"
    assert batch.faction_id == "coalition.alpha"
    assert "red" not in batch.model_dump_json() and "blue" not in batch.model_dump_json()
    assert ActionBatchV2.model_validate_json(batch.model_dump_json()) == batch


@pytest.mark.parametrize(
    ("factory", "changes"),
    (
        (_persistent, {"valid_until_tick": 39}),
        (_discrete, {"valid_until_tick": 39}),
    ),
)
def test_command_and_action_reject_invalid_tick_ttl(factory: Any, changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="valid_until_tick|tick|TTL"):
        factory(**changes)


def test_action_batch_rejects_duplicate_ids_across_each_command_class() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        ActionBatchV2(
            schema_version="2.0",
            session_id="session-1",
            batch_id="batch-duplicate",
            idempotency_key="attempt-duplicate",
            faction_id="coalition.alpha",
            based_on_tick=40,
            valid_until_tick=80,
            persistent_commands=(_persistent(), _persistent()),
            discrete_actions=(_discrete(), _discrete()),
        )


def test_authority_event_carries_dynamic_participants_and_audit_evidence() -> None:
    event = AuthorityEventV2(
        schema_version="2.0",
        event_id="event-900",
        tick=42,
        sim_time_s=4.2,
        event_type="combat.weapon_resolved",
        faction_ids=("coalition.alpha", "opposition.zulu", "observer.neutral"),
        entity_ids=("aircraft/arbitrary-47", "surface/arbitrary-12"),
        evidence={
            "weapon_ref": "weapons.interceptor@2.0.0",
            "effect_ref": "effects.fragmentation@2.0.0",
            "probability": 0.75,
            "sample": 0.25,
            "damage": {"health_before": 1.0, "health_after": 0.3},
        },
    )

    assert event.faction_ids[2] == "observer.neutral"
    assert event.evidence["damage"]["health_after"] == 0.3
    assert AuthorityEventV2.model_validate_json(event.model_dump_json()) == event


def test_replay_and_checkpoint_metadata_freeze_all_reproducibility_hashes() -> None:
    replay = ReplayMetadataV2(
        schema_version="2.0",
        session_id="session-1",
        scenario_id="generic.exercise.any-name",
        engine_version="2.0.0",
        seed=73,
        resolved_hash=SHA_A,
        catalog_hashes={"platforms.generic@2.0.0": SHA_B},
        plugin_hashes={"models.dynamics@2.0.0": SHA_C},
        map_hash=SHA_D,
    )
    checkpoint = CheckpointMetadataV2(
        schema_version="2.0",
        session_id="session-1",
        scenario_id="generic.exercise.any-name",
        tick=42,
        engine_version="2.0.0",
        seed=73,
        resolved_hash=SHA_A,
        catalog_hashes={"platforms.generic@2.0.0": SHA_B},
        plugin_hashes={"models.dynamics@2.0.0": SHA_C},
        map_hash=SHA_D,
        checkpoint_hash=SHA_E,
        rng_streams=("dynamics", "sensor", "combat"),
    )

    assert replay.catalog_hashes["platforms.generic@2.0.0"] == SHA_B
    assert checkpoint.checkpoint_hash == SHA_E
    assert ReplayMetadataV2.model_validate_json(replay.model_dump_json()) == replay
    assert CheckpointMetadataV2.model_validate_json(checkpoint.model_dump_json()) == checkpoint


def test_stable_error_has_location_value_and_actionable_suggestion() -> None:
    error = StableErrorV2(
        schema_version="2.0",
        code="scenario.resource_incompatible",
        message="loadout exceeds platform slot capacity",
        path=("entities", "17", "loadout_ref"),
        value="loadouts.heavy@2.0.0",
        suggestion="select a compatible loadout or a platform with two payload slots",
        details={"required_slots": 2, "available_slots": 1},
    )

    assert error.path == ("entities", "17", "loadout_ref")
    assert error.value == "loadouts.heavy@2.0.0"
    assert error.suggestion.startswith("select")
    assert StableErrorV2.model_validate_json(error.model_dump_json()) == error


@pytest.mark.parametrize("bad", (math.nan, math.inf, -math.inf))
def test_all_interface_payloads_reject_nested_nonfinite_values(bad: float) -> None:
    with pytest.raises(ValidationError, match="finite"):
        AuthorityEventV2(
            schema_version="2.0",
            event_id="bad-number",
            tick=1,
            sim_time_s=0.1,
            event_type="diagnostic",
            faction_ids=("any.faction",),
            entity_ids=(),
            evidence={"nested": {"sample": bad}},
        )


def test_unknown_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError, match="extra"):
        StableErrorV2.model_validate(
            {
                "schema_version": "2.0",
                "code": "schema.invalid",
                "message": "invalid",
                "path": ("field",),
                "suggestion": "correct the field",
                "legacy_side": "red",
            }
        )


def test_payload_evidence_hashes_and_error_details_are_deeply_immutable() -> None:
    command = _persistent()
    event = AuthorityEventV2(
        schema_version="2.0",
        event_id="event-immutable",
        tick=1,
        sim_time_s=0.1,
        event_type="diagnostic",
        faction_ids=("any.faction",),
        entity_ids=("any-entity",),
        evidence={"nested": {"sequence": [1, 2]}},
    )
    replay = ReplayMetadataV2(
        schema_version="2.0",
        session_id="session-1",
        scenario_id="generic.exercise",
        engine_version="2.0.0",
        seed=1,
        resolved_hash=SHA_A,
        catalog_hashes={"resource@2.0.0": SHA_B},
        plugin_hashes={"plugin@2.0.0": SHA_C},
        map_hash=SHA_D,
    )

    with pytest.raises((TypeError, AttributeError)):
        command.payload["target"]["position_m"][0] = 99.0
    with pytest.raises((TypeError, AttributeError)):
        event.evidence["nested"]["sequence"] += (3,)
    with pytest.raises((TypeError, AttributeError)):
        replay.catalog_hashes["resource@2.0.0"] = SHA_E


@pytest.mark.parametrize(
    "factory",
    (
        lambda: _persistent(command_type="navigate_typo"),
        lambda: _discrete(action_type="launch_everything_typo"),
    ),
)
def test_action_and_command_types_are_controlled_identifiers(factory: Any) -> None:
    with pytest.raises(ValidationError):
        factory()


@pytest.mark.parametrize(
    "code",
    ("UPPERCASE.ERROR", "contains spaces", "leading-dot", ".schema.invalid", "schema..invalid"),
)
def test_stable_error_code_uses_machine_readable_dotted_format(code: str) -> None:
    with pytest.raises(ValidationError, match="code|string|pattern"):
        StableErrorV2(
            schema_version="2.0",
            code=code,
            message="invalid",
            suggestion="use a registered stable error code",
        )

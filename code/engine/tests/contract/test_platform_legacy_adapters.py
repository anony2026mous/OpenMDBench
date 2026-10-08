"""Compatibility tests for the intentionally temporary RF-01 adapters."""

from openmdbench.policies.actions import ActionBatch as LegacyBatch
from openmdbench.policies.actions import PlatformAction
from openmdbench.schemas.legacy_adapters import (
    legacy_action_batch_to_platform,
    red_action_batch_to_platform,
)
from openmdbench.schemas.md_ad_002_interface import (
    EngagementAction,
    NavigationAction,
    RedActionBatch,
    RedPlatformAction,
)
from openmdbench.schemas.platform import ActionBatch


def test_legacy_action_adapter_preserves_navigation_fire_and_ram() -> None:
    legacy = LegacyBatch(
        timestamp=4,
        actions=(
            PlatformAction(
                entity_id="blue-uav-1",
                navigation="move_to",
                target=(1.0, 2.0, 300.0),
                speed_mps=45.0,
                engage_contact_id="red-1",
                weapon_id="uav_interceptor_missile",
                ram_target_id="red-2",
            ),
        ),
        high_level_intent={"phase": "intercept"},
    )
    before = legacy.model_dump(mode="json")
    canonical = legacy_action_batch_to_platform(
        legacy, session_id="s-1", command_id="batch-1", valid_until_tick=8
    )

    assert [item.action_type for item in canonical.discrete_actions] == [
        "fire_weapon",
        "ram",
    ]
    assert canonical.persistent_commands[0].payload["target_m"] == [1.0, 2.0, 300.0]
    assert legacy.model_dump(mode="json") == before
    assert ActionBatch.model_validate_json(canonical.model_dump_json()) == canonical


def test_red_action_adapter_maps_engagement_and_versioned_extensions() -> None:
    legacy = RedActionBatch(
        scenario_id="MD-AD-002-MEDIUM",
        timestamp=7,
        actions=(
            RedPlatformAction(
                entity_id="red-uav-1",
                navigation=NavigationAction(
                    mode="move_to", target_m=(2.0, 3.0, 500.0), speed_mps=40.0
                ),
                engagement=EngagementAction(
                    contact_id="blue-1", weapon_id="uav_interceptor_missile"
                ),
            ),
        ),
    )
    canonical = red_action_batch_to_platform(
        legacy, session_id="s-2", command_id="batch-2", valid_until_tick=9
    )

    assert canonical.schema_version == "1.0"
    assert canonical.extensions["legacy_scenario_id"] == "MD-AD-002-MEDIUM"
    assert canonical.discrete_actions[0].payload["contact_id"] == "blue-1"

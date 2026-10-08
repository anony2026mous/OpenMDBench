from typing import Literal, cast

import pytest
from openmdbench.catalog.builtin_models import builtin_model_registry
from openmdbench.catalog.legacy_adapters import md_ad_002_catalog_definitions
from openmdbench.catalog.repository import CatalogRepository
from openmdbench.core.entities import ComponentState, Domain, Lifecycle, PlatformAsset, Side
from openmdbench.core.world import ContactTrack, WorldState
from openmdbench.policies.actions import ActionBatch, PlatformAction
from openmdbench.scenarios.md_ad_002_config import load_md_ad_002_config
from openmdbench.systems.combat.ad2 import AD2Combat


def _asset(
    entity_id: str, side: Side, kind: Literal["uav", "shore_radar"], x: float
) -> PlatformAsset:
    inventory = {"uav_interceptor_missile": 6} if kind == "uav" else {"shore_ciws": 12}
    return PlatformAsset(
        id=entity_id,
        side=side,
        domain=Domain.AIR if kind == "uav" else Domain.SHORE,
        position=(x, 0.0, 100.0),
        platform_type=kind,
        components=ComponentState(weapon_inventory=inventory),
    )


def _action(attacker: str, weapon: str) -> PlatformAction:
    return PlatformAction(
        entity_id=attacker,
        navigation="hold_position",
        engage_contact_id="contact-red-1",
        weapon_id=weapon,
    )


def _world(target_x: float = 9_000.0) -> WorldState:
    world = WorldState("combat", tick=20)
    world.registry.register(_asset("red-uav", Side.RED, "uav", target_x + 1_000.0))
    world.registry.register(_asset("red-shore", Side.RED, "shore_radar", target_x + 500.0))
    world.registry.register(_asset("blue-1", Side.BLUE, "uav", target_x))
    world.contacts[Side.RED] = [
        ContactTrack(
            "contact-red-1",
            Side.RED,
            Domain.AIR,
            (target_x, 0.0, 100.0),
            (0.0, 0.0, 0.0),
            10.0,
            1.0,
            10,
            ("radar",),
            last_update_tick=20,
        )
    ]
    return world


def test_ciws_wins_stable_same_target_arbitration() -> None:
    config = load_md_ad_002_config("MD-AD-002-EASY").config
    world = _world()
    combat = AD2Combat(config, 7, (0.0, 0.0))
    actions = (_action("red-uav", "uav_interceptor_missile"), _action("red-shore", "shore_ciws"))
    events = combat.resolve(
        world,
        ActionBatch(timestamp=20, actions=tuple(reversed(actions))),
        truth_by_contact={"contact-red-1": "blue-1"},
    )
    rounds = [event for event in events if event["event_type"] == "combat_round"]
    assert [event["attacker_id"] for event in rounds] == ["red-shore"]


def test_illegal_missile_in_denial_zone_consumes_no_resources_or_rng() -> None:
    config = load_md_ad_002_config("MD-AD-002-EASY").config
    world = _world(1_000.0)
    combat = AD2Combat(config, 7, (0.0, 0.0))
    rng_before = combat.rng.snapshot()
    attacker = cast(PlatformAsset, world.registry.get("red-uav"))
    ammo_before = attacker.components.weapon_inventory
    events = combat.resolve(
        world,
        ActionBatch(timestamp=20, actions=(_action("red-uav", "uav_interceptor_missile"),)),
        truth_by_contact={"contact-red-1": "blue-1"},
    )
    assert events[0]["rejection_code"] == "missile_denial_zone_prohibited"
    assert combat.rng.snapshot() == rng_before
    attacker_after = cast(PlatformAsset, world.registry.get("red-uav"))
    assert attacker_after.components.weapon_inventory == ammo_before
    assert combat.cooldowns == {}


def test_component_and_truth_rejections_cover_roe_fail_closed_paths() -> None:
    config = load_md_ad_002_config("MD-AD-002-EASY").config
    cases: tuple[tuple[dict[str, object], dict[str, str], str], ...] = (
        (
            {
                "components": ComponentState(
                    weapon_inventory={"uav_interceptor_missile": 6},
                    weapons_operational=False,
                )
            },
            {"contact-red-1": "blue-1"},
            "attacker_unavailable",
        ),
        (
            {
                "components": ComponentState(
                    weapon_inventory={"uav_interceptor_missile": 6},
                    communication_status="offline",
                )
            },
            {"contact-red-1": "blue-1"},
            "command_not_delivered",
        ),
        ({"lifecycle": Lifecycle.DESTROYED}, {"contact-red-1": "blue-1"}, "attacker_unavailable"),
        ({}, {}, "target_not_hostile"),
    )
    for update, truth, expected in cases:
        world = _world()
        attacker = cast(PlatformAsset, world.registry.get("red-uav"))
        world.registry.update(attacker.model_copy(update=update))
        combat = AD2Combat(config, 7, (0.0, 0.0))
        events = combat.resolve(
            world,
            ActionBatch(
                timestamp=20,
                actions=(_action("red-uav", "uav_interceptor_missile"),),
            ),
            truth_by_contact=truth,
        )
        assert events[0]["rejection_code"] == expected


def test_catalog_definition_load_order_does_not_change_combat_result() -> None:
    config = load_md_ad_002_config("MD-AD-002-EASY").config
    definitions = md_ad_002_catalog_definitions(config)
    forward = CatalogRepository(
        definitions, engine_version="0.1.0", model_registry=builtin_model_registry()
    )
    reversed_catalog = CatalogRepository(
        reversed(definitions),
        engine_version="0.1.0",
        model_registry=builtin_model_registry(),
    )
    batch = ActionBatch(
        timestamp=20,
        actions=(_action("red-uav", "uav_interceptor_missile"),),
    )
    first = AD2Combat(config, 73, (0.0, 0.0), catalog=forward).resolve(
        _world(), batch, truth_by_contact={"contact-red-1": "blue-1"}
    )
    second = AD2Combat(config, 73, (0.0, 0.0), catalog=reversed_catalog).resolve(
        _world(), batch, truth_by_contact={"contact-red-1": "blue-1"}
    )
    assert first == second


def test_catalog_hash_is_checkpointed_and_validated() -> None:
    config = load_md_ad_002_config("MD-AD-002-EASY").config
    combat = AD2Combat(config, 7, (0.0, 0.0))
    snapshot = combat.snapshot()
    assert snapshot["catalog_hash"] == combat.catalog.content_hash
    snapshot["catalog_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="catalog hash mismatch"):
        AD2Combat.from_snapshot(config, snapshot)

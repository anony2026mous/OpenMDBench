"""Catalog identity must travel with formal replay/session metadata."""

from pathlib import Path

from openmdbench.api.sessions import SessionStore
from openmdbench.core.entities import PlatformAsset
from openmdbench.replay import ReplayReader


def test_ad2_replay_records_catalog_schema_and_content_hash(tmp_path: Path) -> None:
    store = SessionStore(replay_dir=tmp_path)
    session = store.create("MD-AD-002-EASY", 7)
    assert session.env._ad2_combat is not None
    catalog_hash = session.env._ad2_combat.catalog.content_hash
    store.delete(session.session_id)

    reader = ReplayReader(tmp_path / f"{session.session_id}.replay.jsonl")
    assert reader.metadata.schema_versions["catalog"] == "1.0"
    assert reader.metadata.dynamics_metadata is not None
    assert reader.metadata.dynamics_metadata["catalog"]["content_hash"] == catalog_hash


def test_two_sessions_share_no_catalog_or_runtime_inventory_mutation() -> None:
    store = SessionStore()
    first = store.create("MD-AD-002-EASY", 7)
    second = store.create("MD-AD-002-EASY", 7)
    assert first.env._ad2_combat is not None and second.env._ad2_combat is not None
    assert first.env._ad2_combat.catalog is not second.env._ad2_combat.catalog
    first_weapon = first.env._ad2_combat.catalog.resolve("weapons", "uav_interceptor_missile@1.0.0")
    second_weapon = second.env._ad2_combat.catalog.resolve(
        "weapons", "uav_interceptor_missile@1.0.0"
    )
    assert first_weapon == second_weapon and first_weapon is not second_weapon

    assert first.env.world is not None and second.env.world is not None
    first_uav = first.env.world.registry.get("red-interceptor-uav-1")
    second_uav = second.env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(first_uav, PlatformAsset) and isinstance(second_uav, PlatformAsset)
    inventory = dict(first_uav.components.weapon_inventory)
    inventory["uav_interceptor_missile"] -= 1
    first.env.world.registry.update(
        first_uav.model_copy(
            update={
                "components": first_uav.components.model_copy(
                    update={"weapon_inventory": inventory}
                )
            }
        )
    )
    assert second_uav.components.weapon_inventory["uav_interceptor_missile"] == 12

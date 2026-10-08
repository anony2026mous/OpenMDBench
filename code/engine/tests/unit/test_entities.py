"""Unified entity lifecycle, serialization, and legacy-adapter tests."""

import pytest
from openmdbench.core.entities import (
    ComponentState,
    Domain,
    EntityRegistry,
    Lifecycle,
    PlatformAsset,
    Side,
)
from openmdbench.domains.surface.legacy_adapter import adapt_legacy_usv


def _usv(entity_id: str = "usv-1") -> PlatformAsset:
    return PlatformAsset(
        id=entity_id,
        side=Side.BLUE,
        domain=Domain.SURFACE,
        platform_type="usv",
        position=(1.0, 2.0, 0.0),
        components=ComponentState(weapon_inventory={"rws": 1}),
    )


def test_entity_serialization_round_trip() -> None:
    entity = _usv()
    assert PlatformAsset.model_validate_json(entity.model_dump_json()) == entity


def test_destroyed_entity_is_retained_but_not_active_and_id_is_never_reused() -> None:
    registry = EntityRegistry()
    registry.register(_usv())
    destroyed = registry.destroy("usv-1")
    assert destroyed.lifecycle is Lifecycle.DESTROYED
    assert registry.get("usv-1") == destroyed
    assert registry.active_entities() == ()
    with pytest.raises(ValueError, match="cannot be reused"):
        registry.register(_usv())


def test_legacy_adapter_converts_internal_heading_and_copies_state() -> None:
    entity = adapt_legacy_usv(
        entity_id="legacy-usv",
        side=Side.BLUE,
        position=[10.0, 20.0],
        velocity=[1.0, 0.0],
        psi_rad=0.0,
    )
    assert entity.heading_deg == pytest.approx(90.0)
    assert entity.position == (10.0, 20.0, 0.0)

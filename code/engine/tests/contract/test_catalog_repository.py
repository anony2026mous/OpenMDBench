"""RF-02 versioned catalog and trusted model registry contracts."""

import pytest
from openmdbench.catalog import (
    CatalogConflictError,
    CatalogRepository,
    CatalogResolutionError,
    EffectDefinition,
    EngineCompatibility,
    ModelRegistry,
    PlatformDefinition,
    ResourceDefinition,
    SensorDefinition,
    WeaponDefinition,
    parse_exact_resource_ref,
)
from pydantic import ValidationError


def _effect() -> EffectDefinition:
    return EffectDefinition(
        schema_version="1.0",
        resource_type="effects",
        id="kinetic_damage",
        version="1.0.0",
        display_name="Kinetic damage",
        model="fractional_damage_v1",
        compatibility=EngineCompatibility(engine=">=0.1.0,<1.0.0"),
        damage_fraction=0.75,
    )


def _weapon() -> WeaponDefinition:
    return WeaponDefinition(
        schema_version="1.0",
        resource_type="weapons",
        id="interceptor",
        version="1.2.0",
        display_name="Interceptor",
        model="probability_instant_v1",
        compatibility=EngineCompatibility(engine=">=0.1.0,<1.0.0"),
        dependencies=("kinetic_damage@1.0.0",),
        allowed_platform_types=("uav",),
        target_domains=("air",),
        minimum_range_m=100.0,
        maximum_range_m=20_000.0,
        hit_probability=0.8,
        guidance="command",
        contact_required=True,
        cooldown_ticks=3,
        rounds_per_action=1,
        energy_cost=0.0002,
        effect_ref="kinetic_damage@1.0.0",
    )


def test_exact_ref_semver_engine_compatibility_and_unknown_fail_closed() -> None:
    assert parse_exact_resource_ref("interceptor@1.2.0") == ("interceptor", "1.2.0")
    for invalid in ("interceptor", "interceptor@latest", "interceptor@1.2", "@1.0.0"):
        with pytest.raises(ValueError):
            parse_exact_resource_ref(invalid)

    repository = CatalogRepository((_weapon(), _effect()), engine_version="0.1.0")
    assert repository.resolve("weapons", "interceptor@1.2.0") == _weapon()
    with pytest.raises(CatalogResolutionError, match="unknown"):
        repository.resolve("weapons", "missing@1.0.0")
    with pytest.raises(CatalogResolutionError, match="incompatible"):
        CatalogRepository((_weapon(),), engine_version="1.0.0")


def test_duplicate_cycle_and_invalid_resource_are_rejected() -> None:
    with pytest.raises(CatalogConflictError, match="duplicate"):
        CatalogRepository((_effect(), _effect()), engine_version="0.1.0")
    first = ResourceDefinition(
        schema_version="1.0",
        resource_type="missions",
        id="first",
        version="1.0.0",
        display_name="first",
        model="declarative_v1",
        compatibility=EngineCompatibility(engine=">=0.1.0,<1.0.0"),
        dependencies=("second@1.0.0",),
    )
    second = first.model_copy(
        update={"id": "second", "display_name": "second", "dependencies": ("first@1.0.0",)}
    )
    with pytest.raises(CatalogResolutionError, match="cyclic"):
        CatalogRepository((first, second), engine_version="0.1.0")
    with pytest.raises(ValidationError):
        WeaponDefinition.model_validate({**_weapon().model_dump(), "maximum_range_m": float("nan")})


def test_hash_and_resolution_are_independent_of_load_order() -> None:
    first = CatalogRepository((_weapon(), _effect()), engine_version="0.1.0")
    second = CatalogRepository((_effect(), _weapon()), engine_version="0.1.0")
    assert first.content_hash == second.content_hash
    assert first.snapshot() == second.snapshot()
    changed_weapon = _weapon().model_copy(update={"hit_probability": 0.81})
    changed = CatalogRepository((changed_weapon, _effect()), engine_version="0.1.0")
    assert changed.content_hash != first.content_hash
    assert changed.resource_content_hash("weapons", "interceptor@1.2.0") != (
        first.resource_content_hash("weapons", "interceptor@1.2.0")
    )


def test_platform_sensor_weapon_compatibility_matrix_and_isolation() -> None:
    platform = PlatformDefinition(
        schema_version="1.0",
        resource_type="platforms",
        id="interceptor_uav",
        version="1.0.0",
        display_name="Interceptor UAV",
        model="platform_asset_v1",
        compatibility=EngineCompatibility(engine=">=0.1.0,<1.0.0"),
        domain="air",
        platform_type="uav",
        dimensions_m=(3.0, 4.0, 1.0),
        collision_radius_m=2.5,
        health_threshold=1.0,
        energy_capacity=1.0,
        loadout_slots=("air_weapon",),
        payload_capacity_kg=100.0,
        allowed_dynamics=("point_mass_3d@1.0.0",),
        visualization_ref="uav_default@1.0.0",
        fidelity="abstract",
    )
    sensor = SensorDefinition(
        schema_version="1.0",
        resource_type="sensors",
        id="uav_radar",
        version="1.0.0",
        display_name="UAV radar",
        model="probability_sensor_v1",
        compatibility=EngineCompatibility(engine=">=0.1.0,<1.0.0"),
        compatible_platform_types=("uav",),
        kind="radar",
        range_m=30_000.0,
        update_hz=1.0,
        base_detection_probability=0.8,
        field_of_view_deg=360.0,
    )
    repository = CatalogRepository((platform, sensor, _weapon(), _effect()), engine_version="0.1.0")
    assert repository.validate_platform_component(
        "interceptor_uav@1.0.0", "sensors", "uav_radar@1.0.0"
    )
    assert repository.validate_platform_component(
        "interceptor_uav@1.0.0", "weapons", "interceptor@1.2.0"
    )
    one = repository.instantiate("effects", "kinetic_damage@1.0.0")
    two = repository.instantiate("effects", "kinetic_damage@1.0.0")
    assert one == two and one is not two


def test_model_registry_rejects_duplicates_and_returns_fresh_instances() -> None:
    registry = ModelRegistry()
    registry.register("effects", "fractional_damage_v1", lambda definition: {"hits": []})
    with pytest.raises(CatalogConflictError, match="duplicate"):
        registry.register("effects", "fractional_damage_v1", lambda definition: {})
    registry.freeze()
    assert registry.create("effects", "fractional_damage_v1", _effect()) == {"hits": []}
    assert registry.create("effects", "fractional_damage_v1", _effect()) is not registry.create(
        "effects", "fractional_damage_v1", _effect()
    )
    with pytest.raises(RuntimeError, match="frozen"):
        registry.register("effects", "other", lambda definition: {})
    with pytest.raises(CatalogResolutionError, match="unknown trusted model"):
        registry.create("effects", "not_registered", _effect())

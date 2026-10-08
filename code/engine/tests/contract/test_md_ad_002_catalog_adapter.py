"""AD2 legacy configuration must normalize into isolated resolved resources."""

import pytest
from openmdbench.catalog import (
    EffectDefinition,
    ProbabilityInstantWeaponModel,
    SensorDefinition,
    WeaponDefinition,
)
from openmdbench.catalog.legacy_adapters import md_ad_002_catalog
from openmdbench.scenarios.md_ad_002_config import load_md_ad_002_config


@pytest.mark.parametrize(
    "scenario_id",
    ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"),
)
def test_formal_ad2_catalog_resolves_platform_sensor_weapon_and_effect(scenario_id: str) -> None:
    config = load_md_ad_002_config(scenario_id).config
    catalog = md_ad_002_catalog(config)
    weapon = catalog.resolve("weapons", "uav_interceptor_missile@1.0.0")
    effect = catalog.resolve("effects", "uav_interceptor_missile_effect@1.0.0")
    sensor = catalog.resolve("sensors", "radar_uav@1.0.0")

    assert isinstance(weapon, WeaponDefinition)
    assert isinstance(effect, EffectDefinition)
    assert isinstance(sensor, SensorDefinition)
    legacy = next(item for item in config.weapons if item.component == weapon.id)
    assert weapon.hit_probability == legacy.hit_probability
    assert effect.damage_fraction == legacy.damage
    assert catalog.validate_platform_component(
        "interceptor_uav@1.0.0", "weapons", "uav_interceptor_missile@1.0.0"
    )
    first = catalog.instantiate("weapons", "uav_interceptor_missile@1.0.0")
    second = catalog.instantiate("weapons", "uav_interceptor_missile@1.0.0")
    assert isinstance(first, ProbabilityInstantWeaponModel)
    assert first == second and first is not second
    assert catalog.validate_platform_component(
        "interceptor_uav@1.0.0", "sensors", "radar_uav@1.0.0"
    )
    assert catalog.validate_platform_component(
        "interceptor_uav@1.0.0", "dynamics", "uav_kinematics@1.0.0"
    )
    assert catalog.validate_platform_component(
        "interceptor_uav@1.0.0", "loadouts", "ad2_uav_loadout@1.0.0"
    )
    with pytest.raises(ValueError, match="incompatible"):
        catalog.validate_platform_component(
            "interceptor_uav@1.0.0", "loadouts", "ad2_shore_loadout@1.0.0"
        )
    assert catalog.resource_content_hash("weapons", "uav_interceptor_missile@1.0.0").startswith(
        "sha256:"
    )


def test_catalog_covers_every_required_namespace_and_has_no_runtime_inventory() -> None:
    config = load_md_ad_002_config("MD-AD-002-EASY").config
    catalog = md_ad_002_catalog(config)
    resource_types = {item["resource_type"] for item in catalog.snapshot()}
    assert resource_types == {
        "maps",
        "platforms",
        "dynamics",
        "loadouts",
        "sensors",
        "weapons",
        "effects",
        "communications",
        "energy",
        "environments",
        "missions",
        "scoring",
        "visualization_assets",
        "trusted_model_plugins",
    }
    encoded = str(catalog.snapshot())
    assert "inventory" not in encoded
    assert "cooldowns" not in encoded

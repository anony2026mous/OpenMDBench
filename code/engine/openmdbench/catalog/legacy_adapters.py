"""Explicit adapters from frozen legacy scenario config into RF-02 resources."""

from __future__ import annotations

from openmdbench.catalog.builtin_models import builtin_model_registry
from openmdbench.catalog.models import (
    CatalogDefinition,
    CommunicationDefinition,
    DynamicsDefinition,
    EffectDefinition,
    EngineCompatibility,
    LoadoutDefinition,
    PlatformDefinition,
    ResourceDefinition,
    ScoringDefinition,
    SensorDefinition,
    WeaponDefinition,
)
from openmdbench.catalog.repository import CatalogRepository
from openmdbench.scenarios.md_ad_002_config import MDAD002Config

ENGINE_COMPATIBILITY = EngineCompatibility(engine=">=0.1.0,<1.0.0")


def _common(
    resource_type: str, resource_id: str, display_name: str, model: str
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "resource_type": resource_type,
        "id": resource_id,
        "version": "1.0.0",
        "display_name": display_name,
        "model": model,
        "compatibility": ENGINE_COMPATIBILITY,
    }


def md_ad_002_catalog_definitions(config: MDAD002Config) -> tuple[CatalogDefinition, ...]:
    """Normalize AD2 v2 values; runtime inventory remains outside the catalog."""
    definitions: list[CatalogDefinition] = []
    platform_specs = {
        "shore_radar": ("shore", (12.0, 12.0, 8.0), 8.0, ("shore_weapon",)),
        "interceptor_uav": ("air", (4.0, 3.0, 1.0), 2.5, ("air_weapon",)),
        "picket_usv": ("surface", (10.0, 3.0, 3.0), 5.0, ("deck_weapon",)),
    }
    for platform_id, (domain, dimensions, radius, slots) in platform_specs.items():
        platform_type = {
            "interceptor_uav": "uav",
            "picket_usv": "usv",
            "shore_radar": "shore_radar",
        }[platform_id]
        definitions.append(
            PlatformDefinition.model_validate(
                {
                    **_common(
                        "platforms",
                        platform_id,
                        platform_id.replace("_", " ").title(),
                        "platform_asset_v1",
                    ),
                    "domain": domain,
                    "platform_type": platform_type,
                    "dimensions_m": dimensions,
                    "collision_radius_m": radius,
                    "health_threshold": 1.0,
                    "energy_capacity": 1.0,
                    "loadout_slots": slots,
                    "payload_capacity_kg": 200.0,
                    "allowed_dynamics": (f"{platform_type}_kinematics@1.0.0",),
                    "visualization_ref": f"{platform_type}_default@1.0.0",
                    "fidelity": "abstract",
                }
            )
        )
    assigned_types = {
        deployment.id: {
            "interceptor_uav": "uav",
            "picket_usv": "usv",
            "shore_radar": "shore_radar",
        }[deployment.platform]
        for deployment in config.deployments
    }
    for sensor in config.sensors:
        definitions.append(
            SensorDefinition.model_validate(
                {
                    **_common(
                        "sensors",
                        sensor.sensor_id,
                        sensor.sensor_id.replace("_", " ").title(),
                        "probability_sensor_v1",
                    ),
                    "compatible_platform_types": tuple(
                        sorted({assigned_types[item] for item in sensor.assigned_entities})
                    ),
                    "kind": sensor.kind,
                    "range_m": sensor.range_m,
                    "update_hz": 1.0 / sensor.report_interval_ticks,
                    "base_detection_probability": sensor.base_detection_probability,
                    "field_of_view_deg": sensor.field_of_view_deg,
                    "low_altitude_range_m": sensor.low_altitude_range_m,
                    "reference_rcs_m2": sensor.reference_rcs_m2,
                }
            )
        )
    for weapon in config.weapons:
        effect_id = f"{weapon.component}_effect"
        definitions.append(
            EffectDefinition.model_validate(
                {
                    **_common(
                        "effects",
                        effect_id,
                        f"{weapon.component} damage",
                        "fractional_damage_v1",
                    ),
                    "damage_fraction": weapon.damage,
                }
            )
        )
        allowed = ("uav",) if weapon.component == "uav_interceptor_missile" else ("shore_radar",)
        effect_ref = f"{effect_id}@1.0.0"
        definitions.append(
            WeaponDefinition.model_validate(
                {
                    **_common(
                        "weapons",
                        weapon.component,
                        weapon.component.replace("_", " ").title(),
                        "probability_instant_v1",
                    ),
                    "dependencies": (effect_ref,),
                    "allowed_platform_types": allowed,
                    "target_domains": ("air",),
                    "minimum_range_m": weapon.minimum_range_m,
                    "maximum_range_m": weapon.maximum_range_m,
                    "hit_probability": weapon.hit_probability,
                    "guidance": "command",
                    "contact_required": True,
                    "cooldown_ticks": weapon.cooldown_ticks,
                    "rounds_per_action": 1,
                    "energy_cost": 0.0002,
                    "effect_ref": effect_ref,
                }
            )
        )
    # All CAT-001 namespaces are represented through the same immutable base.
    definitions.extend(
        (
            DynamicsDefinition.model_validate(
                {
                    **_common("dynamics", "uav_kinematics", "UAV kinematics", "point_mass_3d_v1"),
                    "compatible_platform_types": ("uav",),
                    "spatial_dimensions": 3,
                    "maximum_speed_mps": 80.0,
                }
            ),
            DynamicsDefinition.model_validate(
                {
                    **_common("dynamics", "usv_kinematics", "USV kinematics", "point_mass_2d_v1"),
                    "compatible_platform_types": ("usv",),
                    "spatial_dimensions": 2,
                    "maximum_speed_mps": 20.0,
                }
            ),
            DynamicsDefinition.model_validate(
                {
                    **_common("dynamics", "shore_radar_kinematics", "Static shore", "static_v1"),
                    "compatible_platform_types": ("shore_radar",),
                    "spatial_dimensions": 2,
                    "maximum_speed_mps": 0.0,
                }
            ),
            LoadoutDefinition.model_validate(
                {
                    **_common(
                        "loadouts",
                        "ad2_uav_loadout",
                        "AD2 UAV loadout",
                        "fixed_loadout_v1",
                    ),
                    "compatible_platform_types": ("uav",),
                    "weapon_refs": ("uav_interceptor_missile@1.0.0",),
                    "dependencies": ("uav_interceptor_missile@1.0.0",),
                    "mass_kg": 80.0,
                    "slot_requirements": ("air_weapon",),
                }
            ),
            LoadoutDefinition.model_validate(
                {
                    **_common(
                        "loadouts",
                        "ad2_shore_loadout",
                        "AD2 shore loadout",
                        "fixed_loadout_v1",
                    ),
                    "compatible_platform_types": ("shore_radar",),
                    "weapon_refs": ("shore_ciws@1.0.0",),
                    "dependencies": ("shore_ciws@1.0.0",),
                    "mass_kg": 150.0,
                    "slot_requirements": ("shore_weapon",),
                }
            ),
        )
    )
    definitions.append(
        CommunicationDefinition.model_validate(
            {
                **_common(
                    "communications",
                    "ad2_command_network",
                    "AD2 command network",
                    "delayed_network_v1",
                ),
                "links": tuple(item.model_dump(mode="json") for item in config.communications),
            }
        )
    )
    definitions.append(
        ScoringDefinition.model_validate(
            {
                **_common("scoring", "md_ad_002_v1", "AD2 scoring", "weighted_scoring_v1"),
                "weights": tuple(sorted(config.scoring.weights.items())),
            }
        )
    )
    generic = (
        ("maps", config.map.map_id, "map_asset_v1"),
        ("energy", "ad2_energy", "normalized_energy_v1"),
        ("environments", config.weather_profile, "weather_profile_v1"),
        ("missions", "md_ad_002_denial", "area_denial_v1"),
        ("visualization_assets", "uav_default", "vector_profile_v1"),
        ("trusted_model_plugins", "builtin_models", "builtin_plugin_v1"),
    )
    for resource_type, resource_id, model in generic:
        definitions.append(
            ResourceDefinition.model_validate(
                _common(resource_type, resource_id, resource_id.replace("_", " ").title(), model)
            )
        )
    return tuple(definitions)


def md_ad_002_catalog(config: MDAD002Config) -> CatalogRepository:
    return CatalogRepository(
        md_ad_002_catalog_definitions(config),
        engine_version="0.1.0",
        model_registry=builtin_model_registry(),
    )


__all__ = ["md_ad_002_catalog", "md_ad_002_catalog_definitions"]

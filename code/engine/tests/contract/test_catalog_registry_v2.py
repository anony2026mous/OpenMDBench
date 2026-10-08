"""RF-02 RED contract for the sole CatalogV2 and trusted ModelRegistryV2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from openmdbench.catalog.v2 import (
    CatalogConflictErrorV2,
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    CatalogV2,
    EntityCompositionV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
    ResourceTypeV2,
)
from pydantic import ValidationError

RESOURCE_TYPES: tuple[ResourceTypeV2, ...] = (
    "maps",
    "platforms",
    "dynamics",
    "collision_shapes",
    "sensors",
    "communications",
    "weapons",
    "ammunition",
    "effects",
    "damage_models",
    "energy",
    "environments",
    "loadouts",
    "visualization_assets",
    "missions",
    "scoring",
    "trusted_model_plugins",
)
PLUGIN_HASH = "sha256:" + "f" * 64


def _resource(
    resource_type: ResourceTypeV2,
    identifier: str | None = None,
    *,
    dependencies: tuple[str, ...] = (),
    content: dict[str, Any] | None = None,
    model_id: str = "models.data-profile@2.0.0",
) -> CatalogResourceV2:
    return CatalogResourceV2(
        schema_version="2.0",
        resource_type=resource_type,
        id=identifier or f"{resource_type}.generic",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id=model_id,
        dependencies=dependencies,
        content=content or {"fidelity": "UNVALIDATED"},
    )


def _registry() -> ModelRegistryV2:
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.data-profile",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position": "m", "time": "s"},
            deterministic=True,
            thread_safe=False,
            process_safe=True,
            trusted=True,
            artifact_sha256=PLUGIN_HASH,
            resource_types=RESOURCE_TYPES,
            field_units={"position_m": "m", "sim_time_s": "s"},
        ),
        lambda definition: {"resource_ref": definition.exact_ref, "runtime": {}},
    )
    registry.freeze()
    return registry


def _assign_for_immutability_test(mapping: Any, key: Any, value: Any) -> None:
    """Attempt a runtime mutation without weakening the public Mapping annotation."""
    mapping[key] = value


def test_catalog_covers_every_required_resource_namespace() -> None:
    resources = tuple(_resource(kind) for kind in RESOURCE_TYPES)
    catalog = CatalogV2(resources, engine_version="2.1.0", model_registry=_registry())

    assert tuple(item.resource_type for item in catalog.snapshot()) == tuple(sorted(RESOURCE_TYPES))
    for resource in resources:
        resolved = catalog.resolve(resource.resource_type, resource.exact_ref)
        assert resolved.schema_version == "2.0"
        assert resolved.content_hash.startswith("sha256:")
        assert len(resolved.content_hash) == 71


def test_resource_requires_exact_semver_schema_engine_and_stable_hash() -> None:
    resource = _resource("effects", "effects.kinetic")
    assert resource.exact_ref == "effects.kinetic@2.0.0"
    assert (
        resource.content_hash
        == CatalogResourceV2.model_validate_json(resource.model_dump_json()).content_hash
    )

    for changes in (
        {"version": "latest"},
        {"schema_version": "1.0"},
        {"engine_compatibility": "anything"},
    ):
        with pytest.raises(ValidationError):
            CatalogResourceV2.model_validate({**resource.model_dump(), **changes})


def test_duplicate_missing_dependency_and_cycle_fail_closed() -> None:
    effect = _resource("effects", "effects.shared")
    with pytest.raises(CatalogConflictErrorV2, match="duplicate"):
        CatalogV2((effect, effect), engine_version="2.0.0", model_registry=_registry())

    missing = _resource("weapons", "weapons.missing-effect", dependencies=("effects.absent@2.0.0",))
    with pytest.raises(CatalogResolutionErrorV2, match="missing|unknown"):
        CatalogV2((missing,), engine_version="2.0.0", model_registry=_registry())

    first = _resource("effects", "effects.first", dependencies=("effects.second@2.0.0",))
    second = _resource("effects", "effects.second", dependencies=("effects.first@2.0.0",))
    with pytest.raises(CatalogResolutionErrorV2, match="cycle|cyclic"):
        CatalogV2((first, second), engine_version="2.0.0", model_registry=_registry())


def test_registry_metadata_protocol_and_fresh_runtime_instances() -> None:
    registry = _registry()
    metadata = registry.metadata("models.data-profile@2.0.0")
    assert metadata.interface_version == "2.0"
    assert metadata.units == {"position": "m", "time": "s"}
    assert metadata.deterministic is True
    assert metadata.thread_safe is False and metadata.process_safe is True

    definition = _resource("effects")
    first = registry.create(definition.model_ref, definition)
    second = registry.create(definition.model_ref, definition)
    assert first == second and first is not second
    first["runtime"]["health"] = 0.0
    assert second["runtime"] == {}


def test_registry_rejects_duplicate_unknown_untrusted_and_wrong_interface() -> None:
    base = ModelFactoryMetadataV2(
        schema_version="2.0",
        model_id="models.effect",
        version="2.0.0",
        interface_version="2.0",
        input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0",
        units={},
        deterministic=True,
        thread_safe=True,
        process_safe=True,
        trusted=True,
        artifact_sha256=PLUGIN_HASH,
        resource_types=RESOURCE_TYPES,
        field_units={},
    )
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(base, lambda resource: {})
    with pytest.raises(CatalogConflictErrorV2, match="duplicate"):
        registry.register(base, lambda resource: {})
    with pytest.raises(CatalogResolutionErrorV2, match="unknown"):
        registry.create("models.absent@2.0.0", _resource("effects"))

    for metadata in (
        base.model_copy(update={"model_id": "models.untrusted", "trusted": False}),
        base.model_copy(update={"model_id": "models.wrong-interface", "interface_version": "99.0"}),
        base.model_copy(update={"model_id": "models.nondeterministic", "deterministic": False}),
    ):
        other = ModelRegistryV2(interface_version="2.0")
        with pytest.raises(
            (CatalogResolutionErrorV2, ValidationError),
            match="trusted|interface|determin",
        ):
            other.register(metadata, lambda resource: {})


def _compatibility_resources() -> tuple[CatalogResourceV2, ...]:
    collision = _resource("collision_shapes", "collision.fixed")
    effect = _resource("effects", "effects.any")
    weapon = _resource(
        "weapons",
        "weapons.air-only",
        dependencies=(effect.exact_ref,),
        content={
            "allowed_platform_types": ["aircraft"],
            "target_domains": ["air"],
            "effect_ref": effect.exact_ref,
        },
    )
    ammunition = _resource(
        "ammunition",
        "ammunition.air-only",
        dependencies=(weapon.exact_ref,),
        content={"weapon_ref": weapon.exact_ref, "mass_per_round_kg": 10.0},
    )
    dynamics = _resource(
        "dynamics",
        "dynamics.air",
        content={"compatible_platform_types": ["aircraft"], "mobile": True},
    )
    loadout = _resource(
        "loadouts",
        "loadouts.air",
        dependencies=(weapon.exact_ref, ammunition.exact_ref),
        content={
            "compatible_platform_types": ["aircraft"],
            "required_slots": ["payload"],
            "mass_kg": 80.0,
            "weapon_refs": [weapon.exact_ref],
            "ammunition": {ammunition.exact_ref: 2},
        },
    )
    platform = _resource(
        "platforms",
        "platforms.aircraft",
        dependencies=(collision.exact_ref,),
        content={
            "domain": "air",
            "platform_type": "aircraft",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": ["payload"],
            "payload_capacity_kg": 100.0,
            "collision_shape_ref": collision.exact_ref,
        },
    )
    return platform, dynamics, loadout, weapon, ammunition, effect, collision


def test_platform_dynamics_loadout_payload_slot_and_target_compatibility() -> None:
    resources = _compatibility_resources()
    catalog = CatalogV2(resources, engine_version="2.0.0", model_registry=_registry())
    composition = EntityCompositionV2(
        schema_version="2.0",
        platform_ref="platforms.aircraft@2.0.0",
        dynamics_ref="dynamics.air@2.0.0",
        loadout_ref="loadouts.air@2.0.0",
        target_domains=("air",),
    )
    assert catalog.validate_entity_composition(composition) is True

    platform, dynamics, loadout, weapon, ammunition, effect, collision = resources
    invalid_cases = (
        dynamics.model_copy(
            update={"content": {"compatible_platform_types": ["submarine"], "mobile": True}}
        ),
        loadout.model_copy(
            update={
                "content": {
                    **dict(loadout.content),
                    "required_slots": ["payload", "payload"],
                }
            }
        ),
        loadout.model_copy(update={"content": {**dict(loadout.content), "mass_kg": 101.0}}),
        weapon.model_copy(
            update={"content": {**dict(weapon.content), "target_domains": ["surface"]}}
        ),
    )
    for replacement in invalid_cases:
        candidate = tuple(
            replacement if item.resource_type == replacement.resource_type else item
            for item in resources
        )
        with pytest.raises(CatalogResolutionErrorV2, match="incompatible|slot|payload|target"):
            CatalogV2(
                candidate, engine_version="2.0.0", model_registry=_registry()
            ).validate_entity_composition(composition)

    static_platform = platform.model_copy(
        update={"content": {**dict(platform.content), "mobile": False}}
    )
    candidate = (static_platform, dynamics, loadout, weapon, ammunition, effect, collision)
    with pytest.raises(CatalogResolutionErrorV2, match="static|fixed|dynamics"):
        catalog = CatalogV2(candidate, engine_version="2.0.0", model_registry=_registry())
        catalog.validate_entity_composition(composition)


@pytest.mark.parametrize(
    "runtime_key",
    ("health", "ammo_remaining", "cooldown_remaining", "rng_state", "message_queue"),
)
def test_catalog_rejects_session_runtime_state(runtime_key: str) -> None:
    with pytest.raises(ValidationError, match="runtime|session|mutable|forbidden"):
        _resource("platforms", content={runtime_key: 1})


def test_snapshot_and_hash_are_stable_across_resource_and_registration_order() -> None:
    resources = tuple(_resource(kind) for kind in RESOURCE_TYPES)
    first = CatalogV2(resources, engine_version="2.0.0", model_registry=_registry())
    second = CatalogV2(reversed(resources), engine_version="2.0.0", model_registry=_registry())

    assert first.snapshot() == second.snapshot()
    assert first.content_hash == second.content_hash
    changed = tuple(
        item.model_copy(update={"content": {"fidelity": "VERIFIED"}})
        if item.resource_type == "maps"
        else item
        for item in resources
    )
    assert (
        CatalogV2(changed, engine_version="2.0.0", model_registry=_registry()).content_hash
        != first.content_hash
    )


def test_catalog_requires_an_already_frozen_registry() -> None:
    registry = ModelRegistryV2(interface_version="2.0")
    metadata = ModelFactoryMetadataV2(
        schema_version="2.0",
        model_id="models.data-profile",
        version="2.0.0",
        interface_version="2.0",
        input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0",
        units={},
        deterministic=True,
        thread_safe=True,
        process_safe=True,
        trusted=True,
        artifact_sha256=PLUGIN_HASH,
        resource_types=RESOURCE_TYPES,
        field_units={},
    )
    registry.register(metadata, lambda definition: {})
    with pytest.raises(CatalogResolutionErrorV2, match="registry.*frozen|freeze"):
        CatalogV2((_resource("effects"),), engine_version="2.0.0", model_registry=registry)


def test_registry_and_catalog_hash_include_plugin_artifact_identity() -> None:
    first = _registry()
    changed = ModelRegistryV2(interface_version="2.0")
    metadata = first.metadata("models.data-profile@2.0.0").model_copy(
        update={"artifact_sha256": "sha256:" + "0" * 64}
    )
    changed.register(metadata, lambda definition: {"resource_ref": definition.exact_ref})
    changed.freeze()

    assert first.content_hash != changed.content_hash
    resource = _resource("effects")
    assert (
        CatalogV2((resource,), engine_version="2.0.0", model_registry=first).content_hash
        != CatalogV2((resource,), engine_version="2.0.0", model_registry=changed).content_hash
    )


def test_registry_rejects_definition_model_mismatch_and_unsafe_execution() -> None:
    registry = _registry()
    mismatched = _resource("effects", model_id="models.another@2.0.0")
    with pytest.raises(CatalogResolutionErrorV2, match="model.*match|mismatch"):
        registry.create("models.data-profile@2.0.0", mismatched)

    unsafe = ModelFactoryMetadataV2(
        schema_version="2.0",
        model_id="models.unsafe",
        version="2.0.0",
        interface_version="2.0",
        input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0",
        units={},
        deterministic=True,
        thread_safe=False,
        process_safe=False,
        trusted=True,
        artifact_sha256=PLUGIN_HASH,
        resource_types=RESOURCE_TYPES,
        field_units={},
    )
    mutable = ModelRegistryV2(interface_version="2.0")
    with pytest.raises(CatalogResolutionErrorV2, match="thread|process|safe"):
        mutable.register(unsafe, lambda definition: {})


def test_public_and_internal_catalog_mutation_is_rejected() -> None:
    catalog = CatalogV2((_resource("effects"),), engine_version="2.0.0", model_registry=_registry())
    resolved = catalog.resolve("effects", "effects.generic@2.0.0")
    with pytest.raises((TypeError, ValidationError)):
        resolved.content["runtime"] = True
    with pytest.raises(TypeError):
        _assign_for_immutability_test(
            catalog._definitions, ("effects", "injected", "2.0.0"), resolved
        )
    with pytest.raises(TypeError):
        _assign_for_immutability_test(
            catalog.model_registry._entries,
            "models.injected@2.0.0",
            (
                catalog.model_registry.metadata("models.data-profile@2.0.0"),
                lambda definition: {},
            ),
        )


@pytest.mark.parametrize(
    ("resource_type", "runtime_content"),
    (
        ("energy", {"current_energy": 0.5}),
        ("sensors", {"sensor_mode": "off"}),
        ("ammunition", {"ammunition_remaining": 2}),
        ("weapons", {"cooldown_ticks_remaining": 1}),
        ("damage_models", {"random_generator_state": [1, 2]}),
        ("communications", {"pending_messages": []}),
    ),
)
def test_typed_resource_profiles_reject_runtime_state_without_key_blacklist(
    resource_type: ResourceTypeV2, runtime_content: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError, match="runtime|state|profile|forbidden"):
        _resource(resource_type, content=runtime_content)


def test_catalog_resource_rejects_non_string_mapping_keys() -> None:
    with pytest.raises(ValidationError, match="string|key"):
        _resource(
            "effects",
            content=cast(dict[str, Any], {1: "not-a-string-key"}),
        )


def test_model_io_schema_and_units_are_validated_when_catalog_is_built() -> None:
    cases = (
        {"input_schema": "wrong-input@9.0"},
        {"output_schema": "wrong-output@9.0"},
        {"units": {"position": "nautical-furlong", "time": "fortnight"}},
    )
    for changes in cases:
        registry = ModelRegistryV2(interface_version="2.0")
        metadata = ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.data-profile",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position": "m", "time": "s"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256=PLUGIN_HASH,
            resource_types=RESOURCE_TYPES,
            field_units={"position_m": "m", "sim_time_s": "s"},
        ).model_copy(update=changes)
        registry.register(metadata, lambda definition: {})
        registry.freeze()
        with pytest.raises(CatalogResolutionErrorV2, match="input|output|unit|schema"):
            CatalogV2(
                (_resource("effects"),),
                engine_version="2.0.0",
                model_registry=registry,
            )


def test_component_resource_references_and_compatibility_are_complete() -> None:
    registry = _registry()
    sensor = _resource(
        "sensors",
        "sensors.any",
        content={"compatible_platform_types": ["aircraft"], "slot_type": "sensor"},
    )
    communication = _resource(
        "communications",
        "communications.any",
        content={"compatible_platform_types": ["aircraft"], "slot_type": "communication"},
    )
    energy = _resource(
        "energy",
        "energy.any",
        content={"compatible_platform_types": ["aircraft"], "capacity_j": 1000.0},
    )
    collision = _resource(
        "collision_shapes", "collision.any", content={"shape": "sphere", "radius_m": 2.0}
    )
    damage = _resource("damage_models", "damage.any", content={"input_effect": "kinetic"})
    effect = _resource(
        "effects",
        "effects.any",
        dependencies=(damage.exact_ref,),
        content={"damage_model_ref": damage.exact_ref, "effect_type": "kinetic"},
    )
    weapon = _resource(
        "weapons",
        "weapons.any",
        dependencies=(effect.exact_ref,),
        content={
            "allowed_platform_types": ["aircraft"],
            "target_domains": ["air"],
            "effect_ref": effect.exact_ref,
        },
    )
    ammunition = _resource(
        "ammunition",
        "ammunition.any",
        dependencies=(weapon.exact_ref,),
        content={"weapon_ref": weapon.exact_ref, "mass_per_round_kg": 1.0},
    )
    visual = _resource(
        "visualization_assets", "visual.any", content={"profile": "generic-aircraft"}
    )
    platform = _resource(
        "platforms",
        "platforms.complete",
        dependencies=(collision.exact_ref, energy.exact_ref, visual.exact_ref),
        content={
            "platform_type": "aircraft",
            "domain": "air",
            "mobile": False,
            "component_slots": ["sensor", "communication"],
            "collision_shape_ref": collision.exact_ref,
            "energy_ref": energy.exact_ref,
            "visualization_ref": visual.exact_ref,
        },
    )
    resources = (
        sensor,
        communication,
        energy,
        collision,
        damage,
        effect,
        weapon,
        ammunition,
        visual,
        platform,
    )
    catalog = CatalogV2(resources, engine_version="2.0.0", model_registry=registry)
    assert (
        catalog.validate_component_compatibility(
            platform_ref=platform.exact_ref,
            sensor_refs=(sensor.exact_ref,),
            communication_refs=(communication.exact_ref,),
            energy_ref=energy.exact_ref,
            collision_shape_ref=collision.exact_ref,
            ammunition_refs=(ammunition.exact_ref,),
            visualization_ref=visual.exact_ref,
        )
        is True
    )


def test_generic_v2_path_has_no_second_trusted_model_string_table() -> None:
    root = Path(__file__).parents[2]
    compiler_source = (root / "openmdbench/scenarios/compiler.py").read_text(encoding="utf-8")
    assert "_TRUSTED_COMPONENT_MODELS" not in compiler_source


@pytest.mark.parametrize(
    ("target_name", "field", "replacement"),
    (
        ("catalog", "engine_version", "9.9.9"),
        ("catalog", "content_hash", "sha256:" + "0" * 64),
        ("catalog", "model_registry", None),
        ("registry", "interface_version", "9.9"),
        ("registry", "_frozen", False),
    ),
)
def test_catalog_and_registry_attributes_cannot_be_rebound(
    target_name: str, field: str, replacement: Any
) -> None:
    registry = _registry()
    catalog = CatalogV2((_resource("effects"),), engine_version="2.0.0", model_registry=registry)
    target = catalog if target_name == "catalog" else registry
    with pytest.raises((AttributeError, TypeError)):
        setattr(target, field, replacement)


def _full_composition_catalog() -> tuple[CatalogV2, dict[str, CatalogResourceV2]]:
    platform, dynamics, loadout, weapon, ammunition, effect, collision = _compatibility_resources()
    damage = _resource("damage_models", "damage.typed", content={"effect_types": ["blast"]})
    effect = effect.model_copy(
        update={
            "dependencies": (damage.exact_ref,),
            "content": {"damage_model_ref": damage.exact_ref, "effect_type": "blast"},
        }
    )
    weapon = weapon.model_copy(
        update={
            "dependencies": (effect.exact_ref,),
            "content": {
                **dict(weapon.content),
                "effect_ref": effect.exact_ref,
            },
        }
    )
    ammunition = ammunition.model_copy(
        update={
            "dependencies": (weapon.exact_ref,),
            "content": {"weapon_ref": weapon.exact_ref, "mass_per_round_kg": 5.0},
        }
    )
    sensor = _resource(
        "sensors",
        "sensors.shared-slot",
        content={"compatible_platform_types": ["aircraft"], "slot_type": "shared"},
    )
    communication = _resource(
        "communications",
        "communications.radio",
        content={"compatible_platform_types": ["aircraft"], "slot_type": "communication"},
    )
    energy = _resource(
        "energy",
        "energy.air",
        content={"compatible_platform_types": ["aircraft"], "capacity_j": 10_000.0},
    )
    visual = _resource(
        "visualization_assets",
        "visual.air",
        content={"compatible_domains": ["air"], "profile": "aircraft"},
    )
    collision = collision.model_copy(
        update={"content": {"compatible_domains": ["air"], "shape": "sphere"}}
    )
    loadout = loadout.model_copy(
        update={
            "dependencies": (weapon.exact_ref, ammunition.exact_ref),
            "content": {
                **dict(loadout.content),
                "required_slots": ["shared"],
                "weapon_refs": [weapon.exact_ref],
                "ammunition_refs": [ammunition.exact_ref],
            },
        }
    )
    platform = platform.model_copy(
        update={
            "dependencies": (collision.exact_ref, energy.exact_ref, visual.exact_ref),
            "content": {
                **dict(platform.content),
                "component_slots": ["shared", "communication"],
                "collision_shape_ref": collision.exact_ref,
                "energy_ref": energy.exact_ref,
                "visualization_ref": visual.exact_ref,
            },
        }
    )
    by_name: dict[str, CatalogResourceV2] = {
        item.resource_type: item
        for item in (
            platform,
            dynamics,
            loadout,
            weapon,
            ammunition,
            effect,
            collision,
            damage,
            sensor,
            communication,
            energy,
            visual,
        )
    }
    catalog = CatalogV2(tuple(by_name.values()), engine_version="2.0.0", model_registry=_registry())
    return catalog, by_name


def test_full_composition_validation_is_atomic_and_counts_all_slots() -> None:
    catalog, resources = _full_composition_catalog()
    composition = EntityCompositionV2(
        schema_version="2.0",
        platform_ref=resources["platforms"].exact_ref,
        dynamics_ref=resources["dynamics"].exact_ref,
        loadout_ref=resources["loadouts"].exact_ref,
        sensor_refs=(resources["sensors"].exact_ref,),
        communication_refs=(resources["communications"].exact_ref,),
        energy_ref=resources["energy"].exact_ref,
        collision_shape_ref=resources["collision_shapes"].exact_ref,
        visualization_ref=resources["visualization_assets"].exact_ref,
        ammunition={resources["ammunition"].exact_ref: 1},
        target_domains=("air",),
    )
    with pytest.raises(CatalogResolutionErrorV2, match="slot|capacity|combined"):
        catalog.validate_full_composition(composition)


def test_full_composition_rejects_ammunition_outside_loadout_or_weapon() -> None:
    catalog, resources = _full_composition_catalog()
    unrelated_weapon = _resource(
        "weapons",
        "weapons.unrelated",
        dependencies=(resources["effects"].exact_ref,),
        content={
            "allowed_platform_types": ["aircraft"],
            "target_domains": ["air"],
            "effect_ref": resources["effects"].exact_ref,
        },
    )
    unrelated_ammunition = _resource(
        "ammunition",
        "ammunition.unrelated",
        dependencies=(unrelated_weapon.exact_ref,),
        content={"weapon_ref": unrelated_weapon.exact_ref, "mass_per_round_kg": 1.0},
    )
    all_resources = (*catalog.snapshot(), unrelated_weapon, unrelated_ammunition)
    expanded = CatalogV2(all_resources, engine_version="2.0.0", model_registry=_registry())
    composition = EntityCompositionV2(
        schema_version="2.0",
        platform_ref=resources["platforms"].exact_ref,
        dynamics_ref=resources["dynamics"].exact_ref,
        loadout_ref=resources["loadouts"].exact_ref,
        ammunition={unrelated_ammunition.exact_ref: 1},
        target_domains=("air",),
    )
    with pytest.raises(CatalogResolutionErrorV2, match="ammunition|loadout|weapon"):
        expanded.validate_full_composition(composition)


@pytest.mark.parametrize(
    ("resource_type", "field", "bad_value", "message"),
    (
        ("energy", "compatible_platform_types", ["submarine"], "energy|platform"),
        ("collision_shapes", "compatible_domains", ["underwater"], "collision|domain"),
        ("visualization_assets", "compatible_domains", ["surface"], "visual|domain"),
        ("effects", "damage_model_ref", "damage.absent@2.0.0", "effect|damage"),
    ),
)
def test_full_composition_validates_typed_cross_resource_chain(
    resource_type: str, field: str, bad_value: Any, message: str
) -> None:
    _catalog, resources = _full_composition_catalog()
    changed = resources[resource_type].model_copy(
        update={"content": {**dict(resources[resource_type].content), field: bad_value}}
    )
    candidates = tuple(
        changed if item.resource_type == resource_type else item for item in resources.values()
    )
    with pytest.raises(CatalogResolutionErrorV2, match=message):
        CatalogV2(candidates, engine_version="2.0.0", model_registry=_registry())


def test_factory_metadata_resource_types_and_field_units_match_definitions() -> None:
    for changes in (
        {"resource_types": ("sensors",)},
        {"field_units": {"maximum_range_m": "s"}},
    ):
        registry = ModelRegistryV2(interface_version="2.0")
        metadata = _registry().metadata("models.data-profile@2.0.0").model_copy(update=changes)
        registry.register(metadata, lambda definition: {})
        registry.freeze()
        weapon = _resource(
            "weapons",
            content={"maximum_range_m": 1000.0, "target_domains": ["air"]},
        )
        with pytest.raises(CatalogResolutionErrorV2, match="resource.*type|field.*unit|unit"):
            CatalogV2((weapon,), engine_version="2.0.0", model_registry=registry)


def test_generic_composition_compiler_does_not_import_legacy_catalog_authority() -> None:
    root = Path(__file__).parents[2]
    source = (root / "openmdbench/scenarios/compiler.py").read_text(encoding="utf-8")
    assert "from openmdbench.catalog.repository import" not in source
    assert "from openmdbench.catalog.legacy_adapters import" not in source
    method_source = source.split("    def _compile_composition(", 1)[1].split("\n    def ", 1)[0]
    assert "CatalogRepository" not in method_source
    assert "md_ad_002_catalog" not in method_source

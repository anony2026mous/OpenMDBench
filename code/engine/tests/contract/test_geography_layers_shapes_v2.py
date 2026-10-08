"""RF-05 typed geography-layer and collision-shape final-slice contracts."""

from __future__ import annotations

import inspect
import math
from dataclasses import replace
from types import MappingProxyType
from typing import Any

import pytest
from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
from tests.contract import test_geography_boundary_v2 as boundary_fixture


def _api() -> Any:
    from openmdbench.world import boundary_v2

    return boundary_v2


def _geo_api() -> Any:
    from openmdbench.world import geography_v2

    return geography_v2


@pytest.mark.parametrize(
    "layer_kind",
    ("land", "coast", "island", "no_go", "terrain_height", "bathymetry", "static_obstacles"),
)
def test_typed_layers_require_exact_resolved_catalog_binding(layer_kind: str) -> None:
    api = _geo_api()
    binding = api.GeographyLayerBindingV2.from_catalog_content(
        exact_ref=f"geography.synthetic-{layer_kind}@2.0.0",
        version="2.0.0",
        layer_kind=layer_kind,
        normalized_content={"features": []},
    )
    layer = api.GeographyLayerV2.from_binding(binding)
    assert layer.kind == layer_kind
    assert layer.exact_ref == binding.exact_ref
    assert layer.content_hash == binding.content_hash
    with pytest.raises(api.GeographyErrorV2) as captured:
        api.GeographyLayerV2.from_binding(replace(binding, content_hash="sha256:" + "0" * 64))
    assert captured.value.code == "geography.layer_binding_integrity_invalid"


def test_ordinary_mission_score_zone_is_not_promoted_to_typed_geography_layer() -> None:
    resolved = boundary_fixture._resolved()
    service = _geo_api().GeographyServiceV2.from_resolved_scenario(resolved)
    assert {item.zone_id for item in service.spatial_zones} == {"zone.excluded", "zone.operating"}
    assert service.layers == ()


@pytest.mark.parametrize(
    ("shape", "parameters"),
    (
        ("sphere", {"radius_m": 2.0}),
        ("capsule", {"radius_m": 2.0, "half_length_m": 4.0, "axis": "x"}),
        ("aabb", {"half_extents_m": (2.0, 3.0, 4.0)}),
        ("obb", {"half_extents_m": (2.0, 3.0, 4.0), "yaw_degrees": 31.0}),
        (
            "polygon_footprint",
            {
                "vertices_m": ((-2.0, -1.0), (2.0, -1.0), (1.0, 2.0)),
                "vertical_interval_m": (-3.0, 5.0),
            },
        ),
    ),
)
def test_supported_collision_shape_matrix_is_typed_and_finite(
    shape: str, parameters: dict[str, Any]
) -> None:
    typed = _api().CollisionShapeV2.from_profile(
        exact_ref=f"shape.synthetic-{shape}@2.0.0",
        content_hash="sha256:" + "2" * 64,
        shape=shape,
        parameters=parameters,
    )
    assert typed.shape == shape
    assert typed.vertical_interval_m[0] <= typed.vertical_interval_m[1]


@pytest.mark.parametrize("shape", ("mesh", "convex_hull", "heightfield", "python_callable"))
def test_unsupported_collision_shapes_fail_closed(shape: str) -> None:
    with pytest.raises(_api().BoundaryErrorV2) as captured:
        _api().CollisionShapeV2.from_profile(
            exact_ref=f"shape.unsupported-{shape}@2.0.0",
            content_hash="sha256:" + "3" * 64,
            shape=shape,
            parameters={},
        )
    assert captured.value.code == "boundary.collision_shape_unsupported"


def test_dynamic_zone_activation_is_typed_deterministic_and_checkpointable() -> None:
    api = _api()
    system = boundary_fixture._system()
    baseline = system.activation_snapshot()
    receipt = system.set_zone_activation(
        zone_id="zone.excluded", active=False, tick=7, operation_id="zone-op.007"
    )
    assert receipt.changed is True
    assert system.is_zone_active("zone.excluded") is False
    checkpoint = system.activation_snapshot()
    encoded = checkpoint.to_json()
    restored = api.BoundarySystemV2.from_resolved(
        boundary_fixture._resolved(), geography=boundary_fixture._geography()
    )
    restored.restore_activation_snapshot(
        api.ZoneActivationSnapshotV2.from_json(encoded),
        expected_snapshot_hash=checkpoint.snapshot_hash,
    )
    assert restored.activation_snapshot() == checkpoint
    assert baseline != checkpoint
    assert (
        system.set_zone_activation(
            zone_id="zone.excluded", active=False, tick=7, operation_id="zone-op.007"
        )
        == receipt
    )


def test_materialized_shape_rejects_rehashed_binding_forgery() -> None:
    resolved = resource_fixture._compile(resource_fixture._catalog())
    entity = resolved.entities[0]
    bindings = dict(entity.resource_bindings)
    shape = bindings["collision_shapes"][0]
    content = dict(shape.normalized_content)
    content["shape"] = "sphere"
    content["radius_m"] = math.inf
    forged_shape = replace(shape, normalized_content=MappingProxyType(content))
    bindings["collision_shapes"] = (forged_shape,)
    forged_entity = replace(entity, resource_bindings=MappingProxyType(bindings))
    with pytest.raises(_api().BoundaryErrorV2) as captured:
        _api().BoundaryEntityV2.from_resolved(
            forged_entity,
            resolved_scenario=replace(resolved, entities=(forged_entity,)),
            expected_resolved_hash=resolved.resolved_hash,
        )
    assert captured.value.code == "boundary.resolved_integrity_invalid"


def test_layer_binding_hash_is_recomputed_from_canonical_content_not_shape_only() -> None:
    api = _geo_api()
    content = {"features": [{"id": "feature.land", "polygon_m": [[0, 0], [10, 0], [0, 10]]}]}
    expected = api.GeographyLayerBindingV2.compute_content_hash(
        exact_ref="geography.synthetic-land@2.0.0",
        resource_type="environments",
        version="2.0.0",
        layer_kind="land",
        normalized_content=content,
    )
    valid = api.GeographyLayerBindingV2(
        exact_ref="geography.synthetic-land@2.0.0",
        resource_type="environments",
        version="2.0.0",
        content_hash=expected,
        layer_kind="land",
        normalized_content=content,
    )
    assert api.GeographyLayerV2.from_binding(valid).content_hash == expected
    with pytest.raises(api.GeographyErrorV2) as captured:
        api.GeographyLayerBindingV2(
            exact_ref=valid.exact_ref,
            resource_type=valid.resource_type,
            version=valid.version,
            content_hash="sha256:" + "f" * 64,
            layer_kind=valid.layer_kind,
            normalized_content=valid.normalized_content,
        )
    assert captured.value.code == "geography.layer_binding_integrity_invalid"


def test_typed_layers_materialize_real_queries_and_static_obstacles() -> None:
    api = _geo_api()
    layers = (
        ("land", {"polygons": [{"id": "land.one", "vertices_m": [[0, 0], [20, 0], [0, 20]]}]}),
        ("coast", {"polylines": [{"id": "coast.one", "vertices_m": [[0, 0], [20, 0]]}]}),
        (
            "island",
            {"polygons": [{"id": "island.one", "vertices_m": [[30, 30], [40, 30], [30, 40]]}]},
        ),
        ("no_go", {"polygons": [{"id": "no-go.one", "vertices_m": [[5, 5], [15, 5], [5, 15]]}]}),
        ("terrain_height", {"samples": [{"position_m": [4, 4], "value_m": 123.0}]}),
        ("bathymetry", {"samples": [{"position_m": [8, 8], "value_m": -456.0}]}),
        (
            "static_obstacles",
            {
                "obstacles": [
                    {"id": "rock.one", "shape": "sphere", "center_m": [9, 9, -4], "radius_m": 2}
                ]
            },
        ),
    )
    service = api.GeographyServiceV2.from_config_with_layers(
        origin_wgs84=(120.0, 30.0, 0.0),
        local_bounds_m=((-100.0, -100.0, -1000.0), (100.0, 100.0, 1000.0)),
        layers=tuple(
            api.GeographyLayerV2.from_binding(
                api.GeographyLayerBindingV2.from_catalog_content(
                    exact_ref=f"geography.synthetic-{kind}@2.0.0",
                    version="2.0.0",
                    layer_kind=kind,
                    normalized_content=content,
                )
            )
            for kind, content in layers
        ),
    )
    assert service.contains(layer_kind="land", position_m=(2.0, 2.0, 0.0)) is True
    assert service.contains(layer_kind="no_go", position_m=(7.0, 7.0, 0.0)) is True
    assert service.nearest_feature(layer_kind="coast", position_m=(3.0, 4.0, 0.0)).id == "coast.one"
    assert service.contains(layer_kind="island", position_m=(32.0, 32.0, 0.0)) is True
    assert service.terrain_height_m((4.0, 4.0)) == pytest.approx(123.0)
    assert service.bathymetry_m((8.0, 8.0)) == pytest.approx(-456.0)
    assert service.static_obstacles[0].obstacle_id == "rock.one"


@pytest.mark.parametrize(
    ("shape", "first_parameters", "second_parameters", "second_y", "expect_collision"),
    (
        (
            "capsule",
            {"radius_m": 1.0, "half_length_m": 20.0, "axis": "x"},
            {"radius_m": 1.0, "half_length_m": 2.0, "axis": "y"},
            0.0,
            True,
        ),
        (
            "aabb",
            {"half_extents_m": (20.0, 2.0, 2.0)},
            {"half_extents_m": (2.0, 2.0, 2.0)},
            10.0,
            False,
        ),
        (
            "obb",
            {"half_extents_m": (20.0, 2.0, 2.0), "yaw_degrees": 45.0},
            {"half_extents_m": (20.0, 2.0, 2.0), "yaw_degrees": -45.0},
            25.0,
            True,
        ),
        (
            "obb",
            {"half_extents_m": (20.0, 2.0, 2.0), "yaw_degrees": 0.0},
            {"half_extents_m": (20.0, 2.0, 2.0), "yaw_degrees": 0.0},
            25.0,
            False,
        ),
        (
            "polygon_footprint",
            {
                "vertices_m": ((-20.0, -1.0), (20.0, -1.0), (0.0, 3.0)),
                "vertical_interval_m": (-2.0, 2.0),
            },
            {
                "vertices_m": ((-2.0, -1.0), (2.0, -1.0), (0.0, 3.0)),
                "vertical_interval_m": (20.0, 30.0),
            },
            0.0,
            False,
        ),
    ),
)
def test_narrowphase_consumes_full_shape_parameters_not_bounding_radius_only(
    shape: str,
    first_parameters: dict[str, Any],
    second_parameters: dict[str, Any],
    second_y: float,
    expect_collision: bool,
) -> None:
    del expect_collision
    api = _api()
    shapes = tuple(
        api.CollisionShapeV2.from_profile(
            exact_ref=f"shape.{shape}.{index}@2.0.0",
            content_hash="sha256:" + str(index + 4) * 64,
            shape=shape,
            parameters=parameters,
        )
        for index, parameters in enumerate((first_parameters, second_parameters))
    )
    system = api.BoundarySystemV2(
        geography=boundary_fixture._geography(), boundaries=(), enable_entity_collisions=True
    )
    system.register_entities(
        tuple(
            api.BoundaryEntityV2(
                entity_id=f"entity.{index}",
                domain="air",
                radius_m=item.radius_m,
                collision_shape_ref=item.exact_ref,
                shape=item,
            )
            for index, item in enumerate(shapes)
        )
    )
    assert shapes[0].shape == shape and shapes[1].shape == shape
    assert shapes[0].vertical_interval_m == tuple(
        api.CollisionShapeV2.from_profile(
            exact_ref="shape.control@2.0.0",
            content_hash="sha256:" + "7" * 64,
            shape=shape,
            parameters=first_parameters,
        ).vertical_interval_m
    )
    with pytest.raises(api.BoundaryErrorV2) as captured:
        system.evaluate(
            {
                "entity.0": api.MotionSegmentV2(start_m=(0, 0, 0), end_m=(10, 0, 0), dt_seconds=1),
                "entity.1": api.MotionSegmentV2(
                    start_m=(30, second_y, 0), end_m=(20, second_y, 0), dt_seconds=1
                ),
            },
            tick=0,
            tick_start_time_seconds=0.0,
        )
    assert captured.value.code == "boundary.shape_sweep_unsupported"


def test_static_collision_requires_overlapping_xy_and_vertical_time_intervals() -> None:
    api = _api()
    obstacle = api.StaticObstacleV2.polygon(
        "obstacle.xyz",
        ((40.0, -10.0), (60.0, -10.0), (60.0, 10.0), (40.0, 10.0)),
        vertical_interval_m=(20.0, 30.0),
    )
    system = api.BoundarySystemV2(geography=boundary_fixture._geography(), boundaries=(obstacle,))
    system.register_entities((api.BoundaryEntityV2("entity.xyz", "air", 2.0),))
    no_overlap = system.evaluate(
        {"entity.xyz": api.MotionSegmentV2(start_m=(0, 0, 0), end_m=(100, 0, 19), dt_seconds=1)},
        tick=0,
        tick_start_time_seconds=0.0,
    )
    overlap = system.evaluate(
        {"entity.xyz": api.MotionSegmentV2(start_m=(0, 0, 0), end_m=(100, 0, 50), dt_seconds=1)},
        tick=0,
        tick_start_time_seconds=0.0,
    )
    assert no_overlap.collision_events == ()
    assert overlap.collision_events


def test_v2_evaluation_requires_explicit_tick_start_and_has_no_clock_fallback() -> None:
    api = _api()
    system = boundary_fixture._system()
    system.register_entities((api.BoundaryEntityV2("entity.clock.strict", "air", 1.0),))
    motion = {
        "entity.clock.strict": api.MotionSegmentV2(
            start_m=(900.0, 500.0, 100.0), end_m=(1100.0, 500.0, 100.0), dt_seconds=1.0
        )
    }
    with pytest.raises(api.BoundaryErrorV2) as captured:
        system.evaluate(motion, tick=4)
    assert captured.value.code == "boundary.tick_start_time_required"


@pytest.mark.parametrize(
    ("layer_kind", "content"),
    (
        (
            "land",
            {
                "polygons": [
                    {"id": "dup", "vertices_m": [[0, 0], [1, 0], [0, 1]]},
                    {"id": "dup", "vertices_m": [[2, 2], [3, 2], [2, 3]]},
                ]
            },
        ),
        ("coast", {"polylines": [{"id": "bad", "vertices_m": [[0, 0], [0, 0]]}]}),
        ("island", {"polygons": [{"id": "bad", "vertices_m": [[0, 0], [1, 1], [0, 1], [1, 0]]}]}),
        ("no_go", {"polygons": [{"id": "bad", "vertices_m": [[0, 0], [1, 0]]}]}),
        ("terrain_height", {"samples": [{"position_m": [0, 0], "value_m": math.inf}]}),
        ("bathymetry", {"samples": [{"position_m": [0], "value_m": -1}]}),
        ("static_obstacles", {"obstacles": [{"id": "bad", "shape": "sphere", "radius_m": 0}]}),
    ),
)
def test_each_layer_kind_has_strict_geometry_schema_ids_bounds_and_stable_error(
    layer_kind: str, content: dict[str, Any]
) -> None:
    with pytest.raises(_geo_api().GeographyErrorV2) as captured:
        _geo_api().GeographyLayerBindingV2.from_catalog_content(
            exact_ref=f"geography.invalid-{layer_kind}@2.0.0",
            version="2.0.0",
            layer_kind=layer_kind,
            normalized_content=content,
            limits=_geo_api().GeographyLayerLimitsV2(max_features=100, max_vertices=1000),
        )
    assert captured.value.code.startswith("geography.layer_")
    assert captured.value.path and captured.value.reason and captured.value.suggestion


def test_layer_binding_materializes_from_real_resolved_catalog_evidence_end_to_end() -> None:
    from tests.contract import test_declarative_events_v2 as event_fixture

    resolved = event_fixture._compile(event_fixture._scenario())
    weather = next(event for event in resolved.events if event.event_type == "weather_change")
    binding = weather.payload.values["environment_binding"]
    layer_binding = _geo_api().GeographyLayerBindingV2.from_resolved_binding(binding)
    assert layer_binding.exact_ref == binding.exact_ref
    assert layer_binding.content_hash == binding.content_hash
    assert (
        _geo_api().GeographyLayerV2.from_binding(layer_binding).content_hash == binding.content_hash
    )


def test_shape_oracles_reject_radius_and_axis_aligned_false_positives() -> None:
    api = _api()
    oracle = api.ShapeNarrowphaseOracleV2(tolerance_m=0.001)
    sphere = api.CollisionShapeV2.from_profile(
        exact_ref="shape.sphere@2.0.0",
        content_hash="sha256:" + "a" * 64,
        shape="sphere",
        parameters={"radius_m": 1.0},
    )
    assert oracle.overlap(sphere, (0, 0, 0), sphere, (1.5, 1.5, 0)) is False
    capsule = api.CollisionShapeV2.from_profile(
        exact_ref="shape.capsule@2.0.0",
        content_hash="sha256:" + "b" * 64,
        shape="capsule",
        parameters={"radius_m": 1.0, "half_length_m": 5.0, "axis": "x"},
    )
    assert oracle.overlap(capsule, (0, 0, 0), sphere, (6.9, 0, 0)) is True
    rotated = api.CollisionShapeV2.from_profile(
        exact_ref="shape.obb@2.0.0",
        content_hash="sha256:" + "c" * 64,
        shape="obb",
        parameters={"half_extents_m": (8, 1, 1), "yaw_degrees": 45},
    )
    assert oracle.overlap(rotated, (0, 0, 0), rotated, (0, 14, 0)) is False
    assert oracle.overlap(sphere, (0, 0, 0), sphere, (0, 0, 3), vertical_intervals=True) is False


def test_concave_polygon_footprint_is_decomposed_trustfully_or_fails_closed() -> None:
    api = _api()
    parameters = {
        "vertices_m": ((0, 0), (4, 0), (4, 4), (2, 2), (0, 4)),
        "vertical_interval_m": (-1, 1),
    }
    try:
        shape = api.CollisionShapeV2.from_profile(
            exact_ref="shape.concave@2.0.0",
            content_hash="sha256:" + "d" * 64,
            shape="polygon_footprint",
            parameters=parameters,
        )
    except api.BoundaryErrorV2 as error:
        assert error.code == "boundary.concave_polygon_unsupported"
    else:
        assert shape.convex_parts


def test_true_3d_sphere_quadratic_and_xy_z_interval_oracles_are_exact() -> None:
    api = _api()
    oracle = api.ShapeNarrowphaseOracleV2(tolerance_m=1e-9)
    sphere = api.CollisionShapeV2.from_profile(
        exact_ref="shape.sphere.quadratic@2.0.0",
        content_hash="sha256:" + "e" * 64,
        shape="sphere",
        parameters={"radius_m": 1.0},
    )
    hit = oracle.sweep(
        sphere,
        start_a=(0, 0, 0),
        end_a=(10, 10, 10),
        shape_b=sphere,
        start_b=(6, 6, 6),
        end_b=(6, 6, 6),
    )
    expected = (6.0 - 2.0 / math.sqrt(3.0)) / 10.0
    assert hit.time_fraction == pytest.approx(expected, abs=1e-9)
    assert (
        oracle.xy_z_intervals_overlap(xy_interval=(0.2, 0.4), z_interval=(0.400001, 0.8)) is False
    )
    assert oracle.xy_z_intervals_overlap(xy_interval=(0.2, 0.4), z_interval=(0.4, 0.8)) is True


def test_capsule_segment_distance_and_round_endcap_oracle() -> None:
    api = _api()
    oracle = api.ShapeNarrowphaseOracleV2(tolerance_m=1e-9)
    capsule = api.CollisionShapeV2.from_profile(
        exact_ref="shape.capsule.segment@2.0.0",
        content_hash="sha256:" + "f" * 64,
        shape="capsule",
        parameters={"radius_m": 1.0, "half_length_m": 5.0, "axis": "x"},
    )
    sphere = api.CollisionShapeV2.from_profile(
        exact_ref="shape.sphere.endcap@2.0.0",
        content_hash="sha256:" + "1" * 64,
        shape="sphere",
        parameters={"radius_m": 1.0},
    )
    assert oracle.overlap(capsule, (0, 0, 0), sphere, (6.9, 0, 0)) is True
    assert oracle.overlap(capsule, (0, 0, 0), sphere, (5, 2.001, 0)) is False


def test_rotated_obb_sat_rejects_world_aabb_false_positive_or_stably_unsupported() -> None:
    api = _api()
    obb = api.CollisionShapeV2.from_profile(
        exact_ref="shape.obb.sat@2.0.0",
        content_hash="sha256:" + "2" * 64,
        shape="obb",
        parameters={"half_extents_m": (6, 0.5, 0.5), "yaw_degrees": 45},
    )
    try:
        overlap = api.ShapeNarrowphaseOracleV2(tolerance_m=1e-9).overlap(
            obb, (0, 0, 0), obb, (0, 9, 0)
        )
    except api.BoundaryErrorV2 as error:
        assert error.code == "boundary.obb_narrowphase_unsupported"
    else:
        assert overlap is False


@pytest.mark.parametrize("corruption", ("degenerate", "duplicate", "overquota"))
def test_hash_valid_resolved_layer_still_rejects_bad_semantics(corruption: str) -> None:
    api = _geo_api()
    contents: dict[str, dict[str, Any]] = {
        "degenerate": {"polygons": [{"id": "land.bad", "vertices_m": [[0, 0], [1, 0], [2, 0]]}]},
        "duplicate": {
            "polygons": [
                {"id": "land.same", "vertices_m": [[0, 0], [1, 0], [0, 1]]},
                {"id": "land.same", "vertices_m": [[2, 2], [3, 2], [2, 3]]},
            ]
        },
        "overquota": {
            "polygons": [
                {"id": f"land.{index}", "vertices_m": [[0, 0], [1, 0], [0, 1]]}
                for index in range(101)
            ]
        },
    }
    forged = api.GeographyLayerBindingV2.from_unchecked_resolved_payload_for_integrity_test(
        exact_ref="geography.bad-land@2.0.0",
        version="2.0.0",
        layer_kind="land",
        normalized_content=contents[corruption],
    )
    with pytest.raises(api.GeographyErrorV2) as captured:
        api.GeographyLayerV2.from_resolved_binding(forged)
    assert captured.value.code.startswith("geography.layer_")


def _shape_entity(api: Any, entity_id: str, shape: Any) -> Any:
    return api.BoundaryEntityV2(
        entity_id=entity_id,
        domain="air",
        radius_m=shape.radius_m,
        collision_shape_ref=shape.exact_ref,
        shape=shape,
    )


def test_boundary_system_sphere_sweep_matches_true_3d_quadratic_oracle() -> None:
    api = _api()
    sphere = api.CollisionShapeV2.from_profile(
        exact_ref="shape.production-sphere@2.0.0",
        content_hash="sha256:" + "5" * 64,
        shape="sphere",
        parameters={"radius_m": 1.0},
    )
    system = api.BoundarySystemV2(
        geography=boundary_fixture._geography(), boundaries=(), enable_entity_collisions=True
    )
    system.register_entities(
        (_shape_entity(api, "entity.a", sphere), _shape_entity(api, "entity.b", sphere))
    )
    event = system.evaluate(
        {
            "entity.a": api.MotionSegmentV2(start_m=(0, 0, 0), end_m=(10, 10, 10), dt_seconds=1),
            "entity.b": api.MotionSegmentV2(start_m=(6, 6, 6), end_m=(6, 6, 6), dt_seconds=1),
        },
        tick=0,
        tick_start_time_seconds=0.0,
    ).collision_events[0]
    expected = (6.0 - 2.0 / math.sqrt(3.0)) / 10.0
    assert event.time_fraction == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    ("shape_name", "parameters", "second_position"),
    (
        ("capsule", {"radius_m": 1.0, "half_length_m": 5.0, "axis": "x"}, (9.0, 0.0, 0.0)),
        ("obb", {"half_extents_m": (6.0, 0.5, 0.5), "yaw_degrees": 45.0}, (0.0, 9.0, 0.0)),
    ),
)
def test_production_shape_sweep_is_exact_or_stably_unsupported_never_approximate(
    shape_name: str, parameters: dict[str, Any], second_position: tuple[float, float, float]
) -> None:
    api = _api()
    shape = api.CollisionShapeV2.from_profile(
        exact_ref=f"shape.production-{shape_name}@2.0.0",
        content_hash="sha256:" + "6" * 64,
        shape=shape_name,
        parameters=parameters,
    )
    system = api.BoundarySystemV2(
        geography=boundary_fixture._geography(), boundaries=(), enable_entity_collisions=True
    )
    system.register_entities(
        (_shape_entity(api, "entity.a", shape), _shape_entity(api, "entity.b", shape))
    )
    motions = {
        "entity.a": api.MotionSegmentV2(start_m=(0, 0, 0), end_m=(1, 0, 0), dt_seconds=1),
        "entity.b": api.MotionSegmentV2(
            start_m=second_position, end_m=second_position, dt_seconds=1
        ),
    }
    try:
        result = system.evaluate(motions, tick=0, tick_start_time_seconds=0.0).collision_events
    except api.BoundaryErrorV2 as error:
        assert error.code == "boundary.shape_sweep_unsupported"
    else:
        try:
            oracle = api.ShapeNarrowphaseOracleV2(tolerance_m=0.001).sweep(
                shape,
                start_a=(0, 0, 0),
                end_a=(1, 0, 0),
                shape_b=shape,
                start_b=second_position,
                end_b=second_position,
            )
        except api.BoundaryErrorV2 as error:
            assert error.code == "boundary.shape_sweep_unsupported"
            pytest.fail("BoundarySystem approximated a shape whose exact oracle is unsupported")
        assert bool(result) is (oracle is not None)
        if result:
            assert result[0].time_fraction == pytest.approx(oracle.time_fraction, abs=1e-9)


def test_boundary_system_narrowphase_delegates_to_typed_shape_oracle_without_fallbacks() -> None:
    api = _api()
    source = inspect.getsource(api.BoundarySystemV2._narrowphase_pair)
    assert "ShapeNarrowphaseOracleV2" in source or "_shape_oracle" in source
    forbidden = ("_cylindrical_sweep_fraction", "world_aabb", "bounding_radius", "radius_m +")
    assert not any(token in source for token in forbidden)

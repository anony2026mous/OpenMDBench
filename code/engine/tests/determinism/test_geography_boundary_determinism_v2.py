"""RF-05 adversarial geography and continuous-collision determinism contracts."""

from __future__ import annotations

import inspect
import math
from typing import Any

import pytest
from tests.contract import test_geography_boundary_v2 as boundary_fixture


def _geo_api() -> Any:
    return boundary_fixture._geo_api()


def _boundary_api() -> Any:
    return boundary_fixture._boundary_api()


def _point_segment_distance(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    fraction = (
        0.0
        if length_sq == 0.0
        else max(
            0.0,
            min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq),
        )
    )
    return math.hypot(point[0] - (start[0] + fraction * dx), point[1] - (start[1] + fraction * dy))


def _capsule_hits_polygon(
    point: tuple[float, float], radius: float, vertices: tuple[tuple[float, float], ...]
) -> bool:
    inside = False
    previous = vertices[-1]
    for current in vertices:
        if (current[1] > point[1]) != (previous[1] > point[1]):
            crossing_x = (previous[0] - current[0]) * (point[1] - current[1]) / (
                previous[1] - current[1]
            ) + current[0]
            inside ^= point[0] < crossing_x
        if _point_segment_distance(point, previous, current) <= radius:
            return True
        previous = current
    return inside


def _polygon_sweep_oracle(vertices: tuple[tuple[float, float], ...], radius: float) -> float:
    resolution = 200_000
    first = next(
        index
        for index in range(resolution + 1)
        if _capsule_hits_polygon((300.0 * index / resolution, 150.0), radius, vertices)
    )
    low, high = (first - 1) / resolution, first / resolution
    for _unused in range(32):
        middle = (low + high) / 2.0
        if _capsule_hits_polygon((300.0 * middle, 150.0), radius, vertices):
            high = middle
        else:
            low = middle
    return high


def _sphere_pair_toi(first: Any, second: Any, radius_sum: float) -> float | None:
    relative_start = tuple(first.start_m[index] - second.start_m[index] for index in range(3))
    relative_delta = tuple(
        first.end_m[index] - first.start_m[index] - second.end_m[index] + second.start_m[index]
        for index in range(3)
    )
    a = sum(value * value for value in relative_delta)
    b = 2.0 * sum(relative_start[index] * relative_delta[index] for index in range(3))
    c = sum(value * value for value in relative_start) - radius_sum * radius_sum
    if c <= 0.0:
        return 0.0
    discriminant = b * b - 4.0 * a * c
    if a == 0.0 or discriminant < 0.0:
        return None
    result = (-b - math.sqrt(discriminant)) / (2.0 * a)
    return result if 0.0 <= result <= 1.0 else None


@pytest.mark.parametrize("latitude", (0.0, 45.0, 80.0, -80.0))
def test_wgs84_shortest_dateline_delta_and_latitude_scale_are_deterministic(
    latitude: float,
) -> None:
    api = _geo_api()
    service = api.GeographyServiceV2.from_config(
        origin_wgs84=(179.999, latitude, 0.0),
        axis_orientation="east_north_up",
        tolerance_m=0.001,
        local_bounds_m=((-1000.0, -1000.0, -100.0), (1000.0, 1000.0, 100.0)),
    )
    across = service.to_local(frame="wgs84", coordinates=(-179.999, latitude, 0.0))
    assert abs(across[0]) < 500.0
    assert across == service.to_local(frame="wgs84", coordinates=(180.001, latitude, 0.0))


def test_negative_zero_and_sub_tolerance_values_have_one_canonical_quantization() -> None:
    service = boundary_fixture._geography()
    negative = service.canonical_local((-0.0, -0.0, -0.0))
    positive = service.canonical_local((0.0, 0.0, 0.0))
    tiny = service.canonical_local((0.0004, -0.0004, 0.0))
    assert negative == positive == tiny == (0.0, 0.0, 0.0)
    assert all(math.copysign(1.0, value) == 1.0 for value in negative)


@pytest.mark.parametrize(
    ("vertices", "code"),
    (
        (((0.0, 0.0), (10.0, 0.0), (10.0, 0.0), (0.0, 10.0)), "duplicate_vertex"),
        (((0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (0.0, 10.0)), "collinear_vertex"),
        (((0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (10.0, 0.0)), "self_intersection"),
    ),
)
def test_runtime_polygon_revalidates_duplicate_collinear_and_self_intersection(
    vertices: tuple[tuple[float, float], ...], code: str
) -> None:
    with pytest.raises(_boundary_api().BoundaryErrorV2) as captured:
        _boundary_api().StaticObstacleV2.polygon("obstacle.invalid", vertices)
    assert captured.value.code == f"boundary.polygon_{code}"


def test_polygon_holes_are_explicitly_supported_or_fail_closed_not_silently_filled() -> None:
    api = _boundary_api()
    outer = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))
    hole = ((25.0, 25.0), (75.0, 25.0), (75.0, 75.0), (25.0, 75.0))
    try:
        obstacle = api.StaticObstacleV2.polygon("obstacle.hole", outer, holes=(hole,))
    except api.BoundaryErrorV2 as error:
        assert error.code == "boundary.polygon_holes_unsupported"
    else:
        assert obstacle.contains((50.0, 50.0), point_on_edge="inside") is False


def test_multiple_boundary_facts_sort_by_priority_then_tie_break_identifier() -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2(
        geography=boundary_fixture._geography(),
        boundaries=(
            api.StaticObstacleV2.circle("boundary.zeta", (100.0, 100.0), 20.0, priority=10),
            api.StaticObstacleV2.circle("boundary.alpha", (100.0, 100.0), 20.0, priority=10),
            api.StaticObstacleV2.circle("boundary.low", (100.0, 100.0), 20.0, priority=1),
        ),
    )
    system.register_entities((api.BoundaryEntityV2("entity.one", "surface", 1.0),))
    result = system.evaluate(
        {
            "entity.one": api.MotionSegmentV2(
                start_m=(0.0, 100.0, 0.0),
                end_m=(200.0, 100.0, 0.0),
                dt_seconds=1.0,
            )
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    assert tuple(event.boundary_id for event in result.boundary_events) == (
        "boundary.alpha",
        "boundary.zeta",
        "boundary.low",
    )


def _collision_system(entity_ids: tuple[str, ...]) -> Any:
    api = _boundary_api()
    system = api.BoundarySystemV2(
        geography=boundary_fixture._geography(),
        boundaries=(),
        enable_entity_collisions=True,
    )
    system.register_entities(
        tuple(api.BoundaryEntityV2(identifier, "air", 5.0) for identifier in entity_ids)
    )
    return system


@pytest.mark.parametrize(
    ("first", "second", "expect_collision"),
    (
        (((0.0, 0.0, 0.0), (100.0, 0.0, 0.0)), ((100.0, 0.0, 0.0), (0.0, 0.0, 0.0)), True),
        (((0.0, 0.0, 0.0), (100.0, 0.0, 0.0)), ((50.0, 10.0, 0.0), (50.0, 10.0, 0.0)), True),
        (((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), ((5.0, 0.0, 0.0), (6.0, 0.0, 0.0)), True),
        (((0.0, 0.0, 0.0), (100.0, 0.0, 0.0)), ((50.0, 0.0, 20.1), (50.0, 0.0, 20.1)), False),
    ),
)
def test_entity_collision_handles_toi_tangent_start_overlap_and_vertical_separation(
    first: tuple[tuple[float, float, float], tuple[float, float, float]],
    second: tuple[tuple[float, float, float], tuple[float, float, float]],
    expect_collision: bool,
) -> None:
    api = _boundary_api()
    result = _collision_system(("entity.a", "entity.b")).evaluate(
        {
            "entity.a": api.MotionSegmentV2(start_m=first[0], end_m=first[1], dt_seconds=1.0),
            "entity.b": api.MotionSegmentV2(start_m=second[0], end_m=second[1], dt_seconds=1.0),
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    assert bool(result.collision_events) is expect_collision
    if expect_collision:
        event = result.collision_events[0]
        assert 0.0 <= event.time_fraction <= 1.0
        assert math.sqrt(sum(value * value for value in event.normal)) == pytest.approx(1.0)


def test_three_entity_simultaneous_collision_has_stable_pair_order() -> None:
    api = _boundary_api()
    system = _collision_system(("entity.c", "entity.a", "entity.b"))
    motions = {
        "entity.a": api.MotionSegmentV2(
            start_m=(-20.0, 0.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=1.0
        ),
        "entity.b": api.MotionSegmentV2(
            start_m=(20.0, 0.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=1.0
        ),
        "entity.c": api.MotionSegmentV2(
            start_m=(0.0, 20.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=1.0
        ),
    }
    result = system.evaluate(motions, tick=1, tick_start_time_seconds=0.0)
    assert tuple((item.entity_a_id, item.entity_b_id) for item in result.collision_events) == (
        ("entity.a", "entity.b"),
        ("entity.a", "entity.c"),
        ("entity.b", "entity.c"),
    )


def test_one_big_tick_and_ten_substeps_report_same_first_collision() -> None:
    api = _boundary_api()
    big = (
        _collision_system(("entity.a", "entity.b"))
        .evaluate(
            {
                "entity.a": api.MotionSegmentV2(
                    start_m=(0.0, 0.0, 0.0), end_m=(100.0, 0.0, 0.0), dt_seconds=1.0
                ),
                "entity.b": api.MotionSegmentV2(
                    start_m=(100.0, 0.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=1.0
                ),
            },
            tick=1,
            tick_start_time_seconds=0.0,
        )
        .collision_events[0]
    )
    substep_system = _collision_system(("entity.a", "entity.b"))
    substep_first = None
    for index in range(10):
        result = substep_system.evaluate(
            {
                "entity.a": api.MotionSegmentV2(
                    start_m=(index * 10.0, 0.0, 0.0),
                    end_m=((index + 1) * 10.0, 0.0, 0.0),
                    dt_seconds=0.1,
                ),
                "entity.b": api.MotionSegmentV2(
                    start_m=(100.0 - index * 10.0, 0.0, 0.0),
                    end_m=(100.0 - (index + 1) * 10.0, 0.0, 0.0),
                    dt_seconds=0.1,
                ),
            },
            tick=index,
            tick_start_time_seconds=index * 0.1,
        )
        if result.collision_events:
            substep_first = result.collision_events[0]
            break
    assert substep_first is not None
    assert substep_first.absolute_time_seconds == pytest.approx(big.absolute_time_seconds)


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_broadphase_matches_bruteforce_and_is_registration_order_independent(count: int) -> None:
    api = _boundary_api()
    identifiers = tuple(f"entity.{index:03d}" for index in range(count))
    motions = {
        identifier: api.MotionSegmentV2(
            start_m=(float(index * 30), 0.0, 0.0),
            end_m=(float(index * 30 + 20), 0.0, 0.0),
            dt_seconds=1.0,
        )
        for index, identifier in enumerate(identifiers)
    }
    forward = _collision_system(identifiers)
    reverse = _collision_system(tuple(reversed(identifiers)))
    assert (
        forward.evaluate(motions, tick=1, tick_start_time_seconds=0.0).collision_events
        == forward.evaluate_bruteforce(
            motions, tick=1, tick_start_time_seconds=0.0
        ).collision_events
    )
    assert forward.evaluate(motions, tick=1, tick_start_time_seconds=0.0) == reverse.evaluate(
        motions, tick=1, tick_start_time_seconds=0.0
    )


def test_collision_shape_comes_from_exact_resolved_binding_and_unknown_shape_fails_closed() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    api = _boundary_api()
    resolved = resource_fixture._compile(resource_fixture._catalog())
    entity = resolved.entities[0]
    runtime_shape = api.BoundaryEntityV2.from_resolved(
        entity,
        resolved_scenario=resolved,
        expected_resolved_hash=resolved.resolved_hash,
    )
    assert runtime_shape.collision_shape_ref == entity.composition.collision_shape_ref
    assert (
        runtime_shape.shape.content_hash
        == entity.resource_bindings["collision_shapes"][0].content_hash
    )
    forged = entity.model_copy(
        update={
            "composition": entity.composition.model_copy(
                update={"collision_shape_ref": "shape.unknown@2.0.0"}
            )
        }
    )
    with pytest.raises(api.BoundaryErrorV2) as captured:
        api.BoundaryEntityV2.from_resolved(
            forged,
            resolved_scenario=resolved,
            expected_resolved_hash=resolved.resolved_hash,
        )
    assert captured.value.code == "boundary.collision_shape_unsupported"


def test_xyz_contact_requires_vertical_overlap_at_exact_xy_toi() -> None:
    api = _boundary_api()
    system = _collision_system(("entity.alpha", "entity.beta"))
    base = {
        "entity.alpha": api.MotionSegmentV2(
            start_m=(0.0, 0.0, 0.0),
            end_m=(100.0, 0.0, 0.0),
            dt_seconds=1.0,
        )
    }
    misses = system.evaluate(
        {
            **base,
            "entity.beta": api.MotionSegmentV2(
                start_m=(50.0, 0.0, 30.0),
                end_m=(50.0, 0.0, 0.0),
                dt_seconds=1.0,
            ),
        },
        tick=0,
        tick_start_time_seconds=0.0,
    )
    hit_motions = {
        **base,
        "entity.beta": api.MotionSegmentV2(
            start_m=(50.0, 0.0, 30.0),
            end_m=(50.0, 0.0, -20.0001),
            dt_seconds=1.0,
        ),
    }
    hits = system.evaluate(
        hit_motions,
        tick=0,
        tick_start_time_seconds=0.0,
    )
    assert not misses.collision_events
    oracle = _sphere_pair_toi(hit_motions["entity.alpha"], hit_motions["entity.beta"], 10.0)
    assert oracle == pytest.approx(0.439999648, abs=1e-8)
    assert hits.collision_events[0].time_fraction == pytest.approx(oracle, abs=1e-9)


def test_aabb_corner_uses_rounded_minkowski_toi_never_axis_fallback_zero() -> None:
    api = _boundary_api()
    obstacle = api.StaticObstacleV2.polygon(
        "obstacle.axis-aligned",
        ((100.0, 100.0), (200.0, 100.0), (200.0, 200.0), (100.0, 200.0)),
    )
    system = api.BoundarySystemV2(geography=boundary_fixture._geography(), boundaries=(obstacle,))
    system.register_entities((api.BoundaryEntityV2("entity.corner", "surface", 10.0),))
    segment = api.MotionSegmentV2(
        start_m=(0.0, 0.0, 0.0),
        end_m=(100.0, 100.0, 0.0),
        dt_seconds=1.0,
    )
    event = system.evaluate(
        {"entity.corner": segment}, tick=0, tick_start_time_seconds=0.0
    ).collision_events[0]
    expected = (100.0 - 10.0 / math.sqrt(2.0)) / 100.0
    assert event.time_fraction == pytest.approx(expected, abs=1e-9)
    assert event.time_fraction > 0.0


def test_policy_changes_only_response_not_collision_facts() -> None:
    api = _boundary_api()
    motion = {
        "entity.policy": api.MotionSegmentV2(
            start_m=(900.0, 500.0, 100.0),
            end_m=(1100.0, 500.0, 100.0),
            dt_seconds=1.0,
        )
    }
    results = []
    for policy in ("reject", "stop", "reflect", "effect"):
        system = api.BoundarySystemV2.with_policy(
            geography=boundary_fixture._geography(),
            policy=api.BoundaryPolicyV2(policy=policy),
        )
        system.register_entities((api.BoundaryEntityV2("entity.policy", "air", 1.0),))
        results.append(system.evaluate(motion, tick=1, tick_start_time_seconds=0.0))
    fact_sets = [result.fact_fingerprint for result in results]
    response_sets = [result.response_fingerprint for result in results]
    assert len(set(fact_sets)) == 1
    assert len(set(response_sets)) == len(response_sets)


def test_entity_collision_requires_xy_and_vertical_overlap_at_the_same_time() -> None:
    api = _boundary_api()
    system = _collision_system(("entity.a", "entity.b"))
    result = system.evaluate(
        {
            "entity.a": api.MotionSegmentV2(
                start_m=(0.0, 0.0, 0.0),
                end_m=(100.0, 0.0, 20.0),
                velocity_mps=(100.0, 0.0, 20.0),
                dt_seconds=1.0,
            ),
            "entity.b": api.MotionSegmentV2(
                start_m=(50.0, 0.0, 0.0),
                end_m=(50.0, 0.0, -20.0),
                velocity_mps=(0.0, 0.0, -20.0),
                dt_seconds=1.0,
            ),
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    assert result.collision_events == ()


def test_radius_parallel_to_polygon_edge_reports_nonzero_first_contact_toi() -> None:
    api = _boundary_api()
    obstacle = api.StaticObstacleV2.polygon(
        "obstacle.edge",
        ((100.0, 100.0), (200.0, 100.0), (200.0, 200.0), (100.0, 200.0)),
    )
    system = api.BoundarySystemV2(geography=boundary_fixture._geography(), boundaries=(obstacle,))
    system.register_entities((api.BoundaryEntityV2("entity.parallel", "surface", 5.0),))
    event = system.evaluate(
        {
            "entity.parallel": api.MotionSegmentV2(
                start_m=(0.0, 95.0, 0.0),
                end_m=(300.0, 95.0, 0.0),
                velocity_mps=(300.0, 0.0, 0.0),
                dt_seconds=1.0,
            )
        },
        tick=1,
        tick_start_time_seconds=0.0,
    ).collision_events[0]
    assert event.time_fraction == pytest.approx(95.0 / 300.0)
    assert event.normal == pytest.approx((-1.0, 0.0, 0.0))


def test_dateline_inverse_closes_and_polar_origin_fails_closed() -> None:
    api = _geo_api()
    service = api.GeographyServiceV2(
        origin_wgs84=(179.999, 45.0, 0.0),
        local_bounds_m=((-1000.0, -1000.0, -10.0), (1000.0, 1000.0, 10.0)),
        map_resolution_m_per_unit=(1.0, 1.0, 1.0),
        map_origin_local_m=(0.0, 0.0, 0.0),
        map_bounds=((-1000.0, -1000.0, -10.0), (1000.0, 1000.0, 10.0)),
        tolerance_m=0.001,
    )
    point = (-179.999, 45.0, 0.0)
    local = service.to_local(frame="wgs84", coordinates=point)
    inverse = service.from_local(frame="wgs84", coordinates_m=local)
    assert ((inverse[0] - point[0] + 180.0) % 360.0) - 180.0 == pytest.approx(0.0)
    assert inverse[1:] == pytest.approx(point[1:])
    with pytest.raises(api.GeographyErrorV2) as captured:
        api.GeographyServiceV2(
            origin_wgs84=(0.0, 90.0, 0.0),
            local_bounds_m=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)),
            map_resolution_m_per_unit=(1.0, 1.0, 1.0),
            map_origin_local_m=(0.0, 0.0, 0.0),
            map_bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)),
            tolerance_m=0.001,
        )
    assert captured.value.code == "geography.polar_origin_unsupported"


@pytest.mark.parametrize(
    "vertices",
    (
        ((100.0, 100.0), (220.0, 140.0), (180.0, 240.0), (60.0, 200.0)),
        ((100.0, 100.0), (220.0, 100.0), (160.0, 240.0)),
        (
            (100.0, 100.0),
            (240.0, 100.0),
            (240.0, 220.0),
            (170.0, 160.0),
            (100.0, 220.0),
        ),
    ),
)
def test_radius_capsule_sweep_finds_earliest_toi_for_rotated_triangle_and_concave_polygon(
    vertices: tuple[tuple[float, float], ...],
) -> None:
    api = _boundary_api()
    obstacle = api.StaticObstacleV2.polygon("obstacle.arbitrary", vertices)
    system = api.BoundarySystemV2(geography=boundary_fixture._geography(), boundaries=(obstacle,))
    system.register_entities((api.BoundaryEntityV2("entity.sweep", "surface", 7.0),))
    segment = api.MotionSegmentV2(
        start_m=(0.0, 150.0, 0.0),
        end_m=(300.0, 150.0, 0.0),
        velocity_mps=(300.0, 0.0, 0.0),
        dt_seconds=1.0,
    )
    optimized = system.evaluate(
        {"entity.sweep": segment}, tick=1, tick_start_time_seconds=0.0
    ).collision_events[0]
    oracle_toi = _polygon_sweep_oracle(vertices, 7.0)
    assert optimized.time_fraction == pytest.approx(oracle_toi, abs=1e-5)


@pytest.mark.parametrize("z_overlap", (False, True))
def test_entity_collision_uses_intersection_of_xy_and_z_contact_time_intervals(
    z_overlap: bool,
) -> None:
    api = _boundary_api()
    system = _collision_system(("entity.a", "entity.b"))
    second_z = -10.0 if z_overlap else -30.0
    result = system.evaluate(
        {
            "entity.a": api.MotionSegmentV2(
                start_m=(0.0, 0.0, 0.0),
                end_m=(100.0, 0.0, 20.0),
                velocity_mps=(100.0, 0.0, 20.0),
                dt_seconds=1.0,
            ),
            "entity.b": api.MotionSegmentV2(
                start_m=(50.0, 0.0, 20.0),
                end_m=(50.0, 0.0, second_z),
                velocity_mps=(0.0, 0.0, second_z - 20.0),
                dt_seconds=1.0,
            ),
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    assert bool(result.collision_events) is z_overlap
    if z_overlap:
        assert result.collision_events[0].time_fraction > 0.0


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_real_broadphase_matches_independent_bruteforce_oracle_and_reverse_order(
    count: int,
) -> None:
    api = _boundary_api()
    identifiers = tuple(f"entity.{index:03d}" for index in range(count))
    motions = {
        identifier: api.MotionSegmentV2(
            start_m=(float(index * 12), float((index % 3) * 4), 0.0),
            end_m=(float(index * 12 + 20), float((index % 3) * 4), 0.0),
            velocity_mps=(20.0, 0.0, 0.0),
            dt_seconds=1.0,
        )
        for index, identifier in enumerate(identifiers)
    }
    forward = _collision_system(identifiers)
    reverse = _collision_system(tuple(reversed(identifiers)))
    broadphase = forward.evaluate(motions, tick=5, tick_start_time_seconds=0.0).collision_events
    oracle = tuple(
        (identifiers[first], identifiers[second], toi)
        for first in range(count)
        for second in range(first + 1, count)
        if (toi := _sphere_pair_toi(motions[identifiers[first]], motions[identifiers[second]], 2.0))
        is not None
    )
    actual = tuple(
        (event.entity_id, event.other_entity_id, event.time_fraction)
        for event in broadphase
        if event.other_entity_id is not None
    )
    assert actual == pytest.approx(oracle)
    assert (
        broadphase
        == reverse.evaluate(motions, tick=5, tick_start_time_seconds=0.0).collision_events
    )
    source = inspect.getsource(api.BoundarySystemV2.evaluate)
    assert "_broadphase_candidates" in source
    assert "evaluate_bruteforce" not in source

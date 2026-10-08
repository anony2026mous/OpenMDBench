"""RF-05 geography conversion and continuous boundary-system contracts."""

from __future__ import annotations

import importlib
import importlib.util
import math
from dataclasses import replace
from types import MappingProxyType
from typing import Any, cast

import pytest
from openmdbench.scenarios.declarative_v2 import ResolvedScenarioV2
from tests.contract import test_declarative_coordinates_v2 as coordinate_fixture


def _geo_api() -> Any:
    module_name = "openmdbench.world.geography_v2"
    assert importlib.util.find_spec(module_name) is not None
    return importlib.import_module(module_name)


def _boundary_api() -> Any:
    module_name = "openmdbench.world.boundary_v2"
    assert importlib.util.find_spec(module_name) is not None
    return importlib.import_module(module_name)


def _resolved() -> Any:
    return coordinate_fixture._compile(coordinate_fixture._scenario())


def _geography() -> Any:
    return _geo_api().GeographyServiceV2.from_resolved_world(_resolved().world)


@pytest.mark.parametrize(
    ("frame", "point"),
    (
        ("local_m", (20.0, 30.0, 40.0)),
        ("wgs84", (120.0001, 30.0001, 40.0)),
        ("map", (5.0, 10.0, 3.0)),
    ),
)
def test_wgs84_local_map_roundtrip_is_deterministic_with_declared_tolerance(
    frame: str, point: tuple[float, float, float]
) -> None:
    service = _geography()
    local = service.to_local(frame=frame, coordinates=point)
    recovered = service.from_local(frame=frame, coordinates_m=local)
    assert service.distance_between(frame=frame, first=point, second=recovered) <= (
        service.tolerance_m
    )
    assert service.to_local(frame=frame, coordinates=recovered) == pytest.approx(
        local, abs=service.tolerance_m
    )


@pytest.mark.parametrize(
    ("target", "distance", "heading"),
    (
        ((0.0, 100.0, 0.0), 100.0, 0.0),
        ((100.0, 0.0, 0.0), 100.0, 90.0),
        ((0.0, -100.0, 0.0), 100.0, 180.0),
        ((-100.0, 0.0, 0.0), 100.0, 270.0),
    ),
)
def test_distance_and_heading_use_north_zero_clockwise_convention(
    target: tuple[float, float, float], distance: float, heading: float
) -> None:
    service = _geography()
    origin = (0.0, 0.0, 0.0)
    assert service.distance_m(origin, target) == pytest.approx(distance)
    assert service.heading_deg(origin, target) == pytest.approx(heading)


@pytest.mark.parametrize(
    ("frame", "coordinates"),
    (
        ("local_m", (math.nan, 0.0, 0.0)),
        ("local_m", (1001.0, 0.0, 0.0)),
        ("map", (-1.0, 0.0, 0.0)),
        ("wgs84", (181.0, 0.0, 0.0)),
        ("wgs84", (0.0, 91.0, 0.0)),
        ("unknown", (0.0, 0.0, 0.0)),
    ),
)
def test_geography_rejects_nonfinite_out_of_bounds_and_unknown_frames(
    frame: str, coordinates: tuple[float, float, float]
) -> None:
    with pytest.raises(_geo_api().GeographyErrorV2) as captured:
        _geography().to_local(frame=frame, coordinates=coordinates)
    assert captured.value.code.startswith("geography.")
    assert captured.value.path
    assert captured.value.reason and captured.value.suggestion


def _system() -> Any:
    return _boundary_api().BoundarySystemV2.from_resolved(
        _resolved(),
        geography=_geography(),
    )


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_entity_registration_order_does_not_change_boundary_results(count: int) -> None:
    api = _boundary_api()
    entities = tuple(
        api.BoundaryEntityV2(
            entity_id=f"entity.{index:03d}",
            domain="air",
            radius_m=1.0,
        )
        for index in range(count)
    )
    forward = _system()
    reverse = _system()
    forward.register_entities(entities)
    reverse.register_entities(tuple(reversed(entities)))
    motions = {
        item.entity_id: api.MotionSegmentV2(
            start_m=(500.0, 500.0, 100.0),
            end_m=(1100.0, 500.0, 100.0),
            dt_seconds=1.0,
        )
        for item in entities
    }
    assert forward.evaluate(motions, tick=10, tick_start_time_seconds=0.0) == reverse.evaluate(
        motions, tick=10, tick_start_time_seconds=0.0
    )


@pytest.mark.parametrize(
    ("start", "end", "expected_kind"),
    (
        ((500.0, 500.0, 100.0), (1100.0, 500.0, 100.0), "world_exit"),
        ((700.0, 800.0, 100.0), (900.0, 800.0, 100.0), "excluded_zone"),
        ((500.0, 500.0, 499.0), (500.0, 500.0, 501.0), "altitude_max"),
        ((500.0, 500.0, -99.0), (500.0, 500.0, -101.0), "depth_max"),
    ),
)
def test_continuous_sweep_detects_world_zone_altitude_and_depth_crossings(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    expected_kind: str,
) -> None:
    api = _boundary_api()
    system = _system()
    system.register_entities((api.BoundaryEntityV2("entity.mobile", "air", 1.0),))
    result = system.evaluate(
        {"entity.mobile": api.MotionSegmentV2(start_m=start, end_m=end, dt_seconds=0.01)},
        tick=10,
        tick_start_time_seconds=0.0,
    )
    assert result.boundary_events[0].kind == expected_kind
    assert 0.0 <= result.boundary_events[0].time_fraction <= 1.0


def test_polygon_edge_circle_tangent_and_high_speed_obstacle_sweep_are_not_tunneled() -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2(
        geography=_geography(),
        boundaries=(
            api.StaticObstacleV2.polygon(
                "obstacle.polygon",
                ((100.0, 100.0), (200.0, 100.0), (200.0, 200.0), (100.0, 200.0)),
            ),
            api.StaticObstacleV2.circle("obstacle.circle", (400.0, 400.0), 25.0),
        ),
        point_on_edge="inside",
    )
    system.register_entities((api.BoundaryEntityV2("entity.fast", "surface", 5.0),))
    polygon = system.evaluate(
        {
            "entity.fast": api.MotionSegmentV2(
                start_m=(0.0, 100.0, 0.0),
                end_m=(1000.0, 100.0, 0.0),
                dt_seconds=0.001,
            )
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    tangent = system.evaluate(
        {
            "entity.fast": api.MotionSegmentV2(
                start_m=(0.0, 430.0, 0.0),
                end_m=(1000.0, 430.0, 0.0),
                dt_seconds=1.0,
            )
        },
        tick=2,
        tick_start_time_seconds=0.0,
    )
    assert polygon.collision_events[0].obstacle_id == "obstacle.polygon"
    assert tangent.collision_events[0].obstacle_id == "obstacle.circle"


@pytest.mark.parametrize(
    "policy",
    ("reject", "constrain", "stop", "reflect", "effect", "deactivate", "mission_event"),
)
def test_controlled_boundary_policies_emit_stable_events_and_intents(policy: str) -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2.with_policy(
        geography=_geography(),
        policy=api.BoundaryPolicyV2(policy=policy),
    )
    system.register_entities((api.BoundaryEntityV2("entity.policy", "air", 1.0),))
    result = system.evaluate(
        {
            "entity.policy": api.MotionSegmentV2(
                start_m=(999.0, 500.0, 100.0),
                end_m=(1100.0, 500.0, 100.0),
                dt_seconds=1.0,
            )
        },
        tick=7,
        tick_start_time_seconds=0.0,
    )
    assert all(isinstance(item, api.BoundaryEventV2) for item in result.boundary_events)
    assert all(isinstance(item, api.CollisionEventV2) for item in result.collision_events)
    assert all(isinstance(item, api.DamageIntentV2) for item in result.damage_intents)
    assert result.policy_actions[0].policy == policy
    assert result.to_json() == result.to_json()


@pytest.mark.parametrize("policy", ("execute_python", "teleport", "destroy_immediately", ""))
def test_configuration_selects_only_controlled_policy_and_cannot_execute_code(policy: str) -> None:
    with pytest.raises(ValueError):
        _boundary_api().BoundaryPolicyV2(policy=policy)


@pytest.mark.parametrize("dt_seconds", (0.0, -1.0, math.nan, math.inf, True))
def test_sweep_requires_positive_finite_nonboolean_dt(dt_seconds: Any) -> None:
    api = _boundary_api()
    with pytest.raises(ValueError):
        api.MotionSegmentV2(
            start_m=(0.0, 0.0, 0.0),
            end_m=(1.0, 1.0, 0.0),
            dt_seconds=dt_seconds,
        )


def test_ordinary_mission_or_scoring_zone_is_not_implicitly_an_excluded_zone() -> None:
    payload = coordinate_fixture._scenario()
    payload["world"]["zones"].append(
        {
            "id": "zone.mission-score",
            "geometry": {
                "type": "circle",
                "center": {"frame": "local_m", "coordinates": [400.0, 400.0]},
                "radius_m": 50.0,
            },
            "domains": ["air"],
        }
    )
    resolved = coordinate_fixture._compile(payload)
    system = _boundary_api().BoundarySystemV2.from_resolved(
        resolved,
        geography=_geo_api().GeographyServiceV2.from_resolved_world(resolved.world),
    )
    api = _boundary_api()
    system.register_entities((api.BoundaryEntityV2("entity.zone", "air", 1.0),))
    result = system.evaluate(
        {
            "entity.zone": api.MotionSegmentV2(
                start_m=(300.0, 400.0, 100.0),
                end_m=(500.0, 400.0, 100.0),
                dt_seconds=1.0,
            )
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    assert all(event.boundary_id != "zone.mission-score" for event in result.boundary_events)


def test_each_resolved_boundary_keeps_its_own_action_independent_of_name_and_order() -> None:
    payload = coordinate_fixture._scenario()
    payload["world"]["zones"].append(
        {
            "id": "zone.secondary",
            "geometry": {
                "type": "circle",
                "center": {"frame": "local_m", "coordinates": [500.0, 500.0]},
                "radius_m": 100.0,
            },
            "domains": ["air"],
        }
    )
    payload["world"]["boundaries"].append(
        {
            "id": "boundary.secondary",
            "zone_id": "zone.secondary",
            "action": "stop",
            "point_on_edge": "inside",
        }
    )
    first = coordinate_fixture._compile(payload)
    renamed = coordinate_fixture._scenario()
    renamed["world"] = payload["world"]
    renamed["world"]["boundaries"] = list(reversed(renamed["world"]["boundaries"]))
    renamed["world"]["boundaries"][0]["id"] = "boundary.zzz-renamed"
    second = coordinate_fixture._compile(renamed)
    api = _boundary_api()
    first_system = api.BoundarySystemV2.from_resolved(
        first, geography=_geo_api().GeographyServiceV2.from_resolved_world(first.world)
    )
    second_system = api.BoundarySystemV2.from_resolved(
        second, geography=_geo_api().GeographyServiceV2.from_resolved_world(second.world)
    )
    assert first_system.zone_policy("zone.operating").policy == "constrain"
    assert first_system.zone_policy("zone.secondary").policy == "stop"
    assert second_system.zone_policy("zone.operating").policy == "constrain"
    assert second_system.zone_policy("zone.secondary").policy == "stop"


@pytest.mark.parametrize("geometry_type", ("polygon", "circle"))
def test_allowed_zone_inside_to_outside_has_precise_positive_exit_toi(geometry_type: str) -> None:
    api = _boundary_api()
    allowed = (
        api.AllowedZoneV2.polygon(
            "zone.allowed",
            ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)),
        )
        if geometry_type == "polygon"
        else api.AllowedZoneV2.circle("zone.allowed", (50.0, 50.0), 50.0)
    )
    system = api.BoundarySystemV2(
        geography=_geography(),
        allowed_zones=(allowed,),
        zone_policies={"zone.allowed": api.BoundaryPolicyV2("constrain")},
    )
    system.register_entities((api.BoundaryEntityV2("entity.exit", "air", 5.0),))
    result = system.evaluate(
        {
            "entity.exit": api.MotionSegmentV2(
                start_m=(50.0, 50.0, 0.0),
                end_m=(150.0, 50.0, 0.0),
                velocity_mps=(100.0, 0.0, 0.0),
                dt_seconds=1.0,
            )
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    event = result.boundary_events[0]
    assert event.kind == "allowed_zone"
    assert event.time_fraction == pytest.approx(0.45)
    assert event.normal == pytest.approx((1.0, 0.0, 0.0))


@pytest.mark.parametrize("policy", ("reject", "stop", "constrain", "reflect"))
def test_motion_velocity_and_boundary_normal_produce_distinct_typed_responses(policy: str) -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2.with_policy(
        geography=_geography(), policy=api.BoundaryPolicyV2(policy)
    )
    system.register_entities((api.BoundaryEntityV2("entity.response", "air", 1.0),))
    result = system.evaluate(
        {
            "entity.response": api.MotionSegmentV2(
                start_m=(900.0, 500.0, 100.0),
                end_m=(1100.0, 500.0, 100.0),
                velocity_mps=(200.0, 10.0, 0.0),
                dt_seconds=1.0,
            )
        },
        tick=2,
        tick_start_time_seconds=0.0,
    )
    action = result.policy_actions[0]
    assert action.policy == policy
    assert action.boundary_normal == pytest.approx((1.0, 0.0, 0.0))
    expected_velocity = {
        "reject": (200.0, 10.0, 0.0),
        "stop": (0.0, 0.0, 0.0),
        "constrain": (0.0, 10.0, 0.0),
        "reflect": (-200.0, 10.0, 0.0),
    }[policy]
    assert action.resolved_velocity_mps == pytest.approx(expected_velocity)


@pytest.mark.parametrize(
    ("policy", "intent_type"),
    (("deactivate", "DeactivateIntentV2"), ("mission_event", "MissionEventIntentV2")),
)
def test_deactivate_and_mission_event_are_typed_intents(policy: str, intent_type: str) -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2.with_policy(
        geography=_geography(), policy=api.BoundaryPolicyV2(policy)
    )
    system.register_entities((api.BoundaryEntityV2("entity.intent", "air", 1.0),))
    result = system.evaluate(
        {
            "entity.intent": api.MotionSegmentV2(
                start_m=(999.0, 500.0, 100.0),
                end_m=(1001.0, 500.0, 100.0),
                velocity_mps=(2.0, 0.0, 0.0),
                dt_seconds=1.0,
            )
        },
        tick=3,
        tick_start_time_seconds=0.0,
    )
    assert type(result.lifecycle_intents[0]).__name__ == intent_type


@pytest.mark.parametrize(
    ("dto", "changes"),
    (
        ("BoundaryEventV2", {"event_id": "", "time_fraction": 2.0}),
        ("CollisionEventV2", {"entity_id": "", "time_fraction": math.nan}),
    ),
)
def test_event_dtos_reject_invalid_identity_fraction_and_nonfinite_values(
    dto: str, changes: dict[str, Any]
) -> None:
    api = _boundary_api()
    values = {
        "event_id": "event.valid",
        "tick": 1,
        "entity_id": "entity.valid",
        "time_fraction": 0.5,
        "position_m": (0.0, 0.0, 0.0),
    }
    if dto == "BoundaryEventV2":
        values.update(kind="world_exit", boundary_id="world.bounds")
    else:
        values.update(obstacle_id="obstacle.valid", other_entity_id=None)
    values.update(changes)
    with pytest.raises(ValueError):
        getattr(api, dto)(**values)


@pytest.mark.parametrize("corruption", ("binding_content", "binding_hash", "deployment"))
def test_from_resolved_revalidates_complete_resolved_integrity_after_outer_rehash(
    corruption: str,
) -> None:
    resolved = _resolved()
    entity = resolved.entities[0]
    if corruption == "deployment":
        attacked_entity = replace(
            entity,
            boundary_deployment=replace(
                entity.boundary_deployment, allowed_zone_ids=("zone.missing",)
            ),
        )
    else:
        bindings = dict(entity.resource_bindings)
        platform = bindings["platforms"][0]
        if corruption == "binding_content":
            content = dict(platform.normalized_content)
            content["domain"] = "forged-domain"
            platform = replace(platform, normalized_content=MappingProxyType(content))
        else:
            platform = replace(platform, content_hash="sha256:" + "f" * 64)
        bindings["platforms"] = (platform,)
        attacked_entity = replace(entity, resource_bindings=MappingProxyType(bindings))
    attacked = replace(resolved, entities=(attacked_entity, *resolved.entities[1:]))
    attacked = replace(
        attacked,
        resolved_hash=ResolvedScenarioV2.compute_resolved_hash(
            attacked._payload(include_hash=False)
        ),
    )
    with pytest.raises(_boundary_api().BoundaryErrorV2) as captured:
        _boundary_api().BoundarySystemV2.from_resolved(
            attacked,
            geography=_geo_api().GeographyServiceV2.from_resolved_world(attacked.world),
        )
    assert captured.value.code == "boundary.resolved_integrity_invalid"


def test_same_zone_can_be_allowed_for_one_entity_and_excluded_for_another() -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2.from_resolved(_resolved(), geography=_geography())
    system.register_entities(
        (
            api.BoundaryEntityV2(
                "entity.allowed",
                "air",
                1.0,
                allowed_zone_ids=("zone.operating",),
                excluded_zone_ids=(),
            ),
            api.BoundaryEntityV2(
                "entity.excluded",
                "air",
                1.0,
                allowed_zone_ids=(),
                excluded_zone_ids=("zone.operating",),
            ),
        )
    )
    segment = api.MotionSegmentV2(
        start_m=(100.0, 100.0, 100.0),
        end_m=(200.0, 100.0, 100.0),
        velocity_mps=(100.0, 0.0, 0.0),
        dt_seconds=1.0,
    )
    result = system.evaluate(
        {"entity.allowed": segment, "entity.excluded": segment},
        tick=1,
        tick_start_time_seconds=0.0,
    )
    facts = {(event.entity_id, event.kind) for event in result.boundary_events}
    assert ("entity.allowed", "excluded_zone") not in facts
    assert ("entity.excluded", "excluded_zone") in facts


def test_boundary_priority_compiles_roundtrips_integrity_checks_and_orders_runtime() -> None:
    payload = coordinate_fixture._scenario()
    payload["world"]["boundaries"][0]["priority"] = 5
    payload["world"]["zones"].append(
        {
            "id": "zone.priority-high",
            "geometry": {
                "type": "circle",
                "center": {"frame": "local_m", "coordinates": [500.0, 500.0]},
                "radius_m": 100.0,
            },
            "domains": ["air"],
        }
    )
    payload["world"]["boundaries"].append(
        {
            "id": "boundary.priority-high",
            "zone_id": "zone.priority-high",
            "action": "stop",
            "point_on_edge": "inside",
            "priority": 20,
        }
    )
    resolved = coordinate_fixture._compile(payload)
    assert tuple(cast(Any, item).priority for item in resolved.world.boundaries) == (5, 20)
    recovered = ResolvedScenarioV2.from_json(resolved.to_json())
    assert tuple(cast(Any, item).priority for item in recovered.world.boundaries) == (5, 20)
    system = _boundary_api().BoundarySystemV2.from_resolved(
        recovered,
        geography=_geo_api().GeographyServiceV2.from_resolved_world(recovered.world),
    )
    assert system.zone_policy("zone.priority-high").priority == 20


def test_stop_uses_contact_point_zero_velocity_and_excluded_constrain_uses_outward_normal() -> None:
    api = _boundary_api()
    for policy in ("stop", "constrain"):
        system = api.BoundarySystemV2.with_policy(
            geography=_geography(), policy=api.BoundaryPolicyV2(policy)
        )
        system.register_entities((api.BoundaryEntityV2("entity.response", "air", 1.0),))
        result = system.evaluate(
            {
                "entity.response": api.MotionSegmentV2(
                    start_m=(700.0, 800.0, 100.0),
                    end_m=(900.0, 800.0, 100.0),
                    velocity_mps=(200.0, 0.0, 0.0),
                    dt_seconds=1.0,
                )
            },
            tick=1,
            tick_start_time_seconds=0.0,
        )
        action = next(
            item
            for item in result.policy_actions
            if item.cause_event_id.startswith("boundary-event")
        )
        assert action.resolved_end_m == pytest.approx(action.contact_position_m)
        if policy == "stop":
            assert action.resolved_velocity_mps == (0.0, 0.0, 0.0)
        else:
            assert action.boundary_normal == pytest.approx((-1.0, 0.0, 0.0))
            assert action.resolved_velocity_mps[0] == pytest.approx(0.0)


def test_absolute_event_time_is_stable_from_tick_dt_and_toi() -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2.with_policy(
        geography=_geography(), policy=api.BoundaryPolicyV2("stop")
    )
    system.register_entities((api.BoundaryEntityV2("entity.clock", "air", 1.0),))
    result = system.evaluate(
        {
            "entity.clock": api.MotionSegmentV2(
                start_m=(900.0, 500.0, 100.0),
                end_m=(1100.0, 500.0, 100.0),
                velocity_mps=(100.0, 0.0, 0.0),
                dt_seconds=2.0,
            )
        },
        tick=7,
        tick_start_time_seconds=14.0,
    )
    event = result.boundary_events[0]
    assert event.absolute_time_seconds == pytest.approx(14.0 + 2.0 * event.time_fraction)


def test_explicit_tick_start_time_is_the_single_clock_for_all_collision_kinds() -> None:
    api = _boundary_api()
    boundary_system = _system()
    boundary_system.register_entities((api.BoundaryEntityV2("entity.boundary", "air", 1.0),))
    static_system = api.BoundarySystemV2(
        geography=_geography(),
        boundaries=(api.StaticObstacleV2.circle("obstacle.clock", (50.0, 100.0), 10.0),),
    )
    static_system.register_entities((api.BoundaryEntityV2("entity.static", "surface", 1.0),))
    entity_system = api.BoundarySystemV2(
        geography=_geography(), boundaries=(), enable_entity_collisions=True
    )
    entity_system.register_entities(
        (
            api.BoundaryEntityV2("entity.alpha", "air", 1.0),
            api.BoundaryEntityV2("entity.beta", "air", 1.0),
        )
    )
    boundary = boundary_system.evaluate(
        {
            "entity.boundary": api.MotionSegmentV2(
                start_m=(900.0, 500.0, 100.0),
                end_m=(1100.0, 500.0, 100.0),
                dt_seconds=2.0,
            )
        },
        tick=41,
        tick_start_time_seconds=100.0,
    ).boundary_events[0]
    static = static_system.evaluate(
        {
            "entity.static": api.MotionSegmentV2(
                start_m=(0.0, 100.0, 0.0),
                end_m=(100.0, 100.0, 0.0),
                dt_seconds=2.0,
            )
        },
        tick=41,
        tick_start_time_seconds=100.0,
    ).collision_events[0]
    entity = entity_system.evaluate(
        {
            "entity.alpha": api.MotionSegmentV2(
                start_m=(0.0, 0.0, 0.0), end_m=(100.0, 0.0, 0.0), dt_seconds=2.0
            ),
            "entity.beta": api.MotionSegmentV2(
                start_m=(100.0, 0.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=2.0
            ),
        },
        tick=41,
        tick_start_time_seconds=100.0,
    ).collision_events[0]
    for event in (boundary, static, entity):
        assert event.absolute_time_seconds == pytest.approx(100.0 + 2.0 * event.time_fraction)
    repeated = entity_system.evaluate(
        {
            "entity.alpha": api.MotionSegmentV2(
                start_m=(0.0, 0.0, 0.0), end_m=(100.0, 0.0, 0.0), dt_seconds=2.0
            ),
            "entity.beta": api.MotionSegmentV2(
                start_m=(100.0, 0.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=2.0
            ),
        },
        tick=999,
        tick_start_time_seconds=100.0,
    ).collision_events[0]
    assert repeated.absolute_time_seconds == entity.absolute_time_seconds


def test_all_facts_remain_but_only_highest_priority_response_wins_per_entity() -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2(
        geography=_geography(),
        boundaries=(
            api.StaticObstacleV2.circle("boundary.zeta", (50.0, 50.0), 20.0, priority=20),
            api.StaticObstacleV2.circle("boundary.alpha", (50.0, 50.0), 20.0, priority=20),
            api.StaticObstacleV2.circle("boundary.low", (50.0, 50.0), 20.0, priority=5),
        ),
        policy=api.BoundaryPolicyV2("stop"),
    )
    system.register_entities((api.BoundaryEntityV2("entity.priority", "surface", 1.0),))
    result = system.evaluate(
        {
            "entity.priority": api.MotionSegmentV2(
                start_m=(0.0, 50.0, 0.0), end_m=(100.0, 50.0, 0.0), dt_seconds=1.0
            )
        },
        tick=0,
        tick_start_time_seconds=0.0,
    )
    assert tuple(event.boundary_id for event in result.boundary_events) == (
        "boundary.alpha",
        "boundary.zeta",
        "boundary.low",
    )
    assert len(result.policy_actions) == 1
    assert result.policy_actions[0].cause_event_id.endswith("boundary.alpha")
    assert result.policy_actions[0].policy == "stop"


def test_entity_collision_emits_symmetric_responses_and_damage_intents() -> None:
    api = _boundary_api()
    system = api.BoundarySystemV2(
        geography=_geography(), boundaries=(), enable_entity_collisions=True
    )
    system.register_entities(
        (
            api.BoundaryEntityV2("entity.alpha", "air", 5.0),
            api.BoundaryEntityV2("entity.beta", "air", 5.0),
        )
    )
    result = system.evaluate(
        {
            "entity.alpha": api.MotionSegmentV2(
                start_m=(0.0, 0.0, 0.0), end_m=(100.0, 0.0, 0.0), dt_seconds=1.0
            ),
            "entity.beta": api.MotionSegmentV2(
                start_m=(100.0, 0.0, 0.0), end_m=(0.0, 0.0, 0.0), dt_seconds=1.0
            ),
        },
        tick=0,
        tick_start_time_seconds=0.0,
    )
    assert {item.entity_id for item in result.policy_actions} == {"entity.alpha", "entity.beta"}
    assert {item.target_entity_id for item in result.damage_intents} == {
        "entity.alpha",
        "entity.beta",
    }
    assert result.policy_actions[0].normal == tuple(
        -value for value in result.policy_actions[1].normal
    )


def test_boundary_entity_materialization_requires_validated_resolved_anchor() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    api = _boundary_api()
    resolved = resource_fixture._compile(resource_fixture._catalog())
    entity = resolved.entities[0]
    with pytest.raises(api.BoundaryErrorV2) as missing:
        api.BoundaryEntityV2.from_resolved(entity)
    assert missing.value.code == "boundary.resolved_anchor_required"
    materialized = api.BoundaryEntityV2.from_resolved(
        entity,
        resolved_scenario=resolved,
        expected_resolved_hash=resolved.resolved_hash,
    )
    assert materialized.entity_id == entity.id
    bindings = dict(entity.resource_bindings)
    platform = bindings["platforms"][0]
    bindings["platforms"] = (replace(platform, content_hash="sha256:" + "9" * 64),)
    forged_entity = replace(entity, resource_bindings=MappingProxyType(bindings))
    forged = replace(resolved, entities=(forged_entity, *resolved.entities[1:]))
    forged = replace(
        forged,
        resolved_hash=ResolvedScenarioV2.compute_resolved_hash(forged._payload(include_hash=False)),
    )
    with pytest.raises(api.BoundaryErrorV2) as corrupted:
        api.BoundaryEntityV2.from_resolved(
            forged_entity,
            resolved_scenario=forged,
            expected_resolved_hash=forged.resolved_hash,
        )
    assert corrupted.value.code == "boundary.resolved_integrity_invalid"

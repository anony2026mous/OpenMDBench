"""RF-03 RED contracts for coordinates, geometry, and deployment validation."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest
from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
)
from openmdbench.scenarios.declarative_v2 import (
    CompilerErrorV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)

PLUGIN_HASH = "sha256:" + "7" * 64


def _catalog() -> CatalogV2:
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.coordinate-contract",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position_m": "m"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256=PLUGIN_HASH,
            resource_types=("platforms", "dynamics"),
            field_units={"position_m": "m"},
        ),
        lambda definition: definition,
    )
    registry.freeze()
    resources: list[CatalogResourceV2] = []
    for domain in ("air", "surface"):
        dynamics = CatalogResourceV2(
            schema_version="2.0",
            resource_type="dynamics",
            id=f"dynamics.{domain}",
            version="2.0.0",
            engine_compatibility=">=2.0.0,<3.0.0",
            model_id="models.coordinate-contract@2.0.0",
            content={"compatible_platform_types": [domain], "mobile": True},
        )
        platform = CatalogResourceV2(
            schema_version="2.0",
            resource_type="platforms",
            id=f"platforms.{domain}",
            version="2.0.0",
            engine_compatibility=">=2.0.0,<3.0.0",
            model_id="models.coordinate-contract@2.0.0",
            content={
                "platform_type": domain,
                "domain": domain,
                "mobile": True,
                "allowed_dynamics": [dynamics.exact_ref],
                "component_slots": [],
                "payload_capacity_kg": 0.0,
            },
        )
        resources.extend((platform, dynamics))
    return CatalogV2(resources, engine_version="2.0.0", model_registry=registry)


def _position(frame: str, coordinates: list[float]) -> dict[str, Any]:
    return {"frame": frame, "coordinates": coordinates}


def _scenario(position: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "scenario_id": "scenario.coordinate-contract",
        "factions": [{"schema_version": "2.0", "id": "faction.arbitrary"}],
        "relationships": [],
        "entities": [
            {
                "schema_version": "2.0",
                "id": "vehicle.arbitrary",
                "faction_id": "faction.arbitrary",
                "platform_ref": "platforms.air@2.0.0",
                "dynamics_ref": "dynamics.air@2.0.0",
                "initial_state": {
                    "schema_version": "2.0",
                    "position": position or _position("local_m", [20.0, 30.0, 40.0]),
                    "velocity_mps": [0.0, 0.0, 0.0],
                    "heading_deg": 0.0,
                },
                "deployment": {
                    "allowed_zone_ids": ["zone.operating"],
                    "excluded_zone_ids": ["zone.excluded"],
                    "point_on_edge": "inside",
                },
            }
        ],
        "formations": [],
        "world": {
            "schema_version": "2.0",
            "duration_ticks": 1000,
            "tick_seconds": 1.0,
            "coordinate_frame": {
                "canonical_frame": "local_m",
                "origin_wgs84": [120.0, 30.0, 0.0],
                "axis_orientation": "east_north_up",
                "height_semantics": "metres_above_origin",
                "local_bounds_m": [[0.0, 0.0, -100.0], [1000.0, 1000.0, 500.0]],
                "tolerance_m": 0.001,
            },
            "map_transform": {
                "resolution_m_per_unit": [2.0, 2.0, 1.0],
                "map_origin_local_m": [10.0, 10.0, 0.0],
                "axis_orientation": "east_north_up",
                "map_bounds": [[0.0, 0.0, -100.0], [495.0, 495.0, 500.0]],
            },
            "zones": [
                {
                    "id": "zone.operating",
                    "geometry": {
                        "type": "polygon",
                        "positions": [
                            _position("local_m", [0.0, 0.0]),
                            _position("map", [495.0, 0.0]),
                            _position("map", [495.0, 495.0]),
                            _position("local_m", [0.0, 1000.0]),
                        ],
                    },
                    "domains": ["air", "surface"],
                },
                {
                    "id": "zone.excluded",
                    "geometry": {
                        "type": "circle",
                        "center": _position("local_m", [800.0, 800.0]),
                        "radius_m": 25.0,
                    },
                    "domains": ["air"],
                },
            ],
            "boundaries": [
                {
                    "id": "boundary.operating",
                    "zone_id": "zone.operating",
                    "action": "constrain_motion",
                    "point_on_edge": "inside",
                }
            ],
        },
        "events": [
            {
                "schema_version": "2.0",
                "id": "event.marker",
                "event_type": "mission_marker",
                "trigger": {"kind": "tick", "tick": 1},
                "priority": 0,
                "depends_on": [],
                "payload": {
                    "marker_id": "marker.coordinate-contract",
                    "position": _position("map", [5.0, 10.0, 3.0]),
                },
            }
        ],
        "mission_rules": [],
        "score_metrics": [],
    }


def _compile(payload: dict[str, Any]) -> Any:
    package = ScenarioPackageV2.from_mapping({"schema_version": "package@2.0", "scenario": payload})
    return ScenarioCompilerV2(catalog=_catalog()).compile(package)


def _assert_error(
    payload: dict[str, Any], *, code: str, path_contains: tuple[str, ...]
) -> CompilerErrorV2:
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(payload)
    error = captured.value
    assert error.code == code
    assert all(part in error.path for part in path_contains)
    assert error.file and error.value is not None
    assert error.reason and error.suggestion
    return error


@pytest.mark.parametrize(
    ("position", "expected"),
    (
        (_position("local_m", [20.0, 30.0, 40.0]), (20.0, 30.0, 40.0)),
        (_position("map", [5.0, 10.0, 40.0]), (20.0, 30.0, 40.0)),
        (_position("wgs84", [120.00020746, 30.00026949, 40.0]), (20.0, 30.0, 40.0)),
    ),
)
def test_discriminated_positions_normalize_to_canonical_local_metres(
    position: dict[str, Any], expected: tuple[float, float, float]
) -> None:
    resolved = _compile(_scenario(position))
    assert resolved.world.coordinate_frame.canonical_frame == "local_m"
    assert resolved.entities[0].initial_state.position_m == pytest.approx(expected, abs=0.05)
    assert resolved.world.zones[0].geometry.positions_m[1] == pytest.approx(
        (1000.0, 10.0), abs=0.001
    )
    assert resolved.events[0].payload["position_m"] == pytest.approx((20.0, 30.0, 3.0), abs=0.001)


def test_representation_and_input_order_are_hash_equivalent() -> None:
    local = _scenario(_position("local_m", [20.0, 30.0, 40.0]))
    mapped = _scenario(_position("map", [5.0, 10.0, 40.0]))
    mapped["world"]["zones"] = list(reversed(mapped["world"]["zones"]))
    assert _compile(local).resolved_hash == _compile(mapped).resolved_hash


@pytest.mark.parametrize(
    ("mutate", "code", "path"),
    (
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("wgs84", [181.0, 0.0, 0.0])
            ),
            "scenario.coordinate_invalid",
            ("position",),
        ),
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("wgs84", [0.0, 91.0, 0.0])
            ),
            "scenario.coordinate_invalid",
            ("position",),
        ),
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("local_m", [1.0, 2.0])
            ),
            "scenario.coordinate_invalid",
            ("position",),
        ),
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("local_m", [1.0, math.inf, 2.0])
            ),
            "scenario.coordinate_invalid",
            ("position",),
        ),
        (
            lambda p: p["world"].pop("coordinate_frame"),
            "scenario.coordinate_frame_missing",
            ("world",),
        ),
        (lambda p: p["world"].pop("map_transform"), "scenario.map_transform_missing", ("world",)),
        (
            lambda p: p["world"]["map_transform"].update(resolution_m_per_unit=[0.0, 2.0, 1.0]),
            "scenario.map_scale_invalid",
            ("map_transform", "resolution_m_per_unit"),
        ),
        (
            lambda p: p["world"]["map_transform"].update(resolution_m_per_unit=[-1.0, 2.0, 1.0]),
            "scenario.map_scale_invalid",
            ("map_transform", "resolution_m_per_unit"),
        ),
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("local_m", [1001.0, 2.0, 3.0])
            ),
            "scenario.coordinate_out_of_bounds",
            ("position",),
        ),
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("map", [496.0, 2.0, 3.0])
            ),
            "scenario.coordinate_out_of_bounds",
            ("position",),
        ),
        (
            lambda p: p["entities"][0]["initial_state"].update(
                position=_position("local_m", [2.0, 3.0, 501.0])
            ),
            "scenario.altitude_out_of_bounds",
            ("position",),
        ),
    ),
)
def test_invalid_frames_transforms_dimensions_and_bounds_are_stable_errors(
    mutate: Any, code: str, path: tuple[str, ...]
) -> None:
    payload = _scenario()
    mutate(payload)
    _assert_error(payload, code=code, path_contains=path)


@pytest.mark.parametrize(
    ("geometry", "code"),
    (
        (
            {
                "type": "polygon",
                "positions": [_position("local_m", [0.0, 0.0]), _position("local_m", [1.0, 0.0])],
            },
            "scenario.zone_geometry_invalid",
        ),
        (
            {
                "type": "polygon",
                "positions": [
                    _position("local_m", [0.0, 0.0]),
                    _position("local_m", [10.0, 10.0]),
                    _position("local_m", [0.0, 10.0]),
                    _position("local_m", [10.0, 0.0]),
                ],
            },
            "scenario.zone_self_intersection",
        ),
        (
            {"type": "circle", "center": _position("local_m", [10.0, 10.0]), "radius_m": 0.0},
            "scenario.zone_geometry_invalid",
        ),
        (
            {"type": "circle", "center": _position("local_m", [999.0, 999.0]), "radius_m": 10.0},
            "scenario.zone_out_of_bounds",
        ),
    ),
)
def test_zone_geometry_rejects_degenerate_self_intersecting_and_outside_shapes(
    geometry: dict[str, Any], code: str
) -> None:
    payload = _scenario()
    payload["world"]["zones"][0]["geometry"] = geometry
    _assert_error(payload, code=code, path_contains=("world", "zones"))


@pytest.mark.parametrize(
    ("change", "code"),
    (
        ({"zone_id": "zone.missing"}, "scenario.boundary_zone_missing"),
        ({"action": "execute_user_python"}, "scenario.boundary_action_invalid"),
        ({"point_on_edge": "maybe"}, "scenario.edge_policy_invalid"),
    ),
)
def test_boundary_references_actions_and_edge_policy_are_validated(
    change: dict[str, str], code: str
) -> None:
    payload = _scenario()
    payload["world"]["boundaries"][0].update(change)
    _assert_error(payload, code=code, path_contains=("world", "boundaries"))


def test_zone_and_boundary_ids_are_unique() -> None:
    payload = _scenario()
    payload["world"]["zones"].append(copy.deepcopy(payload["world"]["zones"][0]))
    _assert_error(payload, code="scenario.zone_duplicate", path_contains=("world", "zones"))
    payload = _scenario()
    payload["world"]["boundaries"].append(copy.deepcopy(payload["world"]["boundaries"][0]))
    _assert_error(
        payload, code="scenario.boundary_duplicate", path_contains=("world", "boundaries")
    )


def test_deployment_validates_platform_domain_allowed_excluded_and_edge_policy() -> None:
    payload = _scenario(_position("local_m", [800.0, 800.0, 40.0]))
    _assert_error(
        payload,
        code="scenario.deployment_excluded",
        path_contains=("entities", "deployment"),
    )
    payload = _scenario()
    payload["world"]["zones"][0]["domains"] = ["surface"]
    _assert_error(
        payload,
        code="scenario.deployment_domain_incompatible",
        path_contains=("entities", "deployment"),
    )
    payload = _scenario(_position("local_m", [0.0, 500.0, 40.0]))
    payload["entities"][0]["deployment"]["point_on_edge"] = "outside"
    _assert_error(
        payload,
        code="scenario.deployment_outside_allowed",
        path_contains=("entities", "deployment"),
    )


def test_deterministically_empty_feasible_deployment_is_rejected() -> None:
    payload = _scenario()
    payload["world"]["zones"][1]["geometry"] = copy.deepcopy(
        payload["world"]["zones"][0]["geometry"]
    )
    _assert_error(
        payload,
        code="scenario.deployment_feasible_region_empty",
        path_contains=("entities", "deployment"),
    )


@pytest.mark.parametrize(
    ("coordinate_system", "code"),
    (
        ("wgs84", "scenario.coordinate_frame_missing"),
        ("map", "scenario.map_transform_missing"),
    ),
)
def test_v2_never_implicitly_falls_back_to_legacy_position_m_without_metadata(
    coordinate_system: str, code: str
) -> None:
    payload = _scenario()
    state = payload["entities"][0]["initial_state"]
    state["position_m"] = [20.0, 30.0, 40.0]
    state.pop("position")
    payload["world"] = {
        "schema_version": "2.0",
        "coordinate_system": coordinate_system,
        "zones": [],
    }
    _assert_error(payload, code=code, path_contains=("world",))


def test_wgs84_dateline_uses_shortest_longitude_delta_deterministically() -> None:
    payload = _scenario(_position("wgs84", [-179.9999, 0.0, 40.0]))
    frame = payload["world"]["coordinate_frame"]
    frame["origin_wgs84"] = [179.9999, 0.0, 0.0]
    frame["local_bounds_m"] = [[-100.0, -100.0, -100.0], [100.0, 100.0, 500.0]]
    payload["entities"][0].pop("deployment")
    payload["world"]["zones"] = []
    payload["world"]["boundaries"] = []
    first = _compile(payload)
    second = _compile(copy.deepcopy(payload))
    assert first.entities[0].initial_state.position_m == pytest.approx(
        (22.2639, 0.0, 40.0), abs=0.05
    )
    assert first.resolved_hash == second.resolved_hash


@pytest.mark.parametrize(
    ("positions", "code"),
    (
        (
            (
                (0.0, 0.0),
                (10.0, 0.0),
                (10.0, 10.0),
                (0.0004, 0.0004),
                (0.0, 10.0),
            ),
            "scenario.zone_geometry_invalid",
        ),
        (
            ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (5.0, 0.0), (0.0, 10.0)),
            "scenario.zone_self_intersection",
        ),
        (
            ((0.0, 0.0), (10.0, 0.0), (4.0, 0.0), (4.0, 10.0), (0.0, 10.0)),
            "scenario.zone_self_intersection",
        ),
    ),
)
def test_polygon_rejects_quantized_duplicates_contacts_and_collinear_retrace(
    positions: tuple[tuple[float, float], ...], code: str
) -> None:
    payload = _scenario()
    payload["entities"][0].pop("deployment")
    payload["world"]["boundaries"] = []
    payload["world"]["zones"] = [payload["world"]["zones"][0]]
    payload["world"]["zones"][0]["geometry"]["positions"] = [
        _position("local_m", list(point)) for point in positions
    ]
    _assert_error(payload, code=code, path_contains=("world", "zones"))


def test_optional_repeated_closing_vertex_is_normalized_consistently() -> None:
    open_payload = _scenario()
    open_payload["entities"][0].pop("deployment")
    open_payload["world"]["boundaries"] = []
    open_payload["world"]["zones"] = [open_payload["world"]["zones"][0]]
    closed_payload = copy.deepcopy(open_payload)
    positions = closed_payload["world"]["zones"][0]["geometry"]["positions"]
    positions.append(copy.deepcopy(positions[0]))
    open_resolved = _compile(open_payload)
    closed_resolved = _compile(closed_payload)
    assert len(closed_resolved.world.zones[0].geometry.positions_m) == 4
    assert closed_resolved.resolved_hash == open_resolved.resolved_hash


def test_negative_zero_is_canonicalized_in_resolved_json_and_hash() -> None:
    negative = _scenario(_position("local_m", [-0.0, 30.0, 40.0]))
    positive = _scenario(_position("local_m", [0.0, 30.0, 40.0]))
    for payload in (negative, positive):
        payload["entities"][0].pop("deployment")
    resolved = _compile(negative)
    assert resolved.entities[0].initial_state.position_m[0] == 0.0
    assert "-0.0" not in resolved.to_json()
    assert resolved.resolved_hash == _compile(positive).resolved_hash

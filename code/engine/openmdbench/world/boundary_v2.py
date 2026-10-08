"""Generic continuous boundary and collision evaluation for runtime worlds."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType
from typing import Literal, Protocol, Self, cast

from openmdbench.schemas.domain_v2 import DamageIntentV2
from openmdbench.world.geography_v2 import GeographyServiceV2, Vector3V2

BoundaryPolicyNameV2 = Literal[
    "reject",
    "constrain",
    "stop",
    "reflect",
    "effect",
    "deactivate",
    "mission_event",
]
BoundaryKindV2 = Literal[
    "world_exit",
    "altitude_max",
    "depth_max",
    "allowed_zone",
    "excluded_zone",
    "obstacle",
]

_POLICIES = frozenset(
    ("reject", "constrain", "stop", "reflect", "effect", "deactivate", "mission_event")
)
_COLLISION_SHAPES = frozenset(("sphere", "capsule", "aabb", "obb", "polygon_footprint"))


class BoundaryErrorV2(ValueError):
    """Stable spatial-contract failure with machine-readable evidence."""

    def __init__(
        self,
        *,
        code: str,
        path: Sequence[str],
        value: object,
        reason: str,
        suggestion: str,
    ) -> None:
        self.code = code
        self.path = tuple(path)
        self.value = value
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"{code} at {'/'.join(self.path)}: {reason}; suggestion: {suggestion}")


def _boundary_error(
    code: str,
    path: Sequence[str],
    value: object,
    reason: str,
    suggestion: str,
) -> BoundaryErrorV2:
    return BoundaryErrorV2(
        code=code,
        path=path,
        value=value,
        reason=reason,
        suggestion=suggestion,
    )


def _finite_number(value: object, *, name: str, positive: bool = False) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or (positive and float(value) <= 0.0)
    ):
        qualifier = "positive finite" if positive else "finite"
        raise ValueError(f"{name} must be a {qualifier} number")
    return float(value)


def _vector3(value: object, *, name: str) -> Vector3V2:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) != 3
    ):
        raise ValueError(f"{name} must contain exactly three axes")
    return cast(
        Vector3V2,
        tuple(_finite_number(item, name=f"{name}[{index}]") for index, item in enumerate(value)),
    )


def _unit_vector(value: object, *, name: str) -> Vector3V2:
    vector = _vector3(value, name=name)
    length = math.sqrt(sum(axis * axis for axis in vector))
    if length <= 1e-15:
        raise ValueError(f"{name} must have nonzero magnitude")
    return cast(Vector3V2, tuple(axis / length for axis in vector))


def _point2(value: object, *, name: str) -> tuple[float, float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) < 2
    ):
        raise ValueError(f"{name} must contain at least two axes")
    return (
        _finite_number(value[0], name=f"{name}[0]"),
        _finite_number(value[1], name=f"{name}[1]"),
    )


def _identifier(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


@dataclass(frozen=True, slots=True)
class CollisionShapeV2:
    exact_ref: str
    content_hash: str
    shape: Literal["sphere", "capsule", "aabb", "obb", "polygon_footprint"]
    radius_m: float = 0.0
    half_length_m: float = 0.0
    axis: Literal["x", "y", "z"] = "x"
    half_extents_m: Vector3V2 = (0.0, 0.0, 0.0)
    yaw_degrees: float = 0.0
    vertices_m: tuple[tuple[float, float], ...] = ()
    vertical_interval_m: tuple[float, float] = (0.0, 0.0)
    convex_parts: tuple[tuple[tuple[float, float], ...], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "exact_ref", _identifier(self.exact_ref, name="exact_ref"))
        object.__setattr__(
            self, "content_hash", _identifier(self.content_hash, name="content_hash")
        )
        if self.shape not in _COLLISION_SHAPES:
            raise _boundary_error(
                "boundary.collision_shape_unsupported",
                ("shape",),
                self.shape,
                "collision shape algorithm is not supported",
                "use sphere, capsule, aabb, obb, or polygon_footprint",
            )
        radius = _finite_number(self.radius_m, name="radius_m")
        half_length = _finite_number(self.half_length_m, name="half_length_m")
        extents = _vector3(self.half_extents_m, name="half_extents_m")
        yaw = _finite_number(self.yaw_degrees, name="yaw_degrees")
        vertical = (
            _finite_number(self.vertical_interval_m[0], name="vertical_interval_m[0]"),
            _finite_number(self.vertical_interval_m[1], name="vertical_interval_m[1]"),
        )
        if radius < 0.0 or half_length < 0.0 or any(item < 0.0 for item in extents):
            raise ValueError("collision shape dimensions cannot be negative")
        if vertical[0] > vertical[1]:
            raise ValueError("collision shape vertical interval must be ordered")
        if self.axis not in {"x", "y", "z"}:
            raise ValueError("capsule axis must be x, y, or z")
        vertices = tuple(_point2(item, name="vertices_m") for item in self.vertices_m)
        if self.shape == "sphere" and radius <= 0.0:
            raise ValueError("sphere radius must be positive")
        if self.shape == "capsule" and (radius <= 0.0 or half_length <= 0.0):
            raise ValueError("capsule radius and half length must be positive")
        if self.shape in {"aabb", "obb"} and any(item <= 0.0 for item in extents):
            raise ValueError("box half extents must be positive")
        if self.shape == "polygon_footprint" and len(vertices) < 3:
            raise ValueError("polygon footprint must contain at least three vertices")
        object.__setattr__(self, "radius_m", radius)
        object.__setattr__(self, "half_length_m", half_length)
        object.__setattr__(self, "half_extents_m", extents)
        object.__setattr__(self, "yaw_degrees", yaw)
        object.__setattr__(self, "vertices_m", vertices)
        object.__setattr__(self, "vertical_interval_m", vertical)
        if self.shape == "polygon_footprint":
            object.__setattr__(self, "convex_parts", (vertices,))

    @classmethod
    def from_profile(
        cls,
        *,
        exact_ref: str,
        content_hash: str,
        shape: str,
        parameters: Mapping[str, object],
    ) -> Self:
        if shape not in _COLLISION_SHAPES:
            raise _boundary_error(
                "boundary.collision_shape_unsupported",
                ("shape",),
                shape,
                "collision shape algorithm is not supported",
                "use sphere, capsule, aabb, obb, or polygon_footprint",
            )
        if not isinstance(parameters, Mapping):
            raise ValueError("collision shape parameters must be a mapping")
        try:
            if shape == "sphere":
                radius = _finite_number(parameters["radius_m"], name="radius_m", positive=True)
                return cls(
                    exact_ref,
                    content_hash,
                    "sphere",
                    radius_m=radius,
                    vertical_interval_m=(-radius, radius),
                )
            if shape == "capsule":
                radius = _finite_number(parameters["radius_m"], name="radius_m", positive=True)
                half_length = _finite_number(
                    parameters["half_length_m"], name="half_length_m", positive=True
                )
                axis = parameters.get("axis", "x")
                if axis not in {"x", "y", "z"}:
                    raise ValueError("capsule axis must be x, y, or z")
                vertical_extent = radius + (half_length if axis == "z" else 0.0)
                return cls(
                    exact_ref,
                    content_hash,
                    "capsule",
                    radius_m=(radius if axis == "z" else radius + half_length),
                    half_length_m=half_length,
                    axis=cast(Literal["x", "y", "z"], axis),
                    vertical_interval_m=(-vertical_extent, vertical_extent),
                )
            if shape in {"aabb", "obb"}:
                extents = _vector3(parameters["half_extents_m"], name="half_extents_m")
                if any(item <= 0.0 for item in extents):
                    raise ValueError("box half extents must be positive")
                yaw = (
                    0.0
                    if shape == "aabb"
                    else _finite_number(parameters.get("yaw_degrees", 0.0), name="yaw_degrees")
                )
                return cls(
                    exact_ref,
                    content_hash,
                    cast(Literal["aabb", "obb"], shape),
                    radius_m=math.hypot(extents[0], extents[1]),
                    half_extents_m=extents,
                    yaw_degrees=yaw,
                    vertical_interval_m=(-extents[2], extents[2]),
                )
            vertices = tuple(
                _point2(item, name="vertices_m")
                for item in cast(Sequence[object], parameters["vertices_m"])
            )
            vertical_value = parameters.get("vertical_interval_m", (0.0, 0.0))
            if not isinstance(vertical_value, Sequence) or len(vertical_value) != 2:
                raise ValueError("vertical_interval_m must contain two axes")
            vertical = (
                _finite_number(vertical_value[0], name="vertical_interval_m[0]"),
                _finite_number(vertical_value[1], name="vertical_interval_m[1]"),
            )
            if not _polygon_is_convex(vertices):
                raise _boundary_error(
                    "boundary.concave_polygon_unsupported",
                    ("parameters", "vertices_m"),
                    vertices,
                    "concave collision footprint has no trusted decomposition evidence",
                    "provide a convex footprint or compile trusted convex parts",
                )
            return cls(
                exact_ref,
                content_hash,
                "polygon_footprint",
                radius_m=max(math.hypot(*item) for item in vertices),
                vertices_m=vertices,
                vertical_interval_m=vertical,
            )
        except BoundaryErrorV2:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise _boundary_error(
                "boundary.collision_shape_invalid",
                ("parameters",),
                type(error).__name__,
                "collision shape parameters are incomplete or non-finite",
                "provide the complete finite parameter schema for the selected shape",
            ) from error


def _polygon_is_convex(vertices: Sequence[tuple[float, float]]) -> bool:
    if len(vertices) < 3:
        return False
    signs: set[bool] = set()
    for index in range(len(vertices)):
        first = vertices[index]
        second = vertices[(index + 1) % len(vertices)]
        third = vertices[(index + 2) % len(vertices)]
        cross = (second[0] - first[0]) * (third[1] - second[1]) - (second[1] - first[1]) * (
            third[0] - second[0]
        )
        if abs(cross) > 1e-12:
            signs.add(cross > 0.0)
    return len(signs) == 1


@dataclass(frozen=True, slots=True)
class ShapeSweepHitV2:
    time_fraction: float

    def __post_init__(self) -> None:
        fraction = _finite_number(self.time_fraction, name="time_fraction")
        if not 0.0 <= fraction <= 1.0:
            raise ValueError("time_fraction must be within [0, 1]")
        object.__setattr__(self, "time_fraction", fraction)


@dataclass(frozen=True, slots=True)
class ShapeNarrowphaseOracleV2:
    tolerance_m: float = 0.0

    def __post_init__(self) -> None:
        tolerance = _finite_number(self.tolerance_m, name="tolerance_m")
        if tolerance < 0.0:
            raise ValueError("tolerance_m cannot be negative")
        object.__setattr__(self, "tolerance_m", tolerance)

    @staticmethod
    def _capsule_segment(
        shape: CollisionShapeV2, center: Vector3V2
    ) -> tuple[Vector3V2, Vector3V2, float]:
        physical_radius = (
            shape.radius_m if shape.axis == "z" else shape.radius_m - shape.half_length_m
        )
        axis_index = {"x": 0, "y": 1, "z": 2}[shape.axis]
        first = list(center)
        second = list(center)
        first[axis_index] -= shape.half_length_m
        second[axis_index] += shape.half_length_m
        return cast(Vector3V2, tuple(first)), cast(Vector3V2, tuple(second)), physical_radius

    @staticmethod
    def _point_segment_distance(point: Vector3V2, first: Vector3V2, second: Vector3V2) -> float:
        delta = tuple(second[index] - first[index] for index in range(3))
        length = sum(item * item for item in delta)
        fraction = (
            0.0
            if length == 0.0
            else min(
                1.0,
                max(
                    0.0,
                    sum((point[index] - first[index]) * delta[index] for index in range(3))
                    / length,
                ),
            )
        )
        return math.sqrt(
            sum((point[index] - first[index] - fraction * delta[index]) ** 2 for index in range(3))
        )

    def overlap(
        self,
        first: CollisionShapeV2,
        first_position_m: Sequence[float],
        second: CollisionShapeV2,
        second_position_m: Sequence[float],
        *,
        vertical_intervals: bool = True,
    ) -> bool:
        first_position = _vector3(first_position_m, name="first_position_m")
        second_position = _vector3(second_position_m, name="second_position_m")
        if vertical_intervals and (
            first_position[2] + first.vertical_interval_m[1]
            < second_position[2] + second.vertical_interval_m[0] - self.tolerance_m
            or second_position[2] + second.vertical_interval_m[1]
            < first_position[2] + first.vertical_interval_m[0] - self.tolerance_m
        ):
            return False
        if first.shape == second.shape == "sphere":
            return (
                math.sqrt(
                    sum((first_position[index] - second_position[index]) ** 2 for index in range(3))
                )
                <= first.radius_m + second.radius_m + self.tolerance_m
            )
        if first.shape == "capsule" and second.shape == "sphere":
            start, end, radius = self._capsule_segment(first, first_position)
            return self._point_segment_distance(second_position, start, end) <= (
                radius + second.radius_m + self.tolerance_m
            )
        if second.shape == "capsule" and first.shape == "sphere":
            return self.overlap(second, second_position, first, first_position)
        first_polygon = _shape_polygon(first)
        second_polygon = _shape_polygon(second)
        axes: list[tuple[float, float]] = []
        for polygon in (first_polygon, second_polygon):
            for index, point in enumerate(polygon):
                following = polygon[(index + 1) % len(polygon)]
                dx = following[0] - point[0]
                dy = following[1] - point[1]
                length = math.hypot(dx, dy)
                if length > 1e-15:
                    axes.append((-dy / length, dx / length))
        for axis in axes:
            first_projection = tuple(
                (point[0] + first_position[0]) * axis[0] + (point[1] + first_position[1]) * axis[1]
                for point in first_polygon
            )
            second_projection = tuple(
                (point[0] + second_position[0]) * axis[0]
                + (point[1] + second_position[1]) * axis[1]
                for point in second_polygon
            )
            if (
                max(first_projection) < min(second_projection) - self.tolerance_m
                or max(second_projection) < min(first_projection) - self.tolerance_m
            ):
                return False
        return True

    def sweep(
        self,
        shape_a: CollisionShapeV2,
        *,
        start_a: Sequence[float],
        end_a: Sequence[float],
        shape_b: CollisionShapeV2,
        start_b: Sequence[float],
        end_b: Sequence[float],
    ) -> ShapeSweepHitV2 | None:
        """Return the exact continuous 3D sphere contact fraction."""

        if shape_a.shape != "sphere" or shape_b.shape != "sphere":
            raise _boundary_error(
                "boundary.shape_sweep_unsupported",
                ("shape_sweep",),
                (shape_a.shape, shape_b.shape),
                "the public exact sweep oracle currently supports sphere pairs",
                "use sphere shapes or the BoundarySystem controlled shape pipeline",
            )
        first_start = _vector3(start_a, name="start_a")
        first_end = _vector3(end_a, name="end_a")
        second_start = _vector3(start_b, name="start_b")
        second_end = _vector3(end_b, name="end_b")
        fraction = _sphere_sweep_fraction(
            cast(
                Vector3V2,
                tuple(first_start[index] - second_start[index] for index in range(3)),
            ),
            cast(
                Vector3V2,
                tuple(first_end[index] - second_end[index] for index in range(3)),
            ),
            shape_a.radius_m + shape_b.radius_m,
            self.tolerance_m,
        )
        return None if fraction is None else ShapeSweepHitV2(time_fraction=fraction)

    def xy_z_intervals_overlap(
        self,
        *,
        xy_interval: tuple[float, float],
        z_interval: tuple[float, float],
    ) -> bool:
        """Require simultaneous overlap of horizontal and vertical sweep intervals."""

        xy_start, xy_end = (
            _finite_number(xy_interval[0], name="xy_interval"),
            _finite_number(xy_interval[1], name="xy_interval"),
        )
        z_start, z_end = (
            _finite_number(z_interval[0], name="z_interval"),
            _finite_number(z_interval[1], name="z_interval"),
        )
        if xy_start > xy_end or z_start > z_end:
            raise ValueError("sweep intervals must be ordered")
        return max(xy_start, z_start) <= min(xy_end, z_end) + self.tolerance_m


class _CompositionShapeLike(Protocol):
    collision_shape_ref: str | None


class _BindingShapeLike(Protocol):
    exact_ref: str
    content_hash: str
    normalized_content: Mapping[str, object]


class _ResolvedEntityShapeLike(Protocol):
    id: str
    domain: str
    tags: Sequence[str]
    composition: _CompositionShapeLike
    resource_bindings: Mapping[str, Sequence[_BindingShapeLike]]
    boundary_deployment: _BoundaryDeploymentLike | None


class _BoundaryDeploymentLike(Protocol):
    allowed_zone_ids: tuple[str, ...]
    excluded_zone_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BoundaryEntityV2:
    entity_id: str
    domain: str
    radius_m: float
    tags: tuple[str, ...] = ()
    collision_shape_ref: str | None = None
    shape: CollisionShapeV2 | None = None
    allowed_zone_ids: tuple[str, ...] = ()
    excluded_zone_ids: tuple[str, ...] = ()
    mass_kg: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _identifier(self.entity_id, name="entity_id"))
        object.__setattr__(self, "domain", _identifier(self.domain, name="domain"))
        radius = _finite_number(self.radius_m, name="radius_m")
        if radius < 0.0:
            raise ValueError("radius_m cannot be negative")
        if any(not isinstance(tag, str) or not tag for tag in self.tags):
            raise ValueError("tags must contain nonempty strings")
        if len(self.tags) != len(set(self.tags)):
            raise ValueError("tags must be unique")
        object.__setattr__(self, "radius_m", radius)
        mass = _finite_number(self.mass_kg, name="mass_kg")
        if mass < 0.0:
            raise ValueError("mass_kg cannot be negative")
        object.__setattr__(self, "mass_kg", mass)
        object.__setattr__(self, "tags", tuple(self.tags))
        allowed = tuple(
            _identifier(item, name="allowed_zone_ids") for item in self.allowed_zone_ids
        )
        excluded = tuple(
            _identifier(item, name="excluded_zone_ids") for item in self.excluded_zone_ids
        )
        if (
            len(allowed) != len(set(allowed))
            or len(excluded) != len(set(excluded))
            or set(allowed) & set(excluded)
        ):
            raise ValueError("entity spatial-zone IDs must be unique and disjoint")
        object.__setattr__(self, "allowed_zone_ids", tuple(sorted(allowed)))
        object.__setattr__(self, "excluded_zone_ids", tuple(sorted(excluded)))
        if self.shape is None:
            shape = CollisionShapeV2(
                exact_ref=self.collision_shape_ref or "builtin.sphere@2.0.0",
                content_hash="runtime-radius",
                shape="sphere",
                radius_m=radius,
            )
            object.__setattr__(self, "shape", shape)
            object.__setattr__(self, "collision_shape_ref", shape.exact_ref)
        else:
            if self.collision_shape_ref != self.shape.exact_ref:
                raise ValueError("collision shape identity mismatch")
            if abs(radius - self.shape.radius_m) > 1e-12:
                raise ValueError("collision radius does not match shape evidence")

    @classmethod
    def from_resolved(
        cls,
        entity: object,
        *,
        resolved_scenario: _ResolvedScenario | None = None,
        expected_resolved_hash: str | None = None,
    ) -> Self:
        if resolved_scenario is None or expected_resolved_hash is None:
            raise _boundary_error(
                "boundary.resolved_anchor_required",
                ("resolved_scenario", "expected_resolved_hash"),
                None,
                "entity materialization requires scenario and independent hash anchors",
                "pass the validated ResolvedScenarioV2 and its independently retained hash",
            )
        try:
            if resolved_scenario.resolved_hash != expected_resolved_hash:
                raise ValueError("resolved hash anchor mismatch")
            resolved_scenario.validate_integrity()
        except (AttributeError, TypeError, ValueError) as error:
            raise _boundary_error(
                "boundary.resolved_integrity_invalid",
                ("resolved_scenario",),
                type(error).__name__,
                "resolved scenario or independent hash anchor failed integrity validation",
                "use the original validated artifact and independently retained resolved hash",
            ) from error
        try:
            candidate = cast(_ResolvedEntityShapeLike, entity)
            composition = candidate.composition
            exact_ref = composition.collision_shape_ref
            groups = candidate.resource_bindings
            bindings = tuple(groups.get("collision_shapes", ()))
            matches = tuple(item for item in bindings if item.exact_ref == exact_ref)
            if not isinstance(exact_ref, str) or len(matches) != 1:
                raise _boundary_error(
                    "boundary.collision_shape_unsupported",
                    ("entity", candidate.id, "collision_shape_ref"),
                    exact_ref,
                    "resolved collision-shape root has no exact embedded binding",
                    "compile an entity with one trusted exact collision_shapes binding",
                )
            binding = matches[0]
            content = binding.normalized_content
            shape_name = content.get("shape")
            shape = CollisionShapeV2.from_profile(
                exact_ref=exact_ref,
                content_hash=str(binding.content_hash),
                shape=cast(str, shape_name),
                parameters=content,
            )
            return cls(
                entity_id=candidate.id,
                domain=candidate.domain,
                radius_m=shape.radius_m,
                tags=tuple(candidate.tags),
                collision_shape_ref=exact_ref,
                shape=shape,
                allowed_zone_ids=(
                    ()
                    if candidate.boundary_deployment is None
                    else candidate.boundary_deployment.allowed_zone_ids
                ),
                excluded_zone_ids=(
                    ()
                    if candidate.boundary_deployment is None
                    else candidate.boundary_deployment.excluded_zone_ids
                ),
            )
        except BoundaryErrorV2:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise _boundary_error(
                "boundary.collision_shape_unsupported",
                ("entity", "collision_shape_ref"),
                type(error).__name__,
                "resolved collision shape evidence is incomplete or invalid",
                "use an integrity-validated ResolvedEntityV2",
            ) from error


@dataclass(frozen=True, slots=True)
class MotionSegmentV2:
    start_m: Vector3V2
    end_m: Vector3V2
    dt_seconds: float
    velocity_mps: Vector3V2 | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_m", _vector3(self.start_m, name="start_m"))
        object.__setattr__(self, "end_m", _vector3(self.end_m, name="end_m"))
        object.__setattr__(
            self,
            "dt_seconds",
            _finite_number(self.dt_seconds, name="dt_seconds", positive=True),
        )
        velocity = (
            cast(
                Vector3V2,
                tuple(
                    (self.end_m[index] - self.start_m[index]) / self.dt_seconds
                    for index in range(3)
                ),
            )
            if self.velocity_mps is None
            else _vector3(self.velocity_mps, name="velocity_mps")
        )
        object.__setattr__(self, "velocity_mps", velocity)


@dataclass(frozen=True, slots=True)
class BoundaryPolicyV2:
    policy: BoundaryPolicyNameV2
    effect_ref: str = "effects.boundary-collision@2.0.0"
    priority: int = 0

    def __post_init__(self) -> None:
        if self.policy not in _POLICIES:
            raise ValueError("boundary policy is not controlled")
        object.__setattr__(self, "effect_ref", _identifier(self.effect_ref, name="effect_ref"))
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")


@dataclass(frozen=True, slots=True)
class StaticObstacleV2:
    obstacle_id: str
    geometry_type: Literal["polygon", "circle"]
    positions_m: tuple[tuple[float, float], ...] = ()
    center_m: tuple[float, float] | None = None
    radius_m: float | None = None
    domains: tuple[str, ...] = ()
    minimum_z_m: float | None = None
    maximum_z_m: float | None = None
    vertical_interval_m: tuple[float, float] | None = None
    priority: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "obstacle_id", _identifier(self.obstacle_id, name="obstacle_id"))
        if self.geometry_type not in {"polygon", "circle"}:
            raise ValueError("unsupported obstacle geometry")
        if self.geometry_type == "polygon":
            points = tuple(
                _point2(point, name=f"positions_m[{index}]")
                for index, point in enumerate(self.positions_m)
            )
            if len(points) < 3:
                raise ValueError("polygon obstacle requires at least three points")
            _validate_polygon(points, obstacle_id=self.obstacle_id)
            object.__setattr__(self, "positions_m", points)
            if self.center_m is not None or self.radius_m is not None:
                raise ValueError("polygon obstacle cannot define circle fields")
        else:
            if self.center_m is None or self.radius_m is None:
                raise ValueError("circle obstacle requires center and radius")
            object.__setattr__(self, "center_m", _point2(self.center_m, name="center_m"))
            radius = _finite_number(self.radius_m, name="radius_m", positive=True)
            object.__setattr__(self, "radius_m", radius)
            if self.positions_m:
                raise ValueError("circle obstacle cannot define polygon positions")
        if any(not isinstance(domain, str) or not domain for domain in self.domains):
            raise ValueError("domains must contain nonempty strings")
        if len(self.domains) != len(set(self.domains)):
            raise ValueError("domains must be unique")
        object.__setattr__(self, "domains", tuple(self.domains))
        if self.vertical_interval_m is not None:
            if len(self.vertical_interval_m) != 2:
                raise ValueError("vertical_interval_m must contain two bounds")
            interval = (
                _finite_number(self.vertical_interval_m[0], name="vertical_interval_m[0]"),
                _finite_number(self.vertical_interval_m[1], name="vertical_interval_m[1]"),
            )
            if interval[0] > interval[1]:
                raise ValueError("obstacle vertical interval is reversed")
            if self.minimum_z_m is not None or self.maximum_z_m is not None:
                raise ValueError("use one obstacle vertical interval representation")
            object.__setattr__(self, "vertical_interval_m", interval)
            object.__setattr__(self, "minimum_z_m", interval[0])
            object.__setattr__(self, "maximum_z_m", interval[1])
        if self.minimum_z_m is not None:
            object.__setattr__(
                self,
                "minimum_z_m",
                _finite_number(self.minimum_z_m, name="minimum_z_m"),
            )
        if self.maximum_z_m is not None:
            object.__setattr__(
                self,
                "maximum_z_m",
                _finite_number(self.maximum_z_m, name="maximum_z_m"),
            )
        if (
            self.minimum_z_m is not None
            and self.maximum_z_m is not None
            and self.minimum_z_m > self.maximum_z_m
        ):
            raise ValueError("obstacle vertical bounds are reversed")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")

    @classmethod
    def polygon(
        cls,
        obstacle_id: str,
        positions_m: Sequence[Sequence[float]],
        *,
        domains: Sequence[str] = (),
        minimum_z_m: float | None = None,
        maximum_z_m: float | None = None,
        holes: Sequence[Sequence[Sequence[float]]] = (),
        vertical_interval_m: tuple[float, float] | None = None,
        priority: int = 0,
    ) -> Self:
        if holes:
            raise _boundary_error(
                "boundary.polygon_holes_unsupported",
                ("obstacles", obstacle_id, "holes"),
                holes,
                "polygon holes are not supported by this collision kernel",
                "decompose the obstacle into validated simple polygons",
            )
        return cls(
            obstacle_id=obstacle_id,
            geometry_type="polygon",
            positions_m=tuple(
                _point2(point, name=f"positions_m[{index}]")
                for index, point in enumerate(positions_m)
            ),
            domains=tuple(domains),
            minimum_z_m=minimum_z_m,
            maximum_z_m=maximum_z_m,
            vertical_interval_m=vertical_interval_m,
            priority=priority,
        )

    @classmethod
    def circle(
        cls,
        obstacle_id: str,
        center_m: Sequence[float],
        radius_m: float,
        *,
        domains: Sequence[str] = (),
        minimum_z_m: float | None = None,
        maximum_z_m: float | None = None,
        priority: int = 0,
        vertical_interval_m: tuple[float, float] | None = None,
    ) -> Self:
        return cls(
            obstacle_id=obstacle_id,
            geometry_type="circle",
            center_m=_point2(center_m, name="center_m"),
            radius_m=radius_m,
            domains=tuple(domains),
            minimum_z_m=minimum_z_m,
            maximum_z_m=maximum_z_m,
            vertical_interval_m=vertical_interval_m,
            priority=priority,
        )

    def contains(
        self,
        point_m: Sequence[float],
        *,
        point_on_edge: Literal["inside", "outside"] = "inside",
        tolerance_m: float = 0.0,
    ) -> bool:
        point = _point2(point_m, name="point_m")
        if point_on_edge not in {"inside", "outside"}:
            raise ValueError("point_on_edge must be inside or outside")
        tolerance = _finite_number(tolerance_m, name="tolerance_m")
        if tolerance < 0.0:
            raise ValueError("tolerance_m cannot be negative")
        if self.geometry_type == "circle":
            if self.center_m is None or self.radius_m is None:
                raise ValueError("circle zone is missing center or radius")
            distance = math.hypot(point[0] - self.center_m[0], point[1] - self.center_m[1])
            if abs(distance - self.radius_m) <= tolerance:
                return point_on_edge == "inside"
            return distance < self.radius_m
        return _point_in_polygon(
            point,
            self.positions_m,
            tolerance=tolerance,
            edge_inside=point_on_edge == "inside",
        )


@dataclass(frozen=True, slots=True)
class BoundaryEventV2:
    event_id: str
    tick: int
    entity_id: str
    kind: BoundaryKindV2
    boundary_id: str
    time_fraction: float
    position_m: Vector3V2
    normal: Vector3V2 = (1.0, 0.0, 0.0)
    priority: int = 0
    absolute_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _identifier(self.event_id, name="event_id"))
        object.__setattr__(self, "entity_id", _identifier(self.entity_id, name="entity_id"))
        object.__setattr__(self, "boundary_id", _identifier(self.boundary_id, name="boundary_id"))
        if not isinstance(self.tick, int) or isinstance(self.tick, bool) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        fraction = _finite_number(self.time_fraction, name="time_fraction")
        if not 0.0 <= fraction <= 1.0:
            raise ValueError("time_fraction must be within [0, 1]")
        object.__setattr__(self, "time_fraction", fraction)
        object.__setattr__(self, "position_m", _vector3(self.position_m, name="position_m"))
        object.__setattr__(self, "normal", _unit_vector(self.normal, name="normal"))
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        absolute = _finite_number(self.absolute_time_seconds, name="absolute_time_seconds")
        if absolute < 0.0:
            raise ValueError("absolute_time_seconds cannot be negative")
        object.__setattr__(self, "absolute_time_seconds", absolute)


@dataclass(frozen=True, slots=True)
class CollisionEventV2:
    event_id: str
    tick: int
    entity_id: str
    obstacle_id: str | None
    other_entity_id: str | None
    time_fraction: float
    position_m: Vector3V2
    normal: Vector3V2 = (1.0, 0.0, 0.0)
    entity_a_id: str = ""
    entity_b_id: str = ""
    absolute_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _identifier(self.event_id, name="event_id"))
        object.__setattr__(self, "entity_id", _identifier(self.entity_id, name="entity_id"))
        if self.obstacle_id is not None:
            _identifier(self.obstacle_id, name="obstacle_id")
        if self.other_entity_id is not None:
            _identifier(self.other_entity_id, name="other_entity_id")
        if self.obstacle_id is None and self.other_entity_id is None:
            raise ValueError("collision requires obstacle or other entity identity")
        if not isinstance(self.tick, int) or isinstance(self.tick, bool) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        fraction = _finite_number(self.time_fraction, name="time_fraction")
        if not 0.0 <= fraction <= 1.0:
            raise ValueError("time_fraction must be within [0, 1]")
        object.__setattr__(self, "time_fraction", fraction)
        object.__setattr__(self, "position_m", _vector3(self.position_m, name="position_m"))
        object.__setattr__(self, "normal", _unit_vector(self.normal, name="normal"))
        object.__setattr__(
            self,
            "entity_a_id",
            self.entity_id
            if not self.entity_a_id
            else _identifier(self.entity_a_id, name="entity_a_id"),
        )
        fallback_b = self.other_entity_id or self.obstacle_id
        object.__setattr__(
            self,
            "entity_b_id",
            cast(str, fallback_b)
            if not self.entity_b_id
            else _identifier(self.entity_b_id, name="entity_b_id"),
        )
        absolute = _finite_number(self.absolute_time_seconds, name="absolute_time_seconds")
        if absolute < 0.0:
            raise ValueError("absolute_time_seconds cannot be negative")
        object.__setattr__(self, "absolute_time_seconds", absolute)


@dataclass(frozen=True, slots=True)
class BoundaryPolicyActionV2:
    action_id: str
    tick: int
    entity_id: str
    policy: BoundaryPolicyNameV2
    cause_event_id: str
    candidate_end_m: Vector3V2
    resolved_end_m: Vector3V2
    boundary_normal: Vector3V2 = (1.0, 0.0, 0.0)
    resolved_velocity_mps: Vector3V2 = (0.0, 0.0, 0.0)
    contact_position_m: Vector3V2 = (0.0, 0.0, 0.0)

    @property
    def normal(self) -> Vector3V2:
        return self.boundary_normal


@dataclass(frozen=True, slots=True)
class DeactivateIntentV2:
    intent_id: str
    tick: int
    entity_id: str
    cause_event_id: str


@dataclass(frozen=True, slots=True)
class MissionEventIntentV2:
    intent_id: str
    tick: int
    entity_id: str
    cause_event_id: str
    event_type: Literal["boundary_violation"] = "boundary_violation"


def _plain(value: object) -> object:
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in sorted(value.items())}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(item) for item in value]
    return value


class _ImpactDamagePolicyLike(Protocol):
    @property
    def effect_binding(self) -> _BindingShapeLike: ...

    @property
    def damage_binding(self) -> _BindingShapeLike: ...

    @property
    def magnitude_model(self) -> str: ...

    @property
    def magnitude_parameters(self) -> Mapping[str, float]: ...

    @property
    def output_unit(self) -> str: ...


class ImpactMagnitudeModelV2:
    """Canonical dimensionless impact-magnitude calculations."""

    @staticmethod
    def evaluate(
        *,
        model: str,
        parameters: Mapping[str, float],
        relative_velocity_mps: Sequence[float],
        source_mass_kg: float,
        target_mass_kg: float,
        output_unit: str,
    ) -> float:
        velocity = _vector3(relative_velocity_mps, name="relative_velocity_mps")
        source_mass = _finite_number(source_mass_kg, name="source_mass_kg")
        target_mass = _finite_number(target_mass_kg, name="target_mass_kg")
        if source_mass < 0.0 or target_mass < 0.0 or output_unit != "1":
            raise ValueError("impact magnitude requires nonnegative kg masses and unit 1 output")
        expected_parameter = {
            "constant": "value",
            "scaled_relative_speed": "scale",
            "relative_kinetic_energy": "scale",
        }.get(model)
        if expected_parameter is None or set(parameters) != {expected_parameter}:
            raise ValueError("impact magnitude model or parameters are invalid")
        parameter = _finite_number(parameters[expected_parameter], name=expected_parameter)
        if parameter < 0.0:
            raise ValueError("impact magnitude parameter cannot be negative")
        speed_squared = math.fsum(axis * axis for axis in velocity)
        if model == "constant":
            magnitude = parameter
        elif model == "scaled_relative_speed":
            magnitude = parameter * math.sqrt(speed_squared)
        else:
            if source_mass <= 0.0:
                raise ValueError("relative kinetic energy requires positive source mass evidence")
            magnitude = parameter * 0.5 * source_mass * speed_squared
        if not math.isfinite(magnitude) or magnitude < 0.0:
            raise ValueError("impact magnitude result is not finite and nonnegative")
        return magnitude


@dataclass(frozen=True, slots=True)
class ImpactDamageEvidenceV2:
    effect_ref: str
    damage_model_ref: str
    magnitude_model: str
    magnitude_parameters: Mapping[str, float]
    output_unit: str
    pre_impact_relative_velocity_mps: Vector3V2
    source_mass_kg: float
    target_mass_kg: float
    time_fraction: float
    magnitude: float
    evidence_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_ref", _identifier(self.effect_ref, name="effect_ref"))
        object.__setattr__(
            self,
            "damage_model_ref",
            _identifier(self.damage_model_ref, name="damage_model_ref"),
        )
        object.__setattr__(
            self,
            "magnitude_parameters",
            MappingProxyType(dict(sorted(self.magnitude_parameters.items()))),
        )
        velocity = _vector3(
            self.pre_impact_relative_velocity_mps,
            name="pre_impact_relative_velocity_mps",
        )
        object.__setattr__(self, "pre_impact_relative_velocity_mps", velocity)
        for field_name in ("source_mass_kg", "target_mass_kg", "magnitude"):
            value = _finite_number(getattr(self, field_name), name=field_name)
            if value < 0.0:
                raise ValueError(f"{field_name} cannot be negative")
            object.__setattr__(self, field_name, value)
        fraction = _finite_number(self.time_fraction, name="time_fraction")
        if not 0.0 <= fraction <= 1.0:
            raise ValueError("impact time_fraction must be within [0, 1]")
        object.__setattr__(self, "time_fraction", fraction)
        if re.fullmatch(r"sha256:[0-9a-f]{64}", self.evidence_hash) is None:
            raise ValueError("impact evidence hash must be canonical sha256")
        expected_magnitude = ImpactMagnitudeModelV2.evaluate(
            model=self.magnitude_model,
            parameters=self.magnitude_parameters,
            relative_velocity_mps=self.pre_impact_relative_velocity_mps,
            source_mass_kg=self.source_mass_kg,
            target_mass_kg=self.target_mass_kg,
            output_unit=self.output_unit,
        )
        if self.magnitude != expected_magnitude:
            raise ValueError("impact magnitude differs from canonical pre-impact facts")
        payload = {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if field.name != "evidence_hash"
        }
        expected_hash = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    _plain(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
            ).hexdigest()
        )
        if self.evidence_hash != expected_hash:
            raise ValueError("impact evidence canonical hash mismatch")

    @classmethod
    def create(cls, **values: object) -> ImpactDamageEvidenceV2:
        payload = dict(values)
        payload.pop("evidence_hash", None)
        evidence_hash = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    _plain(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
            ).hexdigest()
        )
        return cls(**payload, evidence_hash=evidence_hash)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class BoundaryEvaluationV2:
    tick: int
    boundary_events: tuple[BoundaryEventV2, ...] = ()
    collision_events: tuple[CollisionEventV2, ...] = ()
    damage_intents: tuple[DamageIntentV2, ...] = ()
    policy_actions: tuple[BoundaryPolicyActionV2, ...] = ()
    lifecycle_intents: tuple[DeactivateIntentV2 | MissionEventIntentV2, ...] = ()

    @property
    def fact_fingerprint(self) -> str:
        return json.dumps(
            _plain(
                {
                    "boundary_events": self.boundary_events,
                    "collision_events": self.collision_events,
                }
            ),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @property
    def response_fingerprint(self) -> str:
        return json.dumps(
            _plain(
                {
                    "damage_intents": self.damage_intents,
                    "policy_actions": self.policy_actions,
                    "lifecycle_intents": self.lifecycle_intents,
                }
            ),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def to_json(self) -> str:
        return json.dumps(
            _plain(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )


@dataclass(frozen=True, slots=True)
class ZoneActivationReceiptV2:
    operation_id: str
    zone_id: str
    active: bool
    tick: int
    changed: bool


@dataclass(frozen=True, slots=True)
class ZoneActivationSnapshotV2:
    schema_version: str
    activations: tuple[tuple[str, bool], ...]
    receipts: tuple[ZoneActivationReceiptV2, ...]
    snapshot_hash: str

    def _payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "activations": [list(item) for item in self.activations],
            "receipts": [_plain(item) for item in self.receipts],
        }

    @classmethod
    def build(
        cls,
        activations: Mapping[str, bool],
        receipts: Mapping[str, ZoneActivationReceiptV2],
    ) -> Self:
        ordered_activations = tuple(sorted(activations.items()))
        ordered_receipts = tuple(receipts[key] for key in sorted(receipts))
        payload = {
            "schema_version": "2.0",
            "activations": [list(item) for item in ordered_activations],
            "receipts": [_plain(item) for item in ordered_receipts],
        }
        digest = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest()
        )
        return cls("2.0", ordered_activations, ordered_receipts, digest)

    def __post_init__(self) -> None:
        if self.schema_version != "2.0":
            raise ValueError("zone activation snapshot schema is unsupported")
        if self.activations != tuple(sorted(self.activations)) or len(self.activations) != len(
            {item[0] for item in self.activations}
        ):
            raise ValueError("zone activation snapshot IDs must be unique and ordered")
        if any(not isinstance(active, bool) for _, active in self.activations):
            raise ValueError("zone activation states must be boolean")
        expected = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    self._payload(), sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
            ).hexdigest()
        )
        if self.snapshot_hash != expected:
            raise _boundary_error(
                "boundary.activation_snapshot_integrity_invalid",
                ("snapshot_hash",),
                self.snapshot_hash,
                "zone activation snapshot hash does not match its canonical payload",
                "use an unmodified snapshot and independently retained hash anchor",
            )

    def to_json(self) -> str:
        return json.dumps(
            {**self._payload(), "snapshot_hash": self.snapshot_hash},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, encoded: str) -> Self:
        try:
            payload = json.loads(encoded)
            if not isinstance(payload, dict) or set(payload) != {
                "schema_version",
                "activations",
                "receipts",
                "snapshot_hash",
            }:
                raise ValueError("snapshot fields are invalid")
            activations = tuple(
                (_identifier(item[0], name="zone_id"), item[1]) for item in payload["activations"]
            )
            receipts = tuple(ZoneActivationReceiptV2(**item) for item in payload["receipts"])
            return cls(
                schema_version=payload["schema_version"],
                activations=activations,
                receipts=receipts,
                snapshot_hash=payload["snapshot_hash"],
            )
        except BoundaryErrorV2:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise _boundary_error(
                "boundary.activation_snapshot_integrity_invalid",
                ("snapshot",),
                type(error).__name__,
                "zone activation snapshot JSON is malformed",
                "use canonical JSON returned by ZoneActivationSnapshotV2.to_json",
            ) from error


@dataclass(frozen=True, slots=True)
class AllowedZoneV2:
    zone_id: str
    geometry_type: Literal["polygon", "circle"]
    positions_m: tuple[tuple[float, float], ...]
    center_m: tuple[float, float] | None
    radius_m: float | None
    domains: tuple[str, ...]
    point_on_edge: Literal["inside", "outside"] = "inside"
    priority: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "zone_id", _identifier(self.zone_id, name="zone_id"))
        if self.geometry_type not in {"polygon", "circle"}:
            raise ValueError("unsupported zone geometry")
        if self.point_on_edge not in {"inside", "outside"}:
            raise ValueError("point_on_edge must be inside or outside")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        if self.geometry_type == "polygon":
            points = tuple(
                _point2(point, name=f"positions_m[{index}]")
                for index, point in enumerate(self.positions_m)
            )
            if len(points) < 3:
                raise ValueError("polygon zone requires at least three points")
            _validate_polygon(points, obstacle_id=self.zone_id)
            object.__setattr__(self, "positions_m", points)
            if self.center_m is not None or self.radius_m is not None:
                raise ValueError("polygon zone cannot define circle fields")
        else:
            if self.center_m is None or self.radius_m is None:
                raise ValueError("circle zone requires center and radius")
            object.__setattr__(self, "center_m", _point2(self.center_m, name="center_m"))
            object.__setattr__(
                self,
                "radius_m",
                _finite_number(self.radius_m, name="radius_m", positive=True),
            )
        object.__setattr__(self, "domains", tuple(self.domains))

    @classmethod
    def polygon(
        cls,
        zone_id: str,
        positions_m: Sequence[Sequence[float]],
        *,
        domains: Sequence[str] = (),
        point_on_edge: Literal["inside", "outside"] = "inside",
        priority: int = 0,
    ) -> Self:
        return cls(
            zone_id=zone_id,
            geometry_type="polygon",
            positions_m=tuple(
                _point2(point, name=f"positions_m[{index}]")
                for index, point in enumerate(positions_m)
            ),
            center_m=None,
            radius_m=None,
            domains=tuple(domains),
            point_on_edge=point_on_edge,
            priority=priority,
        )

    @classmethod
    def circle(
        cls,
        zone_id: str,
        center_m: Sequence[float],
        radius_m: float,
        *,
        domains: Sequence[str] = (),
        point_on_edge: Literal["inside", "outside"] = "inside",
        priority: int = 0,
    ) -> Self:
        return cls(
            zone_id=zone_id,
            geometry_type="circle",
            positions_m=(),
            center_m=_point2(center_m, name="center_m"),
            radius_m=radius_m,
            domains=tuple(domains),
            point_on_edge=point_on_edge,
            priority=priority,
        )


_ZoneV2 = AllowedZoneV2


class _ResolvedWorld(Protocol):
    coordinate_frame: object
    zones: Sequence[object]
    boundaries: Sequence[object]


class _ResolvedScenario(Protocol):
    world: _ResolvedWorld
    entities: Sequence[object]
    resolved_hash: str

    def validate_integrity(self) -> None: ...


def _position(segment: MotionSegmentV2, fraction: float) -> Vector3V2:
    bounded = min(1.0, max(0.0, fraction))
    return cast(
        Vector3V2,
        tuple(
            segment.start_m[index] + (segment.end_m[index] - segment.start_m[index]) * bounded
            for index in range(3)
        ),
    )


def _first_axis_crossing(start: float, end: float, threshold: float) -> float:
    if start == end:
        return 0.0
    return min(1.0, max(0.0, (threshold - start) / (end - start)))


def _point_segment_distance_squared(
    point: tuple[float, float], first: tuple[float, float], second: tuple[float, float]
) -> float:
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0.0:
        return (point[0] - first[0]) ** 2 + (point[1] - first[1]) ** 2
    fraction = min(
        1.0,
        max(
            0.0,
            ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy) / length_squared,
        ),
    )
    closest = (first[0] + fraction * dx, first[1] + fraction * dy)
    return (point[0] - closest[0]) ** 2 + (point[1] - closest[1]) ** 2


def _point_in_polygon(
    point: tuple[float, float],
    polygon: tuple[tuple[float, float], ...],
    *,
    tolerance: float,
    edge_inside: bool,
) -> bool:
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if _point_segment_distance_squared(point, first, second) <= tolerance * tolerance:
            return edge_inside
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current[1] > point[1]) != (previous[1] > point[1]):
            intersect_x = (previous[0] - current[0]) * (point[1] - current[1]) / (
                previous[1] - current[1]
            ) + current[0]
            if point[0] < intersect_x:
                inside = not inside
        previous = current
    return inside


def _segment_intersection_fraction(
    start: tuple[float, float],
    end: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
    tolerance: float,
) -> float | None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    ex = second[0] - first[0]
    ey = second[1] - first[1]
    denominator = dx * ey - dy * ex
    offset_x = first[0] - start[0]
    offset_y = first[1] - start[1]
    if abs(denominator) <= tolerance:
        if _point_segment_distance_squared(start, first, second) <= tolerance * tolerance:
            return 0.0
        # Collinear or tangent parallel sweeps are still continuous collisions.
        candidates: list[float] = []
        length_squared = dx * dx + dy * dy
        if length_squared > 0.0:
            for point in (first, second):
                fraction = (
                    (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
                ) / length_squared
                if -tolerance <= fraction <= 1.0 + tolerance:
                    projected = (start[0] + fraction * dx, start[1] + fraction * dy)
                    if (
                        _point_segment_distance_squared(projected, first, second)
                        <= tolerance * tolerance
                    ):
                        candidates.append(min(1.0, max(0.0, fraction)))
        return min(candidates) if candidates else None
    movement_fraction = (offset_x * ey - offset_y * ex) / denominator
    edge_fraction = (offset_x * dy - offset_y * dx) / denominator
    if (
        -tolerance <= movement_fraction <= 1.0 + tolerance
        and -tolerance <= edge_fraction <= 1.0 + tolerance
    ):
        return min(1.0, max(0.0, movement_fraction))
    return None


def _validate_polygon(polygon: tuple[tuple[float, float], ...], *, obstacle_id: str) -> None:
    if len(polygon) != len(set(polygon)):
        raise _boundary_error(
            "boundary.polygon_duplicate_vertex",
            ("obstacles", obstacle_id, "positions_m"),
            polygon,
            "polygon contains a duplicate vertex",
            "provide a simple ring of unique vertices",
        )
    for index in range(len(polygon)):
        previous = polygon[index - 1]
        current = polygon[index]
        following = polygon[(index + 1) % len(polygon)]
        cross = (current[0] - previous[0]) * (following[1] - current[1]) - (
            current[1] - previous[1]
        ) * (following[0] - current[0])
        if abs(cross) <= 1e-12:
            raise _boundary_error(
                "boundary.polygon_collinear_vertex",
                ("obstacles", obstacle_id, "positions_m", str(index)),
                current,
                "three consecutive polygon vertices are collinear",
                "remove the redundant middle vertex",
            )
    edge_count = len(polygon)
    for first_index in range(edge_count):
        first_a = polygon[first_index]
        first_b = polygon[(first_index + 1) % edge_count]
        for second_index in range(first_index + 1, edge_count):
            if second_index in {
                first_index,
                (first_index + 1) % edge_count,
                (first_index - 1) % edge_count,
            }:
                continue
            second_a = polygon[second_index]
            second_b = polygon[(second_index + 1) % edge_count]
            if (
                _segment_intersection_fraction(first_a, first_b, second_a, second_b, 1e-12)
                is not None
            ):
                raise _boundary_error(
                    "boundary.polygon_self_intersection",
                    ("obstacles", obstacle_id, "positions_m"),
                    polygon,
                    "polygon edges self-intersect",
                    "provide one non-self-intersecting simple ring",
                )


def _circle_sweep_fraction(
    start: tuple[float, float],
    end: tuple[float, float],
    center: tuple[float, float],
    radius: float,
    tolerance: float,
) -> float | None:
    relative_x = start[0] - center[0]
    relative_y = start[1] - center[1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    # Entity/entity contact uses the exact resolved shape extent.  The system
    # tolerance is for boundary classification; widening both swept shapes
    # here changes their temporal overlap and can manufacture a collision.
    expanded = radius
    constant = relative_x * relative_x + relative_y * relative_y - expanded * expanded
    if constant <= 0.0:
        return 0.0
    quadratic = dx * dx + dy * dy
    if quadratic == 0.0:
        return None
    linear = 2.0 * (relative_x * dx + relative_y * dy)
    discriminant = linear * linear - 4.0 * quadratic * constant
    if discriminant < -tolerance:
        return None
    root = math.sqrt(max(0.0, discriminant))
    candidates = tuple(
        fraction
        for fraction in (
            (-linear - root) / (2.0 * quadratic),
            (-linear + root) / (2.0 * quadratic),
        )
        if -tolerance <= fraction <= 1.0 + tolerance
    )
    return min(1.0, max(0.0, min(candidates))) if candidates else None


def _polygon_sweep_fraction(
    start: tuple[float, float],
    end: tuple[float, float],
    polygon: tuple[tuple[float, float], ...],
    radius: float,
    tolerance: float,
) -> float | None:
    if _point_in_polygon(start, polygon, tolerance=radius + tolerance, edge_inside=True):
        return 0.0
    candidates: list[float] = []
    for index, edge_first in enumerate(polygon):
        edge_second = polygon[(index + 1) % len(polygon)]
        intersection = _segment_intersection_fraction(
            start, end, edge_first, edge_second, tolerance
        )
        if intersection is not None:
            candidates.append(intersection)
        if radius > 0.0:
            edge_x = edge_second[0] - edge_first[0]
            edge_y = edge_second[1] - edge_first[1]
            edge_length = math.hypot(edge_x, edge_y)
            normal_x = -edge_y / edge_length
            normal_y = edge_x / edge_length
            start_distance = (start[0] - edge_first[0]) * normal_x + (
                start[1] - edge_first[1]
            ) * normal_y
            end_distance = (end[0] - edge_first[0]) * normal_x + (end[1] - edge_first[1]) * normal_y
            distance_delta = end_distance - start_distance
            if distance_delta != 0.0:
                for signed_radius in (-radius, radius):
                    offset_fraction = (signed_radius - start_distance) / distance_delta
                    if 0.0 <= offset_fraction <= 1.0:
                        contact_x = start[0] + (end[0] - start[0]) * offset_fraction
                        contact_y = start[1] + (end[1] - start[1]) * offset_fraction
                        projection = (
                            (contact_x - edge_first[0]) * edge_x
                            + (contact_y - edge_first[1]) * edge_y
                        ) / (edge_length * edge_length)
                        movement_dot_edge = (end[0] - start[0]) * edge_x + (
                            end[1] - start[1]
                        ) * edge_y
                        perpendicular_extension = (
                            abs(movement_dot_edge) <= tolerance
                            and -radius / edge_length <= projection <= 1.0 + radius / edge_length
                        )
                        if 0.0 <= projection <= 1.0 or perpendicular_extension:
                            candidates.append(offset_fraction)
            for vertex in (edge_first, edge_second):
                collision = _circle_sweep_fraction(start, end, vertex, radius, 0.0)
                if collision is not None:
                    candidates.append(collision)
    if candidates:
        return min(candidates)
    # Detect a parallel pass within the entity radius without time sampling.
    if any(
        _segments_distance_squared(start, end, polygon[index], polygon[(index + 1) % len(polygon)])
        <= (radius + tolerance) ** 2
        for index in range(len(polygon))
    ):
        return 0.0
    return None


def _segments_distance_squared(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> float:
    if _segment_intersection_fraction(a, b, c, d, 1e-12) is not None:
        return 0.0
    return min(
        _point_segment_distance_squared(a, c, d),
        _point_segment_distance_squared(b, c, d),
        _point_segment_distance_squared(c, a, b),
        _point_segment_distance_squared(d, a, b),
    )


def _zone_contains(zone: _ZoneV2, point: tuple[float, float], tolerance: float) -> bool:
    if zone.geometry_type == "circle":
        if zone.center_m is None or zone.radius_m is None:
            raise ValueError("circle zone is missing center or radius")
        distance_squared = (point[0] - zone.center_m[0]) ** 2 + (point[1] - zone.center_m[1]) ** 2
        threshold = zone.radius_m + (tolerance if zone.point_on_edge == "inside" else -tolerance)
        return distance_squared <= max(0.0, threshold) ** 2
    return _point_in_polygon(
        point,
        zone.positions_m,
        tolerance=tolerance,
        edge_inside=zone.point_on_edge == "inside",
    )


def _zone_sweep(
    zone: _ZoneV2, segment: MotionSegmentV2, radius_m: float, tolerance: float
) -> float | None:
    start = segment.start_m[:2]
    end = segment.end_m[:2]
    if zone.geometry_type == "circle":
        if zone.center_m is None or zone.radius_m is None:
            raise ValueError("circle zone is missing center or radius")
        return _circle_sweep_fraction(
            start, end, zone.center_m, zone.radius_m + radius_m, tolerance
        )
    return _polygon_sweep_fraction(start, end, zone.positions_m, radius_m, tolerance)


def _zone_exit_fraction_normal(
    zone: _ZoneV2,
    segment: MotionSegmentV2,
    radius_m: float,
    tolerance: float,
) -> tuple[float, Vector3V2] | None:
    start = segment.start_m[:2]
    end = segment.end_m[:2]
    if zone.geometry_type == "circle":
        if zone.center_m is None or zone.radius_m is None:
            raise ValueError("circle zone is missing center or radius")
        effective_radius = zone.radius_m - radius_m
        if effective_radius <= 0.0:
            return 0.0, (1.0, 0.0, 0.0)
        relative_x = start[0] - zone.center_m[0]
        relative_y = start[1] - zone.center_m[1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        quadratic = dx * dx + dy * dy
        if quadratic == 0.0:
            return None
        linear = 2.0 * (relative_x * dx + relative_y * dy)
        constant = relative_x * relative_x + relative_y * relative_y - effective_radius**2
        discriminant = linear * linear - 4.0 * quadratic * constant
        if discriminant < 0.0:
            return None
        root = math.sqrt(discriminant)
        circle_roots = [
            value
            for value in (
                (-linear - root) / (2.0 * quadratic),
                (-linear + root) / (2.0 * quadratic),
            )
            if tolerance < value <= 1.0 + tolerance
        ]
        if not circle_roots:
            return None
        fraction = min(circle_roots)
        contact = _position(segment, fraction)
        normal = _unit_vector(
            (contact[0] - zone.center_m[0], contact[1] - zone.center_m[1], 0.0),
            name="zone_normal",
        )
        return min(1.0, fraction), normal
    polygon = zone.positions_m
    signed_area = sum(
        polygon[index][0] * polygon[(index + 1) % len(polygon)][1]
        - polygon[(index + 1) % len(polygon)][0] * polygon[index][1]
        for index in range(len(polygon))
    )
    exit_candidates: list[tuple[float, Vector3V2]] = []
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        dx = second[0] - first[0]
        dy = second[1] - first[1]
        length = math.hypot(dx, dy)
        if signed_area > 0.0:
            outward: Vector3V2 = (dy / length, -dx / length, 0.0)
        else:
            outward = (-dy / length, dx / length, 0.0)
        start_distance = (start[0] - first[0]) * outward[0] + (start[1] - first[1]) * outward[1]
        end_distance = (end[0] - first[0]) * outward[0] + (end[1] - first[1]) * outward[1]
        threshold = -radius_m
        if start_distance <= threshold + tolerance and end_distance > threshold + tolerance:
            fraction = (threshold - start_distance) / (end_distance - start_distance)
            if 0.0 <= fraction <= 1.0:
                exit_candidates.append((fraction, outward))
    return min(exit_candidates, key=lambda item: item[0]) if exit_candidates else None


def _obstacle_normal(
    obstacle: StaticObstacleV2, position_m: Vector3V2, radius_m: float
) -> Vector3V2:
    if obstacle.geometry_type == "circle":
        if obstacle.center_m is None:
            raise ValueError("circle obstacle is missing center")
        return _unit_vector(
            (
                position_m[0] - obstacle.center_m[0],
                position_m[1] - obstacle.center_m[1],
                0.0,
            ),
            name="collision_normal",
        )
    xs = tuple(point[0] for point in obstacle.positions_m)
    ys = tuple(point[1] for point in obstacle.positions_m)
    candidates = (
        (abs(position_m[0] - (min(xs) - radius_m)), (-1.0, 0.0, 0.0)),
        (abs(position_m[0] - (max(xs) + radius_m)), (1.0, 0.0, 0.0)),
        (abs(position_m[1] - (min(ys) - radius_m)), (0.0, -1.0, 0.0)),
        (abs(position_m[1] - (max(ys) + radius_m)), (0.0, 1.0, 0.0)),
    )
    return min(candidates, key=lambda item: item[0])[1]


class BoundarySystemV2:
    """Continuous, deterministic boundary and collision adjudicator."""

    def __init__(
        self,
        *,
        geography: GeographyServiceV2,
        boundaries: Sequence[StaticObstacleV2] = (),
        point_on_edge: Literal["inside", "outside"] = "inside",
        policy: BoundaryPolicyV2 | None = None,
        allowed_zones: Sequence[_ZoneV2] = (),
        excluded_zones: Sequence[_ZoneV2] = (),
        known_zones: Sequence[_ZoneV2] = (),
        zone_policies: Mapping[str, BoundaryPolicyV2] | None = None,
        enable_entity_collisions: bool = False,
        emit_damage_intents: bool = True,
        impact_damage_policy: _ImpactDamagePolicyLike | None = None,
    ) -> None:
        if point_on_edge not in {"inside", "outside"}:
            raise ValueError("point_on_edge must be inside or outside")
        self._geography = geography
        self._obstacles = tuple(sorted(boundaries, key=lambda item: item.obstacle_id))
        if len(self._obstacles) != len({item.obstacle_id for item in self._obstacles}):
            raise ValueError("obstacle IDs must be unique")
        self._point_on_edge = point_on_edge
        self._policy = policy or BoundaryPolicyV2("constrain")
        self._allowed_zones = tuple(sorted(allowed_zones, key=lambda item: item.zone_id))
        self._excluded_zones = tuple(sorted(excluded_zones, key=lambda item: item.zone_id))
        self._known_zones = tuple(sorted(known_zones, key=lambda item: item.zone_id))
        self._zone_index = {
            item.zone_id: item
            for item in (*self._known_zones, *self._allowed_zones, *self._excluded_zones)
        }
        known_zone_ids = set(self._zone_index)
        supplied_policies = dict(zone_policies or {})
        if set(supplied_policies) - known_zone_ids:
            raise ValueError("zone policy references an unknown spatial zone")
        self._zone_policies = {
            zone_id: supplied_policies.get(zone_id, self._policy)
            for zone_id in sorted(known_zone_ids)
        }
        if not isinstance(enable_entity_collisions, bool):
            raise ValueError("enable_entity_collisions must be boolean")
        if not isinstance(emit_damage_intents, bool):
            raise ValueError("emit_damage_intents must be boolean")
        self._enable_entity_collisions = enable_entity_collisions
        self._emit_damage_intents = emit_damage_intents
        self._impact_damage_policy = impact_damage_policy
        self._entities: dict[str, BoundaryEntityV2] = {}
        self._zone_activation = {zone_id: True for zone_id in sorted(known_zone_ids)}
        self._activation_receipts: dict[str, ZoneActivationReceiptV2] = {}
        self._origin_tick: int | None = None
        self._tick_start_time_seconds: float | None = None

    @classmethod
    def with_policy(
        cls,
        *,
        geography: GeographyServiceV2,
        policy: BoundaryPolicyV2,
        boundaries: Sequence[StaticObstacleV2] = (),
        point_on_edge: Literal["inside", "outside"] = "inside",
    ) -> Self:
        excluded_zones = tuple(
            _ZoneV2(
                zone_id=zone.zone_id,
                geometry_type=zone.geometry_type,
                positions_m=zone.positions_m,
                center_m=zone.center_m,
                radius_m=zone.radius_m,
                domains=zone.domains,
            )
            for zone in geography.spatial_zones
            if zone.deployment_excluded
        )
        return cls(
            geography=geography,
            boundaries=boundaries,
            point_on_edge=point_on_edge,
            policy=policy,
            excluded_zones=excluded_zones,
            zone_policies={zone.zone_id: policy for zone in excluded_zones},
        )

    @classmethod
    def from_resolved(
        cls,
        resolved: _ResolvedScenario,
        *,
        geography: GeographyServiceV2,
        enable_entity_collisions: bool = False,
        emit_damage_intents: bool = True,
    ) -> Self:
        try:
            resolved.validate_integrity()
        except (AttributeError, TypeError, ValueError) as error:
            raise _boundary_error(
                "boundary.resolved_integrity_invalid",
                ("resolved",),
                type(error).__name__,
                "resolved scenario failed complete semantic integrity validation",
                "use the original integrity-validated compiler artifact",
            ) from error
        world = resolved.world
        resolved_boundaries = {str(item.zone_id): item for item in getattr(world, "boundaries", ())}
        allowed: list[_ZoneV2] = []
        excluded: list[_ZoneV2] = []
        known: list[_ZoneV2] = []
        deployment_excluded = {
            zone_id
            for entity in getattr(resolved, "entities", ())
            if getattr(entity, "boundary_deployment", None) is not None
            for zone_id in entity.boundary_deployment.excluded_zone_ids
        }
        zone_policies: dict[str, BoundaryPolicyV2] = {}
        for item in getattr(world, "zones", ()):
            geometry = item.geometry
            zone_id = str(item.id)
            boundary = resolved_boundaries.get(zone_id)
            zone = _ZoneV2(
                zone_id=zone_id,
                geometry_type=cast(Literal["polygon", "circle"], geometry.type),
                positions_m=tuple(
                    _point2(point, name="positions_m") for point in geometry.positions_m
                ),
                center_m=(
                    None
                    if geometry.center_m is None
                    else _point2(geometry.center_m, name="center_m")
                ),
                radius_m=(
                    None
                    if geometry.radius_m is None
                    else _finite_number(geometry.radius_m, name="radius_m", positive=True)
                ),
                domains=tuple(str(domain) for domain in item.domains),
                point_on_edge=cast(
                    Literal["inside", "outside"],
                    getattr(boundary, "point_on_edge", "inside"),
                ),
                priority=int(getattr(boundary, "priority", 0)),
            )
            is_terrain = "terrain:land" in getattr(item, "tags", ())
            if is_terrain:
                known.append(zone)
            elif boundary is not None:
                allowed.append(zone)
            elif zone_id in deployment_excluded:
                excluded.append(zone)
        policy_names = {
            "reject_command": "reject",
            "constrain_motion": "constrain",
            "stop": "stop",
            "reflect": "reflect",
            "collision_effect": "effect",
            "deactivate": "deactivate",
            "mission_event": "mission_event",
        }
        for zone_id, boundary in resolved_boundaries.items():
            policy_name = policy_names.get(getattr(boundary, "action", ""), "constrain")
            zone_policies[zone_id] = BoundaryPolicyV2(
                cast(BoundaryPolicyNameV2, policy_name),
                priority=int(getattr(boundary, "priority", 0)),
            )
        for zone_id in deployment_excluded:
            zone_policies.setdefault(zone_id, BoundaryPolicyV2("constrain"))
        return cls(
            geography=geography,
            point_on_edge="inside",
            policy=BoundaryPolicyV2("constrain"),
            allowed_zones=allowed,
            excluded_zones=excluded,
            known_zones=known,
            zone_policies=zone_policies,
            enable_entity_collisions=enable_entity_collisions,
            emit_damage_intents=emit_damage_intents,
            impact_damage_policy=getattr(resolved, "spatial_effect_policy", None),
        )

    def zone_policy(self, zone_id: str) -> BoundaryPolicyV2:
        try:
            return self._zone_policies[zone_id]
        except KeyError as error:
            raise ValueError(f"unknown spatial zone: {zone_id}") from error

    def is_zone_active(self, zone_id: str) -> bool:
        try:
            return self._zone_activation[zone_id]
        except KeyError as error:
            raise _boundary_error(
                "boundary.zone_unknown",
                ("zone_id",),
                zone_id,
                "zone activation references an unknown spatial boundary",
                "use an allowed or excluded zone ID from the resolved topology",
            ) from error

    def set_zone_activation(
        self, *, zone_id: str, active: bool, tick: int, operation_id: str
    ) -> ZoneActivationReceiptV2:
        zone_id = _identifier(zone_id, name="zone_id")
        operation_id = _identifier(operation_id, name="operation_id")
        if not isinstance(active, bool):
            raise ValueError("active must be boolean")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if zone_id not in self._zone_activation:
            self.is_zone_active(zone_id)
        previous = self._activation_receipts.get(operation_id)
        if previous is not None:
            if (previous.zone_id, previous.active, previous.tick) != (zone_id, active, tick):
                raise _boundary_error(
                    "boundary.activation_operation_conflict",
                    ("operation_id",),
                    operation_id,
                    "operation ID was already used for different activation parameters",
                    "retry with identical parameters or allocate a fresh operation ID",
                )
            return previous
        receipt = ZoneActivationReceiptV2(
            operation_id=operation_id,
            zone_id=zone_id,
            active=active,
            tick=tick,
            changed=self._zone_activation[zone_id] != active,
        )
        self._zone_activation[zone_id] = active
        self._activation_receipts[operation_id] = receipt
        return receipt

    def activation_snapshot(self) -> ZoneActivationSnapshotV2:
        return ZoneActivationSnapshotV2.build(self._zone_activation, self._activation_receipts)

    def restore_activation_snapshot(
        self,
        snapshot: ZoneActivationSnapshotV2,
        *,
        expected_snapshot_hash: str,
    ) -> None:
        if not isinstance(snapshot, ZoneActivationSnapshotV2):
            raise TypeError("snapshot must be ZoneActivationSnapshotV2")
        if snapshot.snapshot_hash != expected_snapshot_hash:
            raise _boundary_error(
                "boundary.activation_snapshot_integrity_invalid",
                ("expected_snapshot_hash",),
                expected_snapshot_hash,
                "independent snapshot hash anchor does not match",
                "pass the independently retained hash for this exact snapshot",
            )
        checked = ZoneActivationSnapshotV2.from_json(snapshot.to_json())
        activations = dict(checked.activations)
        if set(activations) != set(self._zone_activation):
            raise _boundary_error(
                "boundary.activation_snapshot_topology_mismatch",
                ("activations",),
                sorted(activations),
                "snapshot zone topology differs from this boundary system",
                "restore only into the same resolved boundary topology",
            )
        receipts = {item.operation_id: item for item in checked.receipts}
        if len(receipts) != len(checked.receipts):
            raise ValueError("activation receipt operation IDs must be unique")
        self._zone_activation = activations
        self._activation_receipts = receipts

    @property
    def registered_entities(self) -> tuple[BoundaryEntityV2, ...]:
        return tuple(self._entities[key] for key in sorted(self._entities))

    def register_entities(self, entities: Sequence[BoundaryEntityV2]) -> None:
        staged = dict(self._entities)
        for entity in entities:
            if not isinstance(entity, BoundaryEntityV2):
                raise TypeError("registered entity must be BoundaryEntityV2")
            if entity.entity_id in staged:
                raise ValueError(f"duplicate boundary entity ID: {entity.entity_id}")
            unknown_zones = (set(entity.allowed_zone_ids) | set(entity.excluded_zone_ids)) - set(
                self._zone_index
            )
            if unknown_zones:
                raise ValueError(
                    f"entity references unknown spatial zones: {sorted(unknown_zones)}"
                )
            staged[entity.entity_id] = entity
        self._entities = staged

    def _boundary_events(
        self, entity: BoundaryEntityV2, segment: MotionSegmentV2, tick: int
    ) -> list[BoundaryEventV2]:
        lower, upper = self._geography.local_bounds_m
        tolerance = self._geography.tolerance_m
        candidates: list[tuple[int, float, BoundaryKindV2, str, Vector3V2, int]] = []
        horizontal: list[tuple[float, Vector3V2]] = []
        for axis in (0, 1):
            minimum = lower[axis] + entity.radius_m
            maximum = upper[axis] - entity.radius_m
            if segment.end_m[axis] < minimum - tolerance:
                normal = (-1.0, 0.0, 0.0) if axis == 0 else (0.0, -1.0, 0.0)
                horizontal.append(
                    (
                        _first_axis_crossing(segment.start_m[axis], segment.end_m[axis], minimum),
                        normal,
                    )
                )
            elif segment.end_m[axis] > maximum + tolerance:
                normal = (1.0, 0.0, 0.0) if axis == 0 else (0.0, 1.0, 0.0)
                horizontal.append(
                    (
                        _first_axis_crossing(segment.start_m[axis], segment.end_m[axis], maximum),
                        normal,
                    )
                )
        if horizontal:
            fraction, normal = min(horizontal, key=lambda item: item[0])
            candidates.append((0, fraction, "world_exit", "world.bounds", normal, 0))
        minimum_z = lower[2] + entity.radius_m
        maximum_z = upper[2] - entity.radius_m
        if segment.end_m[2] > maximum_z + tolerance:
            candidates.append(
                (
                    1,
                    _first_axis_crossing(segment.start_m[2], segment.end_m[2], maximum_z),
                    "altitude_max",
                    "world.altitude",
                    (0.0, 0.0, 1.0),
                    0,
                )
            )
        if segment.end_m[2] < minimum_z - tolerance:
            candidates.append(
                (
                    2,
                    _first_axis_crossing(segment.start_m[2], segment.end_m[2], minimum_z),
                    "depth_max",
                    "world.depth",
                    (0.0, 0.0, -1.0),
                    0,
                )
            )
        has_entity_topology = bool(entity.allowed_zone_ids or entity.excluded_zone_ids)
        allowed_zones = (
            tuple(self._zone_index[zone_id] for zone_id in entity.allowed_zone_ids)
            if has_entity_topology
            else self._allowed_zones
        )
        excluded_zones = (
            tuple(self._zone_index[zone_id] for zone_id in entity.excluded_zone_ids)
            if has_entity_topology
            else self._excluded_zones
        )
        for zone in allowed_zones:
            if not self._zone_activation[zone.zone_id]:
                continue
            if zone.domains and entity.domain not in zone.domains:
                continue
            exit_fact = _zone_exit_fraction_normal(zone, segment, entity.radius_m, tolerance)
            if exit_fact is not None:
                fraction, normal = exit_fact
                candidates.append(
                    (3, fraction, "allowed_zone", zone.zone_id, normal, zone.priority)
                )
        for zone in excluded_zones:
            if not self._zone_activation[zone.zone_id]:
                continue
            if zone.domains and entity.domain not in zone.domains:
                continue
            excluded_fraction = _zone_sweep(zone, segment, entity.radius_m, tolerance)
            if excluded_fraction is not None:
                contact = _position(segment, excluded_fraction)
                if zone.geometry_type == "circle":
                    if zone.center_m is None:
                        raise ValueError("circle zone is missing center")
                    normal = _unit_vector(
                        (
                            contact[0] - zone.center_m[0],
                            contact[1] - zone.center_m[1],
                            0.0,
                        ),
                        name="zone_normal",
                    )
                else:
                    normal = (1.0, 0.0, 0.0)
                candidates.append(
                    (
                        4,
                        excluded_fraction,
                        "excluded_zone",
                        zone.zone_id,
                        normal,
                        zone.priority,
                    )
                )
        events: list[BoundaryEventV2] = []
        ordered = sorted(candidates, key=lambda item: (item[0], -item[5], item[3], item[1]))
        for index, (_, fraction, kind, boundary_id, normal, priority) in enumerate(ordered):
            events.append(
                BoundaryEventV2(
                    event_id=(
                        f"boundary-event:{tick}:{entity.entity_id}:{kind}:{boundary_id}:{index}"
                    ),
                    tick=tick,
                    entity_id=entity.entity_id,
                    kind=kind,
                    boundary_id=boundary_id,
                    time_fraction=fraction,
                    position_m=_position(segment, fraction),
                    normal=normal,
                    priority=priority,
                    absolute_time_seconds=(
                        tick * segment.dt_seconds + fraction * segment.dt_seconds
                        if self._tick_start_time_seconds is None
                        else self._absolute_time(tick, segment.dt_seconds, fraction)
                    ),
                )
            )
        return events

    def _static_collisions(
        self, entity: BoundaryEntityV2, segment: MotionSegmentV2, tick: int
    ) -> list[CollisionEventV2]:
        collisions: list[CollisionEventV2] = []
        tolerance = self._geography.tolerance_m
        for obstacle in self._obstacles:
            if obstacle.domains and entity.domain not in obstacle.domains:
                continue
            segment_low = min(segment.start_m[2], segment.end_m[2]) - entity.radius_m
            segment_high = max(segment.start_m[2], segment.end_m[2]) + entity.radius_m
            if obstacle.minimum_z_m is not None and segment_high < obstacle.minimum_z_m - tolerance:
                continue
            if obstacle.maximum_z_m is not None and segment_low > obstacle.maximum_z_m + tolerance:
                continue
            if obstacle.geometry_type == "circle":
                if obstacle.center_m is None or obstacle.radius_m is None:
                    raise ValueError("circle obstacle is missing center or radius")
                fraction = _circle_sweep_fraction(
                    segment.start_m[:2],
                    segment.end_m[:2],
                    obstacle.center_m,
                    obstacle.radius_m + entity.radius_m,
                    tolerance,
                )
                reverse_fraction = _circle_sweep_fraction(
                    segment.end_m[:2],
                    segment.start_m[:2],
                    obstacle.center_m,
                    obstacle.radius_m + entity.radius_m,
                    tolerance,
                )
            else:
                fraction = _polygon_sweep_fraction(
                    segment.start_m[:2],
                    segment.end_m[:2],
                    obstacle.positions_m,
                    entity.radius_m,
                    tolerance,
                )
                reverse_fraction = _polygon_sweep_fraction(
                    segment.end_m[:2],
                    segment.start_m[:2],
                    obstacle.positions_m,
                    entity.radius_m,
                    tolerance,
                )
            if fraction is not None and (
                obstacle.minimum_z_m is not None or obstacle.maximum_z_m is not None
            ):
                lower_z = (
                    -math.inf
                    if obstacle.minimum_z_m is None
                    else obstacle.minimum_z_m - entity.radius_m
                )
                upper_z = (
                    math.inf
                    if obstacle.maximum_z_m is None
                    else obstacle.maximum_z_m + entity.radius_m
                )
                vertical = _linear_interval(segment.start_m[2], segment.end_m[2], lower_z, upper_z)
                xy_exit = 1.0 if reverse_fraction is None else 1.0 - reverse_fraction
                if vertical is None or max(fraction, vertical[0]) > min(xy_exit, vertical[1]):
                    fraction = None
                else:
                    fraction = max(fraction, vertical[0])
            if fraction is not None:
                contact = _position(segment, fraction)
                collisions.append(
                    CollisionEventV2(
                        event_id=f"collision:{tick}:{entity.entity_id}:obstacle:{obstacle.obstacle_id}",
                        tick=tick,
                        entity_id=entity.entity_id,
                        obstacle_id=obstacle.obstacle_id,
                        other_entity_id=None,
                        time_fraction=fraction,
                        position_m=contact,
                        normal=_obstacle_normal(obstacle, contact, entity.radius_m),
                        absolute_time_seconds=self._absolute_time(
                            tick, segment.dt_seconds, fraction
                        ),
                    )
                )
        return collisions

    def _broadphase_candidates(
        self, motions: Mapping[str, MotionSegmentV2]
    ) -> tuple[tuple[str, str], ...]:
        swept: list[tuple[float, str, float, float, float, float, float]] = []
        for entity_id in sorted(motions):
            segment = motions[entity_id]
            radius = self._entities[entity_id].radius_m
            swept.append(
                (
                    min(segment.start_m[0], segment.end_m[0]) - radius,
                    entity_id,
                    max(segment.start_m[0], segment.end_m[0]) + radius,
                    min(segment.start_m[1], segment.end_m[1]) - radius,
                    max(segment.start_m[1], segment.end_m[1]) + radius,
                    min(segment.start_m[2], segment.end_m[2]) - radius,
                    max(segment.start_m[2], segment.end_m[2]) + radius,
                )
            )
        swept.sort(key=lambda item: (item[0], item[1]))
        candidates: list[tuple[str, str]] = []
        for first_index, first in enumerate(swept):
            for second in swept[first_index + 1 :]:
                if second[0] > first[2]:
                    break
                if second[3] > first[4] or first[3] > second[4]:
                    continue
                if second[5] > first[6] or first[5] > second[6]:
                    continue
                candidates.append(
                    (first[1], second[1]) if first[1] < second[1] else (second[1], first[1])
                )
        return tuple(sorted(set(candidates)))

    @staticmethod
    def _bruteforce_candidates(
        motions: Mapping[str, MotionSegmentV2],
    ) -> tuple[tuple[str, str], ...]:
        entity_ids = tuple(sorted(motions))
        return tuple(
            (first_id, second_id)
            for first_index, first_id in enumerate(entity_ids)
            for second_id in entity_ids[first_index + 1 :]
        )

    def _narrowphase_pair(
        self,
        first_id: str,
        second_id: str,
        motions: Mapping[str, MotionSegmentV2],
        tick: int,
    ) -> CollisionEventV2 | None:
        first_entity = self._entities[first_id]
        second_entity = self._entities[second_id]
        first = motions[first_id]
        second = motions[second_id]
        if first_entity.shape is None or second_entity.shape is None:
            raise ValueError("collision entity is missing a shape")
        hit = ShapeNarrowphaseOracleV2(tolerance_m=0.0).sweep(
            first_entity.shape,
            start_a=first.start_m,
            end_a=first.end_m,
            shape_b=second_entity.shape,
            start_b=second.start_m,
            end_b=second.end_m,
        )
        if hit is None:
            return None
        fraction = hit.time_fraction
        first_position = _position(first, fraction)
        second_position = _position(second, fraction)
        midpoint = cast(
            Vector3V2,
            tuple((first_position[index] + second_position[index]) / 2.0 for index in range(3)),
        )
        relative_contact = cast(
            Vector3V2,
            tuple(first_position[index] - second_position[index] for index in range(3)),
        )
        if math.sqrt(sum(value * value for value in relative_contact)) <= 1e-15:
            relative_contact = (-1.0, 0.0, 0.0)
        return CollisionEventV2(
            event_id=f"collision:{tick}:{first_id}:entity:{second_id}",
            tick=tick,
            entity_id=first_id,
            obstacle_id=None,
            other_entity_id=second_id,
            time_fraction=fraction,
            position_m=midpoint,
            normal=_unit_vector(relative_contact, name="collision_normal"),
            entity_a_id=first_id,
            entity_b_id=second_id,
            absolute_time_seconds=self._absolute_time(tick, first.dt_seconds, fraction),
        )

    def _entity_collisions(
        self,
        motions: Mapping[str, MotionSegmentV2],
        tick: int,
        candidates: Sequence[tuple[str, str]],
    ) -> list[CollisionEventV2]:
        collisions: list[CollisionEventV2] = []
        for first_id, second_id in candidates:
            event = self._narrowphase_pair(first_id, second_id, motions, tick)
            if event is not None:
                collisions.append(event)
        return collisions

    def _absolute_time(self, tick: int, dt_seconds: float, fraction: float) -> float:
        if self._tick_start_time_seconds is not None:
            return self._tick_start_time_seconds + fraction * dt_seconds
        origin = tick if self._origin_tick is None else self._origin_tick
        return max(0, tick - origin) * dt_seconds + fraction * dt_seconds

    def evaluate(
        self,
        motions: Mapping[str, MotionSegmentV2],
        *,
        tick: int,
        tick_start_time_seconds: float | None = None,
        emit_damage_intents: bool | None = None,
    ) -> BoundaryEvaluationV2:
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if not isinstance(motions, Mapping):
            raise TypeError("motions must be a mapping")
        if tick_start_time_seconds is None:
            raise _boundary_error(
                "boundary.tick_start_time_required",
                ("tick_start_time_seconds",),
                None,
                "v2 boundary evaluation requires an authoritative explicit tick start",
                "pass the World spatial clock tick_start_time_seconds",
            )
        start_time = _finite_number(tick_start_time_seconds, name="tick_start_time_seconds")
        if start_time < 0.0:
            raise ValueError("tick_start_time_seconds cannot be negative")
        self._tick_start_time_seconds = start_time
        damage_intents_enabled = (
            self._emit_damage_intents if emit_damage_intents is None else emit_damage_intents
        )
        if not isinstance(damage_intents_enabled, bool):
            raise TypeError("emit_damage_intents must be boolean")
        if self._origin_tick is None:
            self._origin_tick = tick
        staged: dict[str, MotionSegmentV2] = {}
        for entity_id, segment in motions.items():
            if entity_id not in self._entities:
                raise ValueError(f"motion references unregistered entity: {entity_id}")
            if not isinstance(segment, MotionSegmentV2):
                raise TypeError("motion values must be MotionSegmentV2")
            staged[entity_id] = segment
        boundary_events: list[BoundaryEventV2] = []
        collision_events: list[CollisionEventV2] = []
        for entity_id in sorted(staged):
            entity = self._entities[entity_id]
            segment = staged[entity_id]
            boundary_events.extend(self._boundary_events(entity, segment, tick))
            static_collisions = self._static_collisions(entity, segment, tick)
            collision_events.extend(static_collisions)
            obstacle_index = {item.obstacle_id: item for item in self._obstacles}
            for collision in static_collisions:
                if collision.obstacle_id is None:
                    raise ValueError("static collision is missing obstacle identity")
                obstacle = obstacle_index[collision.obstacle_id]
                boundary_events.append(
                    BoundaryEventV2(
                        event_id=(
                            f"boundary-event:{tick}:{entity_id}:obstacle:{obstacle.obstacle_id}"
                        ),
                        tick=tick,
                        entity_id=entity_id,
                        kind="obstacle",
                        boundary_id=obstacle.obstacle_id,
                        time_fraction=collision.time_fraction,
                        position_m=collision.position_m,
                        normal=collision.normal,
                        priority=obstacle.priority,
                        absolute_time_seconds=self._absolute_time(
                            tick, segment.dt_seconds, collision.time_fraction
                        ),
                    )
                )
        if self._enable_entity_collisions:
            candidates = self._broadphase_candidates(staged)
            collision_events.extend(self._entity_collisions(staged, tick, candidates))
        boundary_events.sort(
            key=lambda item: (
                item.entity_id,
                {
                    "world_exit": 0,
                    "altitude_max": 1,
                    "depth_max": 2,
                    "allowed_zone": 3,
                    "excluded_zone": 4,
                    "obstacle": 5,
                }[item.kind],
                -item.priority,
                item.boundary_id,
                item.time_fraction,
            )
        )
        collision_events.sort(
            key=lambda item: (
                item.entity_a_id,
                item.entity_b_id,
                item.obstacle_id or "",
                item.time_fraction,
            )
        )
        actions: list[BoundaryPolicyActionV2] = []
        intents: list[DamageIntentV2] = []
        lifecycle_intents: list[DeactivateIntentV2 | MissionEventIntentV2] = []
        causes: list[
            tuple[
                str,
                str,
                MotionSegmentV2,
                float,
                Vector3V2,
                BoundaryPolicyV2,
                bool,
                int,
                str,
                str | None,
            ]
        ] = []
        causes.extend(
            (
                event.event_id,
                event.entity_id,
                staged[event.entity_id],
                event.time_fraction,
                event.normal,
                self._zone_policies.get(event.boundary_id, self._policy),
                event.kind == "excluded_zone",
                event.priority,
                event.boundary_id,
                None,
            )
            for event in boundary_events
        )
        causes.extend(
            (
                event.event_id,
                event.entity_id,
                staged[event.entity_id],
                event.time_fraction,
                event.normal,
                self._policy,
                False,
                self._policy.priority,
                event.event_id,
                event.other_entity_id,
            )
            for event in collision_events
            if event.other_entity_id is not None
        )
        causes.extend(
            (
                event.event_id,
                event.other_entity_id,
                staged[event.other_entity_id],
                event.time_fraction,
                cast(Vector3V2, tuple(-axis for axis in event.normal)),
                self._policy,
                False,
                self._policy.priority,
                event.event_id,
                event.entity_id,
            )
            for event in collision_events
            if event.other_entity_id is not None
        )
        winners: dict[
            str,
            tuple[
                str,
                str,
                MotionSegmentV2,
                float,
                Vector3V2,
                BoundaryPolicyV2,
                bool,
                int,
                str,
                str | None,
            ],
        ] = {}
        for cause in causes:
            current = winners.get(cause[1])
            if current is None or (-cause[7], cause[8]) < (-current[7], current[8]):
                winners[cause[1]] = cause
        causes = [winners[entity_id] for entity_id in sorted(winners)]
        for index, (
            event_id,
            entity_id,
            segment,
            fraction,
            normal,
            policy,
            entering_excluded,
            _priority,
            _tie_id,
            collision_source_id,
        ) in enumerate(causes):
            impact = _position(segment, fraction)
            if segment.velocity_mps is None:
                raise ValueError("motion segment is missing resolved velocity")
            velocity = segment.velocity_mps
            impact_damage_evidence: ImpactDamageEvidenceV2 | None = None
            if self._impact_damage_policy is not None and (
                collision_source_id is not None or policy.policy == "effect"
            ):
                source_segment = (
                    staged.get(collision_source_id) if collision_source_id is not None else None
                )
                source_velocity = (
                    (0.0, 0.0, 0.0)
                    if source_segment is None or source_segment.velocity_mps is None
                    else source_segment.velocity_mps
                )
                pre_impact_relative_velocity_mps = cast(
                    Vector3V2,
                    tuple(velocity[axis] - source_velocity[axis] for axis in range(3)),
                )
                target_mass_kg = self._entities[entity_id].mass_kg
                source_mass_kg = (
                    target_mass_kg
                    if collision_source_id is None
                    else self._entities[collision_source_id].mass_kg
                )
                magnitude = ImpactMagnitudeModelV2.evaluate(
                    model=self._impact_damage_policy.magnitude_model,
                    parameters=self._impact_damage_policy.magnitude_parameters,
                    relative_velocity_mps=pre_impact_relative_velocity_mps,
                    source_mass_kg=source_mass_kg,
                    target_mass_kg=target_mass_kg,
                    output_unit=self._impact_damage_policy.output_unit,
                )
                impact_damage_evidence = ImpactDamageEvidenceV2.create(
                    effect_ref=self._impact_damage_policy.effect_binding.exact_ref,
                    damage_model_ref=self._impact_damage_policy.damage_binding.exact_ref,
                    magnitude_model=self._impact_damage_policy.magnitude_model,
                    magnitude_parameters=self._impact_damage_policy.magnitude_parameters,
                    output_unit=self._impact_damage_policy.output_unit,
                    pre_impact_relative_velocity_mps=pre_impact_relative_velocity_mps,
                    source_mass_kg=source_mass_kg,
                    target_mass_kg=target_mass_kg,
                    time_fraction=fraction,
                    magnitude=magnitude,
                )
            resolved_end = segment.end_m
            resolved_velocity = velocity
            normal_component = sum(velocity[axis] * normal[axis] for axis in range(3))
            if policy.policy == "reject":
                resolved_end = segment.start_m
            elif policy.policy in {"stop", "effect"}:
                resolved_end = impact
                resolved_velocity = (0.0, 0.0, 0.0)
            elif policy.policy == "constrain":
                resolved_end = impact
                constrained_component = (
                    min(0.0, normal_component) if entering_excluded else max(0.0, normal_component)
                )
                resolved_velocity = cast(
                    Vector3V2,
                    tuple(
                        velocity[axis] - constrained_component * normal[axis] for axis in range(3)
                    ),
                )
            elif policy.policy == "reflect":
                resolved_end = impact
                resolved_velocity = cast(
                    Vector3V2,
                    tuple(
                        velocity[axis] - 2.0 * normal_component * normal[axis] for axis in range(3)
                    ),
                )
            action_id = f"boundary-action:{tick}:{entity_id}:{index}:{policy.policy}"
            actions.append(
                BoundaryPolicyActionV2(
                    action_id=action_id,
                    tick=tick,
                    entity_id=entity_id,
                    policy=policy.policy,
                    cause_event_id=event_id,
                    candidate_end_m=segment.end_m,
                    resolved_end_m=resolved_end,
                    boundary_normal=normal,
                    resolved_velocity_mps=resolved_velocity,
                    contact_position_m=impact,
                )
            )
            if collision_source_id is not None and damage_intents_enabled:
                evidence_parameters = (
                    {"cause_event_id": event_id, "time_fraction": fraction}
                    if impact_damage_evidence is None
                    else {
                        "cause_event_id": event_id,
                        "time_fraction": fraction,
                        "impact_damage_evidence": _plain(impact_damage_evidence),
                    }
                )
                intents.append(
                    DamageIntentV2(
                        schema_version="2.0",
                        intent_id=f"damage:{tick}:{entity_id}:{index}:collision",
                        tick=tick,
                        source_entity_id=collision_source_id,
                        target_entity_id=entity_id,
                        effect_ref=(
                            policy.effect_ref
                            if impact_damage_evidence is None
                            else impact_damage_evidence.effect_ref
                        ),
                        damage_model_ref=(
                            None
                            if impact_damage_evidence is None
                            else impact_damage_evidence.damage_model_ref
                        ),
                        magnitude=(
                            None
                            if impact_damage_evidence is None
                            else impact_damage_evidence.magnitude
                        ),
                        evidence_hash=(
                            None
                            if impact_damage_evidence is None
                            else impact_damage_evidence.evidence_hash
                        ),
                        source_kind=(None if impact_damage_evidence is None else "collision"),
                        parameters=evidence_parameters,
                    )
                )
            elif policy.policy == "effect" and damage_intents_enabled:
                evidence_parameters = (
                    {"cause_event_id": event_id, "time_fraction": fraction}
                    if impact_damage_evidence is None
                    else {
                        "cause_event_id": event_id,
                        "time_fraction": fraction,
                        "impact_damage_evidence": _plain(impact_damage_evidence),
                    }
                )
                intents.append(
                    DamageIntentV2(
                        schema_version="2.0",
                        intent_id=f"damage:{tick}:{entity_id}:{index}:boundary",
                        tick=tick,
                        source_entity_id="boundary-system",
                        target_entity_id=entity_id,
                        effect_ref=(
                            policy.effect_ref
                            if impact_damage_evidence is None
                            else impact_damage_evidence.effect_ref
                        ),
                        damage_model_ref=(
                            None
                            if impact_damage_evidence is None
                            else impact_damage_evidence.damage_model_ref
                        ),
                        magnitude=(
                            None
                            if impact_damage_evidence is None
                            else impact_damage_evidence.magnitude
                        ),
                        evidence_hash=(
                            None
                            if impact_damage_evidence is None
                            else impact_damage_evidence.evidence_hash
                        ),
                        source_kind=(None if impact_damage_evidence is None else "environment"),
                        parameters=evidence_parameters,
                    )
                )
            elif policy.policy == "deactivate":
                lifecycle_intents.append(
                    DeactivateIntentV2(
                        intent_id=f"deactivate:{tick}:{entity_id}:{index}",
                        tick=tick,
                        entity_id=entity_id,
                        cause_event_id=event_id,
                    )
                )
            elif policy.policy == "mission_event":
                lifecycle_intents.append(
                    MissionEventIntentV2(
                        intent_id=f"mission-event:{tick}:{entity_id}:{index}",
                        tick=tick,
                        entity_id=entity_id,
                        cause_event_id=event_id,
                    )
                )
        return BoundaryEvaluationV2(
            tick=tick,
            boundary_events=tuple(boundary_events),
            collision_events=tuple(collision_events),
            damage_intents=tuple(intents),
            policy_actions=tuple(actions),
            lifecycle_intents=tuple(lifecycle_intents),
        )

    def evaluate_bruteforce(
        self,
        motions: Mapping[str, MotionSegmentV2],
        *,
        tick: int,
        tick_start_time_seconds: float | None = None,
    ) -> BoundaryEvaluationV2:
        """Independent all-pairs oracle sharing only the exact narrow phase."""

        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if tick_start_time_seconds is None:
            raise _boundary_error(
                "boundary.tick_start_time_required",
                ("tick_start_time_seconds",),
                None,
                "v2 boundary evaluation requires an authoritative explicit tick start",
                "pass the World spatial clock tick_start_time_seconds",
            )
        self._tick_start_time_seconds = _finite_number(
            tick_start_time_seconds, name="tick_start_time_seconds"
        )
        staged: dict[str, MotionSegmentV2] = {}
        for entity_id, segment in motions.items():
            if entity_id not in self._entities:
                raise ValueError(f"motion references unregistered entity: {entity_id}")
            if not isinstance(segment, MotionSegmentV2):
                raise TypeError("motion values must be MotionSegmentV2")
            staged[entity_id] = segment
        candidates = self._bruteforce_candidates(staged)
        collisions = self._entity_collisions(staged, tick, candidates)
        collisions.sort(
            key=lambda item: (
                item.entity_a_id,
                item.entity_b_id,
                item.obstacle_id or "",
                item.time_fraction,
            )
        )
        return BoundaryEvaluationV2(tick=tick, collision_events=tuple(collisions))


def _sphere_sweep_fraction(
    relative_start: Vector3V2,
    relative_end: Vector3V2,
    radius: float,
    tolerance: float,
) -> float | None:
    delta = tuple(relative_end[index] - relative_start[index] for index in range(3))
    expanded = radius + tolerance
    constant = sum(axis * axis for axis in relative_start) - expanded * expanded
    if constant <= 0.0:
        return 0.0
    quadratic = sum(axis * axis for axis in delta)
    if quadratic == 0.0:
        return None
    linear = 2.0 * sum(relative_start[index] * delta[index] for index in range(3))
    discriminant = linear * linear - 4.0 * quadratic * constant
    if discriminant < -tolerance:
        return None
    root = math.sqrt(max(0.0, discriminant))
    candidates = tuple(
        fraction
        for fraction in (
            (-linear - root) / (2.0 * quadratic),
            (-linear + root) / (2.0 * quadratic),
        )
        if -tolerance <= fraction <= 1.0 + tolerance
    )
    return min(1.0, max(0.0, min(candidates))) if candidates else None


def _shape_polygon(shape: CollisionShapeV2) -> tuple[tuple[float, float], ...]:
    if shape.shape == "polygon_footprint":
        return shape.vertices_m
    if shape.shape in {"aabb", "obb"}:
        half_x, half_y = shape.half_extents_m[:2]
        yaw = math.radians(shape.yaw_degrees if shape.shape == "obb" else 0.0)
    elif shape.shape == "capsule":
        physical_radius = (
            shape.radius_m if shape.axis == "z" else shape.radius_m - shape.half_length_m
        )
        half_x = physical_radius + (shape.half_length_m if shape.axis == "x" else 0.0)
        half_y = physical_radius + (shape.half_length_m if shape.axis == "y" else 0.0)
        yaw = 0.0
    else:
        half_x = half_y = shape.radius_m
        yaw = 0.0
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    return tuple(
        (
            x * cosine - y * sine,
            x * sine + y * cosine,
        )
        for x, y in (
            (-half_x, -half_y),
            (half_x, -half_y),
            (half_x, half_y),
            (-half_x, half_y),
        )
    )


def _linear_interval(
    start: float, end: float, lower: float, upper: float
) -> tuple[float, float] | None:
    delta = end - start
    if delta == 0.0:
        return (0.0, 1.0) if lower <= start <= upper else None
    first = (lower - start) / delta
    second = (upper - start) / delta
    entry = max(0.0, min(first, second))
    exit_fraction = min(1.0, max(first, second))
    return (entry, exit_fraction) if entry <= exit_fraction else None


__all__ = [
    "AllowedZoneV2",
    "BoundaryEntityV2",
    "BoundaryErrorV2",
    "BoundaryEvaluationV2",
    "BoundaryEventV2",
    "BoundaryKindV2",
    "BoundaryPolicyActionV2",
    "BoundaryPolicyNameV2",
    "BoundaryPolicyV2",
    "BoundarySystemV2",
    "CollisionShapeV2",
    "CollisionEventV2",
    "DamageIntentV2",
    "DeactivateIntentV2",
    "ImpactDamageEvidenceV2",
    "ImpactMagnitudeModelV2",
    "MissionEventIntentV2",
    "MotionSegmentV2",
    "ShapeNarrowphaseOracleV2",
    "ShapeSweepHitV2",
    "StaticObstacleV2",
    "ZoneActivationReceiptV2",
    "ZoneActivationSnapshotV2",
]

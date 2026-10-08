"""Verified, data-driven terrain polygons for formal V2 map resources.

This module deliberately contains no scenario identifiers.  A map Catalog resource
may opt into an immutable terrain source and the compiler can materialise its land
polygons into the resolved world without making the runtime depend on a Catalog.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EARTH_RADIUS_M = 6_378_137.0


class MapTerrainErrorV2(ValueError):
    """Raised when a map's declared terrain source is not authoritative."""


@dataclass(frozen=True, slots=True)
class MapTerrainV2:
    """A checked, canonical local-metre terrain layer from one map resource."""

    origin_wgs84: tuple[float, float, float]
    bounds_m: tuple[tuple[float, float, float], tuple[float, float, float]]
    source_hash: str
    land_polygons_m: tuple[tuple[tuple[float, float], ...], ...]


def _number(value: object, *, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise MapTerrainErrorV2(f"{name} must be a finite number")
    return float(value)


def _vector3(value: object, *, name: str) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise MapTerrainErrorV2(f"{name} must contain three finite coordinates")
    return tuple(_number(item, name=name) for item in value)  # type: ignore[return-value]


def _source_file(source: Mapping[str, object]) -> tuple[bytes, str]:
    relative = source.get("path")
    expected = source.get("sha256")
    if not isinstance(relative, str) or not relative or not isinstance(expected, str):
        raise MapTerrainErrorV2("terrain source identity is incomplete")
    path = (_ROOT / relative).resolve()
    if _ROOT not in path.parents or path.is_symlink() or not path.is_file():
        raise MapTerrainErrorV2("terrain source is outside the repository authority")
    raw = path.read_bytes()
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise MapTerrainErrorV2("terrain source hash mismatch")
    return raw, actual


def _project_wgs84(
    point: Sequence[object], *, origin: tuple[float, float, float]
) -> tuple[float, float]:
    if len(point) < 2:
        raise MapTerrainErrorV2("terrain coordinate must contain longitude and latitude")
    longitude = _number(point[0], name="terrain longitude")
    latitude = _number(point[1], name="terrain latitude")
    if not -180.0 <= longitude <= 180.0 or not -90.0 <= latitude <= 90.0:
        raise MapTerrainErrorV2("terrain coordinate is outside WGS84 bounds")
    longitude_delta = (longitude - origin[0] + 180.0) % 360.0 - 180.0
    return (
        math.radians(longitude_delta) * _EARTH_RADIUS_M * math.cos(math.radians(origin[1])),
        math.radians(latitude - origin[1]) * _EARTH_RADIUS_M,
    )


def _canonical_ring(
    points: Sequence[tuple[float, float]], *, index: int
) -> tuple[tuple[float, float], ...]:
    """Remove source-export noise while rejecting retracing polygon edges."""

    ring = list(dict.fromkeys(points))
    if len(ring) < 3:
        raise MapTerrainErrorV2("terrain polygon is degenerate")
    changed = True
    while changed and len(ring) >= 3:
        changed = False
        for position, current in enumerate(ring):
            previous = ring[position - 1]
            following = ring[(position + 1) % len(ring)]
            incoming = (current[0] - previous[0], current[1] - previous[1])
            outgoing = (following[0] - current[0], following[1] - current[1])
            cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            if abs(cross) > 1e-9:
                continue
            if incoming[0] * outgoing[0] + incoming[1] * outgoing[1] < 0.0:
                ring.pop(position)
                changed = True
                break
            raise MapTerrainErrorV2(f"terrain polygon {index} retraces an edge")
    if len(ring) < 3:
        raise MapTerrainErrorV2("terrain polygon is degenerate")
    return tuple(ring)


def load_map_terrain_v2(content: Mapping[str, object]) -> MapTerrainV2 | None:
    """Load a map's declared terrain source, or ``None`` when it has none.

    The controlled ``raw-polygon-list-wgs84@1.0`` format is intentionally small:
    a JSON list of WGS84 polygon rings, selected by explicit indexes.  It is a map
    resource contract, not a task-scenario adapter.
    """

    source = content.get("terrain_source")
    if source is None:
        return None
    if not isinstance(source, Mapping):
        raise MapTerrainErrorV2("terrain_source must be a mapping")
    if source.get("format") != "raw-polygon-list-wgs84@1.0":
        raise MapTerrainErrorV2("terrain source format is unsupported")
    origin = _vector3(content.get("origin_wgs84"), name="origin_wgs84")
    if not -180.0 <= origin[0] <= 180.0 or not -90.0 <= origin[1] <= 90.0:
        raise MapTerrainErrorV2("map origin is outside WGS84 bounds")
    bounds_value = content.get("bounds_m")
    if (
        not isinstance(bounds_value, Sequence)
        or isinstance(bounds_value, (str, bytes))
        or len(bounds_value) != 2
    ):
        raise MapTerrainErrorV2("bounds_m must contain lower and upper 3D bounds")
    lower = _vector3(bounds_value[0], name="bounds_m.lower")
    upper = _vector3(bounds_value[1], name="bounds_m.upper")
    if any(lower[index] >= upper[index] for index in range(3)):
        raise MapTerrainErrorV2("map bounds must be strictly ordered")
    raw, source_hash = _source_file(source)
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise MapTerrainErrorV2("terrain source is not valid JSON") from error
    if not isinstance(document, list) or any(not isinstance(item, list) for item in document):
        raise MapTerrainErrorV2("terrain source geometry must be a list of polygon rings")
    polygon_indices = source.get("polygon_indices", ())
    closed_range = source.get("closed_polygon_range", (0, 0))
    if (
        not isinstance(polygon_indices, Sequence)
        or isinstance(polygon_indices, (str, bytes))
        or not isinstance(closed_range, Sequence)
        or isinstance(closed_range, (str, bytes))
        or len(closed_range) != 2
    ):
        raise MapTerrainErrorV2("terrain source polygon indexes are invalid")
    indexes: list[int] = []
    for value in polygon_indices:
        if not isinstance(value, int) or isinstance(value, bool):
            raise MapTerrainErrorV2("terrain polygon index must be an integer")
        indexes.append(value)
    start, end = closed_range
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
    ):
        raise MapTerrainErrorV2("closed terrain polygon range must use integers")
    if not 0 <= start <= end <= len(document) or any(
        not 0 <= item < len(document) for item in indexes
    ):
        raise MapTerrainErrorV2("terrain polygon index is outside source geometry")
    for index in range(start, end):
        ring = document[index]
        if len(ring) >= 4 and ring[0] == ring[-1]:
            indexes.append(index)
    chosen = tuple(dict.fromkeys(indexes))
    if not chosen:
        raise MapTerrainErrorV2("terrain source declares no land polygons")
    polygons: list[tuple[tuple[float, float], ...]] = []
    for index in chosen:
        ring = document[index]
        if len(ring) < 3 or any(
            not isinstance(point, Sequence) or isinstance(point, (str, bytes)) for point in ring
        ):
            raise MapTerrainErrorV2("terrain polygon must contain at least three coordinates")
        projected = tuple(_project_wgs84(point, origin=origin) for point in ring)
        if len(projected) >= 2 and projected[0] == projected[-1]:
            projected = projected[:-1]
        polygons.append(_canonical_ring(projected, index=index))
    return MapTerrainV2(
        origin_wgs84=origin,
        bounds_m=(lower, upper),
        source_hash=source_hash,
        land_polygons_m=tuple(polygons),
    )


__all__ = ["MapTerrainErrorV2", "MapTerrainV2", "load_map_terrain_v2"]

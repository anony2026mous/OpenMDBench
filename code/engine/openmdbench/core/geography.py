"""Authoritative Weihai WGS84, local-metre and legacy-map coordinate frame."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from env.geo_coordinate import GeoConverter
from env.map_loader import apply_coordinate_offset, load_polygon_file
from pyproj import CRS, Transformer

from openmdbench.systems.collision import CollisionBody, collides_with_segments, point_in_polygon


@dataclass(frozen=True, slots=True)
class MapIdentity:
    map_id: str
    version: str
    raw_sha256: str
    xy_sha256: str
    geographic_crs: str
    legacy_projection: str
    origin_lonlat: tuple[float, float]
    legacy_scale: float
    offset_xy: tuple[float, float]


@dataclass(frozen=True, slots=True)
class MapVisualizationLayers:
    """Renderer-safe map geometry with lines and filled regions kept distinct."""

    coastline_lines: tuple[tuple[tuple[float, float], ...], ...]
    land_polygons: tuple[tuple[tuple[float, float], ...], ...]
    mission_regions: tuple[tuple[tuple[float, float], ...], ...]

    def bounds(self, *, padding_fraction: float = 0.03) -> tuple[float, float, float, float]:
        """Return the complete visible-map extent with proportional padding."""
        if padding_fraction < 0.0:
            raise ValueError("map padding fraction cannot be negative")
        points = tuple(
            point for geometry in (*self.coastline_lines, *self.land_polygons) for point in geometry
        )
        if not points:
            raise ValueError("map visualization layers contain no geometry")
        x_values = [point[0] for point in points]
        y_values = [point[1] for point in points]
        min_x, max_x = min(x_values), max(x_values)
        min_y, max_y = min(y_values), max(y_values)
        padding_x = (max_x - min_x) * padding_fraction
        padding_y = (max_y - min_y) * padding_fraction
        return (
            min_x - padding_x,
            min_y - padding_y,
            max_x + padding_x,
            max_y + padding_y,
        )


def _weihai_visualization_layers(
    polygons: tuple[tuple[tuple[float, float], ...], ...],
) -> MapVisualizationLayers:
    """Restore the source-layer order frozen by ``regenerate_map_data.py``.

    The checked-in artifact deliberately preserves the original source order:
    fish region, island, rubbish region, 131 coastline paths, and 3 harbor
    boundary paths.  Most coastline paths are open polylines; treating them as
    filled polygons creates multi-kilometre artificial closing edges.  The
    original script grouped ``hrbare + coaline`` as display-line data, so the
    harbor paths remain lines even though their endpoints repeat.
    """

    fish_index = 0
    island_index = 1
    rubbish_index = 2
    coastline_start = 3
    coastline_end = 134
    harbor_end = 137
    if len(polygons) != harbor_end:
        raise ValueError("weihai_v1 visualization layer contract requires exactly 137 geometries")
    coastlines = polygons[coastline_start:coastline_end]
    harbor_boundaries = polygons[coastline_end:harbor_end]
    closed_coastlines = tuple(path for path in coastlines if len(path) >= 4 and path[0] == path[-1])
    land_polygons = (
        polygons[island_index],
        *closed_coastlines,
    )
    return MapVisualizationLayers(
        coastline_lines=(*coastlines, *harbor_boundaries),
        land_polygons=land_polygons,
        mission_regions=(polygons[fish_index], polygons[rubbish_index]),
    )


class GeoFrame:
    """One validated coordinate authority; local XY is true metre-scale AEQD."""

    def __init__(
        self,
        *,
        identity: MapIdentity,
        raw_polygons: tuple[tuple[tuple[float, float], ...], ...],
    ) -> None:
        if identity.legacy_scale <= 0 or not all(
            math.isfinite(value) for value in (*identity.origin_lonlat, *identity.offset_xy)
        ):
            raise ValueError("GeoFrame scale and coordinates must be finite and scale positive")
        lon, lat = identity.origin_lonlat
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("GeoFrame origin is outside WGS84 bounds")
        self.identity = identity
        local_crs = CRS.from_proj4(
            f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
        )
        self._to_local = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
        self._to_wgs84 = Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True)
        self._legacy = GeoConverter(identity.origin_lonlat, identity.legacy_scale)
        self.raw_polygons = raw_polygons
        self.local_polygons = tuple(
            tuple(self.wgs84_to_local(*point) for point in polygon) for polygon in raw_polygons
        )
        self.visualization_layers = _weihai_visualization_layers(self.local_polygons)
        self.coastline_segments = tuple(
            (polygon[index - 1], polygon[index])
            for polygon in self.local_polygons
            for index in range(1, len(polygon))
            if len(polygon) >= 2
        )

    @staticmethod
    def _point(first: float, second: float) -> tuple[float, float]:
        if not math.isfinite(first) or not math.isfinite(second):
            raise ValueError("coordinate values must be finite")
        return float(first), float(second)

    def wgs84_to_local(self, lon: float, lat: float) -> tuple[float, float]:
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("longitude or latitude is outside WGS84 bounds")
        return self._point(*self._to_local.transform(lon, lat))

    def local_to_wgs84(self, east_m: float, north_m: float) -> tuple[float, float]:
        self._point(east_m, north_m)
        return self._point(*self._to_wgs84.transform(east_m, north_m))

    def wgs84_to_map(self, lon: float, lat: float) -> tuple[float, float]:
        self.wgs84_to_local(lon, lat)
        x, y = self._legacy.lonlat_to_xy(lon, lat)
        return x + self.identity.offset_xy[0], y + self.identity.offset_xy[1]

    def map_to_wgs84(self, x: float, y: float) -> tuple[float, float]:
        self._point(x, y)
        return self._legacy.xy_to_lonlat(
            x - self.identity.offset_xy[0], y - self.identity.offset_xy[1]
        )

    def local_to_map(self, east_m: float, north_m: float) -> tuple[float, float]:
        return self.wgs84_to_map(*self.local_to_wgs84(east_m, north_m))

    def map_to_local(self, x: float, y: float) -> tuple[float, float]:
        return self.wgs84_to_local(*self.map_to_wgs84(x, y))

    def is_land_wgs84(self, lon: float, lat: float) -> bool:
        point = self._point(lon, lat)
        return any(
            point_in_polygon(point, polygon) for polygon in self.raw_polygons if len(polygon) >= 3
        )

    def is_land_local(self, east_m: float, north_m: float) -> bool:
        return self.is_land_wgs84(*self.local_to_wgs84(east_m, north_m))

    def collides_with_coast(self, body: CollisionBody) -> bool:
        """Apply the checked-in Weihai polygons as a physical surface constraint."""
        return self.is_land_local(*body.position[:2]) or collides_with_segments(
            body, self.coastline_segments
        )

    def metadata(self) -> dict[str, object]:
        identity = self.identity
        return {
            "map_id": identity.map_id,
            "map_version": identity.version,
            "map_raw_sha256": identity.raw_sha256,
            "map_xy_sha256": identity.xy_sha256,
            "geographic_crs": identity.geographic_crs,
            "local_crs": "WGS84_AEQD",
            "legacy_projection": identity.legacy_projection,
            "origin_lonlat": list(identity.origin_lonlat),
            "legacy_scale": identity.legacy_scale,
            "offset_xy": list(identity.offset_xy),
        }


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def load_weihai_geoframe(
    *,
    map_root: str | Path,
    expected_raw_sha256: str,
    expected_xy_sha256: str,
    origin_lonlat: tuple[float, float] = (122.0, 37.4),
    legacy_scale: float = 50.0,
    offset_margin: float = 10.0,
) -> GeoFrame:
    root = Path(map_root)
    raw_path = root / "weihai_raw_lonlat.txt"
    xy_path = root / "weihai_map.txt"
    actual_raw, actual_xy = _sha256(raw_path), _sha256(xy_path)
    if actual_raw != expected_raw_sha256 or actual_xy != expected_xy_sha256:
        raise ValueError("Weihai map hash mismatch")
    raw = load_polygon_file(str(raw_path))
    xy = load_polygon_file(str(xy_path))
    _, offset_x, offset_y = apply_coordinate_offset(xy, margin=offset_margin)
    polygons = tuple(tuple((float(x), float(y)) for x, y in polygon) for polygon in raw)
    return GeoFrame(
        identity=MapIdentity(
            map_id="weihai_v1",
            version="1.0",
            raw_sha256=actual_raw,
            xy_sha256=actual_xy,
            geographic_crs="EPSG:4326",
            legacy_projection="EPSG:3857",
            origin_lonlat=origin_lonlat,
            legacy_scale=legacy_scale,
            offset_xy=(offset_x, offset_y),
        ),
        raw_polygons=polygons,
    )

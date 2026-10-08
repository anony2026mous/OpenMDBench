"""Water/land oracle for the shared Weihai map: is a local-metre point on land?

Why this exists
---------------
The IE set places suicide boats (surface domain) against "protected assets".  An
asset that actually sits **inland** can never be reached by a boat: the boat runs
aground and dies to ``environment`` boundary damage instead of being intercepted.
That silently turns a "surface raid" scenario into a free win for the defender --
measured on IE-03, where blue fired 2 shots and the four boats all died to
boundary damage (``damage_by_kind = {"environment": 129}``, zero weapon damage on
the attacker's losses).

The check is the map's own authoritative land polygons (the same ones the engine
loads), not a hand-drawn approximation.

Usage:
    python _w1_water_probe.py [x y] [x y] ...
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))

MAP_ROOT = ROOT / "env" / "map_data"


def _point_in_polygon(x: float, y: float, polygon) -> bool:
    inside = False
    count = len(polygon)
    for index in range(count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % count]
        if (y1 > y) != (y2 > y):
            cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < cross:
                inside = not inside
    return inside


def build_frame():
    """Local-metre frame for the shared map (mirrors load_weihai_geoframe)."""
    from env.map_loader import apply_coordinate_offset, load_polygon_file

    from openmdbench.core.geography import GeoFrame, MapIdentity

    raw_path = MAP_ROOT / "weihai_raw_lonlat.txt"
    xy_path = MAP_ROOT / "weihai_map.txt"
    raw = load_polygon_file(str(raw_path))
    xy = load_polygon_file(str(xy_path))
    _, offset_x, offset_y = apply_coordinate_offset(xy, margin=10.0)
    polygons = tuple(tuple((float(px), float(py)) for px, py in polygon)
                     for polygon in raw)
    return GeoFrame(
        identity=MapIdentity(
            map_id="weihai_v1",
            version="1.0",
            raw_sha256="probe",
            xy_sha256="probe",
            geographic_crs="EPSG:4326",
            legacy_projection="EPSG:3857",
            origin_lonlat=(122.2, 37.51),
            legacy_scale=50.0,
            offset_xy=(offset_x, offset_y),
        ),
        raw_polygons=polygons,
    )


def main(argv: list[str]) -> int:
    frame = build_frame()
    land_polygons = frame.visualization_layers.land_polygons
    print(f"land polygons: {len(land_polygons)}  "
          f"(local vertex counts: {[len(p) for p in land_polygons][:6]}...)")

    # Import the shared port-asset table from the generator instead of copying
    # the coordinates: a copy silently drifts when the table is edited, which is
    # exactly how the inland "berth" survived several rounds unnoticed.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _gen_ie_set  # noqa: PLC0415
    PORT_ASSETS = _gen_ie_set.PORT_ASSETS

    named = {fid: (float(PORT_ASSETS[fid][1][0]), float(PORT_ASSETS[fid][1][1]))
             for fid in PORT_ASSETS}
    named[_gen_ie_set.SHORE_SITE[0]] = (float(_gen_ie_set.SHORE_SITE[2][0]),
                                       float(_gen_ie_set.SHORE_SITE[2][1]))
    extra = []
    for index in range(0, len(argv) - 1, 2):
        extra.append((f"argv[{index}]", (float(argv[index]), float(argv[index + 1]))))

    print(f"\n{'point':<24}{'x':>10}{'y':>10}   terrain")
    print("-" * 56)
    for name, (x, y) in list(named.items()) + extra:
        on_land = any(_point_in_polygon(x, y, polygon) for polygon in land_polygons)
        print(f"{name:<24}{x:>10.1f}{y:>10.1f}   {'LAND' if on_land else 'WATER'}")

    print("\n说明：设施若为 LAND，则自爆船（surface 域）不可能抵达 —— 只能在岸边搁浅")
    print("      并被 environment 边界毁伤摧毁，该场景的'水面突袭'因此不成立。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

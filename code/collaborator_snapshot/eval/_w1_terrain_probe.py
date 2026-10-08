"""Test candidate land positions against the engine's compiled terrain zones.

The map's terrain lives in a raw lon/lat polygon file, so hand-converting is
error-prone.  Instead this probe compiles a known-good scenario and reads the
resolved world zones: those are already in local metres and are exactly what the
compiler's deployment check uses.

Usage:
    python _w1_terrain_probe.py [PUBLIC_ID]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))

PUBLIC_ID = sys.argv[1] if len(sys.argv) > 1 else "IE-08-ISLAND-STRIKE"

# IE 场景集使用的 land 域点位（保护目标 + 岸基传感器站），以及 MD-AD-006 已知
# 可编译的点位作为对照组。
CANDIDATES = {
    "IE facility.berth": (-800.0, -300.0),
    "IE facility.command": (-1800.0, 100.0),
    "IE facility.fuel": (-1500.0, -700.0),
    "IE facility.pier": (650.0, -1000.0),
    "IE site.shore-radar": (-2600.0, -300.0),
    "md_ad_006.command": (-1200.0, -200.0),
    "md_ad_006.comms": (-800.0, 250.0),
    "md_ad_006.fuel": (-500.0, -900.0),
    "md_ad_006.pier": (700.0, -1000.0),
}


def point_in_polygon(x: float, y: float, points) -> bool:
    inside = False
    count = len(points)
    for index in range(count):
        x1, y1 = float(points[index][0]), float(points[index][1])
        x2, y2 = float(points[(index + 1) % count][0]), float(points[(index + 1) % count][1])
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def zone_rings(zone) -> list:
    """Every polygon ring of a zone, in local metres."""
    geometry = getattr(zone, "geometry", None)
    if geometry is None:
        return []
    if getattr(geometry, "type", None) == "polygon" and getattr(geometry, "positions_m", None):
        return [[(float(p[0]), float(p[1])) for p in geometry.positions_m]]
    return []


def main() -> int:
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2

    resolved, _catalog = compile_formal_scenario_v2(PUBLIC_ID)
    zones = list(resolved.world.zones)
    print(f"compiled {PUBLIC_ID}: {len(zones)} zones")
    print(f"zone attributes: "
          f"{sorted(a for a in dir(zones[0]) if not a.startswith('_'))}\n")

    terrain = []
    for zone in zones:
        rings = zone_rings(zone)
        tags = tuple(str(tag) for tag in getattr(zone, "tags", ()) or ())
        domains = tuple(str(item) for item in getattr(zone, "domains", ()) or ())
        if rings:
            xs = [p[0] for ring in rings for p in ring]
            ys = [p[1] for ring in rings for p in ring]
            print(f"  {zone.id:<28} tags={tags} domains={domains} "
                  f"pts={sum(len(r) for r in rings)} "
                  f"bbox=({min(xs):.0f},{min(ys):.0f})..({max(xs):.0f},{max(ys):.0f})")
            terrain.append((zone.id, tags, rings))
        else:
            center = getattr(getattr(zone, "geometry", None), "center_m", None)
            radius = getattr(getattr(zone, "geometry", None), "radius_m", None)
            print(f"  {zone.id:<28} tags={tags} domains={domains} "
                  f"center={center} radius={radius}")

    print("\nland occupancy over the island bbox (step 250 m; L=land, .=sea):")
    grid_rings = [ring for _zid, _tags, rings in terrain for ring in rings]
    all_x = [p[0] for ring in grid_rings for p in ring]
    all_y = [p[1] for ring in grid_rings for p in ring]
    lo_x, hi_x = min(all_x), max(all_x)
    lo_y, hi_y = min(all_y), max(all_y)
    step = 250.0
    xs = [lo_x + step * i for i in range(int((hi_x - lo_x) / step) + 1)]
    ys = [hi_y - step * i for i in range(int((hi_y - lo_y) / step) + 1)]
    print("        " + "".join("L" if False else " " for _ in xs))
    for y in ys:
        row = f"y={y:>7.0f} "
        for x in xs:
            row += "L" if any(point_in_polygon(x, y, ring) for ring in grid_rings) else "."
        print(row)
    print("        " + "".join(f"{x/1000:.1f}"[-1] for x in xs) + "  (x in km, tens)")

    print("\ncandidate positions:")
    for name, (x, y) in CANDIDATES.items():
        hit = any(point_in_polygon(x, y, ring) for ring in grid_rings)
        print(f"  {name:<22} ({x:>8.0f},{y:>8.0f}) -> {'LAND' if hit else 'SEA '}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

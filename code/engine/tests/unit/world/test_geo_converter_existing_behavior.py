"""Baseline characterization of the legacy Weihai coordinate path for I001-A01."""

import math
from pathlib import Path

import pytest
from env.geo_coordinate import GeoConverter
from env.map_loader import apply_coordinate_offset, load_polygon_file

ROOT = Path(__file__).parents[3]
MAP_ROOT = ROOT / "env/map_data"


def test_default_origin_scale_and_roundtrip_current_behavior() -> None:
    converter = GeoConverter()
    assert converter.origin_lonlat == [122.0, 37.4]
    assert converter.scale == 50.0
    assert converter.lonlat_to_xy(122.0, 37.4) == pytest.approx((0.0, 0.0))
    for lon, lat in ((121.9, 37.3), (122.15, 37.55), (122.0, 37.4)):
        assert converter.xy_to_lonlat(*converter.lonlat_to_xy(lon, lat)) == pytest.approx(
            (lon, lat), abs=1e-10
        )


def test_checked_in_xy_map_matches_raw_lonlat_projection() -> None:
    converter = GeoConverter()
    raw = load_polygon_file(str(MAP_ROOT / "weihai_raw_lonlat.txt"))
    projected = load_polygon_file(str(MAP_ROOT / "weihai_map.txt"))
    assert len(raw) == len(projected) > 0
    assert [len(region) for region in raw] == [len(region) for region in projected]
    samples = ((0, 0), (len(raw) // 2, 0), (len(raw) - 1, -1))
    for region_index, vertex_index in samples:
        lon, lat = raw[region_index][vertex_index]
        assert projected[region_index][vertex_index] == pytest.approx(
            converter.lonlat_to_xy(lon, lat), abs=1e-9
        )


def test_runtime_offset_is_external_to_converter_and_must_be_removed_for_inverse() -> None:
    converter = GeoConverter()
    projected = load_polygon_file(str(MAP_ROOT / "weihai_map.txt"))
    offset_polygons, offset_x, offset_y = apply_coordinate_offset(projected)
    lon, lat = converter.xy_to_lonlat(
        offset_polygons[0][0][0] - offset_x,
        offset_polygons[0][0][1] - offset_y,
    )
    assert (lon, lat) == pytest.approx(
        tuple(load_polygon_file(str(MAP_ROOT / "weihai_raw_lonlat.txt"))[0][0]), abs=1e-10
    )
    assert converter.xy_to_lonlat(*offset_polygons[0][0]) != pytest.approx((lon, lat), abs=1e-5)


def test_current_validation_accepts_negative_scale_but_rejects_zero() -> None:
    with pytest.raises(ValueError, match="scale"):
        GeoConverter(scale=0.0)
    negative = GeoConverter(scale=-50.0)
    assert all(math.isfinite(value) for value in negative.lonlat_to_xy(122.1, 37.5))

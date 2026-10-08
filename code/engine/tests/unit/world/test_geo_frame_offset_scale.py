import pytest
from openmdbench.core.geography import GeoFrame, MapIdentity


def test_offset_is_symmetric(weihai_frame: GeoFrame) -> None:
    point = (122.3, 37.43)
    mapped = weihai_frame.wgs84_to_map(*point)
    assert mapped == pytest.approx((1086.088337, 1072.709910), abs=1e-6)
    assert weihai_frame.map_to_wgs84(*mapped) == pytest.approx(point, abs=1e-7)


def test_invalid_scale_is_rejected(weihai_frame: GeoFrame) -> None:
    identity = weihai_frame.identity
    invalid = MapIdentity(
        identity.map_id,
        identity.version,
        identity.raw_sha256,
        identity.xy_sha256,
        identity.geographic_crs,
        identity.legacy_projection,
        identity.origin_lonlat,
        -1.0,
        identity.offset_xy,
    )
    with pytest.raises(ValueError, match="scale"):
        GeoFrame(identity=invalid, raw_polygons=weihai_frame.raw_polygons)

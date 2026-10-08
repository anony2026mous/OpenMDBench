"""Phase-A coordinate baseline before the runtime GeoFrame is added in B00."""

import pytest
from env.geo_coordinate import GeoConverter


def test_existing_weihai_projection_roundtrips_site_control_point() -> None:
    converter = GeoConverter(origin_lonlat=(122.0, 37.4), scale=50.0)
    site = (122.3, 37.43)
    assert converter.xy_to_lonlat(*converter.lonlat_to_xy(*site)) == pytest.approx(site, abs=1e-10)

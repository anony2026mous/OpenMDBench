import math

from openmdbench.core.geography import GeoFrame
from pyproj import Geod


def test_local_metre_distance_matches_geodesic_within_half_percent(
    weihai_frame: GeoFrame,
) -> None:
    geod = Geod(ellps="WGS84")
    pairs = (
        ((122.3, 37.43), (122.5824597408, 37.4296625329)),
        ((122.3, 37.43), (122.34893827, 37.45251525)),
    )
    for first, second in pairs:
        geodesic = float(geod.inv(*first, *second)[2])
        local_first = weihai_frame.wgs84_to_local(*first)
        local_second = weihai_frame.wgs84_to_local(*second)
        local = math.dist(local_first, local_second)
        assert abs(local - geodesic) / geodesic <= 0.005

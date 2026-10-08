import pytest
from openmdbench.core.entities import Domain
from openmdbench.core.geography import GeoFrame
from openmdbench.systems.collision import CollisionBody


def test_frozen_land_and_water_points_align_in_both_frames(weihai_frame: GeoFrame) -> None:
    radar = (122.2120311548796, 37.49576800052897)
    usv = (122.23748475625334, 37.49894776615413)
    assert weihai_frame.is_land_wgs84(*radar)
    assert not weihai_frame.is_land_wgs84(*usv)
    assert weihai_frame.map_to_wgs84(*weihai_frame.wgs84_to_map(*radar)) == pytest.approx(
        radar, abs=1e-12
    )
    radar_local = weihai_frame.wgs84_to_local(*radar)
    usv_local = weihai_frame.wgs84_to_local(*usv)
    assert weihai_frame.collides_with_coast(
        CollisionBody("on-land", Domain.SURFACE, (*radar_local, 0.0), 8.0, 1.2)
    )
    assert not weihai_frame.collides_with_coast(
        CollisionBody("in-water", Domain.SURFACE, (*usv_local, 0.0), 8.0, 1.2)
    )


def test_weihai_visualization_preserves_open_coastline_semantics(
    weihai_frame: GeoFrame,
) -> None:
    layers = weihai_frame.visualization_layers
    assert len(layers.coastline_lines) == 134
    assert len(layers.land_polygons) == 22
    assert len(layers.mission_regions) == 2
    assert sum(line[0] != line[-1] for line in layers.coastline_lines) == 110

    # Source coastline 130 has endpoints more than 12 km apart.  It must stay
    # an open line instead of becoming a large artificial filled polygon.
    longest_open_coastline = weihai_frame.local_polygons[133]
    assert longest_open_coastline in layers.coastline_lines
    assert longest_open_coastline not in layers.land_polygons

    # The three hrbare records are harbor display boundaries, not land fills;
    # otherwise the largest one visually swallows Liugong Island and the water
    # separating it from the mainland.
    for harbor_boundary in weihai_frame.local_polygons[134:137]:
        assert harbor_boundary in layers.coastline_lines
        assert harbor_boundary not in layers.land_polygons

    min_x, min_y, max_x, max_y = layers.bounds(padding_fraction=0.0)
    assert max_x - min_x > 78_000.0
    assert max_y - min_y > 58_000.0


def test_physical_coastline_does_not_close_open_source_paths(
    weihai_frame: GeoFrame,
) -> None:
    open_path = weihai_frame.local_polygons[133]
    assert open_path[0] != open_path[-1]
    assert (open_path[-1], open_path[0]) not in weihai_frame.coastline_segments
    assert all(
        (open_path[index - 1], open_path[index]) in weihai_frame.coastline_segments
        for index in range(1, len(open_path))
    )

from pathlib import Path

import pytest
from openmdbench.core.geography import GeoFrame, load_weihai_geoframe


def test_wgs_local_and_map_roundtrips(weihai_frame: GeoFrame) -> None:
    for point in ((122.0, 37.4), (122.3, 37.43), (122.5824597408, 37.4296625329)):
        local = weihai_frame.wgs84_to_local(*point)
        assert weihai_frame.local_to_wgs84(*local) == pytest.approx(point, abs=1e-7)
        mapped = weihai_frame.wgs84_to_map(*point)
        assert weihai_frame.map_to_wgs84(*mapped) == pytest.approx(point, abs=1e-7)
        assert weihai_frame.map_to_local(*weihai_frame.local_to_map(*local)) == pytest.approx(
            local, abs=1e-3
        )


@pytest.mark.parametrize("point", ((float("nan"), 0.0), (float("inf"), 0.0)))
def test_nonfinite_coordinates_are_rejected(
    weihai_frame: GeoFrame, point: tuple[float, float]
) -> None:
    with pytest.raises(ValueError, match="finite|bounds"):
        weihai_frame.wgs84_to_local(*point)


def test_map_hash_mismatch_fails_without_fallback(tmp_path: Path) -> None:
    (tmp_path / "weihai_raw_lonlat.txt").write_text("[]")
    (tmp_path / "weihai_map.txt").write_text("[]")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_weihai_geoframe(
            map_root=tmp_path,
            expected_raw_sha256="sha256:wrong",
            expected_xy_sha256="sha256:wrong",
        )

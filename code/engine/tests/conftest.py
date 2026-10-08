from pathlib import Path

import pytest
from openmdbench.core.geography import GeoFrame, load_weihai_geoframe


@pytest.fixture
def weihai_frame() -> GeoFrame:
    root = Path(__file__).parents[1] / "env/map_data"
    return load_weihai_geoframe(
        map_root=root,
        expected_raw_sha256="sha256:1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675",
        expected_xy_sha256="sha256:6b62aa3d3434a8de27f11bdb22627c42c1d5b930c835cfbf77ce37465a00c067",
    )

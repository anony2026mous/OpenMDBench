"""USV MMG dimension and north-facing hull-path tests."""

import numpy as np
import pytest
from env.calibrated_vessels import kvlcc2_l64
from openmdbench.domains.surface import usv_geometry_from_mmg, usv_path
from openmdbench.schemas.geometry import CollisionShape


def test_usv_collision_and_render_dimensions_come_from_mmg() -> None:
    presentation = usv_geometry_from_mmg(kvlcc2_l64)
    assert presentation.geometry.length_m == pytest.approx(kvlcc2_l64["Lpp"])
    assert presentation.geometry.width_m == pytest.approx(kvlcc2_l64["B"])
    assert presentation.geometry.collision_shape is CollisionShape.CAPSULE


def test_usv_path_is_centered_and_bow_points_north() -> None:
    vertices = np.asarray(usv_path().vertices, dtype=np.float64)[:-1]
    bounds_min = vertices.min(axis=0)
    bounds_max = vertices.max(axis=0)
    np.testing.assert_allclose((bounds_min + bounds_max) / 2.0, [0.0, 0.0])
    bow = vertices[np.argmax(vertices[:, 1])]
    np.testing.assert_allclose(bow, [0.0, 0.5])
    assert np.count_nonzero(vertices[:, 0] == 0.0) == 1

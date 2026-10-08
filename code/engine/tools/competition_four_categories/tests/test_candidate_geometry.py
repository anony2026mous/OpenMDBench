from copy import deepcopy
import itertools
import math

import pytest

from tools.competition_four_categories.build import candidate_catalog
from tools.competition_four_categories.candidate_geometry import enclosing_sphere, SURFACE_SHAPE_REF, SITE_SHAPE_REF


@pytest.mark.parametrize("original,proxy", [("shape.picket-usv", SURFACE_SHAPE_REF), ("shape.fixed-site", SITE_SHAPE_REF)])
def test_candidate_sphere_encloses_every_original_box_corner(original, proxy):
    resources = candidate_catalog()["resources"]
    source = next(r for r in resources if r["id"] == original and r["version"] == "2.0.0")
    old = deepcopy(source)
    result = enclosing_sphere(source, proxy)
    assert source == old
    radius = result["content"]["radius_m"]
    for signs in itertools.product((-1, 1), repeat=3):
        corner = [a*b for a,b in zip(signs, source["content"]["half_extents_m"])]
        assert math.sqrt(sum(x*x for x in corner)) <= radius
    assert result["content"]["shape"] == "sphere"
    assert "half_extents_m" not in result["content"]
    assert result["content"]["compatible_domains"] == source["content"]["compatible_domains"]


def test_proxy_rejects_invalid_extents_instead_of_inventing_a_small_radius():
    with pytest.raises(ValueError):
        enclosing_sphere({"content": {"shape": "obb", "half_extents_m": [5., 0., 1.]}}, "shape.test@1.0.0")

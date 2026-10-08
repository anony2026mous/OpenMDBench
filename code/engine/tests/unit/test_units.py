"""Tests for centralized heading and angle conversions."""

import math

import pytest
from openmdbench.core.units import heading_deg_to_math_rad, math_rad_to_heading_deg


@pytest.mark.parametrize(
    ("heading_deg", "math_rad"),
    [(0.0, math.pi / 2), (90.0, 0.0), (180.0, -math.pi / 2), (270.0, -math.pi)],
)
def test_heading_conversion_covers_four_quadrants(heading_deg: float, math_rad: float) -> None:
    assert heading_deg_to_math_rad(heading_deg) == pytest.approx(math_rad)
    assert math_rad_to_heading_deg(math_rad) == pytest.approx(heading_deg)


def test_heading_conversion_round_trip_normalizes() -> None:
    assert math_rad_to_heading_deg(heading_deg_to_math_rad(450.0)) == pytest.approx(90.0)

"""License, uniqueness, transform, and headless-render tests for M2 profiles."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest
from matplotlib import pyplot as plt
from matplotlib.patches import PathPatch
from openmdbench.core.entities import Lifecycle, Side
from openmdbench.visualization import path_for_profile, transform_profile
from openmdbench.visualization.profiles import display_dimensions, style_for_entity

PROFILES = (
    "uav_generic",
    "usv_generic",
    "shore_radar_generic",
    "auv_generic",
    "civilian_vessel",
    "missile_generic",
)


def test_all_profiles_are_distinct_and_attributed() -> None:
    signatures = {
        tuple(np.asarray(path_for_profile(profile).vertices).round(4).flatten())
        for profile in PROFILES
    }
    assert len(signatures) == len(PROFILES)
    attribution = (
        Path(__file__).resolve().parents[3] / "assets" / "visual" / "ATTRIBUTION.md"
    ).read_text(encoding="utf-8")
    for profile in PROFILES:
        assert profile in attribution


@pytest.mark.parametrize(
    ("heading", "expected_tip"),
    [
        (0.0, (10.0, 25.0)),
        (90.0, (15.0, 20.0)),
        (180.0, (10.0, 15.0)),
        (270.0, (5.0, 20.0)),
    ],
)
def test_usv_heading_rotates_around_world_position(
    heading: float, expected_tip: tuple[float, float]
) -> None:
    path = transform_profile(
        "usv_generic",
        position=(10.0, 20.0),
        heading_deg=heading,
        length_m=10.0,
        width_m=4.0,
    )
    np.testing.assert_allclose(np.asarray(path.vertices)[0], expected_tip, atol=1e-7)


def test_four_domain_profiles_render_with_agg(tmp_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(4, 4))
    for index, profile in enumerate(PROFILES[:4]):
        transformed = transform_profile(
            profile,
            position=(float(index * 20), 0.0),
            heading_deg=float(index * 90),
            length_m=10.0,
            width_m=6.0,
        )
        axis.add_patch(PathPatch(transformed, facecolor="none", edgecolor="black"))
    axis.set_xlim(-10, 70)
    axis.set_ylim(-15, 15)
    output = tmp_path / "four-domains.png"
    figure.savefig(output)
    plt.close(figure)
    assert output.stat().st_size > 0


def test_real_scale_and_minimum_visible_size_preserve_aspect_ratio() -> None:
    assert display_dimensions(20.0, 5.0, meters_per_pixel=1.0) == (20.0, 5.0)
    enlarged = display_dimensions(2.0, 0.5, meters_per_pixel=2.0, minimum_pixels=6.0)
    assert enlarged == (12.0, 3.0)
    with pytest.raises(ValueError, match="positive"):
        display_dimensions(0.0, 1.0, meters_per_pixel=1.0)


def test_colorblind_theme_and_status_have_redundant_cues() -> None:
    blue = style_for_entity(Side.BLUE, Lifecycle.ACTIVE, theme="colorblind")
    red = style_for_entity(Side.RED, Lifecycle.ACTIVE, theme="colorblind")
    destroyed = style_for_entity(Side.BLUE, Lifecycle.DESTROYED, theme="colorblind")
    assert blue.facecolor != red.facecolor
    assert destroyed.linestyle != blue.linestyle
    assert destroyed.alpha < blue.alpha

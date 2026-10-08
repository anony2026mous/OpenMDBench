"""Physical/display geometry separation tests."""

import pytest
from openmdbench.schemas.geometry import (
    CollisionShape,
    EntityGeometry,
    GeometryPresentation,
    VisualProfile,
)


def test_physical_and_display_dimensions_are_independent() -> None:
    presentation = GeometryPresentation(
        geometry=EntityGeometry(
            length_m=64.0,
            width_m=10.0,
            diameter_m=10.0,
            collision_shape=CollisionShape.CAPSULE,
        ),
        visual_profile=VisualProfile(
            profile_id="usv_generic",
            minimum_display_size_m=25.0,
        ),
    )
    assert presentation.geometry.length_m == 64.0
    assert presentation.resolved_visual_profile().minimum_display_size_m == 25.0


def test_missing_profile_has_explicit_fallback() -> None:
    presentation = GeometryPresentation(
        geometry=EntityGeometry(
            length_m=2.0,
            width_m=2.0,
            diameter_m=2.0,
            collision_shape=CollisionShape.CIRCLE,
        )
    )
    assert presentation.resolved_visual_profile().profile_id == "generic_unknown"


def test_capsule_rejects_missing_diameter() -> None:
    with pytest.raises(ValueError, match="diameter_m"):
        EntityGeometry(
            length_m=10.0,
            width_m=2.0,
            collision_shape=CollisionShape.CAPSULE,
        )

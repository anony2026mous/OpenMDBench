"""Physical geometry and independent visualization-profile contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CollisionShape(StrEnum):
    CAPSULE = "capsule"
    CIRCLE = "circle"
    ORIENTED_BOX = "oriented_box"
    POLYGON = "polygon"


class VisualScaleMode(StrEnum):
    REAL = "real"
    MINIMUM_VISIBLE = "minimum_visible"


class EntityGeometry(BaseModel):
    """Physical dimensions used by dynamics and collision systems."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    length_m: float = Field(gt=0.0)
    width_m: float = Field(gt=0.0)
    height_m: float | None = Field(default=None, gt=0.0)
    diameter_m: float | None = Field(default=None, gt=0.0)
    collision_shape: CollisionShape

    @model_validator(mode="after")
    def validate_shape_dimensions(self) -> EntityGeometry:
        if (
            self.collision_shape in {CollisionShape.CAPSULE, CollisionShape.CIRCLE}
            and self.diameter_m is None
        ):
            raise ValueError("capsule and circle geometry require diameter_m")
        return self


class VisualProfile(BaseModel):
    """Rendering identity and display-only minimum size."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str = Field(min_length=1)
    minimum_display_size_m: float = Field(gt=0.0)
    scale_mode: VisualScaleMode = VisualScaleMode.MINIMUM_VISIBLE


FALLBACK_VISUAL_PROFILE = VisualProfile(
    profile_id="generic_unknown",
    minimum_display_size_m=10.0,
)


class GeometryPresentation(BaseModel):
    """Associates physical geometry with an optional display profile."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    geometry: EntityGeometry
    visual_profile: VisualProfile | None = None

    def resolved_visual_profile(self) -> VisualProfile:
        return self.visual_profile or FALLBACK_VISUAL_PROFILE

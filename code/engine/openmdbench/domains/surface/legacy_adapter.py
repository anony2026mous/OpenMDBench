"""Read-only adapter from a legacy USV array slot to a unified entity."""

from __future__ import annotations

from collections.abc import Sequence

from openmdbench.core.entities import ComponentState, Domain, PlatformAsset, Side
from openmdbench.core.units import math_rad_to_heading_deg


def adapt_legacy_usv(
    *,
    entity_id: str,
    side: Side,
    position: Sequence[float],
    velocity: Sequence[float],
    psi_rad: float,
) -> PlatformAsset:
    """Copy legacy state into an immutable unified USV snapshot."""
    return PlatformAsset(
        id=entity_id,
        side=side,
        domain=Domain.SURFACE,
        platform_type="usv",
        position=(float(position[0]), float(position[1]), 0.0),
        velocity=(float(velocity[0]), float(velocity[1]), 0.0),
        heading_deg=math_rad_to_heading_deg(psi_rad),
        components=ComponentState(),
    )

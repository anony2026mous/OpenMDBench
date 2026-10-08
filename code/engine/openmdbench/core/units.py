"""Central conversions for public headings and internal mathematical angles."""

from __future__ import annotations

import math


def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""
    return math.radians(degrees)


def radians_to_degrees(radians: float) -> float:
    """Convert radians to degrees."""
    return math.degrees(radians)


def normalize_heading_deg(heading_deg: float) -> float:
    """Normalize a clockwise-from-north heading to ``[0, 360)``."""
    return heading_deg % 360.0


def normalize_math_angle_rad(angle_rad: float) -> float:
    """Normalize a counter-clockwise-from-east angle to ``[-pi, pi)``."""
    return (angle_rad + math.pi) % math.tau - math.pi


def heading_deg_to_math_rad(heading_deg: float) -> float:
    """Convert clockwise-from-north degrees to counter-clockwise-from-east radians."""
    return normalize_math_angle_rad(math.radians(90.0 - normalize_heading_deg(heading_deg)))


def math_rad_to_heading_deg(angle_rad: float) -> float:
    """Convert counter-clockwise-from-east radians to clockwise-from-north degrees."""
    return normalize_heading_deg(90.0 - math.degrees(angle_rad))


def shortest_heading_error_rad(target_heading_deg: float, current_math_rad: float) -> float:
    """Return the shortest internal mathematical-angle error to a public heading."""
    target_math_rad = heading_deg_to_math_rad(target_heading_deg)
    return normalize_math_angle_rad(target_math_rad - current_math_rad)


def bounded_heading_deg(current: float, target: float, maximum_change: float) -> float:
    """Move a public heading toward a target along the shortest bounded arc."""
    difference = (target - current + 180.0) % 360.0 - 180.0
    change = max(-maximum_change, min(maximum_change, difference))
    return normalize_heading_deg(current + change)

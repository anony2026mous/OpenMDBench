"""Shared lifecycle visibility policy for V2 visualizations."""

from __future__ import annotations

DISPLAYABLE_LIFECYCLES_V2 = frozenset({"active", "degraded"})


def is_displayable_lifecycle_v2(lifecycle: object) -> bool:
    """Return whether a lifecycle state represents an operable entity on the map."""

    return lifecycle in DISPLAYABLE_LIFECYCLES_V2


__all__ = ["DISPLAYABLE_LIFECYCLES_V2", "is_displayable_lifecycle_v2"]

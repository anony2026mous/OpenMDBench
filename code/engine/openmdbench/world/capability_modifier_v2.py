"""Pure deterministic capability modifier composition for fixed-tick worlds."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

OperationV2 = Literal["multiply", "add", "override"]


# The compact aliases retain compatibility with already-versioned environment
# resources.  New resources can use the explicit ``capability_modifiers``
# collection below instead of adding another top-level field.
_ENVIRONMENT_MULTIPLIER_CAPABILITIES_V2: tuple[tuple[str, str], ...] = (
    ("motion_speed_multiplier", "dynamics.speed"),
    ("sensor_range_multiplier", "sensor.range"),
    ("sensor_detection_probability_multiplier", "sensor.probability"),
    ("weapon_hit_probability_multiplier", "weapon.hit_probability"),
    ("communication_loss_multiplier", "communication.loss"),
    ("energy_consumption_multiplier", "energy.consumption"),
)


def _finite(value: float, *, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{name} must be finite")
    return float(value)


@dataclass(frozen=True, slots=True)
class CapabilityModifierV2:
    modifier_id: str
    capability: str
    operation: OperationV2
    value: float
    priority: int = 0
    active_from_tick: int = 0
    inactive_from_tick: int | None = None
    floor: float | None = None
    source_event_id: str | None = None

    def __post_init__(self) -> None:
        if (
            not self.modifier_id
            or not self.capability
            or self.operation not in {"multiply", "add", "override"}
        ):
            raise ValueError("modifier identity, capability, or operation is invalid")
        object.__setattr__(self, "value", _finite(self.value, name="value"))
        if self.floor is not None:
            object.__setattr__(self, "floor", _finite(self.floor, name="floor"))
        if (
            not isinstance(self.priority, int)
            or isinstance(self.priority, bool)
            or not isinstance(self.active_from_tick, int)
            or isinstance(self.active_from_tick, bool)
            or self.active_from_tick < 0
            or (
                self.inactive_from_tick is not None
                and (
                    not isinstance(self.inactive_from_tick, int)
                    or isinstance(self.inactive_from_tick, bool)
                    or self.inactive_from_tick <= self.active_from_tick
                )
            )
        ):
            raise ValueError("modifier tick range or priority is invalid")

    def active_at(self, tick: int) -> bool:
        return self.active_from_tick <= tick and (
            self.inactive_from_tick is None or tick < self.inactive_from_tick
        )


@dataclass(frozen=True, slots=True)
class CapabilityValueV2:
    capability: str
    tick: int
    base_value: float
    value: float
    applied_modifier_ids: tuple[str, ...]
    lifecycle_available: bool
    energy_available: bool


def modifiers_from_environment_content_v2(
    *,
    environment_ref: str,
    content: Mapping[str, object],
    source_event_id: str | None,
    active_from_tick: int,
) -> tuple[CapabilityModifierV2, ...]:
    """Materialise declarative environment values into generic modifiers.

    The resolver deliberately consumes only resource content and an exact
    resource identity.  It has no scenario, faction, platform, or entity
    knowledge, so the same resource can be reused by any World.
    """

    if not environment_ref or not isinstance(content, Mapping):
        raise ValueError("environment identity or content is invalid")
    modifiers: list[CapabilityModifierV2] = []
    explicit = content.get("capability_modifiers", ())
    if explicit not in (None, ()):
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("capability_modifiers must be a sequence")
        for index, item in enumerate(explicit):
            if not isinstance(item, Mapping):
                raise ValueError("capability modifier must be a mapping")
            capability = item.get("capability")
            operation = item.get("operation", "multiply")
            value = item.get("value")
            modifier_id = item.get("modifier_id", f"{environment_ref}:modifier:{index}")
            priority = item.get("priority", 0)
            floor = item.get("floor")
            if (
                not isinstance(capability, str)
                or not isinstance(operation, str)
                or not isinstance(modifier_id, str)
            ):
                raise ValueError("capability modifier identity is invalid")
            modifiers.append(
                CapabilityModifierV2(
                    modifier_id=modifier_id,
                    capability=capability,
                    operation=cast(OperationV2, operation),
                    value=cast(float, value),
                    priority=cast(int, priority),
                    active_from_tick=active_from_tick,
                    floor=cast(float | None, floor),
                    source_event_id=source_event_id,
                )
            )
    for field, capability in _ENVIRONMENT_MULTIPLIER_CAPABILITIES_V2:
        if field not in content:
            continue
        modifiers.append(
            CapabilityModifierV2(
                modifier_id=f"{environment_ref}:{field}",
                capability=capability,
                operation="multiply",
                value=cast(float, content[field]),
                active_from_tick=active_from_tick,
                source_event_id=source_event_id,
            )
        )
    return tuple(sorted(modifiers, key=lambda item: (item.priority, item.modifier_id)))


def resolve_capability_v2(
    *,
    capability: str,
    base_value: float,
    tick: int,
    modifiers: Sequence[CapabilityModifierV2] = (),
    suppressed: bool = False,
    lifecycle_available: bool = True,
    energy_available: bool = True,
) -> CapabilityValueV2:
    """Apply base → sorted modifiers → suppression → lifecycle/energy clamp."""

    if not capability or not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
        raise ValueError("capability or tick is invalid")
    value = _finite(base_value, name="base_value")
    if (
        not isinstance(suppressed, bool)
        or not isinstance(lifecycle_available, bool)
        or not isinstance(energy_available, bool)
    ):
        raise ValueError("availability flags must be boolean")
    active = tuple(
        sorted(
            (item for item in modifiers if item.capability == capability and item.active_at(tick)),
            key=lambda item: (item.priority, item.modifier_id),
        )
    )
    for item in active:
        if item.operation == "multiply":
            value *= item.value
        elif item.operation == "add":
            value += item.value
        else:
            value = item.value
        if item.floor is not None:
            value = max(value, item.floor)
    if suppressed or not lifecycle_available or not energy_available:
        value = 0.0
    return CapabilityValueV2(
        capability,
        tick,
        float(base_value),
        value,
        tuple(item.modifier_id for item in active),
        lifecycle_available,
        energy_available,
    )


__all__ = [
    "CapabilityModifierV2",
    "CapabilityValueV2",
    "modifiers_from_environment_content_v2",
    "resolve_capability_v2",
]

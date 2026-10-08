"""Typed executable capability evidence derived from resolved entity bindings."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from openmdbench.catalog.v2 import MODEL_REF_PATTERN
from openmdbench.scenarios.declarative_v2 import ResolvedEntityV2, ResolvedResourceBindingV2

CapabilityRoleV2 = Literal[
    "platform",
    "dynamics",
    "loadout",
    "sensor",
    "communication",
    "weapon",
    "ammunition",
    "effect",
    "damage",
    "energy",
    "collision",
    "visualization",
    "environment",
]
CapabilityOperationV2 = Literal[
    "host",
    "move",
    "equip",
    "observe",
    "jam",
    "transmit",
    "engage",
    "supply",
    "apply",
    "assess",
    "power",
    "collide",
    "render",
    "configure",
]
CapabilityOriginV2 = Literal["direct", "dependency"]


@dataclass(frozen=True, slots=True)
class CapabilityTokenV2:
    role: CapabilityRoleV2
    resource_ref: str
    model_ref: str
    operation: CapabilityOperationV2
    origin: CapabilityOriginV2
    root_resource_ref: str | None = None

    def __post_init__(self) -> None:
        references = (self.resource_ref, self.model_ref, self.root_resource_ref)
        if any(
            reference is not None and re.fullmatch(MODEL_REF_PATTERN, reference) is None
            for reference in references
        ):
            raise ValueError("capability token references must be exact model references")


class CapabilitySelectorV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: CapabilityRoleV2 | None = None
    resource_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    model_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    operation: CapabilityOperationV2 | None = None
    origin: CapabilityOriginV2 | None = None
    root_resource_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)

    def matches(self, token: CapabilityTokenV2) -> bool:
        return all(
            expected is None or getattr(token, field) == expected
            for field, expected in (
                ("role", self.role),
                ("resource_ref", self.resource_ref),
                ("model_ref", self.model_ref),
                ("operation", self.operation),
                ("origin", self.origin),
                ("root_resource_ref", self.root_resource_ref),
            )
        )


_ROLE_OPERATION: Mapping[str, tuple[CapabilityRoleV2, CapabilityOperationV2]] = MappingProxyType(
    {
        "platforms": ("platform", "host"),
        "dynamics": ("dynamics", "move"),
        "loadouts": ("loadout", "equip"),
        "sensors": ("sensor", "observe"),
        "communications": ("communication", "transmit"),
        "weapons": ("weapon", "engage"),
        "ammunition": ("ammunition", "supply"),
        "effects": ("effect", "apply"),
        "damage_models": ("damage", "assess"),
        "energy": ("energy", "power"),
        "collision_shapes": ("collision", "collide"),
        "visualization_assets": ("visualization", "render"),
        "environments": ("environment", "configure"),
    }
)

COARSE_CAPABILITY_ROLES_V2 = frozenset(
    {"dynamics", "sensor", "communication", "weapon", "energy", "collision", "visualization"}
)

_IMPLICIT_REFERENCE_FIELDS = (
    "weapon_refs",
    "ammunition_refs",
    "effect_ref",
    "damage_model_ref",
    "weapon_ref",
    "energy_ref",
    "collision_shape_ref",
    "visualization_ref",
)


def capability_sort_key(
    token: CapabilityTokenV2,
) -> tuple[str, str, str, str, str, str]:
    return (
        token.role,
        token.resource_ref,
        token.model_ref,
        token.operation,
        token.origin,
        token.root_resource_ref or "",
    )


def _binding_index(entity: ResolvedEntityV2) -> dict[str, ResolvedResourceBindingV2]:
    return {
        binding.exact_ref: binding
        for bindings in entity.resource_bindings.values()
        for binding in bindings
    }


def _direct_roots(entity: ResolvedEntityV2) -> tuple[str, ...]:
    composition = entity.composition
    roots = (
        composition.platform_ref,
        composition.dynamics_ref,
        composition.loadout_ref,
        *composition.sensor_refs,
        *composition.communication_refs,
        composition.energy_ref,
        composition.collision_shape_ref,
        composition.visualization_ref,
        *composition.ammunition,
    )
    return tuple(sorted({reference for reference in roots if reference is not None}))


def _references(binding: ResolvedResourceBindingV2) -> tuple[str, ...]:
    values = set(binding.dependencies)
    for field in _IMPLICIT_REFERENCE_FIELDS:
        value = binding.normalized_content.get(field)
        if isinstance(value, str):
            values.add(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            values.update(item for item in value if isinstance(item, str))
    return tuple(sorted(values))


def capability_tokens_for_entity(entity: ResolvedEntityV2) -> tuple[CapabilityTokenV2, ...]:
    index = _binding_index(entity)
    tokens: set[CapabilityTokenV2] = set()
    for root in _direct_roots(entity):
        pending = [root]
        visited: set[str] = set()
        while pending:
            reference = pending.pop()
            if reference in visited:
                continue
            visited.add(reference)
            binding = index.get(reference)
            if binding is None:
                continue
            role_operation = _ROLE_OPERATION.get(binding.resource_type)
            if role_operation is not None:
                role, operation = role_operation
                tokens.add(
                    CapabilityTokenV2(
                        role=role,
                        resource_ref=binding.exact_ref,
                        model_ref=binding.model_ref,
                        operation=operation,
                        origin="direct" if reference == root else "dependency",
                        root_resource_ref=root,
                    )
                )
            pending.extend(reversed(_references(binding)))
    return tuple(sorted(tokens, key=capability_sort_key))


def coarse_capabilities(tokens: Sequence[CapabilityTokenV2]) -> frozenset[str]:
    return frozenset(token.role for token in tokens if token.role in COARSE_CAPABILITY_ROLES_V2)


def build_capability_index(
    entity_tokens: Mapping[str, Sequence[CapabilityTokenV2]],
) -> MappingProxyType[CapabilityTokenV2, tuple[str, ...]]:
    index: dict[CapabilityTokenV2, list[str]] = {}
    for entity_id, tokens in sorted(entity_tokens.items()):
        for token in tokens:
            index.setdefault(token, []).append(entity_id)
    return MappingProxyType(
        {token: tuple(index[token]) for token in sorted(index, key=capability_sort_key)}
    )


__all__ = [
    "COARSE_CAPABILITY_ROLES_V2",
    "CapabilityOperationV2",
    "CapabilityOriginV2",
    "CapabilityRoleV2",
    "CapabilitySelectorV2",
    "CapabilityTokenV2",
    "build_capability_index",
    "capability_sort_key",
    "capability_tokens_for_entity",
    "coarse_capabilities",
]

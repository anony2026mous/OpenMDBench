"""Immutable controller ownership and future-spawn reservation indexes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from openmdbench.scenarios.declarative_v2 import ResolvedEntityV2
from openmdbench.world.capabilities_v2 import (
    CapabilityTokenV2,
    capability_sort_key,
    capability_tokens_for_entity,
)


@dataclass(frozen=True, slots=True)
class ControllerClaimV2:
    slot_id: str
    controller_id: str
    faction_id: str
    entity_ids: tuple[str, ...]
    action_schema_ref: str
    observation_schema_ref: str
    endpoint_entity_id: str | None
    inbox_capacity: int
    exclusive: bool
    required_coarse_capabilities: tuple[str, ...]
    required_exact_capabilities: tuple[CapabilityTokenV2, ...]
    required_exact_capabilities_by_entity: Mapping[str, tuple[CapabilityTokenV2, ...]]


@dataclass(frozen=True, slots=True)
class ControllerReservationV2:
    controller_binding: str
    entity_id: str
    activation_tick: int
    source_event_id: str


@dataclass(frozen=True, slots=True)
class ControllerOwnershipIndexV2:
    slot_ids: tuple[str, ...]
    controller_ids: tuple[str, ...]
    claimed_entity_ids: tuple[str, ...]
    uncontrolled_entity_ids: tuple[str, ...]
    reserved_entity_ids: tuple[str, ...]
    uncontrolled_policy: str | None
    slot_to_claim: Mapping[str, ControllerClaimV2]
    controller_to_claim: Mapping[str, ControllerClaimV2]
    entity_to_claims: Mapping[str, tuple[ControllerClaimV2, ...]]
    reservation_by_entity: Mapping[str, ControllerReservationV2]
    reservations: tuple[ControllerReservationV2, ...]

    def by_slot(self, slot_id: str) -> ControllerClaimV2:
        return self.slot_to_claim[slot_id]

    def by_controller(self, controller_id: str) -> ControllerClaimV2:
        return self.controller_to_claim[controller_id]

    def by_entity(self, entity_id: str) -> tuple[ControllerClaimV2, ...]:
        return self.entity_to_claims.get(entity_id, ())

    def by_reserved_entity(self, entity_id: str) -> ControllerReservationV2 | None:
        return self.reservation_by_entity.get(entity_id)

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "slot_ids": list(self.slot_ids),
            "controller_ids": list(self.controller_ids),
            "claimed_entity_ids": list(self.claimed_entity_ids),
            "uncontrolled_entity_ids": list(self.uncontrolled_entity_ids),
            "reserved_entity_ids": list(self.reserved_entity_ids),
            "uncontrolled_policy": self.uncontrolled_policy,
            "claims": [_claim_dict(self.slot_to_claim[key]) for key in self.slot_ids],
            "reservations": [
                {
                    "controller_binding": item.controller_binding,
                    "entity_id": item.entity_id,
                    "activation_tick": item.activation_tick,
                    "source_event_id": item.source_event_id,
                }
                for item in self.reservations
            ],
        }


def _token_dict(token: CapabilityTokenV2) -> dict[str, str | None]:
    return {
        "role": token.role,
        "resource_ref": token.resource_ref,
        "model_ref": token.model_ref,
        "operation": token.operation,
        "origin": token.origin,
        "root_resource_ref": token.root_resource_ref,
    }


def _claim_dict(claim: ControllerClaimV2) -> dict[str, Any]:
    return {
        "slot_id": claim.slot_id,
        "controller_id": claim.controller_id,
        "faction_id": claim.faction_id,
        "entity_ids": list(claim.entity_ids),
        "action_schema_ref": claim.action_schema_ref,
        "observation_schema_ref": claim.observation_schema_ref,
        "endpoint_entity_id": claim.endpoint_entity_id,
        "inbox_capacity": claim.inbox_capacity,
        "exclusive": claim.exclusive,
        "required_coarse_capabilities": list(claim.required_coarse_capabilities),
        "required_exact_capabilities": [
            _token_dict(token) for token in claim.required_exact_capabilities
        ],
        "required_exact_capabilities_by_entity": {
            entity_id: [_token_dict(token) for token in tokens]
            for entity_id, tokens in sorted(claim.required_exact_capabilities_by_entity.items())
        },
    }


def _value(item: object, field: str) -> Any:
    return getattr(item, field)


def build_controller_ownership(
    *,
    slots: Sequence[object],
    uncontrolled_policy: str | None,
    entity_factions: Mapping[str, str],
    entity_tokens: Mapping[str, tuple[CapabilityTokenV2, ...]],
    lifecycle_schedule: Sequence[object],
) -> ControllerOwnershipIndexV2:
    # A controller selector is resolved by the compiler against both initial and
    # scheduled entities.  Rebuild the same immutable endpoint universe here so a
    # data-only wave can reserve one controller before its entities are spawned.
    complete_factions = dict(entity_factions)
    complete_tokens = dict(entity_tokens)
    for entry in lifecycle_schedule:
        if _value(entry, "event_type") != "spawn":
            continue
        blueprint = _value(entry, "blueprint")
        if not isinstance(blueprint, ResolvedEntityV2):
            raise ValueError("spawn controller blueprint is invalid")
        complete_factions.setdefault(blueprint.id, blueprint.faction_id)
        complete_tokens.setdefault(blueprint.id, capability_tokens_for_entity(blueprint))
    claims: list[ControllerClaimV2] = []
    claimed_exclusivity: dict[str, bool] = {}
    for slot in sorted(slots, key=lambda item: str(_value(item, "id"))):
        slot_id = _value(slot, "id")
        controller_id = _value(slot, "controller_id")
        faction_id = _value(slot, "faction_id")
        entity_ids = tuple(_value(slot, "resolved_entity_ids"))
        action_schema = _value(slot, "action_schema_ref")
        observation_schema = _value(slot, "observation_schema_ref")
        endpoint_entity_id = getattr(slot, "controller_endpoint_ref", None)
        inbox_capacity = getattr(slot, "inbox_capacity", 256)
        exclusive = _value(slot, "exclusive")
        coarse = tuple(sorted(_value(slot, "required_capabilities")))
        if (
            not all(
                isinstance(value, str) and value for value in (slot_id, controller_id, faction_id)
            )
            or action_schema != "action-batch@2.0"
            or observation_schema != "observation@2.0"
            or (
                endpoint_entity_id is not None
                and (
                    not isinstance(endpoint_entity_id, str)
                    or not endpoint_entity_id
                    or complete_factions.get(endpoint_entity_id) != faction_id
                )
            )
            or not isinstance(inbox_capacity, int)
            or isinstance(inbox_capacity, bool)
            or not 1 <= inbox_capacity <= 4096
            or not isinstance(exclusive, bool)
            or not entity_ids
            or entity_ids != tuple(sorted(set(entity_ids)))
            or any(complete_factions.get(entity_id) != faction_id for entity_id in entity_ids)
        ):
            raise ValueError("invalid resolved controller ownership claim")
        if any(
            entity_id in claimed_exclusivity and (exclusive or claimed_exclusivity[entity_id])
            for entity_id in entity_ids
        ):
            raise ValueError("exclusive controller ownership conflict")
        for entity_id in entity_ids:
            claimed_exclusivity[entity_id] = claimed_exclusivity.get(entity_id, False) or exclusive
        exact_by_entity: dict[str, tuple[CapabilityTokenV2, ...]] = {}
        exact_union: set[CapabilityTokenV2] = set()
        for entity_id in entity_ids:
            matching = tuple(
                sorted(
                    (token for token in complete_tokens[entity_id] if token.role in coarse),
                    key=capability_sort_key,
                )
            )
            if any(not any(token.role == role for token in matching) for role in coarse):
                raise ValueError("controller required capability has no exact evidence")
            exact_by_entity[entity_id] = matching
            exact_union.update(matching)
        exact = tuple(sorted(exact_union, key=capability_sort_key))
        claims.append(
            ControllerClaimV2(
                slot_id=slot_id,
                controller_id=controller_id,
                faction_id=faction_id,
                entity_ids=entity_ids,
                action_schema_ref=action_schema,
                observation_schema_ref=observation_schema,
                endpoint_entity_id=endpoint_entity_id,
                inbox_capacity=inbox_capacity,
                exclusive=exclusive,
                required_coarse_capabilities=coarse,
                required_exact_capabilities=exact,
                required_exact_capabilities_by_entity=MappingProxyType(exact_by_entity),
            )
        )
    slot_to_claim = {claim.slot_id: claim for claim in claims}
    controller_to_claim = {claim.controller_id: claim for claim in claims}
    if len(slot_to_claim) != len(claims) or len(controller_to_claim) != len(claims):
        raise ValueError("duplicate controller slot or controller identity")
    # Runtime ownership snapshots contain active entities only.  Future endpoints
    # remain in the immutable slot claim and become active on the topology refresh
    # performed after their spawn event.
    entity_to_claims: dict[str, list[ControllerClaimV2]] = {
        entity_id: [] for entity_id in entity_factions
    }
    for claim in claims:
        for entity_id in claim.entity_ids:
            if entity_id in entity_to_claims:
                entity_to_claims[entity_id].append(claim)
    reservations: list[ControllerReservationV2] = []
    for entry in lifecycle_schedule:
        if _value(entry, "event_type") != "spawn":
            continue
        blueprint = _value(entry, "blueprint")
        binding = getattr(blueprint, "controller_slot", None)
        if binding is None:
            continue
        entity_id = _value(entry, "entity_id")
        if (
            not isinstance(blueprint, ResolvedEntityV2)
            or not isinstance(binding, str)
            or not binding
        ):
            raise ValueError("spawn controller reservation binding is invalid")
        reservation_claim = slot_to_claim.get(binding) or controller_to_claim.get(binding)
        if reservation_claim is None:
            if binding != f"controller/{entity_id}":
                raise ValueError("spawn controller reservation endpoint is unknown")
        else:
            if blueprint.faction_id != reservation_claim.faction_id:
                raise ValueError("spawn controller reservation faction is incompatible")
            tokens = capability_tokens_for_entity(blueprint)
            if any(
                not any(token.role == role for token in tokens)
                for role in reservation_claim.required_coarse_capabilities
            ):
                raise ValueError("spawn controller reservation capability is missing")
            if reservation_claim.exclusive and reservation_claim.entity_ids:
                raise ValueError("exclusive controller reservation conflicts with an active claim")
        reservations.append(
            ControllerReservationV2(
                controller_binding=binding,
                entity_id=entity_id,
                activation_tick=_value(entry, "tick"),
                source_event_id=_value(entry, "source_event_id"),
            )
        )
    reservations.sort(
        key=lambda item: (
            item.activation_tick,
            item.source_event_id,
            item.entity_id,
            item.controller_binding,
        )
    )
    reservation_by_entity: dict[str, ControllerReservationV2] = {}
    for reservation in reservations:
        reservation_by_entity.setdefault(reservation.entity_id, reservation)
    claimed = tuple(sorted(entity_id for entity_id, values in entity_to_claims.items() if values))
    return ControllerOwnershipIndexV2(
        slot_ids=tuple(sorted(slot_to_claim)),
        controller_ids=tuple(sorted(controller_to_claim)),
        claimed_entity_ids=claimed,
        uncontrolled_entity_ids=tuple(sorted(set(entity_factions) - set(claimed))),
        reserved_entity_ids=tuple(sorted(reservation_by_entity)),
        uncontrolled_policy=uncontrolled_policy,
        slot_to_claim=MappingProxyType(slot_to_claim),
        controller_to_claim=MappingProxyType(controller_to_claim),
        entity_to_claims=MappingProxyType(
            {
                entity_id: tuple(sorted(values, key=lambda item: item.slot_id))
                for entity_id, values in sorted(entity_to_claims.items())
            }
        ),
        reservation_by_entity=MappingProxyType(reservation_by_entity),
        reservations=tuple(reservations),
    )


__all__ = [
    "ControllerClaimV2",
    "ControllerOwnershipIndexV2",
    "ControllerReservationV2",
    "build_controller_ownership",
]

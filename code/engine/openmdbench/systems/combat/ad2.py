"""Stable arbitration and simultaneous abstract combat for MD-AD-002."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from openmdbench.catalog.builtin_models import ProbabilityInstantWeaponModel
from openmdbench.catalog.legacy_adapters import md_ad_002_catalog
from openmdbench.catalog.models import EffectDefinition, WeaponDefinition
from openmdbench.catalog.repository import CatalogRepository
from openmdbench.core.entities import Lifecycle, PlatformAsset, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.world import ContactTrack, WorldState
from openmdbench.policies.actions import ActionBatch, PlatformAction
from openmdbench.scenarios.md_ad_002_config import MDAD002Config
from openmdbench.systems.combat.damage import DamageIntent, apply_simultaneous_damage


class AD2RejectionCode(StrEnum):
    ATTACKER_NOT_RED = "attacker_not_red"
    ATTACKER_UNAVAILABLE = "attacker_unavailable"
    COMMAND_NOT_DELIVERED = "command_not_delivered"
    CONTACT_NOT_OWNED = "contact_not_owned"
    CONTACT_STALE = "contact_stale"
    CONFIDENCE_TOO_LOW = "confidence_too_low"
    TARGET_NOT_HOSTILE = "target_not_hostile"
    TARGET_UNAVAILABLE = "target_unavailable"
    WEAPON_INCOMPATIBLE = "weapon_incompatible"
    INVALID_COUNT = "invalid_count"
    INSUFFICIENT_AMMUNITION = "insufficient_ammunition"
    COOLDOWN_ACTIVE = "cooldown_active"
    ESTIMATED_OUT_OF_RANGE = "estimated_out_of_range"
    TRUTH_OUT_OF_RANGE = "truth_out_of_range"
    MISSILE_DENIAL_ZONE_PROHIBITED = "missile_denial_zone_prohibited"
    DUPLICATE_TARGET = "duplicate_target"


@dataclass(frozen=True, slots=True)
class Candidate:
    action: PlatformAction
    attacker: PlatformAsset
    target: PlatformAsset
    contact: ContactTrack
    weapon: WeaponDefinition
    effect: EffectDefinition


class AD2Combat:
    def __init__(
        self,
        config: MDAD002Config,
        seed: int,
        protected_point: tuple[float, float],
        *,
        catalog: CatalogRepository | None = None,
    ) -> None:
        self.config = config
        self.catalog: CatalogRepository = catalog or md_ad_002_catalog(config)
        self.protected_point = protected_point
        self.rng = SessionRNG(seed)
        self.cooldowns: dict[tuple[str, str], int] = {}
        self.safety_violations = 0
        self.events: list[dict[str, object]] = []

    def _reject(
        self, action: PlatformAction, code: AD2RejectionCode, tick: int
    ) -> dict[str, object]:
        event = {
            "tick": tick,
            "event_type": "engagement_rejected",
            "attacker_id": action.entity_id,
            "contact_id": action.engage_contact_id,
            "weapon_id": action.weapon_id,
            "rejection_code": code.value,
        }
        if code in {
            AD2RejectionCode.ATTACKER_NOT_RED,
            AD2RejectionCode.CONTACT_NOT_OWNED,
            AD2RejectionCode.TARGET_NOT_HOSTILE,
            AD2RejectionCode.MISSILE_DENIAL_ZONE_PROHIBITED,
        }:
            self.safety_violations += 1
        self.events.append(event)
        return event

    def _weapon(self, weapon_id: str | None) -> WeaponDefinition | None:
        if weapon_id is None:
            return None
        try:
            model = self.catalog.instantiate("weapons", f"{weapon_id}@1.0.0")
        except ValueError:
            return None
        return model.definition if isinstance(model, ProbabilityInstantWeaponModel) else None

    def _validate(
        self,
        action: PlatformAction,
        world: WorldState,
        *,
        tick: int,
        truth_id: str | None,
    ) -> Candidate | AD2RejectionCode:
        try:
            attacker = world.registry.get(action.entity_id)
        except KeyError:
            return AD2RejectionCode.ATTACKER_UNAVAILABLE
        if not isinstance(attacker, PlatformAsset) or attacker.side is not Side.RED:
            return AD2RejectionCode.ATTACKER_NOT_RED
        if attacker.lifecycle not in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}:
            return AD2RejectionCode.ATTACKER_UNAVAILABLE
        if not attacker.components.weapons_operational:
            return AD2RejectionCode.ATTACKER_UNAVAILABLE
        if attacker.components.communication_status not in {"connected", "relayed"}:
            return AD2RejectionCode.COMMAND_NOT_DELIVERED
        contact = next(
            (
                item
                for item in world.contacts.get(Side.RED, [])
                if item.contact_id == action.engage_contact_id
            ),
            None,
        )
        if contact is None or contact.owner_side is not Side.RED:
            return AD2RejectionCode.CONTACT_NOT_OWNED
        last_update = contact.last_update_tick or contact.first_detected_tick
        if tick - last_update > 10:
            return AD2RejectionCode.CONTACT_STALE
        if contact.confidence < 0.7:
            return AD2RejectionCode.CONFIDENCE_TOO_LOW
        if truth_id is None:
            return AD2RejectionCode.TARGET_NOT_HOSTILE
        try:
            target = world.registry.get(truth_id)
        except KeyError:
            return AD2RejectionCode.TARGET_NOT_HOSTILE
        if not isinstance(target, PlatformAsset) or target.side is not Side.BLUE:
            return AD2RejectionCode.TARGET_NOT_HOSTILE
        if target.lifecycle not in {
            Lifecycle.ACTIVE,
            Lifecycle.DEGRADED,
            Lifecycle.BREACHED_ACTIVE,
        }:
            return AD2RejectionCode.TARGET_UNAVAILABLE
        weapon = self._weapon(action.weapon_id)
        compatible_platform = {
            "uav_interceptor_missile": "uav",
            "shore_ciws": "shore_radar",
        }
        if weapon is None or attacker.platform_type != compatible_platform[weapon.id]:
            return AD2RejectionCode.WEAPON_INCOMPATIBLE
        if target.domain.value not in weapon.target_domains:
            return AD2RejectionCode.WEAPON_INCOMPATIBLE
        if action.count != weapon.rounds_per_action:
            return AD2RejectionCode.INVALID_COUNT
        if attacker.components.weapon_inventory.get(weapon.id, 0) < action.count:
            return AD2RejectionCode.INSUFFICIENT_AMMUNITION
        last_fired = self.cooldowns.get((attacker.id, weapon.id))
        if last_fired is not None and tick - last_fired < weapon.cooldown_ticks:
            return AD2RejectionCode.COOLDOWN_ACTIVE
        estimated_range = math.dist(attacker.position, contact.position)
        if not weapon.minimum_range_m <= estimated_range <= weapon.maximum_range_m:
            return AD2RejectionCode.ESTIMATED_OUT_OF_RANGE
        truth_range = math.dist(attacker.position, target.position)
        if not weapon.minimum_range_m <= truth_range <= weapon.maximum_range_m:
            return AD2RejectionCode.TRUTH_OUT_OF_RANGE
        if (
            weapon.id == "uav_interceptor_missile"
            and math.dist(target.position[:2], self.protected_point)
            <= self.config.denial_zone.radius
        ):
            return AD2RejectionCode.MISSILE_DENIAL_ZONE_PROHIBITED
        effect = self.catalog.resolve("effects", weapon.effect_ref)
        if not isinstance(effect, EffectDefinition):
            return AD2RejectionCode.WEAPON_INCOMPATIBLE
        return Candidate(action, attacker, target, contact, weapon, effect)

    def resolve(
        self,
        world: WorldState,
        batch: ActionBatch,
        *,
        truth_by_contact: dict[str, str],
        breached_ids: frozenset[str] = frozenset(),
    ) -> tuple[dict[str, object], ...]:
        tick = world.tick
        candidates: list[Candidate] = []
        output: list[dict[str, object]] = []
        actions = tuple(
            action
            for action in batch.actions
            if action.engage_contact_id is not None and action.weapon_id is not None
        )
        for action in sorted(actions, key=lambda item: (item.entity_id, item.weapon_id or "")):
            result = self._validate(
                action,
                world,
                tick=tick,
                truth_id=truth_by_contact.get(action.engage_contact_id or ""),
            )
            if isinstance(result, AD2RejectionCode):
                output.append(self._reject(action, result, tick))
            else:
                candidates.append(result)
        winners: dict[str, Candidate] = {}
        for candidate in sorted(
            candidates,
            key=lambda item: (
                item.target.id,
                0 if item.weapon.id == "shore_ciws" else 1,
                math.dist(item.attacker.position, item.contact.position),
                item.attacker.id,
            ),
        ):
            if candidate.target.id in winners:
                output.append(
                    self._reject(candidate.action, AD2RejectionCode.DUPLICATE_TARGET, tick)
                )
            else:
                winners[candidate.target.id] = candidate
        damage: list[DamageIntent] = []
        for target_id, candidate in sorted(winners.items()):
            sample = float(self.rng.stream("ad2_combat").random())
            distance = math.dist(candidate.attacker.position, candidate.target.position)
            probability = candidate.weapon.hit_probability * max(
                0.5, 1.0 - 0.5 * distance / candidate.weapon.maximum_range_m
            )
            hit = sample < probability
            inventory = dict(candidate.attacker.components.weapon_inventory)
            inventory[candidate.weapon.id] -= candidate.action.count
            launch_cost = candidate.weapon.energy_cost
            world.registry.update(
                candidate.attacker.model_copy(
                    update={
                        "components": candidate.attacker.components.model_copy(
                            update={
                                "weapon_inventory": inventory,
                                "energy": max(
                                    0.0,
                                    candidate.attacker.components.energy - launch_cost,
                                ),
                            }
                        )
                    }
                )
            )
            self.cooldowns[(candidate.attacker.id, candidate.weapon.id)] = tick
            if hit:
                damage.append(
                    DamageIntent(
                        candidate.attacker.id,
                        target_id,
                        candidate.effect.damage_fraction,
                    )
                )
            event = {
                "tick": tick,
                "event_type": "combat_round",
                "attacker_id": candidate.attacker.id,
                "contact_id": candidate.contact.contact_id,
                "weapon_id": candidate.weapon.id,
                "probability": probability,
                "rng_sample": sample,
                "hit": hit,
                "damage": candidate.effect.damage_fraction if hit else 0.0,
                "ammunition_after": inventory[candidate.weapon.id],
            }
            self.events.append(event)
            output.append(event)
        platforms = tuple(
            entity for entity in world.entities_stable() if isinstance(entity, PlatformAsset)
        )
        updated, damage_events = apply_simultaneous_damage(platforms, tuple(damage))
        for entity in updated:
            if entity.id in breached_ids and entity.lifecycle in {
                Lifecycle.ACTIVE,
                Lifecycle.DEGRADED,
            }:
                entity = entity.model_copy(update={"lifecycle": Lifecycle.BREACHED_ACTIVE})
            world.registry.update(entity)
        for item in damage_events:
            event = {
                "tick": tick,
                "event_type": "damage_applied",
                "target_id_internal": item.target_id,
                "health_before": item.health_before,
                "health_after": item.health_after,
                "lifecycle": item.status_after.value,
                "total_damage": item.total_damage,
            }
            self.events.append(event)
            output.append(event)
        return tuple(output)

    def snapshot(self) -> dict[str, Any]:
        return {
            "catalog_hash": self.catalog.content_hash,
            "rng": self.rng.snapshot(),
            "protected_point": list(self.protected_point),
            "cooldowns": [
                [attacker, weapon, tick]
                for (attacker, weapon), tick in sorted(self.cooldowns.items())
            ],
            "safety_violations": self.safety_violations,
            "events": list(self.events),
        }

    @classmethod
    def from_snapshot(cls, config: MDAD002Config, snapshot: dict[str, Any]) -> AD2Combat:
        combat = cls(config, 0, tuple(snapshot["protected_point"]))
        checkpoint_hash = snapshot.get("catalog_hash")
        if checkpoint_hash is not None and checkpoint_hash != combat.catalog.content_hash:
            raise ValueError("checkpoint catalog hash mismatch")
        combat.rng = SessionRNG.from_snapshot(snapshot["rng"])
        combat.cooldowns = {
            (str(attacker), str(weapon)): int(tick)
            for attacker, weapon, tick in snapshot["cooldowns"]
        }
        combat.safety_violations = int(snapshot["safety_violations"])
        combat.events = list(snapshot["events"])
        return combat

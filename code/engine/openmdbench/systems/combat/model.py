"""Range-, ROE-, weather-, ammunition-, and RNG-governed abstract engagement."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import StrEnum

from openmdbench.core.entities import Domain, Lifecycle, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.world import ContactTrack
from openmdbench.systems.weather import WEATHER_EFFECTS, Weather


@dataclass(frozen=True, slots=True)
class WeaponSpec:
    weapon_id: str
    range_m: float
    base_hit_probability: float
    damage: float
    platform_types: tuple[str, ...] = ()
    target_domains: tuple[Domain, ...] = ()
    guidance_sensor: str = "radar"


WEAPONS = {
    "uav_air_to_ground": WeaponSpec(
        "uav_air_to_ground", 8_000.0, 0.7, 0.6, ("uav",), (Domain.SURFACE,), "eo_ir"
    ),
    "uav_interceptor_missile": WeaponSpec(
        "uav_interceptor_missile", 8_000.0, 0.7, 0.6, ("uav",), (Domain.AIR,), "eo_ir"
    ),
    "usv_rws": WeaponSpec("usv_rws", 3_000.0, 0.8, 0.4, ("usv",), (Domain.SURFACE,), "radar"),
    "shore_ciws": WeaponSpec(
        "shore_ciws", 2_000.0, 0.8, 0.5, ("shore_radar",), (Domain.AIR,), "radar"
    ),
    "auv_torpedo": WeaponSpec(
        "auv_torpedo", 5_000.0, 0.6, 0.8, ("auv",), (Domain.UNDERWATER,), "sonar"
    ),
}


@dataclass(frozen=True, slots=True)
class Combatant:
    asset_id: str
    side: Side
    position: tuple[float, float, float]
    health: float
    ammunition: dict[str, int]
    platform_type: str = "usv"
    lifecycle: Lifecycle = Lifecycle.ACTIVE


@dataclass(frozen=True, slots=True)
class CombatResult:
    attacker: Combatant
    target_health: float
    hit: bool
    event: dict[str, object]
    shots: tuple[ShotResult, ...] = ()
    total_damage: float = 0.0


@dataclass(frozen=True, slots=True)
class ShotResult:
    round_index: int
    probability: float
    random_sample: float
    hit: bool
    damage: float


class RejectionCode(StrEnum):
    ATTACKER_UNAVAILABLE = "attacker_unavailable"
    COMMAND_NOT_DELIVERED = "command_not_delivered"
    CONTACT_NOT_OWNED = "contact_not_owned"
    CONTACT_STALE = "contact_stale"
    CONFIDENCE_TOO_LOW = "confidence_too_low"
    NOT_HOSTILE = "not_hostile"
    ROE_PROHIBITED = "roe_prohibited"
    WEAPON_INCOMPATIBLE = "weapon_incompatible"
    INVALID_COUNT = "invalid_count"
    INSUFFICIENT_AMMUNITION = "insufficient_ammunition"
    ESTIMATED_OUT_OF_RANGE = "estimated_out_of_range"
    TRUTH_OUT_OF_RANGE = "truth_out_of_range"


@dataclass(frozen=True, slots=True)
class LegalityResult:
    accepted: bool
    rejection_code: RejectionCode | None = None


def validate_engagement(
    attacker: Combatant,
    contact: ContactTrack | None,
    *,
    target_side: Side,
    target_domain: Domain,
    target_truth_position: tuple[float, float, float],
    weapon_id: str,
    count: int,
    current_tick: int,
    command_delivered: bool,
    hostile: bool,
    roe_permitted: bool,
) -> LegalityResult:
    if attacker.lifecycle not in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}:
        return LegalityResult(False, RejectionCode.ATTACKER_UNAVAILABLE)
    if not command_delivered:
        return LegalityResult(False, RejectionCode.COMMAND_NOT_DELIVERED)
    if contact is None or contact.owner_side is not attacker.side:
        return LegalityResult(False, RejectionCode.CONTACT_NOT_OWNED)
    contact_tick = contact.message_sent_tick or contact.first_detected_tick
    if current_tick - contact_tick > 10:
        return LegalityResult(False, RejectionCode.CONTACT_STALE)
    if contact.confidence < 0.7:
        return LegalityResult(False, RejectionCode.CONFIDENCE_TOO_LOW)
    if not hostile:
        return LegalityResult(False, RejectionCode.NOT_HOSTILE)
    if target_side in {attacker.side, Side.NEUTRAL} or not roe_permitted:
        return LegalityResult(False, RejectionCode.ROE_PROHIBITED)
    weapon = WEAPONS.get(weapon_id)
    if (
        weapon is None
        or (weapon.platform_types and attacker.platform_type not in weapon.platform_types)
        or (weapon.target_domains and target_domain not in weapon.target_domains)
    ):
        return LegalityResult(False, RejectionCode.WEAPON_INCOMPATIBLE)
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        return LegalityResult(False, RejectionCode.INVALID_COUNT)
    if attacker.ammunition.get(weapon_id, 0) < count:
        return LegalityResult(False, RejectionCode.INSUFFICIENT_AMMUNITION)
    if math.dist(attacker.position, contact.position) > weapon.range_m:
        return LegalityResult(False, RejectionCode.ESTIMATED_OUT_OF_RANGE)
    if math.dist(attacker.position, target_truth_position) > weapon.range_m:
        return LegalityResult(False, RejectionCode.TRUTH_OUT_OF_RANGE)
    return LegalityResult(True)


def engage(
    attacker: Combatant,
    contact: ContactTrack | None,
    *,
    target_side: Side,
    target_health: float,
    weapon_id: str,
    count: int,
    weather: Weather,
    rng: SessionRNG,
    allow_neutral_engagement: bool = False,
    current_tick: int = 0,
    command_delivered: bool = True,
    hostile: bool = True,
    roe_permitted: bool = True,
    target_domain: Domain | None = None,
    target_truth_position: tuple[float, float, float] | None = None,
) -> CombatResult:
    inferred_domain = target_domain or (contact.estimated_domain if contact else Domain.SURFACE)
    inferred_truth = target_truth_position or (contact.position if contact else attacker.position)
    legality = validate_engagement(
        attacker,
        contact,
        target_side=target_side,
        target_domain=inferred_domain,
        target_truth_position=inferred_truth,
        weapon_id=weapon_id,
        count=count,
        current_tick=current_tick,
        command_delivered=command_delivered,
        hostile=hostile,
        roe_permitted=roe_permitted
        and (target_side is not Side.NEUTRAL or allow_neutral_engagement),
    )
    if not legality.accepted:
        rejection = legality.rejection_code
        if rejection is None:
            raise RuntimeError("rejected engagement is missing its stable rejection code")
        messages = {
            RejectionCode.CONTACT_NOT_OWNED: (
                "engagement requires a currently legal visible contact"
            ),
            RejectionCode.ROE_PROHIBITED: "ROE prohibits target engagement",
            RejectionCode.ESTIMATED_OUT_OF_RANGE: "target contact is outside weapon range",
        }
        raise ValueError(messages.get(rejection, rejection.value))
    if contact is None:
        raise RuntimeError("accepted engagement is missing its owned contact")
    available = attacker.ammunition[weapon_id]
    weapon = WEAPONS[weapon_id]
    distance = math.dist(attacker.position, contact.position)

    inventory = dict(attacker.ammunition)
    inventory[weapon_id] = available - count
    updated_attacker = replace(attacker, ammunition=inventory)
    distance_modifier = max(0.5, 1.0 - 0.5 * distance / weapon.range_m)
    track_modifier = max(0.5, min(1.0, 0.5 + 0.5 * contact.confidence))
    weather_modifier = 1.0 - getattr(WEATHER_EFFECTS[weather], weapon.guidance_sensor)
    status_modifier = 0.8 if attacker.lifecycle is Lifecycle.DEGRADED else 1.0
    probability = max(
        0.0,
        min(
            1.0,
            weapon.base_hit_probability
            * distance_modifier
            * track_modifier
            * weather_modifier
            * status_modifier,
        ),
    )
    samples = rng.stream("combat").random(count)
    shots = tuple(
        ShotResult(index, probability, float(sample), bool(sample < probability), weapon.damage)
        for index, sample in enumerate(samples)
    )
    hit_count = sum(shot.hit for shot in shots)
    total_damage = hit_count * weapon.damage
    hit = hit_count > 0
    resulting_health = max(0.0, target_health - total_damage)
    event = {
        "ammunition_used": count,
        "attacker_id": attacker.asset_id,
        "contact_id": contact.contact_id,
        "destroyed": resulting_health == 0.0,
        "distance_m": distance,
        "event_type": "engagement",
        "hit": hit,
        "probability": probability,
        "random_samples": [shot.random_sample for shot in shots],
        "random_sample": shots[0].random_sample,
        "roe_violation": False,
        "weapon_id": weapon_id,
    }
    return CombatResult(updated_attacker, resulting_health, hit, event, shots, total_damage)

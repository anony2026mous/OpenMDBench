"""Typed World-owned authority, contact, and rules-of-engagement evidence."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Literal

from openmdbench.scenarios.declarative_v2 import ResolvedEntityV2
from openmdbench.world.controllers_v2 import ControllerOwnershipIndexV2


@dataclass(frozen=True, slots=True)
class WorldAuthorityGrantV2:
    """An opaque exact-entity or controller-scoped authority token."""

    token: str
    entity_id: str
    controller_id: str
    entity_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldContactEvidenceV2:
    """One immutable contact observation owned by the World contact store."""

    evidence_id: str
    owner_entity_id: str
    target_entity_id: str
    observed_tick: int
    age_ticks: int
    max_age_ticks: int
    confidence: float
    minimum_confidence: float
    quality: float
    schema_version: Literal["world-contact@2.0"] = "world-contact@2.0"
    measurement_position_m: tuple[float, float, float] | None = None
    confirmation_count: int = 1
    confirmation_frames: int = 1
    stale_after_ticks: int = 1
    confirmed: bool = True
    source_sensor_ref: str | None = None

    def __post_init__(self) -> None:
        if (
            self.schema_version != "world-contact@2.0"
            or not all(
                isinstance(value, str) and 0 < len(value) <= 256
                for value in (
                    self.evidence_id,
                    self.owner_entity_id,
                    self.target_entity_id,
                )
            )
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in (self.observed_tick, self.age_ticks, self.max_age_ticks)
            )
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0
                for value in (self.confidence, self.minimum_confidence, self.quality)
            )
            or (
                self.measurement_position_m is not None
                and (
                    len(self.measurement_position_m) != 3
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        for value in self.measurement_position_m
                    )
                )
            )
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value < 1
                for value in (
                    self.confirmation_count,
                    self.confirmation_frames,
                    self.stale_after_ticks,
                )
            )
            or not isinstance(self.confirmed, bool)
            or self.confirmed != (self.confirmation_count >= self.confirmation_frames)
            or (
                self.source_sensor_ref is not None
                and (not isinstance(self.source_sensor_ref, str) or not self.source_sensor_ref)
            )
        ):
            raise ValueError("World contact evidence is not canonical")


@dataclass(frozen=True, slots=True)
class WorldRoeRuleV2:
    """Resolved typed ROE evidence derived from one compiled relationship edge."""

    rule_id: str
    source_faction_id: str
    target_faction_id: str
    relationship: str
    engagement_permitted: bool
    schema_version: Literal["world-roe@2.0"] = "world-roe@2.0"

    def __post_init__(self) -> None:
        if (
            self.schema_version != "world-roe@2.0"
            or not all(
                isinstance(value, str) and 0 < len(value) <= 256
                for value in (
                    self.rule_id,
                    self.source_faction_id,
                    self.target_faction_id,
                    self.relationship,
                )
            )
            or not isinstance(self.engagement_permitted, bool)
        ):
            raise ValueError("World ROE policy is not canonical")


@dataclass(frozen=True, slots=True)
class WorldComponentDamageProfileV2:
    """Resolved component damage response owned by the production World."""

    resource_ref: str
    role: str
    damage_multiplier: float
    degraded_below: float
    destroyed_at: float


class WorldContactStoreV2:
    """World-owned contact authority with exact owner/target lookup."""

    def __init__(self, records: Sequence[WorldContactEvidenceV2]) -> None:
        indexed: dict[str, dict[tuple[str, str], WorldContactEvidenceV2]] = {}
        for record in records:
            if (
                not record.evidence_id
                or not record.owner_entity_id
                or not record.target_entity_id
                or record.observed_tick < 0
                or record.age_ticks < 0
                or record.max_age_ticks < 0
                or not 0.0 <= record.confidence <= 1.0
                or not 0.0 <= record.minimum_confidence <= 1.0
                or not 0.0 <= record.quality <= 1.0
                or record.confirmation_count < 1
                or record.confirmation_frames < 1
                or record.stale_after_ticks < 1
                or record.confirmed != (record.confirmation_count >= record.confirmation_frames)
                or (record.source_sensor_ref is not None and not record.source_sensor_ref)
            ):
                raise ValueError("World contact evidence is invalid")
            key = (record.owner_entity_id, record.target_entity_id)
            bucket = indexed.setdefault(record.evidence_id, {})
            if key in bucket:
                raise ValueError("World contact evidence identity is duplicated")
            bucket[key] = record
        self._records = indexed

    @property
    def records(self) -> Mapping[str, tuple[WorldContactEvidenceV2, ...]]:
        return MappingProxyType(
            {
                evidence_id: tuple(bucket[key] for key in sorted(bucket))
                for evidence_id, bucket in sorted(self._records.items())
            }
        )

    def install(self, record: WorldContactEvidenceV2) -> None:
        if type(record) is not WorldContactEvidenceV2:
            raise TypeError("contact store requires exact typed World evidence")
        key = (record.owner_entity_id, record.target_entity_id)
        bucket = self._records.setdefault(record.evidence_id, {})
        if key in bucket or bucket:
            raise ValueError("contact evidence identity is already installed")
        bucket[key] = record

    def resolve(
        self,
        *,
        evidence_id: str | None,
        owner_entity_id: str,
        target_entity_id: str,
        current_tick: int,
    ) -> WorldContactEvidenceV2 | None:
        if not isinstance(current_tick, int) or isinstance(current_tick, bool) or current_tick < 0:
            raise ValueError("World contact lookup tick is invalid")
        if evidence_id is not None:
            record = self._records.get(evidence_id, {}).get(
                (owner_entity_id, target_entity_id)
            ) or next(iter(self._records.get(evidence_id, {}).values()), None)
        else:
            matching = tuple(
                record
                for bucket in self._records.values()
                for record in bucket.values()
                if record.owner_entity_id == owner_entity_id
                and record.target_entity_id == target_entity_id
            )
            record = matching[0] if len(matching) == 1 else None
        if record is None:
            return None
        return replace(
            record,
            age_ticks=max(record.age_ticks, current_tick - record.observed_tick),
        )

    def resolve_owned_observation(
        self,
        *,
        evidence_id: str,
        owner_entity_id: str,
        current_tick: int,
    ) -> WorldContactEvidenceV2 | None:
        """Resolve an opaque public track without exposing its truth association."""

        if not isinstance(current_tick, int) or isinstance(current_tick, bool) or current_tick < 0:
            raise ValueError("World contact lookup tick is invalid")
        matches = tuple(
            record
            for record in self._records.get(evidence_id, {}).values()
            if record.owner_entity_id == owner_entity_id
        )
        if len(matches) != 1:
            return None
        record = matches[0]
        return replace(
            record,
            age_ticks=max(record.age_ticks, current_tick - record.observed_tick),
        )

    def inject_fault(self, evidence_id: str, *, fault: str) -> None:
        """Apply one controlled evidence fault for boundary rejection testing."""

        if fault == "missing":
            self._records.pop(evidence_id, None)
            return
        bucket = self._records.get(evidence_id)
        if not bucket:
            return
        updated: dict[tuple[str, str], WorldContactEvidenceV2] = {}
        for key, record in bucket.items():
            if fault == "wrong_owner":
                changed = replace(record, owner_entity_id=record.target_entity_id)
            elif fault == "wrong_target":
                changed = replace(record, target_entity_id=record.owner_entity_id)
            elif fault == "stale":
                changed = replace(record, age_ticks=record.max_age_ticks + 1)
            elif fault == "low_confidence":
                changed = replace(
                    record,
                    confidence=max(0.0, record.minimum_confidence / 2.0),
                )
            else:
                raise ValueError("unsupported World contact fault")
            updated[key] = changed
        self._records[evidence_id] = updated


def build_world_authority_grants_v2(
    *,
    entity_factions: Mapping[str, str],
    controller_ownership: ControllerOwnershipIndexV2,
) -> Mapping[str, WorldAuthorityGrantV2]:
    """Build compatible entity and controller-scoped opaque authority grants."""

    grants: dict[str, WorldAuthorityGrantV2] = {}
    for entity_id in sorted(entity_factions):
        claims = controller_ownership.by_entity(entity_id)
        if len(claims) != 1:
            continue
        token = f"authority.{entity_id}"
        grants[token] = WorldAuthorityGrantV2(
            token=token,
            entity_id=entity_id,
            controller_id=claims[0].controller_id,
            entity_ids=(entity_id,),
        )

    for controller_id in sorted(controller_ownership.controller_ids):
        claim = controller_ownership.by_controller(controller_id)
        token = "authority.controller." + hashlib.sha256(controller_id.encode()).hexdigest()
        if token in grants:
            raise ValueError("controller authority token collides with an entity authority token")
        grants[token] = WorldAuthorityGrantV2(
            token=token,
            entity_id="",
            controller_id=controller_id,
            entity_ids=claim.entity_ids,
        )

    return MappingProxyType(grants)


def build_component_damage_profiles_v2(
    entities: Sequence[ResolvedEntityV2],
) -> Mapping[str, WorldComponentDamageProfileV2]:
    """Resolve immutable per-component damage profiles without platform branching."""

    profiles: dict[str, WorldComponentDamageProfileV2] = {}
    for entity in sorted(entities, key=lambda item: item.id):
        for role in ("communications", "sensors", "weapons"):
            for binding in entity.resource_bindings.get(role, ()):
                raw_multiplier = binding.normalized_content.get("damage_multiplier", 1.0)
                if (
                    isinstance(raw_multiplier, bool)
                    or not isinstance(raw_multiplier, (int, float))
                    or not math.isfinite(float(raw_multiplier))
                    or not float(raw_multiplier) >= 0.0
                ):
                    raise ValueError("component damage multiplier is invalid")
                profile = WorldComponentDamageProfileV2(
                    resource_ref=binding.exact_ref,
                    role=role,
                    damage_multiplier=float(raw_multiplier),
                    degraded_below=1.0,
                    destroyed_at=0.0,
                )
                previous = profiles.setdefault(binding.exact_ref, profile)
                if previous != profile:
                    raise ValueError("component damage profile evidence conflicts")
    return MappingProxyType(dict(sorted(profiles.items())))


__all__ = [
    "WorldAuthorityGrantV2",
    "WorldContactEvidenceV2",
    "WorldContactStoreV2",
    "WorldComponentDamageProfileV2",
    "WorldRoeRuleV2",
    "build_world_authority_grants_v2",
    "build_component_damage_profiles_v2",
]

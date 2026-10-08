"""Generic deterministic rule agents consuming only public schema-v2 session views."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Literal, Self, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.scenarios.formal_v2 import formal_scenario_registry_v2
from openmdbench.schemas.core_v2 import ObservationV2
from openmdbench.schemas.interface_v2 import (
    ActionBatchV2,
    DiscreteActionV2,
    PersistentCommandV2,
)
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2


class _RuleConfigV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class AttackRuleConfigV2(_RuleConfigV2):
    faction_id: str = Field(min_length=1, max_length=256)
    pattern: Literal["direct", "split_evasion", "multi_axis_serpentine"]
    speed_mps: float = Field(gt=0.0)
    split_angle_deg: float = Field(ge=0.0, le=80.0)
    serpentine_angle_deg: float = Field(ge=0.0, le=45.0)
    serpentine_period_ticks: int = Field(ge=1)
    turn_on_first_contact: bool = False
    contact_turn_deg: float = Field(default=0.0, ge=0.0, le=45.0)
    speed_cycle_mps: tuple[float, ...] = ()
    speed_cycle_ticks: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_speed_cycle(self) -> Self:
        if any(not math.isfinite(value) or value <= 0.0 for value in self.speed_cycle_mps):
            raise ValueError("rule-agent speed cycle values must be finite and positive")
        return self


class WeaponRuleConfigV2(_RuleConfigV2):
    selector_tags: tuple[str, ...] = Field(min_length=1)
    weapon_ref: str = Field(min_length=1, max_length=256)
    minimum_range_m: float = Field(ge=0.0)
    maximum_range_m: float = Field(gt=0.0)
    cooldown_ticks: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.maximum_range_m <= self.minimum_range_m:
            raise ValueError("rule-agent weapon range is empty")
        if tuple(sorted(set(self.selector_tags))) != self.selector_tags:
            raise ValueError("rule-agent selector tags must be unique and sorted")
        return self


class DefenceRuleConfigV2(_RuleConfigV2):
    faction_id: str = Field(min_length=1, max_length=256)
    intercept_speed_mps: float = Field(gt=0.0)
    contact_confidence: float = Field(ge=0.0, le=1.0)
    maximum_contact_age_ticks: int = Field(ge=0)
    weapon_policies: tuple[WeaponRuleConfigV2, ...] = Field(min_length=1)


class FormalRuleAgentProfileV2(_RuleConfigV2):
    schema_version: Literal["rule-agent-team@2.0"]
    objective_m: tuple[float, float]
    decision_interval_ticks: int = Field(ge=1, le=60)
    attack: AttackRuleConfigV2
    defence: DefenceRuleConfigV2

    @model_validator(mode="after")
    def validate_factions(self) -> Self:
        if self.attack.faction_id == self.defence.faction_id:
            raise ValueError("rule-agent opponents require distinct factions")
        return self


class RuleAgentDecisionV2(_RuleConfigV2):
    tick: int = Field(ge=0)
    observation_ticks: tuple[int, int]
    attack_command_ids: tuple[str, ...]
    defence_command_ids: tuple[str, ...]
    fire_action_ids: tuple[str, ...]
    fire_contact_ids: tuple[str, ...]
    attack_headings_deg: tuple[float, ...]


def load_formal_rule_agent_profile_v2(public_id: str) -> FormalRuleAgentProfileV2:
    """Load one strictly data-only policy profile next to its formal package."""

    try:
        package_root = formal_scenario_registry_v2()[public_id].package_root
    except KeyError as error:
        raise ValueError(f"unknown formal V2 scenario: {public_id}") from error
    path = package_root / "agents.yaml"
    if path.is_symlink() or not path.is_file() or path.parent.resolve() != package_root.resolve():
        raise ValueError("formal rule-agent profile is unavailable")
    payload = yaml.safe_load(path.read_bytes())
    return FormalRuleAgentProfileV2.model_validate(payload)


def _heading_to(origin: tuple[float, ...], target: tuple[float, ...]) -> float:
    east = float(target[0]) - float(origin[0])
    north = float(target[1]) - float(origin[1])
    if math.hypot(east, north) <= 1e-9:
        return 0.0
    return math.degrees(math.atan2(east, north)) % 360.0


def _stable_lane(entity_id: str) -> tuple[int, float]:
    digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
    sign = -1 if digest[-1] % 2 else 1
    phase = int.from_bytes(digest[1:5], "big") / float(2**32)
    return sign, phase


class FormalRuleAgentTeamV2:
    """Two opposing policies bridged to a Session only through public V2 DTOs."""

    def __init__(self, profile: FormalRuleAgentProfileV2, *, seed: int) -> None:
        self.profile = profile
        self.seed = seed
        self.last_decision: RuleAgentDecisionV2 | None = None
        self._last_fired: dict[tuple[str, str], int] = {}
        self._commanded_attack_entities: set[str] = set()
        self._contact_triggered_attack_entities: set[str] = set()

    @classmethod
    def for_scenario(cls, public_id: str, *, seed: int) -> FormalRuleAgentTeamV2:
        return cls(load_formal_rule_agent_profile_v2(public_id), seed=seed)

    def _attack_heading(
        self,
        entity_id: str,
        position: tuple[float, ...],
        tick: int,
        *,
        contact_triggered: bool,
    ) -> float:
        attack = self.profile.attack
        base = _heading_to(position, self.profile.objective_m)
        sign, phase = _stable_lane(entity_id)
        if attack.pattern == "direct":
            return base
        if attack.pattern == "split_evasion":
            angle = attack.split_angle_deg
            if contact_triggered:
                angle += attack.contact_turn_deg
            return (base + sign * angle) % 360.0
        cycle = 2.0 * math.pi * (tick / attack.serpentine_period_ticks + phase)
        return (
            base
            + sign
            * (attack.split_angle_deg + (attack.contact_turn_deg if contact_triggered else 0.0))
            + attack.serpentine_angle_deg * math.sin(cycle)
        ) % 360.0

    def _attack_speed(self, entity_id: str, tick: int) -> float:
        """Select a deterministic profile-defined speed without hidden world state."""

        attack = self.profile.attack
        values = attack.speed_cycle_mps or (attack.speed_mps,)
        digest = hashlib.sha256(f"{self.seed}:{entity_id}".encode()).digest()
        phase = int.from_bytes(digest[:4], "big") % len(values)
        return values[(phase + tick // attack.speed_cycle_ticks) % len(values)]

    @staticmethod
    def _authority_by_entity(session: SessionLifecycleV2) -> dict[str, str]:
        return {
            grant.entity_id: token for token, grant in session.world_view.authority_tokens.items()
        }

    @staticmethod
    def _own_by_id(observation: ObservationV2) -> dict[str, dict[str, object]]:
        return {str(item["entity_id"]): item for item in observation.own_entities}

    def _submit(
        self,
        session: SessionLifecycleV2,
        *,
        faction_id: str,
        entity_id: str,
        token: str,
        tick: int,
        valid_until_tick: int,
        command: PersistentCommandV2,
        action: DiscreteActionV2 | None,
    ) -> None:
        children = () if action is None else (action,)
        suffix = f"{entity_id}.{tick}"
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id=f"rule.batch.{suffix}",
                idempotency_key=f"rule.idempotency.{suffix}",
                faction_id=faction_id,
                based_on_tick=tick,
                valid_until_tick=valid_until_tick,
                persistent_commands=(command,),
                discrete_actions=children,
            ),
            authority_token=token,
            operation_id=f"rule.submit.{suffix}",
            expected_tick=tick,
        )

    def __call__(self, session: SessionLifecycleV2) -> None:
        tick = session.world_view.tick
        tokens = self._authority_by_entity(session)
        attack_observation = session.world_view.observation(
            observer_faction_id=self.profile.attack.faction_id
        )
        defence_observation = session.world_view.observation(
            observer_faction_id=self.profile.defence.faction_id
        )
        attack_commands: list[str] = []
        defence_commands: list[str] = []
        fire_actions: list[str] = []
        fire_contacts: list[str] = []
        attack_headings: list[float] = []
        refresh = tick % self.profile.decision_interval_ticks == 0
        valid_until_tick = tick + self.profile.decision_interval_ticks
        attack_contact_owners = {
            str(contact["observer_entity_id"])
            for contact in attack_observation.contacts_by_faction.get(
                self.profile.attack.faction_id, ()
            )
            if "observer_entity_id" in contact
        }
        if self.profile.attack.turn_on_first_contact:
            self._contact_triggered_attack_entities.update(attack_contact_owners)

        for entity_id, state in sorted(self._own_by_id(attack_observation).items()):
            token = tokens.get(entity_id)
            if token is None or state.get("lifecycle_state") not in {"active", "degraded"}:
                continue
            if entity_id in self._commanded_attack_entities and not refresh:
                continue
            position = tuple(float(value) for value in cast(Sequence[float], state["position_m"]))
            heading = self._attack_heading(
                entity_id,
                position,
                tick,
                contact_triggered=(
                    self.profile.attack.turn_on_first_contact
                    and entity_id in self._contact_triggered_attack_entities
                ),
            )
            command_id = f"rule.attack.navigation.{entity_id}.{tick}"
            command = PersistentCommandV2(
                schema_version="2.0",
                command_id=command_id,
                command_type="navigation",
                entity_id=entity_id,
                faction_id=self.profile.attack.faction_id,
                based_on_tick=tick,
                valid_until_tick=valid_until_tick,
                payload={
                    "speed_mps": self._attack_speed(entity_id, tick),
                    "heading_deg": heading,
                    "altitude_m": position[2],
                },
            )
            self._submit(
                session,
                faction_id=self.profile.attack.faction_id,
                entity_id=entity_id,
                token=token,
                tick=tick,
                valid_until_tick=valid_until_tick,
                command=command,
                action=None,
            )
            attack_commands.append(command_id)
            attack_headings.append(heading)
            self._commanded_attack_entities.add(entity_id)

        contacts = tuple(
            contact
            for contact in defence_observation.contacts_by_faction.get(
                self.profile.defence.faction_id, ()
            )
            if float(contact["confidence"]) >= self.profile.defence.contact_confidence
            and int(contact["age_ticks"]) <= self.profile.defence.maximum_contact_age_ticks
        )
        contacts = tuple(
            sorted(
                contacts,
                key=lambda item: (
                    math.dist(item["estimated_position_m"][:2], self.profile.objective_m),
                    str(item["contact_id"]),
                ),
            )
        )
        defence_by_id = self._own_by_id(defence_observation)
        for entity in session.world_view.entities_stable():
            entity_id = entity.id
            defence_state = defence_by_id.get(entity_id)
            token = tokens.get(entity_id)
            if (
                defence_state is None
                or token is None
                or defence_state.get("lifecycle_state")
                not in {
                    "active",
                    "degraded",
                }
            ):
                continue
            tags = frozenset(entity.definition.tags)
            weapon_policy = next(
                (
                    policy
                    for policy in self.profile.defence.weapon_policies
                    if set(policy.selector_tags) <= tags
                ),
                None,
            )
            if weapon_policy is None:
                continue
            if not refresh:
                continue
            own_position = tuple(
                float(value) for value in cast(Sequence[float], defence_state["position_m"])
            )
            track = contacts[0] if contacts else None
            target_position = (
                self.profile.objective_m
                if track is None
                else tuple(float(value) for value in track["estimated_position_m"])
            )
            heading = _heading_to(own_position, target_position)
            command_id = f"rule.defence.navigation.{entity_id}.{tick}"
            command = PersistentCommandV2(
                schema_version="2.0",
                command_id=command_id,
                command_type="navigation",
                entity_id=entity_id,
                faction_id=self.profile.defence.faction_id,
                based_on_tick=tick,
                valid_until_tick=valid_until_tick,
                payload={
                    "speed_mps": self.profile.defence.intercept_speed_mps,
                    "heading_deg": heading,
                    "altitude_m": own_position[2],
                },
            )
            action: DiscreteActionV2 | None = None
            owned_tracks = tuple(
                item for item in contacts if item["observer_entity_id"] == entity_id
            )
            for owned_track in owned_tracks:
                distance = math.dist(own_position, owned_track["estimated_position_m"])
                last_tick = self._last_fired.get((entity_id, weapon_policy.weapon_ref), -(10**9))
                if (
                    weapon_policy.minimum_range_m <= distance <= weapon_policy.maximum_range_m
                    and tick - last_tick >= weapon_policy.cooldown_ticks
                ):
                    contact_id = str(owned_track["contact_id"])
                    action_id = f"rule.defence.fire.{entity_id}.{tick}"
                    action = DiscreteActionV2(
                        schema_version="2.0",
                        action_id=action_id,
                        action_type="fire_weapon",
                        entity_id=entity_id,
                        faction_id=self.profile.defence.faction_id,
                        based_on_tick=tick,
                        valid_until_tick=tick,
                        payload={
                            "weapon_ref": weapon_policy.weapon_ref,
                            "contact_id": contact_id,
                        },
                    )
                    self._last_fired[(entity_id, weapon_policy.weapon_ref)] = tick
                    fire_actions.append(action_id)
                    fire_contacts.append(contact_id)
                    break
            self._submit(
                session,
                faction_id=self.profile.defence.faction_id,
                entity_id=entity_id,
                token=token,
                tick=tick,
                valid_until_tick=valid_until_tick,
                command=command,
                action=action,
            )
            defence_commands.append(command_id)

        self.last_decision = RuleAgentDecisionV2(
            tick=tick,
            observation_ticks=(attack_observation.tick, defence_observation.tick),
            attack_command_ids=tuple(attack_commands),
            defence_command_ids=tuple(defence_commands),
            fire_action_ids=tuple(fire_actions),
            fire_contact_ids=tuple(fire_contacts),
            attack_headings_deg=tuple(attack_headings),
        )


__all__ = [
    "AttackRuleConfigV2",
    "DefenceRuleConfigV2",
    "FormalRuleAgentProfileV2",
    "FormalRuleAgentTeamV2",
    "RuleAgentDecisionV2",
    "WeaponRuleConfigV2",
    "load_formal_rule_agent_profile_v2",
]

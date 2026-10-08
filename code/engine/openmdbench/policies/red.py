"""Red ingress/evasion baseline using only its public observation."""

from __future__ import annotations

import math
from enum import StrEnum

from openmdbench.policies.actions import ActionBatch, PlatformAction
from openmdbench.schemas.observation import DetectedContact, Observation


class RedState(StrEnum):
    INGRESS = "INGRESS"
    EVADE = "EVADE"
    BREACH = "BREACH"
    DESTROYED = "DESTROYED"
    TIMEOUT = "TIMEOUT"


class RedIngressAgent:
    def __init__(
        self,
        protected_point: tuple[float, float, float],
        *,
        protected_radius_m: float = 500.0,
        cruise_speed_mps: float = 40.0,
    ) -> None:
        self.protected_point = protected_point
        self.protected_radius_m = protected_radius_m
        self.cruise_speed_mps = cruise_speed_mps
        self.state = RedState.INGRESS
        self._clear_ticks = 0

    def reset(self, observation: Observation, seed: int) -> None:
        del observation, seed
        self.state = RedState.INGRESS
        self._clear_ticks = 0

    @staticmethod
    def _distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
        return math.dist(first, second)

    def _evasion_heading(
        self,
        position: tuple[float, float, float],
        threat: DetectedContact,
    ) -> float:
        east = self.protected_point[0] - position[0]
        north = self.protected_point[1] - position[1]
        ingress_heading = math.degrees(math.atan2(east, north)) % 360.0
        candidates = (-45.0, -30.0, -15.0, 0.0, 15.0, 30.0, 45.0)
        scored: list[tuple[float, float, float]] = []
        for offset in candidates:
            heading = (ingress_heading + offset) % 360.0
            radians = math.radians(heading)
            next_position = (
                position[0] + self.cruise_speed_mps * math.sin(radians),
                position[1] + self.cruise_speed_mps * math.cos(radians),
                position[2],
            )
            scored.append((self._distance(next_position, threat.position), -offset, heading))
        return max(scored)[2]

    def act(self, observation: Observation) -> ActionBatch:
        friendlies = observation.situational_data.friendly_assets
        if not friendlies:
            self.state = RedState.DESTROYED
            return ActionBatch(timestamp=observation.timestamp, actions=())
        ownship = min(friendlies, key=lambda asset: asset.id)
        if observation.time_remaining == 0:
            self.state = RedState.TIMEOUT
        elif self._distance(ownship.position, self.protected_point) <= self.protected_radius_m:
            self.state = RedState.BREACH
        contacts = sorted(
            observation.situational_data.detected_contacts,
            key=lambda contact: (self._distance(ownship.position, contact.position), contact.id),
        )
        nearest = contacts[0] if contacts else None
        nearest_distance = (
            self._distance(ownship.position, nearest.position) if nearest is not None else math.inf
        )
        if self.state in {RedState.INGRESS, RedState.EVADE}:
            if nearest is not None and nearest_distance < 6_000.0:
                self.state = RedState.EVADE
                self._clear_ticks = 0
            elif self.state is RedState.EVADE:
                self._clear_ticks = self._clear_ticks + 1 if nearest_distance > 8_000.0 else 0
                if self._clear_ticks >= 5:
                    self.state = RedState.INGRESS
                    self._clear_ticks = 0
        if self.state in {RedState.BREACH, RedState.DESTROYED, RedState.TIMEOUT}:
            action = PlatformAction(entity_id=ownship.id, navigation="hold_position")
        elif self.state is RedState.EVADE and nearest is not None:
            heading = self._evasion_heading(ownship.position, nearest)
            radians = math.radians(heading)
            target = (
                ownship.position[0] + 10_000.0 * math.sin(radians),
                ownship.position[1] + 10_000.0 * math.cos(radians),
                ownship.position[2],
            )
            action = PlatformAction(
                entity_id=ownship.id,
                navigation="move_to",
                target=target,
                speed_mps=self.cruise_speed_mps,
            )
        else:
            action = PlatformAction(
                entity_id=ownship.id,
                navigation="move_to",
                target=self.protected_point,
                speed_mps=self.cruise_speed_mps,
            )
        return ActionBatch(
            timestamp=observation.timestamp,
            actions=(action,),
            high_level_intent={"state": self.state.value},
        )

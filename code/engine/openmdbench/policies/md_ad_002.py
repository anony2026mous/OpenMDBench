"""Deterministic EASY baselines using only public observations."""

from __future__ import annotations

import math

from openmdbench.core.rng import SessionRNG
from openmdbench.policies.actions import ActionBatch, PlatformAction
from openmdbench.schemas.md_ad_002_interface import (
    CommunicationAction,
    EngagementAction,
    NavigationAction,
    RedActionBatch,
    RedObservation,
    RedPlatformAction,
    SensorAction,
)
from openmdbench.schemas.observation import Observation


class AD2RedBaselineAgent:
    def __init__(self, protected_point: tuple[float, float]) -> None:
        self.protected_point = protected_point
        self.last_fired: dict[tuple[str, str], int] = {}

    def reset(self, observation: RedObservation, seed: int) -> None:
        del observation, seed
        self.last_fired.clear()

    def snapshot(self) -> dict[str, object]:
        return {
            "last_fired": [
                [entity_id, weapon_id, tick]
                for (entity_id, weapon_id), tick in sorted(self.last_fired.items())
            ]
        }

    def restore(self, snapshot: dict[str, object]) -> None:
        records = snapshot.get("last_fired", [])
        if not isinstance(records, list):
            raise ValueError("invalid red agent checkpoint")
        self.last_fired = {
            (str(entity_id), str(weapon_id)): int(tick) for entity_id, weapon_id, tick in records
        }

    def act(self, observation: RedObservation) -> RedActionBatch:
        contacts = sorted(
            (
                contact
                for contact in observation.contacts
                if contact.confidence >= 0.7 and contact.age <= 10
            ),
            key=lambda contact: (
                math.dist(contact.position_m[:2], self.protected_point),
                contact.contact_id,
            ),
        )
        assigned: set[str] = set()
        actions: list[RedPlatformAction] = []
        for asset in sorted(observation.own_forces, key=lambda item: item.entity_id):
            if asset.operational_status not in {"active", "degraded"}:
                continue
            engagement = None
            navigation = NavigationAction(mode="hold_position")
            sensor = SensorAction(mode="active_search")
            if asset.platform_type == "uav":
                available = next(
                    (contact for contact in contacts if contact.contact_id not in assigned), None
                )
                if available is not None:
                    navigation = NavigationAction(
                        mode="move_to", target_m=available.position_m, speed_mps=40.0
                    )
                    distance = math.dist(asset.position_m, available.position_m)
                    if (
                        500.0 <= distance <= 8_000.0
                        and asset.weapons.get("uav_interceptor_missile", 0) > 0
                        and observation.timestamp
                        - self.last_fired.get((asset.entity_id, "uav_interceptor_missile"), -5)
                        >= 5
                        and math.dist(available.position_m[:2], self.protected_point) > 8_000.0
                        and asset.communication_status in {"connected", "relayed"}
                    ):
                        engagement = EngagementAction(
                            contact_id=available.contact_id,
                            weapon_id="uav_interceptor_missile",
                        )
                        assigned.add(available.contact_id)
                        self.last_fired[(asset.entity_id, "uav_interceptor_missile")] = (
                            observation.timestamp
                        )
            elif asset.platform_type == "shore_radar":
                available = next(
                    (
                        contact
                        for contact in contacts
                        if contact.contact_id not in assigned
                        and 300.0 <= math.dist(asset.position_m, contact.position_m) <= 2_000.0
                    ),
                    None,
                )
                if available is not None and asset.weapons.get("shore_ciws", 0) > 0:
                    engagement = EngagementAction(
                        contact_id=available.contact_id, weapon_id="shore_ciws"
                    )
                    assigned.add(available.contact_id)
            actions.append(
                RedPlatformAction(
                    entity_id=asset.entity_id,
                    navigation=navigation,
                    sensor=sensor,
                    communication=CommunicationAction(
                        relay_enabled=(
                            observation.scenario_id == "MD-AD-002-HARD"
                            and asset.platform_type == "usv"
                        )
                    ),
                    engagement=engagement,
                    ciws_auto=asset.platform_type == "shore_radar",
                )
            )
        return RedActionBatch(
            scenario_id=observation.scenario_id,
            timestamp=observation.timestamp,
            actions=tuple(actions),
            high_level_intent={"strategy": "forward_intercept", "assigned": sorted(assigned)},
        )


class AD2EasyBlueAgent:
    def __init__(self, protected_point: tuple[float, float, float]) -> None:
        self.protected_point = protected_point

    def reset(self, observation: Observation, seed: int) -> None:
        del observation, seed

    def snapshot(self) -> dict[str, object]:
        return {}

    def restore(self, snapshot: dict[str, object]) -> None:
        if snapshot:
            raise ValueError("invalid EASY blue agent checkpoint")

    def act(self, observation: Observation) -> ActionBatch:
        return ActionBatch(
            timestamp=observation.timestamp,
            actions=tuple(
                PlatformAction(
                    entity_id=asset.id,
                    navigation="move_to",
                    target=(self.protected_point[0], self.protected_point[1], asset.position[2]),
                    speed_mps=45.0,
                )
                for asset in sorted(
                    observation.situational_data.friendly_assets, key=lambda item: item.id
                )
                if asset.type == "uav"
            ),
            high_level_intent={"strategy": "easy_direct_ingress"},
        )


class AD2MediumBlueAgent:
    """Public-only split ingress with one event-triggered evasive turn per asset."""

    def __init__(self, protected_point: tuple[float, float, float]) -> None:
        self.protected_point = protected_point
        self.rng = SessionRNG(0)
        self.evasion_until: dict[str, int] = {}
        self.evasion_angle: dict[str, float] = {}
        self.processed_engagement_ticks: set[int] = set()

    def reset(self, observation: Observation, seed: int) -> None:
        del observation
        self.rng.reset(seed)
        self.evasion_until.clear()
        self.evasion_angle.clear()
        self.processed_engagement_ticks.clear()

    def snapshot(self) -> dict[str, object]:
        return {
            "rng": self.rng.snapshot(),
            "evasion_until": dict(sorted(self.evasion_until.items())),
            "evasion_angle": dict(sorted(self.evasion_angle.items())),
            "processed_engagement_ticks": sorted(self.processed_engagement_ticks),
        }

    def restore(self, snapshot: dict[str, object]) -> None:
        rng = snapshot.get("rng")
        until = snapshot.get("evasion_until")
        angles = snapshot.get("evasion_angle")
        ticks = snapshot.get("processed_engagement_ticks")
        if (
            not isinstance(rng, dict)
            or not isinstance(until, dict)
            or not isinstance(angles, dict)
            or not isinstance(ticks, list)
        ):
            raise ValueError("invalid MEDIUM blue agent checkpoint")
        self.rng = SessionRNG.from_snapshot(rng)
        self.evasion_until = {str(key): int(value) for key, value in until.items()}
        self.evasion_angle = {str(key): float(value) for key, value in angles.items()}
        self.processed_engagement_ticks = {int(value) for value in ticks}

    @staticmethod
    def _rotate(east: float, north: float, angle_deg: float) -> tuple[float, float]:
        angle = math.radians(angle_deg)
        return (
            east * math.cos(angle) - north * math.sin(angle),
            east * math.sin(angle) + north * math.cos(angle),
        )

    def act(self, observation: Observation) -> ActionBatch:
        assets = tuple(
            asset
            for asset in sorted(
                observation.situational_data.friendly_assets, key=lambda item: item.id
            )
            if asset.type == "uav"
        )
        engagement_count = (
            sum(event.get("event_type") == "engagement" for event in observation.event_log)
            if observation.timestamp not in self.processed_engagement_ticks
            else 0
        )
        if engagement_count:
            self.processed_engagement_ticks.add(observation.timestamp)
        candidates = [asset for asset in assets if asset.id not in self.evasion_angle]
        for asset in candidates[:engagement_count]:
            magnitude = float(self.rng.stream(f"medium_evasion:{asset.id}").uniform(20.0, 35.0))
            sign = -1.0 if int(asset.id.rsplit("-", 1)[-1]) % 2 else 1.0
            self.evasion_angle[asset.id] = sign * magnitude
            self.evasion_until[asset.id] = observation.timestamp + 10

        actions: list[PlatformAction] = []
        for asset in assets:
            east = self.protected_point[0] - asset.position[0]
            north = self.protected_point[1] - asset.position[1]
            index = int(asset.id.rsplit("-", 1)[-1])
            split_angle = 15.0 if index % 4 in {3, 0} else 0.0
            evasion_angle = (
                self.evasion_angle.get(asset.id, 0.0)
                if observation.timestamp < self.evasion_until.get(asset.id, -1)
                else 0.0
            )
            target_east, target_north = self._rotate(east, north, split_angle + evasion_angle)
            actions.append(
                PlatformAction(
                    entity_id=asset.id,
                    navigation="move_to",
                    target=(
                        asset.position[0] + target_east,
                        asset.position[1] + target_north,
                        asset.position[2],
                    ),
                    speed_mps=max(30.0, min(45.0, math.hypot(*asset.velocity[:2]))),
                )
            )
        return ActionBatch(
            timestamp=observation.timestamp,
            actions=tuple(actions),
            high_level_intent={
                "strategy": "medium_split_single_evasion",
                "evading": sorted(
                    entity_id
                    for entity_id, until in self.evasion_until.items()
                    if observation.timestamp < until
                ),
            },
        )


class AD2HardBlueAgent:
    """Public-only multi-axis ingress with continuous deterministic serpentine motion."""

    def __init__(self, protected_point: tuple[float, float, float]) -> None:
        self.protected_point = protected_point

    def reset(self, observation: Observation, seed: int) -> None:
        del observation, seed

    def snapshot(self) -> dict[str, object]:
        return {}

    def restore(self, snapshot: dict[str, object]) -> None:
        if snapshot:
            raise ValueError("invalid HARD blue agent checkpoint")

    def act(self, observation: Observation) -> ActionBatch:
        actions: list[PlatformAction] = []
        for asset in sorted(observation.situational_data.friendly_assets, key=lambda item: item.id):
            if asset.type != "uav":
                continue
            index = int(asset.id.rsplit("-", 1)[-1])
            axis_angle = (-20.0, -10.0, 10.0, 20.0)[index % 4]
            phase = (observation.timestamp + index * 5) % 40
            serpentine = 18.0 if phase < 20 else -18.0
            east = self.protected_point[0] - asset.position[0]
            north = self.protected_point[1] - asset.position[1]
            target_east, target_north = AD2MediumBlueAgent._rotate(
                east, north, axis_angle + serpentine
            )
            actions.append(
                PlatformAction(
                    entity_id=asset.id,
                    navigation="move_to",
                    target=(
                        asset.position[0] + target_east,
                        asset.position[1] + target_north,
                        asset.position[2],
                    ),
                    speed_mps=max(30.0, min(45.0, math.hypot(*asset.velocity[:2]))),
                )
            )
        return ActionBatch(
            timestamp=observation.timestamp,
            actions=tuple(actions),
            high_level_intent={
                "strategy": "hard_multi_axis_continuous_serpentine",
                "phase": observation.timestamp % 40,
            },
        )

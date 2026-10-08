"""Fixed-slot Gymnasium adapter over the canonical MD-AD-002 DTOs."""

from __future__ import annotations

from typing import Any, cast

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from numpy.typing import NDArray

from openmdbench.envs.benchmark import OpenMDBenchEnv
from openmdbench.schemas.md_ad_002_interface import (
    CommunicationAction,
    EngagementAction,
    NavigationAction,
    RedActionBatch,
    RedObservation,
    RedPlatformAction,
    SensorAction,
)

NAVIGATION_MODES = ("hold_position", "move_to", "patrol", "guard", "active_search")
SENSOR_MODES = (None, "off", "passive", "active_search")
WEAPON_IDS = (None, "uav_interceptor_missile", "shore_ciws")


class MDAD002GymEnv(gym.Env[dict[str, NDArray[Any]], dict[str, NDArray[Any]]]):
    """Expose canonical actions through deterministic fixed-size numeric slots."""

    metadata = {"render_modes": []}

    def __init__(self, scenario_id: str = "MD-AD-002-EASY", seed: int | None = None) -> None:
        super().__init__()
        self.core = OpenMDBenchEnv(scenario_id=scenario_id, seed=seed)
        self.scenario_id = scenario_id
        self.entity_ids: tuple[str, ...] = ()
        finite = np.finfo(np.float32).max
        self.action_space = spaces.Dict(
            {
                "action_mask": spaces.MultiBinary(7),
                "navigation_mode": spaces.MultiDiscrete(np.full(7, 5, dtype=np.int64)),
                "target_m": spaces.Box(-finite, finite, shape=(7, 3), dtype=np.float32),
                "speed_mps": spaces.Box(0.0, 80.0, shape=(7,), dtype=np.float32),
                "sensor_mode": spaces.MultiDiscrete(np.full(7, 4, dtype=np.int64)),
                "relay_enabled": spaces.MultiBinary(7),
                "engagement_mask": spaces.MultiBinary(7),
                "contact_slot": spaces.MultiDiscrete(np.full(7, 15, dtype=np.int64)),
                "weapon": spaces.MultiDiscrete(np.full(7, 3, dtype=np.int64)),
                "ciws_auto": spaces.MultiDiscrete(np.full(7, 3, dtype=np.int64)),
            }
        )
        self.observation_space = spaces.Dict(
            {
                "timestamp": spaces.Box(0, 1_800, shape=(1,), dtype=np.int32),
                "own_mask": spaces.MultiBinary(7),
                "own_state": spaces.Box(-finite, finite, shape=(7, 12), dtype=np.float32),
                "contact_mask": spaces.MultiBinary(15),
                "contact_state": spaces.Box(-finite, finite, shape=(15, 10), dtype=np.float32),
                "mission_state": spaces.Box(-finite, finite, shape=(3,), dtype=np.float32),
            }
        )

    @staticmethod
    def _encoded(observation: RedObservation) -> dict[str, NDArray[Any]]:
        own_mask = np.zeros(7, dtype=np.int8)
        own_state = np.zeros((7, 12), dtype=np.float32)
        for slot, entity in enumerate(observation.own_forces[:7]):
            own_mask[slot] = 1
            own_state[slot] = np.asarray(
                (
                    *entity.position_m,
                    *entity.velocity_mps,
                    entity.heading_deg,
                    entity.health,
                    entity.energy,
                    float(sum(entity.weapons.values())),
                    float(entity.communication_status in {"connected", "relayed"}),
                    float(entity.sensor_mode != "off"),
                ),
                dtype=np.float32,
            )
        contact_mask = np.zeros(15, dtype=np.int8)
        contact_state = np.zeros((15, 10), dtype=np.float32)
        for slot, contact in enumerate(observation.contacts[:15]):
            contact_mask[slot] = 1
            contact_state[slot] = np.asarray(
                (
                    *contact.position_m,
                    *contact.velocity_mps,
                    contact.confidence,
                    contact.uncertainty_m,
                    float(contact.age),
                    float(contact.estimated_domain == "air"),
                ),
                dtype=np.float32,
            )
        mission = observation.mission_status
        time_remaining = mission.get("time_remaining", 0)
        breach_count = mission.get("breach_count", 0)
        if not isinstance(time_remaining, (int, float)) or not isinstance(
            breach_count, (int, float)
        ):
            raise RuntimeError("invalid numeric mission status")
        return {
            "timestamp": np.asarray([observation.timestamp], dtype=np.int32),
            "own_mask": own_mask,
            "own_state": own_state,
            "contact_mask": contact_mask,
            "contact_state": contact_state,
            "mission_state": np.asarray(
                (
                    float(time_remaining),
                    float(breach_count),
                    float(mission.get("status") != "in_progress"),
                ),
                dtype=np.float32,
            ),
        }

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, NDArray[Any]], dict[str, Any]]:
        super().reset(seed=seed)
        self.core.reset(seed=seed, options=options)
        public = self.core.red_observation()
        self.entity_ids = tuple(entity.entity_id for entity in public.own_forces)
        encoded = self._encoded(public)
        return encoded, {"red_observation": public.model_dump(mode="json")}

    def _batch(self, action: dict[str, NDArray[Any]]) -> RedActionBatch:
        if not self.action_space.contains(action):
            raise ValueError("action does not belong to MD-AD-002 action_space")
        public = self.core.red_observation()
        contacts = tuple(contact.contact_id for contact in public.contacts[:15])
        actions: list[RedPlatformAction] = []
        for slot, entity_id in enumerate(self.entity_ids):
            if not bool(action["action_mask"][slot]):
                continue
            mode = cast(Any, NAVIGATION_MODES[int(action["navigation_mode"][slot])])
            target_values = action["target_m"][slot]
            target = (
                float(target_values[0]),
                float(target_values[1]),
                float(target_values[2]),
            )
            navigation = NavigationAction(
                mode=mode,
                target_m=target if mode in {"move_to", "patrol", "guard"} else None,
                speed_mps=float(action["speed_mps"][slot]),
            )
            sensor_index = int(action["sensor_mode"][slot])
            sensor = (
                SensorAction(mode=cast(Any, SENSOR_MODES[sensor_index]))
                if SENSOR_MODES[sensor_index] is not None
                else None
            )
            engagement = None
            if bool(action["engagement_mask"][slot]):
                contact_slot = int(action["contact_slot"][slot])
                weapon = WEAPON_IDS[int(action["weapon"][slot])]
                if contact_slot >= len(contacts) or weapon is None:
                    raise ValueError("engagement references an empty contact/weapon slot")
                engagement = EngagementAction(
                    contact_id=contacts[contact_slot], weapon_id=cast(Any, weapon)
                )
            actions.append(
                RedPlatformAction(
                    entity_id=entity_id,
                    navigation=navigation,
                    sensor=sensor,
                    communication=CommunicationAction(
                        relay_enabled=bool(action["relay_enabled"][slot])
                    ),
                    engagement=engagement,
                    ciws_auto=(
                        None
                        if int(action["ciws_auto"][slot]) == 0
                        else int(action["ciws_auto"][slot]) == 2
                    ),
                )
            )
        return RedActionBatch(
            scenario_id=cast(Any, self.scenario_id),
            timestamp=public.timestamp,
            actions=tuple(actions),
        )

    def encode_action_batch(self, batch: RedActionBatch) -> dict[str, NDArray[Any]]:
        """Encode the canonical DTO without changing policy decisions."""
        public = self.core.red_observation()
        if batch.timestamp != public.timestamp or batch.scenario_id != public.scenario_id:
            raise ValueError("action batch does not match current Gym observation")
        contacts = {contact.contact_id: slot for slot, contact in enumerate(public.contacts[:15])}
        slots = {entity_id: slot for slot, entity_id in enumerate(self.entity_ids)}
        encoded: dict[str, NDArray[Any]] = {
            "action_mask": np.zeros(7, dtype=np.int8),
            "navigation_mode": np.zeros(7, dtype=np.int64),
            "target_m": np.zeros((7, 3), dtype=np.float32),
            "speed_mps": np.zeros(7, dtype=np.float32),
            "sensor_mode": np.zeros(7, dtype=np.int64),
            "relay_enabled": np.zeros(7, dtype=np.int8),
            "engagement_mask": np.zeros(7, dtype=np.int8),
            "contact_slot": np.zeros(7, dtype=np.int64),
            "weapon": np.zeros(7, dtype=np.int64),
            "ciws_auto": np.zeros(7, dtype=np.int64),
        }
        for item in batch.actions:
            if item.entity_id not in slots:
                raise ValueError(f"action entity has no Gym slot: {item.entity_id}")
            slot = slots[item.entity_id]
            encoded["action_mask"][slot] = 1
            encoded["navigation_mode"][slot] = NAVIGATION_MODES.index(item.navigation.mode)
            if item.navigation.target_m is not None:
                encoded["target_m"][slot] = item.navigation.target_m
            encoded["speed_mps"][slot] = item.navigation.speed_mps
            if item.sensor is not None:
                encoded["sensor_mode"][slot] = SENSOR_MODES.index(item.sensor.mode)
            if item.communication is not None:
                encoded["relay_enabled"][slot] = item.communication.relay_enabled
            if item.engagement is not None:
                if item.engagement.contact_id not in contacts:
                    raise ValueError("engagement contact has no Gym slot")
                encoded["engagement_mask"][slot] = 1
                encoded["contact_slot"][slot] = contacts[item.engagement.contact_id]
                encoded["weapon"][slot] = WEAPON_IDS.index(item.engagement.weapon_id)
            if item.ciws_auto is not None:
                encoded["ciws_auto"][slot] = 2 if item.ciws_auto else 1
        if not self.action_space.contains(encoded):
            raise RuntimeError("canonical action could not be represented by Gym space")
        return encoded

    def step(
        self, action: dict[str, NDArray[Any]]
    ) -> tuple[dict[str, NDArray[Any]], float, bool, bool, dict[str, Any]]:
        batch = self._batch(action)
        public, reward, terminated, truncated, info = self.core.step_red_action_batch(batch)
        return (
            self._encoded(public),
            reward,
            terminated,
            truncated,
            {
                **info,
                "red_observation": public.model_dump(mode="json"),
            },
        )

    def close(self) -> None:
        self.core.close()

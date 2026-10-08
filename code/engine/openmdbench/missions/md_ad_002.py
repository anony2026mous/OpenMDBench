"""Latched per-target breach adjudication for the MD-AD-002 scenario family."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from openmdbench.core.entities import Lifecycle, PlatformAsset, Side
from openmdbench.core.world import WorldState


class MDAD002Outcome(StrEnum):
    IN_PROGRESS = "in_progress"
    BLUE_SUCCESS = "blue_success"
    RED_SUCCESS = "red_success"
    TERMINATED = "terminated"


@dataclass(frozen=True, slots=True)
class MDAD002Result:
    outcome: MDAD002Outcome
    reason: str
    breach_count: int
    terminal: bool


class MDAD002Adjudicator:
    def __init__(
        self,
        *,
        protected_point: tuple[float, float],
        protection_radius_m: float = 8_000.0,
        breach_threshold: int = 3,
        time_limit_ticks: int = 1_800,
        total_threats: int = 15,
    ) -> None:
        self.protected_point = protected_point
        self.protection_radius_m = protection_radius_m
        self.breach_threshold = breach_threshold
        self.time_limit_ticks = time_limit_ticks
        self.total_threats = total_threats
        self.breached_ids: set[str] = set()
        self.events: list[dict[str, object]] = []
        self.result = MDAD002Result(MDAD002Outcome.IN_PROGRESS, "in_progress", 0, False)

    def latch_breaches(
        self,
        world: WorldState,
        tick: int,
        *,
        previous_positions: dict[str, tuple[float, float, float]] | None = None,
    ) -> tuple[str, ...]:
        previous_positions = previous_positions or {}
        newly_breached: list[str] = []
        for entity in world.entities_for_side(Side.BLUE):
            if not isinstance(entity, PlatformAsset) or entity.lifecycle not in {
                Lifecycle.ACTIVE,
                Lifecycle.DEGRADED,
                Lifecycle.BREACHED_ACTIVE,
            }:
                continue
            start = previous_positions.get(entity.id, entity.position)
            segment_x = entity.position[0] - start[0]
            segment_y = entity.position[1] - start[1]
            length_squared = segment_x**2 + segment_y**2
            projection = (
                0.0
                if length_squared == 0.0
                else max(
                    0.0,
                    min(
                        1.0,
                        (
                            (self.protected_point[0] - start[0]) * segment_x
                            + (self.protected_point[1] - start[1]) * segment_y
                        )
                        / length_squared,
                    ),
                )
            )
            closest = (
                start[0] + projection * segment_x,
                start[1] + projection * segment_y,
            )
            if math.dist(closest, self.protected_point) > self.protection_radius_m:
                continue
            if entity.id not in self.breached_ids:
                self.breached_ids.add(entity.id)
                newly_breached.append(entity.id)
                self.events.append(
                    {
                        "tick": tick,
                        "event_type": "breach_latched",
                        "entity_id": entity.id,
                        "breach_count": len(self.breached_ids),
                    }
                )
            if entity.lifecycle is not Lifecycle.BREACHED_ACTIVE:
                world.registry.update(
                    entity.model_copy(update={"lifecycle": Lifecycle.BREACHED_ACTIVE})
                )
        return tuple(newly_breached)

    @staticmethod
    def _resources_exhausted(world: WorldState) -> bool:
        red = tuple(
            entity
            for entity in world.entities_for_side(Side.RED)
            if isinstance(entity, PlatformAsset)
        )
        uavs = tuple(entity for entity in red if entity.platform_type == "uav")
        shore = tuple(entity for entity in red if entity.platform_type == "shore_radar")
        uavs_unavailable = all(
            entity.lifecycle
            not in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
            for entity in uavs
        )
        missiles_empty = all(
            entity.components.weapon_inventory.get("uav_interceptor_missile", 0) == 0
            for entity in uavs
        )
        ciws_empty_or_unavailable = all(
            entity.components.weapon_inventory.get("shore_ciws", 0) == 0
            or entity.lifecycle not in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}
            for entity in shore
        )
        return (
            bool(uavs)
            and bool(shore)
            and uavs_unavailable
            and missiles_empty
            and ciws_empty_or_unavailable
        )

    def advance(
        self,
        world: WorldState,
        *,
        tick: int,
        scheduled_count: int,
        administrator_terminated: bool = False,
    ) -> MDAD002Result:
        if self.result.terminal:
            return self.result
        blue = tuple(
            entity
            for entity in world.entities_for_side(Side.BLUE)
            if isinstance(entity, PlatformAsset)
        )
        terminal_states = {
            Lifecycle.DESTROYED,
            Lifecycle.IMPACTED,
            Lifecycle.OUT_OF_BOUNDS,
            Lifecycle.REMOVED,
            Lifecycle.CRASHED,
        }
        all_destroyed = len(blue) == self.total_threats and all(
            entity.lifecycle is Lifecycle.DESTROYED for entity in blue
        )
        all_terminal = (
            scheduled_count == 0
            and len(blue) == self.total_threats
            and all(entity.lifecycle in terminal_states for entity in blue)
        )
        if administrator_terminated:
            outcome, reason = MDAD002Outcome.TERMINATED, "administrator_terminated"
        elif len(self.breached_ids) >= self.breach_threshold:
            outcome, reason = MDAD002Outcome.BLUE_SUCCESS, "breach_threshold_reached"
        elif self._resources_exhausted(world):
            outcome, reason = MDAD002Outcome.BLUE_SUCCESS, "red_resources_exhausted"
        elif all_destroyed:
            outcome, reason = MDAD002Outcome.RED_SUCCESS, "all_threats_destroyed"
        elif all_terminal:
            outcome, reason = MDAD002Outcome.RED_SUCCESS, "all_threats_terminal"
        elif tick >= self.time_limit_ticks:
            outcome, reason = (
                (MDAD002Outcome.BLUE_SUCCESS, "timeout_with_breaches")
                if len(self.breached_ids) >= self.breach_threshold
                else (MDAD002Outcome.RED_SUCCESS, "timeout_denial_success")
            )
        else:
            outcome, reason = MDAD002Outcome.IN_PROGRESS, "in_progress"
        self.result = MDAD002Result(
            outcome, reason, len(self.breached_ids), outcome is not MDAD002Outcome.IN_PROGRESS
        )
        if self.result.terminal:
            self.events.append(
                {
                    "tick": tick,
                    "event_type": "mission_terminal",
                    "outcome": outcome.value,
                    "reason": reason,
                    "breach_count": len(self.breached_ids),
                }
            )
        return self.result

    def snapshot(self) -> dict[str, Any]:
        return {
            "protected_point": list(self.protected_point),
            "protection_radius_m": self.protection_radius_m,
            "breach_threshold": self.breach_threshold,
            "time_limit_ticks": self.time_limit_ticks,
            "total_threats": self.total_threats,
            "breached_ids": sorted(self.breached_ids),
            "events": list(self.events),
            "result": {
                "outcome": self.result.outcome.value,
                "reason": self.result.reason,
                "breach_count": self.result.breach_count,
                "terminal": self.result.terminal,
            },
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> MDAD002Adjudicator:
        adjudicator = cls(
            protected_point=tuple(snapshot["protected_point"]),
            protection_radius_m=float(snapshot["protection_radius_m"]),
            breach_threshold=int(snapshot["breach_threshold"]),
            time_limit_ticks=int(snapshot["time_limit_ticks"]),
            total_threats=int(snapshot["total_threats"]),
        )
        adjudicator.breached_ids = set(snapshot["breached_ids"])
        adjudicator.events = list(snapshot["events"])
        result = snapshot["result"]
        adjudicator.result = MDAD002Result(
            MDAD002Outcome(result["outcome"]),
            str(result["reason"]),
            int(result["breach_count"]),
            bool(result["terminal"]),
        )
        return adjudicator

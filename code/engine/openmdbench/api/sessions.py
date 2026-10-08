"""Replaceable in-process session storage used by the REST adapter."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any, cast
from uuid import uuid4

import numpy as np

from openmdbench.core.entities import Domain, Lifecycle, PlatformAsset, Side
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.replay.audit import AuditLog
from openmdbench.replay.log import ReplayWriter
from openmdbench.schemas.md_ad_002_interface import RedActionBatch
from openmdbench.visualization.schema import (
    DetectionSets,
    ReplayMetadata,
    ScoreSets,
    SideScore,
    VisualizationDetection,
    VisualizationEntity,
    VisualizationEvent,
    VisualizationFrame,
)


@dataclass(slots=True)
class Session:
    session_id: str
    scenario_id: str
    seed: int
    env: OpenMDBenchEnv
    observation: dict[str, int | float | str | list[float]]
    total_reward: float = 0.0
    terminated: bool = False
    truncated: bool = False
    idempotency: dict[str, tuple[object, dict[str, Any]]] = field(default_factory=dict)
    action_times: list[float] = field(default_factory=list)
    audit: AuditLog | None = None
    replay: ReplayWriter | None = None
    last_heading: float = 0.0
    wave_event_count: int = 0

    @property
    def status(self) -> str:
        if self.terminated:
            return "terminated"
        if self.truncated:
            return "timeout"
        return "running"

    def checkpoint(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": "1.0",
            "scenario_id": self.scenario_id,
            "scenario_hash": self.env.scenario_hash,
            "runtime_metadata": (
                asdict(self.env._runtime.metadata) if self.env._runtime is not None else None
            ),
            "seed": self.seed,
            "simulation": self.env.export_state(),
            "mission": {"status": self.status, "timestamp": self.observation["timestamp"]},
            "event_queue": [],
            "entities": self.env.scenario.model_dump(mode="json")["entities"],
            "contacts": [],
            "sensor_tracks": [],
            "communication_queue": [],
            "metrics": {"total_reward": self.total_reward},
            "current_commands": {"velocity": self.observation["velocity"]},
            "total_reward": self.total_reward,
            "terminated": self.terminated,
            "truncated": self.truncated,
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return {**body, "checkpoint_hash": f"sha256:{hashlib.sha256(encoded).hexdigest()}"}


class SessionStore:
    def __init__(
        self,
        *,
        rate_limit: int = 60,
        rate_window_seconds: float = 1.0,
        audit_dir: str | Path | None = None,
        replay_dir: str | Path | None = None,
    ) -> None:
        if rate_limit <= 0 or rate_window_seconds <= 0:
            raise ValueError("rate limit and window must be positive")
        self._sessions: dict[str, Session] = {}
        self.rate_limit = rate_limit
        self.rate_window_seconds = rate_window_seconds
        self.audit_dir = Path(audit_dir) if audit_dir is not None else None
        self.replay_dir = Path(replay_dir) if replay_dir is not None else None

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    def create(self, scenario_id: str, seed: int) -> Session:
        env = OpenMDBenchEnv(scenario_id=scenario_id, seed=seed)
        observation, _ = env.reset(seed=seed)
        session_id = str(uuid4())
        audit = AuditLog(self.audit_dir / f"{session_id}.audit.jsonl") if self.audit_dir else None
        replay = None
        if self.replay_dir is not None:
            replay = ReplayWriter(
                self.replay_dir / f"{session_id}.replay.jsonl",
                ReplayMetadata(
                    match_id=session_id,
                    scenario_id=scenario_id,
                    seed=seed,
                    tick_seconds=1.0,
                    coordinate_system="local_enu",
                    engine_version="0.1.0",
                    config_hash=env.scenario_hash,
                    schema_versions={
                        "replay": "1.0",
                        **({"catalog": "1.0"} if env._ad2_combat is not None else {}),
                    },
                    map_identity=env.map_metadata,
                    dynamics_metadata=env.dynamics_metadata,
                ),
            )
        session = Session(
            session_id, scenario_id, seed, env, observation, audit=audit, replay=replay
        )
        if env.world is not None:
            env.world.session_id = session_id
        self._sessions[session.session_id] = session
        self.record(
            session,
            "session_created",
            {
                "scenario_id": scenario_id,
                "scenario_hash": env.scenario_hash,
                "seed": seed,
                "runtime_metadata": (
                    asdict(env._runtime.metadata) if env._runtime is not None else None
                ),
            },
        )
        self._write_replay_frame(session, actions=())
        return session

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise KeyError("session not found") from error

    def delete(self, session_id: str) -> Session:
        session = self.get(session_id)
        del self._sessions[session_id]
        self.record(session, "session_closed", {"timestamp": session.observation["timestamp"]})
        if session.replay is not None:
            session.replay.close()
        session.env.close()
        return session

    def step(self, session: Session, action: tuple[float, float]) -> dict[str, Any]:
        observation, reward, terminated, truncated, info = session.env.step(
            np.asarray(action, dtype=np.float32)
        )
        session.observation = observation
        session.total_reward += reward
        session.terminated = terminated
        session.truncated = truncated
        session.last_heading = float(action[1])
        self.record(
            session,
            "action_accepted",
            {
                "action": list(action),
                "reward": reward,
                "terminated": terminated,
                "timestamp": observation["timestamp"],
                "truncated": truncated,
            },
        )
        terminal_events = (
            (VisualizationEvent(event_type="session_ended", message=session.status),)
            if terminated or truncated
            else ()
        )
        self._write_replay_frame(
            session,
            actions=({"type": "kinematic", "speed_mps": action[0], "heading": action[1]},),
            events=terminal_events,
        )
        if (terminated or truncated) and session.replay is not None:
            session.replay.close()
        return {
            "observation": observation,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "info": info,
        }

    def step_action_batch(self, session: Session, batch: RedActionBatch) -> dict[str, Any]:
        observation, reward, terminated, truncated, info = session.env.step_red_action_batch(batch)
        public_observation = observation.model_dump(mode="json")
        time_remaining = observation.mission_status["time_remaining"]
        if not isinstance(time_remaining, int):
            raise RuntimeError("public mission status has invalid time_remaining")
        session.observation = {
            "timestamp": observation.timestamp,
            "mission_status": str(observation.mission_status["status"]),
            "time_remaining": time_remaining,
            "scenario_id": observation.scenario_id,
            "position": [0.0, 0.0],
            "velocity": [0.0, 0.0],
            "goal_direction": [0.0, 0.0],
            "energy": 1.0,
            "mission_briefing": "MD-AD-002 public mission",
        }
        session.total_reward += reward
        session.terminated = terminated
        session.truncated = truncated
        self.record(
            session,
            "action_batch_accepted",
            {
                "timestamp": observation.timestamp,
                "action_count": len(batch.actions),
                "terminated": terminated,
                "truncated": truncated,
            },
        )
        terminal_events = (
            (VisualizationEvent(event_type="session_ended", message=session.status),)
            if terminated or truncated
            else ()
        )
        self._write_replay_frame(
            session,
            actions=(
                {
                    "type": "red_action_batch",
                    "batch": batch.model_dump(mode="json"),
                },
            ),
            events=terminal_events,
        )
        if (terminated or truncated) and session.replay is not None:
            session.replay.close()
        return {
            "observation": public_observation,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "info": info,
        }

    def check_rate_limit(self, session: Session) -> None:
        now = monotonic()
        session.action_times[:] = [
            value for value in session.action_times if now - value < self.rate_window_seconds
        ]
        if len(session.action_times) >= self.rate_limit:
            raise RuntimeError("action rate limit exceeded")
        session.action_times.append(now)

    @staticmethod
    def record(session: Session, event_type: str, payload: dict[str, Any]) -> None:
        if session.audit is not None:
            session.audit.append(event_type, payload)

    @staticmethod
    def _write_replay_frame(
        session: Session,
        *,
        actions: tuple[dict[str, Any], ...],
        events: tuple[VisualizationEvent, ...] = (),
    ) -> None:
        if session.replay is None:
            return
        runtime_events = tuple(
            VisualizationEvent(
                event_type=str(record["event_type"]),
                entity_id=(
                    str(record["entity_id"]) if record.get("entity_id") is not None else None
                ),
                data={
                    key: value
                    for key, value in record.items()
                    if key not in {"event_type", "entity_id"}
                },
            )
            for record in session.env.wave_events[session.wave_event_count :]
        )
        session.wave_event_count = len(session.env.wave_events)
        events = (*events, *runtime_events)
        domains = {
            "uav": Domain.AIR,
            "usv": Domain.SURFACE,
            "shore_radar": Domain.SHORE,
            "auv": Domain.UNDERWATER,
        }
        if session.env.world is not None:
            entities = tuple(
                VisualizationEntity(
                    id=entity.id,
                    side=entity.side,
                    type=entity.platform_type,
                    domain=entity.domain,
                    position=entity.position,
                    velocity=entity.velocity,
                    heading=entity.heading_deg,
                    health=entity.components.health,
                    energy=entity.components.energy,
                    sensor_mode=entity.components.sensor_mode,
                    comm_status=entity.components.communication_status,
                    status=entity.lifecycle,
                    visual_profile=f"{entity.platform_type}_generic",
                    weapon_inventory=dict(entity.components.weapon_inventory),
                    position_wgs84=(
                        (
                            *session.env.geo_frame.local_to_wgs84(*entity.position[:2]),
                            entity.position[2],
                        )
                        if session.env.geo_frame is not None
                        else None
                    ),
                )
                for entity in session.env.world.entities_stable()
                if isinstance(entity, PlatformAsset)
            )
        else:
            controlled = next(
                entity for entity in session.env.scenario.entities if entity.side.value == "blue"
            )
            position_xy = cast(list[float], session.observation["position"])
            velocity_xy = cast(list[float], session.observation["velocity"])
            entities = tuple(
                VisualizationEntity(
                    id=deployment.id,
                    side=deployment.side,
                    type=deployment.type,
                    domain=domains[deployment.type],
                    position=(position_xy[0], position_xy[1], deployment.position[2])
                    if deployment.id == controlled.id
                    else deployment.position,
                    velocity=(velocity_xy[0], velocity_xy[1], 0.0)
                    if deployment.id == controlled.id
                    else (0.0, 0.0, 0.0),
                    heading=session.last_heading if deployment.id == controlled.id else 0.0,
                    health=1.0,
                    energy=1.0,
                    sensor_mode="off",
                    comm_status="connected",
                    status=Lifecycle.ACTIVE,
                    visual_profile=f"{deployment.type}_generic",
                    weapon_inventory={},
                )
                for deployment in session.env.scenario.entities
            )
        detection_sets = DetectionSets()
        if session.env.world is not None:
            detection_sets = DetectionSets(
                blue=tuple(
                    VisualizationDetection(
                        id=track.contact_id,
                        estimated_domain=track.estimated_domain,
                        position=track.position,
                        position_uncertainty=track.uncertainty_m,
                        confidence=track.confidence,
                        message_sent_time=track.message_sent_tick,
                        message_source=track.message_source,
                    )
                    for track in session.env.world.contacts.get(Side.BLUE, [])
                ),
                red=tuple(
                    VisualizationDetection(
                        id=track.contact_id,
                        estimated_domain=track.estimated_domain,
                        position=track.position,
                        position_uncertainty=track.uncertainty_m,
                        confidence=track.confidence,
                        message_sent_time=track.message_sent_tick,
                        message_source=track.message_source,
                    )
                    for track in session.env.world.contacts.get(Side.RED, [])
                ),
            )
        session.replay.write_frame(
            VisualizationFrame(
                timestamp=cast(int, session.observation["timestamp"]),
                actions=actions,
                entities=entities,
                detections=detection_sets,
                events=events,
                scores=ScoreSets(
                    blue=SideScore(total=0.0, metrics={"reward": session.total_reward}),
                    red=SideScore(total=0.0),
                ),
            )
        )

    def restore(self, checkpoint: dict[str, object]) -> Session:
        claimed_hash = checkpoint.get("checkpoint_hash")
        body = {key: value for key, value in checkpoint.items() if key != "checkpoint_hash"}
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        actual_hash = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
        if claimed_hash != actual_hash:
            raise ValueError("checkpoint integrity check failed")
        if checkpoint.get("schema_version") != "1.0":
            raise ValueError("unsupported checkpoint schema version")
        scenario_id = str(checkpoint["scenario_id"])
        seed = cast(int, checkpoint["seed"])
        session = self.create(scenario_id, seed)
        if checkpoint.get("scenario_hash") != session.env.scenario_hash:
            self.delete(session.session_id)
            raise ValueError("checkpoint scenario hash mismatch")
        simulation = cast(dict[str, Any], checkpoint["simulation"])
        session.observation = session.env.import_state(simulation)
        session.terminated = bool(checkpoint["terminated"])
        session.truncated = bool(checkpoint["truncated"])
        session.total_reward = float(checkpoint["total_reward"])  # type: ignore[arg-type]
        return session

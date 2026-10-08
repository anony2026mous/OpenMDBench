"""Scenario-backed Gymnasium environment and explicit tensor adapter."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from functools import partial
from typing import TYPE_CHECKING, Any, Literal, cast

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from gymnasium.vector import SyncVectorEnv
from numpy.typing import NDArray

from openmdbench.core.entities import ComponentState, Domain, Lifecycle, PlatformAsset, Side
from openmdbench.core.geography import GeoFrame
from openmdbench.core.rng import SessionRNG, configuration_hash
from openmdbench.core.units import heading_deg_to_math_rad
from openmdbench.core.world import ContactTrack, WorldState, observation_for_side
from openmdbench.domains.air import UAVCommand, UAVState, step_uav
from openmdbench.domains.shore import ShoreRadarState, apply_shore_command
from openmdbench.domains.surface.actions import validate_kinematic_actions
from openmdbench.missions.md_ad_002 import MDAD002Adjudicator
from openmdbench.policies.actions import ActionBatch, PlatformAction
from openmdbench.policies.md_ad_002 import (
    AD2EasyBlueAgent,
    AD2HardBlueAgent,
    AD2MediumBlueAgent,
)
from openmdbench.scenarios.loader import load_scenario_id, render_briefing
from openmdbench.scenarios.resolved import ResolvedScenario
from openmdbench.scenarios.runtime import (
    ScenarioRuntime,
    ScheduledEntity,
    create_runtime_from_resolved,
    create_scenario_runtime,
    has_scenario_runtime,
)
from openmdbench.scenarios.schema import Scenario
from openmdbench.schemas.md_ad_002_interface import (
    RedActionBatch,
    RedContact,
    RedObservation,
    RedOwnForce,
    RedPlatformAction,
)
from openmdbench.schemas.observation import Observation
from openmdbench.systems.collision import swept_collision, swept_path_crosses_segments
from openmdbench.systems.combat import (
    Combatant,
    DamageIntent,
    RejectionCode,
    apply_simultaneous_damage,
    engage,
    validate_engagement,
)
from openmdbench.systems.combat.ad2 import AD2Combat
from openmdbench.systems.communications import (
    CommEndpoint,
    CommunicationNetwork,
    LinkKind,
)
from openmdbench.systems.energy import AD2_ENERGY_PROFILES, ENERGY_PROFILES, consume_energy
from openmdbench.systems.sensors import (
    DetectionEngine,
    Sensor,
    SensorKind,
    SensorPlatform,
    TargetTruth,
    fuse_tracks,
)
from openmdbench.systems.sensors.ad2 import AD2Perception
from openmdbench.systems.weather import Weather

StructuredObservation = dict[str, int | float | str | list[float]]

if TYPE_CHECKING:
    from openmdbench.domains.surface.mmg_adapter import Sim2SeaMMGAdapter


class OpenMDBenchEnv(gym.Env[StructuredObservation, NDArray[np.float32]]):
    """Deterministic local environment exposing a structured public observation."""

    metadata = {"render_modes": []}

    @property
    def _usv_mmg_adapter(self) -> Sim2SeaMMGAdapter | None:
        """Return a deterministic single-USV view for generic callers."""
        if not self._usv_mmg_adapters:
            return None
        return self._usv_mmg_adapters[sorted(self._usv_mmg_adapters)[0]]

    def __init__(
        self,
        *,
        scenario_id: str = "MD-REC-001",
        seed: int | None = None,
        observation_mode: str = "structured",
        resolved_scenario: ResolvedScenario | None = None,
    ) -> None:
        super().__init__()
        if observation_mode != "structured":
            raise ValueError("core environment only supports observation_mode='structured'")
        if resolved_scenario is not None:
            if scenario_id != "MD-REC-001" and scenario_id != resolved_scenario.scenario_id:
                raise ValueError("scenario_id does not match resolved_scenario")
            scenario_id = resolved_scenario.scenario_id
            self.scenario = Scenario.model_validate(resolved_scenario.components["scenario"])
        else:
            self.scenario = load_scenario_id(scenario_id)
        self._resolved_scenario = resolved_scenario
        self.geo_frame: GeoFrame | None = None
        self.map_metadata: dict[str, object] | None = None
        self.dynamics_metadata: dict[str, object] | None = None
        self.config_metadata: dict[str, str] | None = None
        self.world: WorldState | None = None
        self.last_advanced_entity_ids: tuple[str, ...] = ()
        self.last_dynamics_trace: tuple[tuple[str, str], ...] = ()
        self.last_energy_trace: tuple[tuple[str, float], ...] = ()
        self._md_int_config: Any | None = None
        self._usv_mmg_adapters: dict[str, Sim2SeaMMGAdapter] = {}
        self._sensor_engines: dict[str, DetectionEngine] = {}
        self._ad2_perception: AD2Perception | None = None
        self._ad2_combat: AD2Combat | None = None
        self._ad2_adjudicator: MDAD002Adjudicator | None = None
        self._ad2_blue_agent: AD2EasyBlueAgent | AD2MediumBlueAgent | AD2HardBlueAgent | None = None
        self._ad2_pending_delivered_actions: list[RedPlatformAction] = []
        self._ad2_event_rng = SessionRNG(seed or 0)
        self._ad2_suppressed_until: dict[str, int] = {}
        self._ad2_suppression_prior: dict[str, dict[str, object]] = {}
        self._ad2_suppression_triggered = False
        self._ad2_adjudication_event_count = 0
        self._perception_event_count = 0
        self._communication: CommunicationNetwork | None = None
        self._combat_rng = SessionRNG(seed or 0)
        self._adjudicator: Any | None = None
        self._protected_point = np.zeros(2, dtype=np.float64)
        self.last_combat_audit: tuple[dict[str, object], ...] = ()
        self.last_public_combat_events: tuple[dict[str, object], ...] = ()
        self._pending_navigation: dict[str, tuple[float, float, float]] = {}
        self._pending_ramming_intents: dict[str, str] = {}
        self._defer_collision_damage = False
        self._pending_collision_lifecycles: dict[str, Lifecycle] = {}
        self.last_collision_events: tuple[dict[str, object], ...] = ()
        self._runtime: ScenarioRuntime | None = None
        self._primary_entity_id: str | None = None
        self.scheduled_entities: tuple[ScheduledEntity, ...] = ()
        self.wave_events: list[dict[str, object]] = []
        md_int_config: Any | None = None
        if resolved_scenario is not None:
            self._runtime = create_runtime_from_resolved(resolved_scenario, seed or 0)
        elif has_scenario_runtime(scenario_id):
            self._runtime = create_scenario_runtime(scenario_id, seed or 0)
        if self._runtime is not None:
            self.geo_frame = self._runtime.geo_frame
            self.map_metadata = self._runtime.metadata.map_identity
            self.world = self._runtime.world
            self._primary_entity_id = self._runtime.primary_entity_id
            self.scheduled_entities = self._runtime.scheduled_entities
            self._protected_point = np.asarray(self._runtime.protected_point, dtype=np.float64)
            self.dynamics_metadata = (
                {
                    name: {"mode": component.mode, **component.metadata}
                    for name, component in md_int_config.dynamics.items()
                }
                if md_int_config is not None
                else {"runtime": "configuration_driven_v1"}
            )
            self._md_int_config = md_int_config
            if self._runtime.md_ad_config is not None:
                self._ad2_perception = AD2Perception(self._runtime.md_ad_config, seed or 0)
                protected_point = (
                    float(self._protected_point[0]),
                    float(self._protected_point[1]),
                )
                self._ad2_combat = AD2Combat(self._runtime.md_ad_config, seed or 0, protected_point)
                self._ad2_adjudicator = MDAD002Adjudicator(
                    protected_point=protected_point,
                    protection_radius_m=self._runtime.md_ad_config.denial_zone.radius,
                    breach_threshold=(self._runtime.md_ad_config.adjudication.breach_threshold),
                    time_limit_ticks=self._runtime.time_limit_ticks,
                )
            self.scenario_hash = self._runtime.metadata.config_hash
            self.config_metadata = {
                "scenario_id": self._runtime.metadata.scenario_id,
                "config_version": self._runtime.metadata.config_version,
                "config_hash": self._runtime.metadata.config_hash,
            }
            if self._ad2_combat is not None:
                self.config_metadata["catalog_hash"] = self._ad2_combat.catalog.content_hash
            self.dynamics_metadata = {
                **(self.dynamics_metadata or {}),
                "scenario_runtime": asdict(self._runtime.metadata),
            }
            if self._ad2_combat is not None:
                self.dynamics_metadata["catalog"] = {
                    "schema_version": "1.0",
                    "content_hash": self._ad2_combat.catalog.content_hash,
                }
        else:
            self.scenario_hash = configuration_hash(
                {"scenario": self.scenario.model_dump(mode="json")}
            )
        self._time_limit_ticks = (
            self._runtime.time_limit_ticks
            if self._runtime is not None
            else self.scenario.time_limit_ticks
        )
        self.default_seed = seed
        min_x, min_y, max_x, max_y = self.scenario.world.bounds
        self._lower = np.array([min_x, min_y], dtype=np.float64)
        self._upper = np.array([max_x, max_y], dtype=np.float64)
        briefing = render_briefing(self.scenario)
        maximum_action_speed = 80.0 if self._runtime is not None else 12.9
        self.action_space = spaces.Box(
            low=np.array([0.0, 0.0], dtype=np.float32),
            high=np.array(
                [maximum_action_speed, np.nextafter(np.float32(360.0), np.float32(0.0))],
                dtype=np.float32,
            ),
            dtype=np.float32,
        )
        self.observation_space = spaces.Dict(
            {
                "goal_direction": spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32),
                "energy": spaces.Box(0.0, 1.0, shape=(), dtype=np.float32),
                "mission_briefing": spaces.Text(
                    max_length=4096, min_length=1, charset=frozenset(briefing)
                ),
                "mission_status": spaces.Text(
                    max_length=16,
                    min_length=1,
                    charset=frozenset("runningterminatedtimeout"),
                ),
                "position": spaces.Box(
                    self._lower.astype(np.float32), self._upper.astype(np.float32), dtype=np.float32
                ),
                "scenario_id": spaces.Text(
                    max_length=64,
                    min_length=1,
                    charset=frozenset(self.scenario.scenario_id),
                ),
                "time_remaining": spaces.Discrete(self._time_limit_ticks + 1),
                "timestamp": spaces.Discrete(self._time_limit_ticks + 1),
                "velocity": spaces.Box(
                    -maximum_action_speed,
                    maximum_action_speed,
                    shape=(2,),
                    dtype=np.float32,
                ),
            }
        )
        blue = next(entity for entity in self.scenario.entities if entity.side == Side.BLUE)
        opponents = tuple(entity for entity in self.scenario.entities if entity.side == Side.RED)
        if self._runtime is not None and self.world is not None:
            primary = self.world.registry.get(self._runtime.primary_entity_id)
            self._initial_position = np.asarray(primary.position[:2], dtype=np.float64)
            self._goal = np.asarray(self._runtime.compatibility_goal, dtype=np.float64)
        else:
            self._initial_position = np.array(blue.position[:2], dtype=np.float64)
            self._goal = (
                np.array(opponents[0].position[:2], dtype=np.float64)
                if opponents
                else (self._lower + self._upper) / 2.0
            )
        self._position = self._initial_position.copy()
        self._velocity = np.zeros(2, dtype=np.float64)
        self._tick = 0
        self._ended = False
        self._terminated = False
        self._truncated = False
        if self.world is not None:
            self._reset_communication(seed or 0)
            self._spawn_due(0)

    def _spawn_due(self, tick: int) -> None:
        """Activate due descriptors exactly once in stable entity-ID order."""
        if self.world is None:
            return
        due = tuple(
            sorted(
                (item for item in self.scheduled_entities if item.scheduled_tick <= tick),
                key=lambda item: item.entity_id,
            )
        )
        for item in due:
            heading_rad = heading_deg_to_math_rad(item.heading_deg)
            self.world.registry.register(
                PlatformAsset(
                    id=item.entity_id,
                    side=item.side,
                    domain={
                        "uav": Domain.AIR,
                        "usv": Domain.SURFACE,
                        "shore_radar": Domain.SHORE,
                        "auv": Domain.UNDERWATER,
                    }[item.platform_type],
                    platform_type=item.platform_type,
                    position=item.position,
                    velocity=(
                        item.speed_mps * math.cos(heading_rad),
                        item.speed_mps * math.sin(heading_rad),
                        0.0,
                    ),
                    heading_deg=item.heading_deg,
                    components=ComponentState(
                        sensor_mode="active_search",
                        weapon_inventory=dict(item.weapon_inventory or {}),
                    ),
                )
            )
            self.wave_events.append(
                {
                    "tick": tick,
                    "event_type": "entity_spawned",
                    "entity_id": item.entity_id,
                    "wave_id": item.wave_id,
                }
            )
        due_ids = {item.entity_id for item in due}
        self.scheduled_entities = tuple(
            item for item in self.scheduled_entities if item.entity_id not in due_ids
        )

    def _apply_world_constraints(
        self,
        tick: int,
        previous_positions: dict[str, tuple[float, float, float]] | None = None,
    ) -> None:
        """Latch terminal boundary, terrain-impact, and physical-contact states."""
        if self.world is None or self.geo_frame is None:
            return
        min_x, min_y, max_x, max_y = self.geo_frame.visualization_layers.bounds(
            padding_fraction=0.0
        )
        active = tuple(
            entity
            for entity in self.world.entities_stable()
            if isinstance(entity, PlatformAsset)
            and entity.lifecycle
            in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
        )
        terminal: dict[str, Lifecycle] = {}
        collision_events: list[dict[str, object]] = []
        previous_positions = previous_positions or {}
        for entity in active:
            x, y, z = entity.position
            if not min_x <= x <= max_x or not min_y <= y <= max_y:
                terminal[entity.id] = Lifecycle.OUT_OF_BOUNDS
            elif entity.platform_type == "usv" and (
                self.geo_frame.is_land_local(x, y)
                or (
                    entity.id in previous_positions
                    and swept_path_crosses_segments(
                        previous_positions[entity.id][:2],
                        entity.position[:2],
                        self.geo_frame.coastline_segments,
                    )
                )
            ):
                terminal[entity.id] = Lifecycle.DRIFTING
            elif entity.platform_type == "uav" and z <= 0 and self.geo_frame.is_land_local(x, y):
                terminal[entity.id] = Lifecycle.IMPACTED
        for index, first in enumerate(active):
            for second in active[index + 1 :]:
                first_start = previous_positions.get(first.id, first.position)
                second_start = previous_positions.get(second.id, second.position)
                evidence = swept_collision(
                    first_start,
                    first.position,
                    second_start,
                    second.position,
                    horizontal_limit_m=5.0,
                )
                if evidence is None:
                    continue
                if self._defer_collision_damage:
                    self._pending_collision_lifecycles[first.id] = Lifecycle.DESTROYED
                    self._pending_collision_lifecycles[second.id] = Lifecycle.DESTROYED
                else:
                    terminal[first.id] = Lifecycle.DESTROYED
                    terminal[second.id] = Lifecycle.DESTROYED
                aggressors = tuple(
                    entity_id
                    for entity_id, target_id in sorted(self._pending_ramming_intents.items())
                    if (entity_id, target_id) in {(first.id, second.id), (second.id, first.id)}
                )
                collision_events.append(
                    {
                        "tick": tick,
                        "event_type": "platform_collision",
                        "classification": (
                            "deliberate_ramming" if aggressors else "accidental_collision"
                        ),
                        "participants": (first.id, second.id),
                        "aggressor_ids": aggressors,
                        "intended_targets": {
                            entity_id: self._pending_ramming_intents[entity_id]
                            for entity_id in aggressors
                        },
                        "impact_position": evidence.impact_position,
                        "closest_fraction": evidence.closest_fraction,
                        "horizontal_separation_m": evidence.horizontal_separation_m,
                        "vertical_separation_m": evidence.vertical_separation_m,
                        "relative_speed_mps": evidence.relative_speed_mps,
                        "outcomes": {first.id: "destroyed", second.id: "destroyed"},
                    }
                )
        self.last_collision_events = tuple(collision_events)
        self.wave_events.extend(collision_events)
        for entity_id, lifecycle in sorted(terminal.items()):
            terminal_entity = self.world.registry.get(entity_id)
            self.world.registry.update(terminal_entity.model_copy(update={"lifecycle": lifecycle}))
            self.wave_events.append(
                {
                    "tick": tick,
                    "event_type": "entity_terminal",
                    "entity_id": entity_id,
                    "lifecycle": lifecycle.value,
                }
            )

    def _apply_pending_collision_damage(self) -> None:
        """Commit collision outcomes after same-tick combat intents have resolved."""
        if self.world is None:
            self._pending_collision_lifecycles = {}
            return
        for entity_id, lifecycle in sorted(self._pending_collision_lifecycles.items()):
            entity = self.world.registry.get(entity_id)
            if not isinstance(entity, PlatformAsset):
                continue
            self.world.registry.update(entity.model_copy(update={"lifecycle": lifecycle}))
            self.wave_events.append(
                {
                    "tick": self.world.tick,
                    "event_type": "entity_terminal",
                    "entity_id": entity_id,
                    "lifecycle": lifecycle.value,
                }
            )
        self._pending_collision_lifecycles = {}
        self._update_mission_result()

    def _reset_sensor_engines(self, seed: int) -> None:
        if self.world is None:
            self._sensor_engines = {}
            return
        component_names = {
            "shore_radar": "shore_air_radar",
            "uav": "uav_eo_ir",
            "usv": "usv_radar",
        }
        sensor_ids = tuple(
            f"{entity.id}:{component_names[entity.platform_type]}"
            for entity in self.world.entities_stable()
            if isinstance(entity, PlatformAsset) and entity.platform_type in component_names
        )
        self._sensor_engines = {
            sensor_id: DetectionEngine(SessionRNG(seed + index))
            for index, sensor_id in enumerate(sensor_ids)
        }

    def _reset_communication(self, seed: int) -> None:
        if self.world is None:
            self._communication = None
            return
        network = CommunicationNetwork(SessionRNG(seed))
        network.register(
            CommEndpoint(
                "blue-command",
                (float(self._protected_point[0]), float(self._protected_point[1]), 0.0),
                LinkKind.LOS,
                200_000.0,
                100_000_000.0,
                side="blue",
                physical_latency_ms=20.0,
            )
        )
        network.register(
            CommEndpoint(
                "red-command",
                (float(self._protected_point[0]), float(self._protected_point[1]), 0.0),
                LinkKind.WIRED,
                50_000.0,
                100_000_000.0,
                side="red",
                physical_latency_ms=0.0,
            )
        )
        for entity in self.world.entities_stable():
            if not isinstance(entity, PlatformAsset):
                continue
            if entity.platform_type == "shore_radar":
                kind, range_m, bandwidth, latency_ms = (
                    LinkKind.WIRED,
                    0.0,
                    100_000_000.0,
                    0.0,
                )
            elif entity.platform_type == "uav":
                kind, range_m, bandwidth, latency_ms = (
                    LinkKind.LOS,
                    50_000.0,
                    10_000_000.0,
                    20.0,
                )
            else:
                kind, range_m, bandwidth, latency_ms = (
                    LinkKind.LOS,
                    30_000.0,
                    5_000_000.0,
                    50.0,
                )
            network.register(
                CommEndpoint(
                    entity.id,
                    entity.position,
                    kind,
                    range_m,
                    bandwidth,
                    side=entity.side.value,
                    relay_enabled=(
                        entity.platform_type == "usv"
                        and self._runtime is not None
                        and self._runtime.md_ad_config is not None
                        and self._runtime.md_ad_config.difficulty == "hard"
                    ),
                    physical_latency_ms=latency_ms,
                )
            )
        self._communication = network

    def _ad2_blocked_links(self, tick: int) -> tuple[tuple[str, str], ...]:
        if self._runtime is None or self._runtime.md_ad_config is None:
            return ()
        active = any(
            event.component == "jamming"
            and event.tick <= tick < event.tick + event.duration_seconds
            for event in self._runtime.md_ad_config.difficulty_events
        )
        if not active:
            return ()
        return tuple(
            ("red-command", entity.id)
            for entity in self.world.entities_for_side(Side.RED)  # type: ignore[union-attr]
            if isinstance(entity, PlatformAsset) and entity.platform_type == "uav"
        )

    def _deliver_ad2_messages(
        self, tick: int, *, consume_commands: bool = False
    ) -> tuple[RedPlatformAction, ...]:
        if self._communication is None or self.world is None:
            return ()
        contacts = {track.contact_id: track for track in self.world.contacts.get(Side.RED, ())}
        actions: list[RedPlatformAction] = []
        for message in self._communication.deliver(tick):
            message_type = message.payload.get("message_type")
            if message_type == "ad2_command":
                self._ad2_pending_delivered_actions.append(
                    RedPlatformAction.model_validate(message.payload["action"])
                )
                continue
            if message_type != "ad2_contact":
                continue
            values = dict(message.payload["track"])
            values["owner_side"] = Side(values["owner_side"])
            values["estimated_domain"] = Domain(values["estimated_domain"])
            values["position"] = tuple(values["position"])
            values["velocity"] = tuple(values["velocity"])
            values["detected_by"] = tuple(values["detected_by"])
            values["message_sent_tick"] = message.sent_tick
            values["message_source"] = message.sender_id
            track = ContactTrack(**values)
            contacts[track.contact_id] = track
        self.world.contacts[Side.RED] = [
            track
            for _, track in sorted(contacts.items())
            if tick - (track.last_update_tick or track.first_detected_tick) <= 10
        ]
        if not consume_commands:
            return ()
        actions.extend(self._ad2_pending_delivered_actions)
        self._ad2_pending_delivered_actions.clear()
        return tuple(sorted(actions, key=lambda action: action.entity_id))

    def _route_ad2_tracks(self, tracks: tuple[ContactTrack, ...], tick: int) -> None:
        if self._communication is None or self.world is None:
            return
        for entity in self.world.entities_for_side(Side.RED):
            if isinstance(entity, PlatformAsset) and entity.id in self._communication.endpoints:
                self._communication.update_position(entity.id, entity.position)
        blocked_links = self._ad2_blocked_links(tick)
        for entity in self.world.entities_for_side(Side.RED):
            if not isinstance(entity, PlatformAsset) or entity.platform_type == "shore_radar":
                continue
            try:
                route = self._communication.route(
                    entity.id,
                    "red-command",
                    blocked_links=blocked_links,
                )
                status = "connected" if len(route) == 2 else "relayed"
            except ConnectionError:
                status = "offline"
            self.world.registry.update(
                entity.model_copy(
                    update={
                        "components": entity.components.model_copy(
                            update={"communication_status": status}
                        )
                    }
                )
            )
        for track in tracks:
            candidates: list[tuple[int, str]] = []
            for source in track.detected_by:
                sender_id = source.split(":", 1)[0]
                if sender_id not in self._communication.endpoints:
                    continue
                try:
                    route = self._communication.route(
                        sender_id,
                        "red-command",
                        blocked_links=blocked_links,
                    )
                except ConnectionError:
                    continue
                candidates.append((len(route), sender_id))
            if not candidates:
                continue
            sender_id = min(candidates)[1]
            self._communication.send_routed(
                sender_id,
                "red-command",
                {"message_type": "ad2_contact", "track": asdict(track)},
                tick=tick,
                expires_tick=tick + 10,
                payload_bytes=512,
                blocked_links=blocked_links,
                generated_tick=track.last_update_tick or tick,
            )
        self._deliver_ad2_messages(tick)
        self.wave_events.extend(self._communication.events)
        self._communication.events.clear()

    def _sensor_for(self, entity: PlatformAsset) -> Sensor | None:
        if self._md_int_config is None:
            return None
        component_name = {
            "shore_radar": "shore_air_radar",
            "uav": "uav_eo_ir",
            "usv": "usv_radar",
        }.get(entity.platform_type)
        if component_name is None:
            return None
        component = self._md_int_config.sensors[component_name]
        values = {name: float(parameter.value) for name, parameter in component.parameters.items()}
        kind = SensorKind.EO_IR if entity.platform_type == "uav" else SensorKind.RADAR
        return Sensor(
            sensor_id=f"{entity.id}:{component_name}",
            kind=kind,
            range_m=values["range"] * (0.7 if entity.lifecycle is Lifecycle.DEGRADED else 1.0),
            update_hz=values["update_rate"],
            base_detection_probability=values["base_detection_probability"],
            field_of_view_deg=values["field_of_view"],
            uncertainty_fraction=values["uncertainty_fraction"],
            minimum_uncertainty_m=values["minimum_uncertainty"],
            initial_confidence=values["initial_confidence"],
        )

    def _update_sensors(self, tick: int) -> None:
        if self.world is None:
            return
        if self._ad2_perception is not None:
            tracks = self._ad2_perception.update(self.world, tick)
            if (
                self._runtime is not None
                and self._runtime.md_ad_config is not None
                and self._runtime.md_ad_config.difficulty == "hard"
            ):
                self._route_ad2_tracks(tracks, tick)
            else:
                self.world.contacts[Side.RED] = list(tracks)
            new_events = self._ad2_perception.events[self._perception_event_count :]
            # Raw per-sensor reports are high-rate diagnostic facts owned by the
            # perception subsystem.  Copying them into the scenario event journal
            # makes long matches grow with sensors × targets × ticks and also
            # leaks a truth-oriented diagnostic through the public event path.
            self.wave_events.extend(
                {key: value for key, value in event.items() if key != "truth_id"}
                for event in new_events
                if event.get("event_type") != "sensor_report"
            )
            self._perception_event_count = len(self._ad2_perception.events)
            if self._perception_event_count > 32_768:
                # Trim in large chunks.  Deleting one old item on every tick is
                # itself O(history) and turns a bounded journal into a long-soak
                # CPU cliff once the limit is reached.
                del self._ad2_perception.events[:16_384]
                self._perception_event_count = len(self._ad2_perception.events)
            return
        if self._communication is None:
            raise RuntimeError("sensor propagation requires the communication network")
        platforms = tuple(
            entity
            for entity in self.world.entities_stable()
            if isinstance(entity, PlatformAsset)
            and entity.lifecycle
            in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
        )
        for entity in platforms:
            sensor = self._sensor_for(entity)
            if sensor is None or entity.components.sensor_mode == "off":
                continue
            targets = tuple(
                TargetTruth(
                    entity_id=target.id,
                    domain=target.domain,
                    position=target.position,
                    velocity=target.velocity,
                )
                for target in platforms
                if target.side is not entity.side
            )
            engine = self._sensor_engines[sensor.sensor_id]
            self._communication.update_position(entity.id, entity.position)
            tracks = engine.scan(
                SensorPlatform(
                    platform_id=entity.id,
                    platform_type=entity.platform_type,
                    side=entity.side,
                    domain=entity.domain,
                    position=entity.position,
                    sensor=sensor,
                    heading_deg=entity.heading_deg,
                ),
                targets,
                tick=tick,
                weather=Weather.CLEAR,
            )
            recipient = f"{entity.side.value}-command"
            for track in tracks:
                payload = {
                    "contact_id": track.contact_id,
                    "owner_side": track.owner_side.value,
                    "estimated_domain": track.estimated_domain.value,
                    "position": track.position,
                    "velocity": track.velocity,
                    "uncertainty_m": track.uncertainty_m,
                    "confidence": track.confidence,
                    "first_detected_tick": track.first_detected_tick,
                    "detected_by": track.detected_by,
                    "inferred_type": track.inferred_type,
                    "last_update_tick": track.last_update_tick,
                }
                try:
                    self._communication.send(
                        entity.id,
                        recipient,
                        payload,
                        tick=tick,
                        expires_tick=tick + 10,
                        payload_bytes=512,
                    )
                except ConnectionError:
                    continue
        delivered_by_side: dict[Side, list[ContactTrack]] = {
            Side.BLUE: [],
            Side.RED: [],
        }
        for message in self._communication.deliver(tick):
            delivered_payload = message.payload
            side = Side(str(delivered_payload["owner_side"]))
            delivered_by_side[side].append(
                ContactTrack(
                    contact_id=str(delivered_payload["contact_id"]),
                    owner_side=side,
                    estimated_domain=Domain(str(delivered_payload["estimated_domain"])),
                    position=cast(tuple[float, float, float], tuple(delivered_payload["position"])),
                    velocity=cast(tuple[float, float, float], tuple(delivered_payload["velocity"])),
                    uncertainty_m=float(delivered_payload["uncertainty_m"]),
                    confidence=float(delivered_payload["confidence"]),
                    first_detected_tick=int(delivered_payload["first_detected_tick"]),
                    detected_by=cast(tuple[str, ...], tuple(delivered_payload["detected_by"])),
                    inferred_type=str(delivered_payload["inferred_type"]),
                    message_sent_tick=message.sent_tick,
                    message_source=message.sender_id,
                    last_update_tick=(
                        int(delivered_payload["last_update_tick"])
                        if delivered_payload.get("last_update_tick") is not None
                        else None
                    ),
                )
            )
        self.world.contacts = {
            side: list(fuse_tracks(tuple(tracks))) for side, tracks in delivered_by_side.items()
        }

    def public_observation(self, side: Side | str) -> Observation:
        if self.world is None:
            raise RuntimeError("public world observation requires a formal world")
        observation = observation_for_side(self.world, Side(side))
        return observation.model_copy(update={"event_log": self.last_public_combat_events})

    def _apply_ad2_difficulty_events(self, tick: int) -> None:
        if self.world is None or self._runtime is None:
            return
        if self._runtime.md_ad_config is None:
            resolved = self._runtime.resolved
            if resolved is None or "composition" not in resolved.components:
                return
            for resolved_event in resolved.events:
                if resolved_event.tick != tick:
                    continue
                payload = dict(resolved_event.payload)
                if resolved_event.event_type == "weather_change":
                    weather = str(payload.get("weather", "clear"))
                    self.world.weather = weather
                    payload["weather"] = weather
                self.wave_events.append(
                    {"event_type": resolved_event.event_type, "tick": tick, **payload}
                )
            return
        for event in self._runtime.md_ad_config.difficulty_events:
            if event.component == "weather" and event.mode == "cloudy" and event.tick == tick:
                weather = "cloudy"
                self.world.weather = weather
                self.wave_events.append(
                    {
                        "event_type": "weather_changed",
                        "tick": tick,
                        "weather": weather,
                    }
                )
            elif (
                event.component == "weather" and event.mode == "rain_or_fog" and event.tick == tick
            ):
                weather = str(
                    self._ad2_event_rng.stream("hard_weather").choice(("light_rain", "fog"))
                )
                self.world.weather = weather
                self.wave_events.append(
                    {
                        "event_type": "weather_changed",
                        "tick": tick,
                        "weather": weather,
                    }
                )
            elif event.component == "sea_state" and event.mode == "state_4" and event.tick == tick:
                self.world.sea_state = 4
                self.wave_events.append(
                    {"event_type": "sea_state_changed", "tick": tick, "sea_state": 4}
                )
            elif event.component == "jamming" and event.tick == tick:
                self.wave_events.append(
                    {
                        "event_type": "jamming_started",
                        "tick": tick,
                        "mode": event.mode,
                        "ends_tick": tick + event.duration_seconds,
                    }
                )
            elif (
                event.component == "jamming"
                and event.duration_seconds
                and event.tick + event.duration_seconds == tick
            ):
                self.wave_events.append(
                    {"event_type": "jamming_ended", "tick": tick, "mode": event.mode}
                )
        for entity_id, until in tuple(sorted(self._ad2_suppressed_until.items())):
            if tick != until:
                continue
            entity = self.world.registry.get(entity_id)
            if isinstance(entity, PlatformAsset):
                prior = self._ad2_suppression_prior.pop(entity_id)
                components = entity.components.model_copy(
                    update=cast(dict[str, Any], prior["components"])
                )
                self.world.registry.update(
                    entity.model_copy(
                        update={
                            "components": components,
                            "lifecycle": Lifecycle(str(prior["lifecycle"])),
                        }
                    )
                )
                if self._communication is not None and entity_id in self._communication.endpoints:
                    self._communication.set_online(entity_id, bool(prior["communication_online"]))
            del self._ad2_suppressed_until[entity_id]
            self.wave_events.append(
                {"event_type": "suppression_ended", "tick": tick, "entity_id": entity_id}
            )
        suppression = next(
            (
                event
                for event in self._runtime.md_ad_config.difficulty_events
                if event.component == "suppression" and event.mode == "usv_proximity_trigger"
            ),
            None,
        )
        if suppression is None or self._ad2_suppression_triggered:
            return
        usv = self.world.registry.get("red-picket-usv-1")
        if not isinstance(usv, PlatformAsset):
            return
        threats = (
            entity
            for entity in self.world.entities_for_side(Side.BLUE)
            if isinstance(entity, PlatformAsset)
            and entity.lifecycle
            in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
        )
        trigger = next(
            (entity for entity in threats if math.dist(entity.position, usv.position) <= 5_000.0),
            None,
        )
        if trigger is None:
            return
        until = tick + suppression.duration_seconds
        self._ad2_suppression_prior[usv.id] = {
            "lifecycle": usv.lifecycle.value,
            "communication_online": (
                self._communication.endpoints[usv.id].online
                if self._communication is not None
                else True
            ),
            "components": {
                "sensor_operational": usv.components.sensor_operational,
                "communication_operational": usv.components.communication_operational,
                "propulsion_operational": usv.components.propulsion_operational,
                "weapons_operational": usv.components.weapons_operational,
            },
        }
        components = usv.components.model_copy(
            update={
                "sensor_operational": False,
                "communication_operational": False,
                "propulsion_operational": False,
                "weapons_operational": False,
                "communication_status": "offline",
            }
        )
        self.world.registry.update(
            usv.model_copy(
                update={
                    "components": components,
                    "lifecycle": Lifecycle.DEGRADED,
                    "velocity": (0.0, 0.0, 0.0),
                }
            )
        )
        if self._communication is not None:
            self._communication.set_online(usv.id, False)
        self._ad2_suppressed_until[usv.id] = until
        self._ad2_suppression_triggered = True
        self.wave_events.append(
            {
                "event_type": "suppression_started",
                "tick": tick,
                "entity_id": usv.id,
                "source_id": trigger.id,
                "ends_tick": until,
            }
        )

    def red_observation(self) -> RedObservation:
        """Build the MD-AD-002 allowlisted public observation."""
        if self.world is None or self._runtime is None or self._runtime.md_ad_config is None:
            raise RuntimeError("red observation is only available for MD-AD-002")
        own_forces = tuple(
            RedOwnForce(
                entity_id=entity.id,
                platform_type=entity.platform_type,
                position_m=entity.position,
                velocity_mps=entity.velocity,
                heading_deg=entity.heading_deg,
                health=entity.components.health,
                energy=entity.components.energy,
                operational_status=entity.lifecycle.value,
                sensor_mode=entity.components.sensor_mode,
                communication_status=entity.components.communication_status,
                weapons=dict(entity.components.weapon_inventory),
                current_command=entity.components.current_command,
            )
            for entity in self.world.entities_for_side(Side.RED)
            if isinstance(entity, PlatformAsset)
        )
        contacts = tuple(
            RedContact(
                contact_id=track.contact_id,
                estimated_domain=track.estimated_domain.value,
                position_m=track.position,
                velocity_mps=track.velocity,
                estimated_type=track.inferred_type,
                confidence=track.confidence,
                uncertainty_m=track.uncertainty_m,
                age=max(0, self.world.tick - (track.last_update_tick or track.first_detected_tick)),
                sources=track.detected_by,
                last_update=track.last_update_tick,
            )
            for track in sorted(
                self.world.contacts.get(Side.RED, ()), key=lambda item: item.contact_id
            )
        )
        return RedObservation(
            scenario_id=cast(Any, self.scenario.scenario_id),
            timestamp=self.world.tick,
            own_forces=own_forces,
            contacts=contacts,
            environment={"weather": self.world.weather, "sea_state": self.world.sea_state},
            mission_status={
                "status": self.world.mission_status,
                "time_remaining": self.world.time_remaining,
                "breach_count": (
                    len(self._ad2_adjudicator.breached_ids)
                    if self._ad2_adjudicator is not None
                    else 0
                ),
            },
            visible_events=tuple(
                cast(
                    dict[str, str | int | float | bool | None],
                    {
                        key: value
                        for key, value in event.items()
                        if key not in {"source_id", "truth_id", "target_id_internal", "rng_sample"}
                    },
                )
                for event in self.wave_events
                if event.get("tick") == self.world.tick
                and event.get("event_type")
                in {
                    "jamming_started",
                    "jamming_ended",
                    "weather_changed",
                    "sea_state_changed",
                    "suppression_started",
                    "suppression_ended",
                    "command_not_delivered",
                    "command_discarded_unavailable",
                    "message_dropped",
                    "message_delivered",
                    "message_expired",
                }
                and all(
                    isinstance(value, (str, int, float, bool)) or value is None
                    for key, value in event.items()
                    if key not in {"source_id", "truth_id", "target_id_internal", "rng_sample"}
                )
            ),
        )

    def _validate_red_batch(self, batch: RedActionBatch) -> ActionBatch:
        """Validate the entire public batch before any world mutation."""
        if self.world is None or self._runtime is None or self._runtime.md_ad_config is None:
            raise RuntimeError("RedActionBatch is only available for MD-AD-002")
        if batch.scenario_id != self.scenario.scenario_id:
            raise ValueError("action batch scenario_id mismatch")
        if batch.timestamp != self.world.tick:
            raise ValueError("action batch timestamp mismatch")
        contacts = {track.contact_id for track in self.world.contacts.get(Side.RED, ())}
        converted = []
        for action in batch.actions:
            try:
                entity = self.world.registry.get(action.entity_id)
            except KeyError as error:
                raise ValueError(f"unknown action entity: {action.entity_id}") from error
            if not isinstance(entity, PlatformAsset) or entity.side is not Side.RED:
                raise ValueError(f"action entity is not controlled by red: {action.entity_id}")
            if entity.lifecycle not in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}:
                raise ValueError(f"action entity is unavailable: {action.entity_id}")
            if entity.platform_type == "shore_radar" and action.navigation.mode not in {
                "hold_position",
                "active_search",
            }:
                raise ValueError("shore platform rejects movement")
            if entity.platform_type == "usv" and action.engagement is not None:
                raise ValueError("USV weapon engagement is unsupported")
            if action.engagement is not None and action.engagement.contact_id not in contacts:
                raise ValueError("engagement contact is not owned by red")
            converted.append(
                PlatformAction(
                    entity_id=action.entity_id,
                    navigation=action.navigation.mode,
                    target=action.navigation.target_m,
                    speed_mps=action.navigation.speed_mps,
                    engage_contact_id=(
                        action.engagement.contact_id if action.engagement is not None else None
                    ),
                    weapon_id=(
                        action.engagement.weapon_id if action.engagement is not None else None
                    ),
                    count=action.engagement.count if action.engagement is not None else 1,
                )
            )
        return ActionBatch(
            timestamp=batch.timestamp,
            actions=tuple(converted),
            high_level_intent=batch.high_level_intent,
        )

    def step_red_action_batch(
        self, batch: RedActionBatch
    ) -> tuple[RedObservation, float, bool, bool, dict[str, object]]:
        """Apply one canonical red batch; missing platforms deterministically hold."""
        event_start = len(self.wave_events)
        internal = self._validate_red_batch(batch)
        if self.world is None:
            raise RuntimeError("MD-AD-002 action batch requires an active world")
        is_hard = (
            self._runtime is not None
            and self._runtime.md_ad_config is not None
            and self._runtime.md_ad_config.difficulty == "hard"
        )
        public_batch = batch
        if is_hard:
            if self._communication is None:
                raise RuntimeError("HARD action delivery requires communication network")
            delivered = list(self._deliver_ad2_messages(self.world.tick, consume_commands=True))
            blocked_links = self._ad2_blocked_links(self.world.tick)
            for action in batch.actions:
                try:
                    self._communication.send_routed(
                        "red-command",
                        action.entity_id,
                        {"message_type": "ad2_command", "action": action.model_dump(mode="json")},
                        tick=self.world.tick,
                        expires_tick=self.world.tick + (2 if action.engagement else 10),
                        payload_bytes=1_024,
                        blocked_links=blocked_links,
                    )
                except ConnectionError:
                    self.wave_events.append(
                        {
                            "event_type": "command_not_delivered",
                            "tick": self.world.tick,
                            "entity_id": action.entity_id,
                        }
                    )
            delivered.extend(self._deliver_ad2_messages(self.world.tick, consume_commands=True))
            current_contacts = {
                contact.contact_id for contact in self.world.contacts.get(Side.RED, ())
            }
            applicable: list[RedPlatformAction] = []
            for action in delivered:
                entity = self.world.registry.get(action.entity_id)
                if not isinstance(entity, PlatformAsset) or entity.lifecycle not in {
                    Lifecycle.ACTIVE,
                    Lifecycle.DEGRADED,
                }:
                    self.wave_events.append(
                        {
                            "event_type": "command_discarded_unavailable",
                            "tick": self.world.tick,
                            "entity_id": action.entity_id,
                        }
                    )
                    continue
                applicable.append(
                    action.model_copy(update={"engagement": None})
                    if action.engagement is not None
                    and action.engagement.contact_id not in current_contacts
                    else action
                )
            delivered = applicable
            public_batch = batch.model_copy(update={"actions": tuple(delivered)})
            internal = self._validate_red_batch(public_batch)
            self.wave_events.extend(self._communication.events)
            self._communication.events.clear()
        public_actions = {action.entity_id: action for action in public_batch.actions}
        for entity_id, action in sorted(public_actions.items()):
            entity = self.world.registry.get(entity_id)
            if not isinstance(entity, PlatformAsset):
                raise RuntimeError("validated red entity is no longer a platform")
            component_updates: dict[str, object] = {
                "current_command": action.model_dump(mode="json")
            }
            if action.sensor is not None:
                component_updates["sensor_mode"] = action.sensor.mode
            if action.communication is not None:
                if is_hard and entity.platform_type == "usv" and self._communication is not None:
                    self._communication.set_relay_enabled(
                        entity.id, action.communication.relay_enabled
                    )
                elif not is_hard:
                    component_updates["communication_status"] = (
                        "relayed" if action.communication.relay_enabled else "connected"
                    )
            self.world.registry.update(
                entity.model_copy(
                    update={"components": entity.components.model_copy(update=component_updates)}
                )
            )
        submitted = {action.entity_id for action in internal.actions}
        missing = tuple(
            entity.id
            for entity in self.world.entities_for_side(Side.RED)
            if isinstance(entity, PlatformAsset)
            and entity.lifecycle in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}
            and entity.id not in submitted
        )
        for entity_id in missing:
            self.wave_events.append(
                {
                    "tick": self.world.tick,
                    "event_type": (
                        "action_defaulted_continue_last" if is_hard else "action_defaulted_hold"
                    ),
                    "entity_id": entity_id,
                }
            )
        actions = (
            internal.actions
            if is_hard
            else (
                *internal.actions,
                *(
                    PlatformAction(entity_id=entity_id, navigation="hold_position")
                    for entity_id in missing
                ),
            )
        )
        red_internal = internal.model_copy(update={"actions": actions})
        blue_internal = (
            self._ad2_blue_agent.act(self.public_observation(Side.BLUE))
            if self._ad2_blue_agent is not None
            else ActionBatch(timestamp=self.world.tick, actions=())
        )
        _blue, _red, terminated, info = self.step_bilateral(blue_internal, red_internal)
        communication_events = tuple(
            event
            for event in self.wave_events[event_start:]
            if str(event.get("event_type", "")).startswith(("message_", "command_", "jamming_"))
        )
        return (
            self.red_observation(),
            0.0,
            terminated,
            False,
            {
                **info,
                "communication_events": communication_events,
                "blue_action": blue_internal.model_dump(mode="json"),
            },
        )

    def resolve_combat(self, batch: ActionBatch) -> tuple[dict[str, object], ...]:
        """Validate all engage intents, resolve shots, then apply damage simultaneously."""
        if self.world is None:
            raise RuntimeError("combat resolution requires a formal world")
        if batch.timestamp != self.world.tick:
            raise ValueError("action batch timestamp does not match the current world tick")
        if self._ad2_combat is not None:
            truth = (
                self._ad2_perception.truth_by_contact() if self._ad2_perception is not None else {}
            )
            events = self._ad2_combat.resolve(
                self.world,
                batch,
                truth_by_contact=truth,
                breached_ids=frozenset(
                    self._ad2_adjudicator.breached_ids if self._ad2_adjudicator is not None else ()
                ),
            )
            self.last_combat_audit = events
            self.last_public_combat_events = tuple(
                {
                    key: value
                    for key, value in event.items()
                    if key not in {"rng_sample", "target_id_internal"}
                }
                for event in events
            )
            self.wave_events.extend(self.last_public_combat_events)
            self._update_mission_result()
            return self.last_public_combat_events
        audit: list[dict[str, object]] = []
        public_events: list[dict[str, object]] = []
        damage_intents: list[DamageIntent] = []
        ordered_actions = sorted(
            batch.actions, key=lambda item: (item.entity_id, item.weapon_id or "")
        )
        for action in ordered_actions:
            if action.engage_contact_id is None or action.weapon_id is None:
                continue
            attacker_entity = self.world.registry.get(action.entity_id)
            if not isinstance(attacker_entity, PlatformAsset):
                continue
            contact = next(
                (
                    track
                    for track in self.world.contacts.get(attacker_entity.side, [])
                    if track.contact_id == action.engage_contact_id
                ),
                None,
            )
            candidates = tuple(
                entity
                for entity in self.world.entities_stable()
                if isinstance(entity, PlatformAsset)
                and entity.side is not attacker_entity.side
                and contact is not None
                and entity.domain is contact.estimated_domain
            )
            associated_truth_ids = {
                truth_id
                for engine in self._sensor_engines.values()
                for contact_id, truth_id in engine.truth_by_contact().items()
                if contact_id == action.engage_contact_id
            }
            associated_target = None
            if len(associated_truth_ids) == 1:
                candidate = self.world.registry.get(next(iter(associated_truth_ids)))
                if isinstance(candidate, PlatformAsset) and candidate in candidates:
                    associated_target = candidate
            target = associated_target or (candidates[0] if len(candidates) == 1 else None)
            combatant = Combatant(
                attacker_entity.id,
                attacker_entity.side,
                attacker_entity.position,
                attacker_entity.components.health,
                dict(attacker_entity.components.weapon_inventory),
                attacker_entity.platform_type,
                attacker_entity.lifecycle,
            )
            legality = validate_engagement(
                combatant,
                contact,
                target_side=target.side if target is not None else Side.NEUTRAL,
                target_domain=target.domain if target is not None else Domain.AIR,
                target_truth_position=(
                    target.position if target is not None else attacker_entity.position
                ),
                weapon_id=action.weapon_id,
                count=action.count,
                current_tick=self.world.tick,
                command_delivered=attacker_entity.components.communication_status
                in {"connected", "relayed"},
                hostile=target is not None,
                roe_permitted=target is not None,
            )
            if not legality.accepted or contact is None or target is None:
                code = (
                    RejectionCode.CONTACT_NOT_OWNED
                    if contact is not None and target is None
                    else legality.rejection_code or RejectionCode.CONTACT_NOT_OWNED
                )
                audit.append(
                    {
                        "event_type": "engagement_rejected",
                        "attacker_entity_id": attacker_entity.id,
                        "target_contact_id": action.engage_contact_id,
                        "rejection_code": code.value,
                    }
                )
                continue
            result = engage(
                combatant,
                contact,
                target_side=target.side,
                target_health=target.components.health,
                weapon_id=action.weapon_id,
                count=action.count,
                weather=Weather.CLEAR,
                rng=self._combat_rng,
                current_tick=self.world.tick,
                target_domain=target.domain,
                target_truth_position=target.position,
            )
            launch_cost = ENERGY_PROFILES[attacker_entity.platform_type].engagement_cost
            self.world.registry.update(
                attacker_entity.model_copy(
                    update={
                        "components": attacker_entity.components.model_copy(
                            update={
                                "weapon_inventory": result.attacker.ammunition,
                                "energy": max(
                                    0.0,
                                    attacker_entity.components.energy - launch_cost * action.count,
                                ),
                            }
                        )
                    }
                )
            )
            damage_intents.append(DamageIntent(attacker_entity.id, target.id, result.total_damage))
            for shot in result.shots:
                audit.append(
                    {
                        "event_type": "combat_round",
                        "timestamp": self.world.tick,
                        "attacker_entity_id": attacker_entity.id,
                        "target_contact_id": contact.contact_id,
                        "target_entity_id_internal": target.id,
                        "weapon_id": action.weapon_id,
                        "round_index": shot.round_index,
                        "p_hit": shot.probability,
                        "rng_sample": shot.random_sample,
                        "hit": shot.hit,
                        "damage": shot.damage if shot.hit else 0.0,
                    }
                )
            public_events.append(
                {
                    "event_type": "engagement",
                    "attacker_id": attacker_entity.id,
                    "contact_id": contact.contact_id,
                    "weapon_id": action.weapon_id,
                    "rounds": action.count,
                    "hits": sum(shot.hit for shot in result.shots),
                }
            )
        platforms = tuple(
            entity for entity in self.world.entities_stable() if isinstance(entity, PlatformAsset)
        )
        updated, _events = apply_simultaneous_damage(platforms, tuple(damage_intents))
        for entity in updated:
            self.world.registry.update(entity)
        self.last_combat_audit = tuple(audit)
        self.last_public_combat_events = tuple(public_events)
        self._update_mission_result()
        return self.last_public_combat_events

    def step_bilateral(
        self, blue_batch: ActionBatch, red_batch: ActionBatch
    ) -> tuple[Observation, Observation, bool, dict[str, object]]:
        """Atomically accept T actions, advance the world, then resolve combined fire."""
        if self.world is None:
            raise RuntimeError("bilateral stepping requires a formal world")
        if blue_batch.timestamp != self.world.tick or red_batch.timestamp != self.world.tick:
            raise ValueError("both action batches must use the current timestamp")
        self._ad2_pending_delivered_actions = []
        validated_ramming_intents: dict[str, str] = {}
        for action in (*blue_batch.actions, *red_batch.actions):
            entity = self.world.registry.get(action.entity_id)
            if action.ram_target_id is not None:
                try:
                    target = self.world.registry.get(action.ram_target_id)
                except KeyError as error:
                    raise ValueError("unknown ramming target") from error
                if not isinstance(entity, PlatformAsset) or not isinstance(target, PlatformAsset):
                    raise ValueError("ramming requires platform attacker and target")
                if entity.side is target.side:
                    raise ValueError("ramming target must be on the opposing side")
                if entity.lifecycle not in {
                    Lifecycle.ACTIVE,
                    Lifecycle.DEGRADED,
                    Lifecycle.BREACHED_ACTIVE,
                } or target.lifecycle not in {
                    Lifecycle.ACTIVE,
                    Lifecycle.DEGRADED,
                    Lifecycle.BREACHED_ACTIVE,
                }:
                    raise ValueError("ramming attacker and target must be available")
                validated_ramming_intents[entity.id] = target.id

        self._pending_navigation = {}
        self._pending_ramming_intents = validated_ramming_intents
        for action in (*blue_batch.actions, *red_batch.actions):
            entity = self.world.registry.get(action.entity_id)
            if action.navigation == "hold_position":
                self._pending_navigation[action.entity_id] = (
                    0.0,
                    entity.heading_deg,
                    entity.position[2],
                )
                continue
            if action.target is None or action.navigation not in {
                "move_to",
                "patrol",
                "guard",
            }:
                continue
            east = action.target[0] - entity.position[0]
            north = action.target[1] - entity.position[1]
            heading = math.degrees(math.atan2(east, north)) % 360.0
            self._pending_navigation[action.entity_id] = (
                action.speed_mps,
                heading,
                action.target[2],
            )
        if self._primary_entity_id is None:
            raise RuntimeError("bilateral stepping requires a primary entity")
        controlled = self._pending_navigation.get(
            self._primary_entity_id,
            (40.0, 90.0, self.world.registry.get(self._primary_entity_id).position[2]),
        )
        self._defer_collision_damage = True
        try:
            _observation, _reward, terminated, _truncated, info = self.step(
                np.asarray(controlled[:2], dtype=np.float32)
            )
            combined = ActionBatch(
                timestamp=self.world.tick,
                actions=(*blue_batch.actions, *red_batch.actions),
                high_level_intent={
                    "blue": blue_batch.high_level_intent,
                    "red": red_batch.high_level_intent,
                },
            )
            public_events = self.resolve_combat(combined)
            self._apply_pending_collision_damage()
        finally:
            self._defer_collision_damage = False
            self._pending_collision_lifecycles = {}
            self._pending_navigation = {}
            self._pending_ramming_intents = {}
        return (
            self.public_observation(Side.BLUE),
            self.public_observation(Side.RED),
            self._terminated or terminated,
            {
                "public_combat_events": public_events,
                "collision_events": self.last_collision_events,
                **info,
            },
        )

    def _update_mission_result(
        self,
        previous_positions: dict[str, tuple[float, float, float]] | None = None,
    ) -> None:
        if self.world is None:
            return
        if self._ad2_adjudicator is not None:
            self._ad2_adjudicator.latch_breaches(
                self.world,
                self.world.tick,
                previous_positions=previous_positions,
            )
            ad2_result = self._ad2_adjudicator.advance(
                self.world,
                tick=self.world.tick,
                scheduled_count=len(self.scheduled_entities),
            )
            self.world.mission_status = ad2_result.outcome.value
            self.wave_events.extend(
                self._ad2_adjudicator.events[self._ad2_adjudication_event_count :]
            )
            self._ad2_adjudication_event_count = len(self._ad2_adjudicator.events)
            if ad2_result.terminal:
                self._terminated = True
                self._ended = True
            return
        if self._adjudicator is None:
            return
        if self._runtime is None or self._runtime.threat_entity_id is None:
            raise RuntimeError("adjudication runtime does not define a threat entity")
        threat = self.world.registry.get(self._runtime.threat_entity_id)
        if not isinstance(threat, PlatformAsset):
            raise RuntimeError("red-uav-1 must remain a platform asset")
        if self._runtime.protection_radius_m is None:
            raise RuntimeError("adjudication runtime does not define a protection radius")
        protection_radius = self._runtime.protection_radius_m
        alive = threat.lifecycle in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}
        breach = (
            alive and math.dist(threat.position[:2], self._protected_point) <= protection_radius
        )
        available_lifecycles = {Lifecycle.ACTIVE, Lifecycle.DEGRADED}
        interceptors = tuple(
            entity
            for entity in self.world.registry.all_entities()
            if isinstance(entity, PlatformAsset)
            and entity.side is Side.BLUE
            and entity.platform_type == "uav"
        )
        shore_defenses = tuple(
            entity
            for entity in self.world.registry.all_entities()
            if isinstance(entity, PlatformAsset)
            and entity.side is Side.BLUE
            and entity.platform_type == "shore_radar"
        )
        unavailable_interceptor_lifecycles = {
            Lifecycle.DESTROYED,
            Lifecycle.CRASHED,
            Lifecycle.OFFLINE,
        }
        all_interceptors_unavailable = (
            bool(interceptors)
            and all(
                entity.lifecycle in unavailable_interceptor_lifecycles for entity in interceptors
            )
            and not any(
                entity.lifecycle in available_lifecycles
                and entity.components.weapons_operational
                and entity.components.weapon_inventory.get("shore_ciws", 0) > 0
                for entity in shore_defenses
            )
        )
        result = self._adjudicator.advance(
            tick=self.world.tick,
            breach_candidate=breach,
            threat_destroyed=threat.lifecycle is Lifecycle.DESTROYED,
            all_interceptors_unavailable=all_interceptors_unavailable,
        )
        self.world.mission_status = result.outcome.value
        if result.terminal:
            self._terminated = True
            self._ended = True

    def _observation(self) -> StructuredObservation:
        delta = self._goal - self._position
        distance = float(np.linalg.norm(delta))
        direction = delta / distance if distance else np.zeros(2)
        controlled_energy = 1.0
        if self.world is not None:
            if self._primary_entity_id is None:
                raise RuntimeError("formal runtime requires a primary compatibility entity")
            controlled = self.world.registry.get(self._primary_entity_id)
            if isinstance(controlled, PlatformAsset):
                controlled_energy = controlled.components.energy
        return {
            "energy": controlled_energy,
            "goal_direction": direction.astype(np.float32).tolist(),
            "mission_briefing": render_briefing(self.scenario),
            "mission_status": (
                "terminated" if self._terminated else "timeout" if self._truncated else "running"
            ),
            "position": self._position.astype(np.float32).tolist(),
            "scenario_id": self.scenario.scenario_id,
            "time_remaining": self._time_limit_ticks - self._tick,
            "timestamp": self._tick,
            "velocity": self._velocity.astype(np.float32).tolist(),
        }

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[StructuredObservation, dict[str, Any]]:
        effective_seed = self.default_seed if seed is None else seed
        super().reset(seed=effective_seed)
        options = options or {}
        self._position = np.array(
            options.get("position", self._initial_position), dtype=np.float64, copy=True
        )
        if (
            self._position.shape != (2,)
            or np.any(self._position < self._lower)
            or np.any(self._position > self._upper)
        ):
            raise ValueError("reset position must be a two-coordinate point within world bounds")
        self._velocity.fill(0.0)
        self._tick = 0
        self._ended = False
        self._terminated = False
        self._truncated = False
        self.last_advanced_entity_ids = ()
        self.last_dynamics_trace = ()
        self.last_energy_trace = ()
        self.last_combat_audit = ()
        self.last_public_combat_events = ()
        self._pending_navigation = {}
        self._pending_ramming_intents = {}
        self._defer_collision_damage = False
        self._pending_collision_lifecycles = {}
        self.last_collision_events = ()
        self._ad2_event_rng.reset(int(effective_seed or 0))
        self._ad2_suppressed_until = {}
        self._ad2_suppression_prior = {}
        self._ad2_suppression_triggered = False
        if self._runtime is not None:
            self._runtime = (
                create_runtime_from_resolved(self._resolved_scenario, int(effective_seed or 0))
                if self._resolved_scenario is not None
                else create_scenario_runtime(self.scenario.scenario_id, int(effective_seed or 0))
            )
            self.world = self._runtime.world
            self.geo_frame = self._runtime.geo_frame
            self._primary_entity_id = self._runtime.primary_entity_id
            self.scheduled_entities = self._runtime.scheduled_entities
            self.wave_events = []
            self._usv_mmg_adapters = {}
            if self._md_int_config is not None:
                self._reset_sensor_engines(int(effective_seed or 0))
                self._ad2_perception = None
            elif self._runtime.md_ad_config is not None:
                self._ad2_perception = AD2Perception(
                    self._runtime.md_ad_config, int(effective_seed or 0)
                )
                protected_point = (
                    float(self._runtime.protected_point[0]),
                    float(self._runtime.protected_point[1]),
                )
                self._ad2_combat = AD2Combat(
                    self._runtime.md_ad_config,
                    int(effective_seed or 0),
                    protected_point,
                )
                self._ad2_adjudicator = MDAD002Adjudicator(
                    protected_point=protected_point,
                    protection_radius_m=self._runtime.md_ad_config.denial_zone.radius,
                    breach_threshold=(self._runtime.md_ad_config.adjudication.breach_threshold),
                    time_limit_ticks=self._runtime.time_limit_ticks,
                )
                self._ad2_adjudication_event_count = 0
                self._perception_event_count = 0
            self._reset_communication(int(effective_seed or 0))
            self._combat_rng = SessionRNG(int(effective_seed or 0))
            self._adjudicator = None
            self._spawn_due(0)
            if self._runtime.md_ad_config is not None:
                protected = (
                    float(self._protected_point[0]),
                    float(self._protected_point[1]),
                    100.0,
                )
                difficulty = self._runtime.md_ad_config.difficulty
                self._ad2_blue_agent = (
                    AD2MediumBlueAgent(protected)
                    if difficulty == "medium"
                    else AD2EasyBlueAgent(protected)
                    if difficulty == "easy"
                    else AD2HardBlueAgent(protected)
                )
                if self._ad2_blue_agent is not None:
                    self._ad2_blue_agent.reset(
                        self.public_observation(Side.BLUE), int(effective_seed or 0)
                    )
        return self._observation(), {"scenario_id": self.scenario.scenario_id}

    def step(
        self, action: NDArray[np.float32]
    ) -> tuple[StructuredObservation, float, bool, bool, dict[str, Any]]:
        if self._ended:
            raise RuntimeError("step() called after episode end; call reset()")
        if self.world is None:
            speed, heading = validate_kinematic_actions(action)
        else:
            values = np.asarray(action, dtype=np.float64)
            if values.shape != (2,) or not np.all(np.isfinite(values)):
                raise ValueError("UAV action must contain finite speed and heading values")
            speed, heading = float(values[0]), float(values[1])
            if not 0.0 <= speed <= 80.0 or not 0.0 <= heading < 360.0:
                raise ValueError("UAV speed/heading must be within [0,80] and [0,360)")
        radians = heading_deg_to_math_rad(float(heading))
        self._velocity = float(speed) * np.array([math.cos(radians), math.sin(radians)])
        old_distance = float(np.linalg.norm(self._goal - self._position))
        if self.world is not None:
            self._apply_ad2_difficulty_events(self._tick + 1)
            traversed = tuple(
                entity
                for entity in self.world.entities_stable()
                if entity.lifecycle
                in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
            )
            previous_positions = {entity.id: entity.position for entity in traversed}
            self.last_advanced_entity_ids = tuple(entity.id for entity in traversed)
            trace: list[tuple[str, str]] = []
            for entity in traversed:
                if (
                    isinstance(entity, PlatformAsset)
                    and not entity.components.propulsion_operational
                ):
                    self.world.registry.update(
                        entity.model_copy(update={"velocity": (0.0, 0.0, 0.0)})
                    )
                    trace.append((entity.id, "propulsion_suppressed"))
                    continue
                if not isinstance(entity, PlatformAsset) or entity.platform_type != "uav":
                    if isinstance(entity, PlatformAsset) and entity.platform_type == "usv":
                        pending = self._pending_navigation.get(entity.id)
                        if pending is not None and pending[0] == 0.0:
                            self.world.registry.update(
                                entity.model_copy(update={"velocity": (0.0, 0.0, 0.0)})
                            )
                            trace.append((entity.id, "hold"))
                            continue
                        if entity.id not in self._usv_mmg_adapters:
                            from openmdbench.domains.surface.mmg_adapter import (
                                MMGState,
                                Sim2SeaMMGAdapter,
                            )

                            self._usv_mmg_adapters[entity.id] = Sim2SeaMMGAdapter(
                                MMGState(
                                    position_xy_m=entity.position[:2],
                                    heading_deg=entity.heading_deg,
                                    body_velocity_mps=(0.0, 0.0, 0.0),
                                )
                            )
                        has_navigation_command = entity.id in self._pending_navigation
                        commanded_speed, commanded_heading, _commanded_altitude = (
                            self._pending_navigation.get(
                                entity.id,
                                (
                                    math.hypot(entity.velocity[0], entity.velocity[1]),
                                    entity.heading_deg,
                                    entity.position[2],
                                ),
                            )
                        )
                        usv_result = self._usv_mmg_adapters[entity.id].step_target(
                            target_speed_mps=commanded_speed,
                            target_heading_deg=commanded_heading,
                        )
                        position_xy = (
                            entity.position[:2]
                            if not has_navigation_command
                            and math.hypot(entity.velocity[0], entity.velocity[1]) == 0.0
                            else usv_result.position_xy_m
                        )
                        psi = heading_deg_to_math_rad(usv_result.heading_deg)
                        surge, sway, _yaw_rate = usv_result.body_velocity_mps
                        self.world.registry.update(
                            entity.model_copy(
                                update={
                                    "position": (*position_xy, entity.position[2]),
                                    "velocity": (
                                        math.cos(psi) * surge - math.sin(psi) * sway,
                                        math.sin(psi) * surge + math.cos(psi) * sway,
                                        0.0,
                                    ),
                                    "heading_deg": usv_result.heading_deg,
                                }
                            )
                        )
                        trace.append((entity.id, "sim2sea_mmg"))
                        continue
                    if isinstance(entity, PlatformAsset) and entity.platform_type == "shore_radar":
                        radar_result = apply_shore_command(
                            ShoreRadarState(
                                position=entity.position,
                                beam_heading_deg=entity.heading_deg,
                                sensor_mode=entity.components.sensor_mode,
                            ),
                            "hold_position",
                            {},
                        )
                        self.world.registry.update(
                            entity.model_copy(update={"position": radar_result.position})
                        )
                        trace.append((entity.id, "fixed_shore"))
                        continue
                    trace.append((entity.id, "hold"))
                    continue
                current_speed = math.hypot(entity.velocity[0], entity.velocity[1])
                default_command = (
                    (speed, heading, entity.position[2])
                    if entity.id == self._primary_entity_id
                    else (current_speed, entity.heading_deg, entity.position[2])
                )
                commanded_speed, commanded_heading, commanded_altitude = (
                    self._pending_navigation.get(entity.id, default_command)
                )
                factor = 0.7 if entity.lifecycle is Lifecycle.DEGRADED else 1.0
                result = step_uav(
                    UAVState(
                        position=entity.position,
                        heading_deg=entity.heading_deg,
                        speed_mps=current_speed,
                        energy=entity.components.energy,
                    ),
                    UAVCommand(
                        heading_deg=commanded_heading,
                        speed_mps=commanded_speed,
                        altitude_m=commanded_altitude,
                    ),
                    performance_factor=factor,
                )
                result_heading_rad = heading_deg_to_math_rad(result.heading_deg)
                self.world.registry.update(
                    entity.model_copy(
                        update={
                            "position": result.position,
                            "velocity": (
                                result.speed_mps * math.cos(result_heading_rad),
                                result.speed_mps * math.sin(result_heading_rad),
                                result.position[2] - entity.position[2],
                            ),
                            "heading_deg": result.heading_deg,
                        }
                    )
                )
                trace.append((entity.id, "step_uav"))
            self.last_dynamics_trace = tuple(trace)
            energy_trace: list[tuple[str, float]] = []
            for entity in self.world.entities_stable():
                if not isinstance(entity, PlatformAsset):
                    continue
                if entity.platform_type == "shore_radar":
                    energy_trace.append((entity.id, entity.components.energy))
                    continue
                if entity.lifecycle not in {
                    Lifecycle.ACTIVE,
                    Lifecycle.DEGRADED,
                    Lifecycle.BREACHED_ACTIVE,
                }:
                    continue
                entity_speed = math.hypot(entity.velocity[0], entity.velocity[1])
                energy_result = consume_energy(
                    entity.platform_type,
                    entity.components.energy,
                    entity_speed,
                    sensor_active=entity.components.sensor_mode != "off",
                    profile=(
                        AD2_ENERGY_PROFILES[entity.platform_type]
                        if self._runtime is not None and self._runtime.md_ad_config is not None
                        else ENERGY_PROFILES[entity.platform_type]
                    ),
                )
                lifecycle = (
                    Lifecycle(energy_result.operational_status)
                    if energy_result.energy == 0.0
                    else entity.lifecycle
                )
                self.world.registry.update(
                    entity.model_copy(
                        update={
                            "components": entity.components.model_copy(
                                update={"energy": energy_result.energy}
                            ),
                            "lifecycle": lifecycle,
                        }
                    )
                )
                energy_trace.append((entity.id, energy_result.energy))
            self.last_energy_trace = tuple(energy_trace)
            self._apply_world_constraints(self._tick + 1, previous_positions)
            self._update_sensors(self._tick + 1)
            if self._primary_entity_id is None:
                raise RuntimeError("formal runtime requires a primary compatibility entity")
            controlled = self.world.registry.get(self._primary_entity_id)
            self._position = np.asarray(controlled.position[:2], dtype=np.float64)
            self._velocity = np.asarray(controlled.velocity[:2], dtype=np.float64)
        else:
            self._position += self._velocity
        self._tick += 1
        if self.world is not None:
            self._spawn_due(self._tick)
            self.world.tick = self._tick
            self.world.time_remaining = max(
                0,
                (self._runtime.time_limit_ticks if self._runtime is not None else 0) - self._tick,
            )
            self._update_mission_result(previous_positions)
        outside = bool(np.any(self._position < self._lower) or np.any(self._position > self._upper))
        reached = float(np.linalg.norm(self._goal - self._position)) <= 10.0
        if self.world is not None:
            terminated = self._terminated
            truncated = (
                self._adjudicator is None
                and self._tick >= self._time_limit_ticks
                and not terminated
            )
        else:
            terminated = outside or reached
            truncated = self._tick >= self._time_limit_ticks and not terminated
        self._ended = terminated or truncated
        self._terminated = terminated
        self._truncated = truncated
        reward = old_distance - float(np.linalg.norm(self._goal - self._position))
        return (
            self._observation(),
            reward,
            terminated,
            truncated,
            {
                "outside_world": outside,
                "reached_goal": reached,
            },
        )

    def authority_world_snapshot(self) -> dict[str, Any]:
        """Return the authority-world payload used by the completed match log."""
        if self.world is None:
            raise RuntimeError("authority world snapshot requires an initialized world")
        return {
            "session_id": self.world.session_id,
            "entities": [entity.model_dump(mode="json") for entity in self.world.entities_stable()],
            "contacts": {
                side.value: [asdict(track) for track in tracks]
                for side, tracks in self.world.contacts.items()
            },
            "tick": self.world.tick,
            "mission_briefing": self.world.mission_briefing,
            "mission_status": self.world.mission_status,
            "time_remaining": self.world.time_remaining,
            "weather": self.world.weather,
            "sea_state": self.world.sea_state,
        }

    def export_state(self) -> dict[str, Any]:
        """Return every mutable field needed for exact continuation."""
        state: dict[str, Any] = {
            "position": self._position.tolist(),
            "velocity": self._velocity.tolist(),
            "goal": self._goal.tolist(),
            "tick": self._tick,
            "terminated": self._terminated,
            "truncated": self._truncated,
            "numpy_rng": self.np_random.bit_generator.state,
            "map_identity": self.map_metadata,
            "runtime_metadata": (
                asdict(self._runtime.metadata) if self._runtime is not None else None
            ),
            "scheduled_entities": [asdict(entity) for entity in self.scheduled_entities],
            "wave_events": list(self.wave_events),
            "last_collision_events": list(self.last_collision_events),
        }
        if self.world is not None:
            state["world"] = self.authority_world_snapshot()
            state["sensor_engines"] = {
                sensor_id: engine.snapshot()
                for sensor_id, engine in sorted(self._sensor_engines.items())
            }
            state["ad2_perception"] = (
                self._ad2_perception.snapshot() if self._ad2_perception is not None else None
            )
            state["ad2_combat"] = (
                self._ad2_combat.snapshot() if self._ad2_combat is not None else None
            )
            state["ad2_adjudication"] = (
                self._ad2_adjudicator.snapshot() if self._ad2_adjudicator is not None else None
            )
            state["ad2_blue_agent"] = (
                self._ad2_blue_agent.snapshot() if self._ad2_blue_agent is not None else None
            )
            state["ad2_pending_delivered_actions"] = [
                action.model_dump(mode="json") for action in self._ad2_pending_delivered_actions
            ]
            state["ad2_event_rng"] = self._ad2_event_rng.snapshot()
            state["ad2_suppressed_until"] = dict(sorted(self._ad2_suppressed_until.items()))
            state["ad2_suppression_prior"] = dict(sorted(self._ad2_suppression_prior.items()))
            state["ad2_suppression_triggered"] = self._ad2_suppression_triggered
            state["communication"] = (
                self._communication.snapshot() if self._communication is not None else None
            )
            state["combat_rng"] = self._combat_rng.snapshot()
            state["usv_mmg_adapters"] = {
                entity_id: adapter.snapshot()
                for entity_id, adapter in sorted(self._usv_mmg_adapters.items())
            }
            state["adjudication"] = (
                self._adjudicator.snapshot() if self._adjudicator is not None else None
            )
        return state

    def import_state(self, state: dict[str, Any]) -> StructuredObservation:
        """Restore state without replaying or consuming randomness."""
        if state.get("map_identity") != self.map_metadata:
            raise ValueError("checkpoint map identity mismatch")
        expected_runtime = asdict(self._runtime.metadata) if self._runtime is not None else None
        if json.dumps(state.get("runtime_metadata"), sort_keys=True) != json.dumps(
            expected_runtime, sort_keys=True
        ):
            raise ValueError("checkpoint runtime metadata/config hash mismatch")
        scheduled_records = state.get("scheduled_entities")
        if not isinstance(scheduled_records, list):
            raise ValueError("checkpoint scheduled entity descriptors mismatch")
        known = {
            item.entity_id: item
            for item in (self._runtime.scheduled_entities if self._runtime else ())
        }
        restored_scheduled = tuple(
            ScheduledEntity(
                entity_id=str(record["entity_id"]),
                wave_id=str(record["wave_id"]),
                scheduled_tick=int(record["scheduled_tick"]),
                position=cast(
                    tuple[float, float, float],
                    tuple(float(value) for value in record["position"]),
                ),
                heading_deg=float(record["heading_deg"]),
                speed_mps=float(record["speed_mps"]),
                side=Side(str(record.get("side", known[str(record["entity_id"])].side.value))),
                platform_type=cast(
                    Literal["uav", "usv", "shore_radar", "auv"],
                    str(
                        record.get(
                            "platform_type",
                            known[str(record["entity_id"])].platform_type,
                        )
                    ),
                ),
                weapon_inventory=(
                    None
                    if record.get("weapon_inventory") is None
                    else {
                        str(key): int(value)
                        for key, value in cast(dict[str, Any], record["weapon_inventory"]).items()
                    }
                ),
                required_surface=cast(
                    Literal["water", "land", "any"],
                    str(
                        record.get(
                            "required_surface",
                            known[str(record["entity_id"])].required_surface,
                        )
                    ),
                ),
            )
            for record in scheduled_records
        )
        if any(
            item.entity_id not in known or item != known[item.entity_id]
            for item in restored_scheduled
        ):
            raise ValueError("checkpoint scheduled entity descriptors mismatch")
        self.scheduled_entities = restored_scheduled
        self.wave_events = list(state.get("wave_events", []))
        self._position = np.asarray(state["position"], dtype=np.float64)
        self._velocity = np.asarray(state["velocity"], dtype=np.float64)
        self._goal = np.asarray(state["goal"], dtype=np.float64)
        self._tick = int(state["tick"])
        self._terminated = bool(state["terminated"])
        self._truncated = bool(state["truncated"])
        self._ended = self._terminated or self._truncated
        self.np_random.bit_generator.state = state["numpy_rng"]
        world_record = state.get("world")
        if world_record is not None:
            self.world = WorldState(
                session_id=str(world_record["session_id"]),
                tick=int(world_record["tick"]),
                mission_briefing=str(world_record["mission_briefing"]),
                mission_status=str(world_record["mission_status"]),
                time_remaining=int(world_record["time_remaining"]),
                weather=str(world_record["weather"]),
                sea_state=int(world_record.get("sea_state", 2)),
            )
            for entity_record in world_record["entities"]:
                self.world.registry.register(PlatformAsset.model_validate(entity_record))
            contacts: dict[Side, list[ContactTrack]] = {}
            for side_value, track_records in world_record["contacts"].items():
                side = Side(side_value)
                contacts[side] = []
                for track_record in track_records:
                    values = dict(track_record)
                    values["owner_side"] = Side(values["owner_side"])
                    values["estimated_domain"] = Domain(values["estimated_domain"])
                    contacts[side].append(ContactTrack(**values))
            self.world.contacts = contacts
            self._sensor_engines = {
                sensor_id: DetectionEngine.from_snapshot(snapshot)
                for sensor_id, snapshot in state["sensor_engines"].items()
            }
            perception = state.get("ad2_perception")
            self._ad2_perception = (
                AD2Perception.from_snapshot(self._runtime.md_ad_config, perception)
                if perception is not None
                and self._runtime is not None
                and self._runtime.md_ad_config is not None
                else None
            )
            self._perception_event_count = (
                len(self._ad2_perception.events) if self._ad2_perception is not None else 0
            )
            ad2_combat = state.get("ad2_combat")
            self._ad2_combat = (
                AD2Combat.from_snapshot(self._runtime.md_ad_config, ad2_combat)
                if ad2_combat is not None
                and self._runtime is not None
                and self._runtime.md_ad_config is not None
                else None
            )
            ad2_adjudication = state.get("ad2_adjudication")
            self._ad2_adjudicator = (
                MDAD002Adjudicator.from_snapshot(ad2_adjudication)
                if ad2_adjudication is not None
                else None
            )
            self._ad2_adjudication_event_count = (
                len(self._ad2_adjudicator.events) if self._ad2_adjudicator is not None else 0
            )
            blue_agent_state = state.get("ad2_blue_agent")
            self._ad2_blue_agent = None
            if (
                blue_agent_state is not None
                and self._runtime is not None
                and self._runtime.md_ad_config is not None
            ):
                protected = (
                    float(self._protected_point[0]),
                    float(self._protected_point[1]),
                    100.0,
                )
                difficulty = self._runtime.md_ad_config.difficulty
                self._ad2_blue_agent = (
                    AD2MediumBlueAgent(protected)
                    if difficulty == "medium"
                    else AD2EasyBlueAgent(protected)
                    if difficulty == "easy"
                    else AD2HardBlueAgent(protected)
                )
                if self._ad2_blue_agent is not None:
                    self._ad2_blue_agent.restore(blue_agent_state)
            self._ad2_pending_delivered_actions = [
                RedPlatformAction.model_validate(record)
                for record in state.get("ad2_pending_delivered_actions", [])
            ]
            self.last_collision_events = tuple(
                dict(record) for record in state.get("last_collision_events", [])
            )
            self._ad2_event_rng = SessionRNG.from_snapshot(
                state.get("ad2_event_rng", {"seed": 0, "streams": {}})
            )
            self._ad2_suppressed_until = {
                str(key): int(value) for key, value in state.get("ad2_suppressed_until", {}).items()
            }
            self._ad2_suppression_prior = {
                str(key): dict(value)
                for key, value in state.get("ad2_suppression_prior", {}).items()
            }
            self._ad2_suppression_triggered = bool(state.get("ad2_suppression_triggered", False))
            communication = state.get("communication")
            self._communication = (
                CommunicationNetwork.from_snapshot(SessionRNG(0), communication)
                if communication is not None
                else None
            )
            self._combat_rng = SessionRNG.from_snapshot(state["combat_rng"])
            self._adjudicator = None
            from openmdbench.domains.surface.mmg_adapter import Sim2SeaMMGAdapter

            self._usv_mmg_adapters = {
                entity_id: Sim2SeaMMGAdapter.from_snapshot(snapshot)
                for entity_id, snapshot in state.get("usv_mmg_adapters", {}).items()
            }
        return self._observation()


class TensorObservationWrapper(
    gym.ObservationWrapper[NDArray[np.float32], NDArray[np.float32], StructuredObservation]
):
    """Convert the structured contract to an eight-value training tensor."""

    def __init__(self, env: OpenMDBenchEnv) -> None:
        super().__init__(env)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(8,), dtype=np.float32)

    def observation(self, observation: StructuredObservation) -> NDArray[np.float32]:
        position = np.asarray(observation["position"], dtype=np.float32)
        velocity = np.asarray(observation["velocity"], dtype=np.float32)
        direction = np.asarray(observation["goal_direction"], dtype=np.float32)
        tick = float(cast(int, observation["timestamp"]))
        remaining = float(cast(int, observation["time_remaining"]))
        return np.concatenate((position, velocity, direction, [tick, remaining])).astype(np.float32)


def _make_tensor_env(scenario_id: str, seed: int | None) -> TensorObservationWrapper:
    return TensorObservationWrapper(OpenMDBenchEnv(scenario_id=scenario_id, seed=seed))


def make_vector_env(
    scenario_ids: list[str] | tuple[str, ...], *, seeds: list[int] | tuple[int, ...] | None = None
) -> SyncVectorEnv:
    """Create isolated, synchronously batched scenario sessions."""
    if not scenario_ids:
        raise ValueError("at least one scenario_id is required")
    if seeds is None:
        seeds = tuple(0 for _ in scenario_ids)
    if len(seeds) != len(scenario_ids):
        raise ValueError("seeds and scenario_ids must have the same length")
    factories = [
        partial(_make_tensor_env, scenario_id, seed)
        for scenario_id, seed in zip(scenario_ids, seeds, strict=True)
    ]
    return SyncVectorEnv(factories)

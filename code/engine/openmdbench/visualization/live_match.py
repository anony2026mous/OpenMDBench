"""Interactive visualization support for retained scenarios."""

from __future__ import annotations

import math
from typing import Any, Literal, cast

from openmdbench.core.entities import PlatformAsset
from openmdbench.runners.md_ad_002 import (
    AD2MatchResult,
    run_md_ad_002_easy,
    run_md_ad_002_hard,
    run_md_ad_002_medium,
)
from openmdbench.scoring.md_ad_002 import AD2MetricState, score_metric_state
from openmdbench.visualization.live import VisualizationView, frame_from_world
from openmdbench.visualization.schema import (
    MissionPanel,
    ScoreSets,
    SideScore,
    VisualizationEvent,
)


def run_live_md_ad_002(
    *,
    scenario_id: Literal["MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"],
    seed: int = 73,
    speed: float = 20.0,
    view: VisualizationView = "referee",
    map_extent: Literal["full", "task"] = "task",
    max_ticks: int = 1_800,
    block_on_finish: bool = True,
) -> AD2MatchResult:
    """Run any MD-AD-002 difficulty with a shared, retained-mode live display."""
    if speed <= 0.0:
        raise ValueError("live visualization speed must be positive")
    import matplotlib.pyplot as plt

    from openmdbench.visualization.dashboard import VisualizationDashboard
    from openmdbench.visualization.renderer import MatplotlibRenderer

    plt.ion()
    figure, axes = plt.subplots(figsize=(16, 10))
    dashboard: VisualizationDashboard | None = None
    announced_spawn_events: set[tuple[int, str]] = set()
    announced_kills: set[str] = set()

    def update(
        env: Any,
        blue: dict[str, Any],
        red: dict[str, Any],
        info: dict[str, Any],
        metric_state: AD2MetricState,
    ) -> None:
        nonlocal dashboard
        if not plt.fignum_exists(figure.number):
            raise KeyboardInterrupt("visualization window closed")
        if env.world is None or env.geo_frame is None or env._runtime is None:
            raise RuntimeError("live MD-AD-002 visualization requires its formal runtime")
        config = env._runtime.md_ad_config
        if config is None:
            raise RuntimeError("live MD-AD-002 visualization requires scenario configuration")
        if dashboard is None:
            layers = env.geo_frame.visualization_layers
            if map_extent == "full":
                bounds = layers.bounds()
            else:
                positions = [entity.position for entity in env.world.entities_stable()]
                positions.extend(
                    (*env.geo_frame.wgs84_to_local(zone.lon_deg, zone.lat_deg), 0.0)
                    for zone in config.spawn_zone_geometry.values()
                )
                positions.append((*tuple(float(value) for value in env._protected_point), 0.0))
                bounds = (
                    min(position[0] for position in positions) - 5_000.0,
                    min(position[1] for position in positions) - 5_000.0,
                    max(position[0] for position in positions) + 5_000.0,
                    max(position[1] for position in positions) + 5_000.0,
                )
            axes.set_xlim(bounds[0], bounds[2])
            axes.set_ylim(bounds[1], bounds[3])
            axes.set_aspect("equal", adjustable="box")
            axes.set_xlabel("Local East (m)")
            axes.set_ylabel("Local North (m)")
            renderer = MatplotlibRenderer(
                axes,
                static_polygons=layers.land_polygons,
                static_lines=layers.coastline_lines,
            )
            dashboard = VisualizationDashboard(renderer, view=view)

        events = [
            VisualizationEvent(
                event_type="protection_zone",
                message="8 km denial zone",
                data={
                    "center": tuple(float(value) for value in env._protected_point),
                    "radius_m": float(config.denial_zone.radius),
                },
            )
        ]
        entities = {entity.id: entity for entity in env.world.entities_stable()}
        entity_waves = {
            str(event["entity_id"]): str(event["wave_id"])
            for event in env.wave_events
            if event.get("event_type") == "entity_spawned"
            and event.get("entity_id") is not None
            and event.get("wave_id") is not None
        }
        breached_ids = env._ad2_adjudicator.breached_ids
        wave_summaries: list[dict[str, object]] = []
        for wave in config.waves:
            wave_entities = tuple(
                entity
                for entity_id, wave_id in sorted(entity_waves.items())
                if wave_id == wave.id
                for entity in (entities.get(entity_id),)
                if isinstance(entity, PlatformAsset)
            )
            wave_summaries.append(
                {
                    "wave_id": wave.id,
                    "planned": wave.count,
                    "spawned": len(wave_entities),
                    "active": sum(
                        entity.lifecycle.value in {"active", "degraded", "breached_active"}
                        for entity in wave_entities
                    ),
                    "destroyed": sum(
                        entity.lifecycle.value
                        in {
                            "destroyed",
                            "crashed",
                            "impacted",
                            "out_of_bounds",
                            "removed",
                        }
                        for entity in wave_entities
                    ),
                    "breached": sum(entity.id in breached_ids for entity in wave_entities),
                }
            )
        next_scheduled = min(
            env.scheduled_entities,
            key=lambda item: (item.scheduled_tick, item.wave_id, item.entity_id),
            default=None,
        )
        events.append(
            VisualizationEvent(
                event_type="wave_status",
                data={
                    "entity_waves": entity_waves,
                    "waves": tuple(wave_summaries),
                    "next_wave": (
                        {
                            "wave_id": next_scheduled.wave_id,
                            "spawn_tick": next_scheduled.scheduled_tick,
                            "ticks_remaining": max(
                                0, next_scheduled.scheduled_tick - env.world.tick
                            ),
                        }
                        if next_scheduled is not None
                        else None
                    ),
                    "visible_to": ("referee",),
                },
            )
        )
        for scenario_event in env.wave_events:
            if scenario_event.get("event_type") != "entity_spawned":
                continue
            entity_id = str(scenario_event.get("entity_id", ""))
            event_tick = int(scenario_event.get("tick", 0))
            event_key = (event_tick, entity_id)
            if event_key in announced_spawn_events:
                continue
            entity = entities.get(entity_id)
            if entity is None:
                continue
            announced_spawn_events.add(event_key)
            wave_id = str(scenario_event.get("wave_id", "unknown"))
            events.append(
                VisualizationEvent(
                    event_type="wave_spawn",
                    entity_id=entity_id,
                    message=f"{wave_id.upper()} DEPLOYED: {entity_id}",
                    data={
                        "position": entity.position,
                        "wave_id": wave_id,
                        "spawn_tick": event_tick,
                        "visible_to": ("referee",),
                    },
                )
            )
        blue_intent = blue.get("high_level_intent", {})
        evading = (
            {str(entity_id) for entity_id in blue_intent.get("evading", ())}
            if isinstance(blue_intent, dict)
            else set()
        )
        strategy = str(blue_intent.get("strategy", "")) if isinstance(blue_intent, dict) else ""
        for action in blue.get("actions", ()):
            if not isinstance(action, dict):
                continue
            entity_id = str(action.get("entity_id", ""))
            if not (entity_id in evading or strategy == "hard_multi_axis_continuous_serpentine"):
                continue
            entity = entities.get(entity_id)
            target = action.get("target")
            if entity is None or not isinstance(target, (list, tuple)) or len(target) < 2:
                continue
            east = float(target[0]) - entity.position[0]
            north = float(target[1]) - entity.position[1]
            distance = math.hypot(east, north)
            scale = min(4_000.0 / distance, 1.0) if distance > 0.0 else 0.0
            events.append(
                VisualizationEvent(
                    event_type="maneuver_vector",
                    entity_id=entity_id,
                    data={
                        "start": entity.position,
                        "end": (
                            entity.position[0] + east * scale,
                            entity.position[1] + north * scale,
                            entity.position[2],
                        ),
                        "mode": "evasion" if entity_id in evading else "serpentine",
                        "visible_to": ("referee",),
                    },
                )
            )
        for sensor in config.sensors:
            for entity_id in sensor.assigned_entities:
                entity = entities.get(entity_id)
                if entity is None or not isinstance(entity, PlatformAsset):
                    continue
                if entity.lifecycle.value not in {"active", "degraded"}:
                    continue
                if entity.components.sensor_mode == "off":
                    continue
                events.append(
                    VisualizationEvent(
                        event_type="sensor_range",
                        entity_id=entity_id,
                        data={
                            "center": entity.position[:2],
                            "radius_m": float(sensor.range_m),
                            "side": entity.side.value,
                        },
                    )
                )
        for combat_event in env.last_combat_audit:
            if combat_event.get("event_type") != "combat_round":
                continue
            attacker_id = combat_event.get("attacker_id") or combat_event.get("attacker_entity_id")
            target_id = combat_event.get("target_id_internal") or combat_event.get(
                "target_entity_id_internal"
            )
            attacker = entities.get(str(attacker_id))
            target = entities.get(str(target_id))
            if attacker is None or target is None:
                continue
            hit = bool(combat_event.get("hit"))
            events.append(
                VisualizationEvent(
                    event_type="weapon_fired",
                    entity_id=str(attacker_id),
                    message=(
                        f"{combat_event.get('weapon_id', 'weapon')} {'HIT' if hit else 'MISS'}"
                    ),
                    data={
                        "start": attacker.position,
                        "end": target.position,
                        "hit": hit,
                        "weapon_id": combat_event.get("weapon_id", "weapon"),
                        "target_health": (
                            target.components.health if isinstance(target, PlatformAsset) else None
                        ),
                        "target_status": target.lifecycle.value,
                        "visible_to": ("referee",),
                    },
                )
            )
            if hit and target.lifecycle.value == "destroyed" and target.id not in announced_kills:
                announced_kills.add(target.id)
                weapon_id = str(combat_event.get("weapon_id", "weapon"))
                events.append(
                    VisualizationEvent(
                        event_type="entity_killed",
                        entity_id=str(attacker_id),
                        message=f"{attacker_id} [{weapon_id}] destroyed {target.id}",
                        data={
                            "attacker_id": str(attacker_id),
                            "weapon_id": weapon_id,
                            "target_id": target.id,
                            "tick": env.world.tick,
                            "visible_to": ("referee",),
                        },
                    )
                )
        communication_events = cast(
            tuple[dict[str, object], ...], info.get("communication_events", ())
        )
        network = env._communication
        if network is not None:
            for communication_event in communication_events:
                event_type = str(communication_event.get("event_type", "communication"))
                route_value = communication_event.get("route", ())
                route = (
                    tuple(str(endpoint_id) for endpoint_id in route_value)
                    if isinstance(route_value, (list, tuple))
                    else ()
                )
                if not route and event_type == "command_not_delivered":
                    entity_id = str(communication_event.get("entity_id", ""))
                    route = ("red-command", entity_id)
                points = tuple(
                    network.endpoints[endpoint_id].position
                    for endpoint_id in route
                    if endpoint_id in network.endpoints
                )
                status = {
                    "message_queued": "queued",
                    "message_delivered": "delivered",
                    "message_dropped": "dropped",
                    "message_expired": "expired",
                    "command_not_delivered": "blocked",
                    "command_discarded_unavailable": "blocked",
                }.get(event_type)
                if status is not None and len(points) >= 2:
                    events.append(
                        VisualizationEvent(
                            event_type="communication_route",
                            message=(f"COMM {status.upper()} {' -> '.join(route)}"),
                            data={
                                "points": points,
                                "route": route,
                                "status": status,
                                "sent_tick": communication_event.get("sent_tick"),
                                "arrival_tick": communication_event.get("arrival_tick"),
                                "physical_latency_ms": communication_event.get(
                                    "physical_latency_ms"
                                ),
                                "visible_to": ("referee", "red"),
                            },
                        )
                    )
        collision_events = cast(tuple[dict[str, object], ...], info.get("collision_events", ()))
        for collision_event in collision_events:
            impact_position = collision_event.get("impact_position")
            participants_value = collision_event.get("participants", ())
            participants = (
                tuple(str(entity_id) for entity_id in participants_value)
                if isinstance(participants_value, (list, tuple))
                else ()
            )
            classification = str(collision_event.get("classification", "accidental_collision"))
            relative_speed_value = collision_event.get("relative_speed_mps", 0.0)
            relative_speed = (
                float(relative_speed_value)
                if isinstance(relative_speed_value, (int, float))
                else 0.0
            )
            events.append(
                VisualizationEvent(
                    event_type="collision_impact",
                    message=(
                        f"{classification.upper()}: {' <-> '.join(participants)} | "
                        f"relative {relative_speed:.1f} m/s"
                    ),
                    data={
                        **collision_event,
                        "position": impact_position,
                        "visible_to": ("referee",),
                    },
                )
            )
            intended_targets = collision_event.get("intended_targets", {})
            if isinstance(intended_targets, dict) and intended_targets:
                for aggressor_id, target_id_value in sorted(intended_targets.items()):
                    target_id = str(target_id_value)
                    announced_kills.update((str(aggressor_id), target_id))
                    events.append(
                        VisualizationEvent(
                            event_type="entity_killed",
                            entity_id=str(aggressor_id),
                            message=f"{aggressor_id} [RAMMING] destroyed {target_id}",
                            data={
                                "attacker_id": str(aggressor_id),
                                "weapon_id": "RAMMING",
                                "target_id": target_id,
                                "tick": env.world.tick,
                                "visible_to": ("referee",),
                            },
                        )
                    )
            elif len(participants) == 2:
                announced_kills.update(participants)
                events.append(
                    VisualizationEvent(
                        event_type="entity_killed",
                        message=(
                            f"{participants[0]} [ACCIDENTAL COLLISION] "
                            f"{participants[1]}; both destroyed"
                        ),
                        data={
                            "participants": participants,
                            "weapon_id": "ACCIDENTAL_COLLISION",
                            "tick": env.world.tick,
                            "visible_to": ("referee",),
                        },
                    )
                )
        public_events = cast(tuple[dict[str, object], ...], info["public_combat_events"])
        events.extend(
            VisualizationEvent(
                event_type=str(event.get("event_type", "combat")),
                entity_id=(
                    str(event["attacker_id"]) if event.get("attacker_id") is not None else None
                ),
                message=str(event.get("message", event.get("event_type", "combat"))),
                data=event,
            )
            for event in public_events
        )
        events.extend(
            VisualizationEvent(
                event_type=str(event.get("event_type", "scenario")),
                message=str(event.get("event_type", "scenario")),
                data=event,
            )
            for event in env.wave_events
            if event.get("tick") == env.world.tick
        )
        adjudication = env._ad2_adjudicator.result
        score = score_metric_state(metric_state)
        frame = frame_from_world(
            env.world,
            view="referee",
            actions=(
                {"side": "blue", "batch": blue},
                {"side": "red", "batch": red},
            ),
            events=tuple(events),
            scores=ScoreSets(
                blue=SideScore(total=max(0.0, 1.0 - score.total_score)),
                red=SideScore(total=score.total_score),
            ),
            geo_frame=env.geo_frame,
        ).model_copy(
            update={
                "mission": MissionPanel(
                    status=adjudication.outcome.value,
                    objective=adjudication.reason,
                    time_remaining=env.world.time_remaining,
                )
            }
        )
        axes.set_title(f"{scenario_id} live | tick {env.world.tick} | {adjudication.outcome.value}")
        dashboard.update(frame)
        figure.canvas.draw_idle()
        figure.canvas.flush_events()
        plt.pause(1.0 / speed)

    runners = {
        "MD-AD-002-EASY": run_md_ad_002_easy,
        "MD-AD-002-MEDIUM": run_md_ad_002_medium,
        "MD-AD-002-HARD": run_md_ad_002_hard,
    }
    result = runners[scenario_id](seed=seed, max_ticks=max_ticks, on_tick=update)
    plt.ioff()
    figure.canvas.draw_idle()
    if block_on_finish:
        plt.show(block=True)
    else:
        plt.close(figure)
    return result

"""Deterministic MD-AD-002 EASY rule-agent runner."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from openmdbench.core.entities import Lifecycle, PlatformAsset, Side
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import (
    ActionBatch,
    AD2EasyBlueAgent,
    AD2HardBlueAgent,
    AD2MediumBlueAgent,
    AD2RedBaselineAgent,
)
from openmdbench.replay.md_ad_002 import AD2AuthorityLog
from openmdbench.scoring.md_ad_002 import (
    EARLY_WARNING_BASELINES,
    AD2MetricState,
    AD2Score,
    score_metric_state,
)


@dataclass(frozen=True, slots=True)
class AD2MatchResult:
    seed: int
    ticks: int
    outcome: str
    reason: str
    breaches: int
    events: tuple[dict[str, object], ...]
    score: AD2Score


AD2TickCallback = Callable[
    [OpenMDBenchEnv, dict[str, Any], dict[str, Any], dict[str, Any], AD2MetricState], None
]


def _run_md_ad_002(
    *,
    scenario_id: str,
    seed: int = 73,
    max_ticks: int = 1_800,
    blue_hold: bool = False,
    disable_red_engage: bool = False,
    adjudication_time_limit_ticks: int | None = None,
    log_path: str | Path | None = None,
    checkpoint_dir: str | Path | None = None,
    checkpoint_every: int = 100,
    resume_checkpoint: str | Path | None = None,
    on_tick: AD2TickCallback | None = None,
) -> AD2MatchResult:
    if max_ticks <= 0:
        raise ValueError("max_ticks must be positive")
    env = OpenMDBenchEnv(scenario_id=scenario_id, seed=seed)
    env.reset(seed=seed)
    if env.world is None or env._ad2_adjudicator is None:
        raise RuntimeError("MD-AD-002 runner requires its formal world and adjudicator")
    if checkpoint_every <= 0:
        raise ValueError("checkpoint_every must be positive")
    if adjudication_time_limit_ticks is not None:
        if adjudication_time_limit_ticks <= 0:
            raise ValueError("adjudication_time_limit_ticks must be positive")
        env._ad2_adjudicator.time_limit_ticks = adjudication_time_limit_ticks
    protected = (float(env._protected_point[0]), float(env._protected_point[1]))
    red = AD2RedBaselineAgent(protected)
    blue = (
        AD2EasyBlueAgent((*protected, 100.0))
        if scenario_id == "MD-AD-002-EASY"
        else AD2MediumBlueAgent((*protected, 100.0))
        if scenario_id == "MD-AD-002-MEDIUM"
        else AD2HardBlueAgent((*protected, 100.0))
    )
    red_observation = env.red_observation()
    blue_observation = env.public_observation(Side.BLUE)
    red.reset(red_observation, seed)
    blue.reset(blue_observation, seed)
    initial_ammo = sum(
        sum(entity.components.weapon_inventory.values())
        for entity in env.world.entities_for_side(Side.RED)
        if isinstance(entity, PlatformAsset)
    )
    first_engagement: int | None = None
    usv_supported_contacts: set[str] = set()
    usv_detection_distance_m: float | None = None
    usv_online_platform_ticks = 0
    usv_available_platform_ticks = 0
    relay_required_ticks = 0
    relay_success_ticks = 0
    metric_state = AD2MetricState(
        scenario_id=env.scenario.scenario_id,
        destroyed_blue=0,
        breaches=0,
        initial_ammo=initial_ammo,
        remaining_ammo=initial_ammo,
        first_engagement_tick=None,
        usv_detection_distance_m=None,
        usv_online_platform_ticks=0,
        usv_available_platform_ticks=0,
        safety_violations=0,
    )
    if resume_checkpoint is not None:
        checkpoint = json.loads(Path(resume_checkpoint).read_text(encoding="utf-8"))
        runner_state = checkpoint.get("runner")
        if not isinstance(runner_state, dict) or not isinstance(
            runner_state.get("metric_state"), dict
        ):
            raise ValueError("checkpoint is missing MD-AD-002 runner metric state")
        expected_runner_identity = {
            "scenario_id": scenario_id,
            "seed": seed,
            "blue_hold": blue_hold,
            "disable_red_engage": disable_red_engage,
            "adjudication_time_limit_ticks": adjudication_time_limit_ticks,
        }
        if any(runner_state.get(key) != value for key, value in expected_runner_identity.items()):
            raise ValueError("checkpoint runner identity or options mismatch")
        env.import_state(checkpoint["simulation"])
        red.restore(checkpoint["red_agent"])
        blue.restore(checkpoint["blue_agent"])
        metric_state = AD2MetricState.from_payload(runner_state["metric_state"])
        if metric_state.scenario_id != scenario_id:
            raise ValueError("checkpoint runner scenario mismatch")
        initial_ammo = metric_state.initial_ammo
        first_engagement = metric_state.first_engagement_tick
        usv_detection_distance_m = metric_state.usv_detection_distance_m
        usv_online_platform_ticks = metric_state.usv_online_platform_ticks
        usv_available_platform_ticks = metric_state.usv_available_platform_ticks
        relay_required_ticks = metric_state.relay_required_ticks
        relay_success_ticks = metric_state.relay_success_ticks
        usv_supported_contacts = {
            str(contact_id) for contact_id in runner_state.get("usv_supported_contacts", [])
        }
        red_observation = env.red_observation()
        blue_observation = env.public_observation(Side.BLUE)
        if max_ticks < env.world.tick:
            raise ValueError("max_ticks cannot precede the checkpoint tick")
    baseline_version, baseline_distance_m = EARLY_WARNING_BASELINES[env.scenario.scenario_id]
    logger = (
        AD2AuthorityLog(
            log_path,
            {
                "scenario_id": env.scenario.scenario_id,
                "seed": seed,
                "config_hash": env.scenario_hash,
                "map_identity": env.map_metadata,
                "early_warning_baseline_version": baseline_version,
                "early_warning_baseline_distance_m": baseline_distance_m,
            },
        )
        if log_path is not None
        else None
    )
    try:
        for _ in range(max(0, max_ticks - env.world.tick)):
            red_batch = red.act(red_observation)
            if disable_red_engage:
                red_batch = red_batch.model_copy(
                    update={
                        "actions": tuple(
                            action.model_copy(update={"engagement": None})
                            for action in red_batch.actions
                        )
                    }
                )
            blue_batch = blue.act(blue_observation)
            if blue_hold:
                blue_batch = blue_batch.model_copy(
                    update={
                        "actions": tuple(
                            action.model_copy(
                                update={
                                    "navigation": "hold_position",
                                    "target": None,
                                    "speed_mps": 0.0,
                                }
                            )
                            for action in blue_batch.actions
                        )
                    }
                )
            if scenario_id == "MD-AD-002-HARD" and not blue_hold:
                _red, _reward, terminal, _truncated, info = env.step_red_action_batch(red_batch)
                blue_observation = env.public_observation(Side.BLUE)
                blue_batch = ActionBatch.model_validate(info["blue_action"])
            else:
                internal_red = env._validate_red_batch(red_batch)
                blue_observation, _legacy_red, terminal, info = env.step_bilateral(
                    blue_batch, internal_red
                )
            red_observation = env.red_observation()
            if first_engagement is None and any(
                event.get("event_type") == "engagement"
                for event in cast(tuple[dict[str, object], ...], info["public_combat_events"])
            ):
                first_engagement = env.world.tick
            for contact in red_observation.contacts:
                if contact.contact_id in usv_supported_contacts or not any(
                    source.startswith("red-picket-usv-") for source in contact.sources
                ):
                    continue
                usv_supported_contacts.add(contact.contact_id)
                distance = math.dist(contact.position_m[:2], protected)
                usv_detection_distance_m = max(usv_detection_distance_m or 0.0, distance)
            usvs = tuple(
                entity
                for entity in env.world.entities_for_side(Side.RED)
                if isinstance(entity, PlatformAsset) and entity.id.startswith("red-picket-usv-")
            )
            usv_available_platform_ticks += len(usvs)
            usv_online_platform_ticks += sum(
                entity.lifecycle in {Lifecycle.ACTIVE, Lifecycle.DEGRADED}
                and entity.components.sensor_mode != "off"
                and entity.components.communication_status in {"connected", "relayed"}
                for entity in usvs
            )
            if scenario_id == "MD-AD-002-HARD" and env._ad2_blocked_links(env.world.tick):
                relay_required_ticks += 1
                relay_success_ticks += int(
                    any(
                        entity.components.communication_status == "relayed"
                        for entity in env.world.entities_for_side(Side.RED)
                        if isinstance(entity, PlatformAsset) and entity.platform_type == "uav"
                    )
                )
            blue_entities_now = tuple(
                entity
                for entity in env.world.entities_for_side(Side.BLUE)
                if isinstance(entity, PlatformAsset)
            )
            remaining_ammo_now = sum(
                sum(entity.components.weapon_inventory.values())
                for entity in env.world.entities_for_side(Side.RED)
                if isinstance(entity, PlatformAsset)
            )
            metric_state = AD2MetricState(
                scenario_id=env.scenario.scenario_id,
                destroyed_blue=sum(
                    entity.lifecycle is Lifecycle.DESTROYED for entity in blue_entities_now
                ),
                breaches=len(env._ad2_adjudicator.breached_ids),
                initial_ammo=initial_ammo,
                remaining_ammo=remaining_ammo_now,
                first_engagement_tick=first_engagement,
                usv_detection_distance_m=usv_detection_distance_m,
                usv_online_platform_ticks=usv_online_platform_ticks,
                usv_available_platform_ticks=usv_available_platform_ticks,
                safety_violations=(env._ad2_combat.safety_violations if env._ad2_combat else 0),
                relay_required_ticks=relay_required_ticks,
                relay_success_ticks=relay_success_ticks,
            )
            if logger is not None:
                logger.append(
                    "tick",
                    {
                        "timestamp": env.world.tick,
                        "red_observation": red_observation.model_dump(mode="json"),
                        "red_action": red_batch.model_dump(mode="json"),
                        "blue_action": blue_batch.model_dump(mode="json"),
                        "public_combat_events": info["public_combat_events"],
                        "scenario_events": tuple(
                            event
                            for event in env.wave_events
                            if event.get("tick") == env.world.tick
                        ),
                        "world": env.authority_world_snapshot(),
                        "metric_state": metric_state.as_payload(),
                    },
                )
            if checkpoint_dir is not None and env.world.tick % checkpoint_every == 0:
                checkpoint_path = Path(checkpoint_dir) / f"tick-{env.world.tick:04d}.json"
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(
                    json.dumps(
                        {
                            "simulation": env.export_state(),
                            "red_agent": red.snapshot(),
                            "blue_agent": blue.snapshot(),
                            "runner": {
                                "scenario_id": scenario_id,
                                "seed": seed,
                                "blue_hold": blue_hold,
                                "disable_red_engage": disable_red_engage,
                                "adjudication_time_limit_ticks": (adjudication_time_limit_ticks),
                                "metric_state": metric_state.as_payload(),
                                "usv_supported_contacts": sorted(usv_supported_contacts),
                            },
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
            if on_tick is not None:
                on_tick(
                    env,
                    blue_batch.model_dump(mode="json"),
                    red_batch.model_dump(mode="json"),
                    cast(dict[str, Any], info),
                    metric_state,
                )
            if terminal:
                break
    finally:
        if logger is not None:
            logger.close()
    adjudication = env._ad2_adjudicator.result
    score = score_metric_state(metric_state)
    return AD2MatchResult(
        seed,
        env.world.tick,
        adjudication.outcome.value,
        adjudication.reason,
        adjudication.breach_count,
        tuple(env.wave_events),
        score,
    )


def run_md_ad_002_easy(
    *,
    seed: int = 73,
    max_ticks: int = 1_800,
    blue_hold: bool = False,
    disable_red_engage: bool = False,
    adjudication_time_limit_ticks: int | None = None,
    log_path: str | Path | None = None,
    checkpoint_dir: str | Path | None = None,
    checkpoint_every: int = 100,
    resume_checkpoint: str | Path | None = None,
    on_tick: AD2TickCallback | None = None,
) -> AD2MatchResult:
    return _run_md_ad_002(
        scenario_id="MD-AD-002-EASY",
        seed=seed,
        max_ticks=max_ticks,
        blue_hold=blue_hold,
        disable_red_engage=disable_red_engage,
        adjudication_time_limit_ticks=adjudication_time_limit_ticks,
        log_path=log_path,
        checkpoint_dir=checkpoint_dir,
        checkpoint_every=checkpoint_every,
        resume_checkpoint=resume_checkpoint,
        on_tick=on_tick,
    )


def run_md_ad_002_medium(
    *,
    seed: int = 73,
    max_ticks: int = 1_800,
    blue_hold: bool = False,
    disable_red_engage: bool = False,
    adjudication_time_limit_ticks: int | None = None,
    log_path: str | Path | None = None,
    checkpoint_dir: str | Path | None = None,
    checkpoint_every: int = 100,
    resume_checkpoint: str | Path | None = None,
    on_tick: AD2TickCallback | None = None,
) -> AD2MatchResult:
    return _run_md_ad_002(
        scenario_id="MD-AD-002-MEDIUM",
        seed=seed,
        max_ticks=max_ticks,
        blue_hold=blue_hold,
        disable_red_engage=disable_red_engage,
        adjudication_time_limit_ticks=adjudication_time_limit_ticks,
        log_path=log_path,
        checkpoint_dir=checkpoint_dir,
        checkpoint_every=checkpoint_every,
        resume_checkpoint=resume_checkpoint,
        on_tick=on_tick,
    )


def run_md_ad_002_hard(
    *,
    seed: int = 73,
    max_ticks: int = 1_800,
    blue_hold: bool = False,
    disable_red_engage: bool = False,
    adjudication_time_limit_ticks: int | None = None,
    log_path: str | Path | None = None,
    checkpoint_dir: str | Path | None = None,
    checkpoint_every: int = 100,
    resume_checkpoint: str | Path | None = None,
    on_tick: AD2TickCallback | None = None,
) -> AD2MatchResult:
    return _run_md_ad_002(
        scenario_id="MD-AD-002-HARD",
        seed=seed,
        max_ticks=max_ticks,
        blue_hold=blue_hold,
        disable_red_engage=disable_red_engage,
        adjudication_time_limit_ticks=adjudication_time_limit_ticks,
        log_path=log_path,
        checkpoint_dir=checkpoint_dir,
        checkpoint_every=checkpoint_every,
        resume_checkpoint=resume_checkpoint,
        on_tick=on_tick,
    )

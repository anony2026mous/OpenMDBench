"""Live and replay presentation for formal V2 sessions using one rich-frame contract."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openmdbench.policies.rule_v2 import FormalRuleAgentTeamV2
from openmdbench.replay.v2 import (
    ReplayHeaderV2,
    ReplayRecordV2,
    ReplayWriterV2,
)
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.visualization.formal_v2 import ViewV2, build_formal_frame_v2
from openmdbench.visualization.renderer_v2 import (
    LivePresentationStatusV2,
    MatplotlibRendererV2,
    interpolate_frame_v2,
)

ActionProviderV2 = Callable[[SessionLifecycleV2], None]


@dataclass(frozen=True, slots=True)
class _LivePacingSnapshotV2:
    """Configured pacing and display measurements for one authority frame."""

    target_speed: float
    rendered_fps: float
    render_fps_cap: float
    skipped_ticks: int


@dataclass(slots=True)
class _LivePacerV2:
    """Schedule fixed simulation ticks independently from GUI presentation.

    Simulation time remains authoritative.  This class only decides when the
    event loop may paint the latest immutable frame, allowing overdue ticks to
    catch up before an expensive Matplotlib update is attempted.
    """

    target_speed: float
    render_fps_cap: float
    started_wall_time_s: float
    initial_sim_time_s: float
    next_render_wall_time_s: float = field(init=False)
    last_rendered_tick: int | None = field(default=None, init=False)
    rendered_frames: int = field(default=0, init=False)
    skipped_ticks: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.target_speed <= 0.0 or math.isnan(self.target_speed):
            raise ValueError("visualization speed must be positive")
        if self.render_fps_cap <= 0.0 or not math.isfinite(self.render_fps_cap):
            raise ValueError("render_fps must be a finite positive value")
        self.next_render_wall_time_s = self.started_wall_time_s

    def next_tick_deadline(self, *, current_sim_time_s: float, tick_seconds: float) -> float:
        """Return the wall-clock deadline for the next fixed physics tick."""

        if tick_seconds <= 0.0 or not math.isfinite(tick_seconds):
            raise ValueError("tick_seconds must be a finite positive value")
        return (
            self.started_wall_time_s
            + (current_sim_time_s - self.initial_sim_time_s + tick_seconds) / self.target_speed
        )

    def render_due(self, *, wall_time_s: float) -> bool:
        return wall_time_s >= self.next_render_wall_time_s

    def record_render(
        self, *, tick: int, sim_time_s: float, wall_time_s: float
    ) -> _LivePacingSnapshotV2:
        """Record one local paint without changing the authority frame."""

        if (
            tick < 0
            or sim_time_s < self.initial_sim_time_s
            or self.last_rendered_tick is not None
            and tick < self.last_rendered_tick
        ):
            raise ValueError("rendered tick and simulation time must be monotonic")
        if self.last_rendered_tick is None:
            self.skipped_ticks += max(0, tick - 1)
        else:
            self.skipped_ticks += max(0, tick - self.last_rendered_tick - 1)
        self.last_rendered_tick = tick
        self.rendered_frames += 1
        elapsed_wall_time_s = max(0.0, wall_time_s - self.started_wall_time_s)
        rendered_fps = (
            0.0 if elapsed_wall_time_s <= 0.0 else self.rendered_frames / elapsed_wall_time_s
        )
        self.next_render_wall_time_s = wall_time_s + 1.0 / self.render_fps_cap
        return _LivePacingSnapshotV2(
            target_speed=self.target_speed,
            rendered_fps=rendered_fps,
            render_fps_cap=self.render_fps_cap,
            skipped_ticks=self.skipped_ticks,
        )

    def complete_render(self, *, wall_time_s: float) -> None:
        """Start the next display interval after an expensive paint completes."""

        if wall_time_s < self.started_wall_time_s:
            raise ValueError("render completion time cannot precede live start")
        self.next_render_wall_time_s = wall_time_s + 1.0 / self.render_fps_cap


def _presentation_status(snapshot: _LivePacingSnapshotV2) -> LivePresentationStatusV2:
    """Translate local pacing data into renderer-only display metadata."""

    return LivePresentationStatusV2(
        target_speed=snapshot.target_speed,
        rendered_fps=snapshot.rendered_fps,
        render_fps_cap=snapshot.render_fps_cap,
        skipped_ticks=snapshot.skipped_ticks,
    )


def _submit_declared_motion(
    session: SessionLifecycleV2, *, submitted_entity_ids: set[str], valid_until_tick: int
) -> None:
    """Install a generic demo command preserving each entity's declared initial motion."""

    grants_by_entity = {
        grant.entity_id: token for token, grant in session.world_view.authority_tokens.items()
    }
    tick = session.world_view.tick
    for entity in session.world_view.entities_stable():
        if entity.id in submitted_entity_ids or entity.id not in grants_by_entity:
            continue
        initial = entity.definition.runtime_initial.initial_state
        velocity = tuple(float(value) for value in initial.velocity_mps)
        speed = math.hypot(velocity[0], velocity[1])
        if speed <= 1e-6:
            submitted_entity_ids.add(entity.id)
            continue
        command = PersistentCommandV2(
            schema_version="2.0",
            command_id=f"live.declared-motion.{entity.id}",
            command_type="navigation",
            entity_id=entity.id,
            faction_id=entity.faction_id,
            based_on_tick=tick,
            valid_until_tick=valid_until_tick,
            payload={
                "speed_mps": speed,
                "heading_deg": float(initial.heading_deg),
                "altitude_m": float(initial.position_m[2]),
            },
        )
        batch = ActionBatchV2(
            schema_version="2.0",
            session_id=session.session_id,
            batch_id=f"live.batch.{entity.id}",
            idempotency_key=f"live.idem.{entity.id}",
            faction_id=entity.faction_id,
            based_on_tick=tick,
            valid_until_tick=valid_until_tick,
            persistent_commands=(command,),
        )
        session.submit_actions(
            batch=batch,
            authority_token=grants_by_entity[entity.id],
            operation_id=f"live.submit.{entity.id}",
            expected_tick=tick,
        )
        submitted_entity_ids.add(entity.id)


def _record(
    frame: Any,
    *,
    authority_receipt_hash: str,
    event_hashes: tuple[str, ...],
) -> ReplayRecordV2:
    payload = {
        "schema_version": "replay-record@2.0",
        "tick": frame.tick,
        "frame": frame.model_dump(mode="json"),
        "authority_receipt_hash": authority_receipt_hash,
        "event_receipt_hashes": event_hashes,
    }
    return ReplayRecordV2(
        tick=frame.tick,
        frame=frame,
        authority_receipt_hash=authority_receipt_hash,
        event_receipt_hashes=event_hashes,
        record_hash=ReplayRecordV2.compute_hash(payload),
    )


def run_live_formal_v2(
    public_id: str,
    *,
    seed: int = 73,
    speed: float = 20.0,
    render_fps: float = 12.0,
    max_ticks: int | None = None,
    replay_path: Path | None = None,
    action_provider: ActionProviderV2 | None = None,
    maintain_declared_motion: bool = True,
    view: ViewV2 = "referee",
    faction_id: str | None = None,
    block_on_finish: bool = True,
    use_rule_agents: bool = True,
) -> Path | None:
    """Run a formal V2 session with fixed ticks and independently paced display.

    ``speed`` is the target simulation-seconds per wall-clock second.  It never
    changes the physics time step.  ``render_fps`` caps GUI refreshes only: a
    delayed renderer displays the latest frame after all overdue ticks are
    advanced, while every tick still executes normally. Optional replay output
    collects every authority frame in memory and writes one artifact only after
    the match ends.
    """

    if speed <= 0.0 or math.isnan(speed):
        raise ValueError("visualization speed must be positive")
    if render_fps <= 0.0 or not math.isfinite(render_fps):
        raise ValueError("render_fps must be a finite positive value")
    import matplotlib

    if block_on_finish and "agg" in matplotlib.get_backend().lower():
        try:
            matplotlib.use("TkAgg", force=True)
        except ImportError as exc:
            raise RuntimeError(
                "interactive visualization requires a GUI Matplotlib backend (TkAgg)"
            ) from exc
    import matplotlib.pyplot as plt

    resolved, catalog = compile_formal_scenario_v2(public_id)
    limit = int(resolved.world.duration_ticks or 0) if max_ticks is None else max_ticks
    if limit < 1:
        raise ValueError("visualization tick limit must be positive")
    session = create_formal_session_v2(public_id, session_id=f"live.{public_id.lower()}", seed=seed)
    rule_team = (
        FormalRuleAgentTeamV2.for_scenario(public_id, seed=seed)
        if action_provider is None and use_rule_agents
        else None
    )
    session.load().start()
    figure, axes = plt.subplots(figsize=(16, 9))
    figure.subplots_adjust(right=0.76)
    if block_on_finish:
        plt.show(block=False)
    renderer = MatplotlibRendererV2(figure, axes)
    writer: ReplayWriterV2 | None = None
    submitted_entity_ids: set[str] = set()
    if replay_path is not None:
        replay_path.parent.mkdir(parents=True, exist_ok=True)
        writer = ReplayWriterV2(
            replay_path,
            header=ReplayHeaderV2(
                session_id=session.session_id,
                resolved_hash=resolved.resolved_hash,
                catalog_hash=resolved.catalog_hash,
                model_registry_hash=resolved.model_registry_hash,
                seed=seed,
            ),
        )

    def advance_authority_tick() -> tuple[VisualizationFrameV2 | None, bool]:
        """Advance exactly one tick and optionally record its authority frame."""

        if rule_team is not None:
            rule_team(session)
        elif action_provider is not None:
            action_provider(session)
        elif maintain_declared_motion:
            _submit_declared_motion(
                session,
                submitted_entity_ids=submitted_entity_ids,
                valid_until_tick=limit,
            )
        tick = session.world_view.tick
        receipt = session.step(operation_id=f"live.tick.{tick}", expected_tick=tick)
        terminal = any(
            item.terminal_result is not None for item in receipt.world_receipt.mission_receipts
        )
        if writer is None:
            return None, terminal
        frame = build_formal_frame_v2(
            session,
            catalog,
            view=view,
            faction_id=faction_id,
        )
        event_hashes = tuple(
            item.payload_hash
            for event_receipt in receipt.world_receipt.event_receipts
            for item in event_receipt.typed_event_receipts
        )
        writer.write(
            _record(
                frame,
                authority_receipt_hash=receipt.receipt_hash,
                event_hashes=event_hashes,
            )
        )
        return frame, terminal

    try:
        if not block_on_finish:
            while session.world_view.tick < limit and plt.fignum_exists(figure.number):
                frame, terminal = advance_authority_tick()
                if frame is None:
                    frame = build_formal_frame_v2(
                        session,
                        catalog,
                        view=view,
                        faction_id=faction_id,
                    )
                renderer.update(frame)
                figure.canvas.draw()
                if terminal:
                    break
        elif speed <= 0.5:
            # Preserve slow-motion interpolation.  Decoupled frame sampling is
            # aimed at accelerated playback, where painting every authority
            # tick is the bottleneck.
            tick_seconds = float(resolved.world.tick_seconds or 1.0)
            initial_sim_time_s = float(session.world_view.tick) * tick_seconds
            pacer = _LivePacerV2(
                target_speed=speed,
                render_fps_cap=render_fps,
                started_wall_time_s=time.monotonic(),
                initial_sim_time_s=initial_sim_time_s,
            )
            previous_frame: VisualizationFrameV2 | None = None
            while session.world_view.tick < limit and plt.fignum_exists(figure.number):
                wall_tick_started = time.monotonic()
                frame, terminal = advance_authority_tick()
                if frame is None:
                    frame = build_formal_frame_v2(
                        session,
                        catalog,
                        view=view,
                        faction_id=faction_id,
                    )
                subframes = 2 if previous_frame is not None else 1
                for index in range(1, subframes + 1):
                    presentation = (
                        frame
                        if previous_frame is None
                        else interpolate_frame_v2(previous_frame, frame, index / subframes)
                    )
                    status = _presentation_status(
                        pacer.record_render(
                            tick=frame.tick,
                            sim_time_s=presentation.sim_time_s,
                            wall_time_s=time.monotonic(),
                        )
                    )
                    renderer.update(presentation, presentation_status=status)
                    figure.canvas.flush_events()
                    pacer.complete_render(wall_time_s=time.monotonic())
                    remaining = max(
                        0.001,
                        tick_seconds / speed - (time.monotonic() - wall_tick_started),
                    )
                    figure.canvas.start_event_loop(remaining / (subframes - index + 1))
                previous_frame = frame
                if terminal:
                    break
        else:
            tick_seconds = float(resolved.world.tick_seconds or 1.0)
            initial_sim_time_s = float(session.world_view.tick) * tick_seconds
            pacer = _LivePacerV2(
                target_speed=speed,
                render_fps_cap=render_fps,
                started_wall_time_s=time.monotonic(),
                initial_sim_time_s=initial_sim_time_s,
            )
            latest_frame: VisualizationFrameV2 | None = None
            terminal = False
            while plt.fignum_exists(figure.number):
                wall_time_s = time.monotonic()
                finished = terminal or session.world_view.tick >= limit
                has_new_frame = (
                    session.world_view.tick > 0
                    and session.world_view.tick != pacer.last_rendered_tick
                )
                if has_new_frame and (finished or pacer.render_due(wall_time_s=wall_time_s)):
                    if latest_frame is None or latest_frame.tick != session.world_view.tick:
                        latest_frame = build_formal_frame_v2(
                            session,
                            catalog,
                            view=view,
                            faction_id=faction_id,
                        )
                    status = _presentation_status(
                        pacer.record_render(
                            tick=latest_frame.tick,
                            sim_time_s=latest_frame.sim_time_s,
                            wall_time_s=wall_time_s,
                        )
                    )
                    renderer.update(latest_frame, presentation_status=status)
                    figure.canvas.flush_events()
                    pacer.complete_render(wall_time_s=time.monotonic())
                    if finished:
                        break
                    continue
                if not finished:
                    current_sim_time_s = (
                        initial_sim_time_s + float(session.world_view.tick) * tick_seconds
                    )
                    if wall_time_s >= pacer.next_tick_deadline(
                        current_sim_time_s=current_sim_time_s,
                        tick_seconds=tick_seconds,
                    ):
                        latest_frame, terminal = advance_authority_tick()
                        # A non-recording live session intentionally skips
                        # frame construction until the next paint.
                        continue
                if finished:
                    break
                current_sim_time_s = (
                    initial_sim_time_s + float(session.world_view.tick) * tick_seconds
                )
                next_tick_wall_time_s = pacer.next_tick_deadline(
                    current_sim_time_s=current_sim_time_s,
                    tick_seconds=tick_seconds,
                )
                next_wake_time_s = (
                    min(next_tick_wall_time_s, pacer.next_render_wall_time_s)
                    if has_new_frame
                    else next_tick_wall_time_s
                )
                figure.canvas.start_event_loop(max(0.001, next_wake_time_s - time.monotonic()))
        if block_on_finish and plt.fignum_exists(figure.number):
            plt.show(block=True)
    finally:
        if writer is not None:
            writer.close()
        renderer.close()
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()
        if not block_on_finish and plt.fignum_exists(figure.number):
            plt.close(figure)
    return replay_path


__all__ = ["ActionProviderV2", "run_live_formal_v2"]

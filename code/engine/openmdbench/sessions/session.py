"""RF-04 session authority: lifecycle, snapshots and one serialized writer."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from threading import Event, RLock, Thread, current_thread
from time import monotonic, sleep
from typing import Any, Protocol, cast

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from openmdbench.core.rng import SessionRNG
from openmdbench.core.session_runtime import SessionRuntime
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.scenarios.resolved import ResolvedScenario
from openmdbench.schemas.platform import ActionBatch, ActionReceipt, CommandResult
from openmdbench.sessions.commands import CommandQueue, TickActions
from openmdbench.visualization.frame_bus import LiveFrameBus, LiveFrameSource
from openmdbench.visualization.live import VisualizationView
from openmdbench.visualization.schema import VisualizationFrame


class SessionState(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATING = "terminating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class SessionTransitionError(RuntimeError):
    code = "session.invalid_transition"

    def __init__(self, operation: str, state: SessionState) -> None:
        self.operation = operation
        self.state = state
        super().__init__(f"{self.code}: cannot {operation} while session is {state.value}")


class ObservationSnapshot(BaseModel):
    """Atomically published, immutable observation frame."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    scenario_id: str
    scenario_hash: str
    tick: int = Field(ge=0)
    state: SessionState
    state_version: int = Field(ge=0)
    observation_json: str
    reward: float = 0.0
    total_reward: float = 0.0
    terminated: bool = False
    truncated: bool = False

    @property
    def observation(self) -> dict[str, Any]:
        value = json.loads(self.observation_json)
        if not isinstance(value, dict):
            raise RuntimeError("snapshot observation is not an object")
        return value


@dataclass(frozen=True, slots=True)
class SessionResult:
    state: SessionState
    tick: int
    total_reward: float
    reason: str


class SimulationKernel(Protocol):
    def reset(self, *, seed: int | None = None) -> tuple[Mapping[str, Any], Mapping[str, Any]]: ...

    def step(
        self, action: object
    ) -> tuple[Mapping[str, Any], float, bool, bool, Mapping[str, Any]]: ...

    def close(self) -> None: ...


KernelFactory = Callable[[ResolvedScenario, int], SimulationKernel]
CommandApplier = Callable[[SimulationKernel, TickActions, object], object]


def _default_kernel(resolved: ResolvedScenario, seed: int) -> SimulationKernel:
    return cast(SimulationKernel, SessionRuntime(resolved, seed))


class SimulationSession:
    """Own one simulation kernel; all mutation is serialized through ``step``.

    The kernel and its mutable ``WorldState`` are deliberately private. Readers
    receive only immutable snapshots published while holding the writer lock.
    Native MMG/Taichi state remains session-local in this in-process RF-04
    implementation; process isolation is the deployment boundary for kernels
    later found to retain process-global native state.
    """

    def __init__(
        self,
        session_id: str,
        resolved: ResolvedScenario,
        *,
        seed: int,
        kernel_factory: KernelFactory | None = None,
        command_applier: CommandApplier | None = None,
    ) -> None:
        if not session_id:
            raise ValueError("session_id cannot be empty")
        if seed < 0:
            raise ValueError("seed must be non-negative")
        if resolved.resolved_hash != resolved.expected_hash():
            raise ValueError("resolved scenario hash does not match its content")
        self.session_id = session_id
        self.resolved = resolved
        self.seed = seed
        self.rng = SessionRNG(seed)
        self._command_queue = CommandQueue(
            session_id,
            entity_sides={item.entity_id: item.side for item in resolved.deployments},
        )
        self._kernel_factory = kernel_factory or _default_kernel
        self._command_applier = command_applier
        self._kernel: SimulationKernel | None = None
        self._state = SessionState.CREATED
        self._state_version = 0
        self._tick = 0
        self._total_reward = 0.0
        self._snapshot: ObservationSnapshot | None = None
        self._commands: list[object] = []
        self._events: list[dict[str, Any]] = []
        self._logs: list[dict[str, Any]] = []
        self._checkpoints: list[dict[str, Any]] = []
        self._result: SessionResult | None = None
        self._lock = RLock()
        self._stop = Event()
        self._runner: Thread | None = None
        self._last_kernel_action: object = (0.0, 0.0)
        self._frame_buses = {view: LiveFrameBus() for view in ("referee", "blue", "red", "public")}

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    @property
    def state_version(self) -> int:
        with self._lock:
            return self._state_version

    @property
    def result(self) -> SessionResult | None:
        with self._lock:
            return self._result

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(json.loads(json.dumps(item)) for item in self._events)

    def _transition(self, target: SessionState) -> None:
        if self._state is target:
            return
        self._state = target
        self._state_version += 1
        self._events.append({"state": target.value, "version": self._state_version})

    def initialize(self) -> SimulationSession:
        with self._lock:
            if self._state is SessionState.INITIALIZED:
                return self
            if self._state is not SessionState.CREATED:
                raise SessionTransitionError("initialize", self._state)
            kernel = self._kernel_factory(self.resolved, self.seed)
            try:
                observation, _ = kernel.reset(seed=self.seed)
            except Exception:
                kernel.close()
                self._transition(SessionState.FAILED)
                raise
            self._kernel = kernel
            self._transition(SessionState.INITIALIZED)
            self._publish(observation)
            self._publish_visualization()
            return self

    def start(self) -> SimulationSession:
        with self._lock:
            if self._state is SessionState.RUNNING:
                return self
            if self._state is not SessionState.INITIALIZED:
                raise SessionTransitionError("start", self._state)
            self._transition(SessionState.RUNNING)
            self._republish_state()
            return self

    def pause(self) -> SimulationSession:
        with self._lock:
            if self._state is SessionState.PAUSED:
                return self
            if self._state is not SessionState.RUNNING:
                raise SessionTransitionError("pause", self._state)
            self._transition(SessionState.PAUSED)
            self._republish_state()
            return self

    def resume(self) -> SimulationSession:
        with self._lock:
            if self._state is SessionState.RUNNING:
                return self
            if self._state is not SessionState.PAUSED:
                raise SessionTransitionError("resume", self._state)
            self._transition(SessionState.RUNNING)
            self._republish_state()
            return self

    def submit_actions(self, batch: ActionBatch, *, actor_side: str) -> ActionReceipt:
        with self._lock:
            if self._state not in {
                SessionState.INITIALIZED,
                SessionState.RUNNING,
                SessionState.PAUSED,
            }:
                raise SessionTransitionError("submit actions", self._state)
            return self._command_queue.submit(batch, self._tick, actor_side=actor_side)

    def command_result(self, command_id: str) -> CommandResult:
        with self._lock:
            return self._command_queue.result(command_id)

    def step(self, action: object | None = None) -> ObservationSnapshot:
        with self._lock:
            if self._state is not SessionState.RUNNING:
                raise SessionTransitionError("step", self._state)
            if self._kernel is None:
                raise RuntimeError("initialized session has no kernel")
            self._commands.append(action)
            try:
                tick_actions = self._command_queue.apply_tick(self._tick + 1)
                selected_action = self._resolve_kernel_action(action, tick_actions)
                if self._command_applier is not None:
                    selected_action = self._command_applier(
                        self._kernel, tick_actions, selected_action
                    )
                kernel_action = (
                    np.asarray(selected_action, dtype=np.float32)
                    if isinstance(self._kernel, (OpenMDBenchEnv, SessionRuntime))
                    else selected_action
                )
                observation, reward, terminated, truncated, info = self._kernel.step(kernel_action)
            except Exception:
                self._transition(SessionState.FAILED)
                self._result = SessionResult(self._state, self._tick, self._total_reward, "error")
                self._close_kernel()
                self._republish_state()
                raise
            self._tick += 1
            self._total_reward += float(reward)
            self._logs.append({"tick": self._tick, "info": dict(info)})
            if terminated or truncated:
                self._transition(SessionState.COMPLETED)
                reason = "terminated" if terminated else "truncated"
                self._result = SessionResult(self._state, self._tick, self._total_reward, reason)
            snapshot = self._publish(
                observation,
                reward=float(reward),
                terminated=bool(terminated),
                truncated=bool(truncated),
            )
            self._publish_visualization()
            return snapshot

    def visualization_snapshot(self, view: VisualizationView) -> VisualizationFrame:
        with self._lock:
            return self._frame_buses[view].latest()

    def frame_source(self, view: VisualizationView) -> LiveFrameSource:
        """Return a read-only live source; publishers remain session-private."""
        return LiveFrameSource(self._frame_buses[view])

    def _publish_visualization(self) -> None:
        kernel = self._kernel
        if kernel is None or not hasattr(kernel, "visualization_frame"):
            return
        for view, bus in self._frame_buses.items():
            frame = kernel.visualization_frame(view)
            bus.publish(frame)

    def _resolve_kernel_action(self, explicit: object | None, tick_actions: TickActions) -> object:
        if explicit is not None:
            self._last_kernel_action = explicit
            return explicit
        navigation = next(
            (
                item
                for item in tick_actions.persistent_commands
                if item.command_type in {"navigation", "patrol", "hold"}
            ),
            None,
        )
        if navigation is not None:
            if navigation.command_type == "hold":
                self._last_kernel_action = (0.0, 0.0)
            else:
                self._last_kernel_action = (
                    float(navigation.payload.get("speed_mps", 0.0)),
                    float(navigation.payload.get("heading_deg", 0.0)),
                )
        return self._last_kernel_action

    def snapshot(self) -> ObservationSnapshot:
        with self._lock:
            if self._snapshot is None:
                raise SessionTransitionError("snapshot", self._state)
            return self._snapshot

    def start_continuous(
        self,
        action_provider: Callable[[ObservationSnapshot], object],
        *,
        speed_ratio: float = 1.0,
    ) -> SimulationSession:
        if speed_ratio <= 0.0:
            raise ValueError("speed_ratio must be positive")
        with self._lock:
            self.start()
            if self._runner is not None and self._runner.is_alive():
                return self
            self._stop.clear()

            def run() -> None:
                interval = float(self.resolved.clock.tick_seconds or 1.0) / speed_ratio
                while not self._stop.is_set():
                    started = monotonic()
                    with self._lock:
                        state = self._state
                    if state is SessionState.PAUSED:
                        sleep(min(interval, 0.01))
                        continue
                    if state is not SessionState.RUNNING:
                        return
                    try:
                        self.step(action_provider(self.snapshot()))
                    except Exception:
                        return
                    self._stop.wait(max(0.0, interval - (monotonic() - started)))

            self._runner = Thread(target=run, name=f"simulation-{self.session_id}", daemon=True)
            self._runner.start()
            return self

    def cancel(self) -> SimulationSession:
        with self._lock:
            if self._state is SessionState.CANCELLED:
                return self
            if self._state in {SessionState.CLOSED, SessionState.COMPLETED, SessionState.FAILED}:
                raise SessionTransitionError("cancel", self._state)
            self._transition(SessionState.CANCELLED)
            self._result = SessionResult(self._state, self._tick, self._total_reward, "cancelled")
            self._stop.set()
            self._close_kernel()
            for bus in self._frame_buses.values():
                bus.close()
            self._republish_state()
            return self

    def expire(self) -> SimulationSession:
        with self._lock:
            if self._state is SessionState.EXPIRED:
                return self
            if self._state in {SessionState.CLOSED, SessionState.COMPLETED, SessionState.FAILED}:
                raise SessionTransitionError("expire", self._state)
            self._transition(SessionState.EXPIRED)
            self._result = SessionResult(self._state, self._tick, self._total_reward, "expired")
            self._stop.set()
            self._close_kernel()
            self._republish_state()
            return self

    def close(self) -> SimulationSession:
        runner: Thread | None
        with self._lock:
            if self._state is SessionState.CLOSED:
                return self
            self._transition(SessionState.TERMINATING)
            self._stop.set()
            runner = self._runner
        if runner is not None and runner is not current_thread():
            runner.join(timeout=5.0)
        with self._lock:
            self._close_kernel()
            self._logs.clear()
            self._commands.clear()
            self._checkpoints.clear()
            self._transition(SessionState.CLOSED)
            self._republish_state()
            return self

    def _close_kernel(self) -> None:
        if self._kernel is not None:
            self._kernel.close()
            self._kernel = None

    def _publish(
        self,
        observation: Mapping[str, Any],
        *,
        reward: float = 0.0,
        terminated: bool = False,
        truncated: bool = False,
    ) -> ObservationSnapshot:
        encoded = json.dumps(observation, sort_keys=True, separators=(",", ":"))
        self._snapshot = ObservationSnapshot(
            session_id=self.session_id,
            scenario_id=self.resolved.scenario_id,
            scenario_hash=self.resolved.resolved_hash,
            tick=self._tick,
            state=self._state,
            state_version=self._state_version,
            observation_json=encoded,
            reward=reward,
            total_reward=self._total_reward,
            terminated=terminated,
            truncated=truncated,
        )
        return self._snapshot

    def _republish_state(self) -> None:
        if self._snapshot is not None:
            old = self._snapshot
            self._snapshot = old.model_copy(
                update={"state": self._state, "state_version": self._state_version}
            )

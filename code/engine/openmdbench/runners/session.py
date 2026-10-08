"""RF-06 unified lockstep, continuous and read-only replay runners."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, RLock, Thread
from time import monotonic

from openmdbench.sessions.session import ObservationSnapshot, SessionState, SimulationSession


@dataclass(frozen=True, slots=True)
class RunnerClock:
    physics_dt_s: float
    decision_interval_ticks: int = 1
    speed_ratio: float = 1.0
    wall_clock_timeout_s: float | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.physics_dt_s) or self.physics_dt_s <= 0.0:
            raise ValueError("physics_dt_s must be finite and positive")
        if self.decision_interval_ticks < 1:
            raise ValueError("decision_interval_ticks must be positive")
        if self.speed_ratio <= 0.0 or math.isnan(self.speed_ratio):
            raise ValueError("speed_ratio must be positive")
        if self.wall_clock_timeout_s is not None and (
            not math.isfinite(self.wall_clock_timeout_s) or self.wall_clock_timeout_s <= 0.0
        ):
            raise ValueError("wall_clock_timeout_s must be finite and positive")


class LockstepRunner:
    def __init__(self, session: SimulationSession, clock: RunnerClock) -> None:
        self.session = session
        self.clock = clock

    @property
    def sim_time_s(self) -> float:
        return self.session.snapshot().tick * self.clock.physics_dt_s

    def run(self) -> LockstepRunner:
        self.session.start()
        return self

    def pause(self) -> None:
        self.session.pause()

    def resume(self) -> None:
        self.session.resume()

    def step(self, action: object | None = None) -> ObservationSnapshot:
        latest = self.session.snapshot()
        for _ in range(self.clock.decision_interval_ticks):
            latest = self.session.step(action)
            if self.session.state is not SessionState.RUNNING:
                break
        return latest

    def set_speed(self, speed_ratio: float) -> None:
        if speed_ratio <= 0.0 or math.isnan(speed_ratio):
            raise ValueError("speed_ratio must be positive")
        self.clock = RunnerClock(
            physics_dt_s=self.clock.physics_dt_s,
            decision_interval_ticks=self.clock.decision_interval_ticks,
            speed_ratio=speed_ratio,
            wall_clock_timeout_s=self.clock.wall_clock_timeout_s,
        )

    def terminate(self) -> None:
        if self.session.state in {
            SessionState.CREATED,
            SessionState.INITIALIZED,
            SessionState.RUNNING,
            SessionState.PAUSED,
        }:
            self.session.cancel()


class ContinuousRunner:
    def __init__(
        self,
        session: SimulationSession,
        clock: RunnerClock,
        *,
        action_provider: Callable[[ObservationSnapshot], object],
    ) -> None:
        self.session = session
        self.clock = clock
        self._action_provider = action_provider
        self._stop = Event()
        self._done = Event()
        self._thread: Thread | None = None
        self._clock_lock = RLock()

    @property
    def sim_time_s(self) -> float:
        return self.session.snapshot().tick * self.clock.physics_dt_s

    def run(self) -> ContinuousRunner:
        self.session.start()
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._done.clear()

        def loop() -> None:
            wall_started = monotonic()
            try:
                while not self._stop.is_set():
                    state = self.session.state
                    if state is SessionState.PAUSED:
                        self._stop.wait(0.001)
                        continue
                    if state is not SessionState.RUNNING:
                        return
                    started = monotonic()
                    snapshot = self.session.snapshot()
                    self.session.step(self._action_provider(snapshot))
                    with self._clock_lock:
                        clock = self.clock
                    if (
                        clock.wall_clock_timeout_s is not None
                        and monotonic() - wall_started >= clock.wall_clock_timeout_s
                        and self.session.state is SessionState.RUNNING
                    ):
                        self.session.expire()
                        return
                    interval = (
                        0.0
                        if math.isinf(clock.speed_ratio)
                        else clock.physics_dt_s / clock.speed_ratio
                    )
                    self._stop.wait(max(0.0, interval - (monotonic() - started)))
            finally:
                self._done.set()

        self._thread = Thread(
            target=loop, name=f"continuous-{self.session.session_id}", daemon=True
        )
        self._thread.start()
        return self

    def pause(self) -> None:
        self.session.pause()

    def resume(self) -> None:
        self.session.resume()

    def set_speed(self, speed_ratio: float) -> None:
        if speed_ratio <= 0.0 or math.isnan(speed_ratio):
            raise ValueError("speed_ratio must be positive")
        with self._clock_lock:
            self.clock = RunnerClock(
                physics_dt_s=self.clock.physics_dt_s,
                decision_interval_ticks=self.clock.decision_interval_ticks,
                speed_ratio=speed_ratio,
                wall_clock_timeout_s=self.clock.wall_clock_timeout_s,
            )

    def wait(self, *, timeout: float | None = None) -> ObservationSnapshot:
        if not self._done.wait(timeout):
            raise TimeoutError("continuous runner did not finish before timeout")
        return self.session.snapshot()

    def terminate(self) -> None:
        self._stop.set()
        if self.session.state in {
            SessionState.CREATED,
            SessionState.INITIALIZED,
            SessionState.RUNNING,
            SessionState.PAUSED,
        }:
            self.session.cancel()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

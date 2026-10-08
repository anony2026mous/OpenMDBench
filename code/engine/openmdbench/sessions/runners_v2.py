"""Schema-v2 session runners.

Runners pace or group calls to :class:`SessionLifecycleV2`; they never receive a
mutable World reference and never implement simulation rules.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from threading import Condition, RLock, Thread
from types import MappingProxyType
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from openmdbench.sessions.lifecycle_v2 import (
    ActionApplyReceiptV2,
    SessionLifecycleV2,
    SessionStateV2,
)


class RunnerFailureV2(RuntimeError):
    """Stable runner-boundary rejection."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class RunnerConfigV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=True)

    physics_dt_seconds: float = Field(gt=0.0)
    decision_interval_ticks: StrictInt = Field(ge=1, le=100_000)
    speed_ratio: float = Field(gt=0.0)

    @model_validator(mode="after")
    def validate_timing(self) -> RunnerConfigV2:
        if not math.isfinite(self.physics_dt_seconds):
            raise ValueError("runner physics dt must be finite")
        if math.isnan(self.speed_ratio):
            raise ValueError("runner speed ratio cannot be NaN")
        return self


class RunnerDecisionReceiptV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    operation_id: str = Field(min_length=1, max_length=256)
    start_tick: StrictInt = Field(ge=0)
    end_tick: StrictInt = Field(ge=0)
    tick_receipts: tuple[ActionApplyReceiptV2, ...]

    @model_validator(mode="after")
    def validate_ticks(self) -> RunnerDecisionReceiptV2:
        if self.end_tick - self.start_tick != len(self.tick_receipts):
            raise ValueError("runner receipt tick span is inconsistent")
        return self


def _validate_binding(session: SessionLifecycleV2, config: RunnerConfigV2) -> None:
    if not isinstance(session, SessionLifecycleV2):
        raise RunnerFailureV2("runner.session_invalid", "runner requires a V2 session")
    if config.physics_dt_seconds != session.physics_dt_seconds:
        raise RunnerFailureV2(
            "runner.clock_anchor_invalid", "runner and session physics clocks differ"
        )


class LockstepRunnerV2:
    """Advance exactly one configured decision interval per explicit call."""

    def __init__(self, *, session: SessionLifecycleV2, config: RunnerConfigV2) -> None:
        _validate_binding(session, config)
        self._session = session
        self.config = config
        self._lock = RLock()

    def step(self, *, operation_id: str, expected_tick: int) -> RunnerDecisionReceiptV2:
        with self._lock:
            if self._session.state is not SessionStateV2.RUNNING:
                raise RunnerFailureV2("runner.session_not_running", "session is not running")
            if self._session.world_view.tick != expected_tick:
                raise RunnerFailureV2("runner.tick_conflict", "expected tick is stale")
            receipts: list[ActionApplyReceiptV2] = []
            for offset in range(self.config.decision_interval_ticks):
                tick = expected_tick + offset
                receipts.append(
                    self._session.step(
                        operation_id=f"{operation_id}:physics:{offset}", expected_tick=tick
                    )
                )
            return RunnerDecisionReceiptV2(
                operation_id=operation_id,
                start_tick=expected_tick,
                end_tick=expected_tick + self.config.decision_interval_ticks,
                tick_receipts=tuple(receipts),
            )


class ContinuousRunnerV2:
    """One optional background writer that paces lockstep decisions by wall time."""

    def __init__(
        self,
        *,
        session: SessionLifecycleV2,
        config: RunnerConfigV2,
        sleep: Callable[[float], None],
    ) -> None:
        _validate_binding(session, config)
        self._session = session
        self.config = config
        self._sleep = sleep
        self._lockstep = LockstepRunnerV2(session=session, config=config)
        self._condition = Condition(RLock())
        self._paused = False
        self._terminated = False
        self._thread: Thread | None = None
        self._operation_prefix = "continuous"
        self._sequence = 0
        self._failure: BaseException | None = None

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _pace(self) -> None:
        if math.isfinite(self.config.speed_ratio):
            self._sleep(
                self.config.physics_dt_seconds
                * self.config.decision_interval_ticks
                / self.config.speed_ratio
            )

    def run_steps(
        self, *, steps: int, operation_prefix: str
    ) -> tuple[RunnerDecisionReceiptV2, ...]:
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
            raise RunnerFailureV2("runner.steps_invalid", "steps must be a non-negative integer")
        results: list[RunnerDecisionReceiptV2] = []
        for index in range(steps):
            tick = self._session.world_view.tick
            results.append(
                self._lockstep.step(operation_id=f"{operation_prefix}:{index}", expected_tick=tick)
            )
            self._pace()
        return tuple(results)

    def _run(self) -> None:
        try:
            while True:
                with self._condition:
                    while self._paused and not self._terminated:
                        self._condition.wait()
                    if self._terminated:
                        return
                    sequence = self._sequence
                    self._sequence += 1
                tick = self._session.world_view.tick
                self._lockstep.step(
                    operation_id=f"{self._operation_prefix}:{sequence}", expected_tick=tick
                )
                self._pace()
        except BaseException as error:
            with self._condition:
                if self._session.state in {SessionStateV2.STOPPED, SessionStateV2.CLOSED}:
                    self._failure = None
                else:
                    self._failure = error
                self._terminated = True
                self._condition.notify_all()

    def start(self, *, operation_prefix: str = "continuous") -> ContinuousRunnerV2:
        with self._condition:
            if self.is_alive:
                raise RunnerFailureV2("runner.already_running", "runner already has a writer")
            self._operation_prefix = operation_prefix
            self._terminated = False
            self._paused = False
            self._failure = None
            self._thread = Thread(target=self._run, name=f"runner:{operation_prefix}", daemon=True)
            self._thread.start()
        return self

    def pause(self) -> ContinuousRunnerV2:
        with self._condition:
            self._paused = True
        return self

    def resume(self) -> ContinuousRunnerV2:
        with self._condition:
            if self._terminated:
                raise RunnerFailureV2("runner.terminated", "terminated runner cannot resume")
            self._paused = False
            self._condition.notify_all()
        return self

    def terminate(self, *, timeout_seconds: float) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0.0:
            raise RunnerFailureV2("runner.timeout_invalid", "timeout must be finite and positive")
        with self._condition:
            self._terminated = True
            self._paused = False
            self._condition.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout_seconds)
            if thread.is_alive():
                raise RunnerFailureV2("runner.terminate_timeout", "writer did not terminate")
        self._thread = None
        if self._failure is not None:
            raise RunnerFailureV2("runner.writer_failed", str(self._failure))

    def close(self) -> None:
        self.terminate(timeout_seconds=5.0)

    def __enter__(self) -> ContinuousRunnerV2:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _freeze_record(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_record(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_record(item) for item in value)
    return value


class ReplayRunnerV2:
    """Read immutable records without constructing Session, World, RNG, or models."""

    def __init__(self, *, records: Sequence[Mapping[str, Any]]) -> None:
        self._records = tuple(_freeze_record(item) for item in records)
        self._index = 0

    def next(self) -> Mapping[str, Any] | None:
        if self._index >= len(self._records):
            return None
        value = cast(Mapping[str, Any], self._records[self._index])
        self._index += 1
        return value

    def seek(self, index: int) -> Mapping[str, Any]:
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or not 0 <= index < len(self._records)
        ):
            raise RunnerFailureV2("runner.replay_index_invalid", "replay index is out of range")
        self._index = index + 1
        return cast(Mapping[str, Any], self._records[index])


__all__ = [
    "ContinuousRunnerV2",
    "LockstepRunnerV2",
    "ReplayRunnerV2",
    "RunnerConfigV2",
    "RunnerDecisionReceiptV2",
    "RunnerFailureV2",
]

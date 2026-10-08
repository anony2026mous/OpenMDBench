"""Lazy public exports keep replay imports independent from simulation kernels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openmdbench.runners.replay import ReplayRunner
    from openmdbench.runners.session import ContinuousRunner, LockstepRunner, RunnerClock

__all__ = [
    "ContinuousRunner",
    "LockstepRunner",
    "ReplayRunner",
    "RunnerClock",
]


def __getattr__(name: str) -> Any:
    if name == "ReplayRunner":
        from openmdbench.runners.replay import ReplayRunner

        return ReplayRunner
    if name in {"ContinuousRunner", "LockstepRunner", "RunnerClock"}:
        from openmdbench.runners import session

        return getattr(session, name)
    raise AttributeError(name)

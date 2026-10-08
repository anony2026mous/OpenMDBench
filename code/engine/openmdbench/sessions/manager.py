"""Thread-safe ownership registry for simulation sessions."""

from __future__ import annotations

from threading import RLock
from uuid import uuid4

from openmdbench.scenarios.resolved import ResolvedScenario
from openmdbench.sessions.session import CommandApplier, KernelFactory, SimulationSession


class SessionManager:
    def __init__(
        self,
        *,
        kernel_factory: KernelFactory | None = None,
        command_applier: CommandApplier | None = None,
    ) -> None:
        self._kernel_factory = kernel_factory
        self._command_applier = command_applier
        self._sessions: dict[str, SimulationSession] = {}
        self._lock = RLock()

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def create(
        self,
        resolved: ResolvedScenario,
        *,
        seed: int,
        session_id: str | None = None,
    ) -> SimulationSession:
        identifier = session_id or str(uuid4())
        with self._lock:
            if identifier in self._sessions:
                raise ValueError(f"duplicate session_id: {identifier}")
            session = SimulationSession(
                identifier,
                resolved,
                seed=seed,
                kernel_factory=self._kernel_factory,
                command_applier=self._command_applier,
            )
            self._sessions[identifier] = session
            return session

    def get(self, session_id: str) -> SimulationSession:
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as error:
                raise KeyError("session not found") from error

    def close(self, session_id: str) -> SimulationSession:
        with self._lock:
            session = self.get(session_id)
            del self._sessions[session_id]
        session.close()
        return session

    def close_all(self) -> None:
        with self._lock:
            sessions = tuple(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.close()

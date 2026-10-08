"""Public authority boundary shared by REST, SDK and local adapters."""

from __future__ import annotations

from collections.abc import Callable

from openmdbench.scenarios.compiler import ScenarioCompiler
from openmdbench.scenarios.runtime import formal_package_ref
from openmdbench.schemas.platform import ActionBatch, ActionReceipt, CommandResult
from openmdbench.sessions.manager import SessionManager
from openmdbench.sessions.session import ObservationSnapshot, SimulationSession
from openmdbench.visualization.live import VisualizationView
from openmdbench.visualization.schema import VisualizationFrame


class AgentGateway:
    """No-world-state facade for every agent-facing transport."""

    def __init__(self, manager: SessionManager | None = None) -> None:
        self._manager = manager or SessionManager()
        self._compiler = ScenarioCompiler()

    @property
    def active_count(self) -> int:
        return self._manager.active_count

    def create(self, scenario_id: str, *, seed: int = 0) -> SimulationSession:
        resolved = self._compiler.compile_package(formal_package_ref(scenario_id))
        return self._manager.create(resolved, seed=seed).initialize()

    def session(self, session_id: str) -> SimulationSession:
        return self._manager.get(session_id)

    def snapshot(self, session_id: str) -> ObservationSnapshot:
        return self.session(session_id).snapshot()

    def start(self, session_id: str) -> ObservationSnapshot:
        session = self.session(session_id)
        session.start()
        return session.snapshot()

    def step(self, session_id: str, action: object | None = None) -> ObservationSnapshot:
        return self.session(session_id).step(action)

    def submit(self, session_id: str, batch: ActionBatch, *, actor_side: str) -> ActionReceipt:
        return self.session(session_id).submit_actions(batch, actor_side=actor_side)

    def command_result(self, session_id: str, command_id: str) -> CommandResult:
        return self.session(session_id).command_result(command_id)

    def control(self, session_id: str, operation: str) -> ObservationSnapshot:
        session = self.session(session_id)
        operations: dict[str, Callable[[], SimulationSession]] = {
            "start": session.start,
            "pause": session.pause,
            "resume": session.resume,
            "cancel": session.cancel,
        }
        try:
            operations[operation]()
        except KeyError as error:
            raise ValueError(f"unsupported control operation: {operation}") from error
        return session.snapshot()

    def frame(self, session_id: str, view: VisualizationView) -> VisualizationFrame:
        return self.session(session_id).visualization_snapshot(view)

    def close(self, session_id: str) -> None:
        self._manager.close(session_id)

    def close_all(self) -> None:
        self._manager.close_all()

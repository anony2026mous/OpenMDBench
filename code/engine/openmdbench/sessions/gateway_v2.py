"""One transport-independent schema-v2 agent authority boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from threading import RLock
from types import MappingProxyType
from typing import Any

from openmdbench.schemas.core_v2 import ObservationV2
from openmdbench.schemas.interface_v2 import ActionBatchV2
from openmdbench.sessions.lifecycle_v2 import (
    ActionApplyReceiptV2,
    ActionReceiptV2,
    SessionCheckpointV2,
    SessionLifecycleV2,
    SessionStateV2,
)
from openmdbench.visualization.v2 import FrameBuilderV2

SessionFactoryV2 = Callable[[str, int], SessionLifecycleV2]
SessionRestoreFactoryV2 = Callable[[SessionCheckpointV2], SessionLifecycleV2]
VisualizationFactoryV2 = Callable[[SessionLifecycleV2, str], Any]


class AgentGatewayV2:
    """Own V2 sessions without exposing their World or queue writer."""

    def __init__(
        self,
        *,
        session_factory: SessionFactoryV2 | None = None,
        restore_factory: SessionRestoreFactoryV2 | None = None,
        visualization_factory: VisualizationFactoryV2 | None = None,
    ) -> None:
        self._sessions: dict[str, SessionLifecycleV2] = {}
        self._session_factory = session_factory
        self._restore_factory = restore_factory
        self._visualization_factory = visualization_factory
        self._lock = RLock()

    @property
    def session_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._sessions))

    def attach(self, session: SessionLifecycleV2) -> str:
        if (
            not isinstance(session, SessionLifecycleV2)
            or session.state is not SessionStateV2.CREATED
        ):
            raise ValueError("gateway accepts one uninitialized V2 session authority")
        with self._lock:
            if session.session_id in self._sessions:
                raise ValueError("gateway session identity already exists")
            self._sessions[session.session_id] = session
            return session.session_id

    def create(self, *, session_id: str, seed: int) -> str:
        if self._session_factory is None:
            raise RuntimeError("gateway session factory is not configured")
        return self.attach(self._session_factory(session_id, seed))

    def restore(self, checkpoint: SessionCheckpointV2) -> str:
        if self._restore_factory is None:
            raise RuntimeError("gateway restore factory is not configured")
        session = self._restore_factory(checkpoint)
        if not isinstance(session, SessionLifecycleV2) or session.state in {
            SessionStateV2.CREATED,
            SessionStateV2.CLOSED,
        }:
            raise ValueError("gateway restore factory returned an invalid restored session")
        restored_checkpoint = session.checkpoint()
        if (
            restored_checkpoint.session_id != checkpoint.session_id
            or restored_checkpoint.checkpoint_hash != checkpoint.checkpoint_hash
        ):
            if session.state in {
                SessionStateV2.RUNNING,
                SessionStateV2.LOADED,
                SessionStateV2.PAUSED,
            }:
                session.stop()
            session.close()
            raise ValueError("gateway restore factory returned a different checkpoint authority")
        with self._lock:
            if session.session_id in self._sessions:
                raise ValueError("gateway session identity already exists")
            self._sessions[session.session_id] = session
        return session.session_id

    def _get(self, session_id: str) -> SessionLifecycleV2:
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as error:
                raise KeyError(f"unknown session: {session_id}") from error

    def control(self, session_id: str, operation: str) -> SessionStateV2:
        session = self._get(session_id)
        if operation == "load":
            session.load()
        elif operation == "start":
            session.start()
        elif operation == "pause":
            session.pause()
        elif operation == "resume":
            session.resume()
        elif operation == "stop":
            session.stop()
        else:
            raise ValueError("unsupported session control operation")
        return session.state

    def observation(self, session_id: str, *, faction_id: str) -> ObservationV2:
        return self._get(session_id).world_view.observation(observer_faction_id=faction_id)

    def submit(
        self,
        session_id: str,
        *,
        batch: ActionBatchV2,
        authority_token: str,
        operation_id: str,
        expected_tick: int,
    ) -> ActionReceiptV2:
        if batch.session_id != session_id:
            raise ValueError("action batch session differs from gateway route")
        return self._get(session_id).submit_actions(
            batch=batch,
            authority_token=authority_token,
            operation_id=operation_id,
            expected_tick=expected_tick,
        )

    def step(
        self, session_id: str, *, operation_id: str, expected_tick: int
    ) -> ActionApplyReceiptV2:
        return self._get(session_id).step(operation_id=operation_id, expected_tick=expected_tick)

    def checkpoint(self, session_id: str) -> SessionCheckpointV2:
        return self._get(session_id).checkpoint()

    def command_status(self, session_id: str, child_id: str) -> str:
        statuses = self._get(session_id).action_status_view.statuses
        try:
            return statuses[child_id]
        except KeyError as error:
            raise KeyError(f"unknown command or action: {child_id}") from error

    def events(self, session_id: str) -> tuple[Mapping[str, Any], ...]:
        world = self._get(session_id).world_view.checkpoint()
        values: list[Mapping[str, Any]] = []
        for tick in world.world_tick_ledger:
            values.extend(tick.event_receipts)
        return tuple(MappingProxyType(dict(item)) for item in values)

    def result(self, session_id: str) -> Mapping[str, Any]:
        mission = self._get(session_id).world_view.checkpoint().mission_scoring_checkpoint
        if mission is None:
            return MappingProxyType({"terminal_result": None, "score_state": {}})
        return MappingProxyType(
            {
                "terminal_result": mission.get("terminal_result"),
                "score_state": mission.get("score_state", {}),
            }
        )

    def visualization(self, session_id: str, *, faction_id: str) -> Any:
        session = self._get(session_id)
        if self._visualization_factory is not None:
            return self._visualization_factory(session, faction_id)
        return FrameBuilderV2.from_observation(
            session.world_view.observation(observer_faction_id=faction_id),
            scenario_id=session.resolved.scenario_id,
        )

    def replay_artifact(self, session_id: str, *, faction_id: str) -> Mapping[str, Any]:
        session = self._get(session_id)
        checkpoint = session.checkpoint()
        frame = self.visualization(session_id, faction_id=faction_id)
        return MappingProxyType(
            {
                "schema_version": "gateway-replay@2.0",
                "session_id": session_id,
                "resolved_hash": checkpoint.resolved_hash,
                "catalog_hash": checkpoint.catalog_hash,
                "model_registry_hash": checkpoint.model_registry_hash,
                "seed": checkpoint.seed,
                "records": (
                    {
                        "tick": frame.tick,
                        "frame": frame.model_dump(mode="json"),
                        "world_checkpoint_hash": checkpoint.world_checkpoint_hash,
                    },
                ),
            }
        )

    def close(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id)
        if session.state in {
            SessionStateV2.RUNNING,
            SessionStateV2.LOADED,
            SessionStateV2.PAUSED,
        }:
            session.stop()
        session.close()


class StructuredPythonAdapterV2:
    def __init__(self, gateway: AgentGatewayV2, *, session_id: str, faction_id: str) -> None:
        self.gateway = gateway
        self.session_id = session_id
        self.faction_id = faction_id

    def observation(self) -> ObservationV2:
        return self.gateway.observation(self.session_id, faction_id=self.faction_id)

    def submit(
        self, batch: ActionBatchV2, *, authority_token: str, operation_id: str
    ) -> ActionReceiptV2:
        return self.gateway.submit(
            self.session_id,
            batch=batch,
            authority_token=authority_token,
            operation_id=operation_id,
            expected_tick=self.observation().tick,
        )

    def step(self, *, operation_id: str) -> ActionApplyReceiptV2:
        return self.gateway.step(
            self.session_id, operation_id=operation_id, expected_tick=self.observation().tick
        )


class GymnasiumAdapterV2:
    """Gymnasium-compatible signatures without owning simulation semantics."""

    def __init__(self, adapter: StructuredPythonAdapterV2, *, authority_token: str) -> None:
        self.adapter = adapter
        self._authority_token = authority_token

    def reset(self) -> tuple[Mapping[str, object], Mapping[str, object]]:
        observation = self.adapter.observation()
        return MappingProxyType(observation.model_dump(mode="json")), MappingProxyType({})

    def step(
        self, action: ActionBatchV2 | None
    ) -> tuple[Mapping[str, object], float, bool, bool, Mapping[str, object]]:
        if action is not None:
            self.adapter.submit(
                action,
                authority_token=self._authority_token,
                operation_id=f"gym.submit.{action.idempotency_key}",
            )
        receipt = self.adapter.step(operation_id=f"gym.tick.{self.adapter.observation().tick}")
        observation = self.adapter.observation()
        mission_receipts = tuple(getattr(receipt.world_receipt, "mission_receipts", ()))
        terminal_result = (
            None if not mission_receipts else mission_receipts[-1].terminal_result
        )
        outcome = None if terminal_result is None else terminal_result.outcome
        terminated = outcome is not None and outcome != "timeout"
        truncated = outcome == "timeout"
        terminal_payload = (
            None
            if terminal_result is None
            else {
                "rule_id": terminal_result.rule_id,
                "outcome": terminal_result.outcome,
                "priority": terminal_result.priority,
                "tick": terminal_result.tick,
                "latched": terminal_result.latched,
                "trigger_evidence": dict(terminal_result.trigger_evidence),
                "ranking": dict(terminal_result.ranking),
            }
        )
        return (
            MappingProxyType(observation.model_dump(mode="json")),
            0.0,
            terminated,
            truncated,
            MappingProxyType(
                {
                    "receipt_hash": receipt.receipt_hash,
                    "terminal_result": terminal_payload,
                }
            ),
        )


class VectorEnvAdapterV2:
    def __init__(self, environments: Sequence[GymnasiumAdapterV2]) -> None:
        if not environments or len({item.adapter.session_id for item in environments}) != len(
            environments
        ):
            raise ValueError("vector environments require unique nonempty sessions")
        self.environments = tuple(environments)

    def reset(self) -> tuple[tuple[Mapping[str, object], ...], tuple[Mapping[str, object], ...]]:
        values = tuple(item.reset() for item in self.environments)
        return tuple(item[0] for item in values), tuple(item[1] for item in values)

    def step(
        self, actions: Sequence[ActionBatchV2 | None]
    ) -> tuple[tuple[Mapping[str, object], float, bool, bool, Mapping[str, object]], ...]:
        if len(actions) != len(self.environments):
            raise ValueError("vector action cardinality mismatch")
        return tuple(
            environment.step(action)
            for environment, action in zip(self.environments, actions, strict=True)
        )


__all__ = [
    "AgentGatewayV2",
    "GymnasiumAdapterV2",
    "StructuredPythonAdapterV2",
    "VectorEnvAdapterV2",
    "SessionFactoryV2",
    "SessionRestoreFactoryV2",
    "VisualizationFactoryV2",
]

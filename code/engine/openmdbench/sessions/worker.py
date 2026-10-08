"""Spawn-isolated simulation worker with bounded request/response queues."""

from __future__ import annotations

from multiprocessing import get_context
from multiprocessing.process import BaseProcess
from multiprocessing.queues import Queue
from queue import Empty
from time import monotonic
from typing import Any

from openmdbench.scenarios.resolved import ResolvedScenario
from openmdbench.sessions.session import SimulationSession


def _worker_main(
    resolved_payload: dict[str, Any],
    seed: int,
    command_queue: Queue[Any],
    response_queue: Queue[Any],
) -> None:
    resolved = ResolvedScenario.model_validate(resolved_payload)
    session = SimulationSession("worker", resolved, seed=seed).initialize()
    try:
        while True:
            request_id, operation, payload = command_queue.get()
            if operation == "close":
                response_queue.put((request_id, True, None))
                return
            try:
                if operation == "start":
                    session.start()
                    value: object = session.snapshot().model_dump(mode="json")
                elif operation == "step":
                    value = session.step(payload).model_dump(mode="json")
                elif operation == "snapshot":
                    value = session.snapshot().model_dump(mode="json")
                elif operation == "heartbeat":
                    value = {"state": session.state.value, "monotonic": monotonic()}
                else:
                    raise ValueError(f"unsupported worker operation: {operation}")
                response_queue.put((request_id, True, value))
            except Exception as error:  # noqa: BLE001 - isolate failure at process boundary
                response_queue.put((request_id, False, (error.__class__.__name__, str(error))))
    finally:
        session.close()


class SessionWorker:
    """One spawned process per native simulation session."""

    def __init__(self, resolved: ResolvedScenario, *, seed: int, queue_capacity: int = 64) -> None:
        if queue_capacity < 1:
            raise ValueError("queue_capacity must be positive")
        context = get_context("spawn")
        self._requests: Queue[Any] = context.Queue(maxsize=queue_capacity)
        self._responses: Queue[Any] = context.Queue(maxsize=queue_capacity)
        self._process: BaseProcess = context.Process(
            target=_worker_main,
            args=(resolved.model_dump(mode="json"), seed, self._requests, self._responses),
            daemon=True,
        )
        self._next_id = 0
        self._process.start()

    @property
    def is_alive(self) -> bool:
        return self._process.is_alive()

    def request(self, operation: str, payload: object = None, *, timeout: float = 30.0) -> Any:
        if timeout <= 0.0:
            raise ValueError("timeout must be positive")
        if not self.is_alive:
            raise RuntimeError("simulation worker is not alive")
        self._next_id += 1
        request_id = self._next_id
        self._requests.put((request_id, operation, payload), timeout=timeout)
        try:
            response_id, ok, value = self._responses.get(timeout=timeout)
        except Empty as error:
            raise TimeoutError("simulation worker response timed out") from error
        if response_id != request_id:
            raise RuntimeError("simulation worker response ordering violation")
        if not ok:
            error_type, message = value
            raise RuntimeError(f"worker {error_type}: {message}")
        return value

    def close(self, *, timeout: float = 10.0) -> None:
        if self.is_alive:
            try:
                self.request("close", timeout=timeout)
            finally:
                self._process.join(timeout)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout)
        self._requests.close()
        self._responses.close()

    def __enter__(self) -> SessionWorker:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

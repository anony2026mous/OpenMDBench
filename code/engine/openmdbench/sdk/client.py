"""Synchronous client implemented exclusively against the public REST API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import httpx


class OpenMDBenchError(RuntimeError):
    def __init__(self, status_code: int, body: object) -> None:
        super().__init__(f"OpenMDBench API returned HTTP {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class OpenMDBenchClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def __enter__(self) -> OpenMDBenchClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: object | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        response = self._client.request(method, path, json=json, headers=headers)
        if response.is_error:
            try:
                body: object = response.json()
            except ValueError:
                body = response.text
            raise OpenMDBenchError(response.status_code, body)
        return response.json()

    def scenarios(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self._request("GET", "/v1/scenarios")
        return result

    def create_session(self, scenario_id: str, *, seed: int = 0) -> dict[str, Any]:
        result: dict[str, Any] = self._request(
            "POST", "/v1/sessions", json={"scenario_id": scenario_id, "seed": seed}
        )
        return result

    def session(self, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/v1/sessions/{session_id}")
        return result

    def observation(self, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/v1/sessions/{session_id}/observation")
        return result

    def submit_action(
        self,
        session_id: str,
        *,
        timestamp: int,
        action: tuple[float, float] | list[float],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = self._request(
            "POST",
            f"/v1/sessions/{session_id}/actions",
            json={"timestamp": timestamp, "action": list(action)},
            headers={"Idempotency-Key": idempotency_key or str(uuid4())},
        )
        return result

    def submit_action_batch(
        self,
        session_id: str,
        *,
        action_batch: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Submit the canonical MD-AD-002 RedActionBatch without schema translation."""
        timestamp = action_batch.get("timestamp")
        if not isinstance(timestamp, int):
            raise ValueError("action_batch timestamp must be an integer")
        result: dict[str, Any] = self._request(
            "POST",
            f"/v1/sessions/{session_id}/actions",
            json={"timestamp": timestamp, "action_batch": dict(action_batch)},
            headers={"Idempotency-Key": idempotency_key or str(uuid4())},
        )
        return result

    def results(self, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/v1/sessions/{session_id}/results")
        return result

    def checkpoint(self, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("POST", f"/v1/sessions/{session_id}/checkpoints")
        return result

    def restore(self, session_id: str, checkpoint: dict[str, object]) -> dict[str, Any]:
        result: dict[str, Any] = self._request(
            "POST", f"/v1/sessions/{session_id}/restore", json={"checkpoint": checkpoint}
        )
        return result

    def close_session(self, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("DELETE", f"/v1/sessions/{session_id}")
        return result

    def close(self) -> None:
        self._client.close()

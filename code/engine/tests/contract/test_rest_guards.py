"""Idempotency, error, rate-limit, and isolation contracts."""

import asyncio
from typing import Any

import httpx
from openmdbench.api.app import create_app
from openmdbench.api.sessions import SessionStore


async def _create(client: httpx.AsyncClient, seed: int) -> str:
    response = await client.post("/v1/sessions", json={"scenario_id": "MD-REC-001", "seed": seed})
    return str(response.json()["session_id"])


async def _guard_contracts() -> None:
    transport = httpx.ASGITransport(app=create_app(SessionStore(rate_limit=2)))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first_id = await _create(client, 1)
        second_id = await _create(client, 2)
        endpoint = f"/v1/sessions/{first_id}/actions"
        payload = {"timestamp": 0, "action": [2.0, 30.0]}
        headers = {"Idempotency-Key": "same", "X-Request-ID": "request-123"}
        first = await client.post(endpoint, json=payload, headers=headers)
        repeated = await client.post(endpoint, json=payload, headers=headers)
        assert first.json() == repeated.json()
        assert repeated.headers["X-Request-ID"] == "request-123"
        assert (await client.get(f"/v1/sessions/{first_id}")).json()["timestamp"] == 1
        assert (await client.get(f"/v1/sessions/{second_id}")).json()["timestamp"] == 0

        conflict = await client.post(
            endpoint,
            json={"timestamp": 1, "action": [1.0, 0.0]},
            headers={"Idempotency-Key": "same"},
        )
        assert conflict.status_code == 409
        assert set(conflict.json()) == {"code", "message", "details", "request_id"}

        invalid = await client.post(
            endpoint,
            json={"timestamp": 1, "action": [99.0, 0.0]},
            headers={"Idempotency-Key": "invalid"},
        )
        assert invalid.status_code == 422
        assert (await client.get(f"/v1/sessions/{first_id}")).json()["timestamp"] == 1

        accepted = await client.post(
            endpoint,
            json={"timestamp": 1, "action": [1.0, 0.0]},
            headers={"Idempotency-Key": "second"},
        )
        assert accepted.status_code == 200
        limited = await client.post(
            endpoint,
            json={"timestamp": 2, "action": [1.0, 0.0]},
            headers={"Idempotency-Key": "third"},
        )
        assert limited.status_code == 429
        assert limited.json()["code"] == "rate_limited"


def test_rest_guards() -> None:
    asyncio.run(_guard_contracts())


async def _validation_error() -> dict[str, Any]:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/sessions", json={"seed": 1})
        assert response.status_code == 422
        body: dict[str, Any] = response.json()
        return body


def test_validation_uses_unified_error_shape() -> None:
    assert set(asyncio.run(_validation_error())) == {
        "code",
        "message",
        "details",
        "request_id",
    }

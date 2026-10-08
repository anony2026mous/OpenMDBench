"""REST anti-cheat and hostile-input regression tests."""

import asyncio
from collections.abc import AsyncIterator

import httpx
from openmdbench.api.app import create_app
from openmdbench.api.sessions import SessionStore


async def _oversized_chunks() -> AsyncIterator[bytes]:
    for _ in range(3):
        yield b"x" * 100


async def _security_checks() -> None:
    app = create_app(SessionStore(rate_limit=2), max_body_bytes=256)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        traversal = await client.post(
            "/v1/sessions", json={"scenario_id": "../../etc/passwd", "seed": 1}
        )
        assert traversal.status_code == 422
        oversized = await client.post(
            "/v1/sessions", content=b"x" * 300, headers={"content-type": "application/json"}
        )
        assert oversized.status_code == 413
        assert oversized.json()["code"] == "payload_too_large"
        chunked = await client.post(
            "/v1/sessions",
            content=_oversized_chunks(),
            headers={"content-type": "application/json", "transfer-encoding": "chunked"},
        )
        assert chunked.status_code == 413

        first = (
            await client.post("/v1/sessions", json={"scenario_id": "MD-REC-001", "seed": 1})
        ).json()["session_id"]
        second = (
            await client.post("/v1/sessions", json={"scenario_id": "MD-REC-001", "seed": 2})
        ).json()["session_id"]
        unknown_contact = await client.post(
            f"/v1/sessions/{first}/actions",
            json={"timestamp": 0, "action": [1.0, 0.0], "target_id": "secret-contact"},
            headers={"Idempotency-Key": "unknown"},
        )
        assert unknown_contact.status_code == 422
        assert (await client.get(f"/v1/sessions/{first}")).json()["timestamp"] == 0
        assert (await client.get(f"/v1/sessions/{second}")).json()["timestamp"] == 0


def test_api_security_boundaries() -> None:
    asyncio.run(_security_checks())

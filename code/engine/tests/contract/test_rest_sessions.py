"""REST route and OpenAPI contract smoke tests."""

import asyncio
from typing import Any

import httpx
from openmdbench.api.app import create_app


async def _lifecycle() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/health/live")).json() == {"status": "live"}
        assert (await client.get("/health/ready")).json() == {"status": "ready"}
        scenarios: list[dict[str, Any]] = (await client.get("/v1/scenarios")).json()
        # MD-INT-001 is retired: the public list contains the 35 YAML scenarios,
        # with the AD-002 placeholder replaced by its three formal variants.
        assert len(scenarios) == 37
        scenario_ids = {item["scenario_id"] for item in scenarios}
        assert {
            "MD-AD-002-EASY",
            "MD-AD-002-MEDIUM",
            "MD-AD-002-HARD",
        } <= scenario_ids
        assert "MD-AD-002" not in scenario_ids
        assert "MD-INT-001" not in scenario_ids
        created = await client.post("/v1/sessions", json={"scenario_id": "MD-REC-001", "seed": 7})
        assert created.status_code == 201
        session_id = created.json()["session_id"]
        assert (await client.get(f"/v1/sessions/{session_id}")).status_code == 200
        observation = (await client.get(f"/v1/sessions/{session_id}/observation")).json()
        stepped = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json={"timestamp": observation["timestamp"], "action": [1.0, 45.0]},
            headers={"Idempotency-Key": "step-1"},
        )
        assert stepped.status_code == 200
        assert stepped.json()["observation"]["timestamp"] == 1
        assert (await client.get(f"/v1/sessions/{session_id}/results")).status_code == 200
        checkpoint = (await client.post(f"/v1/sessions/{session_id}/checkpoints")).json()
        restored = await client.post(
            f"/v1/sessions/{session_id}/restore", json={"checkpoint": checkpoint}
        )
        assert restored.status_code == 201
        assert restored.json()["session_id"] != session_id
        assert (await client.delete(f"/v1/sessions/{session_id}")).json()["status"] == "closed"
        assert (await client.get(f"/v1/sessions/{session_id}")).status_code == 404


def test_health_scenarios_and_session_lifecycle() -> None:
    asyncio.run(_lifecycle())


async def _openapi() -> dict[str, Any]:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response: dict[str, Any] = (await client.get("/openapi.json")).json()
        return response


def test_openapi_publishes_all_required_routes() -> None:
    paths = _run_openapi()["paths"]
    required = {
        "/health/live",
        "/health/ready",
        "/v1/scenarios",
        "/v1/sessions",
        "/v1/sessions/{session_id}",
        "/v1/sessions/{session_id}/observation",
        "/v1/sessions/{session_id}/actions",
        "/v1/sessions/{session_id}/results",
        "/v1/sessions/{session_id}/checkpoints",
        "/v1/sessions/{session_id}/restore",
    }
    assert required <= set(paths)


def _run_openapi() -> dict[str, Any]:
    return asyncio.run(_openapi())

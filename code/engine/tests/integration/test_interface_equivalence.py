"""Local Gym, REST, and SDK must expose the same core transition results."""

import asyncio
import json
from typing import Any

import httpx
import numpy as np
from openmdbench.api.app import create_app
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.sdk import OpenMDBenchClient

ACTIONS = ((1.0, 20.0), (2.0, 80.0), (3.0, 140.0))


def _run_local() -> list[tuple[dict[str, Any], float, bool, bool]]:
    env = OpenMDBenchEnv(scenario_id="MD-REC-001", seed=7)
    env.reset(seed=7)
    results: list[tuple[dict[str, Any], float, bool, bool]] = []
    for action in ACTIONS:
        observation, reward, terminated, truncated, _ = env.step(
            np.asarray(action, dtype=np.float32)
        )
        results.append((observation, reward, terminated, truncated))
    return results


async def _run_rest() -> list[tuple[dict[str, Any], float, bool, bool]]:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/v1/sessions", json={"scenario_id": "MD-REC-001", "seed": 7})
        session_id = created.json()["session_id"]
        results: list[tuple[dict[str, Any], float, bool, bool]] = []
        for timestamp, action in enumerate(ACTIONS):
            response = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json={"timestamp": timestamp, "action": action},
                headers={"Idempotency-Key": f"rest-{timestamp}"},
            )
            body = response.json()
            results.append(
                (body["observation"], body["reward"], body["terminated"], body["truncated"])
            )
        return results


class SDKTransportFixture:
    """Small deterministic public-HTTP fixture for SDK serialization equivalence."""

    def __init__(self) -> None:
        self.env = OpenMDBenchEnv()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/sessions":
            self.env = OpenMDBenchEnv(scenario_id="MD-REC-001", seed=7)
            self.env.reset(seed=7)
            return httpx.Response(201, json={"session_id": "sdk-session"})
        if request.url.path.endswith("/actions"):
            action = json.loads(request.read())["action"]
            observation, reward, terminated, truncated, info = self.env.step(
                np.asarray(action, dtype=np.float32)
            )
            return httpx.Response(
                200,
                json={
                    "observation": observation,
                    "reward": reward,
                    "terminated": terminated,
                    "truncated": truncated,
                    "info": info,
                },
            )
        return httpx.Response(404)


def _run_sdk() -> list[tuple[dict[str, Any], float, bool, bool]]:
    results: list[tuple[dict[str, Any], float, bool, bool]] = []
    with OpenMDBenchClient(transport=httpx.MockTransport(SDKTransportFixture())) as client:
        session_id = client.create_session("MD-REC-001", seed=7)["session_id"]
        for timestamp, action in enumerate(ACTIONS):
            body = client.submit_action(
                session_id,
                timestamp=timestamp,
                action=action,
                idempotency_key=f"sdk-{timestamp}",
            )
            results.append(
                (body["observation"], body["reward"], body["terminated"], body["truncated"])
            )
    return results


def test_local_rest_and_sdk_sequences_are_equivalent() -> None:
    local = _run_local()
    assert asyncio.run(_run_rest()) == local
    assert _run_sdk() == local

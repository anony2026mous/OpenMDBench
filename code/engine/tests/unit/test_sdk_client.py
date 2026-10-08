"""Public SDK request and error behavior."""

import json

import httpx
import pytest
from openmdbench.sdk import OpenMDBenchClient, OpenMDBenchError


def test_sdk_uses_public_routes_and_idempotency_header() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/actions"):
            return httpx.Response(200, json={"terminated": False, "truncated": False})
        if request.method == "POST" and request.url.path == "/v1/sessions":
            return httpx.Response(201, json={"session_id": "session-1"})
        return httpx.Response(200, json={"status": "ok"})

    with OpenMDBenchClient(transport=httpx.MockTransport(handler)) as client:
        assert client.create_session("MD-REC-001", seed=7)["session_id"] == "session-1"
        client.observation("session-1")
        client.submit_action(
            "session-1", timestamp=0, action=(1.0, 90.0), idempotency_key="action-1"
        )
        client.results("session-1")
        client.checkpoint("session-1")
        client.restore("session-1", {"schema_version": "1.0"})
        client.close_session("session-1")
    assert all(request.url.path.startswith("/v1/") for request in requests)
    action_request = next(request for request in requests if request.url.path.endswith("/actions"))
    assert action_request.headers["Idempotency-Key"] == "action-1"
    assert json.loads(action_request.content)["timestamp"] == 0


def test_sdk_raises_structured_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"code": "conflict"})

    with (
        OpenMDBenchClient(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(OpenMDBenchError) as captured,
    ):
        client.session("missing")
    assert captured.value.status_code == 409
    assert captured.value.body == {"code": "conflict"}

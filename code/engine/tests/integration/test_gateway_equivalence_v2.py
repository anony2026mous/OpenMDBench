"""RF-12 Python, Gym, Vector, and REST delegation equivalence."""

from __future__ import annotations

import asyncio

import httpx
from openmdbench.api.gateway_v2 import create_gateway_app_v2
from openmdbench.sessions.gateway_v2 import (
    AgentGatewayV2,
    GymnasiumAdapterV2,
    StructuredPythonAdapterV2,
    VectorEnvAdapterV2,
)
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from tests.integration.test_session_action_world_v2 import _authority, _batch, _session


def _gateway(
    identifier: str,
) -> tuple[AgentGatewayV2, StructuredPythonAdapterV2, SessionLifecycleV2]:
    gateway = AgentGatewayV2()
    session = _session(identifier)
    gateway.attach(session)
    gateway.control(identifier, "load")
    gateway.control(identifier, "start")
    return (
        gateway,
        StructuredPythonAdapterV2(gateway, session_id=identifier, faction_id="coalition.alpha"),
        session,
    )


def test_structured_python_and_gym_produce_equivalent_public_state() -> None:
    py_gateway, python, python_session = _gateway("session.python")
    gym_gateway, gym_python, gym_session = _gateway("session.gym")
    python_batch = _batch(python_session).model_copy(update={"session_id": "session.python"})
    gym_batch = _batch(gym_session).model_copy(update={"session_id": "session.gym"})
    python.submit(
        python_batch,
        authority_token=_authority(python_session),
        operation_id="python.submit",
    )
    python.step(operation_id="python.tick")
    gym = GymnasiumAdapterV2(gym_python, authority_token=_authority(gym_session))
    gym.step(gym_batch)
    py_observation = python.observation().model_dump(mode="json")
    gym_observation = gym_python.observation().model_dump(mode="json")
    for value in (py_observation, gym_observation):
        value.pop("session_id")
    assert py_observation == gym_observation
    py_gateway.close("session.python")
    gym_gateway.close("session.gym")


def test_rest_uses_same_gateway_and_retry_does_not_repeat_discrete_action() -> None:
    async def exercise() -> None:
        gateway, adapter, session = _gateway("session.rest")
        batch = _batch(session).model_copy(update={"session_id": "session.rest"})
        request = {
            "batch": batch.model_dump(mode="json"),
            "authority_token": _authority(session),
            "operation_id": "rest.submit",
            "expected_tick": 0,
        }
        transport = httpx.ASGITransport(app=create_gateway_app_v2(gateway))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/v2/sessions/session.rest/actions", json=request)
            second = await client.post("/v2/sessions/session.rest/actions", json=request)
            assert first.status_code == second.status_code == 200
            assert first.json() == second.json()
            stepped = await client.post(
                "/v2/sessions/session.rest/step",
                json={"operation_id": "rest.tick", "expected_tick": 0},
            )
            assert stepped.status_code == 200
            observed = await client.get(
                "/v2/sessions/session.rest/observation",
                params={"faction_id": "coalition.alpha"},
            )
            assert observed.json() == adapter.observation().model_dump(mode="json")
        assert session.queue_view.consumed_discrete_action_ids == ("action.fire.001",)
        gateway.close("session.rest")

    asyncio.run(exercise())


def test_vector_sessions_are_isolated_and_cardinality_checked() -> None:
    pairs = tuple(_gateway(f"session.vector.{index}") for index in range(4))
    vector = VectorEnvAdapterV2(
        tuple(
            GymnasiumAdapterV2(adapter, authority_token=_authority(session))
            for _gateway_value, adapter, session in pairs
        )
    )
    observations, _infos = vector.reset()
    assert len(observations) == 4
    results = vector.step((None, None, None, None))
    assert tuple(item[0]["tick"] for item in results) == (1, 1, 1, 1)
    for gateway, _adapter, session in pairs:
        gateway.close(session.session_id)


def test_rest_crud_status_events_result_visualization_and_replay_are_authoritative() -> None:
    async def exercise() -> None:
        created_sessions: dict[str, SessionLifecycleV2] = {}

        def create_session(identifier: str, seed: int) -> SessionLifecycleV2:
            session = _session(identifier, seed=seed)
            created_sessions[identifier] = session
            return session

        def restore_session(checkpoint: object) -> SessionLifecycleV2:
            from openmdbench.sessions.lifecycle_v2 import SessionCheckpointV2

            assert isinstance(checkpoint, SessionCheckpointV2)
            source = created_sessions[checkpoint.session_id]
            return SessionLifecycleV2.restore(
                checkpoint=checkpoint,
                expected_checkpoint_hash=checkpoint.checkpoint_hash,
                resolved=source.resolved,
                expected_resolved_hash=source.resolved.resolved_hash,
                model_registry=source.world_factory._model_registry,
                expected_model_registry_hash=source.model_registry_hash,
                world_factory=source.world_factory,
            )

        gateway = AgentGatewayV2(
            session_factory=create_session,
            restore_factory=restore_session,
        )
        transport = httpx.ASGITransport(app=create_gateway_app_v2(gateway))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/v2/sessions", json={"session_id": "session.rest.crud", "seed": 73}
            )
            assert created.status_code == 201
            for operation in ("load", "start"):
                controlled = await client.post(
                    "/v2/sessions/session.rest.crud/control", json={"operation": operation}
                )
                assert controlled.status_code == 200
            session = created_sessions["session.rest.crud"]
            batch = _batch(session).model_copy(update={"session_id": "session.rest.crud"})
            submitted = await client.post(
                "/v2/sessions/session.rest.crud/actions",
                json={
                    "batch": batch.model_dump(mode="json"),
                    "authority_token": _authority(session),
                    "operation_id": "rest.crud.submit",
                    "expected_tick": 0,
                },
            )
            assert submitted.status_code == 200
            status = await client.get(
                "/v2/sessions/session.rest.crud/commands/command.navigation.001"
            )
            assert status.json()["status"] == "queued"
            stepped = await client.post(
                "/v2/sessions/session.rest.crud/step",
                json={"operation_id": "rest.crud.tick", "expected_tick": 0},
            )
            assert stepped.status_code == 200
            active = await client.get(
                "/v2/sessions/session.rest.crud/commands/command.navigation.001"
            )
            assert active.json()["status"] == "active"
            for suffix in ("events", "result"):
                response = await client.get(f"/v2/sessions/session.rest.crud/{suffix}")
                assert response.status_code == 200
            frame = await client.get(
                "/v2/sessions/session.rest.crud/visualization",
                params={"faction_id": "coalition.alpha"},
            )
            replay = await client.get(
                "/v2/sessions/session.rest.crud/replay",
                params={"faction_id": "coalition.alpha"},
            )
            assert frame.json()["tick"] == replay.json()["records"][0]["tick"] == 1
            checkpoint = await client.get("/v2/sessions/session.rest.crud/checkpoint")
            deleted = await client.delete("/v2/sessions/session.rest.crud")
            assert deleted.status_code == 204
            assert gateway.session_ids == ()
            restored = await client.post(
                "/v2/sessions/restore", json={"checkpoint": checkpoint.json()}
            )
            assert restored.status_code == 201
            restored_observation = await client.get(
                "/v2/sessions/session.rest.crud/observation",
                params={"faction_id": "coalition.alpha"},
            )
            assert restored_observation.json()["tick"] == 1
            assert (await client.delete("/v2/sessions/session.rest.crud")).status_code == 204

    asyncio.run(exercise())

"""MD3-08 public-interface contracts over a formal data-only package."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import cast

import httpx
import pytest
from openmdbench.api.gateway_v2 import create_gateway_app_v2
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.sessions.gateway_v2 import (
    AgentGatewayV2,
    GymnasiumAdapterV2,
    StructuredPythonAdapterV2,
    VectorEnvAdapterV2,
)
from openmdbench.sessions.lifecycle_v2 import SessionFailureV2, SessionLifecycleV2

DEFENDER_MOVERS = (
    "unit.guard.usv.01",
    "unit.guard.usv.02",
    "unit.guard.usv.03",
    "unit.guard.uav.01",
    "unit.guard.uav.02",
)


def _controller_authority(session: SessionLifecycleV2, controller_id: str) -> str:
    tokens = session.world_view.authority_tokens
    return next(
        token
        for token, grant in tokens.items()
        if grant.controller_id == controller_id
        and grant.entity_id == ""
        and set(getattr(grant, "entity_ids", ())).issuperset(DEFENDER_MOVERS)
    )


def _defender_batch(session: SessionLifecycleV2) -> ActionBatchV2:
    tick = session.world_view.tick
    return ActionBatchV2(
        schema_version="2.0",
        session_id=session.session_id,
        batch_id="batch.defender.five",
        idempotency_key="idem.defender.five",
        faction_id="faction.defender",
        based_on_tick=tick,
        valid_until_tick=tick + 2,
        persistent_commands=tuple(
            PersistentCommandV2(
                schema_version="2.0",
                command_id=f"command.navigation.{entity_id.replace('.', '-')}",
                command_type="navigation",
                entity_id=entity_id,
                faction_id="faction.defender",
                based_on_tick=tick,
                valid_until_tick=tick + 2,
                payload={"speed_mps": 1.0, "heading_deg": 90.0},
            )
            for entity_id in DEFENDER_MOVERS
        ),
    )


def _running_gateway(
    session_id: str,
) -> tuple[AgentGatewayV2, SessionLifecycleV2, StructuredPythonAdapterV2, str]:
    session = create_formal_session_v2("MD-INT-003-EASY", session_id=session_id, seed=73)
    gateway = AgentGatewayV2()
    gateway.attach(session)
    gateway.control(session_id, "load")
    gateway.control(session_id, "start")
    return (
        gateway,
        session,
        StructuredPythonAdapterV2(gateway, session_id=session_id, faction_id="faction.defender"),
        _controller_authority(session, "agent.defence"),
    )


def _without_session_id(observation: Mapping[str, object]) -> dict[str, object]:
    value = dict(observation)
    value.pop("session_id")
    return value


def test_one_controller_batch_controls_all_five_defender_movers() -> None:
    session = create_formal_session_v2("MD-INT-003-EASY", session_id="md3.interfaces.five", seed=73)
    session.load().start()
    try:
        authority = _controller_authority(session, "agent.defence")
        batch = _defender_batch(session)
        session.submit_actions(
            batch=batch,
            authority_token=authority,
            operation_id="md3.interfaces.submit.five",
            expected_tick=0,
        )
        first_receipt = session.step(operation_id="md3.interfaces.tick.five.0", expected_tick=0)
        assert first_receipt.activated_command_ids == ("command.navigation.unit-guard-usv-01",)
        second_receipt = session.step(operation_id="md3.interfaces.tick.five.1", expected_tick=1)
        assert tuple(
            sorted((*first_receipt.activated_command_ids, *second_receipt.activated_command_ids))
        ) == tuple(sorted(command.command_id for command in batch.persistent_commands))
    finally:
        session.stop().close()


def test_shore_navigation_and_cross_faction_batch_are_rejected_without_advancing() -> None:
    session = create_formal_session_v2(
        "MD-INT-003-EASY", session_id="md3.interfaces.reject", seed=73
    )
    session.load().start()
    try:
        authority = _controller_authority(session, "agent.defence")
        tick = session.world_view.tick
        shore = PersistentCommandV2(
            schema_version="2.0",
            command_id="command.navigation.shore",
            command_type="navigation",
            entity_id="unit.guard.shore.01",
            faction_id="faction.defender",
            based_on_tick=tick,
            valid_until_tick=tick + 1,
            payload={"speed_mps": 1.0, "heading_deg": 90.0},
        )
        shore_batch = ActionBatchV2(
            schema_version="2.0",
            session_id=session.session_id,
            batch_id="batch.shore.reject",
            idempotency_key="idem.shore.reject",
            faction_id="faction.defender",
            based_on_tick=tick,
            valid_until_tick=tick + 1,
            persistent_commands=(shore,),
        )
        with pytest.raises(SessionFailureV2, match="capability_missing"):
            session.submit_actions(
                batch=shore_batch,
                authority_token=authority,
                operation_id="md3.interfaces.submit.shore",
                expected_tick=tick,
            )
        attacker = PersistentCommandV2(
            schema_version="2.0",
            command_id="command.navigation.attacker",
            command_type="navigation",
            entity_id="unit.raid.usv.01",
            faction_id="faction.attacker",
            based_on_tick=tick,
            valid_until_tick=tick + 1,
            payload={"speed_mps": 1.0, "heading_deg": 90.0},
        )
        attacker_batch = ActionBatchV2(
            schema_version="2.0",
            session_id=session.session_id,
            batch_id="batch.cross-faction.reject",
            idempotency_key="idem.cross-faction.reject",
            faction_id="faction.attacker",
            based_on_tick=tick,
            valid_until_tick=tick + 1,
            persistent_commands=(attacker,),
        )
        with pytest.raises(SessionFailureV2, match="controller_authority_invalid"):
            session.submit_actions(
                batch=attacker_batch,
                authority_token=authority,
                operation_id="md3.interfaces.submit.cross-faction",
                expected_tick=tick,
            )
        assert session.world_view.tick == tick
    finally:
        session.stop().close()


def test_python_gym_vector_and_rest_share_one_public_action_timeline() -> None:
    python_gateway, python_session, python, python_authority = _running_gateway(
        "md3.interfaces.python"
    )
    gym_gateway, gym_session, gym_python, gym_authority = _running_gateway("md3.interfaces.gym")
    rest_gateway, rest_session, rest_python, rest_authority = _running_gateway(
        "md3.interfaces.rest"
    )
    vector_pairs = tuple(_running_gateway(f"md3.interfaces.vector.{index}") for index in range(2))
    try:
        python_batch = _defender_batch(python_session)
        python.submit(
            python_batch,
            authority_token=python_authority,
            operation_id="md3.interfaces.python.submit",
        )
        python.step(operation_id="md3.interfaces.python.step")
        python_observation = _without_session_id(python.observation().model_dump(mode="json"))

        gym = GymnasiumAdapterV2(gym_python, authority_token=gym_authority)
        gym_observation, _reward, terminated, truncated, _info = gym.step(
            _defender_batch(gym_session)
        )
        assert terminated is False and truncated is False
        assert _without_session_id(gym_observation) == python_observation

        vector = VectorEnvAdapterV2(
            tuple(
                GymnasiumAdapterV2(adapter, authority_token=authority)
                for _gateway, _session, adapter, authority in vector_pairs
            )
        )
        vector_results = vector.step(
            tuple(
                _defender_batch(session) for _gateway, session, _adapter, _authority in vector_pairs
            )
        )
        assert len(vector_results) == 2
        assert all(
            _without_session_id(result[0]) == python_observation for result in vector_results
        )

        async def exercise_rest() -> dict[str, object]:
            transport = httpx.ASGITransport(app=create_gateway_app_v2(rest_gateway))
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                before = await client.get(
                    "/v2/sessions/md3.interfaces.rest/observation",
                    params={"faction_id": "faction.defender"},
                )
                assert before.status_code == 200 and before.json()["tick"] == 0
                request = {
                    "batch": _defender_batch(rest_session).model_dump(mode="json"),
                    "authority_token": rest_authority,
                    "operation_id": "md3.interfaces.rest.submit",
                    "expected_tick": 0,
                }
                first = await client.post("/v2/sessions/md3.interfaces.rest/actions", json=request)
                retry = await client.post("/v2/sessions/md3.interfaces.rest/actions", json=request)
                assert first.status_code == retry.status_code == 200
                assert first.json() == retry.json()
                unchanged = await client.get(
                    "/v2/sessions/md3.interfaces.rest/observation",
                    params={"faction_id": "faction.defender"},
                )
                assert unchanged.json()["tick"] == 0
                stepped = await client.post(
                    "/v2/sessions/md3.interfaces.rest/step",
                    json={"operation_id": "md3.interfaces.rest.step", "expected_tick": 0},
                )
                assert stepped.status_code == 200
                after = await client.get(
                    "/v2/sessions/md3.interfaces.rest/observation",
                    params={"faction_id": "faction.defender"},
                )
                assert after.status_code == 200
                return cast(dict[str, object], after.json())

        assert _without_session_id(asyncio.run(exercise_rest())) == python_observation
        assert (
            _without_session_id(rest_python.observation().model_dump(mode="json"))
            == python_observation
        )
    finally:
        for gateway, session, _adapter, _authority in (
            (python_gateway, python_session, python, python_authority),
            (gym_gateway, gym_session, gym_python, gym_authority),
            (rest_gateway, rest_session, rest_python, rest_authority),
            *vector_pairs,
        ):
            gateway.close(session.session_id)

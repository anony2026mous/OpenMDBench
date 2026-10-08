import asyncio
from pathlib import Path

import httpx
from openmdbench.api.app import create_app
from openmdbench.api.sessions import SessionStore
from openmdbench.policies import AD2RedBaselineAgent
from openmdbench.replay import ReplayReader
from openmdbench.schemas.md_ad_002_interface import RedObservation


async def _terminal_match() -> None:
    store = SessionStore()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(store)), base_url="http://test"
    ) as client:
        created = await client.post(
            "/v1/sessions", json={"scenario_id": "MD-AD-002-EASY", "seed": 17}
        )
        assert created.status_code == 201
        session_id = created.json()["session_id"]
        session = store.get(session_id)
        assert session.env._ad2_adjudicator is not None
        session.env._ad2_adjudicator.time_limit_ticks = 5
        protected = (
            float(session.env._protected_point[0]),
            float(session.env._protected_point[1]),
        )
        agent = AD2RedBaselineAgent(protected)
        for tick in range(5):
            payload = (await client.get(f"/v1/sessions/{session_id}/observation")).json()
            observation = RedObservation.model_validate(payload)
            response = await client.post(
                f"/v1/sessions/{session_id}/actions",
                headers={"Idempotency-Key": f"tick-{tick}"},
                json={
                    "timestamp": observation.timestamp,
                    "action_batch": agent.act(observation).model_dump(mode="json"),
                },
            )
            assert response.status_code == 200, response.text
        result = (await client.get(f"/v1/sessions/{session_id}/results")).json()
        assert result["outcome"] == "red_success"
        assert result["reason"] == "timeout_denial_success"


def test_same_red_policy_core_completes_rest_match() -> None:
    asyncio.run(_terminal_match())


async def _medium_timeout_match() -> None:
    store = SessionStore()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(store)), base_url="http://test"
    ) as client:
        created = await client.post(
            "/v1/sessions", json={"scenario_id": "MD-AD-002-MEDIUM", "seed": 18}
        )
        assert created.status_code == 201
        session = store.get(created.json()["session_id"])
        assert session.env._ad2_adjudicator is not None
        session.env._ad2_adjudicator.time_limit_ticks = 1
        observation = RedObservation.model_validate(
            (await client.get(f"/v1/sessions/{session.session_id}/observation")).json()
        )
        agent = AD2RedBaselineAgent(
            (float(session.env._protected_point[0]), float(session.env._protected_point[1]))
        )
        response = await client.post(
            f"/v1/sessions/{session.session_id}/actions",
            headers={"Idempotency-Key": "medium-0"},
            json={
                "timestamp": observation.timestamp,
                "action_batch": agent.act(observation).model_dump(mode="json"),
            },
        )
        assert response.status_code == 200
        result = (await client.get(f"/v1/sessions/{session.session_id}/results")).json()
        assert result["reason"] == "timeout_denial_success"


def test_medium_uses_same_rest_contract() -> None:
    asyncio.run(_medium_timeout_match())


def test_rest_action_batch_persists_each_ad2_replay_frame(tmp_path: Path) -> None:
    store = SessionStore(replay_dir=tmp_path)
    session = store.create("MD-AD-002-EASY", seed=19)
    observation = session.env.red_observation()
    agent = AD2RedBaselineAgent(
        (float(session.env._protected_point[0]), float(session.env._protected_point[1]))
    )

    store.step_action_batch(session, agent.act(observation))
    store.delete(session.session_id)

    frames = tuple(ReplayReader(tmp_path / f"{session.session_id}.replay.jsonl").frames())
    assert [frame.timestamp for frame in frames] == [0, 1]

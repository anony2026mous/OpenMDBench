import copy
from typing import Any

import pytest
from openmdbench.api.models import ActionRequest
from openmdbench.api.sessions import SessionStore
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.schemas.md_ad_002_interface import RedActionBatch
from pydantic import ValidationError


def _batch(timestamp: int, entity_id: str = "red-interceptor-uav-1") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "scenario_id": "MD-AD-002-EASY",
        "timestamp": timestamp,
        "actions": [
            {
                "entity_id": entity_id,
                "navigation": {"mode": "hold_position"},
                "sensor": {"mode": "active_search"},
                "communication": {"relay_enabled": False},
                "engagement": None,
                "ciws_auto": None,
            }
        ],
        "high_level_intent": {"strategy": "hold"},
    }


def test_canonical_batch_json_round_trip_and_duplicate_rejected() -> None:
    batch = RedActionBatch.model_validate(_batch(0))
    assert RedActionBatch.model_validate_json(batch.model_dump_json()) == batch
    duplicate = _batch(0)
    duplicate["actions"] = [duplicate["actions"][0], duplicate["actions"][0]]
    with pytest.raises(ValidationError, match="duplicate entity"):
        RedActionBatch.model_validate(duplicate)


def test_unknown_entity_batch_is_atomic() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=11)
    env.reset(seed=11)
    before = copy.deepcopy(env.export_state())
    with pytest.raises(ValueError, match="unknown action entity"):
        env.step_red_action_batch(RedActionBatch.model_validate(_batch(0, "red-unknown")))
    assert env.export_state() == before


def test_red_observation_reports_own_operational_status() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=12)
    env.reset(seed=12)
    observation = env.red_observation()
    assert len(observation.own_forces) == 7
    assert {asset.operational_status for asset in observation.own_forces} == {"active"}


def test_non_finite_target_and_wrong_scenario_fail_closed() -> None:
    invalid = _batch(0)
    invalid["actions"][0]["navigation"] = {
        "mode": "move_to",
        "target_m": [float("nan"), 0.0, 100.0],
    }
    with pytest.raises(ValidationError, match="finite"):
        RedActionBatch.model_validate(invalid)

    invalid_altitude = _batch(0)
    invalid_altitude["actions"][0]["navigation"] = {
        "mode": "move_to",
        "target_m": [0.0, 0.0, 3_001.0],
    }
    with pytest.raises(ValidationError, match="altitude"):
        RedActionBatch.model_validate(invalid_altitude)

    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=1)
    env.reset(seed=1)
    before = copy.deepcopy(env.export_state())
    with pytest.raises(ValueError, match="scenario_id mismatch"):
        env.step_red_action_batch(RedActionBatch.model_validate(_batch(0)))
    assert env.export_state() == before


def test_two_action_batch_sessions_are_isolated() -> None:
    first = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=1)
    second = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=2)
    first.reset(seed=1)
    second.reset(seed=2)
    second_before = copy.deepcopy(second.export_state())
    first.step_red_action_batch(RedActionBatch.model_validate(_batch(0)))
    assert second.export_state() == second_before


def test_rest_request_and_session_adapter_preserve_canonical_batch() -> None:
    request = ActionRequest.model_validate({"timestamp": 0, "action_batch": _batch(0)})
    assert request.action_batch is not None
    assert RedActionBatch.model_validate(
        request.model_dump(mode="json")["action_batch"]
    ) == RedActionBatch.model_validate(_batch(0))
    store = SessionStore()
    session = store.create("MD-AD-002-EASY", 5)
    observation = session.env.red_observation().model_dump(mode="json")
    assert "own_forces" in observation and "contacts" in observation
    assert "blue-striker-uav-01" not in str(observation)
    result = store.step_action_batch(session, request.action_batch)
    assert result["observation"]["schema_version"] == "1.0"

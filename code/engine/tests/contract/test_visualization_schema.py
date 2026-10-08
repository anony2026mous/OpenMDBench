"""VisualizationFrame examples, versioning, and diagnostic contracts."""

import pytest
from openmdbench.visualization.schema import (
    REPLAY_RECORD_ADAPTER,
    ReplayMetadata,
    VisualizationFrame,
    replay_json_schema,
)
from pydantic import ValidationError


def _frame() -> dict[str, object]:
    return {
        "record_type": "frame",
        "timestamp": 42,
        "actions": [],
        "entities": [
            {
                "id": "usv-blue-1",
                "side": "blue",
                "type": "usv",
                "domain": "surface",
                "position": [100.0, 200.0, 0.0],
                "velocity": [2.0, 1.0, 0.0],
                "heading": 63.0,
                "health": 0.9,
                "energy": 0.72,
                "sensor_mode": "active_search",
                "comm_status": "connected",
                "status": "active",
                "visual_profile": "usv_generic",
            }
        ],
        "detections": {"blue": [], "red": []},
        "events": [],
        "scores": {"blue": {"total": 0.65}, "red": {"total": 0.42}},
    }


def test_requirements_examples_and_json_schema_validate() -> None:
    metadata = ReplayMetadata.model_validate(
        {
            "record_type": "metadata",
            "schema_version": "1.0",
            "match_id": "match-001",
            "scenario_id": "MD-INT-003",
            "seed": 7,
            "tick_seconds": 1.0,
            "coordinate_system": "local_enu",
            "engine_version": "1.0.0",
            "config_hash": "sha256:abc",
        }
    )
    assert metadata.match_id == "match-001"
    assert VisualizationFrame.model_validate(_frame()).timestamp == 42
    schema = replay_json_schema()
    assert "$defs" in schema and "discriminator" in schema


def test_unknown_major_version_is_rejected() -> None:
    payload = {
        "record_type": "metadata",
        "schema_version": "2.0",
        "match_id": "match-001",
        "scenario_id": "MD-INT-003",
        "seed": 7,
        "tick_seconds": 1.0,
        "coordinate_system": "local_enu",
        "engine_version": "1.0.0",
        "config_hash": "sha256:abc",
    }
    with pytest.raises(ValidationError, match="schema_version"):
        REPLAY_RECORD_ADAPTER.validate_python(payload)


def test_missing_required_field_reports_full_path() -> None:
    payload = _frame()
    del payload["entities"]
    with pytest.raises(ValidationError) as captured:
        VisualizationFrame.model_validate(payload)
    assert captured.value.errors()[0]["loc"] == ("entities",)

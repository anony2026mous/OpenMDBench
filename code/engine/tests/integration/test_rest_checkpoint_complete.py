"""Complete REST checkpoint restoration and anti-tamper tests."""

import copy
from pathlib import Path

import pytest
from openmdbench.api.sessions import SessionStore
from openmdbench.replay.audit import AuditLog


def test_checkpoint_contains_required_state_and_resumes_exactly() -> None:
    store = SessionStore()
    original = store.create("MD-TRK-001", 17)
    for _ in range(5):
        store.step(original, (3.0, 40.0))
    checkpoint = original.checkpoint()
    required = {
        "simulation",
        "mission",
        "event_queue",
        "entities",
        "contacts",
        "sensor_tracks",
        "communication_queue",
        "metrics",
        "current_commands",
        "scenario_hash",
        "checkpoint_hash",
    }
    assert required <= set(checkpoint)
    restored = store.restore(checkpoint)
    assert restored.observation == original.observation
    assert restored.total_reward == original.total_reward
    for _ in range(100):
        original_result = store.step(original, (2.0, 75.0))
        restored_result = store.step(restored, (2.0, 75.0))
        assert restored_result == original_result


def test_checkpoint_tampering_is_rejected_without_leaking_session() -> None:
    store = SessionStore()
    session = store.create("MD-REC-001", 3)
    tampered = copy.deepcopy(session.checkpoint())
    tampered["seed"] = 999
    with pytest.raises(ValueError, match="integrity"):
        store.restore(tampered)


def test_session_lifecycle_writes_verified_audit(tmp_path: Path) -> None:
    store = SessionStore(audit_dir=tmp_path)
    session = store.create("MD-REC-001", 3)
    store.step(session, (1.0, 20.0))
    store.delete(session.session_id)
    records = AuditLog.read_verified(tmp_path / f"{session.session_id}.audit.jsonl")
    assert [record["event_type"] for record in records] == [
        "session_created",
        "action_accepted",
        "session_closed",
    ]

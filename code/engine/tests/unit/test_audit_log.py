"""Audit hash-chain integrity tests."""

import json
from pathlib import Path

import pytest
from openmdbench.replay.audit import GENESIS_HASH, AuditLog


def test_audit_jsonl_sequence_and_hash_chain(tmp_path: Path) -> None:
    path = tmp_path / "session.audit.jsonl"
    log = AuditLog(path)
    first = log.append("session_created", {"seed": 7})
    second = log.append("action_accepted", {"timestamp": 0})
    assert first["previous_hash"] == GENESIS_HASH
    assert second["previous_hash"] == first["record_hash"]
    assert [record["sequence"] for record in AuditLog.read_verified(path)] == [0, 1]


def test_audit_tampering_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "session.audit.jsonl"
    AuditLog(path).append("metric", {"score": 0.5})
    record = json.loads(path.read_text(encoding="utf-8"))
    record["payload"]["score"] = 1.0
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        AuditLog.read_verified(path)

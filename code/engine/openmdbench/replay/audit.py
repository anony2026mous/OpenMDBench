"""Append-only JSONL audit records protected by a SHA-256 hash chain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GENESIS_HASH = "sha256:" + "0" * 64


def _digest(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


class AuditLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.sequence = 0
        self.previous_hash = GENESIS_HASH
        if self.path.exists() and self.path.stat().st_size:
            records = self.read_verified(self.path)
            self.sequence = int(records[-1]["sequence"]) + 1
            self.previous_hash = str(records[-1]["record_hash"])

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "sequence": self.sequence,
            "previous_hash": self.previous_hash,
            "event_type": event_type,
            "payload": payload,
        }
        record = {**body, "record_hash": _digest(body)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        self.sequence += 1
        self.previous_hash = str(record["record_hash"])
        return record

    @staticmethod
    def read_verified(path: str | Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        previous_hash = GENESIS_HASH
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        for expected_sequence, line in enumerate(lines):
            record: dict[str, Any] = json.loads(line)
            claimed_hash = record.pop("record_hash", None)
            if record.get("sequence") != expected_sequence:
                raise ValueError("audit sequence mismatch")
            if record.get("previous_hash") != previous_hash:
                raise ValueError("audit previous hash mismatch")
            actual_hash = _digest(record)
            if claimed_hash != actual_hash:
                raise ValueError("audit record hash mismatch")
            record["record_hash"] = claimed_hash
            records.append(record)
            previous_hash = actual_hash
        return records

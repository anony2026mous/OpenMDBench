"""Replay path and hostile JSON inputs cannot bypass validation."""

from pathlib import Path

import pytest
from openmdbench.replay import ReplayFormatError, ReplayReader


def test_replay_rejects_oversized_nesting_and_unknown_version(tmp_path: Path) -> None:
    malicious = tmp_path / "malicious.jsonl"
    malicious.write_text("[" * 2_000 + "]" * 2_000, encoding="utf-8")
    with pytest.raises(ReplayFormatError, match="line 1"):
        ReplayReader(malicious)

    unknown = tmp_path / "unknown.jsonl"
    unknown.write_text('{"record_type":"metadata","schema_version":"999.0"}\n', encoding="utf-8")
    with pytest.raises(ReplayFormatError, match="schema_version"):
        ReplayReader(unknown)

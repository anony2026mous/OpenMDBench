"""Headless replay CLI smoke test."""

import subprocess
import sys
from pathlib import Path

from openmdbench.api.sessions import SessionStore


def test_replay_cli_exports_png(tmp_path: Path) -> None:
    store = SessionStore(replay_dir=tmp_path)
    session = store.create("MD-REC-001", 7)
    store.step(session, (1.0, 45.0))
    store.delete(session.session_id)
    replay = tmp_path / f"{session.session_id}.replay.jsonl"
    output = tmp_path / "smoke.png"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openmdbench.cli",
            "replay",
            str(replay),
            "--headless",
            "--view",
            "blue",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_bytes().startswith(b"\x89PNG")

"""Replay's import boundary must stay independent of the simulation kernel."""

from __future__ import annotations

import subprocess
import sys


def test_replay_module_does_not_import_environment_or_native_kernel() -> None:
    code = (
        "import sys; import openmdbench.runners.replay; "
        "assert 'openmdbench.envs' not in sys.modules; "
        "assert 'taichi' not in sys.modules"
    )
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and constant source
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    assert completed.returncode == 0, completed.stderr

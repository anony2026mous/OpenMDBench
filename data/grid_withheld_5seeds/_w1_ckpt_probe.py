"""Locate the exact condition that fails MD-AD-006's checkpoint integrity check.

Read-only probe: builds the session, steps a few ticks, then asks for the world
checkpoint.  ``CheckpointErrorV2`` wraps the original ``ValueError`` raised by
``MissionScoringCheckpointV2.validate_integrity``; the inner traceback's last
frame inside ``missions/engine_v2.py`` is the failing condition.
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))

from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")
TICKS = int(os.environ.get("PROBE_TICKS", "3"))


def main() -> int:
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.ckpt", seed=7)
    session.load().start()
    for _ in range(TICKS):
        session.step(operation_id=f"audit.ckpt.{session.world_view.tick:08d}",
                     expected_tick=session.world_view.tick)
    try:
        session.world_view.checkpoint()
        print("checkpoint OK")
    except Exception as error:  # noqa: BLE001
        print(f"checkpoint FAILED: {type(error).__name__}: {error}")
        cause = error.__cause__ or error.__context__
        seen = 0
        while cause is not None and seen < 6:
            tb = cause.__traceback__
            frames = [f for f in traceback.extract_tb(tb)
                      if f.filename.endswith(("engine_v2.py", "checkpoint_v2.py"))]
            print(f"  cause[{seen}] {type(cause).__name__}: {cause}")
            for frame in frames[-3:]:
                print(f"      {Path(frame.filename).name}:{frame.lineno}  {frame.line}")
            cause = cause.__cause__ or cause.__context__
            seen += 1
    session.stop()
    session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

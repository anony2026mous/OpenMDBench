"""Print the full chained cause of a session-construction failure.

Usage:
    python _w1_session_error.py [PUBLIC_ID]

``run_episode`` and the smoke test only report the outermost code, which for a
world-building failure hides the real reason inside ``__cause__``.  This probe
unwinds the chain and prints every level, including ``NativeDynamicsErrorV2``'s
structured ``code`` / ``path`` / ``value`` / ``reason`` fields.

Windows note: the session body lives inside ``main()`` behind the
``__name__ == "__main__"`` guard, because the MMG solver runs in a
``multiprocessing`` child and ``spawn`` re-imports ``__main__`` there.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))


def main(public_id: str) -> int:
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    try:
        session = create_formal_session_v2(public_id, session_id="audit.error", seed=7)
        session.load().start()
    except Exception as error:  # noqa: BLE001 - the whole point is to report it
        depth = 0
        current: BaseException | None = error
        while current is not None and depth < 12:
            print(f"--- level {depth}: {type(current).__name__}")
            print(f"    str    : {current}")
            for attribute in ("code", "path", "value", "reason", "suggestion"):
                if hasattr(current, attribute):
                    print(f"    {attribute:<7}: {getattr(current, attribute)!r}")
            current = current.__cause__ or current.__context__
            depth += 1
        return 1

    print("session constructed successfully")
    print(f"entities = {len(session.world_view.entities_stable())}")
    session.stop()
    session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "IE-08-ISLAND-STRIKE"))

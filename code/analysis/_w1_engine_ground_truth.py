"""Ask the engine whether an UNSPAWNED intruder counts toward `count <= 0`.

`rule.intruders-destroyed` selects intruders in {active, scheduled, degraded} and
fires when the count is <= 0.  If a wave that has not spawned yet is reported as
`scheduled` and therefore counts, the rule can only fire after the last wave has
spawned.  If instead unspawned waves are absent from the selection evidence, the
rule fires as soon as the CURRENTLY SPAWNED intruders die, and episode length
becomes an arm-controlled quantity the analysis must handle explicitly.

No guessing: build the real session and read the real snapshot.  The whole thing
lives under `main()` because the engine spawns a multiprocessing worker (sim2sea
MMG), which on Windows requires the __main__ guard.
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Code\source-code\openmd\source-code\source_codes")
EVAL = Path(r"C:\Code\source-code\openmd\code\eval")
os.environ.setdefault("OPENMDBENCH_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL))


def main() -> int:
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    scen = sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET"
    ticks = [int(x) for x in sys.argv[2:]] or [0]

    print("=" * 100)
    print(f"ENGINE GROUND TRUTH   scenario={scen}   probe ticks={ticks}")
    print("=" * 100)

    session = create_formal_session_v2(scen, session_id="probe.terminal.0", seed=7)
    session.load().start()
    wv = session.world_view

    entities = list(wv.entities_stable())
    intruders = [e for e in entities if "intruder" in tuple(getattr(e, "tags", ()) or ())]
    print(f"\n  tick {wv.tick}: {len(entities)} entities, "
          f"{len(intruders)} intruder-tagged")
    for e in entities:
        tags = tuple(getattr(e, "tags", ()) or ())
        mark = "  <== INTRUDER" if "intruder" in tags else ""
        print(f"    {e.id:<34} lifecycle={str(getattr(e, 'lifecycle', '?')):<10} "
              f"tags={tags}{mark}")

    for t in ticks:
        print(f"\n--- mission fact snapshot, tick {t} ---")
        snap = None
        for name in ("mission_fact_snapshot", "fact_snapshot"):
            fn = getattr(wv, name, None)
            if callable(fn):
                try:
                    snap = fn(tick=t)
                    print(f"    via world_view.{name}")
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"    world_view.{name} raised {type(exc).__name__}: {exc}")
        if snap is None:
            try:
                cp = wv.checkpoint()
            except Exception as exc:  # noqa: BLE001
                print(f"    checkpoint() raised {exc}")
                continue
            ms = getattr(cp, "mission_scoring_checkpoint", None)
            print(f"    fallback: checkpoint mission payload = {type(ms).__name__}")
            for attr in ("selection_evidence", "entity_states", "mission_states"):
                v = getattr(ms, attr, None)
                n = len(v) if hasattr(v, "__len__") else "n/a"
                print(f"      {attr}: {type(v).__name__} len={n}")
            continue

        ev = tuple(getattr(snap, "selection_evidence", ()) or ())
        intr = [r for r in ev if "intruder" in tuple(getattr(r, "tags", ()) or ())]
        cnt = Counter(str(getattr(r, "lifecycle", "?")) for r in intr)
        print(f"    selection_evidence rows={len(ev)}  intruder rows={len(intr)}")
        print(f"    intruder lifecycle census: {dict(cnt)}")
        for r in intr:
            print(f"      {getattr(r, 'entity_id', '?'):<34} "
                  f"lifecycle={getattr(r, 'lifecycle', '?')}")
        alive = sum(v for k, v in cnt.items() if k in ("scheduled", "active", "degraded"))
        print(f"    alive per rule selector {('scheduled','active','degraded')}: {alive}")
        print(f"    => 'count <= 0' would fire at this tick: {alive <= 0}")

    session.stop()
    session.close()
    print("\n  done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

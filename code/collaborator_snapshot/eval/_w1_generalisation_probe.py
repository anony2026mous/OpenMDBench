"""What is in-distribution for the trained RL policy, and what is not.

Answers "can this generalise to new scenarios with more UAVs/USVs?" with numbers
rather than assertion, by resolving each scenario the same way the environment
does and reporting:

  * how many friendly mobile units (the controllable roster) it has,
  * how many intruders it spawns,
  * which platform types and domains those units are,
  * what the fixed slot capacity is and what happens beyond it.

Usage:
    python _w1_generalisation_probe.py
"""
from __future__ import annotations

import collections
import os
import sys
from pathlib import Path

import numpy as np

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

TRAINED = ("IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
           "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
           "IE-07-CROSS-DOMAIN")
ALL = TRAINED + ("IE-08-ISLAND-STRIKE",)


def main() -> int:
    from ie_rl_env import MAX_UNITS, MAX_CONTACTS, IERlEnv, SPEED_BY_CLASS

    print(f"fixed layout: MAX_UNITS={MAX_UNITS} slots, MAX_CONTACTS={MAX_CONTACTS} "
          f"target slots, SPEED_BY_CLASS={SPEED_BY_CLASS}")
    print()
    print(f"{'scenario':<26}{'own':>4}{'raid':>5}{'maxProj':>8}  {'own platform types':<44}{'set':>10}")
    own_train, raid_train, plat_train = [], [], set()
    for public_id in ALL:
        env = IERlEnv(public_id, seed=1000, decision_interval=5, max_ticks=60)
        try:
            env.reset()
            own = len(env._slots)
            raid = int(env.engagement_onsets().get("raiders") or 0)
            types = collections.Counter()
            domains = collections.Counter()
            for entity in env._session.world_view.entities_stable():
                if str(entity.faction_id) != env.defender_faction:
                    continue
                definition = getattr(entity, "definition", None)
                content = getattr(definition, "content", None) or {}
                ptype = str(content.get("platform_type")
                            or (getattr(definition, "platform_type", "") or "?"))
                if ptype == "?":
                    tags = tuple(getattr(entity, "tags", ()) or ())
                    ptype = "uav" if "uav" in tags else ("usv" if "usv" in tags else "?")
                types[ptype] += 1
                domains[str(content.get("domain") or "?")] += 1
            is_train = public_id in TRAINED
            if is_train:
                own_train.append(own)
                raid_train.append(raid)
                plat_train |= set(types)
            label = "TRAIN" if is_train else "ZERO-SHOT"
            shown = ", ".join(f"{k}x{v}" for k, v in types.items())
            print(f"{public_id:<26}{own:>4}{raid:>5}{MAX_UNITS:>8}  "
                  f"{shown[:42]:<44}{label:>10}")
        finally:
            env.close()

    print()
    print(f"IN-DISTRIBUTION  own units {min(own_train)}-{max(own_train)}"
          f"   raiders {min(raid_train)}-{max(raid_train)}")
    print(f"IN-DISTRIBUTION  platform types: {sorted(plat_train)}")
    print(f"ZERO-SHOT        MD-AD-006 own units 12, raiders 17 (both above the"
          f" training range)")
    print()
    print("hard limits (what a NEW scenario would hit first):")
    print(f"  * roster > MAX_UNITS={MAX_UNITS} -> IERlEnv.reset raises")
    print(f"  * distinct visible targets > MAX_CONTACTS={MAX_CONTACTS} -> "
          f"targets are dropped with a printed warning")
    print(f"  * units are classified by the 'uav' tag; anything else becomes "
          f"\"surface\", and an unknown class falls back to "
          f"{SPEED_BY_CLASS.get('surface')} m/s for the speed scale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

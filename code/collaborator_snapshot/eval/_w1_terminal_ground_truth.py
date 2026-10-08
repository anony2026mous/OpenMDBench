"""Ground truth for the terminal tick: read the scenario's ACTUAL rule set, then ask
the engine's own fact snapshot how many intruders are alive at tick 0.

The question this answers is not academic.  `rule.intruders-destroyed` fires when
the count of intruders in {scheduled, active, degraded} is zero.  If unspawned
waves count as `scheduled`, the rule cannot fire before the last wave has spawned,
and the observed 66-tick `defender_success` would mean something quite different
from "the arm killed wave 2 early".  Guessing from the episode log is not enough:
read the rule and ask the engine.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

ROOT = Path(r"C:\Code\source-code\openmd\source-code\source_codes")
os.environ.setdefault("OPENMDBENCH_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT))

FORMAL = ROOT / "scenarios" / "formal"

print("=" * 104)
print("TERMINAL-RULE STRUCTURE (read from scenario.rules.termination)")
print("=" * 104)

scen_dir = "ie_01_single_target"
doc = yaml.safe_load((FORMAL / scen_dir / "scenario.yaml").read_text(encoding="utf-8"))
sc = doc["scenario"]
rules = ((sc.get("rules") or {}).get("termination") or [])
print(f"\n  {scen_dir}: {len(rules)} termination rules")
for r in rules:
    rid = r.get("id")
    prio = r.get("priority")
    cond = r.get("condition") or {}
    op = cond.get("operator")
    sel = cond.get("selector") or {}
    params = cond.get("parameters") or {}
    out = r.get("outcome") or {}
    lc = sel.get("include_lifecycle")
    tags = sel.get("tags")
    print(f"\n    {rid}  priority={prio}")
    print(f"      operator={op}  params={params}")
    print(f"      selector tags={tags} factions={sel.get('factions')}")
    print(f"      include_lifecycle={lc}")
    print(f"      -> terminal={out.get('terminal')} result={out.get('result')}")

print("\n" + "=" * 104)
print("ENGINE FACT SNAPSHOT: how many intruders are 'alive' at tick 0?")
print("=" * 104)

try:
    from openmdbench.envs.benchmark import OpenMDBenchEnv  # type: ignore
except Exception as exc:  # noqa: BLE001
    print(f"  import failed: {type(exc).__name__}: {exc}")
    raise SystemExit(1)

env = None
try:
    env = OpenMDBenchEnv(scenario=scen_dir.replace("_", "-").upper())
except Exception as exc:  # noqa: BLE001
    print(f"  env construction with that name failed ({exc}); trying package path")
    try:
        env = OpenMDBenchEnv(scenario_dir=str(FORMAL / scen_dir))
    except Exception as exc2:  # noqa: BLE001
        print(f"  still failed: {type(exc2).__name__}: {exc2}")
        raise SystemExit(1)

sched = getattr(env, "scheduled_entities", None)
print(f"\n  scheduled_entities at t=0: {len(sched) if sched is not None else 'n/a'}")
if sched:
    for it in sched:
        print(f"    {it.entity_id:<28} wave={getattr(it, 'wave_id', '?'):<12} "
              f"tick={getattr(it, 'scheduled_tick', '?')}")

snap = None
for meth in ("mission_fact_snapshot", "fact_snapshot"):
    fn = getattr(env, meth, None)
    if callable(fn):
        try:
            snap = fn(tick=0)
            print(f"\n  snapshot via env.{meth}(tick=0)")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"  env.{meth} raised {type(exc).__name__}: {exc}")

if snap is None:
    world = getattr(env, "world", None) or getattr(env, "_world", None)
    fn = getattr(world, "mission_fact_snapshot", None) if world is not None else None
    if callable(fn):
        try:
            snap = fn(tick=0)
            print("\n  snapshot via world.mission_fact_snapshot(tick=0)")
        except Exception as exc:  # noqa: BLE001
            print(f"  world.mission_fact_snapshot raised {type(exc).__name__}: {exc}")

if snap is None:
    print("\n  could not obtain a fact snapshot; falling back to entity dump")
    world = getattr(env, "world", None) or getattr(env, "_world", None)
    ents = getattr(world, "entities", None) if world is not None else None
    if isinstance(ents, dict):
        for k, v in ents.items():
            if "intruder" in k:
                print(f"    {k:<30} lifecycle={getattr(v, 'lifecycle', '?')} "
                      f"tags={getattr(v, 'tags', '?')}")
else:
    ev = getattr(snap, "selection_evidence", ())
    print(f"\n  selection_evidence rows: {len(ev)}")
    from collections import Counter
    cnt = Counter()
    for row in ev:
        if "intruder" in tuple(getattr(row, "tags", ()) or ()):
            cnt[getattr(row, "lifecycle", "?")] += 1
    print(f"  intruder-tagged rows by lifecycle: {dict(cnt)}")
    alive = sum(v for k, v in cnt.items() if k in ("scheduled", "active", "degraded"))
    print(f"  alive per the rule's selector ({'scheduled','active','degraded'}): {alive}")
    print(f"\n  => rule 'count <= 0' satisfied at tick 0: {alive <= 0}")
    if alive > 0:
        print("     So the rule CANNOT fire at tick 0. The 66-tick episode therefore")
        print("     means every intruder in those lifecycles was gone by tick 66 -")
        print("     including, if present, ones not yet spawned at tick 0.")

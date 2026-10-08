"""Four-seed projection: current phase + the queued fourth seed.

Split into two phases because they are strictly sequential: the queued seed cannot
start until the running grid driver exits (both phases share the same 6-way
concurrency ceiling on the shared LLM endpoint, so they must not overlap).
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")
STATE = RUNS / "_grid_state.json"
ARMS = ("llm", "llm-rl", "pure-llm")
CURRENT_SEEDS = (7, 11, 13)
EXTRA_SEED = 17
SCEN = 14
CONC = 6

done: Counter = Counter()
for p in RUNS.glob("*_n3*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict) or d.get("aborted"):
        continue
    if int(d.get("ticks_run") or 0) <= 0:
        continue
    card = d.get("strategy_scorecard") or {}
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    done[(str(d.get("planner")), int(d.get("seed") or 0))] += 1

state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
per_arm: dict[str, list[float]] = defaultdict(list)
for k, v in state.items():
    if v.get("ok") and v.get("elapsed_s"):
        per_arm[k.split("|")[0]].append(float(v["elapsed_s"]))
mean_of = {a: (st.mean(per_arm[a]) if per_arm.get(a) else 2400.0) for a in ARMS}

print("=" * 88)
print("FOUR-SEED PROJECTION")
print("=" * 88)
print(f"\n  {'arm':<10}" + "".join(f"{'s' + str(s):>8}" for s in CURRENT_SEEDS)
      + f"{'s17':>8}{'total/56':>10}")
for a in ARMS:
    row = "".join(f"{done.get((a, s), 0):>8}" for s in CURRENT_SEEDS)
    print(f"  {a:<10}{row}{done.get((a, EXTRA_SEED), 0):>8}"
          f"{sum(done.get((a, s), 0) for s in CURRENT_SEEDS + (EXTRA_SEED,)):>10}")

# ---- phase 1: finish seeds 7/11/13
p1_cells = 0
p1_serial = 0.0
for a in ARMS:
    n = sum(SCEN - done.get((a, s), 0) for s in CURRENT_SEEDS)
    p1_cells += n
    p1_serial += mean_of[a] * n

# ---- phase 2: the queued fourth seed
p2_cells = 0
p2_serial = 0.0
for a in ARMS:
    n = SCEN - done.get((a, EXTRA_SEED), 0)
    p2_cells += n
    p2_serial += mean_of[a] * n

print("\n--- measured per-episode wall time ---")
for a in ARMS:
    el = per_arm.get(a, [])
    print(f"    {a:<10} n={len(el):>2}  mean {mean_of[a] / 60:5.1f} min")

print("\n--- phase 1: finish seeds 7 / 11 / 13 ---")
print(f"    {p1_cells:>3} episodes   serial {p1_serial / 3600:5.1f} h   "
      f"-> {p1_serial / CONC / 3600:4.1f} h at {CONC}-way")

print(f"\n--- phase 2: queued seed {EXTRA_SEED} (starts only after phase 1 exits) ---")
print(f"    {p2_cells:>3} episodes   serial {p2_serial / 3600:5.1f} h   "
      f"-> {p2_serial / CONC / 3600:4.1f} h at {CONC}-way")

total = (p1_serial + p2_serial) / CONC
print(f"\n  TOTAL REMAINING: {p1_cells + p2_cells} episodes, "
      f"{total / 3600:.1f} h at {CONC}-way")
lo, hi = total / 3600 * 0.85, total / 3600 * 1.2
print(f"  ETA: {lo:.1f}-{hi:.1f} h from now")

import time
print(f"  finish around {time.strftime('%m-%d %H:%M', time.localtime(time.time() + lo * 3600))}"
      f" - {time.strftime('%m-%d %H:%M', time.localtime(time.time() + hi * 3600))}")

print(f"\n  Final dataset: 3 arms x 14 scenarios x 4 seeds = 168 withheld cells")
print(f"  (baselines stay reused from the archive; they are never re-run)")

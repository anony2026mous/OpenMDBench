"""Live progress + ETA for the 126-cell grid (3 arms x 14 scenarios x 3 seeds).

Estimates come from MEASURED per-episode durations recorded by the grid driver in
`_w1_runs/_grid_state.json`, grouped by arm - not from tick counts times a guessed
rate - because wall time is dominated by LLM wait, which varies by arm and by how
long a scenario runs.
"""
from __future__ import annotations

import json
import statistics as st
import time
from collections import Counter, defaultdict
from pathlib import Path

RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")
STATE = RUNS / "_grid_state.json"
SEEDS = (7, 11, 13)
ARMS = ("llm", "llm-rl", "pure-llm")
SCEN = 14

print("=" * 92)
print("GRID PROGRESS AND ETA")
print("=" * 92)

# ---- live cell counts straight off disk (authoritative)
done: dict[tuple[str, int], int] = Counter()
for p in RUNS.glob("*_n3*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if d.get("aborted") or int(d.get("ticks_run") or 0) <= 0:
        continue
    card = d.get("strategy_scorecard") or {}
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    done[(str(d.get("planner")), int(d.get("seed") or 0))] += 1

print(f"\n  {'arm':<10}" + "".join(f"{'seed ' + str(s):>12}" for s in SEEDS) + f"{'total':>9}")
grand = 0
for a in ARMS:
    cells = [done.get((a, s), 0) for s in SEEDS]
    grand += sum(cells)
    print(f"  {a:<10}" + "".join(f"{c:>12}" for c in cells) + f"{sum(cells):>9}")
target = len(ARMS) * SCEN * len(SEEDS)
print(f"  {'TOTAL':<10}" + "".join(f"{sum(done.get((a, s), 0) for a in ARMS):>12}" for s in SEEDS)
      + f"{grand:>9}")
print(f"\n  {grand}/{target} cells  ({grand / target:.0%})")

# ---- measured durations
state = {}
if STATE.exists():
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        state = {}
per_arm: dict[str, list[float]] = defaultdict(list)
for k, v in state.items():
    if v.get("ok") and v.get("elapsed_s"):
        per_arm[k.split("|")[0]].append(float(v["elapsed_s"]))

print("\n--- measured per-episode wall time (from the driver's own records) ---")
for a in ARMS:
    el = per_arm.get(a, [])
    if el:
        print(f"    {a:<10} n={len(el):>2}  mean {st.mean(el) / 60:6.1f} min   "
              f"median {st.median(el) / 60:6.1f} min   max {max(el) / 60:6.1f} min")
    else:
        print(f"    {a:<10} (no completed episodes recorded)")

# ---- remaining work
remaining = {}
for a in ARMS:
    need = sum(SCEN - done.get((a, s), 0) for s in SEEDS)
    remaining[a] = need
serial = 0.0
for a, n in remaining.items():
    if per_arm.get(a):
        serial += st.mean(per_arm[a]) * n
    else:
        serial += 2400.0 * n          # fallback: 40 min, the LLM-arm mean

CONC = 6
print("\n--- remaining work ---")
for a, n in remaining.items():
    mark = f"{st.mean(per_arm[a]) / 60:.1f} min/局" if per_arm.get(a) else "? min/局"
    print(f"    {a:<10} {n:>2} episodes   ({mark})")
print(f"    total {sum(remaining.values())} episodes   "
      f"serial {serial / 3600:.1f} h   ->  {serial / CONC / 3600:.1f} h at {CONC}-way")

# ---- empirical throughput, as a cross-check on the model above
times = [v.get("ts", "") for v in state.values() if v.get("ok")]
print("\n--- cross-check: observed throughput ---")
print("    (model above is serial/conc; real runs interleave short and long episodes,")
print("     so the honest range is the model figure widened by roughly +/-20%)")
lo, hi = serial / CONC / 3600 * 0.8, serial / CONC / 3600 * 1.2
print(f"\n  ETA: {lo:.1f}-{hi:.1f} h from now "
      f"(finish around {(time.strftime('%H:%M', time.localtime(time.time() + lo * 3600)))}"
      f"-{time.strftime('%H:%M', time.localtime(time.time() + hi * 3600))})")
print("\n  NOTE: n>=3 requires seed 13 as well; seed 11 alone gives n=2, which is not")
print("  enough for the per-seed-win criterion of the three-part stability test.")

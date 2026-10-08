"""What actually drives episode wall-clock? ticks, plan calls, or neither?

Needed before touching concurrency: if most episodes end early (~100 ticks), the
batch is far cheaper than the median-based estimate, and the bottleneck may not
be the endpoint at all.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = {"IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"}

rows = []
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if str(d.get("scenario", "")).upper() not in SCEN:
        continue
    pl = str(d.get("planner", "")).lower()
    if pl not in ("llm", "pure-llm", "purellm"):
        continue
    el = d.get("elapsed_seconds")
    tk = d.get("ticks_run")
    if not isinstance(el, (int, float)) or not isinstance(tk, int) or tk <= 0:
        continue
    de = d.get("defender") or {}
    calls = de.get("llm_calls") if isinstance(de, dict) else None
    rows.append({"planner": pl, "elapsed": float(el), "ticks": tk,
                 "calls": calls if isinstance(calls, int) else None,
                 "scen": str(d.get("scenario")).upper()})

print(f"episodes with wall-clock record: {len(rows)}")
for pl in ("llm", "pure-llm"):
    v = [r for r in rows if r["planner"] == pl]
    if not v:
        continue
    el = sorted(r["elapsed"] for r in v)
    tk = sorted(r["ticks"] for r in v)
    print(f"\n=== {pl} (n={len(v)}) ===")
    print(f"  elapsed  p10={el[len(el)//10]:>7.0f}s  median={st.median(el):>7.0f}s  "
          f"p90={el[int(len(el)*0.9)]:>7.0f}s  max={max(el):>7.0f}s")
    print(f"  ticks    p10={tk[len(tk)//10]:>7d}   median={st.median(tk):>7.0f}   "
          f"p90={tk[int(len(tk)*0.9)]:>7d}   max={max(tk):>7d}")
    q = [r for r in v if r["calls"]]
    if q:
        print(f"  llm_calls p10={sorted(r['calls'] for r in q)[len(q)//10]:>5d}  "
              f"median={st.median([r['calls'] for r in q]):>6.0f}")

print()
print("=== elapsed vs ticks correlation (llm arms) ===")
v = [r for r in rows if r["planner"] == "llm"]
if len(v) > 5:
    xs = [r["ticks"] for r in v]
    ys = [r["elapsed"] for r in v]
    mx, my = st.mean(xs), st.mean(ys)
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = sum((a - mx) ** 2 for a in xs) ** 0.5
    sy = sum((b - my) ** 2 for b in ys) ** 0.5
    print(f"  Pearson r = {cov / (sx * sy):.3f}   n={len(v)}")
    # seconds per tick
    ratios = [r["elapsed"] / r["ticks"] for r in v if r["ticks"] > 20]
    print(f"  elapsed/ticks: median={st.median(ratios):.2f} s/tick  "
          f"i.e. ~{st.median(ratios) * 10:.0f} s per 10-tick plan cycle")

print()
print("=== projected batch time under the REAL tick distribution ===")
v = [r for r in rows if r["planner"] == "llm"]
if v:
    per_tick = st.median([r["elapsed"] / r["ticks"] for r in v if r["ticks"] > 20])
    med_ticks = st.median([r["ticks"] for r in v])
    print(f"  median ticks for llm arms = {med_ticks:.0f}")
    print(f"  => projected median episode = {per_tick * med_ticks:.0f}s "
          f"(vs median observed {st.median([r['elapsed'] for r in v]):.0f}s)")
    print(f"  55 episodes x {per_tick * med_ticks:.0f}s = {55 * per_tick * med_ticks / 3600:.2f} h serial")

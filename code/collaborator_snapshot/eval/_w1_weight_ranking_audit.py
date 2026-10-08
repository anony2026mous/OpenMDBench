"""Is v9 actually the best weight? Compare every checkpoint on equal footing.

Read-only. For each eval scenario, averages each `llm-rl` checkpoint's score and
reports the hold-rate, so the "v9 is best" question is answered from data.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}

# (scenario, ckpt) -> [scores]
data: dict[tuple[str, str], list[float]] = defaultdict(list)
seeds: dict[tuple[str, str], set[int]] = defaultdict(set)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json"):
        continue
    try:
        with open(os.path.join(RUNS, fn), encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper().strip()
    sc = ALIAS.get(sc, sc)
    if sc not in SCENARIOS:
        continue
    if str(d.get("planner", "")).lower() not in ("llm-rl", "llmrl", "rl"):
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    theta = str(ex.get("theta") or "")
    name = os.path.basename(theta)
    ck = tag or (name[len("theta_"):-len(".npz")] if name.startswith("theta_") else "")
    if not ck or "llm" not in ck:
        continue
    ss = d.get("score_state") or {}
    v = ss.get("score.facility-integrity")
    if v is None:
        continue
    data[(sc, ck)].append(float(v))
    sd = d.get("seed")
    if isinstance(sd, int):
        seeds[(sc, ck)].add(sd)

cks = sorted({c for _, c in data})
print("checkpoints found on the llm-rl arm:", ", ".join(cks))
print()

# per-scenario means
hdr = f"{'scenario':<26}" + "".join(f"{c.replace('arm5_',''):>16}" for c in cks)
print(hdr)
print("-" * len(hdr))
per_ck_scores: dict[str, list[float]] = defaultdict(list)
for sc in SCENARIOS:
    row = f"{sc:<26}"
    for c in cks:
        vals = data.get((sc, c), [])
        if vals:
            m = st.mean(vals)
            per_ck_scores[c].append(m)
            row += f"{m:>10.4f}({len(seeds[(sc, c)])}s)"
        else:
            row += f"{'-':>16}"
    print(row)

print()
print("=== summary per checkpoint (scenarios where it has data) ===")
for c in cks:
    vals = per_ck_scores.get(c, [])
    if not vals:
        continue
    hold = sum(1 for v in vals if v >= 0.5)
    print(f"  {c:<26} scenarios={len(vals):>2}  mean={st.mean(vals):.4f}  "
          f"median={st.median(vals):.4f}  hold(>=0.5)={hold}/{len(vals)}")

# the six discriminating scenarios the audit singled out
SIX = ["IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
       "IE-08-ISLAND-STRIKE", "IE-11-DECOY-SCREEN", "IE-13-DEEP-STRIKE"]
print()
print("=== the six discriminating scenarios only ===")
for c in cks:
    vals = [st.mean(data[(sc, c)]) for sc in SIX if data.get((sc, c))]
    if vals:
        print(f"  {c:<26} n={len(vals)}  mean={st.mean(vals):.4f}")

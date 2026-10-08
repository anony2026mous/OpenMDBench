"""Measure the ACTUAL impact of the three defects, from recorded episodes.

Defect A: prompt says speed_range "0-45" while the envelope caps at 43 (IE-01..07,
          09..14) or 40 (IE-08).
   -> measurable: did the LLM ever emit speed_mps > the real cap? If never, the
      wrong bound never bound anything.
Defect B: fallback 15.0 vs ExecutorConfigV2.default_speed_mps 12.0.
   -> measurable: how often does _speed_limit fall through to the default? That
      requires the platform kind and every tag to miss speed_max_by_tag.
Defect C: few-shot examples show speed_mps 40.
   -> not directly measurable, but we can check the distribution of emitted speeds
      to see whether the model clusters on 40.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
LOGS = os.path.join(RUNS, "logs")

print("=" * 92)
print("Defect A: did the LLM ever emit a speed above the real envelope?")
print("=" * 92)
speeds = []
n_lines = 0
for lg in glob.glob(os.path.join(LOGS, "*.jsonl")):
    for line in open(lg, encoding="utf-8", errors="ignore"):
        if "speed_mps" not in line:
            continue
        n_lines += 1
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        # look for emitted speeds in any nested structure
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "speed_mps" and isinstance(v, (int, float)):
                        speeds.append(float(v))
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(e)

print(f"  log lines mentioning speed_mps : {n_lines}")
print(f"  numeric speed_mps values found : {len(speeds)}")
if speeds:
    over43 = sum(1 for s in speeds if s > 43.0)
    over40 = sum(1 for s in speeds if s > 40.0)
    print(f"  distribution: min={min(speeds):.1f} median={st.median(speeds):.1f} "
          f"max={max(speeds):.1f}")
    print(f"  values > 43 (cap in most IE scenarios) : {over43}  "
          f"({over43 / len(speeds):.2%})")
    print(f"  values > 40 (cap in IE-08)             : {over40}  "
          f"({over40 / len(speeds):.2%})")
    c = collections.Counter(round(s) for s in speeds)
    print("  most common emitted speeds:", c.most_common(8))

print()
print("=" * 92)
print("Defect B: how often does _speed_limit fall through to its hardcoded default?")
print("=" * 92)
# speed_max_by_tag covers uav/usv/interceptor/picket. Enumerate which entity tags
# actually appear in the defender roster of the 14 IE scenarios.
FORMAL = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"
import yaml  # noqa: E402

tag_counter = collections.Counter()
for d in sorted(os.listdir(FORMAL)):
    sp = os.path.join(FORMAL, d, "scenario.yaml")
    if not os.path.exists(sp):
        continue
    y = yaml.safe_load(open(sp, encoding="utf-8")) or {}
    for ent in ((y.get("scenario") or {}).get("entities") or []):
        for t in (ent.get("tags") or ()):
            tag_counter[str(t)] += 1
covered = {"uav", "usv", "interceptor", "picket"}
uncovered = {t: n for t, n in tag_counter.items() if t not in covered}
print(f"  tags seen across IE scenarios : {len(tag_counter)}")
print(f"  covered by speed_max_by_tag   : {sorted(t for t in tag_counter if t in covered)}")
print(f"  NOT covered (would hit 15.0)  : {sorted(uncovered)}")
print("  => the hardcoded 15.0 is reachable only for entities whose platform kind and")
print("     every tag miss the table. Tally of such tags above shows whether it bites.")

print()
print("=" * 92)
print("Defect C: does the model cluster on the few-shot example value 40?")
print("=" * 92)
if speeds:
    c = collections.Counter(round(s) for s in speeds)
    tot = sum(c.values())
    for val in (40, 43, 45, 8, 10, 12, 15):
        print(f"  speed≈{val:<3} appears {c.get(val, 0):>6} times "
              f"({c.get(val, 0) / tot:.2%})")

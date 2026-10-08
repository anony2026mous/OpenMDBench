"""How much work is lost if the machine is shut down now?

Facts needed:
  * completed episodes are already on disk -> safe
  * in-flight episodes: is a checkpoint available (resume) or not (restart)?
  * what still has not started
"""
from __future__ import annotations

import glob
import json
import os
import time

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
CK = os.path.join(RUNS, "checkpoints")
LOGS = os.path.join(RUNS, "logs")

print("=== completed episodes on disk (SAFE) ===")
for pat, lab in (("*_top.json", "llm-rule (tag=top)"),
                 ("*_envfix*.json", "pure-llm (tag=envfix)"),
                 ("*_topb*.json", "llm-rl  (tag=topb)")):
    fs = glob.glob(os.path.join(RUNS, pat))
    print(f"  {lab:<26} {len(fs):>3} files")

print()
print("=== checkpoints available for resume ===")
cks = sorted(glob.glob(os.path.join(CK, "*.ckpt.json")))
print(f"  {len(cks)} checkpoint files")
recent = sorted(cks, key=os.path.getmtime, reverse=True)[:14]
for c in recent:
    st = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(c)))
    print(f"    {os.path.basename(c):<42} {os.path.getsize(c)/2**20:>7.1f} MB  written {st}")

print()
print("=== in-flight episodes: progress and whether a checkpoint exists ===")
for lg in sorted(glob.glob(os.path.join(LOGS, "*_topb*.jsonl")), key=os.path.getmtime, reverse=True)[:4]:
    stem = os.path.basename(lg)[:-6]          # strip .jsonl
    # checkpoint naming: <SCENARIO-ID>_<seed>.ckpt.json
    res = os.path.join(RUNS, stem + ".json")
    done = os.path.exists(res)
    lines = open(lg, encoding="utf-8", errors="ignore").read().splitlines()
    if not lines:
        continue
    last = lines[-1]
    tick = json.loads(last).get("tick") if last.startswith("{") else None
    first_ts = json.loads(lines[0]).get("ts")
    last_ts = json.loads(last).get("ts")
    run_s = (last_ts - first_ts) if (first_ts and last_ts) else 0
    print(f"\n  {stem}")
    print(f"    result file exists : {done}")
    print(f"    last event tick    : {tick}")
    print(f"    running for        : {run_s/60:.1f} min")

print()
print("=== what has NOT started (seed 13 batch) ===")
pending = []
for sc in ("IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-04-COMBINED-ARMS",
           "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED", "IE-07-CROSS-DOMAIN",
           "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER",
           "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE",
           "IE-14-SATURATION-THREE-WAVE"):
    p = os.path.join(RUNS, f"ie_llmrl_{sc.lower()}_topb_s13.json")
    if not os.path.exists(p):
        pending.append(sc)
print(f"  {len(pending)} episodes of llm-rl seed 13 not started: "
      f"{', '.join(s.replace('IE-','') for s in pending)}")

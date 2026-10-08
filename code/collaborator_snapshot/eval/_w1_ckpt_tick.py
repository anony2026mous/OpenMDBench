"""Read the tick at which each in-flight episode's checkpoint was taken."""
from __future__ import annotations

import json
import os

CK = r"C:\Code\source-code\openmd\code\eval\_w1_runs\checkpoints"

for n in ("IE-08-ISLAND-STRIKE_11.ckpt.json", "IE-13-DEEP-STRIKE_11.ckpt.json"):
    p = os.path.join(CK, n)
    if not os.path.exists(p):
        print(n, "not found")
        continue
    d = json.load(open(p, encoding="utf-8"))
    print(f"=== {n} ===")
    for k in ("session_id", "seed", "resolved_hash", "world_checkpoint_hash",
              "runner_mode", "physics_dt_seconds"):
        if k in d:
            print(f"   {k:<24} = {str(d[k])[:64]}")
    wc = d.get("world_checkpoint") or {}
    tk = None
    for k in ("tick", "world_tick", "current_tick"):
        if k in wc:
            tk = wc[k]
            break
    if tk is None and "world_tick_ledger" in wc:
        tk = len(wc["world_tick_ledger"])
    print(f"   checkpoint tick          = {tk}")
    sid = str(d.get("session_id") or "")
    print(f"   session_id implies seed  = {sid}")

"""Show the layer breakdown that produces the 0.66 vs 0.90 gap on IE-01."""
from __future__ import annotations

import json
import os

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

for fn in ("ie_llmrl_ie-01-single-target_v12a.json",
           "ie_llmrl_ie-01-single-target_v9_paired_final.json"):
    p = os.path.join(RUNS, fn)
    if not os.path.exists(p):
        print("missing", fn)
        continue
    card = (json.load(open(p, encoding="utf-8")).get("strategy_scorecard") or {})
    print("=" * 84)
    print(fn, " defender_score =", card.get("defender_score"),
          " scored_weight =", card.get("scored_weight"))
    print("=" * 84)
    layers = card.get("layers") or {}
    lw = card.get("layer_weights") or {}
    print(f"  {'layer':<12}{'value':>10}{'weight':>9}   contribution")
    for name in sorted(layers):
        v = layers[name]
        w = lw.get(name, 0)
        if isinstance(v, (int, float)) and isinstance(w, (int, float)):
            print(f"  {name:<12}{v:>10.4f}{w:>9.2f}   {v * w:.4f}")
    print()
    for key in ("facilities", "depth", "exchange"):
        blk = card.get(key)
        if isinstance(blk, dict):
            print(f"  -- {key} detail --")
            for k, v in blk.items():
                if not isinstance(v, (dict, list)):
                    print(f"     {k:<28} {v}")
            print()
    tl = card.get("terminal")
    if isinstance(tl, dict):
        print("  -- terminal --")
        for k, v in tl.items():
            if not isinstance(v, (dict, list)):
                print(f"     {k:<28} {v}")
    print()

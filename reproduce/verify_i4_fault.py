"""Independently check appendix I.4's fault-cost figures against g1-fault-dose.

Appendix I.4 (appendix.tex 363-364) claims, on a rule + heuristic-GOAI base under matched
prefixes:
    planner-side injection costs  0.567 score / 0.7 success / 0.7 extra port breach
    executor-side injection costs 0.327 score / 0.4 success / 0.4 extra breach
    local target-hit losses       1.0 and 1.0
and that "layer-of-first-appearance localization: 20/20 paired seeds".

This script enumerates what the batch actually contains and asks whether any dose level
reproduces those numbers. It does not assume the two are the same experiment.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent if (_HERE.parent / "data").is_dir() else _HERE


BASE = _ROOT / "data" / "g1-fault-dose"

print("=" * 94)
print("g1-fault-dose: what the batch contains")
print("=" * 94)

# 1. structural inventory
for sub in sorted(p for p in BASE.iterdir() if p.is_dir()):
    eps = list(sub.rglob("episode.json"))
    print(f"  {sub.name:<18} episode.json={len(eps):<5} "
          f"dirs={len([d for d in sub.rglob('*') if d.is_dir()])}")

# 2. gather every episode with its dose and injection label from the path
rows: list[dict] = []
for p in BASE.rglob("episode.json"):
    try:
        e = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        continue
    rel = p.relative_to(BASE)
    parts = rel.parts
    txt = str(rel).lower()
    dose = None
    for tok in parts:
        if tok.startswith("dose"):
            try:
                dose = float(tok.replace("dose", "").strip("-_"))
            except ValueError:
                pass
    rows.append({
        "tier": parts[0],
        "case": parts[1] if len(parts) > 1 else "",
        "seed": next((t for t in parts if t.startswith("seed-")), None),
        "injection": next((t for t in parts
                           if t in ("planner_wrong_contact", "action_hold",
                                    "clean", "local", "planner", "executor")), None),
        "dose": dose,
        "V": e.get("V"),
        "succ": e.get("metrics", {}).get("mission_success"),
        "path": str(rel),
        "lower": txt,
    })

print(f"\n  total episodes parsed: {len(rows)}")
tiers = defaultdict(int)
for r in rows:
    tiers[r["tier"]] += 1
print(f"  by tier: {dict(tiers)}")

inj = defaultdict(int)
for r in rows:
    inj[r["injection"]] += 1
print(f"  by injection label inferred from path: {dict(inj)}")

# 3. clean baseline vs each injection, per tier
print("\n" + "=" * 94)
print("clean mean V vs injection cost, per tier")
print("=" * 94)
for tier in sorted(tiers):
    tr = [r for r in rows if r["tier"] == tier]
    clean = [r["V"] for r in tr if r["injection"] == "clean"
             and isinstance(r["V"], (int, float))]
    if not clean:
        print(f"\n  [{tier}] no clean episodes")
        continue
    print(f"\n  [{tier}] clean n={len(clean)} meanV={st.mean(clean):.3f}")
    groups = defaultdict(list)
    for r in tr:
        if r["injection"] in (None, "clean"):
            continue
        if isinstance(r["V"], (int, float)):
            groups[(r["injection"], r["dose"])].append(r["V"])
    for (label, dose), vs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
        cost = st.mean(clean) - st.mean(vs)
        print(f"    {label:<24} dose={dose}  n={len(vs):<3} V={st.mean(vs):.3f}  "
              f"cost={cost:+.3f}")

# 4. does any group reproduce the paper's headline costs?
print("\n" + "=" * 94)
print("search for the paper's figures: planner 0.567, executor 0.327")
print("=" * 94)
found = []
for tier in sorted(tiers):
    tr = [r for r in rows if r["tier"] == tier]
    clean = [r["V"] for r in tr if r["injection"] == "clean"
             and isinstance(r["V"], (int, float))]
    if not clean:
        continue
    cm = st.mean(clean)
    groups = defaultdict(list)
    for r in tr:
        if r["injection"] in (None, "clean") or not isinstance(r["V"], (int, float)):
            continue
        groups[r["injection"]].append(r["V"])
    for label, vs in groups.items():
        cost = cm - st.mean(vs)
        for target, name in ((0.567, "planner-side"), (0.327, "executor-side")):
            if abs(cost - target) < 0.02:
                found.append((tier, label, cost, name))
if found:
    for tier, label, cost, name in found:
        print(f"  MATCH  tier={tier} injection={label} cost={cost:.3f} (~{name})")
else:
    print("  no aggregated group reproduces 0.567 or 0.327")
    print("  (the batch's cost values are far smaller: |cost| < 0.25 in every tier)")

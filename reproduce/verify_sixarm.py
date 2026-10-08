"""Verify the MAIN-TEXT tab:sixarm aggregates against the delivered P1 batch.

main.tex tab:sixarm reports mean composites over 10 paired seeds and the deployment
accounting identity. Appendix I.1 reports the same batch from the per-seed angle. If the
P1 delivery is the source, both must agree with it.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

RAW = Path(r"C:\Code\source-code\release_assets\collaborator_runs"
           r"\e2-delivery-20261003\raw\P1__six_arm__s501-510__main__v1")

# main.tex line 314-319
PAPER_MEAN = {"rule-rule": 0.913, "rl": 0.883, "rule-rl": 0.810,
              "llm-rule": 0.700, "llm-rl": 0.673, "pure-llm": 0.280}
# main.tex line 316-318 identity terms
PAPER_IDENT = {"rule-rl": ("E", -0.103), "llm-rule": ("P", -0.213),
               "llm-rl": ("I", +0.077)}

got: dict[str, list[float]] = {}
succ: dict[str, int] = {}
for p in RAW.rglob("episode.json"):
    e = json.loads(p.read_text(encoding="utf-8"))
    a = e.get("config", {}).get("arm")
    v = e.get("V")
    if not a or not isinstance(v, (int, float)):
        continue
    got.setdefault(a, []).append(float(v))
    if e.get("metrics", {}).get("mission_success") is True:
        succ[a] = succ.get(a, 0) + 1

print("=" * 88)
print("main.tex tab:sixarm  vs  delivered P1 batch (10 paired seeds)")
print("=" * 88)
print(f"  {'stack':<11}{'n':>4}{'mean':>9}{'paper':>9}{'diff':>9}{'succ':>7}{'paper':>7}")
bad = 0
for a, pv in sorted(PAPER_MEAN.items(), key=lambda kv: -kv[1]):
    vs = got.get(a, [])
    if not vs:
        print(f"  {a:<11}  MISSING")
        bad += 1
        continue
    m = st.mean(vs)
    ok = abs(m - pv) <= 0.0005
    if not ok:
        bad += 1
    print(f"  {a:<11}{len(vs):>4}{m:>9.3f}{pv:>9.3f}{m - pv:>+9.3f}"
          f"{succ.get(a, 0):>4}/10{'':>3}{'' if ok else '  DIFFERS'}")

print(f"\n  mean mismatches: {bad}/6")

# Deployment accounting identity: P = V_LR - V_RR, E = V_RM - V_RR, I = synergy
m = {a: st.mean(v) for a, v in got.items() if v}
print("\n  deployment accounting identity (P/E/I):")
Vm = m.get("rule-rule")
for arm, (sym, pv) in PAPER_IDENT.items():
    ov = m.get(arm)
    if Vm is None or ov is None:
        print(f"    {sym}: cannot compute")
        continue
    # E and P are direct differences; I is the residual so that P+E+I == total gain
    if sym == "E":
        calc = ov - Vm
    elif sym == "P":
        calc = ov - Vm
    else:
        calc = (m.get("llm-rl", 0) - Vm) - ((m.get("llm-rule", 0) - Vm)
                                           + (m.get("rule-rl", 0) - Vm))
    print(f"    {sym:<2} computed {calc:+.3f}   paper {pv:+.3f}   "
          f"diff {calc - pv:+.3f}")

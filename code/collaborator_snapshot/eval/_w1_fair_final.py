"""Final comparison for the IE-11 fair-口径 pilot.

Reports, once the runs land:
  1. per-arm withheld scores vs the declared (with-intel) snapshot
  2. the claim test against rule-rule / rl (unaffected by the briefing switch)
  3. attribution: how much came from the briefing vs from the ROE bug fix
  4. a seed-level view so n=1 cells are visible as such
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

# declared (with-intel) snapshot means, IE-11
DECL = {"llm-rule": 0.680, "llm-rl": 0.757, "pure-llm": 0.618,
        "rule-rule": 0.681, "rl": 0.184}
# declared-口径 per-seed detail, for the same scenario
DECL_SEEDS = {
    "llm-rule": [0.699, 0.680, 0.661],
    "pure-llm": [0.752, 0.618, 0.485],
    "llm-rl": [0.628, 0.757, 0.886],
}


def rows(pat):
    out = []
    for p in sorted(glob.glob(os.path.join(RUNS, pat))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        c = d.get("strategy_scorecard") or {}
        if "defender_score" not in c:
            continue
        out.append({"file": os.path.basename(p), "seed": d.get("seed"),
                    "ticks": d.get("ticks_run"),
                    "fires": d.get("total_fires_defender"),
                    "score": float(c["defender_score"])})
    return out


PATS = {
    "llm-rule": "ie_llm_ie-11-decoy-screen_fair*.json",
    "pure-llm": "ie_purellm_ie-11-decoy-screen_fair*.json",
    "llm-rl": "ie_llmrl_ie-11-decoy-screen_fair*.json",
}

print("=" * 88)
print("IE-11  withheld (NO enemy intel)  vs  declared (full intel)")
print("=" * 88)
new = {}
for arm, pat in PATS.items():
    rs = rows(pat)
    new[arm] = rs
    print(f"\n--- {arm} ---")
    if not rs:
        print("    (no episodes yet)")
        continue
    for r in rs:
        print(f"    seed={r['seed']}  ticks={r['ticks']:<5} fires={r['fires']:<3} "
              f"score={r['score']:.4f}")
    sc = [r["score"] for r in rs]
    print(f"    n={len(sc)}  mean={st.mean(sc):.4f}  "
          f"declared={DECL[arm]:.3f}  delta={st.mean(sc) - DECL[arm]:+.4f}")

print()
print("=" * 88)
print("CLAIM TEST: hybrid vs single architectures (baselines unaffected by the switch)")
print("=" * 88)
for arm in ("llm-rule", "llm-rl"):
    rs = new.get(arm) or []
    if len(rs) < 2:
        print(f"  {arm}: n={len(rs)} — not enough to judge")
        continue
    m = st.mean([r["score"] for r in rs])
    for opp in ("rule-rule", "rl"):
        base = DECL[opp]
        verdict = "WIN " if m > base else "LOSE"
        print(f"  {arm:<10} vs {opp:<10} {m:.4f} vs {base:.4f}  "
              f"{verdict} (Δ{m - base:+.4f})  n={len(rs)}")

print()
print("=" * 88)
print("ATTRIBUTION (needs the bugfix-only arm to be complete)")
print("=" * 88)
print("  declared(intel+bug) -> bugfix-only(intel,no bug) -> withheld(no intel,no bug)")
print("  delta1 = bug-fix contribution;   delta2 = effect of removing the intel")
for arm in ("llm-rule", "pure-llm", "llm-rl"):
    rs = new.get(arm) or []
    if len(rs) >= 2:
        m = st.mean([r["score"] for r in rs])
        print(f"    {arm:<10} declared={DECL[arm]:.3f}  withheld={m:.3f}  "
              f"combined effect={m - DECL[arm]:+.3f}  (split needs bugfix-only)")

print()
print("=" * 88)
print("PER-SEED VIEW (n=1 cells are single observations, not arm means)")
print("=" * 88)
for arm in ("llm-rule", "pure-llm", "llm-rl"):
    rs = new.get(arm) or []
    got = {r["seed"]: r["score"] for r in rs}
    print(f"  {arm:<10} declared={DECL_SEEDS[arm]}  withheld={[got.get(s) for s in (7, 11, 13)]}")

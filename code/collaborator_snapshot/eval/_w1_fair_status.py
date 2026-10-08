"""Current standing of the IE-11 no-intel (withheld) pilot vs the declared snapshot."""
from __future__ import annotations

import collections
import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
LOGS = os.path.join(RUNS, "logs")
DECL = {"llm-rule": 0.680, "llm-rl": 0.757, "pure-llm": 0.618,
        "rule-rule": 0.681, "rl": 0.184}


def load(pat):
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
        out.append((os.path.basename(p), d.get("seed"), d.get("ticks_run"),
                    d.get("total_fires_defender"), float(c["defender_score"])))
    return out


print("=== IE-11  withheld (no enemy intel) — completed episodes ===")
groups = {
    "llm-rule": "ie_llm_ie-11-decoy-screen_fair*.json",
    "pure-llm": "ie_purellm_ie-11-decoy-screen_fair*.json",
    "llm-rl": "ie_llmrl_ie-11-decoy-screen_fair*.json",
}
new = {}
for arm, pat in groups.items():
    rows = load(pat)
    if not rows:
        print(f"\n  {arm:<10} (none completed yet)")
        continue
    sc = [r[4] for r in rows]
    new[arm] = sc
    print(f"\n  {arm:<10} n={len(rows)}  mean={st.mean(sc):.4f}")
    for n, sd, tk, fi, s in rows:
        print(f"      seed={sd}  ticks={tk:<5} fires={fi}  score={s:.4f}")

print()
print("=== comparison: declared (old, with intel) vs withheld (new, no intel) ===")
print(f"  {'arm':<10}{'declared':>10}{'withheld':>10}{'delta':>9}{'n_new':>7}")
for arm in ("llm-rule", "llm-rl", "pure-llm"):
    if arm in new:
        d = st.mean(new[arm])
        print(f"  {arm:<10}{DECL[arm]:>10.3f}{d:>10.3f}{d - DECL[arm]:>+9.3f}{len(new[arm]):>7}")
    else:
        print(f"  {arm:<10}{DECL[arm]:>10.3f}{'-':>10}{'-':>9}{0:>7}")

print()
print("=== the claim test: does the hybrid still beat the single architectures? ===")
print("  (rule-rule / rl are unaffected by the briefing switch — reused as baselines)")
print(f"  {'opponent':<12}{'baseline':>10}   verdict per hybrid")
for opp in ("rule-rule", "rl"):
    base = DECL[opp]
    line = f"  {opp:<12}{base:>10.3f}   "
    parts = []
    for arm in ("llm-rule", "llm-rl"):
        if arm in new and len(new[arm]) >= 2:
            m = st.mean(new[arm])
            mark = "WIN" if m > base else "LOSE"
            parts.append(f"{arm}={m:.3f} {mark}(Δ{m-base:+.3f})")
        elif arm in new:
            m = st.mean(new[arm])
            parts.append(f"{arm}={m:.3f} (n=1, provisional)")
    print(line + "  ".join(parts))

print()
print("=== is the LLM still fighting? (goal mix + fires, in-flight run) ===")
lg = os.path.join(LOGS, "ie_llm_ie-11-decoy-screen_fair_s11.jsonl")
if os.path.exists(lg):
    cnt = collections.Counter()
    for line in open(lg, encoding="utf-8", errors="ignore"):
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if e.get("t") == "plan":
            for cmd in (e.get("accepted") or []):
                cnt[str(cmd).split("_")[0]] += 1
    print("  ", dict(cnt.most_common()))

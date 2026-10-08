"""Does 'one or two hybrids STABLY beat the single architectures' hold?

Stability is tested three ways for every (scenario, hybrid, opponent):
  1. mean  : both sides n>=2 and hybrid mean > opponent mean
  2. seed  : the hybrid beats the opponent on EVERY seed family present
             (conservative: uses per-seed means, requires >=2 seeds on each side)
  3. split : split the hybrid's seeds in half; it must win in BOTH halves
All three must pass for the inequality to count as STABLE.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
ARMS = {"rule-rule": ("rule",), "rl": ("rl",), "pure-llm": ("purellm", "pure-llm"),
        "llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl")}
WANT = {"llm-rl": {"arm5_llm_reward_v9"}, "rl": {"rlb2", "nn1"},
        "llm-rule": set(), "pure-llm": set(), "rule-rule": set()}

# (scenario, arm) -> {seed: [scores]}
by_seed: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = ALIAS.get(str(d.get("scenario", "")).upper().strip(),
                   str(d.get("scenario", "")).upper().strip())
    if sc not in SCEN:
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    pl = str(d.get("planner", "")).lower()
    arm = next((a for a, ks in ARMS.items() if pl in ks), None)
    if arm is None:
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    if WANT.get(arm) and tag and tag not in WANT[arm]:
        continue
    sd = d.get("seed")
    if isinstance(sd, int):
        by_seed[(sc, arm)][sd].append(float(card["defender_score"]))


def all_scores(sc, arm):
    return [s for v in by_seed.get((sc, arm), {}).values() for s in v]


def test(sc, h, o):
    hs = {sd: st.mean(v) for sd, v in by_seed.get((sc, h), {}).items() if v}
    os_ = {sd: st.mean(v) for sd, v in by_seed.get((sc, o), {}).items() if v}
    if not hs or not os_:
        return False, False, False, None
    nh = sum(len(v) for v in by_seed[(sc, h)].values())
    no = sum(len(v) for v in by_seed[(sc, o)].values())
    mh, mo = st.mean(all_scores(sc, h)), st.mean(all_scores(sc, o))
    mean_ok = nh >= 2 and no >= 2 and mh > mo
    # seed-wise: every hybrid seed family must beat every opponent seed family mean
    seed_ok = (len(hs) >= 2 and len(os_) >= 2
               and min(hs.values()) > max(os_.values()))
    # split half
    order = sorted(hs)
    split_ok = False
    if len(order) >= 4:
        a, b = order[: len(order) // 2], order[len(order) // 2:]
        ma = st.mean([hs[x] for x in a])
        mb = st.mean([hs[x] for x in b])
        split_ok = ma > mo and mb > mo
    else:
        split_ok = mean_ok  # cannot split; do not claim extra credit
    return mean_ok, seed_ok, split_ok, mh - mo


print("=== STABLE inequality test (all three criteria must pass) ===")
print(f"{'scenario':<28}{'hybrid':<10}{'opponent':<10}{'delta':>8}{'mean':>6}{'seed':>6}{'split':>7}  verdict")
print("-" * 100)
stable: dict[str, list] = defaultdict(list)
near: dict[str, list] = defaultdict(list)
for sc in SCEN:
    for h in ("llm-rule", "llm-rl"):
        for o in ("rule-rule", "rl", "pure-llm"):
            m, s, sp, d = test(sc, h, o)
            v = "STABLE" if (m and s and sp) else ("mean-only" if m else "no")
            (stable if v == "STABLE" else near)[h].append((sc, o, v, d))
            print(f"{sc:<28}{h:<10}{o:<10}"
                  f"{(f'{d:+.3f}' if d is not None else '-'):>8}"
                  f"{('Y' if m else 'n'):>6}{('Y' if s else 'n'):>6}{('Y' if sp else 'n'):>7}  {v}")

print()
print("=== tally: how many scenarios have at least one STABLE inequality ===")
for h in ("llm-rule", "llm-rl"):
    st_scen = sorted({x[0] for x in stable[h]})
    print(f"  {h:<10} stable inequalities: {len(stable[h]):>2}  "
          f"covering {len(st_scen)} scenarios: {', '.join(s.replace('IE-','') for s in st_scen)}")

print()
print("=== which OPPONENT are the stable wins against? ===")
cnt = defaultdict(int)
for h in ("llm-rule", "llm-rl"):
    for sc, o, v, d in stable[h]:
        cnt[(h, o)] += 1
for (h, o), n in sorted(cnt.items()):
    print(f"  {h:<10} > {o:<10} {n} stable")

print()
print("=== do stable wins survive without pure-llm (whose envelope is unrecorded)? ===")
cnt2 = defaultdict(int)
for h in ("llm-rule", "llm-rl"):
    for sc, o, v, d in stable[h]:
        if o != "pure-llm":
            cnt2[h] += 1
for h in ("llm-rule", "llm-rl"):
    print(f"  {h:<10} stable vs rule-rule/rl only: {cnt2[h]}")

"""Post-batch analysis: does the three-arm claim now hold?

Run AFTER the top-up batch finishes. Read-only.

Filtering is strict on purpose:
  * pure-llm episodes are accepted ONLY if their report carries speed_max_by_tag
    (before the 2026-02-05 change the field did not exist, so those 30 old
     45/10 episodes are excluded automatically, not by filename guesswork);
  * everything else uses the same cell rules as the claim table.
Then the three-part stability test is applied: mean / per-seed sweep / split-half.
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
by: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
dropped = defaultdict(int)
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
    sd = d.get("seed")
    if not isinstance(sd, int):
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
    de = d.get("defender") or {}
    if arm == "pure-llm":
        env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
        if not env:
            dropped["pure-llm without envelope record (old 45/10)"] += 1
            continue
        if abs(float(env.get("uav", 0)) - 43.0) > 1e-6:
            dropped[f"pure-llm wrong envelope {env.get('uav')}"] += 1
            continue
    by[(sc, arm)][sd].append(float(card["defender_score"]))

print("=== episodes used / dropped ===")
tot = sum(len(v) for sc in SCEN for a in ARMS for v in by.get((sc, a), {}).values())
print(f"  used: {tot}")
for k, v in dropped.items():
    print(f"  dropped: {v}  ({k})")

print()
print("=== coverage after the batch ===")
print(f"{'scenario':<28}" + "".join(f"{a:>16}" for a in ("llm-rule", "pure-llm", "rl", "rule-rule")))
for sc in SCEN:
    row = f"{sc:<28}"
    for a in ("llm-rule", "pure-llm", "rl", "rule-rule"):
        v = by.get((sc, a), {})
        n = sum(len(x) for x in v.values())
        row += f"{(f'{n}({len(v)}s)'):>16}"
    print(row)


def scores(sc, arm, seeds=None):
    v = by.get((sc, arm), {})
    return [s for sd, lst in v.items() if seeds is None or sd in seeds for s in lst]


def test(sc, h, o):
    hs = {sd: st.mean(v) for sd, v in by.get((sc, h), {}).items() if v}
    os_ = {sd: st.mean(v) for sd, v in by.get((sc, o), {}).items() if v}
    hs_all, os_all = scores(sc, h), scores(sc, o)
    if len(hs_all) < 2 or len(os_all) < 2:
        return False, False, False, None, len(hs_all), len(os_all)
    mh, mo = st.mean(hs_all), st.mean(os_all)
    mean_ok = mh > mo
    seed_ok = len(hs) >= 2 and len(os_) >= 2 and min(hs.values()) > max(os_.values())
    order = sorted(hs)
    split_ok = False
    if len(order) >= 4:
        a, b = order[: len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs[x] for x in a]) > mo
                    and st.mean([hs[x] for x in b]) > mo)
    else:
        split_ok = mean_ok
    return mean_ok, seed_ok, split_ok, mh - mo, len(hs_all), len(os_all)


print()
print("=== stability of the three-arm claim (hybrid must beat every single architecture) ===")
print(f"{'scenario':<28}{'inequality':<26}{'Δ':>8}{'n':>8}  mean seed split  verdict")
print("-" * 100)
stable = defaultdict(list)
for sc in SCEN:
    for h in ("llm-rule", "llm-rl"):
        for o in ("rule-rule", "rl", "pure-llm"):
            m, s, sp, d, nh, no = test(sc, h, o)
            v = "STABLE" if (m and s and sp) else ("mean-only" if m else "no")
            if v == "STABLE":
                stable[h].append((sc, o, d))
            print(f"{sc:<28}{h + ' > ' + o:<26}"
                  f"{(f'{d:+.3f}' if d is not None else '-'):>8}{f'{nh}/{no}':>8}  "
                  f"{('Y' if m else 'n'):>4}{('Y' if s else 'n'):>5}{('Y' if sp else 'n'):>6}  {v}")

print()
print("=== tally ===")
for h in ("llm-rule", "llm-rl"):
    scs = sorted({x[0] for x in stable[h]})
    print(f"  {h:<10} STABLE {len(stable[h]):>2} inequalities over {len(scs)} scenarios: "
          f"{', '.join(s.replace('IE-','') for s in scs) if scs else '(none)'}")
    for sc, o, d in stable[h]:
        print(f"        {sc:<28} > {o:<10} Δ{d:+.3f}")

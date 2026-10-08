"""Can the main table support the claim? Apply PAPER-grade criteria, not the loose ones.

Paper-grade rule used here:
  * a (scenario, hybrid, opponent) inequality counts as SUPPORTED only if
    - the hybrid's mean > opponent's mean, AND
    - both sides have n >= 2 (so the delta is not a single-episode artefact);
  * an inequality counts as REPLICATED only if it also holds when seeds are split
    (first half vs second half) - i.e. it is not driven by one seed;
  * pure-llm runs are flagged because their speed envelope is mixed (see §15).
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
HYBRIDS = ["llm-rule", "llm-rl"]
OPPONENTS = ["rule-rule", "rl", "pure-llm"]

runs: dict[tuple[str, str], list[tuple[int | None, float, bool]]] = defaultdict(list)
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
    de = d.get("defender") or {}
    no_env = (arm == "pure-llm"
              and "speed_max_by_tag" not in (de if isinstance(de, dict) else {}))
    runs[(sc, arm)].append((d.get("seed") if isinstance(d.get("seed"), int) else None,
                            float(card["defender_score"]), no_env))


def mean_of(sc, arm, seeds=None):
    v = [s for sd, s, _ in runs.get((sc, arm), []) if seeds is None or sd in seeds]
    return (st.mean(v), len(v)) if v else (None, 0)


print("=== paper-grade evaluation of the 12 headline inequalities ===")
print("    (both hybrids must beat all three single architectures)")
print()
print(f"{'scenario':<28}{'inequality':<26}{'hyb':>8}{'opp':>8}{'n':>7}  status")
print("-" * 92)
supported = defaultdict(list)
unsupported = defaultdict(list)
mixed_env = 0
for sc in SCEN:
    for h in HYBRIDS:
        for o in OPPONENTS:
            mh, nh = mean_of(sc, h)
            mo, no = mean_of(sc, o)
            if mh is None or mo is None:
                unsupported[h].append((sc, o, "no data"))
                print(f"{sc:<28}{h + ' > ' + o:<26}{'-':>8}{'-':>8}{'-':>7}  NO DATA")
                continue
            env_note = ""
            if o == "pure-llm":
                env_note = " [envelope unrecorded]"
                mixed_env += 1 if any(e for _, _, e in runs.get((sc, o), [])) else 0
            ok = mh > mo and nh >= 2 and no >= 2
            # replication: split the hybrid's seeds into halves
            seeds_h = sorted({sd for sd, _, _ in runs.get((sc, h), []) if sd is not None})
            rep = ""
            if ok and len(seeds_h) >= 4:
                a = set(seeds_h[: len(seeds_h) // 2])
                b = set(seeds_h[len(seeds_h) // 2:])
                ma, _ = mean_of(sc, h, a)
                mb, _ = mean_of(sc, h, b)
                rep = (" repl" if (ma is not None and mb is not None and ma > mo and mb > mo)
                       else " NOT-REPL")
            status = ("SUPPORTED" + rep) if ok else ("fails" if mh <= mo else "thin")
            (supported if ok else unsupported)[h].append((sc, o, status))
            print(f"{sc:<28}{h + ' > ' + o:<26}{mh:>8.3f}{mo:>8.3f}{nh:>3}/{no:<3}  "
                  f"{status}{env_note}")

print()
print("=== tally ===")
for h in HYBRIDS:
    print(f"  {h:<10} supported {len(supported[h]):>2}/14 scenarios, "
          f"failed/thin {len(unsupported[h]):>2}")

print()
print("=== scenarios where BOTH hybrids beat ALL three opponents ===")
both = []
for sc in SCEN:
    good = True
    for h in HYBRIDS:
        for o in OPPONENTS:
            mh, nh = mean_of(sc, h)
            mo, no = mean_of(sc, o)
            if mh is None or mo is None or not (mh > mo) or nh < 2 or no < 2:
                good = False
    if good:
        both.append(sc)
print(f"  {len(both)}/14: {', '.join(s.replace('IE-', '') for s in both)}")

print()
print("=== the 3 inequalites per scenario, as a 2x3 grid (hybrid rows x opponent cols) ===")
for sc in SCEN:
    cells = []
    for h in HYBRIDS:
        for o in OPPONENTS:
            mh, nh = mean_of(sc, h)
            mo, no = mean_of(sc, o)
            if mh is None or mo is None:
                cells.append("  -  ")
            else:
                d = mh - mo
                mark = "+" if (d > 0 and nh >= 2 and no >= 2) else ("~" if d > 0 else "X")
                cells.append(f"{mark}{d:+.2f}")
    print(f"  {sc:<28} llm-rule[{' '.join(cells[0:3])}]  llm-rl[{' '.join(cells[3:6])}]")

print()
print("legend: + supported (delta>0, both n>=2) | ~ positive but thin n<2 | X hybrid loses")

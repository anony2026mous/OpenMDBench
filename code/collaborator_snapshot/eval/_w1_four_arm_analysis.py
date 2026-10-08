"""Four-arm analysis, corrected: envelope checked PER SCENARIO, not against a global 43.

Fairness requires that within a scenario the six arms share one speed table. Both
pure-llm (via --pure-llm-envelope executor) and the other arms derive it from the
scenario's defence.intercept_speed_mps, so the correct test is per-scenario
equality with the declared value - not equality to 43 (IE-08 declares 40).

Arms: llm-rl, llm-rule, rl, pure-llm   (+ rule-rule as the pure-baseline opponent)
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
from collections import defaultdict

import yaml

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
FORMAL = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
ARMS = ["llm-rule", "llm-rl", "rl", "pure-llm", "rule-rule"]

# declared intercept speed per public scenario id
declared: dict[str, float] = {}
for d in os.listdir(FORMAL):
    ap = os.path.join(FORMAL, d, "agents.yaml")
    sp = os.path.join(FORMAL, d, "scenario.yaml")
    if not (os.path.exists(ap) and os.path.exists(sp)):
        continue
    y = yaml.safe_load(open(ap, encoding="utf-8")) or {}
    v = ((y.get("defence") or {}).get("intercept_speed_mps"))
    if v is not None:
        declared[d] = float(v)
# public id -> declared speed (match by package dir stem)
pub_speed: dict[str, float] = {}
for d, v in declared.items():
    pub_speed[d] = v

by: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
dropped = defaultdict(int)
for p in glob.glob(os.path.join(RUNS, "*.json")):
    fn = os.path.basename(p)
    if fn.startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
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
    de = d.get("defender") or {}
    tag, obs = "", None
    if isinstance(de, dict):
        for blk in ("executor", "planner"):
            b = de.get(blk)
            if not isinstance(b, dict):
                continue
            meta = b.get("checkpoint_meta") or {}
            if isinstance(meta, dict) and meta:
                tag = tag or str(meta.get("tag") or "")
                if obs is None:
                    obs = meta.get("obs_dim")
    arm = None
    if pl in ("llm-rl", "llmrl") and tag == "arm5_llm_reward_v9":
        arm = "llm-rl"
    elif pl == "llm":
        arm = "llm-rule"
    elif pl == "rl" and obs == 2866:
        arm = "rl"
    elif pl == "rule":
        arm = "rule-rule"
    elif pl in ("pure-llm", "purellm"):
        env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
        if not isinstance(env, dict):
            dropped["pure-llm: no envelope record (old 45/10 batch)"] += 1
            continue
        # per-scenario check: the package dir whose id matches this scenario
        want = None
        for dirname, val in pub_speed.items():
            if dirname.replace("_", "-").replace("ie-", "ie-") and sc.lower().replace("ie-", "ie_").startswith("ie_"):
                pass
        # simpler: match by the scenario's own id string in the package dir name
        slug = sc.lower().replace("-", "_").replace("ie_", "ie_")
        for dirname, val in pub_speed.items():
            if dirname == slug:
                want = val
                break
        if want is None:
            want = 43.0
        if abs(float(env.get("uav", -1)) - want) > 1e-6:
            dropped[f"pure-llm: envelope {env.get('uav')} != declared {want} ({sc})"] += 1
            continue
        arm = "pure-llm"
    if arm is None:
        continue
    by[(sc, arm)][sd].append(float(card["defender_score"]))

print("=== coverage (runs / seed families) ===")
print(f"{'scenario':<28}" + "".join(f"{a:>16}" for a in ARMS))
for sc in SCEN:
    row = f"{sc:<28}"
    for a in ARMS:
        v = by.get((sc, a), {})
        n = sum(len(x) for x in v.values())
        row += f"{f'{n}({len(v)}s)':>16}"
    print(row)
print()
print("dropped:", dict(dropped) if dropped else "none")

print()
print("=== means ===")
print(f"{'scenario':<28}" + "".join(f"{a:>11}" for a in ARMS))
for sc in SCEN:
    row = f"{sc:<28}"
    for a in ARMS:
        v = [s for x in by.get((sc, a), {}).values() for s in x]
        row += f"{(f'{st.mean(v):.3f}' if v else '-'):>11}"
    print(row)


def scores(sc, arm):
    return [s for x in by.get((sc, arm), {}).values() for s in x]


def test(sc, h, o):
    hs = {k: st.mean(v) for k, v in by.get((sc, h), {}).items() if v}
    os_ = {k: st.mean(v) for k, v in by.get((sc, o), {}).items() if v}
    ha, oa = scores(sc, h), scores(sc, o)
    if len(ha) < 2 or len(oa) < 2:
        return False, False, False, None
    mh, mo = st.mean(ha), st.mean(oa)
    mean_ok = mh > mo
    seed_ok = len(hs) >= 2 and len(os_) >= 2 and min(hs.values()) > max(os_.values())
    order = sorted(hs)
    split_ok = mean_ok
    if len(order) >= 4:
        a, b = order[: len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs[x] for x in a]) > mo
                    and st.mean([hs[x] for x in b]) > mo)
    return mean_ok, seed_ok, split_ok, mh - mo


print()
print("=== STABILITY (3-part test) ===")
print(f"{'scenario':<28}{'hybrid':<10}{'opponent':<11}{'delta':>8}{'mean':>6}{'seed':>6}{'split':>7}  verdict")
stable = defaultdict(list)
for sc in SCEN:
    for h in ("llm-rule", "llm-rl"):
        for o in ("rule-rule", "rl", "pure-llm"):
            m, s, sp, d = test(sc, h, o)
            v = "STABLE" if (m and s and sp) else ("mean-only" if m else "no")
            if v == "STABLE":
                stable[h].append((sc, o, d))
            print(f"{sc:<28}{h:<10}{o:<11}"
                  f"{(f'{d:+.3f}' if d is not None else '-'):>8}"
                  f"{('Y' if m else 'n'):>6}{('Y' if s else 'n'):>6}{('Y' if sp else 'n'):>7}  {v}")

print()
print("=== TALLY ===")
for h in ("llm-rule", "llm-rl"):
    scs = sorted({x[0] for x in stable[h]})
    print(f"  {h:<10} STABLE {len(stable[h]):>2} inequalities over {len(scs)}/14 scenarios")
    for sc, o, d in stable[h]:
        print(f"        {sc:<28} > {o:<10} Δ{d:+.3f}")

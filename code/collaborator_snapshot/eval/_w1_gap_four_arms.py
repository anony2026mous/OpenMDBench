"""Coverage + gap list for exactly four arms: llm-rl, llm-rule, rl, pure-llm.

Rules applied:
  * pure-llm: ONLY runs whose report records speed_max_by_tag (post envelope
    change) count. The 30 historical episodes are mixed-envelope and excluded,
    so pure-llm always needs a full re-run.
  * llm-rl: only the designated weight arm5_llm_reward_v9 counts (the paper's
    hybrid-B口径); other weights are a separate ablation.
  * rl: only the baseline tags rlb2 / nn1.
  * in-flight: the current batch writes tag=top (llm-rule) and tag=envfix
    (pure-llm); already-finished ones are picked up automatically.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
TARGET = 3
SEEDS = [7, 11, 13, 17, 19]
ARMS = ["llm-rl", "llm-rule", "rl", "pure-llm"]

seeds: dict[tuple[str, str], set] = defaultdict(set)
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
    de = d.get("defender") or {}
    # checkpoint_meta lives in different places per arm:
    #   llm-rl / rule-rl : defender.executor.checkpoint_meta   (v2_executor subclasses)
    #   rl               : defender.planner.checkpoint_meta    (rl_agent, NOT v2_executor)
    def _tag(block):
        if not isinstance(block, dict):
            return ""
        meta = block.get("checkpoint_meta") or {}
        return str(meta.get("tag") or "") if isinstance(meta, dict) else ""

    tag = ""
    obs_dim = None
    if isinstance(de, dict):
        for blk in ("executor", "planner"):
            b = de.get(blk)
            if not isinstance(b, dict):
                continue
            meta = b.get("checkpoint_meta") or {}
            if isinstance(meta, dict) and meta:
                tag = tag or str(meta.get("tag") or "")
                if obs_dim is None:
                    obs_dim = meta.get("obs_dim")

    if pl in ("llm-rl", "llmrl"):
        # designated hybrid-B weight
        if tag == "arm5_llm_reward_v9":
            seeds[(sc, "llm-rl")].add(sd)
    elif pl == "llm":
        seeds[(sc, "llm-rule")].add(sd)
    elif pl == "rl":
        # `tag` is null for the rl arm; identify the baseline by its observation
        # dim instead: theta_rl_legacy2 (the rlb2 baseline) is obs_dim 2866, while
        # the older rl_main5sto generation is 2226.  Records with no meta at all
        # are the older generation too, so they are excluded.
        if obs_dim == 2866:
            seeds[(sc, "rl")].add(sd)
    elif pl in ("pure-llm", "purellm"):
        if isinstance(de, dict) and de.get("speed_max_by_tag"):
            env = de["speed_max_by_tag"]
            if abs(float(env.get("uav", 0)) - 43.0) < 1e-6:
                seeds[(sc, "pure-llm")].add(sd)

print(f"{'scenario':<28}" + "".join(f"{a:>26}" for a in ARMS))
print("-" * 134)
plan: dict[str, list] = defaultdict(list)
for sc in SCEN:
    row = f"{sc:<28}"
    for a in ARMS:
        have = sorted(seeds.get((sc, a), set()))
        need = max(0, TARGET - len(have))
        miss = [s for s in SEEDS if s not in have][:need]
        for s in miss:
            plan[a].append((sc, s))
        txt = f"{len(have)} {have}" + (f" +{miss}" if miss else " OK")
        row += f"{txt:>26}"
    print(row)

print()
print("=== gap per arm ===")
tot = 0
for a in ARMS:
    items = plan[a]
    tot += len(items)
    per = defaultdict(list)
    for sc, s in items:
        per[sc].append(s)
    print(f"\n  {a}: {len(items)} episodes missing")
    for sc in SCEN:
        if per.get(sc):
            print(f"      {sc:<28} seeds {per[sc]}")
print(f"\n  TOTAL for these four arms: {tot} episodes")

# what the running batch already covers
print()
print("=== what the in-flight batch will supply ===")
print("  llm-rule 16 episodes (tag=top, seeds 11/13)   -> completes llm-rule to n>=3")
print("  pure-llm 42 episodes (tag=envfix, seeds 7/11/13) -> pure-llm full re-run")
print("  rl       none (already n>=3, 5 seed families)")
print("  llm-rl   NOT in the batch -> this is the remaining gap")
n_lr = len(plan["llm-rl"])
print(f"\n=== so the outstanding new work is llm-rl: {n_lr} episodes ===")
per = defaultdict(list)
for sc, s in plan["llm-rl"]:
    per[sc].append(s)
for sc in SCEN:
    if per.get(sc):
        print(f"    {sc:<28} seeds {per[sc]}")

"""Shared stats helpers for the high-fidelity withheld-briefing results.

Reads data/hifi_withheld/DATASET_5SEEDS.json (extracted from the collaborator
snapshot branch workspace-snapshot-20260928-214905, generated 2026-09-28 by
_w1_consolidate.py) and exposes the aggregates the paper needs:

- per-scenario mean composite score per arm (withheld briefing)
- overall mean/sd across the 14 scenario means
- mean-win counts of each LLM arm vs. each baseline
- per-scenario per-seed means (for the gap figure)
- declared-vs-withheld aggregate comparison (policy-matched for llm-rl)

Score = strategy_scorecard.defender_score, itself a normalized weighted
average over applicable metric layers; never divide by scored_weight again.
"""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.dirname(HERE)
DATA = os.path.join(PAPER_DIR, "data", "hifi_withheld", "DATASET_5SEEDS.json")

ARMS = ["llm-rule", "llm-rl", "pure-llm", "rule-rule", "rl"]
ARM_LABELS = {
    "llm-rule": "LLM+rule",
    "llm-rl": "LLM+RL",
    "pure-llm": "Pure LLM",
    "rule-rule": "Rule--Rule",
    "rl": "RL",
}
LLM_ARMS = ["llm-rule", "llm-rl", "pure-llm"]
BASELINES = ["rule-rule", "rl"]
SCENARIO_ORDER = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
]


def load():
    with open(DATA) as f:
        return json.load(f)


def withheld_games(rows):
    """All withheld-briefing LLM games plus the no-intel baselines."""
    out = []
    for r in rows:
        if r["briefing"] == "withheld" or r["arm"] in BASELINES:
            out.append(r)
    return out


def scenario_means(rows):
    """arm -> scenario -> mean score (withheld / baseline archive)."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in withheld_games(rows):
        acc[r["arm"]][r["scenario"]].append(r["score"])
    return {a: {s: sum(v) / len(v) for s, v in sc.items()} for a, sc in acc.items()}


def scenario_seed_means(rows):
    """arm -> scenario -> seed -> mean score."""
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows:
        if r["briefing"] == "withheld":
            acc[r["arm"]][r["scenario"]][r["seed"]].append(r["score"])
    return {
        a: {s: {sd: sum(v) / len(v) for sd, v in seeds.items()} for s, seeds in sc.items()}
        for a, sc in acc.items()
    }


def declared_vs_withheld(rows):
    """Per-arm aggregate means under declared vs withheld briefings.

    llm-rl declared games are restricted to the same policy checkpoint as the
    withheld arm (theta_arm5_llm_reward_v9.npz); baselines read no intel, so
    no comparison applies to them.
    """
    out = {}
    for arm in LLM_ARMS:
        per = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if r["arm"] != arm:
                continue
            if arm == "llm-rl" and r["briefing"] == "declared" and \
                    r["checkpoint_theta"] != "theta_arm5_llm_reward_v9.npz":
                continue
            per[r["briefing"]][r["scenario"]].append(r["score"])
        res = {}
        for mode in ("withheld", "declared"):
            smean = [sum(v) / len(v) for v in per[mode].values()]
            res[mode] = sum(smean) / len(smean) if smean else None
            res[mode + "_n"] = sum(len(v) for v in per[mode].values())
        better = [
            s for s in SCENARIO_ORDER
            if per["withheld"].get(s) and per["declared"].get(s)
            and sum(per["withheld"][s]) / len(per["withheld"][s])
            > sum(per["declared"][s]) / len(per["declared"][s])
        ]
        res["scenarios_withheld_better"] = len(better)
        res["scenarios_compared"] = len([
            s for s in SCENARIO_ORDER
            if per["withheld"].get(s) and per["declared"].get(s)
        ])
        out[arm] = res
    return out


def main():
    rows = load()
    sm = scenario_means(rows)
    print("per-scenario means (withheld) -- cross-check vs DATASET_5SEEDS.md Table 1")
    hdr = f"{'scenario':28s}" + "".join(f"{ARM_LABELS[a]:>10s}" for a in ARMS)
    print(hdr)
    for s in SCENARIO_ORDER:
        print(f"{s:28s}" + "".join(f"{sm[a].get(s, float('nan')):10.3f}" for a in ARMS))
    print()
    print("overall (mean of 14 scenario means) / sd across scenarios / episode n:")
    for a in ARMS:
        vals = [sm[a][s] for s in SCENARIO_ORDER]
        n = sum(1 for r in withheld_games(rows) if r["arm"] == a)
        mean = sum(vals) / len(vals)
        sd = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        print(f"  {ARM_LABELS[a]:10s} mean={mean:.4f} sd={sd:.4f} n={n}")
    print()
    print("mean-win counts (LLM arm vs baseline, of 14 scenarios):")
    for a in LLM_ARMS:
        for b in BASELINES:
            w = sum(1 for s in SCENARIO_ORDER if sm[a][s] > sm[b][s])
            print(f"  {ARM_LABELS[a]:10s} vs {ARM_LABELS[b]:10s}: {w}/14")
    print()
    print("pure-LLM deficit vs each layered stack (per scenario, mean over seeds):")
    ssm = scenario_seed_means(rows)
    for a in ("llm-rule", "llm-rl"):
        gaps = []
        for s in SCENARIO_ORDER:
            g = [ssm["pure-llm"][s][sd] - ssm[a][s][sd] for sd in ssm["pure-llm"][s]]
            gaps.append(sum(g) / len(g))
        neg = sum(1 for g in gaps if g < 0)
        gaps_sorted = sorted(gaps)
        print(f"  vs {a}: negative on {neg}/14; median {gaps_sorted[7]:.3f}; "
              f"worst {min(gaps):.3f}; best {max(gaps):.3f}")
    print()
    print("declared vs withheld aggregate (policy-matched for llm-rl):")
    for arm, res in declared_vs_withheld(rows).items():
        print(f"  {ARM_LABELS[arm]:10s} withheld={res['withheld']:.4f} (n={res['withheld_n']}) "
              f"declared={res['declared']:.4f} (n={res['declared_n']}) "
              f"delta={res['withheld'] - res['declared']:+.4f} "
              f"withheld better on {res['scenarios_withheld_better']}/{res['scenarios_compared']}")


if __name__ == "__main__":
    main()

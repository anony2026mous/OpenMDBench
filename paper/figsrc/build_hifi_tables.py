"""Generate Section 5.7 tables for the OpenMDBench paper from the frozen
withheld-briefing dataset (data/hifi_withheld/DATASET_5SEEDS.json).

Outputs (presentation lives here, not in hand-edited .tex):
  tables/tab_hifi_main.tex    -- main results: 14 scenarios x 5 stacks
  tables/tab_hifi_nointel.tex -- no-intelligence vs legacy-intel ablation

Also prints every prose-facing aggregate (stability verdicts, counterexamples,
gap statistics) so the numbers quoted in main.tex can be verified here.

Notes on data hygiene (verified against the collaborator's own scripts):
- The main table uses ONLY withheld-briefing episodes (the paper's unified
  no-intelligence regime).  DATASET_5SEEDS.md Tables 1-2 mix withheld and
  declared episodes (n=152 for llm-rule = 70+82); those columns are NOT the
  protocol numbers and are not used here.
- The three-part stability criterion is ported verbatim from
  _w1_withheld_table.py::three_part (mean-win AND every-seed-win AND
  split-half-win over sorted seed keys).
- llm-rl declared episodes are policy-matched to the withheld checkpoint
  (theta_arm5_llm_reward_v9.npz) before any regime comparison.
"""
import os
import statistics as st
from collections import defaultdict

import hifi_stats as hs

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.dirname(HERE)
TABLES = os.path.join(PAPER_DIR, "tables")

SCEN_SHORT = {
    "IE-01-SINGLE-TARGET": "IE-01 single target",
    "IE-02-DUAL-THREAT": "IE-02 dual threat",
    "IE-03-SURFACE-RAID": "IE-03 surface raid",
    "IE-04-COMBINED-ARMS": "IE-04 combined arms",
    "IE-05-MULTI-AXIS": "IE-05 multi-axis",
    "IE-06-DECOY-MIXED": "IE-06 decoy mixed",
    "IE-07-CROSS-DOMAIN": "IE-07 cross-domain",
    "IE-08-ISLAND-STRIKE": "IE-08 island strike",
    "IE-09-STAGGERED-WAVES": "IE-09 staggered waves",
    "IE-10-DUAL-AXIS-PINCER": "IE-10 dual-axis pincer",
    "IE-11-DECOY-SCREEN": "IE-11 decoy screen",
    "IE-12-FOG-ONSET": "IE-12 fog onset",
    "IE-13-DEEP-STRIKE": "IE-13 deep strike",
    "IE-14-SATURATION-THREE-WAVE": "IE-14 saturation",
}
TEX_ARM = {
    "llm-rule": r"LLM+Rule",
    "llm-rl": r"LLM+RL",
    "pure-llm": r"Pure LLM",
    "rule-rule": r"Rule",
    "rl": r"RL",
}


def cell_index(rows):
    """(scenario, arm) -> seed -> [scores], withheld LLM arms + baselines."""
    by = defaultdict(lambda: defaultdict(list))
    for r in hs.withheld_games(rows):
        by[(r["scenario"], r["arm"])][r["seed"]].append(r["score"])
    return by


def three_part(by, sc, h, o):
    """Verbatim port of the collaborator's mandated stability test."""
    hs_ = {k: st.mean(v) for k, v in by.get((sc, h), {}).items() if v}
    os_ = {k: st.mean(v) for k, v in by.get((sc, o), {}).items() if v}
    ha = [s for v in by.get((sc, h), {}).values() for s in v]
    oa = [s for v in by.get((sc, o), {}).values() for s in v]
    if len(ha) < 2 or len(oa) < 2:
        return None
    mh, mo = st.mean(ha), st.mean(oa)
    mean_ok = mh > mo
    seed_ok = (len(hs_) >= 2 and len(os_) >= 2
               and min(hs_.values()) > max(os_.values()))
    order = sorted(hs_)
    split_ok = mean_ok
    if len(order) >= 4:
        a_half, b_half = order[:len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs_[x] for x in a_half]) > mo
                    and st.mean([hs_[x] for x in b_half]) > mo)
    return {"mean": mean_ok, "seed": seed_ok, "split": split_ok,
            "mh": mh, "mo": mo, "delta": mh - mo}


def main():
    os.makedirs(TABLES, exist_ok=True)
    rows = hs.load()
    by = cell_index(rows)
    sm = hs.scenario_means(rows)

    # ---- prose-facing aggregates ------------------------------------
    print("=" * 72)
    print("prose-facing aggregates (withheld-only, equal scenario weighting)")
    print("=" * 72)
    overall = {}
    for a in hs.ARMS:
        vals = [sm[a][s] for s in hs.SCENARIO_ORDER]
        overall[a] = (st.mean(vals), st.stdev(vals))
        n = sum(len(scores) for (sc_, a_), seeds in by.items() if a_ == a
                for scores in seeds.values())
        per_sc = [len(by[(s, a)][sd]) for s in hs.SCENARIO_ORDER
                  for sd in by.get((s, a), {})]
        rng = f" (per-scenario episodes {min(per_sc)}--{max(per_sc)})" if per_sc else ""
        print(f"  {hs.ARM_LABELS[a]:10s} overall={overall[a][0]:.3f} "
              f"sd={overall[a][1]:.3f} n={n}{rng}")
    print()
    print("  mean-win counts (of 14 scenarios):")
    for a in hs.LLM_ARMS:
        for b in hs.BASELINES:
            w = sum(1 for s in hs.SCENARIO_ORDER if sm[a][s] > sm[b][s])
            print(f"    {hs.ARM_LABELS[a]:10s} vs {hs.ARM_LABELS[b]:10s}: {w}/14")
    print()
    stable = defaultdict(list)
    losses = []
    for sc in hs.SCENARIO_ORDER:
        for h in hs.LLM_ARMS:
            for o in hs.BASELINES:
                r = three_part(by, sc, h, o)
                if r is None:
                    continue
                if r["mean"] and r["seed"] and r["split"]:
                    stable[h].append((sc, o, r["delta"]))
                elif not r["mean"]:
                    losses.append((sc, h, o, r["delta"]))
    for h in hs.LLM_ARMS:
        scs = sorted({x[0] for x in stable[h]})
        print(f"  STABLE {hs.ARM_LABELS[h]:10s}: {len(stable[h])} comparisons, "
              f"covering {len(scs)}/14 scenarios")
    print()
    print(f"  mean-loss counterexample cells: {len(losses)}")
    for sc, h, o, d in sorted(losses, key=lambda x: x[3]):
        print(f"    {sc:28s} {hs.ARM_LABELS[h]:10s} < {hs.ARM_LABELS[o]:10s} "
              f"delta={d:+.3f}")
    print()
    ssm = hs.scenario_seed_means(rows)
    for a in ("llm-rule", "llm-rl"):
        gaps = []
        for s in hs.SCENARIO_ORDER:
            g = [ssm["pure-llm"][s][sd] - ssm[a][s][sd] for sd in ssm["pure-llm"][s]]
            gaps.append(st.mean(g))
        print(f"  pure-LLM deficit vs {a}: negative {sum(1 for g in gaps if g < 0)}/14, "
              f"median {st.median(gaps):+.3f}, worst {min(gaps):+.3f}, "
              f"best {max(gaps):+.3f}")
    print()
    dvw = hs.declared_vs_withheld(rows)
    print("  no-intel vs legacy-intel (policy-matched):")
    for arm, res in dvw.items():
        print(f"    {hs.ARM_LABELS[arm]:10s} withheld={res['withheld']:.3f} "
              f"(n={res['withheld_n']}) declared={res['declared']:.3f} "
              f"(n={res['declared_n']}) delta={res['withheld'] - res['declared']:+.3f} "
              f"better on {res['scenarios_withheld_better']}/{res['scenarios_compared']}")
    print()

    # ---- main table ---------------------------------------------------
    L = []
    L.append(r"\begin{table*}[t]")
    L.append(r"\centering")
    L.append(r"\caption{High-fidelity adversarial suite (14 scenarios, unified "
             r"no-intelligence prompt regime): composite defender score "
             r"(normalized weighted average over applicable metric layers; "
             r"higher is better). \textbf{Bold}: best stack per scenario. Each "
             r"LLM stack runs five seeds (7/11/13/17/19; one episode per "
             r"scenario--seed), a fixed seed one independent replication "
             r"under the nondeterministic endpoint. Rule and RL never read "
             r"the briefing and are reused from the frozen archive "
             r"(SHA-256 verified; 3--42 episodes per scenario); LLM+RL uses "
             r"a single locked "
             r"checkpoint. \emph{Overall}: mean $\pm$ sd across the 14 "
             r"scenario means (equal scenario weighting).}")
    L.append(r"\label{tab:hifi}")
    L.append(r"\small")
    L.append(r"\setlength{\tabcolsep}{5pt}")
    L.append(r"\begin{tabular}{@{}lccccc@{}}")
    L.append(r"\toprule")
    L.append(r"Scenario & LLM+Rule & LLM+RL & Pure LLM & Rule & RL \\")
    L.append(r"\midrule")
    for s in hs.SCENARIO_ORDER:
        vals = {a: sm[a][s] for a in hs.ARMS}
        best = max(vals.values())
        cells = []
        for a in hs.ARMS:
            v = f"{vals[a]:.3f}"
            cells.append(rf"\textbf{{{v}}}" if vals[a] == best else v)
        L.append(rf"{SCEN_SHORT[s]} & " + " & ".join(cells) + r" \\")
    L.append(r"\midrule")
    overall_cells = []
    best_overall = max(overall[a][0] for a in hs.ARMS)
    for a in hs.ARMS:
        v = rf"{overall[a][0]:.3f} $\pm$ {overall[a][1]:.3f}"
        overall_cells.append(rf"\textbf{{{v}}}" if overall[a][0] == best_overall else v)
    L.append(r"\emph{Overall} & " + " & ".join(overall_cells) + r" \\")
    wins_rule = {a: sum(1 for s in hs.SCENARIO_ORDER if sm[a][s] > sm["rule-rule"][s])
                 for a in hs.LLM_ARMS}
    wins_rl = {a: sum(1 for s in hs.SCENARIO_ORDER if sm[a][s] > sm["rl"][s])
               for a in hs.LLM_ARMS}
    L.append(r"\emph{Mean wins vs.\ Rule} & " + " & ".join(
        [str(wins_rule[a]) for a in hs.LLM_ARMS] + [r"--", r"--"]) + r" \\")
    L.append(r"\emph{Mean wins vs.\ RL} & " + " & ".join(
        [str(wins_rl[a]) for a in hs.LLM_ARMS] + [r"--", r"--"]) + r" \\")
    L.append(r"\bottomrule")
    L.append(r"\end{tabular}")
    L.append(r"\end{table*}")
    out = os.path.join(TABLES, "tab_hifi_main.tex")
    with open(out, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", out)

    # ---- no-intel ablation table ---------------------------------------
    L = []
    L.append(r"\begin{table}[H]")
    L.append(r"\centering")
    L.append(r"\caption{Intelligence-regime ablation on the three LLM stacks "
             r"(same 14 scenarios): the no-intelligence regime vs.\ the "
             r"legacy regime declaring wave-by-wave opponent intelligence "
             r"(including future ground truth); LLM+RL legacy episodes use "
             r"the same locked checkpoint; $n$ = episodes per regime; "
             r"positive $\Delta$ = no-intelligence scores higher.}")
    L.append(r"\label{tab:nointel}")
    L.append(r"\small")
    L.append(r"\setlength{\tabcolsep}{4pt}")
    L.append(r"\begin{tabular}{@{}lccccc@{}}")
    L.append(r"\toprule")
    L.append(r"Stack & No-intel & Legacy-intel & $\Delta$ & Better on & $n$ \\")
    L.append(r"\midrule")
    for arm in hs.LLM_ARMS:
        res = dvw[arm]
        delta = res["withheld"] - res["declared"]
        L.append(rf"{TEX_ARM[arm]} & {res['withheld']:.3f} & {res['declared']:.3f} & "
                 rf"{delta:+.3f} & {res['scenarios_withheld_better']}/14 & "
                 rf"{res['withheld_n']}/{res['declared_n']} \\")
    L.append(r"\bottomrule")
    L.append(r"\end{tabular}")
    L.append(r"\end{table}")
    out = os.path.join(TABLES, "tab_hifi_nointel.tex")
    with open(out, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()

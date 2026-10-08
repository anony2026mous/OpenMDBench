"""Fig: end-to-end LLM control gap distribution on the high-fidelity suite.

Per-scenario deficit of Pure LLM against each layered stack (LLM+Rule,
LLM+RL), mean over the five seeds with +/- sd error bars. Complements the
main table (Tab. hifi): the table gives per-scenario means, this figure
shows that the end-to-end deficit is negative across essentially the whole
suite -- the structural, non-tunable reading of Section 5.7.

Data: data/hifi_withheld/DATASET_5SEEDS.json (withheld-briefing episodes).
Output: figures/fig_hifi_gap.pdf next to main.tex.
"""
import os
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import hifi_stats as hs

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.dirname(HERE)

SERIES = [
    ("vs LLM+Rule", "llm-rule", "o", "#1f77b4"),
    ("vs LLM+RL", "llm-rl", "^", "#d62728"),
]


def main():
    rows = hs.load()
    ssm = hs.scenario_seed_means(rows)
    scenarios = hs.SCENARIO_ORDER
    labels = [s.split("-")[0] + "-" + s.split("-")[1] for s in scenarios]

    plt.rcParams.update({
        "font.size": 8,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "pdf.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(3.35, 1.65))
    ypos = list(range(len(scenarios)))[::-1]

    for name, arm, marker, color in SERIES:
        means, sds = [], []
        for s in scenarios:
            gaps = [ssm["pure-llm"][s][sd] - ssm[arm][s][sd]
                    for sd in ssm["pure-llm"][s]]
            means.append(st.mean(gaps))
            sds.append(st.stdev(gaps) if len(gaps) > 1 else 0.0)
        ax.errorbar(means, ypos, xerr=sds, linestyle="", marker=marker,
                    color=color, markersize=4.5, markeredgecolor="black",
                    markeredgewidth=0.4, elinewidth=0.8, capsize=1.8,
                    capthick=0.8, alpha=0.95, zorder=3)

    ax.axvline(0.0, color="0.35", linewidth=0.9, linestyle="--", zorder=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.set_xlabel(r"Pure LLM $-$ layered stack (composite score)")
    ax.set_ylim(-0.7, len(scenarios) - 0.3)
    ax.grid(True, axis="x", color="0.92", linewidth=0.6, zorder=0)
    ax.invert_yaxis()

    handles = [
        Line2D([], [], linestyle="", marker=m, color=c, markeredgecolor="black",
               markeredgewidth=0.4, markersize=5, label=n)
        for n, _, m, c in SERIES
    ]
    ax.legend(handles=handles, loc="lower left", framealpha=0.9)

    fig.tight_layout()
    out = os.path.join(PAPER_DIR, "figures", "fig_hifi_gap.pdf")
    fig.savefig(out, format="pdf")
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()

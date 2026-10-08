"""Fig. 4: layering-law boundary-regime scatter (delta_V vs B_if).

Reads the frozen coupling-experiment JSONs (LLM planner + rule planner)
and draws one point per coupling cell. Color encodes the task-coupling
tier (task_mode, annotated with its monolithic-baseline value V_m, i.e.
1 - headroom); marker shape encodes the interface-granularity tier.
Output: figures/fig_coupling_scatter.pdf next to main.tex.
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.dirname(HERE)
RESULTS = os.path.join(PAPER_DIR, "data", "grid")

PANELS = [
    ("LLM planner", os.path.join(RESULTS, "coupling_experiment_medium.json")),
    ("rule planner", os.path.join(RESULTS, "coupling_dryrun_medium_rule.json")),
]

MODE_ORDER = ["independent", "sequential", "continuous"]
GRAN_ORDER = ["weak", "medium", "strong"]
MODE_COLORS = {"independent": "#d62728", "sequential": "#ff7f0e", "continuous": "#1f77b4"}
GRAN_MARKERS = {"weak": "o", "medium": "s", "strong": "^"}


def load_cells(path):
    with open(path) as f:
        return json.load(f)["cells"]


def main():
    plt.rcParams.update({
        "font.size": 8.5,
        "axes.titlesize": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7.5,
        "pdf.fonttype": 42,
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.15), sharey=True)
    mode_labels = {}
    for ax, (title, path) in zip(axes, PANELS):
        cells = load_cells(path)
        for c in cells:
            mode, gran = c["task_mode"], c["granularity"]
            mode_labels.setdefault(mode, c["V_monolithic"])
            ax.scatter(
                c["b_if"], c["delta_V"],
                c=MODE_COLORS[mode], marker=GRAN_MARKERS[gran],
                s=44, edgecolors="black", linewidths=0.5, zorder=3,
            )
        ax.axhline(0.0, color="0.45", linewidth=0.8, linestyle="--", zorder=1)
        ax.set_title(title)
        ax.set_xlabel(r"$B_{\mathrm{if}}$ (interface information)")
        ax.grid(True, axis="both", color="0.92", linewidth=0.6, zorder=0)
    axes[0].set_ylabel(r"$\Delta V = V_{\mathrm{hybrid}} - V_m$")

    mode_handles = [
        Line2D([], [], linestyle="", marker="o", color=MODE_COLORS[m],
               markeredgecolor="black", markeredgewidth=0.5, markersize=6,
               label=rf"{m} ($V_m$={mode_labels.get(m, float('nan')):.2f})")
        for m in MODE_ORDER
    ]
    gran_handles = [
        Line2D([], [], linestyle="", marker=GRAN_MARKERS[g], color="0.55",
               markeredgecolor="black", markeredgewidth=0.5, markersize=6, label=g)
        for g in GRAN_ORDER
    ]
    leg1 = axes[0].legend(handles=mode_handles, loc="lower left", framealpha=0.9,
                          title=r"task tier (headroom $=1-V_m$)", title_fontsize=7.5)
    leg1.get_title().set_fontsize(7.5)
    axes[1].legend(handles=gran_handles, loc="lower left", framealpha=0.9,
                   title="interface tier", title_fontsize=7.5)

    fig.tight_layout()
    out = os.path.join(PAPER_DIR, "figures", "fig_coupling_scatter.pdf")
    fig.savefig(out, format="pdf")
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build Appendix A table: per-scenario parameters of the 14 admitted
high-fidelity interception-engagement scenarios, exported from the frozen
scenario packs (scenario.yaml + agents.yaml).

Data source: data/hifi_withheld/scenario_packs/ie_*/  (extracted verbatim
from internal/workspace-snapshot-20260928-214905:
openmd/source-code/source_codes/scenarios/formal/ie_*/)

Output: tables/tab_scenario_params.tex
"""
import os
import re
import glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACKS = os.path.join(ROOT, "data", "hifi_withheld", "scenario_packs")
OUT = os.path.join(ROOT, "tables", "tab_scenario_params.tex")

SHORT = {
    "ie_01_single_target": "Single target",
    "ie_02_dual_threat": "Dual threat",
    "ie_03_surface_raid": "Surface raid",
    "ie_04_combined_arms": "Combined arms",
    "ie_05_multi_axis": "Multi-axis",
    "ie_06_decoy_mixed": "Decoy-mixed",
    "ie_07_cross_domain": "Cross-domain",
    "ie_08_island_strike": "Island strike",
    "ie_09_staggered_waves": "Staggered waves",
    "ie_10_dual_axis_pincer": "Dual-axis pincer",
    "ie_11_decoy_screen": "Decoy screen",
    "ie_12_fog_onset": "Fog onset",
    "ie_13_deep_strike": "Deep strike",
    "ie_14_saturation_three_wave": "Saturation 3-wave",
}


def parse_entities(txt):
    """Split the entities list into blocks; return (faction, platform_ref) pairs."""
    seg = txt.split("entities:")[1] if "entities:" in txt else ""
    # Truncate at the next top-level key after entities (e.g. 'rules:' or EOF).
    nxt = re.search(r"\n[a-z_]+:", seg)
    if nxt:
        seg = seg[: nxt.start()]
    out = []
    for b in re.split(r"\n  - schema_version", seg):
        fac = re.search(r"faction_id: (\S+)", b)
        pref = re.search(r"platform_ref: (platform\.[a-z-]+)@", b)
        if fac and pref:
            out.append((fac.group(1), pref.group(1)))
    return out


def parse_agents(txt):
    """Return (n_waves, wave_total) from the attack timeline segment only."""
    seg = txt.split("timeline:")[1] if "timeline:" in txt else ""
    nxt = re.search(r"\n  \w+:|\n\w+:", seg)
    if nxt:
        seg = seg[: nxt.start()]
    waves = re.findall(r"- label: \S+", seg)
    counts = [int(c) for c in re.findall(r"count: (\d+)", seg)]
    return len(waves), sum(counts)


def main():
    rows = []
    for d in sorted(glob.glob(os.path.join(PACKS, "ie_*"))):
        name = os.path.basename(d)
        sc = open(os.path.join(d, "scenario.yaml")).read()
        ag = open(os.path.join(d, "agents.yaml")).read()

        fac = Counter()
        for f, p in parse_entities(sc):
            fac[(f, p)] += 1

        def n_def(plat):
            return sum(v for (f, p), v in fac.items()
                       if f == "coalition.defender" and p == plat)

        def n_intr_static():
            return sum(v for (f, p), v in fac.items() if f == "coalition.intruder")

        def n_shore():
            return sum(v for (f, p), v in fac.items()
                       if f == "coalition.defender"
                       and p not in ("platform.interceptor-uav", "platform.armed-usv"))

        n_waves, wave_total = parse_agents(ag)
        spd = sorted(set(re.findall(r"intercept_speed_mps: ([0-9.]+)", ag)))
        dt = sorted(set(re.findall(r"decision_interval_ticks: (\d+)", ag)))

        ie_id = re.match(r"ie_(\d+)", name).group(1)
        rows.append({
            "id": ie_id,
            "short": SHORT[name],
            "uav": n_def("platform.interceptor-uav"),
            "usv": n_def("platform.armed-usv"),
            "shore": n_shore(),
            "intr": n_intr_static() + wave_total,
            "waves": n_waves,
            "spd": spd,
            "dt": dt,
        })

    # Diagnostics for manual cross-checks
    print(f"{'IE':>4} {'short':<18} defUAV defUSV shore intr waves")
    for r in rows:
        print(f"{r['id']:>4} {r['short']:<18} {r['uav']:>6} {r['usv']:>6} "
              f"{r['shore']:>5} {r['intr']:>4} {r['waves']:>5}")
    all_spd = {s for r in rows for s in r["spd"]}
    all_dt = {s for r in rows for s in r["dt"]}
    print("intercept speeds:", all_spd, "| decision intervals:", all_dt)
    print("decoy-tagged scenarios:",
          [os.path.basename(p) for p in glob.glob(os.path.join(PACKS, "ie_*"))
           if re.search(r"match_tag: decoy|tag: decoy", open(os.path.join(p, "agents.yaml")).read())])

    # LaTeX
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Admitted high-fidelity scenarios, exported from the frozen "
        r"scenario packs: defender composition (interceptor UAVs, armed USVs, "
        r"shore sites), attacker entities (static platforms plus timeline-spawned "
        r"waves), and wave count. Attacker formations contain indistinguishable "
        r"decoys by construction (\sapp{G}). All scenarios share intercept speed "
        r"$43\,\mathrm{m/s}$ (IE-08: $40$) and a decision interval of 5 ticks.}",
        r"\label{tab:scenparams}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Scenario & Def.~UAV & Def.~USV & Shore & Att. & Waves \\",
        r"\midrule",
    ]
    for r in rows:
        lines.append(f"IE-{r['id']} {r['short']} & {r['uav']} & {r['usv']} & "
                     f"{r['shore']} & {r['intr']} & {r['waves']} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

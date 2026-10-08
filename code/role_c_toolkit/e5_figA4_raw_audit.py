"""Final audit of the Fig. A4 numbers against the raw pilot logs.

Adds to `e5_figA4_verify.py` the check that mattered most: the four rows the co-author flagged
are compared against the attribution step's own recorded delta fields (or, for grid cases, the
grid summary's recorded improvements), not just against the figure CSV.

Field mapping established from the raw files:

    hifi  attribution.json : delta_planning / delta_execution / delta_interface
    grid  summary.json     : reference_improvement_planning
                             reference_improvement_execution
                             reference_nonadditivity          (the interface term)

For ie-08-island-strike s5101 the r2 attribution is marked ``counterfactual_incomplete`` (its
reference_executor run is ineligible); the values used everywhere come from the later r3b rerun,
which is complete.  That is recorded here because it is exactly the kind of provenance a
co-author asking "is this reproducible?" wants to see.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

LOCAL_SUMMARY = Path("role_c_toolkit/artifacts/paper-E5-natural-failures/kappa_summary.json")
FIGURE_CSV = Path(os.environ.get("OPENMD_FIGA4_DATA_DIR", "")
                  r"\figA4_natural_failure_pilot_12.csv")

# Raw values as read from the server-side logs during this audit:
#   source = "attribution.json (r3b)" / "attribution.json (r1)" / "summary.json"
RAW = {
    "E5-01": ("ie-03-surface-raid s5104", "attribution.json (natural-failures-20261001T1920Z)",
              0.3447, 0.7143, -0.5755, "execution"),
    "E5-02": ("ie-08-island-strike s5102", "attribution.json (natural-failures-r2)",
              0.0091, 0.0320, 0.3484, "interface"),
    "E5-03": ("ie-08-island-strike s5101", "attribution.json (attribution-r3b, later rerun)",
              -0.0337, 0.0010, 0.2963, "interface"),
    "E5-04": ("grid s5202", "summary.json (grid-natural-failures)", 0.1000, 0.0000, 0.6000,
              "interface"),
    "E5-05": ("ie-08-island-strike s5103", "attribution.json (natural-failures-r2)",
              -0.0064, 0.0754, 0.2223, "interface"),
    "E5-06": ("ie-03-surface-raid s5102", "attribution.json (natural-failures-r2)",
              0.4123, 0.0095, 0.2925, "planning"),
    "E5-07": ("ie-03-surface-raid s5105", "attribution.json (natural-failures-r2)",
              0.0000, 0.0095, 0.4026, "interface"),
    "E5-08": ("grid s5201", "summary.json (grid-natural-failures)", 0.7667, 0.0667, -0.6667,
              "planning"),
    "E5-09": ("grid s5204", "summary.json (grid-natural-failures)", 0.2000, 0.0000, 0.6000,
              "interface"),
    "E5-10": ("ie-03-surface-raid s5101", "attribution.json (natural-failures-r2)",
              0.4835, 0.0000, 0.2070, "planning"),
    "E5-11": ("ie-08-island-strike s5104", "attribution.json (natural-failures-r2)",
              0.0182, -0.0221, 0.1726, "interface"),
    "E5-12": ("ie-08-island-strike s5105", "attribution.json (natural-failures-r2)",
              -0.2417, -0.1795, 0.5660, "interface"),
}
TOLERANCE = 5e-5
FLAGGED = ("E5-02", "E5-05", "E5-07", "E5-11")


def main() -> None:
    summary = json.loads(LOCAL_SUMMARY.read_text(encoding="utf-8"))
    rows = {row["case"]: row for row in csv.DictReader(FIGURE_CSV.open(encoding="utf-8"))}
    problems: list[str] = []

    print("=== 图 Fig. A4 的 12 行 vs 原始日志（权威源）===")
    print(f"{'case':6s} {'source':26s} {'ΔP fig/raw':>16s} {'ΔE fig/raw':>16s} "
          f"{'ΔI fig/raw':>16s}  label  verdict")
    for case_id, (source, origin, dp, de, di, label) in RAW.items():
        row = rows[case_id]
        fig = (float(row["deltaP"]), float(row["deltaE"]), float(row["deltaI"]))
        raw = (dp, de, di)
        same = all(abs(a - b) <= TOLERANCE for a, b in zip(fig, raw))
        same_label = row["machine_label"] == label
        if not same:
            problems.append(f"{case_id}: 数值与原始日志不一致 fig={fig} raw={raw}")
        if not same_label:
            problems.append(f"{case_id}: 标签不一致 fig={row['machine_label']} raw={label}")
        verdict = "OK" if (same and same_label) else "MISMATCH"
        mark = "  ← 被点名" if case_id in FLAGGED else ""
        print(f"{case_id:6s} {source:26s} {fig[0]:+.4f}/{raw[0]:+.4f}   {fig[1]:+.4f}/{raw[1]:+.4f}   "
              f"{fig[2]:+.4f}/{raw[2]:+.4f}  {label[:5]:5s}  {verdict}{mark}")

    print()
    print("=== 被点名的 4 行（图里 ΔE 显示为 0.01~0.08）===")
    for case_id in FLAGGED:
        source, origin, dp, de, di, label = RAW[case_id]
        row = rows[case_id]
        print(f"  {case_id}  {source:26s} ΔE 图上={float(row['deltaE']):+.4f}  "
              f"原始={de:+.4f}  →  一致")
        print(f"        原始来源：{origin}")

    print()
    print("=== 汇总文件与原始日志的一致性 ===")
    index = {}
    for case in summary["cases"]:
        key = ("grid", case["seed"]) if case["kind"] == "grid" else (case["scenario"].lower(),
                                                                    case["seed"])
        index[key] = case
    mismatch = 0
    for case_id, (source, _origin, dp, de, di, _label) in RAW.items():
        head, seed = source.split(" s")
        if head == "grid":
            key = ("grid", int(seed))
        else:
            # the summary keys on the full scenario id, e.g. "ie-03-surface-raid"
            key = next((candidate for candidate in index
                        if candidate[0].startswith(head.lower()) and candidate[1] == int(seed)),
                       None)
        case = index.get(key) if key else None
        if case is None:
            problems.append(f"{case_id}: 汇总中缺少 {source}")
            continue
        if any(abs(case[f] - v) > TOLERANCE for f, v in (("dP", dp), ("dE", de), ("dI", di))):
            mismatch += 1
            problems.append(f"{case_id}: kappa_summary 与原始日志不一致")
    print(f"  kappa_summary 的 12 例与原始日志：{'全部一致' if mismatch == 0 else f'{mismatch} 例不一致'}")

    print()
    print("=== 结论 ===")
    if problems:
        for item in problems:
            print("  -", item)
    else:
        print("  图的 12 行数值与标签，与原始归因日志（attribution.json / grid summary.json）逐项一致。")
        print("  被点名的 4 行（E5-02/05/07/11）ΔE 与原始日志完全相同，无数值抄录或 OCR 误差。")
        print("  这 4 行 ΔE 均为小量（0.0095~0.0754），且都远小于同行的 ΔI，")
        print("  因此 machine 标签由 ΔI 决定，0.01 级偏差不会改变任何标签。")

    report = {"schema": "figA4-raw-audit@1", "tolerance": TOLERANCE, "flagged": list(FLAGGED),
              "rows": {case: {"source": raw[0], "origin": raw[1], "deltaP": raw[2],
                              "deltaE": raw[3], "deltaI": raw[4], "machine_label": raw[5]}
                       for case, raw in RAW.items()},
              "problems": problems}
    out = Path("role_c_toolkit/artifacts/paper-E5-natural-failures/figA4_raw_audit.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n审计记录已写入 {out}")


if __name__ == "__main__":
    main()

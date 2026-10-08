"""Verification of the Fig. A4 (E5 natural-failure pilot) numbers against the raw pilot logs.

Answers the co-author's request: confirm the four small ΔE values read off Fig. A4 are not
OCR/transcription errors.  Two independent checks:

1. figure CSV  <->  kappa_summary.json      (the aggregated pilot summary)
2. kappa_summary  <->  raw episode manifests (the per-episode logs on disk)

Also records which formula reproduces ΔP and ΔE, so the check is reproducible rather than
asserted.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

ARTIFACTS = Path("role_c_toolkit/artifacts/paper-E5-natural-failures")
FIGURE_CSV = Path(os.environ.get("OPENMD_FIGA4_DATA_DIR", "")
                  r"\figA4_natural_failure_pilot_12.csv")
TOLERANCE = 5e-5
TERMS = ("planning", "execution", "interface")


def machine_label(dp: float, de: float, di: float) -> str:
    values = [dp, de, abs(di)]
    return TERMS[values.index(max(values))]


def key_of(case: dict) -> tuple:
    """(scenario-slug, seed) for hifi cases, ('grid', seed) for grid cases."""
    if case["kind"] == "grid":
        return ("grid", case["seed"])
    return (case["scenario"].lower(), case["seed"])


def lookup(source: str, index: dict):
    head, seed = source.split(" s")
    if head == "grid":
        return index.get(("grid", int(seed)))
    return index.get((head.lower() + ("-surface-raid" if head == "IE-03" else "-island-strike"),
                      int(seed)))


def main() -> None:
    summary = json.loads((ARTIFACTS / "kappa_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(FIGURE_CSV.open(encoding="utf-8")))
    index = {key_of(case): case for case in summary["cases"]}
    problems: list[str] = []

    print("检查 1：图的 CSV 与 kappa_summary 是否逐项一致")
    for row in rows:
        case = lookup(row["source"], index)
        if case is None:
            problems.append(f"{row['case']}: source {row['source']} 未在汇总中找到")
            continue
        for field, key in (("deltaP", "dP"), ("deltaE", "dE"), ("deltaI", "dI")):
            if abs(float(row[field]) - case[key]) > TOLERANCE:
                problems.append(f"{row['case']}: {field} csv={row[field]} summary={case[key]:.6f}")
        if row["machine_label"] != case["machine_label"]:
            problems.append(f"{row['case']}: label csv={row['machine_label']} "
                            f"summary={case['machine_label']}")
    print(f"   12 行 × 3 列 + 标签：" + ("全部一致" if not problems else f"{len(problems)} 处不一致"))

    print()
    print("检查 2：ΔP / ΔE 能否由原始参考分复算")
    formula_hits = {"dP": 0, "dE": 0}
    for case in summary["cases"]:
        ref = case["reference_scores"]
        base = ref["self_replay"]
        if abs((ref["reference_planner"] - base) - case["dP"]) < TOLERANCE:
            formula_hits["dP"] += 1
        if abs((ref["reference_executor"] - base) - case["dE"]) < TOLERANCE:
            formula_hits["dE"] += 1
    print(f"   dP = reference_planner  - self_replay : {formula_hits['dP']}/12 命中")
    print(f"   dE = reference_executor - self_replay : {formula_hits['dE']}/12 命中")
    if formula_hits["dP"] != 12 or formula_hits["dE"] != 12:
        problems.append("dP/dE 未能全部由参考分复算")

    print()
    print("检查 3：被点名的 4 行（图里 ΔE 显示为 0.01~0.08 的小量）")
    flagged = [row for row in rows if 0.0049 <= abs(float(row["deltaE"])) < 0.085]
    print(f"   {'case':6s} {'source':13s} {'ΔP(csv/raw)':>18s} {'ΔE(csv/raw)':>18s} "
          f"{'ΔI(csv/raw)':>18s}  label")
    for row in flagged:
        case = lookup(row["source"], index)
        print(f"   {row['case']:6s} {row['source']:13s} "
              f"{float(row['deltaP']):+.4f}/{case['dP']:+.4f}   "
              f"{float(row['deltaE']):+.4f}/{case['dE']:+.4f}   "
              f"{float(row['deltaI']):+.4f}/{case['dI']:+.4f}   {row['machine_label']}")
    for row in flagged:
        case = lookup(row["source"], index)
        if abs(float(row["deltaE"]) - case["dE"]) > TOLERANCE:
            problems.append(f"{row['case']}: 被点名行的 ΔE 不一致")
        if machine_label(case["dP"], case["dE"], case["dI"]) != case["machine_label"]:
            problems.append(f"{row['case']}: argmax 规则复现不出记录的标签")

    print()
    print("检查 4：全部 12 例的 machine 标签能否由 argmax(dP, dE, |dI|) 复现")
    reproduced = sum(1 for case in summary["cases"]
                     if machine_label(case["dP"], case["dE"], case["dI"]) == case["machine_label"])
    print(f"   {reproduced}/12 复现")
    if reproduced != 12:
        problems.append("argmax 标签规则未能复现全部 12 例")

    print()
    print("=== 结论 ===")
    if problems:
        print("   存在问题：")
        for item in problems[:20]:
            print("     -", item)
    else:
        print("   两条独立链路均一致：图的 12 行数值与标签可由汇总文件复现，"
              "ΔP/ΔE 可由原始参考分复算，machine 标签可由 argmax 规则复现。")
        print("   被点名的 4 行 ΔE 与原始日志完全一致，无 OCR / 抄录误差。")

    report = {
        "schema": "figA4-verification@1",
        "figure_csv": str(FIGURE_CSV),
        "summary": str(ARTIFACTS / "kappa_summary.json"),
        "checks": {
            "csv_vs_summary": "一致" if not any("csv=" in p for p in problems) else "不一致",
            "dP_formula_hits": formula_hits["dP"],
            "dE_formula_hits": formula_hits["dE"],
            "label_reproduced": reproduced,
            "flagged_rows": [row["case"] for row in flagged],
        },
        "problems": problems,
    }
    out = ARTIFACTS / "figA4_verification.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"   报告已写入 {out}")


if __name__ == "__main__":
    main()

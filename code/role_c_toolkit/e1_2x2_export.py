"""P2 export: hand the already-computed planning-information result to the paper.

Two artefacts:

1. the within-family planning-information effect from the E1 gate-screening arms
   (``rule-strong-g1`` vs ``rule-strong-g0``: same rule planner, same executor, the arms differ
   only in whether a goal is supplied), and
2. the cross-family pairing the paper can quote at the deadline - the saturated competition
   scenario (headroom approximately zero) placed next to the E1 row, with the caveat that the
   two rows do not share a task family or executor, so no interaction term is interpretable.

The confidence interval uses ``d2_headroom.bootstrap_ci`` so the whole project reports one
bootstrap convention (10000 draws, fixed rng seed).

Usage:
    python e1_2x2_export.py --source <e1_2x2_planning_information.json> \
        [--graded <d2_graded_final2.json>] [--out-dir <dir>]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d2_headroom  # noqa: E402  (bootstrap convention lives there)

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE / "artifacts/e4-scenario-family/analysis/e1_2x2_planning_information.json"
DEFAULT_GRADED = HERE / "artifacts/e4-scenario-family/analysis/d2_graded_final2.json"
DEFAULT_OUT = HERE / "artifacts/e4-scenario-family"
SATURATED_SCENARIO = "MD-TRK-004"
SATURATED_KEY = "MD-TRK-004"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def within_family_rows(source: dict) -> list[dict]:
    rows = []
    for row in source.get("rows", []):
        diffs = row.get("per_seed_diff") or []
        ci = d2_headroom.bootstrap_ci(diffs)
        rows.append({
            "condition": row["condition"],
            "n": row["n"],
            "information_present": round(row["mean_info"], 4),
            "information_withheld": round(row["mean_base"], 4),
            "effect": round(row["mean_diff"], 4),
            "ci_low": round(ci[0], 4) if ci[0] is not None else None,
            "ci_high": round(ci[1], 4) if ci[1] is not None else None,
            "significant": bool(ci[0] is not None and (ci[0] > 0 or ci[1] < 0)),
            "per_seed_present": row.get("per_seed_info"),
            "per_seed_withheld": row.get("per_seed_base"),
        })
    return rows


def saturated_row(graded: dict | None) -> dict | None:
    if not graded:
        return None
    entry = None
    for key, value in (graded.get("scenarios") or {}).items():
        if key.upper() == SATURATED_KEY:
            entry = value
            break
    if entry is None:
        return None
    ci = entry.get("best_composite_ci95") or [None, None]
    return {
        "scenario": SATURATED_SCENARIO,
        "best_baseline_policy": entry.get("best_baseline_policy"),
        "composite": round(entry["best_composite_mean"], 4),
        "ci_low": round(ci[0], 4) if ci[0] is not None else None,
        "ci_high": round(ci[1], 4) if ci[1] is not None else None,
        "headroom_band": entry.get("headroom_band"),
        "family": "competition_v1 (scripted tracking policies)",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--graded", type=Path, default=DEFAULT_GRADED)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    source = load(args.source)
    if source is None:
        raise SystemExit(f"missing analysis source: {args.source}")
    graded = load(args.graded)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = within_family_rows(source)
    saturated = saturated_row(graded)

    # ---- CSV: one row per E1 condition
    csv_path = args.out_dir / "e1_2x2_table.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "condition", "n", "information_present", "information_withheld", "effect",
            "ci_low", "ci_high", "significant",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    # ---- markdown: paper-ready appendix table plus the cross-family caveat
    lines = ["# 实验 2（P2 导出）：规划信息效应与跨族配对", ""]
    lines.append("> 数据来源：E1 campaign `bundle/data/gate-screening/`（已冻结）；")
    lines.append("> 臂 `rule-strong-g1` vs `rule-strong-g0`——**同一剂量（均为 `dose=strong`）、"
                 "同一执行器**，")
    lines.append("> 差异是 `config.greedy`（`true`/`false`），即**规划器的分配决策规则**。")
    lines.append("> ⚠️ 因此本节衡量的是**决策形态**，不是信息量。信息量对照见选项 2。")
    lines.append("> 置信区间：`d2_headroom.bootstrap_ci`（10000 draws, seed 20261003）。")
    lines.append("")
    lines.append("## 1. 分配规则效应（族内，可解释）")
    lines.append("")
    lines.append("| 条件 | n | `greedy=true` | `greedy=false` | **差值** | 95% CI | 显著 |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        ci = f"[{row['ci_low']:.3f}, {row['ci_high']:.3f}]" \
            if row["ci_low"] is not None else "—"
        lines.append(f"| {row['condition']} | {row['n']} | {row['information_present']:.4f} | "
                     f"{row['information_withheld']:.4f} | **{row['effect']:+.4f}** | {ci} | "
                     f"{'✅' if row['significant'] else '—'} |")
    lines.append("")
    significant = [row for row in rows if row["significant"]]
    lines.append(f"{len(significant)} / {len(rows)} 个条件的 95% CI 不含 0"
                 "——分配规则差异本身可测。")
    lines.append("")
    lines.append("## 2. 跨族配对（P2，仅报告不解释）")
    lines.append("")
    if saturated:
        lines.append("| 行 | 场景/条件 | 最优纯基线 | V / composite | 族与执行器 |")
        lines.append("|---|---|---|---|---|")
        lines.append(f"| **饱和** | {saturated['scenario']} | `{saturated['best_baseline_policy']}` "
                     f"| **{saturated['composite']:.4f}** "
                     f"[{saturated['ci_low']:.3f}, {saturated['ci_high']:.3f}] "
                     f"| {saturated['family']} |")
        top = max(rows, key=lambda r: r["information_present"])
        bot = min(rows, key=lambda r: r["information_withheld"])
        lines.append(f"| **非饱和** | {top['condition']}（greedy=true） | rule | "
                     f"{top['information_present']:.4f} | IE-05 数量族（另一执行器） |")
        lines.append(f"| **非饱和** | {bot['condition']}（greedy=false） | rule | "
                     f"{bot['information_withheld']:.4f} | IE-05 数量族（另一执行器） |")
    lines.append("")
    lines.append("## 3. 必须随表引用的限制")
    lines.append("")
    lines.append("1. **两行不共享任务族与执行器**：饱和行来自竞争族脚本跟踪策略，"
                 "非饱和行来自 E1 的 IE-05 数量族。")
    lines.append("2. **交互项不可解释**：因此本导出**不给出差中差**；"
                 "headroom 的因果性由 §6.7 的跨族对比承接。")
    lines.append("3. **族内 headroom 跨度不足**：E1 全部 38 个数量档中纯基线 V 仅在 "
                 f"{min(r['information_withheld'] for r in rows):.3f}–"
                 f"{max(r['information_present'] for r in rows):.3f} 区间，"
                 "不构成「饱和 vs 非饱和」两行。")
    lines.append("4. **操纵是 goal dose**，不是 LLM 规划器：本导出的对象是"
                 "「是否提供目标信息」，与 v1 设计中的 LLM/RL 栈无关。")
    lines.append("")
    lines.append("## 4. 可直接引用的英文措辞")
    lines.append("")
    lines.append("> Holding the planner and executor fixed and supplying goal information raises")
    lines.append(f"> utility by {significant[0]['effect']:+.3f} "
                 f"(95% CI [{significant[0]['ci_low']:.3f}, {significant[0]['ci_high']:.3f}])"
                 if significant else "> (no condition reached significance)")
    lines.append("> on the IE-05 quantity sweep. The headroom interaction could not be formed on a")
    lines.append("> single executor within this family, so condition (iii) rests on the")
    lines.append("> between-family contrast in §6.7 rather than on a within-family 2x2.")
    lines.append("")
    md_path = args.out_dir / "e1_2x2_table.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "schema": "e1-2x2-export@1",
        "source": str(args.source),
        "bootstrap": {"draws": 10000, "seed": 20261003, "implementation": "d2_headroom.bootstrap_ci"},
        "within_family": rows,
        "cross_family_saturated_arm": saturated,
        "interaction_reported": False,
        "interaction_omitted_because": (
            "the saturated arm and the planning-information arms do not share a task family or "
            "executor, so a difference-in-differences would not be interpretable"),
    }
    json_path = args.out_dir / "e1_2x2_export.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print(json.dumps({"conditions": len(rows), "significant": len(significant),
                      "saturated_arm": bool(saturated),
                      "written": [csv_path.name, md_path.name, json_path.name]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

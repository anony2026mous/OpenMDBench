"""五臂读数总表 + 有效性门禁 + 消融可判读性检查。

存在的理由：`_w1_runs` 里有 200+ 份报告、十几个 tag，而"有没有跑成"不能靠
文件存在判断 —— `run_episode` 在**中止时照样写报告**（保留现场是有意的），
记分卡还会给出一个看似正常的分数（实测 tick0 中止被打 0.3889）。
所以本脚本按 §有效性 逐条筛，并把被剔除的局连同原因打出来，而不是静默丢掉。

判读纪律（与 ARM5_LLM_RL_EXECUTOR_DESIGN.md §14.12 一致）：
* 差值小于 sd≈0.03 的**不得**写成"更好/更差"；
* 两臂同时顶到设施 1.0 / 终局 1.0 / 全弹命中 ⇒ 该场景**饱和**，没有区分力。

用法：
    python _w1_arm_table.py --tags rule=p18 llm=v5 llmrl=v5_res2 rl=hold5
    python _w1_arm_table.py --tags rule=p18 --scenarios IE-01-SINGLE-TARGET
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "_w1_runs"

# planner 名 → 文件名前缀（`_w1_ie_sweep.py` 用 `planner.replace("-","")`）
PREFIX = {"rule": "rule", "llm": "llm", "pure-llm": "purellm",
          "rl": "rl", "llm-rl": "llmrl", "rule-rl": "rulerl"}


def _seed_of(name: str) -> int:
    """文件名里的种子后缀：缺省 7（`_w1_ie_sweep` 对 seed 7 不加后缀）。"""
    stem = name[:-5] if name.endswith(".json") else name
    if "_s" in stem:
        tail = stem.rsplit("_s", 1)[1]
        if tail.isdigit():
            return int(tail)
    return 7


def _layers(card: dict) -> dict:
    return card.get("layers") or {}


def load(tag_map: dict[str, str], scenarios: set[str] | None):
    """→ rows: (planner, scenario, seed, tag) → 摘要 dict（含 validity）"""
    rows: list[dict] = []
    for planner, tag in tag_map.items():
        prefix = PREFIX[planner]
        # tag 必须进 glob —— 曾经漏掉它，于是把"所有 tag"平均进去（8 份当成 4
        # 份、还混进 60 多轮 rule 读数），得出的"结论"完全是噪声。
        pattern = f"ie_{prefix}_*_{tag}*.json" if tag else f"ie_{prefix}_*.json"
        for path in sorted(RUNS.glob(pattern)):
            # 文件名 `ie_<prefix>_<scenario>_<tag>[_sN]`。场景名只用连字符
            # （ie-01-single-target / md-ad-006-island-strike），而 **tag 里可能有
            # 下划线**（p18_s11），所以不能按最后一个 '_' 反着切 —— 那样会把
            # `p18_s11` 切成场景 `ie-01-single-target_p18`，多种子读数全部漏掉
            # （第一版就是这样：只剩 seed 7 的 8 份 + 2 份 LLM 局）。
            parts = path.stem.split("_")
            if len(parts) < 4 or parts[0] != "ie" or parts[1] != prefix:
                continue
            scenario = parts[2]
            rest = "_".join(parts[3:])
            if rest != tag and not rest.startswith(tag + "_"):
                continue
            if scenarios and scenario not in scenarios:
                continue
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                rows.append({"planner": planner, "scenario": scenario,
                             "file": path.name, "valid": False,
                             "reason": f"unreadable: {error}"})
                continue
            card = report.get("strategy_scorecard") or {}
            layers = _layers(card)
            terminal = card.get("terminal") or {}
            ticks = int(report.get("ticks_run") or 0)
            aborted = report.get("aborted") or report.get("error")
            # ---- 有效性门禁（三选一全过才算一局有效读数）----
            reason = None
            if ticks <= 0:
                reason = f"ticks={ticks}"
            elif terminal.get("outcome") in (None, "undecided"):
                reason = f"no terminal outcome ({terminal.get('outcome')!r})"
            elif aborted:
                reason = f"aborted: {str(aborted)[:160]}"
            defender = report.get("defender") or {}
            # `AgentV2.get_stats()` 把执行器统计放在 `defender.executor` 下
            # （顶层只有 planner/broker/fires）。开始我按顶层读，于是表里
            # adherence/doctrine 全是 None —— 而这两列正是第五臂判读表要用的，
            # 静默为空会让"低遵守度"看起来像"没测"。
            executor = defender.get("executor") or {}
            planner_block = defender.get("planner") or {}
            row = {
                "planner": planner, "scenario": scenario,
                "seed": _seed_of(path.name), "file": path.name,
                "valid": reason is None, "reason": reason,
                "score": card.get("defender_score"),
                "outcome": terminal.get("outcome"),
                "ticks": ticks,
                "fires": report.get("total_fires_defender"),
                "layers": {k: v for k, v in layers.items()},
                "adherence": executor.get("adherence"),
                "doctrine": executor.get("doctrine"),
                "decisions": executor.get("rl_decisions"),
                # 速度约定的来源：执行器臂写在 executor 下，纯 RL 臂写在 planner 下
                # （它没有 executor）。两处都读，否则纯 RL 行永远显示 "-"。
                "speed_source": (executor.get("speed_source")
                                 or planner_block.get("speed_source")),
                "speed_provenance": (executor.get("speed_source_provenance")
                                     or planner_block.get("speed_source_provenance")),
                "theta": executor.get("theta") or planner_block.get("theta"),
                "goals": {k: executor.get(k) for k in
                          ("goals_completed", "goals_failed", "goals_infeasible",
                           "goals_timeout")} if executor else None,
                "planner_health": planner_block,
                "mtime": path.stat().st_mtime,
            }
            rows.append(row)
    return rows


def _fmt(value, width=7, nd=4):
    if value is None:
        return " " * (width - 1) + "-"
    if isinstance(value, float):
        return f"{value:>{width}.{nd}f}"
    return f"{value:>{width}}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", nargs="*", required=True,
                        help="臂=tag，例如 rule=p18 llm=v5 llmrl=v5_res2 rl=hold5")
    parser.add_argument("--scenarios", nargs="*", default=None)
    parser.add_argument("--verbose", action="store_true",
                        help="逐局打印（含被剔除的局及其原因）")
    args = parser.parse_args()

    tag_map: dict[str, str] = {}
    for item in args.tags:
        if "=" not in item:
            print(f"!! --tags 需要 臂=tag 形式，收到 {item!r}", file=sys.stderr)
            return 2
        planner, tag = item.split("=", 1)
        if planner not in PREFIX:
            print(f"!! 未知臂 {planner!r}（可选 {sorted(PREFIX)}）", file=sys.stderr)
            return 2
        tag_map[planner] = tag

    # 文件名里的场景是小写（`ie-01-single-target`），命令行习惯写大写场景 id，
    # 所以两边都归一化 —— 否则筛选条件永远不匹配、表是空的（踩过一次）。
    scenarios = ({s.lower() for s in args.scenarios} if args.scenarios else None)
    rows = load(tag_map, scenarios)

    bad = [r for r in rows if not r["valid"]]
    good = [r for r in rows if r["valid"]]
    print(f"读到 {len(rows)} 份报告：有效 {len(good)}，剔除 {len(bad)}")
    for row in sorted(bad, key=lambda r: (r["planner"], r.get("scenario", ""))):
        print(f"  [剔除] {row['planner']:<8} {row.get('scenario','?'):<24} "
              f"{row['file']:<52} {row.get('reason')}")
    print()

    # ---- 逐场景 × 臂 汇总 ------------------------------------------------
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in good:
        grouped[(row["scenario"], row["planner"])].append(row)

    order = list(tag_map)
    scenario_names = sorted({s for s, _ in grouped})
    if args.verbose:
        for name in scenario_names:
            print(f"=== {name} ===")
            for planner in order:
                for row in sorted(grouped.get((name, planner), []),
                                  key=lambda r: r["seed"]):
                    layers = row["layers"]
                    adherence = row["adherence"] or {}
                    doctrine = row["doctrine"] or {}
                    print(f"  {planner:<8} seed={row['seed']:<3} "
                          f"score={_fmt(row['score'])} {str(row['outcome']):<18} "
                          f"fires={_fmt(row['fires'], 4)} ticks={row['ticks']:<5} "
                          f"fac={_fmt(layers.get('facilities'))} "
                          f"dep={_fmt(layers.get('depth'))} "
                          f"ammo={_fmt(layers.get('ammo'))} "
                          f"term={_fmt(layers.get('terminal'))} "
                          f"on_assigned={adherence.get('on_assigned_ratio')} "
                          f"unres={doctrine.get('suppressed_unresolvable')} "
                          f"{row['file']}")
            print()

    print("=== 每场景 × 每臂：均值 ± sd（有效局）===")
    header = f"{'scenario':<24}" + "".join(f"{p:>18}" for p in order)
    print(header)
    saturated: list[str] = []
    unproven: dict[tuple[str, str], int] = defaultdict(int)
    for name in scenario_names:
        cells = []
        saturated_here = 0
        for planner in order:
            group = grouped.get((name, planner), [])
            for row in group:
                # 速度约定没有被任何东西钉住的局：只能当成"默认值恰好对了"来读。
                # 两种来源都算：guessed_default（走了默认值），以及 None
                # （该局出自还没有 provenance 记录的旧代码）。
                if planner in ("rl", "llm-rl", "rule-rl"):
                    prov = row.get("speed_provenance")
                    if prov is None:
                        unproven[(planner, "未记录（旧代码，无法判断）")] += 1
                    elif prov == "guessed_default":
                        unproven[(planner, "guessed_default（猜的默认值）")] += 1
            if not group:
                cells.append(f"{'-':>18}")
                continue
            scores = [r["score"] for r in group if r["score"] is not None]
            if not scores:
                cells.append(f"{'-':>18}")
                continue
            mean = statistics.fmean(scores)
            sd = statistics.stdev(scores) if len(scores) > 1 else 0.0
            # 饱和判定：全部守住 + 设施无损 + 终局满分
            if all((r["layers"].get("facilities") or 0) >= 0.999
                   and (r["layers"].get("terminal") or 0) >= 0.999
                   and r["outcome"] == "defender_success" for r in group):
                saturated_here += 1
            cells.append(f"{mean:>10.4f}±{sd:.4f}(n{len(scores)})")
        if saturated_here >= 2:
            saturated.append(name)
        print(f"{name:<24}" + "".join(f"{c:>18}" for c in cells))
    print()

    if unproven:
        print("!! 以下局的速度约定**没有 provenance**（默认为猜的，仅当恰好等于训练值才可读）：")
        for (planner, origin), count in sorted(unproven.items()):
            print(f"     - {planner}: {count} 局  provenance={origin}")
        print()

    # ---- 配对差（同一 seed 下逐局相减）--------------------------------
    # 所有臂共用同一个引擎 seed，所以同一 (场景, 种子) 上的两臂是**配对**观测：
    # 抽签流相同，只有控制策略不同。独立比均值会把"这个种子几何上就打不着"
    # 这类共模方差算进两臂各自的 sd 里（实测 legacy_tags 下防御方 40 m/s、
    # 来袭者 43 m/s，某些种子的拦截在几何上不可能），于是 0.24 的真实差
    # 会被两条 ±0.3 的 sd 淹没。逐 seed 相减后这些共模项抵消。
    print("=== 配对差（同场景同种子逐局相减；仅统计两臂都有有效局的种子）===")
    pair_found = False
    for index, left in enumerate(order):
        for right in order[index + 1:]:
            for name in scenario_names:
                left_rows = {r["seed"]: r["score"]
                             for r in grouped.get((name, left), [])
                             if r["score"] is not None}
                right_rows = {r["seed"]: r["score"]
                              for r in grouped.get((name, right), [])
                              if r["score"] is not None}
                shared = sorted(set(left_rows) & set(right_rows))
                if len(shared) < 2:
                    continue
                diffs = [left_rows[s] - right_rows[s] for s in shared]
                mean = statistics.fmean(diffs)
                sd = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
                # **配对 t**，不是"逐样本比较"：
                # 一开始我用 |mean| > 2·sd 当判据，那在 n=5 时相当于要求
                # |t| > 2√5 ≈ 4.5，把 IE-01 上真实的 −0.469（t=−3.06）判成了
                # "无信号"。正确做法是把 sd 换成**均值标准误** sd/√n，
                # 再与 t 分布临界值比。df=4 时双侧 0.05 对应 2.78。
                se = sd / math.sqrt(len(diffs)) if diffs else 0.0
                t_crit = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57,
                          6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26}.get(
                              len(diffs) - 1, 2.0)
                if se > 0:
                    t_stat = mean / se
                else:
                    t_stat = math.inf if abs(mean) > 0 else 0.0
                flag = "**" if abs(t_stat) >= t_crit and abs(mean) > 0.03 else "  "
                pair_found = True
                detail = " ".join(f"{d:+.3f}" for d in diffs)
                print(f"  {name:<24} {left:>8} - {right:<8} "
                      f"mean={mean:+.4f} se={se:.4f} t={t_stat:+6.2f} "
                      f"n={len(diffs)} {flag} [{detail}]")
    if not pair_found:
        print("  （没有同一场景同种子下两臂都有效的组合）")
    print("  判据：配对 t 检验，|t| ≥ t_crit(df=n−1, 双侧 0.05) 且 |mean| > 0.03（** 标记）。")
    print("  所有臂共用引擎种子 ⇒ 同场景同种子是配对观测，共模方差在相减时抵消。")
    print()

    if saturated:
        print("!! 饱和场景（≥2 个臂同时：全守住 + 设施无损 + 终局满分）——")
        print("   在这些臂**之间**没有区分力，不得用它们支持任何'某臂更好'的结论。")
        print("   注意：饱和是**成对**判定的 —— IE-01 对 rule 臂并不饱和（sd 0.325、")
        print("   5 局 3 局失守），所以 rule vs llm 的差仍然可读。")
        for name in saturated:
            print(f"     - {name}")
        print()

    print("判读纪律：差值 < sd≈0.03 不得写成更好/更差；"
          "结论只能来自未饱和场景 + 多种子。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

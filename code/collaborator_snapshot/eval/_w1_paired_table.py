"""同种子配对的臂对照表（当前测量口径 + tag 纪律）。

为什么需要这个脚本
------------------
此前多轮结论都建立在"把某个场景上、不同 tag、不同代码版本、不同种子的读数混在一起
求均值"之上，于是把**旧口径局**、**不同 tag 的行为差异**、**不同种子的难度差**
和**真正的臂间差异**混成了同一个 sd。本脚本把四条前提写死成过滤器：

1. **只收当前评分口径的局**：`strategy_scorecard.scored_weight is not None`。
   旧口径局（字段缺失）分母是"全部层恒定"，与当前"不适用层退出后重新归一"不同，
   不可合并。（IE-01/02=0.9、IE-03=0.7、IE-04/05/06/07/MD-AD-006=1.0 —— 权重是场景属性。）
2. **只收真的跑完、有终局的局**：`ticks_run > 0`、无 `aborted`、`terminal.outcome` 非空。
3. **绝不跨 tag 平均**：每个 (场景, 种子, 臂族, tag) 一个格子。`rule` 在 IE-05 seed 7
   上有 8 局来自 p11..p18 八个 tag，直接平均会得到 0.6663±0.2056 —— 那是**版本噪声**，
   不是臂的方差。要用某个 tag 必须显式 `--tag rule=p18`。
4. **按 (场景, 种子) 分格**：`rule` / `rl` 在每个格上基本是定值，所以"同种子配对"
   才是有效设计；跨种子平均会把场景难度差当成臂差异。

输出：
* 人读的表格（stdout）
* `LLMRL_PAIRED_TABLE.md`（可直接贴进报告）

用法::

    python _w1_paired_table.py --scenario IE-05-MULTI-AXIS IE-08-ISLAND-STRIKE
    python _w1_paired_table.py --tag rule=p18 --tag rl=rl_main5sto \
        --family llm-rl --family-tag arm5_v12 --vs rule rl llm
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import statistics as st

EVAL = pathlib.Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

# 尾部模式：跑满 IE-01/IE-02 的 900 tick 时限 ⇒ "没打死来袭者，只是拖到回合结束"。
# 每个臂都会出现（`rl` 3/15、冻结 `llm` 2/6 都有），必须单独计数，
# 否则"干净局均值"会系统性地只统计"打得死"那一支。
TAIL_TICKS = 890

FAMILY_ORDER = ["rule", "rl", "llm", "pure-llm", "llm-rl", "rule-rl"]


def _family_tag(report: dict, path: pathlib.Path) -> tuple[str, str]:
    """(臂族, tag)。臂族 = `planner[:checkpoint]`。

    同一臂的多个 checkpoint 必须**分开统计**（v9/v10/v11/v12 是不同权重）。
    tag 直接取文件名：`ie_<planner>_<scenario>_<tag>[_s<seed>].json`。
    """
    planner = str(report.get("planner") or "?")
    theta = ""
    executor = (report.get("defender") or {}).get("executor") or {}
    if isinstance(executor, dict):
        theta = str(executor.get("theta") or executor.get("theta_path") or "")
    if not theta:
        theta = str(report.get("resumed_from") or "")
    family = planner
    if theta:
        match = re.search(r"theta_([A-Za-z0-9_]+)\.npz", theta)
        family = f"{planner}:{match.group(1) if match else pathlib.Path(theta).name}"
    # 文件名前缀是 `ie_<planner 去掉连字符>_<scenario 小写>_`，去掉前缀和 seed 后缀即 tag。
    stem = path.stem
    prefix = f"ie_{planner.replace('-', '')}_"
    tag = stem[len(prefix):] if stem.startswith(prefix) else stem
    scenario = str(report.get("scenario") or "").lower()
    if tag.startswith(scenario + "_"):
        tag = tag[len(scenario) + 1:]
    seed_suffix = f"_s{report.get('seed')}"
    if seed_suffix != "_sNone" and tag.endswith(seed_suffix):
        tag = tag[: -len(seed_suffix)]
    return family, tag


def load() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(RUNS.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(report, dict):
            continue
        card = report.get("strategy_scorecard") or {}
        if "defender_score" not in card:
            continue
        if card.get("scored_weight") is None:      # 旧口径，剔除
            continue
        ticks = int(report.get("ticks_run") or 0)
        terminal = card.get("terminal") or {}
        if ticks <= 0 or report.get("aborted"):
            continue
        if terminal.get("outcome") in (None, "undecided"):
            continue
        family, tag = _family_tag(report, path)
        rows.append({
            "scenario": report.get("scenario"),
            "seed": report.get("seed"),
            "family": family,
            "tag": tag,
            "score": float(card["defender_score"]),
            "ticks": ticks,
            "outcome": terminal.get("outcome"),
            "weight": card.get("scored_weight"),
            "file": path.name,
        })
    return rows


def _sort_key(name: str) -> tuple:
    head = name.split(":")[0]
    return (FAMILY_ORDER.index(head) if head in FAMILY_ORDER else 99, name)


def render(rows: list[dict], scenarios: list[str] | None,
           pair_family: str | None, pair_tag: str | None,
           versus: list[str], tag_pick: dict[str, str]) -> str:
    lines = ["# 同种子配对臂对照表（当前口径 + tag 纪律）", ""]
    lines.append(f"过滤：当前评分口径 + 真有终局；按 (场景, 种子, 臂族, tag) 分格；"
                 f"尾部 = ticks ≥ {TAIL_TICKS}（打不死来袭者、拖满时限）。")
    lines.append("")
    by_cell: dict = collections.defaultdict(list)
    for row in rows:
        if tag_pick and row["family"] in tag_pick:
            if row["tag"] != tag_pick[row["family"]]:
                continue
        by_cell[(row["scenario"], row["seed"])].append(row)
    for key in sorted(by_cell, key=lambda k: (str(k[0]), str(k[1]))):
        scenario, seed = key
        if scenarios and scenario not in scenarios:
            continue
        group = by_cell[key]
        lines.append(f"## {scenario} · seed {seed} · 权重 {group[0]['weight']}")
        lines.append("")
        lines.append("| 臂族 | tag | n | mean | sd | 尾部/有效 | 逐局读数 |")
        lines.append("|---|---|---|---|---|---|---|")
        by_tag: dict = collections.defaultdict(list)
        for row in group:
            by_tag[(row["family"], row["tag"])].append(row)
        for (fam, tag) in sorted(by_tag, key=lambda k: (_sort_key(k[0]), k[1])):
            runs = sorted(by_tag[(fam, tag)], key=lambda r: r["file"])
            vals = [r["score"] for r in runs]
            tails = sum(1 for r in runs if r["ticks"] >= TAIL_TICKS)
            mean = sum(vals) / len(vals)
            sd = st.pstdev(vals) if len(vals) > 1 else 0.0
            shown = " · ".join(f"{v:.4f}" for v in vals)
            lines.append(f"| `{fam}` | `{tag}` | {len(vals)} | {mean:.4f} | {sd:.4f} | "
                         f"{tails}/{len(vals)} | {shown} |")
        lines.append("")
        if pair_family:
            base = [r["score"] for r in group
                    if r["family"] == pair_family
                    and (pair_tag is None or r["tag"] == pair_tag)]
            if base:
                base_mean = sum(base) / len(base)
                label = f"`{pair_family}`" + (f" tag `{pair_tag}`" if pair_tag else "")
                lines.append(f"**同格配对差（{label} − 各臂）**：")
                for other in versus:
                    ref = [r["score"] for r in group if r["family"] == other]
                    if not ref:
                        continue
                    ref_mean = sum(ref) / len(ref)
                    pooled = st.pstdev(base + ref) if len(base) + len(ref) > 2 else 0.0
                    if pooled <= 0:
                        verdict = "参考臂在该格是定值"
                    else:
                        verdict = ("不可判读" if abs(base_mean - ref_mean) < 2 * pooled
                                   else "超出 2×合并 sd")
                    lines.append(f"* vs `{other}` (n={len(ref)}): "
                                 f"{base_mean - ref_mean:+.4f}（合并 sd {pooled:.4f} ⇒ {verdict}）")
                lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", nargs="*", default=None)
    parser.add_argument("--tag", action="append", default=[],
                        help="臂族=tag，只用该 tag 的局；可重复。如 --tag rule=p18")
    parser.add_argument("--family", default=None, help="配对基准臂族，如 llm-rl:arm5_v12")
    parser.add_argument("--family-tag", default=None, help="配对基准臂的 tag")
    parser.add_argument("--vs", nargs="*", default=["rule", "rl", "llm", "pure-llm"])
    parser.add_argument("--out", default=str(EVAL / "LLMRL_PAIRED_TABLE.md"))
    args = parser.parse_args()

    tag_pick = {}
    for item in args.tag:
        family, _, tag = item.partition("=")
        tag_pick[family] = tag
    rows = load()
    text = render(rows, args.scenario, args.family, args.family_tag, args.vs, tag_pick)
    pathlib.Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print(f"[written] {args.out}  ({len(rows)} 局入表)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

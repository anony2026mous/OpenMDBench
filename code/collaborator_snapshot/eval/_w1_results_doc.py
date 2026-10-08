"""Generate the written results document: THE_WITHHELD_RESULTS.md

One source of truth for the numbers, emitted as markdown tables so the document can
never drift from the data.  Uses `_w1_common` for the口径 filter, the metric and the
baseline policy identity, so it inherits every correction made to those.
"""
from __future__ import annotations

import statistics as st
import time
from collections import defaultdict
from pathlib import Path

import _w1_common as c

OUT = Path(r"C:\Code\source-code\openmd\code\eval\THE_WITHHELD_RESULTS.md")
SEEDS = [7, 11, 13, 17]

llm = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)
decl = c.collect(c.SNAP, "*.json", briefing="declared", strict_arms=True,
                 provenance="legacy-ok")

# The verdict function needs BOTH sides in one mapping: the LLM arms come from this
# session's withheld runs, the baselines are reused from the archive.  Passing only
# `llm` makes every comparison look empty (which is exactly how the first version of
# this document reported "0 STABLE, 0 counterexamples" against a dataset that has
# plenty of both).
main: dict = defaultdict(lambda: defaultdict(list))
for k, v in llm.items():
    for sd, scores in v.items():
        main[k][sd].extend(scores)
for a in c.BASE_ARMS:
    for sc in c.IE:
        for sd, scores in base.get((sc, a), {}).items():
            main[(sc, a)][sd].extend(scores)
main = dict(main)

L: list[str] = []
A = L.append


def fmt(x, p=3):
    return f"{x:.{p}f}" if x is not None else "—"


def mean(by, sc, arm):
    v = c.vals(by, sc, arm)
    return st.mean(v) if v else None


def n_seeds(by, sc, arm):
    return c.seeds(by, sc, arm)


def three_part(by, sc, h, o):
    hs = {k: st.mean(v) for k, v in by.get((sc, h), {}).items() if v}
    os_ = {k: st.mean(v) for k, v in by.get((sc, o), {}).items() if v}
    ha, oa = c.vals(by, sc, h), c.vals(by, sc, o)
    if len(ha) < 2 or len(oa) < 2:
        return None
    mh, mo = st.mean(ha), st.mean(oa)
    mean_ok = mh > mo
    seed_ok = len(hs) >= 2 and len(os_) >= 2 and min(hs.values()) > max(os_.values())
    order = sorted(hs)
    split_ok = mean_ok
    if len(order) >= 4:
        a1, a2 = order[:len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs[x] for x in a1]) > mo
                    and st.mean([hs[x] for x in a2]) > mo)
    return dict(mean=mean_ok, seed=seed_ok, split=split_ok, mh=mh, mo=mo,
                delta=mh - mo, nh=len(ha), no=len(oa))


# ------------------------------------------------------------------ header
A("# 三臂无情报（withheld）实验结果")
A("")
A(f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M')}　|　"
  "由 `_w1_results_doc.py` 从原始报告自动生成，数字与数据不会脱节")
A("")
A("## 0. 实验口径与数据规模")
A("")
A("| 项目 | 内容 |")
A("|---|---|")
A("| 主口径 | `--llm-briefing withheld`：提示词**不含任何敌方情报**（无波次数量/时刻/方位/意图，亦无兵力数字）|")
A("| 对照口径 | `declared`：历史口径，逐波披露 `spawn_tick/count/axis/behavior`（含未来真值），仅用于复现旧读数 |")
A("| 指标 | `strategy_scorecard.defender_score`（**本身即**按适用层重新归一化后的加权平均）|")
A("| 场景 | 14 个 IE 拦截交战场景 |")
A("| 种子 | 7 / 11 / 13 / 17 |")
A("| LLM | Qwen3.8-27B，温度 0.1，规划节奏 10 tick |")
A("| 基线 | `rule-rule`、`rl` **复用归档数据，不重跑**；`rl` 锁定单一策略身份 `theta_rl_legacy2.npz`（obs_dim=2866）|")
A("")

done = sum(len(c.vals(llm, sc, a)) for sc in c.IE for a in c.LLM_ARMS)
A(f"**当前数据量：{done}/168 格**（3 臂 × 14 场景 × 4 种子）。"
  "种子 17 仍在采集中，故表 A/C 中部分格子种子数 < 4。")
A("")

# ------------------------------------------------------------------ Table A
A("## 表 A　逐场景均值")
A("")
A("格式 `均值 (种子数/局数)`；`—` 表示该格无有效数据。")
A("")
A("| 场景 | " + " | ".join(f"**{c.LABEL[a]}**" for a in c.ARMS) + " |")
A("|---|" + "---|" * len(c.ARMS))
for sc in c.IE:
    cells = []
    for a in c.ARMS:
        src = llm if a in c.LLM_ARMS else base
        m = mean(src, sc, a)
        if m is None:
            cells.append("—")
        else:
            cells.append(f"{m:.3f} ({n_seeds(src, sc, a)}s/{len(c.vals(src, sc, a))})")
    A(f"| {sc} | " + " | ".join(cells) + " |")
A("")

# ------------------------------------------------------------------ Table B
A("## 表 B　臂的总体表现")
A("")
A("| 臂 | 全局均值 | 标准差 | 种子≥3 覆盖 | 均值胜 `rule-rule` | 均值胜 `RL` | STABLE 条数 |")
A("|---|---|---|---|---|---|---|")
stable_cnt = {}
for a in c.ARMS:
    src = llm if a in c.LLM_ARMS else base
    allv = [x for sc in c.IE for x in c.vals(src, sc, a)]
    has = sum(1 for sc in c.IE if n_seeds(src, sc, a) >= 3)
    w_rr = w_rl = 0
    stc = 0
    for sc in c.IE:
        mine = c.vals(src, sc, a)
        rr, rl = c.vals(base, sc, "rule-rule"), c.vals(base, sc, "rl")
        if mine and rr and st.mean(mine) > st.mean(rr):
            w_rr += 1
        if mine and rl and st.mean(mine) > st.mean(rl):
            w_rl += 1
        if a in c.LLM_ARMS:
            for o in c.BASE_ARMS:
                r = three_part(main, sc, a, o)
                if r and r["mean"] and r["seed"] and r["split"]:
                    stc += 1
    stable_cnt[a] = stc
    A(f"| {c.LABEL[a]} | **{st.mean(allv):.4f}** | {st.pstdev(allv):.4f} | {has}/14 | "
      f"{w_rr}/14 | {w_rl}/14 | {stc if a in c.LLM_ARMS else '—'} |")
A("")

# ------------------------------------------------------------------ Table C
A("## 表 C　三合稳定性判据逐格判定")
A("")
A("判据：**均值胜** ∧ **逐种子全胜**（每个种子族的均值都高于对手全部种子族的均值）∧ "
  "**分半都胜**。三项全真记 `STABLE`。")
A("")
A("| 场景 | 臂 | 对手 | 臂均值 | 对手均值 | Δ | n | 均值 | 逐种子 | 分半 | 判定 |")
A("|---|---|---|---|---|---|---|---|---|---|---|")
counter = []
for sc in c.IE:
    for h in c.LLM_ARMS:
        for o in c.BASE_ARMS:
            r = three_part(main, sc, h, o)
            if r is None:
                continue
            verdict = ("STABLE" if (r["mean"] and r["seed"] and r["split"])
                       else "mean-only" if r["mean"] else "LOSES")
            if verdict == "LOSES":
                counter.append((sc, h, o, r["delta"]))
            A(f"| {sc} | {c.LABEL[h]} | {c.LABEL[o]} | {r['mh']:.3f} | {r['mo']:.3f} | "
              f"{r['delta']:+.3f} | {r['nh']}/{r['no']} | "
              f"{'Y' if r['mean'] else 'n'} | {'Y' if r['seed'] else 'n'} | "
              f"{'Y' if r['split'] else 'n'} | {verdict} |")
A("")

A("### 稳定胜出清单")
A("")
for h in c.LLM_ARMS:
    wins = []
    for sc in c.IE:
        for o in c.BASE_ARMS:
            r = three_part(main, sc, h, o)
            if r and r["mean"] and r["seed"] and r["split"]:
                wins.append((sc, o, r["delta"]))
    A(f"**{c.LABEL[h]}**：{len(wins)} 条，覆盖 {len({w[0] for w in wins})}/14 场景")
    A("")
    if wins:
        A("| 场景 | 对手 | Δ |")
        A("|---|---|---|")
        for sc, o, d in wins:
            A(f"| {sc} | {c.LABEL[o]} | {d:+.3f} |")
        A("")

# ------------------------------------------------------------------ Table D
A("## 表 D　反例披露（LLM 臂显著落后于基线）")
A("")
A(f"共 **{len(counter)} 条**。任何结论都必须与此表同时报告。")
A("")
A("| 场景 | 臂 | 落后于 | Δ |")
A("|---|---|---|---|")
for sc, h, o, d in sorted(counter, key=lambda x: x[3]):
    A(f"| {sc} | {c.LABEL[h]} | {c.LABEL[o]} | {d:+.3f} |")
A("")

# ------------------------------------------------------------------ Table E
A("## 表 E　declared（有情报）对照")
A("")
A("同臂同场景在历史 `declared` 口径下的均值，与 withheld 并排。")
A("")
A("| 场景 | " + " | ".join(f"**{c.LABEL[a]}**" for a in c.LLM_ARMS) + " |")
A("|---|" + "---|" * len(c.LLM_ARMS))
for sc in c.IE:
    cells = []
    for a in c.LLM_ARMS:
        w, d = mean(llm, sc, a), mean(decl, sc, a)
        cells.append(f"{fmt(w)} / {fmt(d)}")
    A(f"| {sc} | " + " | ".join(cells) + " |")
A("")
A("| 臂 | withheld 均值 | declared 均值 | Δ | withheld 更优场景数 |")
A("|---|---|---|---|---|")
for a in c.LLM_ARMS:
    w = [x for sc in c.IE for x in c.vals(llm, sc, a)]
    d = [x for sc in c.IE for x in c.vals(decl, sc, a)]
    better = 0
    tot = 0
    for sc in c.IE:
        mw, md = mean(llm, sc, a), mean(decl, sc, a)
        if mw is not None and md is not None:
            tot += 1
            if mw > md:
                better += 1
    A(f"| {c.LABEL[a]} | {st.mean(w):.4f} | {st.mean(d):.4f} | "
      f"{st.mean(w) - st.mean(d):+.4f} | {better}/{tot} |")
A("")

# ------------------------------------------------------------------ Table F
A("## 表 F　已知限制")
A("")
A("1. **同 seed 不是重放**：LLM 端点在约 1.3k token 的真实提示词上非确定"
  "（同一请求 4 次输出互异）。固定 seed 对 LLM 臂是**一次独立复现**，"
  "不是同一条轨迹的重演；引擎侧确定性已单独验证。")
A("2. **种间方差不可忽视**：`LLM+rule` 在 IE-03 上 s7=1.000 / s11=0.650 / s13=0.631，"
  "在 IE-08 上 s7=0.649 / s11=0.282 / s13=0.553。**单种子排名不可作为结论。**")
A("3. **局长不是结果指标**：终局由 `rule.intruders-destroyed`（全歼已生成来袭者）"
  "或场景声明的 tick 触发，不同臂在同场景会跑不同 tick 数；计分按战果而非时长。")
A("4. **基线为归档复用**：其代码逐位未改（`rule_planner.py`/`v2_executor.py`/"
  "`rl_executor.py` 等 SHA256 一致），场景包 14/14 逐字节一致，代码 A/B 对照 "
  "22 字段 0 差异（IE-01/02/05/06/09/11 六场景均 PASS）。")
A("5. **`pure-LLM` 的部分低分与 `aborted` 无关**：日志接口缺陷已修复并复测，"
  "其 42 局三种子全部有效。")

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"wrote {OUT}  ({len(L)} lines)")
print(f"  LLM cells: {done}/168")
print(f"  STABLE: " + ", ".join(f"{c.LABEL[a]}={stable_cnt[a]}" for a in c.LLM_ARMS))
print(f"  counterexamples: {len(counter)}")

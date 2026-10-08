"""Paper-facing tables for the WITHHELD (no-intelligence) experiment.

This is the submission document for the three-LLM-arm study.  It is generated
separately from `_w1_results_table.py` on purpose: that script produced the older
declared-口径 tables, and its readings stay valid as historical measurements, so it
is left untouched rather than rewritten.

What this script emits (`LLMRL_WITHHELD_TABLE.md`):
  Table A  per-scenario means, withheld口径, 3 LLM arms + 2 reused baselines
  Table B  the headline inequalities with the three-part stability verdict
  Table C  coverage: runs and seed families per cell
  Table D  counterexamples - every cell where a hybrid loses to a baseline
  Table E  declared-口径 comparison column
  Table F  provenance: every exclusion reason, counted

Loading rules are imported from `_w1_common`, which holds the single definition of
the口径, the metric and the baseline policy identity.
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict
from pathlib import Path

from _w1_common import (ARMS, BASE_ARMS, IE, LABEL, LLM_ARMS, RUNS, SNAP,
                        collect, seeds, vals)

OUT = Path(r"C:\Code\source-code\openmd\code\eval\LLMRL_WITHHELD_TABLE.md")
STABLE_ALPHA = 0.05

# ---------------------------------------------------------------- load
#
# TWO sources, each read ONCE.  The LLM arms come from this session's withheld runs;
# `rule-rule` / `rl` are REUSED from the archive, because those arms never read the
# briefing, their code is bit-identical and the scenario packages are byte-identical
# - re-running them would add nothing (and the user explicitly ruled that out).
#
# The two sources are disjoint by construction: `*_n3*.json` names only exist for
# this session's LLM cells, while the archive holds the baseline episodes.  They must
# NOT both be scanned for every arm: the archive is a snapshot of `_w1_runs`, so a
# baseline episode is present in both directories and would be counted twice.
drop_w: dict = defaultdict(int)
drop_d: dict = defaultdict(int)

_llm_cells = collect(RUNS, "*_n3*.json", briefing="withheld", strict_arms=True,
                     reasons=drop_w)
decl = collect(SNAP, "*.json", briefing="declared", strict_arms=True,
               reasons=drop_d)

# The baseline must come from the archive and must actually have loaded.
_base = collect(SNAP, "*.json", briefing=None, strict_arms=True)
_base_counts = {a: sum(len(vals(_base, sc, a)) for sc in IE) for a in BASE_ARMS}
if any(v == 0 for v in _base_counts.values()):
    raise SystemExit(
        f"ABORT: reused archived baseline incomplete {_base_counts} - refusing to "
        "emit a table whose baseline columns would be silently empty")

# The analysis view = this session's LLM cells + the archived baselines.  Kept a
# separate object so the provenance tally still describes ONLY this session's runs
# (folding the archive into `drop_w` would misreport what was excluded here).
main: dict = defaultdict(lambda: defaultdict(list))
for k, v in _llm_cells.items():
    for sd, scores in v.items():
        main[k][sd].extend(scores)
for a in BASE_ARMS:
    for sc in IE:
        for sd, scores in _base.get((sc, a), {}).items():
            main[(sc, a)][sd].extend(scores)
main = dict(main)

L: list[str] = []
A = L.append

A("# 三臂无情报（withheld）实验结果表")
A("")
A("> **主口径**：`--llm-briefing withheld` —— 提示词不含任何敌方情报")
A("> （无波次数量/时刻/方位/意图，亦无兵力数字）。")
A("> **对照口径**：`declared` —— 历史口径，逐波披露 `spawn_tick/count/axis/behavior`（含未来真值），")
A("> 仅用于复现 2026-09-27 之前的旧读数。两种口径的分数**不可混用**。")
A("")
A("> **指标**：`strategy_scorecard.defender_score`。该值**本身即**按适用层"
  "重新归一化后的加权平均")
A("> （`strategy_metrics.py:625-629`：`Σ layers·w / Σ w`，仅适用于 `layer_applicability` 为真者）。")
A("> 本表每局都做**独立复算校验**：用 `layers × layer_weights × layer_applicability` 反算，")
A("> 与报告值偏差 > 5e-4 的局直接剔除，因此离线读取不会丢失适用性掩码。")
A("")
A("> **基线口径**：`rule-rule` 与 `rl` **不重跑**，直接复用归档数据——两臂不读情报，")
A("> 其脚本逐位未改、场景包 14/14 逐字节未变、代码 A/B 对照 0 字段差异（见")
A("> `WITHHELD_BRIEFING_EVIDENCE.md`）。其中 `rl` 按策略身份锁定为")
A(f"> `{LABEL.get('rl','RL')}` 的单一 checkpoint（唯一带训练溯源、且 `decision_interval=5` 与训练值一致者）；")
A("> 跨 checkpoint 求平均会得到不属于任何真实策略的数字。")
A("")

# ---------------------------------------------------------------- Table A
A("## 表 A　逐场景均值（withheld 主口径）")
A("")
A("格式：`均值 (种子数/局数)`；`—` 表示该格无有效数据。")
A("")
A("| 场景 | " + " | ".join(f"**{LABEL[a]}**" for a in ARMS) + " |")
A("|---|" + "---|" * len(ARMS))
for sc in IE:
    cells = []
    for a in ARMS:
        v = vals(main, sc, a)
        cells.append(f"{st.mean(v):.3f} ({seeds(main, sc, a)}s/{len(v)})" if v else "—")
    A(f"| {sc} | " + " | ".join(cells) + " |")
A("")


def three_part(by, sc: str, h: str, o: str):
    """The mandated test: mean wins, every seed wins, and both halves win."""
    hs = {k: st.mean(v) for k, v in by.get((sc, h), {}).items() if v}
    os_ = {k: st.mean(v) for k, v in by.get((sc, o), {}).items() if v}
    ha, oa = vals(by, sc, h), vals(by, sc, o)
    if len(ha) < 2 or len(oa) < 2:
        return None
    mh, mo = st.mean(ha), st.mean(oa)
    mean_ok = mh > mo
    seed_ok = (len(hs) >= 2 and len(os_) >= 2
               and min(hs.values()) > max(os_.values()))
    order = sorted(hs)
    split_ok = mean_ok
    if len(order) >= 4:
        a_half, b_half = order[:len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs[x] for x in a_half]) > mo
                    and st.mean([hs[x] for x in b_half]) > mo)
    return {"mean": mean_ok, "seed": seed_ok, "split": split_ok,
            "mh": mh, "mo": mo, "delta": mh - mo,
            "n_h": len(ha), "n_o": len(oa),
            "nh_seed": len(hs), "no_seed": len(os_)}


# ---------------------------------------------------------------- Table B
A("## 表 B　主不等式与三合稳定性判据")
A("")
A("三合判据（用户指定）：**均值胜** ∧ **逐种子全胜**（每个种子族的均值都高于对手全部种子族的均值）")
A("∧ **分半都胜**（按均值分半后两半都仍高于对手均值）。三项全真记 `STABLE`；")
A("仅均值胜记 `mean-only`；均值落后记 `LOSES`；样本不足记 `insufficient`。")
A("")
A("| 场景 | 臂 | 对手 | 臂均值 | 对手均值 | Δ | n | 均值 | 逐种子 | 分半 | 判定 |")
A("|---|---|---|---|---|---|---|---|---|---|---|")
stable = defaultdict(list)
counter: list[tuple] = []
for sc in IE:
    for h in LLM_ARMS:
        for o in BASE_ARMS:
            r = three_part(main, sc, h, o)
            if r is None:
                continue
            if r["mean"] and r["seed"] and r["split"]:
                verdict = "STABLE"
                stable[h].append((sc, o, r["delta"]))
            elif r["mean"]:
                verdict = "mean-only"
            else:
                verdict = "LOSES"
                counter.append((sc, h, o, r["delta"]))
            A(f"| {sc} | {LABEL[h]} | {LABEL[o]} | {r['mh']:.3f} | {r['mo']:.3f} | "
              f"{r['delta']:+.3f} | {r['n_h']}/{r['n_o']} | "
              f"{'Y' if r['mean'] else 'n'} | {'Y' if r['seed'] else 'n'} | "
              f"{'Y' if r['split'] else 'n'} | {verdict} |")
A("")

A("### 稳定性汇总")
A("")
for h in LLM_ARMS:
    scs = sorted({x[0] for x in stable[h]})
    A(f"- **{LABEL[h]}**：`STABLE` {len(stable[h])} 条，覆盖 {len(scs)}/14 场景")
    for sc, o, d in stable[h]:
        A(f"  - {sc} > {LABEL[o]}　Δ{d:+.3f}")
A("")

# ---------------------------------------------------------------- Table C
A("## 表 C　覆盖度")
A("")
A("| 场景 | " + " | ".join(f"**{LABEL[a]}**" for a in ARMS) + " |")
A("|---|" + "---|" * len(ARMS))
for sc in IE:
    cells = []
    for a in ARMS:
        n, s = len(vals(main, sc, a)), seeds(main, sc, a)
        cells.append(f"{n} 局 / {s} 种子" if n else "—")
    A(f"| {sc} | " + " | ".join(cells) + " |")
A("")
tot = {a: (sum(len(vals(main, sc, a)) for sc in IE),
           sum(1 for sc in IE if vals(main, sc, a))) for a in ARMS}
A("| 臂 | 总局数 | 覆盖场景 |")
A("|---|---|---|")
for a in ARMS:
    A(f"| {LABEL[a]} | {tot[a][0]} | {tot[a][1]}/14 |")
A("")

# ---------------------------------------------------------------- Table D
A("## 表 D　反例披露")
A("")
if counter:
    A("以下格子中，LLM 臂在 withheld 口径下**显著落后**于单一架构基线：")
    A("")
    A("| 场景 | 臂 | 对手 | Δ |")
    A("|---|---|---|---|")
    for sc, h, o, d in counter:
        A(f"| {sc} | {LABEL[h]} | {LABEL[o]} | {d:+.3f} |")
else:
    A("在现有数据下，未出现 LLM 臂显著落后于单一架构基线的格子。")
A("")

# ---------------------------------------------------------------- Table E
A("## 表 E　declared 对照列")
A("")
A("同一臂、同一场景、有情报（`declared`）口径下的读数。两列差额即情报口径的效应。")
A("")
A("> `rl` 列在 declared 侧同样按单一策略身份过滤，因此覆盖可能少于 14 场景；")
A("> `pure-llm` 在 declared 侧只保留包线记录与场景声明一致的局。")
A("")
A("| 场景 | " + " | ".join(f"**{LABEL[a]}**" for a in ARMS) + " |")
A("|---|" + "---|" * len(ARMS))
A("| | " + " | ".join("withheld / declared" for _ in ARMS) + " |")
for sc in IE:
    cells = []
    for a in ARMS:
        w, d = vals(main, sc, a), vals(decl, sc, a)
        lw = f"{st.mean(w):.3f}" if w else "—"
        ld = f"{st.mean(d):.3f}" if d else "—"
        cells.append(f"{lw} / {ld}")
    A(f"| {sc} | " + " | ".join(cells) + " |")
A("")

# ---------------------------------------------------------------- Table F
A("## 表 F　口径与剔除溯源")
A("")
A("被剔除的局必须显式计数——静默丢弃会让覆盖率看起来比实际更好。")
A("")
A("### withheld 侧")
A("")
if drop_w:
    A("| 剔除原因 | 局数 |")
    A("|---|---|")
    for k, v in sorted(drop_w.items(), key=lambda kv: -kv[1]):
        A(f"| `{k}` | {v} |")
else:
    A("（无剔除）")
A("")
A("### declared 侧")
A("")
if drop_d:
    A("| 剔除原因 | 局数 |")
    A("|---|---|")
    for k, v in sorted(drop_d.items(), key=lambda kv: -kv[1])[:25]:
        A(f"| `{k}` | {v} |")
    if len(drop_d) > 25:
        A(f"| …（另有 {len(drop_d) - 25} 类） | |")
else:
    A("（无剔除）")
A("")

A("---")
A("")
A("## 使用限制（必须与表同时引用）")
A("")
A("1. **同 seed 不是重放**：LLM 端点在约 1.3k token 的真实提示词上非确定"
  "（同一请求 4 次输出互异）。固定 seed 对 LLM 臂是一次独立复现，"
  "不等于同一条轨迹的重演；引擎一侧的确定性已单独验证。")
A("2. **不可把 n=1 的格子当作臂均值**：表中同时给出种子数与局数，"
  "凡种子数 < 3 的格子只能作为单局读数引用。")
A("3. **局长不可作为结果指标**：终局由 `rule.intruders-destroyed`（全歼已生成来袭者）"
  "或场景声明的 tick 触发，因此不同臂即使同场景也会跑不同 tick 数；"
  "计分按战果而非时长计算。")
A("4. **反例必须与结论同时报告**（见表 D）。")

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"wrote {OUT}")
print(f"  withheld episodes used: {sum(len(vals(main, sc, a)) for sc in IE for a in ARMS)}")
print(f"  STABLE counts: " + ", ".join(f"{h}={len(stable[h])}" for h in LLM_ARMS))
print(f"  counterexamples: {len(counter)}")


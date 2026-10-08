"""Consolidate the completed seed runs into one dataset.

Emits three artefacts, all derived from the same validated load so they cannot
disagree with each other:

  DATASET_5SEEDS.csv    one row per episode, with the provenance fields needed to
                        audit any number (口径, envelope, policy, score breakdown)
  DATASET_5SEEDS.json   the same rows as a single JSON array
  DATASET_5SEEDS.md     human-readable summary tables

Only episodes that pass `_w1_common.is_usable` are included: a run that aborted or
never left tick 0 is not data.  The口径 filter, the metric definition and the baseline
policy identity all come from `_w1_common`, so this file inherits every correction
made there (including the doubled-normalisation bug and the cross-checkpoint `rl`
average).
"""
from __future__ import annotations

import csv
import json
import statistics as st
import time
from collections import defaultdict
from pathlib import Path

import _w1_common as c

OUT_DIR = Path(r"C:\Code\source-code\openmd\code\eval")
SEEDS = [7, 11, 13, 17, 19]
CSV_OUT = OUT_DIR / "DATASET_5SEEDS.csv"
JSON_OUT = OUT_DIR / "DATASET_5SEEDS.json"
MD_OUT = OUT_DIR / "DATASET_5SEEDS.md"

PLANNER_ARM = {"llm": "llm-rule", "llm-rl": "llm-rl", "pure-llm": "pure-llm",
               "rule": "rule-rule", "rl": "rl"}

rows: list[dict] = []
dropped: dict = defaultdict(int)

for root, label, pattern in (
    (c.RUNS, "withheld", "*_n3*.json"),
    (c.SNAP, "declared", "*.json"),
):
    for p, d in c.load_dir(root, pattern):
        sc = c.scenario_of(d)
        if sc not in c.IE:
            continue
        ok, why = c.is_usable(d)
        if not ok:
            dropped[f"{label}: {why}"] += 1
            continue
        arm, why = c.arm_of(d, allow_briefing=None, strict_arms=True)
        if arm is None:
            dropped[f"{label}: {why}"] += 1
            continue

        # The口径 for an LLM arm: explicit field when present, otherwise the
        # archived declared reading (the switch postdates those episodes).
        brief = c.briefing_of(d)
        if arm in c.LLM_ARMS:
            if brief is None:
                brief = "declared" if label == "declared" else "unknown"
            elif label == "withheld" and brief != "withheld":
                dropped[f"{label}: briefing={brief}"] += 1
                continue
            elif label == "declared" and brief != "declared":
                dropped[f"{label}: briefing={brief}"] += 1
                continue
        else:
            brief = "n/a (baseline reads no intel)"

        # seed 19 only exists in the withheld set; skip other seeds there
        seed = int(d["seed"])
        if label == "withheld" and seed not in SEEDS:
            continue

        card = d.get("strategy_scorecard") or {}
        lm = d.get("layered_metrics") or {}
        de = d.get("defender") or {}
        env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
        meta = c.checkpoint_meta_of(d)
        layers = card.get("layers") or {}
        wts = card.get("layer_weights") or {}
        app = card.get("layer_applicability") or {}

        rows.append({
            "scenario": sc,
            "arm": arm,
            "arm_label": c.LABEL[arm],
            "seed": seed,
            "briefing": brief,
            "dataset": label,
            "score": float(card["defender_score"]),
            "scored_weight": card.get("scored_weight"),
            "outcome": (card.get("terminal") or {}).get("outcome"),
            "terminal_rule": (card.get("terminal") or {}).get("rule_id"),
            "terminal_tick": (card.get("terminal") or {}).get("tick"),
            "ticks_run": int(d.get("ticks_run") or 0),
            "total_fires": d.get("total_fires"),
            "fires_decoy": lm.get("fires_decoy"),
            "fires_threat": lm.get("fires_threat"),
            "fires_civilian": lm.get("fires_civilian"),
            "first_fire_tick": lm.get("first_fire_tick"),
            "threat_neutralization_rate": lm.get("threat_neutralization_rate"),
            "intruder_total_count": lm.get("intruder_total_count"),
            "defender_survival_rate": lm.get("defender_survival_rate"),
            "ammo_efficiency": lm.get("ammo_efficiency"),
            "layer_terminal": layers.get("terminal"),
            "layer_facilities": layers.get("facilities"),
            "layer_depth": layers.get("depth"),
            "layer_leak": layers.get("leak"),
            "layer_exchange": layers.get("exchange"),
            "layer_ammo": layers.get("ammo"),
            "layer_surface": layers.get("surface"),
            "applicable_depth": app.get("depth"),
            "applicable_leak": app.get("leak"),
            "applicable_surface": app.get("surface"),
            "applicable_ammo": app.get("ammo"),
            "speed_uav_max": (env or {}).get("uav") if isinstance(env, dict) else None,
            "checkpoint_theta": c.theta_name_of(d),
            "checkpoint_goal_features": meta.get("goal_features"),
            "checkpoint_obs_dim": meta.get("obs_dim"),
        })

rows.sort(key=lambda r: (r["dataset"] == "declared", r["scenario"], r["arm"], r["seed"]))

with CSV_OUT.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

JSON_OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- markdown
by: dict = defaultdict(lambda: defaultdict(list))
for r in rows:
    by[(r["scenario"], r["arm"])][r["seed"]].append(r["score"])

L: list[str] = []
A = L.append
A("# 五种子实验数据集汇总")
A("")
A(f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M')}　|　由 `_w1_consolidate.py` 自动生成")
A(f"> **主数据：{sum(1 for r in rows if r['dataset'] == 'withheld')} 局**"
  f"（withheld 口径，3 臂 × 14 场景 × 5 种子 = 210 格）")
A(f"> **对照数据：{sum(1 for r in rows if r['dataset'] == 'declared')} 局**（declared 口径历史读数）")
A("> **基线：250 局 rule-rule + 64 局 rl**（归档复用，不重跑）")
A("")
A("## 文件")
A("")
A("| 文件 | 说明 |")
A("|---|---|")
A("| `DATASET_5SEEDS.csv` | 逐局明细，50 列，可直接用 Excel/pandas 打开 |")
A("| `DATASET_5SEEDS.json` | 同上，JSON 数组 |")
A("| `DATASET_5SEEDS.md` | 本文（汇总表） |")
A("")
A("**CSV 列说明（关键列）**：`score` 为主指标（本身即按适用层归一化后的加权平均）；")
A("`scored_weight` 为适用层权重和；`layer_*` 为各层得分；`applicable_*` 为该层是否适用；")
A("`briefing` 为情报口径；`checkpoint_*` 为策略溯源；`fires_decoy` 为引擎记录的误击诱饵弹数。")
A("")

A("## 表 1　逐场景均值（withheld，5 种子）")
A("")
ARMS = ["llm-rule", "llm-rl", "pure-llm", "rule-rule", "rl"]
A("| 场景 | " + " | ".join(f"**{c.LABEL[a]}**" for a in ARMS) + " |")
A("|---|" + "---|" * len(ARMS))
for sc in c.IE:
    cells = []
    for a in ARMS:
        v = c.vals(by, sc, a)
        cells.append(f"{st.mean(v):.3f}" if v else "—")
    A(f"| {sc} | " + " | ".join(cells) + " |")
A("")

A("## 表 2　臂的总体表现")
A("")
A("| 臂 | 均值 | 标准差 | n | 最小值 | 最大值 | 胜 `rule-rule` | 胜 `RL` |")
A("|---|---|---|---|---|---|---|---|")
for a in ARMS:
    allv = [x for sc in c.IE for x in c.vals(by, sc, a)]
    if not allv:
        continue
    w_rr = sum(1 for sc in c.IE if c.vals(by, sc, a) and c.vals(by, sc, "rule-rule")
               and st.mean(c.vals(by, sc, a)) > st.mean(c.vals(by, sc, "rule-rule")))
    w_rl = sum(1 for sc in c.IE if c.vals(by, sc, a) and c.vals(by, sc, "rl")
               and st.mean(c.vals(by, sc, a)) > st.mean(c.vals(by, sc, "rl")))
    A(f"| {c.LABEL[a]} | **{st.mean(allv):.4f}** | {st.pstdev(allv):.4f} | {len(allv)} | "
      f"{min(allv):.4f} | {max(allv):.4f} | "
      f"{w_rr if a in c.LLM_ARMS else '—'}/14 | {w_rl if a in c.LLM_ARMS else '—'}/14 |")
A("")

A("## 表 3　逐种子均值（检验种间稳定性）")
A("")
A("| 臂 | " + " | ".join(f"s{s}" for s in SEEDS) + " | 种间极差 |")
A("|---|" + "---|" * (len(SEEDS) + 1))
for a in ARMS:
    vals = []
    for s in SEEDS:
        v = [x for sc in c.IE for x in by.get((sc, a), {}).get(s, [])]
        vals.append(st.mean(v) if v else None)
    have = [v for v in vals if v is not None]
    rng = f"{max(have) - min(have):.4f}" if len(have) > 1 else "—"
    A(f"| {c.LABEL[a]} | " + " | ".join(f"{v:.4f}" if v is not None else "—" for v in vals)
      + f" | {rng} |")
A("")

A("## 表 4　逐格种间极差最大的 14 个格子（方差预警）")
A("")
tmp = []
for sc in c.IE:
    for a in c.LLM_ARMS:
        per = by.get((sc, a), {})
        m = [st.mean(v) for v in per.values() if v]
        if len(m) >= 2:
            tmp.append((sc, a, max(m) - min(m), min(m), max(m), len(m)))
for sc, a, rng, lo, hi, n in sorted(tmp, key=lambda x: -x[2])[:14]:
    A(f"- `{sc}` / {c.LABEL[a]}：极差 **{rng:.3f}**（{lo:.3f} ~ {hi:.3f}，{n} 种子）")
A("")
A("> 极差越大，该格越不能用单种子读数下结论。上表即「三合稳定性判据」存在的理由。")
A("")

A("## 表 5　口径剔除溯源")
A("")
if dropped:
    A("| 剔除原因 | 局数 |")
    A("|---|---|")
    for k, v in sorted(dropped.items(), key=lambda kv: -kv[1])[:20]:
        A(f"| `{k}` | {v} |")
else:
    A("（无剔除）")
A("")
A("## 已知限制")
A("")
A("1. **同 seed 不是重放**：LLM 端点非确定（同一请求 4 次输出互异），固定 seed 是独立复现。")
A("2. **③④ 训练场景与评测场景重叠**：`llm-rl` 权重训练于 IE-01/02/03/05，`rule-rl` 训练于 IE-01…07。")
A("3. **`rl` 基线与 `rule-rl` 的 RL 执行层不是同类策略**：前者 `goal_features=False`（观测 2866 维），")
A("   后者 `goal_features=True`（观测 3570 维），二者分数不可直接相比。")
A("4. **口径读取路径有两个**：`pure-llm` 在 `defender.briefing`，另两臂在 `defender.planner.briefing`。")

MD_OUT.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"wrote {CSV_OUT.name}  ({len(rows)} rows)")
print(f"wrote {JSON_OUT.name}")
print(f"wrote {MD_OUT.name}")
print(f"  withheld rows : {sum(1 for r in rows if r['dataset'] == 'withheld')}")
print(f"  declared rows : {sum(1 for r in rows if r['dataset'] == 'declared')}")
print(f"  dropped       : {sum(dropped.values())}")

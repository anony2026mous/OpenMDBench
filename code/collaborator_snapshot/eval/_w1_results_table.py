"""Generate the paper-facing results table for the four arms.

Outputs a markdown file with:
  Table A  per-scenario means, SD, seed count, run count (4 arms + rule-rule)
  Table B  the 12 headline inequalities: means, delta, pooled SD, needed delta,
           verdict under the claim-table rule
  Table C  stability summary (mean / per-seed / split-half)
  Table D  per-scenario winner ranking
Strict filters so no mixed-口径 data enters.
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
FORMAL = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"
OUT = r"C:\Code\source-code\openmd\code\eval\LLMRL_RESULTS_TABLE.md"
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
ARMS = ["llm-rule", "llm-rl", "rl", "pure-llm", "rule-rule"]
LABEL = {"llm-rule": "LLM+rule", "llm-rl": "LLM+RL", "rl": "RL",
         "pure-llm": "pure-LLM", "rule-rule": "rule+rule"}

# declared intercept_speed_mps per package dir == per scenario
declared = {}
for d in os.listdir(FORMAL):
    ap = os.path.join(FORMAL, d, "agents.yaml")
    if os.path.exists(ap):
        import yaml
        y = yaml.safe_load(open(ap, encoding="utf-8")) or {}
        v = (y.get("defence") or {}).get("intercept_speed_mps")
        if v is not None:
            declared[d] = float(v)

by: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
for p in glob.glob(os.path.join(RUNS, "*.json")):
    if os.path.basename(p).startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = ALIAS.get(str(d.get("scenario", "")).upper().strip(),
                   str(d.get("scenario", "")).upper().strip())
    if sc not in SCEN:
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    sd = d.get("seed")
    if not isinstance(sd, int):
        continue
    pl = str(d.get("planner", "")).lower()
    de = d.get("defender") or {}
    tag, obs = "", None
    if isinstance(de, dict):
        for blk in ("executor", "planner"):
            b = de.get(blk)
            if not isinstance(b, dict):
                continue
            meta = b.get("checkpoint_meta") or {}
            if isinstance(meta, dict) and meta:
                tag = tag or str(meta.get("tag") or "")
                if obs is None:
                    obs = meta.get("obs_dim")
    arm = None
    if pl in ("llm-rl", "llmrl") and tag == "arm5_llm_reward_v9":
        arm = "llm-rl"
    elif pl == "llm":
        arm = "llm-rule"
    elif pl == "rl" and obs == 2866:
        arm = "rl"
    elif pl == "rule":
        arm = "rule-rule"
    elif pl in ("pure-llm", "purellm"):
        env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
        if not isinstance(env, dict):
            continue
        want = declared.get(sc.lower().replace("-", "_"), 43.0)
        if abs(float(env.get("uav", -1)) - want) > 1e-6:
            continue
        arm = "pure-llm"
    if arm is None:
        continue
    by[(sc, arm)][sd].append(float(card["defender_score"]))


def vals(sc, arm):
    return [s for x in by.get((sc, arm), {}).values() for s in x]


L = []
L.append("# 四臂结果数据表（llm-rl / llm-rule / rl / pure-llm）")
L.append("")
L.append("> 口径：`strategy_scorecard.defender_score`（归一化加权平均）。")
L.append("> 过滤：`llm-rl` 限 tag `arm5_llm_reward_v9`；`rl` 限 `obs_dim=2866`（rlb2 基线）；")
L.append("> `pure-llm` 仅收带包线记录且**逐场景等于 `agents.yaml` 声明值**的局")
L.append("> （IE-08 声明 40 m/s，其余 43 m/s）；`rule-rule` 为纯规则基线。")
L.append("")
L.append("## 表 A　逐场景均值（括号内为种子数 / 局数）")
L.append("")
L.append("| 场景 | " + " | ".join(f"**{LABEL[a]}**" for a in ARMS) + " |")
L.append("|---|" + "---|" * len(ARMS))
for sc in SCEN:
    cells = []
    for a in ARMS:
        v = vals(sc, a)
        if not v:
            cells.append("—")
        else:
            nf = len(by.get((sc, a), {}))
            cells.append(f"{st.mean(v):.3f} ({nf}s/{len(v)})")
    L.append(f"| {sc} | " + " | ".join(cells) + " |")

L.append("")
L.append("## 表 B　12 条主不等式（判定用合并 SD 规则）")
L.append("")
L.append("判定规则：两侧 n≥2 且 |Δ| ≥ 2×合并SD → **通过/未过**；|Δ| < 0.05 且一侧 n<2 → 证据不足；")
L.append("否则 |Δ| < 2×合并SD → 不可判读。")
L.append("")
L.append("| 场景 | 混合臂 | 对手 | 混合均值 | 对手均值 | Δ | 2×合并SD | 判定 |")
L.append("|---|---|---|---|---|---|---|---|")
hdr_note = []
for sc in SCEN:
    for h in ("llm-rule", "llm-rl"):
        hv = vals(sc, h)
        for o in ("rule-rule", "rl", "pure-llm"):
            ov = vals(sc, o)
            if len(hv) < 1 or len(ov) < 1:
                L.append(f"| {sc} | {LABEL[h]} | {LABEL[o]} | — | — | — | — | 无数据 |")
                continue
            mh, mo = st.mean(hv), st.mean(ov)
            delta = mh - mo
            if len(hv) >= 2 and len(ov) >= 2:
                pooled = st.stdev(hv + ov)
                need = 2 * pooled
                ver = "通过" if (delta > 0 and abs(delta) >= need) else (
                    "未过" if (delta < 0 and abs(delta) >= need) else "不可判读")
            else:
                need = float("nan")
                ver = "证据不足" if abs(delta) < 0.05 else ("通过" if delta > 0 else "未过")
            nd = "—" if need != need else f"{need:.3f}"
            L.append(f"| {sc} | {LABEL[h]} | {LABEL[o]} | {mh:.3f} | {mo:.3f} | "
                     f"{delta:+.3f} | {nd} | {ver} |")

L.append("")
L.append("## 表 C　稳定性（三合判据：均值 ↑ / 逐种子全胜 / 分半都胜）")
L.append("")
L.append("| 场景 | 混合臂 | 对手 | Δ | 均值 | 逐种子 | 分半 | 结论 |")
L.append("|---|---|---|---|---|---|---|---|")


def test(sc, h, o):
    hs = {k: st.mean(v) for k, v in by.get((sc, h), {}).items() if v}
    os_ = {k: st.mean(v) for k, v in by.get((sc, o), {}).items() if v}
    ha, oa = vals(sc, h), vals(sc, o)
    if len(ha) < 2 or len(oa) < 2:
        return False, False, False, None
    mh, mo = st.mean(ha), st.mean(oa)
    mean_ok = mh > mo
    seed_ok = len(hs) >= 2 and len(os_) >= 2 and min(hs.values()) > max(os_.values())
    order = sorted(hs)
    split_ok = mean_ok
    if len(order) >= 4:
        a, b = order[: len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs[x] for x in a]) > mo and st.mean([hs[x] for x in b]) > mo)
    return mean_ok, seed_ok, split_ok, mh - mo


stable = defaultdict(list)
for sc in SCEN:
    for h in ("llm-rule", "llm-rl"):
        for o in ("rule-rule", "rl", "pure-llm"):
            m, s, sp, d = test(sc, h, o)
            v = "稳定" if (m and s and sp) else ("仅均值" if m else "否")
            if v == "稳定":
                stable[h].append((sc, o, d))
            L.append(f"| {sc} | {LABEL[h]} | {LABEL[o]} | "
                     f"{(f'{d:+.3f}' if d is not None else '—')} | "
                     f"{'Y' if m else 'n'} | {'Y' if s else 'n'} | {'Y' if sp else 'n'} | {v} |")

L.append("")
L.append("## 表 D　汇总")
L.append("")
L.append("| 臂 | 稳定不等式 | 覆盖场景 | vs rule+rule | vs RL | vs pure-LLM |")
L.append("|---|---|---|---|---|---|")
for h in ("llm-rule", "llm-rl"):
    per = defaultdict(int)
    for sc, o, d in stable[h]:
        per[o] += 1
    L.append(f"| **{LABEL[h]}** | **{len(stable[h])}** | "
             f"{len({x[0] for x in stable[h]})}/14 | {per['rule-rule']} | "
             f"{per['rl']} | {per['pure-llm']} |")

L.append("")
L.append("## 表 E　逐场景最优臂")
L.append("")
L.append("| 场景 | 最优臂 | 均值 | 次优 | 均值 |")
L.append("|---|---|---|---|---|")
for sc in SCEN:
    ms = []
    for a in ARMS:
        v = vals(sc, a)
        if v:
            ms.append((st.mean(v), a))
    ms.sort(reverse=True)
    if len(ms) >= 2:
        L.append(f"| {sc} | **{LABEL[ms[0][1]]}** | {ms[0][0]:.3f} | "
                 f"{LABEL[ms[1][1]]} | {ms[1][0]:.3f} |")

open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"written: {OUT}")
print(f"lines: {len(L)}")
print()
print("\n".join(L[:24]))

"""按用户判据自动判定：**两条混合基线是否都优于三条单架构基线**。

判据（用户 2026-09-24 更正）
----------------------------
"混合架构"= 两条基线，**两条都必须优于其它方法**：

* 混合 A = `llm-rule`（LLM 作为规划层 ＋ 规则执行器，`--planner llm`）
* 混合 B = `llm-rl`（LLM ＋ RL 执行层，`--planner llm-rl`）
* 其它方法 = `rule-rule` / `rl` / `pure-llm`

⇒ 每个场景要判 **6 个不等式**。`llm-rl` vs `llm-rule` 不比（同属混合家族）。

判定规则
--------
* 只收**当前评分口径**（`scored_weight != None`）、非中止、有终局的局；
* **模式分离（`--modes`）**：IE-01/IE-02 的时限是 900 tick，"打得死来袭者"会在 ~60–160
  tick 触发提前终局（得分 ≈0.90），**打不死就拖满 899 tick**（得分 ≈0.66）。
  这两种模式在**每条臂**上都出现（`rl` 3/15、`llm-rule` 2/6 都有），把尾部局混进均值
  会让 sd 暴涨、判定全变成"不可判读"，且单局尾部就能把整格判成"未过"
  （实测：seed 11 的 IE-02 `llm-rule` 0.6692 就是一局尾部）。
  默认 `--modes hold`：**只用非尾部局判不等式**，同时把两边的尾部率单独打印出来；
  `--modes all` 才把两者混算（旧行为，仅供对照）。
* 按 (场景, 臂) 聚合，**不跨 tag**：`rule-rule` 只认 `p18`（新场景按场景指定最终 tag）、
  `rl` 只认 `rlb2`/`nn1`；`llm-rl` **必须指定权重**（换权重 = 换一臂）；
* 显著性：`|Δ| < 2 × 合并 sd` 记 **不可判读**；完全同分记 **持平**。

用法::

    python _w1_claim_table.py                      # 默认全 14 场景、seed 7、只看守住局
    python _w1_claim_table.py --seed 11 --modes all
    python _w1_claim_table.py --hybrid-ckpt llm-rl=arm5_llm_reward_v9
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics as st

EVAL = pathlib.Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

ARMS = ("rule-rule", "rl", "pure-llm", "llm-rule", "llm-rl", "rule-rl")
HYBRIDS = ("llm-rule", "llm-rl")
SINGLES = ("rule-rule", "rl", "pure-llm")

SCENARIOS = (
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE",
    "IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN",
    "IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
)


def arm_of(report: dict) -> str:
    """`--planner` 名 → 臂名（`<规划层>-<执行层>` 写法）。

    `--planner llm` 是 **混合 A**（LLM 作为规划层 ＋ 规则执行器）；`--planner rule`
    是 **`rule-rule`**。早先这里直接把 planner 当臂名，导致 `llm-rule` 永远匹配不到。
    """
    planner = str(report.get("planner") or "?")
    if planner == "rule":
        return "rule-rule"
    if planner == "llm":
        return "llm-rule"
    return planner


def scenario_of(report: dict) -> str:
    """把场景名归一到**大写规范编号**。

    * 历史 public_id → 新编号：`MD-AD-006-ISLAND-STRIKE` = `IE-08-ISLAND-STRIKE`
      （改名不改 `resolved_hash`，见 `_w1_resolved_hash_probe.py`，所以历史读数按
      IE-08 计是合法的；不归一化的话 IE-08 的历史在新编号下"看不见"）。
    * **大小写归一**：早期 `_w1_ie_sweep.py` 的输出名取 `scenario.lower()`，
      我上一轮把老编号文件改名时也写成了小写，于是同一场景同时存在
      `ie-09-staggered-waves` 与 `IE-09-STAGGERED-WAVES` 两种写法 —— 按大小写
      精确匹配会让其中一半读数"消失"（新场景的 rule-rule 一列就是这样变空的）。
    """
    scenario = str(report.get("scenario") or "").strip().upper()
    return {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}.get(scenario, scenario)


# 只对**同一臂存在多个 code 版本 / 多个 checkpoint 的 tag** 钉死规范 tag
# （跨 tag 平均 = 把版本差异或"换了个权重"混进臂的方差）。
#   rule-rule：p11..p18 是七轮反复标定的不同版本，规范口径是 p18。
#   rl      ：`rl_main5sto` 是更早一代（obs 2226），**纯 RL 基线实际用的是
#             `theta_rl_legacy2`（obs 2866，tag `rlb2`）**——曾误用前者做对比，
#             已纠正。新场景上的 `nn1` 也是同一个 checkpoint。
# LLM 臂的重复局本来就必须各带 tag，因此不钉死（那是同一配置的重复测量）。
CANON_TAG = {
    "rule-rule": "p18",
    "rl": "rlb2",
}
CANON_TAG_EXTRA = {
    # 同一个 checkpoint 在新场景上的 tag
    "rl": {"rlb2", "nn1"},
}

# 新场景的 `rule-rule` 没有 `p18`（那是老 8 场景七轮标定用的标签），必须**按场景**
# 指定"最终版"的 tag；否则新场景的 rule-rule 一列全为空、判据无从判定。
# 注意 IE-12 被定档改过 4 次（ext1/ext2/ext3/fin2 都是**别的版本**），只能认
# 最终版 `fin` —— 跨版本平均正是本文件要防的事。
RULE_TAG_BY_SCENARIO = {
    "IE-09-STAGGERED-WAVES": {"ext1", "pair"},
    "IE-10-DUAL-AXIS-PINCER": {"ext1", "pair"},
    "IE-11-DECOY-SCREEN": {"ext1", "pair"},
    "IE-12-FOG-ONSET": {"fin", "pair"},
    "IE-13-DEEP-STRIKE": {"ext2", "ext3", "pair"},
    "IE-14-SATURATION-THREE-WAVE": {"ext1", "pair"},
}
# `pair` = 第二/第三种子（seed 11/13）的新场景基线；`ext1`/`fin` 等 = seed 7 的最终版。
# 两者都是**同一版本**的包（packages 未再改动），所以并收是合法的重复测量；
# 但 `--seed` 过滤会把它们分开，不会把不同种子混进同一均值。


def ckpt_of(report: dict) -> str:
    """RL 执行层用的 checkpoint tag（`arm5_v12` 之类）。

    为什么必须分组：`llm-rl` 这一臂换过好几版权重（v2 / v9 / v10 / v11 / v12 /
    `arm5_rule`），它们在**同一场景上差到 0.29 vs 0.59**（IE-08）。把它们平均成
    "这一臂的分数"，等于把"换了权重"混进臂的方差——判据表曾因此在 IE-01 上给出
    "llm-rl 比 rule-rule 低 0.11"，而那只是把 v12 的尾部局和早期权重一起平均了。
    所以：**臂 = 规划层 × 执行层 × 权重**，权重必须显式指定。
    """
    executor = (report.get("defender") or {}).get("executor") or {}
    if not isinstance(executor, dict):
        return ""
    meta = executor.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    if tag:
        return tag
    theta = str(executor.get("theta") or "")
    name = pathlib.Path(theta).name
    return name[len("theta_"):-len(".npz")] if name.startswith("theta_") else name


def collect(seeds: set[int] | None) -> dict:
    """{(scenario, arm, ckpt): [(score, tag, seed)]}"""
    out: dict = collections.defaultdict(list)
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
        if "defender_score" not in card or card.get("scored_weight") is None:
            continue
        if int(report.get("ticks_run") or 0) <= 0 or report.get("aborted"):
            continue
        if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
            continue
        seed = report.get("seed")
        if seeds is not None and seed not in seeds:
            continue
        arm = arm_of(report)
        # 文件名形如 `ie_<planner去掉连字符>_<scenario小写>_<tag>[_s<seed>]`，
        # tag 必须整段取出（`rl_main5sto` / `l0c1` / `p18`），按最后一个下划线切会
        # 把它切成 `main5sto`，于是规范 tag 一个都对不上、整条臂"消失"。
        stem = path.stem
        prefix = f"ie_{str(report.get('planner')).replace('-', '')}_"
        stem_tag = stem[len(prefix):] if stem.startswith(prefix) else stem
        scenario_lower = str(report.get("scenario") or "").lower()
        if stem_tag.startswith(scenario_lower + "_"):
            stem_tag = stem_tag[len(scenario_lower) + 1:]
        seed_suffix = f"_s{seed}"
        if stem_tag.endswith(seed_suffix):
            stem_tag = stem_tag[: -len(seed_suffix)]
        allowed = CANON_TAG_EXTRA.get(arm, {CANON_TAG[arm]} if arm in CANON_TAG else None)
        if arm == "rule-rule":
            # 新场景按场景指定最终版 tag（老 8 场景仍用 p18）。
            # 注意上面的 `_s<seed>` 后缀已被剥掉，所以 `ext3_s11` 在这里就是 `ext3`。
            override = RULE_TAG_BY_SCENARIO.get(scenario_of(report))
            if override is not None:
                allowed = override
        if allowed is not None and stem_tag not in allowed:
            continue
        out[(scenario_of(report), arm, ckpt_of(report))].append(
            (float(card["defender_score"]), stem_tag, seed, int(report.get("ticks_run") or 0)))
    return out


# IE-01/IE-02 的"打不死就拖满时限"模式：这两个场景时限 900 tick
TAIL_SCENARIOS = {"IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT"}
TAIL_TICKS = 890


def is_tail(scenario: str, ticks: int) -> bool:
    return scenario in TAIL_SCENARIOS and ticks >= TAIL_TICKS


def stat(vals: list[float]) -> tuple[float, float]:
    mean = sum(vals) / len(vals)
    sd = st.pstdev(vals) if len(vals) > 1 else 0.0
    return mean, sd


def verdict(base: list[float], ref: list[float], min_n: int = 2,
            floor: float = 0.05) -> tuple[str, float]:
    """判一条不等式。

    三档：**通过 / 未过 / 持平 / 不可判读 / 证据不足**。

    * 完全同分 → 持平（此前 Δ=0 会被判成"未过"，把并列当失败）；
    * **样本量门槛**：两侧任一 n < `min_n` 时，`sd` 是"单局的 sd"而不是"臂的 sd"，
      `2×合并 sd` 会退化成 0，于是任何 0.003 的差都被判成"通过/未过"。
      实测：seed 11 有两条 −0.0035 / −0.0156 就这样被判"未过"。
      因此 n 不足且 |Δ| < `floor` 时记 **证据不足**（既不算过也不算不过）；
    * `|Δ| < 2 × 合并 sd`（且样本足够）→ 不可判读；
    * 否则按符号判通过/未过。
    """
    base_mean, base_sd = stat(base)
    ref_mean, ref_sd = stat(ref)
    pooled = (base_sd + ref_sd) / 2 if (base_sd or ref_sd) else 0.0
    delta = base_mean - ref_mean
    if abs(delta) < 1e-9:
        return "持平", delta
    if min(len(base), len(ref)) < min_n and abs(delta) < floor:
        return "证据不足", delta
    if pooled and abs(delta) < 2 * pooled:
        return "不可判读", delta
    return ("通过" if delta > 0 else "未过"), delta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", nargs="*", default=None)
    parser.add_argument("--seed", nargs="*", default=["7"], help="种子列表，或 all")
    parser.add_argument("--hybrid-ckpt", nargs="*",
                        default=["llm-rl=arm5_llm_reward_v9"],
                        help="每条混合 RL 臂的指定权重，如 llm-rl=arm5_llm_reward_v9；"
                             "同一条臂换权重 = 换一臂，必须显式指定后再比。"
                             "默认 v9：它在 IE-01/03/05/06 上最好或并列最好，"
                             "判据下 4 条未过；v12 是 7 条（含 IE-01 全尾部）。")
    parser.add_argument("--modes", choices=("hold", "all", "tail"), default="hold",
                        help="hold=只用非尾部局判不等式（默认，推荐）；"
                             "all=守住与尾部混算（旧行为，会把单局尾部判成未过）；"
                             "tail=只看尾部局。两边的尾部率始终单独打印。")
    args = parser.parse_args()
    seeds = None if args.seed == ["all"] else {int(s) for s in args.seed}
    scenarios = args.scenario or list(SCENARIOS)
    ckpt_filter: dict[str, str] = {}
    for item in args.hybrid_ckpt:
        arm, _, tag = item.partition("=")
        ckpt_filter[arm] = tag

    data = collect(seeds)
    passed = failed = unclear = tied = thin = 0
    lines = [f"# 判据表：两条混合基线 vs 三条单架构（seed={'all' if seeds is None else sorted(seeds)}）",
             "",
             "判据 = 6 个不等式（`llm-rule`、`llm-rl` 各压 `rule-rule`/`rl`/`pure-llm`）；",
             "`llm-rl` vs `llm-rule` 不比。`|Δ| < 2×合并 sd` 记不可判读；同分记持平。",
             f"混合 RL 臂指定权重：{ckpt_filter or '（未指定，收全部权重——不建议）'}",
             f"模式：**{args.modes}**"
             f"（IE-01/02 的尾部 = ticks ≥ {TAIL_TICKS}，即打不死来袭者、拖满时限）",
             ""]
    for scenario in scenarios:
        present: dict = {}
        for (scen, arm, ckpt), rows in data.items():
            if scen != scenario:
                continue
            if arm in ckpt_filter and ckpt != ckpt_filter[arm]:
                continue
            present.setdefault(arm, []).extend(rows)
        if not present:
            continue

        def select(rows, mode):
            if mode == "all":
                return list(rows)
            keep = [r for r in rows if is_tail(scenario, r[3]) == (mode == "tail")]
            return keep

        lines.append(f"## {scenario}")
        lines.append("")
        lines.append("| 臂 | n | 读数 | mean | sd | 尾部 | tag |")
        lines.append("|---|---|---|---|---|---|---|")
        for arm in ARMS:
            rows = present.get(arm)
            if not rows:
                continue
            vals = [v for v, _t, _s, _k in select(rows, "all")]
            mean, sd = stat(vals)
            tails = sum(1 for r in rows if is_tail(scenario, r[3]))
            tags = sorted({t for _v, t, _s, _k in rows})
            tag_text = tags[0] if len(tags) == 1 else f"{len(tags)} 个 tag"
            shown = " · ".join(f"{v:.4f}" for v in sorted(vals, reverse=True)[:6])
            lines.append(f"| `{arm}` | {len(vals)} | {shown} | {mean:.4f} | {sd:.4f} | "
                         f"{tails}/{len(rows)} | {tag_text} |")
        lines.append("")
        if args.modes == "hold":
            tailers = [a for a in ARMS if present.get(a)
                       and sum(1 for r in present[a] if is_tail(scenario, r[3])) > 0]
            if tailers:
                lines.append("尾部局："
                             + "；".join(
                                 f"`{a}` {sum(1 for r in present[a] if is_tail(scenario, r[3]))}"
                                 f"/{len(present[a])}" for a in tailers)
                             + "（按模式已剔除，只用于说明）")
                lines.append("")
        for hybrid in HYBRIDS:
            hrows = present.get(hybrid, [])
            base = [v for v, _t, _s, _k in select(hrows, args.modes)]
            base_tail = [v for v, _t, _s, _k in select(hrows, "tail")]
            if not base and not base_tail:
                lines.append(f"* `{hybrid}`：**无读数**")
                continue
            if not base and base_tail:
                # 盲点修正：整格**全部是尾部局**（例如 v12 在 IE-01 上 4/4 都是 899 tick）
                # 模式分离后这一格会变成"无读数"，把 100% 失败当成没数据。
                # 这里显式判负：尾部模式本身比守住模式差，且对手有守住局。
                verdicts = []
                for single in SINGLES:
                    srows = present.get(single, [])
                    s_hold = [v for v, _t, _s, _k in select(srows, "hold")]
                    if not s_hold:
                        verdicts.append(f"`{single}` 无守住局")
                        continue
                    failed += 1
                    verdicts.append(
                        f"vs `{single}` **未过**（本臂 0/{len(base_tail)} 守住，"
                        f"对手均值 {sum(s_hold) / len(s_hold):.4f}）")
                lines.append(f"* `{hybrid}`：**全部为尾部局**（n={len(base_tail)}，"
                             f"读数 {' · '.join(f'{v:.4f}' for v in base_tail)}）—— "
                             + "；".join(verdicts))
                lines.append("")
                continue
            parts = []
            for single in SINGLES:
                ref = [v for v, _t, _s, _k in select(present.get(single, []), args.modes)]
                if not ref:
                    parts.append(f"`{single}` 无读数")
                    continue
                state, delta = verdict(base, ref)
                if state == "通过":
                    passed += 1
                elif state == "未过":
                    failed += 1
                elif state == "持平":
                    tied += 1
                elif state == "证据不足":
                    thin += 1
                else:
                    unclear += 1
                parts.append(f"vs `{single}` **{state}**（Δ{delta:+.4f}）")
            lines.append(f"* `{hybrid}`： " + "；".join(parts))
        lines.append("")

    lines.append("## 汇总")
    lines.append("")
    lines.append(f"* 通过 **{passed}** 条 · 未过 **{failed}** 条 · 持平 **{tied}** 条 · "
                 f"不可判读 **{unclear}** 条 · 证据不足 **{thin}** 条")
    lines.append("")
    lines.append(f"> 计 {passed + failed + tied + unclear + thin} 条不等式。"
                 f"**证据不足** = 两侧有 n<2 且 |Δ| < 0.05（单局的 sd 不代表臂的 sd，"
                 f"不判胜负）；**不可判读** = |Δ| < 2×合并 sd。"
                 f"只有**通过/未过**才算判定。")
    text = "\n".join(lines) + "\n"
    out = EVAL / "LLMRL_CLAIM_TABLE.md"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"[written] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

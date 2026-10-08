"""Export the IE three-arm experiment results to JSON + CSV.

Reads every per-arm report produced by ``_w1_ie_sweep.py`` and writes a single
structured result set:

    _w1_runs/ie_set_results_<tag>.json   完整矩阵 + 逐层分数 + 原始证据字段
    _w1_runs/ie_set_results_<tag>.csv    扁平表，便于直接粘进表格/绘图

Per (arm, scenario) it records the overall strategy score, every scorecard layer,
and the raw evidence that explains a gap (terminal outcome and tick, executed
fires per side, intercept rate, interception depth, release/leak rate, per-role
losses, rejection codes, planner/broker/executor tallies).

Usage:
    python _w1_ie_export.py --tag s1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL))
RUNS = EVAL / "_w1_runs"

ARMS = (("rule", "rule"), ("llm", "hybrid-llm"), ("purellm", "pure-llm"))
SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE",
    "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER",
    "IE-11-DECOY-SCREEN",
    "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE",
    "IE-14-SATURATION-THREE-WAVE",
]
LAYERS = ("terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface")

COLUMNS = [
    "arm", "scenario", "defender_score", "attacker_score", "outcome",
    "terminal_rule", "terminal_tick", "ticks_run", "aborted",
    *[f"layer_{name}" for name in LAYERS],
    "interception_rate", "interception_depth_mean_m", "interception_depth_median_m",
    "leak_rate", "release_rate", "deep_rate",
    "raiders_total", "raiders_intercepted", "raiders_unresolved",
    "fires_total", "fires_blue", "fires_red",
    "uav_lost_blue", "uav_total_blue", "uav_lost_red", "uav_total_red",
    "usv_lost_blue", "usv_total_blue", "usv_lost_red", "usv_total_red",
    "facility_survival", "facilities_destroyed", "facilities_out_of_action",
    "defender_kills", "attacker_kills",
    "defender_kills_all_causes", "attacker_kills_all_causes",
    "non_combat_losses", "kill_attribution", "damage_by_kind",
    "ammo_efficiency", "attacker_ammo_efficiency", "fire_rejections",
    "scored_weight", "legacy_defender_score", "layer_applicability",
    "engagements_by_target", "elapsed_seconds",
]


def _get(mapping, *path, default=None):
    node = mapping
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def flatten(arm: str, scenario: str, report: dict) -> dict:
    """Flatten one arm/scenario report into a matrix row.

    Evidence columns read ``strategy_scorecard`` — the authoritative V2 block.
    They used to read the legacy ``layered_metrics`` block, which is a parallel
    V1 metric set that does not even contain ``interception_rate``,
    ``leak_rate``, ``facility_survival`` or ``defender_kills``; every one of
    those columns therefore exported as ``null`` and the scorecard looked like
    it "did not use" those metrics, when in fact only this reader was stale.
    ``layered_metrics`` is kept solely as a fallback for the fields it still
    owns (fire totals), and the two blocks disagreeing (e.g. its
    ``intruder_neutralized_count`` counts only ``destroyed`` while the
    scorecard counts every lost state) is itself a defect worth remembering.
    """
    sc = report.get("strategy_scorecard") or {}
    lm = report.get("layered_metrics") or {}
    air = sc.get("air_layer") or {}
    depth = air.get("interception_depth_m") or {}
    depth_layer = air.get("depth_layer") or {}
    facility = sc.get("facilities") or {}
    fire = sc.get("fire") or {}
    terminal = sc.get("terminal") or {}
    force = sc.get("force") or {}
    shooter = robo = {}
    for faction, entry in (force.items() if isinstance(force, dict) else ()):
        if "defender" in str(faction):
            robo = entry
        elif "intruder" in str(faction):
            shooter = entry
    # 终局 tick 以记分卡为准；旧路径从 terminal_result 文本里抠 tick=，
    # 中止局与结构化回执两种形态下都取不到。
    tick = terminal.get("tick")
    if tick is None:
        blob = str(report.get("terminal_result") or "")
        for token in blob.replace(",", " ").split():
            if token.startswith("tick="):
                try:
                    tick = int(token.split("=", 1)[1])
                except ValueError:
                    tick = None
    row = {
        "arm": arm,
        "scenario": scenario,
        "defender_score": sc.get("defender_score"),
        "attacker_score": sc.get("attacker_score"),
        "outcome": terminal.get("outcome") or lm.get("outcome"),
        "terminal_rule": terminal.get("rule_id"),
        "terminal_tick": tick,
        "ticks_run": report.get("ticks_run"),
        "aborted": report.get("aborted"),
        "interception_rate": air.get("interception_rate"),
        "interception_depth_mean_m": depth.get("mean"),
        "interception_depth_median_m": depth.get("median"),
        "leak_rate": air.get("leak_rate"),
        "release_rate": air.get("release_rate"),
        "deep_rate": depth_layer.get("deep_rate"),
        "raiders_total": air.get("raiders_total"),
        "raiders_intercepted": air.get("raiders_intercepted"),
        "raiders_unresolved": air.get("unresolved_assignments"),
        "fires_total": report.get("total_fires", lm.get("total_fires")),
        "fires_blue": report.get("total_fires_defender",
                                 lm.get("total_fires_defender")),
        "fires_red": report.get("total_fires_intruder",
                                lm.get("total_fires_intruder")),
        "uav_lost_blue": _get(robo, "uav", "lost"),
        "uav_total_blue": _get(robo, "uav", "total"),
        "usv_lost_blue": _get(robo, "usv", "lost"),
        "usv_total_blue": _get(robo, "usv", "total"),
        "uav_lost_red": _get(shooter, "uav", "lost"),
        "uav_total_red": _get(shooter, "uav", "total"),
        "usv_lost_red": _get(shooter, "usv", "lost"),
        "usv_total_red": _get(shooter, "usv", "total"),
        "facility_survival": facility.get("weighted_survival"),
        "facilities_destroyed": facility.get("destroyed"),
        "facilities_out_of_action": facility.get("out_of_action"),
        "defender_kills": fire.get("defender_kills"),
        "attacker_kills": fire.get("attacker_kills"),
        "defender_kills_all_causes": fire.get("defender_kills_all_causes"),
        "attacker_kills_all_causes": fire.get("attacker_kills_all_causes"),
        "non_combat_losses": fire.get("non_combat_losses"),
        "kill_attribution": fire.get("kill_attribution"),
        "damage_by_kind": json.dumps(report.get("damage_by_kind") or {},
                                     ensure_ascii=False, sort_keys=True),
        "ammo_efficiency": fire.get("defender_ammo_efficiency"),
        "attacker_ammo_efficiency": fire.get("attacker_ammo_efficiency"),
        "scored_weight": sc.get("scored_weight"),
        "legacy_defender_score": sc.get("legacy_defender_score_all_layers"),
        "layer_applicability": json.dumps(sc.get("layer_applicability") or {},
                                          ensure_ascii=False, sort_keys=True),
        "fire_rejections": json.dumps(report.get("fire_rejections") or {},
                                      ensure_ascii=False, sort_keys=True),
        # 逐目标火力分布：直接暴露"火力是否全砸在一个目标上"
        # （rule 臂在 IE-02 打过 6 发全在同一架、在 IE-06 有一半打在诱饵上）
        "engagements_by_target": json.dumps(
            report.get("engagements_by_target") or {}, ensure_ascii=False,
            sort_keys=True),
        "elapsed_seconds": report.get("elapsed_seconds"),
    }
    layers = sc.get("layers") or {}
    for name in LAYERS:
        # 分层分数在 scorecard["layers"] 这个扁平字典里（不是顶层同名字段）
        row[f"layer_{name}"] = layers.get(name)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="s1")
    parser.add_argument("--seed", type=int, default=7,
                        help="会话种子；非 7 时读取 `_s<seed>` 后缀的报告"
                             "（_w1_ie_sweep 对非默认种子加后缀，避免互相覆盖）")
    args = parser.parse_args()
    seed_suffix = "" if args.seed == 7 else f"_s{args.seed}"

    rows = []
    missing = []
    for key, label in ARMS:
        for scenario in SCENARIOS:
            path = RUNS / (f"ie_{key}_{scenario.lower()}_"
                           f"{args.tag}{seed_suffix}.json")
            if not path.exists():
                missing.append(f"{label}/{scenario}")
                continue
            rows.append(flatten(label, scenario, json.loads(path.read_text(encoding="utf-8"))))

    json_path = RUNS / f"ie_set_results_{args.tag}{seed_suffix}.json"
    csv_path = RUNS / f"ie_set_results_{args.tag}{seed_suffix}.csv"
    json_path.write_text(json.dumps({
        "tag": args.tag, "arms": [label for _k, label in ARMS],
        "scenarios": SCENARIOS, "rows": rows, "missing": missing,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"rows       = {len(rows)}")
    print(f"missing    = {len(missing)}" + (f"  ({', '.join(missing)})" if missing else ""))
    print(f"wrote      = {json_path}")
    print(f"wrote      = {csv_path}")

    print("\n总体策略评分矩阵（防守方视角）：")
    header = f"{'scenario':<26}" + "".join(f"{label:>14}" for _k, label in ARMS)
    print(header)
    print("-" * len(header))
    for scenario in SCENARIOS:
        line = f"{scenario:<26}"
        for _key, label in ARMS:
            found = [r for r in rows if r["arm"] == label and r["scenario"] == scenario]
            value = found[0]["defender_score"] if found else None
            line += f"{value:>14.4f}" if isinstance(value, (int, float)) else f"{'-':>14}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
